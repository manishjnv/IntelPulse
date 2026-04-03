#!/bin/bash
# Setup billing alerts for IntelPulse demo

echo "Setting up billing alerts..."

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# Create SNS topic for billing alerts
echo "Creating SNS topic..."
TOPIC_ARN=$(aws sns create-topic --name IntelPulse-Billing-Alerts --output text)
echo "Topic ARN: $TOPIC_ARN"

# Subscribe your email (replace with your email)
echo "Subscribe to alerts by running:"
echo "aws sns subscribe --topic-arn $TOPIC_ARN --protocol email --notification-endpoint YOUR_EMAIL@example.com"

# Create billing alarm at $50
echo "Creating $50 billing alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "IntelPulse-Cost-Alert-50" \
  --alarm-description "Alert when costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions $TOPIC_ARN \
  --region us-east-1

# Create billing alarm at $80
echo "Creating $80 billing alarm..."
aws cloudwatch put-metric-alarm \
  --alarm-name "IntelPulse-Cost-Alert-80" \
  --alarm-description "Alert when costs exceed $80" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions $TOPIC_ARN \
  --region us-east-1

echo "✅ Billing alerts configured!"
echo "You will receive email notifications at $50 and $80 spend"
