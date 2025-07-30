# Enhanced RegulensAI One-Click Installer

## Overview

The enhanced `oneclickinstall.sh` script has been updated to integrate with our comprehensive RegulensAI implementation, including all enhanced features: centralized logging, APM monitoring, disaster recovery, enhanced documentation, and configuration management.

## 🚀 **What's New in the Enhanced Installer**

### **1. Consolidated Service Startup Integration**
- **Integrated Startup Script**: Uses `scripts/start_all_services.sh` for comprehensive service orchestration
- **Fallback Support**: Maintains backward compatibility with basic startup if consolidated script unavailable
- **Enhanced Service Coverage**: Includes ELK stack, APM monitoring, and background services

### **2. Enhanced Database Setup**
- **Consolidated Schema Support**: Recognizes and validates the enhanced database schema
- **Multi-Database Support**: Works with Supabase, PostgreSQL, and other database providers
- **Schema Validation**: Provides detailed information about included tables and features

### **3. Expanded Port Management**
- **Additional Services**: Added ports for Elasticsearch (9200), Kibana (5601), Logstash (5044)
- **Smart Conflict Resolution**: Automatically resolves port conflicts for all services
- **Enhanced Monitoring**: Supports full monitoring stack port allocation

### **4. Comprehensive Installation Summary**
- **Enhanced Feature Overview**: Highlights all new capabilities
- **Detailed Access URLs**: Provides access to all monitoring and management interfaces
- **Operational Guidance**: Includes management commands for enhanced features

## 📋 **Installation Process**

### **Prerequisites**
The installer automatically checks for:
- Docker and Docker Compose
- Python 3 for management scripts
- Sufficient disk space (10GB minimum)
- Available memory (4GB minimum)
- Required directories and files

### **Installation Steps**

1. **Prerequisites Check** - Validates system requirements
2. **Port Conflict Resolution** - Automatically resolves port conflicts
3. **Environment Setup** - Configures environment variables
4. **Docker Environment** - Sets up Docker network and volumes
5. **Enhanced Database Setup** - Validates database configuration and schema
6. **Complete Service Startup** - Uses consolidated startup script
7. **Post-Installation Setup** - Configures additional features
8. **Installation Summary** - Provides comprehensive access information

### **Usage**

```bash
# Run the enhanced one-click installer
./oneclickinstall.sh

# The installer will:
# 1. Check all prerequisites
# 2. Resolve any port conflicts
# 3. Set up the environment
# 4. Initialize the enhanced database schema
# 5. Start all services using the consolidated script
# 6. Provide comprehensive access information
```

## 🌐 **Access Points After Installation**

### **Core Platform**
- **RegulensAI Web UI**: http://localhost:3000
- **Main API**: http://localhost:8000
- **Health Check**: http://localhost:8000/v1/health

### **Enhanced Documentation**
- **Integrated Documentation Portal**: http://localhost:3000/documentation
  - Enhanced API documentation with OAuth2/SAML examples
  - Cloud deployment guides (AWS/GCP/Azure)
  - Configuration management and compliance scanning
  - Interactive API testing and validation

- **Standalone Documentation Portal**: http://localhost:8501
- **Testing Portal**: http://localhost:8502

### **Monitoring & Observability**
- **Centralized Logging (Kibana)**: http://localhost:5601
  - ELK stack with log aggregation and analysis
  - Real-time log monitoring and alerting
  - Log retention and archival management

- **APM Monitoring (Grafana)**: http://localhost:3001
  - Application performance monitoring
  - Distributed tracing and error tracking
  - Performance baselines and regression detection

- **Distributed Tracing (Jaeger)**: http://localhost:16686
- **Metrics Collection (Prometheus)**: http://localhost:9090

### **API Documentation**
- **Interactive Swagger UI**: http://localhost:8000/docs
- **Clean ReDoc Interface**: http://localhost:8000/redoc

## 🛠 **Enhanced Management Commands**

### **Service Management**
```bash
# Start all services (comprehensive)
./scripts/start_all_services.sh

# Stop all services
./scripts/start_all_services.sh --stop

# Check service status
./scripts/start_all_services.sh --status

# View help
./scripts/start_all_services.sh --help
```

### **Operational Management**
```bash
# Disaster Recovery management
python3 -m scripts.dr_manager status
python3 -m scripts.dr_manager full-test --dry-run

# Backup management
python3 -m scripts.backup_manager status
python3 -m scripts.backup_manager create

# Centralized logging management
python3 -m scripts.logging_manager status
python3 -m scripts.logging_manager tail
```

### **Docker Management**
```bash
# View all service logs
docker-compose logs -f

# Restart specific service
docker-compose restart [service-name]

# View service status
docker-compose ps

# Update platform
git pull && docker-compose up --build -d
```

## 🔧 **Configuration**

### **Environment Variables**
The installer creates and manages these key environment variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Service Ports (auto-assigned if conflicts detected)
API_PORT=8000
UI_PORT=3000
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
GRAFANA_PORT=3001
PROMETHEUS_PORT=9090

# Security
JWT_SECRET_KEY=your-jwt-secret
REDIS_PASSWORD=your-redis-password

# AI Features
OPENAI_API_KEY=your-openai-key
CLAUDE_API_KEY=your-claude-key
```

### **Important Files**
- **Configuration**: `.env`
- **Installation Log**: `install.log`
- **Consolidated Startup Script**: `scripts/start_all_services.sh`
- **Enhanced Database Schema**: `core_infra/database/schema.sql`
- **Docker Compose**: `docker-compose.yml`
- **UI Services**: `core_infra/ui/docker-compose.ui.yml`

## 🚨 **Troubleshooting**

### **Installation Issues**
```bash
# Check installation log
tail -f install.log

# Verify Docker status
docker info

# Check service status
docker-compose ps

# View service logs
docker-compose logs [service-name]
```

### **Port Conflicts**
The installer automatically resolves port conflicts, but you can manually check:
```bash
# Check which process is using a port
lsof -i :PORT

# View assigned ports in .env
grep "_PORT=" .env
```

### **Service Health Issues**
```bash
# Check API health
curl http://localhost:8000/v1/health

# Check database connectivity
python3 -c "from core_infra.config import DatabaseConfig; import asyncio; asyncio.run(DatabaseConfig.validate_schema())"

# Check consolidated startup logs
tail -f logs/startup.log
```

### **Memory/Resource Issues**
```bash
# Check available memory
free -h

# Check disk space
df -h

# Check Docker resource usage
docker stats
```

## 🔒 **Security Considerations**

### **Production Deployment**
Before deploying to production:

1. **Change Default Secrets**:
   ```bash
   # Update in .env file
   JWT_SECRET_KEY=your-production-jwt-secret
   REDIS_PASSWORD=your-production-redis-password
   ```

2. **Configure SSL/TLS**:
   - Set up reverse proxy (nginx/Apache)
   - Configure SSL certificates
   - Update service URLs to use HTTPS

3. **Set Up Firewall Rules**:
   - Restrict access to internal ports
   - Allow only necessary external access
   - Configure VPN access for management interfaces

4. **Enable Enhanced Security Features**:
   ```bash
   # Configure automated backups
   python3 -m scripts.backup_manager configure

   # Set up disaster recovery testing
   python3 -m scripts.dr_manager configure

   # Configure compliance scanning
   # Access via web UI at /documentation
   ```

## 📈 **Performance Optimization**

### **Resource Allocation**
- **Minimum Requirements**: 4GB RAM, 10GB disk space
- **Recommended**: 8GB RAM, 50GB disk space for production
- **Elasticsearch**: Requires significant memory for log indexing
- **Database**: Consider connection pooling for high load

### **Monitoring Setup**
1. **Configure Grafana Dashboards**: http://localhost:3001
2. **Set Up Kibana Visualizations**: http://localhost:5601
3. **Configure Prometheus Alerts**: http://localhost:9090
4. **Review APM Metrics**: Integrated in Grafana

## 🎯 **Next Steps After Installation**

1. **Access RegulensAI Web UI**: http://localhost:3000
2. **Explore Enhanced Documentation**: http://localhost:3000/documentation
3. **Configure Monitoring Dashboards**: http://localhost:3001
4. **Set Up Log Analysis**: http://localhost:5601
5. **Test API Endpoints**: http://localhost:8000/docs
6. **Configure Database Credentials**: Update `.env` file
7. **Set Up AI API Keys**: Add OpenAI/Claude keys to `.env`
8. **Run Disaster Recovery Test**: `python3 -m scripts.dr_manager full-test --dry-run`
9. **Configure Compliance Scanning**: Access via web UI
10. **Set Up Automated Backups**: `python3 -m scripts.backup_manager configure`

## 🎉 **Success Indicators**

After successful installation, you should see:

- ✅ All services running in `docker-compose ps`
- ✅ API health check passing at http://localhost:8000/v1/health
- ✅ Web UI accessible at http://localhost:3000
- ✅ Kibana accessible at http://localhost:5601
- ✅ Grafana accessible at http://localhost:3001
- ✅ Documentation portal accessible at http://localhost:3000/documentation
- ✅ All enhanced features available and functional

**The RegulensAI platform is now ready for enterprise use with complete operational excellence! 🚀**
