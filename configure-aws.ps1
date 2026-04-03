# AWS Configuration Script
# This script will help you configure AWS CLI credentials

Write-Host "AWS CLI Configuration" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green
Write-Host ""

# Run aws configure
aws configure

Write-Host ""
Write-Host "Configuration complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Verifying AWS credentials..." -ForegroundColor Yellow

# Verify credentials
aws sts get-caller-identity

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ AWS credentials configured successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Bootstrap CDK: cd infra && npx cdk bootstrap" -ForegroundColor White
    Write-Host "2. Deploy stack: npx cdk deploy IntelPulseStack" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "✗ AWS credential verification failed" -ForegroundColor Red
    Write-Host "Please check your access key and secret key" -ForegroundColor Yellow
}
