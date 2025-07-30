# RegulensAI Integrated Operations Center

## 🚀 Overview

The RegulensAI Operations Center provides a comprehensive web-based interface for deployment, monitoring, and system operations. This integrated approach ensures that operational procedures are always up-to-date, accessible, and properly version-controlled alongside the application code.

**🎯 Key Benefits:**
- **Always up-to-date** - Documentation is version-controlled with the application
- **Interactive workflows** - Step-by-step guides with real-time validation
- **Integrated monitoring** - Real-time system status and health checks
- **Role-based access** - Secure operations with proper permissions
- **Searchable troubleshooting** - Quick problem resolution with executable solutions

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security Configuration](#security-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD
- Network: 1Gbps

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 32GB+
- Storage: 500GB+ SSD with backup
- Network: 10Gbps
- Load balancer with SSL termination

### Software Dependencies

- Docker 24.0+
- Docker Compose 2.0+
- PostgreSQL 15+ (or Supabase)
- Redis 7.0+
- Python 3.11+
- Node.js 18+ (for UI components)

### External Services

- **Database**: Supabase or PostgreSQL cluster
- **Cache**: Redis cluster or managed Redis
- **Storage**: S3-compatible object storage
- **Email**: SMTP service (SendGrid, AWS SES, etc.)
- **Monitoring**: Grafana, Prometheus (optional)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/regulens-ai.git
cd regulens-ai
```

### 2. Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

**Critical Environment Variables:**

```bash
# Application
APP_ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# Security - GENERATE SECURE VALUES
JWT_SECRET_KEY=your-jwt-secret-key-change-this-to-secure-random-string
ENCRYPTION_KEY=your-encryption-key-change-this-to-secure-random-string

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-secure-redis-password

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=noreply@your-domain.com

# AI Services
OPENAI_API_KEY=your-openai-api-key
CLAUDE_API_KEY=your-claude-api-key

# Monitoring
GRAFANA_ADMIN_PASSWORD=your-secure-grafana-password
```

### 3. Generate Secure Keys

```bash
# Generate JWT secret (32+ characters)
openssl rand -base64 32

# Generate encryption key (32+ characters)
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 24
```

## Docker Deployment

### 1. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - APP_ENVIRONMENT=production
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
```

### 2. Production Dockerfile

Create `Dockerfile.prod`:

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENVIRONMENT=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "core_infra.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3. Deploy with Docker

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f app
```

## Kubernetes Deployment

### 1. Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: regulens-ai

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: regulens-config
  namespace: regulens-ai
data:
  APP_ENVIRONMENT: "production"
  DEBUG: "false"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
```

### 2. Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: regulens-secrets
  namespace: regulens-ai
type: Opaque
stringData:
  JWT_SECRET_KEY: "your-jwt-secret-key"
  ENCRYPTION_KEY: "your-encryption-key"
  DATABASE_URL: "postgresql://user:pass@host:5432/db"
  REDIS_PASSWORD: "your-redis-password"
  OPENAI_API_KEY: "your-openai-api-key"
```

### 3. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: regulens-ai
  namespace: regulens-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: regulens-ai
  template:
    metadata:
      labels:
        app: regulens-ai
    spec:
      containers:
      - name: regulens-ai
        image: regulens-ai:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: regulens-config
        - secretRef:
            name: regulens-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 4. Service and Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: regulens-ai-service
  namespace: regulens-ai
spec:
  selector:
    app: regulens-ai
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: regulens-ai-ingress
  namespace: regulens-ai
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.regulens.ai
    secretName: regulens-ai-tls
  rules:
  - host: api.regulens.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: regulens-ai-service
            port:
              number: 80
```

### 5. Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n regulens-ai
kubectl get services -n regulens-ai
kubectl get ingress -n regulens-ai
```

## Cloud Deployment

### AWS ECS Deployment

1. **Create ECS Cluster**
2. **Setup RDS for PostgreSQL**
3. **Setup ElastiCache for Redis**
4. **Configure Application Load Balancer**
5. **Deploy using ECS Service**

### Google Cloud Run Deployment

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/regulens-ai

# Deploy to Cloud Run
gcloud run deploy regulens-ai \
  --image gcr.io/PROJECT_ID/regulens-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10
```

### Azure Container Instances

```bash
# Create resource group
az group create --name regulens-ai --location eastus

# Deploy container
az container create \
  --resource-group regulens-ai \
  --name regulens-ai \
  --image regulens-ai:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables APP_ENVIRONMENT=production
```

## Security Configuration

### 1. SSL/TLS Setup

```nginx
# nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name api.regulens.ai;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Firewall Configuration

```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### 3. Database Security

- Enable SSL connections
- Use strong passwords
- Implement connection pooling
- Regular security updates
- Network isolation

## Monitoring Setup

### 1. Health Checks

The application provides comprehensive health checks:

```bash
# Application health
curl https://api.regulens.ai/health

# Database health
curl https://api.regulens.ai/health/database

# Cache health
curl https://api.regulens.ai/health/cache
```

### 2. Metrics Collection

Configure Prometheus metrics collection:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'regulens-ai'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
```

### 3. Log Management

Configure structured logging:

```bash
# View application logs
docker-compose logs -f app

# Search logs
docker-compose logs app | grep ERROR
```

## Backup and Recovery

### 1. Database Backup

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="regulens_backup_${DATE}.sql"

pg_dump $DATABASE_URL > ${BACKUP_DIR}/${BACKUP_FILE}
gzip ${BACKUP_DIR}/${BACKUP_FILE}

# Upload to S3
aws s3 cp ${BACKUP_DIR}/${BACKUP_FILE}.gz s3://your-backup-bucket/
```

### 2. Application Data Backup

```bash
# Backup uploaded files
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/

# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

### 3. Recovery Procedures

```bash
# Database recovery
gunzip -c backup_file.sql.gz | psql $DATABASE_URL

# Application recovery
docker-compose down
docker-compose pull
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Application won't start**
   - Check environment variables
   - Verify database connectivity
   - Check logs for errors

2. **Database connection errors**
   - Verify DATABASE_URL
   - Check network connectivity
   - Ensure database is running

3. **High memory usage**
   - Monitor application metrics
   - Check for memory leaks
   - Adjust container limits

4. **Performance issues**
   - Enable caching
   - Optimize database queries
   - Scale horizontally

### Log Analysis

```bash
# Check application logs
docker-compose logs app | tail -100

# Check error logs
docker-compose logs app | grep ERROR

# Monitor real-time logs
docker-compose logs -f app
```

### Performance Monitoring

```bash
# Check resource usage
docker stats

# Monitor database performance
docker-compose exec db psql -c "SELECT * FROM pg_stat_activity;"

# Check cache performance
docker-compose exec redis redis-cli info stats
```

## Support

For deployment support:
- **Documentation**: [https://docs.regulens.ai/deployment](https://docs.regulens.ai/deployment)
- **Support Email**: support@regulens.ai
- **Emergency Support**: +1-800-REGULENS

## Security Contacts

For security issues:
- **Security Email**: security@regulens.ai
- **PGP Key**: Available at [https://regulens.ai/.well-known/pgp-key.txt](https://regulens.ai/.well-known/pgp-key.txt)
