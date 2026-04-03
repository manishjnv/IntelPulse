# Security Setup Guide

This guide walks you through securing your IntelPulse deployment.

## Quick Start

### 1. Generate Secrets

Run the secrets generation script:

```bash
./scripts/generate_secrets.sh > .env.secrets
```

This generates:
- JWT secret key (for token signing)
- PostgreSQL password
- Redis password  
- OpenSearch password

### 2. Create .env File

Copy the production example:

```bash
cp .env.production.example .env
```

Then fill in the secrets from step 1:

```bash
# Merge generated secrets into .env
cat .env.secrets >> .env
```

### 3. Verify .gitignore

Ensure `.env` is in `.gitignore`:

```bash
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

### 4. Set Additional Secrets

Add your API keys and OAuth credentials to `.env`:

```bash
# Google OAuth (get from https://console.cloud.google.com)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Threat Feed API Keys
NVD_API_KEY=your-nvd-key
VIRUSTOTAL_API_KEY=your-vt-key
SHODAN_API_KEY=your-shodan-key
# ... etc
```

### 5. Validate Configuration

Run the validation script:

```bash
python scripts/validate_security.py
```

This checks:
- All required secrets are set
- Secrets meet minimum length requirements
- No default/weak passwords are used
- CORS configuration is secure

## Production Deployment

### AWS Secrets Manager (Recommended)

For AWS deployments, use Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name intelpulse/production \
  --secret-string file://.env.secrets \
  --region ap-south-1

# Update ECS task definition to reference secret
# See docs/AWS_SETUP_GUIDE.md for details
```

### Environment Variables

For ECS/Fargate, set environment variables in task definition:

```json
{
  "environment": [
    {"name": "ENVIRONMENT", "value": "production"},
    {"name": "DOMAIN", "value": "intelpulse.tech"}
  ],
  "secrets": [
    {
      "name": "SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:intelpulse/production:SECRET_KEY::"
    }
  ]
}
```

## Security Checklist

### Before First Deployment

- [ ] Generated strong secrets (32+ characters)
- [ ] Created `.env` file with all required variables
- [ ] Verified `.env` is in `.gitignore`
- [ ] Set CORS origins to specific domains (no wildcards)
- [ ] Configured Google OAuth with production callback URL
- [ ] Obtained API keys for threat feeds
- [ ] Set up SMTP for email OTP (if using)

### Production Configuration

- [ ] `ENVIRONMENT=production`
- [ ] `SECRET_KEY` is randomly generated (not default)
- [ ] All database passwords are strong
- [ ] HTTPS is enforced
- [ ] Rate limiting is enabled
- [ ] Security headers are configured
- [ ] Audit logging is enabled

### Post-Deployment

- [ ] Test authentication flow
- [ ] Verify HTTPS certificate
- [ ] Check security headers (use securityheaders.com)
- [ ] Test rate limiting
- [ ] Review audit logs
- [ ] Set up monitoring and alerts
- [ ] Configure automated backups
- [ ] Document incident response procedures

## Security Maintenance

### Regular Tasks

**Weekly:**
- Review audit logs for suspicious activity
- Check for failed authentication attempts
- Monitor rate limit violations

**Monthly:**
- Update dependencies (npm audit, pip-audit)
- Review and rotate API keys
- Test backup restoration
- Review access logs

**Quarterly:**
- Rotate all secrets (SECRET_KEY, database passwords)
- Security audit and penetration testing
- Review and update security policies
- Update disaster recovery procedures

### Secret Rotation

To rotate secrets:

1. Generate new secrets:
   ```bash
   ./scripts/generate_secrets.sh > .env.new
   ```

2. Update secrets in AWS Secrets Manager or .env

3. Restart services with zero-downtime:
   ```bash
   # ECS will automatically pick up new secrets
   aws ecs update-service --force-new-deployment \
     --service intelpulse-api --cluster intelpulse
   ```

4. Verify services are healthy

5. Revoke old secrets after 24 hours

## Incident Response

If a security incident occurs:

1. **Immediate Actions:**
   - Rotate all secrets immediately
   - Review audit logs for unauthorized access
   - Disable compromised accounts
   - Block suspicious IP addresses

2. **Investigation:**
   - Determine scope of breach
   - Identify affected data
   - Document timeline of events

3. **Remediation:**
   - Patch vulnerabilities
   - Update security controls
   - Notify affected users (if required)

4. **Post-Incident:**
   - Conduct root cause analysis
   - Update security procedures
   - Implement additional controls
   - Document lessons learned

## Compliance

### Data Protection

- All data in transit is encrypted (TLS 1.2+)
- Sensitive data at rest is encrypted
- PII is minimized and protected
- Data retention policies are enforced

### Audit Logging

All security-relevant events are logged:
- Authentication attempts (success/failure)
- Authorization failures
- Data access and modifications
- Configuration changes
- Security policy violations

### Access Control

- Principle of least privilege
- Role-based access control (RBAC)
- Multi-factor authentication (MFA) for admin acco