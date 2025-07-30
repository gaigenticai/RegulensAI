# RegulensAI Production Environment Deployment Runbook

## 📋 Overview

This runbook provides comprehensive instructions for deploying RegulensAI to the production environment with enterprise-grade security, high availability, and disaster recovery considerations.

## 🎯 Prerequisites

### Infrastructure Requirements
- Multi-zone Kubernetes cluster (v1.24+) with minimum 64GB RAM, 32 CPU cores
- High-availability PostgreSQL cluster (v14+) with 1TB+ storage, read replicas
- Redis Cluster (v6+) with 32GB memory, persistence enabled
- Multi-region load balancer with WAF and DDoS protection
- Container registry with vulnerability scanning
- Backup storage with cross-region replication

### Security Requirements
- Network segmentation and firewall rules
- SSL/TLS certificates from trusted CA
- Secrets management system (HashiCorp Vault, AWS Secrets Manager)
- Security scanning and compliance validation
- Audit logging and SIEM integration

### Compliance Requirements
- SOC 2 Type II compliance validation
- Data encryption at rest and in transit
- Access control and privilege management
- Backup and retention policies
- Incident response procedures

## 🔒 Pre-Deployment Security Validation

### Step 1: Security Scan and Compliance Check

```bash
# 1. Container security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image regulensai:production-v1.0.0

# 2. Kubernetes security scan
kubectl run kube-bench --rm -i --tty --restart=Never \
  --image=aquasec/kube-bench:latest -- --version 1.24

# 3. Network policy validation
kubectl apply --dry-run=client -f security/network-policies.yaml

# 4. RBAC validation
kubectl auth can-i --list --as=system:serviceaccount:regulensai-prod:regulensai-api
```

### Step 2: Database Security Hardening

```bash
# 1. Connect to production database cluster
export PROD_DB_URL="postgresql://regulensai_prod:secure_password@prod-db-cluster.example.com:5432/regulensai_prod"
export PROD_DB_REPLICA_URL="postgresql://regulensai_readonly:readonly_password@prod-db-replica.example.com:5432/regulensai_prod"

# 2. Verify SSL/TLS encryption
psql "$PROD_DB_URL?sslmode=require" -c "SHOW ssl;"

# 3. Database security audit
psql $PROD_DB_URL << EOF
-- Check user privileges
SELECT usename, usesuper, usecreatedb, usebypassrls FROM pg_user;

-- Verify encryption settings
SELECT name, setting FROM pg_settings WHERE name LIKE '%ssl%' OR name LIKE '%encrypt%';

-- Check authentication methods
SELECT * FROM pg_hba_file_rules WHERE type != 'comment';
EOF
```

## 🗄️ Production Database Deployment

### Step 3: Database Cluster Preparation

```bash
# 1. Create database backup before deployment
pg_dump $PROD_DB_URL > "backup_$(date +%Y%m%d_%H%M%S).sql"

# 2. Verify database cluster health
psql $PROD_DB_URL -c "SELECT * FROM pg_stat_replication;"

# 3. Test failover capabilities
# (Coordinate with DBA team for planned failover test)

# 4. Pre-migration validation
python core_infra/database/migrate.py \
  --database-url $PROD_DB_URL \
  --status \
  --validate-only
```

### Step 4: Production Schema Migration

```bash
# 1. Create migration checkpoint
psql $PROD_DB_URL -c "SELECT pg_create_restore_point('pre_migration_$(date +%Y%m%d_%H%M%S)');"

# 2. Run migration dry-run with timing
time python core_infra/database/migrate.py \
  --database-url $PROD_DB_URL \
  --dry-run \
  --verbose

# 3. Apply migrations with monitoring
python core_infra/database/migrate.py \
  --database-url $PROD_DB_URL \
  --monitor-performance \
  --timeout 3600

# 4. Verify migration success
psql $PROD_DB_URL << EOF
-- Check migration status
SELECT migration_name, applied_at FROM migration_history ORDER BY applied_at DESC LIMIT 10;

-- Verify table counts
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables 
ORDER BY n_tup_ins DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE idx_scan > 0 
ORDER BY idx_scan DESC;
EOF
```

### Step 5: Database Performance Optimization

```bash
# Apply production-specific optimizations
psql $PROD_DB_URL << EOF
-- Production PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET default_statistics_target = 500;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET max_worker_processes = 16;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 16;

-- Connection pooling settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements,auto_explain';

-- Reload configuration
SELECT pg_reload_conf();

-- Update table statistics
ANALYZE;

-- Reindex critical tables
REINDEX INDEX CONCURRENTLY idx_users_email;
REINDEX INDEX CONCURRENTLY idx_transactions_customer_id;
REINDEX INDEX CONCURRENTLY idx_compliance_tasks_status;
EOF
```

## 🚀 Production Application Deployment

### Step 6: Blue-Green Deployment Setup

```bash
# 1. Create production namespace
kubectl create namespace regulensai-prod

# 2. Label nodes for production workloads
kubectl label nodes prod-node-1 prod-node-2 prod-node-3 \
  workload-type=production \
  security-zone=restricted

# 3. Create production secrets from vault
vault kv get -format=json secret/regulensai/prod | \
  jq -r '.data.data | to_entries[] | "kubectl create secret generic \(.key) --namespace=regulensai-prod --from-literal=value=\(.value)"' | \
  bash

# 4. Deploy blue environment (current production)
helm install regulensai-blue ./helm/regulensai \
  --namespace regulensai-prod \
  --values ./helm/regulensai/values-production.yaml \
  --set image.tag=production-v1.0.0 \
  --set deployment.color=blue \
  --set database.url="$PROD_DB_URL" \
  --set database.replicaUrl="$PROD_DB_REPLICA_URL"
```

### Step 7: Green Environment Deployment

```bash
# 1. Deploy green environment (new version)
helm install regulensai-green ./helm/regulensai \
  --namespace regulensai-prod \
  --values ./helm/regulensai/values-production.yaml \
  --set image.tag=production-v1.1.0 \
  --set deployment.color=green \
  --set database.url="$PROD_DB_URL" \
  --set database.replicaUrl="$PROD_DB_REPLICA_URL" \
  --set service.enabled=false  # Don't expose to traffic yet

# 2. Wait for green deployment to be ready
kubectl wait --for=condition=available --timeout=600s \
  deployment/regulensai-green-api -n regulensai-prod

# 3. Run comprehensive health checks on green environment
kubectl exec -n regulensai-prod deployment/regulensai-green-api -- \
  python -m pytest tests/health/ -v --tb=short
```

### Step 8: Production Validation

```bash
# 1. Database connectivity test
kubectl exec -n regulensai-prod deployment/regulensai-green-api -- \
  python -c "
import asyncio
from core_infra.database import get_database
async def test_prod_db():
    async with get_database() as db:
        # Test read operations
        user_count = await db.fetchval('SELECT COUNT(*) FROM users')
        print(f'User count: {user_count}')
        
        # Test write operations (safe test)
        test_id = await db.fetchval('SELECT gen_random_uuid()')
        print(f'UUID generation test: {test_id}')
        
        # Test complex query performance
        import time
        start = time.time()
        result = await db.fetchval('''
            SELECT COUNT(*) FROM compliance_tasks ct 
            JOIN users u ON ct.assigned_to = u.id 
            WHERE ct.status = 'pending'
        ''')
        duration = time.time() - start
        print(f'Complex query result: {result}, duration: {duration:.3f}s')
asyncio.run(test_prod_db())
"

# 2. API functionality test
GREEN_SERVICE_IP=$(kubectl get svc regulensai-green-api -n regulensai-prod -o jsonpath='{.spec.clusterIP}')

# Test authentication
TOKEN=$(curl -s -X POST http://$GREEN_SERVICE_IP:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@regulens.ai", "password": "production_password"}' | \
  jq -r '.access_token')

# Test core endpoints
curl -H "Authorization: Bearer $TOKEN" \
  http://$GREEN_SERVICE_IP:8000/api/v1/dashboard/metrics

curl -H "Authorization: Bearer $TOKEN" \
  http://$GREEN_SERVICE_IP:8000/api/v1/compliance/tasks?page=1&size=5

# 3. Performance benchmark
kubectl run load-test --rm -i --tty --restart=Never \
  --image=loadimpact/k6:latest -- run - <<EOF
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 50,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function() {
  let response = http.get('http://$GREEN_SERVICE_IP:8000/api/v1/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });
}
EOF
```

## 🔄 Blue-Green Traffic Switch

### Step 9: Gradual Traffic Migration

```bash
# 1. Route 10% traffic to green environment
kubectl patch service regulensai-api -n regulensai-prod -p '
{
  "spec": {
    "selector": {
      "app": "regulensai-api"
    }
  },
  "metadata": {
    "annotations": {
      "nginx.ingress.kubernetes.io/canary": "true",
      "nginx.ingress.kubernetes.io/canary-weight": "10"
    }
  }
}'

# 2. Monitor metrics for 15 minutes
kubectl logs -f -n regulensai-prod deployment/regulensai-green-api

# 3. Increase to 50% traffic
kubectl patch service regulensai-api -n regulensai-prod -p '
{
  "metadata": {
    "annotations": {
      "nginx.ingress.kubernetes.io/canary-weight": "50"
    }
  }
}'

# 4. Monitor for another 15 minutes, then switch 100%
kubectl patch service regulensai-api -n regulensai-prod -p '
{
  "spec": {
    "selector": {
      "app": "regulensai-green-api"
    }
  },
  "metadata": {
    "annotations": {
      "nginx.ingress.kubernetes.io/canary": "false"
    }
  }
}'
```

### Step 10: Post-Deployment Validation

```bash
# 1. Comprehensive system health check
curl -f https://api.regulens.ai/api/v1/health

# 2. Database performance monitoring
psql $PROD_DB_URL << EOF
-- Monitor active connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

-- Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';

-- Monitor database size
SELECT pg_size_pretty(pg_database_size('regulensai_prod'));
EOF

# 3. Application metrics validation
kubectl exec -n regulensai-prod deployment/regulensai-green-api -- \
  curl -s http://localhost:8000/metrics | grep -E "(http_requests_total|database_connections_active)"
```

## 📊 Production Monitoring Setup

### Step 11: Enhanced Monitoring and Alerting

```bash
# 1. Deploy production monitoring stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring/production-values.yaml \
  --set grafana.adminPassword="$(vault kv get -field=password secret/grafana/admin)"

# 2. Configure database monitoring
kubectl apply -f monitoring/postgres-exporter-production.yaml

# 3. Set up critical alerts
kubectl apply -f monitoring/production-alerts.yaml

# 4. Configure log aggregation
kubectl apply -f logging/fluentd-production.yaml
```

## 🔄 Rollback Procedures

### Emergency Rollback

```bash
# 1. Immediate traffic switch back to blue
kubectl patch service regulensai-api -n regulensai-prod -p '
{
  "spec": {
    "selector": {
      "app": "regulensai-blue-api"
    }
  }
}'

# 2. Database rollback (if migration issues)
psql $PROD_DB_URL -c "SELECT pg_create_restore_point('emergency_rollback_$(date +%Y%m%d_%H%M%S)');"
python core_infra/database/migrate.py --database-url $PROD_DB_URL --rollback last_migration

# 3. Verify rollback success
curl -f https://api.regulens.ai/api/v1/health
```

## ✅ Production Deployment Checklist

- [ ] Security scans passed
- [ ] Database cluster health verified
- [ ] Schema migrations applied successfully
- [ ] Blue-green deployment completed
- [ ] Performance benchmarks met
- [ ] Monitoring and alerting configured
- [ ] SSL certificates valid
- [ ] Backup procedures verified
- [ ] Disaster recovery tested
- [ ] Compliance validation completed
- [ ] Documentation updated
- [ ] Stakeholders notified

## 🚨 Emergency Contacts

- **Production On-Call**: +1-555-PROD (7763)
- **Database Team**: dba-oncall@regulens.ai
- **Security Team**: security-incident@regulens.ai
- **Engineering Manager**: eng-manager@regulens.ai
- **CTO**: cto@regulens.ai
