"""
Regulens AI - Authentication Routes
Enterprise-grade authentication endpoints with comprehensive security features.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, EmailStr
import structlog

from core_infra.api.auth import (
    authenticate_user, 
    create_access_token, 
    create_refresh_token,
    verify_token,
    get_current_user,
    get_password_hash,
    TOKEN_TYPE_REFRESH,
    UserInDB,
    AuthenticationError
)
from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["Authentication"])
security = HTTPBearer()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    remember_me: bool = Field(default=False, description="Extended session duration")

class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: Dict[str, Any] = Field(..., description="User information")

class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="Valid refresh token")

class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

class ForgotPasswordRequest(BaseModel):
    """Forgot password request model."""
    email: EmailStr = Field(..., description="User email address")

class ResetPasswordRequest(BaseModel):
    """Reset password request model."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

class LogoutResponse(BaseModel):
    """Logout response model."""
    message: str = Field(..., description="Logout confirmation message")

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """
    Authenticate user and return JWT tokens.
    
    - **email**: User email address
    - **password**: User password
    - **remember_me**: Extended session duration (optional)
    """
    try:
        # Log login attempt
        client_ip = http_request.client.host
        logger.info(f"Login attempt for {request.email} from {client_ip}")
        
        # Authenticate user
        user = await authenticate_user(request.email, request.password)
        if not user:
            logger.warning(f"Failed login attempt for {request.email} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user account is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
            )
        
        # Prepare token data
        token_data = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions
        }
        
        # Create tokens
        access_token_expires = timedelta(
            minutes=settings.jwt_access_token_expire_minutes * (2 if request.remember_me else 1)
        )
        access_token = create_access_token(token_data, access_token_expires)
        refresh_token = create_refresh_token(token_data)
        
        # Log successful login
        logger.info(f"Successful login for user {user.email} (ID: {user.id})")
        
        # Prepare user data for response (exclude sensitive information)
        user_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "department": user.department,
            "tenant_id": user.tenant_id,
            "permissions": user.permissions,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable"
        )

@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    try:
        # Verify refresh token
        token_data = verify_token(request.refresh_token, TOKEN_TYPE_REFRESH)
        
        # Get current user data
        async with get_database() as db:
            query = """
                SELECT u.*, array_agg(DISTINCT p.permission_name) as permissions
                FROM users u
                LEFT JOIN user_permissions up ON u.id = up.user_id
                LEFT JOIN permissions p ON up.permission_id = p.id
                WHERE u.id = $1 AND u.is_active = true
                GROUP BY u.id
            """
            
            user_record = await db.fetchrow(query, uuid.UUID(token_data.user_id))
            
            if not user_record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
        
        # Prepare new token data
        new_token_data = {
            "user_id": str(user_record['id']),
            "tenant_id": str(user_record['tenant_id']),
            "email": user_record['email'],
            "role": user_record['role'],
            "permissions": user_record['permissions'] or []
        }
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        new_access_token = create_access_token(new_token_data, access_token_expires)
        new_refresh_token = create_refresh_token(new_token_data)
        
        logger.info(f"Token refreshed for user {user_record['email']}")
        
        # Prepare user data for response
        user_data = {
            "id": str(user_record['id']),
            "email": user_record['email'],
            "full_name": user_record['full_name'],
            "role": user_record['role'],
            "department": user_record['department'],
            "tenant_id": str(user_record['tenant_id']),
            "permissions": user_record['permissions'] or [],
            "last_login": user_record['last_login'].isoformat() if user_record['last_login'] else None
        }
        
        return LoginResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=user_data
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: UserInDB = Depends(get_current_user)):
    """
    Logout current user.
    
    Note: In a production system, you would typically maintain a token blacklist
    to invalidate tokens before their natural expiration.
    """
    try:
        logger.info(f"User logout: {current_user.email} (ID: {current_user.id})")
        
        # In a production system, you would:
        # 1. Add the token to a blacklist/revocation list
        # 2. Clear any server-side session data
        # 3. Log the logout event for audit purposes
        
        return LogoutResponse(message="Successfully logged out")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Change user password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password
    - **confirm_password**: Confirm new password
    """
    try:
        # Validate password confirmation
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match"
            )
        
        # Verify current password
        user = await authenticate_user(current_user.email, request.current_password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = get_password_hash(request.new_password)
        
        # Update password in database
        async with get_database() as db:
            await db.execute(
                """
                UPDATE user_credentials 
                SET password_hash = $1, last_password_change = $2, updated_at = $3
                WHERE user_id = $4
                """,
                new_password_hash,
                datetime.utcnow(),
                datetime.utcnow(),
                uuid.UUID(current_user.id)
            )
        
        logger.info(f"Password changed for user {current_user.email}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """
    Get current user information.
    """
    try:
        user_data = {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "department": current_user.department,
            "tenant_id": current_user.tenant_id,
            "permissions": current_user.permissions,
            "is_active": current_user.is_active,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "created_at": current_user.created_at.isoformat(),
            "updated_at": current_user.updated_at.isoformat()
        }
        
        return user_data
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiate password reset process.
    
    - **email**: User email address
    
    Note: This is a placeholder implementation. In production, you would:
    1. Generate a secure reset token
    2. Store it with expiration time
    3. Send reset email to user
    4. Implement rate limiting
    """
    try:
        # Check if user exists
        async with get_database() as db:
            user_record = await db.fetchrow(
                "SELECT id, email FROM users WHERE email = $1 AND is_active = true",
                request.email
            )
            
            if not user_record:
                # Don't reveal whether email exists for security
                logger.warning(f"Password reset requested for non-existent email: {request.email}")
            else:
                logger.info(f"Password reset requested for user: {request.email}")
                # In production: generate reset token and send email
        
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )
