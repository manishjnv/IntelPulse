"""Unit tests for service modules (pure-function layers)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest


class TestScoring:
    """app.services.scoring — compute_risk_score"""

    def test_basic_score(self):
        from app.services.scoring import compute_risk_score
        item = {
            "severity": "high",
            "is_kev": False,
            "source_reliability": 70,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "related_ioc_count": 5,
        }
        score = compute_risk_score(item)
        assert 0 <= score <= 100

    def test_kev_boosts_score(self):
        from app.services.scoring import compute_risk_score
        base = {
            "severity": "medium",
            "is_kev": False,
            "source_reliability": 50,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "related_ioc_count": 0,
        }
        kev = {**base, "is_kev": True}
        assert compute_risk_score(kev) > compute_risk_score(base)

    def test_critical_scores_higher(self):
        from app.services.scoring import compute_risk_score
        base = {
            "is_kev": False,
            "source_reliability": 50,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "related_ioc_count": 0,
        }
        critical = {**base, "severity": "critical"}
        low = {**base, "severity": "low"}
        assert compute_risk_score(critical) > compute_risk_score(low)

    def test_exploit_available_boost(self):
        from app.services.scoring import compute_risk_score
        base = {
            "severity": "medium",
            "is_kev": False,
            "source_reliability": 50,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "related_ioc_count": 0,
            "exploit_available": False,
        }
        with_exploit = {**base, "exploit_available": True}
        assert compute_risk_score(with_exploit) > compute_risk_score(base)

    def test_freshness_decay(self):
        from app.services.scoring import compute_risk_score
        base = {
            "severity": "medium",
            "is_kev": False,
            "source_reliability": 50,
            "related_ioc_count": 0,
        }
        fresh = {**base, "published_at": datetime.now(timezone.utc).isoformat()}
        old = {**base, "published_at": (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()}
        assert compute_risk_score(fresh) > compute_risk_score(old)

    def test_custom_weights(self):
        from app.services.scoring import compute_risk_score
        item = {
            "severity": "critical",
            "is_kev": True,
            "source_reliability": 100,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "related_ioc_count": 50,
        }
        # All weight on severity
        score_sev = compute_risk_score(item, {"kev_presence": 0, "severity": 100, "source_reliability": 0, "freshness": 0, "ioc_prevalence": 0})
        # All weight on KEV
        score_kev = compute_risk_score(item, {"kev_presence": 100, "severity": 0, "source_reliability": 0, "freshness": 0, "ioc_prevalence": 0})
        # Both should be valid scores
        assert 0 <= score_sev <= 100
        assert 0 <= score_kev <= 100

    def test_score_bounds(self):
        from app.services.scoring import compute_risk_score
        # Maximum possible inputs
        max_item = {
            "severity": "critical",
            "is_kev": True,
            "source_reliability": 100,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "related_ioc_count": 100,
            "exploit_available": True,
            "exploitability_score": 10.0,
        }
        assert compute_risk_score(max_item) <= 100

        # Minimum inputs
        min_item = {"severity": "unknown"}
        assert compute_risk_score(min_item) >= 0

    def test_zero_weights(self):
        from app.services.scoring import compute_risk_score
        item = {"severity": "critical", "is_kev": True}
        score = compute_risk_score(item, {"kev_presence": 0, "severity": 0, "source_reliability": 0, "freshness": 0, "ioc_prevalence": 0})
        assert score == 0

    def test_empty_item(self):
        from app.services.scoring import compute_risk_score
        score = compute_risk_score({})
        assert 0 <= score <= 100

    def test_batch_score(self):
        from app.services.scoring import batch_score
        items = [
            {"severity": "critical", "is_kev": True},
            {"severity": "low", "is_kev": False},
        ]
        scored = batch_score(items)
        assert len(scored) == 2
        assert scored[0]["risk_score"] > scored[1]["risk_score"]
