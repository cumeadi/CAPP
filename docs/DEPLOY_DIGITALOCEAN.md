# DigitalOcean Deployment Guide

This guide walks through deploying the CAPP (Canza Autonomous Payment Protocol) application to DigitalOcean App Platform with managed PostgreSQL and Redis services.

## Prerequisites

- DigitalOcean account with sufficient credits
- GitHub repository access (https://github.com/cumeadi/CAPP)
- Docker Hub account (for container image registry)
- doctl CLI installed (`brew install doctl` on macOS)
- Valid API credentials for blockchain RPC endpoints:
  - Alchemy API key (for Polygon, Base, Arbitrum)
  - Aptos node URL access
  - WalletConnect Project ID

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│       DigitalOcean App Platform                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │ capp-api     │  │ capp-wallet          │   │
│  │ (FastAPI)    │  │ (Next.js port 3000)  │   │
│  │ port 8000    │  │                      │   │
│  └──────────────┘  └──────────────────────┘   │
│                                                 │
│  ┌──────────────────────┐                      │
│  │ capp-web             │                      │
│  │ (Next.js port 3000)  │                      │
│  └──────────────────────┘                      │
│                                                 │
├─────────────────────────────────────────────────┤
│  Managed Services                               │
├─────────────────────────────────────────────────┤
│  • PostgreSQL Database (capp-db)               │
│  • Redis Cache (if configured)                  │
│  • Automatic SSL/TLS via Let's Encrypt         │
│  • Built-in monitoring and logging             │
└─────────────────────────────────────────────────┘
```

## Step 1: Configure Docker Hub Access

DigitalOcean App Platform can pull images from Docker Hub. Ensure your images are pushed:

```bash
# Login to Docker Hub
docker login

# Build and push images (if not already done)
docker build -t cumeadi/capp:api-latest .
docker build -t cumeadi/capp:wallet-latest apps/wallet/
docker build -t cumeadi/capp:web-latest apps/web/

docker push cumeadi/capp:api-latest
docker push cumeadi/capp:wallet-latest
docker push cumeadi/capp:web-latest
```

## Step 2: Create DigitalOcean App via CLI

### Option A: Using DigitalOcean CLI (doctl)

1. **Initialize doctl:**
   ```bash
   doctl auth init
   # Follow prompts to enter your DigitalOcean API token
   ```

2. **Create the app:**
   ```bash
   doctl apps create --spec app.yaml
   # This returns the app ID
   ```

3. **Monitor deployment:**
   ```bash
   doctl apps get <APP_ID>
   doctl apps logs <APP_ID> component capp-api
   ```

### Option B: Using DigitalOcean Web Console

1. Go to DigitalOcean Control Panel → Apps
2. Click "Create App"
3. Select "GitHub" as source
4. Connect your GitHub account and select `cumeadi/CAPP` repository
5. Select branch: `main`
6. Click "Next"
7. Select "Edit Configuration"
8. Copy contents of `app.yaml` into the configuration editor
9. Click "Next" and review settings
10. Click "Create Resources"

## Step 3: Set Environment Variables

Once the app is created, configure secrets in DigitalOcean:

### Via CLI:
```bash
# Set secrets (environment variables not visible in logs)
doctl apps update <APP_ID> \
  --env-secret DB_PASSWORD=your_actual_password \
  --env-secret SECRET_KEY=your_secret_key \
  --env-secret ALCHEMY_API_KEY=your_alchemy_key \
  --env-secret APTOS_PRIVATE_KEY=your_aptos_private_key \
  --env-secret POLYGON_PRIVATE_KEY=your_polygon_private_key \
  --env-secret BASE_PRIVATE_KEY=your_base_private_key \
  --env-secret ARBITRUM_PRIVATE_KEY=your_arbitrum_private_key \
  --env-secret WALLETCONNECT_PROJECT_ID=your_walletconnect_id \
  --env-secret REDIS_URL=redis://default:password@host:6379/0
```

### Via Web Console:
1. Go to your app → Settings → Environment
2. Add each secret using the "Add Secret" button
3. Use `RUN_TIME` scope for secrets that should be available at runtime
4. Click "Save"

## Step 4: Configure Database Connection

The app.yaml references `${DB_PASSWORD}`, `${DB_HOST}`, and `${DB_PORT}`.

**If using DigitalOcean Managed PostgreSQL:**

1. Create a Managed PostgreSQL cluster:
   ```bash
   doctl databases create capp-db \
     --engine pg \
     --region nyc3 \
     --size db-s-1vcpu-1gb \
     --version 15
   ```

2. Get connection details:
   ```bash
   doctl databases connection capp-db
   # Returns: postgresql://doadmin:password@host:25060/defaultdb?sslmode=require
   ```

3. Update environment variables with actual connection string values

**If using external database:**
- Update `DATABASE_URL` in environment variables
- Ensure firewall rules allow DigitalOcean app IP addresses

## Step 5: Deploy the Application

### Initial Deployment:
```bash
# Create initial deployment
doctl apps create-deployment <APP_ID>
```

### Monitor Deployment:
```bash
# Watch deployment progress
doctl apps describe <APP_ID> --format=Status,Updated,Details

# View component logs
doctl apps logs <APP_ID> component capp-api
doctl apps logs <APP_ID> component capp-wallet
doctl apps logs <APP_ID> component capp-web
```

### Verify Services:
```bash
# Once deployment completes, get the app domain
APP_URL=$(doctl apps get <APP_ID> --format DefaultDomain --no-header)

# Test API health
curl https://${APP_URL}/api/health

# Test wallet frontend
curl https://${APP_URL}/

# Test web frontend
curl https://${APP_URL}/app
```

## Step 6: Set Up Custom Domain (Optional)

1. In DigitalOcean web console: App → Settings → Domains
2. Click "Add Domain"
3. Enter your domain (e.g., `capp.yourdomain.com`)
4. Update DNS records at your domain registrar:
   - CNAME: `capp.yourdomain.com` → `your-app.ondigitaloceans.app`
5. SSL certificate will auto-provision in ~15 minutes

## Step 7: Configure Auto-Deployment from GitHub

The app.yaml contains GitHub integration. When you push to `main` branch:

1. DigitalOcean detects changes
2. Runs tests (if configured in GitHub Actions)
3. Builds new Docker images
4. Deploys automatically

To enable pull request previews:
```bash
doctl apps update <APP_ID> --feature pull-request-previews
```

## Step 8: Set Up Monitoring & Alerts

### Monitor via DigitalOcean Console:
1. App → Metrics
   - View CPU, memory, network usage
   - Monitor request rates and latencies

2. App → Logs
   - Tail logs from all components
   - Filter by component or time range

### Configure Health Checks:
Already configured in app.yaml:
- Backend: `/health` endpoint every 30 seconds
- Frontend: `/` endpoint every 10 seconds

### Set Up Alerts:
1. Monitoring → Alerts
2. Create alert for:
   - High memory usage (>80%)
   - High CPU usage (>80%)
   - App down (health check failures)
   - Database connection errors

## Troubleshooting

### Deployment Fails During Build

**Check build logs:**
```bash
doctl apps logs <APP_ID> --follow
```

**Common issues:**
- Missing environment variables
- Docker image pull failures (check Docker Hub access)
- Build command errors (verify Dockerfile syntax)

### Services Crash After Deployment

**Check service logs:**
```bash
doctl apps logs <APP_ID> component capp-api
```

**Common causes:**
- Database connection failure (check DB_PASSWORD, DB_HOST)
- Missing environment variables at runtime
- Port conflicts (ensure ports 8000, 3000 are free)

### High Memory Usage

**Scale up service:**
```bash
# Edit app.yaml and change instance_size_slug
doctl apps update <APP_ID> --spec app.yaml
```

**Available sizes:**
- `basic-xs` - $7/month (256MB RAM)
- `basic-s` - $15/month (512MB RAM)
- `basic-m` - $25/month (1GB RAM)
- `basic-l` - $50/month (2GB RAM)

### Database Connection Issues

**Verify connectivity:**
```bash
# From your local machine
psql postgresql://doadmin:password@host:25060/defaultdb?sslmode=require

# Inside DigitalOcean app (via console)
doctl apps logs <APP_ID> component capp-api | grep -i database
```

**Check firewall:**
1. Go to Database → Firewall
2. Ensure DigitalOcean App Platform IPs are whitelisted
3. Or enable "Allow Trusted Sources"

## Backup & Recovery

### Automated Backups:
DigitalOcean Managed PostgreSQL includes automatic daily backups (30-day retention).

### Manual Backup:
```bash
# Dump database
pg_dump "postgresql://doadmin:password@host:25060/defaultdb?sslmode=require" > capp-backup.sql

# Restore from backup
psql "postgresql://doadmin:password@host:25060/defaultdb?sslmode=require" < capp-backup.sql
```

### Rollback Procedure:
1. Get previous deployment ID:
   ```bash
   doctl apps deployments list <APP_ID>
   ```

2. Re-deploy previous version:
   ```bash
   doctl apps create-deployment <APP_ID> --source-digest <PREVIOUS_DIGEST>
   ```

## Scaling Configuration

### Horizontal Scaling (More Instances):
Update in app.yaml:
```yaml
capp-api:
  max_instance_count: 5        # Auto-scale up to 5 instances
  instance_size_slug: basic-s  # Each instance gets 512MB RAM

capp-wallet:
  max_instance_count: 3        # Frontend can scale to 3 instances
```

Apply changes:
```bash
doctl apps update <APP_ID> --spec app.yaml
```

### Vertical Scaling (More Resources):
Change `instance_size_slug`:
- `basic-xs` (256MB) → `basic-s` (512MB) → `basic-m` (1GB) → `basic-l` (2GB)

## Cost Estimation

Monthly costs for CAPP on DigitalOcean:

```
App Platform:
  - capp-api (basic-s): $15/month
  - capp-wallet (basic-xs): $7/month
  - capp-web (basic-xs): $7/month
  Subtotal: $29/month base

Managed PostgreSQL (medium, 3GB): $45/month

Managed Redis (512MB, optional): $15/month

Domain/SSL: Included

Total Estimate: $74-89/month
```

## Production Checklist

- [ ] Environment variables configured in DigitalOcean
- [ ] Database backups enabled and tested
- [ ] Health checks passing for all services
- [ ] Monitoring and alerts configured
- [ ] Custom domain configured (optional)
- [ ] HTTPS/SSL working correctly
- [ ] Database connection pooling configured
- [ ] Error tracking (Sentry) integrated
- [ ] Logging reviewed and configured
- [ ] Rate limiting enabled if needed
- [ ] API documentation deployed
- [ ] Runbook created for common operations

## Next Steps

1. **Monitor deployment** for 24 hours
   - Watch logs and metrics
   - Test all endpoints
   - Verify wallet connections

2. **Set up CI/CD** in GitHub Actions
   - Run tests on push
   - Build Docker images
   - Auto-deploy on success

3. **Configure alerting**
   - Set up Slack/email notifications
   - Create on-call rotation

4. **Plan scaling strategy**
   - Monitor peak usage
   - Adjust resource allocation
   - Implement caching if needed

For support, visit: https://www.digitalocean.com/docs/app-platform/

