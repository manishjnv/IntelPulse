# IntelPulse — Deployment Pipeline

How code on `main` reaches [https://intelpulse.tech/](https://intelpulse.tech/), how long it should take, and how to keep it fast.

## Overview

```text
 git push origin main
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ GitHub Actions — .github/workflows/ci.yml            │
│                                                      │
│  python-lint ────┐                                   │
│                  ├──►  deploy  (only on push to main)│
│  ui-lint ────────┘                                   │
└─────────────────┬────────────────────────────────────┘
                  │ SSH (appleboy/ssh-action@v1)
                  ▼
┌──────────────────────────────────────────────────────┐
│ EC2  — /opt/IntelPulse/scripts/deploy.sh             │
│                                                      │
│  1. git fetch + reset --hard origin/main             │
│  2. docker compose build --parallel    (BuildKit)    │
│  3. SQL migrations  (db/migrations/*.sql)            │
│  4. docker compose up -d --remove-orphans            │
│  5. wait for health (poll every 2s, max 120s)        │
└──────────────────────────────────────────────────────┘
```

## Expected timings (after the 2026-04-17 perf pass)

| Phase | P50 | P90 | Notes |
|---|---|---|---|
| `python-lint` job | 10–15s | 20s | ruff + mypy only; no runtime deps |
| `ui-lint` job | 25–35s | 45s | `npm ci` (cached) + `tsc --noEmit` |
| **Lint wall-clock** | **~30s** | **~45s** | Jobs run in parallel; slower one sets the floor |
| Deploy — Python-only change | 20–30s | 40s | pip cache 100% hit, only `COPY api/` layer rebuilds |
| Deploy — UI-only change | 40–60s | 80s | Next.js `npm run build` always re-runs |
| Deploy — dep change (`pyproject.toml` / `package-lock.json`) | 30–60s | 90s | Cache-miss delta install |
| Deploy — no-op redeploy | 15–20s | 25s | Images identical, just container recreate + health |
| Deploy — Dockerfile change (cold BuildKit) | 60–120s | 2m | One-off; cache warms back up on the next run |
| **End-to-end P50** | **~60–90s** | | Common case: Python source edit |

If a deploy exceeds P90, the culprit is usually one of:
- New Python or Node dep (cache-miss delta install)
- Dockerfile edited (BuildKit cache mount invalidated)
- A service's healthcheck staying unhealthy for the 120s wait window

## Performance decisions (and what they cost)

### 1. Split `lint` into `python-lint` + `ui-lint` (parallel)
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Single serial lint job ran Python setup + Node setup + both checks sequentially (~60s). Split saves ~30s because the UI side dominates once the Python side is minimized.

### 2. Python lint installs `ruff mypy` only — not the full runtime stack
Ruff is a static checker. It reads source files; it doesn't import them. Installing FastAPI + boto3 + SQLAlchemy + pydantic + structlog just to check syntax is ~25s wasted per run. `pip install ruff mypy` is ~3s.

### 3. `pip` cache on `setup-python@v5`
Key by hashed `pyproject.toml`. Ruff/mypy reinstall is a no-op after the first run.

### 4. BuildKit cache mounts in every Dockerfile
- `docker/Dockerfile.api` and `docker/Dockerfile.worker`:
  ```dockerfile
  RUN --mount=type=cache,target=/root/.cache/pip \
      pip install --prefix=/install -r /tmp/requirements.txt
  ```
- `docker/Dockerfile.ui`:
  ```dockerfile
  RUN --mount=type=cache,target=/root/.npm \
      npm ci
  ```

Cache mounts persist between builds on the same host (EC2). When
`pyproject.toml` / `package-lock.json` is unchanged, the install layer
is a **no-op read** from the mount. When deps change, only the delta
gets fetched.

Consequence: `--no-cache-dir` was removed from pip calls (it would
defeat the mount by refusing to write wheels).

### 5. Health poll cadence: 10s → 2s
[`scripts/deploy.sh`](../scripts/deploy.sh)

`sleep 10` meant the loop could wait up to 10 extra seconds after all services were already healthy. `sleep 2` catches the transition within 2s. Max wait still 120s.

### 6. Image pruning moved off the deploy path
Old behaviour: `docker image prune -f --filter "until=48h"` ran on **every** deploy. This nuked the BuildKit cache layers that the mounts were trying to reuse — every deploy paid the cold-cache cost.

New behaviour: pruning is a weekly cron via [`scripts/docker-cleanup.sh`](../scripts/docker-cleanup.sh). Keeps 7 days of layers, runs Sundays at 03:00 UTC, logs to `/opt/IntelPulse/docker-cleanup.log`.

Install once on EC2:
```bash
(crontab -l 2>/dev/null | grep -v docker-cleanup; \
 echo '0 3 * * 0 /opt/IntelPulse/scripts/docker-cleanup.sh >> /opt/IntelPulse/docker-cleanup.log 2>&1') \
  | crontab -
```

## Required GitHub Secrets

Environment-scoped to `production` (not repo-scoped):

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | `3.87.235.189` |
| `DEPLOY_USER` | `ubuntu` |
| `DEPLOY_SSH_KEY` | contents of `intelpulse2.pem` |

List with `gh secret list --env production`. Plain `gh secret list` shows nothing because these live under the environment.

## How to test the pipeline

```bash
# Watch the latest run
gh run list --limit 1
gh run watch $(gh run list --limit 1 --json databaseId -q '.[0].databaseId')

# Tail live deploy log on EC2
ssh intelpulse2 "tail -f /opt/IntelPulse/deploy.log"

# Verify what's actually live
ssh intelpulse2 "cd /opt/IntelPulse && git log -1 --format='%h %s'"

# Production API health
curl -s https://intelpulse.tech/api/v1/health
```

## Manual deploy recovery (CI broken, EC2 reachable)

```bash
ssh intelpulse2 "sudo -u ubuntu /opt/IntelPulse/scripts/deploy.sh"
ssh intelpulse2 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

## Further optimizations (not implemented)

These were scoped but deferred — they trade engineering time for another 30-50% speedup:

1. **Pre-build images in CI, push to ECR.** EC2 does `docker compose pull && up -d` instead of building locally. Makes EC2 deploys a consistent ~20s regardless of what changed. CI picks up the build cost (parallelizable with lint). Effort: ~2h.
2. **Buildx remote cache.** Push layer cache to a registry with `--cache-to=type=registry,...`; share between CI and EC2 so even first-deploy-after-Dockerfile-change is warm. Effort: ~1h.
3. **Per-service rebuild detection.** Today `docker compose build --parallel` rebuilds every image. A `git diff --name-only` in deploy.sh could let us rebuild only api, only ui, or only worker depending on what files changed. Effort: ~3h.
4. **Rolling deploys.** Bring up new containers beside old ones, flip traffic when healthy (via Caddy reverse-proxy config). Cuts the 120s health wait to zero downtime. Effort: ~4h.
