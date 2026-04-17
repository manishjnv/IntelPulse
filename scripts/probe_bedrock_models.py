#!/usr/bin/env python3
"""Probe AWS Bedrock model availability + suitability for IntelPulse."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import boto3

REGION = "us-east-1"

CANDIDATES: list[tuple[str, str]] = [
    ("Nova Lite (current)",        "amazon.nova-lite-v1:0"),
    ("Nova Pro",                   "amazon.nova-pro-v1:0"),
    ("Nova Premier",               "amazon.nova-premier-v1:0"),
    ("Nova 2 Lite",                "amazon.nova-2-lite-v1:0"),
    ("Nova Micro",                 "amazon.nova-micro-v1:0"),
    ("Llama 3.3 70B Instruct",     "us.meta.llama3-3-70b-instruct-v1:0"),
    ("Llama 3.1 70B Instruct",     "us.meta.llama3-1-70b-instruct-v1:0"),
    ("Llama 3.2 90B Instruct",     "us.meta.llama3-2-90b-instruct-v1:0"),
    ("Llama 4 Maverick 17B",       "us.meta.llama4-maverick-17b-instruct-v1:0"),
    ("Llama 4 Scout 17B",          "us.meta.llama4-scout-17b-instruct-v1:0"),
    ("Mistral Small (2402)",       "mistral.mistral-small-2402-v1:0"),
    ("Mistral Large (2402)",       "mistral.mistral-large-2402-v1:0"),
    ("Mistral Large 3 675B",       "us.mistral.mistral-large-3-675b-instruct"),
    ("Mistral Ministral 3 8B",     "us.mistral.ministral-3-8b-instruct"),
    ("Magistral Small 2509",       "us.mistral.magistral-small-2509"),
    ("DeepSeek-R1",                "us.deepseek.r1-v1:0"),
    ("DeepSeek V3.2",              "us.deepseek.v3.2"),
    ("AI21 Jamba 1.5 Large",       "ai21.jamba-1-5-large-v1:0"),
    ("AI21 Jamba 1.5 Mini",        "ai21.jamba-1-5-mini-v1:0"),
    ("Cohere Command R+",          "cohere.command-r-plus-v1:0"),
]

TEST_USER_PROMPT = """Extract threat intelligence from this article. Reply with ONLY a JSON object.

ARTICLE:
"Akira ransomware affiliates exploited CVE-2024-1709 in ConnectWise
ScreenConnect to deploy Cobalt Strike beacons. The campaign used
176.65.150.25 as C2 and xel7morax.in.net as a loader domain. Victim
organisations in manufacturing and healthcare were observed."

Respond with this exact JSON shape:
{"cves": [...], "ioc_ips": [...], "ioc_domains": [...], "actors": [...], "sectors": [...], "severity": "critical|high|medium|low"}
"""

SYSTEM_PROMPT = (
    "You are a threat-intelligence extraction assistant. "
    "Respond with valid JSON only — no prose, no markdown fences."
)


@dataclass
class Probe:
    name: str
    model_id: str
    access: bool = False
    latency_ms: int | None = None
    output_tokens: int | None = None
    json_ok: bool = False
    refused: bool = False
    err: str = ""
    extracted: dict = field(default_factory=dict)


def converse_probe(model_id: str) -> Probe:
    p = Probe(name="", model_id=model_id)
    rt = boto3.client("bedrock-runtime", region_name=REGION)
    t0 = time.monotonic()
    try:
        resp = rt.converse(
            modelId=model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": TEST_USER_PROMPT}]}],
            inferenceConfig={"maxTokens": 400, "temperature": 0.2},
        )
        p.latency_ms = int((time.monotonic() - t0) * 1000)
        p.access = True

        usage = resp.get("usage", {}) or {}
        p.output_tokens = usage.get("outputTokens")

        msg = resp.get("output", {}).get("message", {})
        parts = msg.get("content", []) or []
        text = "".join(part.get("text", "") for part in parts if "text" in part).strip()

        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]
            text = text.rstrip("`").strip()

        # DeepSeek R1 likes to wrap thinking in <think>...</think> — strip it
        if "<think>" in text:
            after = text.split("</think>", 1)
            text = (after[1] if len(after) > 1 else after[0]).strip()

        try:
            data = json.loads(text)
            p.json_ok = True
            p.extracted = {
                "cves": data.get("cves", []),
                "ips": data.get("ioc_ips", []),
                "domains": data.get("ioc_domains", []),
                "actors": data.get("actors", []),
                "sectors": data.get("sectors", []),
                "severity": data.get("severity", ""),
            }
        except json.JSONDecodeError:
            p.extracted = {"non_json_preview": text[:160].replace("\n", " ")}

        low = text.lower()
        if any(tok in low for tok in (
            "cannot help", "can't help", "cannot provide", "can't provide",
            "i'm unable", "not able to provide", "cannot assist",
        )):
            p.refused = True

    except Exception as e:  # noqa: BLE001
        p.err = f"{type(e).__name__}: {e}"[:220]
    return p


def main() -> int:
    print(f"[bedrock-probe] region={REGION}\n")
    results: list[Probe] = []
    for name, mid in CANDIDATES:
        p = converse_probe(mid)
        p.name = name
        results.append(p)
        status = "OK " if p.access else "DENY"
        if p.access:
            extra = f"{p.latency_ms}ms / {p.output_tokens}t / json={'Y' if p.json_ok else 'N'} / refused={'Y' if p.refused else 'N'}"
        else:
            extra = p.err[:120]
        print(f"  {status}  {name:28s}  {mid:50s}  {extra}")

    print("\n=== MATRIX ===")
    print(f"{'Model':<28} {'Access':<7} {'Lat(ms)':<9} {'Out(t)':<7} {'JSON':<5} {'Refused':<8} {'Err/Note'}")
    for p in results:
        err = p.err[:60] if p.err else ("refusal" if p.refused else "")
        print(
            f"{p.name:<28} "
            f"{'Y' if p.access else 'N':<7} "
            f"{str(p.latency_ms or ''):<9} "
            f"{str(p.output_tokens or ''):<7} "
            f"{'Y' if p.json_ok else 'N':<5} "
            f"{'Y' if p.refused else 'N':<8} "
            f"{err}"
        )

    print("\n=== EXTRACTION PREVIEW ===")
    for p in results:
        if p.json_ok:
            e = p.extracted
            print(
                f"{p.name:<28} cves={e.get('cves')} "
                f"ips={e.get('ips')} domains={e.get('domains')} "
                f"severity={e.get('severity')}"
            )
        elif p.access:
            print(f"{p.name:<28} (non-JSON) {p.extracted.get('non_json_preview','')[:100]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
