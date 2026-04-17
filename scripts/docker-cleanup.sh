#!/bin/bash
# ============================================================
# IntelPulse TI Platform — Weekly Docker cleanup
# ============================================================
# Runs via cron (weekly, Sunday 03:00 UTC). Kept OUT of deploy.sh so
# Docker layer cache survives between deploys for faster builds.
#
# Install once on EC2:
#   (crontab -l 2>/dev/null; \
#    echo '0 3 * * 0 /opt/IntelPulse/scripts/docker-cleanup.sh >> /opt/IntelPulse/docker-cleanup.log 2>&1') \
#     | crontab -
#
# Prunes:
#   - Dangling images (no tag, no reference)
#   - Build cache older than 7 days
#   - Stopped containers older than 7 days
# ============================================================
set -euo pipefail

LOG_FILE="/opt/IntelPulse/docker-cleanup.log"

echo "=== Docker cleanup — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ===" | tee -a "$LOG_FILE"

# Disk use before
df -h / | tail -1 | awk '{print "Disk before: " $3 " used / " $2 " (" $5 ")"}' | tee -a "$LOG_FILE"

# Dangling images (cheap, always safe)
docker image prune -f 2>&1 | tail -1 | tee -a "$LOG_FILE"

# Build cache older than 7 days — keeps recent layers for fast deploys
docker builder prune -f --filter "until=168h" 2>&1 | tail -1 | tee -a "$LOG_FILE"

# Stopped containers older than 7 days
docker container prune -f --filter "until=168h" 2>&1 | tail -1 | tee -a "$LOG_FILE"

# Disk use after
df -h / | tail -1 | awk '{print "Disk after:  " $3 " used / " $2 " (" $5 ")"}' | tee -a "$LOG_FILE"

echo "=== done ===" | tee -a "$LOG_FILE"
