# GitHub Secrets Configuration for CAPP Deployment

This guide explains how to configure GitHub Secrets for automated CI/CD deployment to DigitalOcean.

## Required Secrets

### Docker Hub Credentials
```
DOCKER_USERNAME: your-docker-hub-username
DOCKER_PASSWORD: your-docker-hub-access-token  (NOT your password)
DOCKER_REGISTRY: your-docker-hub-username/capp
```

**How to create Docker Hub Access Token:**
1. Login to https://hub.docker.com
2. Click your profile → Account Settings → Security
3. Click "New Access Token"
4. Set Permissions: Read, Write, Delete
5. Copy token and use as `DOCKER_PASSWORD`

### DigitalOcean Credentials
```
DIGITALOCEAN_ACCESS_TOKEN: your-digitalocean-api-token
```

**How to create DigitalOcean API Token:**
1. Login to https://cloud.digitalocean.com
2. Go to Settings → API/Tokens
3. Click "Generate New Token"
4. Set Expiration: No expiration (or 90 days)
5. Select Scopes: **all** (for App Platform management)
6. Copy token immediately (can't view again)

### Blockchain & Application Secrets
```
WALLETCONNECT_PROJECT_ID: your-walletconnect-project-id
ALCHEMY_API_KEY: your-alchemy-api-key
```

**How to get WalletConnect Project ID:**
1. Go to https://cloud.walletconnect.com
2. Create a new project
3. Copy Project ID from dashboard
4. Use in both GitHub Secrets and app.yaml

**How to get Alchemy API Key:**
1. Create account at https://www.alchemy.com
2. Create new app
3. Copy API key from dashboard

### Slack Webhook (Optional, for Notifications)
```
SLACK_WEBHOOK_URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**How to create Slack Webhook:**
1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create New App" or select existing workspace
3. Enable Incoming Webhooks
4. Click "Add New Webhook to Workspace"
5. Select target channel
6. Copy Webhook URL

---

## How to Add Secrets to GitHub

### Method 1: Via GitHub Web UI (Recommended)
1. Go to your repository: https://github.com/YOUR-USERNAME/CAPP
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:
   - Name: `DOCKER_USERNAME`
   - Value: `your-docker-hub-username`
5. Click **Add secret**
6. Repeat for all secrets below

### Method 2: Via GitHub CLI
```bash
# Login to GitHub
gh auth login

# Add each secret
gh secret set DOCKER_USERNAME --body "your-docker-hub-username"
gh secret set DOCKER_PASSWORD --body "your-docker-hub-access-token"
gh secret set DOCKER_REGISTRY --body "your-docker-hub-username/capp"
gh secret set DIGITALOCEAN_ACCESS_TOKEN --body "your-do-api-token"
gh secret set WALLETCONNECT_PROJECT_ID --body "your-project-id"
gh secret set ALCHEMY_API_KEY --body "your-alchemy-key"
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/services/..."
```

---

## Required Secrets Checklist

Create all these secrets in GitHub before attempting deployment:

- [ ] `DOCKER_USERNAME` - Docker Hub username
- [ ] `DOCKER_PASSWORD` - Docker Hub access token
- [ ] `DOCKER_REGISTRY` - Docker registry path (username/capp)
- [ ] `DIGITALOCEAN_ACCESS_TOKEN` - DigitalOcean API token
- [ ] `WALLETCONNECT_PROJECT_ID` - WalletConnect project ID
- [ ] `ALCHEMY_API_KEY` - Alchemy API key
- [ ] `SLACK_WEBHOOK_URL` - (Optional) Slack webhook for notifications

**Verification:**
```bash
# List all secrets (redacted values)
gh secret list
```

Expected output:
```
ALCHEMY_API_KEY           Updated 2026-03-18
DIGITALOCEAN_ACCESS_TOKEN Updated 2026-03-18
DOCKER_PASSWORD           Updated 2026-03-18
DOCKER_REGISTRY           Updated 2026-03-18
DOCKER_USERNAME           Updated 2026-03-18
SLACK_WEBHOOK_URL         Updated 2026-03-18
WALLETCONNECT_PROJECT_ID  Updated 2026-03-18
```

---

## Testing Secrets Configuration

Once secrets are added:

1. **Trigger test deployment:**
   ```bash
   # Push to develop branch to trigger staging build
   git checkout develop
   git commit --allow-empty -m "test: trigger CI/CD"
   git push origin develop
   ```

2. **Monitor GitHub Actions:**
   - Go to your repository
   - Click **Actions** tab
   - Watch the workflow run
   - Check for any secret-related errors

3. **Verify images in Docker Hub:**
   ```bash
   # After successful build
   curl -s https://hub.docker.com/v2/repositories/yourusername/capp-api/
   ```

4. **Check DigitalOcean deployment:**
   ```bash
   doctl apps list
   doctl apps get-deployment <APP_ID>
   ```

---

## Troubleshooting Secrets

### "Secret not found" Error in Workflow
- Verify secret name matches exactly (case-sensitive)
- Check secret is in correct repository (not organization-level)
- Wait 1-2 minutes after adding secret before triggering workflow

### Docker Push Fails with 401 Unauthorized
- Verify `DOCKER_PASSWORD` is access token, not account password
- Check access token has Read, Write, Delete permissions
- Verify `DOCKER_USERNAME` matches Docker Hub account

### DigitalOcean Deployment Fails
- Verify `DIGITALOCEAN_ACCESS_TOKEN` has correct permissions
- Check token hasn't expired
- Regenerate token if unsure

### Sensitive Data Leaked in Logs
- GitHub automatically masks secret values
- If you see "***" in logs, it's redacted (safe)
- Regenerate any exposed credentials immediately

---

## Security Best Practices

1. **Never commit secrets to code:**
   - Use GitHub Secrets, not `.env` files
   - Add `.env*` to `.gitignore`

2. **Rotate secrets regularly:**
   - Change access tokens every 90 days
   - Document when secrets were last rotated

3. **Use least privilege:**
   - API tokens should only have necessary scopes
   - DigitalOcean: avoid "admin" scope if possible
   - Docker Hub: use read-only tokens for pulls only

4. **Audit secret usage:**
   - GitHub shows who accessed secrets in audit logs
   - DigitalOcean shows API token usage
   - Monitor for unusual activity

---

## Next Steps

After configuring secrets:

1. ✅ Follow **DEPLOY_DIGITALOCEAN.md** for manual DigitalOcean setup
2. ✅ Push to `main` branch to trigger automatic deployment
3. ✅ Monitor GitHub Actions for successful build & deploy
4. ✅ Verify app is running on DigitalOcean domain
5. ✅ Test wallet connections and blockchain connectivity
