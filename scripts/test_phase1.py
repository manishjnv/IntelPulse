#!/usr/bin/env python3
"""Phase 1 Quick Wins - End-to-End Tests"""
import urllib.request, json, sys

BASE = 'http://localhost:8000/api/v1'
HEADERS = {
    'X-User-Id': '00000000-0000-0000-0000-000000000001',
    'X-User-Email': 'admin@test.com',
    'X-User-Role': 'admin',
    'Content-Type': 'application/json'
}

passed = 0
failed = 0

def api(method, path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp else b'{}'
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {}

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name} {detail}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")

# --- Test 1: List cases with sorting ---
print("=== Test 1: List cases with sort ===")
code, data = api('GET', '/cases?page=1&page_size=3&sort_by=updated_at&sort_order=desc')
check("List cases returns 200", code == 200, f"(got {code})")
check("Response has 'cases' key", 'cases' in data)
check("Response has 'total' key", 'total' in data)

# --- Test 2: SQL injection guard ---
print("\n=== Test 2: SQL injection guard ===")
code, data = api('GET', '/cases?page=1&sort_by=;DROP TABLE cases;--')
check("Invalid sort_by returns 200 (falls back to default)", code == 200, f"(got {code})")
check("Response still has cases", 'cases' in data)

# --- Test 3: Sort by different columns ---
print("\n=== Test 3: Sort by title asc ===")
code, data = api('GET', '/cases?page=1&page_size=50&sort_by=title&sort_order=asc')
check("Sort by title returns 200", code == 200)
titles = [c['title'] for c in data.get('cases', [])]
if len(titles) >= 2:
    check("Titles are sorted ascending", titles == sorted(titles, key=str.lower), f"{titles[:3]}")

# --- Test 4: Create + Clone ---
print("\n=== Test 4: Create case for clone test ===")
code, created = api('POST', '/cases', {
    'title': 'Phase1 Clone Test Case',
    'case_type': 'investigation',
    'priority': 'high',
    'severity': 'medium',
    'tlp': 'TLP:GREEN',
    'tags': ['test', 'phase1']
})
check("Create case returns 201", code == 201, f"(got {code})")
case_id = created.get('id')
check("Case has ID", case_id is not None)

if case_id:
    print("\n=== Test 5: Clone case ===")
    code, cloned = api('POST', f'/cases/{case_id}/clone')
    check("Clone returns 201", code == 201, f"(got {code})")
    check("Clone title has (Copy)", '(Copy)' in cloned.get('title', ''), f"title={cloned.get('title')}")
    check("Clone status is 'new'", cloned.get('status') == 'new', f"status={cloned.get('status')}")
    check("Clone preserves tags", 'test' in cloned.get('tags', []), f"tags={cloned.get('tags')}")
    cloned_id = cloned.get('id')

    print("\n=== Test 6: Add item + counter trigger ===")
    code, item = api('POST', f'/cases/{case_id}/items', {
        'item_type': 'intel',
        'item_id': 'test-intel-001',
        'item_title': 'Test Intel Item'
    })
    check("Add item returns 201", code == 201, f"(got {code})")

    # Check counter was updated by trigger
    code2, refreshed = api('GET', f'/cases/{case_id}')
    check("Intel counter incremented", refreshed.get('linked_intel_count', 0) >= 1,
          f"linked_intel_count={refreshed.get('linked_intel_count')}")

    print("\n=== Test 7: Duplicate item (race condition guard) ===")
    code, dup = api('POST', f'/cases/{case_id}/items', {
        'item_type': 'intel',
        'item_id': 'test-intel-001',
        'item_title': 'Test Intel Item'
    })
    check("Duplicate item returns 409", code == 409, f"(got {code})")

    print("\n=== Test 8: Reconcile counters ===")
    code, rec = api('POST', f'/cases/{case_id}/reconcile')
    check("Reconcile returns 200", code == 200, f"(got {code})")
    check("Reconcile returns counters", 'linked_intel_count' in rec, f"result={rec}")

    # Cleanup
    print("\n=== Cleanup ===")
    if cloned_id:
        api('DELETE', f'/cases/{cloned_id}')
        print(f"  Deleted cloned case {cloned_id}")
    api('DELETE', f'/cases/{case_id}')
    print(f"  Deleted test case {case_id}")

# --- Test 9: Stats endpoint ---
print("\n=== Test 9: Stats endpoint ===")
code, stats = api('GET', '/cases/stats')
check("Stats returns 200", code == 200, f"(got {code})")
check("Stats has total_cases", 'total_cases' in stats)

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed} tests")
if failed > 0:
    sys.exit(1)
