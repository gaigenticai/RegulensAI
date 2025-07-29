"""
Regulens AI - Task Management Routes
Enterprise-grade workflow and task management endpoints.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import (
    get_current_user,
    verify_tenant_access,
    require_permission,
    UserInDB
)
from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["Task Management"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TaskCreate(BaseModel):
    """Task creation request model."""
    title: str = Field(..., min_length=2, max_length=200, description="Task title")
    description: str = Field(..., min_length=10, description="Task description")
    task_type: str = Field(..., description="Type of task")
    priority: str = Field(..., description="Priority level (low, medium, high, critical)")
    due_date: Optional[datetime] = Field(None, description="Due date")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    related_entity_type: Optional[str] = Field(None, description="Related entity type")
    related_entity_id: Optional[str] = Field(None, description="Related entity ID")

class TaskUpdate(BaseModel):
    """Task update request model."""
    title: Optional[str] = Field(None, min_length=2, max_length=200, description="Task title")
    description: Optional[str] = Field(None, min_length=10, description="Task description")
    status: Optional[str] = Field(None, description="Task status")
    priority: Optional[str] = Field(None, description="Priority level")
    due_date: Optional[datetime] = Field(None, description="Due date")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    completion_notes: Optional[str] = Field(None, description="Completion notes")

class TaskResponse(BaseModel):
    """Task response model."""
    id: str
    title: str
    description: str
    task_type: str
    status: str
    priority: str
    due_date: Optional[str]
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    created_by: str
    created_by_name: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    completion_notes: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str

# ============================================================================
# TASK ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    current_user: UserInDB = Depends(require_permission("compliance.tasks.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get list of tasks with filtering.
    
    Requires permission: compliance.tasks.read
    """
    try:
        async with get_database() as db:
            # Build query conditions
            conditions = ["t.tenant_id = $1"]
            params = [uuid.UUID(tenant_id)]
            param_count = 1
            
            if status:
                param_count += 1
                conditions.append(f"t.status = ${param_count}")
                params.append(status)
            
            if assigned_to:
                param_count += 1
                conditions.append(f"t.assigned_to = ${param_count}")
                params.append(uuid.UUID(assigned_to))
            
            if task_type:
                param_count += 1
                conditions.append(f"t.task_type = ${param_count}")
                params.append(task_type)
            
            if priority:
                param_count += 1
                conditions.append(f"t.priority = ${param_count}")
                params.append(priority)
            
            query = f"""
                SELECT t.*, 
                       u1.full_name as assigned_to_name,
                       u2.full_name as created_by_name
                FROM tasks t
                LEFT JOIN users u1 ON t.assigned_to = u1.id
                LEFT JOIN users u2 ON t.created_by = u2.id
                WHERE {' AND '.join(conditions)}
                ORDER BY 
                    CASE t.priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        ELSE 4 
                    END,
                    t.due_date ASC NULLS LAST,
                    t.created_at DESC
                LIMIT ${param_count + 1}
            """
            params.append(limit)
            
            tasks = await db.fetch(query, *params)
            
            return [
                TaskResponse(
                    id=str(task['id']),
                    title=task['title'],
                    description=task['description'],
                    task_type=task['task_type'],
                    status=task['status'],
                    priority=task['priority'],
                    due_date=task['due_date'].isoformat() if task['due_date'] else None,
                    assigned_to=str(task['assigned_to']) if task['assigned_to'] else None,
                    assigned_to_name=task['assigned_to_name'],
                    created_by=str(task['created_by']),
                    created_by_name=task['created_by_name'],
                    related_entity_type=task['related_entity_type'],
                    related_entity_id=str(task['related_entity_id']) if task['related_entity_id'] else None,
                    completion_notes=task['completion_notes'],
                    completed_at=task['completed_at'].isoformat() if task['completed_at'] else None,
                    created_at=task['created_at'].isoformat(),
                    updated_at=task['updated_at'].isoformat()
                )
                for task in tasks
            ]
            
    except Exception as e:
        logger.error(f"Get tasks failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: UserInDB = Depends(require_permission("compliance.tasks.create")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Create a new task.
    
    Requires permission: compliance.tasks.create
    """
    try:
        async with get_database() as db:
            # Verify assigned user exists if provided
            assigned_to_name = None
            if task_data.assigned_to:
                assigned_user = await db.fetchrow(
                    "SELECT id, full_name FROM users WHERE id = $1 AND tenant_id = $2",
                    uuid.UUID(task_data.assigned_to),
                    uuid.UUID(tenant_id)
                )
                
                if not assigned_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Assigned user not found"
                    )
                assigned_to_name = assigned_user['full_name']
            
            # Create task
            task_id = uuid.uuid4()
            task_record = await db.fetchrow(
                """
                INSERT INTO tasks (
                    id, tenant_id, title, description, task_type, priority,
                    due_date, assigned_to, created_by, related_entity_type,
                    related_entity_id, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                task_id,
                uuid.UUID(tenant_id),
                task_data.title,
                task_data.description,
                task_data.task_type,
                task_data.priority,
                task_data.due_date,
                uuid.UUID(task_data.assigned_to) if task_data.assigned_to else None,
                uuid.UUID(current_user.id),
                task_data.related_entity_type,
                uuid.UUID(task_data.related_entity_id) if task_data.related_entity_id else None,
                'pending'
            )
            
            logger.info(f"Task created: {task_data.title} by {current_user.email}")
            
            return TaskResponse(
                id=str(task_record['id']),
                title=task_record['title'],
                description=task_record['description'],
                task_type=task_record['task_type'],
                status=task_record['status'],
                priority=task_record['priority'],
                due_date=task_record['due_date'].isoformat() if task_record['due_date'] else None,
                assigned_to=str(task_record['assigned_to']) if task_record['assigned_to'] else None,
                assigned_to_name=assigned_to_name,
                created_by=str(task_record['created_by']),
                created_by_name=current_user.full_name,
                related_entity_type=task_record['related_entity_type'],
                related_entity_id=str(task_record['related_entity_id']) if task_record['related_entity_id'] else None,
                completion_notes=None,
                completed_at=None,
                created_at=task_record['created_at'].isoformat(),
                updated_at=task_record['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create task failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: UserInDB = Depends(require_permission("compliance.tasks.update")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Update a task.
    
    Requires permission: compliance.tasks.update
    """
    try:
        async with get_database() as db:
            # Check if task exists
            existing_task = await db.fetchrow(
                "SELECT id FROM tasks WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(task_id),
                uuid.UUID(tenant_id)
            )
            
            if not existing_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
            
            # Build update query
            update_fields = []
            params = []
            param_count = 0
            
            if task_data.title is not None:
                param_count += 1
                update_fields.append(f"title = ${param_count}")
                params.append(task_data.title)
            
            if task_data.description is not None:
                param_count += 1
                update_fields.append(f"description = ${param_count}")
                params.append(task_data.description)
            
            if task_data.status is not None:
                param_count += 1
                update_fields.append(f"status = ${param_count}")
                params.append(task_data.status)
                
                # Set completion timestamp if completed
                if task_data.status == 'completed':
                    param_count += 1
                    update_fields.append(f"completed_at = ${param_count}")
                    params.append(datetime.utcnow())
            
            if task_data.priority is not None:
                param_count += 1
                update_fields.append(f"priority = ${param_count}")
                params.append(task_data.priority)
            
            if task_data.due_date is not None:
                param_count += 1
                update_fields.append(f"due_date = ${param_count}")
                params.append(task_data.due_date)
            
            if task_data.assigned_to is not None:
                param_count += 1
                update_fields.append(f"assigned_to = ${param_count}")
                params.append(uuid.UUID(task_data.assigned_to))
            
            if task_data.completion_notes is not None:
                param_count += 1
                update_fields.append(f"completion_notes = ${param_count}")
                params.append(task_data.completion_notes)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            # Add updated_at
            param_count += 1
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            
            # Add WHERE conditions
            param_count += 1
            params.append(uuid.UUID(task_id))
            param_count += 1
            params.append(uuid.UUID(tenant_id))
            
            update_query = f"""
                UPDATE tasks 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count - 1} AND tenant_id = ${param_count}
                RETURNING *
            """
            
            updated_task = await db.fetchrow(update_query, *params)
            
            # Get user names
            user_names_query = """
                SELECT 
                    u1.full_name as assigned_to_name,
                    u2.full_name as created_by_name
                FROM tasks t
                LEFT JOIN users u1 ON t.assigned_to = u1.id
                LEFT JOIN users u2 ON t.created_by = u2.id
                WHERE t.id = $1
            """
            user_names = await db.fetchrow(user_names_query, uuid.UUID(task_id))
            
            logger.info(f"Task updated: {updated_task['title']} by {current_user.email}")
            
            return TaskResponse(
                id=str(updated_task['id']),
                title=updated_task['title'],
                description=updated_task['description'],
                task_type=updated_task['task_type'],
                status=updated_task['status'],
                priority=updated_task['priority'],
                due_date=updated_task['due_date'].isoformat() if updated_task['due_date'] else None,
                assigned_to=str(updated_task['assigned_to']) if updated_task['assigned_to'] else None,
                assigned_to_name=user_names['assigned_to_name'],
                created_by=str(updated_task['created_by']),
                created_by_name=user_names['created_by_name'],
                related_entity_type=updated_task['related_entity_type'],
                related_entity_id=str(updated_task['related_entity_id']) if updated_task['related_entity_id'] else None,
                completion_notes=updated_task['completion_notes'],
                completed_at=updated_task['completed_at'].isoformat() if updated_task['completed_at'] else None,
                created_at=updated_task['created_at'].isoformat(),
                updated_at=updated_task['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update task failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )
