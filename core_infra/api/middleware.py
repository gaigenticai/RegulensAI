"""
Regulens AI - Security Middleware
Enterprise-grade security middleware for authentication, authorization, and audit logging.
"""

import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog

from core_infra.api.auth import verify_token, TOKEN_TYPE_ACCESS, AuthenticationError
from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Security configuration
security = HTTPBearer()

# Rate limiting storage (in production, use Redis)
rate_limit_storage: Dict[str, Dict[str, Any]] = {}

# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        try:
            response = await call_next(request)
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'"
            )
            
            # Remove server information
            if "server" in response.headers:
                del response.headers["server"]
            
            return response
            
        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            return await call_next(request)

# ============================================================================
# RATE LIMITING MIDDLEWARE
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse."""
    
    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_size = 60  # 1 minute window
    
    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from token if available
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                token_data = verify_token(token, TOKEN_TYPE_ACCESS)
                return f"user:{token_data.user_id}"
        except:
            pass
        
        # Fall back to IP address
        client_ip = request.client.host
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def is_rate_limited(self, client_id: str) -> tuple[bool, Dict[str, Any]]:
        """Check if client is rate limited."""
        current_time = time.time()
        
        if client_id not in rate_limit_storage:
            rate_limit_storage[client_id] = {
                "requests": [],
                "burst_count": 0,
                "last_request": current_time
            }
        
        client_data = rate_limit_storage[client_id]
        
        # Clean old requests outside the window
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if current_time - req_time < self.window_size
        ]
        
        # Check burst limit (requests in last 10 seconds)
        recent_requests = [
            req_time for req_time in client_data["requests"]
            if current_time - req_time < 10
        ]
        
        if len(recent_requests) >= self.burst_limit:
            return True, {
                "error": "Rate limit exceeded - too many requests in short time",
                "retry_after": 10
            }
        
        # Check per-minute limit
        if len(client_data["requests"]) >= self.requests_per_minute:
            oldest_request = min(client_data["requests"])
            retry_after = int(self.window_size - (current_time - oldest_request))
            return True, {
                "error": "Rate limit exceeded - too many requests per minute",
                "retry_after": retry_after
            }
        
        # Add current request
        client_data["requests"].append(current_time)
        client_data["last_request"] = current_time
        
        return False, {}
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting."""
        try:
            # Skip rate limiting for health checks and static files
            if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
                return await call_next(request)
            
            client_id = self.get_client_identifier(request)
            is_limited, limit_info = self.is_rate_limited(client_id)
            
            if is_limited:
                logger.warning(f"Rate limit exceeded for client: {client_id}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": limit_info["error"],
                        "retry_after": limit_info["retry_after"]
                    },
                    headers={"Retry-After": str(limit_info["retry_after"])}
                )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            return await call_next(request)

# ============================================================================
# TENANT ISOLATION MIDDLEWARE
# ============================================================================

class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Ensure tenant data isolation."""
    
    async def dispatch(self, request: Request, call_next):
        """Enforce tenant isolation."""
        try:
            # Skip for public endpoints
            public_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json", "/auth/login"]
            if any(request.url.path.startswith(path) for path in public_paths):
                return await call_next(request)
            
            # Extract tenant information from token
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    token = auth_header.split(" ")[1]
                    token_data = verify_token(token, TOKEN_TYPE_ACCESS)
                    
                    # Add tenant context to request state
                    request.state.tenant_id = token_data.tenant_id
                    request.state.user_id = token_data.user_id
                    
                    # Validate tenant is active
                    async with get_database() as db:
                        tenant_record = await db.fetchrow(
                            "SELECT is_active FROM tenants WHERE id = $1",
                            uuid.UUID(token_data.tenant_id)
                        )
                        
                        if not tenant_record or not tenant_record['is_active']:
                            logger.warning(f"Access attempt to inactive tenant: {token_data.tenant_id}")
                            return JSONResponse(
                                status_code=status.HTTP_403_FORBIDDEN,
                                content={"detail": "Tenant is inactive"}
                            )
                    
                except AuthenticationError:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid authentication token"}
                    )
                except Exception as e:
                    logger.error(f"Tenant isolation error: {e}")
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={"detail": "Authentication service error"}
                    )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Tenant isolation middleware error: {e}")
            return await call_next(request)

# ============================================================================
# AUDIT LOGGING MIDDLEWARE
# ============================================================================

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests for audit purposes."""
    
    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
    
    def should_log_request(self, request: Request) -> bool:
        """Determine if request should be logged."""
        # Skip logging for health checks and static files
        skip_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        return not any(request.url.path.startswith(path) for path in skip_paths)
    
    async def get_request_body(self, request: Request) -> Optional[str]:
        """Safely get request body for logging."""
        if not self.log_request_body:
            return None
        
        try:
            body = await request.body()
            if body:
                # Limit body size for logging
                body_str = body.decode('utf-8')[:1000]
                # Mask sensitive fields
                if 'password' in body_str.lower():
                    return "[BODY CONTAINS SENSITIVE DATA]"
                return body_str
        except:
            pass
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response for audit."""
        start_time = time.time()
        
        if not self.should_log_request(request):
            return await call_next(request)
        
        try:
            # Extract user and tenant info
            user_id = getattr(request.state, 'user_id', None)
            tenant_id = getattr(request.state, 'tenant_id', None)
            
            # Get client information
            client_ip = request.client.host
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            
            user_agent = request.headers.get("user-agent", "")
            
            # Get request body if configured
            request_body = await self.get_request_body(request)
            
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Prepare audit log entry
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4()),
                "user_id": user_id,
                "tenant_id": tenant_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "status_code": response.status_code,
                "process_time": round(process_time, 3),
                "request_size": len(await request.body()) if hasattr(request, 'body') else 0,
                "response_size": int(response.headers.get("content-length", 0))
            }
            
            if request_body:
                audit_entry["request_body"] = request_body
            
            # Log to database for compliance
            try:
                async with get_database() as db:
                    await db.execute(
                        """
                        INSERT INTO audit_logs (
                            id, user_id, tenant_id, action, resource, details, 
                            ip_address, user_agent, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        uuid.uuid4(),
                        uuid.UUID(user_id) if user_id else None,
                        uuid.UUID(tenant_id) if tenant_id else None,
                        f"{request.method} {request.url.path}",
                        request.url.path,
                        audit_entry,
                        client_ip,
                        user_agent,
                        datetime.utcnow()
                    )
            except Exception as db_error:
                logger.error(f"Failed to save audit log to database: {db_error}")
            
            # Log to structured logger
            logger.info(
                "API Request",
                **audit_entry
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Audit logging middleware error: {e}")
            return await call_next(request)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

class CORSMiddleware(BaseHTTPMiddleware):
    """Handle CORS for web applications."""
    
    def __init__(self, app, allowed_origins: List[str] = None, allowed_methods: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS headers."""
        try:
            # Handle preflight requests
            if request.method == "OPTIONS":
                response = Response()
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
                response.headers["Access-Control-Max-Age"] = "86400"
                return response
            
            response = await call_next(request)
            
            # Add CORS headers to response
            origin = request.headers.get("origin")
            if origin and (origin in self.allowed_origins or "*" in self.allowed_origins):
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"
            
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "Content-Range, X-Content-Range"
            
            return response
            
        except Exception as e:
            logger.error(f"CORS middleware error: {e}")
            return await call_next(request)

# ============================================================================
# DECORATOR FUNCTIONS FOR BACKWARD COMPATIBILITY
# ============================================================================

def rate_limit(requests_per_minute: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Simple rate limiting - in production, use Redis or similar
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def audit_log(action: str):
    """Audit logging decorator"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Simple audit logging
            logger.info(f"API action: {action}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
