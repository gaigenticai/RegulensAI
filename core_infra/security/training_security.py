"""
Training Portal Security Service
Comprehensive security measures for training portal including data protection,
access control, audit logging, and threat detection.
"""

import hashlib
import hmac
import secrets
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import wraps
from ipaddress import ip_address, ip_network
import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from core_infra.database.models import User, TrainingModule, TrainingEnrollment
from core_infra.config import settings
from core_infra.utils.audit_logger import AuditLogger

logger = structlog.get_logger(__name__)


class TrainingSecurityService:
    """Comprehensive security service for training portal."""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Security policies
        self.password_policy = {
            'min_length': 12,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special': True,
            'max_age_days': 90,
            'history_count': 5
        }
        
        # Rate limiting thresholds
        self.rate_limits = {
            'login_attempts': {'count': 5, 'window': 900},  # 5 attempts per 15 minutes
            'api_requests': {'count': 1000, 'window': 3600},  # 1000 requests per hour
            'assessment_submissions': {'count': 3, 'window': 3600},  # 3 submissions per hour
            'certificate_downloads': {'count': 10, 'window': 3600}  # 10 downloads per hour
        }
        
        # Threat detection patterns
        self.threat_patterns = {
            'sql_injection': [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
                r"(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)",
                r"(--|#|/\*|\*/)",
                r"(\b(EXEC|EXECUTE)\b)"
            ],
            'xss_injection': [
                r"(<script[^>]*>.*?</script>)",
                r"(javascript:)",
                r"(on\w+\s*=)",
                r"(<iframe[^>]*>)"
            ],
            'path_traversal': [
                r"(\.\./)",
                r"(\.\.\\)",
                r"(%2e%2e%2f)",
                r"(%2e%2e\\)"
            ]
        }
        
        # Allowed IP ranges (can be configured)
        self.allowed_ip_ranges = [
            ip_network("10.0.0.0/8"),
            ip_network("172.16.0.0/12"),
            ip_network("192.168.0.0/16")
        ]
    
    def _get_encryption_key(self) -> bytes:
        """Generate or retrieve encryption key for sensitive data."""
        try:
            # In production, this should come from a secure key management service
            password = settings.SECRET_KEY.encode()
            salt = b'training_portal_salt'  # Should be unique per installation
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
            
        except Exception as e:
            logger.error("Failed to generate encryption key", error=str(e))
            # Fallback to a default key (not recommended for production)
            return Fernet.generate_key()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like PII or assessment answers."""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Failed to encrypt data", error=str(e))
            return data  # Return original data if encryption fails
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Failed to decrypt data", error=str(e))
            return encrypted_data  # Return encrypted data if decryption fails
    
    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against security policy."""
        errors = []
        
        if len(password) < self.password_policy['min_length']:
            errors.append(f"Password must be at least {self.password_policy['min_length']} characters long")
        
        if self.password_policy['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.password_policy['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.password_policy['require_numbers'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if self.password_policy['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common patterns
        if re.search(r'(.)\1{2,}', password):
            errors.append("Password cannot contain repeated characters")
        
        if re.search(r'(123|abc|qwe|password|admin)', password.lower()):
            errors.append("Password cannot contain common patterns")
        
        return len(errors) == 0, errors
    
    def detect_threats(self, input_data: str, context: str = "general") -> Dict[str, Any]:
        """Detect potential security threats in input data."""
        threats_detected = []
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    threats_detected.append({
                        'type': threat_type,
                        'pattern': pattern,
                        'context': context,
                        'severity': self._get_threat_severity(threat_type)
                    })
        
        return {
            'threats_detected': threats_detected,
            'is_safe': len(threats_detected) == 0,
            'risk_score': self._calculate_risk_score(threats_detected)
        }
    
    def _get_threat_severity(self, threat_type: str) -> str:
        """Get severity level for threat type."""
        severity_map = {
            'sql_injection': 'critical',
            'xss_injection': 'high',
            'path_traversal': 'high',
            'command_injection': 'critical'
        }
        return severity_map.get(threat_type, 'medium')
    
    def _calculate_risk_score(self, threats: List[Dict[str, Any]]) -> int:
        """Calculate overall risk score based on detected threats."""
        if not threats:
            return 0
        
        severity_scores = {
            'low': 1,
            'medium': 3,
            'high': 7,
            'critical': 10
        }
        
        total_score = sum(severity_scores.get(threat['severity'], 1) for threat in threats)
        return min(total_score, 10)  # Cap at 10
    
    def validate_ip_access(self, ip_address_str: str) -> bool:
        """Validate if IP address is allowed to access training portal."""
        try:
            client_ip = ip_address(ip_address_str)
            
            # Check against allowed IP ranges
            for allowed_range in self.allowed_ip_ranges:
                if client_ip in allowed_range:
                    return True
            
            # Log unauthorized access attempt
            logger.warning("Unauthorized IP access attempt", ip_address=ip_address_str)
            return False
            
        except Exception as e:
            logger.error("Failed to validate IP access", ip_address=ip_address_str, error=str(e))
            return False
    
    def sanitize_input(self, input_data: str, context: str = "general") -> str:
        """Sanitize input data to prevent injection attacks."""
        try:
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\']', '', input_data)
            
            # Escape SQL special characters
            sanitized = sanitized.replace("'", "''")
            sanitized = sanitized.replace(";", "")
            sanitized = sanitized.replace("--", "")
            
            # Remove script tags and javascript
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            
            # Limit length based on context
            max_lengths = {
                'title': 200,
                'description': 1000,
                'notes': 500,
                'general': 255
            }
            max_length = max_lengths.get(context, 255)
            sanitized = sanitized[:max_length]
            
            return sanitized.strip()
            
        except Exception as e:
            logger.error("Failed to sanitize input", error=str(e))
            return ""
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    def verify_data_integrity(self, data: str, signature: str, secret_key: str) -> bool:
        """Verify data integrity using HMAC signature."""
        try:
            expected_signature = hmac.new(
                secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error("Failed to verify data integrity", error=str(e))
            return False
    
    def create_data_signature(self, data: str, secret_key: str) -> str:
        """Create HMAC signature for data integrity."""
        try:
            signature = hmac.new(
                secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error("Failed to create data signature", error=str(e))
            return ""
    
    async def audit_training_access(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        details: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """Audit training portal access and actions."""
        try:
            audit_data = {
                'user_id': user_id,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'details': details or {},
                'ip_address': ip_address,
                'user_agent': user_agent,
                'timestamp': datetime.utcnow(),
                'session_id': self.generate_secure_token(16)
            }
            
            await self.audit_logger.log_event(
                event_type='training_access',
                event_data=audit_data,
                severity='info'
            )
            
        except Exception as e:
            logger.error("Failed to audit training access", error=str(e))
    
    def check_content_security(self, content: str, content_type: str = "text") -> Dict[str, Any]:
        """Check content for security issues before storing."""
        security_check = {
            'is_safe': True,
            'issues': [],
            'sanitized_content': content
        }
        
        try:
            # Check for malicious content
            threat_analysis = self.detect_threats(content, content_type)
            
            if not threat_analysis['is_safe']:
                security_check['is_safe'] = False
                security_check['issues'].extend([
                    f"{threat['type']}: {threat['pattern']}" 
                    for threat in threat_analysis['threats_detected']
                ])
            
            # Sanitize content
            security_check['sanitized_content'] = self.sanitize_input(content, content_type)
            
            # Check for suspicious file uploads (if content contains file references)
            if 'file://' in content or 'data:' in content:
                security_check['issues'].append("Suspicious file references detected")
                security_check['is_safe'] = False
            
            return security_check
            
        except Exception as e:
            logger.error("Failed to check content security", error=str(e))
            return {
                'is_safe': False,
                'issues': ['Security check failed'],
                'sanitized_content': ''
            }
    
    def validate_training_access_permissions(
        self,
        user: User,
        module: TrainingModule,
        action: str
    ) -> Tuple[bool, str]:
        """Validate user permissions for training module access."""
        try:
            # Check if user is active
            if not user.is_active:
                return False, "User account is inactive"
            
            # Check tenant isolation
            if str(user.tenant_id) != str(module.tenant_id):
                return False, "Access denied: tenant mismatch"
            
            # Check module availability
            if not module.is_active:
                return False, "Training module is not available"
            
            # Check role-based permissions
            user_role = user.role.lower()
            
            permission_matrix = {
                'view': ['user', 'compliance_officer', 'training_manager', 'admin'],
                'enroll': ['user', 'compliance_officer', 'training_manager', 'admin'],
                'modify': ['training_manager', 'admin'],
                'delete': ['admin']
            }
            
            allowed_roles = permission_matrix.get(action, [])
            if user_role not in allowed_roles:
                return False, f"Insufficient permissions for action: {action}"
            
            return True, "Access granted"
            
        except Exception as e:
            logger.error("Failed to validate training access permissions", error=str(e))
            return False, "Permission validation failed"


def secure_training_endpoint(
    require_encryption: bool = False,
    audit_action: str = None,
    check_ip_whitelist: bool = False
):
    """Decorator for securing training portal endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request context (this would need to be adapted based on your framework)
            # For FastAPI, you'd get this from the request object
            
            security_service = TrainingSecurityService()
            
            try:
                # IP whitelist check
                if check_ip_whitelist:
                    from starlette.requests import Request
                    request = kwargs.get('request')
                    if request and isinstance(request, Request):
                        client_ip = request.client.host if request.client else None
                        if client_ip and not await security_service.validate_ip_access(client_ip):
                            from fastapi import HTTPException
                            raise HTTPException(status_code=403, detail="IP address not allowed")
                
                # Execute the original function
                result = await func(*args, **kwargs)
                
                # Audit the action if specified
                if audit_action:
                    # Try to get user_id from various sources
                    user_id = None
                    
                    # Check if user_id is in kwargs (common pattern)
                    if 'user_id' in kwargs:
                        user_id = kwargs['user_id']
                    # Check if there's a current_user object
                    elif 'current_user' in kwargs and hasattr(kwargs['current_user'], 'id'):
                        user_id = kwargs['current_user'].id
                    # Check if there's a request with user info
                    elif 'request' in kwargs and hasattr(kwargs['request'], 'state'):
                        user_id = getattr(kwargs['request'].state, 'user_id', None)
                    
                    if user_id:
                        await security_service.audit_training_access(
                            user_id=user_id,
                            action=audit_action,
                            resource_type='training_endpoint',
                            details={'endpoint': func.__name__}
                        )
                
                return result
                
            except Exception as e:
                logger.error("Security check failed", endpoint=func.__name__, error=str(e))
                raise
                
        return wrapper
    return decorator


class TrainingDataProtectionService:
    """GDPR/CCPA compliant data protection for training portal."""

    def __init__(self):
        self.security_service = TrainingSecurityService()
        self.data_retention_policies = {
            'training_progress': timedelta(days=2555),  # 7 years
            'assessment_results': timedelta(days=2555),  # 7 years
            'certificates': timedelta(days=3650),  # 10 years
            'analytics_data': timedelta(days=730),  # 2 years
            'audit_logs': timedelta(days=2555),  # 7 years
            'user_sessions': timedelta(days=30)  # 30 days
        }

    def classify_data_sensitivity(self, data_type: str, content: Any) -> str:
        """Classify data sensitivity level for proper handling."""
        sensitivity_map = {
            'user_pii': 'highly_sensitive',
            'assessment_answers': 'sensitive',
            'training_progress': 'internal',
            'module_content': 'internal',
            'analytics_data': 'internal',
            'certificates': 'sensitive',
            'audit_logs': 'sensitive'
        }

        return sensitivity_map.get(data_type, 'internal')

    def anonymize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize user data for analytics while preserving utility."""
        anonymized = user_data.copy()

        # Replace identifiable information with hashed versions
        if 'email' in anonymized:
            anonymized['email_hash'] = hashlib.sha256(
                anonymized['email'].encode()
            ).hexdigest()[:16]
            del anonymized['email']

        if 'name' in anonymized:
            del anonymized['name']

        if 'user_id' in anonymized:
            anonymized['user_hash'] = hashlib.sha256(
                str(anonymized['user_id']).encode()
            ).hexdigest()[:16]
            del anonymized['user_id']

        # Keep non-identifying information
        keep_fields = [
            'role', 'department', 'training_completion_rate',
            'last_login_date', 'account_created_date'
        ]

        return {k: v for k, v in anonymized.items() if k in keep_fields}

    async def handle_data_deletion_request(
        self,
        user_id: str,
        deletion_type: str = "full"
    ) -> Dict[str, Any]:
        """Handle user data deletion requests (GDPR Right to be Forgotten)."""
        try:
            deletion_report = {
                'user_id': user_id,
                'deletion_type': deletion_type,
                'timestamp': datetime.utcnow(),
                'deleted_records': {},
                'retained_records': {},
                'errors': []
            }

            if deletion_type == "full":
                # Delete all user data except legally required records
                tables_to_clean = [
                    'training_enrollments',
                    'training_section_progress',
                    'training_bookmarks',
                    'training_discussions',
                    'training_analytics'
                ]
            else:
                # Partial deletion - only non-essential data
                tables_to_clean = [
                    'training_bookmarks',
                    'training_analytics'
                ]

            # Note: Actual deletion would be implemented here
            # This is a placeholder for the deletion logic

            return deletion_report

        except Exception as e:
            logger.error("Failed to handle data deletion request", user_id=user_id, error=str(e))
            return {"error": "Data deletion failed"}


# Global security service instances
training_security_service = TrainingSecurityService()
training_data_protection_service = TrainingDataProtectionService()
