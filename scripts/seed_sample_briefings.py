#!/usr/bin/env python3
"""Seed the IntelPulse DB with three enriched sample threat briefings.

Each briefing pulls together news-feed + IOC-database correlations so the
/briefings page has a realistic demo surface — ransomware & infostealer
infrastructure, nation-state critical-infrastructure targeting, and a
daily zero-day watch.

Usage:
    python -m scripts.seed_sample_briefings              # insert missing
    python -m scripts.seed_sample_briefings --force      # delete + reinsert
    python -m scripts.seed_sample_briefings --dry-run    # show only

All briefing titles are uniformly prefixed with "[SAMPLE] " so the seed
can re-discover its own rows for idempotent updates without touching
real user content.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

# Make `app.*` imports resolvable when run from ti-platform/scripts or ti-platform.
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
sys.path.insert(0, os.path.join(_root, "api"))
sys.path.insert(0, _root)

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.models import ThreatBriefing

from scripts.sample_data import SAMPLE_BRIEFINGS


SAMPLE_PREFIX = "[SAMPLE] "


def _make_session_factory() -> tuple:
    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=2)
    Session_ = sessionmaker(bind=engine)
    return engine, Session_


def _expected_titles() -> set[str]:
    return {SAMPLE_PREFIX + b["title"] for b in SAMPLE_BRIEFINGS}


def _purge_samples(session: Session) -> int:
    titles = _expected_titles()
    if not titles:
        return 0
    rows = session.execute(
        select(ThreatBriefing.id).where(ThreatBriefing.title.in_(list(titles)))
    ).scalars().all()
    if not rows:
        # Also clean any stale rows carrying our prefix in case a title was renamed.
        r = session.execute(
            delete(ThreatBriefing).where(ThreatBriefing.title.like(SAMPLE_PREFIX + "%"))
        )
        return r.rowcount or 0
    r = session.execute(
        delete(ThreatBriefing).where(ThreatBriefing.id.in_(rows))
    )
    return r.rowcount or len(rows)


def _title_exists(session: Session, title: str) -> bool:
    return bool(
        session.execute(
            select(ThreatBriefing.id).where(ThreatBriefing.title == title).limit(1)
        ).scalar()
    )


def seed_briefings(session: Session, *, dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    created = 0
    skipped = 0

    # Offset created_at so briefings appear on a realistic timeline:
    # sample 0 -> 3h ago, sample 1 -> 30h ago, sample 2 -> 6h ago (daily newest after weekly).
    created_offsets_hours = [3, 30, 6]

    for idx, spec in enumerate(SAMPLE_BRIEFINGS):
        title = SAMPLE_PREFIX + spec["title"]
        if _title_exists(session, title):
            skipped += 1
            continue

        days_back = int(spec.get("days_back", 7))
        created_at = now - timedelta(hours=created_offsets_hours[idx % 3])
        period_end = created_at
        period_start = created_at - timedelta(days=days_back)

        raw_data = {
            "title": spec["title"],
            "executive_summary": spec["executive_summary"],
            "key_findings": spec.get("raw_data_findings", []),
            "sections": spec.get("raw_data_sections", []),
            "recommendations": spec.get("recommendations", []),
            "seeded": True,
        }

        tb = ThreatBriefing(
            id=uuid.uuid4(),
            period=spec["period"],
            period_start=period_start,
            period_end=period_end,
            title=title,
            executive_summary=spec["executive_summary"],
            key_campaigns=spec.get("key_campaigns", []),
            key_vulnerabilities=spec.get("key_vulnerabilities", []),
            key_actors=spec.get("key_actors", []),
            sector_threats=spec.get("sector_threats", {}),
            stats=spec.get("stats", {}),
            recommendations=spec.get("recommendations", []),
            raw_data=raw_data,
            created_at=created_at,
        )

        if dry_run:
            created += 1
            continue

        session.add(tb)
        session.flush()
        created += 1

    return {"created": created, "skipped": skipped, "total": len(SAMPLE_BRIEFINGS)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Delete existing sample briefings first, then reinsert.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without writing to the DB.")
    args = parser.parse_args()

    engine, Session_ = _make_session_factory()
    session: Session = Session_()
    try:
        if args.force and not args.dry_run:
            n = _purge_samples(session)
            session.commit()
            print(f"[force] purged {n} existing sample briefings")

        result = seed_briefings(session, dry_run=args.dry_run)

        if args.dry_run:
            print(f"[dry-run] would create {result['created']} / "
                  f"skip {result['skipped']} / total {result['total']}")
            session.rollback()
        else:
            session.commit()
            print(f"[ok] created {result['created']}, skipped {result['skipped']} "
                  f"(existing), total {result['total']}")
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
