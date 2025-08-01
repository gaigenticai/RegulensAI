"""Workflow Orchestrator for Intelligent Automation

This module provides workflow orchestration capabilities for complex
multi-step automation processes with dependencies and conditional logic.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid

from core_infra.config import settings
from core_infra.exceptions import SystemException, ValidationError
from core_infra.monitoring.observability import monitor_performance

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowOrchestrator:
    """
    Orchestrates complex multi-step workflows with intelligent routing.
    
    Features:
    - Multi-step workflow execution
    - Conditional branching
    - Parallel execution
    - Error handling and recovery
    - State management
    """
    
    def __init__(self):
        """Initialize workflow orchestrator."""
        self.workflow_definitions = self._load_workflow_definitions()
        self.active_executions = {}
        self.step_handlers = {
            'rpa': self._execute_rpa_step,
            'api_call': self._execute_api_step,
            'decision': self._execute_decision_step,
            'parallel': self._execute_parallel_step,
            'script': self._execute_script_step
        }
        logger.info("Workflow orchestrator initialized")
    
    def _load_workflow_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load workflow definitions."""
        return {
            'customer_onboarding': {
                'name': 'Customer Onboarding',
                'description': 'Automated customer onboarding with KYC',
                'steps': [
                    {
                        'id': 'validate_input',
                        'name': 'Validate Input',
                        'type': 'script',
                        'config': {'script': 'validate_customer_data'},
                        'dependencies': []
                    },
                    {
                        'id': 'kyc_verification',
                        'name': 'KYC Verification',
                        'type': 'rpa',
                        'config': {'process_name': 'kyc_document_processing'},
                        'dependencies': ['validate_input']
                    },
                    {
                        'id': 'risk_assessment',
                        'name': 'Risk Assessment',
                        'type': 'api_call',
                        'config': {'endpoint': '/api/v1/risk/assess', 'method': 'POST'},
                        'dependencies': ['kyc_verification']
                    },
                    {
                        'id': 'approval_decision',
                        'name': 'Approval Decision',
                        'type': 'decision',
                        'config': {
                            'conditions': {'risk_score': {'operator': 'less_than', 'value': 70}}
                        },
                        'dependencies': ['risk_assessment']
                    },
                    {
                        'id': 'create_account',
                        'name': 'Create Account',
                        'type': 'api_call',
                        'config': {'endpoint': '/api/v1/customers', 'method': 'POST'},
                        'dependencies': ['approval_decision'],
                        'conditions': {'approval_decision.approved': True}
                    }
                ]
            },
            'compliance_review': {
                'name': 'Compliance Review',
                'description': 'Automated compliance review process',
                'steps': [
                    {
                        'id': 'gather_data',
                        'name': 'Gather Data',
                        'type': 'parallel',
                        'config': {
                            'tasks': ['fetch_transactions', 'fetch_regulations', 'fetch_history']
                        },
                        'dependencies': []
                    },
                    {
                        'id': 'analyze_compliance',
                        'name': 'Analyze Compliance',
                        'type': 'rpa',
                        'config': {'process_name': 'compliance_analysis'},
                        'dependencies': ['gather_data']
                    },
                    {
                        'id': 'generate_report',
                        'name': 'Generate Report',
                        'type': 'rpa',
                        'config': {'process_name': 'regulatory_report_generation'},
                        'dependencies': ['analyze_compliance']
                    }
                ]
            }
        }
    
    @monitor_performance
    async def execute_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        try:
            # Get workflow definition
            workflow_def = self.workflow_definitions.get(workflow_name)
            if not workflow_def:
                raise ValidationError(f"Unknown workflow: {workflow_name}")
            
            # Create execution instance
            execution_id = str(uuid.uuid4())
            execution = {
                'execution_id': execution_id,
                'workflow_name': workflow_name,
                'status': WorkflowStatus.PENDING.value,
                'input_data': input_data,
                'context': context or {},
                'step_results': {},
                'started_at': datetime.utcnow(),
                'current_step': None
            }
            
            self.active_executions[execution_id] = execution
            
            # Execute workflow
            execution['status'] = WorkflowStatus.RUNNING.value
            await self._execute_steps(workflow_def['steps'], execution)
            
            # Complete workflow
            execution['status'] = WorkflowStatus.COMPLETED.value
            execution['completed_at'] = datetime.utcnow()
            
            return {
                'execution_id': execution_id,
                'status': 'completed',
                'results': execution['step_results'],
                'duration': (execution['completed_at'] - execution['started_at']).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            if 'execution' in locals():
                execution['status'] = WorkflowStatus.FAILED.value
                execution['error'] = str(e)
            raise SystemException(f"Workflow execution failed: {str(e)}")
    
    async def _execute_steps(self, steps: List[Dict], execution: Dict):
        """Execute workflow steps in order."""
        executed_steps = set()
        
        while len(executed_steps) < len(steps):
            # Find ready steps
            ready_steps = []
            for step in steps:
                if step['id'] not in executed_steps:
                    if all(dep in executed_steps for dep in step.get('dependencies', [])):
                        if self._check_conditions(step, execution):
                            ready_steps.append(step)
            
            if not ready_steps:
                break
            
            # Execute ready steps
            for step in ready_steps:
                execution['current_step'] = step['id']
                await self._execute_step(step, execution)
                executed_steps.add(step['id'])
    
    def _check_conditions(self, step: Dict, execution: Dict) -> bool:
        """Check if step conditions are met."""
        conditions = step.get('conditions', {})
        if not conditions:
            return True
        
        for key, expected in conditions.items():
            actual = self._get_value(key, execution)
            if actual != expected:
                return False
        
        return True
    
    def _get_value(self, path: str, execution: Dict) -> Any:
        """Get value from execution context using dot notation."""
        parts = path.split('.')
        value = execution
        
        for part in parts:
            if part == 'input_data':
                value = execution.get('input_data', {})
            elif part == 'context':
                value = execution.get('context', {})
            elif part in execution.get('step_results', {}):
                value = execution['step_results'][part]
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    async def _execute_step(self, step: Dict, execution: Dict):
        """Execute a single workflow step."""
        logger.info(f"Executing step: {step['name']}")
        
        try:
            handler = self.step_handlers.get(step['type'])
            if not handler:
                raise SystemException(f"Unknown step type: {step['type']}")
            
            result = await handler(step, execution)
            
            execution['step_results'][step['id']] = {
                'status': 'completed',
                'result': result,
                'completed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Step execution failed: {step['name']} - {e}")
            execution['step_results'][step['id']] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
            raise
    
    async def _execute_rpa_step(self, step: Dict, execution: Dict) -> Any:
        """Execute RPA process step."""
        from core_infra.services.intelligent_automation.rpa_integrator import rpa_integrator
        
        process_name = step['config']['process_name']
        input_data = self._prepare_input(step, execution)
        
        result = await rpa_integrator.execute_process(process_name, input_data)
        return result.get('result')
    
    async def _execute_api_step(self, step: Dict, execution: Dict) -> Any:
        """Execute API call step."""
        import aiohttp
        
        config = step['config']
        endpoint = config['endpoint']
        method = config.get('method', 'GET')
        
        # Prepare data
        data = self._prepare_input(step, execution)
        
        # Make API call
        async with aiohttp.ClientSession() as session:
            url = f"{getattr(settings, 'api_base_url', 'http://localhost:8000')}{endpoint}"
            
            if method == 'GET':
                async with session.get(url, params=data) as response:
                    return await response.json()
            elif method == 'POST':
                async with session.post(url, json=data) as response:
                    return await response.json()
            else:
                async with session.request(method, url, json=data) as response:
                    return await response.json()
    
    async def _execute_decision_step(self, step: Dict, execution: Dict) -> Any:
        """Execute decision step."""
        conditions = step['config'].get('conditions', {})
        
        for field, condition in conditions.items():
            value = self._get_value(field, execution)
            operator = condition['operator']
            expected = condition['value']
            
            if operator == 'equals' and value != expected:
                return {'approved': False, 'reason': f'{field} not equal to {expected}'}
            elif operator == 'less_than' and value >= expected:
                return {'approved': False, 'reason': f'{field} not less than {expected}'}
            elif operator == 'greater_than' and value <= expected:
                return {'approved': False, 'reason': f'{field} not greater than {expected}'}
        
        return {'approved': True}
    
    async def _execute_parallel_step(self, step: Dict, execution: Dict) -> Any:
        """Execute parallel tasks."""
        tasks = []
        
        for task_name in step['config'].get('tasks', []):
            # Create API call tasks
            task = asyncio.create_task(
                self._execute_api_step(
                    {'config': {'endpoint': f'/api/v1/{task_name}', 'method': 'GET'}},
                    execution
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'parallel_results': {
                task_name: result 
                for task_name, result in zip(step['config']['tasks'], results)
            }
        }
    
    async def _execute_script_step(self, step: Dict, execution: Dict) -> Any:
        """Execute custom script step."""
        script_name = step['config']['script']
        
        # Execute predefined scripts
        if script_name == 'validate_customer_data':
            customer_data = execution['input_data'].get('customer_data', {})
            required_fields = ['name', 'email', 'phone']
            
            for field in required_fields:
                if field not in customer_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            return {'valid': True, 'validated_fields': required_fields}
        
        return {'executed': script_name}
    
    def _prepare_input(self, step: Dict, execution: Dict) -> Dict[str, Any]:
        """Prepare input data for step execution."""
        input_mapping = step.get('config', {}).get('input_mapping', {})
        
        if not input_mapping:
            return execution['input_data']
        
        prepared_input = {}
        for target, source in input_mapping.items():
            value = self._get_value(source, execution)
            if value is not None:
                prepared_input[target] = value
        
        return prepared_input
    
    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause a running workflow."""
        execution = self.active_executions.get(execution_id)
        if execution and execution['status'] == WorkflowStatus.RUNNING.value:
            execution['status'] = WorkflowStatus.PAUSED.value
            return True
        return False
    
    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume a paused workflow."""
        execution = self.active_executions.get(execution_id)
        if execution and execution['status'] == WorkflowStatus.PAUSED.value:
            execution['status'] = WorkflowStatus.RUNNING.value
            # Would continue execution from current step
            return True
        return False
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a workflow execution."""
        execution = self.active_executions.get(execution_id)
        if execution and execution['status'] in [WorkflowStatus.RUNNING.value, WorkflowStatus.PAUSED.value]:
            execution['status'] = WorkflowStatus.CANCELLED.value
            execution['cancelled_at'] = datetime.utcnow()
            return True
        return False
    
    def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return None
        
        return {
            'execution_id': execution_id,
            'workflow_name': execution.get('workflow_name'),
            'status': execution.get('status'),
            'current_step': execution.get('current_step'),
            'started_at': execution.get('started_at').isoformat() if execution.get('started_at') else None,
            'step_results': execution.get('step_results', {})
        }
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List available workflows."""
        return [
            {
                'name': name,
                'description': definition.get('description', ''),
                'steps_count': len(definition.get('steps', []))
            }
            for name, definition in self.workflow_definitions.items()
        ]


# Global workflow orchestrator instance
workflow_orchestrator = WorkflowOrchestrator()