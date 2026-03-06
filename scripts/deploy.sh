#!/bin/bash
# =============================================
# IntelWatch TI Platform — Deploy Script
# =============================================
# Called by GitHub Actions CI/CD or manually.
# Usage: /opt/ti-platform/scripts/deploy.sh
# =============================================
set -euo pipefail

APP_DIR="/opt/ti-platform"
COMPOSE_FILE="docker-compose.yml"
LOG_FILE="/opt/ti-platform/deploy.log"

cd "$APP_DIR"

echo "=======================================" | tee -a "$LOG_FILE"
echo " Deploying IntelWatch — $(date -u '+%Y-%m-%d %H:%M:%S UTC')" | tee -a "$LOG_FILE"
echo "=======================================" | tee -a "$LOG_FILE"

# ── 1. Pull latest code ───────────────────────────────
echo "[1/5] Pulling latest code..." | tee -a "$LOG_FILE"
git fetch origin main
git reset --hard origin/main
echo "  Commit: $(git rev-parse --short HEAD)" | tee -a "$LOG_FILE"

# ── 2. Build images ───────────────────────────────────
echo "[2/5] Building Docker images..." | tee -a "$LOG_FILE"
docker compose -f "$COMPOSE_FILE" build --parallel 2>&1 | tail -5 | tee -a "$LOG_FILE"

# ── 3. Run SQL migrations ─────────────────────────────
echo "[3/6] Running SQL migrations..." | tee -a "$LOG_FILE"
POSTGRES_CONTAINER=$(docker compose ps -q postgres 2>/dev/null || echo "")
if [ -n "$POSTGRES_CONTAINER" ]; then
    for migration in db/migrations/*.sql; do
        if [ -f "$migration" ]; then
            BASENAME=$(basename "$migration")
            echo "  Applying $BASENAME..." | tee -a "$LOG_FILE"
            docker exec -i "$POSTGRES_CONTAINER" psql -U ti -d ti_platform < "$migration" 2>&1 | tail -3 | tee -a "$LOG_FILE"
        fi
    done
else
    echo "  WARNING: postgres container not running — skipping migrations" | tee -a "$LOG_FILE"
fi

# ── 4. Restart services ───────────────────────────────
echo "[4/6] Starting services..." | tee -a "$LOG_FILE"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans 2>&1 | tee -a "$LOG_FILE"

# ── 5. Wait for health checks ─────────────────────────
echo "[5/6] Waiting for health checks..." | tee -a "$LOG_FILE"
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    HEALTHY=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || true)
    TOTAL=$(docker compose ps --format json 2>/dev/null | wc -l || true)
    echo "  Health: $HEALTHY/$TOTAL services healthy ($ELAPSED s)" | tee -a "$LOG_FILE"
    if [ "$HEALTHY" -ge 3 ]; then
        break
    fi
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

# ── 6. Cleanup ─────────────────────────────────────────
echo "[6/6] Cleaning up old images..." | tee -a "$LOG_FILE"
docker image prune -f --filter "until=48h" 2>&1 | tail -1 | tee -a "$LOG_FILE"

# ── Summary ────────────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Deploy complete! Services:" | tee -a "$LOG_FILE"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | tee -a "$LOG_FILE"

# Quick health check
API_STATUS=$(curl -sf http://localhost:8000/api/v1/health | head -c 200 || echo "UNREACHABLE")
echo "" | tee -a "$LOG_FILE"
echo "API Health: $API_STATUS" | tee -a "$LOG_FILE"
echo "=======================================" | tee -a "$LOG_FILE"
