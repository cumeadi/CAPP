# CAPP DigitalOcean Deployment Checklist

## ✅ Completed Setup

### Docker Images (Already Pushed)
- [x] `cumeadi/capp:api-latest` - FastAPI backend
- [x] `cumeadi/capp:wallet-latest` - Wallet frontend (Next.js)
- [x] `cumeadi/capp:web-latest` - Web frontend (Next.js)

### Configuration Files Created
- [x] `app.yaml` - DigitalOcean App Platform specification
- [x] `.env.digitalocean` - Environment variables template
- [x] `apps/wallet/.env.production` - Wallet frontend environment
- [x] `apps/web/.env.production` - Web frontend environment
- [x] `docs/DEPLOY_DIGITALOCEAN.md` - Deployment guide (11KB)
- [x] `.github/workflows/deploy.yml` - CI/CD for production
- [x] `.github/workflows/staging.yml` - CI/CD for staging

### PostgreSQL Database
- [x] Created on DigitalOcean (`capp-db`)
- [x] Region: nyc3
- [x] Status: Online and ready

## 🔧 Required Manual Steps (Before Deployment)

### Step 1: Set Up GitHub Secrets (If Not Already Done)
GitHub repository needs these secrets for CI/CD:

```bash
# Set these in your GitHub repo Settings → Secrets and variables
DOCKER_HUB_USERNAME=cumeadi
DOCKER_HUB_TOKEN=<your-docker-hub-token>
DIGITALOCEAN_ACCESS_TOKEN=<your-digitalocean-api-token>
SLACK_WEBHOOK_URL=<optional-slack-webhook>
```

**How to get these tokens:**
- Docker Hub Token: https://hub.docker.com/settings/security
- DigitalOcean Token: https://cloud.digitalocean.com/account/api/tokens

### Step 2: Gather Required Environment Variables

Before deploying, prepare these values:

**Database:**
- `DB_PASSWORD` - From DigitalOcean PostgreSQL
- `DB_HOST` - From DigitalOcean PostgreSQL
- `DB_PORT` - Usually `25060` for DigitalOcean

**Blockchain RPC Endpoints:**
- `ALCHEMY_API_KEY` - Get from https://www.alchemy.com
- `APTOS_PRIVATE_KEY` - Your funded Aptos testnet key
- `POLYGON_PRIVATE_KEY` - Your funded Polygon Amoy key
- `BASE_PRIVATE_KEY` - Your funded Base Sepolia key
- `ARBITRUM_PRIVATE_KEY` - Your funded Arbitrum Sepolia key

**Other Required:**
- `SECRET_KEY` - Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `WALLETCONNECT_PROJECT_ID` - Get from https://cloud.walletconnect.com

**Optional:**
- `SLACK_WEBHOOK_URL` - For deployment notifications
- `REDIS_URL` - If using managed Redis (format: `redis://default:password@host:6379/0`)

### Step 3: Create DigitalOcean App

Choose one method:

**Option A: Using CLI (Recommended)**
```bash
# Install doctl if needed
brew install doctl

# Authenticate
doctl auth init

# Create app from app.yaml
doctl apps create --spec app.yaml

# Get your app ID for next steps
APP_ID=$(doctl apps list --format ID --no-header | head -1)
echo $APP_ID
```

**Option B: Using Web Console**
1. Go to https://cloud.digitalocean.com/apps
2. Click "Create App"
3. Select GitHub → Connect → Select `cumeadi/CAPP`
4. Choose `main` branch
5. Click "Edit Configuration"
6. Paste contents of `app.yaml`
7. Click "Create Resources"

### Step 4: Configure Environment Variables in DigitalOcean

Once app is created, add secrets via CLI:

```bash
doctl apps update $APP_ID \
  --env-secret DB_PASSWORD=$DB_PASSWORD \
  --env-secret DB_HOST=$DB_HOST \
  --env-secret DB_PORT=25060 \
  --env-secret SECRET_KEY=$SECRET_KEY \
  --env-secret ALCHEMY_API_KEY=$ALCHEMY_API_KEY \
  --env-secret APTOS_PRIVATE_KEY=$APTOS_PRIVATE_KEY \
  --env-secret POLYGON_PRIVATE_KEY=$POLYGON_PRIVATE_KEY \
  --env-secret BASE_PRIVATE_KEY=$BASE_PRIVATE_KEY \
  --env-secret ARBITRUM_PRIVATE_KEY=$ARBITRUM_PRIVATE_KEY \
  --env-secret WALLETCONNECT_PROJECT_ID=$WALLETCONNECT_PROJECT_ID \
  --env-secret REDIS_URL=$REDIS_URL
```

Or via DigitalOcean Web Console:
1. Go to your app → Settings → Environment
2. Add each secret with "Add Secret" button
3. Set scope to "RUN_TIME"
4. Save changes

### Step 5: Deploy Application

**Via CLI:**
```bash
# Create initial deployment
doctl apps create-deployment $APP_ID

# Monitor progress (wait for status ACTIVE or DEGRADED)
watch "doctl apps get $APP_ID --format Status,Updated"

# View logs
doctl apps logs $APP_ID component capp-api --follow
```

**Via Web Console:**
1. Go to app → Deployments
2. Click "Create Deployment"
3. Monitor progress in deployments list

### Step 6: Verify Deployment

Once deployment completes:

```bash
# Get app domain
DOMAIN=$(doctl apps get $APP_ID --format DefaultDomain --no-header)
echo "App URL: https://$DOMAIN"

# Test API
curl https://$DOMAIN/api/health

# Test wallet frontend
curl https://$DOMAIN/

# Test web frontend  
curl https://$DOMAIN/app
```

### Step 7: Set Up Custom Domain (Optional)

```bash
# Add custom domain
doctl apps update $APP_ID --domain yourdomain.com

# Update DNS at your registrar:
# Create CNAME record: yourdomain.com → your-app.ondigitaloceans.app

# SSL auto-provisions in 15 minutes
```

### Step 8: Configure Monitoring & Alerts

**Via Web Console:**
1. Go to app → Monitoring → Alerts
2. Add alerts for:
   - Health check failures
   - High memory (>80%)
   - High CPU (>80%)
   - Deployment failures

**View logs:**
```bash
# Follow all logs
doctl apps logs $APP_ID --follow

# Logs for specific component
doctl apps logs $APP_ID component capp-api --follow
doctl apps logs $APP_ID component capp-wallet --follow
doctl apps logs $APP_ID component capp-web --follow

# Search logs
doctl apps logs $APP_ID | grep error
```

## 📋 Deployment Timeline

**Expected timeline for full deployment:**

1. **5 minutes** - Create app in DigitalOcean
2. **15 minutes** - Deploy containers (build + startup)
3. **5 minutes** - SSL certificate provision
4. **5 minutes** - Smoke tests and verification

**Total: ~30 minutes for first deployment**

## 🔍 Post-Deployment Verification

After deployment, verify:

- [ ] API responds to `curl https://$DOMAIN/api/health`
- [ ] Wallet frontend loads at `https://$DOMAIN/`
- [ ] Web frontend loads at `https://$DOMAIN/app`
- [ ] Database connection works (check logs for connection errors)
- [ ] All three services showing as "Running" in DigitalOcean console
- [ ] Health checks passing (green checks in DigitalOcean)
- [ ] Memory usage reasonable (<80% per service)
- [ ] CPU usage reasonable (<70% per service)

## 🚀 CI/CD Pipeline (Automatic on Push)

Once GitHub Secrets are configured:

1. **Push to `main` branch:**
   - Runs tests
   - Builds Docker images
   - Pushes to Docker Hub
   - Auto-deploys to DigitalOcean

2. **Push to `develop` branch:**
   - Runs tests
   - Builds staging images
   - Deploys to staging environment

No manual Docker commands needed - everything is automated!

## 🆘 Troubleshooting

### Deployment Fails
```bash
# Check logs
doctl apps logs $APP_ID --follow

# Check app status
doctl apps describe $APP_ID
```

### Services Crashing
- Check all environment variables are set
- Verify database connection string
- Check Docker image exists in Docker Hub
- View service-specific logs

### High Memory Usage
- Scale up instance size in app.yaml: `instance_size_slug: basic-m`
- Apply: `doctl apps update $APP_ID --spec app.yaml`

## 📞 Support Resources

- **DigitalOcean Docs:** https://docs.digitalocean.com/products/app-platform/
- **Deployment Guide:** `docs/DEPLOY_DIGITALOCEAN.md`
- **GitHub Actions Workflows:** `.github/workflows/`
- **App Configuration:** `app.yaml`

## 🎯 Next Steps After Deployment

1. Monitor app for 24 hours
2. Test wallet functionality on testnet
3. Set up custom domain
4. Enable auto-scaling if traffic increases
5. Configure backup strategy
6. Set up Slack notifications for alerts
7. Create runbooks for common operations

---

**Once deployment completes, the CAPP wallet will be live and accessible to users!**
