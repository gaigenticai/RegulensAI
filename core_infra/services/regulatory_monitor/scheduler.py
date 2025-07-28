"""
Regulatory Scheduler - Task Management and Scheduling
Manages background monitoring tasks and ensures reliable data collection.
"""

import asyncio
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
from contextlib import asynccontextmanager

from core_infra.database.connection import get_database
from core_infra.services.monitoring import track_operation
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class ScheduledTask:
    """Represents a scheduled monitoring task."""
    id: str
    name: str
    task_type: str  # 'regulatory_monitor', 'compliance_check', 'document_analysis'
    source_id: Optional[str]
    interval_minutes: int
    priority: TaskPriority
    status: TaskStatus = TaskStatus.SCHEDULED
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    failure_count: int = 0
    max_failures: int = 3
    timeout_seconds: int = 300
    retry_delay_minutes: int = 5
    enabled: bool = True
    task_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskExecution:
    """Represents a task execution instance."""
    id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class RegulatoryScheduler:
    """
    Manages scheduled tasks for regulatory monitoring and compliance checking.
    Provides reliable task execution with retry logic and failure handling.
    """
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.execution_history: List[TaskExecution] = []
        self.max_history_size = 1000
    
    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting regulatory scheduler")
        self.is_running = True
        
        # Load tasks from database
        await self._load_tasks_from_database()
        
        # Register default task handlers
        self._register_default_handlers()
        
        # Start scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info(f"Scheduler started with {len(self.tasks)} tasks")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return
        
        logger.info("Stopping regulatory scheduler")
        self.is_running = False
        
        # Cancel scheduler task
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            logger.info(f"Cancelling running task: {task_id}")
            task.cancel()
        
        # Wait for running tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        self.running_tasks.clear()
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                await self._process_scheduled_tasks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_scheduled_tasks(self):
        """Process tasks that are due for execution."""
        current_time = datetime.utcnow()
        
        for task in self.tasks.values():
            if not task.enabled:
                continue
            
            if task.status == TaskStatus.RUNNING:
                # Check for timeout
                await self._check_task_timeout(task)
                continue
            
            if self._is_task_due(task, current_time):
                await self._execute_task(task)
    
    def _is_task_due(self, task: ScheduledTask, current_time: datetime) -> bool:
        """Check if a task is due for execution."""
        if task.next_run is None:
            # First run
            return True
        
        return current_time >= task.next_run
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        if task.id in self.running_tasks:
            logger.warning(f"Task {task.id} is already running")
            return
        
        if task.failure_count >= task.max_failures:
            logger.warning(f"Task {task.id} has exceeded max failures, disabling")
            task.enabled = False
            await self._update_task_in_database(task)
            return
        
        logger.info(f"Executing task: {task.name} ({task.id})")
        
        # Create execution record
        execution = TaskExecution(
            id=f"{task.id}_{int(datetime.utcnow().timestamp())}",
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.utcnow()
        task.next_run = self._calculate_next_run(task)
        
        try:
            # Get task handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise Exception(f"No handler found for task type: {task.task_type}")
            
            # Execute task with timeout
            task_coroutine = self._run_task_with_timeout(handler, task, execution)
            self.running_tasks[task.id] = asyncio.create_task(task_coroutine)
            
        except Exception as e:
            logger.error(f"Failed to start task {task.id}: {e}")
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            
            await self._record_execution(execution)
            await self._update_task_in_database(task)
    
    async def _run_task_with_timeout(self, handler: Callable, task: ScheduledTask, execution: TaskExecution):
        """Run task with timeout and error handling."""
        try:
            # Execute task with timeout
            result = await asyncio.wait_for(
                handler(task.task_data),
                timeout=task.timeout_seconds
            )
            
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.failure_count = 0  # Reset failure count on success
            
            execution.status = TaskStatus.COMPLETED
            execution.result = result
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            
            logger.info(f"Task {task.id} completed successfully in {execution.duration_seconds:.2f}s")
            
        except asyncio.TimeoutError:
            logger.error(f"Task {task.id} timed out after {task.timeout_seconds}s")
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
            execution.status = TaskStatus.FAILED
            execution.error_message = f"Task timed out after {task.timeout_seconds} seconds"
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = task.timeout_seconds
            
        except asyncio.CancelledError:
            logger.info(f"Task {task.id} was cancelled")
            task.status = TaskStatus.CANCELLED
            
            execution.status = TaskStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            
        finally:
            # Clean up running task
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
            
            # Record execution
            await self._record_execution(execution)
            
            # Update task in database
            await self._update_task_in_database(task)
            
            # Schedule retry if needed
            if task.status == TaskStatus.FAILED and task.failure_count < task.max_failures:
                await self._schedule_retry(task)
    
    async def _check_task_timeout(self, task: ScheduledTask):
        """Check if a running task has timed out."""
        if task.last_run is None:
            return
        
        elapsed = (datetime.utcnow() - task.last_run).total_seconds()
        if elapsed > task.timeout_seconds:
            logger.warning(f"Task {task.id} appears to be stuck, attempting to cancel")
            
            # Cancel the running task
            if task.id in self.running_tasks:
                self.running_tasks[task.id].cancel()
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calculate the next run time for a task."""
        return datetime.utcnow() + timedelta(minutes=task.interval_minutes)
    
    async def _schedule_retry(self, task: ScheduledTask):
        """Schedule a retry for a failed task."""
        retry_delay = task.retry_delay_minutes * (2 ** min(task.failure_count - 1, 4))  # Exponential backoff
        task.next_run = datetime.utcnow() + timedelta(minutes=retry_delay)
        
        logger.info(f"Scheduling retry for task {task.id} in {retry_delay} minutes")
    
    def _register_default_handlers(self):
        """Register default task handlers."""
        self.task_handlers.update({
            'regulatory_monitor': self._handle_regulatory_monitor,
            'compliance_check': self._handle_compliance_check,
            'document_analysis': self._handle_document_analysis,
            'risk_assessment': self._handle_risk_assessment,
            'notification_check': self._handle_notification_check
        })
    
    async def _handle_regulatory_monitor(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle regulatory monitoring task."""
        from .monitor import regulatory_monitor
        
        source_id = task_data.get('source_id')
        if not source_id:
            raise ValueError("source_id required for regulatory monitoring task")
        
        # Get source configuration
        source = next((s for s in regulatory_monitor.sources if s.id == source_id), None)
        if not source:
            raise ValueError(f"Unknown source: {source_id}")
        
        # Perform monitoring check
        await regulatory_monitor._check_source_updates(source)
        
        return {
            'source_id': source_id,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_compliance_check(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle compliance checking task."""
        # Implement compliance checking logic
        check_type = task_data.get('check_type', 'general')
        
        result = {
            'check_type': check_type,
            'status': 'completed',
            'findings': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add specific compliance check logic here
        if check_type == 'aml_transaction_review':
            result['findings'] = await self._check_aml_transactions()
        elif check_type == 'kyc_document_expiry':
            result['findings'] = await self._check_kyc_expiry()
        elif check_type == 'regulatory_deadline_monitor':
            result['findings'] = await self._check_regulatory_deadlines()
        
        return result
    
    async def _handle_document_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document analysis task."""
        from .analyzer import RegulatoryAnalyzer
        
        document_id = task_data.get('document_id')
        if not document_id:
            raise ValueError("document_id required for document analysis task")
        
        analyzer = RegulatoryAnalyzer()
        
        # Get document data from database
        async with get_database() as db:
            query = "SELECT * FROM regulatory_documents WHERE id = $1"
            document = await db.fetchrow(query, document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
        
        # Perform analysis
        document_data = dict(document)
        await analyzer.analyze_document(document_id, document_data)
        
        return {
            'document_id': document_id,
            'status': 'analyzed',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _handle_risk_assessment(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle risk assessment task."""
        assessment_type = task_data.get('assessment_type', 'general')
        
        result = {
            'assessment_type': assessment_type,
            'risk_level': 'medium',
            'findings': [],
            'recommendations': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add risk assessment logic here
        return result
    
    async def _handle_notification_check(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle notification checking task."""
        # Check for pending notifications and send them
        notification_count = 0
        
        # Implementation would check notification queue and send pending notifications
        
        return {
            'notifications_sent': notification_count,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _check_aml_transactions(self) -> List[Dict[str, Any]]:
        """Check for suspicious AML transactions."""
        findings = []
        
        async with get_database() as db:
            query = """
                SELECT t.id, t.transaction_id, t.amount, t.suspicious_activity_score, c.full_name
                FROM transactions t
                JOIN customers c ON t.customer_id = c.id
                WHERE t.aml_status = 'flagged' 
                AND t.transaction_date > NOW() - INTERVAL '24 hours'
            """
            rows = await db.fetch(query)
            
            for row in rows:
                findings.append({
                    'type': 'suspicious_transaction',
                    'transaction_id': row['transaction_id'],
                    'amount': float(row['amount']),
                    'customer': row['full_name'],
                    'risk_score': float(row['suspicious_activity_score']) if row['suspicious_activity_score'] else 0,
                    'action_required': 'review_and_investigate'
                })
        
        return findings
    
    async def _check_kyc_expiry(self) -> List[Dict[str, Any]]:
        """Check for expiring KYC documents."""
        findings = []
        
        async with get_database() as db:
            query = """
                SELECT id, full_name, due_diligence_date, next_review_date
                FROM customers
                WHERE next_review_date <= NOW() + INTERVAL '30 days'
                AND kyc_status = 'verified'
            """
            rows = await db.fetch(query)
            
            for row in rows:
                days_until_expiry = (row['next_review_date'] - datetime.utcnow()).days
                findings.append({
                    'type': 'kyc_review_due',
                    'customer_id': row['id'],
                    'customer_name': row['full_name'],
                    'days_until_expiry': days_until_expiry,
                    'action_required': 'schedule_kyc_review'
                })
        
        return findings
    
    async def _check_regulatory_deadlines(self) -> List[Dict[str, Any]]:
        """Check for upcoming regulatory deadlines."""
        findings = []
        
        async with get_database() as db:
            query = """
                SELECT ro.id, ro.obligation_text, ro.compliance_deadline, rd.title
                FROM regulatory_obligations ro
                JOIN regulatory_documents rd ON ro.document_id = rd.id
                WHERE ro.compliance_deadline <= NOW() + INTERVAL '90 days'
                AND ro.compliance_deadline > NOW()
            """
            rows = await db.fetch(query)
            
            for row in rows:
                days_until_deadline = (row['compliance_deadline'] - datetime.utcnow()).days
                findings.append({
                    'type': 'regulatory_deadline',
                    'obligation_id': row['id'],
                    'document_title': row['title'],
                    'obligation': row['obligation_text'][:200] + '...',
                    'days_until_deadline': days_until_deadline,
                    'action_required': 'prepare_compliance_response'
                })
        
        return findings
    
    async def add_task(self, task: ScheduledTask) -> bool:
        """Add a new scheduled task."""
        try:
            # Set next run time if not specified
            if task.next_run is None:
                task.next_run = self._calculate_next_run(task)
            
            # Add to memory
            self.tasks[task.id] = task
            
            # Save to database
            await self._save_task_to_database(task)
            
            logger.info(f"Added scheduled task: {task.name} ({task.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add task {task.id}: {e}")
            return False
    
    async def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        try:
            # Cancel if running
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            # Remove from memory
            if task_id in self.tasks:
                del self.tasks[task_id]
            
            # Remove from database
            await self._remove_task_from_database(task_id)
            
            logger.info(f"Removed scheduled task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a scheduled task."""
        try:
            if task_id not in self.tasks:
                raise ValueError(f"Task not found: {task_id}")
            
            task = self.tasks[task_id]
            
            # Update task properties
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            task.updated_at = datetime.utcnow()
            
            # Update next run time if interval changed
            if 'interval_minutes' in updates:
                task.next_run = self._calculate_next_run(task)
            
            # Update in database
            await self._update_task_in_database(task)
            
            logger.info(f"Updated scheduled task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        return {
            'id': task.id,
            'name': task.name,
            'type': task.task_type,
            'status': task.status.value,
            'enabled': task.enabled,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'failure_count': task.failure_count,
            'max_failures': task.max_failures,
            'interval_minutes': task.interval_minutes,
            'priority': task.priority.value
        }
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """Get status information for all tasks."""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    async def _load_tasks_from_database(self):
        """Load tasks from database."""
        try:
            # Create scheduled_tasks table if it doesn't exist
            await self._ensure_tasks_table()
            
            async with get_database() as db:
                query = "SELECT * FROM scheduled_tasks WHERE enabled = true"
                rows = await db.fetch(query)
                
                for row in rows:
                    task = ScheduledTask(
                        id=row['id'],
                        name=row['name'],
                        task_type=row['task_type'],
                        source_id=row['source_id'],
                        interval_minutes=row['interval_minutes'],
                        priority=TaskPriority(row['priority']),
                        status=TaskStatus(row['status']),
                        last_run=row['last_run'],
                        next_run=row['next_run'],
                        failure_count=row['failure_count'],
                        max_failures=row['max_failures'],
                        timeout_seconds=row['timeout_seconds'],
                        retry_delay_minutes=row['retry_delay_minutes'],
                        enabled=row['enabled'],
                        task_data=json.loads(row['task_data']) if row['task_data'] else {},
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    self.tasks[task.id] = task
                
                logger.info(f"Loaded {len(self.tasks)} tasks from database")
                
        except Exception as e:
            logger.error(f"Failed to load tasks from database: {e}")
    
    async def _ensure_tasks_table(self):
        """Ensure the scheduled_tasks table exists."""
        async with get_database() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id text PRIMARY KEY,
                    name text NOT NULL,
                    task_type text NOT NULL,
                    source_id text,
                    interval_minutes integer NOT NULL,
                    priority text NOT NULL DEFAULT 'normal',
                    status text NOT NULL DEFAULT 'scheduled',
                    last_run timestamp with time zone,
                    next_run timestamp with time zone,
                    failure_count integer NOT NULL DEFAULT 0,
                    max_failures integer NOT NULL DEFAULT 3,
                    timeout_seconds integer NOT NULL DEFAULT 300,
                    retry_delay_minutes integer NOT NULL DEFAULT 5,
                    enabled boolean NOT NULL DEFAULT true,
                    task_data text,
                    created_at timestamp with time zone DEFAULT now(),
                    updated_at timestamp with time zone DEFAULT now()
                )
            """)
    
    async def _save_task_to_database(self, task: ScheduledTask):
        """Save task to database."""
        async with get_database() as db:
            query = """
                INSERT INTO scheduled_tasks (
                    id, name, task_type, source_id, interval_minutes, priority,
                    status, last_run, next_run, failure_count, max_failures,
                    timeout_seconds, retry_delay_minutes, enabled, task_data,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    task_type = EXCLUDED.task_type,
                    source_id = EXCLUDED.source_id,
                    interval_minutes = EXCLUDED.interval_minutes,
                    priority = EXCLUDED.priority,
                    status = EXCLUDED.status,
                    last_run = EXCLUDED.last_run,
                    next_run = EXCLUDED.next_run,
                    failure_count = EXCLUDED.failure_count,
                    max_failures = EXCLUDED.max_failures,
                    timeout_seconds = EXCLUDED.timeout_seconds,
                    retry_delay_minutes = EXCLUDED.retry_delay_minutes,
                    enabled = EXCLUDED.enabled,
                    task_data = EXCLUDED.task_data,
                    updated_at = EXCLUDED.updated_at
            """
            
            await db.execute(
                query, task.id, task.name, task.task_type, task.source_id,
                task.interval_minutes, task.priority.value, task.status.value,
                task.last_run, task.next_run, task.failure_count, task.max_failures,
                task.timeout_seconds, task.retry_delay_minutes, task.enabled,
                json.dumps(task.task_data), task.created_at, task.updated_at
            )
    
    async def _update_task_in_database(self, task: ScheduledTask):
        """Update task in database."""
        task.updated_at = datetime.utcnow()
        await self._save_task_to_database(task)
    
    async def _remove_task_from_database(self, task_id: str):
        """Remove task from database."""
        async with get_database() as db:
            await db.execute("DELETE FROM scheduled_tasks WHERE id = $1", task_id)
    
    async def _record_execution(self, execution: TaskExecution):
        """Record task execution in history."""
        self.execution_history.append(execution)
        
        # Trim history if it gets too large
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size//2:]
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a custom task handler."""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered task handler for type: {task_type}")
    
    async def create_regulatory_monitoring_tasks(self):
        """Create default regulatory monitoring tasks."""
        from .monitor import regulatory_monitor
        
        for source in regulatory_monitor.sources:
            if not source.is_active:
                continue
            
            task = ScheduledTask(
                id=f"regulatory_monitor_{source.id}",
                name=f"Monitor {source.name}",
                task_type="regulatory_monitor",
                source_id=source.id,
                interval_minutes=source.update_frequency,
                priority=TaskPriority.HIGH,
                task_data={"source_id": source.id},
                timeout_seconds=600,  # 10 minutes timeout
                max_failures=5
            )
            
            await self.add_task(task)


# Global scheduler instance
regulatory_scheduler = RegulatoryScheduler()


async def start_scheduler():
    """Start the regulatory scheduler."""
    await regulatory_scheduler.start()


async def stop_scheduler():
    """Stop the regulatory scheduler."""
    await regulatory_scheduler.stop()


async def get_scheduler_status():
    """Get scheduler status."""
    return {
        'is_running': regulatory_scheduler.is_running,
        'total_tasks': len(regulatory_scheduler.tasks),
        'running_tasks': len(regulatory_scheduler.running_tasks),
        'tasks': regulatory_scheduler.get_all_tasks_status()
    } 