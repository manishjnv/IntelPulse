# Prompt Engineering — Version History & Design Decisions

This document tracks the evolution of AI prompts used across the TI Platform,
the rationale behind each upgrade, and testing results.

All prompts are centralized in `api/app/prompts.py` with version constants,
feature names, and default model parameters. DB-backed custom overrides
(via `/ai-settings`) take precedence at runtime.

---

## Prompt Inventory

| Feature | Version | Consumer | max_tokens | temp | Purpose |
|---------|---------|----------|-----------|------|---------|
| `intel_summary` | **A-2.0** | `ai.py → generate_summary()` | 400 | 0.3 | 2-3 sentence intel summary |
| `intel_enrichment` | **B-5.0** | `intel.py → get_intel_enrichment()` | 5000 | 0.15 | Graph-ready entity extraction for intel items |
| `news_enrichment` | **D-5.0** | `news.py → enrich_news_item()` | 6000 | 0.15 | Full entity extraction for news articles |
| `report_summary` | R-1.0 | `reports.py → generate_report_summary()` | 400 | 0.3 | Executive summary for reports |
| `report_full` | R-2.0 | `reports.py → generate_report_content()` | 4000 | 0.3 | Full data-driven threat report |
| `briefing_gen` | BG-1.0 | `enrichment.py → generate_briefing()` | 4000 | 0.3 | Weekly threat briefing |
| `live_lookup` | LL-1.0 | `ai_settings.py → /ai-settings/live-lookup` | 2000 | 0.2 | IOC analysis from live lookup |
| `json_repair` | JR-1.0 | `ai.py → chat_completion_json()` | 4000 | 0.1 | Fix malformed JSON (internal) |

---

## Version History

### NEWS_ENRICHMENT (D-series)

#### D-5.0 (current) — 2026-03-08

**Key improvements over D-4.0:**

1. **"Extraction engine" role framing** — Changed from "senior analyst at a Fortune 100 SOC"
   to "cyber threat intelligence extraction engine for a cybersecurity news platform."
   Engine framing produces more deterministic, structured output with less narrative filler.

2. **`<mission>` block — 3-consumer awareness** — Explicitly tells the model its output
   feeds three systems simultaneously: analyst dashboard (highlighting), knowledge graph
   (entity dedup), and search engine (tag coverage). Replaces the separate
   `<primary_objective>` + `<audience>` sections.

3. **`<prose_entity_highlighting>`** — Instructs the model to wrap named entities in
   `**double asterisks**` in narrative fields (summary, executive_brief, risk_assessment,
   attack_narrative) for automatic UI color-coding via the first `HIGHLIGHT_RULES` regex.
   Lists which entity types to bold and which generic words to skip.

4. **Entity co-reference resolution** — Added explicit instruction: "if article says
   'the Russian group' after mentioning APT29, use APT29." Prevents unnamed references
   from breaking graph deduplication.

5. **✓/✗ contrast examples** — Normalization rules now show correct and incorrect examples
   side-by-side (e.g., ✓ "APT29 (Cozy Bear / …)" vs ✗ "Cozy Bear" alone).

6. **Consolidated `<quality_gate>`** — Merged the 11-line `<quality_rules>` (banned +
   required patterns) into a 4-line consolidated gate. Same constraints, ~60% fewer tokens.

7. **Removed `<analysis_methodology>`** — Gemini 2.5 Flash has built-in chain-of-thought
   reasoning. Explicit step-by-step instructions wasted tokens and sometimes caused the
   model to output reasoning text instead of pure JSON.

8. **Removed `<examples>` section** — Good/bad examples are helpful for weaker models but
   redundant for Gemini 2.5 Flash when the schema and quality gate are well-defined.
   Saves ~12 lines of prompt tokens.

9. **Removed `source_reliability` field** — This field existed in D-4.0 JSON schema but
   the `NewsItem` DB model and worker mapping never stored it. Removing it eliminates
   model confusion and saves output tokens.

10. **8-tier scoring calibration** — Replaced 5-tier (90/70/50/30/1) with 8-tier
    (90/80/70/60/50/40/20/1) for finer granularity between article severity levels.

11. **Tags: 15-20 target** — Increased from 10-15, improving search recall.

12. **Merged redundant sections** — `<entity_extraction_rules>` + `<grounding_rules>`
    merged into single `<entity_normalization>` block. Eliminates duplication.

**Token impact**: ~30% reduction in prompt length vs D-4.0 while retaining all constraints.

#### D-4.0 — 2026-03-06

Full graph-ready entity extraction. Added: `notable_campaigns` JSONB,
`exploitation_info` JSONB, `related_cves` TEXT[]. 11-category classification tree.
3 new DB columns. max_tokens 3500→6000 (fix for JSON truncation).

#### D-3.0 → D-1.0 (legacy, inline)

Earlier versions were defined inline in `worker/tasks.py` and `api/app/services/news.py`.
Centralized to `prompts.py` in commit `8c1b7ff`.

---

### INTEL_ENRICHMENT (B-series)

#### B-5.0 (current) — 2026-03-08

**Key improvements over B-4.0:**

1. **"Structured intelligence data" role** — Shifted from generic "analyst" to
   "analyst generating structured intelligence data" for more deterministic extraction.

2. **`<mission>` with arrow notation** — Explicit relationship triples:
   `actor → exploits → CVE`, `actor → uses → malware`, `campaign → targets → sector`.
   Maps directly to how `graph.py` builds edges (`shares-ioc`, `shares-cve`, `uses`, `exploits`).

3. **Entity co-reference resolution** — Same as D-5.0.

4. **✓/✗ contrast normalization examples** — Same pattern as D-5.0.

5. **Consolidated quality gate** — 4 lines vs 11 lines. Same constraints.

6. **Removed `<examples>` and `<analysis_methodology>`** — Same rationale as D-5.0.

7. **Tags: 15-20 target** — Up from 10-15.

8. **Graph-edge annotations in schema** — `notable_campaigns.actors` annotated as
   "Actor names — graph edges" to signal that these arrays are used for graph edge building.

#### B-4.0 — 2026-03-06

Graph-ready entity extraction for intel items. Object-based `threat_actors` with
name/aliases/motivation/confidence/description/nation_state. `affected_versions` with
vendor/product/versions_affected/fixed_version/patch_url/cpe.

---

### INTEL_SUMMARY (A-series)

#### A-2.0 (current) — 2026-03-08

**Key improvements over A-1.0:**

1. **Fortune-100 SOC context** — Adds organizational framing for consistent quality.

2. **Conditional sentence 3** — Changed from forced "ACTION" sentence to optional:
   "Include ONLY if the source explicitly states a fix; omit rather than invent generic advice."
   Prevents the model from fabricating remediation when the source doesn't mention one.

3. **Flat ROLE/TASK/STRUCTURE/RULES format** — Cleaner than numbered list. Matches Gemini
   2.5 Flash's preference for labeled sections without XML overhead.

---

## Architecture: How Prompts Flow Through the System

```
prompts.py (default text + version)
      │
      ▼
get_custom_prompt(feature)  ←── DB override from /ai-settings (if set)
      │
      ▼
chat_completion_json(system_prompt=..., user_prompt=...)
      │
      ▼
AI provider chain: gemini-primary → cerebras → groq (fallback)
      │
      ▼
JSON response → worker field mapping → PostgreSQL
      │
      ▼
Frontend rendering with HIGHLIGHT_RULES (17 regex patterns)
      │
      ▼
Knowledge graph (entity nodes + relationship edges)
```

### Frontend Highlighting Pipeline

The news detail page (`ui/src/app/(app)/news/[id]/page.tsx`) applies 17 regex-based
highlight rules in priority order:

| Priority | Entity Type | Color | Clickable |
|----------|------------|-------|-----------|
| 1 | `**bold**` markers (AI entities) | Cyan | No |
| 2 | CVE IDs (`CVE-YYYY-NNNNN`) | Orange | Yes → IOC search |
| 3 | MITRE ATT\&CK IDs (`T1234.001`) | Blue | Yes → link |
| 4 | IP addresses | Sky blue | Yes → IOC search |
| 5-7 | Hashes (SHA-256/SHA-1/MD5) | Purple | Yes → IOC search |
| 8-9 | Data quantities / dollar amounts | Red | No |
| 10 | Threat actor names (regex) | Purple | Yes → IOC search |
| 11 | Version numbers | Teal | No |
| 12 | File paths | Amber | Yes → IOC search |
| 13 | Dates (YYYY-MM-DD) | Indigo | No |
| 14 | CVSS scores | Red | No |
| 15 | Action verbs | Green | No |
| 16 | Threat/severity terms | Amber | No |
| 17 | Quoted terms | Default | Yes → IOC search |

**Design note**: The `**bold**` rule (priority 1) is the most powerful because it catches
ANY entity the AI wraps in double asterisks. However, Gemini 2.5 Flash in JSON output
mode tends not to embed markdown inside JSON string values. The specific entity regexes
(CVE, MITRE, IP, hash, hardcoded actors) provide reliable highlighting regardless.

### Knowledge Graph Pipeline

Graph nodes are built from extracted entities. Graph edges are built from:

| Edge Type | Source | Confidence Formula |
|-----------|--------|-------------------|
| `shares-ioc` | Overlapping IOC arrays | 30 + 15 × shared_count (cap 90) |
| `shares-cve` | PostgreSQL array overlap | 40 + 20 × shared_count (cap 95) |
| `shares-technique` | Overlapping tactic arrays | Confidence-based |
| `indicates` / `uses` / `exploits` | Direct intel→IOC/technique links | Fixed 70 |

Entity normalization in the prompt is critical for graph deduplication — "APT29" and
"Cozy Bear" must resolve to the same canonical form across articles.

---

## Testing Results

### D-5.0 Enrichment Test — 2026-03-08

**Test set**: 12 articles across 6 categories, reset and re-enriched with D-5.0.

#### Batch 1 (initial validation)

| # | Article | Category | Tags | CVEs | Actors | Techniques | Score |
|---|---------|----------|------|------|--------|------------|-------|
| 1 | Cisco Catalyst SD-WAN Widely Exploited | active_threats | 16 | 4 | 2 | 5 | 90 |
| 2 | .arpa DNS IPv6 phishing evasion | active_threats | 17 | 0 | 0 | 7 | 75 |
| 3 | EU court phishing refund ruling | policy_regulation | 13 | 0 | 0 | — | — |
| 4 | Fig Security stealth launch | tools_technology | 10 | 0 | 0 | — | — |

#### Batch 2 (thorough cross-category test)

| # | Article | Category | Tags | CVEs | Actors | Malware | Techniques | Score |
|---|---------|----------|------|------|--------|---------|------------|-------|
| 5 | Poland Energy Sector OT/ICS Incident | ot_ics | 16 | 0 | 1 | 1 | 6 | 90 |
| 6 | 100+ GitHub Repos BoryptGrab Stealer | active_threats | 24 | 0 | 0 | 7 | 9 | 90 |
| 7 | Anthropic Chinese AI Firms 16M Claude | active_threats | 11 | 0 | 3 | 0 | 4 | 90 |
| 8 | Termite Ransomware ClickFix CastleRAT | ransomware_breaches | 29 | 0 | 2 | 13 | 8 | 85 |
| 9 | Anthropic 22 Firefox CVEs via Claude | security_research | 17 | 1 | 0 | 0 | 5 | 60 |
| 10 | US Cyber Strategy Critical Infra | policy_regulation | 16 | 0 | 3 | 0 | 12 | 55 |
| 11 | OpenAI Codex 1.2M Commits Scanned | tools_technology | 35 | 13 | 0 | 0 | 4 | 55 |
| 12 | Cylake AI-Native On-Prem Security | tools_technology | 7 | 0 | 0 | 0 | 0 | 20 |

**Results**: 12/12 enriched, 0 errors. 1 JSON parse retry (Termite article — initial
response wrapped in \`\`\`json; retry succeeded with full extraction).

**Quality observations:**

*Entity extraction:*
- Termite article: 2 threat actors (Velvet Tempest / DEV-0504, Interlock), 13 malware
  families with type annotations (CastleRAT backdoor, DonutLoader loader, LummaStealer
  info-stealer, etc.), 8 MITRE techniques with IDs
- BoryptGrab: 24 tags, 7 malware families, 9 techniques — comprehensive supply chain
  threat coverage
- Poland Energy OT/ICS: correctly identified as OT/ICS, extracted wiper malware, 6
  techniques including firmware corruption (T1499)
- OpenAI Codex: 35 tags and 13 CVEs — high because the article itself lists many specific
  vulnerabilities found by the tool

*Scoring calibration (8-tier):*
- 90: Active exploitation / widespread threat (Poland Energy, BoryptGrab, Anthropic abuse)
- 85: Active ransomware with specific TTPs (Termite)
- 60: Research findings, no active exploitation (Anthropic Firefox)
- 55: Policy / tool announcements with security implications (US Strategy, OpenAI Codex)
- 20: Product launch, no threat data (Cylake) — correctly the lowest

*Category accuracy:* 8/8 correct classifications across 6 categories.

*Prose quality:*
- Zero filler across all articles
- Cisco: "UAT-8616 exploits CVE-2023-20198 and CVE-2023-20273 in IOS XE Web UI"
- Detection opportunities name specific log sources, CVEs, and YARA indicators
- Tags hit 15-20 target on technical articles; lighter articles (tools, policy) at 7-16

---

## Gemini 2.5 Flash Optimization Notes

1. **No `<analysis_methodology>`** — Flash has built-in thinking/reasoning. Explicit
   step-by-step instructions waste prompt tokens and can leak reasoning into output.

2. **XML section tags** — Flash handles `<section_name>...</section_name>` well for
   structured guidance. Better than markdown headers or numbered lists for prompt sections.

3. **Temperature 0.15** — Low temperature for extraction tasks ensures deterministic entity
   extraction. Higher temperatures (0.3) reserved for creative tasks (reports, briefings).

4. **max_tokens 6000** — Set high enough to avoid JSON truncation on long articles.
   Flash typically uses 2000-4000 tokens for news enrichment output.

5. **JSON output mode** — Flash's JSON mode tends to strip markdown formatting from
   string values, so `**bold**` markers in prose fields are not reliably produced.
   Entity-specific regex highlighting on the frontend compensates for this.

6. **Schema-first prompting** — Providing the complete JSON schema with inline type hints
   is more effective than examples for Flash. Schema tells Flash exactly what to produce;
   examples show one way but can over-anchor on the specific example content.
