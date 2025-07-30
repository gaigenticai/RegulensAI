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
from core_infra.api.auth import get_current_user, verify_tenant_access
from core_infra.services.training_service import TrainingService
from core_infra.services.certificate_service import CertificateService
from core_infra.services.analytics_service import AnalyticsService
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
async def get_training_modules(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search query"),
    current_user = Depends(get_current_user),
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

        return TrainingListResponse(
            modules=[TrainingModuleResponse(**module.to_dict()) for module in modules['items']],
            total=modules['total'],
            page=page,
            size=size,
            pages=modules['pages']
        )

    except Exception as e:
        logger.error("Failed to get training modules", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve training modules")


@router.get("/modules/{module_id}", response_model=TrainingModuleResponse)
async def get_training_module(
    module_id: str = Path(..., description="Training module ID"),
    current_user = Depends(get_current_user),
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
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Create a new training module."""
    try:
        # Check permissions
        if not await training_service.has_permission(current_user.id, 'training.modules.create'):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

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
# TRAINING ENROLLMENT ENDPOINTS
# ============================================================================

@router.get("/enrollments", response_model=List[TrainingEnrollmentResponse])
async def get_user_enrollments(
    status: Optional[str] = Query(None, description="Filter by enrollment status"),
    current_user = Depends(get_current_user)
):
    """Get current user's training enrollments."""
    try:
        enrollments = await training_service.get_user_enrollments(
            user_id=current_user.id,
            status=status
        )

        return [TrainingEnrollmentResponse(**enrollment.to_dict()) for enrollment in enrollments]

    except Exception as e:
        logger.error("Failed to get user enrollments", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve enrollments")


@router.post("/enrollments", response_model=TrainingEnrollmentResponse)
async def enroll_in_training(
    enrollment_data: TrainingEnrollmentCreate,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Enroll user in a training module."""
    try:
        # Verify module exists and is accessible
        module = await training_service.get_module_by_id(
            enrollment_data.module_id,
            current_user.tenant_id
        )
        if not module:
            raise HTTPException(status_code=404, detail="Training module not found")

        # Check if already enrolled
        existing_enrollment = await training_service.get_enrollment(
            user_id=current_user.id,
            module_id=enrollment_data.module_id
        )
        if existing_enrollment:
            raise HTTPException(status_code=409, detail="Already enrolled in this module")

        enrollment = await training_service.create_enrollment(
            user_id=current_user.id,
            module_id=enrollment_data.module_id,
            target_completion_date=enrollment_data.target_completion_date,
            notes=enrollment_data.notes
        )

        return TrainingEnrollmentResponse(**enrollment.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create enrollment", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to enroll in training")


# ============================================================================
# SEARCH AND RECOMMENDATIONS
# ============================================================================

@router.post("/search")
async def search_training_content(
    search_request: TrainingSearchRequest,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Search training content with advanced filtering."""
    try:
        results = await training_service.search_content(
            query=search_request.query,
            tenant_id=current_user.tenant_id,
            filters={
                'category': search_request.category,
                'difficulty_level': search_request.difficulty_level,
                'content_type': search_request.content_type
            },
            limit=search_request.limit
        )

        return {
            'query': search_request.query,
            'results': results,
            'total_results': len(results)
        }

    except Exception as e:
        logger.error("Search failed", query=search_request.query, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/recommendations")
async def get_training_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get personalized training recommendations."""
    try:
        # Get user's training history
        user_history = await training_service.get_user_enrollments(current_user.id)

        recommendations = recommendation_engine.get_training_recommendations(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            user_history=user_history,
            limit=limit
        )

        return {
            'recommendations': recommendations,
            'total': len(recommendations),
            'user_id': current_user.id
        }

    except Exception as e:
        logger.error("Failed to get recommendations", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


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


# ============================================================================
# TRAINING MODULES
# ============================================================================

@training_bp.route('/modules', methods=['GET'])
@jwt_required()
@cache_result(timeout=300)  # Cache for 5 minutes
def get_training_modules():
    """Get all available training modules with optional filtering."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Get query parameters
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        content_type = request.args.get('content_type')
        mandatory = request.args.get('mandatory')
        sort_by = request.args.get('sort_by', 'title')
        sort_order = request.args.get('sort_order', 'asc')
        search = request.args.get('search')
        
        # Build query
        query = TrainingModule.query.filter(
            TrainingModule.tenant_id == user.tenant_id,
            TrainingModule.is_active == True
        )
        
        # Apply filters
        if category:
            query = query.filter(TrainingModule.category == category)
        
        if difficulty:
            query = query.filter(TrainingModule.difficulty_level == difficulty)
        
        if content_type:
            query = query.filter(TrainingModule.content_type == content_type)
        
        if mandatory is not None:
            is_mandatory = mandatory.lower() == 'true'
            query = query.filter(TrainingModule.is_mandatory == is_mandatory)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    TrainingModule.title.ilike(search_term),
                    TrainingModule.description.ilike(search_term)
                )
            )
        
        # Apply sorting
        sort_column = getattr(TrainingModule, sort_by, TrainingModule.title)
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Paginate results
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        paginated_modules = paginate_query(query, page, per_page)
        
        # Get user enrollments for these modules
        module_ids = [m.id for m in paginated_modules.items]
        enrollments = TrainingEnrollment.query.filter(
            TrainingEnrollment.user_id == user_id,
            TrainingEnrollment.module_id.in_(module_ids)
        ).all()
        
        enrollment_map = {e.module_id: e for e in enrollments}
        
        # Format response
        modules_data = []
        for module in paginated_modules.items:
            enrollment = enrollment_map.get(module.id)
            module_data = {
                'id': str(module.id),
                'module_code': module.module_code,
                'title': module.title,
                'description': module.description,
                'category': module.category,
                'difficulty_level': module.difficulty_level,
                'estimated_duration_minutes': module.estimated_duration_minutes,
                'learning_objectives': module.learning_objectives,
                'prerequisites': module.prerequisites,
                'content_type': module.content_type,
                'is_mandatory': module.is_mandatory,
                'version': module.version,
                'created_at': module.created_at.isoformat(),
                'enrollment': {
                    'id': str(enrollment.id),
                    'status': enrollment.status,
                    'completion_percentage': float(enrollment.completion_percentage or 0),
                    'enrolled_at': enrollment.enrolled_at.isoformat(),
                    'started_at': enrollment.started_at.isoformat() if enrollment.started_at else None,
                    'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None,
                    'last_accessed_at': enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None
                } if enrollment else None
            }
            modules_data.append(module_data)
        
        return jsonify({
            'modules': modules_data,
            'pagination': {
                'page': paginated_modules.page,
                'pages': paginated_modules.pages,
                'per_page': paginated_modules.per_page,
                'total': paginated_modules.total
            }
        })
        
    except Exception as e:
        logger.error("Failed to get training modules", error=str(e))
        return jsonify({'error': 'Failed to retrieve training modules'}), 500


@training_bp.route('/modules/<module_id>', methods=['GET'])
@jwt_required()
def get_training_module(module_id):
    """Get a specific training module with sections."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        module = TrainingModule.query.filter(
            TrainingModule.id == module_id,
            TrainingModule.tenant_id == user.tenant_id,
            TrainingModule.is_active == True
        ).first()
        
        if not module:
            return jsonify({'error': 'Module not found'}), 404
        
        # Get sections
        sections = TrainingSection.query.filter(
            TrainingSection.module_id == module_id
        ).order_by(TrainingSection.section_order).all()
        
        # Get user enrollment
        enrollment = TrainingEnrollment.query.filter(
            TrainingEnrollment.user_id == user_id,
            TrainingEnrollment.module_id == module_id
        ).first()
        
        # Get section progress if enrolled
        section_progress = {}
        if enrollment:
            progress_records = TrainingSectionProgress.query.filter(
                TrainingSectionProgress.enrollment_id == enrollment.id
            ).all()
            section_progress = {p.section_id: p for p in progress_records}
        
        # Format response
        module_data = {
            'id': str(module.id),
            'module_code': module.module_code,
            'title': module.title,
            'description': module.description,
            'category': module.category,
            'difficulty_level': module.difficulty_level,
            'estimated_duration_minutes': module.estimated_duration_minutes,
            'learning_objectives': module.learning_objectives,
            'prerequisites': module.prerequisites,
            'content_type': module.content_type,
            'is_mandatory': module.is_mandatory,
            'version': module.version,
            'sections': [
                {
                    'id': str(section.id),
                    'section_code': section.section_code,
                    'title': section.title,
                    'description': section.description,
                    'content_markdown': section.content_markdown,
                    'content_html': section.content_html,
                    'section_order': section.section_order,
                    'estimated_duration_minutes': section.estimated_duration_minutes,
                    'is_interactive': section.is_interactive,
                    'interactive_elements': section.interactive_elements,
                    'is_required': section.is_required,
                    'progress': {
                        'status': section_progress.get(section.id).status if section.id in section_progress else 'not_started',
                        'started_at': section_progress.get(section.id).started_at.isoformat() if section.id in section_progress and section_progress.get(section.id).started_at else None,
                        'completed_at': section_progress.get(section.id).completed_at.isoformat() if section.id in section_progress and section_progress.get(section.id).completed_at else None,
                        'time_spent_minutes': section_progress.get(section.id).time_spent_minutes if section.id in section_progress else 0
                    }
                } for section in sections
            ],
            'enrollment': {
                'id': str(enrollment.id),
                'status': enrollment.status,
                'completion_percentage': float(enrollment.completion_percentage or 0),
                'enrolled_at': enrollment.enrolled_at.isoformat(),
                'started_at': enrollment.started_at.isoformat() if enrollment.started_at else None,
                'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None,
                'last_accessed_at': enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None,
                'total_time_spent_minutes': enrollment.total_time_spent_minutes or 0
            } if enrollment else None
        }
        
        return jsonify(module_data)
        
    except Exception as e:
        logger.error("Failed to get training module", module_id=module_id, error=str(e))
        return jsonify({'error': 'Failed to retrieve training module'}), 500


@training_bp.route('/modules/search', methods=['GET'])
@jwt_required()
def search_training_modules():
    """Search training modules with advanced filtering."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        query_text = request.args.get('q', '')
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        content_type = request.args.get('content_type')
        
        if not query_text:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Use training service for advanced search
        results = training_service.search_modules(
            tenant_id=user.tenant_id,
            query=query_text,
            filters={
                'category': category,
                'difficulty': difficulty,
                'content_type': content_type
            },
            user_id=user_id
        )
        
        return jsonify({'results': results})
        
    except Exception as e:
        logger.error("Failed to search training modules", error=str(e))
        return jsonify({'error': 'Search failed'}), 500


# ============================================================================
# ENROLLMENTS AND PROGRESS
# ============================================================================

@training_bp.route('/enrollments', methods=['GET'])
@jwt_required()
def get_user_enrollments():
    """Get user's training enrollments."""
    try:
        user_id = get_jwt_identity()
        
        enrollments = TrainingEnrollment.query.filter(
            TrainingEnrollment.user_id == user_id
        ).options(
            joinedload(TrainingEnrollment.module)
        ).all()
        
        enrollments_data = []
        for enrollment in enrollments:
            enrollment_data = {
                'id': str(enrollment.id),
                'module_id': str(enrollment.module_id),
                'module_title': enrollment.module.title,
                'module_category': enrollment.module.category,
                'status': enrollment.status,
                'completion_percentage': float(enrollment.completion_percentage or 0),
                'enrolled_at': enrollment.enrolled_at.isoformat(),
                'started_at': enrollment.started_at.isoformat() if enrollment.started_at else None,
                'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None,
                'last_accessed_at': enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None,
                'total_time_spent_minutes': enrollment.total_time_spent_minutes or 0,
                'target_completion_date': enrollment.target_completion_date.isoformat() if enrollment.target_completion_date else None
            }
            enrollments_data.append(enrollment_data)
        
        return jsonify({'enrollments': enrollments_data})
        
    except Exception as e:
        logger.error("Failed to get user enrollments", user_id=user_id, error=str(e))
        return jsonify({'error': 'Failed to retrieve enrollments'}), 500


@training_bp.route('/enrollments', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'module_id': {'type': 'string'},
        'target_completion_date': {'type': 'string', 'format': 'date-time'}
    },
    'required': ['module_id']
})
def enroll_in_module():
    """Enroll user in a training module."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        module_id = data['module_id']
        target_completion_date = data.get('target_completion_date')
        
        # Check if module exists and is accessible
        module = TrainingModule.query.filter(
            TrainingModule.id == module_id,
            TrainingModule.tenant_id == user.tenant_id,
            TrainingModule.is_active == True
        ).first()
        
        if not module:
            return jsonify({'error': 'Module not found or not accessible'}), 404
        
        # Check if already enrolled
        existing_enrollment = TrainingEnrollment.query.filter(
            TrainingEnrollment.user_id == user_id,
            TrainingEnrollment.module_id == module_id
        ).first()
        
        if existing_enrollment:
            return jsonify({'error': 'Already enrolled in this module'}), 400
        
        # Create enrollment
        enrollment = TrainingEnrollment(
            user_id=user_id,
            module_id=module_id,
            target_completion_date=datetime.fromisoformat(target_completion_date.replace('Z', '+00:00')) if target_completion_date else None,
            status='enrolled'
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        # Track analytics event
        analytics_service.track_event(
            user_id=user_id,
            tenant_id=user.tenant_id,
            event_type='module_enrollment',
            event_data={'module_id': module_id},
            module_id=module_id
        )
        
        return jsonify({
            'id': str(enrollment.id),
            'message': 'Successfully enrolled in module'
        }), 201
        
    except Exception as e:
        logger.error("Failed to enroll in module", user_id=user_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to enroll in module'}), 500


@training_bp.route('/enrollments/<enrollment_id>/sections/<section_id>/progress', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'status': {'type': 'string', 'enum': ['not_started', 'in_progress', 'completed', 'skipped']},
        'time_spent_minutes': {'type': 'integer', 'minimum': 0},
        'last_position': {'type': 'string'},
        'notes': {'type': 'string'},
        'interactions': {'type': 'object'}
    }
})
def update_section_progress(enrollment_id, section_id):
    """Update progress for a training section."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verify enrollment belongs to user
        enrollment = TrainingEnrollment.query.filter(
            TrainingEnrollment.id == enrollment_id,
            TrainingEnrollment.user_id == user_id
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        # Get or create section progress
        section_progress = TrainingSectionProgress.query.filter(
            TrainingSectionProgress.enrollment_id == enrollment_id,
            TrainingSectionProgress.section_id == section_id
        ).first()
        
        if not section_progress:
            section_progress = TrainingSectionProgress(
                enrollment_id=enrollment_id,
                section_id=section_id
            )
            db.session.add(section_progress)
        
        # Update progress
        if 'status' in data:
            section_progress.status = data['status']
            
            if data['status'] == 'in_progress' and not section_progress.started_at:
                section_progress.started_at = datetime.utcnow()
            elif data['status'] == 'completed' and not section_progress.completed_at:
                section_progress.completed_at = datetime.utcnow()
        
        if 'time_spent_minutes' in data:
            section_progress.time_spent_minutes = (section_progress.time_spent_minutes or 0) + data['time_spent_minutes']
        
        if 'last_position' in data:
            section_progress.last_position = data['last_position']
        
        if 'notes' in data:
            section_progress.notes = data['notes']
        
        if 'interactions' in data:
            section_progress.interactions = data['interactions']
        
        # Update enrollment last accessed time
        enrollment.last_accessed_at = datetime.utcnow()
        
        # Update overall enrollment progress
        training_service.update_enrollment_progress(enrollment_id)
        
        db.session.commit()
        
        # Track analytics
        analytics_service.track_event(
            user_id=user_id,
            tenant_id=enrollment.module.tenant_id,
            event_type='section_progress_update',
            event_data={
                'section_id': section_id,
                'status': data.get('status'),
                'time_spent': data.get('time_spent_minutes', 0)
            },
            module_id=enrollment.module_id,
            section_id=section_id
        )
        
        return jsonify({'message': 'Section progress updated successfully'})
        
    except Exception as e:
        logger.error("Failed to update section progress", enrollment_id=enrollment_id, section_id=section_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to update section progress'}), 500


# ============================================================================
# BOOKMARKS
# ============================================================================

@training_bp.route('/bookmarks', methods=['GET'])
@jwt_required()
def get_user_bookmarks():
    """Get user's training bookmarks."""
    try:
        user_id = get_jwt_identity()
        
        bookmarks = TrainingBookmark.query.filter(
            TrainingBookmark.user_id == user_id
        ).options(
            joinedload(TrainingBookmark.module),
            joinedload(TrainingBookmark.section)
        ).order_by(desc(TrainingBookmark.created_at)).all()
        
        bookmarks_data = []
        for bookmark in bookmarks:
            bookmark_data = {
                'id': str(bookmark.id),
                'title': bookmark.title,
                'description': bookmark.description,
                'bookmark_type': bookmark.bookmark_type,
                'position_data': bookmark.position_data,
                'tags': bookmark.tags,
                'created_at': bookmark.created_at.isoformat(),
                'module': {
                    'id': str(bookmark.module.id),
                    'title': bookmark.module.title,
                    'category': bookmark.module.category
                } if bookmark.module else None,
                'section': {
                    'id': str(bookmark.section.id),
                    'title': bookmark.section.title
                } if bookmark.section else None
            }
            bookmarks_data.append(bookmark_data)
        
        return jsonify({'bookmarks': bookmarks_data})
        
    except Exception as e:
        logger.error("Failed to get user bookmarks", user_id=user_id, error=str(e))
        return jsonify({'error': 'Failed to retrieve bookmarks'}), 500


@training_bp.route('/bookmarks', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'module_id': {'type': 'string'},
        'section_id': {'type': 'string'},
        'title': {'type': 'string'},
        'description': {'type': 'string'},
        'bookmark_type': {'type': 'string', 'enum': ['module', 'section', 'position']},
        'position_data': {'type': 'object'},
        'tags': {'type': 'array', 'items': {'type': 'string'}}
    },
    'required': ['title']
})
def create_bookmark():
    """Create a new training bookmark."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        bookmark = TrainingBookmark(
            user_id=user_id,
            module_id=data.get('module_id'),
            section_id=data.get('section_id'),
            title=data['title'],
            description=data.get('description'),
            bookmark_type=data.get('bookmark_type', 'section'),
            position_data=data.get('position_data', {}),
            tags=data.get('tags', [])
        )
        
        db.session.add(bookmark)
        db.session.commit()
        
        return jsonify({
            'id': str(bookmark.id),
            'message': 'Bookmark created successfully'
        }), 201
        
    except Exception as e:
        logger.error("Failed to create bookmark", user_id=user_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to create bookmark'}), 500


@training_bp.route('/bookmarks/<bookmark_id>', methods=['DELETE'])
@jwt_required()
def delete_bookmark(bookmark_id):
    """Delete a training bookmark."""
    try:
        user_id = get_jwt_identity()
        
        bookmark = TrainingBookmark.query.filter(
            TrainingBookmark.id == bookmark_id,
            TrainingBookmark.user_id == user_id
        ).first()
        
        if not bookmark:
            return jsonify({'error': 'Bookmark not found'}), 404
        
        db.session.delete(bookmark)
        db.session.commit()
        
        return jsonify({'message': 'Bookmark deleted successfully'})

    except Exception as e:
        logger.error("Failed to delete bookmark", bookmark_id=bookmark_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to delete bookmark'}), 500


# ============================================================================
# CERTIFICATES
# ============================================================================

@training_bp.route('/certificates', methods=['GET'])
@jwt_required()
def get_user_certificates():
    """Get user's training certificates."""
    try:
        user_id = get_jwt_identity()

        certificates = TrainingCertificate.query.filter(
            TrainingCertificate.user_id == user_id
        ).options(
            joinedload(TrainingCertificate.module),
            joinedload(TrainingCertificate.enrollment)
        ).order_by(desc(TrainingCertificate.issued_at)).all()

        certificates_data = []
        for cert in certificates:
            cert_data = {
                'id': str(cert.id),
                'certificate_number': cert.certificate_number,
                'certificate_type': cert.certificate_type,
                'issued_at': cert.issued_at.isoformat(),
                'expires_at': cert.expires_at.isoformat() if cert.expires_at else None,
                'final_score': float(cert.final_score) if cert.final_score else None,
                'verification_code': cert.verification_code,
                'is_valid': cert.is_valid,
                'module_title': cert.module.title,
                'module_category': cert.module.category,
                'user_name': cert.user.full_name
            }
            certificates_data.append(cert_data)

        return jsonify({'certificates': certificates_data})

    except Exception as e:
        logger.error("Failed to get user certificates", user_id=user_id, error=str(e))
        return jsonify({'error': 'Failed to retrieve certificates'}), 500


@training_bp.route('/certificates/generate', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'enrollment_id': {'type': 'string'}
    },
    'required': ['enrollment_id']
})
def generate_certificate():
    """Generate a certificate for completed training."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        enrollment_id = data['enrollment_id']

        # Verify enrollment and completion
        enrollment = TrainingEnrollment.query.filter(
            TrainingEnrollment.id == enrollment_id,
            TrainingEnrollment.user_id == user_id,
            TrainingEnrollment.status == 'completed'
        ).first()

        if not enrollment:
            return jsonify({'error': 'Enrollment not found or not completed'}), 404

        # Check if certificate already exists
        existing_cert = TrainingCertificate.query.filter(
            TrainingCertificate.enrollment_id == enrollment_id
        ).first()

        if existing_cert:
            return jsonify({'error': 'Certificate already exists for this enrollment'}), 400

        # Generate certificate using service
        certificate = certificate_service.generate_certificate(enrollment_id)

        return jsonify({
            'id': str(certificate.id),
            'certificate_number': certificate.certificate_number,
            'verification_code': certificate.verification_code,
            'message': 'Certificate generated successfully'
        }), 201

    except Exception as e:
        logger.error("Failed to generate certificate", enrollment_id=enrollment_id, error=str(e))
        return jsonify({'error': 'Failed to generate certificate'}), 500


@training_bp.route('/certificates/<certificate_id>/download', methods=['GET'])
@jwt_required()
def download_certificate(certificate_id):
    """Download a certificate file."""
    try:
        user_id = get_jwt_identity()
        format_type = request.args.get('format', 'pdf')

        certificate = TrainingCertificate.query.filter(
            TrainingCertificate.id == certificate_id,
            TrainingCertificate.user_id == user_id
        ).first()

        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404

        # Generate certificate file using service
        file_path = certificate_service.generate_certificate_file(certificate, format_type)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"certificate-{certificate.certificate_number}.{format_type}"
        )

    except Exception as e:
        logger.error("Failed to download certificate", certificate_id=certificate_id, error=str(e))
        return jsonify({'error': 'Failed to download certificate'}), 500


@training_bp.route('/certificates/verify/<verification_code>', methods=['GET'])
def verify_certificate(verification_code):
    """Verify a certificate using verification code."""
    try:
        certificate = TrainingCertificate.query.filter(
            TrainingCertificate.verification_code == verification_code,
            TrainingCertificate.is_valid == True
        ).options(
            joinedload(TrainingCertificate.user),
            joinedload(TrainingCertificate.module)
        ).first()

        if not certificate:
            return jsonify({
                'valid': False,
                'error': 'Certificate not found or invalid'
            }), 404

        # Check if expired
        if certificate.expires_at and certificate.expires_at < datetime.utcnow():
            return jsonify({
                'valid': False,
                'error': 'Certificate has expired'
            }), 400

        return jsonify({
            'valid': True,
            'certificate_number': certificate.certificate_number,
            'user_name': certificate.user.full_name,
            'module_title': certificate.module.title,
            'issued_at': certificate.issued_at.isoformat(),
            'expires_at': certificate.expires_at.isoformat() if certificate.expires_at else None,
            'final_score': float(certificate.final_score) if certificate.final_score else None
        })

    except Exception as e:
        logger.error("Failed to verify certificate", verification_code=verification_code, error=str(e))
        return jsonify({'error': 'Verification failed'}), 500


# ============================================================================
# DISCUSSIONS
# ============================================================================

@training_bp.route('/modules/<module_id>/discussions', methods=['GET'])
@jwt_required()
def get_module_discussions(module_id):
    """Get discussions for a training module."""
    try:
        user_id = get_jwt_identity()
        section_id = request.args.get('section_id')

        query = TrainingDiscussion.query.filter(
            TrainingDiscussion.module_id == module_id,
            TrainingDiscussion.parent_id.is_(None)  # Only top-level discussions
        )

        if section_id:
            query = query.filter(TrainingDiscussion.section_id == section_id)

        discussions = query.options(
            joinedload(TrainingDiscussion.user),
            joinedload(TrainingDiscussion.replies)
        ).order_by(desc(TrainingDiscussion.created_at)).all()

        discussions_data = []
        for discussion in discussions:
            # Get user's vote
            user_vote = TrainingDiscussionVote.query.filter(
                TrainingDiscussionVote.discussion_id == discussion.id,
                TrainingDiscussionVote.user_id == user_id
            ).first()

            discussion_data = {
                'id': str(discussion.id),
                'title': discussion.title,
                'content': discussion.content,
                'discussion_type': discussion.discussion_type,
                'is_pinned': discussion.is_pinned,
                'is_resolved': discussion.is_resolved,
                'upvotes': discussion.upvotes,
                'downvotes': discussion.downvotes,
                'user_vote': user_vote.vote_type if user_vote else None,
                'user_name': discussion.user.full_name,
                'created_at': discussion.created_at.isoformat(),
                'replies': [
                    {
                        'id': str(reply.id),
                        'content': reply.content,
                        'user_name': reply.user.full_name,
                        'created_at': reply.created_at.isoformat()
                    } for reply in discussion.replies
                ]
            }
            discussions_data.append(discussion_data)

        return jsonify({'discussions': discussions_data})

    except Exception as e:
        logger.error("Failed to get module discussions", module_id=module_id, error=str(e))
        return jsonify({'error': 'Failed to retrieve discussions'}), 500


@training_bp.route('/discussions', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'module_id': {'type': 'string'},
        'section_id': {'type': 'string'},
        'title': {'type': 'string'},
        'content': {'type': 'string'},
        'discussion_type': {'type': 'string', 'enum': ['question', 'comment', 'answer', 'tip']}
    },
    'required': ['module_id', 'content', 'discussion_type']
})
def create_discussion():
    """Create a new discussion post."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        discussion = TrainingDiscussion(
            module_id=data['module_id'],
            section_id=data.get('section_id'),
            user_id=user_id,
            title=data.get('title'),
            content=data['content'],
            discussion_type=data['discussion_type']
        )

        db.session.add(discussion)
        db.session.commit()

        return jsonify({
            'id': str(discussion.id),
            'message': 'Discussion created successfully'
        }), 201

    except Exception as e:
        logger.error("Failed to create discussion", user_id=user_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to create discussion'}), 500


@training_bp.route('/discussions/<discussion_id>/vote', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'vote_type': {'type': 'string', 'enum': ['upvote', 'downvote']}
    },
    'required': ['vote_type']
})
def vote_on_discussion(discussion_id):
    """Vote on a discussion post."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        vote_type = data['vote_type']

        # Check if user already voted
        existing_vote = TrainingDiscussionVote.query.filter(
            TrainingDiscussionVote.discussion_id == discussion_id,
            TrainingDiscussionVote.user_id == user_id
        ).first()

        discussion = TrainingDiscussion.query.get(discussion_id)
        if not discussion:
            return jsonify({'error': 'Discussion not found'}), 404

        if existing_vote:
            # Update existing vote
            if existing_vote.vote_type != vote_type:
                # Change vote type
                if existing_vote.vote_type == 'upvote':
                    discussion.upvotes = max(0, discussion.upvotes - 1)
                else:
                    discussion.downvotes = max(0, discussion.downvotes - 1)

                existing_vote.vote_type = vote_type

                if vote_type == 'upvote':
                    discussion.upvotes += 1
                else:
                    discussion.downvotes += 1
            # If same vote type, remove vote
            else:
                if vote_type == 'upvote':
                    discussion.upvotes = max(0, discussion.upvotes - 1)
                else:
                    discussion.downvotes = max(0, discussion.downvotes - 1)

                db.session.delete(existing_vote)
        else:
            # Create new vote
            vote = TrainingDiscussionVote(
                discussion_id=discussion_id,
                user_id=user_id,
                vote_type=vote_type
            )
            db.session.add(vote)

            if vote_type == 'upvote':
                discussion.upvotes += 1
            else:
                discussion.downvotes += 1

        db.session.commit()

        return jsonify({'message': 'Vote recorded successfully'})

    except Exception as e:
        logger.error("Failed to vote on discussion", discussion_id=discussion_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Failed to record vote'}), 500


# ============================================================================
# ANALYTICS
# ============================================================================

@training_bp.route('/analytics/user', methods=['GET'])
@jwt_required()
def get_user_analytics():
    """Get user training analytics."""
    try:
        user_id = get_jwt_identity()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Use analytics service to get comprehensive data
        analytics_data = analytics_service.get_user_analytics(
            user_id=user_id,
            start_date=datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None,
            end_date=datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        )

        return jsonify(analytics_data)

    except Exception as e:
        logger.error("Failed to get user analytics", user_id=user_id, error=str(e))
        return jsonify({'error': 'Failed to retrieve analytics'}), 500


@training_bp.route('/analytics/events', methods=['POST'])
@jwt_required()
@validate_json_schema({
    'type': 'object',
    'properties': {
        'event_type': {'type': 'string'},
        'event_data': {'type': 'object'},
        'module_id': {'type': 'string'},
        'section_id': {'type': 'string'}
    },
    'required': ['event_type']
})
def track_analytics_event():
    """Track a training analytics event."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()

        # Track event using analytics service
        analytics_service.track_event(
            user_id=user_id,
            tenant_id=user.tenant_id,
            event_type=data['event_type'],
            event_data=data.get('event_data', {}),
            module_id=data.get('module_id'),
            section_id=data.get('section_id')
        )

        return jsonify({'message': 'Event tracked successfully'})

    except Exception as e:
        logger.error("Failed to track analytics event", user_id=user_id, error=str(e))
        return jsonify({'error': 'Failed to track event'}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@training_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@training_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401


@training_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403


@training_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@training_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
