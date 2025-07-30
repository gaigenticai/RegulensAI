"""
RegulensAI Disaster Recovery API Routes
Web API endpoints for DR management, testing, and monitoring integration.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from core_infra.auth.dependencies import get_current_user, require_permission
from core_infra.disaster_recovery.dr_manager import (
    dr_manager,
    get_dr_status,
    run_dr_test,
    run_full_dr_test,
    DRTestType,
    DRStatus,
    DRSeverity
)
from core_infra.logging.centralized_logging import get_centralized_logger, LogCategory
from core_infra.monitoring.apm_integration import apm_manager
from core_infra.monitoring.apm_decorators import apm_track_api
from core_infra.notification.notification_service import notification_service


logger = structlog.get_logger(__name__)
router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DRTestRequest(BaseModel):
    """DR test execution request."""
    component: str = Field(..., description="Component to test")
    test_type: str = Field(..., description="Type of DR test")
    dry_run: bool = Field(default=True, description="Whether to run in dry-run mode")
    notify_on_completion: bool = Field(default=True, description="Send notification on completion")


class DRTestResponse(BaseModel):
    """DR test execution response."""
    test_id: str
    status: str
    message: str
    estimated_duration_minutes: Optional[int] = None


class DRStatusResponse(BaseModel):
    """DR status response."""
    overall_status: str
    health_score: float
    components: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    recent_tests: List[Dict[str, Any]]
    last_updated: str


class DREventResponse(BaseModel):
    """DR event response."""
    event_id: str
    timestamp: str
    event_type: str
    severity: str
    component: str
    description: str
    status: str
    recovery_actions: List[str]


class DRComponentResponse(BaseModel):
    """DR component status response."""
    component: str
    status: str
    rto_minutes: int
    rpo_minutes: int
    priority: int
    automated_recovery: bool
    last_test_time: Optional[str]
    last_backup_time: Optional[str]
    dependencies: List[str]


# ============================================================================
# DR STATUS AND MONITORING ENDPOINTS
# ============================================================================

@router.get("/status", response_model=DRStatusResponse)
@apm_track_api("get_dr_status")
async def get_disaster_recovery_status(
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:read"))
):
    """Get comprehensive disaster recovery status."""
    try:
        status = await get_dr_status()
        
        return DRStatusResponse(
            overall_status=status["overall_status"],
            health_score=status["health_score"],
            components=status["components"],
            recent_events=status["recent_events"],
            recent_tests=status["recent_tests"],
            last_updated=status["last_updated"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get DR status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DR status")


@router.get("/components", response_model=List[DRComponentResponse])
@apm_track_api("get_dr_components")
async def get_dr_components(
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:read"))
):
    """Get detailed status of all DR components."""
    try:
        status = await get_dr_status()
        components = []
        
        for component_name, component_data in status["components"].items():
            components.append(DRComponentResponse(
                component=component_name,
                status=component_data["status"],
                rto_minutes=component_data["rto_minutes"],
                rpo_minutes=component_data["rpo_minutes"],
                priority=component_data["priority"],
                automated_recovery=component_data["automated_recovery"],
                last_test_time=component_data["last_test_time"],
                last_backup_time=component_data["last_backup_time"],
                dependencies=component_data["dependencies"]
            ))
        
        # Sort by priority
        components.sort(key=lambda x: x.priority)
        
        return components
        
    except Exception as e:
        logger.error(f"Failed to get DR components: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DR components")


@router.get("/events", response_model=List[DREventResponse])
@apm_track_api("get_dr_events")
async def get_dr_events(
    limit: int = Query(default=50, le=200, description="Maximum number of events to return"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    component: Optional[str] = Query(default=None, description="Filter by component"),
    hours: Optional[int] = Query(default=24, description="Hours of history to include"),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:read"))
):
    """Get DR events with filtering options."""
    try:
        status = await get_dr_status()
        events = status["recent_events"]
        
        # Apply filters
        if severity:
            events = [e for e in events if e.get("severity") == severity]
        
        if component:
            events = [e for e in events if e.get("component") == component]
        
        if hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            events = [
                e for e in events 
                if datetime.fromisoformat(e.get("timestamp", "")) > cutoff_time
            ]
        
        # Limit results
        events = events[:limit]
        
        return [
            DREventResponse(
                event_id=event["event_id"],
                timestamp=event["timestamp"],
                event_type=event["event_type"],
                severity=event["severity"],
                component=event["component"],
                description=event["description"],
                status=event["status"],
                recovery_actions=event.get("recovery_actions", [])
            )
            for event in events
        ]
        
    except Exception as e:
        logger.error(f"Failed to get DR events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DR events")


@router.get("/health-score")
@apm_track_api("get_dr_health_score")
async def get_dr_health_score(
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:read"))
):
    """Get DR health score and breakdown."""
    try:
        status = await get_dr_status()
        
        # Calculate component scores
        component_scores = {}
        for component_name, component_data in status["components"].items():
            if component_data["status"] == "healthy":
                score = 100
            elif component_data["status"] == "warning":
                score = 70
            elif component_data["status"] == "testing":
                score = 85
            else:
                score = 0
            
            component_scores[component_name] = {
                "score": score,
                "status": component_data["status"],
                "priority": component_data["priority"]
            }
        
        return {
            "overall_score": status["health_score"],
            "component_scores": component_scores,
            "status": status["overall_status"],
            "last_updated": status["last_updated"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get DR health score: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DR health score")


# ============================================================================
# DR TESTING ENDPOINTS
# ============================================================================

@router.post("/test", response_model=DRTestResponse)
@apm_track_api("run_dr_test")
async def run_disaster_recovery_test(
    request: DRTestRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:test"))
):
    """Run disaster recovery test for specific component."""
    try:
        # Validate test type
        try:
            test_type = DRTestType(request.test_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid test type: {request.test_type}"
            )
        
        # Validate component
        status = await get_dr_status()
        if request.component not in status["components"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown component: {request.component}"
            )
        
        # Estimate duration based on test type and component
        estimated_duration = _estimate_test_duration(request.component, test_type)
        
        # Run test in background
        background_tasks.add_task(
            _execute_dr_test_background,
            request.component,
            request.test_type,
            request.dry_run,
            request.notify_on_completion,
            current_user.id
        )
        
        # Log test initiation
        dr_logger = await get_centralized_logger("dr_api")
        await dr_logger.info(
            f"DR test initiated: {request.component} - {request.test_type}",
            category=LogCategory.SYSTEM,
            component=request.component,
            test_type=request.test_type,
            dry_run=request.dry_run,
            user_id=current_user.id
        )
        
        return DRTestResponse(
            test_id=f"{request.component}_{request.test_type}_{int(datetime.utcnow().timestamp())}",
            status="initiated",
            message=f"DR test started for {request.component}",
            estimated_duration_minutes=estimated_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate DR test: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate DR test")


@router.post("/test/full", response_model=DRTestResponse)
@apm_track_api("run_full_dr_test")
async def run_full_disaster_recovery_test(
    dry_run: bool = Query(default=True, description="Whether to run in dry-run mode"),
    notify_on_completion: bool = Query(default=True, description="Send notification on completion"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:test"))
):
    """Run comprehensive disaster recovery test for all components."""
    try:
        # Run full test in background
        background_tasks.add_task(
            _execute_full_dr_test_background,
            dry_run,
            notify_on_completion,
            current_user.id
        )
        
        # Log full test initiation
        dr_logger = await get_centralized_logger("dr_api")
        await dr_logger.info(
            "Full DR test initiated",
            category=LogCategory.SYSTEM,
            dry_run=dry_run,
            user_id=current_user.id
        )
        
        return DRTestResponse(
            test_id=f"full_dr_test_{int(datetime.utcnow().timestamp())}",
            status="initiated",
            message="Full DR test started for all components",
            estimated_duration_minutes=60  # Estimate 1 hour for full test
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate full DR test: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate full DR test")


@router.get("/test/results")
@apm_track_api("get_dr_test_results")
async def get_dr_test_results(
    limit: int = Query(default=20, le=100, description="Maximum number of results to return"),
    component: Optional[str] = Query(default=None, description="Filter by component"),
    test_type: Optional[str] = Query(default=None, description="Filter by test type"),
    status: Optional[str] = Query(default=None, description="Filter by test status"),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permission("dr:read"))
):
    """Get DR test results with filtering options."""
    try:
        dr_status = await get_dr_status()
        test_results = dr_status["recent_tests"]
        
        # Apply filters
        if component:
            test_results = [t for t in test_results if t.get("component") == component]
        
        if test_type:
            test_results = [t for t in test_results if t.get("test_type") == test_type]
        
        if status:
            test_results = [t for t in test_results if t.get("status") == status]
        
        # Limit results
        test_results = test_results[:limit]
        
        return {
            "test_results": test_results,
            "total_count": len(test_results),
            "filters_applied": {
                "component": component,
                "test_type": test_type,
                "status": status
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get DR test results: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DR test results")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _estimate_test_duration(component: str, test_type: DRTestType) -> int:
    """Estimate test duration in minutes."""
    base_durations = {
        DRTestType.BACKUP_VALIDATION: 5,
        DRTestType.FAILOVER_TEST: 15,
        DRTestType.RECOVERY_TEST: 30,
        DRTestType.FULL_DR_TEST: 60
    }
    
    # Adjust based on component complexity
    component_multipliers = {
        "database": 1.5,
        "api_services": 1.0,
        "web_ui": 0.5,
        "monitoring": 1.2,
        "file_storage": 2.0
    }
    
    base_duration = base_durations.get(test_type, 10)
    multiplier = component_multipliers.get(component, 1.0)
    
    return int(base_duration * multiplier)


async def _execute_dr_test_background(
    component: str,
    test_type: str,
    dry_run: bool,
    notify_on_completion: bool,
    user_id: str
):
    """Execute DR test in background task."""
    try:
        result = await run_dr_test(component, test_type, dry_run)
        
        # Log completion
        dr_logger = await get_centralized_logger("dr_api")
        await dr_logger.info(
            f"DR test completed: {component} - {test_type}",
            category=LogCategory.SYSTEM,
            component=component,
            test_type=test_type,
            test_status=result.status,
            duration_minutes=result.duration_minutes,
            user_id=user_id
        )
        
        # Send notification if requested
        if notify_on_completion:
            await _send_test_completion_notification(result, user_id)
            
    except Exception as e:
        dr_logger = await get_centralized_logger("dr_api")
        await dr_logger.error(
            f"DR test failed in background: {component} - {test_type}",
            category=LogCategory.SYSTEM,
            error=str(e),
            user_id=user_id
        )


async def _execute_full_dr_test_background(
    dry_run: bool,
    notify_on_completion: bool,
    user_id: str
):
    """Execute full DR test in background task."""
    try:
        results = await run_full_dr_test(dry_run)
        
        # Calculate summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.status == "passed")
        failed_tests = total_tests - passed_tests
        
        # Log completion
        dr_logger = await get_centralized_logger("dr_api")
        await dr_logger.info(
            "Full DR test completed",
            category=LogCategory.SYSTEM,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            user_id=user_id
        )
        
        # Send notification if requested
        if notify_on_completion:
            await _send_full_test_completion_notification(results, user_id)
            
    except Exception as e:
        dr_logger = await get_centralized_logger("dr_api")
        await dr_logger.error(
            "Full DR test failed in background",
            category=LogCategory.SYSTEM,
            error=str(e),
            user_id=user_id
        )


async def _send_test_completion_notification(result, user_id: str):
    """Send notification for test completion."""
    await notification_service.send('DR Test Completed', f'Status: {result.status}', user_id)


async def _send_full_test_completion_notification(results: Dict, user_id: str):
    """Send notification for full test completion."""
    summary = f"Full DR test completed with {len(results)} components tested."
    await notification_service.send('Full DR Test Completed', summary, user_id)
