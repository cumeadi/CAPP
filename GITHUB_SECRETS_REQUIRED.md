# GitHub Secrets Setup Required

The GitHub Actions workflows require several secrets to be configured. Follow these steps to set them up.

## Step 1: Access GitHub Secrets

1. Go to your GitHub repository: https://github.com/cumeadi/CAPP
2. Navigate to **Settings** (top right)
3. Select **Secrets and variables** → **Actions** (left sidebar)

## Step 2: Add Required Secrets

Click **"New repository secret"** for each of the following:

### Required Secrets

#### 1. Docker Hub Credentials
```
Name: DOCKER_HUB_USERNAME
Value: cumeadi
```

```
Name: DOCKER_HUB_TOKEN
Value: [Your Docker Hub access token]
```

**How to get Docker Hub token:**
1. Go to https://hub.docker.com/settings/security
2. Click **"New Access Token"**
3. Name it: `github-actions`
4. Copy the token and paste it as the secret value

#### 2. DigitalOcean API Token
```
Name: DIGITALOCEAN_ACCESS_TOKEN
Value: [Your DigitalOcean API token]
```

**How to get DigitalOcean token:**
1. Go to https://cloud.digitalocean.com/account/api/tokens
2. Click **"Generate New Token"**
3. Name it: `github-actions`
4. Select **Read and Write** permissions
5. Generate and copy the token

#### 3. Slack Webhook (Optional)
```
Name: SLACK_WEBHOOK_URL
Value: [Your Slack webhook URL]
```

**How to get Slack webhook (optional):**
1. Go to https://api.slack.com/apps
2. Create a new app or select existing
3. Enable **Incoming Webhooks**
4. Click **Add New Webhook to Workspace**
5. Select channel and authorize
6. Copy the webhook URL

## Step 3: Verify Secrets

After adding all secrets:

```bash
# List secrets (you won't see values, only names)
gh secret list -R cumeadi/CAPP
```

You should see:
```
DOCKER_HUB_USERNAME      Updated 2026-03-21T...
DOCKER_HUB_TOKEN         Updated 2026-03-21T...
DIGITALOCEAN_ACCESS_TOKEN Updated 2026-03-21T...
SLACK_WEBHOOK_URL        Updated 2026-03-21T... (if added)
```

## Step 4: Test Workflow

1. Make a small commit to trigger the workflow:
   ```bash
   echo "# CAPP Deployment Ready" >> README.md
   git add README.md
   git commit -m "Trigger CI/CD workflow test"
   git push origin main
   ```

2. Go to **Actions** tab in GitHub
3. Watch the workflow run
4. Check for any error messages

## Troubleshooting

### Error: "Username and password required"
- ❌ Docker Hub credentials not set
- ✅ Go to Settings → Secrets → Add `DOCKER_HUB_USERNAME` and `DOCKER_HUB_TOKEN`

### Error: "DigitalOcean token invalid"
- ❌ Token expired or has wrong permissions
- ✅ Generate new token with **Read and Write** permissions

### Error: "Repository not found"
- ❌ Docker image push destination wrong
- ✅ Verify Docker Hub username matches `DOCKER_HUB_USERNAME` secret

### Workflow shows deprecation warnings
- ⚠️ This is expected and will be auto-fixed when GitHub forces Node.js 24
- ✅ We've added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` which will help

## What Happens After Setup

Once secrets are configured:

1. **Any push to `main`:**
   - Builds Docker images
   - Pushes to Docker Hub
   - Deploys to DigitalOcean (if app exists)
   - Sends Slack notification (if webhook configured)

2. **Any push to `develop`:**
   - Builds staging Docker images
   - Tests staging endpoints
   - Sends Slack notification

## Security Best Practices

⚠️ **Important:**
- ✅ Secrets are encrypted at rest
- ✅ Secrets are masked in logs (won't appear in workflow output)
- ✅ Only available to GitHub Actions workflows
- ❌ Never commit secrets to git
- ❌ Never paste secrets in issues/PRs
- ⚠️ Rotate tokens periodically (monthly recommended)

## Revoking Secrets

If a secret is compromised:

1. **Revoke the token:**
   - Docker Hub: https://hub.docker.com/settings/security → Delete token
   - DigitalOcean: https://cloud.digitalocean.com/account/api/tokens → Revoke
   - Slack: Delete webhook at https://api.slack.com/apps

2. **Delete from GitHub:**
   - Settings → Secrets → Delete secret

3. **Generate new token and update GitHub secret**

## Quick Reference

| Secret Name | Source | Read More |
|---|---|---|
| `DOCKER_HUB_USERNAME` | Docker Hub settings | https://docs.docker.com/docker-hub/ |
| `DOCKER_HUB_TOKEN` | Docker Hub security | https://docs.docker.com/docker-hub/access-tokens/ |
| `DIGITALOCEAN_ACCESS_TOKEN` | DO API tokens | https://docs.digitalocean.com/reference/api/create-personal-access-token/ |
| `SLACK_WEBHOOK_URL` | Slack API | https://api.slack.com/messaging/webhooks |

---

**Setup takes ~5 minutes. After this, your CI/CD pipeline is fully automated!** 🚀
