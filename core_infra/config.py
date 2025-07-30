"""
Regulens AI - Configuration Management
Enterprise-grade configuration with environment variable validation.
"""

import os
from functools import lru_cache
from typing import List, Optional, Dict, Any
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
import structlog

logger = structlog.get_logger(__name__)


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
    # VALIDATORS
    # ============================================================================
    
    @field_validator('app_environment')
    @classmethod
    def validate_environment(cls, v):
        allowed_environments = ['development', 'staging', 'production', 'testing']
        if v not in allowed_environments:
            raise ValueError(f'Environment must be one of: {allowed_environments}')
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
            raise ValueError('Database URL must be a PostgreSQL connection string')
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
            raise ValueError('AML threshold amount must be positive')
        return v
    
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
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        feature_attr = f"feature_{feature_name.lower()}"
        return getattr(self, feature_attr, False)
    
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
    Get cached application settings.
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
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


def reload_settings() -> Settings:
    """
    Force reload of settings (useful for testing).
    Clears the cache and loads fresh settings.
    """
    get_settings.cache_clear()
    return get_settings()


# Export settings instance for convenient access
settings = get_settings() 