"""
Training Portal API Routes
Provides REST API endpoints for the training portal functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, File, UploadFile, Response
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import uuid
import json

from core_infra.database.models import (
    User, Tenant,
    TrainingModule, TrainingSection, TrainingAssessment,
    TrainingEnrollment, TrainingSectionProgress, TrainingAssessmentAttempt,
    TrainingBookmark, TrainingCertificate, TrainingAchievement,
    TrainingDiscussion, TrainingDiscussionVote, TrainingAnalytics,
    TrainingReport
)
from core_infra.api.auth import get_current_user, verify_tenant_access, require_permission, UserInDB
from core_infra.services.training_service import TrainingService
from core_infra.services.certificate_service import CertificateService
from core_infra.services.analytics_service import AnalyticsService
from core_infra.services.training_cache_service import training_cache_service
from core_infra.services.training_performance_service import training_performance_service, monitor_performance
from core_infra.utils.validation import validate_json_schema
from core_infra.utils.pagination import paginate_query
from core_infra.utils.cache import cache_result
from core_infra.utils.search import SearchEngine
from core_infra.utils.recommendations import RecommendationEngine
import structlog

logger = structlog.get_logger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/training", tags=["Training Portal"])

# Initialize services
training_service = TrainingService()
certificate_service = CertificateService()
analytics_service = AnalyticsService()
search_engine = SearchEngine()
recommendation_engine = RecommendationEngine()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TrainingModuleCreate(BaseModel):
    """Training module creation request model."""
    module_code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., description="Module category")
    difficulty_level: str = Field(default="beginner", description="Difficulty level")
    estimated_duration_minutes: int = Field(default=60, ge=1, le=1440)
    prerequisites: List[str] = Field(default=[], description="Prerequisite module codes")
    learning_objectives: List[str] = Field(default=[], description="Learning objectives")
    content_type: str = Field(default="interactive", description="Content type")
    content_url: Optional[str] = Field(None, description="External content URL")
    content_data: Dict[str, Any] = Field(default={}, description="Embedded content data")
    is_mandatory: bool = Field(default=False)
    is_active: bool = Field(default=True)

class TrainingModuleUpdate(BaseModel):
    """Training module update request model."""
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    prerequisites: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None
    content_type: Optional[str] = None
    content_url: Optional[str] = None
    content_data: Optional[Dict[str, Any]] = None
    is_mandatory: Optional[bool] = None
    is_active: Optional[bool] = None

class TrainingEnrollmentCreate(BaseModel):
    """Training enrollment request model."""
    module_id: str = Field(..., description="Training module ID")
    target_completion_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)

class TrainingAssessmentSubmission(BaseModel):
    """Assessment submission model."""
    assessment_id: str = Field(..., description="Assessment ID")
    answers: Dict[str, Any] = Field(..., description="User answers")
    time_spent_minutes: Optional[int] = Field(None, ge=0)

class TrainingBookmarkCreate(BaseModel):
    """Bookmark creation model."""
    module_id: Optional[str] = None
    section_id: Optional[str] = None
    bookmark_type: str = Field(default="section")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    position_data: Dict[str, Any] = Field(default={})
    tags: List[str] = Field(default=[])
    is_private: bool = Field(default=True)

class TrainingDiscussionCreate(BaseModel):
    """Discussion creation model."""
    module_id: str = Field(..., description="Module ID")
    section_id: Optional[str] = None
    parent_id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    discussion_type: str = Field(default="question")

class TrainingSearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = None
    difficulty_level: Optional[str] = None
    content_type: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)

class TrainingModuleResponse(BaseModel):
    """Training module response model."""
    id: str
    module_code: str
    title: str
    description: Optional[str]
    category: str
    difficulty_level: str
    estimated_duration_minutes: int
    prerequisites: List[str]
    learning_objectives: List[str]
    content_type: str
    content_url: Optional[str]
    is_mandatory: bool
    is_active: bool
    created_at: str
    updated_at: str

class TrainingEnrollmentResponse(BaseModel):
    """Training enrollment response model."""
    id: str
    module_id: str
    status: str
    completion_percentage: float
    enrolled_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    last_accessed_at: Optional[str]
    total_time_spent_minutes: int
    target_completion_date: Optional[str]

class TrainingListResponse(BaseModel):
    """Training list response model."""
    modules: List[TrainingModuleResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# TRAINING MODULE ENDPOINTS
# ============================================================================

@router.get("/modules", response_model=TrainingListResponse)
@monitor_performance(endpoint="/training/modules", method="GET")
async def get_training_modules(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search query"),
    current_user: UserInDB = Depends(require_permission("training.modules.read")),
    tenant_check = Depends(verify_tenant_access)
):
    """Get training modules with filtering and pagination."""
    try:
        # Build base query
        query_filters = {
            'tenant_id': current_user.tenant_id,
            'is_active': True
        }

        if category:
            query_filters['category'] = category
        if difficulty_level:
            query_filters['difficulty_level'] = difficulty_level

        # Check cache first
        cached_modules = await training_cache_service.get_cached_modules(
            tenant_id=current_user.tenant_id,
            filters=query_filters,
            page=page,
            size=size
        )

        if cached_modules:
            return TrainingListResponse(**cached_modules)

        # Get modules with search if provided
        if search:
            modules = await training_service.search_modules(
                search_query=search,
                filters=query_filters,
                page=page,
                size=size
            )
        else:
            modules = await training_service.get_modules(
                filters=query_filters,
                page=page,
                size=size
            )

        # Prepare response
        response_data = {
            "modules": [TrainingModuleResponse(**module.to_dict()) for module in modules['items']],
            "total": modules['total'],
            "page": page,
            "size": size,
            "pages": modules['pages']
        }

        # Cache the result
        await training_cache_service.cache_modules(
            tenant_id=current_user.tenant_id,
            modules_data=response_data,
            filters=query_filters,
            page=page,
            size=size
        )

        return TrainingListResponse(**response_data)

    except Exception as e:
        logger.error("Failed to get training modules", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve training modules")


@router.get("/modules/{module_id}", response_model=TrainingModuleResponse)
async def get_training_module(
    module_id: str = Path(..., description="Training module ID"),
    current_user: UserInDB = Depends(require_permission("training.modules.read")),
    tenant_check = Depends(verify_tenant_access)
):
    """Get a specific training module."""
    try:
        module = await training_service.get_module_by_id(module_id, current_user.tenant_id)
        if not module:
            raise HTTPException(status_code=404, detail="Training module not found")
        
        return TrainingModuleResponse(**module.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get training module", module_id=module_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve training module")


@router.post("/modules", response_model=TrainingModuleResponse)
async def create_training_module(
    module_data: TrainingModuleCreate,
    current_user: UserInDB = Depends(require_permission("training.modules.create")),
    tenant_check = Depends(verify_tenant_access)
):
    """Create a new training module."""
    try:
        # Permission already checked by decorator
        
        module = await training_service.create_module(
            module_data=module_data.dict(),
            tenant_id=current_user.tenant_id,
            created_by=current_user.id
        )
        
        return TrainingModuleResponse(**module.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create training module", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create training module")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def training_portal_health():
    """Training portal health check."""
    try:
        # Check service dependencies
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'training_service': 'healthy',
                'certificate_service': 'healthy',
                'analytics_service': 'healthy',
                'search_engine': 'healthy',
                'recommendation_engine': 'healthy'
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }
