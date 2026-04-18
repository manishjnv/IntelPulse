"""Bump Bedrock agent ORCHESTRATION maximumLength 1024 -> 4096.

Why
---
Amazon Bedrock agents created via the console default to
``promptCreationMode=DEFAULT`` with an ``ORCHESTRATION`` inference config
capped at ``maximumLength=1024`` output tokens. That cap is too tight for
IntelPulse news enrichment (27-field JSON schema) and causes the Supervisor
to emit preamble text instead of a clean JSON response — which is why
``AI_USE_AGENTS`` has stayed ``false`` for the news path.

The Bedrock API rejects a bare inference-config override when
``promptCreationMode=DEFAULT``. To bump the ceiling you must switch the
mode to ``OVERRIDDEN`` AND supply a full ``basePromptTemplate``. This
script does both by reading the current (default) template from
``get_agent`` and echoing it back alongside the bumped inference config.

What it does (per agent)
------------------------
1. ``get_agent`` -> pull the current ORCHESTRATION prompt config.
2. If already ``OVERRIDDEN`` with ``maximumLength >= 4096`` -> skip.
3. Otherwise ``update_agent`` with the ORCHESTRATION prompt flipped to
   ``OVERRIDDEN`` + ``maximumLength=4096`` + the existing base template.
   All other prompt types (PRE_PROCESSING, POST_PROCESSING, etc.) are
   preserved verbatim.
4. ``prepare_agent`` -> build the DRAFT into a ready-to-alias version.
5. Wait until prepared, then ``update_agent_alias`` to move the ``live``
   alias onto the new version.

Re-runnable; idempotent.

Usage
-----
    ssh intelpulse2 "docker exec intelpulse-api-1 python -m \\
        scripts.bump_agent_token_ceiling"

(The script lives under ``infra/scripts/`` in the repo, but the api
container only has ``/app/scripts/`` mounted, so copy it in first if you
run it that way. Locally from a machine with Bedrock agent creds:
``python -m infra.scripts.bump_agent_token_ceiling``.)
"""

from __future__ import annotations

import copy
import json
import sys
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
TARGET_MAX_LENGTH = 4096

# From project_multi_agent_future.md
AGENTS: list[dict[str, str]] = [
    {
        "name": "IntelPulse-Threat-Analyst",
        "agent_id": "FQBSERZQMP",
        "alias_id": "HLSRFAFL42",  # "live-v2"
        "alias_name": "live-v2",
    },
    {
        "name": "IntelPulse-IOC-Analyst",
        "agent_id": "UX0RYONP98",
        "alias_id": "SFDO1GO27Y",  # "live"
        "alias_name": "live",
    },
    {
        "name": "IntelPulse-Risk-Scorer",
        "agent_id": "WH4N4SUKMB",
        "alias_id": "BP6KQNKDUB",  # "live"
        "alias_name": "live",
    },
]


def _find_orchestration(
    poc: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, int]:
    """Return (config dict, index) for the ORCHESTRATION prompt, else (None, -1)."""
    for i, pc in enumerate((poc or {}).get("promptConfigurations", [])):
        if pc.get("promptType") == "ORCHESTRATION":
            return pc, i
    return None, -1


def _already_bumped(pc: dict[str, Any]) -> bool:
    if pc.get("promptCreationMode") != "OVERRIDDEN":
        return False
    cap = (pc.get("inferenceConfiguration") or {}).get("maximumLength")
    return isinstance(cap, int) and cap >= TARGET_MAX_LENGTH


def _build_overridden(pc: dict[str, Any]) -> dict[str, Any]:
    """Return a new ORCHESTRATION prompt config with mode=OVERRIDDEN + bumped cap.

    Copies the existing template verbatim so the agent's behavior is unchanged
    apart from the higher output ceiling.
    """
    new = copy.deepcopy(pc)
    new["promptCreationMode"] = "OVERRIDDEN"
    new.setdefault("promptState", "ENABLED")
    inf = dict(new.get("inferenceConfiguration") or {})
    inf["maximumLength"] = TARGET_MAX_LENGTH
    # Nova requires temperature/topP/topK/stopSequences to be present when
    # overriding — the existing pc already carries them from the default config.
    new["inferenceConfiguration"] = inf
    if not new.get("basePromptTemplate"):
        raise RuntimeError(
            "ORCHESTRATION prompt is missing basePromptTemplate — cannot override"
        )
    return new


def _strip_for_default(pc: dict[str, Any]) -> dict[str, Any]:
    """Strip fields Bedrock rejects when promptCreationMode=DEFAULT.

    Bedrock validates that DEFAULT-mode prompt configs do NOT carry
    basePromptTemplate, inferenceConfiguration, or promptState — those
    are only valid when promptCreationMode=OVERRIDDEN. The get_agent
    response echoes them (for readability), but update_agent rejects
    them. So for every config we're keeping as DEFAULT we strip them.
    """
    kept = {"promptType", "promptCreationMode", "parserMode"}
    return {k: v for k, v in pc.items() if k in kept}


def _build_update_payload(agent: dict[str, Any], new_orch: dict[str, Any]) -> dict[str, Any]:
    """Build the update_agent kwargs. All prompt types carry forward; the
    ORCHESTRATION slot is replaced by new_orch (which we override), and
    every other slot is stripped down to fields valid under DEFAULT mode.
    """
    poc = copy.deepcopy(agent.get("promptOverrideConfiguration") or {})
    configs = list(poc.get("promptConfigurations") or [])
    rewritten: list[dict[str, Any]] = []
    replaced = False
    for pc in configs:
        if pc.get("promptType") == "ORCHESTRATION":
            rewritten.append(new_orch)
            replaced = True
        elif pc.get("promptCreationMode") == "OVERRIDDEN":
            # Already overridden elsewhere — leave it alone.
            rewritten.append(pc)
        else:
            rewritten.append(_strip_for_default(pc))
    if not replaced:
        rewritten.append(new_orch)
    poc["promptConfigurations"] = rewritten

    payload: dict[str, Any] = {
        "agentId": agent["agentId"],
        "agentName": agent["agentName"],
        "agentResourceRoleArn": agent["agentResourceRoleArn"],
        "foundationModel": agent["foundationModel"],
        "instruction": agent["instruction"],
        "promptOverrideConfiguration": poc,
    }
    # Carry over optional fields only if present, to avoid accidentally
    # nulling them out.
    for key in (
        "description",
        "idleSessionTTLInSeconds",
        "customerEncryptionKeyArn",
        "guardrailConfiguration",
        "agentCollaboration",
        "memoryConfiguration",
        "orchestrationType",
        "customOrchestration",
    ):
        if agent.get(key) is not None:
            payload[key] = agent[key]
    return payload


def _wait_until_prepared(client, agent_id: str, timeout: int = 180) -> str:
    """Poll get_agent until agentStatus is PREPARED, return the latest version."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get_agent(agentId=agent_id)
        status = r["agent"]["agentStatus"]
        if status == "PREPARED":
            return r["agent"].get("agentVersion", "DRAFT")
        if status == "FAILED":
            raise RuntimeError(
                f"agent {agent_id} entered FAILED state during prepare"
            )
        time.sleep(3)
    raise TimeoutError(f"agent {agent_id} did not reach PREPARED within {timeout}s")


def _latest_numbered_version(client, agent_id: str) -> str:
    """Return the highest numeric version ID (skipping DRAFT)."""
    versions: list[str] = []
    paginator = client.get_paginator("list_agent_versions")
    for page in paginator.paginate(agentId=agent_id):
        for v in page.get("agentVersionSummaries", []):
            ver = v.get("agentVersion")
            if ver and ver != "DRAFT":
                versions.append(ver)
    if not versions:
        raise RuntimeError(f"agent {agent_id} has no numbered versions")
    return max(versions, key=lambda s: int(s) if s.isdigit() else -1)


def process_agent(client, agent_cfg: dict[str, str]) -> str:
    name = agent_cfg["name"]
    agent_id = agent_cfg["agent_id"]
    alias_id = agent_cfg["alias_id"]
    alias_name = agent_cfg["alias_name"]

    print(f"== {name} ({agent_id}) ==")
    agent = client.get_agent(agentId=agent_id)["agent"]
    orch, _idx = _find_orchestration(agent.get("promptOverrideConfiguration"))
    if orch is None:
        raise RuntimeError(f"{name}: no ORCHESTRATION prompt config in agent")

    cur_len = (orch.get("inferenceConfiguration") or {}).get("maximumLength")
    print(f"   current mode={orch.get('promptCreationMode')} maxLen={cur_len}")

    if _already_bumped(orch):
        print(f"   already OVERRIDDEN at >= {TARGET_MAX_LENGTH} — skipping")
        return "skipped"

    new_orch = _build_overridden(orch)
    payload = _build_update_payload(agent, new_orch)
    client.update_agent(**payload)
    print(f"   update_agent OK -> maxLen={TARGET_MAX_LENGTH}, mode=OVERRIDDEN")

    client.prepare_agent(agentId=agent_id)
    new_version = _wait_until_prepared(client, agent_id)
    # get_agent on a DRAFT after prepare leaves the version at DRAFT — we need
    # the latest numbered version bound to the alias.
    if new_version == "DRAFT":
        new_version = _latest_numbered_version(client, agent_id)
    print(f"   prepare_agent OK -> version {new_version}")

    client.update_agent_alias(
        agentId=agent_id,
        agentAliasId=alias_id,
        agentAliasName=alias_name,
        routingConfiguration=[{"agentVersion": new_version}],
    )
    print(f"   alias {alias_name!r} -> version {new_version}")
    return "bumped"


def main() -> int:
    client = boto3.client("bedrock-agent", region_name=REGION)
    results: dict[str, str] = {}
    for cfg in AGENTS:
        try:
            results[cfg["name"]] = process_agent(client, cfg)
        except ClientError as exc:
            results[cfg["name"]] = f"ERROR: {exc.response['Error']['Code']}: {exc.response['Error']['Message']}"
        except Exception as exc:  # pragma: no cover
            results[cfg["name"]] = f"ERROR: {type(exc).__name__}: {exc}"
    print("\n== summary ==")
    print(json.dumps(results, indent=2))
    return 0 if all(not v.startswith("ERROR") for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
