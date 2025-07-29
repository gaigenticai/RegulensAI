"""
Configuration management for RegulensAI
"""
import os
from typing import List

class Settings:
    """Application settings"""
    
    def __init__(self):
        self.app_version = "1.0.0"
        self.api_version = "v1"
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database
        self.database_url = os.getenv("DATABASE_URL", "")
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        
        # Security
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        self.jwt_access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # Features
        self.regulatory_monitor_enabled = True
        self.aml_monitoring_enabled = True
        self.jaeger_enabled = False
        self.jaeger_service_name = "regulens-ai"
        
        # API Documentation
        self.api_docs_enabled = True
        self.swagger_ui_enabled = True
        self.redoc_enabled = True
        
        # CORS
        self.cors_enabled = True
        self.cors_allowed_origins = "*"
        self.cors_allowed_methods = "GET,POST,PUT,DELETE,OPTIONS"
        self.cors_allowed_headers = "*"
        
        # Rate limiting
        self.rate_limit_enabled = False
        self.rate_limit_requests_per_minute = 60
        self.rate_limit_burst = 10
        
        # Multi-tenancy
        self.tenant_isolation_enabled = False

_settings = None

def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 