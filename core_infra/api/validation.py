"""
Regulens AI - Input Validation Framework
Enterprise-grade input validation with comprehensive security measures.
"""

import re
import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Type
from decimal import Decimal, InvalidOperation
from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, Field, validator, root_validator
from fastapi import HTTPException, status
import structlog

from core_infra.exceptions import DataValidationException

# Initialize logging
logger = structlog.get_logger(__name__)

# Security patterns
SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()+=\[\]{}|;:\'\"<>/\\]*$')
SQL_INJECTION_PATTERNS = [
    r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)',
    r'(--|#|/\*|\*/)',
    r'(\bOR\b.*=.*\bOR\b)',
    r'(\bAND\b.*=.*\bAND\b)',
    r'(\'.*\'|\".*\")',
    r'(\bxp_cmdshell\b|\bsp_executesql\b)'
]
XSS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'<iframe[^>]*>.*?</iframe>',
    r'<object[^>]*>.*?</object>',
    r'<embed[^>]*>.*?</embed>'
]

# File type validation
ALLOWED_DOCUMENT_TYPES = {
    'pdf': ['application/pdf'],
    'image': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp'],
    'document': ['application/pdf', 'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain'],
    'spreadsheet': ['application/vnd.ms-excel',
                   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                   'text/csv']
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_STRING_LENGTH = 10000
MAX_ARRAY_LENGTH = 1000

class ValidationError(Exception):
    """Custom validation error."""
    pass

class SecurityValidator:
    """Security-focused input validation utilities."""
    
    @staticmethod
    def validate_string_safety(value: str, field_name: str = "field") -> str:
        """Validate string for security threats."""
        if not isinstance(value, str):
            raise DataValidationException(field_name, value, "must be a string")
        
        if len(value) > MAX_STRING_LENGTH:
            raise DataValidationException(
                field_name, len(value), 
                f"exceeds maximum length of {MAX_STRING_LENGTH}"
            )
        
        # Check for SQL injection patterns
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected in {field_name}: {pattern}")
                raise DataValidationException(
                    field_name, "[REDACTED]", 
                    "contains potentially malicious content"
                )
        
        # Check for XSS patterns
        for pattern in XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS attempt detected in {field_name}: {pattern}")
                raise DataValidationException(
                    field_name, "[REDACTED]", 
                    "contains potentially malicious content"
                )
        
        # Check for safe characters only
        if not SAFE_STRING_PATTERN.match(value):
            raise DataValidationException(
                field_name, "[REDACTED]", 
                "contains invalid characters"
            )
        
        return value.strip()
    
    @staticmethod
    def validate_email_address(email: str, field_name: str = "email") -> str:
        """Validate email address format and security."""
        try:
            # Basic string safety check
            email = SecurityValidator.validate_string_safety(email, field_name)
            
            # Email format validation
            validated_email = validate_email(email)
            normalized_email = validated_email.email
            
            # Additional security checks
            if len(normalized_email) > 254:  # RFC 5321 limit
                raise DataValidationException(
                    field_name, len(normalized_email),
                    "email address too long"
                )
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'\.{2,}',  # Multiple consecutive dots
                r'^\.|\.$',  # Starting or ending with dot
                r'@.*@',  # Multiple @ symbols
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, normalized_email):
                    raise DataValidationException(
                        field_name, "[REDACTED]",
                        "invalid email format"
                    )
            
            return normalized_email
            
        except EmailNotValidError as e:
            raise DataValidationException(field_name, "[REDACTED]", str(e))
    
    @staticmethod
    def validate_uuid(value: Union[str, uuid.UUID], field_name: str = "id") -> str:
        """Validate UUID format."""
        try:
            if isinstance(value, str):
                # Basic string safety check
                value = SecurityValidator.validate_string_safety(value, field_name)
                uuid_obj = uuid.UUID(value)
            elif isinstance(value, uuid.UUID):
                uuid_obj = value
            else:
                raise DataValidationException(
                    field_name, type(value).__name__,
                    "must be a valid UUID string or UUID object"
                )
            
            return str(uuid_obj)
            
        except ValueError as e:
            raise DataValidationException(field_name, "[REDACTED]", "invalid UUID format")
    
    @staticmethod
    def validate_numeric(value: Union[int, float, str], field_name: str = "number",
                        min_value: Optional[float] = None, 
                        max_value: Optional[float] = None) -> Union[int, float]:
        """Validate numeric input with range checking."""
        try:
            if isinstance(value, str):
                # Basic string safety check
                value = SecurityValidator.validate_string_safety(value, field_name)
                
                # Try to convert to number
                if '.' in value:
                    numeric_value = float(value)
                else:
                    numeric_value = int(value)
            elif isinstance(value, (int, float)):
                numeric_value = value
            else:
                raise DataValidationException(
                    field_name, type(value).__name__,
                    "must be a number"
                )
            
            # Range validation
            if min_value is not None and numeric_value < min_value:
                raise DataValidationException(
                    field_name, numeric_value,
                    f"must be at least {min_value}"
                )
            
            if max_value is not None and numeric_value > max_value:
                raise DataValidationException(
                    field_name, numeric_value,
                    f"must be at most {max_value}"
                )
            
            return numeric_value
            
        except (ValueError, InvalidOperation) as e:
            raise DataValidationException(field_name, "[REDACTED]", "invalid number format")
    
    @staticmethod
    def validate_decimal_amount(value: Union[str, float, Decimal], 
                              field_name: str = "amount") -> Decimal:
        """Validate monetary amounts with precision."""
        try:
            if isinstance(value, str):
                value = SecurityValidator.validate_string_safety(value, field_name)
                decimal_value = Decimal(value)
            elif isinstance(value, (int, float)):
                decimal_value = Decimal(str(value))
            elif isinstance(value, Decimal):
                decimal_value = value
            else:
                raise DataValidationException(
                    field_name, type(value).__name__,
                    "must be a valid decimal amount"
                )
            
            # Check for reasonable precision (2 decimal places for currency)
            if decimal_value.as_tuple().exponent < -2:
                raise DataValidationException(
                    field_name, str(decimal_value),
                    "too many decimal places (maximum 2)"
                )
            
            # Check for reasonable range
            if decimal_value < 0:
                raise DataValidationException(
                    field_name, str(decimal_value),
                    "amount cannot be negative"
                )
            
            if decimal_value > Decimal('999999999.99'):
                raise DataValidationException(
                    field_name, str(decimal_value),
                    "amount exceeds maximum allowed value"
                )
            
            return decimal_value
            
        except (ValueError, InvalidOperation) as e:
            raise DataValidationException(field_name, "[REDACTED]", "invalid decimal format")
    
    @staticmethod
    def validate_date(value: Union[str, datetime, date], 
                     field_name: str = "date") -> datetime:
        """Validate date input."""
        try:
            if isinstance(value, str):
                value = SecurityValidator.validate_string_safety(value, field_name)
                
                # Try common date formats
                date_formats = [
                    '%Y-%m-%d',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S.%fZ'
                ]
                
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_date is None:
                    raise ValueError("No matching date format")
                
                return parsed_date
                
            elif isinstance(value, datetime):
                return value
            elif isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            else:
                raise DataValidationException(
                    field_name, type(value).__name__,
                    "must be a valid date"
                )
                
        except ValueError as e:
            raise DataValidationException(field_name, "[REDACTED]", "invalid date format")
    
    @staticmethod
    def validate_array(value: List[Any], field_name: str = "array",
                      max_length: int = MAX_ARRAY_LENGTH) -> List[Any]:
        """Validate array input."""
        if not isinstance(value, list):
            raise DataValidationException(
                field_name, type(value).__name__,
                "must be an array"
            )
        
        if len(value) > max_length:
            raise DataValidationException(
                field_name, len(value),
                f"array too long (maximum {max_length} items)"
            )
        
        return value
    
    @staticmethod
    def validate_country_code(value: str, field_name: str = "country") -> str:
        """Validate ISO 3166-1 alpha-2 country code."""
        value = SecurityValidator.validate_string_safety(value, field_name)
        
        if len(value) != 2:
            raise DataValidationException(
                field_name, value,
                "must be a 2-character ISO country code"
            )
        
        if not value.isalpha():
            raise DataValidationException(
                field_name, value,
                "must contain only letters"
            )
        
        return value.upper()
    
    @staticmethod
    def validate_currency_code(value: str, field_name: str = "currency") -> str:
        """Validate ISO 4217 currency code."""
        value = SecurityValidator.validate_string_safety(value, field_name)
        
        if len(value) != 3:
            raise DataValidationException(
                field_name, value,
                "must be a 3-character ISO currency code"
            )
        
        if not value.isalpha():
            raise DataValidationException(
                field_name, value,
                "must contain only letters"
            )
        
        return value.upper()

class FileValidator:
    """File upload validation utilities."""
    
    @staticmethod
    def validate_file_type(filename: str, content_type: str, 
                          allowed_types: List[str]) -> bool:
        """Validate file type based on extension and MIME type."""
        if not filename or not content_type:
            raise DataValidationException("file", filename, "filename and content type required")
        
        # Get file extension
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Check if content type is allowed
        allowed_mime_types = []
        for file_type in allowed_types:
            if file_type in ALLOWED_DOCUMENT_TYPES:
                allowed_mime_types.extend(ALLOWED_DOCUMENT_TYPES[file_type])
        
        if content_type not in allowed_mime_types:
            raise DataValidationException(
                "file", content_type,
                f"file type not allowed. Allowed types: {allowed_types}"
            )
        
        return True
    
    @staticmethod
    def validate_file_size(file_size: int, max_size: int = MAX_FILE_SIZE) -> bool:
        """Validate file size."""
        if file_size > max_size:
            raise DataValidationException(
                "file", f"{file_size} bytes",
                f"file too large (maximum {max_size} bytes)"
            )
        
        return True
    
    @staticmethod
    def validate_filename(filename: str) -> str:
        """Validate and sanitize filename."""
        if not filename:
            raise DataValidationException("filename", filename, "filename required")
        
        # Remove path traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Validate safe characters
        safe_filename_pattern = re.compile(r'^[a-zA-Z0-9\-_. ]+$')
        if not safe_filename_pattern.match(filename):
            raise DataValidationException(
                "filename", "[REDACTED]",
                "filename contains invalid characters"
            )
        
        if len(filename) > 255:
            raise DataValidationException(
                "filename", len(filename),
                "filename too long (maximum 255 characters)"
            )
        
        return filename.strip()
