# Security Setup Guide

Quick guide to setting up security features in CAPP.

## 1. Generate Secrets

```bash
# Generate a secure SECRET_KEY
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(64)))"
```

## 2. Configure Environment Variables

Copy `.env.example` to `.env` and update:

```env
# CRITICAL: Change these before deploying!
SECRET_KEY=<your-64-character-secret>
ENVIRONMENT=production
DEBUG=false

# CORS: Only allow your frontend domains
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Database with SSL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require

# Redis
REDIS_URL=redis://localhost:6379

# Blockchain credentials (replace demo values)
APTOS_PRIVATE_KEY=<your-real-private-key>
APTOS_ACCOUNT_ADDRESS=<your-real-address>

# MMO Provider Credentials
MMO_MPESA_CONSUMER_KEY=<real-key>
MMO_MPESA_CONSUMER_SECRET=<real-secret>
MMO_MPESA_BUSINESS_SHORT_CODE=<real-code>
MMO_MPESA_PASSKEY=<real-passkey>

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
```

## 3. Test Authentication

### Register a new user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "phone_number": "+1234567890"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Use the access token

```bash
TOKEN="<your-access-token>"

curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Create a payment (authenticated)

```bash
curl -X POST http://localhost:8000/api/v1/payments/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_id": "PAY-001",
    "payment_type": "personal_remittance",
    "payment_method": "mobile_money",
    "amount": 1000,
    "from_currency": "KES",
    "to_currency": "UGX",
    "sender_name": "John Doe",
    "sender_phone": "+254712345678",
    "sender_country": "KE",
    "recipient_name": "Jane Doe",
    "recipient_phone": "+256712345678",
    "recipient_country": "UG"
  }'
```

## 4. Verify Security Headers

```bash
curl -I http://localhost:8000/health
```

You should see headers like:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; ...
```

## 5. Test Rate Limiting

```bash
# This should succeed
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"user$i@example.com\", \"password\": \"Pass123!\", \"full_name\": \"User $i\"}"
done

# The 6th request should be rate limited (429 error)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user6@example.com", "password": "Pass123!", "full_name": "User 6"}'
```

## 6. Production Deployment Checklist

- [ ] Generated new SECRET_KEY (64+ characters)
- [ ] Set ENVIRONMENT=production
- [ ] Set DEBUG=false
- [ ] Configured ALLOWED_ORIGINS with real domains
- [ ] Replaced all demo/default credentials
- [ ] Enabled HTTPS/TLS
- [ ] Configured firewall rules
- [ ] Set up database backups
- [ ] Configured Sentry for error tracking
- [ ] Set up monitoring and alerting
- [ ] Reviewed and tested all security features

## 7. Monitoring Security

### Check application logs

```bash
# Security warnings will appear in logs
tail -f logs/capp.log | grep -i "security\|warning\|error"
```

### Monitor failed login attempts

```bash
# Check for repeated failed logins
grep "Failed login attempt" logs/capp.log
```

### Check rate limit hits

```bash
# Monitor rate limit violations
grep "Rate limit exceeded" logs/capp.log
```

## 8. Common Issues

### Issue: "SECRET_KEY is using an insecure default value"

**Solution**: Generate a new secret key and update `.env`

### Issue: "CORS allows all origins in production"

**Solution**: Update ALLOWED_ORIGINS in `.env` with specific domains

### Issue: Rate limits too restrictive

**Solution**: Adjust RATE_LIMIT_PER_MINUTE and RATE_LIMIT_PER_HOUR in `.env`

### Issue: Token expired

**Solution**: Use refresh token to get new access token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your-refresh-token>"}'
```

## 9. Security Best Practices

1. **Never commit `.env` file** - It's git-ignored by default
2. **Rotate secrets regularly** - Every 90 days recommended
3. **Use HTTPS in production** - Always
4. **Monitor logs** - Set up alerts for security events
5. **Keep dependencies updated** - Run `pip list --outdated` regularly
6. **Review access logs** - Check for suspicious patterns
7. **Test security** - Regularly verify all protections are working

## Need Help?

- Read full documentation: `/docs/SECURITY.md`
- Check API docs: `http://localhost:8000/docs`
- Report security issues: security@capp.com
