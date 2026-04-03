#!/bin/bash
# Generate secure secrets for production deployment

echo "# ============================================="
echo "# IntelPulse Production Secrets"
echo "# ============================================="
echo "# Generated: $(date)"
echo "# IMPORTANT: Store these securely and never commit to git!"
echo ""
echo "# Copy these to your .env file or secrets manager"
echo ""

echo "# JWT Secret Key (32 bytes hex)"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo ""

echo "# PostgreSQL Password (32 bytes base64)"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo ""

echo "# Redis Password (32 bytes base64)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo ""

echo "# OpenSearch Password (32 bytes base64)"
echo "OPENSEARCH_PASSWORD=$(openssl rand -base64 32)"
echo ""

echo "# ============================================="
echo "# Next Steps:"
echo "# 1. Copy these values to your .env file"
echo "# 2. Update docker-compose.yml to use environment variables"
echo "# 3. Never commit .env to version control"
echo "# 4. Rotate these secrets every 90 days"
echo "# ============================================="
