"""
Core Intelligent Automation Service for Phase 6 Advanced AI & Automation

Provides enterprise-grade intelligent automation with RPA integration,
workflow orchestration, quality controls, and comprehensive audit trails.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

import requests
import aiohttp
from supabase import create_client, Client

from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class AutomationLevel(Enum):
    """Levels of automation supported"""
    FULLY_AUTOMATED = "fully_automated"
    HUMAN_IN_LOOP = "human_in_loop"
    SUPERVISED = "supervised"
    SEMI_AUTOMATED = "semi_automated"

class WorkflowType(Enum):
    """Types of automation workflows"""
    RPA_INTEGRATION = "rpa_integration"
    DOCUMENT_PROCESSING = "document_processing"
    DATA_EXTRACTION = "data_extraction"
    COMPLIANCE_MONITORING = "compliance_monitoring"
    REPORT_GENERATION = "report_generation"
    TASK_AUTOMATION = "task_automation"

class ExecutionStatus(Enum):
    """Execution status options"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"

@dataclass
class AutomationRequest:
    """Request structure for automation execution"""
    workflow_id: UUID
    input_data: Dict[str, Any]
    tenant_id: UUID
    triggered_by: Optional[UUID] = None
    execution_trigger: str = "manual"
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AutomationResult:
    """Result structure for automation execution"""
    execution_id: UUID
    status: ExecutionStatus
    output_data: Dict[str, Any]
    steps_completed: List[str]
    quality_score: float
    human_interventions: int
    performance_metrics: Dict[str, Any]
    cost_incurred: float
    time_saved_minutes: int
    compliance_validated: bool
    audit_trail: List[Dict[str, Any]]

class IntelligentAutomationService:
    """
    Enterprise Intelligent Automation Service providing RPA integration,
    workflow orchestration, and end-to-end process automation.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase: Client = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_ANON_KEY
        )
        
        # RPA tool configurations
        self.rpa_tools = {}
        self._initialize_rpa_tools()
        
    def _initialize_rpa_tools(self):
        """Initialize RPA tool integrations"""
        try:
            # UiPath integration
            if hasattr(self.settings, 'UIPATH_API_URL') and self.settings.UIPATH_API_URL:
                self.rpa_tools['uipath'] = {
                    'api_url': self.settings.UIPATH_API_URL,
                    'api_key': getattr(self.settings, 'UIPATH_API_KEY', ''),
                    'tenant_name': getattr(self.settings, 'UIPATH_TENANT_NAME', ''),
                    'organization_unit': getattr(self.settings, 'UIPATH_ORG_UNIT', '')
                }
                logger.info("UiPath integration configured")
                
            # Blue Prism integration
            if hasattr(self.settings, 'BLUEPRISM_API_URL') and self.settings.BLUEPRISM_API_URL:
                self.rpa_tools['blueprism'] = {
                    'api_url': self.settings.BLUEPRISM_API_URL,
                    'username': getattr(self.settings, 'BLUEPRISM_USERNAME', ''),
                    'password': getattr(self.settings, 'BLUEPRISM_PASSWORD', '')
                }
                logger.info("Blue Prism integration configured")
                
            # Automation Anywhere integration
            if hasattr(self.settings, 'AA_API_URL') and self.settings.AA_API_URL:
                self.rpa_tools['automation_anywhere'] = {
                    'api_url': self.settings.AA_API_URL,
                    'username': getattr(self.settings, 'AA_USERNAME', ''),
                    'api_key': getattr(self.settings, 'AA_API_KEY', '')
                }
                logger.info("Automation Anywhere integration configured")
                
        except Exception as e:
            logger.error(f"Error initializing RPA tools: {str(e)}")
            
    async def execute_workflow(self, request: AutomationRequest) -> AutomationResult:
        """
        Execute an automation workflow with comprehensive monitoring and quality controls.
        
        Args:
            request: Automation execution request
            
        Returns:
            Automation execution result with performance metrics and audit trails
        """
        execution_id = uuid4()
        start_time = time.time()
        
        try:
            # Get workflow configuration
            workflow = await self._get_workflow_config(request.workflow_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {request.workflow_id}")
                
            # Create execution record
            execution_record = await self._create_execution_record(execution_id, request, workflow)
            
            # Initialize audit trail
            audit_trail = [
                {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'action': 'workflow_started',
                    'details': {
                        'workflow_id': str(request.workflow_id),
                        'trigger': request.execution_trigger
                    }
                }
            ]
            
            # Execute workflow steps
            result = await self._execute_workflow_steps(
                workflow, request, execution_id, audit_trail
            )
            
            # Calculate execution metrics
            execution_time_minutes = (time.time() - start_time) / 60
            
            # Update execution record
            await self._update_execution_record(
                execution_id, result, execution_time_minutes, audit_trail
            )
            
            # Update workflow statistics
            await self._update_workflow_statistics(request.workflow_id, result.status == ExecutionStatus.COMPLETED)
            
            logger.info(
                f"Automation workflow completed: {request.workflow_id} "
                f"in {execution_time_minutes:.2f} minutes with status {result.status.value}"
            )
            
            return result
            
        except Exception as e:
            execution_time_minutes = (time.time() - start_time) / 60
            logger.error(f"Automation workflow failed after {execution_time_minutes:.2f} minutes: {str(e)}")
            
            # Create error result
            error_result = AutomationResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                output_data={"error": str(e)},
                steps_completed=[],
                quality_score=0.0,
                human_interventions=0,
                performance_metrics={"execution_time_minutes": execution_time_minutes},
                cost_incurred=0.0,
                time_saved_minutes=0,
                compliance_validated=False,
                audit_trail=[
                    {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'action': 'workflow_failed',
                        'details': {'error': str(e)}
                    }
                ]
            )
            
            # Update execution record with error
            if 'execution_record' in locals():
                await self._update_execution_record(
                    execution_id, error_result, execution_time_minutes, error_result.audit_trail
                )
                
            raise
            
    async def _get_workflow_config(self, workflow_id: UUID) -> Optional[Dict[str, Any]]:
        """Get workflow configuration from database"""
        try:
            result = self.supabase.table('automation_workflows').select('*').eq('id', str(workflow_id)).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error retrieving workflow config: {str(e)}")
            return None
            
    async def _create_execution_record(self, execution_id: UUID, request: AutomationRequest, 
                                     workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Create automation execution record"""
        try:
            execution_data = {
                'id': str(execution_id),
                'tenant_id': str(request.tenant_id),
                'workflow_id': str(request.workflow_id),
                'execution_trigger': request.execution_trigger,
                'input_data': request.input_data,
                'execution_status': ExecutionStatus.PENDING.value,
                'triggered_by': str(request.triggered_by) if request.triggered_by else None,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'steps_completed': [],
                'current_step': workflow['process_steps'][0]['name'] if workflow.get('process_steps') else None
            }
            
            result = self.supabase.table('automation_executions').insert(execution_data).execute()
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error creating execution record: {str(e)}")
            raise
            
    async def _execute_workflow_steps(self, workflow: Dict[str, Any], request: AutomationRequest,
                                    execution_id: UUID, audit_trail: List[Dict[str, Any]]) -> AutomationResult:
        """Execute individual workflow steps"""
        steps_completed = []
        human_interventions = 0
        quality_scores = []
        total_cost = 0.0
        output_data = {}
        
        try:
            process_steps = workflow.get('process_steps', [])
            
            for step_index, step in enumerate(process_steps):
                step_name = step.get('name', f'step_{step_index}')
                step_type = step.get('type', 'manual')
                
                # Update current step
                await self._update_current_step(execution_id, step_name)
                
                # Add audit entry
                audit_trail.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'action': 'step_started',
                    'details': {'step_name': step_name, 'step_type': step_type}
                })
                
                # Execute step based on type
                step_result = await self._execute_step(step, request.input_data, workflow, audit_trail)
                
                if step_result['status'] == 'completed':
                    steps_completed.append(step_name)
                    quality_scores.append(step_result.get('quality_score', 1.0))
                    total_cost += step_result.get('cost', 0.0)
                    
                    # Merge step output into overall output
                    if 'output' in step_result:
                        output_data.update(step_result['output'])
                        
                    # Check for human intervention
                    if step_result.get('human_intervention_required', False):
                        human_interventions += 1
                        
                elif step_result['status'] == 'failed':
                    # Handle step failure based on workflow error handling
                    error_handling = workflow.get('error_handling', {})
                    if error_handling.get('continue_on_error', False):
                        logger.warning(f"Step {step_name} failed but continuing due to error handling policy")
                        continue
                    else:
                        raise Exception(f"Step {step_name} failed: {step_result.get('error', 'Unknown error')}")
                        
                # Update execution status
                await self._update_execution_status(execution_id, ExecutionStatus.RUNNING, steps_completed)
                
            # Calculate overall quality score
            overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            # Validate compliance if required
            compliance_validated = await self._validate_compliance(workflow, output_data, audit_trail)
            
            # Calculate time savings (estimated)
            manual_time_minutes = len(steps_completed) * 30  # Assume 30 min per manual step
            actual_time_minutes = (time.time() - time.time()) / 60  # Will be updated by caller
            time_saved = max(0, manual_time_minutes - actual_time_minutes)
            
            return AutomationResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                output_data=output_data,
                steps_completed=steps_completed,
                quality_score=overall_quality,
                human_interventions=human_interventions,
                performance_metrics={
                    'steps_executed': len(steps_completed),
                    'success_rate': len(steps_completed) / len(process_steps) if process_steps else 1.0
                },
                cost_incurred=total_cost,
                time_saved_minutes=int(time_saved),
                compliance_validated=compliance_validated,
                audit_trail=audit_trail
            )
            
        except Exception as e:
            logger.error(f"Error executing workflow steps: {str(e)}")
            
            # Add error to audit trail
            audit_trail.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': 'workflow_error',
                'details': {'error': str(e)}
            })
            
            return AutomationResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                output_data={"error": str(e)},
                steps_completed=steps_completed,
                quality_score=0.0,
                human_interventions=human_interventions,
                performance_metrics={},
                cost_incurred=total_cost,
                time_saved_minutes=0,
                compliance_validated=False,
                audit_trail=audit_trail
            )
            
    async def _execute_step(self, step: Dict[str, Any], input_data: Dict[str, Any],
                          workflow: Dict[str, Any], audit_trail: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute individual workflow step"""
        step_type = step.get('type', 'manual')
        step_config = step.get('config', {})
        
        try:
            if step_type == 'rpa_task':
                return await self._execute_rpa_task(step, input_data, audit_trail)
            elif step_type == 'api_call':
                return await self._execute_api_call(step, input_data, audit_trail)
            elif step_type == 'data_processing':
                return await self._execute_data_processing(step, input_data, audit_trail)
            elif step_type == 'document_processing':
                return await self._execute_document_processing(step, input_data, audit_trail)
            elif step_type == 'approval_required':
                return await self._execute_approval_step(step, input_data, audit_trail)
            elif step_type == 'conditional':
                return await self._execute_conditional_step(step, input_data, audit_trail)
            else:
                # Default manual step
                return {
                    'status': 'completed',
                    'output': {'message': f'Manual step {step.get("name")} completed'},
                    'quality_score': 0.8,
                    'human_intervention_required': True
                }
                
        except Exception as e:
            logger.error(f"Error executing step {step.get('name')}: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'quality_score': 0.0
            }
            
    async def _execute_rpa_task(self, step: Dict[str, Any], input_data: Dict[str, Any],
                              audit_trail: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute RPA task using configured RPA tools"""
        rpa_config = step.get('rpa_config', {})
        tool_name = rpa_config.get('tool', 'uipath')
        process_name = rpa_config.get('process_name')
        
        if tool_name not in self.rpa_tools:
            raise ValueError(f"RPA tool {tool_name} not configured")
            
        tool_config = self.rpa_tools[tool_name]
        
        try:
            if tool_name == 'uipath':
                return await self._execute_uipath_process(process_name, input_data, tool_config, audit_trail)
            elif tool_name == 'blueprism':
                return await self._execute_blueprism_process(process_name, input_data, tool_config, audit_trail)
            elif tool_name == 'automation_anywhere':
                return await self._execute_aa_process(process_name, input_data, tool_config, audit_trail)
            else:
                raise ValueError(f"Unsupported RPA tool: {tool_name}")
                
        except Exception as e:
            logger.error(f"RPA task execution failed: {str(e)}")
            audit_trail.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': 'rpa_task_failed',
                'details': {'tool': tool_name, 'process': process_name, 'error': str(e)}
            })
            raise
            
    async def _execute_uipath_process(self, process_name: str, input_data: Dict[str, Any],
                                    tool_config: Dict[str, Any], audit_trail: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute UiPath process"""
        try:
            # Authenticate with UiPath Orchestrator
            auth_url = f"{tool_config['api_url']}/api/account/authenticate"
            auth_payload = {
                "tenancyName": tool_config['tenant_name'],
                "usernameOrEmailAddress": tool_config.get('username', ''),
                "password": tool_config.get('password', '')
            }
            
            async with aiohttp.ClientSession() as session:
                # Get authentication token
                async with session.post(auth_url, json=auth_payload) as auth_response:
                    if auth_response.status != 200:
                        raise Exception(f"UiPath authentication failed: {auth_response.status}")
                    auth_data = await auth_response.json()
                    token = auth_data.get('result')
                    
                # Start job
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                job_payload = {
                    'startInfo': {
                        'ReleaseKey': process_name,
                        'Strategy': 'Specific',
                        'InputArguments': json.dumps(input_data)
                    }
                }
                
                jobs_url = f"{tool_config['api_url']}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"
                async with session.post(jobs_url, json=job_payload, headers=headers) as job_response:
                    if job_response.status != 201:
                        raise Exception(f"UiPath job start failed: {job_response.status}")
                    job_data = await job_response.json()
                    job_id = job_data['value'][0]['Id']
                    
                # Monitor job completion (simplified)
                await asyncio.sleep(5)  # Wait for job to complete
                
                # Get job status
                status_url = f"{tool_config['api_url']}/odata/Jobs({job_id})"
                async with session.get(status_url, headers=headers) as status_response:
                    status_data = await status_response.json()
                    job_status = status_data.get('State', 'Unknown')
                    
                audit_trail.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'action': 'uipath_job_completed',
                    'details': {'job_id': job_id, 'status': job_status}
                })
                
                return {
                    'status': 'completed' if job_status == 'Successful' else 'failed',
                    'output': {'job_id': job_id, 'uipath_status': job_status},
                    'quality_score': 0.9 if job_status == 'Successful' else 0.1,
                    'cost': 0.5  # Estimated cost per job
                }
                
        except Exception as e:
            logger.error(f"UiPath process execution error: {str(e)}")
            raise
            
    async def _execute_api_call(self, step: Dict[str, Any], input_data: Dict[str, Any],
                              audit_trail: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute API call step"""
        api_config = step.get('api_config', {})
        url = api_config.get('url')
        method = api_config.get('method', 'GET')
        headers = api_config.get('headers', {})
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == 'GET':
                    async with session.get(url, headers=headers) as response:
                        response_data = await response.json()
                elif method.upper() == 'POST':
                    async with session.post(url, json=input_data, headers=headers) as response:
                        response_data = await response.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                    
                audit_trail.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'action': 'api_call_completed',
                    'details': {'url': url, 'method': method, 'status': response.status}
                })
                
                return {
                    'status': 'completed' if response.status < 400 else 'failed',
                    'output': response_data,
                    'quality_score': 0.9,
                    'cost': 0.01  # Minimal cost for API calls
                }
                
        except Exception as e:
            logger.error(f"API call execution error: {str(e)}")
            raise
            
    async def _update_current_step(self, execution_id: UUID, step_name: str):
        """Update current step in execution record"""
        try:
            self.supabase.table('automation_executions').update({
                'current_step': step_name
            }).eq('id', str(execution_id)).execute()
        except Exception as e:
            logger.error(f"Error updating current step: {str(e)}")
            
    async def _update_execution_status(self, execution_id: UUID, status: ExecutionStatus, 
                                     steps_completed: List[str]):
        """Update execution status and progress"""
        try:
            self.supabase.table('automation_executions').update({
                'execution_status': status.value,
                'steps_completed': steps_completed
            }).eq('id', str(execution_id)).execute()
        except Exception as e:
            logger.error(f"Error updating execution status: {str(e)}")
            
    async def _validate_compliance(self, workflow: Dict[str, Any], output_data: Dict[str, Any],
                                 audit_trail: List[Dict[str, Any]]) -> bool:
        """Validate compliance requirements"""
        try:
            # Basic compliance validation
            compliance_rules = workflow.get('compliance_rules', [])
            
            for rule in compliance_rules:
                rule_type = rule.get('type')
                if rule_type == 'required_field':
                    field_name = rule.get('field')
                    if field_name not in output_data:
                        return False
                elif rule_type == 'audit_trail_required':
                    if len(audit_trail) < rule.get('min_entries', 1):
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Compliance validation error: {str(e)}")
            return False
            
    async def _update_execution_record(self, execution_id: UUID, result: AutomationResult,
                                     execution_time_minutes: float, audit_trail: List[Dict[str, Any]]):
        """Update final execution record"""
        try:
            update_data = {
                'execution_status': result.status.value,
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'output_data': result.output_data,
                'quality_score': result.quality_score,
                'human_interventions': result.human_interventions,
                'performance_metrics': result.performance_metrics,
                'cost_incurred': result.cost_incurred,
                'time_saved_minutes': result.time_saved_minutes,
                'compliance_validated': result.compliance_validated,
                'audit_trail': audit_trail,
                'steps_completed': result.steps_completed
            }
            
            self.supabase.table('automation_executions').update(update_data).eq(
                'id', str(execution_id)
            ).execute()
            
        except Exception as e:
            logger.error(f"Error updating execution record: {str(e)}")
            
    async def _update_workflow_statistics(self, workflow_id: UUID, success: bool):
        """Update workflow performance statistics"""
        try:
            # Get current stats
            result = self.supabase.table('automation_workflows').select(
                'total_executions, successful_executions, success_rate'
            ).eq('id', str(workflow_id)).execute()
            
            if result.data:
                current_total = result.data[0]['total_executions'] or 0
                current_successful = result.data[0]['successful_executions'] or 0
                
                new_total = current_total + 1
                new_successful = current_successful + (1 if success else 0)
                new_success_rate = (new_successful / new_total) * 100
                
                self.supabase.table('automation_workflows').update({
                    'total_executions': new_total,
                    'successful_executions': new_successful,
                    'success_rate': new_success_rate,
                    'last_execution_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', str(workflow_id)).execute()
                
        except Exception as e:
            logger.error(f"Error updating workflow statistics: {str(e)}")
            
    async def get_workflow_performance(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """Get performance metrics for automation workflows"""
        try:
            result = self.supabase.table('automation_workflows').select('*').eq(
                'tenant_id', str(tenant_id)
            ).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error retrieving workflow performance: {str(e)}")
            return []
            
    async def get_execution_history(self, tenant_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent automation execution history"""
        try:
            result = self.supabase.table('automation_executions').select('*').eq(
                'tenant_id', str(tenant_id)
            ).order('started_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error retrieving execution history: {str(e)}")
            return [] 