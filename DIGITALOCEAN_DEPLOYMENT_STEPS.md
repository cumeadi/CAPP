# DigitalOcean App Platform Deployment - Manual Setup

Since `doctl` CLI has limitations with the app spec format, we'll use the DigitalOcean web console for deployment. The process is straightforward and takes about 5 minutes.

## Step 1: Create App via Web Console

1. **Go to DigitalOcean Dashboard:**
   - https://cloud.digitalocean.com/apps

2. **Click "Create App"**
   - Select source: **GitHub**
   - Authenticate GitHub if needed
   - Select repository: **cumeadi/CAPP**
   - Select branch: **main**
   - Click "Next"

## Step 2: Configure Services

The system will auto-detect Dockerfiles. You'll see:
- **capp-api** (Dockerfile in root)
- **capp-wallet** (apps/wallet/Dockerfile)
- **capp-web** (apps/web/Dockerfile)

For each service, configure:

### For capp-api:
- **HTTP Port:** 8000
- **Instance Size:** Basic (512MB RAM, $15/month)
- **Min Instances:** 1
- **Max Instances:** 3
- **Health Check:** GET /health

### For capp-wallet & capp-web:
- **HTTP Port:** 3000
- **Instance Size:** Basic XS (256MB RAM, $7/month)
- **Min Instances:** 1
- **Max Instances:** 2
- **Health Check:** GET /

## Step 3: Add Database

1. Click "Add Resource" → "Database"
2. Select **PostgreSQL**
3. Name: **capp-db**
4. Engine Version: **15**
5. Production tier: **Yes**
6. Region: **nyc3**
7. Size: **Basic ($15/month, 1GB RAM)**

## Step 4: Configure Environment Variables

After creating the app, go to **App Settings → Environment**

Add these secrets (scope: **RUN_TIME**):

```
DATABASE_URL
DB_PASSWORD
DB_HOST
DB_PORT
SECRET_KEY
ALCHEMY_API_KEY
APTOS_PRIVATE_KEY
POLYGON_PRIVATE_KEY
BASE_PRIVATE_KEY
ARBITRUM_PRIVATE_KEY
WALLETCONNECT_PROJECT_ID
REDIS_URL (optional)
```

## Step 5: Configure HTTP Routes

Go to **App Settings → Ingress**

Configure paths:
- `/api` → capp-api (port 8000)
- `/` → capp-wallet (port 3000)
- `/app` → capp-web (port 3000)

## Step 6: Deploy

1. Review configuration
2. Click "Create Resources"
3. Wait for deployment (10-15 minutes)

## Step 7: Get Your App URL

Once deployed:
```bash
# Get your app's domain
doctl apps list --format Name,DefaultDomain
```

Test endpoints:
```bash
curl https://your-app.ondigitaloceans.app/api/health
curl https://your-app.ondigitaloceans.app/
curl https://your-app.ondigitaloceans.app/app
```

## Required Environment Values

Before deploying, gather these:

**Database** (from DigitalOcean PostgreSQL):
- `DB_HOST`: capp-db-do-user-XXXXX.m.db.ondigitalocean.com
- `DB_PORT`: 25060
- `DB_PASSWORD`: Your database password

**Blockchain Keys** (from your wallets):
- `APTOS_PRIVATE_KEY`: Your funded Aptos testnet key
- `POLYGON_PRIVATE_KEY`: Your funded Polygon Amoy key
- `BASE_PRIVATE_KEY`: Your funded Base Sepolia key
- `ARBITRUM_PRIVATE_KEY`: Your funded Arbitrum Sepolia key

**APIs**:
- `ALCHEMY_API_KEY`: From https://www.alchemy.com
- `WALLETCONNECT_PROJECT_ID`: From https://cloud.walletconnect.com

**Security**:
- `SECRET_KEY`: Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`

## Alternative: Use doctl with GitHub URL

Once the app is created via web UI, you can manage it via CLI:

```bash
# List apps
doctl apps list

# Get app ID
APP_ID=$(doctl apps list --format ID --no-header | head -1)

# View app status
doctl apps get $APP_ID

# View logs
doctl apps logs $APP_ID component capp-api --follow

# Create new deployment
doctl apps create-deployment $APP_ID

# Update environment variables
doctl apps update $APP_ID \
  --env-secret DB_PASSWORD=value \
  --env-secret SECRET_KEY=value \
  ...
```

## Cost Estimate

```
Services:
- capp-api (Basic): $15/month
- capp-wallet (Basic XS): $7/month
- capp-web (Basic XS): $7/month
Subtotal: $29/month

Database:
- PostgreSQL (Basic, 1GB): $15/month

Total: ~$44/month
```

## Next Steps After Deployment

1. Monitor logs for errors
2. Test wallet functionality
3. Set up custom domain (optional)
4. Configure monitoring alerts
5. Enable auto-deployments from GitHub

---

**Duration:** ~15 minutes total
**Difficulty:** Easy
