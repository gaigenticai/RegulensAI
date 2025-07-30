# RegulensAI Consolidated System Files

## Overview

This document describes the two critical consolidated files that ensure system integrity for the complete RegulensAI implementation, including all enhanced features (centralized logging, APM, disaster recovery, enhanced documentation, and configuration management).

## 📊 Database Schema File

**File**: `core_infra/database/schema.sql`

### Purpose
Unified database schema containing ALL tables, indexes, constraints, and initial data required for the complete RegulensAI ecosystem.

### Enhanced Tables Added

#### **Centralized Logging System Tables**
- `centralized_logs` - Main log aggregation table with structured logging
- `log_aggregation_rules` - Pattern matching and alerting rules
- `log_retention_policies` - Retention and archival policies by category

#### **Application Performance Monitoring (APM) Tables**
- `apm_transactions` - Transaction tracking with timing and metadata
- `apm_spans` - Distributed tracing spans for detailed analysis
- `apm_errors` - Error tracking with fingerprinting and aggregation
- `apm_metrics` - Custom metrics for business and technical KPIs
- `apm_performance_baselines` - Performance baselines for regression detection

#### **Disaster Recovery System Tables**
- `dr_objectives` - RTO/RPO objectives by component
- `dr_test_results` - Test execution results and validation
- `dr_events` - DR events, incidents, and status tracking
- `dr_backup_metadata` - Backup metadata and integrity tracking

#### **Configuration Management Tables**
- `configuration_versions` - Configuration version control and change tracking
- `configuration_drift` - Configuration drift detection and monitoring
- `configuration_compliance_scans` - Compliance scanning results

### Key Features
- **Comprehensive Indexing**: Optimized indexes for all query patterns
- **Foreign Key Constraints**: Proper referential integrity
- **Check Constraints**: Data validation at database level
- **Comments**: Detailed table and column documentation
- **Tenant Isolation**: Multi-tenant support across all tables

### Usage
```bash
# Apply schema to database
psql -d regulensai -f core_infra/database/schema.sql

# Or use the migration system
python3 -m core_infra.database.migrate
```

## 🚀 Service Startup Script

**File**: `scripts/start_all_services.sh`

### Purpose
Unified startup script that brings up the entire RegulensAI ecosystem in the correct order with proper dependency management and health checks.

### Service Startup Order

1. **Prerequisites Check**
   - Docker and Docker Compose availability
   - Required directories and files
   - System resources (disk space, memory)
   - Environment configuration

2. **Database Initialization**
   - Database connectivity verification
   - Schema migrations
   - Schema validation

3. **Infrastructure Services**
   - Redis (caching and sessions)
   - Qdrant (vector database)

4. **ELK Stack (Centralized Logging)**
   - Elasticsearch (log storage and search)
   - Logstash (log processing)
   - Kibana (log visualization)
   - Filebeat (log shipping)

5. **Monitoring Services (APM)**
   - Jaeger (distributed tracing)
   - Prometheus (metrics collection)
   - Grafana (monitoring dashboards)

6. **Application Services**
   - RegulensAI API (core application)
   - Compliance Engine
   - Notification Service
   - Regulatory Monitoring Service

7. **UI Services**
   - RegulensAI Web UI
   - Additional UI portals (if available)

8. **Background Services**
   - Disaster Recovery monitoring
   - Centralized Logging manager
   - Backup manager

### Key Features

#### **Dependency Management**
- Services start in correct order based on dependencies
- Health checks before proceeding to next service
- Configurable timeouts and retry logic

#### **Health Verification**
- Port connectivity checks
- HTTP endpoint health checks
- Database connectivity validation
- Service-specific health endpoints

#### **Error Handling**
- Comprehensive error logging
- Rollback capabilities on failure
- Service status tracking
- Failed service identification

#### **Integration Testing**
- API connectivity tests
- Database connectivity through API
- Redis connectivity through API
- Centralized logging system test
- APM system test

### Usage

#### **Start All Services**
```bash
# Start complete RegulensAI ecosystem
./scripts/start_all_services.sh

# View help
./scripts/start_all_services.sh --help
```

#### **Check Service Status**
```bash
# Check status without starting
./scripts/start_all_services.sh --status
```

#### **Stop All Services**
```bash
# Stop all services
./scripts/start_all_services.sh --stop
```

### Environment Variables

The script respects these environment variables:
- `STARTUP_TIMEOUT` - Service startup timeout (default: 300s)
- `HEALTH_CHECK_TIMEOUT` - Health check timeout (default: 60s)
- `COMPOSE_CMD` - Docker compose command (auto-detected)

### Service Ports

Default ports used by services:
- **Database**: 5432 (PostgreSQL)
- **Redis**: 6379
- **Elasticsearch**: 9200
- **Kibana**: 5601
- **RegulensAI API**: 8000
- **RegulensAI UI**: 3000
- **Prometheus**: 9090
- **Grafana**: 3001
- **Jaeger**: 16686

## 🔧 System Integration

### **Database Schema Integration**
The consolidated schema ensures:
- All enhanced features have proper database support
- Consistent data modeling across all components
- Optimized performance with proper indexing
- Multi-tenant support for enterprise deployments

### **Service Startup Integration**
The startup script ensures:
- All services start in correct dependency order
- Health checks verify system readiness
- Integration tests validate end-to-end functionality
- Comprehensive logging for troubleshooting

## 📋 Verification Checklist

### **Database Schema Verification**
- [ ] All core RegulensAI tables present
- [ ] Centralized logging tables created
- [ ] APM monitoring tables created
- [ ] Disaster recovery tables created
- [ ] Configuration management tables created
- [ ] All indexes created successfully
- [ ] Foreign key constraints applied
- [ ] Check constraints validated

### **Service Startup Verification**
- [ ] All infrastructure services start successfully
- [ ] ELK stack components are healthy
- [ ] Monitoring services are accessible
- [ ] Application services respond to health checks
- [ ] UI services are accessible
- [ ] Background services are running
- [ ] Integration tests pass
- [ ] All service URLs are accessible

## 🚨 Troubleshooting

### **Common Database Issues**
```bash
# Check database connectivity
psql -d regulensai -c "SELECT 1"

# Verify schema
python3 -c "from core_infra.config import DatabaseConfig; import asyncio; asyncio.run(DatabaseConfig.validate_schema())"

# Check table existence
psql -d regulensai -c "\dt"
```

### **Common Service Issues**
```bash
# Check Docker status
docker info

# View service logs
docker-compose logs -f [service-name]

# Check service health
curl http://localhost:8000/v1/health

# View startup logs
tail -f logs/startup.log
```

### **Port Conflicts**
If services fail to start due to port conflicts:
1. Check which process is using the port: `lsof -i :PORT`
2. Stop the conflicting process or change the port in `.env`
3. Restart the services

### **Memory Issues**
If services fail due to memory constraints:
1. Check available memory: `free -h`
2. Increase Docker memory limits
3. Consider reducing the number of concurrent services

## 📈 Performance Considerations

### **Database Performance**
- All tables have optimized indexes for common query patterns
- Partitioning can be added for high-volume tables (logs, metrics)
- Connection pooling is configured in the application

### **Service Performance**
- Services start with health checks to ensure readiness
- Resource limits are configured in Docker Compose
- Monitoring is in place to track performance

## 🔒 Security Considerations

### **Database Security**
- All tables support tenant isolation
- Sensitive data is properly constrained
- Audit trails are maintained for configuration changes

### **Service Security**
- Services communicate over internal Docker network
- External access is limited to necessary ports
- Authentication is required for all API endpoints

## 📚 Related Documentation

- **API Documentation**: Available at `/documentation` in the web UI
- **Deployment Guides**: Cloud-specific guides in the documentation portal
- **Configuration Management**: Drift detection and compliance scanning
- **Disaster Recovery**: Comprehensive DR procedures and testing
- **Monitoring**: APM integration and centralized logging

## 🎯 Next Steps

After running the consolidated files:

1. **Access the RegulensAI UI** at http://localhost:3000
2. **Review API documentation** at http://localhost:8000/docs
3. **Configure monitoring dashboards** in Grafana
4. **Set up log analysis** in Kibana
5. **Run disaster recovery tests**: `python3 -m scripts.dr_manager full-test --dry-run`
6. **Configure compliance scanning** in the web UI
7. **Set up automated backups** and retention policies

The RegulensAI ecosystem is now fully operational with enterprise-grade capabilities! 🚀
