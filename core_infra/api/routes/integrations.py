"""
Enterprise Integrations API Routes

FastAPI routes for managing enterprise system integrations:
- GRC system integration management
- Core banking system connections
- External data source configuration
- Document management integration
- Integration health monitoring
- Cost and performance analytics
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from core_infra.config import get_settings
from core_infra.services.integrations import (
    GRCIntegrationService,
    CoreBankingIntegrationService,
    ExternalDataIntegrationService,
    DocumentManagementIntegrationService,
    IntegrationManagerService
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Pydantic models for request/response
class IntegrationSystemCreate(BaseModel):
    system_name: str = Field(..., description="Name of the integration system")
    system_type: str = Field(..., description="Type of system (grc, core_banking, external_data, document_management)")
    vendor: str = Field(..., description="Vendor name")
    base_url: str = Field(..., description="Base URL for the system")
    authentication_type: str = Field(..., description="Authentication method")
    authentication_config: Dict[str, Any] = Field(default={}, description="Authentication configuration")
    api_endpoints: Dict[str, Any] = Field(default={}, description="API endpoint configurations")
    sync_frequency: str = Field(default="hourly", description="Synchronization frequency")

class EntityScreeningRequest(BaseModel):
    entity_name: str = Field(..., description="Name of entity to screen")
    entity_id: Optional[str] = Field(None, description="Internal entity ID")
    entity_type: str = Field(default="individual", description="Type of entity")
    screening_type: str = Field(default="comprehensive", description="Type of screening")
    additional_data: Dict[str, Any] = Field(default={}, description="Additional entity data")

class DocumentLifecycleAction(BaseModel):
    action: str = Field(..., description="Lifecycle action (approve, reject, archive, etc.)")
    comments: Optional[str] = Field(None, description="Action comments")
    assigned_to: Optional[str] = Field(None, description="User to assign to")

# Mock dependency for getting supabase client
async def get_supabase_client():
    # In production, this would return actual Supabase client
    return None

# GRC Integration Routes
@router.post("/grc/sync-risks")
async def sync_grc_risks(
    tenant_id: str = Query(..., description="Tenant ID"),
    system_type: Optional[str] = Query(None, description="Specific GRC system type"),
    supabase_client = Depends(get_supabase_client)
):
    """Synchronize risk registers from GRC systems."""
    try:
        async with GRCIntegrationService(supabase_client) as grc_service:
            result = await grc_service.sync_risk_registers(tenant_id, system_type)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "GRC risk sync completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"GRC risk sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GRC risk sync failed: {str(e)}")

@router.post("/grc/push-updates")
async def push_grc_updates(
    tenant_id: str = Query(..., description="Tenant ID"),
    updates: List[Dict[str, Any]] = Body(..., description="Compliance updates to push"),
    supabase_client = Depends(get_supabase_client)
):
    """Push compliance updates to GRC systems."""
    try:
        async with GRCIntegrationService(supabase_client) as grc_service:
            result = await grc_service.push_compliance_updates(tenant_id, updates)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Updates pushed to GRC systems",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"GRC updates push failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GRC updates push failed: {str(e)}")

# Core Banking Integration Routes
@router.post("/banking/sync-transactions")
async def sync_banking_transactions(
    tenant_id: str = Query(..., description="Tenant ID"),
    system_type: Optional[str] = Query(None, description="Specific CBS type"),
    start_date: Optional[datetime] = Query(None, description="Start date for sync"),
    end_date: Optional[datetime] = Query(None, description="End date for sync"),
    supabase_client = Depends(get_supabase_client)
):
    """Synchronize transactions from core banking systems."""
    try:
        async with CoreBankingIntegrationService(supabase_client) as cbs_service:
            result = await cbs_service.sync_transactions(tenant_id, system_type, start_date, end_date)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Banking transactions sync completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Banking transaction sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Banking transaction sync failed: {str(e)}")

@router.post("/banking/start-realtime-monitoring")
async def start_realtime_banking_monitoring(
    tenant_id: str = Query(..., description="Tenant ID"),
    system_type: Optional[str] = Query(None, description="Specific CBS type"),
    supabase_client = Depends(get_supabase_client)
):
    """Start real-time transaction monitoring from CBS."""
    try:
        async with CoreBankingIntegrationService(supabase_client) as cbs_service:
            result = await cbs_service.start_realtime_monitoring(tenant_id, system_type)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Real-time monitoring started",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Real-time monitoring startup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Real-time monitoring startup failed: {str(e)}")

@router.post("/banking/process-realtime-transaction")
async def process_realtime_transaction(
    transaction_data: Dict[str, Any] = Body(..., description="Real-time transaction data"),
    supabase_client = Depends(get_supabase_client)
):
    """Process incoming real-time transaction from CBS webhook."""
    try:
        async with CoreBankingIntegrationService(supabase_client) as cbs_service:
            result = await cbs_service.process_realtime_transaction(transaction_data)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Real-time transaction processed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Real-time transaction processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Real-time transaction processing failed: {str(e)}")

# External Data Integration Routes
@router.post("/external-data/screen-entity")
async def screen_entity(
    tenant_id: str = Query(..., description="Tenant ID"),
    screening_request: EntityScreeningRequest,
    supabase_client = Depends(get_supabase_client)
):
    """Screen entity against sanctions, PEP, and watchlists."""
    try:
        entity_data = {
            'name': screening_request.entity_name,
            'id': screening_request.entity_id,
            'type': screening_request.entity_type,
            **screening_request.additional_data
        }
        
        async with ExternalDataIntegrationService(supabase_client) as external_service:
            result = await external_service.screen_entity(tenant_id, entity_data, screening_request.screening_type)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Entity screening completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Entity screening failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Entity screening failed: {str(e)}")

@router.post("/external-data/update-sources")
async def update_external_data_sources(
    tenant_id: str = Query(..., description="Tenant ID"),
    source_type: Optional[str] = Query(None, description="Specific source type to update"),
    supabase_client = Depends(get_supabase_client)
):
    """Update external data sources (sanctions lists, PEP data, etc.)."""
    try:
        async with ExternalDataIntegrationService(supabase_client) as external_service:
            result = await external_service.update_data_sources(tenant_id, source_type)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "External data sources updated",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"External data source update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"External data source update failed: {str(e)}")

# Document Management Integration Routes
@router.post("/documents/sync")
async def sync_documents(
    tenant_id: str = Query(..., description="Tenant ID"),
    repository_type: Optional[str] = Query(None, description="Specific repository type"),
    supabase_client = Depends(get_supabase_client)
):
    """Synchronize documents from document repositories."""
    try:
        async with DocumentManagementIntegrationService(supabase_client) as doc_service:
            result = await doc_service.sync_documents(tenant_id, repository_type)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Document sync completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Document sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document sync failed: {str(e)}")

@router.post("/documents/{document_id}/lifecycle")
async def manage_document_lifecycle(
    document_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    lifecycle_action: DocumentLifecycleAction,
    supabase_client = Depends(get_supabase_client)
):
    """Manage document lifecycle (review, approve, archive, delete)."""
    try:
        async with DocumentManagementIntegrationService(supabase_client) as doc_service:
            result = await doc_service.manage_document_lifecycle(tenant_id, document_id, lifecycle_action.action)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"Document lifecycle action '{lifecycle_action.action}' completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Document lifecycle management failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document lifecycle management failed: {str(e)}")

@router.post("/documents/{document_id}/extract-metadata")
async def extract_document_metadata(
    document_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    supabase_client = Depends(get_supabase_client)
):
    """Extract and analyze document metadata and content."""
    try:
        async with DocumentManagementIntegrationService(supabase_client) as doc_service:
            result = await doc_service.extract_document_metadata(tenant_id, document_id)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Document metadata extraction completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Document metadata extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document metadata extraction failed: {str(e)}")

# Integration Management Routes
@router.get("/dashboard")
async def get_integration_dashboard(
    tenant_id: str = Query(..., description="Tenant ID"),
    supabase_client = Depends(get_supabase_client)
):
    """Get comprehensive integration dashboard data."""
    try:
        async with IntegrationManagerService(supabase_client) as manager_service:
            result = await manager_service.get_integration_dashboard(tenant_id)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Integration dashboard data retrieved",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Integration dashboard failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration dashboard failed: {str(e)}")

@router.post("/monitor-health")
async def monitor_integration_health(
    tenant_id: str = Query(..., description="Tenant ID"),
    supabase_client = Depends(get_supabase_client)
):
    """Monitor integration health and handle failures."""
    try:
        async with IntegrationManagerService(supabase_client) as manager_service:
            result = await manager_service.monitor_integration_health(tenant_id)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Integration health monitoring completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Integration health monitoring failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration health monitoring failed: {str(e)}")

@router.get("/cost-management")
async def manage_integration_costs(
    tenant_id: str = Query(..., description="Tenant ID"),
    supabase_client = Depends(get_supabase_client)
):
    """Manage and optimize integration costs."""
    try:
        async with IntegrationManagerService(supabase_client) as manager_service:
            result = await manager_service.manage_integration_costs(tenant_id)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Integration cost management completed",
                    "data": result
                }
            )
    except Exception as e:
        logger.error(f"Integration cost management failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration cost management failed: {str(e)}")

# Integration System CRUD Routes
@router.post("/systems")
async def create_integration_system(
    tenant_id: str = Query(..., description="Tenant ID"),
    system_data: IntegrationSystemCreate,
    supabase_client = Depends(get_supabase_client)
):
    """Create new integration system configuration."""
    try:
        # Mock implementation - would create actual system record
        system_id = "mock-system-id"
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Integration system created successfully",
                "data": {
                    "system_id": system_id,
                    "system_name": system_data.system_name,
                    "system_type": system_data.system_type,
                    "vendor": system_data.vendor,
                    "status": "active"
                }
            }
        )
    except Exception as e:
        logger.error(f"Integration system creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration system creation failed: {str(e)}")

@router.get("/systems")
async def list_integration_systems(
    tenant_id: str = Query(..., description="Tenant ID"),
    system_type: Optional[str] = Query(None, description="Filter by system type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    supabase_client = Depends(get_supabase_client)
):
    """List integration systems for tenant."""
    try:
        # Mock implementation - would fetch actual systems
        systems = [
            {
                "id": "system-1",
                "system_name": "Archer GRC",
                "system_type": "grc",
                "vendor": "archer",
                "status": "active",
                "last_sync_at": "2024-01-15T10:00:00Z",
                "health_status": "healthy"
            },
            {
                "id": "system-2",
                "system_name": "Temenos T24",
                "system_type": "core_banking",
                "vendor": "temenos",
                "status": "active",
                "last_sync_at": "2024-01-15T10:30:00Z",
                "health_status": "healthy"
            }
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Integration systems retrieved",
                "data": {
                    "systems": systems,
                    "total_count": len(systems)
                }
            }
        )
    except Exception as e:
        logger.error(f"Integration systems listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration systems listing failed: {str(e)}")

@router.get("/systems/{system_id}")
async def get_integration_system(
    system_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    supabase_client = Depends(get_supabase_client)
):
    """Get specific integration system details."""
    try:
        # Mock implementation - would fetch actual system
        system = {
            "id": system_id,
            "system_name": "Archer GRC",
            "system_type": "grc",
            "vendor": "archer",
            "status": "active",
            "base_url": "https://archer.company.com",
            "authentication_type": "oauth2",
            "sync_frequency": "hourly",
            "last_sync_at": "2024-01-15T10:00:00Z",
            "next_sync_at": "2024-01-15T11:00:00Z",
            "error_count": 0,
            "health_status": "healthy",
            "performance_metrics": {
                "average_response_time_ms": 250,
                "success_rate_percentage": 99.5,
                "total_requests_24h": 1440
            }
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Integration system details retrieved",
                "data": system
            }
        )
    except Exception as e:
        logger.error(f"Integration system retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration system retrieval failed: {str(e)}")

@router.put("/systems/{system_id}")
async def update_integration_system(
    system_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    system_data: IntegrationSystemCreate,
    supabase_client = Depends(get_supabase_client)
):
    """Update integration system configuration."""
    try:
        # Mock implementation - would update actual system
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Integration system updated successfully",
                "data": {
                    "system_id": system_id,
                    "updated_fields": list(system_data.dict().keys())
                }
            }
        )
    except Exception as e:
        logger.error(f"Integration system update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration system update failed: {str(e)}")

@router.delete("/systems/{system_id}")
async def delete_integration_system(
    system_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    supabase_client = Depends(get_supabase_client)
):
    """Delete integration system configuration."""
    try:
        # Mock implementation - would delete actual system
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Integration system deleted successfully",
                "data": {
                    "system_id": system_id,
                    "deleted_at": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Integration system deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Integration system deletion failed: {str(e)}") 