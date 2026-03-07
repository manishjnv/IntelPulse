#!/usr/bin/env python3
"""Direct service-level tests for Phase 1 Quick Wins."""
import asyncio
import sys
sys.path.insert(0, "/app")

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name} {detail}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")

async def run_tests():
    from app.core.database import engine, async_session_factory
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
    from app.services.cases import (
        list_cases, create_case, clone_case,
        reconcile_case_counters, add_case_item, ALLOWED_SORT_COLUMNS,
    )

    Session = async_session_factory

    # --- Test 1: ALLOWED_SORT_COLUMNS exists ---
    print("=== Test 1: Sort column allowlist ===")
    check("ALLOWED_SORT_COLUMNS defined", ALLOWED_SORT_COLUMNS is not None)
    check("Contains expected columns", "title" in ALLOWED_SORT_COLUMNS and "priority" in ALLOWED_SORT_COLUMNS)
    print(f"  Columns: {ALLOWED_SORT_COLUMNS}")

    # --- Test 2: SQL injection guard ---
    print("\n=== Test 2: SQL injection guard ===")
    async with Session() as db:
        cases, total = await list_cases(db, page=1, page_size=3, sort_by=";DROP TABLE cases;", sort_order="desc")
        check("Malicious sort_by doesn't crash", True)
        check("Returns valid response", isinstance(cases, list) and isinstance(total, int),
              f"total={total}, cases_count={len(cases)}")

    # --- Test 3: Valid sort columns ---
    print("\n=== Test 3: Sort by different columns ===")
    for col in ["title", "priority", "status", "created_at", "updated_at"]:
        async with Session() as db:
            cases, total = await list_cases(db, page=1, page_size=3, sort_by=col, sort_order="asc")
            check(f"Sort by {col}", isinstance(cases, list), f"count={len(cases)}")

    # --- Test 4: Create + Clone ---
    print("\n=== Test 4: Create case ===")
    test_user_id = None
    async with Session() as db:
        # Get any user
        r = await db.execute(text("SELECT id FROM users LIMIT 1"))
        row = r.scalar_one_or_none()
        if row:
            test_user_id = str(row)
            print(f"  Using user_id: {test_user_id}")

    if test_user_id:
        async with Session() as db:
            case = await create_case(
                db,
                owner_id=test_user_id,
                data={
                    "title": "Phase1 Test Case",
                    "case_type": "investigation",
                    "priority": "high",
                    "severity": "medium",
                    "tlp": "TLP:GREEN",
                    "tags": ["test", "phase1"],
                },
            )
            await db.commit()
            check("Case created", case is not None and case.id is not None, f"id={case.id}")
            case_id = str(case.id)

        print("\n=== Test 5: Clone case ===")
        async with Session() as db:
            cloned = await clone_case(db, case_id, test_user_id)
            await db.commit()
            check("Clone created", cloned is not None)
            check("Clone title has (Copy)", "(Copy)" in cloned.title, f"title={cloned.title}")
            check("Clone status is new", cloned.status == "new", f"status={cloned.status}")
            check("Clone has tags", "test" in cloned.tags, f"tags={cloned.tags}")
            cloned_id = str(cloned.id)

        print("\n=== Test 6: Add item + duplicate guard ===")
        async with Session() as db:
            item = await add_case_item(
                db, case_id,
                user_id=test_user_id,
                data={
                    'item_type': 'intel',
                    'item_id': 'test-intel-999',
                    'item_title': 'Test Intel',
                },
            )
            await db.commit()
            check("Item added", item is not None and not isinstance(item, str), f"item={item}")

        # Try duplicate
        dup_409 = False
        async with Session() as db:
            try:
                result = await add_case_item(
                    db, case_id,
                    user_id=test_user_id,
                    data={
                        'item_type': 'intel',
                        'item_id': 'test-intel-999',
                        'item_title': 'Test Intel',
                    },
                )
                dup_409 = (result == "duplicate")
            except Exception as e:
                dup_409 = "IntegrityError" in type(e).__name__ or "duplicate" in str(e).lower()
        check("Duplicate item prevented", dup_409)

        print("\n=== Test 7: Reconcile counters ===")
        async with Session() as db:
            await reconcile_case_counters(db, case_id)
            await db.commit()
            check("Reconcile completed without error", True)

        # Verify counters after reconcile
        async with Session() as db:
            from app.services.cases import get_case as get_case_fn
            refreshed = await get_case_fn(db, case_id)
            check("Intel counter correct after reconcile", refreshed.linked_intel_count == 1,
                  f"linked_intel_count={refreshed.linked_intel_count}")

        print("\n=== Test 8: DB trigger verification ===")
        async with Session() as db:
            r = await db.execute(text(
                "SELECT tgname FROM pg_trigger WHERE tgname = 'trg_case_item_counters'"
            ))
            trigger = r.scalar_one_or_none()
            check("Counter trigger exists", trigger is not None, f"trigger={trigger}")

        # Cleanup
        print("\n=== Cleanup ===")
        async with Session() as db:
            await db.execute(text(f"DELETE FROM case_items WHERE case_id = '{case_id}'"))
            await db.execute(text(f"DELETE FROM case_items WHERE case_id = '{cloned_id}'"))
            await db.execute(text(f"DELETE FROM case_activities WHERE case_id = '{case_id}'"))
            await db.execute(text(f"DELETE FROM case_activities WHERE case_id = '{cloned_id}'"))
            await db.execute(text(f"DELETE FROM cases WHERE id = '{cloned_id}'"))
            await db.execute(text(f"DELETE FROM cases WHERE id = '{case_id}'"))
            await db.commit()
            print(f"  Cleaned up test cases")
    else:
        print("  SKIP: No users found in DB, skipping create/clone tests")

    # --- Test 9: FK constraints ---
    print("\n=== Test 9: FK constraints ===")
    async with Session() as db:
        r = await db.execute(text("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE constraint_name IN ('fk_case_items_added_by', 'fk_case_activities_user_id')
        """))
        constraints = [row[0] for row in r.fetchall()]
        check("FK fk_case_items_added_by exists", "fk_case_items_added_by" in constraints, f"found={constraints}")
        check("FK fk_case_activities_user_id exists", "fk_case_activities_user_id" in constraints)

    # --- Test 10: Index on updated_at ---
    print("\n=== Test 10: Index on updated_at ===")
    async with Session() as db:
        r = await db.execute(text("""
            SELECT indexname FROM pg_indexes WHERE indexname = 'idx_cases_updated'
        """))
        idx = r.scalar_one_or_none()
        check("idx_cases_updated index exists", idx is not None, f"index={idx}")

    await engine.dispose()

asyncio.run(run_tests())

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed} tests")
if failed > 0:
    sys.exit(1)
else:
    print("ALL PHASE 1 BACKEND TESTS PASSED!")
