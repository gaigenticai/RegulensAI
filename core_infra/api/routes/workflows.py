"""
Workflows API Routes
Comprehensive API endpoints for workflow management, task orchestration, and impact assessments.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import get_current_user, verify_tenant_access
from core_infra.database.connection import get_database
from core_infra.services.workflows import (
    WorkflowOrchestrator, WorkflowEngine, TaskManager, ImpactAssessor,
    WorkflowDefinition, ComplianceTask, RegulatoryImpact
)
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()

# Initialize workflow components
workflow_orchestrator = WorkflowOrchestrator()
workflow_engine = workflow_orchestrator.workflow_engine
task_manager = workflow_orchestrator.task_manager
impact_assessor = workflow_orchestrator.impact_assessor

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class WorkflowDefinitionCreate(BaseModel):
    """Model for creating workflow definitions."""
    name: str = Field(..., description="Workflow name")
    description: str = Field("", description="Workflow description")
    category: str = Field("general", description="Workflow category")
    tasks: List[Dict[str, Any]] = Field([], description="Task definitions")
    triggers: List[Dict[str, Any]] = Field([], description="Trigger configurations")
    flow_logic: Dict[str, Any] = Field({}, description="Flow control logic")
    variables: Dict[str, Any] = Field({}, description="Default variables")
    settings: Dict[str, Any] = Field({}, description="Workflow settings")


class WorkflowTriggerCreate(BaseModel):
    """Model for creating workflow triggers."""
    name: str = Field(..., description="Trigger name")
    trigger_type: str = Field(..., description="Type of trigger")
    workflow_definition_id: str = Field(..., description="Workflow to trigger")
    conditions: Dict[str, Any] = Field({}, description="Trigger conditions")
    priority: int = Field(1, description="Trigger priority")
    cooldown_minutes: int = Field(0, description="Cooldown period in minutes")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")


class TaskCreate(BaseModel):
    """Model for creating compliance tasks."""
    title: str = Field(..., description="Task title")
    description: str = Field("", description="Task description")
    task_type: str = Field("regulatory_review", description="Type of task")
    priority: str = Field("medium", description="Task priority")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID")
    assignee_id: Optional[str] = Field(None, description="Assigned user ID")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    estimated_effort_hours: Optional[float] = Field(None, description="Estimated effort")
    requirements: List[str] = Field([], description="Task requirements")
    acceptance_criteria: List[str] = Field([], description="Acceptance criteria")
    regulatory_reference: Optional[str] = Field(None, description="Related regulation")
    tags: List[str] = Field([], description="Task tags")


class TaskUpdate(BaseModel):
    """Model for updating task progress."""
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[str] = Field(None, description="Task status")
    notes: Optional[str] = Field(None, description="Progress notes")
    evidence: List[Dict[str, Any]] = Field([], description="Evidence attachments")


class TaskComment(BaseModel):
    """Model for task comments."""
    text: str = Field(..., description="Comment text")
    is_internal: bool = Field(True, description="Internal comment flag")
    mentioned_users: List[str] = Field([], description="Mentioned user IDs")


class ImpactAssessmentRequest(BaseModel):
    """Model for requesting impact assessment."""
    regulation_id: str = Field(..., description="Regulation ID to assess")
    force_reassessment: bool = Field(False, description="Force new assessment")


class WorkflowStartRequest(BaseModel):
    """Model for starting workflows."""
    definition_id: str = Field(..., description="Workflow definition ID")
    trigger_data: Dict[str, Any] = Field({}, description="Trigger data")
    initial_variables: Dict[str, Any] = Field({}, description="Initial variables")


# ============================================================================
# WORKFLOW DEFINITION ENDPOINTS
# ============================================================================

@router.get("/definitions", response_model=List[Dict[str, Any]])
async def get_workflow_definitions(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: bool = Query(True, description="Filter by active status"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get workflow definitions."""
    try:
        async with get_database() as db:
            conditions = ["1=1"]
            params = []
            
            if category:
                conditions.append(f"category = ${len(params) + 1}")
                params.append(category)
            
            if is_active is not None:
                conditions.append(f"is_active = ${len(params) + 1}")
                params.append(is_active)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT id, name, description, version, category, is_active,
                       created_by, created_at, updated_at
                FROM workflow_definitions
                WHERE {where_clause}
                ORDER BY name
            """
            
            definitions = await db.fetch(query, *params)
            return [dict(definition) for definition in definitions]
            
    except Exception as e:
        logger.error(f"Failed to get workflow definitions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow definitions")


@router.post("/definitions", response_model=Dict[str, Any])
async def create_workflow_definition(
    definition_data: WorkflowDefinitionCreate,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Create a new workflow definition."""
    try:
        definition_id = await workflow_orchestrator.create_workflow_definition(
            definition_data.dict(),
            current_user.get('id', 'unknown')
        )
        
        return {
            "definition_id": definition_id,
            "message": "Workflow definition created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create workflow definition: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workflow definition")


@router.get("/definitions/{definition_id}", response_model=Dict[str, Any])
async def get_workflow_definition(
    definition_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get a specific workflow definition."""
    try:
        async with get_database() as db:
            query = "SELECT * FROM workflow_definitions WHERE id = $1"
            definition = await db.fetchrow(query, definition_id)
            
            if not definition:
                raise HTTPException(status_code=404, detail="Workflow definition not found")
            
            return dict(definition)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow definition")


# ============================================================================
# WORKFLOW EXECUTION ENDPOINTS
# ============================================================================

@router.post("/start", response_model=Dict[str, Any])
async def start_workflow(
    request: WorkflowStartRequest,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Start a new workflow execution."""
    try:
        workflow_id = await workflow_engine.start_workflow(
            definition_id=request.definition_id,
            triggered_by=current_user.get('id', 'unknown'),
            trigger_data=request.trigger_data,
            initial_variables=request.initial_variables
        )
        
        return {
            "workflow_id": workflow_id,
            "message": "Workflow started successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@router.get("/executions", response_model=List[Dict[str, Any]])
async def get_workflow_executions(
    definition_id: Optional[str] = Query(None, description="Filter by definition"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get workflow executions."""
    try:
        if definition_id:
            executions = await workflow_orchestrator.get_active_workflows(definition_id)
        else:
            executions = await workflow_orchestrator.get_active_workflows()
        
        # Apply status filter
        if status:
            executions = [ex for ex in executions if ex.get('status') == status]
        
        # Apply limit
        executions = executions[:limit]
        
        return executions
        
    except Exception as e:
        logger.error(f"Failed to get workflow executions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow executions")


@router.get("/executions/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_execution(
    workflow_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get a specific workflow execution."""
    try:
        execution = await workflow_orchestrator.get_workflow_status(workflow_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow execution not found")
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow execution {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow execution")


@router.post("/executions/{workflow_id}/pause", response_model=Dict[str, Any])
async def pause_workflow(
    workflow_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Pause a workflow execution."""
    try:
        success = await workflow_engine.pause_workflow(workflow_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to pause workflow")
        
        return {"message": "Workflow paused successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause workflow")


@router.post("/executions/{workflow_id}/resume", response_model=Dict[str, Any])
async def resume_workflow(
    workflow_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Resume a paused workflow execution."""
    try:
        success = await workflow_engine.resume_workflow(workflow_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to resume workflow")
        
        return {"message": "Workflow resumed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume workflow")


@router.post("/executions/{workflow_id}/cancel", response_model=Dict[str, Any])
async def cancel_workflow(
    workflow_id: str,
    reason: str = Query(..., description="Cancellation reason"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Cancel a workflow execution."""
    try:
        success = await workflow_orchestrator.cancel_workflow(
            workflow_id, reason, current_user.get('id', 'unknown')
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel workflow")
        
        return {"message": "Workflow cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel workflow")


# ============================================================================
# TASK MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/tasks", response_model=Dict[str, Any])
async def create_task(
    task_data: TaskCreate,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Create a new compliance task."""
    try:
        task_id = await task_manager.create_task(
            task_data.dict(),
            current_user.get('id', 'unknown')
        )
        
        # Auto-assign if assignee specified
        if task_data.assignee_id:
            await task_manager.assign_task(
                task_id,
                task_data.assignee_id,
                'user',
                current_user.get('id', 'unknown')
            )
        
        return {
            "task_id": task_id,
            "message": "Task created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task")


@router.get("/tasks", response_model=List[Dict[str, Any]])
async def get_tasks(
    assignee_id: Optional[str] = Query(None, description="Filter by assignee"),
    status: Optional[str] = Query(None, description="Filter by status"),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    overdue_only: bool = Query(False, description="Show only overdue tasks"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get compliance tasks with filtering."""
    try:
        # If no assignee specified, get tasks for current user
        if not assignee_id:
            assignee_id = current_user.get('id')
        
        # Get user tasks
        status_filter = [task_manager.TaskStatus(status)] if status else None
        tasks = await task_manager.get_user_tasks(assignee_id, status_filter)
        
        # Apply additional filters
        if workflow_id:
            tasks = [t for t in tasks if t.workflow_id == workflow_id]
        
        if priority:
            tasks = [t for t in tasks if t.priority.value == priority]
        
        if overdue_only:
            current_time = datetime.utcnow()
            tasks = [t for t in tasks if t.due_date and t.due_date < current_time]
        
        # Convert to API format
        task_list = []
        for task in tasks[:limit]:
            task_dict = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type.value,
                "priority": task.priority.value,
                "status": task.status.value,
                "workflow_id": task.workflow_id,
                "parent_task_id": task.parent_task_id,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "progress_percentage": task.progress_percentage,
                "assignee": task.assignment.assignee_id if task.assignment else None,
                "regulatory_reference": task.regulatory_reference,
                "tags": task.tags
            }
            task_list.append(task_dict)
        
        return task_list
        
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task(
    task_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get a specific task."""
    try:
        task = await task_manager._get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert to API format
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type.value,
            "priority": task.priority.value,
            "status": task.status.value,
            "workflow_id": task.workflow_id,
            "parent_task_id": task.parent_task_id,
            "created_by": task.created_by,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "progress_percentage": task.progress_percentage,
            "estimated_effort_hours": task.estimated_effort_hours,
            "actual_effort_hours": task.actual_effort_hours,
            "assignment": task.assignment.__dict__ if task.assignment else None,
            "requirements": task.requirements,
            "acceptance_criteria": task.acceptance_criteria,
            "required_approvals": task.required_approvals,
            "required_evidence": task.required_evidence,
            "regulatory_reference": task.regulatory_reference,
            "business_justification": task.business_justification,
            "dependencies": task.dependencies,
            "evidence": [e.__dict__ for e in task.evidence],
            "comments": [c.__dict__ for c in task.comments],
            "tags": task.tags,
            "metadata": task.metadata
        }
        
        return task_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task")


@router.post("/tasks/{task_id}/assign", response_model=Dict[str, Any])
async def assign_task(
    task_id: str,
    assignee_id: str = Query(..., description="User ID to assign task to"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Assign a task to a user."""
    try:
        success = await task_manager.assign_task(
            task_id,
            assignee_id,
            'user',
            current_user.get('id', 'unknown')
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to assign task")
        
        return {"message": "Task assigned successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign task")


@router.post("/tasks/{task_id}/start", response_model=Dict[str, Any])
async def start_task(
    task_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Start work on a task."""
    try:
        success = await task_manager.start_task(
            task_id,
            current_user.get('id', 'unknown')
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start task")
        
        return {"message": "Task started successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start task")


@router.post("/tasks/{task_id}/update", response_model=Dict[str, Any])
async def update_task_progress(
    task_id: str,
    update_data: TaskUpdate,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Update task progress."""
    try:
        if update_data.progress_percentage is not None:
            success = await task_manager.update_task_progress(
                task_id,
                update_data.progress_percentage,
                current_user.get('id', 'unknown'),
                update_data.notes or ""
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to update task progress")
        
        return {"message": "Task updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task")


@router.post("/tasks/{task_id}/complete", response_model=Dict[str, Any])
async def complete_task(
    task_id: str,
    completion_notes: str = Query("", description="Completion notes"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Complete a task."""
    try:
        success = await task_manager.complete_task(
            task_id,
            current_user.get('id', 'unknown'),
            completion_notes
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete task")
        
        return {"message": "Task completed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete task")


@router.post("/tasks/{task_id}/comments", response_model=Dict[str, Any])
async def add_task_comment(
    task_id: str,
    comment: TaskComment,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Add a comment to a task."""
    try:
        comment_id = await task_manager.add_task_comment(
            task_id,
            comment.text,
            current_user.get('id', 'unknown'),
            comment.is_internal,
            comment.mentioned_users
        )
        
        return {
            "comment_id": comment_id,
            "message": "Comment added successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to add comment to task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add comment")


@router.post("/tasks/{task_id}/escalate", response_model=Dict[str, Any])
async def escalate_task(
    task_id: str,
    reason: str = Query(..., description="Escalation reason"),
    escalate_to: Optional[str] = Query(None, description="Escalation target"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Escalate a task."""
    try:
        success = await task_manager.escalate_task(
            task_id,
            current_user.get('id', 'unknown'),
            reason,
            escalate_to
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to escalate task")
        
        return {"message": "Task escalated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to escalate task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to escalate task")


# ============================================================================
# IMPACT ASSESSMENT ENDPOINTS
# ============================================================================

@router.post("/assessments", response_model=Dict[str, Any])
async def create_impact_assessment(
    request: ImpactAssessmentRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Create or update a regulatory impact assessment."""
    try:
        # Get regulation data
        async with get_database() as db:
            query = "SELECT * FROM regulatory_documents WHERE id = $1"
            regulation = await db.fetchrow(query, request.regulation_id)
            
            if not regulation:
                raise HTTPException(status_code=404, detail="Regulation not found")
        
        # Queue assessment task
        background_tasks.add_task(
            _assess_regulation_background,
            request.regulation_id,
            dict(regulation),
            request.force_reassessment
        )
        
        return {
            "message": "Impact assessment queued successfully",
            "regulation_id": request.regulation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue impact assessment: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue impact assessment")


@router.get("/assessments/{regulation_id}", response_model=Dict[str, Any])
async def get_impact_assessment(
    regulation_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get impact assessment for a regulation."""
    try:
        async with get_database() as db:
            query = """
                SELECT * FROM regulatory_impact_assessments 
                WHERE regulation_id = $1 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            assessment = await db.fetchrow(query, regulation_id)
            
            if not assessment:
                raise HTTPException(status_code=404, detail="Impact assessment not found")
            
            return dict(assessment)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get impact assessment: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve impact assessment")


@router.get("/assessments", response_model=List[Dict[str, Any]])
async def get_impact_assessments(
    impact_level: Optional[str] = Query(None, description="Filter by impact level"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get impact assessments with filtering."""
    try:
        async with get_database() as db:
            conditions = []
            params = []
            
            if impact_level:
                conditions.append(f"impact_level = ${len(params) + 1}")
                params.append(impact_level)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT * FROM regulatory_impact_assessments 
                WHERE {where_clause}
                ORDER BY created_at DESC 
                LIMIT ${len(params) + 1}
            """
            params.append(limit)
            
            assessments = await db.fetch(query, *params)
            return [dict(assessment) for assessment in assessments]
            
    except Exception as e:
        logger.error(f"Failed to get impact assessments: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve impact assessments")


# ============================================================================
# TRIGGERS AND ORCHESTRATION ENDPOINTS
# ============================================================================

@router.post("/triggers", response_model=Dict[str, Any])
async def create_workflow_trigger(
    trigger_data: WorkflowTriggerCreate,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Create a new workflow trigger."""
    try:
        trigger_id = await workflow_orchestrator.create_workflow_trigger(
            trigger_data.dict(),
            current_user.get('id', 'unknown')
        )
        
        return {
            "trigger_id": trigger_id,
            "message": "Workflow trigger created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create workflow trigger: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workflow trigger")


@router.get("/triggers", response_model=List[Dict[str, Any]])
async def get_workflow_triggers(
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    enabled_only: bool = Query(True, description="Show only enabled triggers"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get workflow triggers."""
    try:
        async with get_database() as db:
            conditions = []
            params = []
            
            if trigger_type:
                conditions.append(f"trigger_type = ${len(params) + 1}")
                params.append(trigger_type)
            
            if enabled_only:
                conditions.append(f"enabled = ${len(params) + 1}")
                params.append(True)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT * FROM workflow_triggers 
                WHERE {where_clause}
                ORDER BY priority DESC, name
            """
            
            triggers = await db.fetch(query, *params)
            return [dict(trigger) for trigger in triggers]
            
    except Exception as e:
        logger.error(f"Failed to get workflow triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow triggers")


@router.post("/triggers/{trigger_id}/test", response_model=Dict[str, Any])
async def test_workflow_trigger(
    trigger_id: str,
    test_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Test a workflow trigger with sample data."""
    try:
        result = await workflow_orchestrator.test_trigger(trigger_id, test_data)
        return result
        
    except Exception as e:
        logger.error(f"Failed to test workflow trigger {trigger_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to test workflow trigger")


@router.post("/regulatory-change", response_model=Dict[str, Any])
async def handle_regulatory_change(
    background_tasks: BackgroundTasks,
    regulation_id: str = Query(..., description="Regulation ID"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Handle regulatory change with full orchestration."""
    try:
        # Get regulation data
        async with get_database() as db:
            query = "SELECT * FROM regulatory_documents WHERE id = $1"
            regulation = await db.fetchrow(query, regulation_id)
            
            if not regulation:
                raise HTTPException(status_code=404, detail="Regulation not found")
        
        # Queue orchestration task
        background_tasks.add_task(
            _handle_regulatory_change_background,
            regulation_id,
            dict(regulation)
        )
        
        return {
            "message": "Regulatory change handling initiated",
            "regulation_id": regulation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle regulatory change: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle regulatory change")


# ============================================================================
# ANALYTICS AND REPORTING ENDPOINTS
# ============================================================================

@router.get("/metrics", response_model=Dict[str, Any])
async def get_workflow_metrics(
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get workflow performance metrics."""
    try:
        workflow_metrics = await workflow_orchestrator.get_workflow_metrics()
        task_metrics = await task_manager.get_task_statistics()
        
        return {
            "workflows": workflow_metrics,
            "tasks": task_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow metrics")


@router.get("/tasks/overdue", response_model=List[Dict[str, Any]])
async def get_overdue_tasks(
    business_unit: Optional[str] = Query(None, description="Filter by business unit"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get overdue tasks."""
    try:
        overdue_tasks = await task_manager.get_overdue_tasks(business_unit)
        
        # Convert to API format
        task_list = []
        for task in overdue_tasks:
            days_overdue = (datetime.utcnow() - task.due_date).days if task.due_date else 0
            
            task_dict = {
                "id": task.id,
                "title": task.title,
                "priority": task.priority.value,
                "assignee": task.assignment.assignee_id if task.assignment else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "days_overdue": days_overdue,
                "workflow_id": task.workflow_id,
                "regulatory_reference": task.regulatory_reference
            }
            task_list.append(task_dict)
        
        return task_list
        
    except Exception as e:
        logger.error(f"Failed to get overdue tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve overdue tasks")


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_workflow_dashboard(
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get workflow dashboard data."""
    try:
        # Get user's tasks
        user_id = current_user.get('id')
        user_tasks = await task_manager.get_user_tasks(user_id)
        
        # Get active workflows
        active_workflows = await workflow_orchestrator.get_active_workflows()
        
        # Get recent impact assessments
        async with get_database() as db:
            recent_assessments = await db.fetch("""
                SELECT regulation_id, regulation_title, impact_level, created_at
                FROM regulatory_impact_assessments
                ORDER BY created_at DESC
                LIMIT 10
            """)
        
        # Calculate summary statistics
        task_stats = {
            'total': len(user_tasks),
            'in_progress': len([t for t in user_tasks if t.status.value == 'in_progress']),
            'overdue': len([t for t in user_tasks if t.due_date and t.due_date < datetime.utcnow()]),
            'completed_today': len([t for t in user_tasks if 
                                  t.completed_at and t.completed_at.date() == datetime.utcnow().date()])
        }
        
        workflow_stats = {
            'active': len([w for w in active_workflows if w.get('status') == 'active']),
            'completed_today': len([w for w in active_workflows if 
                                  w.get('completed_at') and 
                                  datetime.fromisoformat(w['completed_at']).date() == datetime.utcnow().date()])
        }
        
        return {
            "task_summary": task_stats,
            "workflow_summary": workflow_stats,
            "recent_assessments": [dict(a) for a in recent_assessments],
            "my_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority.value,
                    "status": t.status.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "progress": t.progress_percentage
                }
                for t in user_tasks[:10]  # Show top 10 tasks
            ],
            "active_workflows": active_workflows[:5]  # Show top 5 workflows
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


# ============================================================================
# BACKGROUND TASK FUNCTIONS
# ============================================================================

async def _assess_regulation_background(regulation_id: str, regulation_data: Dict[str, Any], force_reassessment: bool):
    """Background task for impact assessment."""
    try:
        await impact_assessor.assess_regulatory_impact(regulation_id, regulation_data, force_reassessment)
        logger.info(f"Completed background impact assessment for {regulation_id}")
    except Exception as e:
        logger.error(f"Background impact assessment failed for {regulation_id}: {e}")


async def _handle_regulatory_change_background(regulation_id: str, regulation_data: Dict[str, Any]):
    """Background task for regulatory change handling."""
    try:
        result = await workflow_orchestrator.handle_regulatory_change(regulation_id, regulation_data)
        logger.info(f"Completed background regulatory change handling for {regulation_id}")
    except Exception as e:
        logger.error(f"Background regulatory change handling failed for {regulation_id}: {e}") 