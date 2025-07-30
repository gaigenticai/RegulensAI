"""
RegulensAI - Enhanced Configuration Management
Enterprise-grade configuration with comprehensive validation and error handling.
"""

import os
import re
import json
import yaml
import asyncio
import asyncpg
import redis
from pathlib import Path
from functools import lru_cache
from typing import List, Optional, Dict, Any, Union, Tuple
from urllib.parse import urlparse
from pydantic import Field, SecretStr, field_validator, ValidationError, model_validator
from pydantic_settings import BaseSettings
import structlog
import requests
from datetime import datetime

logger = structlog.get_logger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration validation errors."""

    def __init__(self, message: str, field: str = None, suggestions: List[str] = None):
        self.field = field
        self.suggestions = suggestions or []
        super().__init__(message)


class DatabaseSchemaValidator:
    """Validates database schema compatibility and requirements."""

    REQUIRED_TABLES = {
        # Core tables from Phase 1
        'tenants', 'users', 'customers', 'transactions', 'compliance_programs',
        'compliance_tasks', 'regulatory_documents', 'audit_logs', 'notifications',
        'performance_metrics', 'system_configurations',

        # Phase 2 additions
        'scheduled_tasks', 'task_executions', 'document_embeddings',
        'document_similarity', 'regulatory_changes', 'regulatory_impact_assessments',
        'workflow_executions', 'workflow_steps',

        # Phase 3 additions (Training Portal)
        'training_modules', 'training_sections', 'training_assessments',
        'training_enrollments', 'training_progress', 'training_certificates',
        'training_section_progress', 'training_assessment_attempts',

        # Operations and monitoring tables
        'system_health_checks', 'backup_logs', 'file_uploads'
    }

    REQUIRED_INDEXES = {
        'idx_users_email', 'idx_users_tenant_id', 'idx_customers_tenant_id',
        'idx_transactions_customer_id', 'idx_compliance_tasks_status',
        'idx_audit_logs_tenant_id', 'idx_regulatory_documents_jurisdiction',
        'idx_training_enrollments_user_id', 'idx_training_progress_enrollment_id'
    }

    REQUIRED_CONSTRAINTS = {
        'chk_user_status', 'chk_transaction_status', 'chk_compliance_task_status',
        'chk_training_module_category', 'chk_training_module_difficulty'
    }

    @staticmethod
    async def validate_schema(database_url: str) -> Tuple[bool, List[str]]:
        """Validate database schema against requirements."""
        errors = []

        try:
            conn = await asyncpg.connect(database_url)

            try:
                # Check required tables
                existing_tables = await conn.fetch("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                existing_table_names = {row['table_name'] for row in existing_tables}

                missing_tables = DatabaseSchemaValidator.REQUIRED_TABLES - existing_table_names
                if missing_tables:
                    errors.append(f"Missing required tables: {', '.join(sorted(missing_tables))}")

                # Check required indexes
                existing_indexes = await conn.fetch("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public'
                """)
                existing_index_names = {row['indexname'] for row in existing_indexes}

                missing_indexes = DatabaseSchemaValidator.REQUIRED_INDEXES - existing_index_names
                if missing_indexes:
                    errors.append(f"Missing required indexes: {', '.join(sorted(missing_indexes))}")

                # Check database extensions
                extensions = await conn.fetch("SELECT extname FROM pg_extension")
                extension_names = {row['extname'] for row in extensions}

                required_extensions = {'uuid-ossp', 'pg_trgm', 'btree_gin'}
                missing_extensions = required_extensions - extension_names
                if missing_extensions:
                    errors.append(f"Missing required extensions: {', '.join(sorted(missing_extensions))}")

                # Check database version
                version_info = await conn.fetchval("SELECT version()")
                if not re.search(r'PostgreSQL (1[4-9]|[2-9]\d)', version_info):
                    errors.append("PostgreSQL version 14+ is required")

                return len(errors) == 0, errors

            finally:
                await conn.close()

        except Exception as e:
            errors.append(f"Database connection failed: {str(e)}")
            return False, errors


class ExternalServiceValidator:
    """Validates external service connectivity and credentials."""

    @staticmethod
    async def validate_redis_connection(redis_url: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """Validate Redis connection."""
        try:
            if password:
                # Parse URL and add password
                parsed = urlparse(redis_url)
                redis_url = f"redis://:{password}@{parsed.hostname}:{parsed.port}{parsed.path}"

            r = redis.from_url(redis_url, socket_timeout=5)
            r.ping()
            return True, "Redis connection successful"
        except Exception as e:
            return False, f"Redis connection failed: {str(e)}"

    @staticmethod
    def validate_smtp_config(host: str, port: int, username: str = None, password: str = None) -> Tuple[bool, str]:
        """Validate SMTP configuration."""
        try:
            import smtplib

            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()

            if username and password:
                server.login(username, password)

            server.quit()
            return True, "SMTP configuration valid"
        except Exception as e:
            return False, f"SMTP validation failed: {str(e)}"

    @staticmethod
    def validate_api_endpoint(url: str, api_key: str = None, timeout: int = 10) -> Tuple[bool, str]:
        """Validate external API endpoint."""
        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            response = requests.get(url, headers=headers, timeout=timeout)

            if response.status_code == 200:
                return True, "API endpoint accessible"
            elif response.status_code == 401:
                return False, "API authentication failed - check credentials"
            elif response.status_code == 403:
                return False, "API access forbidden - check permissions"
            else:
                return False, f"API returned status {response.status_code}"

        except requests.exceptions.Timeout:
            return False, "API endpoint timeout - check network connectivity"
        except requests.exceptions.ConnectionError:
            return False, "API endpoint unreachable - check URL and network"
        except Exception as e:
            return False, f"API validation failed: {str(e)}"


class Settings(BaseSettings):
    """
    Application configuration using Pydantic BaseSettings.
    All configuration can be overridden via environment variables.
    """
    
    # ============================================================================
    # APPLICATION CONFIGURATION
    # ============================================================================
    
    app_name: str = Field(default="Regulens AI Financial Compliance Platform", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_environment: str = Field(default="development", env="APP_ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    api_version: str = Field(default="v1", env="API_VERSION")
    api_port: int = Field(default=8000, env="API_PORT")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    
    # ============================================================================
    # SECURITY CONFIGURATION
    # ============================================================================
    
    jwt_secret_key: SecretStr = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    encryption_key: SecretStr = Field(env="ENCRYPTION_KEY")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    
    # Supabase Cloud Configuration
    supabase_url: str = Field(env="SUPABASE_URL")
    supabase_anon_key: SecretStr = Field(env="SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr = Field(env="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    
    # ============================================================================
    # REDIS CONFIGURATION
    # ============================================================================
    
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[SecretStr] = Field(default=None, env="REDIS_PASSWORD")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    cache_default_timeout: int = Field(default=300, env="CACHE_DEFAULT_TIMEOUT")
    
    # ============================================================================
    # STORAGE CONFIGURATION
    # ============================================================================
    
    storage_provider: str = Field(default="supabase", env="STORAGE_PROVIDER")
    supabase_storage_bucket: str = Field(default="compliance-documents", env="SUPABASE_STORAGE_BUCKET")
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")
    allowed_file_types: str = Field(default="pdf,docx,xlsx,csv,txt,json", env="ALLOWED_FILE_TYPES")
    
    # ============================================================================
    # AI/ML CONFIGURATION
    # ============================================================================
    
    openai_api_key: Optional[SecretStr] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=4000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    claude_api_key: Optional[SecretStr] = Field(default=None, env="CLAUDE_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # ============================================================================
    # LANGSMITH CONFIGURATION
    # ============================================================================
    
    langchain_tracing_v2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[SecretStr] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="regulens-ai-compliance", env="LANGCHAIN_PROJECT")
    
    # ============================================================================
    # REGULATORY DATA SOURCES
    # ============================================================================
    
    regulatory_monitor_enabled: bool = Field(default=True, env="REGULATORY_MONITOR_ENABLED")
    regulatory_monitor_interval_minutes: int = Field(default=60, env="REGULATORY_MONITOR_INTERVAL_MINUTES")
    sec_api_key: Optional[SecretStr] = Field(default=None, env="SEC_API_KEY")
    fca_api_key: Optional[SecretStr] = Field(default=None, env="FCA_API_KEY")
    ecb_api_key: Optional[SecretStr] = Field(default=None, env="ECB_API_KEY")
    fincen_api_key: Optional[SecretStr] = Field(default=None, env="FINCEN_API_KEY")
    
    # ============================================================================
    # AML/KYC CONFIGURATION
    # ============================================================================
    
    aml_monitoring_enabled: bool = Field(default=True, env="AML_MONITORING_ENABLED")
    aml_threshold_amount: float = Field(default=10000.0, env="AML_THRESHOLD_AMOUNT")
    aml_high_risk_countries: str = Field(default="IR,KP,SY,AF,MM", env="AML_HIGH_RISK_COUNTRIES")
    sanctions_list_update_interval_hours: int = Field(default=24, env="SANCTIONS_LIST_UPDATE_INTERVAL_HOURS")
    pep_screening_enabled: bool = Field(default=True, env="PEP_SCREENING_ENABLED")
    transaction_monitoring_real_time: bool = Field(default=True, env="TRANSACTION_MONITORING_REAL_TIME")
    
    # ============================================================================
    # COMPLIANCE WORKFLOW CONFIGURATION
    # ============================================================================
    
    task_assignment_auto: bool = Field(default=True, env="TASK_ASSIGNMENT_AUTO")
    escalation_enabled: bool = Field(default=True, env="ESCALATION_ENABLED")
    escalation_threshold_hours: int = Field(default=48, env="ESCALATION_THRESHOLD_HOURS")
    notification_email_enabled: bool = Field(default=True, env="NOTIFICATION_EMAIL_ENABLED")
    notification_sms_enabled: bool = Field(default=False, env="NOTIFICATION_SMS_ENABLED")
    compliance_review_cycle_days: int = Field(default=90, env="COMPLIANCE_REVIEW_CYCLE_DAYS")
    
    # ============================================================================
    # EMAIL CONFIGURATION
    # ============================================================================
    
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[SecretStr] = Field(default=None, env="SMTP_PASSWORD")
    email_from: str = Field(default="noreply@regulens-ai.com", env="EMAIL_FROM")
    email_from_name: str = Field(default="Regulens AI Compliance Platform", env="EMAIL_FROM_NAME")

    # ============================================================================
    # SMS CONFIGURATION (TWILIO)
    # ============================================================================

    twilio_account_sid: Optional[str] = Field(default=None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[SecretStr] = Field(default=None, env="TWILIO_AUTH_TOKEN")
    twilio_from_number: Optional[str] = Field(default=None, env="TWILIO_FROM_NUMBER")

    # ============================================================================
    # COLLABORATION PLATFORMS
    # ============================================================================

    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    teams_webhook_url: Optional[str] = Field(default=None, env="TEAMS_WEBHOOK_URL")
    discord_webhook_url: Optional[str] = Field(default=None, env="DISCORD_WEBHOOK_URL")
    
    # ============================================================================
    # OBSERVABILITY AND MONITORING
    # ============================================================================
    
    jaeger_enabled: bool = Field(default=True, env="JAEGER_ENABLED")
    jaeger_agent_host: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    jaeger_agent_port: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    jaeger_service_name: str = Field(default="regulens-ai-compliance", env="JAEGER_SERVICE_NAME")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # ============================================================================
    # QDRANT VECTOR DATABASE
    # ============================================================================
    
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[SecretStr] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(default="regulatory_documents", env="QDRANT_COLLECTION_NAME")
    vector_dimension: int = Field(default=1536, env="VECTOR_DIMENSION")
    
    # ============================================================================
    # FASTEMBED CONFIGURATION
    # ============================================================================
    
    fastembed_model: str = Field(default="BAAI/bge-small-en-v1.5", env="FASTEMBED_MODEL")
    fastembed_cache_dir: str = Field(default="./models_cache", env="FASTEMBED_CACHE_DIR")
    
    # ============================================================================
    # API RATE LIMITING
    # ============================================================================

    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")

    # ============================================================================
    # BACKUP CONFIGURATION
    # ============================================================================

    backup_enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    backup_s3_bucket: Optional[str] = Field(default=None, env="BACKUP_S3_BUCKET")
    backup_retention_days: int = Field(default=30, env="BACKUP_RETENTION_DAYS")
    backup_schedule: str = Field(default="0 2 * * *", env="BACKUP_SCHEDULE")  # Daily at 2 AM
    backup_compression_enabled: bool = Field(default=True, env="BACKUP_COMPRESSION_ENABLED")
    backup_notification_webhook: Optional[str] = Field(default=None, env="BACKUP_NOTIFICATION_WEBHOOK")
    staging_database_url: Optional[str] = Field(default=None, env="STAGING_DATABASE_URL")

    # ============================================================================
    # CENTRALIZED LOGGING CONFIGURATION
    # ============================================================================

    # Elasticsearch Configuration
    elasticsearch_enabled: bool = Field(default=False, env="ELASTICSEARCH_ENABLED")
    elasticsearch_host: str = Field(default="localhost", env="ELASTICSEARCH_HOST")
    elasticsearch_port: int = Field(default=9200, env="ELASTICSEARCH_PORT")
    elasticsearch_scheme: str = Field(default="http", env="ELASTICSEARCH_SCHEME")
    elasticsearch_username: Optional[str] = Field(default=None, env="ELASTICSEARCH_USERNAME")
    elasticsearch_password: Optional[SecretStr] = Field(default=None, env="ELASTICSEARCH_PASSWORD")
    elasticsearch_verify_certs: bool = Field(default=False, env="ELASTICSEARCH_VERIFY_CERTS")
    elasticsearch_timeout: int = Field(default=30, env="ELASTICSEARCH_TIMEOUT")

    # Log Shipping Configuration
    log_buffer_size: int = Field(default=1000, env="LOG_BUFFER_SIZE")
    log_flush_interval: int = Field(default=30, env="LOG_FLUSH_INTERVAL")
    log_retry_attempts: int = Field(default=3, env="LOG_RETRY_ATTEMPTS")
    log_retry_delay: int = Field(default=5, env="LOG_RETRY_DELAY")

    # File Logging Configuration
    file_logging_enabled: bool = Field(default=True, env="FILE_LOGGING_ENABLED")
    log_directory: str = Field(default="/var/log/regulensai", env="LOG_DIRECTORY")

    # External Logging Services
    siem_logging_enabled: bool = Field(default=False, env="SIEM_LOGGING_ENABLED")
    siem_endpoint: Optional[str] = Field(default=None, env="SIEM_ENDPOINT")
    siem_api_key: Optional[SecretStr] = Field(default=None, env="SIEM_API_KEY")

    # Log Webhooks (JSON array of webhook configurations)
    log_webhooks_config: Optional[str] = Field(default=None, env="LOG_WEBHOOKS_CONFIG")

    @property
    def log_webhooks(self) -> List[Dict[str, Any]]:
        """Parse log webhooks configuration from JSON."""
        if not self.log_webhooks_config:
            return []

        try:
            import json
            return json.loads(self.log_webhooks_config)
        except (json.JSONDecodeError, TypeError):
            return []

    # ============================================================================
    # APPLICATION PERFORMANCE MONITORING (APM) CONFIGURATION
    # ============================================================================

    # Elastic APM Configuration
    elastic_apm_enabled: bool = Field(default=False, env="ELASTIC_APM_ENABLED")
    elastic_apm_service_name: str = Field(default="regulensai", env="ELASTIC_APM_SERVICE_NAME")
    elastic_apm_server_url: str = Field(default="http://localhost:8200", env="ELASTIC_APM_SERVER_URL")
    elastic_apm_secret_token: Optional[SecretStr] = Field(default=None, env="ELASTIC_APM_SECRET_TOKEN")
    elastic_apm_sample_rate: float = Field(default=1.0, env="ELASTIC_APM_SAMPLE_RATE")

    # New Relic Configuration
    newrelic_enabled: bool = Field(default=False, env="NEWRELIC_ENABLED")
    newrelic_config_file: Optional[str] = Field(default=None, env="NEWRELIC_CONFIG_FILE")
    newrelic_license_key: Optional[SecretStr] = Field(default=None, env="NEWRELIC_LICENSE_KEY")

    # Datadog Configuration
    datadog_apm_enabled: bool = Field(default=False, env="DATADOG_APM_ENABLED")
    datadog_hostname: Optional[str] = Field(default=None, env="DATADOG_HOSTNAME")
    datadog_port: int = Field(default=8126, env="DATADOG_PORT")
    datadog_service_name: str = Field(default="regulensai", env="DATADOG_SERVICE_NAME")
    datadog_api_key: Optional[SecretStr] = Field(default=None, env="DATADOG_API_KEY")

    # Performance Monitoring Configuration
    performance_monitoring_enabled: bool = Field(default=True, env="PERFORMANCE_MONITORING_ENABLED")
    performance_baseline_update_interval: int = Field(default=3600, env="PERFORMANCE_BASELINE_UPDATE_INTERVAL")  # seconds
    performance_regression_threshold: float = Field(default=20.0, env="PERFORMANCE_REGRESSION_THRESHOLD")  # percentage

    # Database Performance Monitoring
    db_performance_monitoring_enabled: bool = Field(default=True, env="DB_PERFORMANCE_MONITORING_ENABLED")
    db_slow_query_threshold: float = Field(default=1.0, env="DB_SLOW_QUERY_THRESHOLD")  # seconds
    db_query_sampling_rate: float = Field(default=1.0, env="DB_QUERY_SAMPLING_RATE")

    # Error Tracking Configuration
    error_tracking_enabled: bool = Field(default=True, env="ERROR_TRACKING_ENABLED")
    error_rate_alert_threshold: float = Field(default=10.0, env="ERROR_RATE_ALERT_THRESHOLD")  # errors per minute
    error_aggregation_window: int = Field(default=300, env="ERROR_AGGREGATION_WINDOW")  # seconds

    # Resource Monitoring Configuration
    resource_monitoring_enabled: bool = Field(default=True, env="RESOURCE_MONITORING_ENABLED")
    resource_monitoring_interval: int = Field(default=30, env="RESOURCE_MONITORING_INTERVAL")  # seconds
    cpu_usage_alert_threshold: float = Field(default=80.0, env="CPU_USAGE_ALERT_THRESHOLD")  # percentage
    memory_usage_alert_threshold: float = Field(default=85.0, env="MEMORY_USAGE_ALERT_THRESHOLD")  # percentage

    # Business Metrics Configuration
    business_metrics_enabled: bool = Field(default=True, env="BUSINESS_METRICS_ENABLED")
    compliance_processing_time_threshold: float = Field(default=30.0, env="COMPLIANCE_PROCESSING_TIME_THRESHOLD")  # seconds
    regulatory_ingestion_rate_threshold: float = Field(default=100.0, env="REGULATORY_INGESTION_RATE_THRESHOLD")  # records/second
    
    # ============================================================================
    # COMPLIANCE SPECIFIC CONFIGURATION
    # ============================================================================
    
    regulatory_jurisdictions: str = Field(default="US,UK,EU,AU,SG,CA", env="REGULATORY_JURISDICTIONS")
    compliance_frameworks: str = Field(default="SOX,GDPR,PCI_DSS,AML,KYC,BASEL_III,MIFID_II", env="COMPLIANCE_FRAMEWORKS")
    risk_assessment_frequency_days: int = Field(default=30, env="RISK_ASSESSMENT_FREQUENCY_DAYS")
    audit_retention_years: int = Field(default=7, env="AUDIT_RETENTION_YEARS")
    document_retention_years: int = Field(default=10, env="DOCUMENT_RETENTION_YEARS")
    
    # ============================================================================
    # MULTI-TENANT CONFIGURATION
    # ============================================================================
    
    tenant_isolation_enabled: bool = Field(default=True, env="TENANT_ISOLATION_ENABLED")
    default_tenant_settings: str = Field(
        default='{"max_users":100,"max_customers":10000,"max_transactions_per_month":100000}',
        env="DEFAULT_TENANT_SETTINGS"
    )
    tenant_onboarding_auto_approve: bool = Field(default=False, env="TENANT_ONBOARDING_AUTO_APPROVE")
    
    # ============================================================================
    # BACKUP AND DISASTER RECOVERY
    # ============================================================================
    
    backup_enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    backup_frequency_hours: int = Field(default=6, env="BACKUP_FREQUENCY_HOURS")
    backup_retention_days: int = Field(default=30, env="BACKUP_RETENTION_DAYS")
    disaster_recovery_enabled: bool = Field(default=True, env="DISASTER_RECOVERY_ENABLED")
    failover_automatic: bool = Field(default=False, env="FAILOVER_AUTOMATIC")
    
    # ============================================================================
    # PERFORMANCE CONFIGURATION
    # ============================================================================
    
    async_task_queue_enabled: bool = Field(default=True, env="ASYNC_TASK_QUEUE_ENABLED")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    worker_processes: int = Field(default=4, env="WORKER_PROCESSES")
    worker_connections: int = Field(default=1000, env="WORKER_CONNECTIONS")
    
    # ============================================================================
    # CORS CONFIGURATION
    # ============================================================================
    
    cors_enabled: bool = Field(default=True, env="CORS_ENABLED")
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080,https://your-frontend-domain.com",
        env="CORS_ALLOWED_ORIGINS"
    )
    cors_allowed_methods: str = Field(default="GET,POST,PUT,DELETE,OPTIONS", env="CORS_ALLOWED_METHODS")
    cors_allowed_headers: str = Field(default="Content-Type,Authorization,X-Tenant-ID", env="CORS_ALLOWED_HEADERS")
    
    # ============================================================================
    # DEVELOPMENT TOOLS
    # ============================================================================
    
    hot_reload_enabled: bool = Field(default=True, env="HOT_RELOAD_ENABLED")
    api_docs_enabled: bool = Field(default=True, env="API_DOCS_ENABLED")
    swagger_ui_enabled: bool = Field(default=True, env="SWAGGER_UI_ENABLED")
    redoc_enabled: bool = Field(default=True, env="REDOC_ENABLED")
    
    # ============================================================================
    # AI MODEL CONFIGURATION
    # ============================================================================
    
    ai_regulatory_insights_enabled: bool = Field(default=True, env="AI_REGULATORY_INSIGHTS_ENABLED")
    ai_risk_scoring_enabled: bool = Field(default=True, env="AI_RISK_SCORING_ENABLED")
    ai_document_classification_enabled: bool = Field(default=True, env="AI_DOCUMENT_CLASSIFICATION_ENABLED")
    ai_sentiment_analysis_enabled: bool = Field(default=True, env="AI_SENTIMENT_ANALYSIS_ENABLED")
    ai_fraud_detection_enabled: bool = Field(default=True, env="AI_FRAUD_DETECTION_ENABLED")
    
    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    
    feature_advanced_analytics: bool = Field(default=True, env="FEATURE_ADVANCED_ANALYTICS")
    feature_predictive_compliance: bool = Field(default=True, env="FEATURE_PREDICTIVE_COMPLIANCE")
    feature_automated_reporting: bool = Field(default=True, env="FEATURE_AUTOMATED_REPORTING")
    feature_real_time_monitoring: bool = Field(default=True, env="FEATURE_REAL_TIME_MONITORING")
    feature_mobile_alerts: bool = Field(default=False, env="FEATURE_MOBILE_ALERTS")
    
    # ============================================================================
    # LOCALIZATION
    # ============================================================================
    
    default_timezone: str = Field(default="UTC", env="DEFAULT_TIMEZONE")
    supported_languages: str = Field(default="en,es,fr,de,pt,zh,ja", env="SUPPORTED_LANGUAGES")
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")
    date_format: str = Field(default="YYYY-MM-DD", env="DATE_FORMAT")
    currency_default: str = Field(default="USD", env="CURRENCY_DEFAULT")
    
    # ============================================================================
    # ENHANCED VALIDATORS
    # ============================================================================

    @field_validator('app_environment')
    @classmethod
    def validate_environment(cls, v):
        allowed_environments = ['development', 'staging', 'production', 'testing']
        if v not in allowed_environments:
            raise ConfigurationError(
                f'Environment must be one of: {allowed_environments}',
                field='app_environment',
                suggestions=[f"Set APP_ENVIRONMENT to one of: {', '.join(allowed_environments)}"]
            )
        return v

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret_key(cls, v):
        secret = v.get_secret_value() if isinstance(v, SecretStr) else v
        if len(secret) < 32:
            raise ConfigurationError(
                'JWT secret key must be at least 32 characters long for security',
                field='jwt_secret_key',
                suggestions=[
                    "Generate a secure key: openssl rand -hex 32",
                    "Use a password manager to generate a strong secret",
                    "Ensure the key is stored securely in environment variables"
                ]
            )
        return v

    @field_validator('encryption_key')
    @classmethod
    def validate_encryption_key(cls, v):
        key = v.get_secret_value() if isinstance(v, SecretStr) else v
        if len(key) != 44:  # Base64 encoded 32-byte key
            raise ConfigurationError(
                'Encryption key must be a 44-character base64-encoded 32-byte key',
                field='encryption_key',
                suggestions=[
                    "Generate a key: python -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode())'",
                    "Use Fernet.generate_key() from cryptography library",
                    "Ensure the key is properly base64 encoded"
                ]
            )
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()
    
    @field_validator('jwt_algorithm')
    @classmethod
    def validate_jwt_algorithm(cls, v):
        allowed_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
        if v not in allowed_algorithms:
            raise ValueError(f'JWT algorithm must be one of: {allowed_algorithms}')
        return v
    
    @field_validator('storage_provider')
    @classmethod
    def validate_storage_provider(cls, v):
        allowed_providers = ['supabase', 's3', 'azure', 'gcp']
        if v not in allowed_providers:
            raise ValueError(f'Storage provider must be one of: {allowed_providers}')
        return v
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'postgres://')):
            raise ConfigurationError(
                'Database URL must be a PostgreSQL connection string',
                field='database_url',
                suggestions=[
                    "Format: postgresql://username:password@host:port/database",
                    "Example: postgresql://user:pass@localhost:5432/regulensai",
                    "Ensure PostgreSQL is running and accessible"
                ]
            )

        # Parse and validate URL components
        try:
            parsed = urlparse(v)
            if not parsed.hostname:
                raise ConfigurationError(
                    'Database URL must include hostname',
                    field='database_url',
                    suggestions=["Include hostname in URL: postgresql://user:pass@hostname:5432/db"]
                )

            if not parsed.path or parsed.path == '/':
                raise ConfigurationError(
                    'Database URL must include database name',
                    field='database_url',
                    suggestions=["Include database name: postgresql://user:pass@host:5432/database_name"]
                )

        except Exception as e:
            raise ConfigurationError(
                f'Invalid database URL format: {str(e)}',
                field='database_url',
                suggestions=["Check URL format: postgresql://username:password@host:port/database"]
            )

        return v

    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v):
        if not v.startswith('https://') or not v.endswith('.supabase.co'):
            raise ConfigurationError(
                'Supabase URL must be a valid Supabase project URL',
                field='supabase_url',
                suggestions=[
                    "Format: https://your-project.supabase.co",
                    "Get URL from Supabase dashboard > Settings > API",
                    "Ensure project is active and accessible"
                ]
            )
        return v
    
    @field_validator('redis_url')
    @classmethod
    def validate_redis_url(cls, v):
        if not v.startswith('redis://'):
            raise ValueError('Redis URL must be a valid Redis connection string')
        return v
    
    @field_validator('api_port')
    @classmethod
    def validate_api_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('API port must be between 1 and 65535')
        return v
    
    @field_validator('bcrypt_rounds')
    @classmethod
    def validate_bcrypt_rounds(cls, v):
        if not 10 <= v <= 15:
            raise ValueError('Bcrypt rounds should be between 10 and 15 for security and performance')
        return v
    
    @field_validator('aml_threshold_amount')
    @classmethod
    def validate_aml_threshold(cls, v):
        if v <= 0:
            raise ConfigurationError(
                'AML threshold amount must be positive',
                field='aml_threshold_amount',
                suggestions=["Set to a reasonable amount like 10000.0 for $10,000 threshold"]
            )
        return v

    @field_validator('smtp_host', 'smtp_port')
    @classmethod
    def validate_smtp_config(cls, v, info):
        if info.field_name == 'smtp_host' and v:
            # Basic hostname validation
            if not re.match(r'^[a-zA-Z0-9.-]+$', v):
                raise ConfigurationError(
                    'SMTP host must be a valid hostname',
                    field='smtp_host',
                    suggestions=["Example: smtp.gmail.com, mail.company.com"]
                )

        if info.field_name == 'smtp_port' and v:
            if not 1 <= v <= 65535:
                raise ConfigurationError(
                    'SMTP port must be between 1 and 65535',
                    field='smtp_port',
                    suggestions=["Common ports: 587 (TLS), 465 (SSL), 25 (plain)"]
                )

        return v

    @model_validator(mode='after')
    def validate_environment_specific_requirements(self):
        """Validate environment-specific configuration requirements."""

        # Production environment validations
        if self.app_environment == 'production':
            self._validate_production_requirements()

        # Staging environment validations
        elif self.app_environment == 'staging':
            self._validate_staging_requirements()

        # Development environment validations
        elif self.app_environment == 'development':
            self._validate_development_requirements()

        return self

    def _validate_production_requirements(self):
        """Validate production-specific requirements."""
        errors = []

        # Security requirements
        if self.debug:
            errors.append("Debug mode must be disabled in production")

        if self.jwt_access_token_expire_minutes > 60:
            errors.append("JWT token expiration should be ≤ 60 minutes in production")

        if self.bcrypt_rounds < 12:
            errors.append("Bcrypt rounds should be ≥ 12 in production for security")

        # Monitoring requirements
        if not self.metrics_enabled:
            errors.append("Metrics must be enabled in production")

        if not self.jaeger_enabled:
            errors.append("Distributed tracing should be enabled in production")

        # Backup requirements
        if not self.backup_enabled:
            errors.append("Database backups must be enabled in production")

        if not self.disaster_recovery_enabled:
            errors.append("Disaster recovery must be enabled in production")

        # SSL/TLS requirements
        if 'localhost' in self.database_url or '127.0.0.1' in self.database_url:
            errors.append("Production database should not use localhost")

        if errors:
            raise ConfigurationError(
                f"Production environment validation failed: {'; '.join(errors)}",
                field='app_environment',
                suggestions=[
                    "Review production security checklist",
                    "Enable all monitoring and backup features",
                    "Use secure external services, not localhost"
                ]
            )

    def _validate_staging_requirements(self):
        """Validate staging-specific requirements."""
        errors = []

        # Staging should mirror production but allow some flexibility
        if not self.metrics_enabled:
            errors.append("Metrics should be enabled in staging for testing")

        if self.backup_frequency_hours > 24:
            errors.append("Backup frequency should be ≤ 24 hours in staging")

        if errors:
            raise ConfigurationError(
                f"Staging environment validation failed: {'; '.join(errors)}",
                field='app_environment',
                suggestions=["Staging should closely mirror production configuration"]
            )

    def _validate_development_requirements(self):
        """Validate development-specific requirements."""
        # Development is more flexible, but still has some requirements
        if self.database_pool_size > 10:
            logger.warning("Large database pool size in development may be unnecessary")

        if not self.hot_reload_enabled:
            logger.info("Hot reload disabled - enable for better development experience")
    
    # ============================================================================
    # COMPUTED PROPERTIES
    # ============================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_environment == 'production'
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_environment == 'development'
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app_environment == 'testing'
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list."""
        return [ext.strip() for ext in self.allowed_file_types.split(',')]
    
    @property
    def regulatory_jurisdictions_list(self) -> List[str]:
        """Get regulatory jurisdictions as a list."""
        return [j.strip() for j in self.regulatory_jurisdictions.split(',')]
    
    @property
    def compliance_frameworks_list(self) -> List[str]:
        """Get compliance frameworks as a list."""
        return [f.strip() for f in self.compliance_frameworks.split(',')]
    
    @property
    def aml_high_risk_countries_list(self) -> List[str]:
        """Get high-risk countries as a list."""
        return [c.strip() for c in self.aml_high_risk_countries.split(',')]
    
    @property
    def supported_languages_list(self) -> List[str]:
        """Get supported languages as a list."""
        return [lang.strip() for lang in self.supported_languages.split(',')]
    
    @property
    def cors_allowed_origins_list(self) -> List[str]:
        """Get CORS allowed origins as a list."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(',')]
    
    @property
    def default_tenant_settings_dict(self) -> Dict[str, Any]:
        """Get default tenant settings as a dictionary."""
        import json
        try:
            return json.loads(self.default_tenant_settings)
        except json.JSONDecodeError:
            logger.warning("Invalid default tenant settings JSON, using defaults")
            return {
                "max_users": 100,
                "max_customers": 10000,
                "max_transactions_per_month": 100000
            }
    
    # ============================================================================
    # COMPREHENSIVE VALIDATION METHODS
    # ============================================================================

    async def validate_all_configurations(self) -> Dict[str, Any]:
        """
        Perform comprehensive validation of all configuration settings.
        Returns validation results with detailed error information.
        """
        validation_results = {
            'overall_status': 'pending',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': self.app_environment,
            'validations': {}
        }

        # Database validation
        validation_results['validations']['database'] = await self._validate_database_config()

        # Redis validation
        validation_results['validations']['redis'] = await self._validate_redis_config()

        # External services validation
        validation_results['validations']['external_services'] = await self._validate_external_services()

        # Security validation
        validation_results['validations']['security'] = self._validate_security_config()

        # File system validation
        validation_results['validations']['filesystem'] = self._validate_filesystem_config()

        # AI/ML services validation
        validation_results['validations']['ai_services'] = await self._validate_ai_services()

        # Determine overall status
        all_passed = all(
            result.get('status') == 'passed'
            for result in validation_results['validations'].values()
        )
        validation_results['overall_status'] = 'passed' if all_passed else 'failed'

        return validation_results

    async def _validate_database_config(self) -> Dict[str, Any]:
        """Validate database configuration and connectivity."""
        result = {
            'status': 'pending',
            'checks': {},
            'errors': [],
            'warnings': []
        }

        try:
            # Test database connectivity
            result['checks']['connectivity'] = await self._test_database_connectivity()

            # Validate schema compatibility
            schema_valid, schema_errors = await DatabaseSchemaValidator.validate_schema(self.database_url)
            result['checks']['schema'] = {
                'status': 'passed' if schema_valid else 'failed',
                'errors': schema_errors
            }

            # Check database configuration
            result['checks']['configuration'] = self._validate_database_settings()

            # Determine overall database validation status
            all_db_checks_passed = all(
                check.get('status') == 'passed'
                for check in result['checks'].values()
            )
            result['status'] = 'passed' if all_db_checks_passed else 'failed'

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Database validation failed: {str(e)}")

        return result

    async def _test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity and basic operations."""
        try:
            conn = await asyncpg.connect(self.database_url)

            try:
                # Test basic query
                await conn.fetchval("SELECT 1")

                # Test transaction capability
                async with conn.transaction():
                    await conn.fetchval("SELECT NOW()")

                return {
                    'status': 'passed',
                    'message': 'Database connectivity successful'
                }

            finally:
                await conn.close()

        except Exception as e:
            return {
                'status': 'failed',
                'message': f"Database connectivity failed: {str(e)}",
                'suggestions': [
                    "Check database server is running",
                    "Verify connection string format",
                    "Ensure network connectivity to database host",
                    "Validate database credentials"
                ]
            }

    def _validate_database_settings(self) -> Dict[str, Any]:
        """Validate database pool and connection settings."""
        warnings = []

        # Check pool size settings
        if self.database_pool_size > 50:
            warnings.append("Large database pool size may consume excessive resources")

        if self.database_pool_timeout < 10:
            warnings.append("Short pool timeout may cause connection failures under load")

        if self.database_pool_recycle < 1800:  # 30 minutes
            warnings.append("Short connection recycle time may impact performance")

        return {
            'status': 'passed',
            'warnings': warnings,
            'recommendations': [
                f"Pool size: {self.database_pool_size} (recommended: 10-30 for most applications)",
                f"Pool timeout: {self.database_pool_timeout}s (recommended: 30s+)",
                f"Connection recycle: {self.database_pool_recycle}s (recommended: 3600s+)"
            ]
        }

    async def _validate_redis_config(self) -> Dict[str, Any]:
        """Validate Redis configuration and connectivity."""
        result = {
            'status': 'pending',
            'checks': {},
            'errors': [],
            'warnings': []
        }

        try:
            # Test Redis connectivity
            redis_valid, redis_message = await ExternalServiceValidator.validate_redis_connection(
                self.redis_url,
                self.redis_password.get_secret_value() if self.redis_password else None
            )

            result['checks']['connectivity'] = {
                'status': 'passed' if redis_valid else 'failed',
                'message': redis_message
            }

            # Validate Redis settings
            if self.redis_max_connections > 100:
                result['warnings'].append("High Redis max connections may impact performance")

            if self.cache_default_timeout < 60:
                result['warnings'].append("Short cache timeout may reduce cache effectiveness")

            result['status'] = 'passed' if redis_valid else 'failed'

        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Redis validation failed: {str(e)}")

        return result

    # ============================================================================
    # CONFIGURATION METHODS
    # ============================================================================
    
    def get_database_url(self, for_async: bool = True) -> str:
        """Get database URL with async driver if needed."""
        if for_async and self.database_url.startswith('postgresql://'):
            return self.database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return self.database_url
    
    def get_redis_url_with_password(self) -> str:
        """Get Redis URL with password included."""
        if self.redis_password:
            # Parse URL and add password
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.redis_url)
            if not parsed.username:
                netloc = f":{self.redis_password.get_secret_value()}@{parsed.hostname}:{parsed.port}"
                return urlunparse(parsed._replace(netloc=netloc))
        return self.redis_url
    
    async def _validate_external_services(self) -> Dict[str, Any]:
        """Validate external service configurations."""
        result = {
            'status': 'passed',
            'checks': {},
            'errors': [],
            'warnings': []
        }

        # SMTP validation
        if self.notification_email_enabled and self.smtp_username and self.smtp_password:
            smtp_valid, smtp_message = ExternalServiceValidator.validate_smtp_config(
                self.smtp_host, self.smtp_port,
                self.smtp_username, self.smtp_password.get_secret_value()
            )
            result['checks']['smtp'] = {
                'status': 'passed' if smtp_valid else 'failed',
                'message': smtp_message
            }

        # API endpoints validation
        api_checks = {}

        # OpenAI API
        if self.openai_api_key:
            openai_valid, openai_message = ExternalServiceValidator.validate_api_endpoint(
                "https://api.openai.com/v1/models",
                self.openai_api_key.get_secret_value()
            )
            api_checks['openai'] = {
                'status': 'passed' if openai_valid else 'failed',
                'message': openai_message
            }

        # Claude API
        if self.claude_api_key:
            claude_valid, claude_message = ExternalServiceValidator.validate_api_endpoint(
                "https://api.anthropic.com/v1/messages",
                self.claude_api_key.get_secret_value()
            )
            api_checks['claude'] = {
                'status': 'passed' if claude_valid else 'failed',
                'message': claude_message
            }

        result['checks']['api_endpoints'] = api_checks

        # Check if any critical services failed
        failed_checks = [
            check for check in result['checks'].values()
            if isinstance(check, dict) and check.get('status') == 'failed'
        ]

        if failed_checks:
            result['status'] = 'failed'
            result['errors'].append(f"{len(failed_checks)} external service(s) failed validation")

        return result

    def _validate_security_config(self) -> Dict[str, Any]:
        """Validate security configuration settings."""
        result = {
            'status': 'passed',
            'checks': {},
            'errors': [],
            'warnings': []
        }

        # JWT configuration
        jwt_checks = []

        if self.jwt_access_token_expire_minutes > 120:
            jwt_checks.append("JWT access token expiration is very long (>2 hours)")

        if self.jwt_refresh_token_expire_days > 90:
            jwt_checks.append("JWT refresh token expiration is very long (>90 days)")

        if self.jwt_algorithm.startswith('HS') and len(self.jwt_secret_key.get_secret_value()) < 64:
            jwt_checks.append("JWT secret key should be longer for HMAC algorithms")

        result['checks']['jwt'] = {
            'status': 'passed' if not jwt_checks else 'warning',
            'issues': jwt_checks
        }

        # Encryption settings
        encryption_checks = []

        if self.bcrypt_rounds < 10:
            encryption_checks.append("Bcrypt rounds too low for security")
        elif self.bcrypt_rounds > 15:
            encryption_checks.append("Bcrypt rounds very high - may impact performance")

        result['checks']['encryption'] = {
            'status': 'passed' if not encryption_checks else 'warning',
            'issues': encryption_checks
        }

        # CORS settings
        cors_checks = []

        if self.cors_enabled and '*' in self.cors_allowed_origins:
            cors_checks.append("CORS allows all origins (*) - security risk in production")

        result['checks']['cors'] = {
            'status': 'passed' if not cors_checks else 'warning',
            'issues': cors_checks
        }

        return result

    def _validate_filesystem_config(self) -> Dict[str, Any]:
        """Validate filesystem and storage configuration."""
        result = {
            'status': 'passed',
            'checks': {},
            'errors': [],
            'warnings': []
        }

        # Check cache directory
        cache_dir = Path(self.fastembed_cache_dir)
        if not cache_dir.exists():
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                result['checks']['cache_directory'] = {
                    'status': 'passed',
                    'message': f"Created cache directory: {cache_dir}"
                }
            except Exception as e:
                result['checks']['cache_directory'] = {
                    'status': 'failed',
                    'message': f"Cannot create cache directory: {str(e)}"
                }
                result['status'] = 'failed'
        else:
            result['checks']['cache_directory'] = {
                'status': 'passed',
                'message': f"Cache directory exists: {cache_dir}"
            }

        # Validate file size limits
        if self.max_file_size_mb > 1000:  # 1GB
            result['warnings'].append("Very large file size limit may impact performance")

        # Validate allowed file types
        allowed_types = self.allowed_file_types_list
        if 'exe' in allowed_types or 'bat' in allowed_types:
            result['warnings'].append("Executable file types in allowed list - security risk")

        return result

    async def _validate_ai_services(self) -> Dict[str, Any]:
        """Validate AI/ML service configurations."""
        result = {
            'status': 'passed',
            'checks': {},
            'errors': [],
            'warnings': []
        }

        # OpenAI configuration
        if self.ai_regulatory_insights_enabled and not self.openai_api_key:
            result['warnings'].append("AI insights enabled but OpenAI API key not configured")

        # Model configuration
        if self.openai_max_tokens > 8000:
            result['warnings'].append("High OpenAI max tokens may increase costs")

        if self.openai_temperature > 0.5:
            result['warnings'].append("High OpenAI temperature may reduce consistency")

        # Vector database configuration
        if self.vector_dimension not in [384, 512, 768, 1024, 1536]:
            result['warnings'].append("Unusual vector dimension - ensure compatibility with embedding model")

        return result

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        feature_attr = f"feature_{feature_name.lower()}"
        return getattr(self, feature_attr, False)

    @classmethod
    def validate_config_file(cls, file_path: Union[str, Path]) -> Tuple[bool, List[str]]:
        """Validate configuration file format and content."""
        file_path = Path(file_path)
        errors = []

        if not file_path.exists():
            return False, [f"Configuration file not found: {file_path}"]

        try:
            if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    json.load(f)
            elif file_path.suffix.lower() == '.env':
                # Validate .env file format
                with open(file_path, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' not in line:
                                errors.append(f"Line {line_num}: Invalid format, missing '='")
            else:
                errors.append(f"Unsupported configuration file format: {file_path.suffix}")

            return len(errors) == 0, errors

        except yaml.YAMLError as e:
            return False, [f"YAML parsing error: {str(e)}"]
        except json.JSONDecodeError as e:
            return False, [f"JSON parsing error: {str(e)}"]
        except Exception as e:
            return False, [f"Configuration file validation error: {str(e)}"]
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "use_enum_values": True,
        "extra": "allow"
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings with comprehensive validation.
    Uses LRU cache to avoid reading environment variables multiple times.
    """
    try:
        settings = Settings()
        logger.info(
            "Configuration loaded successfully",
            environment=settings.app_environment,
            debug=settings.debug,
            api_port=settings.api_port
        )
        return settings

    except ConfigurationError as e:
        logger.error(
            "Configuration validation failed",
            field=e.field,
            error=str(e),
            suggestions=e.suggestions
        )

        # Provide actionable error message
        error_msg = f"Configuration Error in {e.field}: {str(e)}"
        if e.suggestions:
            error_msg += f"\n\nSuggestions:\n" + "\n".join(f"  - {s}" for s in e.suggestions)

        raise ConfigurationError(error_msg, e.field, e.suggestions)

    except ValidationError as e:
        logger.error("Pydantic validation failed", errors=e.errors())

        # Format validation errors with suggestions
        formatted_errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error['loc'])
            msg = error['msg']
            formatted_errors.append(f"  {field}: {msg}")

        error_msg = "Configuration validation failed:\n" + "\n".join(formatted_errors)
        error_msg += "\n\nPlease check your environment variables and configuration files."

        raise ConfigurationError(error_msg)

    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        raise ConfigurationError(f"Failed to load configuration: {str(e)}")


def reload_settings() -> Settings:
    """
    Force reload of settings (useful for testing).
    Clears the cache and loads fresh settings.
    """
    get_settings.cache_clear()
    return get_settings()


async def validate_configuration(settings: Settings = None) -> Dict[str, Any]:
    """
    Perform comprehensive configuration validation.

    Args:
        settings: Settings instance to validate (uses default if None)

    Returns:
        Dict containing validation results
    """
    if settings is None:
        settings = get_settings()

    logger.info("Starting comprehensive configuration validation",
                environment=settings.app_environment)

    try:
        validation_results = await settings.validate_all_configurations()

        # Log validation summary
        overall_status = validation_results['overall_status']
        failed_validations = [
            name for name, result in validation_results['validations'].items()
            if result.get('status') == 'failed'
        ]

        if overall_status == 'passed':
            logger.info("Configuration validation completed successfully")
        else:
            logger.error(
                "Configuration validation failed",
                failed_validations=failed_validations,
                total_validations=len(validation_results['validations'])
            )

        return validation_results

    except Exception as e:
        logger.error("Configuration validation error", error=str(e))
        return {
            'overall_status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'validations': {}
        }


def get_configuration_summary(settings: Settings = None) -> Dict[str, Any]:
    """
    Get a summary of current configuration settings.

    Args:
        settings: Settings instance to summarize (uses default if None)

    Returns:
        Dict containing configuration summary
    """
    if settings is None:
        settings = get_settings()

    return {
        'environment': settings.app_environment,
        'debug_mode': settings.debug,
        'api_configuration': {
            'host': settings.api_host,
            'port': settings.api_port,
            'version': settings.api_version,
            'cors_enabled': settings.cors_enabled
        },
        'database_configuration': {
            'pool_size': settings.database_pool_size,
            'max_overflow': settings.database_max_overflow,
            'pool_timeout': settings.database_pool_timeout
        },
        'security_configuration': {
            'jwt_algorithm': settings.jwt_algorithm,
            'jwt_access_token_expire_minutes': settings.jwt_access_token_expire_minutes,
            'bcrypt_rounds': settings.bcrypt_rounds
        },
        'feature_flags': {
            'advanced_analytics': settings.feature_advanced_analytics,
            'predictive_compliance': settings.feature_predictive_compliance,
            'automated_reporting': settings.feature_automated_reporting,
            'real_time_monitoring': settings.feature_real_time_monitoring,
            'mobile_alerts': settings.feature_mobile_alerts
        },
        'ai_configuration': {
            'regulatory_insights_enabled': settings.ai_regulatory_insights_enabled,
            'risk_scoring_enabled': settings.ai_risk_scoring_enabled,
            'document_classification_enabled': settings.ai_document_classification_enabled,
            'openai_model': settings.openai_model,
            'anthropic_model': settings.anthropic_model
        },
        'monitoring_configuration': {
            'metrics_enabled': settings.metrics_enabled,
            'jaeger_enabled': settings.jaeger_enabled,
            'log_level': settings.log_level
        }
    }


# Export settings instance for convenient access
settings = get_settings() 