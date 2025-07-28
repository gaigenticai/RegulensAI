"""
Workflow Engine - Core Workflow Execution Engine
Manages workflow execution, state transitions, and task orchestration.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json

from core_infra.database.connection import get_database
from core_infra.services.monitoring import track_operation
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WorkflowStatus(Enum):
    """Workflow execution status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TaskStatus(Enum):
    """Individual task status within workflows."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WorkflowContext:
    """Context data available throughout workflow execution."""
    workflow_id: str
    triggered_by: str
    trigger_data: Dict[str, Any]
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TaskDefinition:
    """Definition of a task within a workflow."""
    id: str
    name: str
    type: str  # 'manual', 'automated', 'approval', 'condition', 'notification'
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration_hours: Optional[float] = None
    requires_approval: bool = False
    assignee_role: Optional[str] = None
    assignee_user_id: Optional[str] = None
    due_date_offset_hours: Optional[int] = None
    prerequisites: List[str] = field(default_factory=list)  # Task IDs that must complete first
    conditions: Dict[str, Any] = field(default_factory=dict)  # Execution conditions
    automation_config: Dict[str, Any] = field(default_factory=dict)  # For automated tasks
    notification_config: Dict[str, Any] = field(default_factory=dict)  # For notifications
    approval_config: Dict[str, Any] = field(default_factory=dict)  # For approval tasks


@dataclass
class WorkflowState:
    """Current state of a workflow execution."""
    workflow_id: str
    definition_id: str
    status: WorkflowStatus
    current_tasks: List[str]  # Currently active task IDs
    completed_tasks: List[str]  # Completed task IDs
    failed_tasks: List[str]  # Failed task IDs
    context: WorkflowContext
    started_at: datetime
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    error_message: Optional[str] = None


@dataclass  
class WorkflowDefinition:
    """Complete workflow definition with tasks and flow logic."""
    id: str
    name: str
    description: str
    version: str
    category: str  # 'regulatory_change', 'compliance_review', 'incident_response', etc.
    tasks: List[TaskDefinition]
    triggers: List[Dict[str, Any]]  # What can trigger this workflow
    flow_logic: Dict[str, Any]  # Task dependencies and conditions
    variables: Dict[str, Any] = field(default_factory=dict)  # Default variables
    settings: Dict[str, Any] = field(default_factory=dict)  # Workflow settings
    is_active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class WorkflowEngine:
    """
    Core workflow execution engine that manages compliance workflows,
    task orchestration, and state transitions.
    """
    
    def __init__(self):
        self.running_workflows: Dict[str, WorkflowState] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {}
        self.execution_pool = {}
        self.max_concurrent_workflows = settings.max_concurrent_workflows
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default task handlers and condition evaluators."""
        self.task_handlers.update({
            'manual': self._handle_manual_task,
            'automated': self._handle_automated_task,
            'approval': self._handle_approval_task,
            'condition': self._handle_condition_task,
            'notification': self._handle_notification_task,
            'document_review': self._handle_document_review_task,
            'risk_assessment': self._handle_risk_assessment_task,
            'compliance_check': self._handle_compliance_check_task,
            'regulatory_filing': self._handle_regulatory_filing_task
        })
        
        self.condition_evaluators.update({
            'always': lambda context, config: True,
            'never': lambda context, config: False,
            'variable_equals': self._evaluate_variable_equals,
            'variable_greater_than': self._evaluate_variable_greater_than,
            'task_completed': self._evaluate_task_completed,
            'approval_received': self._evaluate_approval_received,
            'deadline_approaching': self._evaluate_deadline_approaching
        })
    
    @track_operation("workflow_engine.start_workflow")
    async def start_workflow(self, definition_id: str, triggered_by: str, 
                           trigger_data: Dict[str, Any] = None,
                           initial_variables: Dict[str, Any] = None) -> str:
        """
        Start a new workflow execution.
        
        Args:
            definition_id: ID of the workflow definition to execute
            triggered_by: User or system that triggered the workflow
            trigger_data: Data that triggered the workflow
            initial_variables: Initial variables for the workflow context
            
        Returns:
            Workflow execution ID
        """
        try:
            # Get workflow definition
            definition = await self._get_workflow_definition(definition_id)
            if not definition:
                raise ValueError(f"Workflow definition not found: {definition_id}")
            
            if not definition.is_active:
                raise ValueError(f"Workflow definition is not active: {definition_id}")
            
            # Create workflow execution ID
            workflow_id = str(uuid.uuid4())
            
            # Initialize context
            context = WorkflowContext(
                workflow_id=workflow_id,
                triggered_by=triggered_by,
                trigger_data=trigger_data or {},
                variables={**definition.variables, **(initial_variables or {})},
                metadata={
                    'definition_id': definition_id,
                    'definition_name': definition.name,
                    'definition_version': definition.version,
                    'category': definition.category
                }
            )
            
            # Create workflow state
            state = WorkflowState(
                workflow_id=workflow_id,
                definition_id=definition_id,
                status=WorkflowStatus.ACTIVE,
                current_tasks=[],
                completed_tasks=[],
                failed_tasks=[],
                context=context,
                started_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            
            # Store in memory
            self.running_workflows[workflow_id] = state
            
            # Persist to database
            await self._persist_workflow_state(state)
            
            # Determine initial tasks
            initial_tasks = self._get_initial_tasks(definition)
            
            # Start initial tasks
            for task_def in initial_tasks:
                await self._start_task(workflow_id, task_def)
            
            logger.info(f"Started workflow {workflow_id} from definition {definition_id}")
            
            return workflow_id
            
        except Exception as e:
            logger.error(f"Failed to start workflow {definition_id}: {e}")
            raise
    
    @track_operation("workflow_engine.complete_task")
    async def complete_task(self, workflow_id: str, task_id: str, 
                          result: Dict[str, Any] = None,
                          completed_by: str = None) -> bool:
        """
        Mark a task as completed and continue workflow execution.
        
        Args:
            workflow_id: Workflow execution ID
            task_id: Task ID to complete
            result: Task execution result
            completed_by: User who completed the task
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                logger.error(f"Workflow not found: {workflow_id}")
                return False
            
            if task_id not in state.current_tasks:
                logger.warning(f"Task {task_id} is not currently active in workflow {workflow_id}")
                return False
            
            # Move task from current to completed
            state.current_tasks.remove(task_id)
            state.completed_tasks.append(task_id)
            state.last_activity_at = datetime.utcnow()
            
            # Update context with task result
            if result:
                state.context.variables.update(result.get('variables', {}))
                state.context.execution_history.append({
                    'task_id': task_id,
                    'action': 'completed',
                    'result': result,
                    'completed_by': completed_by,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Update task status in database
            await self._update_task_status(workflow_id, task_id, TaskStatus.COMPLETED, result)
            
            # Check for next tasks
            await self._continue_workflow(workflow_id)
            
            logger.info(f"Task {task_id} completed in workflow {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task {task_id} in workflow {workflow_id}: {e}")
            return False
    
    @track_operation("workflow_engine.fail_task")
    async def fail_task(self, workflow_id: str, task_id: str, 
                       error_message: str, failed_by: str = None) -> bool:
        """
        Mark a task as failed and handle failure according to workflow logic.
        
        Args:
            workflow_id: Workflow execution ID
            task_id: Task ID that failed
            error_message: Reason for failure
            failed_by: User or system that reported the failure
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                logger.error(f"Workflow not found: {workflow_id}")
                return False
            
            if task_id not in state.current_tasks:
                logger.warning(f"Task {task_id} is not currently active in workflow {workflow_id}")
                return False
            
            # Move task from current to failed
            state.current_tasks.remove(task_id)
            state.failed_tasks.append(task_id)
            state.last_activity_at = datetime.utcnow()
            
            # Update context with failure info
            state.context.execution_history.append({
                'task_id': task_id,
                'action': 'failed',
                'error_message': error_message,
                'failed_by': failed_by,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Update task status in database
            await self._update_task_status(workflow_id, task_id, TaskStatus.FAILED, {'error': error_message})
            
            # Handle failure according to workflow configuration
            definition = await self._get_workflow_definition(state.definition_id)
            failure_behavior = definition.settings.get('failure_behavior', 'stop')
            
            if failure_behavior == 'continue':
                # Continue with other tasks
                await self._continue_workflow(workflow_id)
            elif failure_behavior == 'retry':
                # Retry the failed task
                await self._retry_task(workflow_id, task_id)
            else:
                # Stop the workflow
                await self._fail_workflow(workflow_id, f"Task {task_id} failed: {error_message}")
            
            logger.warning(f"Task {task_id} failed in workflow {workflow_id}: {error_message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fail task {task_id} in workflow {workflow_id}: {e}")
            return False
    
    async def _continue_workflow(self, workflow_id: str):
        """Continue workflow execution by starting next available tasks."""
        try:
            state = self.running_workflows.get(workflow_id)
            if not state or state.status != WorkflowStatus.ACTIVE:
                return
            
            definition = await self._get_workflow_definition(state.definition_id)
            if not definition:
                return
            
            # Find tasks that can now be started
            ready_tasks = self._get_ready_tasks(definition, state)
            
            # Start ready tasks
            for task_def in ready_tasks:
                await self._start_task(workflow_id, task_def)
            
            # Check if workflow is complete
            await self._check_workflow_completion(workflow_id)
            
            # Update progress
            await self._update_workflow_progress(workflow_id)
            
        except Exception as e:
            logger.error(f"Failed to continue workflow {workflow_id}: {e}")
    
    async def _start_task(self, workflow_id: str, task_def: TaskDefinition):
        """Start execution of a specific task."""
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                return
            
            # Add to current tasks
            state.current_tasks.append(task_def.id)
            state.last_activity_at = datetime.utcnow()
            
            # Calculate due date
            due_date = None
            if task_def.due_date_offset_hours:
                due_date = datetime.utcnow() + timedelta(hours=task_def.due_date_offset_hours)
            
            # Create task record in database
            await self._create_task_record(workflow_id, task_def, due_date)
            
            # Get task handler
            handler = self.task_handlers.get(task_def.type)
            if not handler:
                logger.error(f"No handler found for task type: {task_def.type}")
                await self.fail_task(workflow_id, task_def.id, f"No handler for task type: {task_def.type}")
                return
            
            # Execute task handler
            try:
                await handler(workflow_id, task_def, state.context)
                logger.info(f"Started task {task_def.id} in workflow {workflow_id}")
            except Exception as e:
                logger.error(f"Task handler failed for {task_def.id}: {e}")
                await self.fail_task(workflow_id, task_def.id, str(e))
            
        except Exception as e:
            logger.error(f"Failed to start task {task_def.id} in workflow {workflow_id}: {e}")
    
    def _get_initial_tasks(self, definition: WorkflowDefinition) -> List[TaskDefinition]:
        """Get tasks that can be started initially (no prerequisites)."""
        return [task for task in definition.tasks if not task.prerequisites]
    
    def _get_ready_tasks(self, definition: WorkflowDefinition, state: WorkflowState) -> List[TaskDefinition]:
        """Get tasks that are ready to be started based on completed prerequisites."""
        ready_tasks = []
        
        for task in definition.tasks:
            # Skip if already started, completed, or failed
            if (task.id in state.current_tasks or 
                task.id in state.completed_tasks or 
                task.id in state.failed_tasks):
                continue
            
            # Check prerequisites
            if self._are_prerequisites_met(task, state):
                # Check conditions
                if self._evaluate_task_conditions(task, state.context):
                    ready_tasks.append(task)
        
        return ready_tasks
    
    def _are_prerequisites_met(self, task: TaskDefinition, state: WorkflowState) -> bool:
        """Check if all task prerequisites are completed."""
        for prereq_id in task.prerequisites:
            if prereq_id not in state.completed_tasks:
                return False
        return True
    
    def _evaluate_task_conditions(self, task: TaskDefinition, context: WorkflowContext) -> bool:
        """Evaluate task execution conditions."""
        if not task.conditions:
            return True
        
        for condition_type, config in task.conditions.items():
            evaluator = self.condition_evaluators.get(condition_type)
            if evaluator and not evaluator(context, config):
                return False
        
        return True
    
    async def _check_workflow_completion(self, workflow_id: str):
        """Check if workflow is complete and update status accordingly."""
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                return
            
            definition = await self._get_workflow_definition(state.definition_id)
            if not definition:
                return
            
            # Count tasks by status
            total_tasks = len(definition.tasks)
            completed_tasks = len(state.completed_tasks)
            failed_tasks = len(state.failed_tasks)
            current_tasks = len(state.current_tasks)
            
            # Check completion conditions
            if completed_tasks + failed_tasks == total_tasks:
                # All tasks are done
                if failed_tasks == 0:
                    await self._complete_workflow(workflow_id)
                else:
                    # Determine if failures are acceptable
                    max_failures = definition.settings.get('max_acceptable_failures', 0)
                    if failed_tasks <= max_failures:
                        await self._complete_workflow(workflow_id)
                    else:
                        await self._fail_workflow(workflow_id, f"Too many failed tasks: {failed_tasks}")
            
            elif current_tasks == 0 and completed_tasks > 0:
                # No current tasks but some completed - check if stuck
                remaining_tasks = total_tasks - completed_tasks - failed_tasks
                if remaining_tasks > 0:
                    # There are uncompleted tasks with no current tasks - might be stuck
                    logger.warning(f"Workflow {workflow_id} might be stuck with {remaining_tasks} remaining tasks")
            
        except Exception as e:
            logger.error(f"Failed to check workflow completion for {workflow_id}: {e}")
    
    async def _complete_workflow(self, workflow_id: str):
        """Mark workflow as completed."""
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                return
            
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.utcnow()
            state.last_activity_at = datetime.utcnow()
            state.progress_percentage = 100.0
            
            # Update context
            state.context.execution_history.append({
                'action': 'workflow_completed',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Persist final state
            await self._persist_workflow_state(state)
            
            # Remove from active workflows
            del self.running_workflows[workflow_id]
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to complete workflow {workflow_id}: {e}")
    
    async def _fail_workflow(self, workflow_id: str, error_message: str):
        """Mark workflow as failed."""
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                return
            
            state.status = WorkflowStatus.FAILED
            state.completed_at = datetime.utcnow()
            state.last_activity_at = datetime.utcnow()
            state.error_message = error_message
            
            # Cancel all current tasks
            for task_id in state.current_tasks:
                await self._update_task_status(workflow_id, task_id, TaskStatus.CANCELLED)
            
            state.current_tasks.clear()
            
            # Update context
            state.context.execution_history.append({
                'action': 'workflow_failed',
                'error_message': error_message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Persist final state
            await self._persist_workflow_state(state)
            
            # Remove from active workflows
            del self.running_workflows[workflow_id]
            
            logger.error(f"Workflow {workflow_id} failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to fail workflow {workflow_id}: {e}")
    
    async def _update_workflow_progress(self, workflow_id: str):
        """Update workflow progress percentage."""
        try:
            state = self.running_workflows.get(workflow_id)
            if not state:
                return
            
            definition = await self._get_workflow_definition(state.definition_id)
            if not definition:
                return
            
            total_tasks = len(definition.tasks)
            completed_tasks = len(state.completed_tasks)
            
            if total_tasks > 0:
                state.progress_percentage = (completed_tasks / total_tasks) * 100.0
            else:
                state.progress_percentage = 100.0
            
            # Persist updated progress
            await self._persist_workflow_state(state)
            
        except Exception as e:
            logger.error(f"Failed to update workflow progress for {workflow_id}: {e}")
    
    # ========================================================================
    # TASK HANDLERS
    # ========================================================================
    
    async def _handle_manual_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle manual task - assign to user and wait for completion."""
        # Task is created and assigned - completion handled externally
        pass
    
    async def _handle_automated_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle automated task execution."""
        try:
            automation_type = task_def.automation_config.get('type')
            
            if automation_type == 'api_call':
                result = await self._execute_api_call(task_def.automation_config)
            elif automation_type == 'script':
                result = await self._execute_script(task_def.automation_config)
            elif automation_type == 'database_update':
                result = await self._execute_database_update(task_def.automation_config)
            else:
                raise ValueError(f"Unknown automation type: {automation_type}")
            
            # Auto-complete the task
            await self.complete_task(workflow_id, task_def.id, result, "system")
            
        except Exception as e:
            logger.error(f"Automated task failed: {e}")
            raise
    
    async def _handle_approval_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle approval task - send notification and wait for approval."""
        # Create approval request and send notifications
        approval_config = task_def.approval_config
        approvers = approval_config.get('approvers', [])
        
        # Send approval notifications
        for approver in approvers:
            await self._send_approval_notification(workflow_id, task_def.id, approver)
    
    async def _handle_condition_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle conditional task - evaluate condition and complete automatically."""
        try:
            condition_result = self._evaluate_task_conditions(task_def, context)
            
            result = {
                'condition_result': condition_result,
                'variables': {'condition_outcome': condition_result}
            }
            
            await self.complete_task(workflow_id, task_def.id, result, "system")
            
        except Exception as e:
            logger.error(f"Condition task failed: {e}")
            raise
    
    async def _handle_notification_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle notification task - send notifications and complete."""
        try:
            notification_config = task_def.notification_config
            
            # Send notifications
            await self._send_workflow_notification(workflow_id, task_def.id, notification_config)
            
            # Auto-complete the task
            result = {'notification_sent': True}
            await self.complete_task(workflow_id, task_def.id, result, "system")
            
        except Exception as e:
            logger.error(f"Notification task failed: {e}")
            raise
    
    async def _handle_document_review_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle document review task."""
        # Create document review assignment
        pass
    
    async def _handle_risk_assessment_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle risk assessment task."""
        # Trigger risk assessment workflow
        pass
    
    async def _handle_compliance_check_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle compliance check task."""
        # Execute compliance verification
        pass
    
    async def _handle_regulatory_filing_task(self, workflow_id: str, task_def: TaskDefinition, context: WorkflowContext):
        """Handle regulatory filing task."""
        # Prepare and submit regulatory filing
        pass
    
    # ========================================================================
    # CONDITION EVALUATORS
    # ========================================================================
    
    def _evaluate_variable_equals(self, context: WorkflowContext, config: Dict[str, Any]) -> bool:
        """Evaluate if a variable equals a specific value."""
        variable_name = config.get('variable')
        expected_value = config.get('value')
        actual_value = context.variables.get(variable_name)
        return actual_value == expected_value
    
    def _evaluate_variable_greater_than(self, context: WorkflowContext, config: Dict[str, Any]) -> bool:
        """Evaluate if a variable is greater than a specific value."""
        variable_name = config.get('variable')
        threshold = config.get('threshold')
        actual_value = context.variables.get(variable_name, 0)
        try:
            return float(actual_value) > float(threshold)
        except (ValueError, TypeError):
            return False
    
    def _evaluate_task_completed(self, context: WorkflowContext, config: Dict[str, Any]) -> bool:
        """Evaluate if a specific task is completed."""
        task_id = config.get('task_id')
        # This would check the workflow state to see if task is completed
        return True  # Simplified for now
    
    def _evaluate_approval_received(self, context: WorkflowContext, config: Dict[str, Any]) -> bool:
        """Evaluate if approval has been received."""
        approval_key = config.get('approval_key', 'approval_received')
        return context.variables.get(approval_key, False)
    
    def _evaluate_deadline_approaching(self, context: WorkflowContext, config: Dict[str, Any]) -> bool:
        """Evaluate if a deadline is approaching."""
        deadline_date = config.get('deadline')
        warning_hours = config.get('warning_hours', 24)
        
        if not deadline_date:
            return False
        
        try:
            deadline = datetime.fromisoformat(deadline_date)
            warning_time = deadline - timedelta(hours=warning_hours)
            return datetime.utcnow() >= warning_time
        except (ValueError, TypeError):
            return False
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    async def _get_workflow_definition(self, definition_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition from database or cache."""
        if definition_id in self.workflow_definitions:
            return self.workflow_definitions[definition_id]
        
        try:
            async with get_database() as db:
                query = "SELECT * FROM workflow_definitions WHERE id = $1 AND is_active = true"
                row = await db.fetchrow(query, definition_id)
                
                if row:
                    definition = WorkflowDefinition(
                        id=row['id'],
                        name=row['name'],
                        description=row['description'],
                        version=row['version'],
                        category=row['category'],
                        tasks=json.loads(row['tasks_definition']),
                        triggers=json.loads(row['triggers']),
                        flow_logic=json.loads(row['flow_logic']),
                        variables=json.loads(row['default_variables']),
                        settings=json.loads(row['settings']),
                        is_active=row['is_active'],
                        created_by=row['created_by'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    
                    # Cache for future use
                    self.workflow_definitions[definition_id] = definition
                    return definition
                
        except Exception as e:
            logger.error(f"Failed to get workflow definition {definition_id}: {e}")
        
        return None
    
    async def _persist_workflow_state(self, state: WorkflowState):
        """Persist workflow state to database."""
        try:
            async with get_database() as db:
                query = """
                    INSERT INTO workflow_executions (
                        id, definition_id, status, current_tasks, completed_tasks,
                        failed_tasks, context_data, started_at, completed_at,
                        last_activity_at, progress_percentage, error_message
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        current_tasks = EXCLUDED.current_tasks,
                        completed_tasks = EXCLUDED.completed_tasks,
                        failed_tasks = EXCLUDED.failed_tasks,
                        context_data = EXCLUDED.context_data,
                        completed_at = EXCLUDED.completed_at,
                        last_activity_at = EXCLUDED.last_activity_at,
                        progress_percentage = EXCLUDED.progress_percentage,
                        error_message = EXCLUDED.error_message
                """
                
                await db.execute(
                    query,
                    state.workflow_id,
                    state.definition_id,
                    state.status.value,
                    json.dumps(state.current_tasks),
                    json.dumps(state.completed_tasks),
                    json.dumps(state.failed_tasks),
                    json.dumps({
                        'triggered_by': state.context.triggered_by,
                        'trigger_data': state.context.trigger_data,
                        'variables': state.context.variables,
                        'metadata': state.context.metadata,
                        'execution_history': state.context.execution_history
                    }),
                    state.started_at,
                    state.completed_at,
                    state.last_activity_at,
                    state.progress_percentage,
                    state.error_message
                )
                
        except Exception as e:
            logger.error(f"Failed to persist workflow state {state.workflow_id}: {e}")
    
    async def _create_task_record(self, workflow_id: str, task_def: TaskDefinition, due_date: Optional[datetime]):
        """Create task record in database."""
        try:
            async with get_database() as db:
                query = """
                    INSERT INTO workflow_tasks (
                        id, workflow_id, name, type, description, priority,
                        status, assignee_role, assignee_user_id, due_date,
                        estimated_duration_hours, requires_approval, 
                        task_config, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """
                
                await db.execute(
                    query,
                    task_def.id,
                    workflow_id,
                    task_def.name,
                    task_def.type,
                    task_def.description,
                    task_def.priority.value,
                    TaskStatus.PENDING.value,
                    task_def.assignee_role,
                    task_def.assignee_user_id,
                    due_date,
                    task_def.estimated_duration_hours,
                    task_def.requires_approval,
                    json.dumps({
                        'prerequisites': task_def.prerequisites,
                        'conditions': task_def.conditions,
                        'automation_config': task_def.automation_config,
                        'notification_config': task_def.notification_config,
                        'approval_config': task_def.approval_config
                    }),
                    datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Failed to create task record {task_def.id}: {e}")
    
    async def _update_task_status(self, workflow_id: str, task_id: str, 
                                status: TaskStatus, result: Dict[str, Any] = None):
        """Update task status in database."""
        try:
            async with get_database() as db:
                query = """
                    UPDATE workflow_tasks 
                    SET status = $1, completed_at = $2, result_data = $3, updated_at = $4
                    WHERE id = $5 AND workflow_id = $6
                """
                
                completed_at = datetime.utcnow() if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] else None
                
                await db.execute(
                    query,
                    status.value,
                    completed_at,
                    json.dumps(result) if result else None,
                    datetime.utcnow(),
                    task_id,
                    workflow_id
                )
                
        except Exception as e:
            logger.error(f"Failed to update task status {task_id}: {e}")
    
    # ========================================================================
    # AUTOMATION HELPERS
    # ========================================================================
    
    async def _execute_api_call(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call for automated task."""
        # Implementation would make HTTP requests
        return {'api_call_result': 'success'}
    
    async def _execute_script(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute script for automated task."""
        # Implementation would execute scripts safely
        return {'script_result': 'success'}
    
    async def _execute_database_update(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database update for automated task."""
        # Implementation would perform database operations
        return {'database_update_result': 'success'}
    
    async def _send_approval_notification(self, workflow_id: str, task_id: str, approver: str):
        """Send approval notification."""
        # Implementation would send notifications
        pass
    
    async def _send_workflow_notification(self, workflow_id: str, task_id: str, config: Dict[str, Any]):
        """Send workflow notification."""
        # Implementation would send notifications
        pass
    
    async def _retry_task(self, workflow_id: str, task_id: str):
        """Retry a failed task."""
        # Implementation would retry task execution
        pass
    
    # ========================================================================
    # PUBLIC API METHODS
    # ========================================================================
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get current workflow status."""
        return self.running_workflows.get(workflow_id)
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause workflow execution."""
        state = self.running_workflows.get(workflow_id)
        if state and state.status == WorkflowStatus.ACTIVE:
            state.status = WorkflowStatus.PAUSED
            state.last_activity_at = datetime.utcnow()
            await self._persist_workflow_state(state)
            return True
        return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume paused workflow execution."""
        state = self.running_workflows.get(workflow_id)
        if state and state.status == WorkflowStatus.PAUSED:
            state.status = WorkflowStatus.ACTIVE
            state.last_activity_at = datetime.utcnow()
            await self._persist_workflow_state(state)
            await self._continue_workflow(workflow_id)
            return True
        return False
    
    async def cancel_workflow(self, workflow_id: str, reason: str = None) -> bool:
        """Cancel workflow execution."""
        state = self.running_workflows.get(workflow_id)
        if state and state.status in [WorkflowStatus.ACTIVE, WorkflowStatus.PAUSED]:
            state.status = WorkflowStatus.CANCELLED
            state.completed_at = datetime.utcnow()
            state.last_activity_at = datetime.utcnow()
            state.error_message = reason
            
            # Cancel all current tasks
            for task_id in state.current_tasks:
                await self._update_task_status(workflow_id, task_id, TaskStatus.CANCELLED)
            
            state.current_tasks.clear()
            
            await self._persist_workflow_state(state)
            del self.running_workflows[workflow_id]
            return True
        return False
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register custom task handler."""
        self.task_handlers[task_type] = handler
    
    def register_condition_evaluator(self, condition_type: str, evaluator: Callable):
        """Register custom condition evaluator."""
        self.condition_evaluators[condition_type] = evaluator 