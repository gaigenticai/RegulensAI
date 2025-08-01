"""
Transaction Management API Routes
Provides endpoints for transaction monitoring, AML screening, and suspicious activity reporting.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import structlog

from core_infra.database.connection import get_database
from core_infra.api.auth import get_current_user, require_permission, verify_tenant_access, UserInDB
from core_infra.exceptions import ResourceNotFoundException, exception_to_http_exception

logger = structlog.get_logger(__name__)
router = APIRouter()

# ============================================================================
# RESPONSE MODELS
# ============================================================================

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
    updated_at: str

class TransactionListResponse(BaseModel):
    """Transaction list response with pagination."""
    transactions: List[TransactionResponse]
    total: int
    page: int
    size: int
    total_pages: int

class TransactionStatsResponse(BaseModel):
    """Transaction statistics response."""
    total_transactions: int
    total_amount: float
    suspicious_transactions: int
    pending_review: int
    sar_filed: int
    average_risk_score: float

# ============================================================================
# TRANSACTION ENDPOINTS
# ============================================================================

@router.get("/", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by monitoring status"),
    risk_threshold: Optional[int] = Query(None, description="Minimum risk score"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    current_user: UserInDB = Depends(require_permission("transactions.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get list of transactions with filtering and pagination.
    
    Requires permission: transactions.read
    """
    try:
        async with get_database() as db:
            # Build dynamic query
            conditions = ["t.tenant_id = $1"]
            params = [uuid.UUID(tenant_id)]
            param_count = 1
            
            if status:
                param_count += 1
                conditions.append(f"t.monitoring_status = ${param_count}")
                params.append(status)
                
            if risk_threshold:
                param_count += 1
                conditions.append(f"t.risk_score >= ${param_count}")
                params.append(risk_threshold)
                
            if customer_id:
                param_count += 1
                conditions.append(f"t.customer_id = ${param_count}")
                params.append(uuid.UUID(customer_id))
                
            if transaction_type:
                param_count += 1
                conditions.append(f"t.transaction_type = ${param_count}")
                params.append(transaction_type)
                
            if currency:
                param_count += 1
                conditions.append(f"t.currency = ${param_count}")
                params.append(currency)
            
            where_clause = " AND ".join(conditions)
            offset = (page - 1) * size
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM transactions t WHERE {where_clause}"
            total = await db.fetchval(count_query, *params)
            
            # Get transactions with customer info
            query = f"""
                SELECT t.id, t.customer_id, t.transaction_type, t.amount, t.currency,
                       t.source_country, t.destination_country, t.monitoring_status,
                       t.risk_score, t.suspicious_indicators, t.requires_sar,
                       t.created_at, t.updated_at,
                       c.first_name || ' ' || c.last_name as customer_name
                FROM transactions t
                LEFT JOIN customers c ON t.customer_id = c.id
                WHERE {where_clause}
                ORDER BY t.created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            
            params.extend([size, offset])
            transactions = await db.fetch(query, *params)
            
            transaction_list = [
                TransactionResponse(
                    id=str(txn['id']),
                    customer_id=str(txn['customer_id']),
                    customer_name=txn['customer_name'] or 'Unknown Customer',
                    transaction_type=txn['transaction_type'],
                    amount=float(txn['amount']),
                    currency=txn['currency'],
                    source_country=txn['source_country'] or '',
                    destination_country=txn['destination_country'] or '',
                    monitoring_status=txn['monitoring_status'] or 'pending',
                    risk_score=txn['risk_score'] or 0,
                    suspicious_indicators=txn['suspicious_indicators'] or [],
                    requires_sar=txn['requires_sar'] or False,
                    created_at=txn['created_at'].isoformat(),
                    updated_at=txn['updated_at'].isoformat()
                )
                for txn in transactions
            ]
            
            total_pages = (total + size - 1) // size
            
            return TransactionListResponse(
                transactions=transaction_list,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )
            
    except Exception as e:
        logger.error(f"Get transactions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transactions"
        )

@router.get("/suspicious", response_model=TransactionListResponse)
async def get_suspicious_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    risk_threshold: int = Query(70, description="Minimum risk score for suspicious transactions"),
    current_user: UserInDB = Depends(require_permission("transactions.monitor")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get suspicious transactions requiring review.
    
    Requires permission: transactions.monitor
    """
    try:
        async with get_database() as db:
            offset = (page - 1) * size
            
            # Get total count of suspicious transactions
            total = await db.fetchval(
                """
                SELECT COUNT(*) FROM transactions 
                WHERE tenant_id = $1 AND (risk_score >= $2 OR requires_sar = true)
                """,
                uuid.UUID(tenant_id),
                risk_threshold
            )
            
            # Get suspicious transactions
            transactions = await db.fetch(
                """
                SELECT t.id, t.customer_id, t.transaction_type, t.amount, t.currency,
                       t.source_country, t.destination_country, t.monitoring_status,
                       t.risk_score, t.suspicious_indicators, t.requires_sar,
                       t.created_at, t.updated_at,
                       c.first_name || ' ' || c.last_name as customer_name
                FROM transactions t
                LEFT JOIN customers c ON t.customer_id = c.id
                WHERE t.tenant_id = $1 AND (t.risk_score >= $2 OR t.requires_sar = true)
                ORDER BY t.risk_score DESC, t.created_at DESC
                LIMIT $3 OFFSET $4
                """,
                uuid.UUID(tenant_id),
                risk_threshold,
                size,
                offset
            )
            
            transaction_list = [
                TransactionResponse(
                    id=str(txn['id']),
                    customer_id=str(txn['customer_id']),
                    customer_name=txn['customer_name'] or 'Unknown Customer',
                    transaction_type=txn['transaction_type'],
                    amount=float(txn['amount']),
                    currency=txn['currency'],
                    source_country=txn['source_country'] or '',
                    destination_country=txn['destination_country'] or '',
                    monitoring_status=txn['monitoring_status'] or 'pending',
                    risk_score=txn['risk_score'] or 0,
                    suspicious_indicators=txn['suspicious_indicators'] or [],
                    requires_sar=txn['requires_sar'] or False,
                    created_at=txn['created_at'].isoformat(),
                    updated_at=txn['updated_at'].isoformat()
                )
                for txn in transactions
            ]
            
            total_pages = (total + size - 1) // size
            
            return TransactionListResponse(
                transactions=transaction_list,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )
            
    except Exception as e:
        logger.error(f"Get suspicious transactions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suspicious transactions"
        )

@router.get("/stats", response_model=TransactionStatsResponse)
async def get_transaction_stats(
    current_user: UserInDB = Depends(require_permission("transactions.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get transaction statistics for the tenant.
    
    Requires permission: transactions.read
    """
    try:
        async with get_database() as db:
            stats = await db.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_transactions,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COUNT(*) FILTER (WHERE risk_score >= 70) as suspicious_transactions,
                    COUNT(*) FILTER (WHERE monitoring_status = 'pending_review') as pending_review,
                    COUNT(*) FILTER (WHERE requires_sar = true) as sar_filed,
                    COALESCE(AVG(risk_score), 0) as average_risk_score
                FROM transactions
                WHERE tenant_id = $1
                """,
                uuid.UUID(tenant_id)
            )
            
            return TransactionStatsResponse(
                total_transactions=stats['total_transactions'],
                total_amount=float(stats['total_amount']),
                suspicious_transactions=stats['suspicious_transactions'],
                pending_review=stats['pending_review'],
                sar_filed=stats['sar_filed'],
                average_risk_score=float(stats['average_risk_score'])
            )
            
    except Exception as e:
        logger.error(f"Get transaction stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transaction statistics"
        )
