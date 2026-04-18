"""Aggregate web-vitals RUM beacons from structured API logs.

The /api/v1/rum endpoint writes one structured log line per beacon via
structlog's JSONRenderer in production. This script reads those lines
from stdin, filters to `event == "web_vital"`, groups by (path, metric),
and prints p50/p75/p95/count per group.

Usage:
    ssh intelpulse2 'docker compose logs --tail 200000 api' | \
      python scripts/rum_report.py

    # follow mode — prints an updated table every 30s while the pipe stays open
    ssh intelpulse2 'docker compose logs -f api' | \
      python scripts/rum_report.py --follow

Google's Web Vitals thresholds (used for the rating column if --rating is set):
    LCP   good ≤ 2500   poor > 4000
    INP   good ≤ 200    poor > 500
    CLS   good ≤ 0.1    poor > 0.25
    FCP   good ≤ 1800   poor > 3000
    TTFB  good ≤ 800    poor > 1800
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from statistics import median


# Google Core Web Vitals thresholds (ms for timings, unitless for CLS)
THRESHOLDS: dict[str, tuple[float, float]] = {
    "LCP": (2500, 4000),
    "INP": (200, 500),
    "CLS": (0.1, 0.25),
    "FCP": (1800, 3000),
    "TTFB": (800, 1800),
    "FID": (100, 300),
}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    frac = k - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def rate(metric: str, value: float) -> str:
    t = THRESHOLDS.get(metric)
    if not t:
        return "-"
    good, poor = t
    if value <= good:
        return "good"
    if value <= poor:
        return "needs"
    return "poor"


def render(groups: dict[tuple[str, str], list[float]]) -> str:
    lines: list[str] = []
    lines.append(
        f"{'path':<30} {'metric':<8} {'n':>6} {'p50':>9} {'p75':>9} {'p95':>9} {'rating(p75)':<11}"
    )
    lines.append("-" * 88)
    # Sort by (path, metric). Surface core vitals first for each path.
    core_order = {m: i for i, m in enumerate(["LCP", "INP", "CLS", "FCP", "TTFB", "FID"])}
    keys = sorted(
        groups.keys(),
        key=lambda k: (k[0], core_order.get(k[1], 99), k[1]),
    )
    for path, metric in keys:
        vals = groups[(path, metric)]
        n = len(vals)
        p50 = percentile(vals, 0.50)
        p75 = percentile(vals, 0.75)
        p95 = percentile(vals, 0.95)
        fmt = ".3f" if metric == "CLS" else ".0f"
        lines.append(
            f"{path[:30]:<30} {metric:<8} {n:>6} "
            f"{p50:>9{fmt}} {p75:>9{fmt}} {p95:>9{fmt}} "
            f"{rate(metric, p75):<11}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Re-render every 30s while stdin is open (for `docker compose logs -f`).",
    )
    args = parser.parse_args()

    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    next_render = time.time() + 30

    for raw in sys.stdin:
        line = raw.strip()
        # Structlog JSONRenderer writes pure JSON. But docker-compose may prefix
        # lines with "api-1  | ..." — strip that.
        if "|" in line and not line.startswith("{"):
            _, _, line = line.partition("|")
            line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if rec.get("event") != "web_vital":
            continue
        metric = rec.get("metric")
        value = rec.get("value")
        path = rec.get("path") or "/"
        if not isinstance(metric, str) or not isinstance(value, (int, float)):
            continue
        groups[(path, metric)].append(float(value))

        if args.follow and time.time() >= next_render:
            print("\x1b[2J\x1b[H", end="")  # clear screen, move cursor home
            print(render(groups))
            next_render = time.time() + 30

    print(render(groups))


if __name__ == "__main__":
    main()
