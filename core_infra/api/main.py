"""
Regulens AI - Financial Compliance Platform
Main FastAPI Application

Enterprise-grade compliance platform for financial services.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from core_infra.database.connection import init_database, close_database
from core_infra.services.monitoring import setup_tracing, get_metrics
from core_infra.api.middleware import (
    RateLimitMiddleware,
    TenantIsolationMiddleware,
    SecurityHeadersMiddleware,
    AuditLoggingMiddleware
)
from core_infra.api.auth import get_current_user, verify_tenant_access
from core_infra.api.routes import (
    auth_router,
    tenants_router,
    users_router,
    regulatory_router,
    compliance_router,
    aml_router,
    tasks_router,
    reports_router,
    ai_router,
    operations_router,
    health_router
)
from core_infra.api.routes.ui_portals import router as ui_portals_router
from core_infra.api.routes.security_testing import router as security_testing_router
from core_infra.api.routes.phase6_ai import include_phase6_routes
from core_infra.api.training_portal.routes import router as training_portal_router
from core_infra.config import get_settings
from core_infra.exceptions import (
    RegulensBaseException,
    exception_to_http_exception
)
from core_infra.api.swagger_config import get_enhanced_openapi_schema, get_api_tags_metadata

# Initialize structured logging
logger = structlog.get_logger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Get application settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    try:
        # Startup
        logger.info("Starting Regulens AI Financial Compliance Platform")
        
        # Initialize database connections
        await init_database()
        logger.info("Database connections initialized")
        
        # Setup distributed tracing
        if settings.jaeger_enabled:
            setup_tracing(settings.jaeger_service_name)
            logger.info("Distributed tracing initialized")
        
        # Initialize AI models cache
        await init_ai_models()
        logger.info("AI models cache initialized")
        
        # Start background monitoring tasks
        await start_background_tasks()
        logger.info("Background monitoring tasks started")

        # Initialize UI portal managers
        await init_ui_portals()
        logger.info("UI portal managers initialized")

        # Initialize auto-scaling controller
        await init_autoscaling()
        logger.info("Auto-scaling controller initialized")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Regulens AI Financial Compliance Platform")
        
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        # Stop background tasks
        await stop_background_tasks()
        logger.info("Background tasks stopped")


async def init_ai_models():
    """Initialize AI models and embeddings cache."""
    try:
        from core_infra.ai.models import initialize_models
        await initialize_models()
    except Exception as e:
        logger.warning(f"Failed to initialize AI models: {e}")


async def init_ui_portals():
    """Initialize UI portal managers."""
    try:
        from core_infra.ui import initialize_ui_portals
        await initialize_ui_portals()
        logger.info("UI portal framework initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize UI portals: {e}")


async def init_autoscaling():
    """Initialize auto-scaling controller."""
    try:
        from core_infra.autoscaling.controller import autoscaling_controller
        await autoscaling_controller.initialize()
        logger.info("Auto-scaling controller initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize auto-scaling: {e}")


async def start_background_tasks():
    """Start background monitoring and compliance tasks."""
    try:
        from core_infra.services.regulatory_monitor import start_monitoring
        from core_infra.services.compliance_engine import start_compliance_monitoring
        
        if settings.regulatory_monitor_enabled:
            asyncio.create_task(start_monitoring())
            
        if settings.aml_monitoring_enabled:
            asyncio.create_task(start_compliance_monitoring())
            
    except Exception as e:
        logger.warning(f"Failed to start background tasks: {e}")


async def stop_background_tasks():
    """Stop background tasks gracefully."""
    try:
        # Cancel all running tasks
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.warning(f"Error stopping background tasks: {e}")


# Create FastAPI application
app = FastAPI(
    title="Regulens AI - Financial Compliance Platform",
    description="Enterprise-grade financial compliance platform with comprehensive API documentation",
    version=settings.app_version,
    openapi_url=f"/{settings.api_version}/openapi.json" if settings.api_docs_enabled else None,
    docs_url="/docs" if settings.swagger_ui_enabled else None,
    redoc_url="/redoc" if settings.redoc_enabled else None,
    lifespan=lifespan,
    debug=settings.debug,
    openapi_tags=get_api_tags_metadata()
)

# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS Configuration
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=settings.cors_allowed_methods.split(","),
        allow_headers=settings.cors_allowed_headers.split(","),
    )

# Trusted Hosts (Production Security)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.regulens-ai.com", "localhost", "127.0.0.1"]
    )

# Session Management
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key,
    max_age=settings.jwt_access_token_expire_minutes * 60
)

# Request Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate Limiting
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
        burst_limit=settings.rate_limit_burst
    )

# Multi-tenant Isolation
if settings.tenant_isolation_enabled:
    app.add_middleware(TenantIsolationMiddleware)

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Audit Logging
app.add_middleware(AuditLoggingMiddleware)

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RegulensBaseException)
async def regulens_exception_handler(request: Request, exc: RegulensBaseException):
    """Handle custom Regulens exceptions."""
    http_exc = exception_to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": get_current_timestamp()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with security-conscious error messages."""
    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    # In production, don't expose internal error details
    if settings.debug:
        error_detail = str(exc)
    else:
        error_detail = "An internal error occurred. Please contact support if the issue persists."
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": error_detail,
            "status_code": 500,
            "timestamp": get_current_timestamp()
        }
    )

# ============================================================================
# ROUTE REGISTRATION
# ============================================================================

# Health and System Routes
app.include_router(health_router, prefix=f"/{settings.api_version}", tags=["System"])

# Authentication and Authorization
app.include_router(auth_router, prefix=f"/{settings.api_version}/auth", tags=["Authentication"])

# Core Management
app.include_router(tenants_router, prefix=f"/{settings.api_version}/tenants", tags=["Tenants"])
app.include_router(users_router, prefix=f"/{settings.api_version}/users", tags=["Users"])

# Regulatory Intelligence
app.include_router(regulatory_router, prefix=f"/{settings.api_version}/regulatory", tags=["Regulatory"])

# Compliance Management
app.include_router(compliance_router, prefix=f"/{settings.api_version}/compliance", tags=["Compliance"])

# AML/KYC
app.include_router(aml_router, prefix=f"/{settings.api_version}/aml", tags=["AML/KYC"])

# Workflow Management
app.include_router(tasks_router, prefix=f"/{settings.api_version}/tasks", tags=["Tasks"])

# Reporting and Analytics
app.include_router(reports_router, prefix=f"/{settings.api_version}/reports", tags=["Reports"])

# AI and Insights
app.include_router(ai_router, prefix=f"/{settings.api_version}/ai", tags=["AI Insights"])

# Operations and Deployment
app.include_router(operations_router, prefix=f"/{settings.api_version}/operations", tags=["Operations"])

# UI Portals (Phase 4)
app.include_router(ui_portals_router, tags=["UI Portals"])

# Security Testing (Phase 5)
app.include_router(security_testing_router, tags=["Security Testing"])

# Training Portal
app.include_router(training_portal_router, prefix=f"/{settings.api_version}", tags=["Training Portal"])

# Phase 6 Advanced AI & Automation
include_phase6_routes(app)

# Enhanced OpenAPI Schema
app.openapi = lambda: get_enhanced_openapi_schema(app)

# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with platform information."""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Regulens AI - Financial Compliance Platform</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 20px; margin-bottom: 30px; }}
            .feature {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #2c5aa0; }}
            .links {{ margin-top: 30px; }}
            .links a {{ display: inline-block; margin: 10px 15px 10px 0; padding: 10px 20px; background: #2c5aa0; color: white; text-decoration: none; border-radius: 5px; }}
            .links a:hover {{ background: #1e3f73; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏛️ Regulens AI</h1>
                <h2>Enterprise Financial Compliance Platform</h2>
                <p>Version {settings.app_version} | Environment: {settings.app_environment}</p>
            </div>
            
            <div class="feature">
                <h3>🔍 Regulatory Intelligence</h3>
                <p>Real-time monitoring of global regulatory updates with AI-powered analysis</p>
            </div>
            
            <div class="feature">
                <h3>🛡️ AML/KYC Compliance</h3>
                <p>Automated customer due diligence and transaction monitoring</p>
            </div>
            
            <div class="feature">
                <h3>🤖 AI Regulatory Expert</h3>
                <p>Natural language processing for regulatory interpretation and insights</p>
            </div>
            
            <div class="feature">
                <h3>📊 Compliance Workflows</h3>
                <p>Automated task assignment, impact assessments, and audit trails</p>
            </div>
            
            <div class="links">
                <a href="/docs">API Documentation</a>
                <a href="/redoc">API Reference</a>
                <a href="/{settings.api_version}/health">System Health</a>
                <a href="/{settings.api_version}/metrics">Metrics</a>
            </div>
        </div>
    </body>
    </html>
    """)


@app.get(f"/{settings.api_version}/info")
async def get_platform_info():
    """Get platform information and capabilities."""
    return {
        "platform": "Regulens AI Financial Compliance Platform",
        "version": settings.app_version,
        "environment": settings.app_environment,
        "capabilities": {
            "regulatory_monitoring": settings.regulatory_monitor_enabled,
            "aml_compliance": settings.aml_monitoring_enabled,
            "ai_insights": settings.ai_regulatory_insights_enabled,
            "real_time_monitoring": settings.transaction_monitoring_real_time,
            "multi_tenant": settings.tenant_isolation_enabled
        },
        "supported_jurisdictions": settings.regulatory_jurisdictions.split(","),
        "compliance_frameworks": settings.compliance_frameworks.split(","),
        "timestamp": get_current_timestamp()
    }


@app.get(f"/{settings.api_version}/metrics")
async def get_platform_metrics():
    """Get platform performance metrics."""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    
    return await get_metrics()


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "core_infra.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.hot_reload_enabled and settings.debug,
        workers=1 if settings.debug else settings.worker_processes,
        log_level=settings.log_level.lower(),
        access_log=True,
        server_header=False,
        date_header=False
    ) 