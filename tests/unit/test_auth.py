"""
Unit tests for authentication module.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from core_infra.api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    authenticate_user,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    AuthenticationError
)

class TestPasswordHandling:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith('$2b$')  # bcrypt prefix
    
    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_verification_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "testpassword123"
        invalid_hash = "invalid_hash"
        
        assert verify_password(password, invalid_hash) is False

class TestTokenHandling:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {
            "user_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "admin",
            "permissions": ["users.read"]
        }
        
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        assert token.count('.') == 2  # JWT has 3 parts separated by dots
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {
            "user_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "email": "test@example.com"
        }
        
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 100
        assert token.count('.') == 2
    
    def test_verify_access_token_success(self):
        """Test successful access token verification."""
        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": "test@example.com",
            "role": "admin",
            "permissions": ["users.read"]
        }
        
        token = create_access_token(data)
        token_data = verify_token(token, TOKEN_TYPE_ACCESS)
        
        assert token_data.user_id == user_id
        assert token_data.tenant_id == tenant_id
        assert token_data.email == "test@example.com"
        assert token_data.role == "admin"
        assert token_data.permissions == ["users.read"]
        assert token_data.token_type == TOKEN_TYPE_ACCESS
    
    def test_verify_refresh_token_success(self):
        """Test successful refresh token verification."""
        user_id = str(uuid.uuid4())
        data = {
            "user_id": user_id,
            "tenant_id": str(uuid.uuid4()),
            "email": "test@example.com"
        }
        
        token = create_refresh_token(data)
        token_data = verify_token(token, TOKEN_TYPE_REFRESH)
        
        assert token_data.user_id == user_id
        assert token_data.token_type == TOKEN_TYPE_REFRESH
    
    def test_verify_token_invalid_token(self):
        """Test token verification with invalid token."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            verify_token("invalid.token.here", TOKEN_TYPE_ACCESS)
    
    def test_verify_token_wrong_type(self):
        """Test token verification with wrong token type."""
        data = {"user_id": str(uuid.uuid4())}
        access_token = create_access_token(data)
        
        with pytest.raises(AuthenticationError, match="Invalid token type"):
            verify_token(access_token, TOKEN_TYPE_REFRESH)
    
    def test_verify_expired_token(self):
        """Test verification of expired token."""
        data = {"user_id": str(uuid.uuid4())}
        # Create token with negative expiry (already expired)
        expired_token = create_access_token(data, timedelta(seconds=-1))
        
        with pytest.raises(AuthenticationError, match="Token has expired"):
            verify_token(expired_token, TOKEN_TYPE_ACCESS)

class TestUserAuthentication:
    """Test user authentication functions."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, test_user, db_connection):
        """Test successful user authentication."""
        with patch('core_infra.api.auth.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_connection
            
            user = await authenticate_user("test@example.com", "testpassword123")
            
            assert user is not None
            assert user.email == "test@example.com"
            assert user.full_name == "Test User"
            assert user.role == "admin"
            assert user.is_active is True
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, test_user, db_connection):
        """Test authentication with wrong password."""
        with patch('core_infra.api.auth.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_connection
            
            user = await authenticate_user("test@example.com", "wrongpassword")
            
            assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, db_connection):
        """Test authentication with non-existent user."""
        with patch('core_infra.api.auth.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_connection
            
            user = await authenticate_user("nonexistent@example.com", "password")
            
            assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, test_user, db_connection):
        """Test authentication with inactive user."""
        # Deactivate user
        await db_connection.execute(
            "UPDATE users SET is_active = false WHERE id = $1",
            test_user['id']
        )
        
        with patch('core_infra.api.auth.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_connection
            
            user = await authenticate_user("test@example.com", "testpassword123")
            
            assert user is None

class TestAuthenticationErrors:
    """Test authentication error handling."""
    
    def test_authentication_error_creation(self):
        """Test AuthenticationError creation."""
        error = AuthenticationError("Test error")
        assert str(error) == "Test error"
    
    def test_password_hashing_error(self):
        """Test password hashing error handling."""
        with patch('core_infra.api.auth.pwd_context.hash') as mock_hash:
            mock_hash.side_effect = Exception("Hashing failed")
            
            with pytest.raises(AuthenticationError, match="Password hashing failed"):
                get_password_hash("password")
    
    def test_token_creation_error(self):
        """Test token creation error handling."""
        with patch('core_infra.api.auth.jwt.encode') as mock_encode:
            mock_encode.side_effect = Exception("Encoding failed")
            
            with pytest.raises(AuthenticationError, match="Token creation failed"):
                create_access_token({"user_id": "test"})

class TestTokenExpiry:
    """Test token expiry handling."""
    
    def test_access_token_default_expiry(self):
        """Test access token has correct default expiry."""
        data = {"user_id": str(uuid.uuid4())}
        token = create_access_token(data)
        token_data = verify_token(token, TOKEN_TYPE_ACCESS)
        
        # Token should expire in approximately 30 minutes (default)
        time_diff = token_data.exp - datetime.utcnow()
        assert 25 <= time_diff.total_seconds() / 60 <= 35  # Allow some variance
    
    def test_access_token_custom_expiry(self):
        """Test access token with custom expiry."""
        data = {"user_id": str(uuid.uuid4())}
        custom_expiry = timedelta(hours=2)
        token = create_access_token(data, custom_expiry)
        token_data = verify_token(token, TOKEN_TYPE_ACCESS)
        
        # Token should expire in approximately 2 hours
        time_diff = token_data.exp - datetime.utcnow()
        assert 115 <= time_diff.total_seconds() / 60 <= 125  # Allow some variance
    
    def test_refresh_token_expiry(self):
        """Test refresh token has correct expiry."""
        data = {"user_id": str(uuid.uuid4())}
        token = create_refresh_token(data)
        token_data = verify_token(token, TOKEN_TYPE_REFRESH)
        
        # Token should expire in approximately 7 days (default)
        time_diff = token_data.exp - datetime.utcnow()
        expected_seconds = 7 * 24 * 60 * 60  # 7 days in seconds
        assert expected_seconds - 300 <= time_diff.total_seconds() <= expected_seconds + 300
