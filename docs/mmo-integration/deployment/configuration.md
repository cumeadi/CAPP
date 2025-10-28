# Configuration Guide

## Overview

This guide covers environment configuration, credential management, and deployment setup for the MMO integration.

## Environment Variables

### Core Application Settings

```bash
# Application
APP_NAME="CAPP"
APP_VERSION="0.1.0"
ENVIRONMENT="production"  # development, staging, production
DEBUG="false"

# Server
HOST="0.0.0.0"
PORT="8000"

# Security
SECRET_KEY="your-secret-key-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Database
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/capp"
DATABASE_POOL_SIZE="20"
DATABASE_MAX_OVERFLOW="30"

# Redis
REDIS_URL="redis://localhost:6379"
REDIS_POOL_SIZE="10"
```

### M-Pesa Configuration

```bash
# M-Pesa
MMO_MPESA_CONSUMER_KEY="your_consumer_key"
MMO_MPESA_CONSUMER_SECRET="your_consumer_secret"
MMO_MPESA_BUSINESS_SHORT_CODE="174379"
MMO_MPESA_PASSKEY="your_passkey"
MPESA_ENVIRONMENT="sandbox"  # sandbox or production
```

### MTN Mobile Money Configuration

```bash
# MTN Mobile Money
MTN_MOMO_SUBSCRIPTION_KEY="your_subscription_key"
MTN_MOMO_API_USER="your_api_user_uuid"
MTN_MOMO_API_KEY="your_api_key"
MTN_MOMO_ENVIRONMENT="sandbox"  # sandbox or production
```

### Airtel Money Configuration

```bash
# Airtel Money
AIRTEL_MONEY_CLIENT_ID="your_client_id"
AIRTEL_MONEY_CLIENT_SECRET="your_client_secret"
AIRTEL_MONEY_API_KEY="your_api_key"
AIRTEL_MONEY_ENVIRONMENT="staging"  # staging or production
```

---

## Configuration Files

### 1. Environment File (.env)

Create a `.env` file in the project root:

```bash
# .env
#  Application Settings
APP_NAME=CAPP
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://capp_user:secure_password@db:5432/capp_prod

# M-Pesa
MMO_MPESA_CONSUMER_KEY=${MPESA_CONSUMER_KEY}
MMO_MPESA_CONSUMER_SECRET=${MPESA_CONSUMER_SECRET}
MMO_MPESA_BUSINESS_SHORT_CODE=600000
MMO_MPESA_PASSKEY=${MPESA_PASSKEY}

# MTN Mobile Money
MTN_MOMO_SUBSCRIPTION_KEY=${MTN_SUBSCRIPTION_KEY}
MTN_MOMO_API_USER=${MTN_API_USER}
MTN_MOMO_API_KEY=${MTN_API_KEY}
MTN_MOMO_ENVIRONMENT=production

# Airtel Money
AIRTEL_MONEY_CLIENT_ID=${AIRTEL_CLIENT_ID}
AIRTEL_MONEY_CLIENT_SECRET=${AIRTEL_CLIENT_SECRET}
AIRTEL_MONEY_API_KEY=${AIRTEL_API_KEY}
AIRTEL_MONEY_ENVIRONMENT=production
```

### 2. Docker Compose (docker-compose.yml)

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/capp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    command: uvicorn applications.capp.main:app --host 0.0.0.0 --port 8000

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=capp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
```

### 3. Kubernetes Configuration

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: capp-mmo
  labels:
    app: capp
    component: mmo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: capp
      component: mmo
  template:
    metadata:
      labels:
        app: capp
        component: mmo
    spec:
      containers:
      - name: capp
        image: capp:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: capp-secrets
              key: database-url
        - name: MMO_MPESA_CONSUMER_KEY
          valueFrom:
            secretKeyRef:
              name: mpesa-secrets
              key: consumer-key
        - name: MMO_MPESA_CONSUMER_SECRET
          valueFrom:
            secretKeyRef:
              name: mpesa-secrets
              key: consumer-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## Secrets Management

### AWS Secrets Manager

```python
import boto3
import json

def get_secrets():
    """Retrieve secrets from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')

    response = client.get_secret_value(SecretId='capp/mmo/credentials')
    secrets = json.loads(response['SecretString'])

    return secrets

# Usage
secrets = get_secrets()
mpesa_key = secrets['MPESA_CONSUMER_KEY']
```

### HashiCorp Vault

```python
import hvac

def get_vault_secrets():
    """Retrieve secrets from Vault"""
    client = hvac.Client(url='https://vault.example.com')
    client.token = os.environ['VAULT_TOKEN']

    # Read secrets
    secret = client.secrets.kv.v2.read_secret_version(
        path='capp/mmo'
    )

    return secret['data']['data']

# Usage
secrets = get_vault_secrets()
mtn_key = secrets['MTN_MOMO_SUBSCRIPTION_KEY']
```

### Kubernetes Secrets

```bash
# Create secret from file
kubectl create secret generic mpesa-secrets \
  --from-literal=consumer-key=$MPESA_CONSUMER_KEY \
  --from-literal=consumer-secret=$MPESA_CONSUMER_SECRET \
  --from-literal=passkey=$MPESA_PASSKEY

# Create secret from file
kubectl create secret generic mtn-secrets \
  --from-file=./mtn-credentials.json

# Create secret from env file
kubectl create secret generic airtel-secrets \
  --from-env-file=./airtel.env
```

---

## Database Setup

### PostgreSQL

```bash
# Create database
createdb capp_production

# Run migrations
alembic upgrade head

# Create indexes
psql capp_production < sql/indexes.sql
```

### Migration Script

```python
# alembic/versions/001_create_mmo_tables.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # MMO Callbacks table
    op.create_table(
        'mmo_callbacks',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_transaction_id', sa.String(255), nullable=False),
        sa.Column('callback_data', sa.Text(), nullable=False),
        sa.Column('callback_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50)),
        sa.Column('amount', sa.Numeric(15, 2)),
        sa.Column('currency', sa.String(3)),
        sa.Column('processed', sa.Boolean(), default=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # Create indexes
    op.create_index('idx_mmo_provider_tx', 'mmo_callbacks',
                    ['provider', 'provider_transaction_id'])
    op.create_index('idx_mmo_processed', 'mmo_callbacks',
                    ['processed', 'received_at'])

def downgrade():
    op.drop_table('mmo_callbacks')
```

---

## Webhook Configuration

### Nginx Reverse Proxy

```nginx
# nginx.conf
upstream capp_backend {
    server web:8000;
}

server {
    listen 80;
    server_name api.capp.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.capp.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Webhook endpoints
    location /v1/webhooks/ {
        proxy_pass http://capp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for webhook processing
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;

        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

### Cloudflare Configuration

```yaml
# cloudflare-workers/webhook-proxy.js
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Forward webhooks to origin
  const url = new URL(request.url)

  if (url.pathname.startsWith('/v1/webhooks/')) {
    // Add security headers
    const headers = new Headers(request.headers)
    headers.set('X-Forwarded-By', 'Cloudflare')

    return fetch(request, {
      headers: headers,
      cf: {
        cacheEverything: false
      }
    })
  }

  return new Response('Not Found', { status: 404 })
}
```

---

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'capp-mmo'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "MMO Integration Metrics",
    "panels": [
      {
        "title": "Transaction Success Rate",
        "targets": [
          {
            "expr": "rate(mmo_transactions_successful[5m]) / rate(mmo_transactions_total[5m])"
          }
        ]
      },
      {
        "title": "Circuit Breaker State",
        "targets": [
          {
            "expr": "mmo_circuit_breaker_state"
          }
        ]
      },
      {
        "title": "Response Time (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mmo_request_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

### Structured Logging

```python
import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Usage
logger = structlog.get_logger()
logger.info(
    "mmo_payment_initiated",
    provider="mpesa",
    transaction_id="ABC123",
    amount=1000.0,
    currency="KES"
)
```

---

## Health Checks

### Application Health Endpoint

```python
from fastapi import APIRouter
from applications.capp.capp.core.database import check_db_connection
from applications.capp.capp.core.redis import check_redis_connection

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    checks = {
        "database": await check_db_connection(),
        "redis": await check_redis_connection(),
        "status": "healthy"
    }

    if not all([checks["database"], checks["redis"]]):
        checks["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=checks)

    return checks

@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    # Check if application is ready to serve requests
    return {"status": "ready"}
```

### Docker Health Check

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "applications.capp.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Backup & Recovery

### Database Backup

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"

# Create backup
pg_dump -h localhost -U postgres capp_production | gzip > "${BACKUP_DIR}/capp_${DATE}.sql.gz"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/capp_${DATE}.sql.gz" s3://capp-backups/postgres/

# Keep only last 7 days locally
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +7 -delete
```

### Restore from Backup

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

# Download from S3
aws s3 cp "s3://capp-backups/postgres/${BACKUP_FILE}" /tmp/

# Restore database
gunzip -c "/tmp/${BACKUP_FILE}" | psql -h localhost -U postgres capp_production
```

---

## Load Balancing

### HAProxy Configuration

```
# haproxy.cfg
global
    maxconn 4096

defaults
    mode http
    timeout connect 5s
    timeout client 30s
    timeout server 30s

frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/capp.pem
    default_backend capp_backend

backend capp_backend
    balance roundrobin
    option httpchk GET /health
    server web1 10.0.1.10:8000 check
    server web2 10.0.1.11:8000 check
    server web3 10.0.1.12:8000 check
```

---

## Performance Tuning

### Uvicorn Workers

```bash
# Production deployment
uvicorn applications.capp.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --log-level info \
  --access-log \
  --proxy-headers
```

### Gunicorn with Uvicorn Workers

```bash
gunicorn applications.capp.main:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --worker-connections 1000 \
  --max-requests 10000 \
  --max-requests-jitter 1000 \
  --timeout 30 \
  --graceful-timeout 10 \
  --keep-alive 5 \
  --log-level info
```

---

## Security Checklist

- [ ] Use HTTPS for all endpoints
- [ ] Store credentials in secrets manager
- [ ] Enable rate limiting
- [ ] Implement webhook signature verification
- [ ] Set up Web Application Firewall (WAF)
- [ ] Enable DDoS protection
- [ ] Implement IP whitelisting for admin endpoints
- [ ] Use strong database passwords
- [ ] Enable database encryption at rest
- [ ] Set up audit logging
- [ ] Implement intrusion detection
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Use least privilege principle

---

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check database is running
docker-compose ps db

# Check connection
psql -h localhost -U postgres -d capp -c "SELECT 1"

# View logs
docker-compose logs db
```

**Webhook Not Receiving Callbacks**
```bash
# Test webhook endpoint
curl -X POST https://your-domain.com/v1/webhooks/mpesa/stkpush \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check firewall rules
iptables -L

# Verify SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

**High Memory Usage**
```bash
# Check memory usage
docker stats

# Reduce worker count
# Implement connection pooling
# Enable response caching
```

---

## Support

For configuration assistance:
- Email: devops@capp.com
- Slack: #mmo-deployment
- Documentation: https://docs.capp.com/deployment
