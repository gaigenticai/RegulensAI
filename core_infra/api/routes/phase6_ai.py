"""
Phase 6 Advanced AI & Automation API Routes

This module provides REST API endpoints for:
- Natural Language Processing services
- Computer Vision processing
- Advanced ML experiments and AutoML
- Intelligent Automation workflows
- Integration with enterprise AI/ML platforms
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from core_infra.services.nlp import NLPService, NLPRequest, ProcessingType as NLPProcessingType, ModelProvider
from core_infra.services.computer_vision import ComputerVisionService, CVRequest, ProcessingType as CVProcessingType, CVProvider
from core_infra.services.intelligent_automation import IntelligentAutomationService, AutomationRequest

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/phase6", tags=["Phase 6 Advanced AI"])
security = HTTPBearer()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class NLPProcessRequest(BaseModel):
    """Request model for NLP processing"""
    text: str = Field(..., description="Text to process", max_length=100000)
    processing_type: str = Field(..., description="Type of NLP processing")
    model_provider: str = Field(..., description="NLP model provider")
    tenant_id: UUID = Field(..., description="Tenant ID")
    language: str = Field(default="en", description="Language code")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class CVProcessRequest(BaseModel):
    """Request model for Computer Vision processing"""
    processing_type: str = Field(..., description="Type of CV processing")
    provider: str = Field(..., description="CV provider")
    tenant_id: UUID = Field(..., description="Tenant ID")
    document_id: Optional[UUID] = Field(default=None, description="Related document ID")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class AutomationExecuteRequest(BaseModel):
    """Request model for automation workflow execution"""
    workflow_id: UUID = Field(..., description="Workflow ID to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for workflow")
    tenant_id: UUID = Field(..., description="Tenant ID")
    execution_trigger: str = Field(default="manual", description="Trigger type")
    triggered_by: Optional[UUID] = Field(default=None, description="User who triggered")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class WorkflowCreateRequest(BaseModel):
    """Request model for creating automation workflows"""
    workflow_name: str = Field(..., description="Workflow name")
    workflow_type: str = Field(..., description="Type of workflow")
    automation_level: str = Field(..., description="Level of automation")
    tenant_id: UUID = Field(..., description="Tenant ID")
    trigger_conditions: Dict[str, Any] = Field(..., description="Trigger conditions")
    process_steps: List[Dict[str, Any]] = Field(..., description="Process steps")
    decision_logic: Optional[Dict[str, Any]] = Field(default=None)
    integration_configs: Optional[Dict[str, Any]] = Field(default=None)
    quality_controls: Optional[List[Dict[str, Any]]] = Field(default=None)
    error_handling: Optional[Dict[str, Any]] = Field(default=None)

# Response models
class StandardResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

# ============================================================================
# NATURAL LANGUAGE PROCESSING ENDPOINTS
# ============================================================================

@router.post("/nlp/process", response_model=StandardResponse)
async def process_text_nlp(
    request: NLPProcessRequest,
    token: str = Depends(security)
):
    """
    Process text using Natural Language Processing models.
    
    Supports multiple processing types:
    - policy_analysis: Analyze compliance policies
    - contract_extraction: Extract contract information
    - qa_response: Generate Q&A responses
    - entity_recognition: Extract named entities
    - classification: Classify documents
    - summarization: Generate summaries
    - sentiment_analysis: Analyze sentiment
    """
    try:
        nlp_service = NLPService()
        
        # Convert string enums to proper enum types
        try:
            processing_type = NLPProcessingType(request.processing_type)
            model_provider = ModelProvider(request.model_provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
            
        # Create NLP request
        nlp_request = NLPRequest(
            text=request.text,
            processing_type=processing_type,
            model_provider=model_provider,
            tenant_id=request.tenant_id,
            metadata=request.metadata,
            language=request.language,
            confidence_threshold=request.confidence_threshold
        )
        
        # Process text
        result = await nlp_service.process_text(nlp_request)
        
        return StandardResponse(
            success=True,
            message="Text processed successfully",
            data={
                "processed_output": result.processed_output,
                "extracted_entities": result.extracted_entities,
                "key_phrases": result.key_phrases,
                "sentiment_score": result.sentiment_score,
                "confidence_score": result.confidence_score,
                "processing_time_ms": result.processing_time_ms,
                "token_count": result.token_count,
                "cost_estimate": result.cost_estimate
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"NLP processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during NLP processing")

@router.get("/nlp/models/{tenant_id}", response_model=StandardResponse)
async def get_nlp_models(
    tenant_id: UUID,
    model_type: Optional[str] = None,
    token: str = Depends(security)
):
    """Get NLP model performance metrics for a tenant"""
    try:
        nlp_service = NLPService()
        models = await nlp_service.get_model_performance(tenant_id, model_type)
        
        return StandardResponse(
            success=True,
            message="NLP models retrieved successfully",
            data=models
        )
        
    except Exception as e:
        logger.error(f"Error retrieving NLP models: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving NLP models")

@router.get("/nlp/history/{tenant_id}", response_model=StandardResponse)
async def get_nlp_history(
    tenant_id: UUID,
    limit: int = 100,
    token: str = Depends(security)
):
    """Get NLP processing history for a tenant"""
    try:
        nlp_service = NLPService()
        history = await nlp_service.get_processing_history(tenant_id, limit)
        
        return StandardResponse(
            success=True,
            message="NLP processing history retrieved successfully",
            data=history
        )
        
    except Exception as e:
        logger.error(f"Error retrieving NLP history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving NLP history")

# ============================================================================
# COMPUTER VISION ENDPOINTS
# ============================================================================

@router.post("/cv/process", response_model=StandardResponse)
async def process_document_cv(
    file: UploadFile = File(...),
    processing_type: str = Form(...),
    provider: str = Form(...),
    tenant_id: str = Form(...),
    document_id: Optional[str] = Form(None),
    confidence_threshold: float = Form(0.7),
    token: str = Depends(security)
):
    """
    Process document using Computer Vision models.
    
    Supports multiple processing types:
    - classification: Classify document types
    - kyc_verification: Verify KYC documents
    - signature_detection: Detect signatures
    - ocr_extraction: Extract text via OCR
    - form_parsing: Parse form fields
    - table_extraction: Extract table data
    """
    try:
        cv_service = ComputerVisionService()
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
            
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            
        try:
            # Convert string enums to proper enum types
            try:
                cv_processing_type = CVProcessingType(processing_type)
                cv_provider = CVProvider(provider)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
                
            # Create CV request
            cv_request = CVRequest(
                file_path=temp_file_path,
                processing_type=cv_processing_type,
                provider=cv_provider,
                tenant_id=UUID(tenant_id),
                document_id=UUID(document_id) if document_id else None,
                confidence_threshold=confidence_threshold
            )
            
            # Process document
            result = await cv_service.process_document(cv_request)
            
            return StandardResponse(
                success=True,
                message="Document processed successfully",
                data={
                    "document_classification": result.document_classification,
                    "extracted_text": result.extracted_text,
                    "extracted_fields": result.extracted_fields,
                    "detected_signatures": result.detected_signatures,
                    "verification_results": result.verification_results,
                    "confidence_scores": result.confidence_scores,
                    "quality_score": result.quality_score,
                    "processing_time_ms": result.processing_time_ms,
                    "processing_cost": result.processing_cost
                }
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"CV processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during CV processing")

@router.get("/cv/models/{tenant_id}", response_model=StandardResponse)
async def get_cv_models(
    tenant_id: UUID,
    model_type: Optional[str] = None,
    token: str = Depends(security)
):
    """Get Computer Vision model performance metrics for a tenant"""
    try:
        cv_service = ComputerVisionService()
        models = await cv_service.get_model_performance(tenant_id, model_type)
        
        return StandardResponse(
            success=True,
            message="CV models retrieved successfully",
            data=models
        )
        
    except Exception as e:
        logger.error(f"Error retrieving CV models: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving CV models")

@router.get("/cv/history/{tenant_id}", response_model=StandardResponse)
async def get_cv_history(
    tenant_id: UUID,
    limit: int = 100,
    token: str = Depends(security)
):
    """Get Computer Vision processing history for a tenant"""
    try:
        cv_service = ComputerVisionService()
        history = await cv_service.get_processing_history(tenant_id, limit)
        
        return StandardResponse(
            success=True,
            message="CV processing history retrieved successfully",
            data=history
        )
        
    except Exception as e:
        logger.error(f"Error retrieving CV history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving CV history")

# ============================================================================
# INTELLIGENT AUTOMATION ENDPOINTS
# ============================================================================

@router.post("/automation/workflows", response_model=StandardResponse)
async def create_automation_workflow(
    request: WorkflowCreateRequest,
    token: str = Depends(security)
):
    """Create a new automation workflow"""
    try:
        from supabase import create_client
        from core_infra.config import get_settings
        
        settings = get_settings()
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        
        workflow_data = {
            'tenant_id': str(request.tenant_id),
            'workflow_name': request.workflow_name,
            'workflow_type': request.workflow_type,
            'automation_level': request.automation_level,
            'trigger_conditions': request.trigger_conditions,
            'process_steps': request.process_steps,
            'decision_logic': request.decision_logic or {},
            'integration_configs': request.integration_configs or {},
            'quality_controls': request.quality_controls or [],
            'error_handling': request.error_handling or {},
            'workflow_status': 'draft',
            'created_by': str(request.tenant_id)  # Using tenant as fallback
        }
        
        result = supabase.table('automation_workflows').insert(workflow_data).execute()
        
        return StandardResponse(
            success=True,
            message="Automation workflow created successfully",
            data=result.data[0] if result.data else None
        )
        
    except Exception as e:
        logger.error(f"Error creating automation workflow: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating automation workflow")

@router.post("/automation/execute", response_model=StandardResponse)
async def execute_automation_workflow(
    request: AutomationExecuteRequest,
    token: str = Depends(security)
):
    """Execute an automation workflow"""
    try:
        automation_service = IntelligentAutomationService()
        
        # Create automation request
        automation_request = AutomationRequest(
            workflow_id=request.workflow_id,
            input_data=request.input_data,
            tenant_id=request.tenant_id,
            triggered_by=request.triggered_by,
            execution_trigger=request.execution_trigger,
            metadata=request.metadata
        )
        
        # Execute workflow
        result = await automation_service.execute_workflow(automation_request)
        
        return StandardResponse(
            success=True,
            message="Automation workflow executed successfully",
            data={
                "execution_id": str(result.execution_id),
                "status": result.status.value,
                "output_data": result.output_data,
                "steps_completed": result.steps_completed,
                "quality_score": result.quality_score,
                "human_interventions": result.human_interventions,
                "performance_metrics": result.performance_metrics,
                "cost_incurred": result.cost_incurred,
                "time_saved_minutes": result.time_saved_minutes,
                "compliance_validated": result.compliance_validated
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Automation execution error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during automation execution")

@router.get("/automation/workflows/{tenant_id}", response_model=StandardResponse)
async def get_automation_workflows(
    tenant_id: UUID,
    workflow_type: Optional[str] = None,
    status: Optional[str] = None,
    token: str = Depends(security)
):
    """Get automation workflows for a tenant"""
    try:
        from supabase import create_client
        from core_infra.config import get_settings
        
        settings = get_settings()
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        
        query = supabase.table('automation_workflows').select('*').eq('tenant_id', str(tenant_id))
        
        if workflow_type:
            query = query.eq('workflow_type', workflow_type)
        if status:
            query = query.eq('workflow_status', status)
            
        result = query.execute()
        
        return StandardResponse(
            success=True,
            message="Automation workflows retrieved successfully",
            data=result.data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving automation workflows: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving automation workflows")

@router.get("/automation/performance/{tenant_id}", response_model=StandardResponse)
async def get_automation_performance(
    tenant_id: UUID,
    token: str = Depends(security)
):
    """Get automation performance metrics for a tenant"""
    try:
        automation_service = IntelligentAutomationService()
        performance = await automation_service.get_workflow_performance(tenant_id)
        
        return StandardResponse(
            success=True,
            message="Automation performance metrics retrieved successfully",
            data=performance
        )
        
    except Exception as e:
        logger.error(f"Error retrieving automation performance: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving automation performance")

@router.get("/automation/executions/{tenant_id}", response_model=StandardResponse)
async def get_automation_executions(
    tenant_id: UUID,
    limit: int = 100,
    token: str = Depends(security)
):
    """Get automation execution history for a tenant"""
    try:
        automation_service = IntelligentAutomationService()
        executions = await automation_service.get_execution_history(tenant_id, limit)
        
        return StandardResponse(
            success=True,
            message="Automation execution history retrieved successfully",
            data=executions
        )
        
    except Exception as e:
        logger.error(f"Error retrieving automation executions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving automation executions")

# ============================================================================
# CHATBOT AND CONVERSATIONAL AI ENDPOINTS
# ============================================================================

@router.post("/chatbot/conversation", response_model=StandardResponse)
async def create_chatbot_conversation(
    tenant_id: UUID,
    user_id: Optional[UUID] = None,
    chatbot_type: str = "regulatory_qa",
    token: str = Depends(security)
):
    """Create a new chatbot conversation session"""
    try:
        from supabase import create_client
        from core_infra.config import get_settings
        import uuid
        
        settings = get_settings()
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        
        session_id = str(uuid.uuid4())
        
        conversation_data = {
            'tenant_id': str(tenant_id),
            'user_id': str(user_id) if user_id else None,
            'session_id': session_id,
            'chatbot_type': chatbot_type,
            'conversation_context': {},
            'message_history': [],
            'resolution_status': 'ongoing',
            'total_messages': 0,
            'started_at': datetime.now().isoformat()
        }
        
        result = supabase.table('chatbot_conversations').insert(conversation_data).execute()
        
        return StandardResponse(
            success=True,
            message="Chatbot conversation created successfully",
            data=result.data[0] if result.data else None
        )
        
    except Exception as e:
        logger.error(f"Error creating chatbot conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating chatbot conversation")

# ============================================================================
# DASHBOARD AND ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/dashboard/overview/{tenant_id}", response_model=StandardResponse)
async def get_phase6_dashboard(
    tenant_id: UUID,
    token: str = Depends(security)
):
    """Get Phase 6 AI services overview dashboard data"""
    try:
        # Initialize services
        nlp_service = NLPService()
        cv_service = ComputerVisionService()
        automation_service = IntelligentAutomationService()
        
        # Get recent activity data
        nlp_history = await nlp_service.get_processing_history(tenant_id, 10)
        cv_history = await cv_service.get_processing_history(tenant_id, 10)
        automation_executions = await automation_service.get_execution_history(tenant_id, 10)
        
        # Get performance metrics
        nlp_models = await nlp_service.get_model_performance(tenant_id)
        cv_models = await cv_service.get_model_performance(tenant_id)
        automation_performance = await automation_service.get_workflow_performance(tenant_id)
        
        dashboard_data = {
            "summary": {
                "nlp_requests_today": len(nlp_history),
                "cv_documents_processed": len(cv_history),
                "automation_executions": len(automation_executions),
                "active_models": len(nlp_models) + len(cv_models),
                "active_workflows": len([w for w in automation_performance if w.get('workflow_status') == 'active'])
            },
            "recent_activity": {
                "nlp_processing": nlp_history,
                "cv_processing": cv_history,
                "automation_executions": automation_executions
            },
            "performance_metrics": {
                "nlp_models": nlp_models,
                "cv_models": cv_models,
                "automation_workflows": automation_performance
            }
        }
        
        return StandardResponse(
            success=True,
            message="Phase 6 dashboard data retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving dashboard data")

# Add router to main app
def include_phase6_routes(app):
    """Include Phase 6 routes in the main FastAPI app"""
    app.include_router(router) 