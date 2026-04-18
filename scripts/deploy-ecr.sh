#!/bin/bash
# ─────────────────────────────────────────────────────────────
# IntelPulse TI Platform — ECR-pull Deploy Script
# ─────────────────────────────────────────────────────────────
# Alternative to scripts/deploy.sh. Instead of building images on the
# VPS, pulls them from ECR (tagged by commit SHA by the GH Actions
# workflow in .github/workflows/ecr-push.yml) and runs them.
#
# Prerequisites
#   - AWS resources provisioned via scripts/provision_ecr.py.
#   - EC2 instance profile carries the `ECRPullFromIntelPulseRepos`
#     inline policy (attached by provision_ecr.py).
#   - .github/workflows/ecr-push.yml has completed at least one
#     successful run, so the `latest` tag actually exists on ECR.
#   - Images for the target SHA have been pushed (GH Actions run
#     completed for that commit) — otherwise `compose pull` falls
#     back to `latest`.
#
# Usage (called by CI, manually, or as the SSH-action script:)
#   /opt/IntelPulse/scripts/deploy-ecr.sh           # uses latest
#   IMAGE_TAG=<git-sha> /opt/IntelPulse/scripts/deploy-ecr.sh
#
# Falls back to the legacy build-on-VPS path if the ECR pull fails
# (e.g. AWS creds missing, repo empty). The fallback is explicit —
# exits with the original error first so an operator sees the cause,
# then tells them how to run scripts/deploy.sh instead.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/opt/IntelPulse"
COMPOSE_BASE="docker-compose.yml"
COMPOSE_ECR="docker-compose.ecr.yml"
LOG_FILE="/opt/IntelPulse/deploy.log"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="${ECR_REGISTRY:-604275788592.dkr.ecr.${AWS_REGION}.amazonaws.com}"

# Prefer the docker compose v2 plugin; fall back to v1 if missing.
if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "FATAL: neither 'docker compose' nor 'docker-compose' is available" >&2
    exit 1
fi

cd "$APP_DIR"

echo "=======================================" | tee -a "$LOG_FILE"
echo " ECR Deploy — $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a "$LOG_FILE"
echo "=======================================" | tee -a "$LOG_FILE"

# ── 1. Sync repo (still needed for compose files, migrations, Caddyfile) ──
echo "[1/5] Syncing repo..." | tee -a "$LOG_FILE"
git fetch origin main
git reset --hard origin/main
COMMIT_SHA="$(git rev-parse HEAD)"
echo "  Commit: ${COMMIT_SHA:0:7}" | tee -a "$LOG_FILE"

# ── 2. Authenticate with ECR ─────────────────────────────────
# Uses the EC2 instance profile (attached by provision_ecr.py).
# `docker login` writes ~/.docker/config.json; that stays valid for 12 h.
echo "[2/5] Authenticating with ECR..." | tee -a "$LOG_FILE"
if ! aws ecr get-login-password --region "$AWS_REGION" \
        | docker login --username AWS --password-stdin "$ECR_REGISTRY" \
        2>&1 | tee -a "$LOG_FILE"
then
    echo "" | tee -a "$LOG_FILE"
    echo "!! ECR auth FAILED. Fall back to in-VPS build:" | tee -a "$LOG_FILE"
    echo "   /opt/IntelPulse/scripts/deploy.sh" | tee -a "$LOG_FILE"
    exit 1
fi

# ── 3. Pull images (tagged by this commit SHA, or `latest`) ──
IMAGE_TAG="${IMAGE_TAG:-$COMMIT_SHA}"
export IMAGE_TAG
echo "[3/5] Pulling ECR images with tag=$IMAGE_TAG..." | tee -a "$LOG_FILE"
if ! $COMPOSE -f "$COMPOSE_BASE" -f "$COMPOSE_ECR" pull api ui worker scheduler \
        2>&1 | tail -20 | tee -a "$LOG_FILE"
then
    echo "  Tagged pull failed — retrying with IMAGE_TAG=latest..." | tee -a "$LOG_FILE"
    IMAGE_TAG=latest
    export IMAGE_TAG
    $COMPOSE -f "$COMPOSE_BASE" -f "$COMPOSE_ECR" pull api ui worker scheduler \
        2>&1 | tail -20 | tee -a "$LOG_FILE"
fi

# ── 4. Run migrations against the running postgres container ──
# Same shape as scripts/deploy.sh — idempotent SQL with IF NOT EXISTS.
echo "[4/5] Running SQL migrations..." | tee -a "$LOG_FILE"
POSTGRES_CONTAINER=$($COMPOSE ps -q postgres 2>/dev/null || echo "")
if [ -n "$POSTGRES_CONTAINER" ]; then
    for migration in db/migrations/*.sql; do
        if [ -f "$migration" ]; then
            BASENAME=$(basename "$migration")
            echo "  Applying $BASENAME..." | tee -a "$LOG_FILE"
            docker exec -i "$POSTGRES_CONTAINER" \
                psql -U ti -d ti_platform < "$migration" 2>&1 \
                | tail -3 | tee -a "$LOG_FILE"
        fi
    done
fi

# ── 5. Up -d (no --build; images came from pull) ─────────────
echo "[5/5] Starting services..." | tee -a "$LOG_FILE"
$COMPOSE -f "$COMPOSE_BASE" -f "$COMPOSE_ECR" up -d --remove-orphans \
    2>&1 | tee -a "$LOG_FILE"

# Caddyfile bind-mount freshness (see scripts/deploy.sh).
if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -qE '^caddy/'; then
    echo "  Caddyfile changed — restarting caddy to re-bind mount..." \
        | tee -a "$LOG_FILE"
    $COMPOSE -f "$COMPOSE_BASE" -f "$COMPOSE_ECR" restart caddy \
        2>&1 | tail -3 | tee -a "$LOG_FILE"
fi

# Health wait.
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    HEALTHY=$($COMPOSE ps --format json 2>/dev/null | grep -c '"healthy"' || true)
    if [ "$HEALTHY" -ge 3 ]; then
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

echo "" | tee -a "$LOG_FILE"
echo "Deploy complete. Services:" | tee -a "$LOG_FILE"
$COMPOSE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" \
    2>/dev/null | tee -a "$LOG_FILE"

API_STATUS=$(curl -sf http://localhost:8000/api/v1/health | head -c 200 || echo "UNREACHABLE")
echo "" | tee -a "$LOG_FILE"
echo "API Health: $API_STATUS" | tee -a "$LOG_FILE"
echo "=======================================" | tee -a "$LOG_FILE"
