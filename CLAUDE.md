# IntelPulse — project overlay for Claude Code

> **Canonical committed copy.** A sibling local-only file at `../CLAUDE.md` (one dir up, outside this repo) exists because Claude Code in this workspace auto-loads from `e:\code\IntelPulse\` cwd (where `.claude/settings.local.json` allowlist and `~/.claude/projects/e--code-IntelPulse/` memory resolve). The sibling's paths carry a `ti-platform/` prefix; paths here are repo-relative. **If you edit one, sync the other — the only semantic diff is path prefixes.**

Loads on top of the global `~/.claude/CLAUDE.md` orchestration playbook. When this file conflicts with global, **this file wins**. Paths below are relative to this repo root.

## Where things live

- **Stack:** FastAPI `api/` + Next.js `ui/` + `worker/` + `scheduler/` + Caddy + Postgres/Redis/OpenSearch
- **Memory (personal, not in repo):** `~/.claude/projects/e--code-IntelPulse/memory/` — `MEMORY.md` is the index; `session_*.md` are handoffs; `rca_*.md` are incident postmortems
- **Production:** `https://intelpulse.tech/` — open/no-login (demo_mode=true by design)
- **Deploy:** every push to `main` → GH Actions → ECR build+push → SSH to EC2 `intelpulse2` → `scripts/deploy-ecr.sh` (image tag = commit SHA)
- **Allow-listed autonomous ops:** `.claude/settings.local.json` whitelists `ssh intelpulse2 *`, `git push origin main`, `gh run *`

## Phase 0 warm-start reads (fire in ONE parallel message)

This file and `MEMORY.md` auto-load at session start — do NOT re-read them. Phase 0 only needs:

1. The **most recent** `session_*.md` (latest date wins; `MEMORY.md` index lists them)
2. Any `rca_*.md` whose topic overlaps the user's request (pick by reading memory index titles, not by re-reading `MEMORY.md`)

Then state: goal / relevant RCAs / plan / what will be delegated. Wait for user approval.

## Load-bearing paths (Phase 3 line-by-line diff review required, regardless of subagent)

Any diff touching these paths must be critiqued by Opus before push, and if security-adjacent also gated by `codex:rescue`:

- `api/app/services/database.py` — SQLi sensitivity (enum allowlist, RCA #1)
- `api/app/core/url_validation.py`, `api/app/core/safe_httpx.py` — SSRF guard + DNS-rebinding TOCTOU (pinned IP + SNI)
- `api/app/services/bedrock_adapter.py`, `api/app/services/ai.py` — tiered model routing; Converse-API dispatch by ID prefix
- `api/app/services/tasks.py` — RQ tasks MUST raise on error (RCA: returning error dicts = invisible outages)
- `api/app/services/scheduler.py` — watchdog uses live `scheduler.schedule()` count, not hardcoded constant
- `caddy/Caddyfile` — edge CSP + security headers (bind-mount inode trap — deploy.sh must restart caddy on change)
- `ui/next.config.js` — CSP + defense-in-depth headers
- `.github/workflows/ci.yml`, `scripts/deploy-ecr.sh` — deploy pipeline (OIDC sub shape, +x bit on Windows, stale-script bootstrap — see `rca_ecr_deploy_pipeline.md`)
- `db/migrations/*.sql` — schema/index migrations
- `api/app/core/rate_limit*`, any middleware resolving client IP — `X-Real-IP` / proxy-headers trap

## IntelPulse-specific hard rules

- **"Done" means live on prod.** Default: commit → push → CI → deploy → verify. Do not stop at "committed locally" unless the user explicitly asks to hold. (See `feedback_commit_push_deploy_default.md`.)
- **Treat every endpoint as publicly reachable.** `demo_mode=true` authenticates anonymous callers as admin. SSRF / SQLi / XSS / unsafe-default findings escalate; IDOR / missing-auth findings do not apply.
- **Measurement hygiene.** Do not measure cache hit rates or tail latency within 2 minutes of a deploy — container restart nukes Redis. Wait or you will chase a non-bug. (See `rca_perf_measurement_gotchas.md`.)
- **Bundle-split wins come from unique code, not duplicated shared code.** Splitting a tab into its own chunk often saves ~0.5 KB even when the tab "looks" like 10 KB — shared React/lucide/UI deduplicates.
- **Bedrock tiering is empirically chosen.** Do not change `model_<feature>` defaults without re-running `scripts/probe_bedrock_models.py` and logging the matrix. Nova's content filter refuses ~20 % of cybersec content — Llama family is the permissive fallback.

## Delegation playbook specific to IntelPulse

| Recurring task | Model | Notes |
|---|---|---|
| Add `Depends(edge_cacheable)` / any identical decorator to N routes | Sonnet × N parallel | One agent per file, template diff in prompt |
| RSC migration (`/threats` template → `/investigate` `/search` `/news`) | Sonnet × 3 parallel | Each gets `threats/page.tsx` + `threats-client.tsx` as reference |
| Post-deploy header/cache audit (curl grid over N URLs) | Haiku × 1 | Returns checkmark table |
| Multi-file grep (`text(f"`, `prefetch={false}`, `xlsx` references) | Haiku × 1 | |
| Bedrock model probe matrix collation | Haiku × 1 | |
| SSRF / CSP / SECRET_KEY / SQLi / auth changes | Opus draft + `codex:rescue` before push | Always |
| Seeders (`seed_sample_*.py`, `apply_tiered_model_routing.py`) | Sonnet | Idempotent contract, write tests for the idempotency |
| Deploy pipeline edits (`ci.yml`, `deploy-ecr.sh`) | Opus | Load-bearing; re-read `rca_ecr_deploy_pipeline.md` first |

## `codex:rescue` invocation template

When gating a security/auth/classifier/load-bearing diff through `codex:rescue`, use this shape so sign-offs are auditable in the session-state doc:

```text
[DELEGATE_TO_CODEX_RESCUE]
Change: <commit SHA or "HEAD~1..HEAD" diff ref>
Files touched: <load-bearing paths — full list>
Contract / threat: <what this must preserve — e.g. "SSRF guard pins IP into httpx request, preserves Host header + SNI, follow_redirects=False, retries=0">
Specifically verify: <1-3 concrete edge cases — e.g. "(1) literal-IPv6 URL, (2) redirect response, (3) custom port + SNI hostname mismatch">
Return: accept / revise / reject, with rationale per edge case.
```

Log the outcome as a single line in the session-state `codex:rescue` footer row: `<commit> — <accept | revised: <what> | rejected: <why>>`. If Codex disagrees and you push anyway, write the rationale into the session-state body, not just the footer.

## Phase 6 handoff contract (required)

Every session-state `session_*.md` ends with this footer. One line per row, `n/a — <reason>` if empty (never omit):

```markdown
## Agent utilization
- Opus (main): <e.g. "plan + 3 diff critiques + final prod verify">
- Sonnet: <e.g. "3 parallel RSC page migrations; 1 sequential bedrock_adapter edit (load-bearing)">
- Haiku: <e.g. "curl-grid header audit over 11 endpoints; grep sweep for xlsx imports">
- codex:rescue: <e.g. "SSRF pinned-transport diff — accepted; CSP Caddy mirror — revised (added COOP)">
```

## Session-start self-check (do this before Phase 1)

- Is there a `session_*.md` from the last 24 h I haven't reconciled? If yes, read it — I may be mid-thread.
- Is CI currently green? (`gh run list --branch main --limit 3`) If red, fix or acknowledge before starting new work.
- Any stale memory entry that contradicts current code? Flag to user; do not silently override.
