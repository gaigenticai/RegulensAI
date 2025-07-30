"""
Training Portal Database Optimization Utilities
Advanced database optimization strategies for training portal performance.
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text, func, and_, or_, select, update, delete
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager
from sqlalchemy.sql import Select
from datetime import datetime, timedelta
import structlog

from core_infra.database.models import (
    TrainingModule, TrainingSection, TrainingEnrollment,
    TrainingSectionProgress, TrainingAssessment, TrainingCertificate,
    TrainingAnalytics, User, Tenant
)
from core_infra.database.connection import get_db_session

logger = structlog.get_logger(__name__)


class TrainingDBOptimizer:
    """Database optimization utilities for training portal."""
    
    def __init__(self):
        self.query_cache = {}
        self.index_recommendations = []
    
    def get_optimized_modules_query(
        self,
        tenant_id: str,
        filters: Dict[str, Any] = None,
        include_sections: bool = False,
        include_enrollments: bool = False
    ) -> Select:
        """Get optimized query for training modules with proper joins and filtering."""
        
        # Base query with optimized loading
        query = select(TrainingModule).where(
            and_(
                TrainingModule.tenant_id == tenant_id,
                TrainingModule.is_active == True
            )
        )
        
        # Add eager loading based on requirements
        if include_sections:
            query = query.options(selectinload(TrainingModule.sections))
        
        if include_enrollments:
            query = query.options(selectinload(TrainingModule.enrollments))
        
        # Apply filters efficiently
        if filters:
            if filters.get('category'):
                query = query.where(TrainingModule.category == filters['category'])
            
            if filters.get('difficulty_level'):
                query = query.where(TrainingModule.difficulty_level == filters['difficulty_level'])
            
            if filters.get('is_mandatory') is not None:
                query = query.where(TrainingModule.is_mandatory == filters['is_mandatory'])
            
            if filters.get('content_type'):
                query = query.where(TrainingModule.content_type == filters['content_type'])
            
            # Text search optimization
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.where(
                    or_(
                        TrainingModule.title.ilike(search_term),
                        TrainingModule.description.ilike(search_term),
                        TrainingModule.learning_objectives.op('?&')(
                            [filters['search']]  # JSON array contains search term
                        )
                    )
                )
        
        return query
    
    def get_user_enrollments_optimized(
        self,
        user_id: str,
        status_filter: str = None,
        include_progress: bool = True,
        include_module_details: bool = True
    ) -> Select:
        """Get optimized query for user enrollments with minimal database hits."""
        
        query = select(TrainingEnrollment).where(
            TrainingEnrollment.user_id == user_id
        )
        
        # Optimize joins based on requirements
        if include_module_details:
            query = query.options(
                joinedload(TrainingEnrollment.module).selectinload(TrainingModule.sections)
            )
        
        if include_progress:
            query = query.options(
                selectinload(TrainingEnrollment.section_progress)
            )
        
        # Apply status filter
        if status_filter:
            query = query.where(TrainingEnrollment.status == status_filter)
        
        # Order by most recent first
        query = query.order_by(TrainingEnrollment.last_accessed_at.desc().nullslast())
        
        return query
    
    def get_enrollment_progress_optimized(self, enrollment_id: str) -> Select:
        """Get optimized query for enrollment progress with all related data."""
        
        return select(TrainingEnrollment).where(
            TrainingEnrollment.id == enrollment_id
        ).options(
            joinedload(TrainingEnrollment.module).selectinload(TrainingModule.sections),
            selectinload(TrainingEnrollment.section_progress),
            joinedload(TrainingEnrollment.user)
        )
    
    def get_analytics_data_optimized(
        self,
        tenant_id: str,
        user_id: str = None,
        time_range: Tuple[datetime, datetime] = None
    ) -> Select:
        """Get optimized analytics query with aggregations."""
        
        query = select(TrainingAnalytics).where(
            TrainingAnalytics.tenant_id == tenant_id
        )
        
        if user_id:
            query = query.where(TrainingAnalytics.user_id == user_id)
        
        if time_range:
            start_time, end_time = time_range
            query = query.where(
                and_(
                    TrainingAnalytics.created_at >= start_time,
                    TrainingAnalytics.created_at <= end_time
                )
            )
        
        # Order by most recent first for efficient pagination
        query = query.order_by(TrainingAnalytics.created_at.desc())
        
        return query
    
    async def get_dashboard_metrics_optimized(
        self,
        db: Session,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get dashboard metrics with optimized aggregation queries."""
        
        try:
            # Use raw SQL for complex aggregations
            metrics_query = text("""
                SELECT 
                    COUNT(DISTINCT tm.id) as total_modules,
                    COUNT(DISTINCT CASE WHEN tm.is_mandatory THEN tm.id END) as mandatory_modules,
                    COUNT(DISTINCT te.id) as total_enrollments,
                    COUNT(DISTINCT CASE WHEN te.status = 'completed' THEN te.id END) as completed_enrollments,
                    COUNT(DISTINCT CASE WHEN te.status = 'in_progress' THEN te.id END) as active_enrollments,
                    COUNT(DISTINCT tc.id) as total_certificates,
                    COUNT(DISTINCT te.user_id) as unique_learners,
                    AVG(te.completion_percentage) as avg_completion_rate,
                    AVG(EXTRACT(EPOCH FROM (te.completed_at - te.enrolled_at))/3600) as avg_completion_time_hours
                FROM training_modules tm
                LEFT JOIN training_enrollments te ON tm.id = te.module_id
                LEFT JOIN training_certificates tc ON te.id = tc.enrollment_id
                WHERE tm.tenant_id = :tenant_id AND tm.is_active = true
            """)
            
            result = db.execute(metrics_query, {"tenant_id": tenant_id}).fetchone()
            
            # Get recent activity
            recent_activity_query = text("""
                SELECT 
                    DATE(te.enrolled_at) as date,
                    COUNT(*) as enrollments,
                    COUNT(CASE WHEN te.status = 'completed' THEN 1 END) as completions
                FROM training_enrollments te
                JOIN training_modules tm ON te.module_id = tm.id
                WHERE tm.tenant_id = :tenant_id 
                    AND te.enrolled_at >= :start_date
                GROUP BY DATE(te.enrolled_at)
                ORDER BY date DESC
                LIMIT 30
            """)
            
            start_date = datetime.utcnow() - timedelta(days=30)
            activity_results = db.execute(
                recent_activity_query, 
                {"tenant_id": tenant_id, "start_date": start_date}
            ).fetchall()
            
            return {
                "total_modules": result.total_modules or 0,
                "mandatory_modules": result.mandatory_modules or 0,
                "total_enrollments": result.total_enrollments or 0,
                "completed_enrollments": result.completed_enrollments or 0,
                "active_enrollments": result.active_enrollments or 0,
                "total_certificates": result.total_certificates or 0,
                "unique_learners": result.unique_learners or 0,
                "avg_completion_rate": float(result.avg_completion_rate or 0),
                "avg_completion_time_hours": float(result.avg_completion_time_hours or 0),
                "recent_activity": [
                    {
                        "date": row.date.isoformat() if row.date else None,
                        "enrollments": row.enrollments,
                        "completions": row.completions
                    }
                    for row in activity_results
                ]
            }
            
        except Exception as e:
            logger.error("Failed to get optimized dashboard metrics", error=str(e))
            return {}
    
    async def bulk_update_progress(
        self,
        db: Session,
        progress_updates: List[Dict[str, Any]]
    ) -> bool:
        """Efficiently bulk update section progress."""
        
        try:
            # Group updates by enrollment for efficiency
            enrollment_updates = {}
            for update in progress_updates:
                enrollment_id = update['enrollment_id']
                if enrollment_id not in enrollment_updates:
                    enrollment_updates[enrollment_id] = []
                enrollment_updates[enrollment_id].append(update)
            
            # Process each enrollment's updates
            for enrollment_id, updates in enrollment_updates.items():
                # Update section progress in batch
                for update in updates:
                    stmt = update(TrainingSectionProgress).where(
                        and_(
                            TrainingSectionProgress.enrollment_id == enrollment_id,
                            TrainingSectionProgress.section_id == update['section_id']
                        )
                    ).values(
                        status=update.get('status'),
                        time_spent_minutes=update.get('time_spent_minutes'),
                        last_position=update.get('last_position'),
                        notes=update.get('notes'),
                        interactions=update.get('interactions'),
                        updated_at=datetime.utcnow()
                    )
                    db.execute(stmt)
                
                # Update enrollment last accessed time
                enrollment_stmt = update(TrainingEnrollment).where(
                    TrainingEnrollment.id == enrollment_id
                ).values(
                    last_accessed_at=datetime.utcnow()
                )
                db.execute(enrollment_stmt)
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error("Failed to bulk update progress", error=str(e))
            db.rollback()
            return False
    
    def get_recommended_indexes(self) -> List[Dict[str, str]]:
        """Get recommended database indexes for training portal performance."""
        
        return [
            {
                "table": "training_modules",
                "columns": ["tenant_id", "is_active", "category"],
                "type": "composite",
                "reason": "Optimize module filtering queries"
            },
            {
                "table": "training_modules",
                "columns": ["title", "description"],
                "type": "gin",
                "reason": "Optimize text search queries"
            },
            {
                "table": "training_enrollments",
                "columns": ["user_id", "status"],
                "type": "composite",
                "reason": "Optimize user enrollment queries"
            },
            {
                "table": "training_enrollments",
                "columns": ["module_id", "status"],
                "type": "composite",
                "reason": "Optimize module enrollment statistics"
            },
            {
                "table": "training_section_progress",
                "columns": ["enrollment_id", "section_id"],
                "type": "composite",
                "reason": "Optimize progress tracking queries"
            },
            {
                "table": "training_analytics",
                "columns": ["tenant_id", "created_at"],
                "type": "composite",
                "reason": "Optimize analytics time-series queries"
            },
            {
                "table": "training_analytics",
                "columns": ["user_id", "event_type", "created_at"],
                "type": "composite",
                "reason": "Optimize user analytics queries"
            },
            {
                "table": "training_certificates",
                "columns": ["user_id", "issued_at"],
                "type": "composite",
                "reason": "Optimize certificate queries"
            },
            {
                "table": "training_certificates",
                "columns": ["verification_code"],
                "type": "unique",
                "reason": "Optimize certificate verification"
            }
        ]
    
    async def analyze_query_performance(
        self,
        db: Session,
        query: str,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analyze query performance and provide optimization suggestions."""
        
        try:
            # Use EXPLAIN ANALYZE for PostgreSQL
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            
            result = db.execute(text(explain_query), params or {}).fetchone()
            explain_data = result[0] if result else {}
            
            # Extract key performance metrics
            plan = explain_data.get('Plan', {}) if explain_data else {}
            
            analysis = {
                "execution_time": explain_data.get('Execution Time', 0),
                "planning_time": explain_data.get('Planning Time', 0),
                "total_cost": plan.get('Total Cost', 0),
                "actual_rows": plan.get('Actual Rows', 0),
                "node_type": plan.get('Node Type', ''),
                "suggestions": []
            }
            
            # Generate optimization suggestions
            if analysis["execution_time"] > 1000:  # > 1 second
                analysis["suggestions"].append("Consider adding appropriate indexes")
            
            if plan.get('Node Type') == 'Seq Scan':
                analysis["suggestions"].append("Sequential scan detected - consider adding index")
            
            if analysis["total_cost"] > 10000:
                analysis["suggestions"].append("High cost query - consider query optimization")
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze query performance", error=str(e))
            return {"error": "Query analysis failed"}


# Global optimizer instance
training_db_optimizer = TrainingDBOptimizer()
