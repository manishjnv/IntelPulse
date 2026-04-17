#!/usr/bin/env python3
"""Seed the IntelPulse demo DB with rich sample cases and reports.

Writes directly to Postgres via SQLAlchemy (same sync engine the worker
uses). Replaces the older curl-based `seed_sample_reports.py` flow with
one that is reliable, idempotent, and dry-run friendly.

Usage:
    python -m scripts.seed_sample_data            # insert missing only
    python -m scripts.seed_sample_data --force    # delete+reinsert all samples
    python -m scripts.seed_sample_data --dry-run  # print what would happen
    python -m scripts.seed_sample_data --cases    # seed only cases
    python -m scripts.seed_sample_data --reports  # seed only reports

All sample titles are uniformly prefixed with "[SAMPLE] " so the seed can
re-discover its own rows for idempotent updates without accidentally
touching real user content.
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
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings
from app.models.models import (
    Case,
    CaseActivity,
    CaseItem,
    Report,
    ReportItem,
    User,
)

from scripts.sample_data import SAMPLE_CASES, SAMPLE_REPORTS
from scripts.sample_data.reports_data import REPORT_TYPES, SEVERITIES, TLP_FOR_SEVERITY


# ── Constants ───────────────────────────────────────────────

SAMPLE_PREFIX = "[SAMPLE] "
DEFAULT_AUTHOR_EMAIL = "seed-bot@intelpulse.local"
DEFAULT_AUTHOR_NAME = "IntelPulse Sample Data Seeder"


# ── DB session ──────────────────────────────────────────────

def _make_session_factory() -> tuple:
    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=2)
    Session_ = sessionmaker(bind=engine)
    return engine, Session_


# ── Helpers ─────────────────────────────────────────────────

def _get_or_create_seed_user(session: Session, email_override: str | None = None) -> User:
    """Find the seed author user or create one on the fly.

    If an email override (e.g. the configured demo user email) is passed
    and exists, we reuse it so samples appear under the operator's
    primary identity. Otherwise we fall back to a dedicated seed bot user.
    """
    if email_override:
        u = session.execute(select(User).where(User.email == email_override)).scalar_one_or_none()
        if u:
            return u

    u = session.execute(
        select(User).where(User.email == DEFAULT_AUTHOR_EMAIL)
    ).scalar_one_or_none()
    if u:
        return u

    u = User(
        id=uuid.uuid4(),
        email=DEFAULT_AUTHOR_EMAIL,
        name=DEFAULT_AUTHOR_NAME,
        role="admin",
        is_active=True,
    )
    session.add(u)
    session.flush()
    return u


def _sample_titles(prefix: str) -> set[str]:
    """All titles we expect to see in the DB — used for idempotent delete."""
    titles = set()
    for c in SAMPLE_CASES:
        titles.add(prefix + c["title"])
    for rtype in REPORT_TYPES:
        for sev in SEVERITIES:
            entry = SAMPLE_REPORTS.get(rtype, {}).get(sev)
            if entry:
                titles.add(prefix + entry["title"])
    return titles


def _purge_existing_samples(session: Session, *, only: str = "all") -> tuple[int, int]:
    """Delete all rows whose title starts with the sample prefix.

    Returns (cases_deleted, reports_deleted). Child rows (items, activities)
    are removed first to satisfy FK-less but logical integrity.
    """
    cases_deleted = 0
    reports_deleted = 0

    if only in ("all", "cases"):
        case_rows = session.execute(
            select(Case.id).where(Case.title.like(SAMPLE_PREFIX + "%"))
        ).scalars().all()
        if case_rows:
            session.execute(delete(CaseActivity).where(CaseActivity.case_id.in_(case_rows)))
            session.execute(delete(CaseItem).where(CaseItem.case_id.in_(case_rows)))
            r = session.execute(delete(Case).where(Case.id.in_(case_rows)))
            cases_deleted = r.rowcount or len(case_rows)

    if only in ("all", "reports"):
        report_rows = session.execute(
            select(Report.id).where(Report.title.like(SAMPLE_PREFIX + "%"))
        ).scalars().all()
        if report_rows:
            session.execute(delete(ReportItem).where(ReportItem.report_id.in_(report_rows)))
            r = session.execute(delete(Report).where(Report.id.in_(report_rows)))
            reports_deleted = r.rowcount or len(report_rows)

    return cases_deleted, reports_deleted


def _title_exists(session: Session, model, title: str) -> bool:
    return bool(
        session.execute(select(model.id).where(model.title == title).limit(1)).scalar()
    )


# ── Case seeding ────────────────────────────────────────────

def seed_cases(session: Session, *, author: User, dry_run: bool = False) -> dict:
    """Insert sample cases that aren't already present (by prefixed title).

    Older cases are backdated so the demo shows a realistic spread on the
    updated_at timeline. Newer entries first in SAMPLE_CASES → newest
    created_at; older entries get progressively older timestamps.
    """
    now = datetime.now(timezone.utc)
    created_count = 0
    skipped_count = 0
    items_created = 0
    activities_created = 0

    for idx, spec in enumerate(SAMPLE_CASES):
        title = SAMPLE_PREFIX + spec["title"]

        if _title_exists(session, Case, title):
            skipped_count += 1
            continue

        # Offset created_at so newest sample is 2h ago, older ones further back.
        created_at = now - timedelta(hours=2 + idx * 18)
        updated_at = created_at + timedelta(hours=1)
        is_closed = spec["status"] in ("resolved", "closed")

        items = spec.get("items", []) or []
        activities = spec.get("activities", []) or []

        # Pre-count denormalised counters so they match the items we add.
        intel_n = sum(1 for i in items if i["item_type"] == "intel")
        ioc_n = sum(1 for i in items if i["item_type"] == "ioc")
        obs_n = sum(
            1 for i in items
            if i["item_type"] in ("technique", "observable", "artefact", "artifact")
        )

        case = Case(
            id=uuid.uuid4(),
            title=title,
            description=spec.get("description"),
            case_type=spec["case_type"],
            status=spec["status"],
            priority=spec["priority"],
            severity=spec["severity"],
            tlp=spec.get("tlp", "TLP:GREEN"),
            owner_id=author.id,
            assignee_id=author.id,
            tags=spec.get("tags", []),
            linked_intel_count=intel_n,
            linked_ioc_count=ioc_n,
            linked_observable_count=obs_n,
            created_at=created_at,
            updated_at=updated_at,
            closed_at=updated_at + timedelta(hours=3) if is_closed else None,
        )

        if dry_run:
            created_count += 1
            items_created += len(items)
            activities_created += len(activities)
            continue

        session.add(case)
        session.flush()

        # Items — link order preserved so the UI shows them chronologically.
        for i, item_spec in enumerate(items):
            session.add(CaseItem(
                id=uuid.uuid4(),
                case_id=case.id,
                item_type=item_spec["item_type"],
                item_id=item_spec["item_id"],
                item_title=item_spec.get("item_title"),
                item_metadata=item_spec.get("item_metadata", {}) or {},
                added_by=author.id,
                notes=item_spec.get("notes"),
                created_at=created_at + timedelta(minutes=10 + i * 5),
            ))
            items_created += 1

        # Activities — distributed across the case lifetime.
        for i, act_spec in enumerate(activities):
            session.add(CaseActivity(
                id=uuid.uuid4(),
                case_id=case.id,
                user_id=author.id,
                action=act_spec["action"],
                detail=act_spec.get("detail"),
                meta={},
                created_at=created_at + timedelta(minutes=i * 15),
            ))
            activities_created += 1

        session.flush()
        created_count += 1

    return {
        "created": created_count,
        "skipped": skipped_count,
        "items": items_created,
        "activities": activities_created,
    }


# ── Report seeding ──────────────────────────────────────────

def seed_reports(session: Session, *, author: User, dry_run: bool = False) -> dict:
    """Insert all 25 (report_type × severity) sample reports."""
    now = datetime.now(timezone.utc)
    created_count = 0
    skipped_count = 0

    # Interleave across severities so the demo dashboard shows a full spread.
    idx = 0
    for rtype in REPORT_TYPES:
        for sev in SEVERITIES:
            entry = SAMPLE_REPORTS.get(rtype, {}).get(sev)
            if not entry:
                continue

            title = SAMPLE_PREFIX + entry["title"]
            if _title_exists(session, Report, title):
                skipped_count += 1
                idx += 1
                continue

            created_at = now - timedelta(hours=1 + idx * 7)
            published_at = (
                created_at + timedelta(hours=2)
                if sev in ("critical", "high")
                else None
            )
            status = "published" if published_at else ("review" if sev == "medium" else "draft")

            report = Report(
                id=uuid.uuid4(),
                title=title,
                summary=entry.get("summary"),
                content={"sections": entry["sections"]},
                report_type=rtype,
                status=status,
                severity=sev,
                tlp=entry.get("tlp", TLP_FOR_SEVERITY[sev]),
                author_id=author.id,
                template=rtype,
                tags=entry.get("tags", []),
                linked_intel_count=0,
                linked_ioc_count=0,
                linked_technique_count=0,
                created_at=created_at,
                updated_at=created_at,
                published_at=published_at,
            )

            if dry_run:
                created_count += 1
                idx += 1
                continue

            session.add(report)
            session.flush()
            created_count += 1
            idx += 1

    return {"created": created_count, "skipped": skipped_count}


# ── Entry point ─────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed rich sample cases + reports.")
    parser.add_argument("--force", action="store_true",
                        help="Delete all existing sample rows first, then reinsert.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be written without touching the DB.")
    parser.add_argument("--cases", action="store_true",
                        help="Seed only cases (default: seed both).")
    parser.add_argument("--reports", action="store_true",
                        help="Seed only reports (default: seed both).")
    parser.add_argument("--author-email", default=None,
                        help="Use an existing user with this email as the author/owner. "
                             "Falls back to a dedicated seed bot user if not found.")
    args = parser.parse_args()

    seed_cases_enabled = args.cases or not args.reports
    seed_reports_enabled = args.reports or not args.cases

    engine, Session_ = _make_session_factory()
    session = Session_()

    summary: dict = {"cases": None, "reports": None, "purged": None}

    try:
        author = _get_or_create_seed_user(session, args.author_email)
        print(f"Seed author: {author.email} (id={str(author.id)[:8]})")

        if args.force:
            only = "all"
            if args.cases and not args.reports:
                only = "cases"
            elif args.reports and not args.cases:
                only = "reports"

            if args.dry_run:
                # Count without deleting
                cases_n = session.execute(
                    select(Case.id).where(Case.title.like(SAMPLE_PREFIX + "%"))
                ).scalars().all()
                reports_n = session.execute(
                    select(Report.id).where(Report.title.like(SAMPLE_PREFIX + "%"))
                ).scalars().all()
                summary["purged"] = {"cases": len(cases_n), "reports": len(reports_n)}
                print(f"[dry-run] Would purge {len(cases_n)} sample cases and "
                      f"{len(reports_n)} sample reports before reinsert.")
            else:
                cd, rd = _purge_existing_samples(session, only=only)
                summary["purged"] = {"cases": cd, "reports": rd}
                print(f"Purged existing samples: {cd} cases, {rd} reports.")

        if seed_cases_enabled:
            summary["cases"] = seed_cases(session, author=author, dry_run=args.dry_run)
        if seed_reports_enabled:
            summary["reports"] = seed_reports(session, author=author, dry_run=args.dry_run)

        if args.dry_run:
            session.rollback()
            print("[dry-run] No changes committed.")
        else:
            session.commit()

        print("\n" + "=" * 60)
        if summary["cases"]:
            c = summary["cases"]
            print(f"Cases:   created={c['created']}, skipped={c['skipped']}, "
                  f"items={c['items']}, activities={c['activities']}")
        if summary["reports"]:
            r = summary["reports"]
            print(f"Reports: created={r['created']}, skipped={r['skipped']}")
        print("=" * 60)
        return 0

    except Exception as e:
        session.rollback()
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
