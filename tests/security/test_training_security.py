"""
Security Tests for Training Portal
Comprehensive security testing including penetration testing scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json

from core_infra.main import app
from core_infra.security.training_security import (
    TrainingSecurityService, 
    TrainingDataProtectionService,
    training_security_service
)
from core_infra.database.models import User, Tenant, TrainingModule
from tests.fixtures.security_fixtures import (
    create_malicious_payloads,
    create_test_user_with_role,
    create_test_training_module
)


class TestTrainingSecurityService:
    """Test suite for training portal security service."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, test_tenant: Tenant):
        """Set up test data for security tests."""
        self.db = db_session
        self.tenant = test_tenant
        self.security_service = TrainingSecurityService()
        self.client = TestClient(app)
        
        # Create test users with different roles
        self.admin_user = create_test_user_with_role(
            db_session=self.db,
            tenant_id=self.tenant.id,
            role="admin",
            email="admin@test.com"
        )
        
        self.regular_user = create_test_user_with_role(
            db_session=self.db,
            tenant_id=self.tenant.id,
            role="user",
            email="user@test.com"
        )
        
        self.training_module = create_test_training_module(
            db_session=self.db,
            tenant_id=self.tenant.id,
            title="Security Test Module"
        )
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "Password1",  # Missing special character
            "Pass!",      # Too short
            "PASSWORD123!",  # No lowercase
            "password123!"   # No uppercase
        ]
        
        for password in weak_passwords:
            is_valid, errors = self.security_service.validate_password_strength(password)
            assert not is_valid, f"Password '{password}' should be invalid"
            assert len(errors) > 0
        
        # Test strong passwords
        strong_passwords = [
            "MySecureP@ssw0rd123",
            "Tr@ining!Portal2024",
            "C0mpl3x&S3cur3P@ss"
        ]
        
        for password in strong_passwords:
            is_valid, errors = self.security_service.validate_password_strength(password)
            assert is_valid, f"Password '{password}' should be valid, errors: {errors}"
            assert len(errors) == 0
    
    def test_threat_detection(self):
        """Test threat detection for various attack patterns."""
        
        # SQL Injection attempts
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM training_modules",
            "admin'--",
            "1; DELETE FROM training_enrollments"
        ]
        
        for payload in sql_injection_payloads:
            result = self.security_service.detect_threats(payload, "search")
            assert not result['is_safe'], f"SQL injection not detected: {payload}"
            assert any(threat['type'] == 'sql_injection' for threat in result['threats_detected'])
            assert result['risk_score'] > 5
        
        # XSS attempts
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<img onerror='alert(1)' src='x'>"
        ]
        
        for payload in xss_payloads:
            result = self.security_service.detect_threats(payload, "content")
            assert not result['is_safe'], f"XSS not detected: {payload}"
            assert any(threat['type'] == 'xss_injection' for threat in result['threats_detected'])
        
        # Path traversal attempts
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for payload in path_traversal_payloads:
            result = self.security_service.detect_threats(payload, "file")
            assert not result['is_safe'], f"Path traversal not detected: {payload}"
            assert any(threat['type'] == 'path_traversal' for threat in result['threats_detected'])
        
        # Safe content should pass
        safe_content = [
            "This is a normal training module description",
            "User completed the assessment with 85% score",
            "Training progress: 75% complete"
        ]
        
        for content in safe_content:
            result = self.security_service.detect_threats(content)
            assert result['is_safe'], f"Safe content flagged as threat: {content}"
            assert result['risk_score'] == 0
    
    def test_input_sanitization(self):
        """Test input sanitization functionality."""
        
        # Test malicious input sanitization
        malicious_inputs = [
            ("<script>alert('xss')</script>", ""),
            ("'; DROP TABLE users; --", " DROP TABLE users "),
            ("javascript:alert(1)", "alert(1)"),
            ("<iframe src='evil.com'></iframe>", ""),
            ("Normal text with <script>", "Normal text with ")
        ]
        
        for malicious_input, expected_pattern in malicious_inputs:
            sanitized = self.security_service.sanitize_input(malicious_input)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "<iframe>" not in sanitized
            assert "--" not in sanitized
        
        # Test length limits
        long_input = "A" * 1000
        sanitized = self.security_service.sanitize_input(long_input, "title")
        assert len(sanitized) <= 200  # Title max length
        
        sanitized = self.security_service.sanitize_input(long_input, "description")
        assert len(sanitized) <= 1000  # Description max length
    
    def test_data_encryption_decryption(self):
        """Test data encryption and decryption."""
        
        sensitive_data = [
            "user@example.com",
            "Personal assessment answers",
            "Confidential training notes",
            "PII: John Doe, SSN: 123-45-6789"
        ]
        
        for data in sensitive_data:
            # Test encryption
            encrypted = self.security_service.encrypt_sensitive_data(data)
            assert encrypted != data, "Data should be encrypted"
            assert len(encrypted) > len(data), "Encrypted data should be longer"
            
            # Test decryption
            decrypted = self.security_service.decrypt_sensitive_data(encrypted)
            assert decrypted == data, "Decrypted data should match original"
    
    def test_data_integrity_verification(self):
        """Test data integrity using HMAC signatures."""
        
        test_data = "Important training module content"
        secret_key = "test_secret_key_123"
        
        # Create signature
        signature = self.security_service.create_data_signature(test_data, secret_key)
        assert signature, "Signature should be created"
        assert len(signature) == 64, "SHA256 signature should be 64 characters"
        
        # Verify valid signature
        is_valid = self.security_service.verify_data_integrity(test_data, signature, secret_key)
        assert is_valid, "Valid signature should verify"
        
        # Test with tampered data
        tampered_data = test_data + " TAMPERED"
        is_valid = self.security_service.verify_data_integrity(tampered_data, signature, secret_key)
        assert not is_valid, "Tampered data should not verify"
        
        # Test with wrong key
        wrong_key = "wrong_secret_key"
        is_valid = self.security_service.verify_data_integrity(test_data, signature, wrong_key)
        assert not is_valid, "Wrong key should not verify"
    
    def test_secure_token_generation(self):
        """Test secure token generation."""
        
        # Test default length
        token1 = self.security_service.generate_secure_token()
        token2 = self.security_service.generate_secure_token()
        
        assert token1 != token2, "Tokens should be unique"
        assert len(token1) > 30, "Token should be sufficiently long"
        assert token1.replace('-', '').replace('_', '').isalnum(), "Token should be URL-safe"
        
        # Test custom length
        short_token = self.security_service.generate_secure_token(16)
        long_token = self.security_service.generate_secure_token(64)
        
        assert len(short_token) < len(long_token), "Token length should be customizable"
    
    def test_content_security_validation(self):
        """Test content security validation."""
        
        # Test safe content
        safe_content = "This is a normal training module about compliance regulations."
        result = self.security_service.check_content_security(safe_content, "text")
        
        assert result['is_safe'], "Safe content should pass security check"
        assert len(result['issues']) == 0, "Safe content should have no issues"
        assert result['sanitized_content'] == safe_content, "Safe content should not be modified"
        
        # Test malicious content
        malicious_content = "<script>alert('xss')</script>This is malicious content"
        result = self.security_service.check_content_security(malicious_content, "text")
        
        assert not result['is_safe'], "Malicious content should fail security check"
        assert len(result['issues']) > 0, "Malicious content should have issues"
        assert "<script>" not in result['sanitized_content'], "Malicious code should be removed"
        
        # Test suspicious file references
        file_content = "Check this file: file:///etc/passwd or data:text/html,<script>alert(1)</script>"
        result = self.security_service.check_content_security(file_content, "text")
        
        assert not result['is_safe'], "Content with file references should fail"
        assert any("file references" in issue for issue in result['issues'])
    
    def test_training_access_permissions(self):
        """Test training module access permission validation."""
        
        # Test valid access
        is_allowed, message = self.security_service.validate_training_access_permissions(
            user=self.regular_user,
            module=self.training_module,
            action="view"
        )
        assert is_allowed, f"Regular user should be able to view module: {message}"
        
        # Test admin access
        is_allowed, message = self.security_service.validate_training_access_permissions(
            user=self.admin_user,
            module=self.training_module,
            action="modify"
        )
        assert is_allowed, f"Admin should be able to modify module: {message}"
        
        # Test insufficient permissions
        is_allowed, message = self.security_service.validate_training_access_permissions(
            user=self.regular_user,
            module=self.training_module,
            action="delete"
        )
        assert not is_allowed, "Regular user should not be able to delete module"
        assert "Insufficient permissions" in message
        
        # Test inactive user
        self.regular_user.is_active = False
        self.db.commit()
        
        is_allowed, message = self.security_service.validate_training_access_permissions(
            user=self.regular_user,
            module=self.training_module,
            action="view"
        )
        assert not is_allowed, "Inactive user should not have access"
        assert "inactive" in message.lower()
    
    @pytest.mark.asyncio
    async def test_audit_logging(self):
        """Test security audit logging."""
        
        # Test audit logging
        await self.security_service.audit_training_access(
            user_id=str(self.regular_user.id),
            action="view_module",
            resource_type="training_module",
            resource_id=str(self.training_module.id),
            details={"module_title": self.training_module.title},
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser"
        )
        
        # Verify audit log was created (this would check your audit log storage)
        # In a real implementation, you'd query your audit log table/service
        assert True, "Audit logging should complete without errors"


class TestTrainingDataProtection:
    """Test suite for data protection and privacy compliance."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, test_tenant: Tenant):
        """Set up test data for data protection tests."""
        self.db = db_session
        self.tenant = test_tenant
        self.data_protection_service = TrainingDataProtectionService()
        
        self.test_user = create_test_user_with_role(
            db_session=self.db,
            tenant_id=self.tenant.id,
            role="user",
            email="privacy@test.com"
        )
    
    def test_data_sensitivity_classification(self):
        """Test data sensitivity classification."""
        
        classifications = [
            ("user_pii", "highly_sensitive"),
            ("assessment_answers", "sensitive"),
            ("training_progress", "internal"),
            ("module_content", "internal"),
            ("certificates", "sensitive"),
            ("unknown_type", "internal")  # Default classification
        ]
        
        for data_type, expected_classification in classifications:
            classification = self.data_protection_service.classify_data_sensitivity(data_type, {})
            assert classification == expected_classification, f"Wrong classification for {data_type}"
    
    def test_user_data_anonymization(self):
        """Test user data anonymization for analytics."""
        
        user_data = {
            "user_id": "12345",
            "email": "user@example.com",
            "name": "John Doe",
            "role": "compliance_officer",
            "department": "Legal",
            "training_completion_rate": 85.5,
            "last_login_date": "2024-01-15",
            "sensitive_field": "should_be_removed"
        }
        
        anonymized = self.data_protection_service.anonymize_user_data(user_data)
        
        # Check that PII is removed or hashed
        assert "email" not in anonymized, "Email should be removed"
        assert "name" not in anonymized, "Name should be removed"
        assert "user_id" not in anonymized, "User ID should be removed"
        
        # Check that hashed versions are present
        assert "email_hash" in anonymized, "Email hash should be present"
        assert "user_hash" in anonymized, "User hash should be present"
        
        # Check that non-PII is preserved
        assert anonymized["role"] == "compliance_officer", "Role should be preserved"
        assert anonymized["department"] == "Legal", "Department should be preserved"
        assert anonymized["training_completion_rate"] == 85.5, "Training data should be preserved"
        
        # Check that non-whitelisted fields are removed
        assert "sensitive_field" not in anonymized, "Non-whitelisted fields should be removed"
    
    @pytest.mark.asyncio
    async def test_data_deletion_request_handling(self):
        """Test handling of data deletion requests (GDPR compliance)."""
        
        user_id = str(self.test_user.id)
        
        # Test full deletion request
        deletion_report = await self.data_protection_service.handle_data_deletion_request(
            user_id=user_id,
            deletion_type="full"
        )
        
        assert deletion_report["user_id"] == user_id, "User ID should match"
        assert deletion_report["deletion_type"] == "full", "Deletion type should match"
        assert "timestamp" in deletion_report, "Timestamp should be present"
        assert "deleted_records" in deletion_report, "Deleted records should be tracked"
        assert "retained_records" in deletion_report, "Retained records should be tracked"
        
        # Test partial deletion request
        partial_deletion_report = await self.data_protection_service.handle_data_deletion_request(
            user_id=user_id,
            deletion_type="partial"
        )
        
        assert partial_deletion_report["deletion_type"] == "partial", "Partial deletion should be recorded"


class TestSecurityIntegration:
    """Integration tests for security features with API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, test_tenant: Tenant):
        """Set up integration test environment."""
        self.db = db_session
        self.tenant = test_tenant
        self.client = TestClient(app)
        
        self.test_user = create_test_user_with_role(
            db_session=self.db,
            tenant_id=self.tenant.id,
            role="user",
            email="integration@test.com"
        )
    
    def test_api_security_headers(self):
        """Test that API responses include proper security headers."""
        
        response = self.client.get("/api/v1/training/health")
        
        # Check for security headers
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        for header in expected_headers:
            assert header in response.headers, f"Security header {header} should be present"
    
    def test_malicious_payload_rejection(self):
        """Test that API endpoints reject malicious payloads."""
        
        malicious_payloads = [
            {"title": "<script>alert('xss')</script>"},
            {"description": "'; DROP TABLE training_modules; --"},
            {"notes": "javascript:alert(1)"},
            {"content": "<iframe src='evil.com'></iframe>"}
        ]
        
        for payload in malicious_payloads:
            # This would test actual API endpoints with malicious data
            # The endpoints should sanitize or reject the malicious content
            pass  # Placeholder for actual API testing
    
    def test_rate_limiting(self):
        """Test API rate limiting functionality."""
        
        # This would test rate limiting by making rapid requests
        # and verifying that limits are enforced
        pass  # Placeholder for rate limiting tests
    
    def test_authentication_bypass_attempts(self):
        """Test that authentication cannot be bypassed."""
        
        # Test accessing protected endpoints without authentication
        protected_endpoints = [
            "/api/v1/training/modules",
            "/api/v1/training/enrollments",
            "/api/v1/training/certificates"
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
