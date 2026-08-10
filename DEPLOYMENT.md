# PipPulse AI - Deployment & Operations Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Secrets Management](#secrets-management)
4. [Docker Compose Deployment](#docker-compose-deployment)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Observability](#monitoring--observability)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tuning](#performance-tuning)

## Prerequisites

### Required Software
- Docker & Docker Compose (v3.8+)
- Python 3.10+ (for local development)
- Node.js 18+ (for frontend)
- Git

### External Services
- NewsAPI key (https://newsapi.org)
- Twitter/X API credentials
- Reddit API credentials
- Telegram Bot credentials
- OpenAI API key (optional, for enhanced analysis)

### Hardware Requirements
- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB RAM, 4 CPU cores, SSD storage
- **Production**: 16GB+ RAM, 8+ CPU cores, dedicated databases

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd PipPulse-AI
```

### 2. Create Environment File
```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required Environment Variables:**
```env
# Database
MONGO_USERNAME=pippulse
MONGO_PASSWORD=pippulse123
MONGO_DATABASE=pippulse

POSTGRES_USER=pippulse
POSTGRES_PASSWORD=pippulse123
POSTGRES_DB=pippulse

INFLUXDB_USERNAME=pippulse
INFLUXDB_PASSWORD=pippulse123
INFLUXDB_ORG=pippulse
INFLUXDB_BUCKET=signals
INFLUXDB_PRICE_BUCKET=forex_prices
INFLUXDB_TOKEN=pippulse-super-secret-token-change-in-production

# APIs
NEWSAPI_KEY=your_key_here
ALPHAVANTAGE_API_KEY=your_key_here
TWITTER_BEARER_TOKEN=your_token_here
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here

# Signal Generation
SIGNAL_LATENCY_TARGET=5
CONFIDENCE_THRESHOLD=0.6
MAX_BATCH_SIZE=32
```

### 3. Install Dependencies

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 4. Start Local Services
```bash
# From project root
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

## Secrets Management

### Overview
Proper secrets management is critical for security. PipPulse-AI uses environment variables for all sensitive data and should **NEVER** have hardcoded credentials in code or configuration files.

### Security Best Practices

**DO:**
- ✅ Store secrets in environment variables
- ✅ Use `.env` file locally (add to `.gitignore`)
- ✅ Rotate secrets regularly
- ✅ Use strong passwords (minimum 16 characters)
- ✅ Use managed secrets services in production
- ✅ Audit access to sensitive data
- ✅ Use different secrets per environment

**DON'T:**
- ❌ Commit `.env` files to version control
- ❌ Hardcode passwords in code
- ❌ Use default credentials in production
- ❌ Share secrets via email or chat
- ❌ Use simple/weak passwords
- ❌ Store secrets in comments or documentation

### Local Development
For local development, use `.env` file with development credentials:

```bash
# Copy example file
cp .env.example .env

# Edit with development passwords (NOT production!)
nano .env
```

**Important:** The `.env` file is git-ignored and never committed.

### Staging Environment
For staging (test deployments):

```bash
# Option 1: AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id pippulse/staging/secrets

# Option 2: Environment variables in CI/CD
# Set in GitHub Actions, GitLab CI, or similar

# Option 3: Docker secrets (Docker Swarm)
docker secret create pippulse_db_password db_password.txt
```

### Production Environment
**Mandatory: Use AWS Secrets Manager or equivalent**

```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name pippulse/prod/mongodb-password \
  --secret-string "your-secure-password"

# Retrieve in application
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id pippulse/prod/mongodb-password \
  --query 'SecretString' \
  --output text)

# Set as environment variable
export MONGO_PASSWORD=$SECRET
```

### Secrets to Manage

| Secret | Used By | Environment | Min Length |
|--------|---------|-------------|-----------|
| MONGO_PASSWORD | MongoDB | All | 16 chars |
| POSTGRES_PASSWORD | PostgreSQL | All | 16 chars |
| INFLUXDB_TOKEN | InfluxDB | All | 32 chars |
| JWT_SECRET_KEY | API Auth | All | 32 chars |
| NEWSAPI_KEY | News API | Prod only | - |
| ALPHAVANTAGE_API_KEY | Price Data | Prod only | - |
| TWITTER_BEARER_TOKEN | Twitter API | Prod only | - |

### Rotation Schedule
- **Dev passwords**: Change monthly or when developer leaves
- **Staging passwords**: Change weekly
- **Production passwords**: Change monthly (zero-downtime rotation recommended)
- **API keys**: Rotate quarterly or if compromised

### Monitoring & Auditing
```bash
# Check which services are using secrets
docker-compose ps

# View secret usage in logs (be careful!)
docker-compose logs backend | grep -i password  # CAUTION: may expose secrets

# Audit CloudTrail for AWS Secrets Manager access (AWS only)
aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=pippulse
```

### Emergency Rotation
If a secret is compromised:

```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -base64 32)

# 2. Update in AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id pippulse/prod/mongodb-password \
  --secret-string "$NEW_SECRET"

# 3. Restart affected services
docker-compose restart backend signal-engine collector

# 4. Verify services are running
docker-compose ps
```

## Docker Compose Deployment

### Starting Services
```bash
# Build and start all services
docker-compose up -d --build

# View service status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f signal-engine
```

### Service Endpoints

| Service | URL | Port |
|---------|-----|------|
| Backend API | http://localhost:8000 | 8000 |
| Frontend | http://localhost:3000 | 3000 |
| MongoDB | mongodb://localhost:27017 | 27017 |
| Redis | redis://localhost:6379 | 6379 |
| PostgreSQL | postgresql://localhost:5432 | 5432 |
| InfluxDB | http://localhost:8086 | 8086 |

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health/

# Detailed health
curl http://localhost:8000/health/detailed

# WebSocket metrics
curl http://localhost:8000/health/websocket/metrics

# Readiness
curl http://localhost:8000/health/ready

# Liveness
curl http://localhost:8000/health/live
```

### Stopping Services
```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop backend
```

## Production Deployment

### 1. Infrastructure Setup

**AWS ECS/Kubernetes Example:**
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pippulse-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pippulse-backend
  template:
    metadata:
      labels:
        app: pippulse-backend
    spec:
      containers:
      - name: backend
        image: pippulse/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### 2. Database Configuration

**MongoDB Atlas (Cloud):**
- Create cluster in MongoDB Atlas
- Configure IP whitelist
- Export connection string to `MONGODB_URI`

**PostgreSQL (RDS):**
- Create RDS instance
- Configure security groups
- Update `POSTGRES_URI` connection string

**Redis (ElastiCache):**
- Create ElastiCache cluster
- Enable encryption in transit
- Update `REDIS_URI`

### 3. Environment Configuration
```bash
# Production .env template
ENVIRONMENT=production
LOG_LEVEL=INFO

# External Services
NEWSAPI_KEY=${NEWSAPI_KEY}
TWITTER_BEARER_TOKEN=${TWITTER_BEARER_TOKEN}
# ... other API keys

# Database (use managed services)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/pippulse
POSTGRES_URI=postgresql://user:password@endpoint:5432/pippulse
REDIS_URI=redis://endpoint:6379/0
INFLUXDB_URL=https://influxdb.endpoint.com
INFLUXDB_TOKEN=${INFLUXDB_TOKEN}

# Performance
SIGNAL_LATENCY_TARGET=3
MAX_BATCH_SIZE=64
CONFIDENCE_THRESHOLD=0.7
```

### 4. SSL/TLS Configuration
```bash
# Use Let's Encrypt for SSL certificates
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d api.pippulse.ai

# Configure Nginx reverse proxy
nginx -t && nginx -s reload
```

### 5. Deployment Script
```bash
#!/bin/bash
# deploy.sh

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: ./deploy.sh <version>"
  exit 1
fi

echo "Deploying PipPulse AI v$VERSION"

# Pull latest code
git pull origin main

# Build Docker images
docker build -t pippulse/backend:$VERSION ./backend
docker build -t pippulse/frontend:$VERSION ./frontend

# Push to registry
docker push pippulse/backend:$VERSION
docker push pippulse/frontend:$VERSION

# Deploy via Kubernetes/ECS
kubectl set image deployment/pippulse-backend pippulse-backend=pippulse/backend:$VERSION

# Wait for rollout
kubectl rollout status deployment/pippulse-backend

echo "Deployment completed successfully"
```

## Monitoring & Observability

### 1. WebSocket Metrics
```bash
# Real-time WebSocket metrics
curl http://localhost:8000/health/websocket/metrics

# Sample response:
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "websocket": {
    "total_connections": 42,
    "avg_latency_ms": 15.3,
    "total_messages_sent": 2847,
    "total_messages_received": 1923
  }
}
```

### 2. Logging Configuration
```python
# Configure structured logging in production
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
        }
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### 3. Prometheus Metrics
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pippulse-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 4. Alerting Rules
```yaml
# alerts.yml
groups:
  - name: pippulse
    rules:
      - alert: HighWebSocketLatency
        expr: websocket_latency_ms > 50
        for: 5m
        annotations:
          summary: "High WebSocket latency detected"

      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate exceeds 5%"

      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_active >= db_connections_max
        for: 2m
        annotations:
          summary: "Database connection pool exhausted"
```

## Troubleshooting

### Service Won't Start
```bash
# Check container logs
docker-compose logs backend

# Verify database connectivity
docker-compose exec backend python -c "from app.database import get_mongodb; get_mongodb().command('ping')"

# Check environment variables
docker-compose exec backend env | grep -E "MONGO|REDIS|POSTGRES"
```

### WebSocket Connection Issues
```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/ws/

# Check connection metrics
curl http://localhost:8000/health/websocket/metrics

# Monitor real-time logs
docker-compose logs -f backend | grep -i websocket
```

### Database Connection Timeouts
```bash
# Check database service health
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
docker-compose exec postgres psql -U pippulse -c "SELECT 1"
docker-compose exec redis redis-cli ping

# Increase connection timeout in .env
DATABASE_TIMEOUT=30
CONNECTION_POOL_SIZE=20
```

### Memory Issues
```bash
# Monitor container memory usage
docker stats pippulse-backend

# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 1G

# Check Python memory usage
docker-compose exec backend python -m memory_profiler app/main.py
```

### Signal Generation Delays
```bash
# Check signal queue depth
docker-compose exec redis redis-cli LLEN signal_queue

# Monitor signal engine logs
docker-compose logs -f signal-engine

# Verify FinBERT model loaded
docker-compose exec signal-engine python -c "from transformers import AutoModelForSequenceClassification; model = AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert'); print('Model loaded successfully')"
```

## Performance Tuning

### 1. WebSocket Configuration
```python
# app/config.py
WEBSOCKET_CONFIG = {
    "message_queue_size": 100,
    "ping_interval": 30,
    "ping_timeout": 10,
    "connect_timeout": 5,
    "send_timeout": 5,
    "max_retries": 3,
    "retry_delay": 1.0
}
```

### 2. Database Connection Pooling
```python
# SQLAlchemy pool configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

### 3. Redis Optimization
```bash
# docker-compose.yml - Redis service
command: redis-server 
  --maxmemory 512mb 
  --maxmemory-policy allkeys-lru 
  --tcp-backlog 511 
  --tcp-keepalive 300 
  --timeout 0 
  --databases 16
```

### 4. Backend Performance
```python
# app/config.py
PERFORMANCE_CONFIG = {
    "worker_threads": 4,
    "async_tasks_max": 100,
    "cache_ttl": 300,  # 5 minutes
    "batch_size": 32,
    "signal_latency_target_ms": 3000
}
```

### 5. Frontend Optimization
```javascript
// next.config.js
module.exports = {
  compress: true,
  swcMinify: true,
  images: {
    domains: ['api.pippulse.ai'],
  },
  headers: async () => [
    {
      source: '/:path*',
      headers: [
        {
          key: 'Cache-Control',
          value: 'public, max-age=3600, must-revalidate'
        }
      ]
    }
  ]
}
```

### 6. Scaling Considerations
- **Horizontal Scaling**: Run multiple backend instances behind load balancer
- **Database Replication**: Set up MongoDB/PostgreSQL replication
- **Caching Layer**: Use Redis for session/signal cache
- **CDN**: Distribute frontend assets globally
- **Message Queue**: Use RabbitMQ/Celery for long-running tasks

## Support & Maintenance

### Regular Maintenance Tasks
- Daily: Check service health and error rates
- Weekly: Review performance metrics and optimize
- Monthly: Update dependencies and security patches
- Quarterly: Capacity planning and scaling assessment

### Rollback Procedure
```bash
# Rollback to previous version
kubectl rollout undo deployment/pippulse-backend

# Or manually
docker pull pippulse/backend:v1.2.0
docker tag pippulse/backend:v1.2.0 pippulse/backend:latest
docker-compose up -d
```

### Backup & Recovery
```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --archive > backup_$(date +%Y%m%d).archive

# Restore MongoDB
docker-compose exec mongodb mongorestore --archive < backup_20240115.archive

# Backup PostgreSQL
docker-compose exec postgres pg_dump -U pippulse > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
docker-compose exec postgres psql -U pippulse < backup_20240115.sql
```
