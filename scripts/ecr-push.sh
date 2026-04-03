#!/bin/bash
set -e

# IntelPulse - ECR Image Build and Push Script
# This script builds Docker images and pushes them to AWS ECR

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-604275788592}"
GIT_SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# ECR repository URIs
API_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/intelpulse/api"
UI_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/intelpulse/ui"
WORKER_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/intelpulse/worker"

echo "========================================="
echo "IntelPulse - ECR Image Build and Push"
echo "========================================="
echo "Region: ${AWS_REGION}"
echo "Account: ${AWS_ACCOUNT_ID}"
echo "Git SHA: ${GIT_SHA}"
echo "Timestamp: ${TIMESTAMP}"
echo "========================================="

# Step 1: Login to ECR
echo ""
echo "Step 1: Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
echo "✓ ECR login successful"

# Step 2: Build API image
echo ""
echo "Step 2: Building API image..."
docker build -f docker/Dockerfile.api -t intelpulse-api:${GIT_SHA} -t intelpulse-api:latest .
echo "✓ API image built"

# Step 3: Build UI image
echo ""
echo "Step 3: Building UI image..."
docker build -f docker/Dockerfile.ui -t intelpulse-ui:${GIT_SHA} -t intelpulse-ui:latest .
echo "✓ UI image built"

# Step 4: Build Worker image
echo ""
echo "Step 4: Building Worker image..."
docker build -f docker/Dockerfile.worker -t intelpulse-worker:${GIT_SHA} -t intelpulse-worker:latest .
echo "✓ Worker image built"

# Step 5: Tag images for ECR
echo ""
echo "Step 5: Tagging images for ECR..."
docker tag intelpulse-api:${GIT_SHA} ${API_REPO}:${GIT_SHA}
docker tag intelpulse-api:latest ${API_REPO}:latest
docker tag intelpulse-ui:${GIT_SHA} ${UI_REPO}:${GIT_SHA}
docker tag intelpulse-ui:latest ${UI_REPO}:latest
docker tag intelpulse-worker:${GIT_SHA} ${WORKER_REPO}:${GIT_SHA}
docker tag intelpulse-worker:latest ${WORKER_REPO}:latest
echo "✓ Images tagged"

# Step 6: Push API images
echo ""
echo "Step 6: Pushing API images to ECR..."
docker push ${API_REPO}:${GIT_SHA}
docker push ${API_REPO}:latest
echo "✓ API images pushed"

# Step 7: Push UI images
echo ""
echo "Step 7: Pushing UI images to ECR..."
docker push ${UI_REPO}:${GIT_SHA}
docker push ${UI_REPO}:latest
echo "✓ UI images pushed"

# Step 8: Push Worker images
echo ""
echo "Step 8: Pushing Worker images to ECR..."
docker push ${WORKER_REPO}:${GIT_SHA}
docker push ${WORKER_REPO}:latest
echo "✓ Worker images pushed"

echo ""
echo "========================================="
echo "✓ All images successfully pushed to ECR"
echo "========================================="
echo ""
echo "Image URIs:"
echo "  API:    ${API_REPO}:${GIT_SHA}"
echo "  UI:     ${UI_REPO}:${GIT_SHA}"
echo "  Worker: ${WORKER_REPO}:${GIT_SHA}"
echo ""
echo "Latest tags:"
echo "  API:    ${API_REPO}:latest"
echo "  UI:     ${UI_REPO}:latest"
echo "  Worker: ${WORKER_REPO}:latest"
echo ""
