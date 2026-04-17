"""Targeted tests for the bug-fix pass.

These tests cover the pure-function parts of the fix set so they can run
without a DB, Redis, or the full FastAPI stack:

  - _is_public_ip (IoC extraction)
  - _is_probable_malicious_domain (IoC extraction)
  - _merge_tactic_labels (ATT&CK sync)
  - _format_modified_filter (GitHub advisory cursor)
  - scheduler.EXPECTED_JOB_COUNT_KEY publishes live count

Integration tests for the re-raise pattern, the news cleanup race, and the
ingest_feed failure path are covered indirectly by the production suite —
these unit tests lock in the correctness of the primitives they rely on.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone

import pytest

# These tests don't touch the Redis client — opt out of the autouse mock
# fixture so we don't require the `redis` package in the test runner env.
pytestmark = pytest.mark.no_redis_stub


# ── _is_public_ip ───────────────────────────────────────────

def _load_ioc_helpers():
    """Import the worker-module helpers without pulling in RQ/DB/httpx.

    We read the source, snip the helpers, and exec them in an isolated
    namespace. Keeps the test independent of the heavy worker imports.
    """
    worker_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "worker", "tasks.py"
    )
    with open(worker_path, encoding="utf-8") as f:
        src = f.read()

    # Extract the three helper defs + their backing set by slicing on markers
    def _extract(name: str, src_text: str) -> str:
        # Crude but stable: take from `def NAME` to the next top-level `def `
        # or top-level statement that starts at column 0 and isn't a def/var.
        m = re.search(rf"^def {name}\(", src_text, re.MULTILINE)
        if not m:
            raise RuntimeError(f"helper {name} not found")
        start = m.start()
        # Find the next top-level `def ` after start
        rest = src_text[start + 1:]
        m2 = re.search(r"^(def |_BENIGN_DOMAIN_SUFFIXES|async def )", rest, re.MULTILINE)
        end = start + 1 + m2.start() if m2 else len(src_text)
        return src_text[start:end]

    # Pull the benign suffix set literally
    m = re.search(
        r"^_BENIGN_DOMAIN_SUFFIXES = frozenset\(\{[^}]*\}\)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        raise RuntimeError("benign suffix set missing")
    benign_block = m.group(0)

    code = (
        _extract("_is_public_ip", src)
        + "\n\n"
        + benign_block
        + "\n\n"
        + _extract("_is_probable_malicious_domain", src)
        + "\n\n"
        + _extract("_merge_tactic_labels", src)
        + "\n"
    )
    ns: dict = {}
    exec(code, ns)
    return ns


helpers = _load_ioc_helpers()


@pytest.mark.parametrize(
    "ip, expected",
    [
        # Public
        ("8.8.8.8", True),
        ("1.1.1.1", True),
        ("142.250.72.14", True),
        # Private RFC1918
        ("10.0.0.1", False),
        ("10.255.255.255", False),
        ("172.16.0.1", False),
        ("172.31.255.254", False),
        ("192.168.1.1", False),
        # Not RFC1918
        ("172.15.0.1", True),
        ("172.32.0.1", True),
        # Loopback / link-local / reserved / multicast
        ("127.0.0.1", False),
        ("169.254.1.2", False),
        ("0.0.0.0", False),
        ("224.0.0.1", False),
        ("239.255.255.255", False),
        ("255.255.255.255", False),
        # CGNAT
        ("100.64.0.1", False),
        ("100.127.255.254", False),
        ("100.63.255.254", True),  # just outside CGNAT
        ("100.128.0.1", True),     # just outside CGNAT
        # Documentation ranges
        ("192.0.2.1", False),
        ("198.51.100.1", False),
        ("203.0.113.1", False),
        # Benchmark
        ("198.18.0.1", False),
        ("198.19.255.254", False),
        # Malformed
        ("not.an.ip.address", False),
        ("256.0.0.1", False),
        ("1.2.3", False),
    ],
)
def test_is_public_ip(ip, expected):
    assert helpers["_is_public_ip"](ip) is expected


# ── _is_probable_malicious_domain ────────────────────────────

@pytest.mark.parametrize(
    "domain, expected",
    [
        # Benign — exact match
        ("nist.gov", False),
        ("github.com", False),
        ("virustotal.com", False),
        ("mitre.org", False),
        # Benign — subdomain of allowlisted suffix
        ("docs.github.com", False),
        ("raw.githubusercontent.com", False),
        ("blog.microsoft.com", False),
        ("nvd.nist.gov", False),
        # Numeric TLD (IP that slipped through)
        ("1.2.3.4", False),
        # Obviously malicious-looking unknown domains
        ("evil-c2.xyz", True),
        ("badactor.tk", True),
        ("malware.example.ru", True),
        # Edge — no dot
        ("localhost", False),
        ("", False),
    ],
)
def test_is_probable_malicious_domain(domain, expected):
    assert helpers["_is_probable_malicious_domain"](domain) is expected


# ── _merge_tactic_labels ─────────────────────────────────────

def test_merge_tactic_labels_new_only():
    assert helpers["_merge_tactic_labels"](None, "Execution") == "Execution"


def test_merge_tactic_labels_existing_only():
    assert helpers["_merge_tactic_labels"]("Initial Access", "") == "Initial Access"


def test_merge_tactic_labels_dedupe():
    assert (
        helpers["_merge_tactic_labels"]("Initial Access", "Initial Access")
        == "Initial Access"
    )


def test_merge_tactic_labels_combine():
    got = helpers["_merge_tactic_labels"]("Initial Access", "Execution")
    assert got == "Initial Access / Execution"


def test_merge_tactic_labels_preserve_existing_order():
    got = helpers["_merge_tactic_labels"](
        "Initial Access / Persistence", "Execution"
    )
    assert got == "Initial Access / Persistence / Execution"


def test_merge_tactic_labels_truncates_to_100():
    long_existing = " / ".join(f"Tactic{i}" for i in range(20))
    got = helpers["_merge_tactic_labels"](long_existing, "Execution")
    assert len(got) <= 100


def test_merge_tactic_labels_both_empty():
    assert helpers["_merge_tactic_labels"](None, None) == ""
    assert helpers["_merge_tactic_labels"]("", "") == ""


# ── GitHub advisory cursor (_format_modified_filter) ─────────

def _load_ghsa_helper():
    """Extract the static cursor-formatter from cisa_advisories.py."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..", "app", "services", "feeds", "cisa_advisories.py",
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    m = re.search(
        r"@staticmethod\s+def _format_modified_filter\(cursor: str\) -> str \| None:"
        r".*?(?=\n    def |\nclass |\Z)",
        src,
        re.DOTALL,
    )
    assert m, "_format_modified_filter not found"
    body = m.group(0)
    # Re-shape as a free-standing function (drop @staticmethod)
    body = body.replace("@staticmethod\n    def _format_modified_filter(",
                        "def _format_modified_filter(")
    # Dedent 4 spaces
    body = "\n".join(
        line[4:] if line.startswith("    ") else line for line in body.splitlines()
    )
    ns: dict = {"datetime": datetime, "timezone": timezone}
    exec(body, ns)
    return ns["_format_modified_filter"]


format_modified = _load_ghsa_helper()


def test_ghsa_cursor_iso_with_tz():
    got = format_modified("2026-04-17T15:30:00+00:00")
    assert got == ">2026-04-17T15:30:00Z"


def test_ghsa_cursor_iso_with_z():
    got = format_modified("2026-04-17T15:30:00Z")
    assert got == ">2026-04-17T15:30:00Z"


def test_ghsa_cursor_iso_naive_treated_as_utc():
    got = format_modified("2026-04-17T15:30:00")
    assert got == ">2026-04-17T15:30:00Z"


def test_ghsa_cursor_non_utc_converted():
    # +05:30 offset → UTC
    got = format_modified("2026-04-17T21:00:00+05:30")
    assert got == ">2026-04-17T15:30:00Z"


def test_ghsa_cursor_malformed_returns_none():
    assert format_modified("not-a-date") is None
    assert format_modified("") is None


# ── scheduler live-count constant ────────────────────────────

def test_scheduler_schedule_calls_match_published_count():
    """The scheduler used to have a hard-coded EXPECTED_JOB_COUNT. If the
    magic number drifted from the real schedule count, the watchdog
    wouldn't catch a single missing job. The fix switched to a live count
    written to Redis. This test simply locks in that the number of
    .schedule( calls is positive and the hard-coded constant is gone.
    """
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "worker", "scheduler.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    n_schedules = len(re.findall(r"scheduler\.schedule\(", src))
    assert n_schedules >= 20, f"expected many schedules, got {n_schedules}"
    # The old magic-number constant must be gone
    assert "EXPECTED_JOB_COUNT = " not in src
    # The live-count key must be referenced
    assert "EXPECTED_JOB_COUNT_KEY" in src


def test_healthcheck_reads_live_count():
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "worker", "healthcheck.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # The old hard-coded expected count must be gone
    assert "EXPECTED_JOBS = 14" not in src
    assert "EXPECTED_JOBS = 29" not in src
    # Must now read the shared Redis key
    assert "scheduler:expected_job_count" in src


# ── re-raise regression: no task swallows via return {"error": ──

def test_no_task_returns_error_in_except_block():
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "worker", "tasks.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # Scan each except block: if it contains `return {"error"`, that's the
    # old pattern where failures silently become dict returns. Allow the
    # intentional non-exception early returns (e.g. "Unknown feed" guard)
    # which live OUTSIDE any except block.
    except_blocks = re.findall(r"except Exception[^\n]*:[\s\S]*?(?=\n\S|\Z)", src)
    bad = [b for b in except_blocks if 'return {"error"' in b]
    assert not bad, f"{len(bad)} except block(s) still swallow via return dict"
