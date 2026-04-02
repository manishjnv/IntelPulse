# Exhaustive Normalization, Validation, Mapping & Transformation Audit

> **Scope**: Every instance of normalization, validation, mapping, transformation, coercion, and cleaning across the entire IntelPulse codebase.
>
> **Date**: 2026-03-08

---

## Table of Contents

1. [Severity Mapping](#1-severity-mapping)
2. [Date/Time Parsing & Normalization](#2-datetime-parsing--normalization)
3. [IOC Type Detection & Asset Type Mapping](#3-ioc-type-detection--asset-type-mapping)
4. [Category / Enum Normalization](#4-category--enum-normalization)
5. [String Cleaning & Text Normalization](#5-string-cleaning--text-normalization)
6. [Hashing & Deduplication](#6-hashing--deduplication)
7. [Score Clamping & Numeric Coercion](#7-score-clamping--numeric-coercion)
8. [Geographic & Industry Mapping](#8-geographic--industry-mapping)
9. [Product / Vendor Normalization](#9-product--vendor-normalization)
10. [Campaign / Actor Name Normalization](#10-campaign--actor-name-normalization)
11. [AI Response Parsing & Validation](#11-ai-response-parsing--validation)
12. [Feed Connector normalize() Methods](#12-feed-connector-normalize-methods)
13. [MITRE ATT&CK Keyword Mapping](#13-mitre-attck-keyword-mapping)
14. [Pydantic Schema Validation](#14-pydantic-schema-validation)
15. [SQL / DB-Level Constraints](#15-sql--db-level-constraints)
16. [OpenSearch Field Mapping](#16-opensearch-field-mapping)
17. [Export Transformations](#17-export-transformations)
18. [Dual Source-of-Truth Issues](#18-dual-source-of-truth-issues)
19. [Duplication / Code-Clone Issues](#19-duplication--code-clone-issues)
20. [Inline Validation → Extract to Functions](#20-inline-validation--extract-to-functions)
21. [Reuse Opportunities](#21-reuse-opportunities)

---

## 1. Severity Mapping

Every location where severity strings are derived or mapped.

### 1A. `api/app/services/scoring.py` L28-35 — `SEVERITY_SCORES`

- **Category**: Mapping (string → int)
- **Input → Output**: `str("critical"|"high"|"medium"|"low"|"info"|"unknown")` → `int(100|80|50|25|10|0)`
- **Dependencies**: Used by `compute_risk_score()` at L42
- **Duplication**: None — single canonical mapping for risk scoring
- **Reuse potential**: Could be imported by other modules that need numeric severity

### 1B. `api/app/services/intel_extraction.py` L30 — `_SEVERITY_RANK`

- **Category**: Mapping (string → int priority rank)
- **Input → Output**: `str("critical"→4, "high"→3, "medium"→2, "low"→1, "info"→0, "unknown"→-1)`
- **Dependencies**: Used by `_upsert_product_sync()` L155, `_upsert_campaign_sync()` L211 for "keep higher severity on conflict"
- **Duplication**: **DUPLICATED concept** with `SEVERITY_SCORES` in scoring.py but different scale/purpose
- **Reuse potential**: Could share a single `SEVERITY_RANK` constant

### 1C. `api/app/services/intel_extraction.py` L636-638 — `_priority_to_severity()`

- **Category**: Mapping (priority string → severity string)
- **Input → Output**: `str("critical"|"high"|"medium"|"low")` → `str` (same values, with fallback to `"unknown"`)
- **Dependencies**: Called by `_extract_products_sync()` L111, `_extract_campaigns_sync()` L194
- **Duplication**: Near-identical to `_map_severity()` in cisa_advisories.py

### 1D. `api/app/services/feeds/threatfox.py` L29-33 — `_SEVERITY_MAP`

- **Category**: Mapping (source-specific severity → normalized)
- **Input → Output**: `"high"→"critical"`, `"medium"→"high"`, `"low"→"medium"`
- **Dependencies**: Used in `normalize()` L86-160, plus keyword-based override (botnet/c2/payload→critical)
- **Duplication**: Every feed has its own severity logic — see below

### 1E. `api/app/services/feeds/abuseipdb.py` L118-180 — inline severity

- **Category**: Inline mapping (abuse_score thresholds → severity)
- **Input → Output**: `int(abuse_score)` → `str`: `≥90→"critical"`, `≥70→"high"`, `≥50→"medium"`, else→`"low"`
- **Duplication**: **INLINE** — should be extracted to a function

### 1F. `api/app/services/feeds/kev.py` L41-110 — hardcoded `"critical"`

- **Category**: Constant assignment
- **Input → Output**: All KEV entries → `severity="critical"` (hardcoded)
- **Duplication**: N/A — domain-correct (all KEV entries are critical by definition)

### 1G. `api/app/services/feeds/nvd.py` L62-155 — `baseSeverity` passthrough

- **Category**: Passthrough (from NVD CVSS data)
- **Input → Output**: Uses `baseSeverity` from CVSS v3.1→v3.0→v2 cascade, lowercased
- **Duplication**: N/A — source-specific

### 1H. `api/app/services/feeds/otx.py` L65-160 — indicator-count-based

- **Category**: Inline mapping (indicator count → severity)
- **Input → Output**: `int(indicator_count)` → `str`: `>100→"critical"`, `>50→"high"`, `>10→"medium"`, else→`"low"`
- **Duplication**: **INLINE** — should be extracted

### 1I. `api/app/services/feeds/urlhaus.py` L65-115 — status-based

- **Category**: Inline mapping (URL status → severity)
- **Input → Output**: `str(status)` → `"high"` if `"online"`, else `"medium"`
- **Duplication**: **INLINE**

### 1J. `api/app/services/feeds/shodan.py` L118-134 — `_normalize_cvedb()` CVSS-based + KEV/EPSS boost

- **Category**: Threshold mapping (CVSS v3 → severity) + conditional boost
- **Input → Output**: `float(cvss_v3)` → `str`: `≥9.0→"critical"`, `≥7.0→"high"`, `≥4.0→"medium"`, else→`"low"`, then KEV boost, EPSS boost
- **Duplication**: Similar CVSS logic as NVD but with added boost rules

### 1K. `api/app/services/feeds/shodan.py` L248-260 — `_normalize_host()` vuln-count-based

- **Category**: Threshold mapping (vulnerability count → severity)
- **Input → Output**: `int(vuln_count)` → `str`: `≥10→"critical"`, `≥5→"high"`, `≥1→"medium"`, else→`"low"`
- **Duplication**: Similar pattern to OTX indicator-count mapping

### 1L. `api/app/services/feeds/virustotal.py` L237-243 — detection-ratio-based

- **Category**: Threshold mapping (detection ratio → severity)
- **Input → Output**: `float(detection_ratio)` → `str`: `≥0.6→"critical"`, `≥0.3→"high"`, `≥0.1→"medium"`, else→`"low"`
- **Duplication**: Unique to VT

### 1M. `api/app/services/feeds/exploitdb.py` L109-121 — `_classify_exploit()` keyword-based

- **Category**: Keyword matching (title+desc → severity)
- **Input → Output**: `str(combined_text)` → `str`: RCE keywords→`"critical"`, privesc→`"high"`, DoS/XSS→`"medium"`, default→`"high"`
- **Duplication**: Similar keyword approach as MITRE ATT&CK's `_severity_from_description()`

### 1N. `api/app/services/feeds/cisa_advisories.py` L74-77 — `_map_severity()`

- **Category**: Mapping (passthrough with default)
- **Input → Output**: `str|None` → `str`: same value lowered, default `"medium"`
- **Duplication**: Near-identical to `_priority_to_severity()` in intel_extraction.py

### 1O. `api/app/services/feeds/mitre_attack.py` L152-161 — `_severity_from_description()` keyword-based

- **Category**: Keyword matching (description → severity by object type)
- **Input → Output**: Description text + obj_type → `str`: nation-state keywords→`"critical"`, APT keywords→`"high"`, else `"high"` (actors) or `"medium"` (campaigns)
- **Duplication**: Similar pattern to ExploitDB

### 1P. `api/app/services/feeds/malwarebazaar.py` L79-85 — `_severity_from_tags()` keyword-based

- **Category**: Set intersection (tags → severity)
- **Input → Output**: `list[str](tags)` → `str`: ransomware/APT keywords→`"critical"`, trojan/RAT→`"high"`, else→`"medium"`
- **Duplication**: Similar set-intersection pattern, unique keyword set

---

## 2. Date/Time Parsing & Normalization

### 2A. `api/app/services/news.py` L142-156 — `_parse_pub_date()`

- **Category**: Multi-format date parser
- **Input → Output**: `str` → `datetime|None` — tries RFC 2822 (`parsedate_to_datetime`), then ISO formats, then `%Y-%m-%d`
- **Dependencies**: Used in `_fetch_rss()` for RSS/Atom date parsing
- **Duplication**: **DUPLICATED pattern** — at least 6 other date parsers exist

### 2B. `api/app/services/scoring.py` L85-100 — `_compute_freshness()`

- **Category**: Date parsing + time-decay bucketing
- **Input → Output**: `str` → `float(0.1-1.0)` — ISO parse, then bucket by age (1d=1.0, 7d=0.9, 30d=0.7, 90d=0.4, else=0.1)
- **Dependencies**: Used by `compute_risk_score()` L42

### 2C. `api/app/services/feeds/exploitdb.py` L79-84 — `_parse_rss_date()`

- **Category**: RSS date parser
- **Input → Output**: `str|None` → `datetime|None` — `parsedate_to_datetime().astimezone(utc)`
- **Duplication**: **SUBSET of `_parse_pub_date()`** in news.py

### 2D. `api/app/services/feeds/abuseipdb.py` — inline ISO parse

- **Category**: Inline date coercion
- **Input → Output**: ISO string → `datetime` via `datetime.fromisoformat()`
- **Duplication**: **INLINE** — repeated across many feeds

### 2E. `api/app/services/feeds/cisa_advisories.py` L68-73 — `_parse_iso()`

- **Category**: ISO parser with Z→+00:00 replacement
- **Input → Output**: `str|None` → `datetime|None`
- **Duplication**: **IDENTICAL pattern** in shodan.py, mitre_attack.py

### 2F. `api/app/services/feeds/mitre_attack.py` L72-78 — `_parse_stix_date()`

- **Category**: STIX/ISO parser with Z→+00:00
- **Input → Output**: `str|None` → `datetime|None`
- **Duplication**: **IDENTICAL to `_parse_iso()`** in cisa_advisories.py

### 2G. `api/app/services/feeds/shodan.py` L157 — inline ISO parse

- **Category**: Inline ISO parse with Z→+00:00
- **Duplication**: **IDENTICAL pattern** to 2E, 2F

### 2H. `api/app/services/feeds/malwarebazaar.py` L72-80 — `_parse_date()`

- **Category**: Multi-format parser
- **Input → Output**: `str|None` → `datetime|None` — tries `%Y-%m-%d %H:%M:%S` then `%Y-%m-%dT%H:%M:%S`
- **Duplication**: Different format set than news.py parser

### 2I. `api/app/services/feeds/virustotal.py` L264-269 — inline epoch → datetime

- **Category**: Unix timestamp conversion
- **Input → Output**: `int(epoch)` → `datetime` via `datetime.fromtimestamp(first_seen, tz=utc)`
- **Duplication**: Unique (epoch-based vs string-based)

---

## 3. IOC Type Detection & Asset Type Mapping

### 3A. `api/app/services/search.py` L14-24 — `IOC_PATTERNS` dict + `detect_ioc_type()`

- **Category**: Regex-based IOC type auto-detection
- **Input → Output**: `str(query)` → `str|None` from patterns: CVE, IP, domain, URL, hash_md5/sha1/sha256, email
- **Dependencies**: Used by `global_search()` for query routing
- **Duplication**: **PARALLEL IMPLEMENTATION** with `_extract_ioc_values()` in tasks.py

### 3B. `worker/tasks.py` L520-600 — `_extract_ioc_values()`

- **Category**: Regex-based IOC extraction from text
- **Input → Output**: `dict(intel_item)` → `list[dict]` of extracted IOCs — source-specific extractors (AbuseIPDB→IP, URLhaus→URL, OTX→multiple) + generic regex fallback
- **Dependencies**: Used in ingestion pipeline for IOC table population
- **Duplication**: Overlapping regex patterns with search.py `IOC_PATTERNS` but different purpose (extraction vs detection)

### 3C. `api/app/services/feeds/threatfox.py` L21-28 — `_TYPE_MAP`

- **Category**: Mapping (ThreatFox ioc_type → AssetType)
- **Input → Output**: `"ip:port"→"ip"`, `"domain"→"domain"`, `"url"→"url"`, `"md5_hash"→"hash_md5"`, `"sha256_hash"→"hash_sha256"`
- **Dependencies**: Used in `normalize()`
- **Duplication**: Feed-specific, but the target values must match `AssetType` enum

### 3D. `api/app/services/feeds/exploitdb.py` L109-121 — `_classify_exploit()` asset_type

- **Category**: Keyword-based asset type detection
- **Input → Output**: `str(combined)` → `"url"` if web keywords, else `"cve"`
- **Duplication**: Simple, feed-specific

---

## 4. Category / Enum Normalization

### 4A. `worker/tasks.py` L1500-1530 — `_VALID_NEWS_CATEGORIES` set

- **Category**: Validation set (11 values)
- **Values**: `active_threats`, `exploited_vulnerabilities`, `ransomware_breaches`, `nation_state`, `cloud_identity`, `ot_ics`, `security_research`, `tools_technology`, `policy_regulation`, **`general_news`**, **`geopolitical_cyber`**
- **Duplication**: ⚠️ **DUAL SOURCE-OF-TRUTH** — see §18

### 4B. `worker/tasks.py` L1532-1568 — `_CATEGORY_FALLBACK_MAP` dict (27 entries)

- **Category**: Mapping (AI-hallucinated category → valid category)
- **Input → Output**: 27 hallucinated strings → valid category, e.g. `"general"→"general_news"`, `"geopolitical"→"geopolitical_cyber"`, `"vulnerability"→"exploited_vulnerabilities"`, `"apt"→"nation_state"`, etc.
- **Dependencies**: Used by `_normalize_category()` L1570

### 4C. `worker/tasks.py` L1570-1582 — `_normalize_category(raw, fallback)`

- **Category**: Normalization function
- **Input → Output**: `str(raw_category)` → `str(valid_category)` — lowered, stripped, checked against `_VALID_NEWS_CATEGORIES`, then `_CATEGORY_FALLBACK_MAP`, then returns `fallback`
- **Dependencies**: Called by `enrich_news_batch()` L1590 and `re_enrich_fallback_news()` L1700

### 4D. `api/app/services/news.py` L300-318 — `_detect_category()`

- **Category**: Keyword-based category pre-detection (before AI)
- **Input → Output**: `str(title, desc)` → `str` from 9 categories (missing `general_news`, `geopolitical_cyber`)
- **Dependencies**: Used as pre-enrichment heuristic
- **Duplication**: ⚠️ Only 9 categories vs 11 in tasks.py

### 4E. `api/app/schemas/__init__.py` L589-598 — `NewsCategory` enum

- **Category**: Pydantic enum definition (9 values)
- **Values**: Missing `general_news` and `geopolitical_cyber`
- **Duplication**: ⚠️ **DUAL SOURCE-OF-TRUTH** — see §18

### 4F. `api/app/models/models.py` L336 — SAEnum for news_items.category

- **Category**: SQLAlchemy enum (11 values)
- **Values**: Includes `general_news` and `geopolitical_cyber`
- **Duplication**: ⚠️ Matches tasks.py but NOT schemas/__init__.py

### 4G. `api/app/prompts.py` L274 — NEWS_ENRICHMENT_PROMPT category list

- **Category**: AI prompt enum list (11 values)
- **Values**: Includes all 11 categories
- **Duplication**: Matches tasks.py and models.py

---

## 5. String Cleaning & Text Normalization

### 5A. `api/app/services/news.py` L160-166 — `_strip_html()`

- **Category**: HTML stripping + whitespace normalization
- **Input → Output**: `str(html)` → `str(plain_text)` — regex tag removal, `html.unescape()`, whitespace collapse, cap at 12000 chars
- **Dependencies**: Used in RSS feed parsing
- **Duplication**: None — single implementation

### 5B. `api/app/services/news.py` L171-215 — `_headline_tokens()`

- **Category**: Text tokenizer for dedup comparison
- **Input → Output**: `str(headline)` → `set[str]` — lowercase, remove punctuation, remove 40 stop words, simple suffix stripping (22 patterns), CVE/number preservation, min stem length 3
- **Dependencies**: Used by `_headline_similarity()`
- **Duplication**: None — custom NLP-lite tokenizer

### 5C. `api/app/services/feeds/threatfox.py` L80-84 — `_clean_ioc_value()`

- **Category**: IOC value cleaning
- **Input → Output**: `str("ip:port")` → `str("ip")` — strips port from ip:port format
- **Dependencies**: Used in `normalize()`
- **Duplication**: Feed-specific

### 5D. `api/app/services/feeds/malwarebazaar.py` — inline `.strip().strip('"')`

- **Category**: CSV field cleaning
- **Input → Output**: Strip whitespace and quotes from CSV fields
- **Dependencies**: Used throughout `normalize()` for every field
- **Duplication**: **INLINE** — repeated ~10 times in the same function

### 5E. `api/app/services/ai.py` L531-540 — `_strip_json_fences()`

- **Category**: AI output cleaning
- **Input → Output**: `str(ai_response)` → `str(raw_json)` — removes markdown ``` fences and "json" prefix
- **Dependencies**: Used by `chat_completion_json()`
- **Duplication**: None — single implementation

### 5F. `api/app/services/ai.py` L235-243 — `_ensure_chat_url()`

- **Category**: URL normalization
- **Input → Output**: `str(base_url)` → `str(full_url)` — appends `/chat/completions`, handles Gemini `/openai` prefix
- **Dependencies**: Used by `_get_chain_async()`
- **Duplication**: None

---

## 6. Hashing & Deduplication

### 6A. `api/app/services/feeds/base.py` L41-43 — `generate_hash(*parts)`

- **Category**: Deterministic dedup hash
- **Input → Output**: `*str` → `str(sha256_hex)` — pipe-joins parts, SHA-256 digest
- **Dependencies**: Called by EVERY feed connector's `normalize()` for `source_hash` field
- **Duplication**: None — single canonical implementation ✓

### 6B. `api/app/services/news.py` L138-139 — `_hash(text)`

- **Category**: Content hashing for news dedup
- **Input → Output**: `str(text)` → `str(sha256_hex)`
- **Dependencies**: Used for headline dedup in news ingestion
- **Duplication**: **PARALLEL IMPLEMENTATION** — same algorithm as `generate_hash()` but different function

### 6C. `api/app/services/news.py` L218-233 — `_headline_similarity()` + L235 threshold

- **Category**: Similarity-based dedup
- **Input → Output**: `(str, str)` → `float(0.0-1.0)` — Jaccard similarity with CVE boost (floor 0.80 if shared CVE), threshold `0.40`
- **Dependencies**: Used in `ingest_news()` for cross-source dedup
- **Duplication**: **Also exists** in `worker/tasks.py` L1303 — `_headline_similarity()` is imported

### 6D. `worker/tasks.py` L691-720 — `_bulk_store()` source_hash dedup

- **Category**: PostgreSQL `ON CONFLICT DO NOTHING` dedup
- **Input → Output**: Items with `source_hash` → insert or skip
- **Dependencies**: Uses `source_hash` generated by feed connectors
- **Duplication**: Also in `api/app/services/database.py` `upsert_intel_item()` — same pattern

### 6E. `api/app/services/intel_extraction.py` L280-310 — `_dedup_arrays_sync()`

- **Category**: SQL-based array deduplication
- **Input → Output**: PostgreSQL arrays → deduplicated using `array_agg(DISTINCT v) FROM unnest(...)`, also recalculates `source_count`
- **Dependencies**: Called after batch upserts
- **Duplication**: None — handles accumulated duplicates from `array_cat` on conflict

---

## 7. Score Clamping & Numeric Coercion

### 7A. `api/app/services/scoring.py` L73 — score normalization formula

- **Category**: Score normalization
- **Formula**: `(score / total_weight) * 100.0`
- **Output**: Float 0-100

### 7B. `api/app/services/scoring.py` L81 — final clamp

- **Category**: Clamping
- **Input → Output**: `int` → `max(0, min(100, round(final)))` — ensures 0-100 range
- **Dependencies**: End of `compute_risk_score()`
- **Duplication**: Same clamping pattern in worker/tasks.py

### 7C. `worker/tasks.py` L1630-1635 — `relevance_score` clamping

- **Category**: Clamping
- **Input → Output**: AI-returned score → `max(1, min(100, int(score)))` — 1-100 range
- **Dependencies**: Used in `enrich_news_batch()` and `re_enrich_fallback_news()`
- **Duplication**: **DUPLICATED** in both enrichment functions

### 7D. `api/app/services/feeds/shodan.py` L141-142 — confidence clamping

- **Category**: Clamping
- **Input → Output**: `min(int((epss * 70) + (30 if is_kev else 0)), 100)` then floor at 20
- **Duplication**: Custom formula, not shared

### 7E. `api/app/schemas/__init__.py` L67 — Pydantic `confidence` field

- **Category**: Pydantic field validation
- **Input → Output**: `int` with `ge=0, le=100` — Pydantic enforces 0-100
- **Dependencies**: Request/response validation
- **Duplication**: DB CHECK constraint echoes this

### 7F. `api/app/schemas/__init__.py` L766-770 — `round_float_scores` validator

- **Category**: Pydantic `@field_validator`
- **Input → Output**: `float|None` → `round(v, 2)` — rounds CVSS/EPSS floats to 2 decimal places
- **Dependencies**: `VulnerableProductResponse` model

---

## 8. Geographic & Industry Mapping

### 8A. `worker/tasks.py` L788-870 — `_CC_CONTINENT` dict (~200 entries)

- **Category**: Mapping (ISO 3166 country code → continent name)
- **Input → Output**: `"US"→"North America"`, `"CN"→"Asia"`, etc.
- **Dependencies**: Used by `enrich_ips_ipinfo()` L920

### 8B. `worker/tasks.py` L871-920 — `_CC_NAMES` dict (~200 entries)

- **Category**: Mapping (ISO 3166 country code → full country name)
- **Input → Output**: `"US"→"United States"`, `"GB"→"United Kingdom"`, etc.
- **Dependencies**: Used by `enrich_ips_ipinfo()` L920

### 8C. `api/app/services/feeds/mitre_attack.py` L164-180 — `_extract_geo()` with `geo_map`

- **Category**: Keyword-based geo extraction from text
- **Input → Output**: `str(description)` → `list[str]` of country/region names — 16 keyword→label mappings
- **Dependencies**: Used in MITRE ATT&CK `normalize()`
- **Duplication**: Not shared with tasks.py `_CC_*` maps — different approach (text mining vs structured code lookup)

### 8D. `api/app/services/feeds/mitre_attack.py` L183-200 — `_extract_industries()` with `industry_map`

- **Category**: Keyword-based industry extraction from text
- **Input → Output**: `str(description)` → `list[str]` of industry names — 18 keyword→label mappings
- **Dependencies**: Used in MITRE ATT&CK `normalize()`
- **Duplication**: Not shared — could be shared with news enrichment

---

## 9. Product / Vendor Normalization

### 9A. `api/app/services/intel_extraction.py` L644-672 — `_normalize_product_name()`

- **Category**: Product name canonicalization
- **Input → Output**: `str` → `str` — strip whitespace, remove trailing version suffixes (`v1.2`, `10.3.x`, `(2024)`), collapse whitespace, smart title-case (preserve acronyms + hyphenated)
- **Dependencies**: Called by `_extract_products_sync()` L111
- **Duplication**: None — single implementation ✓

### 9B. `api/app/services/intel_extraction.py` L680-710 — `_guess_vendor()`

- **Category**: Product→vendor mapping (40 keyword→vendor pairs)
- **Input → Output**: `str(product_name)` → `str(vendor)|None` — keyword substring match
- **Dependencies**: Called by `_extract_products_sync()`
- **Duplication**: None — single implementation ✓

### 9C. `api/app/services/intel_extraction.py` L38-44 — `_PRODUCT_BLOCKLIST` set

- **Category**: Blocklist validation
- **Values**: 10 junk terms (e.g., "nim", "zig", "unknown product", "web browsers")
- **Dependencies**: Used by `_is_junk_product()` L640

### 9D. `api/app/services/intel_extraction.py` L47-50 — `_PRODUCT_JUNK_PATTERNS` regex

- **Category**: Regex blocklist
- **Pattern**: Matches `(N zero-day`, `(multiple `, `all .+ applications`, `generic`, `various`
- **Dependencies**: Used by `_is_junk_product()`

### 9E. `api/app/services/feeds/exploitdb.py` L133-140 — `_extract_products()`

- **Category**: Product extraction from exploit title
- **Input → Output**: `str(title)` → `list[str]` — regex extracts text before version or dash
- **Duplication**: Feed-specific, no overlap

---

## 10. Campaign / Actor Name Normalization

### 10A. `api/app/services/intel_extraction.py` L675-679 — `_normalise_campaign_name()`

- **Category**: Null normalization
- **Input → Output**: `str|None` → `str|None` — converts `"unknown"`, `"null"`, `"n/a"`, `"none"`, `""`, `"unattributed"` → `None`
- **Dependencies**: Used by `_extract_campaigns_sync()` L194

### 10B. `api/app/services/intel_extraction.py` L53 — `_NULL_CAMPAIGN_NAMES` set

- **Category**: Null name blocklist
- **Values**: `{"unknown", "null", "n/a", "none", "", "unattributed"}`
- **Duplication**: The values `"unknown"`, `"unattributed"`, `"n/a"`, `"none"` are also inline-checked in `_extract_campaigns_sync()` L200 for actor names — **PARTIAL DUPLICATION**

---

## 11. AI Response Parsing & Validation

### 11A. `api/app/services/ai.py` L531-540 — `_strip_json_fences()`

- **Category**: AI output cleaning (markdown code fences)
- (See §5E above)

### 11B. `api/app/services/ai.py` L553-600 — `chat_completion_json()` validation

- **Category**: JSON parse + required key validation + retry with corrective prompt
- **Input → Output**: AI raw text → `dict|None` — strips fences, parses JSON, validates keys, retries once with `JSON_REPAIR_PROMPT`
- **Dependencies**: Used by intel enrichment, news enrichment, report generation

### 11C. `worker/tasks.py` L1590-1660 — `enrich_news_batch()` field extraction

- **Category**: AI response field mapping + validation
- **Input → Output**: `dict(ai_response)` → validated fields with:
  - `category` via `_normalize_category()` (§4C)
  - `relevance_score` clamped 1-100 (§7C)
  - `confidence` validated against `("high", "medium", "low")`
  - `recommended_priority` validated against `("critical", "high", "medium", "low")`
  - Array fields: `tags`, `threat_actors`, `malware_families`, `cves`, `tactics_techniques`, `vulnerable_products`, `targeted_sectors`, `targeted_regions`
- **Duplication**: **DUPLICATED** in `re_enrich_fallback_news()` — see §19

---

## 12. Feed Connector normalize() Methods

Each connector inherits from `BaseFeedConnector` and implements `normalize(raw_items) → list[dict]`.

| Feed | File | Key Transformations |
|------|------|-------------------|
| ThreatFox | `feeds/threatfox.py` | `_TYPE_MAP`, `_SEVERITY_MAP`, `_clean_ioc_value()`, keyword severity boost, comma-split tags |
| AbuseIPDB | `feeds/abuseipdb.py` | Inline abuse_score→severity thresholds, ISO date parse |
| CISA KEV | `feeds/kev.py` | Hardcoded critical severity, ransomware tag detection, exploitability=10.0 |
| NVD | `feeds/nvd.py` | CVSS v3.1→v3.0→v2 cascade, baseSeverity passthrough, CPE product extraction |
| OTX | `feeds/otx.py` | TLP mapping (RED/AMBER/GREEN/WHITE), indicator-count severity, IOC type detection |
| URLhaus | `feeds/urlhaus.py` | Status-based severity (online→high), CSV tag parsing |
| Shodan | `feeds/shodan.py` | `_normalize_cvedb()`: CVSS severity + KEV/EPSS boost, confidence formula; `_normalize_host()`: vuln-count severity |
| VirusTotal | `feeds/virustotal.py` | Detection ratio severity, type-specific field mapping (file/ip/domain/url), epoch→datetime |
| ExploitDB | `feeds/exploitdb.py` | RSS XML parse, `_classify_exploit()`, `_extract_cves()`, `_extract_products()` |
| GitHub Advisories | `feeds/cisa_advisories.py` | `_map_severity()`, `_extract_cves()`, `_extract_products()`, CWE extraction |
| MITRE ATT&CK | `feeds/mitre_attack.py` | STIX object filtering, `_severity_from_description()`, `_extract_geo()`, `_extract_industries()`, `_extract_cves()` |
| MalwareBazaar | `feeds/malwarebazaar.py` | CSV parsing, `_severity_from_tags()`, quote stripping |

**Common output schema**: All produce dicts matching the `intel_items` table with: `id`, `title`, `summary`, `description`, `published_at`, `ingested_at`, `updated_at`, `severity`, `risk_score`, `confidence`, `source_name`, `source_url`, `source_reliability`, `source_ref`, `feed_type`, `asset_type`, `tlp`, `tags`, `geo`, `industries`, `cve_ids`, `affected_products`, `related_ioc_count`, `is_kev`, `exploit_available`, `exploitability_score`, `source_hash`.

---

## 13. MITRE ATT&CK Keyword Mapping

### 13A. `api/app/services/mitre.py` L63-450+ — `KEYWORD_TECHNIQUE_MAP` dict

- **Category**: Massive keyword→technique mapping (~300+ entries)
- **Input → Output**: `str(keyword)` → `list[str(technique_ids)]`
- **Sections**: Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, C2, Exfiltration, Impact, Vulnerability Types, Malware Delivery
- **Dependencies**: Used by worker task `map_intel_to_attack()` (referenced in admin.py remap endpoint)
- **Duplication**: None — single canonical mapping ✓

### 13B. `api/app/services/mitre.py` L28-55 — `TACTIC_ORDER` + `TACTIC_LABELS`

- **Category**: Tactic metadata (14 kill-chain phases)
- **Input → Output**: Slug → display label
- **Dependencies**: Used by technique detail views
- **Duplication**: None ✓

---

## 14. Pydantic Schema Validation

### 14A. `api/app/schemas/__init__.py` — Enum definitions

| Enum | Line | Values | DB Equivalent |
|------|------|--------|---------------|
| `SeverityLevel` | L13-21 | 6 values | `severity_level` ✓ match |
| `FeedType` | L24-33 | 7 values | `feed_type` ✓ match |
| `AssetType` | L36-47 | 10 values | `asset_type` ✓ match |
| `TLPLevel` | L50-56 | 5 values | `tlp_level` ✓ match |
| `UserRole` | L59-62 | 3 values | `user_role` ✓ match |
| `NewsCategory` | L589-598 | **9 values** | `news_category` **⚠️ 9 in DB base schema, 11 in code** |
| `ConfidenceLevel` | L601-604 | 3 values | `confidence_level` ✓ match |
| `ReportStatus` | L474 | draft, published, archived | custom ✓ |
| `ReportType` | L484 | 6 types | custom ✓ |
| `CaseType/Status/Priority` | L830-870 | multiple | custom ✓ |

### 14B. `api/app/schemas/__init__.py` — Field-level validators

| Field | Line | Validation | Type |
|-------|------|-----------|------|
| `confidence` | L67 | `ge=0, le=100` | Pydantic |
| `risk_score` | L66 | `ge=0, le=100` | Pydantic |
| `source_reliability` | L68 | `ge=0, le=100` | Pydantic |
| `sort_by` | L138 | `pattern=regex` | Pydantic |
| `ScoringWeights.*` | L245 | `ge=0, le=100` | Pydantic |
| `round_float_scores` | L766-770 | `@field_validator` round to 2dp | Pydantic |

---

## 15. SQL / DB-Level Constraints

### From `db/schema.sql`:

| Table | Column | Constraint |
|-------|--------|-----------|
| `intel_items` | `risk_score` | `CHECK (risk_score >= 0 AND risk_score <= 100)` |
| `intel_items` | `confidence` | `CHECK (confidence >= 0 AND confidence <= 100)` |
| `intel_items` | `source_reliability` | `CHECK (source_reliability >= 0 AND source_reliability <= 100)` |
| `intel_items` | `severity` | `severity_level` enum type |
| `intel_items` | `feed_type` | `feed_type` enum type |
| `intel_items` | `asset_type` | `asset_type` enum type |
| `intel_items` | `tlp` | `tlp_level` enum type |
| `intel_items` | `source_hash` | `UNIQUE` index for dedup |
| `iocs` | `risk_score` | `CHECK (risk_score >= 0 AND risk_score <= 100)` |
| `iocs` | `(value, ioc_type)` | `UNIQUE` compound index |
| `news_items` | `category` | `news_category` enum type |

---

## 16. OpenSearch Field Mapping

### `opensearch/intel-items-mapping.json`

- Keyword fields: `severity`, `feed_type`, `asset_type`, `source_name`, `source_ref`, `tlp`, `tags`, `cve_ids`, `affected_products`, `geo`, `industries`
- Text fields with analyzers: `title`, `summary`, `description`
- `title.keyword` sub-field for alphabetic sorting

### `api/app/services/search.py` L140-290 — `_build_query()`

- Type-specific query routing based on `detected_type`:
  - CVE → `term` on `cve_ids` + `match_phrase` on title/description
  - IP → `term` on `source_ref` + `match_phrase`
  - Hash → `term` on `source_ref` (lowercased)
  - Generic → `multi_match` with fuzziness + `term` on keyword fields

### `worker/tasks.py` L760-770 — `_prepare_os_docs()`

- Field mapping from ingestion dict to OpenSearch document format with default values

---

## 17. Export Transformations

### 17A. `api/app/services/export.py` — `SEVERITY_COLORS` dict

- **Category**: Mapping (severity → hex color)
- **Input → Output**: `"critical"→"FF0000"`, `"high"→"FF6600"`, `"medium"→"FFCC00"`, `"low"→"33CC33"`, `"info"→"3399FF"`, `"unknown"→"CCCCCC"`
- **Dependencies**: Used for Excel cell coloring

### 17B. `api/app/services/export.py` — `export_to_excel()`

- **Category**: Field mapping (dict → Excel columns)
- **Input → Output**: `list[dict]` → `io.BytesIO` — maps 22 fields to columns, joins arrays with comma, formats datetimes, converts booleans to "Yes"/"No"

### 17C. `api/app/routes/dashboard.py` L47-55 — `_feed_to_source` mapping

- **Category**: Feed name → display source name
- **Input → Output**: `"abuseipdb"→"AbuseIPDB"`, `"cisa_kev"→"CISA KEV"`, etc.
- **Dependencies**: Used for dashboard feed status display

---

## 18. Dual Source-of-Truth Issues

### 18A. ⚠️ **CRITICAL: `NewsCategory` — 3-way mismatch**

| Location | Count | Has `general_news`? | Has `geopolitical_cyber`? |
|----------|-------|-------------------|--------------------------|
| `db/schema.sql` `news_category` enum | **9** | ❌ | ❌ |
| `api/app/schemas/__init__.py` `NewsCategory` | **9** | ❌ | ❌ |
| `api/app/models/models.py` SQLAlchemy enum | **11** | ✅ | ✅ |
| `worker/tasks.py` `_VALID_NEWS_CATEGORIES` | **11** | ✅ | ✅ |
| `api/app/prompts.py` AI prompt | **11** | ✅ | ✅ |
| `api/app/services/news.py` `_detect_category()` | **9** | ❌ | ❌ |
| `ui/src/types/index.ts` | **11** | ✅ | ✅ |
| UI components (news pages) | **11** | ✅ | ✅ |

**Impact**: The AI prompt instructs the model to return `general_news` or `geopolitical_cyber`, the worker validates and accepts them, the SQLAlchemy model accepts them, the UI displays them — but the **base DB schema** only has 9 values. A migration likely added the 2 extra values. The Pydantic `NewsCategory` enum and `_detect_category()` are out of date.

**Fix**: Add `general_news` and `geopolitical_cyber` to:
1. `api/app/schemas/__init__.py` `NewsCategory` enum
2. `api/app/services/news.py` `_detect_category()` function
3. Verify DB migration added the values to the `news_category` enum

### 18B. ⚠️ Severity mapping values — consistent but scattered

Six different severity string sets exist:
- `scoring.py` `SEVERITY_SCORES`: critical, high, medium, low, info, unknown
- `intel_extraction.py` `_SEVERITY_RANK`: critical, high, medium, low, info, unknown
- `export.py` `SEVERITY_COLORS`: critical, high, medium, low, info, unknown
- `db/schema.sql` `severity_level` enum: critical, high, medium, low, info, unknown
- `schemas/__init__.py` `SeverityLevel` enum: critical, high, medium, low, info, unknown
- Feed connectors: Only produce critical, high, medium, low (never info or unknown)

All are **consistent** in values, but the mapping dicts could be consolidated (see §21).

### 18C. Admin `valid_feeds` list

- `api/app/routes/admin.py` L97: `valid_feeds = ["nvd", "cisa_kev", "urlhaus", "abuseipdb", "otx", "virustotal", "shodan"]`
- Missing: `threatfox`, `exploitdb`, `cisa_advisories`, `mitre_attack`, `malwarebazaar`
- Not critical (only affects manual trigger), but should stay in sync

---

## 19. Duplication / Code-Clone Issues

### 19A. ⚠️ **`enrich_news_batch()` vs `re_enrich_fallback_news()`**

- **Files**: `worker/tasks.py` L1590-1660 vs L1700-1800
- **Issue**: ~30 lines of identical field-mapping code duplicated verbatim:
  - `_normalize_category()` call
  - `relevance_score` clamping
  - `confidence` validation
  - `recommended_priority` validation
  - Array field extraction (tags, threat_actors, malware_families, cves, etc.)
- **Fix**: Extract a `_apply_enrichment_fields(item, ai_data, fallback_category)` helper

### 19B. Date parser duplication (6+ implementations)

- `news.py` `_parse_pub_date()` — multi-format (RFC 2822 + ISO + %Y-%m-%d)
- `exploitdb.py` `_parse_rss_date()` — RFC 2822 only
- `cisa_advisories.py` `_parse_iso()` — ISO with Z replacement
- `mitre_attack.py` `_parse_stix_date()` — identical to above
- `shodan.py` inline ISO parse — identical to above
- `malwarebazaar.py` `_parse_date()` — two strptime formats
- `scoring.py` `_compute_freshness()` — ISO parse
- **Fix**: Create `BaseFeedConnector.parse_date()` or a shared `utils.parse_date()` that handles all formats

### 19C. IOC regex patterns

- `api/app/services/search.py` `IOC_PATTERNS` — 8 regex patterns for type detection
- `worker/tasks.py` `_extract_ioc_values()` — similar regex patterns for extraction
- Different purposes but could share the compiled regex constants

### 19D. Severity keyword matching (ExploitDB vs MITRE ATT&CK)

- `exploitdb.py` `_classify_exploit()` — keyword→severity
- `mitre_attack.py` `_severity_from_description()` — keyword→severity
- Similar approach, different keyword sets — potential for shared utility

---

## 20. Inline Validation → Extract to Functions

### 20A. AbuseIPDB abuse_score→severity thresholds

- **Location**: `feeds/abuseipdb.py` L130-135 (inline in normalize())
- **Recommendation**: Extract to `_abuse_score_to_severity(score: int) → str`

### 20B. OTX indicator-count→severity

- **Location**: `feeds/otx.py` ~L130 (inline in normalize())
- **Recommendation**: Extract to `_count_severity(count: int, thresholds: tuple) → str`

### 20C. URLhaus status→severity

- **Location**: `feeds/urlhaus.py` ~L95 (inline in normalize())
- **Recommendation**: Simple enough to stay inline

### 20D. MalwareBazaar CSV field stripping

- **Location**: `feeds/malwarebazaar.py` — `.strip().strip('"')` repeated ~10 times
- **Recommendation**: Extract to `_clean_csv(val: str) → str`

### 20E. Actor name null-check inline

- **Location**: `intel_extraction.py` L200 — `if actor.lower() in ("unknown", "unattributed", "n/a", "none")`
- **Recommendation**: Use `_NULL_CAMPAIGN_NAMES` set that's already defined at L53

---

## 21. Reuse Opportunities

### 21A. Shared `parse_date(date_str)` utility

Create a single multi-format date parser that handles:
- RFC 2822 (RSS feeds)
- ISO 8601 with/without Z suffix
- STIX format
- `%Y-%m-%d %H:%M:%S` (CSV exports)
- `%Y-%m-%d` (simple dates)
- Unix epoch (integer timestamps)

All 7+ date parsers could be replaced.

### 21B. Shared `SEVERITY_RANK` constant

Merge `scoring.py` `SEVERITY_SCORES` and `intel_extraction.py` `_SEVERITY_RANK` into one:
```python
SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1, "unknown": 0}
```

### 21C. Shared `threshold_severity(value, thresholds)` function

Many feeds use the pattern: `if x >= T1: "critical" elif x >= T2: "high" ...`
Could be generalized:
```python
def threshold_severity(value: float, thresholds: list[tuple[float, str]]) -> str:
    for threshold, severity in thresholds:
        if value >= threshold:
            return severity
    return "low"
```

### 21D. `_apply_enrichment_fields()` for news enrichment

Extract the ~30 lines of identical AI→DB field mapping from `enrich_news_batch()` and `re_enrich_fallback_news()`.

### 21E. `BaseFeedConnector.parse_iso()` method

Add to the base class since 6 connectors implement their own ISO parser.

### 21F. Consolidated `NewsCategory` definition

Define the canonical 11-value category list in ONE place (e.g., `schemas/__init__.py`) and import everywhere: prompts, tasks.py validation, news.py detection, models.py.

---

## Summary Statistics

| Category | Instance Count |
|----------|---------------|
| Severity mappings | 16 |
| Date/time parsers | 9 |
| IOC type detection | 4 |
| Category/enum normalization | 7 |
| String cleaning functions | 6 |
| Hash/dedup mechanisms | 5 |
| Score clamping instances | 6 |
| Geo/industry mappings | 4 |
| Product/vendor normalization | 5 |
| Campaign/actor normalization | 2 |
| AI response validation | 3 |
| Feed normalize() methods | 12 |
| MITRE ATT&CK mappings | 2 |
| Pydantic validators | 6+ |
| DB-level constraints | 10+ |
| **Total identified instances** | **~97** |

| Issue Type | Count |
|-----------|-------|
| Dual source-of-truth | 3 |
| Code-clone duplication | 4 |
| Inline → extract candidates | 5 |
| Reuse opportunities | 6 |
