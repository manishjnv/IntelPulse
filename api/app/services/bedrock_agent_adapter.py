"""Amazon Bedrock Agents adapter — multi-agent enrichment path.

Routes structured-JSON enrichment requests through a Bedrock Supervisor agent
(``agentCollaboration=SUPERVISOR_ROUTER``) that delegates to specialist
sub-agents (IOC Reputation Analyst, Risk Scorer) and can invoke the
``virustotal_lookup`` action group Lambda.

This adapter is gated behind ``settings.ai_use_agents``. When disabled the
runtime falls back to the single-shot ``BedrockAdapter.ai_analyze_structured``
path in ``bedrock_adapter.py``.

Contract (mirrors ``BedrockAdapter.ai_analyze_structured``):
    async def ai_analyze_structured_via_agent(
        system_prompt: str,
        user_prompt: str,
        *,
        required_keys: list[str] | None = None,
        session_id: str | None = None,
        caller: str = "agent_json",
    ) -> dict | None
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover
    BOTO3_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging import get_logger
from app.normalizers.text import strip_json_fences

logger = get_logger(__name__)
settings = get_settings()

# Transient errors worth retrying once
_TRANSIENT_ERROR_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelTimeoutException",
    "DependencyFailedException",
}


class BedrockAgentAdapter:
    """Adapter for Amazon Bedrock Agent Runtime (``invoke_agent``).

    Streams the agent's completion synchronously, concatenates text chunks,
    and returns parsed structured JSON. Tool-use (action groups) happens
    transparently inside the Bedrock service — the client sees only the
    final completion plus an optional trace.
    """

    def __init__(self) -> None:
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for Bedrock agent adapter. "
                "Install with: pip install boto3"
            )

        self.region = settings.aws_region or "us-east-1"
        self.agent_id = settings.bedrock_supervisor_agent_id
        self.alias_id = settings.bedrock_supervisor_alias_id
        self.timeout = settings.bedrock_agent_timeout or 120

        if not self.agent_id or not self.alias_id:
            raise ValueError(
                "bedrock_supervisor_agent_id and bedrock_supervisor_alias_id "
                "must both be set when ai_use_agents=True"
            )

        self.client = boto3.client(
            service_name="bedrock-agent-runtime",
            region_name=self.region,
        )

        logger.info(
            "bedrock_agent_adapter_initialized",
            region=self.region,
            agent_id=self.agent_id,
            alias_id=self.alias_id,
        )

    # ─────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────
    async def ai_analyze_structured_via_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        required_keys: list[str] | None = None,
        session_id: str | None = None,
        caller: str = "agent_json",
    ) -> dict | None:
        """Invoke the supervisor agent and return parsed structured JSON.

        The agent's instruction already describes its role; ``system_prompt``
        is combined with ``user_prompt`` into a single ``inputText`` so callers
        that previously used the single-shot adapter keep the same signature.

        Returns the parsed dict on success, ``None`` on parse failure or
        missing required keys (same semantics as the single-shot path).
        Raises on non-recoverable Bedrock errors — per RCA
        ``rca_rq_tasks_must_raise``, worker tasks must surface failures rather
        than silently swallow them.
        """
        input_text = self._build_input_text(system_prompt, user_prompt)
        sid = session_id or f"news-enrich-{uuid.uuid4()}"

        logger.info(
            "bedrock_invoke_agent_request",
            agent_id=self.agent_id,
            alias_id=self.alias_id,
            session_id=sid,
            caller=caller,
            input_len=len(input_text),
        )

        raw_text, stats = await asyncio.to_thread(
            self._invoke_and_collect, input_text, sid
        )

        logger.info(
            "bedrock_invoke_agent_response",
            agent_id=self.agent_id,
            session_id=sid,
            caller=caller,
            chunks=stats["chunks"],
            action_group_invocations=stats["action_group_invocations"],
            collaborator_invocations=stats["collaborator_invocations"],
            raw_len=len(raw_text),
        )

        if not raw_text:
            return None

        data = self._parse_json(raw_text, caller=caller)
        if data is None:
            return None

        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                logger.warning(
                    "bedrock_agent_missing_required_keys",
                    caller=caller,
                    missing=missing,
                    keys_got=list(data.keys())[:20],
                )
                return None

        return data

    # ─────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_input_text(system_prompt: str, user_prompt: str) -> str:
        """Combine system + user prompts into a single agent input.

        The agent's own ``instruction`` already sets the role; we append the
        specialist system prompt + the request so the agent produces output
        matching the caller's schema contract.
        """
        return (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt.strip()}\n\n"
            f"REQUEST:\n{user_prompt.strip()}"
        )

    def _invoke_and_collect(
        self, input_text: str, session_id: str
    ) -> tuple[str, dict[str, int]]:
        """Call ``invoke_agent`` and drain the EventStream synchronously.

        Returns ``(concatenated_text, stats)``. Runs in a worker thread so
        the caller's event loop stays free.
        """
        stats = {"chunks": 0, "action_group_invocations": 0, "collaborator_invocations": 0}

        last_err: Exception | None = None
        for attempt in (1, 2):
            try:
                resp = self.client.invoke_agent(
                    agentId=self.agent_id,
                    agentAliasId=self.alias_id,
                    sessionId=session_id,
                    inputText=input_text,
                    enableTrace=True,
                )
                break
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                last_err = e
                if code in _TRANSIENT_ERROR_CODES and attempt == 1:
                    logger.warning(
                        "bedrock_invoke_agent_retry",
                        attempt=attempt, error_code=code, error=str(e)[:200],
                    )
                    continue
                logger.error(
                    "bedrock_invoke_agent_error",
                    error_code=code, error=str(e)[:500],
                )
                raise
            except BotoCoreError as e:
                last_err = e
                logger.error("bedrock_invoke_agent_botocore_error", error=str(e)[:500])
                raise
        else:
            # Exhausted retries without break
            raise last_err  # type: ignore[misc]

        return self._drain_stream(resp["completion"], stats)

    @staticmethod
    def _drain_stream(
        completion_iter: Any, stats: dict[str, int]
    ) -> tuple[str, dict[str, int]]:
        """Consume the InvokeAgent EventStream and return concatenated text.

        Accumulates ``chunk.bytes`` segments; counts action-group + collaborator
        trace events for observability. Surfaces ``returnControl`` events as
        an explicit error — we haven't wired up client-side tool dispatch yet
        (all tools run via Lambda today).
        """
        parts: list[str] = []
        for event in completion_iter:
            if "chunk" in event:
                b = event["chunk"].get("bytes")
                if b:
                    parts.append(b.decode("utf-8", errors="replace"))
                    stats["chunks"] += 1
                continue

            if "trace" in event:
                trace = event["trace"].get("trace", {})
                ot = trace.get("orchestrationTrace", {})
                ii = ot.get("invocationInput", {})
                if "actionGroupInvocationInput" in ii:
                    stats["action_group_invocations"] += 1
                if "agentCollaboratorInvocationInput" in ii:
                    stats["collaborator_invocations"] += 1
                continue

            if "returnControl" in event:
                # Action groups are configured with lambda executors today;
                # ReturnControl would mean we mis-provisioned. Fail loud.
                raise RuntimeError(
                    "Bedrock agent emitted returnControl event but client-side "
                    "dispatch is not implemented. Check action group executor "
                    "configuration — should be {'lambda': <arn>}."
                )

            _ERROR_KEYS = (
                "internalServerException", "validationException", "throttlingException",
                "accessDeniedException", "resourceNotFoundException",
                "serviceQuotaExceededException", "dependencyFailedException",
                "badGatewayException", "modelNotReadyException",
            )
            matched_err = next((k for k in _ERROR_KEYS if k in event), None)
            if matched_err:
                err_body = event.get(matched_err) or {}
                msg = err_body.get("message", "") if isinstance(err_body, dict) else str(err_body)
                raise RuntimeError(f"Bedrock agent stream error [{matched_err}]: {msg}")

        return "".join(parts), stats

    @staticmethod
    def _parse_json(raw_text: str, *, caller: str) -> dict | None:
        """Strip markdown fences and parse JSON. Returns None on parse error."""
        cleaned = strip_json_fences(raw_text)
        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"{caller}_json_parse_error",
                error=str(e)[:200],
                raw=raw_text[:400],
            )
            return None

        if not isinstance(data, dict):
            logger.warning(
                f"{caller}_json_not_a_dict",
                type=type(data).__name__,
                raw=raw_text[:200],
            )
            return None

        return data


# ──────────────────────────────────────────────────────────────────────
# Module-level singleton accessor
# ──────────────────────────────────────────────────────────────────────
_adapter: BedrockAgentAdapter | None = None


def get_bedrock_agent_adapter() -> BedrockAgentAdapter:
    """Return the lazily-initialised module-level adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = BedrockAgentAdapter()
    return _adapter
