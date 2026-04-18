# IntelPulse — Changelog

Running log of notable changes, grouped by date then theme. Every entry
references the commit SHAs that landed the work so you can jump straight
to the diff. Production URL: [https://intelpulse.tech/](https://intelpulse.tech/).

---

## 2026-04-17 — the marathon session

Full-stack push: three security Criticals, multi-agent Bedrock wired
end-to-end, tiered per-feature model routing, AI Configuration page
rebuilt, five major enhancements to the Investigate relationship graph,
deploy pipeline time cut ~60%, git history cleaned, and a long tail of
operational fixes. Site went from "broken AI Configuration panel,
null IOC analyses, 2m30s deploys" to "live-verified end-to-end" in one
sitting.

### 1. Security hardening

Three audit residuals from the 2026-04-17 security audit shipped and
verified live against production.

#### SSRF URL allowlist — `f588c30`

- New [`api/app/core/url_validation.py`](../api/app/core/url_validation.py)
  with `validate_outbound_url()`. Blocks RFC 1918 private ranges,
  loopback (`127/8`, `::1`), link-local (`169.254/16` — includes AWS
  IMDS `169.254.169.254`), carrier-grade NAT (`100.64/10`),
  multicast / reserved / unspecified, IPv4-mapped IPv6 embeddings, and
  well-known metadata hostnames (`localhost`, `metadata.google.internal`,
  `instance-data`, ...). Non-`http`/`https` schemes (`file://`, `ftp://`,
  `javascript:`, `data:`) rejected outright.
- Applied at three call sites that accept user-supplied URLs:
  - `POST /ai-settings/test-provider` → `HTTPException(400,
    "Refusing to contact unsafe URL: ...")`
  - `webhook.deliver_webhook_sync` / `deliver_webhook_async` → returns
    `{success: False, error: "Refused unsafe URL: ..."}` so the rule
    dispatcher keeps shape.
- 46 validator unit tests + 10 webhook integration tests. DNS mocked
  for test-time determinism.
- Known TOCTOU: validator resolves DNS, then `httpx` re-resolves, so an
  attacker with authoritative DNS could still race. Pinning the
  resolved IP into the HTTP client is a follow-up.
- **Live-verified on prod**: `POST /api/v1/ai-settings/test-provider`
  with `http://169.254.169.254/`, `https://10.0.0.1/`,
  `https://localhost:8000/` all returned 400 with distinct error
  messages (scheme / private-IP / blocked-hostname).

#### XSS — briefings print template — `7b6f8bb`

- New [`ui/src/lib/safe-html.ts`](../ui/src/lib/safe-html.ts) provides
  `escapeHtml()` (7-char entity map) and `safeUrl()` (allows only
  `http:`, `https:`, `mailto:` and relative refs; collapses
  `javascript:`/`data:`/`vbscript:` and control-character tricks to `#`).
- [`ui/src/app/(app)/briefings/page.tsx`](../ui/src/app/(app)/briefings/page.tsx)'s
  `buildBriefingHTML()` now routes every `${...}` interpolation through
  `escapeHtml`. Summary newlines still become `<br/>` because escaping
  happens before the newline→br replacement.
- Number fields coerced with `Number()` as belt-and-braces even though
  the TS type is already `number`.
- **Live-verified on prod**: all 7 entity strings (`&amp; &lt; &gt;
  &quot; &#39; &#x2F; &#96;`) present in the `briefings/page-*.js`
  chunk after deploy.

#### `SECRET_KEY` + `POSTGRES_PASSWORD` boot guard — `e091430`

- [`api/app/core/config.py`](../api/app/core/config.py) now rejects
  weak secrets in **both** `production` and `staging` (previously only
  production).
- Blocked-secret list expanded to 13 literals (`change-me`,
  `change-me-in-production`, `secret`, `default`, `test`, `testing`,
  ...) and 7 POSTGRES_PASSWORD literals (`password`, `postgres`,
  `admin`, `changeme`, `ti_secret`, ...).
- Error messages include the offending environment label
  (`PRODUCTION SECRET_KEY must be set to a secure value (not a
  known-weak default)!`).
- `environment` string is `.strip().lower()`-ed before comparison so a
  stray `Production ` env var still hits the guard.
- `development` stays permissive but emits `warnings.warn` so
  misconfig surfaces during first boot.
- 30/30 config tests green.
- **Live-verified on prod**: forced `SECRET_KEY=change-me` inside the
  API container — guard fired with the expected message.

### 2. Multi-agent Bedrock — wired, gated, tiered

#### End-to-end agent path — `b7ba2d3`, `2387747`

- New [`api/app/services/bedrock_agent_adapter.py`](../api/app/services/bedrock_agent_adapter.py)
  drains the Bedrock Agent Runtime `invoke_agent` EventStream
  synchronously via `asyncio.to_thread`; counts action-group +
  collaborator invocations from the trace stream; parses structured
  JSON on completion; **raises** on agent-stream errors or
  `returnControl` per `rca_rq_tasks_must_raise`.
- `chat_completion_json()` gained a `use_agent: bool` kwarg. Default
  off — callers opt in per feature.
- Infra: VirusTotal Lambda handler (`infra/lambdas/virustotal_lookup/`)
  supports both the legacy `{ioc, ioc_type}` direct-invoke shape and
  the Bedrock action-group event envelope. Uses stdlib `urllib` (no
  pip deps, runs bare on `python3.12`). Deterministic stub when
  `SECRET_ARN` is empty, so the demo flow returns sensible data even
  without a real VT key. 12 adapter tests + 8 handler tests.

#### Flag split: news vs IOC — `e224401`, `213013d`, `462e3ef`, `f35bba1`

- `AI_USE_AGENTS` (default `false`) — gates news enrichment. Kept off
  because the Supervisor's configured `maximumLength=1024` causes
  preamble output for the 27-field news schema (supervisor returns
  "Extracting information from the article to create the JSON
  object." instead of the JSON). Known follow-up.
- `AI_USE_AGENTS_FOR_IOC` (default `true`) — new flag, gates IOC live
  lookup (`live_lookup._ai_analyze`). IOC path now routes through the
  Supervisor → IOC-Analyst → `virustotal_lookup` action group, falling
  back to single-shot Nova Lite via `chat_completion_json` on agent
  non-JSON or disjoint prompt.
- Fixed two early-return gates in `_ai_analyze` and its caller that
  bailed when `ai_api_key == ""` (Bedrock mode) — agent path needs
  neither `ai_api_key` nor `ai_api_url`; credentials come from EC2
  IAM via IMDS.
- Legacy `httpx` fallback replaced with `chat_completion_json(
  use_agent=False)` so the Bedrock path is reused properly in fallback
  — **first time** IOC AI analysis actually produced JSON in
  production (previously always `null`).
- **Live-verified on prod**: IOC lookup on `1.1.1.1` returned real 6-
  key analysis in 4.2 s (agent attempt → JSON-parse fail → single-
  shot Bedrock fallback succeeded).

### 3. AI Configuration page — schema fix + rich panels

#### Schema drift unblock — `44c3ef5`

- `/api/v1/ai-settings` had been returning **500** (`UndefinedColumnError`)
  because the ORM declared `feature_kql_generation` /
  `daily_limit_kql_generation` / `prompt_kql_generation` /
  `model_kql_generation` but no migration shipped them to prod.
- [`db/migrations/008_ai_settings_kql.sql`](../db/migrations/008_ai_settings_kql.sql)
  adds all four columns with `IF NOT EXISTS` — safe to re-run.
- Endpoint now returns **200** and the Settings → AI Configuration
  panel loads for the first time this session.

#### Multi-agent pipeline card — `0b932fe`, `421740f`, `2407e00`

- New endpoint `GET /api/v1/ai-settings/pipeline` returns:
  - Routing table: feature → path (agent / single-shot) + model +
    controlling env flag name.
  - Live agent catalog via `boto3` `bedrock-agent.get_agent` for
    Supervisor + all collaborators. Status (PREPARED / PREPARING /
    UNREACHABLE) + agent ID + alias name + collaborator + action-group
    counts.
  - Response cached 60 s in Redis so the Bedrock control plane isn't
    hammered on every UI render.
- UI [`ui/src/components/AIMultiAgentPipeline.tsx`](../ui/src/components/AIMultiAgentPipeline.tsx)
  renders the routing rows + a grid of agent cards with status pills +
  action-group chips. Manual refresh button.
- Two bugs fixed during implementation:
  1. Collaborator agent-ID was sliced with `[-3]` but `aliasArn`'s
     split produces `agent-alias / agentId / aliasId` — correct index
     is `[-2]` (`421740f`).
  2. The guard `"/agent-alias/" in alias_arn` never matched because
     the real ARN has `:agent-alias/` (colon before, slash after), not
     two slashes. Changed to `":agent-alias/"` (`2407e00`).

#### Real-time token + cost widget — `0b932fe`

- New [`api/app/core/ai_telemetry.py`](../api/app/core/ai_telemetry.py)
  with `track_invocation()` + per-model pricing table + daily Redis
  counters (14-day TTL). Pricing covers Nova Lite/Micro/Pro, Titan
  Text Lite/Express, Claude 3 Haiku/3.5 Sonnet/3 Opus, with a
  conservative fallback for unknown models.
- `BedrockAdapter.ai_analyze` (exact tokens from the `usage` block)
  and `BedrockAgentAdapter.ai_analyze_structured_via_agent`
  (approximate via `chars/4` — agent runtime doesn't return flat
  usage) both call `track_invocation` after success. The telemetry
  helper wraps all Redis calls in `try/except` — never raises in the
  hot path.
- New endpoint `GET /api/v1/ai-settings/token-usage?days=7` reads the
  counters with **no server-side cache**, so the widget polls fresh
  values straight from Redis.
- UI [`ui/src/components/AITokenUsageWidget.tsx`](../ui/src/components/AITokenUsageWidget.tsx)
  shows 4 KPIs (today / yesterday with % trend / window / per-model
  with relative bars) and polls every 15 s. "Last: HH:MM:SS"
  indicator. `cache: "no-store"` on the fetch.
- **Live-verified**: fresh IOC lookup after deploy → usage endpoint
  reflected `input: 1114, output: 15, calls: 2` within 2 s, split
  between `bedrock-agent` (503/15) and `amazon.nova-lite-v1` (611/0).

### 4. Tiered per-feature model routing — `c9cffc3`, `22e9216`

- Empirical benchmark via new
  [`scripts/probe_bedrock_models.py`](../scripts/probe_bedrock_models.py)
  (commit `bb74e67`) — lists Bedrock models available on the account
  and runs a cyber-sec JSON-extraction benchmark on each candidate to
  pick per-tier defaults.
- Four tiers mapped in [`docs/ARCHITECTURE.md`](ARCHITECTURE.md):
  - **Classifier** — fast MoE Llama4 Scout for `news_enrichment`,
    `intel_summary`, `kql_generation` (~400 ms p50).
  - **Correlator** — Nova Pro for `intel_enrichment`, `live_lookup` —
    native Bedrock-Agent support + action-group tool calling.
  - **Narrative** — Mistral Large for `briefing_gen`, `report_gen` —
    best prose, quality over speed.
- `model_<feature>` columns in `ai_settings` drive the selection;
  empty string falls back to the primary model (Nova Lite).
- AI Configuration Provider + Health tabs rebuilt Bedrock-aware
  (`ac33127`, `22e9216`) so the UI reflects the actual tiered routing
  rather than the legacy single-provider assumption.

### 5. Investigate — relationship graph overhaul

#### Auto-populate + degree-weighted nodes — `759782d`

- `GET /api/v1/graph/featured?limit=N` returns the most-connected
  entities across the whole graph (SQL: `UNION ALL` source + target,
  `GROUP BY (entity_type, entity_id)`, `COUNT(*) DESC`). Per-type cap
  so one noisy type can't swamp the list. 120 s Redis cache.
- Empty state gone: the page fetches featured on mount and auto-
  centres the graph on the #1 entity when the user hasn't deep-
  linked or typed. First-visit UX now shows a working graph, not
  a placeholder.
- New "Suggested" chip row under the search bar: 10 clickable chips
  with type-colour dot + truncated label + `×degree` count.
- `GraphExplorer` node radius is now degree-proportional (base-by-
  type + up to +10 boost, clamped to 34). The most-connected nodes
  visually dominate.

#### In-graph search filter — `8469a44`

- Live input in a second top-left toolbar row. Case-insensitive
  substring match against `label + id`.
- Direct matches get a pulsing yellow dashed halo; one-hop neighbours
  stay lit so context is preserved; everything else dims to 0.12
  opacity.
- Clear button once text is entered; match count shown in amber on
  the right.

#### PNG / SVG export — `169d80a`

- Download button with dropdown: **PNG** (2× retina canvas raster) or
  **SVG** (editable vector).
- Shared `buildSerialisedSVG()` helper clones the live SVG, injects
  an inline `<defs>` + background gradient rect (the CSS background
  on the live SVG wouldn't survive serialisation).
- Timestamped filename — `intelpulse-graph-2026-04-17T08-34-12.png`.

#### Rich edge-evidence tooltip — `c3a941b`

- Replaced the one-line SVG tooltip (`shares ioc · 85%`) with a
  `foreignObject`-hosted HTML card.
- New `extractEvidence()` reads `edge.metadata` and surfaces up to 3
  lines: `via ip: 185.220.101.45` / `shared iocs: 12` / `via cve:
  CVE-2021-34527` / `via technique: T1059.003` / `first seen:
  Apr 3, 2026`.
- Previously an analyst saw *"shares ioc · 85%"* with no way to know
  *what* the shared IOC was. Now the tooltip names the pivot that
  ties the two nodes together.

#### Mini-map with click-to-pan — `7e09b0d`

- Bottom-left 180×120 overview. Every node as a coloured dot, every
  edge as a thin grey line. Dashed cyan rect tracks the current
  viewport live as the user pans / zooms.
- Click anywhere in the mini-map → re-centre the main view on that
  world coordinate (preserving zoom). Caption reads "overview · click
  to pan".

#### Path explorer (shortest path) — `4ec87c7`

- Togglable path-finder mode in the toolbar (branch-icon button).
- Click source → click target → client-side BFS across `data.edges`
  finds the shortest path (`O(V+E)`).
- Path edges get a golden glow underlay; endpoints get a bold amber
  ring, intermediates a thinner one.
- Status banner at the top: `{hops} hops · {source} → {target}` or
  "No path found" with a suggestion to increase explore depth if the
  nodes are in disjoint components of the loaded graph.
- All 5 graph features compose — filter while in path mode, export a
  graph with the path highlighted, mini-map-click to centre then
  path-find within a cluster.

### 6. Deploy pipeline — 2m30s → ~54s

[`6e175e7`] + [`65e4c57`] — end-to-end performance pass, documented in
[`docs/DEPLOYMENT.md`](DEPLOYMENT.md).

- CI lint split into parallel `python-lint` + `ui-lint` jobs.
- Python lint no longer installs the full FastAPI stack just to run
  `ruff check` — `pip install ruff mypy` only (saves ~25 s per run).
- `setup-python@v5` gained `cache: pip`.
- All three Dockerfiles (`api`, `worker`, `ui`) use BuildKit cache
  mounts for their package managers — `--mount=type=cache,target=/root/.cache/pip`
  for Python, `target=/root/.npm` for node. Dropped `--no-cache-dir`
  from pip so the mount actually caches wheels.
- `deploy.sh` health-check poll cadence 10 s → 2 s. Max wait still
  120 s.
- Per-deploy `docker image prune -f --filter "until=48h"` moved out of
  the hot path. Previously it nuked the very layer cache the mounts
  tried to reuse. New [`scripts/docker-cleanup.sh`](../scripts/docker-cleanup.sh)
  runs weekly (Sun 03:00 UTC) via cron installed on the EC2.
- **Measured**: Python-only commit lint→deploy = ~54 s end-to-end
  (was ~2m30s). Dockerfile-touching commit = ~2m cold, then warm.

### 7. UI polish

- `fef0c46` + `ca49449` — "How it works" pipeline explainer on
  Dashboard, Threats, News, and every top-level page. Page purpose,
  how-to-use, and Amazon Bedrock multi-agent detail.
- `763f395` — raised dark-mode contrast for muted text, tabs, sidebar
  nav.
- `221d5d0` — coloured sidebar nav icons by category so analysts get
  a stable visual map.
- `ef485ec` — removed Admin chrome from header + sidebar. No login
  page exists (`demo_mode=true`), so showing an "Admin" dropdown with
  profile/security/sign-out was misleading. User-menu block deleted;
  desktop + mobile sidebar user sections deleted; unused
  `showUserMenu` + `handleLogout` removed.
- `14c53e1` — seed script for 3 enriched sample threat briefings so
  the Briefings page isn't empty on a fresh DB.
- `a939dd6` — rich sample cases + reports, DB-direct via
  `scripts/seed_sample_data.py`.

### 8. Repo hygiene

- Git history rewritten with `git-filter-repo --commit-callback` to
  strip every `Co-Authored-By: Claude ...` trailer. 17 commits
  matched; all rewritten. Every file blob preserved — pure metadata
  churn. Force-pushed to `origin/main` with explicit user
  authorisation.
- Project-local `.claude/settings.json` now sets
  `attribution.commit = ""` — future commits from this repo don't
  emit the Claude co-author trailer at all.
- GitHub API authoritatively shows 1 contributor (`manishjnv`, 411
  commits); sidebar widget re-indexed post-rewrite.

### 9. Operational fixes

Rolled up from the session:

- `9196216` — scheduler watchdog compared to hardcoded
  `EXPECTED_JOB_COUNT`; now reads the live `scheduler.schedule()`
  count so it doesn't false-alarm when a job is added/removed.
- `b671ee5` — `git update-index --chmod=+x scripts/deploy.sh` so the
  deploy script stays executable across clones.
- `67fad5c` — `deploy.sh` now falls back to `docker-compose` v1 when
  the v2 plugin is missing (some hosts ship Docker 29.x without the
  compose plugin by default).
- `d16df47` — API healthcheck path corrected to
  `/api/v1/health` (was `/health` which returns 404 behind the API
  prefix).
- `f3ae401` + `3eeb2c6` — plumbed `SECRET_KEY` + `DEMO_MODE` through
  `x-common-env` so worker/scheduler/api all receive them. Prevented
  the worker from crash-looping on missing `SECRET_KEY`.
- `af1272c` — same pattern for `AI_USE_AGENTS` +
  `BEDROCK_SUPERVISOR_*` env vars.
- `d988d6b` — `BedrockAdapter` dispatches by model family (Anthropic /
  Nova / Titan) so the adapter serves all three on whatever account
  has access.
- `7d1d811` + `613fe8e` — SQLi in `get_intel_items` enum filters
  patched to use an allowlist; `SECURITY.md` §7 updated to describe
  the defence.
- `71d58d0` — split combined `import json, logging` in
  `enrichment.generate_briefing` to satisfy ruff E401.

---

## How this file is maintained

Add a new dated entry at the top for each session of meaningful
changes. Group by theme. Cite the commit SHA on each bullet so future
readers can pull the diff without searching. Describe the *why*, not
just the *what* — the diff already shows the what.

For trivial (single-line) changes, a one-line bullet under a
“Miscellaneous” heading is fine. Everything else gets at least a
paragraph.

Live verification notes belong inline — it's the only proof that the
change actually made it to production, and it's the first thing a
future debugger will look for when something regresses.
