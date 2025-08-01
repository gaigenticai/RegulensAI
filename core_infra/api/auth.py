"""
Regulens AI - Authentication and Authorization Module
Enterprise-grade JWT authentication with role-based access control and tenant isolation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Security configuration
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

class TokenData(BaseModel):
    """Token payload data model."""
    user_id: str
    tenant_id: str
    email: str
    role: str
    permissions: List[str]
    token_type: str
    exp: datetime
    iat: datetime

class UserInDB(BaseModel):
    """User model for database operations."""
    id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    permissions: List[str]
    department: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class AuthenticationError(Exception):
    """Custom authentication error."""
    pass

class AuthorizationError(Exception):
    """Custom authorization error."""
    pass

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise AuthenticationError("Password hashing failed")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    try:
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": TOKEN_TYPE_ACCESS
        })
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key.get_secret_value(), 
            algorithm=settings.jwt_algorithm
        )
        
        logger.info(f"Access token created for user {data.get('user_id')}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise AuthenticationError("Token creation failed")

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": TOKEN_TYPE_REFRESH
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm
        )
        
        logger.info(f"Refresh token created for user {data.get('user_id')}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Refresh token creation failed: {e}")
        raise AuthenticationError("Refresh token creation failed")

def verify_token(token: str, token_type: str = TOKEN_TYPE_ACCESS) -> TokenData:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        
        # Verify token type
        if payload.get("token_type") != token_type:
            raise AuthenticationError("Invalid token type")
        
        # Extract token data
        token_data = TokenData(
            user_id=payload.get("user_id"),
            tenant_id=payload.get("tenant_id"),
            email=payload.get("email"),
            role=payload.get("role"),
            permissions=payload.get("permissions", []),
            token_type=payload.get("token_type"),
            exp=datetime.fromtimestamp(payload.get("exp")),
            iat=datetime.fromtimestamp(payload.get("iat"))
        )
        
        # Check if token is expired
        if token_data.exp < datetime.utcnow():
            raise AuthenticationError("Token has expired")
        
        return token_data
        
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise AuthenticationError("Token verification failed")

async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with email and password."""
    try:
        async with get_database() as db:
            # Get user from database
            query = """
                SELECT u.*, array_agg(DISTINCT p.permission_name) as permissions
                FROM users u
                LEFT JOIN user_permissions up ON u.id = up.user_id
                LEFT JOIN permissions p ON up.permission_id = p.id
                WHERE u.email = $1 AND u.is_active = true
                GROUP BY u.id
            """
            
            user_record = await db.fetchrow(query, email)
            
            if not user_record:
                logger.warning(f"Authentication failed: user not found for email {email}")
                return None
            
            # Get stored password hash
            password_query = "SELECT password_hash FROM user_credentials WHERE user_id = $1"
            password_record = await db.fetchrow(password_query, user_record['id'])
            
            if not password_record:
                logger.warning(f"Authentication failed: no password found for user {user_record['id']}")
                return None
            
            # Verify password
            if not verify_password(password, password_record['password_hash']):
                logger.warning(f"Authentication failed: invalid password for user {user_record['id']}")
                return None
            
            # Update last login
            await db.execute(
                "UPDATE users SET last_login = $1 WHERE id = $2",
                datetime.utcnow(), user_record['id']
            )
            
            # Create user object
            user = UserInDB(
                id=str(user_record['id']),
                tenant_id=str(user_record['tenant_id']),
                email=user_record['email'],
                full_name=user_record['full_name'],
                role=user_record['role'],
                permissions=user_record['permissions'] or [],
                department=user_record['department'],
                is_active=user_record['is_active'],
                last_login=user_record['last_login'],
                created_at=user_record['created_at'],
                updated_at=user_record['updated_at']
            )
            
            logger.info(f"User authenticated successfully: {email}")
            return user
            
    except Exception as e:
        logger.error(f"User authentication failed: {e}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    """Get current authenticated user from JWT token."""
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Verify token
        token_data = verify_token(token, TOKEN_TYPE_ACCESS)
        
        # Get user from database
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
                raise AuthenticationError("User not found")
            
            user = UserInDB(
                id=str(user_record['id']),
                tenant_id=str(user_record['tenant_id']),
                email=user_record['email'],
                full_name=user_record['full_name'],
                role=user_record['role'],
                permissions=user_record['permissions'] or [],
                department=user_record['department'],
                is_active=user_record['is_active'],
                last_login=user_record['last_login'],
                created_at=user_record['created_at'],
                updated_at=user_record['updated_at']
            )
            
            return user
            
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_tenant_access(current_user: UserInDB = Depends(get_current_user)) -> str:
    """Verify user has access to the requested tenant."""
    try:
        # For now, return the user's tenant ID
        # In a more complex system, this could verify access to multiple tenants
        return current_user.tenant_id
        
    except Exception as e:
        logger.error(f"Tenant access verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access denied"
        )

def require_permission(required_permission: str):
    """Decorator to require specific permission for endpoint access."""
    def permission_checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if required_permission not in current_user.permissions:
            logger.warning(
                f"Permission denied: user {current_user.id} lacks {required_permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {required_permission}"
            )
        return current_user
    
    return permission_checker

def require_role(required_role: str):
    """Decorator to require specific role for endpoint access."""
    def role_checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role != required_role:
            logger.warning(
                f"Role access denied: user {current_user.id} has role {current_user.role}, requires {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {required_role}"
            )
        return current_user
    
    return role_checker
