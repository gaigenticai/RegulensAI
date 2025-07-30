# RegulensAI Staging Environment Deployment Runbook

## 📋 Overview

This runbook provides step-by-step instructions for deploying RegulensAI to the staging environment, including database schema management, application deployment, and verification procedures.

## 🎯 Prerequisites

### Infrastructure Requirements
- Kubernetes cluster (v1.24+) with minimum 16GB RAM, 8 CPU cores
- PostgreSQL database (v14+) with 100GB storage
- Redis cluster (v6+) with 8GB memory
- Load balancer with SSL termination
- Container registry access (Docker Hub, ECR, or GCR)

### Access Requirements
- Kubernetes cluster admin access
- Database admin credentials
- Container registry push/pull permissions
- DNS management access
- SSL certificate management

### Tools Required
```bash
# Install required tools
kubectl version --client
helm version
docker version
psql --version
```

## 🗄️ Database Preparation

### Step 1: Database Setup and Validation

```bash
# 1. Connect to staging database
export STAGING_DB_URL="postgresql://username:password@staging-db.example.com:5432/regulensai_staging"
psql $STAGING_DB_URL

# 2. Verify database connectivity and permissions
\l
\dt
\du

# 3. Create database if not exists
CREATE DATABASE regulensai_staging;
CREATE USER regulensai_staging WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE regulensai_staging TO regulensai_staging;

# 4. Enable required extensions
\c regulensai_staging
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "vector";
```

### Step 2: Schema Migration

```bash
# 1. Clone repository and navigate to database directory
git clone https://github.com/gaigenticai/RegulensAI.git
cd RegulensAI/core_infra/database

# 2. Run migration status check
python migrate.py --database-url $STAGING_DB_URL --status

# 3. Perform dry-run migration
python migrate.py --database-url $STAGING_DB_URL --dry-run

# 4. Apply all migrations
python migrate.py --database-url $STAGING_DB_URL

# 5. Verify schema deployment
psql $STAGING_DB_URL -c "\dt"
psql $STAGING_DB_URL -c "SELECT COUNT(*) FROM migration_history;"
```

### Step 3: Database Performance Optimization

```bash
# Apply staging-specific database optimizations
psql $STAGING_DB_URL << EOF
-- Update PostgreSQL configuration for staging
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();

-- Analyze all tables for query optimization
ANALYZE;
EOF
```

## 🚀 Application Deployment

### Step 4: Environment Configuration

```bash
# 1. Create staging namespace
kubectl create namespace regulensai-staging

# 2. Create configuration secrets
kubectl create secret generic regulensai-secrets \
  --namespace=regulensai-staging \
  --from-literal=database-url="$STAGING_DB_URL" \
  --from-literal=jwt-secret="staging-jwt-secret-key" \
  --from-literal=encryption-key="staging-encryption-key" \
  --from-literal=redis-password="staging-redis-password"

# 3. Create external API secrets
kubectl create secret generic external-api-secrets \
  --namespace=regulensai-staging \
  --from-literal=refinitiv-api-key="staging-refinitiv-key" \
  --from-literal=experian-client-id="staging-experian-id" \
  --from-literal=smtp-password="staging-smtp-password"
```

### Step 5: Helm Deployment

```bash
# 1. Add Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 2. Install dependencies
helm install redis bitnami/redis \
  --namespace regulensai-staging \
  --set auth.password=staging-redis-password \
  --set master.persistence.size=20Gi

# 3. Deploy RegulensAI application
helm install regulensai ./helm/regulensai \
  --namespace regulensai-staging \
  --values ./helm/regulensai/values-staging.yaml \
  --set image.tag=staging-latest \
  --set database.url="$STAGING_DB_URL" \
  --set environment=staging

# 4. Verify deployment
kubectl get pods -n regulensai-staging
kubectl get services -n regulensai-staging
kubectl get ingress -n regulensai-staging
```

### Step 6: Database Migration Verification

```bash
# 1. Check migration pod logs
kubectl logs -n regulensai-staging -l app=regulensai-migration

# 2. Verify database schema
kubectl exec -n regulensai-staging deployment/regulensai-api -- \
  python -c "
from core_infra.database.models import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \\'public\\''))
    print(f'Tables created: {result.scalar()}')
    
    result = conn.execute(text('SELECT migration_name FROM migration_history ORDER BY applied_at'))
    migrations = result.fetchall()
    print(f'Applied migrations: {[m[0] for m in migrations]}')
"

# 3. Test database connectivity from application
kubectl exec -n regulensai-staging deployment/regulensai-api -- \
  python -c "
import asyncio
from core_infra.database import get_database
async def test_db():
    async with get_database() as db:
        result = await db.fetchval('SELECT 1')
        print(f'Database connection test: {result}')
asyncio.run(test_db())
"
```

## 🔍 Verification and Testing

### Step 7: Health Checks

```bash
# 1. Check application health
curl -f http://staging.regulens.ai/api/v1/health

# 2. Test authentication
curl -X POST http://staging.regulens.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@regulens.ai", "password": "admin123"}'

# 3. Test database-dependent endpoints
TOKEN="your-jwt-token"
curl -H "Authorization: Bearer $TOKEN" \
  http://staging.regulens.ai/api/v1/dashboard/metrics

# 4. Test training portal
curl -H "Authorization: Bearer $TOKEN" \
  http://staging.regulens.ai/api/v1/training/modules
```

### Step 8: Performance Validation

```bash
# 1. Database performance check
kubectl exec -n regulensai-staging deployment/regulensai-api -- \
  python -c "
import time
from core_infra.database import get_database
async def perf_test():
    start = time.time()
    async with get_database() as db:
        await db.fetchval('SELECT COUNT(*) FROM users')
    print(f'Query time: {time.time() - start:.3f}s')
asyncio.run(perf_test())
"

# 2. Load test with k6
k6 run --vus 10 --duration 30s tests/performance/staging-load-test.js
```

## 📊 Monitoring Setup

### Step 9: Monitoring and Alerting

```bash
# 1. Install monitoring stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=staging-grafana-password

# 2. Configure database monitoring
kubectl apply -f monitoring/postgres-exporter.yaml

# 3. Set up alerts
kubectl apply -f monitoring/staging-alerts.yaml
```

## 🔄 Rollback Procedures

### Emergency Rollback

```bash
# 1. Rollback application deployment
helm rollback regulensai -n regulensai-staging

# 2. Rollback database migration (if needed)
python migrate.py --database-url $STAGING_DB_URL --rollback migration_name

# 3. Verify rollback
kubectl get pods -n regulensai-staging
curl -f http://staging.regulens.ai/api/v1/health
```

## ✅ Post-Deployment Checklist

- [ ] Database schema deployed successfully
- [ ] All migrations applied without errors
- [ ] Application pods running and healthy
- [ ] Health endpoints responding correctly
- [ ] Authentication working properly
- [ ] Database connectivity verified
- [ ] Performance metrics within acceptable ranges
- [ ] Monitoring and alerting configured
- [ ] SSL certificates valid and configured
- [ ] DNS records pointing to correct load balancer
- [ ] Backup procedures tested
- [ ] Documentation updated with any changes

## 🚨 Troubleshooting

### Common Issues

**Database Connection Failures:**
```bash
# Check database connectivity
kubectl exec -n regulensai-staging deployment/regulensai-api -- \
  nc -zv staging-db.example.com 5432

# Check secrets
kubectl get secret regulensai-secrets -n regulensai-staging -o yaml
```

**Migration Failures:**
```bash
# Check migration logs
kubectl logs -n regulensai-staging -l app=regulensai-migration

# Manual migration status
python migrate.py --database-url $STAGING_DB_URL --status
```

**Performance Issues:**
```bash
# Check database performance
psql $STAGING_DB_URL -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
"
```

## 📞 Support Contacts

- **DevOps Team**: devops@regulens.ai
- **Database Team**: dba@regulens.ai
- **On-call Engineer**: +1-555-0123
- **Escalation**: engineering-manager@regulens.ai
