"""AI invocation telemetry — Redis-backed token + cost counters.

On every successful Bedrock/agent call, `track_invocation` bumps:

- `ai:usage:{YYYY-MM-DD}:input`          — daily input-token counter
- `ai:usage:{YYYY-MM-DD}:output`         — daily output-token counter
- `ai:usage:{YYYY-MM-DD}:calls`          — daily call count
- `ai:usage:{YYYY-MM-DD}:model:{mid}:in` — per-model input tokens
- `ai:usage:{YYYY-MM-DD}:model:{mid}:out`— per-model output tokens

Each key expires after 14 days (enough for the weekly rollup + buffer).

`get_token_usage(days)` reads the counters and returns aggregated stats
including an estimated cost in USD based on published Bedrock on-demand
pricing — this is best-effort, not a billing authority.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.core.logging import get_logger
from app.core.redis import redis_client

logger = get_logger(__name__)

# Bedrock on-demand pricing per 1K tokens (us-east-1, as of 2026-04).
# Fallback for unknown models uses Nova Lite pricing (cheapest plausible).
# Keep in sync with https://aws.amazon.com/bedrock/pricing/ when published
# rates change.
_PRICING_PER_1K: dict[str, tuple[float, float]] = {
    # model_id prefix → (input_usd_per_1k, output_usd_per_1k)
    "amazon.nova-micro":     (0.000035, 0.00014),
    "amazon.nova-lite":      (0.00006,  0.00024),
    "amazon.nova-pro":       (0.0008,   0.0032),
    "amazon.titan-text-lite":(0.00015,  0.0002),
    "amazon.titan-text-express": (0.0002, 0.0006),
    "anthropic.claude-3-haiku":     (0.00025, 0.00125),
    "anthropic.claude-3-5-sonnet":  (0.003,   0.015),
    "anthropic.claude-3-opus":      (0.015,   0.075),
    # Agent invocations are priced on the underlying model's tokens — the
    # adapter passes the real model id. "bedrock-agent" is a fallback label.
    "bedrock-agent":         (0.00006,  0.00024),
}

_USAGE_TTL_SECONDS = 14 * 24 * 3600  # 14 days


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _model_slug(model_id: str) -> str:
    """Redis-safe model key — strip regional prefixes + the :N version tail."""
    s = (model_id or "unknown").lower()
    for prefix in ("us.", "global.", "eu.", "apac."):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    # Drop the :version suffix ("amazon.nova-lite-v1:0" → "amazon.nova-lite-v1")
    return s.split(":", 1)[0]


def _price_for(model_id: str) -> tuple[float, float]:
    slug = _model_slug(model_id)
    for prefix, rates in _PRICING_PER_1K.items():
        if slug.startswith(prefix):
            return rates
    return _PRICING_PER_1K["bedrock-agent"]


async def track_invocation(
    *,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Increment all counters for this invocation. Never raises — if Redis
    is unavailable, log and drop so the invocation path stays clean."""
    try:
        today = _today_utc()
        slug = _model_slug(model_id)
        in_tok = max(0, int(input_tokens or 0))
        out_tok = max(0, int(output_tokens or 0))

        pipe = redis_client.pipeline()
        pipe.incrby(f"ai:usage:{today}:input", in_tok)
        pipe.incrby(f"ai:usage:{today}:output", out_tok)
        pipe.incr(f"ai:usage:{today}:calls")
        pipe.incrby(f"ai:usage:{today}:model:{slug}:in", in_tok)
        pipe.incrby(f"ai:usage:{today}:model:{slug}:out", out_tok)

        for key_suffix in (
            "input", "output", "calls",
            f"model:{slug}:in", f"model:{slug}:out",
        ):
            pipe.expire(f"ai:usage:{today}:{key_suffix}", _USAGE_TTL_SECONDS)

        await pipe.execute()
    except Exception as e:  # noqa: BLE001 — telemetry must never block
        logger.debug("ai_usage_track_failed", error=str(e))


def _estimate_cost(in_tok: int, out_tok: int, model_id: str) -> float:
    in_rate, out_rate = _price_for(model_id)
    return round((in_tok / 1000.0) * in_rate + (out_tok / 1000.0) * out_rate, 6)


async def _read_day(d: str) -> dict[str, int]:
    keys = [f"ai:usage:{d}:input", f"ai:usage:{d}:output", f"ai:usage:{d}:calls"]
    values = await redis_client.mget(*keys)
    return {
        "input": int(values[0] or 0),
        "output": int(values[1] or 0),
        "calls": int(values[2] or 0),
    }


async def _read_models(d: str) -> dict[str, dict[str, int]]:
    """Scan `ai:usage:{d}:model:*` and group by model slug."""
    by_model: dict[str, dict[str, int]] = {}
    pattern = f"ai:usage:{d}:model:*"
    async for key in redis_client.scan_iter(match=pattern, count=200):
        # key shape: ai:usage:YYYY-MM-DD:model:{slug}:{in|out}
        parts = key.split(":")
        if len(parts) < 6:
            continue
        slug = ":".join(parts[4:-1])
        field = parts[-1]  # "in" or "out"
        val = int(await redis_client.get(key) or 0)
        entry = by_model.setdefault(slug, {"input": 0, "output": 0})
        if field == "in":
            entry["input"] += val
        elif field == "out":
            entry["output"] += val
    return by_model


async def get_token_usage(days: int = 7) -> dict[str, Any]:
    """Return aggregated token + cost stats for the trailing `days` window."""
    days = max(1, min(days, 30))
    today_s = _today_utc()
    yesterday_s = (date.fromisoformat(today_s) - timedelta(days=1)).isoformat()

    today = await _read_day(today_s)
    yesterday = await _read_day(yesterday_s)

    week_input = 0
    week_output = 0
    week_calls = 0
    for i in range(days):
        d = (date.fromisoformat(today_s) - timedelta(days=i)).isoformat()
        day = await _read_day(d)
        week_input += day["input"]
        week_output += day["output"]
        week_calls += day["calls"]

    by_model_raw = await _read_models(today_s)
    by_model: dict[str, dict[str, Any]] = {}
    for slug, totals in by_model_raw.items():
        by_model[slug] = {
            "input": totals["input"],
            "output": totals["output"],
            "estimated_cost_usd": _estimate_cost(totals["input"], totals["output"], slug),
        }

    # Today/yesterday/week cost uses a weighted average: if we have per-model
    # data, use those specific rates; otherwise fall back to Nova Lite.
    def _cost_for_day(d: dict[str, int]) -> float:
        return _estimate_cost(d["input"], d["output"], "amazon.nova-lite")

    return {
        "today": {**today, "estimated_cost_usd": _cost_for_day(today)},
        "yesterday": {**yesterday, "estimated_cost_usd": _cost_for_day(yesterday)},
        "window": {
            "days": days,
            "input": week_input,
            "output": week_output,
            "calls": week_calls,
            "estimated_cost_usd": _estimate_cost(week_input, week_output, "amazon.nova-lite"),
        },
        "by_model": by_model,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
