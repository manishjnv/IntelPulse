#!/usr/bin/env python3
"""Apply the tiered Bedrock model routing defaults to ai_settings.

The IntelPulse multi-agent pipeline uses four logical tiers:

    Classifier  → cheap + fast, handles high-volume categorisation
    Correlator  → structured JSON + tool calling for IOC enrichment
    Narrative   → quality-over-speed for briefings and report generation
    Fallback    → permissive model used when the primary refuses content

The ``ai_settings`` table already carries per-feature model overrides
(``model_news_enrichment``, ``model_briefing_gen``, …). This script maps
each feature to a tier and writes a known-good Bedrock model ID when the
column is currently empty (NULL or "").

Safe to re-run — only fills in blanks. Use ``--force`` to overwrite
values that are already set.

Results are grounded in the empirical probe:
``scripts/probe_bedrock_models.py`` on the prod BedrockAccessRole role
(account 604275788592, us-east-1). All chosen models have been verified
to return valid JSON and do not refuse threat-intel content.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
sys.path.insert(0, os.path.join(_root, "api"))
sys.path.insert(0, _root)

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.models import AISetting


# Feature → Bedrock model ID. Keys are the "<feature>" suffix of the
# corresponding model_<feature> column in ai_settings.
TIER_DEFAULTS: dict[str, tuple[str, str]] = {
    # Classifier tier — cheap + fast (Llama 4 Scout 17B, MoE)
    "intel_summary":      ("classifier", "us.meta.llama4-scout-17b-instruct-v1:0"),
    "news_enrichment":    ("classifier", "us.meta.llama4-scout-17b-instruct-v1:0"),
    "kql_generation":     ("classifier", "us.meta.llama4-scout-17b-instruct-v1:0"),
    # Correlator tier — strict JSON + Bedrock-Agent native (Nova Pro)
    "intel_enrichment":   ("correlator", "amazon.nova-pro-v1:0"),
    "live_lookup":        ("correlator", "amazon.nova-pro-v1:0"),
    # Narrative tier — quality writing for weekly briefings + reports
    "briefing_gen":       ("narrative",  "mistral.mistral-large-2402-v1:0"),
    "report_gen":         ("narrative",  "mistral.mistral-large-2402-v1:0"),
}


def _make_session() -> tuple:
    s = get_settings()
    engine = create_engine(s.database_url_sync, pool_pre_ping=True, pool_size=2)
    Session_ = sessionmaker(bind=engine)
    return engine, Session_


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Overwrite per-feature model values even when set.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the planned updates without writing.")
    args = parser.parse_args()

    engine, Session_ = _make_session()
    session: Session = Session_()
    try:
        row = session.execute(
            select(AISetting).where(AISetting.key == "default")
        ).scalar_one_or_none()
        if row is None:
            print("[error] no ai_settings row with key='default' — nothing to update")
            return 1

        planned: list[tuple[str, str, str, str]] = []
        for feature, (tier, model_id) in TIER_DEFAULTS.items():
            col = f"model_{feature}"
            current = getattr(row, col, "") or ""
            if current and not args.force:
                planned.append((feature, tier, current, f"SKIP (already set to '{current}')"))
                continue
            planned.append((feature, tier, current, f"SET -> {model_id}"))

        print(f"Tiered routing plan ({'dry-run' if args.dry_run else 'apply'}):")
        print(f"  {'FEATURE':<20} {'TIER':<10} {'CURRENT':<45} {'ACTION'}")
        for f, t, cur, act in planned:
            print(f"  {f:<20} {t:<10} {cur or '(empty)':<45} {act}")

        if args.dry_run:
            return 0

        applied = 0
        for feature, (tier, model_id) in TIER_DEFAULTS.items():
            col = f"model_{feature}"
            current = getattr(row, col, "") or ""
            if current and not args.force:
                continue
            setattr(row, col, model_id)
            applied += 1

        if applied:
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            print(f"\n[ok] applied {applied} tier defaults")
        else:
            print("\n[ok] nothing to apply (all columns already set — use --force to override)")

        return 0
    except Exception as e:  # noqa: BLE001
        session.rollback()
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
