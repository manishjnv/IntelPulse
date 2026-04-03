#!/bin/bash
# Quick start script for IntelPulse Bedrock Demo

set -e

echo "=================================================="
echo "IntelPulse AWS Bedrock Demo - Quick Start"
echo "=================================================="
echo ""

# Check if running on EC2
if [ ! -f /sys/hypervisor/uuid ] || ! grep -q ec2 /sys/hypervisor/uuid 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for EC2 instances"
    echo "   You can still run it locally, but Bedrock IAM role may not work"
    echo ""
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "   Install with: sudo apt install docker.io docker-compose"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    echo "   Install with: sudo apt install docker-compose"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file with secure passwords..."
    cat > .env <<EOF
# Database
POSTGRES_USER=ti
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=ti_platform

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32)

# Application
SECRET_KEY=$(openssl rand -base64 32)
ENVIRONMENT=production
LOG_LEVEL=INFO

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AI_API_URL=bedrock
AI_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
AI_TIMEOUT=30
AI_ENABLED=true

# Domain (use EC2 public IP for demo)
DOMAIN=localhost
DOMAIN_UI=http://localhost
DOMAIN_API=http://localhost:8000

# Auth (bypass for demo)
DEV_BYPASS_AUTH=true
JWT_EXPIRE_MINUTES=480
EOF
    echo "✅ .env file created"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Check if docker-compose.demo.yml exists
if [ ! -f docker-compose.demo.yml ]; then
    echo "📝 Creating docker-compose.demo.yml..."
    cat > docker-compose.demo.yml <<'EOF'
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ti}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-ti_platform}
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ti}"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_DB: ${POSTGRES_DB:-ti_platform}
      POSTGRES_USER: ${POSTGRES_USER:-ti}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      AWS_REGION: ${AWS_REGION:-us-east-1}
      AI_API_URL: bedrock
      AI_MODEL: ${AI_MODEL}
      AI_ENABLED: "true"
      ENVIRONMENT: production
      LOG_LEVEL: INFO
      DEV_BYPASS_AUTH: "true"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pg_data:
  redis_data:
EOF
    echo "✅ docker-compose.demo.yml created"
    echo ""
else
    echo "✅ docker-compose.demo.yml already exists"
    echo ""
fi

# Check AWS credentials
echo "🔍 Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials configured"
    IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)
    echo "   Identity: $IDENTITY"
    echo ""
else
    echo "⚠️  AWS credentials not found"
    echo "   Make sure EC2 instance has IAM role with Bedrock permissions"
    echo "   Or configure AWS credentials: aws configure"
    echo ""
fi

# Check Bedrock access
echo "🔍 Checking Bedrock access..."
if aws bedrock list-foundation-models --region us-east-1 &> /dev/null; then
    echo "✅ Bedrock access confirmed"
    echo ""
else
    echo "⚠️  Cannot access Bedrock"
    echo "   Make sure IAM role has bedrock:InvokeModel permission"
    echo ""
fi

# Build and start services
echo "🏗️  Building Docker images (this may take 5-10 minutes)..."
docker-compose -f docker-compose.demo.yml build

echo ""
echo "🚀 Starting services..."
docker-compose -f docker-compose.demo.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.demo.yml ps

echo ""
echo "=================================================="
echo "✅ Demo is ready!"
echo "=================================================="
echo ""

# Get public IP if on EC2
if command -v ec2-metadata &> /dev/null; then
    PUBLIC_IP=$(ec2-metadata --public-ipv4 | cut -d " " -f 2)
    echo "🌐 Public IP: $PUBLIC_IP"
    echo ""
    echo "📚 API Documentation: http://$PUBLIC_IP:8000/api/docs"
    echo ""
    echo "🧪 Test the demo endpoint:"
    echo "   curl -X POST http://$PUBLIC_IP:8000/api/v1/demo/analyze \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"ioc\": \"malicious-domain.com\", \"ioc_type\": \"domain\"}'"
else
    echo "📚 API Documentation: http://localhost:8000/api/docs"
    echo ""
    echo "🧪 Test the demo endpoint:"
    echo "   curl -X POST http://localhost:8000/api/v1/demo/analyze \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"ioc\": \"malicious-domain.com\", \"ioc_type\": \"domain\"}'"
fi

echo ""
echo "📋 View logs:"
echo "   docker-compose -f docker-compose.demo.yml logs -f api"
echo ""
echo "🛑 Stop demo:"
echo "   docker-compose -f docker-compose.demo.yml down"
echo ""
