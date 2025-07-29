"""
Regulatory API Routes
API endpoints for regulatory monitoring, document analysis, and insights.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import get_current_user, verify_tenant_access
from core_infra.database.connection import get_database
from core_infra.services.regulatory_monitor import (
    regulatory_monitor, regulatory_scheduler, 
    get_monitor_status, get_scheduler_status
)
from core_infra.services.regulatory_monitor.analyzer import RegulatoryAnalyzer
from core_infra.ai.embeddings import get_document_embeddings_manager
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class RegulatorySourceCreate(BaseModel):
    """Model for creating a regulatory source."""
    name: str = Field(..., description="Name of the regulatory source")
    type: str = Field(..., description="Type of source (rss, api, web_scrape)")
    country_code: str = Field(..., description="Country code (US, UK, EU, etc.)")
    jurisdiction: str = Field(..., description="Jurisdiction (Federal, State, etc.)")
    website_url: Optional[str] = Field(None, description="Main website URL")
    rss_feed_url: Optional[str] = Field(None, description="RSS feed URL")
    api_endpoint: Optional[str] = Field(None, description="API endpoint URL")
    monitoring_enabled: bool = Field(True, description="Enable monitoring")


class RegulatoryDocumentFilter(BaseModel):
    """Model for filtering regulatory documents."""
    document_type: Optional[str] = None
    status: Optional[str] = None
    jurisdiction: Optional[str] = None
    impact_level: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None
    topics: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class DocumentAnalysisRequest(BaseModel):
    """Model for requesting document analysis."""
    document_id: str = Field(..., description="Document ID to analyze")
    force_reanalysis: bool = Field(False, description="Force re-analysis even if already analyzed")


class SimilarDocumentsRequest(BaseModel):
    """Model for finding similar documents."""
    query_text: Optional[str] = Field(None, description="Text to find similar documents for")
    document_id: Optional[str] = Field(None, description="Document ID to find similar documents for")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=50)
    threshold: float = Field(0.7, description="Similarity threshold", ge=0.0, le=1.0)


class ComplianceDeadlineFilter(BaseModel):
    """Model for filtering compliance deadlines."""
    days_ahead: int = Field(90, description="Number of days to look ahead", ge=1, le=365)
    obligation_type: Optional[str] = None
    priority: Optional[str] = None


# ============================================================================
# REGULATORY SOURCES ENDPOINTS
# ============================================================================

@router.get("/sources", response_model=List[Dict[str, Any]])
async def get_regulatory_sources(
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get all regulatory sources."""
    try:
        async with get_database() as db:
            query = """
                SELECT id, name, type, country_code, jurisdiction, website_url,
                       rss_feed_url, api_endpoint, monitoring_enabled, last_monitored,
                       created_at
                FROM regulatory_sources
                ORDER BY name
            """
            sources = await db.fetch(query)
            
            return [dict(source) for source in sources]
            
    except Exception as e:
        logger.error(f"Failed to get regulatory sources: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve regulatory sources")


@router.post("/sources", response_model=Dict[str, Any])
async def create_regulatory_source(
    source_data: RegulatorySourceCreate,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Create a new regulatory source."""
    try:
        async with get_database() as db:
            query = """
                INSERT INTO regulatory_sources (
                    name, type, country_code, jurisdiction, website_url,
                    rss_feed_url, api_endpoint, monitoring_enabled
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, created_at
            """
            
            result = await db.fetchrow(
                query,
                source_data.name,
                source_data.type,
                source_data.country_code,
                source_data.jurisdiction,
                source_data.website_url,
                source_data.rss_feed_url,
                source_data.api_endpoint,
                source_data.monitoring_enabled
            )
            
            return {
                "id": result["id"],
                "message": "Regulatory source created successfully",
                "created_at": result["created_at"]
            }
            
    except Exception as e:
        logger.error(f"Failed to create regulatory source: {e}")
        raise HTTPException(status_code=500, detail="Failed to create regulatory source")


@router.get("/sources/{source_id}", response_model=Dict[str, Any])
async def get_regulatory_source(
    source_id: str,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get a specific regulatory source."""
    try:
        async with get_database() as db:
            query = "SELECT * FROM regulatory_sources WHERE id = $1"
            source = await db.fetchrow(query, source_id)
            
            if not source:
                raise HTTPException(status_code=404, detail="Regulatory source not found")
            
            return dict(source)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get regulatory source {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve regulatory source")


@router.put("/sources/{source_id}/toggle", response_model=Dict[str, Any])
async def toggle_source_monitoring(
    source_id: str,
    enabled: bool = Query(..., description="Enable or disable monitoring"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Enable or disable monitoring for a regulatory source."""
    try:
        async with get_database() as db:
            query = """
                UPDATE regulatory_sources 
                SET monitoring_enabled = $1, updated_at = now()
                WHERE id = $2
                RETURNING name, monitoring_enabled
            """
            
            result = await db.fetchrow(query, enabled, source_id)
            
            if not result:
                raise HTTPException(status_code=404, detail="Regulatory source not found")
            
            action = "enabled" if enabled else "disabled"
            return {
                "message": f"Monitoring {action} for {result['name']}",
                "monitoring_enabled": result["monitoring_enabled"]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle monitoring for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update monitoring status")


# ============================================================================
# REGULATORY DOCUMENTS ENDPOINTS
# ============================================================================

@router.get("/documents", response_model=Dict[str, Any])
async def get_regulatory_documents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    impact_level: Optional[str] = Query(None, description="Filter by impact level"),
    search: Optional[str] = Query(None, description="Search in title and summary"),
    publication_date_from: Optional[datetime] = Query(None, description="Filter from date"),
    publication_date_to: Optional[datetime] = Query(None, description="Filter to date"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get regulatory documents with filtering and pagination."""
    try:
        offset = (page - 1) * size
        
        # Build query conditions
        conditions = []
        params = []
        param_count = 0
        
        if document_type:
            param_count += 1
            conditions.append(f"rd.document_type = ${param_count}")
            params.append(document_type)
        
        if status:
            param_count += 1
            conditions.append(f"rd.status = ${param_count}")
            params.append(status)
        
        if jurisdiction:
            param_count += 1
            conditions.append(f"rs.jurisdiction = ${param_count}")
            params.append(jurisdiction)
        
        if impact_level:
            param_count += 1
            conditions.append(f"rd.impact_level = ${param_count}")
            params.append(impact_level)
        
        if search:
            param_count += 1
            conditions.append(f"(rd.title ILIKE ${param_count} OR rd.summary ILIKE ${param_count})")
            params.append(f"%{search}%")
        
        if publication_date_from:
            param_count += 1
            conditions.append(f"rd.publication_date >= ${param_count}")
            params.append(publication_date_from)
        
        if publication_date_to:
            param_count += 1
            conditions.append(f"rd.publication_date <= ${param_count}")
            params.append(publication_date_to)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        async with get_database() as db:
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM regulatory_documents rd
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                {where_clause}
            """
            
            total_result = await db.fetchrow(count_query, *params)
            total = total_result["total"]
            
            # Get documents
            param_count += 1
            limit_param = param_count
            param_count += 1
            offset_param = param_count
            
            query = f"""
                SELECT rd.id, rd.document_number, rd.title, rd.document_type,
                       rd.status, rd.publication_date, rd.summary, rd.document_url,
                       rd.topics, rd.keywords, rd.impact_level, rd.created_at,
                       rs.name as source_name, rs.jurisdiction
                FROM regulatory_documents rd
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                {where_clause}
                ORDER BY rd.publication_date DESC, rd.created_at DESC
                LIMIT ${limit_param} OFFSET ${offset_param}
            """
            
            params.extend([size, offset])
            documents = await db.fetch(query, *params)
            
            return {
                "documents": [dict(doc) for doc in documents],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "pages": (total + size - 1) // size
                }
            }
            
    except Exception as e:
        logger.error(f"Failed to get regulatory documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve regulatory documents")


@router.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_regulatory_document(
    document_id: str,
    include_analysis: bool = Query(True, description="Include AI analysis results"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get a specific regulatory document with optional analysis."""
    try:
        async with get_database() as db:
            # Get document
            doc_query = """
                SELECT rd.*, rs.name as source_name, rs.jurisdiction, rs.country_code
                FROM regulatory_documents rd
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                WHERE rd.id = $1
            """
            
            document = await db.fetchrow(doc_query, document_id)
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            result = dict(document)
            
            if include_analysis:
                # Get regulatory obligations
                obligations_query = """
                    SELECT id, obligation_text, obligation_type, compliance_deadline,
                           penalty_description, applicable_entities, section_reference
                    FROM regulatory_obligations
                    WHERE document_id = $1
                    ORDER BY obligation_type, created_at
                """
                obligations = await db.fetch(obligations_query, document_id)
                result["obligations"] = [dict(ob) for ob in obligations]
                
                # Get AI insights
                insights_query = """
                    SELECT insight_type, insight_text, confidence_level, created_at
                    FROM regulatory_insights
                    WHERE document_id = $1
                    ORDER BY created_at DESC
                """
                insights = await db.fetch(insights_query, document_id)
                result["insights"] = [dict(insight) for insight in insights]
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.post("/documents/{document_id}/analyze", response_model=Dict[str, Any])
async def analyze_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    force_reanalysis: bool = Query(False, description="Force re-analysis"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Trigger AI analysis of a regulatory document."""
    try:
        async with get_database() as db:
            # Check if document exists
            doc_query = "SELECT * FROM regulatory_documents WHERE id = $1"
            document = await db.fetchrow(doc_query, document_id)
            
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Check if already analyzed
            if not force_reanalysis:
                insights_query = "SELECT COUNT(*) as count FROM regulatory_insights WHERE document_id = $1"
                insights_count = await db.fetchrow(insights_query, document_id)
                
                if insights_count["count"] > 0:
                    return {
                        "message": "Document already analyzed. Use force_reanalysis=true to re-analyze.",
                        "document_id": document_id,
                        "status": "already_analyzed"
                    }
            
            # Queue analysis task
            background_tasks.add_task(
                _analyze_document_background,
                document_id,
                dict(document)
            )
            
            return {
                "message": "Document analysis queued successfully",
                "document_id": document_id,
                "status": "queued"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue analysis for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue document analysis")


async def _analyze_document_background(document_id: str, document_data: Dict[str, Any]):
    """Background task for document analysis."""
    try:
        analyzer = RegulatoryAnalyzer()
        await analyzer.analyze_document(document_id, document_data)
        logger.info(f"Completed background analysis for document {document_id}")
    except Exception as e:
        logger.error(f"Background analysis failed for document {document_id}: {e}")


@router.post("/documents/similar", response_model=List[Dict[str, Any]])
async def find_similar_documents(
    request: SimilarDocumentsRequest,
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Find documents similar to a query text or existing document."""
    try:
        if not request.query_text and not request.document_id:
            raise HTTPException(
                status_code=400, 
                detail="Either query_text or document_id must be provided"
            )
        
        embeddings_manager = get_document_embeddings_manager()
        
        if request.document_id:
            # Find similar to existing document
            similar_docs = await embeddings_manager.search_similar_documents(
                query_text="",  # Not used when document_id provided
                limit=request.limit,
                filters={"document_id": request.document_id}
            )
        else:
            # Find similar to query text
            similar_docs = await embeddings_manager.search_similar_documents(
                query_text=request.query_text,
                limit=request.limit
            )
        
        # Enrich with document metadata
        if similar_docs:
            doc_ids = [doc["document_id"] for doc in similar_docs]
            
            async with get_database() as db:
                query = """
                    SELECT rd.id, rd.title, rd.document_type, rd.publication_date,
                           rd.summary, rs.name as source_name, rs.jurisdiction
                    FROM regulatory_documents rd
                    JOIN regulatory_sources rs ON rd.source_id = rs.id
                    WHERE rd.id = ANY($1)
                """
                
                documents = await db.fetch(query, doc_ids)
                doc_lookup = {doc["id"]: dict(doc) for doc in documents}
                
                # Combine similarity scores with document data
                result = []
                for sim_doc in similar_docs:
                    doc_id = sim_doc["document_id"]
                    if doc_id in doc_lookup:
                        combined = {
                            **doc_lookup[doc_id],
                            "similarity_score": sim_doc["score"],
                            "matched_excerpt": sim_doc.get("text_excerpt", "")
                        }
                        result.append(combined)
                
                return result
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find similar documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar documents")


# ============================================================================
# COMPLIANCE DEADLINES ENDPOINTS
# ============================================================================

@router.get("/deadlines", response_model=List[Dict[str, Any]])
async def get_compliance_deadlines(
    days_ahead: int = Query(90, ge=1, le=365, description="Days to look ahead"),
    obligation_type: Optional[str] = Query(None, description="Filter by obligation type"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get upcoming compliance deadlines."""
    try:
        async with get_database() as db:
            conditions = ["ro.compliance_deadline BETWEEN $1 AND $2"]
            params = [datetime.utcnow(), datetime.utcnow() + timedelta(days=days_ahead)]
            param_count = 2
            
            if obligation_type:
                param_count += 1
                conditions.append(f"ro.obligation_type = ${param_count}")
                params.append(obligation_type)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT ro.id, ro.obligation_text, ro.obligation_type, ro.compliance_deadline,
                       ro.penalty_description, ro.applicable_entities, ro.section_reference,
                       rd.title as document_title, rd.document_number, rd.document_url,
                       rs.name as source_name, rs.jurisdiction,
                       (ro.compliance_deadline - NOW()) as time_remaining
                FROM regulatory_obligations ro
                JOIN regulatory_documents rd ON ro.document_id = rd.id
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                WHERE {where_clause}
                ORDER BY ro.compliance_deadline ASC
            """
            
            deadlines = await db.fetch(query, *params)
            
            result = []
            for deadline in deadlines:
                deadline_dict = dict(deadline)
                
                # Calculate days remaining
                time_remaining = deadline_dict["time_remaining"]
                if time_remaining:
                    deadline_dict["days_remaining"] = time_remaining.days
                    deadline_dict["is_urgent"] = time_remaining.days <= 30
                
                result.append(deadline_dict)
            
            return result
            
    except Exception as e:
        logger.error(f"Failed to get compliance deadlines: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance deadlines")


# ============================================================================
# MONITORING STATUS ENDPOINTS
# ============================================================================

@router.get("/monitoring/status", response_model=Dict[str, Any])
async def get_monitoring_status(
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get regulatory monitoring status."""
    try:
        monitor_status = await get_monitor_status()
        scheduler_status = await get_scheduler_status()
        
        # Get recent activity stats
        async with get_database() as db:
            # Documents added in last 24 hours
            recent_docs_query = """
                SELECT COUNT(*) as count
                FROM regulatory_documents
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """
            recent_docs = await db.fetchrow(recent_docs_query)
            
            # Total documents
            total_docs_query = "SELECT COUNT(*) as count FROM regulatory_documents"
            total_docs = await db.fetchrow(total_docs_query)
            
            # Pending analysis
            pending_analysis_query = """
                SELECT COUNT(*) as count
                FROM regulatory_documents rd
                LEFT JOIN regulatory_insights ri ON rd.id = ri.document_id
                WHERE ri.document_id IS NULL
            """
            pending_analysis = await db.fetchrow(pending_analysis_query)
        
        return {
            "monitoring": monitor_status,
            "scheduler": scheduler_status,
            "statistics": {
                "total_documents": total_docs["count"],
                "documents_added_24h": recent_docs["count"],
                "pending_analysis": pending_analysis["count"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve monitoring status")


@router.post("/monitoring/start", response_model=Dict[str, Any])
async def start_monitoring(
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Start regulatory monitoring."""
    try:
        if regulatory_monitor.is_running:
            return {
                "message": "Monitoring is already running",
                "status": "running"
            }
        
        await regulatory_monitor.start_monitoring()
        
        return {
            "message": "Regulatory monitoring started successfully",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


@router.post("/monitoring/stop", response_model=Dict[str, Any])
async def stop_monitoring(
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Stop regulatory monitoring."""
    try:
        if not regulatory_monitor.is_running:
            return {
                "message": "Monitoring is not running",
                "status": "stopped"
            }
        
        await regulatory_monitor.stop_monitoring()
        
        return {
            "message": "Regulatory monitoring stopped successfully",
            "status": "stopped"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop monitoring")


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_regulatory_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Get regulatory analytics summary."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with get_database() as db:
            # Document trends
            doc_trends_query = """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM regulatory_documents
                WHERE created_at >= $1
                GROUP BY DATE(created_at)
                ORDER BY date
            """
            doc_trends = await db.fetch(doc_trends_query, start_date)
            
            # Document types distribution
            doc_types_query = """
                SELECT document_type, COUNT(*) as count
                FROM regulatory_documents
                WHERE created_at >= $1
                GROUP BY document_type
                ORDER BY count DESC
            """
            doc_types = await db.fetch(doc_types_query, start_date)
            
            # Impact levels distribution
            impact_levels_query = """
                SELECT impact_level, COUNT(*) as count
                FROM regulatory_documents
                WHERE created_at >= $1 AND impact_level IS NOT NULL
                GROUP BY impact_level
                ORDER BY 
                    CASE impact_level
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END
            """
            impact_levels = await db.fetch(impact_levels_query, start_date)
            
            # Top jurisdictions
            jurisdictions_query = """
                SELECT rs.jurisdiction, COUNT(*) as count
                FROM regulatory_documents rd
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                WHERE rd.created_at >= $1
                GROUP BY rs.jurisdiction
                ORDER BY count DESC
                LIMIT 10
            """
            jurisdictions = await db.fetch(jurisdictions_query, start_date)
            
            # Upcoming deadlines count
            deadlines_query = """
                SELECT COUNT(*) as count
                FROM regulatory_obligations
                WHERE compliance_deadline BETWEEN NOW() AND NOW() + INTERVAL '90 days'
            """
            upcoming_deadlines = await db.fetchrow(deadlines_query)
        
        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            },
            "document_trends": [
                {"date": trend["date"].isoformat(), "count": trend["count"]}
                for trend in doc_trends
            ],
            "document_types": [
                {"type": dt["document_type"], "count": dt["count"]}
                for dt in doc_types
            ],
            "impact_levels": [
                {"level": il["impact_level"], "count": il["count"]}
                for il in impact_levels
            ],
            "top_jurisdictions": [
                {"jurisdiction": j["jurisdiction"], "count": j["count"]}
                for j in jurisdictions
            ],
            "upcoming_deadlines": upcoming_deadlines["count"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get regulatory analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@router.get("/export/documents", response_model=Dict[str, Any])
async def export_documents(
    format: str = Query("json", description="Export format (json, csv)"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    days: int = Query(30, ge=1, le=365, description="Days of data to export"),
    current_user = Depends(get_current_user),
    tenant_check = Depends(verify_tenant_access)
):
    """Export regulatory documents data."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query
        conditions = ["rd.created_at >= $1"]
        params = [start_date]
        param_count = 1
        
        if document_type:
            param_count += 1
            conditions.append(f"rd.document_type = ${param_count}")
            params.append(document_type)
        
        if jurisdiction:
            param_count += 1
            conditions.append(f"rs.jurisdiction = ${param_count}")
            params.append(jurisdiction)
        
        where_clause = " AND ".join(conditions)
        
        async with get_database() as db:
            query = f"""
                SELECT rd.id, rd.document_number, rd.title, rd.document_type,
                       rd.status, rd.publication_date, rd.summary, rd.document_url,
                       rd.topics, rd.keywords, rd.impact_level, rd.created_at,
                       rs.name as source_name, rs.jurisdiction, rs.country_code
                FROM regulatory_documents rd
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                WHERE {where_clause}
                ORDER BY rd.publication_date DESC
            """
            
            documents = await db.fetch(query, *params)
        
        if format.lower() == "csv":
            # Convert to CSV format
            import csv
            from io import StringIO
            
            output = StringIO()
            if documents:
                writer = csv.DictWriter(output, fieldnames=documents[0].keys())
                writer.writeheader()
                for doc in documents:
                    # Convert complex fields to JSON strings
                    doc_dict = dict(doc)
                    for key in ['topics', 'keywords']:
                        if doc_dict[key]:
                            doc_dict[key] = json.dumps(doc_dict[key])
                    writer.writerow(doc_dict)
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "format": "csv",
                "content": csv_content,
                "count": len(documents)
            }
        else:
            # Return as JSON
            return {
                "format": "json",
                "documents": [dict(doc) for doc in documents],
                "count": len(documents)
            }
        
    except Exception as e:
        logger.error(f"Failed to export documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to export documents") 