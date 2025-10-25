# CAPP Security Documentation

**Version**: 1.0.0
**Last Updated**: 2025-10-25
**Status**: Phase 1 Security Hardening - Complete

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Rate Limiting](#rate-limiting)
4. [Input Validation](#input-validation)
5. [Security Headers](#security-headers)
6. [Secrets Management](#secrets-management)
7. [CORS Configuration](#cors-configuration)
8. [Security Best Practices](#security-best-practices)
9. [Reporting Security Issues](#reporting-security-issues)

---

## Overview

CAPP implements comprehensive security measures to protect against common web vulnerabilities and ensure safe handling of financial transactions. This document outlines all security features and best practices.

### Security Features Implemented

- ✅ JWT-based authentication with refresh tokens
- ✅ Role-based access control (RBAC)
- ✅ Rate limiting to prevent abuse
- ✅ Input validation and sanitization
- ✅ Security headers (XSS, Clickjacking protection)
- ✅ CORS whitelist configuration
- ✅ Secrets validation on startup
- ✅ Password strength requirements
- ✅ Account lockout after failed login attempts
- ✅ Structured security logging

---

## Authentication & Authorization

### JWT Authentication

CAPP uses JSON Web Tokens (JWT) for stateless authentication.

#### Token Types

1. **Access Token**: Short-lived (30 minutes by default)
   - Used for API authentication
   - Must be included in Authorization header: `Bearer <token>`

2. **Refresh Token**: Long-lived (7 days by default)
   - Used to obtain new access tokens
   - Should be stored securely on the client

#### Authentication Flow

```
1. User login → POST /api/v1/auth/login
2. Server validates credentials
3. Server returns access_token + refresh_token
4. Client stores tokens securely
5. Client includes access_token in subsequent requests
6. When access_token expires, use refresh_token → POST /api/v1/auth/refresh
```

#### Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

#### User Roles

- **ADMIN**: Full system access
- **USER**: Standard user access
- **OPERATOR**: Payment operator access
- **AGENT**: Agent-specific operations
- **READONLY**: Read-only access

### Protected Endpoints

The following endpoints require authentication:

- `POST /api/v1/payments/create`
- `GET /api/v1/payments/{id}/status`
- `POST /api/v1/payments/{id}/cancel`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/change-password`
- `GET /api/v1/auth/me`

### Implementation Example

```python
from fastapi import Depends
from ...api.dependencies.auth import get_current_active_user, require_admin

# Require any authenticated user
@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    return {"message": f"Hello {current_user.email}"}

# Require admin role
@router.get("/admin")
async def admin_endpoint(
    current_user: User = Depends(require_admin)
):
    return {"message": "Admin access granted"}
```

### Account Security Features

1. **Failed Login Protection**
   - Account locked after 5 failed login attempts
   - Status changes to SUSPENDED
   - Manual unlocking required

2. **Session Management**
   - Tokens cannot be revoked server-side (use short expiration)
   - Client must discard tokens on logout
   - Consider implementing token blacklist for production

---

## Rate Limiting

Rate limiting protects against brute force attacks and API abuse.

### Rate Limits by Endpoint Type

| Endpoint Category | Limit | Purpose |
|------------------|-------|---------|
| Registration | 5/minute | Prevent account spam |
| Login | 10/minute | Prevent brute force |
| Token Refresh | 20/minute | Allow normal usage |
| Password Change | 5/hour | Prevent automated attacks |
| Default (All others) | 100/minute, 1000/hour | General protection |

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 60
```

### Rate Limit Exceeded Response

```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

**Status Code**: 429 Too Many Requests
**Retry-After**: 60 seconds

### Configuration

Rate limits are configured in `.env`:

```env
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
```

---

## Input Validation

CAPP implements multiple layers of input validation.

### Validation Layers

1. **Pydantic Models**: Type validation and data parsing
2. **Custom Validators**: Business logic validation
3. **Security Middleware**: Injection attack detection
4. **Size Limits**: Request body size limits (10MB)

### Protected Against

- ✅ SQL Injection
- ✅ XSS (Cross-Site Scripting)
- ✅ Path Traversal
- ✅ Command Injection
- ✅ Null Byte Injection
- ✅ Oversized Requests

### Validation Middleware

The `RequestValidationMiddleware` checks:
- Request size limits
- Content type validation
- SQL injection patterns
- XSS patterns
- Path traversal attempts

### Example: Safe Input Handling

```python
from ...core.validation import (
    sanitize_string,
    validate_no_sql_injection,
    validate_no_xss
)

# Sanitize user input
clean_input = sanitize_string(user_input, max_length=255)

# Validate against injection
safe_input = validate_no_sql_injection(clean_input)
safe_input = validate_no_xss(safe_input)
```

---

## Security Headers

CAPP adds security headers to all HTTP responses.

### Headers Implemented

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), ...
```

### Content Security Policy (CSP)

Current CSP directives:

```
default-src 'self'
script-src 'self' 'unsafe-inline' 'unsafe-eval'
style-src 'self' 'unsafe-inline'
img-src 'self' data: https:
font-src 'self' data:
connect-src 'self'
frame-ancestors 'none'
base-uri 'self'
form-action 'self'
```

**Note**: Adjust CSP for production to remove 'unsafe-inline' and 'unsafe-eval'

### Protection Against

- **Clickjacking**: X-Frame-Options: DENY
- **MIME Sniffing**: X-Content-Type-Options: nosniff
- **XSS**: X-XSS-Protection + CSP
- **Information Leakage**: Referrer-Policy
- **Feature Abuse**: Permissions-Policy

---

## Secrets Management

### Secrets Validation

The application validates all secrets on startup:

- Checks for insecure default values
- Validates secret strength (length, complexity)
- Ensures production secrets are configured
- Logs security warnings

### Secret Requirements

1. **SECRET_KEY**
   - Minimum 32 characters
   - High entropy (mixed character types)
   - Never use default values

2. **API Keys**
   - Unique per environment
   - Rotated regularly (90 days recommended)
   - Stored in environment variables

### Generating Secure Secrets

```python
from ...core.secrets import generate_secret_key

# Generate a new secret key
secret_key = generate_secret_key(length=64)
print(f"SECRET_KEY={secret_key}")
```

### Environment Variables

Required secrets (see `.env.example`):

```env
SECRET_KEY=<64-char-random-string>
APTOS_PRIVATE_KEY=<your-aptos-private-key>
APTOS_ACCOUNT_ADDRESS=<your-aptos-address>
MMO_MPESA_CONSUMER_KEY=<your-mpesa-key>
MMO_MPESA_CONSUMER_SECRET=<your-mpesa-secret>
```

### Production Secrets Checklist

- [ ] All default secrets replaced
- [ ] SECRET_KEY is 64+ characters
- [ ] MMO credentials configured
- [ ] Blockchain credentials configured
- [ ] Secrets stored in secure vault (AWS Secrets Manager, HashiCorp Vault)
- [ ] Secrets rotation schedule established

---

## CORS Configuration

### Default Configuration

CORS is restricted to whitelisted origins only.

```python
# .env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Production Configuration

For production, only allow your frontend domains:

```env
ALLOWED_ORIGINS=https://app.capp.com,https://www.capp.com
```

### CORS Settings

```python
allow_origins=settings.ALLOWED_ORIGINS  # Whitelist only
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"]
```

**⚠️ NEVER use allow_origins=["*"] in production!**

---

## Security Best Practices

### For Developers

1. **Never Commit Secrets**
   - Use `.env` files (git-ignored)
   - Use environment variables
   - Consider secrets management tools

2. **Validate All Inputs**
   - Use Pydantic models
   - Add custom validators
   - Sanitize user input

3. **Follow Principle of Least Privilege**
   - Use appropriate user roles
   - Grant minimum required permissions
   - Review access regularly

4. **Keep Dependencies Updated**
   ```bash
   pip list --outdated
   pip install -U package-name
   ```

5. **Enable Logging**
   - Monitor authentication failures
   - Log security events
   - Review logs regularly

### For DevOps

1. **HTTPS Only**
   - Enable HSTS header in production
   - Use valid SSL certificates
   - Redirect HTTP to HTTPS

2. **Database Security**
   - Use strong credentials
   - Enable SSL connections
   - Restrict network access
   - Regular backups

3. **Network Security**
   - Use firewall rules
   - Restrict port access
   - Use VPC/private networks
   - DDoS protection

4. **Monitoring**
   - Set up Sentry for error tracking
   - Monitor API usage
   - Alert on suspicious activity
   - Regular security audits

### For Users

1. **Strong Passwords**
   - Use password managers
   - Enable 2FA (when available)
   - Don't reuse passwords

2. **Secure Storage**
   - Store tokens securely
   - Use HttpOnly cookies when possible
   - Never log tokens

3. **Logout Properly**
   - Discard tokens on logout
   - Clear sensitive data
   - Use secure devices

---

## Security Checklist

Before deploying to production:

### Application Security
- [ ] All default secrets replaced
- [ ] CORS configured with specific origins
- [ ] Rate limiting enabled
- [ ] Input validation active
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Debug mode disabled
- [ ] Error messages don't leak information

### Infrastructure Security
- [ ] Firewall rules configured
- [ ] Database encrypted at rest
- [ ] SSL/TLS certificates valid
- [ ] Secrets in secure vault
- [ ] Monitoring and alerting setup
- [ ] Backup and recovery tested
- [ ] DDoS protection enabled
- [ ] Security patches applied

### Compliance
- [ ] GDPR compliance (if applicable)
- [ ] PCI DSS compliance (for payments)
- [ ] Data retention policies
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Security policy documented

---

## Reporting Security Issues

### Responsible Disclosure

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email security@capp.com with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

3. Allow 90 days for resolution before public disclosure
4. We will acknowledge receipt within 24-48 hours

### Bug Bounty

Coming soon: Details on our bug bounty program.

---

## Security Roadmap

### Phase 2 (Upcoming)

- [ ] Two-factor authentication (2FA)
- [ ] Token blacklist/revocation
- [ ] IP whitelisting for admin endpoints
- [ ] Advanced fraud detection
- [ ] Webhook signature verification
- [ ] API key rotation automation
- [ ] Security audit logging to external service
- [ ] Penetration testing

### Phase 3 (Future)

- [ ] SOC 2 compliance
- [ ] Biometric authentication
- [ ] Advanced threat detection
- [ ] Zero-trust architecture
- [ ] Formal security certification

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**Last Review**: 2025-10-25
**Next Review**: 2025-11-25
**Document Owner**: Security Team
