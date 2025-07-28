"""
Workflow Orchestrator
Manages workflow triggers, execution coordination, and integration.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import structlog
import json
import uuid

from core_infra.database.connection import get_database
from core_infra.services.monitoring import track_operation
from core_infra.config import get_settings
from .workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowStatus
from .task_manager import TaskManager, ComplianceTask
from .impact_assessor import ImpactAssessor, RegulatoryImpact

logger = structlog.get_logger(__name__)
settings = get_settings()


class TriggerType(Enum):
    """Types of workflow triggers."""
    REGULATORY_CHANGE = "regulatory_change"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    THRESHOLD_BREACH = "threshold_breach"
    DEADLINE_APPROACHING = "deadline_approaching"
    TASK_COMPLETION = "task_completion"
    APPROVAL_REQUIRED = "approval_required"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SYSTEM_EVENT = "system_event"


@dataclass
class WorkflowTrigger:
    """Workflow trigger configuration."""
    id: str
    name: str
    trigger_type: TriggerType
    workflow_definition_id: str
    conditions: Dict[str, Any]
    enabled: bool = True
    priority: int = 1
    cooldown_minutes: int = 0
    last_triggered: Optional[datetime] = None
    metadata: Dict[str, Any] = None


class WorkflowOrchestrator:
    """
    Orchestrates workflow execution, manages triggers, and coordinates
    between different workflow components.
    """
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        self.task_manager = TaskManager()
        self.impact_assessor = ImpactAssessor()
        
        self.triggers: Dict[str, WorkflowTrigger] = {}
        self.trigger_handlers: Dict[TriggerType, Callable] = {}
        self.active_workflows: Dict[str, str] = {}  # workflow_id -> definition_id
        self.workflow_metrics: Dict[str, Dict[str, Any]] = {}
        
        self._register_trigger_handlers()
        self._load_workflow_triggers()
    
    def _register_trigger_handlers(self):
        """Register default trigger handlers."""
        self.trigger_handlers = {
            TriggerType.REGULATORY_CHANGE: self._handle_regulatory_change_trigger,
            TriggerType.SCHEDULED: self._handle_scheduled_trigger,
            TriggerType.MANUAL: self._handle_manual_trigger,
            TriggerType.THRESHOLD_BREACH: self._handle_threshold_breach_trigger,
            TriggerType.DEADLINE_APPROACHING: self._handle_deadline_approaching_trigger,
            TriggerType.TASK_COMPLETION: self._handle_task_completion_trigger,
            TriggerType.APPROVAL_REQUIRED: self._handle_approval_required_trigger,
            TriggerType.COMPLIANCE_VIOLATION: self._handle_compliance_violation_trigger,
            TriggerType.SYSTEM_EVENT: self._handle_system_event_trigger
        }
    
    async def _load_workflow_triggers(self):
        """Load workflow triggers from database."""
        try:
            async with get_database() as db:
                query = "SELECT * FROM workflow_triggers WHERE enabled = true"
                rows = await db.fetch(query)
                
                for row in rows:
                    trigger = WorkflowTrigger(
                        id=row['id'],
                        name=row['name'],
                        trigger_type=TriggerType(row['trigger_type']),
                        workflow_definition_id=row['workflow_definition_id'],
                        conditions=json.loads(row['conditions']),
                        enabled=row['enabled'],
                        priority=row['priority'],
                        cooldown_minutes=row['cooldown_minutes'],
                        last_triggered=row['last_triggered'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else {}
                    )
                    self.triggers[trigger.id] = trigger
                
                logger.info(f"Loaded {len(self.triggers)} workflow triggers")
                
        except Exception as e:
            logger.error(f"Failed to load workflow triggers: {e}")
    
    @track_operation("workflow_orchestrator.trigger_workflow")
    async def trigger_workflow(self, trigger_type: TriggerType, trigger_data: Dict[str, Any],
                             triggered_by: str = "system") -> List[str]:
        """
        Trigger workflows based on event type and data.
        
        Args:
            trigger_type: Type of trigger
            trigger_data: Data associated with the trigger
            triggered_by: Entity that caused the trigger
            
        Returns:
            List of started workflow IDs
        """
        try:
            started_workflows = []
            
            # Find matching triggers
            matching_triggers = self._find_matching_triggers(trigger_type, trigger_data)
            
            # Sort by priority
            matching_triggers.sort(key=lambda t: t.priority, reverse=True)
            
            for trigger in matching_triggers:
                # Check cooldown
                if not self._check_trigger_cooldown(trigger):
                    logger.debug(f"Trigger {trigger.id} in cooldown period")
                    continue
                
                # Evaluate conditions
                if not await self._evaluate_trigger_conditions(trigger, trigger_data):
                    logger.debug(f"Trigger {trigger.id} conditions not met")
                    continue
                
                try:
                    # Start workflow
                    workflow_id = await self.workflow_engine.start_workflow(
                        definition_id=trigger.workflow_definition_id,
                        triggered_by=triggered_by,
                        trigger_data={
                            **trigger_data,
                            'trigger_id': trigger.id,
                            'trigger_type': trigger_type.value
                        }
                    )
                    
                    started_workflows.append(workflow_id)
                    self.active_workflows[workflow_id] = trigger.workflow_definition_id
                    
                    # Update trigger timestamp
                    trigger.last_triggered = datetime.utcnow()
                    await self._update_trigger(trigger)
                    
                    logger.info(f"Triggered workflow {workflow_id} from trigger {trigger.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to start workflow for trigger {trigger.id}: {e}")
            
            return started_workflows
            
        except Exception as e:
            logger.error(f"Failed to trigger workflows: {e}")
            return []
    
    @track_operation("workflow_orchestrator.handle_regulatory_change")
    async def handle_regulatory_change(self, regulation_id: str, regulation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle regulatory change event with comprehensive workflow orchestration.
        
        Args:
            regulation_id: ID of the regulatory change
            regulation_data: Regulatory document data
            
        Returns:
            Orchestration result with workflows and assessments
        """
        try:
            logger.info(f"Handling regulatory change: {regulation_id}")
            
            result = {
                'regulation_id': regulation_id,
                'started_at': datetime.utcnow().isoformat(),
                'workflows_started': [],
                'impact_assessment': None,
                'tasks_created': [],
                'notifications_sent': [],
                'success': True,
                'errors': []
            }
            
            # Step 1: Perform impact assessment
            try:
                impact = await self.impact_assessor.assess_regulatory_impact(
                    regulation_id, regulation_data
                )
                result['impact_assessment'] = {
                    'impact_level': impact.impact_level.value,
                    'affected_business_units': impact.affected_business_units,
                    'estimated_cost': impact.estimated_cost,
                    'estimated_timeline': impact.estimated_timeline,
                    'compliance_deadline': impact.compliance_deadline.isoformat() if impact.compliance_deadline else None
                }
                
                logger.info(f"Impact assessment completed: {impact.impact_level.value}")
                
            except Exception as e:
                error_msg = f"Impact assessment failed: {e}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Step 2: Trigger workflows based on impact level
            trigger_data = {
                'regulation_id': regulation_id,
                'regulation_data': regulation_data,
                'impact_assessment': result.get('impact_assessment', {})
            }
            
            workflows = await self.trigger_workflow(
                TriggerType.REGULATORY_CHANGE,
                trigger_data,
                "regulatory_monitor"
            )
            result['workflows_started'] = workflows
            
            # Step 3: Create immediate compliance tasks for high/critical impact
            if result.get('impact_assessment', {}).get('impact_level') in ['critical', 'high']:
                tasks = await self._create_immediate_compliance_tasks(regulation_id, result['impact_assessment'])
                result['tasks_created'] = tasks
            
            # Step 4: Send notifications
            notifications = await self._send_regulatory_change_notifications(regulation_id, result)
            result['notifications_sent'] = notifications
            
            # Step 5: Schedule follow-up workflows
            await self._schedule_follow_up_workflows(regulation_id, result['impact_assessment'])
            
            result['completed_at'] = datetime.utcnow().isoformat()
            logger.info(f"Regulatory change handling completed for {regulation_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle regulatory change {regulation_id}: {e}")
            return {
                'regulation_id': regulation_id,
                'success': False,
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }
    
    async def create_workflow_definition(self, definition_data: Dict[str, Any], created_by: str) -> str:
        """
        Create a new workflow definition.
        
        Args:
            definition_data: Workflow definition data
            created_by: User creating the definition
            
        Returns:
            Workflow definition ID
        """
        try:
            definition_id = str(uuid.uuid4())
            
            # Create workflow definition
            definition = WorkflowDefinition(
                id=definition_id,
                name=definition_data['name'],
                description=definition_data.get('description', ''),
                version=definition_data.get('version', '1.0'),
                category=definition_data.get('category', 'general'),
                tasks=definition_data.get('tasks', []),
                triggers=definition_data.get('triggers', []),
                flow_logic=definition_data.get('flow_logic', {}),
                variables=definition_data.get('variables', {}),
                settings=definition_data.get('settings', {}),
                created_by=created_by
            )
            
            # Store in database
            await self._store_workflow_definition(definition)
            
            # Cache in workflow engine
            self.workflow_engine.workflow_definitions[definition_id] = definition
            
            logger.info(f"Created workflow definition {definition_id}: {definition.name}")
            
            return definition_id
            
        except Exception as e:
            logger.error(f"Failed to create workflow definition: {e}")
            raise
    
    async def create_workflow_trigger(self, trigger_data: Dict[str, Any], created_by: str) -> str:
        """
        Create a new workflow trigger.
        
        Args:
            trigger_data: Trigger configuration data
            created_by: User creating the trigger
            
        Returns:
            Trigger ID
        """
        try:
            trigger_id = str(uuid.uuid4())
            
            trigger = WorkflowTrigger(
                id=trigger_id,
                name=trigger_data['name'],
                trigger_type=TriggerType(trigger_data['trigger_type']),
                workflow_definition_id=trigger_data['workflow_definition_id'],
                conditions=trigger_data.get('conditions', {}),
                enabled=trigger_data.get('enabled', True),
                priority=trigger_data.get('priority', 1),
                cooldown_minutes=trigger_data.get('cooldown_minutes', 0),
                metadata=trigger_data.get('metadata', {})
            )
            
            # Store in database
            await self._store_workflow_trigger(trigger)
            
            # Cache in memory
            self.triggers[trigger_id] = trigger
            
            logger.info(f"Created workflow trigger {trigger_id}: {trigger.name}")
            
            return trigger_id
            
        except Exception as e:
            logger.error(f"Failed to create workflow trigger: {e}")
            raise
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive workflow status."""
        try:
            # Get workflow state from engine
            workflow_state = await self.workflow_engine.get_workflow_status(workflow_id)
            if not workflow_state:
                return None
            
            # Get related tasks
            workflow_tasks = []
            for task_id in workflow_state.current_tasks + workflow_state.completed_tasks:
                task = await self.task_manager._get_task(task_id)
                if task:
                    workflow_tasks.append({
                        'id': task.id,
                        'title': task.title,
                        'status': task.status.value,
                        'progress': task.progress_percentage,
                        'assignee': task.assignment.assignee_id if task.assignment else None,
                        'due_date': task.due_date.isoformat() if task.due_date else None
                    })
            
            return {
                'workflow_id': workflow_id,
                'definition_id': workflow_state.definition_id,
                'status': workflow_state.status.value,
                'progress_percentage': workflow_state.progress_percentage,
                'started_at': workflow_state.started_at.isoformat(),
                'completed_at': workflow_state.completed_at.isoformat() if workflow_state.completed_at else None,
                'current_tasks': len(workflow_state.current_tasks),
                'completed_tasks': len(workflow_state.completed_tasks),
                'failed_tasks': len(workflow_state.failed_tasks),
                'tasks': workflow_tasks,
                'context': {
                    'triggered_by': workflow_state.context.triggered_by,
                    'variables': workflow_state.context.variables
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow status {workflow_id}: {e}")
            return None
    
    async def get_active_workflows(self, definition_id: str = None) -> List[Dict[str, Any]]:
        """Get list of active workflows."""
        try:
            active_workflows = []
            
            for workflow_id, def_id in self.active_workflows.items():
                if definition_id and def_id != definition_id:
                    continue
                
                status = await self.get_workflow_status(workflow_id)
                if status:
                    active_workflows.append(status)
            
            return active_workflows
            
        except Exception as e:
            logger.error(f"Failed to get active workflows: {e}")
            return []
    
    async def cancel_workflow(self, workflow_id: str, reason: str, cancelled_by: str) -> bool:
        """Cancel a workflow."""
        try:
            success = await self.workflow_engine.cancel_workflow(workflow_id, reason)
            
            if success:
                # Remove from active workflows
                if workflow_id in self.active_workflows:
                    del self.active_workflows[workflow_id]
                
                # Cancel related tasks
                workflow_state = await self.workflow_engine.get_workflow_status(workflow_id)
                if workflow_state:
                    for task_id in workflow_state.current_tasks:
                        task = await self.task_manager._get_task(task_id)
                        if task:
                            # Update task status to cancelled
                            task.status = self.task_manager.TaskStatus.CANCELLED
                            task.updated_at = datetime.utcnow()
                            await self.task_manager._persist_task(task)
                
                logger.info(f"Cancelled workflow {workflow_id}: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False
    
    # ========================================================================
    # TRIGGER HANDLERS
    # ========================================================================
    
    async def _handle_regulatory_change_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle regulatory change trigger."""
        # Check if regulation matches trigger conditions
        regulation_data = trigger_data.get('regulation_data', {})
        conditions = trigger.conditions
        
        # Check document type filter
        if 'document_types' in conditions:
            doc_type = regulation_data.get('document_type', '')
            if doc_type not in conditions['document_types']:
                return False
        
        # Check jurisdiction filter
        if 'jurisdictions' in conditions:
            jurisdiction = regulation_data.get('jurisdiction', '')
            if jurisdiction not in conditions['jurisdictions']:
                return False
        
        # Check impact level filter
        if 'min_impact_level' in conditions:
            impact_assessment = trigger_data.get('impact_assessment', {})
            impact_level = impact_assessment.get('impact_level', 'low')
            min_level = conditions['min_impact_level']
            
            impact_levels = {'none': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            if impact_levels.get(impact_level, 0) < impact_levels.get(min_level, 0):
                return False
        
        return True
    
    async def _handle_scheduled_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle scheduled trigger."""
        # This would implement cron-like scheduling logic
        return True
    
    async def _handle_manual_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle manual trigger."""
        return True
    
    async def _handle_threshold_breach_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle threshold breach trigger."""
        # Check if any monitored metric has breached threshold
        conditions = trigger.conditions
        metric_value = trigger_data.get('metric_value', 0)
        threshold = conditions.get('threshold', 0)
        operator = conditions.get('operator', 'greater_than')
        
        if operator == 'greater_than':
            return metric_value > threshold
        elif operator == 'less_than':
            return metric_value < threshold
        elif operator == 'equals':
            return metric_value == threshold
        
        return False
    
    async def _handle_deadline_approaching_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle deadline approaching trigger."""
        deadline = trigger_data.get('deadline')
        if not deadline:
            return False
        
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)
        
        warning_days = trigger.conditions.get('warning_days', 30)
        warning_time = deadline - timedelta(days=warning_days)
        
        return datetime.utcnow() >= warning_time
    
    async def _handle_task_completion_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle task completion trigger."""
        # Check if specific task or task type was completed
        conditions = trigger.conditions
        task_data = trigger_data.get('task_data', {})
        
        if 'task_types' in conditions:
            task_type = task_data.get('task_type', '')
            if task_type not in conditions['task_types']:
                return False
        
        if 'task_ids' in conditions:
            task_id = task_data.get('task_id', '')
            if task_id not in conditions['task_ids']:
                return False
        
        return True
    
    async def _handle_approval_required_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle approval required trigger."""
        approval_type = trigger_data.get('approval_type', '')
        required_types = trigger.conditions.get('approval_types', [])
        
        return approval_type in required_types
    
    async def _handle_compliance_violation_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle compliance violation trigger."""
        violation_severity = trigger_data.get('severity', 'low')
        min_severity = trigger.conditions.get('min_severity', 'medium')
        
        severity_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        return severity_levels.get(violation_severity, 0) >= severity_levels.get(min_severity, 0)
    
    async def _handle_system_event_trigger(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Handle system event trigger."""
        event_type = trigger_data.get('event_type', '')
        monitored_events = trigger.conditions.get('event_types', [])
        
        return event_type in monitored_events
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _find_matching_triggers(self, trigger_type: TriggerType, trigger_data: Dict[str, Any]) -> List[WorkflowTrigger]:
        """Find triggers that match the given type and data."""
        matching_triggers = []
        
        for trigger in self.triggers.values():
            if trigger.enabled and trigger.trigger_type == trigger_type:
                matching_triggers.append(trigger)
        
        return matching_triggers
    
    def _check_trigger_cooldown(self, trigger: WorkflowTrigger) -> bool:
        """Check if trigger is in cooldown period."""
        if trigger.cooldown_minutes <= 0 or not trigger.last_triggered:
            return True
        
        cooldown_end = trigger.last_triggered + timedelta(minutes=trigger.cooldown_minutes)
        return datetime.utcnow() >= cooldown_end
    
    async def _evaluate_trigger_conditions(self, trigger: WorkflowTrigger, trigger_data: Dict[str, Any]) -> bool:
        """Evaluate trigger conditions."""
        try:
            handler = self.trigger_handlers.get(trigger.trigger_type)
            if handler:
                return await handler(trigger, trigger_data)
            return True
        except Exception as e:
            logger.error(f"Error evaluating trigger conditions for {trigger.id}: {e}")
            return False
    
    async def _create_immediate_compliance_tasks(self, regulation_id: str, impact_assessment: Dict[str, Any]) -> List[str]:
        """Create immediate compliance tasks for high-impact regulations."""
        try:
            tasks_created = []
            
            # Create regulatory review task
            review_task_data = {
                'title': f'Regulatory Review: {regulation_id}',
                'description': 'Conduct detailed review of new regulatory requirements',
                'task_type': 'regulatory_review',
                'priority': 'high' if impact_assessment.get('impact_level') == 'high' else 'critical',
                'regulatory_reference': regulation_id,
                'due_date': datetime.utcnow() + timedelta(days=7),
                'requirements': [
                    'Review regulatory document',
                    'Identify compliance gaps',
                    'Document impact on current processes',
                    'Recommend implementation approach'
                ],
                'required_evidence': ['review_document', 'gap_analysis']
            }
            
            review_task_id = await self.task_manager.create_task(review_task_data, 'system')
            tasks_created.append(review_task_id)
            
            # Create impact assessment validation task
            validation_task_data = {
                'title': f'Impact Assessment Validation: {regulation_id}',
                'description': 'Validate and refine automated impact assessment',
                'task_type': 'risk_assessment',
                'priority': 'high',
                'regulatory_reference': regulation_id,
                'due_date': datetime.utcnow() + timedelta(days=14),
                'parent_task_id': review_task_id
            }
            
            validation_task_id = await self.task_manager.create_task(validation_task_data, 'system')
            tasks_created.append(validation_task_id)
            
            return tasks_created
            
        except Exception as e:
            logger.error(f"Failed to create immediate compliance tasks: {e}")
            return []
    
    async def _send_regulatory_change_notifications(self, regulation_id: str, result: Dict[str, Any]) -> List[str]:
        """Send notifications about regulatory change."""
        # Implementation would send notifications via configured channels
        return ['email_sent', 'slack_notification_sent']
    
    async def _schedule_follow_up_workflows(self, regulation_id: str, impact_assessment: Dict[str, Any]):
        """Schedule follow-up workflows based on deadlines."""
        # Implementation would schedule future workflow triggers
        pass
    
    async def _update_trigger(self, trigger: WorkflowTrigger):
        """Update trigger in database."""
        try:
            async with get_database() as db:
                query = """
                    UPDATE workflow_triggers 
                    SET last_triggered = $1, updated_at = $2
                    WHERE id = $3
                """
                await db.execute(query, trigger.last_triggered, datetime.utcnow(), trigger.id)
        except Exception as e:
            logger.error(f"Failed to update trigger {trigger.id}: {e}")
    
    async def _store_workflow_definition(self, definition: WorkflowDefinition):
        """Store workflow definition in database."""
        try:
            async with get_database() as db:
                query = """
                    INSERT INTO workflow_definitions (
                        id, name, description, version, category, tasks_definition,
                        triggers, flow_logic, default_variables, settings,
                        is_active, created_by, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """
                
                await db.execute(
                    query,
                    definition.id,
                    definition.name,
                    definition.description,
                    definition.version,
                    definition.category,
                    json.dumps([task.__dict__ if hasattr(task, '__dict__') else task for task in definition.tasks]),
                    json.dumps(definition.triggers),
                    json.dumps(definition.flow_logic),
                    json.dumps(definition.variables),
                    json.dumps(definition.settings),
                    definition.is_active,
                    definition.created_by,
                    definition.created_at,
                    definition.updated_at
                )
                
        except Exception as e:
            logger.error(f"Failed to store workflow definition: {e}")
            raise
    
    async def _store_workflow_trigger(self, trigger: WorkflowTrigger):
        """Store workflow trigger in database."""
        try:
            async with get_database() as db:
                query = """
                    INSERT INTO workflow_triggers (
                        id, name, trigger_type, workflow_definition_id, conditions,
                        enabled, priority, cooldown_minutes, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """
                
                await db.execute(
                    query,
                    trigger.id,
                    trigger.name,
                    trigger.trigger_type.value,
                    trigger.workflow_definition_id,
                    json.dumps(trigger.conditions),
                    trigger.enabled,
                    trigger.priority,
                    trigger.cooldown_minutes,
                    json.dumps(trigger.metadata) if trigger.metadata else None,
                    datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Failed to store workflow trigger: {e}")
            raise
    
    # ========================================================================
    # PUBLIC API METHODS
    # ========================================================================
    
    async def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get workflow performance metrics."""
        try:
            async with get_database() as db:
                # Get workflow statistics
                stats_query = """
                    SELECT 
                        COUNT(*) as total_workflows,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_workflows,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_workflows,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_workflows,
                        AVG(CASE WHEN completed_at IS NOT NULL THEN 
                            EXTRACT(EPOCH FROM (completed_at - started_at))/3600 
                        END) as avg_completion_hours
                    FROM workflow_executions
                    WHERE started_at > NOW() - INTERVAL '30 days'
                """
                
                stats = await db.fetchrow(stats_query)
                
                return {
                    'total_workflows': stats['total_workflows'],
                    'active_workflows': stats['active_workflows'],
                    'completed_workflows': stats['completed_workflows'],
                    'failed_workflows': stats['failed_workflows'],
                    'success_rate': (stats['completed_workflows'] / stats['total_workflows'] * 100) if stats['total_workflows'] > 0 else 0,
                    'average_completion_hours': float(stats['avg_completion_hours']) if stats['avg_completion_hours'] else 0,
                    'active_triggers': len([t for t in self.triggers.values() if t.enabled])
                }
                
        except Exception as e:
            logger.error(f"Failed to get workflow metrics: {e}")
            return {}
    
    def register_trigger_handler(self, trigger_type: TriggerType, handler: Callable):
        """Register custom trigger handler."""
        self.trigger_handlers[trigger_type] = handler
        logger.info(f"Registered custom trigger handler for {trigger_type.value}")
    
    async def test_trigger(self, trigger_id: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test a trigger with sample data."""
        try:
            trigger = self.triggers.get(trigger_id)
            if not trigger:
                return {'success': False, 'error': 'Trigger not found'}
            
            # Evaluate conditions
            conditions_met = await self._evaluate_trigger_conditions(trigger, test_data)
            
            return {
                'success': True,
                'trigger_id': trigger_id,
                'conditions_met': conditions_met,
                'cooldown_ok': self._check_trigger_cooldown(trigger),
                'would_trigger': conditions_met and self._check_trigger_cooldown(trigger)
            }
            
        except Exception as e:
            logger.error(f"Failed to test trigger {trigger_id}: {e}")
            return {'success': False, 'error': str(e)} 