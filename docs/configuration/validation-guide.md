# RegulensAI Configuration Validation Guide

## 🎯 Overview

The RegulensAI Configuration Validation System provides comprehensive validation of all system configurations with detailed error messages, actionable suggestions, and environment-specific requirements. This ensures that deployments are secure, reliable, and properly configured.

## 🔧 Key Features

### ✅ Comprehensive Validation
- **Database connectivity and schema validation**
- **External service endpoint validation**
- **Security configuration verification**
- **Environment-specific requirement checks**
- **File system and storage validation**
- **AI/ML service configuration validation**

### 🎯 Environment-Specific Rules
- **Production**: Strict security and monitoring requirements
- **Staging**: Production-like validation with some flexibility
- **Development**: Flexible configuration with warnings for best practices

### 🌐 Web Interface Integration
- **Real-time validation** through Operations Center
- **Interactive error resolution** with copy-to-clipboard commands
- **Configuration summary** with detailed settings overview
- **Validation history** and status tracking

## 🚀 Quick Start

### Access Configuration Validation

Navigate to the Operations Center in the RegulensAI web interface:

```
https://your-regulens-instance.com/operations
```

Click on the **"Configuration"** tab to access validation features.

### API Endpoints

```bash
# Run comprehensive validation
GET /api/v1/operations/configuration/validate?include_summary=true

# Get configuration summary
GET /api/v1/operations/configuration/summary

# Reload configuration
POST /api/v1/operations/configuration/reload

# Validate specific environment
GET /api/v1/operations/configuration/environment/production/validate
```

## 📋 Validation Categories

### 1. Database Validation

**Checks Performed:**
- PostgreSQL connectivity and version (14+)
- Required tables from all phases (Phase 1, 2, 3)
- Essential indexes for performance
- Database extensions (uuid-ossp, pg_trgm, btree_gin)
- Connection pool configuration
- Schema compatibility

**Required Tables:**
```
Core Tables (Phase 1):
- tenants, users, customers, transactions
- compliance_programs, compliance_tasks
- regulatory_documents, audit_logs
- notifications, performance_metrics

Phase 2 Additions:
- scheduled_tasks, task_executions
- document_embeddings, document_similarity
- regulatory_changes, regulatory_impact_assessments
- workflow_executions, workflow_steps

Phase 3 Additions (Training Portal):
- training_modules, training_sections
- training_assessments, training_enrollments
- training_progress, training_certificates
- training_section_progress, training_assessment_attempts

Operations Tables:
- system_health_checks, backup_logs, file_uploads
```

**Example Validation:**
```python
# Database connectivity test
async def validate_database():
    conn = await asyncpg.connect(database_url)
    await conn.fetchval("SELECT 1")  # Basic connectivity
    
    # Schema validation
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    
    # Check required tables exist
    missing_tables = REQUIRED_TABLES - {row['table_name'] for row in tables}
    if missing_tables:
        raise ConfigurationError(f"Missing tables: {missing_tables}")
```

### 2. Security Validation

**JWT Configuration:**
- Secret key length (≥32 characters)
- Token expiration settings
- Algorithm security (HMAC vs RSA)

**Encryption Settings:**
- Encryption key format (44-character base64)
- Bcrypt rounds (≥10, ≥12 for production)
- Password complexity requirements

**CORS Configuration:**
- Origin restrictions (no wildcards in production)
- Allowed methods and headers
- Credential handling

**Example Configuration:**
```yaml
# Secure JWT configuration
JWT_SECRET_KEY: "your-32-character-or-longer-secret-key"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: 30  # ≤60 for production
JWT_ALGORITHM: "HS256"

# Encryption settings
ENCRYPTION_KEY: "base64-encoded-32-byte-key-here"
BCRYPT_ROUNDS: 12  # ≥12 for production

# CORS settings
CORS_ALLOWED_ORIGINS: "https://app.regulens.ai,https://admin.regulens.ai"
```

### 3. External Services Validation

**Supported Services:**
- **Redis**: Connection, authentication, performance settings
- **SMTP**: Email server connectivity and authentication
- **OpenAI API**: Key validation and endpoint accessibility
- **Claude API**: Anthropic service validation
- **Supabase**: Project URL and key validation

**Example Validation:**
```python
# Redis validation
async def validate_redis():
    r = redis.from_url(redis_url, password=password)
    r.ping()  # Test connectivity
    
# SMTP validation
def validate_smtp():
    server = smtplib.SMTP(host, port)
    server.starttls()
    if username and password:
        server.login(username, password)
    server.quit()

# API endpoint validation
def validate_api_endpoint(url, api_key):
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(url, headers=headers, timeout=10)
    return response.status_code == 200
```

### 4. Environment-Specific Validation

#### Production Environment

**Security Requirements:**
```python
# Production validation rules
if environment == 'production':
    assert not debug_mode, "Debug must be disabled"
    assert jwt_expire_minutes <= 60, "Token expiration too long"
    assert bcrypt_rounds >= 12, "Insufficient encryption strength"
    assert metrics_enabled, "Monitoring required"
    assert backup_enabled, "Backups required"
    assert not 'localhost' in database_url, "External database required"
```

#### Staging Environment

**Testing Requirements:**
```python
# Staging validation rules
if environment == 'staging':
    assert metrics_enabled, "Metrics needed for testing"
    assert backup_frequency_hours <= 24, "Regular backups required"
    # Allow some flexibility for testing
```

#### Development Environment

**Development Flexibility:**
```python
# Development warnings (not errors)
if environment == 'development':
    if database_pool_size > 10:
        logger.warning("Large pool size unnecessary in development")
    if not hot_reload_enabled:
        logger.info("Enable hot reload for better experience")
```

## 🔍 Error Handling and Resolution

### Structured Error Messages

All validation errors include:
- **Field name** causing the error
- **Detailed error message** explaining the issue
- **Actionable suggestions** for resolution
- **Example configurations** when applicable

**Example Error Response:**
```json
{
  "error": "Configuration validation failed",
  "field": "jwt_secret_key",
  "message": "JWT secret key must be at least 32 characters long for security",
  "suggestions": [
    "Generate a secure key: openssl rand -hex 32",
    "Use a password manager to generate a strong secret",
    "Ensure the key is stored securely in environment variables"
  ]
}
```

### Common Issues and Solutions

#### Database Connection Issues

**Problem:** `Database connection failed: connection refused`

**Solutions:**
```bash
# Check database server status
kubectl get pods -n database

# Test network connectivity
nc -zv database-host 5432

# Verify credentials
psql $DATABASE_URL -c "SELECT 1;"

# Check connection string format
export DATABASE_URL="postgresql://username:password@host:port/database"
```

#### Missing Database Schema

**Problem:** `Missing required tables: training_modules, training_sections`

**Solutions:**
```bash
# Check migration status
python core_infra/database/migrate.py --status

# Apply missing migrations
python core_infra/database/migrate.py

# Verify schema
psql $DATABASE_URL -c "\dt"
```

#### Security Configuration Issues

**Problem:** `JWT secret key too short`

**Solutions:**
```bash
# Generate secure JWT secret
openssl rand -hex 32

# Generate encryption key
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

# Set environment variables
export JWT_SECRET_KEY="your-generated-secret-key"
export ENCRYPTION_KEY="your-generated-encryption-key"
```

## 🔧 Configuration File Validation

### Supported Formats

**YAML Configuration:**
```yaml
# config.yaml
app_environment: production
debug: false
database_url: postgresql://user:pass@host:5432/db
jwt_secret_key: your-secret-key
```

**JSON Configuration:**
```json
{
  "app_environment": "production",
  "debug": false,
  "database_url": "postgresql://user:pass@host:5432/db",
  "jwt_secret_key": "your-secret-key"
}
```

**Environment Variables (.env):**
```bash
# .env file
APP_ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@host:5432/db
JWT_SECRET_KEY=your-secret-key
```

### File Validation API

```python
from core_infra.config import Settings

# Validate configuration file
valid, errors = Settings.validate_config_file('config.yaml')
if not valid:
    for error in errors:
        print(f"Error: {error}")
```

## 🌐 Web Interface Features

### Real-Time Validation

The Operations Center provides:
- **Live validation status** with color-coded indicators
- **Expandable error details** with specific error messages
- **Copy-to-clipboard commands** for quick resolution
- **Configuration summary** with all current settings

### Validation Dashboard

**Status Indicators:**
- 🟢 **Passed**: All validations successful
- 🟡 **Warning**: Non-critical issues found
- 🔴 **Failed**: Critical issues requiring attention

**Interactive Features:**
- **Refresh validation** on demand
- **Reload configuration** from environment
- **View detailed error messages** with suggestions
- **Export validation reports** for documentation

## 📊 Monitoring and Alerting

### Validation Metrics

The system tracks:
- **Validation success/failure rates**
- **Configuration drift detection**
- **Environment-specific compliance**
- **Security configuration status**

### Integration with Operations Center

- **Deployment workflow integration** - validation runs before deployments
- **Automated validation scheduling** - regular configuration checks
- **Alert integration** - notifications for configuration issues
- **Audit logging** - all validation activities logged

## 🔒 Security Considerations

### Sensitive Data Handling

- **Secrets masking** in logs and UI
- **Secure storage** of validation results
- **Access control** for configuration operations
- **Audit trails** for all configuration changes

### Compliance Features

- **SOC 2 compliance** validation
- **Security baseline** enforcement
- **Configuration drift** detection
- **Change management** integration

## 📞 Support and Troubleshooting

### Getting Help

- **Operations Center**: Built-in help and suggestions
- **API Documentation**: `/api/v1/docs` for detailed API reference
- **Support Team**: devops@regulens.ai for complex issues
- **Emergency**: Use rollback procedures for critical failures

### Best Practices

1. **Run validation before deployments**
2. **Monitor configuration drift regularly**
3. **Use environment-specific configurations**
4. **Keep secrets secure and rotated**
5. **Document configuration changes**
6. **Test validation in staging first**

---

**Last Updated**: January 29, 2024  
**Version**: 1.0.0  
**Maintainer**: DevOps Team <devops@regulens.ai>
