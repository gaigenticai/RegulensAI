"""
Tests for RegulensAI Configuration Validation System
"""

import pytest
import os
import tempfile
import json
import yaml
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from core_infra.config import (
    Settings, 
    ConfigurationError, 
    DatabaseSchemaValidator,
    ExternalServiceValidator,
    get_settings,
    validate_configuration,
    get_configuration_summary
)


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    def test_jwt_secret_key_validation(self):
        """Test JWT secret key validation."""
        # Test short key (should fail)
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(jwt_secret_key="short")
        
        assert "at least 32 characters" in str(exc_info.value)
        assert exc_info.value.field == "jwt_secret_key"
        assert len(exc_info.value.suggestions) > 0
    
    def test_encryption_key_validation(self):
        """Test encryption key validation."""
        # Test invalid length (should fail)
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(encryption_key="invalid_key")
        
        assert "44-character base64-encoded" in str(exc_info.value)
        assert exc_info.value.field == "encryption_key"
    
    def test_database_url_validation(self):
        """Test database URL validation."""
        # Test invalid protocol
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(database_url="mysql://user:pass@host/db")
        
        assert "PostgreSQL connection string" in str(exc_info.value)
        assert exc_info.value.field == "database_url"
        
        # Test missing hostname
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(database_url="postgresql:///database")
        
        assert "must include hostname" in str(exc_info.value)
        
        # Test missing database name
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(database_url="postgresql://user:pass@host:5432/")
        
        assert "must include database name" in str(exc_info.value)
    
    def test_environment_validation(self):
        """Test environment validation."""
        # Test invalid environment
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(app_environment="invalid")
        
        assert "must be one of" in str(exc_info.value)
        assert exc_info.value.field == "app_environment"
    
    def test_supabase_url_validation(self):
        """Test Supabase URL validation."""
        # Test invalid Supabase URL
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(supabase_url="https://invalid.com")
        
        assert "valid Supabase project URL" in str(exc_info.value)
        assert exc_info.value.field == "supabase_url"
    
    def test_aml_threshold_validation(self):
        """Test AML threshold validation."""
        # Test negative threshold
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(aml_threshold_amount=-100.0)
        
        assert "must be positive" in str(exc_info.value)
        assert exc_info.value.field == "aml_threshold_amount"
    
    def test_smtp_validation(self):
        """Test SMTP configuration validation."""
        # Test invalid SMTP host
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(smtp_host="invalid@host!")
        
        assert "valid hostname" in str(exc_info.value)
        assert exc_info.value.field == "smtp_host"
        
        # Test invalid SMTP port
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(smtp_port=99999)
        
        assert "between 1 and 65535" in str(exc_info.value)
        assert exc_info.value.field == "smtp_port"


class TestEnvironmentSpecificValidation:
    """Test environment-specific validation rules."""
    
    def test_production_validation(self):
        """Test production environment validation."""
        # Test production with debug enabled (should fail)
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(
                app_environment="production",
                debug=True,
                jwt_secret_key="a" * 32,
                encryption_key="a" * 44
            )
        
        assert "Debug mode must be disabled" in str(exc_info.value)
        assert exc_info.value.field == "app_environment"
    
    def test_production_security_requirements(self):
        """Test production security requirements."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(
                app_environment="production",
                debug=False,
                jwt_access_token_expire_minutes=180,  # Too long
                bcrypt_rounds=8,  # Too low
                jwt_secret_key="a" * 32,
                encryption_key="a" * 44
            )
        
        error_message = str(exc_info.value)
        assert "≤ 60 minutes" in error_message
        assert "≥ 12 in production" in error_message
    
    def test_staging_validation(self):
        """Test staging environment validation."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(
                app_environment="staging",
                metrics_enabled=False,
                backup_frequency_hours=48,  # Too long
                jwt_secret_key="a" * 32,
                encryption_key="a" * 44
            )
        
        error_message = str(exc_info.value)
        assert "Metrics should be enabled" in error_message
        assert "≤ 24 hours" in error_message


class TestDatabaseSchemaValidator:
    """Test database schema validation."""
    
    @pytest.mark.asyncio
    async def test_schema_validation_success(self):
        """Test successful schema validation."""
        # Mock successful database connection and queries
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            # Mock table check
            mock_conn.fetch.side_effect = [
                # Tables query
                [{'table_name': table} for table in DatabaseSchemaValidator.REQUIRED_TABLES],
                # Indexes query
                [{'indexname': index} for index in DatabaseSchemaValidator.REQUIRED_INDEXES],
                # Extensions query
                [{'extname': 'uuid-ossp'}, {'extname': 'pg_trgm'}, {'extname': 'btree_gin'}]
            ]
            
            # Mock version check
            mock_conn.fetchval.return_value = "PostgreSQL 14.5 on x86_64-pc-linux-gnu"
            
            valid, errors = await DatabaseSchemaValidator.validate_schema("postgresql://test")
            
            assert valid is True
            assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_schema_validation_missing_tables(self):
        """Test schema validation with missing tables."""
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            # Mock missing tables
            existing_tables = list(DatabaseSchemaValidator.REQUIRED_TABLES)[:5]  # Only first 5 tables
            mock_conn.fetch.side_effect = [
                [{'table_name': table} for table in existing_tables],
                [{'indexname': index} for index in DatabaseSchemaValidator.REQUIRED_INDEXES],
                [{'extname': 'uuid-ossp'}, {'extname': 'pg_trgm'}, {'extname': 'btree_gin'}]
            ]
            
            mock_conn.fetchval.return_value = "PostgreSQL 14.5 on x86_64-pc-linux-gnu"
            
            valid, errors = await DatabaseSchemaValidator.validate_schema("postgresql://test")
            
            assert valid is False
            assert any("Missing required tables" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_schema_validation_connection_failure(self):
        """Test schema validation with connection failure."""
        with patch('asyncpg.connect', side_effect=Exception("Connection failed")):
            valid, errors = await DatabaseSchemaValidator.validate_schema("postgresql://test")
            
            assert valid is False
            assert any("Database connection failed" in error for error in errors)


class TestExternalServiceValidator:
    """Test external service validation."""
    
    @pytest.mark.asyncio
    async def test_redis_validation_success(self):
        """Test successful Redis validation."""
        with patch('redis.from_url') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            valid, message = await ExternalServiceValidator.validate_redis_connection("redis://localhost:6379")
            
            assert valid is True
            assert "successful" in message
    
    @pytest.mark.asyncio
    async def test_redis_validation_failure(self):
        """Test Redis validation failure."""
        with patch('redis.from_url', side_effect=Exception("Connection refused")):
            valid, message = await ExternalServiceValidator.validate_redis_connection("redis://localhost:6379")
            
            assert valid is False
            assert "failed" in message
    
    def test_smtp_validation_success(self):
        """Test successful SMTP validation."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            valid, message = ExternalServiceValidator.validate_smtp_config("smtp.gmail.com", 587)
            
            assert valid is True
            assert "valid" in message
    
    def test_smtp_validation_failure(self):
        """Test SMTP validation failure."""
        with patch('smtplib.SMTP', side_effect=Exception("Connection failed")):
            valid, message = ExternalServiceValidator.validate_smtp_config("invalid.host", 587)
            
            assert valid is False
            assert "failed" in message
    
    def test_api_endpoint_validation_success(self):
        """Test successful API endpoint validation."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            valid, message = ExternalServiceValidator.validate_api_endpoint("https://api.example.com")
            
            assert valid is True
            assert "accessible" in message
    
    def test_api_endpoint_validation_auth_failure(self):
        """Test API endpoint validation with auth failure."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response
            
            valid, message = ExternalServiceValidator.validate_api_endpoint("https://api.example.com", "invalid_key")
            
            assert valid is False
            assert "authentication failed" in message


class TestConfigurationFileValidation:
    """Test configuration file format validation."""
    
    def test_yaml_file_validation_success(self):
        """Test successful YAML file validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'key': 'value', 'nested': {'key': 'value'}}, f)
            temp_path = f.name
        
        try:
            valid, errors = Settings.validate_config_file(temp_path)
            assert valid is True
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)
    
    def test_yaml_file_validation_failure(self):
        """Test YAML file validation with syntax error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            valid, errors = Settings.validate_config_file(temp_path)
            assert valid is False
            assert any("YAML parsing error" in error for error in errors)
        finally:
            os.unlink(temp_path)
    
    def test_json_file_validation_success(self):
        """Test successful JSON file validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'key': 'value', 'nested': {'key': 'value'}}, f)
            temp_path = f.name
        
        try:
            valid, errors = Settings.validate_config_file(temp_path)
            assert valid is True
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)
    
    def test_env_file_validation_success(self):
        """Test successful .env file validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KEY1=value1\nKEY2=value2\n# Comment\nKEY3=value3")
            temp_path = f.name
        
        try:
            valid, errors = Settings.validate_config_file(temp_path)
            assert valid is True
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)
    
    def test_env_file_validation_failure(self):
        """Test .env file validation with invalid format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KEY1=value1\nINVALID_LINE_WITHOUT_EQUALS\nKEY2=value2")
            temp_path = f.name
        
        try:
            valid, errors = Settings.validate_config_file(temp_path)
            assert valid is False
            assert any("missing '='" in error for error in errors)
        finally:
            os.unlink(temp_path)
    
    def test_unsupported_file_format(self):
        """Test validation of unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name
        
        try:
            valid, errors = Settings.validate_config_file(temp_path)
            assert valid is False
            assert any("Unsupported configuration file format" in error for error in errors)
        finally:
            os.unlink(temp_path)


class TestConfigurationIntegration:
    """Test configuration validation integration."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation(self):
        """Test comprehensive configuration validation."""
        # Create a valid settings instance
        settings = Settings(
            app_environment="development",
            jwt_secret_key="a" * 32,
            encryption_key="a" * 44,
            database_url="postgresql://user:pass@localhost:5432/test"
        )
        
        # Mock external validations
        with patch.object(settings, '_test_database_connectivity', return_value={'status': 'passed'}), \
             patch.object(DatabaseSchemaValidator, 'validate_schema', return_value=(True, [])), \
             patch.object(ExternalServiceValidator, 'validate_redis_connection', return_value=(True, "Success")):
            
            results = await validate_configuration(settings)
            
            assert results['overall_status'] in ['passed', 'failed']
            assert 'validations' in results
            assert 'timestamp' in results
    
    def test_configuration_summary(self):
        """Test configuration summary generation."""
        settings = Settings(
            app_environment="development",
            jwt_secret_key="a" * 32,
            encryption_key="a" * 44
        )
        
        summary = get_configuration_summary(settings)
        
        assert 'environment' in summary
        assert 'api_configuration' in summary
        assert 'database_configuration' in summary
        assert 'security_configuration' in summary
        assert 'feature_flags' in summary
        assert summary['environment'] == 'development'


if __name__ == "__main__":
    pytest.main([__file__])
