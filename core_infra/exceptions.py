"""
Regulens AI - Exception Handling Framework
Enterprise-grade exception handling with comprehensive error categorization and logging.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
import structlog

# Initialize logging
logger = structlog.get_logger(__name__)

# ============================================================================
# BASE EXCEPTION CLASSES
# ============================================================================

class RegulensBaseException(Exception):
    """Base exception class for all Regulens AI exceptions."""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        user_message: str = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.utcnow()
        self.exception_id = str(uuid.uuid4())
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/response."""
        return {
            "exception_id": self.exception_id,
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }

# ============================================================================
# AUTHENTICATION & AUTHORIZATION EXCEPTIONS
# ============================================================================

class AuthenticationException(RegulensBaseException):
    """Authentication-related exceptions."""
    pass

class AuthorizationException(RegulensBaseException):
    """Authorization-related exceptions."""
    pass

class InvalidTokenException(AuthenticationException):
    """Invalid or expired token."""
    
    def __init__(self, message: str = "Invalid or expired token", **kwargs):
        super().__init__(
            message=message,
            error_code="INVALID_TOKEN",
            user_message="Your session has expired. Please log in again.",
            **kwargs
        )

class InsufficientPermissionsException(AuthorizationException):
    """User lacks required permissions."""
    
    def __init__(self, required_permission: str, **kwargs):
        super().__init__(
            message=f"Permission required: {required_permission}",
            error_code="INSUFFICIENT_PERMISSIONS",
            user_message="You don't have permission to perform this action.",
            details={"required_permission": required_permission},
            **kwargs
        )

class TenantAccessDeniedException(AuthorizationException):
    """Access denied to tenant resources."""
    
    def __init__(self, tenant_id: str = None, **kwargs):
        super().__init__(
            message="Access denied to tenant resources",
            error_code="TENANT_ACCESS_DENIED",
            user_message="You don't have access to this organization's data.",
            details={"tenant_id": tenant_id} if tenant_id else {},
            **kwargs
        )

# ============================================================================
# COMPLIANCE & REGULATORY EXCEPTIONS
# ============================================================================

class ComplianceException(RegulensBaseException):
    """Base class for compliance-related exceptions."""
    pass

class RegulatoryViolationException(ComplianceException):
    """Regulatory compliance violation detected."""
    
    def __init__(self, regulation: str, violation_details: Dict[str, Any], **kwargs):
        super().__init__(
            message=f"Regulatory violation detected: {regulation}",
            error_code="REGULATORY_VIOLATION",
            user_message="This action violates regulatory requirements.",
            details={
                "regulation": regulation,
                "violation_details": violation_details
            },
            **kwargs
        )

class AMLViolationException(ComplianceException):
    """Anti-Money Laundering violation."""
    
    def __init__(self, customer_id: str, transaction_id: str = None, **kwargs):
        super().__init__(
            message="AML violation detected",
            error_code="AML_VIOLATION",
            user_message="This transaction requires additional review for AML compliance.",
            details={
                "customer_id": customer_id,
                "transaction_id": transaction_id
            },
            **kwargs
        )

class KYCViolationException(ComplianceException):
    """Know Your Customer violation."""
    
    def __init__(self, customer_id: str, missing_documents: List[str] = None, **kwargs):
        super().__init__(
            message="KYC requirements not met",
            error_code="KYC_VIOLATION",
            user_message="Customer verification is incomplete.",
            details={
                "customer_id": customer_id,
                "missing_documents": missing_documents or []
            },
            **kwargs
        )

class SanctionsViolationException(ComplianceException):
    """Sanctions screening violation."""
    
    def __init__(self, entity_name: str, sanctions_list: str, **kwargs):
        super().__init__(
            message=f"Sanctions violation: {entity_name} found on {sanctions_list}",
            error_code="SANCTIONS_VIOLATION",
            user_message="This entity is on a sanctions list and cannot be processed.",
            details={
                "entity_name": entity_name,
                "sanctions_list": sanctions_list
            },
            **kwargs
        )

# ============================================================================
# DATA & VALIDATION EXCEPTIONS
# ============================================================================

class DataValidationException(RegulensBaseException):
    """Data validation errors."""
    
    def __init__(self, field: str, value: Any, validation_rule: str, **kwargs):
        super().__init__(
            message=f"Validation failed for field '{field}': {validation_rule}",
            error_code="DATA_VALIDATION_ERROR",
            user_message=f"Invalid value for {field}.",
            details={
                "field": field,
                "value": str(value),
                "validation_rule": validation_rule
            },
            **kwargs
        )

class DataIntegrityException(RegulensBaseException):
    """Data integrity violations."""
    
    def __init__(self, table: str, constraint: str, **kwargs):
        super().__init__(
            message=f"Data integrity violation in {table}: {constraint}",
            error_code="DATA_INTEGRITY_ERROR",
            user_message="Data integrity constraint violated.",
            details={
                "table": table,
                "constraint": constraint
            },
            **kwargs
        )

class DuplicateResourceException(RegulensBaseException):
    """Resource already exists."""
    
    def __init__(self, resource_type: str, identifier: str, **kwargs):
        super().__init__(
            message=f"Duplicate {resource_type}: {identifier}",
            error_code="DUPLICATE_RESOURCE",
            user_message=f"A {resource_type} with this identifier already exists.",
            details={
                "resource_type": resource_type,
                "identifier": identifier
            },
            **kwargs
        )

class ResourceNotFoundException(RegulensBaseException):
    """Resource not found."""
    
    def __init__(self, resource_type: str, identifier: str, **kwargs):
        super().__init__(
            message=f"{resource_type} not found: {identifier}",
            error_code="RESOURCE_NOT_FOUND",
            user_message=f"The requested {resource_type} was not found.",
            details={
                "resource_type": resource_type,
                "identifier": identifier
            },
            **kwargs
        )

# ============================================================================
# BUSINESS LOGIC EXCEPTIONS
# ============================================================================

class BusinessLogicException(RegulensBaseException):
    """Business logic violations."""
    pass

class WorkflowException(BusinessLogicException):
    """Workflow execution errors."""
    
    def __init__(self, workflow_id: str, step: str, reason: str, **kwargs):
        super().__init__(
            message=f"Workflow {workflow_id} failed at step {step}: {reason}",
            error_code="WORKFLOW_ERROR",
            user_message="Workflow execution failed.",
            details={
                "workflow_id": workflow_id,
                "step": step,
                "reason": reason
            },
            **kwargs
        )

class ConfigurationException(BusinessLogicException):
    """Configuration errors."""
    
    def __init__(self, config_key: str, issue: str, **kwargs):
        super().__init__(
            message=f"Configuration error for {config_key}: {issue}",
            error_code="CONFIGURATION_ERROR",
            user_message="System configuration error.",
            details={
                "config_key": config_key,
                "issue": issue
            },
            **kwargs
        )

# ============================================================================
# EXTERNAL SERVICE EXCEPTIONS
# ============================================================================

class ExternalServiceException(RegulensBaseException):
    """External service integration errors."""
    
    def __init__(self, service_name: str, operation: str, error_details: str, **kwargs):
        super().__init__(
            message=f"External service error - {service_name}.{operation}: {error_details}",
            error_code="EXTERNAL_SERVICE_ERROR",
            user_message="External service is temporarily unavailable.",
            details={
                "service_name": service_name,
                "operation": operation,
                "error_details": error_details
            },
            **kwargs
        )

class RateLimitExceededException(ExternalServiceException):
    """Rate limit exceeded for external service."""
    
    def __init__(self, service_name: str, retry_after: int = None, **kwargs):
        super().__init__(
            service_name=service_name,
            operation="rate_limit",
            error_details=f"Rate limit exceeded, retry after {retry_after} seconds" if retry_after else "Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            user_message="Too many requests. Please try again later.",
            details={"retry_after": retry_after} if retry_after else {},
            **kwargs
        )

# ============================================================================
# SYSTEM EXCEPTIONS
# ============================================================================

class SystemException(RegulensBaseException):
    """System-level errors."""
    pass

class DatabaseException(SystemException):
    """Database operation errors."""
    
    def __init__(self, operation: str, error_details: str, **kwargs):
        super().__init__(
            message=f"Database error during {operation}: {error_details}",
            error_code="DATABASE_ERROR",
            user_message="Database operation failed.",
            details={
                "operation": operation,
                "error_details": error_details
            },
            **kwargs
        )

class CacheException(SystemException):
    """Cache operation errors."""
    
    def __init__(self, operation: str, key: str, error_details: str, **kwargs):
        super().__init__(
            message=f"Cache error during {operation} for key {key}: {error_details}",
            error_code="CACHE_ERROR",
            user_message="Cache operation failed.",
            details={
                "operation": operation,
                "key": key,
                "error_details": error_details
            },
            **kwargs
        )

# ============================================================================
# EXCEPTION UTILITIES
# ============================================================================

def log_exception(exception: RegulensBaseException, context: Dict[str, Any] = None):
    """Log exception with full context."""
    log_data = exception.to_dict()
    if context:
        log_data["context"] = context
    
    logger.error(
        f"Exception occurred: {exception.error_code}",
        **log_data
    )

def exception_to_http_exception(exception: RegulensBaseException) -> HTTPException:
    """Convert Regulens exception to FastAPI HTTPException."""
    
    # Map exception types to HTTP status codes
    status_code_map = {
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        InvalidTokenException: status.HTTP_401_UNAUTHORIZED,
        AuthorizationException: status.HTTP_403_FORBIDDEN,
        InsufficientPermissionsException: status.HTTP_403_FORBIDDEN,
        TenantAccessDeniedException: status.HTTP_403_FORBIDDEN,
        DataValidationException: status.HTTP_400_BAD_REQUEST,
        DuplicateResourceException: status.HTTP_409_CONFLICT,
        ResourceNotFoundException: status.HTTP_404_NOT_FOUND,
        RateLimitExceededException: status.HTTP_429_TOO_MANY_REQUESTS,
        ComplianceException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        RegulatoryViolationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AMLViolationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        KYCViolationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        SanctionsViolationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        BusinessLogicException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ExternalServiceException: status.HTTP_503_SERVICE_UNAVAILABLE,
        SystemException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    # Find the most specific status code
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    for exception_type, code in status_code_map.items():
        if isinstance(exception, exception_type):
            status_code = code
            break
    
    # Log the exception
    log_exception(exception)
    
    # Create HTTP exception
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": exception.error_code,
            "message": exception.user_message,
            "exception_id": exception.exception_id,
            "details": exception.details if status_code != status.HTTP_500_INTERNAL_SERVER_ERROR else {}
        }
    )
