"""
Regulens AI - UI Portals API Routes
Enterprise-grade API endpoints for UI portal management, testing, and analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import get_current_user, require_permission
from core_infra.api.middleware import rate_limit, audit_log
from core_infra.ui.portal_manager import (
    portal_session_manager, portal_search_manager, portal_analytics_manager,
    PortalType, EventType, create_portal_session, search_documentation, get_portal_analytics
)
from core_infra.ui.testing_portal import (
    api_test_executor, test_suite_manager, performance_test_manager, test_report_generator,
    TestType, execute_api_test, execute_test_suite, execute_load_test, generate_test_report
)
from core_infra.exceptions import BusinessLogicException, DataValidationException

# Initialize logging
logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/ui", tags=["UI Portals"])

# Pydantic models
class CreateSessionRequest(BaseModel):
    portal_type: str = Field(..., description="Portal type (documentation, testing, analytics, admin)")
    user_agent: Optional[str] = Field(None, description="User agent string")

class CreateSessionResponse(BaseModel):
    session_id: str
    portal_type: str
    expires_at: Optional[datetime]
    created_at: datetime

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    search_type: str = Field(default="all", description="Search type (all, api, guides, tutorials)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")

class SearchResponse(BaseModel):
    query: str
    results: Dict[str, Any]
    execution_time_ms: int
    total_count: int

class APITestRequest(BaseModel):
    endpoint_path: str = Field(..., description="API endpoint path")
    http_method: str = Field(..., description="HTTP method")
    request_data: Dict[str, Any] = Field(default_factory=dict, description="Request data")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Response validation rules")

class APITestResponse(BaseModel):
    test_id: str
    success: bool
    response_status_code: Optional[int]
    response_time_ms: Optional[int]
    error_message: Optional[str]
    executed_at: datetime

class TestSuiteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Test suite name")
    description: str = Field(..., max_length=1000, description="Test suite description")
    tests: List[Dict[str, Any]] = Field(..., description="List of test configurations")

class LoadTestRequest(BaseModel):
    endpoint_path: str = Field(..., description="API endpoint path")
    http_method: str = Field(..., description="HTTP method")
    request_data: Dict[str, Any] = Field(default_factory=dict, description="Request data")
    concurrent_users: int = Field(..., ge=1, le=100, description="Number of concurrent users")
    duration_seconds: int = Field(..., ge=1, le=300, description="Test duration in seconds")

# Portal Session Management Routes

@router.post("/sessions", response_model=CreateSessionResponse)
@rate_limit(requests_per_minute=60)
@audit_log("ui_session_create")
async def create_ui_session(
    request: CreateSessionRequest,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new UI portal session."""
    try:
        # Validate portal type
        try:
            portal_type = PortalType(request.portal_type)
        except ValueError:
            raise DataValidationException(f"Invalid portal type: {request.portal_type}")
        
        # Get client IP
        client_ip = http_request.client.host
        
        # Create session
        session = await create_portal_session(
            portal_type=portal_type,
            user_id=current_user.get("id"),
            tenant_id=current_user["tenant_id"],
            ip_address=client_ip,
            user_agent=request.user_agent
        )
        
        return CreateSessionResponse(
            session_id=session.session_id,
            portal_type=session.portal_type.value,
            expires_at=session.expires_at,
            created_at=session.started_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create UI session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}")
@rate_limit(requests_per_minute=120)
async def get_ui_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get UI portal session information."""
    try:
        session = await portal_session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify session belongs to current tenant
        if session.tenant_id != current_user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "session_id": session.session_id,
            "portal_type": session.portal_type.value,
            "user_id": session.user_id,
            "started_at": session.started_at,
            "last_activity_at": session.last_activity_at,
            "expires_at": session.expires_at,
            "is_active": session.is_active,
            "session_data": session.session_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get UI session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sessions/{session_id}/activity")
@rate_limit(requests_per_minute=300)
async def update_session_activity(
    session_id: str,
    session_data: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update session activity and data."""
    try:
        success = await portal_session_manager.update_session_activity(session_id, session_data)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        return {"success": True, "updated_at": datetime.utcnow()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
@rate_limit(requests_per_minute=60)
@audit_log("ui_session_end")
async def end_ui_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """End a UI portal session."""
    try:
        success = await portal_session_manager.end_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "ended_at": datetime.utcnow()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end UI session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Documentation Portal Routes

@router.post("/documentation/search", response_model=SearchResponse)
@rate_limit(requests_per_minute=100)
@audit_log("documentation_search")
async def search_documentation_portal(
    request: SearchRequest,
    session_id: str = Query(..., description="Portal session ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search documentation portal content."""
    try:
        # Validate session
        session = await portal_session_manager.get_session(session_id)
        if not session or session.portal_type != PortalType.DOCUMENTATION:
            raise HTTPException(status_code=400, detail="Invalid documentation portal session")
        
        # Perform search
        results = await search_documentation(
            query=request.query,
            search_type=request.search_type,
            filters=request.filters,
            session_id=session_id,
            tenant_id=current_user["tenant_id"]
        )
        
        return SearchResponse(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Documentation search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Testing Portal Routes

@router.post("/testing/api-test", response_model=APITestResponse)
@rate_limit(requests_per_minute=50)
@audit_log("api_test_execution")
@require_permission("ai.analysis.trigger")
async def execute_api_test_endpoint(
    request: APITestRequest,
    session_id: str = Query(..., description="Portal session ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Execute an API test."""
    try:
        # Validate session
        session = await portal_session_manager.get_session(session_id)
        if not session or session.portal_type != PortalType.TESTING:
            raise HTTPException(status_code=400, detail="Invalid testing portal session")
        
        # Execute test
        test_result = await execute_api_test(
            session_id=session_id,
            tenant_id=current_user["tenant_id"],
            endpoint_path=request.endpoint_path,
            http_method=request.http_method,
            request_data=request.request_data,
            headers=request.headers,
            validation_rules=request.validation_rules
        )
        
        return APITestResponse(
            test_id=test_result.id,
            success=test_result.success,
            response_status_code=test_result.response_status_code,
            response_time_ms=test_result.response_time_ms,
            error_message=test_result.error_message,
            executed_at=test_result.executed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API test execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/testing/test-suite")
@rate_limit(requests_per_minute=20)
@audit_log("test_suite_create")
@require_permission("ai.analysis.trigger")
async def create_test_suite_endpoint(
    request: TestSuiteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new test suite."""
    try:
        test_suite = await test_suite_manager.create_test_suite(
            name=request.name,
            description=request.description,
            tests=request.tests,
            tenant_id=current_user["tenant_id"],
            created_by=current_user["id"]
        )
        
        return {
            "suite_id": test_suite.id,
            "name": test_suite.name,
            "description": test_suite.description,
            "test_count": len(test_suite.tests),
            "created_at": test_suite.created_at
        }
        
    except Exception as e:
        logger.error(f"Test suite creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/testing/test-suite/{suite_id}/execute")
@rate_limit(requests_per_minute=10)
@audit_log("test_suite_execution")
@require_permission("ai.analysis.trigger")
async def execute_test_suite_endpoint(
    suite_id: str,
    session_id: str = Query(..., description="Portal session ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Execute a test suite."""
    try:
        # Validate session
        session = await portal_session_manager.get_session(session_id)
        if not session or session.portal_type != PortalType.TESTING:
            raise HTTPException(status_code=400, detail="Invalid testing portal session")
        
        # Execute test suite
        results = await execute_test_suite(
            suite_id=suite_id,
            session_id=session_id,
            tenant_id=current_user["tenant_id"]
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/testing/load-test")
@rate_limit(requests_per_minute=5)
@audit_log("load_test_execution")
@require_permission("ai.analysis.trigger")
async def execute_load_test_endpoint(
    request: LoadTestRequest,
    session_id: str = Query(..., description="Portal session ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Execute a load test."""
    try:
        # Validate session
        session = await portal_session_manager.get_session(session_id)
        if not session or session.portal_type != PortalType.TESTING:
            raise HTTPException(status_code=400, detail="Invalid testing portal session")
        
        # Execute load test
        results = await execute_load_test(
            endpoint_path=request.endpoint_path,
            http_method=request.http_method,
            request_data=request.request_data,
            concurrent_users=request.concurrent_users,
            duration_seconds=request.duration_seconds,
            session_id=session_id,
            tenant_id=current_user["tenant_id"]
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Load test execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/testing/reports")
@rate_limit(requests_per_minute=30)
@require_permission("reports.read")
async def get_test_reports(
    start_date: Optional[datetime] = Query(None, description="Start date for report"),
    end_date: Optional[datetime] = Query(None, description="End date for report"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get test execution reports."""
    try:
        report = await generate_test_report(
            tenant_id=current_user["tenant_id"],
            start_date=start_date,
            end_date=end_date
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Test report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Routes

@router.get("/analytics/portal")
@rate_limit(requests_per_minute=60)
@require_permission("reports.read")
async def get_portal_analytics_endpoint(
    portal_type: Optional[str] = Query(None, description="Portal type filter"),
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get portal usage analytics."""
    try:
        # Validate portal type if provided
        portal_type_enum = None
        if portal_type:
            try:
                portal_type_enum = PortalType(portal_type)
            except ValueError:
                raise DataValidationException(f"Invalid portal type: {portal_type}")
        
        analytics = await get_portal_analytics(
            tenant_id=current_user["tenant_id"],
            portal_type=portal_type_enum
        )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portal analytics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def ui_portals_health():
    """Health check for UI portals service."""
    try:
        # Check if managers are initialized
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "portal_session_manager": "healthy",
                "portal_search_manager": "healthy",
                "portal_analytics_manager": "healthy",
                "api_test_executor": "healthy",
                "test_suite_manager": "healthy",
                "performance_test_manager": "healthy",
                "test_report_generator": "healthy"
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"UI portals health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
