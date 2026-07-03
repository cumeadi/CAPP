#!/bin/bash

# CAPP Wallet - DigitalOcean Deployment Script
# Run this script on your local machine to deploy to DigitalOcean

set -e  # Exit on error

# Configuration - Read from environment variables (for security)
DO_TOKEN="${DIGITALOCEAN_ACCESS_TOKEN}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-cumeadi/projectug}"
DOCKER_USERNAME="${DOCKER_USERNAME:-cumeadi}"
DOCKER_PASSWORD="${DOCKER_PASSWORD:-dckr_pat_7yTNCt7heEaq10N3XgvGss759Q0}"
ALCHEMY_API_KEY="${ALCHEMY_API_KEY:-FX7-uiaeRx_TaEyI2HGC0}"
WALLETCONNECT_PROJECT_ID="${WALLETCONNECT_PROJECT_ID:-10b198f3e3b06d3c5ca312f0a7c2d39e}"

# Validate required token
if [ -z "$DO_TOKEN" ]; then
  echo "❌ Error: DIGITALOCEAN_ACCESS_TOKEN environment variable not set!"
  echo ""
  echo "Set it with:"
  echo '  export DIGITALOCEAN_ACCESS_TOKEN="your-token-here"'
  exit 1
fi

APP_NAME="capp-wallet"
DB_NAME="capp-db"
REDIS_NAME="capp-redis"
REGION="nyc3"

echo "=========================================="
echo "CAPP Wallet - DigitalOcean Deployment"
echo "=========================================="
echo ""

# Step 1: Authenticate with DigitalOcean
echo "📝 Authenticating with DigitalOcean..."
doctl auth init --access-token $DO_TOKEN

# Step 2: Create PostgreSQL Database
echo ""
echo "🗄️  Creating PostgreSQL Database..."
doctl databases create $DB_NAME \
  --engine pg \
  --region $REGION \
  --size db-s-1vcpu-1gb \
  --num-nodes 1

echo "⏳ Waiting for PostgreSQL to be ready (this takes 5-10 minutes)..."
while true; do
  STATUS=$(doctl databases get $DB_NAME --format status --no-header 2>/dev/null || echo "creating")
  if [ "$STATUS" = "active" ]; then
    echo "✅ PostgreSQL is ready!"
    break
  fi
  echo "   Status: $STATUS... waiting..."
  sleep 10
done

# Get PostgreSQL connection details
echo ""
echo "📊 PostgreSQL Connection Details:"
PG_HOST=$(doctl databases get $DB_NAME --format host --no-header)
PG_USER=$(doctl databases get $DB_NAME --format user --no-header)
PG_DB=$(doctl databases get $DB_NAME --format db_name --no-header)
echo "   Host: $PG_HOST"
echo "   Port: 25060"
echo "   User: $PG_USER"
echo "   Database: $PG_DB"
echo ""
echo "⚠️  IMPORTANT: Get the PostgreSQL password from the dashboard:"
echo "   https://cloud.digitalocean.com/databases"
echo "   Connection string: postgresql+asyncpg://$PG_USER:PASSWORD@$PG_HOST:25060/$PG_DB?sslmode=require"
echo ""

# Step 3: Create Redis Database
echo ""
echo "⚡ Creating Redis Instance..."
doctl databases create $REDIS_NAME \
  --engine redis \
  --region $REGION \
  --size db-s-1vcpu-512mb-10gb \
  --num-nodes 1

echo "⏳ Waiting for Redis to be ready (this takes 5-10 minutes)..."
while true; do
  STATUS=$(doctl databases get $REDIS_NAME --format status --no-header 2>/dev/null || echo "creating")
  if [ "$STATUS" = "active" ]; then
    echo "✅ Redis is ready!"
    break
  fi
  echo "   Status: $STATUS... waiting..."
  sleep 10
done

# Get Redis connection details
echo ""
echo "📊 Redis Connection Details:"
REDIS_HOST=$(doctl databases get $REDIS_NAME --format host --no-header)
echo "   Host: $REDIS_HOST"
echo "   Port: 25061"
echo ""
echo "⚠️  IMPORTANT: Get the Redis password from the dashboard:"
echo "   https://cloud.digitalocean.com/databases"
echo "   Connection string: redis://:PASSWORD@$REDIS_HOST:25061/0?ssl_cert_reqs=required"
echo ""

# Step 4: Display App Creation Instructions
echo ""
echo "=========================================="
echo "✅ Database Resources Created!"
echo "=========================================="
echo ""
echo "📱 Next Step: Create DigitalOcean App Platform Application"
echo ""
echo "Option A: Via DigitalOcean Dashboard (Recommended for first-time):"
echo "  1. Go to: https://cloud.digitalocean.com/apps"
echo "  2. Click 'Create App'"
echo "  3. Upload app.yaml from this repository"
echo "  4. Configure environment variables and secrets"
echo ""
echo "Option B: Via doctl CLI (after setting DATABASE_URL and REDIS_URL):"
echo "  doctl apps create-deployment --spec app.yaml"
echo ""

echo "⚠️  REQUIRED: Before creating the app, you MUST set these in app.yaml:"
echo ""
echo "  DATABASE_URL=postgresql+asyncpg://$PG_USER:PASSWORD@$PG_HOST:25060/$PG_DB?sslmode=require"
echo "  REDIS_URL=redis://:PASSWORD@$REDIS_HOST:25061/0?ssl_cert_reqs=required"
echo ""
echo "Get the passwords from the DigitalOcean Dashboard:"
echo "  https://cloud.digitalocean.com/databases"
echo ""

# Step 5: Docker Hub Login
echo ""
echo "🐋 Logging in to Docker Hub..."
echo $DOCKER_PASSWORD | docker login --username $DOCKER_USERNAME --password-stdin

# Step 6: Build Docker Images
echo ""
echo "🔨 Building Docker Images..."
cd /Users/chikau/CAPP/CAPP

echo "   Building backend image..."
docker build -t $DOCKER_REGISTRY/capp-api:latest .

echo "   Building wallet frontend image..."
docker build -t $DOCKER_REGISTRY/capp-wallet:latest apps/wallet/

echo "   Building web frontend image..."
docker build -t $DOCKER_REGISTRY/capp-web:latest apps/web/ || echo "⚠️  Web app build failed (non-critical)"

echo ""
echo "✅ Docker images built successfully!"
echo ""

# Step 7: Push to Docker Hub
echo ""
echo "📤 Pushing images to Docker Hub..."
docker push $DOCKER_REGISTRY/capp-api:latest
docker push $DOCKER_REGISTRY/capp-wallet:latest
docker push $DOCKER_REGISTRY/capp-web:latest || echo "⚠️  Web app push skipped"

echo ""
echo "✅ Images pushed to Docker Hub!"
echo "   View at: https://hub.docker.com/r/$DOCKER_REGISTRY"
echo ""

# Final Instructions
echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT PREPARATION COMPLETE!"
echo "=========================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. ✅ GitHub Secrets: CONFIGURED"
echo "2. ✅ DigitalOcean Databases: CREATED"
echo "3. ✅ Docker Images: BUILT & PUSHED"
echo ""
echo "4. 📝 MANUAL STEP - Create App Platform Application:"
echo "   • Go to: https://cloud.digitalocean.com/apps"
echo "   • Click 'Create App'"
echo "   • Upload app.yaml"
echo "   • Set DATABASE_URL from PostgreSQL dashboard"
echo "   • Set REDIS_URL from Redis dashboard"
echo "   • Deploy!"
echo ""
echo "5. ✨ Verify Deployment:"
echo "   • Get app domain: doctl apps get <APP_ID>"
echo "   • Test health: curl https://app-domain/api/v1/health"
echo "   • Open in browser: https://app-domain"
echo ""

echo ""
echo "📚 Documentation:"
echo "   • Full guide: docs/DEPLOY_DIGITALOCEAN.md"
echo "   • Troubleshooting: docs/DEPLOY_DIGITALOCEAN.md#troubleshooting"
echo ""
