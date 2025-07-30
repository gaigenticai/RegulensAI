# RegulensAI Troubleshooting Runbook

This runbook provides step-by-step troubleshooting procedures for common issues in RegulensAI production environments.

## Table of Contents

1. [Emergency Response](#emergency-response)
2. [System Health Checks](#system-health-checks)
3. [Common Issues](#common-issues)
4. [External Integration Issues](#external-integration-issues)
5. [Performance Issues](#performance-issues)
6. [Database Issues](#database-issues)
7. [Notification System Issues](#notification-system-issues)
8. [Security Incidents](#security-incidents)
9. [Escalation Procedures](#escalation-procedures)

## Emergency Response

### Immediate Actions for Critical Issues

1. **Assess Impact**
   - Determine scope of the issue
   - Identify affected tenants/users
   - Check system availability

2. **Initial Response**
   ```bash
   # Check system status
   kubectl get pods -n regulensai
   kubectl get services -n regulensai
   
   # Check application logs
   kubectl logs -f deployment/regulensai-api -n regulensai
   kubectl logs -f deployment/regulensai-worker -n regulensai
   ```

3. **Communication**
   - Notify stakeholders via status page
   - Update incident tracking system
   - Prepare regular status updates

### Emergency Contacts

- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **Platform Team Lead**: +1-XXX-XXX-XXXX
- **DevOps Team**: devops@regulensai.com
- **Security Team**: security@regulensai.com

## System Health Checks

### Quick Health Assessment

```bash
#!/bin/bash
# health_check.sh - Quick system health assessment

echo "=== RegulensAI Health Check ==="
echo "Timestamp: $(date)"
echo

# Check Kubernetes cluster
echo "1. Kubernetes Cluster Status:"
kubectl cluster-info
echo

# Check pod status
echo "2. Pod Status:"
kubectl get pods -n regulensai -o wide
echo

# Check service status
echo "3. Service Status:"
kubectl get services -n regulensai
echo

# Check ingress status
echo "4. Ingress Status:"
kubectl get ingress -n regulensai
echo

# Check database connectivity
echo "5. Database Connectivity:"
python3 -c "
import os
from supabase import create_client
try:
    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
    result = client.table('health_check').select('*').limit(1).execute()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
"
echo

# Check external API connectivity
echo "6. External API Connectivity:"
curl -s -o /dev/null -w "OFAC API: %{http_code}\n" https://www.treasury.gov/ofac/downloads/sdn.xml
curl -s -o /dev/null -w "EU Sanctions API: %{http_code}\n" https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content
echo

echo "=== Health Check Complete ==="
```

### Automated Monitoring Checks

```python
# monitoring_checks.py
import asyncio
import aiohttp
import time
from datetime import datetime

async def check_api_endpoints():
    """Check critical API endpoints."""
    endpoints = [
        'https://api.regulensai.com/v1/health',
        'https://api.regulensai.com/v1/external-data/health',
        'https://api.regulensai.com/v1/notifications/health'
    ]
    
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                start_time = time.time()
                async with session.get(endpoint, timeout=10) as response:
                    response_time = (time.time() - start_time) * 1000
                    results[endpoint] = {
                        'status': response.status,
                        'response_time_ms': response_time,
                        'healthy': response.status == 200
                    }
            except Exception as e:
                results[endpoint] = {
                    'status': 'error',
                    'error': str(e),
                    'healthy': False
                }
    
    return results

# Run health checks
if __name__ == "__main__":
    results = asyncio.run(check_api_endpoints())
    for endpoint, result in results.items():
        status = "✓" if result['healthy'] else "✗"
        print(f"{status} {endpoint}: {result}")
```

## Common Issues

### Issue 1: Application Not Starting

**Symptoms:**
- Pods in CrashLoopBackOff state
- Application logs show startup errors
- Health checks failing

**Diagnosis:**
```bash
# Check pod status and events
kubectl describe pod <pod-name> -n regulensai

# Check application logs
kubectl logs <pod-name> -n regulensai --previous

# Check configuration
kubectl get configmap -n regulensai
kubectl get secret -n regulensai
```

**Resolution Steps:**
1. Verify environment variables are set correctly
2. Check database connectivity
3. Validate configuration files
4. Ensure required secrets are present
5. Check resource limits and requests

**Example Fix:**
```bash
# Update environment variables
kubectl patch deployment regulensai-api -n regulensai -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "api",
            "env": [
              {
                "name": "DATABASE_URL",
                "value": "postgresql://user:pass@host:5432/db"
              }
            ]
          }
        ]
      }
    }
  }
}'
```

### Issue 2: High Memory Usage

**Symptoms:**
- Pods being OOMKilled
- High memory usage alerts
- Slow application performance

**Diagnosis:**
```bash
# Check resource usage
kubectl top pods -n regulensai

# Check memory limits
kubectl describe pod <pod-name> -n regulensai | grep -A 5 "Limits:"

# Monitor memory usage over time
kubectl exec -it <pod-name> -n regulensai -- top
```

**Resolution Steps:**
1. Identify memory-intensive processes
2. Check for memory leaks in application logs
3. Increase memory limits if necessary
4. Optimize application code
5. Implement memory monitoring

### Issue 3: Database Connection Issues

**Symptoms:**
- Database connection timeouts
- "Too many connections" errors
- Slow query performance

**Diagnosis:**
```bash
# Check database connections
psql -h <db-host> -U <username> -d <database> -c "
SELECT count(*) as active_connections, 
       state, 
       application_name 
FROM pg_stat_activity 
WHERE state IS NOT NULL 
GROUP BY state, application_name;
"

# Check connection pool status
kubectl logs <pod-name> -n regulensai | grep -i "connection"
```

**Resolution Steps:**
1. Check connection pool configuration
2. Verify database server capacity
3. Optimize long-running queries
4. Implement connection retry logic
5. Monitor connection usage patterns

## External Integration Issues

### Refinitiv API Issues

**Common Problems:**
- Authentication failures
- Rate limiting
- Data format changes
- Service outages

**Troubleshooting Steps:**
```bash
# Test Refinitiv authentication
curl -X POST https://api.refinitiv.com/auth/oauth2/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=$REFINITIV_USERNAME&password=$REFINITIV_PASSWORD" \
  -H "Authorization: Bearer $REFINITIV_API_KEY"

# Check rate limit status
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     https://api.refinitiv.com/data/pricing/snapshots/v1/ \
     -I | grep -i "x-rate-limit"
```

**Resolution:**
1. Verify credentials are current
2. Implement exponential backoff for rate limits
3. Check Refinitiv service status
4. Update API endpoints if changed

### OFAC Data Issues

**Common Problems:**
- Data download failures
- XML parsing errors
- Stale data warnings

**Troubleshooting Steps:**
```bash
# Test OFAC data download
curl -I https://www.treasury.gov/ofac/downloads/sdn.xml

# Check data freshness
python3 -c "
import requests
from datetime import datetime
response = requests.head('https://www.treasury.gov/ofac/downloads/sdn.xml')
last_modified = response.headers.get('Last-Modified')
print(f'OFAC data last modified: {last_modified}')
"
```

**Resolution:**
1. Verify OFAC URLs are current
2. Check XML parsing logic
3. Implement data validation
4. Set up automated data freshness checks

## Performance Issues

### Slow API Response Times

**Diagnosis:**
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s https://api.regulensai.com/v1/external-data/screen-entity

# Monitor application metrics
kubectl port-forward service/prometheus 9090:9090 -n monitoring
# Access Prometheus at http://localhost:9090
```

**Resolution Steps:**
1. Identify slow endpoints using APM tools
2. Optimize database queries
3. Implement caching strategies
4. Scale horizontally if needed
5. Review and optimize algorithms

### Database Performance Issues

**Diagnosis:**
```sql
-- Check slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'your_table_name';
```

**Resolution:**
1. Add missing indexes
2. Optimize query plans
3. Update table statistics
4. Consider query rewriting
5. Implement query caching

## Notification System Issues

### Email Delivery Failures

**Symptoms:**
- High bounce rates
- Delivery delays
- SMTP errors

**Diagnosis:**
```bash
# Check notification logs
kubectl logs deployment/regulensai-notifications -n regulensai | grep -i "email"

# Test SMTP connectivity
telnet smtp.provider.com 587
```

**Resolution:**
1. Verify SMTP configuration
2. Check email provider status
3. Review bounce handling
4. Implement retry mechanisms
5. Monitor delivery rates

### Webhook Delivery Issues

**Symptoms:**
- Webhook timeouts
- HTTP errors from endpoints
- Missing webhook deliveries

**Diagnosis:**
```bash
# Check webhook logs
kubectl logs deployment/regulensai-notifications -n regulensai | grep -i "webhook"

# Test webhook endpoint
curl -X POST https://customer-webhook-url.com/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": "message"}'
```

**Resolution:**
1. Verify webhook endpoint availability
2. Check authentication requirements
3. Implement retry logic with exponential backoff
4. Monitor webhook response times
5. Provide webhook debugging tools

## Security Incidents

### Suspected Breach

**Immediate Actions:**
1. **Isolate affected systems**
   ```bash
   # Scale down affected deployments
   kubectl scale deployment <deployment-name> --replicas=0 -n regulensai
   
   # Block suspicious IP addresses
   kubectl apply -f network-policy-block.yaml
   ```

2. **Preserve evidence**
   ```bash
   # Capture logs
   kubectl logs deployment/regulensai-api -n regulensai > incident-logs-$(date +%Y%m%d-%H%M%S).log
   
   # Export pod descriptions
   kubectl describe pods -n regulensai > incident-pods-$(date +%Y%m%d-%H%M%S).txt
   ```

3. **Notify security team**
   - Email: security@regulensai.com
   - Phone: +1-XXX-XXX-XXXX (24/7 hotline)

### Authentication Issues

**Symptoms:**
- Unusual login patterns
- Failed authentication attempts
- Token validation errors

**Investigation:**
```bash
# Check authentication logs
kubectl logs deployment/regulensai-auth -n regulensai | grep -i "failed\|error\|suspicious"

# Review access patterns
grep "authentication" /var/log/regulensai/access.log | tail -100
```

**Response:**
1. Review authentication logs
2. Check for brute force attacks
3. Verify token integrity
4. Implement additional security measures
5. Consider temporary access restrictions

## Escalation Procedures

### Severity Levels

**Severity 1 (Critical)**
- Complete system outage
- Data breach or security incident
- Compliance violation

**Response Time:** 15 minutes
**Escalation:** Immediate notification to on-call engineer and management

**Severity 2 (High)**
- Partial system outage
- Performance degradation affecting multiple tenants
- External integration failures

**Response Time:** 1 hour
**Escalation:** Notification to on-call engineer

**Severity 3 (Medium)**
- Single tenant issues
- Non-critical feature failures
- Performance issues affecting single components

**Response Time:** 4 hours
**Escalation:** Standard support queue

**Severity 4 (Low)**
- Minor bugs
- Documentation issues
- Enhancement requests

**Response Time:** 24 hours
**Escalation:** Standard support queue

### Escalation Contacts

1. **Level 1**: On-call Engineer
   - Phone: +1-XXX-XXX-XXXX
   - Email: oncall@regulensai.com

2. **Level 2**: Platform Team Lead
   - Phone: +1-XXX-XXX-XXXX
   - Email: platform-lead@regulensai.com

3. **Level 3**: Engineering Manager
   - Phone: +1-XXX-XXX-XXXX
   - Email: engineering-manager@regulensai.com

4. **Level 4**: CTO
   - Phone: +1-XXX-XXX-XXXX
   - Email: cto@regulensai.com

### Incident Communication

**Internal Communication:**
- Slack: #incidents channel
- Email: incidents@regulensai.com
- Phone: Conference bridge +1-XXX-XXX-XXXX

**External Communication:**
- Status page: https://status.regulensai.com
- Customer notifications: Via email and in-app notifications
- Social media: @RegulensAI (for major outages)

### Post-Incident Review

After resolving any Severity 1 or 2 incident:

1. **Conduct post-mortem within 48 hours**
2. **Document root cause analysis**
3. **Identify preventive measures**
4. **Update runbooks and procedures**
5. **Implement monitoring improvements**

### Tools and Resources

- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **APM**: Jaeger for distributed tracing
- **Incident Management**: PagerDuty
- **Communication**: Slack, Microsoft Teams
- **Documentation**: Confluence, GitHub Wiki

For additional support or questions about this runbook, contact the Platform Team at platform@regulensai.com.

## Quick Reference Commands

### Essential Kubernetes Commands
```bash
# Get all resources in namespace
kubectl get all -n regulensai

# Check pod logs
kubectl logs -f <pod-name> -n regulensai

# Execute command in pod
kubectl exec -it <pod-name> -n regulensai -- /bin/bash

# Port forward for debugging
kubectl port-forward <pod-name> 8080:8080 -n regulensai

# Scale deployment
kubectl scale deployment <deployment-name> --replicas=3 -n regulensai

# Restart deployment
kubectl rollout restart deployment/<deployment-name> -n regulensai
```

### Database Troubleshooting
```bash
# Connect to database
psql -h <host> -U <user> -d <database>

# Check active connections
SELECT count(*) FROM pg_stat_activity;

# Check database size
SELECT pg_size_pretty(pg_database_size('regulensai'));

# Kill long-running queries
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';
```

### Log Analysis
```bash
# Search for errors in logs
kubectl logs deployment/regulensai-api -n regulensai | grep -i error | tail -20

# Follow logs with timestamp
kubectl logs -f deployment/regulensai-api -n regulensai --timestamps

# Get logs from specific time range
kubectl logs deployment/regulensai-api -n regulensai --since=1h

# Export logs to file
kubectl logs deployment/regulensai-api -n regulensai > api-logs-$(date +%Y%m%d).log
```
