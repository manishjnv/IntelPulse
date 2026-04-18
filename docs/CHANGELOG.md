# IntelPulse — Changelog

Running log of notable changes, grouped by date then theme. Every entry
references the commit SHAs that landed the work so you can jump straight
to the diff. Production URL: [https://intelpulse.tech/](https://intelpulse.tech/).

---

## 2026-04-18 (pt9) — final pt7 carry-forwards closed: notifications silent-catch sweep + `/news` subtopic chunk preload

Final two items from the pt7 "Still open" list closed. Three earlier
pt7 items had already shipped in pt8 between sessions (`fb10eef`,
`16b0842`, `08f89ee` — documented in that session's handoff). The
remaining gaps were UX-observability (silent network failures on the
notifications page) and UX-perceived-perf (first-click chunk download
on `/news` subtopic tabs). One environmental item (Windows
`next build` phantom ENOENT) was acknowledged as non-actionable — the
project's rule of "Linux CI is the authoritative build" stands.

Two commits, both UI-only, zero load-bearing paths touched, zero
codex:rescue ceremony. Live-verified on prod.

### 1. `console.error` on 6 notifications silent catches — `18876e3`

[`ui/src/app/(app)/notifications/page.tsx`](../ui/src/app/(app)/notifications/page.tsx)
had 6 `catch { /* silent */ }` blocks swallowing errors from every
notification fetch and mutation. Discovered during Phase 0 `grep`
for `/* silent */` / `/* ignore */` across the `(app)` tree; not
originally on the carry-forward list but folded in as a bonus under
the same rationale as the pt7/pt8 silent-catch sweeps (`7116207`,
`fb10eef`).

Each `catch { /* silent */ }` became
`catch (err) { console.error("[notifications] <handler> failed", err) }`
so devtools surfaces the failure in operator/debug context. **Not**
toasted — this matches the existing rule from pt7 that sidebar
widgets shouldn't toast (noise); user-initiated mutation handlers
(mark-read, delete, clear-all) could arguably toast in a future pass,
noted in the pt9 memory doc.

Six handlers updated:

| Line | Handler | Context |
| --- | --- | --- |
| 85 | `loadNotifications` | bulk list fetch (page, filter, unread-only) |
| 97 | `loadStats` | unread/total counts |
| 119 | `handleMarkRead` | POST `/notifications/mark-read` |
| 131 | `handleMarkAllRead` | POST `/notifications/mark-all-read` |
| 143 | `handleDelete` | DELETE by id |
| 156 | `handleClearAll` | DELETE all (confirm-gated) |

**Live verification.** Fetched `https://intelpulse.tech/notifications`,
extracted the deployed chunk URL (`/_next/static/chunks/app/(app)/notifications/page-2ac2ebd4767f3817.js`),
grepped for `[notifications]`. All 6 distinct context strings present
verbatim in the minified bundle — string literals survive minification
because they're argument values, not identifier names.

Cross-check: `grep -r '/\* silent \*/\|/\* ignore \*/'` under
[`ui/src/app/(app)`](../ui/src/app/(app)/) now returns **zero matches**.
Every silent catch in the app route tree has been replaced with
observable logging (pt7 covered `threats` + `news`; pt8 covered
`feeds` + `settings`; this commit covered `notifications`).

### 2. `/news` subtopic chunk preload on hover/focus — `5e60870`

pt7 commit `892d207` split the `/news` subtopic widgets
(`VendorStatsWidget`, `VulnerableProductsTable`, `ThreatCampaignsTable`)
into their own files loaded via `next/dynamic({ ssr: false })`. That
shaved the `/news` client bundle from 21 kB → 16.7 kB (−4.3 kB), but
introduced a ~200-500 ms chunk-download lag on the first click of the
"Vulnerable Products" or "Threat Campaigns" subtopic tab over a slow
connection. The fallback `<Skeleton />` hides it visually, but the
interaction still *feels* laggy.

Fix: warm the chunk cache when the user's intent becomes visible —
typically `onMouseEnter` (pointer devices), with `onFocus` added for
keyboard nav and touch-hover simulation.

Top-level helper added to
[`ui/src/app/(app)/news/news-client.tsx`](../ui/src/app/(app)/news/news-client.tsx)
right after the existing `dynamic(...)` declarations:

```tsx
// Preload subtopic-tab chunks on hover/focus so the first click doesn't
// pay the ~200-500ms chunk-download penalty on slow connections.
const preloadSubtopic = (id: string) => {
  if (id === "vulnerable-products") {
    void import("./VulnerableProductsTable");
    void import("./VendorStatsWidget");
  } else if (id === "threat-campaigns") {
    void import("./ThreatCampaignsTable");
  }
};
```

Then each of the 3 subtopic `<button>` elements in the tab bar picks
up:

```tsx
onMouseEnter={() => preloadSubtopic(tab.id)}
onFocus={() => preloadSubtopic(tab.id)}
```

**Design choice — `void import("./Foo")` not `.preload()`.**
`next/dynamic`'s returned component does expose a `.preload()` method
on modern Next.js versions, but the TypeScript surface is inconsistent
— `LoadableComponent` sometimes omits it and you end up needing a cast
or `@ts-expect-error`. Calling `import(...)` directly is the same
webpack machinery `next/dynamic` invokes internally: the module cache
dedupes repeat calls (idempotent — hover 10 times, download once),
the chunk-load promise is cached on first resolve. `void` silences
`no-floating-promises` in 4 characters. Net: 3 lines shorter than the
`.preload()` route, no typing escape hatches.

**Why scope to only 2 of the 3 tabs.** The "news" subtopic renders
only in-bundle code (the main news feed + category sidebar + widgets
already present in the main chunk) — no dynamic import to preload.
Entering that `if` branch would be a no-op with a runtime cost. The
function bails on the unhandled id.

**Live verification.** CI run `24603173609` green end-to-end through
Deploy stage with commit `5e60870`. Chunk hash on deployed HTML
advanced from pre-deploy version to `page-b9b88210c2609b84.js`.

String-grep for `preloadSubtopic` in the deployed chunk returned
empty — function names minify to single letters, and dynamic-module
targets become numeric chunk IDs, so direct identifier verification
doesn't work for this kind of change. Indirect checks: literal refs
to `"vulnerable-products"` in the news chunk count 5, `"threat-campaigns"`
count 4 — consistent with the existing tab-id + conditional-render
refs plus the new `if (id === "…")` comparisons in `preloadSubtopic`
(which the minifier keeps as string literals because they're on the
right-hand side of a `===`).

Smoke-testing the hover preload in an actual browser (DevTools
Network panel filtered to `chunk`, hover tab → observe a chunk fetch
*before* click) is the authoritative check and was not performed this
session. Low risk: 13-line addition, only event handlers, no
render-path changes, no state mutation, idempotent.

### 3. Windows `next build` phantom ENOENT — acknowledged as environmental

The pt7 "Still open" list flagged an intermittent Windows-only
failure: `npm run build` in
[`ui/`](../ui/) sometimes emits
`ENOENT: no such file or directory, open '.next/build-manifest.json'`
during the "Collecting page data" phase, even though the file exists
moments later. Root cause: Next.js + Windows filesystem-timing quirk
documented in [`rca_perf_measurement_gotchas.md`](../../../Users/manis/.claude/projects/e--code-IntelPulse/memory/rca_perf_measurement_gotchas.md)
(local memory, not repo-tracked).

**Resolution stance: no code change.** The Linux CI build is the
authoritative measurement — it runs on every push, it produces the
bundle-size table the project treats as canonical per
[`rca_perf_measurement_gotchas.md`](../../../Users/manis/.claude/projects/e--code-IntelPulse/memory/rca_perf_measurement_gotchas.md)
Trap #2, and it has never exhibited the ENOENT. Skipping local build
on Windows saves ~2 min per loop. Upgrading Next.js or moving the dev
loop into WSL would fix it on our side, but neither is warranted for
a negligible inconvenience that doesn't affect prod.

### End-of-session verification matrix

| Task | Live check | Result |
| --- | --- | --- |
| 1. Notifications `console.error` | curl chunk + grep `[notifications]` | 6/6 distinct error strings present |
| 2. `/news` preload refs | curl chunk + count `"vulnerable-products"` + `"threat-campaigns"` | 5 + 4 refs (tab-id + conditional + preload `===`) |
| 3. Silent-catch sweep final state | `grep /\* silent \*/\|/\* ignore \*/` under `ui/src/app/(app)` | 0 matches |
| 4. CI Deploy stage | `gh run view` both commits | both `completed/success` end-to-end |

**Agent utilization this session** — noted here for routing-drift
auditability per the project overlay:

- Opus (main): Phase 0 self-check (CI status + same-pattern grep);
  2 direct self-edits (6 Edits on `notifications/page.tsx` in one
  parallel batch; 2 Edits on `news-client.tsx`); 2 commit/push/verify
  loops; Phase 6 handoff write. All work self-executed — edits fit
  well under the overlay's "≤30 lines across ≤2 files, files in hot
  read cache" threshold for not delegating.
- Sonnet / Haiku / codex:rescue: n/a — work too small to justify
  subagent cold-start, and no load-bearing/security paths touched.

---

## 2026-04-18 — five residuals + deploy pipeline rewire

Four security residuals closed (CSP, DNS-rebinding TOCTOU, xlsx CVE,
Bedrock agent token ceiling) and the deploy pipeline moved from
"build-in-VPS" to "build-on-GH-push-to-ECR-pull-from-EC2". Production
stayed green across 13 commits; each deploy stage now runs in ~20 s
instead of ~60 s. Full end-to-end verification at the end.

### 1. CSP + defense-in-depth headers — `d4e3c1b` `519e30f` `e581b0a`

- [`ui/next.config.js`](../ui/next.config.js) grows a `headers()` block
  with a comprehensive CSP (`default-src 'self'`, `connect-src 'self'`,
  `frame-ancestors 'none'`, `frame-src 'none'`, flagcdn.com image
  allowlist, `object-src 'none'`, COOP/CORP/HSTS, upgrade-insecure-
  requests). `'unsafe-inline'` and `'unsafe-eval'` stay on scripts
  because Next.js 14 hydration + recharts d3-scale need them; retiring
  those is a nonce-middleware follow-up.
- [`caddy/Caddyfile`](../caddy/Caddyfile) mirrors the full directive list
  at the edge — the previous `frame-ancestors 'none'`-only header
  silently overrode whatever Next.js emitted. Applied at both
  `intelpulse.tech` and the direct-IP fallback.
- [`scripts/deploy.sh`](../scripts/deploy.sh) learns to restart the
  Caddy container when `HEAD~1..HEAD` touches `caddy/`. Needed because
  `git reset --hard` rewrites the Caddyfile with a **new inode**, but
  the docker bind-mount established at container start points at the
  **old inode** — so `compose up -d` alone never reloaded the config.

Live verification: `curl -sI https://intelpulse.tech/` carries the full
directive list on both UI and API routes.

### 2. DNS-rebinding TOCTOU close — `96bab7c`

The prior SSRF guard resolved the hostname once, rejected on any
private answer, then handed the URL string to httpx — which
**re-resolved at connect time**. A malicious authoritative DNS could
return 8.8.8.8 to `getaddrinfo()` and 169.254.169.254 to `connect()`
milliseconds later, defeating the allowlist.

- [`api/app/core/url_validation.py`](../api/app/core/url_validation.py)
  adds `resolve_safe_outbound_url()` returning a `ResolvedURL(url,
  scheme, host, port, pinned_ip)` namedtuple. Multi-answer mixed (one
  private + one public) now fails-closed — selecting only the safe
  address would let an attacker's DNS round-robin smuggle in a bad IP
  on the next refresh.
- New
  [`api/app/core/safe_httpx.py`](../api/app/core/safe_httpx.py) wraps
  that into `PinnedHTTPTransport` / `PinnedAsyncHTTPTransport`. The
  transport rewrites `request.url.host` to the pinned IP before
  connect, preserves the original `Host:` header, and sets
  `extensions["sni_hostname"]` so TLS SNI + cert validation still use
  the original hostname. `retries=0`, `follow_redirects=False`.
- Both call sites swapped:
  [`api/app/routes/ai_settings.py`](../api/app/routes/ai_settings.py)
  and
  [`api/app/services/webhook.py`](../api/app/services/webhook.py).
  22 new unit tests (65 total) pass inside the prod api container.

Live verification: three SSRF vectors (AWS IMDS, 10.0.0.1, localhost)
rejected with `HTTP 400` and distinct reasons.

### 3. xlsx → exceljs swap — `7df5ff3`

- `xlsx@0.18.5` carried GHSA-4r6h-8v6p-xvw6 (Prototype Pollution) with
  no patched version on npm — upstream moved to CDN-only. Replaced
  with `exceljs@^4.4.0`, actively maintained.
- New
  [`ui/src/lib/excel-export.ts`](../ui/src/lib/excel-export.ts) wraps
  exceljs behind a single `exportToExcel(rows, sheetName, filename)`
  helper. `import("exceljs")` is dynamic so the ~300 KB library stays
  out of the initial bundle and only loads on the first Export click.
- Both xlsx call sites in
  [`ui/src/app/(app)/geo/page.tsx`](../ui/src/app/(app)/geo/page.tsx)
  swapped. Column-width logic preserved byte-for-byte.

Live verification: 0 xlsx directories in the shipped image; exceljs
bundled in two chunks (`6edf0643.*.js` + the geo page chunk).

### 4. Bedrock agent `maximumLength` 1024 → 4096 — `0420075`

Amazon Bedrock agents created via the Console default to
`promptCreationMode=DEFAULT` with an ORCHESTRATION inference cap of
`maximumLength=1024`. That ceiling was too tight for the 27-field news
enrichment JSON — the Supervisor kept emitting preamble text instead
of a clean JSON response, which is why `AI_USE_AGENTS` stayed `false`
for news.

- New
  [`infra/scripts/bump_agent_token_ceiling.py`](../infra/scripts/bump_agent_token_ceiling.py)
  flips the ORCHESTRATION slot to `OVERRIDDEN` + `maximumLength=4096`
  on all three agents (Supervisor / IOC-Analyst / Risk-Scorer),
  copying the existing base prompt template verbatim so behavior is
  unchanged apart from the higher ceiling.
- Bedrock API quirk the script handles:
  non-`OVERRIDDEN` prompt configs must **not** carry
  `basePromptTemplate` / `inferenceConfiguration` / `promptState` —
  `get_agent` echoes them for readability but `update_agent` rejects
  them. Every non-ORCHESTRATION slot is stripped to `{promptType,
  promptCreationMode, parserMode}` on the way out.
- Run → `prepare_agent` → poll until PREPARED → `update_agent_alias`
  so `live` / `live-v2` points at the new numbered version.
  Idempotent; re-running is a no-op once bumped.

Live verification: all 3 agents on `OVERRIDDEN / 4096`; live
`POST /api/v1/search/live-lookup 8.8.8.8` returns a populated
`ai_analysis` block (summary + key_findings + threat_actors) in
~3.9 s via the Supervisor → IOC-Analyst → VirusTotal action group path.

### 5. Deploy pipeline rewire — build on GH, pull from ECR

Consolidates the deploy into a single gated pipeline so every
production image is an immutable, SHA-tagged ECR artifact. The
in-VPS `docker build` goes away; the EC2 just `docker pull`s what
GH Actions already built.

**Phase A — inert scaffolding — `c250fa5`:**
[`scripts/provision_ecr.py`](../scripts/provision_ecr.py) (idempotent
boto3 creating 3 ECR repos, GitHub OIDC provider, IAM role for GH
Actions scoped to this repo, and ECR-pull policy on EC2's
`BedrockAccessRole` instance profile),
[`docker-compose.ecr.yml`](../docker-compose.ecr.yml) override mapping
api/ui/worker/scheduler to ECR URIs, a standalone
`.github/workflows/ecr-push.yml`, and
[`scripts/deploy-ecr.sh`](../scripts/deploy-ecr.sh) as the alternate
deploy entrypoint. Nothing wired into production yet.

**Phase B — the flip — `07ef355` `a37ca4d` `fcabf14` `67ba23d`
`9404fd9`:**

- Ran `scripts/provision_ecr.py` against account `604275788592`
  (IntelPulseUser has AdministratorAccess via ti-platform-admin group).
  Created 3 ECR repos with scan-on-push, AES256, lifecycle rules
  (expire untagged >7 d, keep last 20 tagged), the OIDC provider,
  `IntelPulseGitHubActionsECR` role, and attached
  `ECRPullFromIntelPulseRepos` to `BedrockAccessRole`.
- Set GH secret `AWS_ROLE_ECR_PUSH` (production-environment-scoped).
- Consolidated ecr-push.yml INTO
  [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) so deploy
  now has a hard `needs: [build-and-push]` dependency — eliminates the
  race where the SSH deploy could `compose pull` the SHA tag before
  build-and-push had pushed it.
- Three new failure modes discovered + captured in the memory RCA
  `rca_ecr_deploy_pipeline.md`:
  1. GitHub OIDC `sub` claim shape depends on whether the job has
     `environment:` — trust policy must allow both
     `repo:...:ref:refs/heads/main` and
     `repo:...:environment:production`.
  2. `git on Windows` drops +x when creating files;
     `git update-index --chmod=+x` is required pre-commit.
  3. SSH-action runs the `script:` block **before** the script has a
     chance to `git reset`, so a new version of the script on disk is
     never picked up on its own first deploy. Workaround: inline
     `git fetch + reset` in the SSH command and invoke via
     `bash scripts/deploy-ecr.sh` so the +x bit is irrelevant.

Ops one-time changes on EC2: `sudo snap install aws-cli --classic`
(deploy-ecr.sh needs `aws ecr get-login-password | docker login`).

Live verification: all 4 app containers on prod now run
`intelpulse/<svc>:9404fd9d…` (SHA-tagged ECR images). Deploy stage
measured at **21 s** on the last run (was 50–60 s with in-VPS build).
Rollback is a one-line change in `ci.yml` back to
`scripts/deploy.sh`; the legacy `build:` blocks in
`docker-compose.yml` still work out of the box.

### End-of-session verification matrix

| Task | Live check | Result |
| --- | --- | --- |
| 1. CSP headers | `curl -I` on UI + API | full directive list + 8 siblings on both |
| 2. SSRF IP-pin | 3 POSTs with IMDS / 10.x / localhost | HTTP 400 × 3, distinct reasons |
| 3. xlsx → exceljs | chunk + package.json probe | exceljs in 2 chunks, xlsx gone, `exceljs:^4.4.0` only |
| 4. Agent token ceiling | `get_agent` × 3 + live IOC lookup | all 3 `OVERRIDDEN/4096`; lookup returns populated `ai_analysis` in ~4 s |
| 5. ECR deploy | `docker ps` image column | 4/4 app containers on `intelpulse/<svc>:9404fd9d…` |

Production green across the whole session: API health 200, 8/8
containers healthy, dashboard + geo pages 200 in ~380 ms.

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
