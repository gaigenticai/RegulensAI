# RegulensAI Operational Procedures Training

## Table of Contents

1. [Overview](#overview)
2. [System Administration](#system-administration)
3. [Monitoring and Alerting](#monitoring-and-alerting)
4. [Incident Response](#incident-response)
5. [Backup and Recovery](#backup-and-recovery)
6. [Security Operations](#security-operations)
7. [Performance Management](#performance-management)
8. [Change Management](#change-management)

## Overview

This training covers essential operational procedures for managing the RegulensAI platform in production environments. It's designed for system administrators, DevOps engineers, and operations teams.

### Learning Objectives

After completing this training, you will be able to:
- Perform routine system administration tasks
- Monitor system health and performance
- Respond to incidents effectively
- Execute backup and recovery procedures
- Manage security operations
- Implement performance optimizations
- Follow change management processes

### Prerequisites

- Basic knowledge of Kubernetes
- Familiarity with Linux/Unix systems
- Understanding of monitoring concepts
- Basic networking knowledge

## System Administration

### Daily Operations Checklist

#### Morning Health Check (9:00 AM)

```bash
#!/bin/bash
# daily_health_check.sh

echo "=== RegulensAI Daily Health Check ==="
echo "Date: $(date)"
echo

# 1. Check Kubernetes cluster status
echo "1. Kubernetes Cluster Status:"
kubectl cluster-info
kubectl get nodes
echo

# 2. Check pod status
echo "2. Pod Status:"
kubectl get pods -n regulensai -o wide
echo

# 3. Check service status
echo "3. Service Status:"
kubectl get services -n regulensai
echo

# 4. Check ingress status
echo "4. Ingress Status:"
kubectl get ingress -n regulensai
echo

# 5. Check persistent volumes
echo "5. Persistent Volume Status:"
kubectl get pv,pvc -n regulensai
echo

# 6. Check resource usage
echo "6. Resource Usage:"
kubectl top nodes
kubectl top pods -n regulensai
echo

# 7. Check recent events
echo "7. Recent Events:"
kubectl get events -n regulensai --sort-by='.lastTimestamp' | tail -10
echo

echo "=== Health Check Complete ==="
```

#### Weekly Maintenance Tasks

**Every Monday (2:00 AM):**
- Update system packages
- Rotate log files
- Clean up old container images
- Review security patches
- Update documentation

**Weekly Maintenance Script:**
```bash
#!/bin/bash
# weekly_maintenance.sh

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean up Docker images
docker system prune -f

# Rotate logs
sudo logrotate -f /etc/logrotate.conf

# Clean up old Kubernetes resources
kubectl delete pods --field-selector=status.phase=Succeeded -n regulensai
kubectl delete pods --field-selector=status.phase=Failed -n regulensai

# Generate weekly report
python3 /opt/regulensai/scripts/weekly_report.py
```

### User Management

#### Adding New Users

```bash
# Create new user account
kubectl create serviceaccount new-user -n regulensai

# Create role binding
kubectl create rolebinding new-user-binding \
  --clusterrole=regulensai-user \
  --serviceaccount=regulensai:new-user \
  -n regulensai

# Generate access token
kubectl create token new-user -n regulensai
```

#### Managing Permissions

```yaml
# regulensai-user-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: regulensai
  name: regulensai-user
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
```

### Configuration Management

#### Environment Configuration

```bash
# Production environment variables
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export DEBUG=false

# Database configuration
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=30

# Redis configuration
export REDIS_POOL_SIZE=10
export REDIS_TIMEOUT=5

# Apply configuration
kubectl apply -f k8s/manifests/configmap.yaml
```

#### Secret Management

```bash
# Update secrets
kubectl create secret generic regulensai-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=encryption-key="..." \
  --dry-run=client -o yaml | kubectl apply -f -

# Rotate secrets
kubectl patch secret regulensai-secrets -p='{"data":{"api-key":"'$(echo -n "new-api-key" | base64)'"}}'
```

## Monitoring and Alerting

### Accessing Monitoring Systems

#### Grafana Dashboard

1. **URL**: https://grafana.regulensai.com
2. **Login**: Use SSO or admin credentials
3. **Key Dashboards**:
   - RegulensAI Overview
   - API Performance
   - External Data Providers
   - System Resources

#### Prometheus Metrics

1. **URL**: https://prometheus.regulensai.com
2. **Key Metrics**:
   - `regulensai_api_requests_total`
   - `regulensai_external_data_requests_total`
   - `regulensai_notifications_sent_total`
   - `regulensai_system_cpu_usage_percent`

#### Jaeger Tracing

1. **URL**: https://jaeger.regulensai.com
2. **Usage**:
   - Search traces by service
   - Analyze request flows
   - Identify performance bottlenecks

### Alert Management

#### Alert Categories

**Critical Alerts (Immediate Response)**:
- Service outages
- High error rates (>5%)
- SLA violations
- Security incidents

**Warning Alerts (Response within 1 hour)**:
- Performance degradation
- Resource usage spikes
- External provider issues

**Info Alerts (Response within 4 hours)**:
- Capacity planning alerts
- Maintenance reminders
- Configuration changes

#### Alert Response Procedures

**Step 1: Acknowledge Alert**
```bash
# Acknowledge alert in AlertManager
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{"status": "acknowledged", "alertname": "HighAPIErrorRate"}'
```

**Step 2: Initial Assessment**
- Check service status
- Review recent changes
- Analyze metrics and logs
- Determine impact scope

**Step 3: Escalation (if needed)**
- Contact on-call engineer
- Notify management for critical issues
- Update status page

### Log Management

#### Accessing Logs

```bash
# Application logs
kubectl logs -f deployment/regulensai-api -n regulensai

# System logs
sudo journalctl -u kubelet -f

# Aggregated logs (if using ELK stack)
curl -X GET "elasticsearch:9200/regulensai-logs/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"level": "ERROR"}}}'
```

#### Log Analysis

**Common Log Patterns**:
- Error patterns: `ERROR|CRITICAL|FATAL`
- Performance issues: `timeout|slow|latency`
- Security events: `authentication|authorization|security`

**Log Analysis Script**:
```bash
#!/bin/bash
# analyze_logs.sh

# Get recent errors
kubectl logs deployment/regulensai-api -n regulensai --since=1h | grep -i error

# Check for performance issues
kubectl logs deployment/regulensai-api -n regulensai --since=1h | grep -i "timeout\|slow"

# Security events
kubectl logs deployment/regulensai-api -n regulensai --since=1h | grep -i "auth\|security"
```

## Incident Response

### Incident Classification

#### Severity Levels

**Severity 1 (Critical)**:
- Complete system outage
- Data breach or security incident
- Compliance violation
- **Response Time**: 15 minutes

**Severity 2 (High)**:
- Partial system outage
- Performance degradation affecting multiple tenants
- External integration failures
- **Response Time**: 1 hour

**Severity 3 (Medium)**:
- Single tenant issues
- Non-critical feature failures
- **Response Time**: 4 hours

**Severity 4 (Low)**:
- Minor bugs
- Documentation issues
- **Response Time**: 24 hours

### Incident Response Process

#### Step 1: Detection and Alerting

**Automated Detection**:
- Monitoring alerts
- Health check failures
- User reports

**Manual Detection**:
- User complaints
- Support tickets
- Routine checks

#### Step 2: Initial Response

```bash
# Incident response checklist
echo "=== Incident Response Checklist ==="
echo "1. Acknowledge the incident"
echo "2. Assess the impact and severity"
echo "3. Notify stakeholders"
echo "4. Begin investigation"
echo "5. Implement immediate fixes"
echo "6. Monitor for resolution"
echo "7. Document the incident"
```

#### Step 3: Investigation

**Gather Information**:
- Check monitoring dashboards
- Review recent changes
- Analyze logs and metrics
- Interview witnesses

**Investigation Tools**:
```bash
# Check system status
kubectl get all -n regulensai

# Review recent events
kubectl get events -n regulensai --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n regulensai

# Review logs
kubectl logs deployment/regulensai-api -n regulensai --since=2h
```

#### Step 4: Resolution

**Common Resolution Steps**:
1. Restart affected services
2. Scale resources if needed
3. Apply configuration fixes
4. Rollback recent changes
5. Implement workarounds

**Resolution Scripts**:
```bash
# Restart service
kubectl rollout restart deployment/regulensai-api -n regulensai

# Scale up resources
kubectl scale deployment regulensai-api --replicas=5 -n regulensai

# Emergency rollback
helm rollback regulensai -n regulensai
```

#### Step 5: Communication

**Internal Communication**:
- Update incident channel
- Notify management
- Brief team members

**External Communication**:
- Update status page
- Notify affected customers
- Provide regular updates

### Post-Incident Review

#### Incident Report Template

```markdown
# Incident Report: [Incident Title]

## Summary
- **Date**: [Date]
- **Duration**: [Start time] - [End time]
- **Severity**: [1-4]
- **Impact**: [Description of impact]

## Timeline
- [Time]: Incident detected
- [Time]: Initial response
- [Time]: Root cause identified
- [Time]: Fix implemented
- [Time]: Incident resolved

## Root Cause
[Detailed description of what caused the incident]

## Resolution
[Description of how the incident was resolved]

## Lessons Learned
- What went well
- What could be improved
- Action items for prevention

## Action Items
- [ ] [Action item 1] - [Owner] - [Due date]
- [ ] [Action item 2] - [Owner] - [Due date]
```

## Backup and Recovery

### Backup Procedures

#### Database Backups

```bash
#!/bin/bash
# database_backup.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="regulensai_backup_${BACKUP_DATE}.sql"

# Create database backup
pg_dump -h $DB_HOST -U $DB_USER -d regulensai > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to S3
aws s3 cp ${BACKUP_FILE}.gz s3://regulensai-backups/database/

# Clean up local files older than 7 days
find /backup/database -name "*.gz" -mtime +7 -delete
```

#### Configuration Backups

```bash
#!/bin/bash
# config_backup.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/config/${BACKUP_DATE}"

mkdir -p $BACKUP_DIR

# Backup Kubernetes configurations
kubectl get all -n regulensai -o yaml > $BACKUP_DIR/k8s-resources.yaml
kubectl get configmaps -n regulensai -o yaml > $BACKUP_DIR/configmaps.yaml
kubectl get secrets -n regulensai -o yaml > $BACKUP_DIR/secrets.yaml

# Backup Helm values
helm get values regulensai -n regulensai > $BACKUP_DIR/helm-values.yaml

# Create archive
tar -czf config_backup_${BACKUP_DATE}.tar.gz -C /backup/config ${BACKUP_DATE}

# Upload to S3
aws s3 cp config_backup_${BACKUP_DATE}.tar.gz s3://regulensai-backups/config/
```

### Recovery Procedures

#### Database Recovery

```bash
#!/bin/bash
# database_recovery.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Download backup from S3
aws s3 cp s3://regulensai-backups/database/$BACKUP_FILE .

# Decompress backup
gunzip $BACKUP_FILE

# Stop application
kubectl scale deployment regulensai-api --replicas=0 -n regulensai

# Restore database
psql -h $DB_HOST -U $DB_USER -d regulensai < ${BACKUP_FILE%.gz}

# Start application
kubectl scale deployment regulensai-api --replicas=3 -n regulensai

# Verify recovery
kubectl wait --for=condition=ready pod -l app=regulensai-api -n regulensai --timeout=300s
```

#### Disaster Recovery

**Recovery Time Objectives (RTO)**:
- Critical systems: 1 hour
- Non-critical systems: 4 hours

**Recovery Point Objectives (RPO)**:
- Database: 15 minutes
- Configuration: 1 hour

**Disaster Recovery Steps**:
1. Assess the scope of the disaster
2. Activate disaster recovery team
3. Restore from backups
4. Verify system functionality
5. Resume normal operations

## Security Operations

### Security Monitoring

#### Security Metrics

- Failed authentication attempts
- Privilege escalation attempts
- Unusual access patterns
- Configuration changes
- Data access patterns

#### Security Alerts

```bash
# Check for security events
kubectl logs deployment/regulensai-api -n regulensai | grep -i "authentication\|authorization\|security"

# Monitor failed logins
grep "authentication failed" /var/log/auth.log | tail -20

# Check for privilege escalation
sudo ausearch -m avc -ts recent
```

### Vulnerability Management

#### Regular Security Scans

```bash
#!/bin/bash
# security_scan.sh

# Scan container images
trivy image regulensai/api:latest

# Scan Kubernetes configurations
kube-score score k8s/manifests/*.yaml

# Check for CVEs
cve-bin-tool --file requirements.txt
```

#### Security Updates

**Monthly Security Review**:
- Review security patches
- Update base images
- Scan for vulnerabilities
- Update security policies

### Access Control

#### Role-Based Access Control (RBAC)

```yaml
# security-admin-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: security-admin
rules:
- apiGroups: [""]
  resources: ["secrets", "serviceaccounts"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

#### Audit Logging

```bash
# Enable audit logging
kubectl patch configmap audit-policy -n kube-system --patch '
data:
  audit-policy.yaml: |
    apiVersion: audit.k8s.io/v1
    kind: Policy
    rules:
    - level: Metadata
      resources:
      - group: ""
        resources: ["secrets", "configmaps"]
'
```

## Performance Management

### Performance Monitoring

#### Key Performance Indicators

- **API Response Time**: < 2 seconds (95th percentile)
- **Throughput**: > 1000 requests/minute
- **Error Rate**: < 1%
- **Availability**: > 99.9%
- **Resource Utilization**: < 80%

#### Performance Analysis

```bash
# Check API performance
kubectl exec -it deployment/regulensai-api -n regulensai -- \
  curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Monitor resource usage
kubectl top pods -n regulensai --sort-by=cpu
kubectl top pods -n regulensai --sort-by=memory
```

### Performance Optimization

#### Scaling Strategies

**Horizontal Pod Autoscaling**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: regulensai-api-hpa
  namespace: regulensai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: regulensai-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Vertical Pod Autoscaling**:
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: regulensai-api-vpa
  namespace: regulensai
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: regulensai-api
  updatePolicy:
    updateMode: "Auto"
```

## Change Management

### Change Control Process

#### Change Categories

**Standard Changes**:
- Routine maintenance
- Security patches
- Configuration updates
- **Approval**: Automated

**Normal Changes**:
- Feature deployments
- Infrastructure changes
- **Approval**: Change Advisory Board

**Emergency Changes**:
- Security fixes
- Critical bug fixes
- **Approval**: Emergency Change Authority

### Deployment Procedures

#### Blue-Green Deployment

```bash
# Execute blue-green deployment
python3 scripts/blue_green_deployment.py deploy \
  --image-tag v1.2.0 \
  --environment production \
  --namespace regulensai
```

#### Rollback Procedures

```bash
# Emergency rollback
helm rollback regulensai -n regulensai

# Or using blue-green script
python3 scripts/blue_green_deployment.py rollback \
  --environment production \
  --namespace regulensai
```

### Testing Procedures

#### Pre-deployment Testing

```bash
# Run smoke tests
python3 scripts/smoke_tests.py --environment staging

# Run integration tests
pytest tests/integration/ -v

# Run performance tests
python3 scripts/performance_tests.py --environment staging
```

#### Post-deployment Verification

```bash
# Verify deployment
python3 scripts/production_verification.py --environment production

# Check health endpoints
curl -f https://api.regulensai.com/health

# Monitor metrics
python3 scripts/monitor_deployment.py --duration 30m
```

## Training Exercises

### Exercise 1: Daily Operations

1. Execute the daily health check script
2. Review monitoring dashboards
3. Check for any alerts or issues
4. Document findings

### Exercise 2: Incident Response

1. Simulate a service outage
2. Follow incident response procedures
3. Implement resolution steps
4. Complete post-incident review

### Exercise 3: Backup and Recovery

1. Execute backup procedures
2. Simulate a data loss scenario
3. Perform recovery procedures
4. Verify data integrity

### Exercise 4: Performance Analysis

1. Analyze current performance metrics
2. Identify potential bottlenecks
3. Implement optimization strategies
4. Measure improvement

## Additional Resources

- **Runbooks**: https://docs.regulensai.com/runbooks
- **Monitoring Dashboards**: https://grafana.regulensai.com
- **Support Portal**: https://support.regulensai.com
- **Emergency Contacts**: Available in incident response documentation

## Support and Feedback

For questions about operational procedures:
- **Email**: operations@regulensai.com
- **Slack**: #operations-support
- **Phone**: +1-XXX-XXX-XXXX (24/7 for critical issues)

---

*This training guide is part of the RegulensAI operations certification program.*
