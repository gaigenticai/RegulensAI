"""
Regulens AI - AML/KYC Routes
Enterprise-grade Anti-Money Laundering and Know Your Customer endpoints.
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
from core_infra.exceptions import (
    ResourceNotFoundException,
    AMLViolationException,
    KYCViolationException,
    SanctionsViolationException,
    exception_to_http_exception
)

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["AML/KYC Management"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CustomerScreeningRequest(BaseModel):
    """Customer screening request model."""
    customer_id: str = Field(..., description="Customer ID to screen")
    screening_type: str = Field(..., description="Type of screening (sanctions, pep, adverse_media)")
    force_refresh: bool = Field(default=False, description="Force refresh of screening data")

class TransactionMonitoringRequest(BaseModel):
    """Transaction monitoring request model."""
    transaction_id: Optional[str] = Field(None, description="Specific transaction ID")
    customer_id: Optional[str] = Field(None, description="Customer ID for monitoring")
    start_date: Optional[datetime] = Field(None, description="Start date for monitoring")
    end_date: Optional[datetime] = Field(None, description="End date for monitoring")
    amount_threshold: Optional[float] = Field(None, description="Amount threshold for monitoring")

class SARCreateRequest(BaseModel):
    """SAR creation request model."""
    customer_id: str = Field(..., description="Customer ID")
    transaction_id: Optional[str] = Field(None, description="Related transaction ID")
    report_type: str = Field(..., description="Type of SAR report")
    suspicious_activity_description: str = Field(..., min_length=50, description="Description of suspicious activity")
    amount: Optional[float] = Field(None, description="Amount involved")
    filing_reason: str = Field(..., description="Reason for filing SAR")

class CustomerResponse(BaseModel):
    """Customer response model."""
    id: str
    customer_type: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    date_of_birth: Optional[str]
    country: str
    risk_score: int
    risk_category: str
    kyc_status: str
    pep_status: bool
    sanctions_status: bool
    last_screening_date: Optional[str]
    created_at: str

class TransactionResponse(BaseModel):
    """Transaction response model."""
    id: str
    customer_id: str
    customer_name: str
    transaction_type: str
    amount: float
    currency: str
    source_country: str
    destination_country: str
    monitoring_status: str
    risk_score: int
    suspicious_indicators: List[str]
    requires_sar: bool
    created_at: str

class SARResponse(BaseModel):
    """SAR response model."""
    id: str
    customer_id: str
    customer_name: str
    transaction_id: Optional[str]
    report_type: str
    suspicious_activity_description: str
    amount: Optional[float]
    status: str
    filing_reason: str
    filed_date: Optional[str]
    created_at: str

class ScreeningResultResponse(BaseModel):
    """Screening result response model."""
    id: str
    customer_id: str
    customer_name: str
    screening_type: str
    status: str
    match_found: bool
    match_details: Optional[Dict[str, Any]]
    risk_level: str
    screened_at: str

# ============================================================================
# CUSTOMER SCREENING ENDPOINTS
# ============================================================================

@router.post("/customers/screen", response_model=ScreeningResultResponse)
async def screen_customer(
    request: CustomerScreeningRequest,
    current_user: UserInDB = Depends(require_permission("aml.customers.screen")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Screen customer against sanctions, PEP, and adverse media lists.
    
    Requires permission: aml.customers.screen
    """
    try:
        async with get_database() as db:
            # Verify customer exists
            customer = await db.fetchrow(
                "SELECT * FROM customers WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(request.customer_id),
                uuid.UUID(tenant_id)
            )
            
            if not customer:
                raise ResourceNotFoundException("customer", request.customer_id)
            
            # Check if recent screening exists (unless force refresh)
            if not request.force_refresh:
                recent_screening = await db.fetchrow(
                    """
                    SELECT * FROM screening_results
                    WHERE customer_id = $1 AND screening_type = $2
                    AND created_at > NOW() - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    uuid.UUID(request.customer_id),
                    request.screening_type
                )
                
                if recent_screening:
                    return ScreeningResultResponse(
                        id=str(recent_screening['id']),
                        customer_id=str(recent_screening['customer_id']),
                        customer_name=f"{customer['first_name']} {customer['last_name']}",
                        screening_type=recent_screening['screening_type'],
                        status=recent_screening['status'],
                        match_found=recent_screening['match_found'],
                        match_details=recent_screening['match_details'],
                        risk_level=recent_screening['risk_level'],
                        screened_at=recent_screening['created_at'].isoformat()
                    )
            
            # Perform screening (simplified implementation)
            screening_result = await _perform_screening(db, customer, request.screening_type)
            
            # Save screening result
            result_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO screening_results (
                    id, tenant_id, customer_id, screening_type, status,
                    match_found, match_details, risk_level, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """,
                result_id,
                uuid.UUID(tenant_id),
                uuid.UUID(request.customer_id),
                request.screening_type,
                screening_result['status'],
                screening_result['match_found'],
                screening_result['match_details'],
                screening_result['risk_level']
            )
            
            # Update customer screening status
            if request.screening_type == 'sanctions':
                await db.execute(
                    "UPDATE customers SET sanctions_status = $1, sanctions_checked_at = NOW() WHERE id = $2",
                    screening_result['match_found'],
                    uuid.UUID(request.customer_id)
                )
            elif request.screening_type == 'pep':
                await db.execute(
                    "UPDATE customers SET pep_status = $1, pep_checked_at = NOW() WHERE id = $2",
                    screening_result['match_found'],
                    uuid.UUID(request.customer_id)
                )
            
            logger.info(f"Customer screening completed: {request.customer_id} - {request.screening_type}")
            
            return ScreeningResultResponse(
                id=str(result_id),
                customer_id=request.customer_id,
                customer_name=f"{customer['first_name']} {customer['last_name']}",
                screening_type=request.screening_type,
                status=screening_result['status'],
                match_found=screening_result['match_found'],
                match_details=screening_result['match_details'],
                risk_level=screening_result['risk_level'],
                screened_at=datetime.utcnow().isoformat()
            )
            
    except ResourceNotFoundException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Customer screening failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Customer screening failed"
        )

@router.get("/customers/{customer_id}/screening-history", response_model=List[ScreeningResultResponse])
async def get_customer_screening_history(
    customer_id: str,
    screening_type: Optional[str] = Query(None, description="Filter by screening type"),
    current_user: UserInDB = Depends(require_permission("aml.customers.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get customer screening history.
    
    Requires permission: aml.customers.read
    """
    try:
        async with get_database() as db:
            # Verify customer exists
            customer = await db.fetchrow(
                "SELECT first_name, last_name FROM customers WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(customer_id),
                uuid.UUID(tenant_id)
            )
            
            if not customer:
                raise ResourceNotFoundException("customer", customer_id)
            
            # Build query
            conditions = ["sr.customer_id = $1"]
            params = [uuid.UUID(customer_id)]
            
            if screening_type:
                conditions.append("sr.screening_type = $2")
                params.append(screening_type)
            
            query = f"""
                SELECT sr.*
                FROM screening_results sr
                WHERE {' AND '.join(conditions)}
                ORDER BY sr.created_at DESC
                LIMIT 100
            """
            
            results = await db.fetch(query, *params)
            
            return [
                ScreeningResultResponse(
                    id=str(result['id']),
                    customer_id=str(result['customer_id']),
                    customer_name=f"{customer['first_name']} {customer['last_name']}",
                    screening_type=result['screening_type'],
                    status=result['status'],
                    match_found=result['match_found'],
                    match_details=result['match_details'],
                    risk_level=result['risk_level'],
                    screened_at=result['created_at'].isoformat()
                )
                for result in results
            ]
            
    except ResourceNotFoundException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Get screening history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve screening history"
        )

# ============================================================================
# TRANSACTION MONITORING ENDPOINTS
# ============================================================================

@router.get("/transactions/suspicious", response_model=List[TransactionResponse])
async def get_suspicious_transactions(
    status: Optional[str] = Query(None, description="Filter by monitoring status"),
    risk_threshold: Optional[int] = Query(50, description="Minimum risk score"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    current_user: UserInDB = Depends(require_permission("aml.transactions.monitor")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get suspicious transactions requiring review.
    
    Requires permission: aml.transactions.monitor
    """
    try:
        async with get_database() as db:
            # Build query conditions
            conditions = ["t.tenant_id = $1", "t.risk_score >= $2"]
            params = [uuid.UUID(tenant_id), risk_threshold]
            param_count = 2
            
            if status:
                param_count += 1
                conditions.append(f"t.monitoring_status = ${param_count}")
                params.append(status)
            
            query = f"""
                SELECT t.*, 
                       c.first_name, c.last_name
                FROM transactions t
                JOIN customers c ON t.customer_id = c.id
                WHERE {' AND '.join(conditions)}
                ORDER BY t.risk_score DESC, t.created_at DESC
                LIMIT ${param_count + 1}
            """
            params.append(limit)
            
            transactions = await db.fetch(query, *params)
            
            return [
                TransactionResponse(
                    id=str(tx['id']),
                    customer_id=str(tx['customer_id']),
                    customer_name=f"{tx['first_name']} {tx['last_name']}",
                    transaction_type=tx['transaction_type'],
                    amount=float(tx['amount']),
                    currency=tx['currency'],
                    source_country=tx['source_country'],
                    destination_country=tx['destination_country'],
                    monitoring_status=tx['monitoring_status'],
                    risk_score=tx['risk_score'],
                    suspicious_indicators=tx['suspicious_indicators'] or [],
                    requires_sar=tx['requires_sar'],
                    created_at=tx['created_at'].isoformat()
                )
                for tx in transactions
            ]
            
    except Exception as e:
        logger.error(f"Get suspicious transactions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve suspicious transactions"
        )

# ============================================================================
# SAR MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/sar", response_model=SARResponse)
async def create_sar(
    sar_data: SARCreateRequest,
    current_user: UserInDB = Depends(require_permission("aml.sar.create")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Create a Suspicious Activity Report.
    
    Requires permission: aml.sar.create
    """
    try:
        async with get_database() as db:
            # Verify customer exists
            customer = await db.fetchrow(
                "SELECT first_name, last_name FROM customers WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(sar_data.customer_id),
                uuid.UUID(tenant_id)
            )
            
            if not customer:
                raise ResourceNotFoundException("customer", sar_data.customer_id)
            
            # Create SAR
            sar_id = uuid.uuid4()
            sar_record = await db.fetchrow(
                """
                INSERT INTO suspicious_activity_reports (
                    id, tenant_id, customer_id, transaction_id, report_type,
                    suspicious_activity_description, amount, filing_reason,
                    status, created_by, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                RETURNING *
                """,
                sar_id,
                uuid.UUID(tenant_id),
                uuid.UUID(sar_data.customer_id),
                uuid.UUID(sar_data.transaction_id) if sar_data.transaction_id else None,
                sar_data.report_type,
                sar_data.suspicious_activity_description,
                sar_data.amount,
                sar_data.filing_reason,
                'draft',
                uuid.UUID(current_user.id)
            )
            
            logger.info(f"SAR created: {sar_id} for customer {sar_data.customer_id}")
            
            return SARResponse(
                id=str(sar_record['id']),
                customer_id=str(sar_record['customer_id']),
                customer_name=f"{customer['first_name']} {customer['last_name']}",
                transaction_id=str(sar_record['transaction_id']) if sar_record['transaction_id'] else None,
                report_type=sar_record['report_type'],
                suspicious_activity_description=sar_record['suspicious_activity_description'],
                amount=float(sar_record['amount']) if sar_record['amount'] else None,
                status=sar_record['status'],
                filing_reason=sar_record['filing_reason'],
                filed_date=None,
                created_at=sar_record['created_at'].isoformat()
            )
            
    except ResourceNotFoundException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Create SAR failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SAR"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _perform_screening(db, customer, screening_type):
    """Perform customer screening (simplified implementation)."""
    # This is a simplified implementation
    # In production, this would integrate with external screening services
    
    customer_name = f"{customer['first_name']} {customer['last_name']}"
    
    # Simulate screening logic
    if screening_type == 'sanctions':
        # Check against sanctions lists
        high_risk_names = ['John Doe', 'Jane Smith']  # Example
        match_found = customer_name in high_risk_names
        risk_level = 'high' if match_found else 'low'
        
    elif screening_type == 'pep':
        # Check against PEP lists
        pep_names = ['Political Person']  # Example
        match_found = customer_name in pep_names
        risk_level = 'medium' if match_found else 'low'
        
    else:
        match_found = False
        risk_level = 'low'
    
    return {
        'status': 'completed',
        'match_found': match_found,
        'match_details': {'matched_name': customer_name} if match_found else None,
        'risk_level': risk_level
    }
