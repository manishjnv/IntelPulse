#!/usr/bin/env python3
"""Legacy curl-based report seeder — kept for backward compatibility.

Prefer `scripts/seed_sample_data.py`, which writes directly to the DB and
seeds cases as well as reports with richer content.

This script POSTs the 25 `(report_type × severity)` sample reports via the
REST API using a pre-existing session cookie at /tmp/cookies.txt. It is
useful when the operator wants to exercise the full create path end-to-end
(AI hooks, audit log, etc.) rather than inserting rows directly.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sample_data.reports_data import (  # noqa: E402
    REPORT_TYPES,
    SAMPLE_REPORTS,
    SEVERITIES,
    TLP_FOR_SEVERITY,
)


BASE = os.environ.get("IP_API_BASE", "http://localhost:8000/api/v1")
COOKIE = os.environ.get("IP_COOKIE_FILE", "/tmp/cookies.txt")


def curl_post(path: str, data: dict) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmp = f.name
    try:
        cmd = (
            f"curl -s -b {COOKIE} -X POST {BASE}{path} "
            f"-H 'Content-Type: application/json' -d @{tmp}"
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        try:
            return json.loads(result.stdout)
        except Exception:
            return {"error": result.stdout}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def main() -> int:
    created = 0
    failed = 0

    for rtype in REPORT_TYPES:
        for severity in SEVERITIES:
            sample = SAMPLE_REPORTS.get(rtype, {}).get(severity)
            if not sample:
                continue
            payload = {
                "title": sample["title"],
                "summary": sample["summary"],
                "report_type": rtype,
                "severity": severity,
                "tlp": TLP_FOR_SEVERITY[severity],
                "tags": sample["tags"],
                "content": {"sections": sample["sections"]},
            }
            result = curl_post("/reports", payload)
            rid = result.get("id")
            if rid:
                created += 1
                print(f"  [OK] {rtype}/{severity}: {sample['title'][:60]}... (id={rid[:8]})")
            else:
                failed += 1
                print(f"  [FAIL] {rtype}/{severity}: {str(result)[:120]}")

    total = len(REPORT_TYPES) * len(SEVERITIES)
    print(f"\n{'=' * 60}")
    print(f"Created: {created}/{total} | Failed: {failed}")
    print(f"{'=' * 60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
