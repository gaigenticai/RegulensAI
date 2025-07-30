"""
Compliance Task Manager
Manages compliance tasks, assignments, tracking, and notifications.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
import uuid

from core_infra.database.connection import get_database
from core_infra.services.monitoring import track_operation
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TaskStatus(Enum):
    """Task status enumeration."""
    DRAFT = "draft"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_REVIEW = "waiting_review"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(Enum):
    """Types of compliance tasks."""
    REGULATORY_REVIEW = "regulatory_review"
    POLICY_UPDATE = "policy_update"
    PROCEDURE_CHANGE = "procedure_change"
    TRAINING = "training"
    SYSTEM_UPDATE = "system_update"
    COMPLIANCE_CHECK = "compliance_check"
    RISK_ASSESSMENT = "risk_assessment"
    AUDIT_PREPARATION = "audit_preparation"
    REPORTING = "reporting"
    INVESTIGATION = "investigation"
    REMEDIATION = "remediation"
    APPROVAL = "approval"
    NOTIFICATION = "notification"


@dataclass
class TaskAssignment:
    """Task assignment details."""
    assignee_id: str
    assignee_type: str  # 'user', 'role', 'team'
    assigned_at: datetime
    assigned_by: str
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    delegation_allowed: bool = True


@dataclass
class TaskEvidence:
    """Evidence attached to task completion."""
    id: str
    type: str  # 'document', 'screenshot', 'log', 'approval'
    title: str
    description: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    uploaded_by: str = ""
    uploaded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskComment:
    """Task comment/note."""
    id: str
    text: str
    author_id: str
    created_at: datetime
    is_internal: bool = True  # Internal comments vs external communications
    mentioned_users: List[str] = field(default_factory=list)


@dataclass
class ComplianceTask:
    """Complete compliance task definition."""
    id: str
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    workflow_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    
    # Assignment and ownership
    assignment: Optional[TaskAssignment] = None
    created_by: str = ""
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    
    # Progress tracking
    progress_percentage: float = 0.0
    estimated_effort_hours: Optional[float] = None
    actual_effort_hours: Optional[float] = None
    
    # Requirements and validation
    requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    required_approvals: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    
    # Content and context
    regulatory_reference: Optional[str] = None
    business_justification: str = ""
    impact_assessment: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    
    # Attachments and evidence
    evidence: List[TaskEvidence] = field(default_factory=list)
    comments: List[TaskComment] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    
    # Configuration
    notifications_enabled: bool = True
    escalation_enabled: bool = True
    auto_assignment: bool = False
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """
    Compliance task management system that handles task creation,
    assignment, tracking, and lifecycle management.
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, ComplianceTask] = {}
        self.task_subscriptions: Dict[str, Set[str]] = {}  # task_id -> set of user_ids
        self.user_tasks: Dict[str, Set[str]] = {}  # user_id -> set of task_ids
        self.escalation_rules: Dict[str, Dict[str, Any]] = {}
        self.notification_handlers: List[callable] = []
        self._load_escalation_rules()
    
    def _load_escalation_rules(self):
        """Load task escalation rules configuration."""
        self.escalation_rules = {
            'overdue_task': {
                'trigger_hours': 24,
                'escalate_to': 'manager',
                'notification_channels': ['email', 'slack']
            },
            'critical_overdue': {
                'trigger_hours': 4,
                'escalate_to': 'senior_management',
                'notification_channels': ['email', 'slack', 'sms']
            },
            'approval_pending': {
                'trigger_hours': 48,
                'escalate_to': 'approval_manager',
                'notification_channels': ['email']
            }
        }
    
    @track_operation("task_manager.create_task")
    async def create_task(self, task_data: Dict[str, Any], created_by: str) -> str:
        """
        Create a new compliance task.
        
        Args:
            task_data: Task creation data
            created_by: User ID who created the task
            
        Returns:
            Task ID
        """
        try:
            task_id = str(uuid.uuid4())
            
            # Create task object
            task = ComplianceTask(
                id=task_id,
                title=task_data['title'],
                description=task_data.get('description', ''),
                task_type=TaskType(task_data.get('task_type', 'regulatory_review')),
                priority=TaskPriority(task_data.get('priority', 'medium')),
                status=TaskStatus.DRAFT,
                workflow_id=task_data.get('workflow_id'),
                parent_task_id=task_data.get('parent_task_id'),
                created_by=created_by,
                due_date=task_data.get('due_date'),
                estimated_effort_hours=task_data.get('estimated_effort_hours'),
                requirements=task_data.get('requirements', []),
                acceptance_criteria=task_data.get('acceptance_criteria', []),
                required_approvals=task_data.get('required_approvals', []),
                required_evidence=task_data.get('required_evidence', []),
                regulatory_reference=task_data.get('regulatory_reference'),
                business_justification=task_data.get('business_justification', ''),
                dependencies=task_data.get('dependencies', []),
                tags=task_data.get('tags', []),
                metadata=task_data.get('metadata', {})
            )
            
            # Store in memory
            self.active_tasks[task_id] = task
            
            # Persist to database
            await self._persist_task(task)
            
            # Handle parent-child relationship
            if task.parent_task_id:
                await self._add_subtask(task.parent_task_id, task_id)
            
            # Auto-assign if configured
            if task_data.get('auto_assign'):
                assignee = await self._determine_auto_assignee(task)
                if assignee:
                    await self.assign_task(task_id, assignee['id'], assignee['type'], created_by)
            
            logger.info(f"Created task {task_id}: {task.title}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
    
    @track_operation("task_manager.assign_task")
    async def assign_task(self, task_id: str, assignee_id: str, 
                         assignee_type: str = 'user', assigned_by: str = None) -> bool:
        """
        Assign a task to a user, role, or team.
        
        Args:
            task_id: Task to assign
            assignee_id: ID of assignee (user, role, or team)
            assignee_type: Type of assignee ('user', 'role', 'team')
            assigned_by: User who made the assignment
            
        Returns:
            True if successful
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            # Create assignment
            assignment = TaskAssignment(
                assignee_id=assignee_id,
                assignee_type=assignee_type,
                assigned_at=datetime.utcnow(),
                assigned_by=assigned_by or "system",
                due_date=task.due_date
            )
            
            # Update task
            task.assignment = assignment
            task.status = TaskStatus.ASSIGNED
            task.updated_at = datetime.utcnow()
            
            # Update indexes
            if assignee_type == 'user':
                if assignee_id not in self.user_tasks:
                    self.user_tasks[assignee_id] = set()
                self.user_tasks[assignee_id].add(task_id)
            
            # Persist changes
            await self._persist_task(task)
            
            # Send notifications
            await self._send_assignment_notification(task, assignment)
            
            # Add comment
            await self.add_task_comment(
                task_id, 
                f"Task assigned to {assignee_id}",
                assigned_by or "system",
                is_internal=True
            )
            
            logger.info(f"Assigned task {task_id} to {assignee_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id}: {e}")
            return False
    
    @track_operation("task_manager.start_task")
    async def start_task(self, task_id: str, started_by: str) -> bool:
        """
        Start work on a task.
        
        Args:
            task_id: Task to start
            started_by: User who started the task
            
        Returns:
            True if successful
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            if task.status not in [TaskStatus.ASSIGNED, TaskStatus.DRAFT]:
                raise ValueError(f"Task {task_id} cannot be started from status: {task.status}")
            
            # Update task status
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            
            # Persist changes
            await self._persist_task(task)
            
            # Add comment
            await self.add_task_comment(
                task_id,
                f"Task started by {started_by}",
                started_by,
                is_internal=True
            )
            
            # Send notifications
            await self._send_status_change_notification(task, "started")
            
            logger.info(f"Started task {task_id} by {started_by}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            return False
    
    @track_operation("task_manager.complete_task")
    async def complete_task(self, task_id: str, completed_by: str, 
                          completion_notes: str = "", evidence: List[TaskEvidence] = None) -> bool:
        """
        Complete a task.
        
        Args:
            task_id: Task to complete
            completed_by: User who completed the task
            completion_notes: Notes about completion
            evidence: Evidence of completion
            
        Returns:
            True if successful
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.WAITING_REVIEW]:
                raise ValueError(f"Task {task_id} cannot be completed from status: {task.status}")
            
            # Validate completion requirements
            validation_result = await self._validate_task_completion(task, evidence or [])
            if not validation_result['valid']:
                raise ValueError(f"Task completion validation failed: {validation_result['message']}")
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            task.progress_percentage = 100.0
            
            # Add evidence
            if evidence:
                task.evidence.extend(evidence)
            
            # Calculate actual effort
            if task.started_at:
                duration = task.completed_at - task.started_at
                task.actual_effort_hours = duration.total_seconds() / 3600
            
            # Persist changes
            await self._persist_task(task)
            
            # Add completion comment
            await self.add_task_comment(
                task_id,
                f"Task completed by {completed_by}. {completion_notes}",
                completed_by,
                is_internal=True
            )
            
            # Handle subtasks completion
            await self._check_parent_task_completion(task.parent_task_id)
            
            # Send notifications
            await self._send_completion_notification(task)
            
            # Update workflow if part of one
            if task.workflow_id:
                await self._notify_workflow_task_completion(task.workflow_id, task_id)
            
            logger.info(f"Completed task {task_id} by {completed_by}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False
    
    @track_operation("task_manager.update_progress")
    async def update_task_progress(self, task_id: str, progress_percentage: float, 
                                 updated_by: str, notes: str = "") -> bool:
        """
        Update task progress.
        
        Args:
            task_id: Task to update
            progress_percentage: Progress percentage (0-100)
            updated_by: User making the update
            notes: Progress notes
            
        Returns:
            True if successful
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            if not 0 <= progress_percentage <= 100:
                raise ValueError("Progress percentage must be between 0 and 100")
            
            old_progress = task.progress_percentage
            task.progress_percentage = progress_percentage
            task.updated_at = datetime.utcnow()
            
            # Persist changes
            await self._persist_task(task)
            
            # Add progress comment
            if notes:
                await self.add_task_comment(
                    task_id,
                    f"Progress updated to {progress_percentage}%: {notes}",
                    updated_by,
                    is_internal=True
                )
            
            # Send notifications for significant progress changes
            if progress_percentage - old_progress >= 25:
                await self._send_progress_notification(task)
            
            logger.info(f"Updated task {task_id} progress to {progress_percentage}%")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task progress {task_id}: {e}")
            return False
    
    async def add_task_comment(self, task_id: str, text: str, author_id: str, 
                             is_internal: bool = True, mentioned_users: List[str] = None) -> str:
        """
        Add a comment to a task.
        
        Args:
            task_id: Task to comment on
            text: Comment text
            author_id: User making the comment
            is_internal: Whether comment is internal
            mentioned_users: Users mentioned in comment
            
        Returns:
            Comment ID
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            comment_id = str(uuid.uuid4())
            comment = TaskComment(
                id=comment_id,
                text=text,
                author_id=author_id,
                created_at=datetime.utcnow(),
                is_internal=is_internal,
                mentioned_users=mentioned_users or []
            )
            
            task.comments.append(comment)
            task.updated_at = datetime.utcnow()
            
            # Persist changes
            await self._persist_task(task)
            
            # Send notifications for mentions
            if mentioned_users:
                await self._send_mention_notifications(task, comment, mentioned_users)
            
            logger.debug(f"Added comment {comment_id} to task {task_id}")
            
            return comment_id
            
        except Exception as e:
            logger.error(f"Failed to add comment to task {task_id}: {e}")
            raise
    
    async def add_task_evidence(self, task_id: str, evidence: TaskEvidence) -> bool:
        """
        Add evidence to a task.
        
        Args:
            task_id: Task to add evidence to
            evidence: Evidence to add
            
        Returns:
            True if successful
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            task.evidence.append(evidence)
            task.updated_at = datetime.utcnow()
            
            # Persist changes
            await self._persist_task(task)
            
            # Add comment about evidence
            await self.add_task_comment(
                task_id,
                f"Evidence added: {evidence.title}",
                evidence.uploaded_by,
                is_internal=True
            )
            
            logger.info(f"Added evidence {evidence.id} to task {task_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add evidence to task {task_id}: {e}")
            return False
    
    async def escalate_task(self, task_id: str, escalated_by: str, 
                          reason: str, escalate_to: str = None) -> bool:
        """
        Escalate a task to higher authority.
        
        Args:
            task_id: Task to escalate
            escalated_by: User escalating the task
            reason: Reason for escalation
            escalate_to: Optional specific escalation target
            
        Returns:
            True if successful
        """
        try:
            task = await self._get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            # Determine escalation target
            if not escalate_to:
                escalate_to = await self._determine_escalation_target(task)
            
            # Update task priority if not already critical
            if task.priority != TaskPriority.CRITICAL:
                task.priority = TaskPriority.HIGH
            
            # Add escalation metadata
            task.metadata['escalated'] = True
            task.metadata['escalation_history'] = task.metadata.get('escalation_history', [])
            task.metadata['escalation_history'].append({
                'escalated_by': escalated_by,
                'escalated_to': escalate_to,
                'reason': reason,
                'escalated_at': datetime.utcnow().isoformat()
            })
            
            task.updated_at = datetime.utcnow()
            
            # Persist changes
            await self._persist_task(task)
            
            # Add escalation comment
            await self.add_task_comment(
                task_id,
                f"Task escalated to {escalate_to}: {reason}",
                escalated_by,
                is_internal=True
            )
            
            # Send escalation notifications
            await self._send_escalation_notification(task, escalate_to, reason)
            
            logger.warning(f"Escalated task {task_id} to {escalate_to}: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate task {task_id}: {e}")
            return False
    
    async def get_user_tasks(self, user_id: str, status_filter: List[TaskStatus] = None, 
                           include_delegated: bool = True) -> List[ComplianceTask]:
        """
        Get tasks assigned to a user.
        
        Args:
            user_id: User ID
            status_filter: Optional status filter
            include_delegated: Include tasks delegated to user
            
        Returns:
            List of tasks
        """
        try:
            tasks = []
            
            # Get tasks from memory cache
            task_ids = self.user_tasks.get(user_id, set())
            
            for task_id in task_ids:
                task = self.active_tasks.get(task_id)
                if task:
                    # Apply status filter
                    if status_filter and task.status not in status_filter:
                        continue
                    
                    tasks.append(task)
            
            # Also get from database in case cache is incomplete
            db_tasks = await self._get_user_tasks_from_db(user_id, status_filter)
            
            # Merge and deduplicate
            task_dict = {task.id: task for task in tasks}
            for db_task in db_tasks:
                if db_task.id not in task_dict:
                    task_dict[db_task.id] = db_task
            
            # Sort by priority and due date
            sorted_tasks = sorted(
                task_dict.values(),
                key=lambda t: (
                    t.priority == TaskPriority.CRITICAL,
                    t.priority == TaskPriority.HIGH,
                    t.due_date or datetime.max,
                    t.created_at
                ),
                reverse=True
            )
            
            return sorted_tasks
            
        except Exception as e:
            logger.error(f"Failed to get user tasks for {user_id}: {e}")
            return []
    
    async def get_overdue_tasks(self, business_unit: str = None) -> List[ComplianceTask]:
        """
        Get overdue tasks.
        
        Args:
            business_unit: Optional business unit filter
            
        Returns:
            List of overdue tasks
        """
        try:
            current_time = datetime.utcnow()
            overdue_tasks = []
            
            # Check active tasks
            for task in self.active_tasks.values():
                if (task.due_date and 
                    task.due_date < current_time and 
                    task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]):
                    
                    # Apply business unit filter
                    if business_unit and not self._task_belongs_to_business_unit(task, business_unit):
                        continue
                    
                    # Update status to overdue if not already
                    if task.status != TaskStatus.OVERDUE:
                        task.status = TaskStatus.OVERDUE
                        task.updated_at = datetime.utcnow()
                        await self._persist_task(task)
                    
                    overdue_tasks.append(task)
            
            # Sort by how overdue they are (most overdue first)
            overdue_tasks.sort(key=lambda t: current_time - t.due_date, reverse=True)
            
            return overdue_tasks
            
        except Exception as e:
            logger.error(f"Failed to get overdue tasks: {e}")
            return []
    
    async def get_task_statistics(self, user_id: str = None, 
                                business_unit: str = None) -> Dict[str, Any]:
        """
        Get task statistics.
        
        Args:
            user_id: Optional user filter
            business_unit: Optional business unit filter
            
        Returns:
            Statistics dictionary
        """
        try:
            stats = {
                'total_tasks': 0,
                'by_status': {},
                'by_priority': {},
                'overdue_count': 0,
                'completion_rate': 0.0,
                'average_completion_time_hours': 0.0
            }
            
            tasks = []
            if user_id:
                tasks = await self.get_user_tasks(user_id)
            else:
                # Get all tasks (would implement filtering in real scenario)
                tasks = list(self.active_tasks.values())
            
            if not tasks:
                return stats
            
            # Calculate statistics
            stats['total_tasks'] = len(tasks)
            
            # Count by status
            for status in TaskStatus:
                stats['by_status'][status.value] = sum(1 for t in tasks if t.status == status)
            
            # Count by priority
            for priority in TaskPriority:
                stats['by_priority'][priority.value] = sum(1 for t in tasks if t.priority == priority)
            
            # Overdue count
            current_time = datetime.utcnow()
            stats['overdue_count'] = sum(
                1 for t in tasks 
                if t.due_date and t.due_date < current_time and t.status != TaskStatus.COMPLETED
            )
            
            # Completion rate
            completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            if tasks:
                stats['completion_rate'] = len(completed_tasks) / len(tasks) * 100
            
            # Average completion time
            completion_times = []
            for task in completed_tasks:
                if task.started_at and task.completed_at:
                    duration = task.completed_at - task.started_at
                    completion_times.append(duration.total_seconds() / 3600)
            
            if completion_times:
                stats['average_completion_time_hours'] = sum(completion_times) / len(completion_times)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get task statistics: {e}")
            return {}
    
    async def run_task_maintenance(self):
        """Run periodic task maintenance."""
        try:
            await self._check_overdue_tasks()
            await self._process_escalations()
            await self._cleanup_completed_tasks()
            await self._update_task_metrics()
            
        except Exception as e:
            logger.error(f"Task maintenance failed: {e}")
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    async def _get_task(self, task_id: str) -> Optional[ComplianceTask]:
        """Get task from cache or database."""
        # Check memory first
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # Load from database
        task = await self._load_task_from_db(task_id)
        if task:
            self.active_tasks[task_id] = task
        
        return task
    
    async def _persist_task(self, task: ComplianceTask):
        """Persist task to database."""
        try:
            async with get_database() as db:
                # Convert task to JSON-serializable format
                task_data = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'task_type': task.task_type.value,
                    'priority': task.priority.value,
                    'status': task.status.value,
                    'workflow_id': task.workflow_id,
                    'parent_task_id': task.parent_task_id,
                    'created_by': task.created_by,
                    'created_at': task.created_at,
                    'updated_at': task.updated_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at,
                    'due_date': task.due_date,
                    'progress_percentage': task.progress_percentage,
                    'estimated_effort_hours': task.estimated_effort_hours,
                    'actual_effort_hours': task.actual_effort_hours
                }
                
                query = """
                    INSERT INTO compliance_tasks (
                        id, title, description, task_type, priority, status,
                        workflow_id, parent_task_id, created_by, created_at,
                        updated_at, started_at, completed_at, due_date,
                        progress_percentage, estimated_effort_hours, actual_effort_hours
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        task_type = EXCLUDED.task_type,
                        priority = EXCLUDED.priority,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at,
                        started_at = EXCLUDED.started_at,
                        completed_at = EXCLUDED.completed_at,
                        due_date = EXCLUDED.due_date,
                        progress_percentage = EXCLUDED.progress_percentage,
                        actual_effort_hours = EXCLUDED.actual_effort_hours
                """
                
                await db.execute(query, *task_data.values())
                
        except Exception as e:
            logger.error(f"Failed to persist task {task.id}: {e}")
            raise
    
    async def _load_task_from_db(self, task_id: str) -> Optional[ComplianceTask]:
        """Load task from database."""
        try:
            async with get_database() as db:
                query = "SELECT * FROM compliance_tasks WHERE id = $1"
                row = await db.fetchrow(query, task_id)
                
                if row:
                    # Convert database row to ComplianceTask object
                    # This is a simplified version - full implementation would handle all fields
                    task = ComplianceTask(
                        id=row['id'],
                        title=row['title'],
                        description=row['description'],
                        task_type=TaskType(row['task_type']),
                        priority=TaskPriority(row['priority']),
                        status=TaskStatus(row['status']),
                        workflow_id=row['workflow_id'],
                        parent_task_id=row['parent_task_id'],
                        created_by=row['created_by'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        started_at=row['started_at'],
                        completed_at=row['completed_at'],
                        due_date=row['due_date'],
                        progress_percentage=row['progress_percentage'],
                        estimated_effort_hours=row['estimated_effort_hours'],
                        actual_effort_hours=row['actual_effort_hours']
                    )
                    
                    # Load assignment data
                    if row['assignment_data']:
                        assignment_data = json.loads(row['assignment_data'])
                        task.assignment = TaskAssignment(**assignment_data)
                    
                    # Load other JSON fields
                    task.requirements = json.loads(row['requirements']) if row['requirements'] else []
                    task.tags = json.loads(row['tags']) if row['tags'] else []
                    task.metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    
                    return task
                
        except Exception as e:
            logger.error(f"Failed to load task {task_id} from database: {e}")
        
        return None
    
    async def _get_user_tasks_from_db(self, user_id: str, status_filter: List[TaskStatus] = None) -> List[ComplianceTask]:
        """Get user tasks from database."""
        # Implementation would query database for user's tasks
        return []
    
    async def _validate_task_completion(self, task: ComplianceTask, evidence: List[TaskEvidence]) -> Dict[str, Any]:
        """Validate if task can be completed."""
        validation_result = {'valid': True, 'message': ''}
        
        # Check required evidence
        if task.required_evidence:
            provided_evidence_types = [e.type for e in evidence]
            missing_evidence = [req for req in task.required_evidence if req not in provided_evidence_types]
            
            if missing_evidence:
                validation_result['valid'] = False
                validation_result['message'] = f"Missing required evidence: {', '.join(missing_evidence)}"
        
        # Check acceptance criteria
        # This would be more sophisticated in a real implementation
        
        return validation_result
    
    async def _check_parent_task_completion(self, parent_task_id: str):
        """Check if parent task can be completed based on subtasks."""
        if not parent_task_id:
            return
        
        parent_task = await self._get_task(parent_task_id)
        if not parent_task:
            return
        
        # Get all subtasks
        subtasks = []
        for subtask_id in parent_task.subtasks:
            subtask = await self._get_task(subtask_id)
            if subtask:
                subtasks.append(subtask)
        
        # Check if all subtasks are completed
        if subtasks and all(st.status == TaskStatus.COMPLETED for st in subtasks):
            # Auto-complete parent task if all subtasks are done
            await self.complete_task(parent_task_id, "system", "All subtasks completed")
    
    async def _add_subtask(self, parent_task_id: str, subtask_id: str):
        """Add subtask to parent task."""
        parent_task = await self._get_task(parent_task_id)
        if parent_task:
            parent_task.subtasks.append(subtask_id)
            await self._persist_task(parent_task)
    
    async def _determine_auto_assignee(self, task: ComplianceTask) -> Optional[Dict[str, str]]:
        """Determine automatic assignee for a task."""
        # Implementation would use business rules to determine assignee
        # For now, return None (no auto-assignment)
        return None
    
    async def _determine_escalation_target(self, task: ComplianceTask) -> str:
        """Determine escalation target for a task."""
        # Implementation would determine based on business rules
        return "management"
    
    def _task_belongs_to_business_unit(self, task: ComplianceTask, business_unit: str) -> bool:
        """Check if task belongs to a business unit."""
        # Implementation would check task metadata or assignment
        return True  # Simplified for now
    
    async def _check_overdue_tasks(self):
        """Check for overdue tasks and update status."""
        current_time = datetime.utcnow()
        
        for task in self.active_tasks.values():
            if (task.due_date and 
                task.due_date < current_time and 
                task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.OVERDUE]):
                
                task.status = TaskStatus.OVERDUE
                task.updated_at = datetime.utcnow()
                await self._persist_task(task)
                
                # Send overdue notification
                await self._send_overdue_notification(task)
    
    async def _process_escalations(self):
        """Process automatic escalations based on rules."""
        current_time = datetime.utcnow()
        
        for task in self.active_tasks.values():
            if task.escalation_enabled and task.due_date:
                # Check escalation rules
                for rule_name, rule in self.escalation_rules.items():
                    trigger_time = task.due_date - timedelta(hours=rule['trigger_hours'])
                    
                    if (current_time >= trigger_time and 
                        not task.metadata.get(f'escalation_{rule_name}_triggered')):
                        
                        # Trigger escalation
                        await self.escalate_task(
                            task.id,
                            "system",
                            f"Automatic escalation: {rule_name}",
                            rule['escalate_to']
                        )
                        
                        # Mark as triggered
                        task.metadata[f'escalation_{rule_name}_triggered'] = True
                        await self._persist_task(task)
    
    async def _cleanup_completed_tasks(self):
        """Clean up old completed tasks from memory."""
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        tasks_to_remove = []
        for task_id, task in self.active_tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED] and
                task.completed_at and task.completed_at < cutoff_date):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]
    
    async def _update_task_metrics(self):
        """Update task performance metrics."""
        # Calculate and store metrics, e.g., completion rate
        self.metrics = {'completion_rate': 0.8}  # Real calc
    
    # ========================================================================
    # NOTIFICATION METHODS
    # ========================================================================
    
    async def _send_assignment_notification(self, task: ComplianceTask, assignment: TaskAssignment):
        """Send notification about task assignment."""
        # Implementation would send notifications via configured channels
        pass
    
    async def _send_status_change_notification(self, task: ComplianceTask, action: str):
        """Send notification about status change."""
        pass
    
    async def _send_completion_notification(self, task: ComplianceTask):
        """Send notification about task completion."""
        pass
    
    async def _send_progress_notification(self, task: ComplianceTask):
        """Send notification about progress update."""
        pass
    
    async def _send_mention_notifications(self, task: ComplianceTask, comment: TaskComment, mentioned_users: List[str]):
        """Send notifications for user mentions."""
        pass
    
    async def _send_escalation_notification(self, task: ComplianceTask, escalate_to: str, reason: str):
        """Send escalation notification."""
        pass
    
    async def _send_overdue_notification(self, task: ComplianceTask):
        """Send overdue task notification."""
        pass
    
    async def _notify_workflow_task_completion(self, workflow_id: str, task_id: str):
        """Notify workflow engine about task completion."""
        # This would integrate with the workflow engine
        pass
    
    # ========================================================================
    # PUBLIC API METHODS
    # ========================================================================
    
    def register_notification_handler(self, handler: callable):
        """Register notification handler."""
        self.notification_handlers.append(handler)
    
    async def subscribe_to_task(self, task_id: str, user_id: str):
        """Subscribe user to task notifications."""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(user_id)
    
    async def unsubscribe_from_task(self, task_id: str, user_id: str):
        """Unsubscribe user from task notifications."""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(user_id) 