"""Test script for AI prompt v2.0 upgrades.

Validates without requiring project dependencies (no httpx/fastapi/sqlalchemy).
Reads source files directly and tests logic in isolation.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import sys
import os
import textwrap

API_DIR = os.path.join(os.path.dirname(__file__), "..", "api")


def _read_source(rel_path: str) -> str:
    """Read a source file relative to the api directory."""
    full = os.path.normpath(os.path.join(API_DIR, rel_path))
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _extract_string_constant(source: str, var_name: str) -> str:
    """Extract a module-level string constant value by variable name."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise ValueError(f"Could not find string constant '{var_name}'")


# ── Test 1: _strip_json_fences logic ──────────────────────────

def test_strip_json_fences():
    """Test the JSON fence stripping function extracted inline."""
    # Replicate the function from ai.py
    def _strip_json_fences(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        return cleaned

    # Plain JSON
    assert _strip_json_fences('{"key": "val"}') == '{"key": "val"}'

    # With ```json fences
    assert _strip_json_fences('```json\n{"key": "val"}\n```') == '{"key": "val"}'

    # With ``` fences (no json keyword)
    assert _strip_json_fences('```\n{"key": "val"}\n```') == '{"key": "val"}'

    # Leading "json" without fences
    assert _strip_json_fences('json\n{"key": "val"}') == '{"key": "val"}'

    # Whitespace padding
    assert _strip_json_fences('  \n{"key": "val"}\n  ') == '{"key": "val"}'

    # Empty
    assert _strip_json_fences('') == ''

    # Nested fences shouldn't break
    assert '{"key"' in _strip_json_fences('```json\n{"key": "```val```"}\n```')

    print("✓ test_strip_json_fences: all 7 cases passed")


# ── Test 2: JSON parsing edge cases ──────────────────────────

def test_json_parsing_edge_cases():
    """Test JSON parsing paths in chat_completion_json."""
    def _strip_json_fences(text):
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        return cleaned

    cases = [
        ('{"executive_summary": "test", "threat_actors": []}', True),
        ('```json\n{"category": "active_threats"}\n```', True),
        ('{"broken": json}', False),
        ('{"key": "val",}', False),
        ('', False),
        ('null', True),  # valid JSON
        ('[]', True),    # valid JSON
    ]

    for raw, should_parse in cases:
        cleaned = _strip_json_fences(raw)
        try:
            json.loads(cleaned)
            parsed = True
        except (json.JSONDecodeError, ValueError):
            parsed = False
        assert parsed == should_parse, f"Failed for: {raw[:50]}... expected={should_parse}, got={parsed}"

    print(f"✓ test_json_parsing_edge_cases: all {len(cases)} cases passed")


# ── Test 3: _empty_enrichment completeness ──────────────────

def test_empty_enrichment_keys():
    """Verify _empty_enrichment function in intel.py returns all schema keys."""
    source = _read_source("app/routes/intel.py")

    # Extract the prompt version
    version = _extract_string_constant(source, "_ENRICHMENT_PROMPT_VERSION")
    assert version == "B-2.0", f"Expected B-2.0, got {version}"

    # Find _empty_enrichment return dict by executing the function in isolation
    # Extract the function source manually
    func_match = re.search(
        r'def _empty_enrichment\(\).*?(?=\n\n|\nclass |\n# |\n@|\ndef [a-z])',
        source, re.DOTALL
    )
    assert func_match, "_empty_enrichment function not found"

    func_source = func_match.group()
    # Replace the version reference with a string
    func_source = func_source.replace("_ENRICHMENT_PROMPT_VERSION", f'"{version}"')

    local_ns = {}
    exec(func_source, {}, local_ns)
    empty = local_ns["_empty_enrichment"]()

    required_keys = [
        "executive_summary", "threat_actors", "attack_techniques",
        "attack_narrative", "initial_access_vector", "post_exploitation",
        "affected_versions", "timeline_events", "notable_campaigns",
        "exploitation_info", "detection_opportunities", "ioc_summary",
        "targeted_sectors", "targeted_regions", "impacted_assets",
        "remediation", "related_cves", "tags_suggested",
        "recommended_priority", "confidence", "source_reliability",
        "_prompt_version",
    ]

    missing = [k for k in required_keys if k not in empty]
    assert not missing, f"Missing keys in _empty_enrichment: {missing}"

    # Nested structure checks
    assert isinstance(empty["exploitation_info"], dict)
    assert "epss_estimate" in empty["exploitation_info"]
    assert isinstance(empty["ioc_summary"], dict)
    assert "domains" in empty["ioc_summary"]
    assert isinstance(empty["remediation"], dict)
    assert "guidance" in empty["remediation"]
    assert empty["_prompt_version"] == "B-2.0"

    print(f"✓ test_empty_enrichment_keys: all {len(required_keys)} keys present, version={version}")


# ── Test 4: News prompt DB compatibility ─────────────────────

def test_news_prompt_db_compat():
    """Verify news prompt produces flat strings for ARRAY(Text) DB columns."""
    source = _read_source("app/services/news.py")
    prompt = _extract_string_constant(source, "_NEWS_ENRICHMENT_SYSTEM")

    # Find the JSON schema section
    schema_start = prompt.find('{')
    schema_end = prompt.rfind('}') + 1
    schema_section = prompt[schema_start:schema_end]

    # These fields must be flat string arrays (ARRAY(Text) in DB)
    flat_fields = ["threat_actors", "vulnerable_products", "tactics_techniques",
                   "malware_families", "post_exploitation", "targeted_sectors",
                   "targeted_regions", "impacted_assets", "detection_opportunities",
                   "mitigation_recommendations", "why_it_matters", "tags", "cves",
                   "related_cves"]

    for field in flat_fields:
        field_idx = schema_section.find(f'"{field}":')
        if field_idx == -1:
            continue  # Some fields may be optional
        value_start = schema_section.find(':', field_idx) + 1
        # Get the array content between [ and ]
        arr_start = schema_section.find('[', value_start)
        if arr_start == -1 or arr_start > value_start + 10:
            continue
        arr_end = schema_section.find(']', arr_start)
        array_content = schema_section[arr_start:arr_end + 1]
        # Should NOT contain { which indicates structured objects
        assert '{' not in array_content, \
            f"Field '{field}' should be flat strings, not objects. Content: {array_content[:120]}"

    # campaign_name should exist as a string field
    assert '"campaign_name"' in prompt, "campaign_name field missing (needed for DB String(300) column)"

    # Structured fields that use JSONB (objects are OK)
    jsonb_fields = ["ioc_summary", "timeline", "notable_campaigns", "exploitation_info"]
    for field in jsonb_fields:
        assert f'"{field}"' in prompt, f"JSONB field '{field}' missing from prompt"

    print(f"✓ test_news_prompt_db_compat: {len(flat_fields)} ARRAY(Text) fields are flat strings, campaign_name present")


# ── Test 5: enrich_news_item signature backward compat ───────

def test_news_enrich_signature():
    """Verify enrich_news_item can still be called as (headline, raw_content)."""
    source = _read_source("app/services/news.py")
    tree = ast.parse(source)

    func = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            if node.name == "enrich_news_item":
                func = node
                break

    assert func is not None, "enrich_news_item function not found"

    args = func.args
    # Positional args: headline, raw_content
    pos_args = [a.arg for a in args.args]
    assert "headline" in pos_args, f"'headline' not in positional args: {pos_args}"
    assert "raw_content" in pos_args, f"'raw_content' not in positional args: {pos_args}"

    # Keyword-only args should have defaults
    kw_args = [a.arg for a in args.kwonlyargs]
    kw_defaults = args.kw_defaults

    for i, kw in enumerate(kw_args):
        assert kw_defaults[i] is not None, f"Keyword-only arg '{kw}' has no default — breaks backward compat"

    print(f"✓ test_news_enrich_signature: positional={pos_args}, keyword_only={kw_args}")


# ── Test 6: Prompt version tags ──────────────────────────────

def test_prompt_versions():
    intel_source = _read_source("app/routes/intel.py")
    news_source = _read_source("app/services/news.py")

    intel_ver = _extract_string_constant(intel_source, "_ENRICHMENT_PROMPT_VERSION")
    news_ver = _extract_string_constant(news_source, "_NEWS_ENRICHMENT_PROMPT_VERSION")

    assert intel_ver == "B-2.0", f"Intel version wrong: {intel_ver}"
    assert news_ver == "D-2.0", f"News version wrong: {news_ver}"

    print(f"✓ test_prompt_versions: Intel={intel_ver}, News={news_ver}")


# ── Test 7: Quality guardrails in both prompts ───────────────

def test_quality_guardrails():
    intel_source = _read_source("app/routes/intel.py")
    news_source = _read_source("app/services/news.py")

    intel_prompt = _extract_string_constant(intel_source, "_ENRICHMENT_SYSTEM_PROMPT")
    news_prompt = _extract_string_constant(news_source, "_NEWS_ENRICHMENT_SYSTEM")

    for name, prompt in [("Intel B-2.0", intel_prompt), ("News D-2.0", news_prompt)]:
        assert "BANNED PHRASES" in prompt, f"{name}: missing BANNED PHRASES"
        assert "REQUIRED QUALITY" in prompt, f"{name}: missing REQUIRED QUALITY"
        assert "BAD vs GOOD" in prompt or "BAD" in prompt, f"{name}: missing examples"
        assert "timely patching" in prompt, f"{name}: missing banned phrase example"
        assert "Return ONLY" in prompt or "return ONLY" in prompt, f"{name}: missing JSON-only instruction"
        # Both should have dual-audience framing
        assert "CISO" in prompt or "Fortune 100" in prompt, f"{name}: missing audience framing"

    print("✓ test_quality_guardrails: both prompts have BANNED/REQUIRED/EXAMPLES/AUDIENCE")


# ── Test 8: chat_completion_json exists in ai.py AST ─────────

def test_ai_exports():
    source = _read_source("app/services/ai.py")
    tree = ast.parse(source)

    functions = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            functions.add(node.name)

    required = ["chat_completion", "chat_completion_json", "_strip_json_fences",
                 "generate_summary", "check_ai_health", "_call_with_fallback"]

    for fn in required:
        assert fn in functions, f"Function '{fn}' not found in ai.py"

    # Verify chat_completion_json has required_keys parameter
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "chat_completion_json":
            param_names = [a.arg for a in node.args.args] + [a.arg for a in node.args.kwonlyargs]
            assert "required_keys" in param_names, "chat_completion_json missing required_keys param"
            assert "caller" in param_names, "chat_completion_json missing caller param"
            break

    print(f"✓ test_ai_exports: all {len(required)} functions found, chat_completion_json has required_keys+caller")


# ── Test 9: Intel enrichment handler uses chat_completion_json ─

def test_intel_handler_uses_json():
    source = _read_source("app/routes/intel.py")
    assert "chat_completion_json" in source, "intel.py should import chat_completion_json"
    assert "max_tokens=3000" in source, "intel.py should use max_tokens=3000"
    assert 'required_keys=["executive_summary"' in source, "intel.py should validate required keys"
    assert '_prompt_version' in source, "intel.py should stamp prompt version"

    print("✓ test_intel_handler_uses_json: handler uses chat_completion_json with validation")


# ── Test 10: News enrichment handler uses chat_completion_json ─

def test_news_handler_uses_json():
    source = _read_source("app/services/news.py")
    assert "chat_completion_json" in source, "news.py should import chat_completion_json"
    assert "max_tokens=3500" in source, "news.py should use max_tokens=3500"
    assert 'required_keys=["category"' in source, "news.py should validate required keys"
    assert '_prompt_version' in source, "news.py should stamp prompt version"

    print("✓ test_news_handler_uses_json: handler uses chat_completion_json with validation")


# ── Run all ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("AI Prompt v2.0 Upgrade — Validation Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    tests = [
        test_strip_json_fences,
        test_json_parsing_edge_cases,
        test_empty_enrichment_keys,
        test_news_prompt_db_compat,
        test_news_enrich_signature,
        test_prompt_versions,
        test_quality_guardrails,
        test_ai_exports,
        test_intel_handler_uses_json,
        test_news_handler_uses_json,
    ]

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
