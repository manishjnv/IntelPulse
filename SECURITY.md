# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in IntelPulse, please report it by emailing security@intelpulse.tech (or create a private security advisory on GitHub).

**Please do not report security vulnerabilities through public GitHub issues.**

## Security Best Practices

### 1. Secrets Management

**CRITICAL**: Never commit secrets to version control!

- All production secrets must be stored in environment variables
- Use `.env` file for local development (never commit this file)
- Use AWS Secrets Manager or similar for production deployments
- Rotate secrets regularly (at least every 90 days)

### 2. Required Environment Variables

Before deploying to production, ensure these are set:

```bash
# Generate strong secrets
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
OPENSEARCH_PASSWORD=$(openssl rand -base64 32)
```

### 3. Production Deployment Checklist

- [ ] All secrets are stored in environment variables or secrets manager
- [ ] `SECRET_KEY` is at least 32 characters and randomly generated
- [ ] Database passwords are strong (32+ characters)
- [ ] Redis password is set and strong
- [ ] CORS origins are explicitly listed (no wildcards)
- [ ] HTTPS is enforced (Strict-Transport-Security header)
- [ ] Rate limiting is enabled
- [ ] Security headers are configured
- [ ] API keys for external services are rotated
- [ ] Audit logging is enabled
- [ ] Backups are configured and tested

### 4. CORS Configuration

In production, explicitly list allowed origins:

```bash
CORS_ORIGINS=https://intelpulse.tech,https://www.intelpulse.tech
```

**Never use wildcards (`*`) with `allow_credentials=True`**

### 5. Rate Limiting

The application includes built-in rate limiting:

- General API: 100 requests/minute per IP
- OTP send: 3 requests/minute per IP
- OTP verify: 5 requests/minute per IP
- OAuth callbacks: 10 requests/minute per IP

### 6. Authentication Security

- JWT tokens expire after 8 hours (configurable)
- Sessions are stored in Redis for server-side validation
- Cookies use `httponly`, `secure`, and `samesite=strict` flags
- OTP codes expire after 5 minutes
- Failed authentication attempts are logged

### 7. Input Validation

- All user input is validated and sanitized
- SQL queries use parameterized statements
- Search queries are length-limited (200 characters)
- Email addresses are validated (max 254 characters)
- Sort columns are whitelisted

### 8. Security Headers

The following security headers are automatically added:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)

### 9. Database Security

- Use separate database users with minimal privileges
- Enable SSL/TLS for database connections in production
- Regular backups with encryption at rest
- Audit logging for sensitive operations

### 10. Redis Security

- Always set a strong password
- Disable dangerous commands (REPLICAOF, SLAVEOF, DEBUG, CONFIG)
- Use protected mode
- Bind to localhost or private network only

## Security Updates

- Keep all dependencies up to date
- Monitor security advisories for Python, Node.js, and Docker images
- Apply security patches promptly
- Review and update this policy regularly

## Compliance

- All passwords are hashed using industry-standard algorithms
- Sensitive data is encrypted in transit (HTTPS/TLS)
- Audit logs capture authentication and authorization events
- PII is handled according to GDPR/privacy regulations

## Contact

For security concerns, contact: security@intelpulse.tech
