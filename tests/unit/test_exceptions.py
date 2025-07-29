"""
Unit tests for exception handling module.
"""

import pytest
import uuid
from datetime import datetime
from fastapi import HTTPException, status

from core_infra.exceptions import (
    RegulensBaseException,
    AuthenticationException,
    AuthorizationException,
    InvalidTokenException,
    InsufficientPermissionsException,
    TenantAccessDeniedException,
    ComplianceException,
    RegulatoryViolationException,
    AMLViolationException,
    KYCViolationException,
    SanctionsViolationException,
    DataValidationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    BusinessLogicException,
    ExternalServiceException,
    RateLimitExceededException,
    SystemException,
    DatabaseException,
    exception_to_http_exception,
    log_exception
)

class TestBaseException:
    """Test base exception functionality."""
    
    def test_base_exception_creation(self):
        """Test base exception creation with all parameters."""
        message = "Test error message"
        error_code = "TEST_ERROR"
        details = {"key": "value"}
        user_message = "User-friendly message"
        
        exception = RegulensBaseException(
            message=message,
            error_code=error_code,
            details=details,
            user_message=user_message
        )
        
        assert exception.message == message
        assert exception.error_code == error_code
        assert exception.details == details
        assert exception.user_message == user_message
        assert isinstance(exception.timestamp, datetime)
        assert isinstance(exception.exception_id, str)
        assert len(exception.exception_id) == 36  # UUID length
    
    def test_base_exception_defaults(self):
        """Test base exception with default values."""
        message = "Test error"
        exception = RegulensBaseException(message)
        
        assert exception.message == message
        assert exception.error_code == "RegulensBaseException"
        assert exception.details == {}
        assert exception.user_message == message
    
    def test_base_exception_to_dict(self):
        """Test exception to dictionary conversion."""
        exception = RegulensBaseException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"},
            user_message="User message"
        )
        
        result = exception.to_dict()
        
        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["details"] == {"key": "value"}
        assert result["user_message"] == "User message"
        assert "exception_id" in result
        assert "timestamp" in result

class TestAuthenticationExceptions:
    """Test authentication-related exceptions."""
    
    def test_invalid_token_exception(self):
        """Test InvalidTokenException."""
        exception = InvalidTokenException()
        
        assert exception.error_code == "INVALID_TOKEN"
        assert "expired" in exception.message.lower()
        assert "log in again" in exception.user_message.lower()
    
    def test_invalid_token_exception_custom_message(self):
        """Test InvalidTokenException with custom message."""
        custom_message = "Custom token error"
        exception = InvalidTokenException(custom_message)
        
        assert exception.message == custom_message
        assert exception.error_code == "INVALID_TOKEN"

class TestAuthorizationExceptions:
    """Test authorization-related exceptions."""
    
    def test_insufficient_permissions_exception(self):
        """Test InsufficientPermissionsException."""
        required_permission = "users.delete"
        exception = InsufficientPermissionsException(required_permission)
        
        assert exception.error_code == "INSUFFICIENT_PERMISSIONS"
        assert required_permission in exception.message
        assert exception.details["required_permission"] == required_permission
        assert "permission" in exception.user_message.lower()
    
    def test_tenant_access_denied_exception(self):
        """Test TenantAccessDeniedException."""
        tenant_id = str(uuid.uuid4())
        exception = TenantAccessDeniedException(tenant_id)
        
        assert exception.error_code == "TENANT_ACCESS_DENIED"
        assert exception.details["tenant_id"] == tenant_id
        assert "organization" in exception.user_message.lower()
    
    def test_tenant_access_denied_exception_no_tenant_id(self):
        """Test TenantAccessDeniedException without tenant ID."""
        exception = TenantAccessDeniedException()
        
        assert exception.error_code == "TENANT_ACCESS_DENIED"
        assert exception.details == {}

class TestComplianceExceptions:
    """Test compliance-related exceptions."""
    
    def test_regulatory_violation_exception(self):
        """Test RegulatoryViolationException."""
        regulation = "SOX"
        violation_details = {"section": "404", "description": "Internal controls"}
        exception = RegulatoryViolationException(regulation, violation_details)
        
        assert exception.error_code == "REGULATORY_VIOLATION"
        assert regulation in exception.message
        assert exception.details["regulation"] == regulation
        assert exception.details["violation_details"] == violation_details
    
    def test_aml_violation_exception(self):
        """Test AMLViolationException."""
        customer_id = str(uuid.uuid4())
        transaction_id = str(uuid.uuid4())
        exception = AMLViolationException(customer_id, transaction_id)
        
        assert exception.error_code == "AML_VIOLATION"
        assert exception.details["customer_id"] == customer_id
        assert exception.details["transaction_id"] == transaction_id
        assert "aml" in exception.user_message.lower()
    
    def test_kyc_violation_exception(self):
        """Test KYCViolationException."""
        customer_id = str(uuid.uuid4())
        missing_docs = ["passport", "proof_of_address"]
        exception = KYCViolationException(customer_id, missing_docs)
        
        assert exception.error_code == "KYC_VIOLATION"
        assert exception.details["customer_id"] == customer_id
        assert exception.details["missing_documents"] == missing_docs
    
    def test_sanctions_violation_exception(self):
        """Test SanctionsViolationException."""
        entity_name = "John Doe"
        sanctions_list = "OFAC SDN"
        exception = SanctionsViolationException(entity_name, sanctions_list)
        
        assert exception.error_code == "SANCTIONS_VIOLATION"
        assert entity_name in exception.message
        assert sanctions_list in exception.message
        assert exception.details["entity_name"] == entity_name
        assert exception.details["sanctions_list"] == sanctions_list

class TestDataExceptions:
    """Test data-related exceptions."""
    
    def test_data_validation_exception(self):
        """Test DataValidationException."""
        field = "email"
        value = "invalid-email"
        validation_rule = "must be valid email format"
        exception = DataValidationException(field, value, validation_rule)
        
        assert exception.error_code == "DATA_VALIDATION_ERROR"
        assert field in exception.message
        assert exception.details["field"] == field
        assert exception.details["value"] == value
        assert exception.details["validation_rule"] == validation_rule
    
    def test_resource_not_found_exception(self):
        """Test ResourceNotFoundException."""
        resource_type = "user"
        identifier = str(uuid.uuid4())
        exception = ResourceNotFoundException(resource_type, identifier)
        
        assert exception.error_code == "RESOURCE_NOT_FOUND"
        assert resource_type in exception.message
        assert identifier in exception.message
        assert exception.details["resource_type"] == resource_type
        assert exception.details["identifier"] == identifier
    
    def test_duplicate_resource_exception(self):
        """Test DuplicateResourceException."""
        resource_type = "email"
        identifier = "test@example.com"
        exception = DuplicateResourceException(resource_type, identifier)
        
        assert exception.error_code == "DUPLICATE_RESOURCE"
        assert resource_type in exception.message
        assert identifier in exception.message
        assert "already exists" in exception.user_message

class TestSystemExceptions:
    """Test system-related exceptions."""
    
    def test_database_exception(self):
        """Test DatabaseException."""
        operation = "INSERT"
        error_details = "Connection timeout"
        exception = DatabaseException(operation, error_details)
        
        assert exception.error_code == "DATABASE_ERROR"
        assert operation in exception.message
        assert error_details in exception.message
        assert exception.details["operation"] == operation
        assert exception.details["error_details"] == error_details
    
    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceededException."""
        service_name = "external_api"
        retry_after = 60
        exception = RateLimitExceededException(service_name, retry_after)
        
        assert exception.error_code == "RATE_LIMIT_EXCEEDED"
        assert service_name in exception.message
        assert exception.details["retry_after"] == retry_after

class TestExceptionToHTTPException:
    """Test conversion of custom exceptions to HTTP exceptions."""
    
    def test_authentication_exception_conversion(self):
        """Test AuthenticationException to HTTP conversion."""
        exception = InvalidTokenException()
        http_exception = exception_to_http_exception(exception)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert http_exception.detail["error_code"] == "INVALID_TOKEN"
        assert "exception_id" in http_exception.detail
    
    def test_authorization_exception_conversion(self):
        """Test AuthorizationException to HTTP conversion."""
        exception = InsufficientPermissionsException("users.delete")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_403_FORBIDDEN
        assert http_exception.detail["error_code"] == "INSUFFICIENT_PERMISSIONS"
    
    def test_validation_exception_conversion(self):
        """Test DataValidationException to HTTP conversion."""
        exception = DataValidationException("email", "invalid", "must be valid")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_400_BAD_REQUEST
        assert http_exception.detail["error_code"] == "DATA_VALIDATION_ERROR"
    
    def test_not_found_exception_conversion(self):
        """Test ResourceNotFoundException to HTTP conversion."""
        exception = ResourceNotFoundException("user", "123")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_404_NOT_FOUND
        assert http_exception.detail["error_code"] == "RESOURCE_NOT_FOUND"
    
    def test_duplicate_exception_conversion(self):
        """Test DuplicateResourceException to HTTP conversion."""
        exception = DuplicateResourceException("email", "test@example.com")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_409_CONFLICT
        assert http_exception.detail["error_code"] == "DUPLICATE_RESOURCE"
    
    def test_compliance_exception_conversion(self):
        """Test ComplianceException to HTTP conversion."""
        exception = AMLViolationException("customer123")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert http_exception.detail["error_code"] == "AML_VIOLATION"
    
    def test_rate_limit_exception_conversion(self):
        """Test RateLimitExceededException to HTTP conversion."""
        exception = RateLimitExceededException("api", 60)
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert http_exception.detail["error_code"] == "RATE_LIMIT_EXCEEDED"
    
    def test_system_exception_conversion(self):
        """Test SystemException to HTTP conversion."""
        exception = DatabaseException("SELECT", "Connection failed")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert http_exception.detail["error_code"] == "DATABASE_ERROR"
        # Details should be empty for 500 errors (security)
        assert http_exception.detail["details"] == {}
    
    def test_unknown_exception_conversion(self):
        """Test unknown exception type conversion."""
        exception = RegulensBaseException("Unknown error")
        http_exception = exception_to_http_exception(exception)
        
        assert http_exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert http_exception.detail["error_code"] == "RegulensBaseException"

class TestLogException:
    """Test exception logging functionality."""
    
    def test_log_exception_basic(self):
        """Test basic exception logging."""
        exception = RegulensBaseException("Test error")
        
        # This should not raise an exception
        log_exception(exception)
    
    def test_log_exception_with_context(self):
        """Test exception logging with context."""
        exception = RegulensBaseException("Test error")
        context = {"user_id": "123", "action": "test"}
        
        # This should not raise an exception
        log_exception(exception, context)
