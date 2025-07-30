"""
Regulens AI API Routes
Centralized import for all API route modules.
"""

from core_infra.api.routes.auth import router as auth_router
from core_infra.api.routes.users import router as users_router
from core_infra.api.routes.tenants import router as tenants_router
from core_infra.api.routes.regulatory import router as regulatory_router
from core_infra.api.routes.compliance import router as compliance_router
from core_infra.api.routes.aml import router as aml_router
from core_infra.api.routes.tasks import router as tasks_router
from core_infra.api.routes.reports import router as reports_router
from core_infra.api.routes.ai import router as ai_router
from core_infra.api.routes.operations import router as operations_router

# Health check router (simplified)
from fastapi import APIRouter
health_router = APIRouter(tags=["Health"])

@health_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "regulens-ai"}

__all__ = [
    "auth_router",
    "users_router",
    "tenants_router",
    "regulatory_router",
    "compliance_router",
    "aml_router",
    "tasks_router",
    "reports_router",
    "ai_router",
    "operations_router",
    "health_router"
]
