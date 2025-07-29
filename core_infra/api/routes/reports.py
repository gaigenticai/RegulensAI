"""
Regulens AI - Reporting Routes
Enterprise-grade compliance reporting and analytics endpoints.
"""

import uuid
from datetime import datetime, timedelta
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

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["Reporting & Analytics"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ReportRequest(BaseModel):
    """Report generation request model."""
    report_type: str = Field(..., description="Type of report")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    filters: Dict[str, Any] = Field(default={}, description="Additional filters")
    format: str = Field(default="json", description="Report format (json, csv, pdf)")

class DashboardMetrics(BaseModel):
    """Dashboard metrics response model."""
    total_customers: int
    high_risk_customers: int
    pending_kyc: int
    active_alerts: int
    open_sars: int
    transactions_today: int
    suspicious_transactions: int
    compliance_score: float

class ComplianceMetrics(BaseModel):
    """Compliance metrics response model."""
    kyc_completion_rate: float
    aml_alert_rate: float
    sar_filing_rate: float
    risk_distribution: Dict[str, int]
    regulatory_violations: int
    overdue_reviews: int

class TransactionMetrics(BaseModel):
    """Transaction metrics response model."""
    total_volume: float
    total_count: int
    average_amount: float
    high_risk_transactions: int
    cross_border_percentage: float
    top_countries: List[Dict[str, Any]]

# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    current_user: UserInDB = Depends(require_permission("reports.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get dashboard metrics overview.
    
    Requires permission: reports.read
    """
    try:
        async with get_database() as db:
            # Get customer metrics
            customer_metrics = await db.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_customers,
                    COUNT(CASE WHEN risk_score >= 70 THEN 1 END) as high_risk_customers,
                    COUNT(CASE WHEN kyc_status IN ('pending', 'incomplete') THEN 1 END) as pending_kyc
                FROM customers
                WHERE tenant_id = $1 AND status = 'active'
                """,
                uuid.UUID(tenant_id)
            )
            
            # Get alert metrics
            alert_metrics = await db.fetchrow(
                """
                SELECT COUNT(*) as active_alerts
                FROM alerts
                WHERE tenant_id = $1 AND status = 'open'
                """,
                uuid.UUID(tenant_id)
            )
            
            # Get SAR metrics
            sar_metrics = await db.fetchrow(
                """
                SELECT COUNT(*) as open_sars
                FROM suspicious_activity_reports
                WHERE tenant_id = $1 AND status IN ('draft', 'pending_review')
                """,
                uuid.UUID(tenant_id)
            )
            
            # Get transaction metrics
            transaction_metrics = await db.fetchrow(
                """
                SELECT 
                    COUNT(*) as transactions_today,
                    COUNT(CASE WHEN risk_score >= 50 THEN 1 END) as suspicious_transactions
                FROM transactions
                WHERE tenant_id = $1 AND DATE(created_at) = CURRENT_DATE
                """,
                uuid.UUID(tenant_id)
            )
            
            # Calculate compliance score (simplified)
            kyc_completion = (customer_metrics['total_customers'] - customer_metrics['pending_kyc']) / max(customer_metrics['total_customers'], 1)
            alert_ratio = alert_metrics['active_alerts'] / max(customer_metrics['total_customers'], 1)
            compliance_score = max(0, min(100, (kyc_completion * 100) - (alert_ratio * 10)))
            
            return DashboardMetrics(
                total_customers=customer_metrics['total_customers'],
                high_risk_customers=customer_metrics['high_risk_customers'],
                pending_kyc=customer_metrics['pending_kyc'],
                active_alerts=alert_metrics['active_alerts'],
                open_sars=sar_metrics['open_sars'],
                transactions_today=transaction_metrics['transactions_today'],
                suspicious_transactions=transaction_metrics['suspicious_transactions'],
                compliance_score=round(compliance_score, 2)
            )
            
    except Exception as e:
        logger.error(f"Get dashboard metrics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )

@router.get("/compliance/metrics", response_model=ComplianceMetrics)
async def get_compliance_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: UserInDB = Depends(require_permission("reports.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get detailed compliance metrics.
    
    Requires permission: reports.read
    """
    try:
        async with get_database() as db:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # KYC completion rate
            kyc_metrics = await db.fetchrow(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN kyc_status = 'compliant' THEN 1 END) as compliant
                FROM customers
                WHERE tenant_id = $1 AND created_at >= $2
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            kyc_completion_rate = (kyc_metrics['compliant'] / max(kyc_metrics['total'], 1)) * 100
            
            # AML alert rate
            aml_metrics = await db.fetchrow(
                """
                SELECT 
                    COUNT(DISTINCT t.id) as total_transactions,
                    COUNT(DISTINCT a.entity_id) as alerted_transactions
                FROM transactions t
                LEFT JOIN alerts a ON a.entity_type = 'transaction' AND a.entity_id = t.id
                WHERE t.tenant_id = $1 AND t.created_at >= $2
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            aml_alert_rate = (aml_metrics['alerted_transactions'] / max(aml_metrics['total_transactions'], 1)) * 100
            
            # SAR filing rate
            sar_metrics = await db.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_sars,
                    COUNT(CASE WHEN status = 'filed' THEN 1 END) as filed_sars
                FROM suspicious_activity_reports
                WHERE tenant_id = $1 AND created_at >= $2
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            sar_filing_rate = (sar_metrics['filed_sars'] / max(sar_metrics['total_sars'], 1)) * 100
            
            # Risk distribution
            risk_distribution = await db.fetch(
                """
                SELECT risk_category, COUNT(*) as count
                FROM customers
                WHERE tenant_id = $1
                GROUP BY risk_category
                """,
                uuid.UUID(tenant_id)
            )
            
            risk_dist_dict = {row['risk_category']: row['count'] for row in risk_distribution}
            
            # Regulatory violations
            violations = await db.fetchval(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE tenant_id = $1 AND alert_type LIKE '%violation%' AND created_at >= $2
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            # Overdue reviews
            overdue_reviews = await db.fetchval(
                """
                SELECT COUNT(*)
                FROM customers
                WHERE tenant_id = $1 
                AND (last_kyc_review IS NULL OR last_kyc_review < NOW() - INTERVAL '1 year')
                """,
                uuid.UUID(tenant_id)
            )
            
            return ComplianceMetrics(
                kyc_completion_rate=round(kyc_completion_rate, 2),
                aml_alert_rate=round(aml_alert_rate, 2),
                sar_filing_rate=round(sar_filing_rate, 2),
                risk_distribution=risk_dist_dict,
                regulatory_violations=violations,
                overdue_reviews=overdue_reviews
            )
            
    except Exception as e:
        logger.error(f"Get compliance metrics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve compliance metrics"
        )

@router.get("/transactions/metrics", response_model=TransactionMetrics)
async def get_transaction_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: UserInDB = Depends(require_permission("reports.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get transaction analytics metrics.
    
    Requires permission: reports.read
    """
    try:
        async with get_database() as db:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic transaction metrics
            basic_metrics = await db.fetchrow(
                """
                SELECT 
                    COALESCE(SUM(amount), 0) as total_volume,
                    COUNT(*) as total_count,
                    COALESCE(AVG(amount), 0) as average_amount,
                    COUNT(CASE WHEN risk_score >= 70 THEN 1 END) as high_risk_transactions
                FROM transactions
                WHERE tenant_id = $1 AND created_at >= $2
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            # Cross-border percentage
            cross_border_metrics = await db.fetchrow(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN source_country != destination_country THEN 1 END) as cross_border
                FROM transactions
                WHERE tenant_id = $1 AND created_at >= $2
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            cross_border_percentage = (cross_border_metrics['cross_border'] / max(cross_border_metrics['total'], 1)) * 100
            
            # Top countries
            top_countries = await db.fetch(
                """
                SELECT 
                    destination_country as country,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE tenant_id = $1 AND created_at >= $2
                GROUP BY destination_country
                ORDER BY total_amount DESC
                LIMIT 10
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            top_countries_list = [
                {
                    "country": row['country'],
                    "transaction_count": row['transaction_count'],
                    "total_amount": float(row['total_amount'])
                }
                for row in top_countries
            ]
            
            return TransactionMetrics(
                total_volume=float(basic_metrics['total_volume']),
                total_count=basic_metrics['total_count'],
                average_amount=float(basic_metrics['average_amount']),
                high_risk_transactions=basic_metrics['high_risk_transactions'],
                cross_border_percentage=round(cross_border_percentage, 2),
                top_countries=top_countries_list
            )
            
    except Exception as e:
        logger.error(f"Get transaction metrics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction metrics"
        )

@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    current_user: UserInDB = Depends(require_permission("reports.create")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Generate a compliance report.
    
    Requires permission: reports.create
    """
    try:
        async with get_database() as db:
            # Create report generation task
            report_id = uuid.uuid4()
            
            await db.execute(
                """
                INSERT INTO report_generations (
                    id, tenant_id, report_type, start_date, end_date,
                    filters, format, status, requested_by, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """,
                report_id,
                uuid.UUID(tenant_id),
                request.report_type,
                request.start_date,
                request.end_date,
                request.filters,
                request.format,
                'pending',
                uuid.UUID(current_user.id)
            )
            
            logger.info(f"Report generation requested: {request.report_type} by {current_user.email}")
            
            # In a real implementation, this would trigger background processing
            return {
                "report_id": str(report_id),
                "status": "pending",
                "message": "Report generation started. You will be notified when complete."
            }
            
    except Exception as e:
        logger.error(f"Generate report failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )

@router.get("/alerts/summary")
async def get_alerts_summary(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: UserInDB = Depends(require_permission("reports.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get alerts summary for the specified period.
    
    Requires permission: reports.read
    """
    try:
        async with get_database() as db:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Alert summary by type
            alert_summary = await db.fetch(
                """
                SELECT 
                    alert_type,
                    severity,
                    COUNT(*) as count,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_count
                FROM alerts
                WHERE tenant_id = $1 AND created_at >= $2
                GROUP BY alert_type, severity
                ORDER BY count DESC
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            # Alert trends by day
            alert_trends = await db.fetch(
                """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM alerts
                WHERE tenant_id = $1 AND created_at >= $2
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                uuid.UUID(tenant_id), start_date
            )
            
            return {
                "summary": [
                    {
                        "alert_type": row['alert_type'],
                        "severity": row['severity'],
                        "total_count": row['count'],
                        "open_count": row['open_count']
                    }
                    for row in alert_summary
                ],
                "trends": [
                    {
                        "date": row['date'].isoformat(),
                        "count": row['count']
                    }
                    for row in alert_trends
                ]
            }
            
    except Exception as e:
        logger.error(f"Get alerts summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts summary"
        )
