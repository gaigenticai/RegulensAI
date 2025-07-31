"""
Analytics Service
Provides analytics and reporting capabilities for the training portal.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, asc
from collections import defaultdict, Counter
import json

from core_infra.database.models import (
    TrainingModule, TrainingEnrollment, TrainingAssessmentAttempt,
    TrainingSectionProgress, TrainingAnalytics, TrainingCertificate,
    TrainingDiscussion, User, Tenant, db
)
from core_infra.exceptions import BusinessLogicException
import structlog

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Service for training portal analytics and reporting."""
    
    def __init__(self):
        """Initialize the Analytics Service with database connection and caching."""
        self.logger = structlog.get_logger(__name__)
        self.cache_ttl = 300  # 5 minutes cache TTL
        self._metrics_cache = {}
        self._cache_timestamps = {}

        # Initialize analytics configuration
        self.analytics_config = {
            'enable_real_time_metrics': True,
            'cache_enabled': True,
            'batch_size': 1000,
            'max_query_timeout': 30,
            'enable_performance_tracking': True
        }

        self.logger.info("Analytics service initialized",
                        config=self.analytics_config)
    
    async def get_training_dashboard_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard metrics for training portal.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dashboard metrics dictionary
        """
        try:
            metrics = {}
            
            # Total modules
            total_modules = TrainingModule.query.filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingModule.is_active == True
            ).count()
            
            # Total enrollments
            total_enrollments = db.session.query(TrainingEnrollment).join(
                TrainingModule, TrainingEnrollment.module_id == TrainingModule.id
            ).filter(TrainingModule.tenant_id == tenant_id).count()
            
            # Completed enrollments
            completed_enrollments = db.session.query(TrainingEnrollment).join(
                TrainingModule, TrainingEnrollment.module_id == TrainingModule.id
            ).filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingEnrollment.status == 'completed'
            ).count()
            
            # Active enrollments
            active_enrollments = db.session.query(TrainingEnrollment).join(
                TrainingModule, TrainingEnrollment.module_id == TrainingModule.id
            ).filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingEnrollment.status.in_(['enrolled', 'in_progress'])
            ).count()
            
            # Certificates issued
            certificates_issued = db.session.query(TrainingCertificate).join(
                TrainingModule, TrainingCertificate.module_id == TrainingModule.id
            ).filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingCertificate.is_valid == True
            ).count()
            
            # Completion rate
            completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
            
            metrics.update({
                'total_modules': total_modules,
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments,
                'active_enrollments': active_enrollments,
                'certificates_issued': certificates_issued,
                'completion_rate': round(completion_rate, 2)
            })
            
            # Recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_enrollments = db.session.query(TrainingEnrollment).join(
                TrainingModule, TrainingEnrollment.module_id == TrainingModule.id
            ).filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingEnrollment.enrolled_at >= thirty_days_ago
            ).count()
            
            recent_completions = db.session.query(TrainingEnrollment).join(
                TrainingModule, TrainingEnrollment.module_id == TrainingModule.id
            ).filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingEnrollment.completed_at >= thirty_days_ago
            ).count()
            
            metrics.update({
                'recent_enrollments': recent_enrollments,
                'recent_completions': recent_completions
            })
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get dashboard metrics", tenant_id=tenant_id, error=str(e))
            raise BusinessLogicException(f"Failed to retrieve dashboard metrics: {e}")
    
    async def get_module_analytics(self, module_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific training module.
        
        Args:
            module_id: Module identifier
            tenant_id: Tenant identifier
            
        Returns:
            Module analytics data
        """
        try:
            # Verify module belongs to tenant
            module = TrainingModule.query.filter(
                TrainingModule.id == module_id,
                TrainingModule.tenant_id == tenant_id
            ).first()
            
            if not module:
                raise BusinessLogicException("Module not found or access denied")
            
            analytics = {
                'module_id': module_id,
                'module_title': module.title,
                'module_category': module.category
            }
            
            # Enrollment statistics
            enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.module_id == module_id
            ).all()
            
            total_enrollments = len(enrollments)
            completed_enrollments = len([e for e in enrollments if e.status == 'completed'])
            in_progress_enrollments = len([e for e in enrollments if e.status == 'in_progress'])
            failed_enrollments = len([e for e in enrollments if e.status == 'failed'])
            
            analytics.update({
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments,
                'in_progress_enrollments': in_progress_enrollments,
                'failed_enrollments': failed_enrollments,
                'completion_rate': (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
            })
            
            # Time analytics
            completed_times = [e.total_time_spent_minutes for e in enrollments if e.status == 'completed' and e.total_time_spent_minutes]
            if completed_times:
                analytics.update({
                    'average_completion_time': sum(completed_times) / len(completed_times),
                    'min_completion_time': min(completed_times),
                    'max_completion_time': max(completed_times)
                })
            
            # Assessment analytics
            assessment_attempts = db.session.query(TrainingAssessmentAttempt).join(
                TrainingEnrollment, TrainingAssessmentAttempt.enrollment_id == TrainingEnrollment.id
            ).filter(TrainingEnrollment.module_id == module_id).all()
            
            if assessment_attempts:
                passed_attempts = [a for a in assessment_attempts if a.passed]
                scores = [a.score for a in assessment_attempts if a.score is not None]
                
                analytics.update({
                    'total_assessment_attempts': len(assessment_attempts),
                    'passed_assessments': len(passed_attempts),
                    'assessment_pass_rate': (len(passed_attempts) / len(assessment_attempts) * 100) if assessment_attempts else 0,
                    'average_score': sum(scores) / len(scores) if scores else 0,
                    'min_score': min(scores) if scores else 0,
                    'max_score': max(scores) if scores else 0
                })
            
            return analytics
            
        except BusinessLogicException:
            raise
        except Exception as e:
            logger.error("Failed to get module analytics", module_id=module_id, error=str(e))
            raise BusinessLogicException(f"Failed to retrieve module analytics: {e}")
    
    async def get_user_progress_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed progress analytics for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            User progress analytics
        """
        try:
            user = User.query.get(user_id)
            if not user:
                raise BusinessLogicException("User not found")
            
            analytics = {
                'user_id': user_id,
                'user_name': user.full_name
            }
            
            # Enrollment statistics
            enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.user_id == user_id
            ).all()
            
            total_enrollments = len(enrollments)
            completed_enrollments = len([e for e in enrollments if e.status == 'completed'])
            in_progress_enrollments = len([e for e in enrollments if e.status == 'in_progress'])
            
            analytics.update({
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments,
                'in_progress_enrollments': in_progress_enrollments,
                'completion_rate': (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
            })
            
            # Category analysis
            category_stats = defaultdict(lambda: {'enrolled': 0, 'completed': 0})
            for enrollment in enrollments:
                if enrollment.module and enrollment.module.category:
                    category = enrollment.module.category
                    category_stats[category]['enrolled'] += 1
                    if enrollment.status == 'completed':
                        category_stats[category]['completed'] += 1
            
            analytics['category_breakdown'] = dict(category_stats)
            
            # Time spent analysis
            total_time_spent = sum(e.total_time_spent_minutes for e in enrollments if e.total_time_spent_minutes)
            analytics['total_time_spent_minutes'] = total_time_spent
            
            # Certificates earned
            certificates = TrainingCertificate.query.filter(
                TrainingCertificate.user_id == user_id,
                TrainingCertificate.is_valid == True
            ).count()
            analytics['certificates_earned'] = certificates
            
            # Recent activity
            recent_activity = []
            for enrollment in sorted(enrollments, key=lambda x: x.last_accessed_at or x.enrolled_at, reverse=True)[:5]:
                if enrollment.module:
                    recent_activity.append({
                        'module_title': enrollment.module.title,
                        'status': enrollment.status,
                        'last_accessed': enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None,
                        'completion_percentage': float(enrollment.completion_percentage) if enrollment.completion_percentage else 0
                    })
            
            analytics['recent_activity'] = recent_activity
            
            return analytics
            
        except BusinessLogicException:
            raise
        except Exception as e:
            logger.error("Failed to get user progress analytics", user_id=user_id, error=str(e))
            raise BusinessLogicException(f"Failed to retrieve user progress analytics: {e}")
    
    async def get_engagement_metrics(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get user engagement metrics for the training portal.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to analyze
            
        Returns:
            Engagement metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Daily active users
            daily_analytics = db.session.query(TrainingAnalytics).join(
                TrainingModule, TrainingAnalytics.module_id == TrainingModule.id
            ).filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingAnalytics.timestamp >= start_date
            ).all()
            
            # Group by date
            daily_users = defaultdict(set)
            daily_events = defaultdict(int)
            
            for event in daily_analytics:
                date_key = event.timestamp.date().isoformat()
                daily_users[date_key].add(event.user_id)
                daily_events[date_key] += 1
            
            # Calculate metrics
            total_unique_users = len(set(event.user_id for event in daily_analytics))
            total_events = len(daily_analytics)
            
            # Most popular modules
            module_views = defaultdict(int)
            for event in daily_analytics:
                if event.module_id and event.event_type == 'page_view':
                    module_views[event.module_id] += 1
            
            popular_modules = []
            for module_id, views in sorted(module_views.items(), key=lambda x: x[1], reverse=True)[:5]:
                module = TrainingModule.query.get(module_id)
                if module:
                    popular_modules.append({
                        'module_id': str(module_id),
                        'module_title': module.title,
                        'views': views
                    })
            
            metrics = {
                'period_days': days,
                'total_unique_users': total_unique_users,
                'total_events': total_events,
                'average_daily_users': total_unique_users / days if days > 0 else 0,
                'average_daily_events': total_events / days if days > 0 else 0,
                'popular_modules': popular_modules,
                'daily_breakdown': [
                    {
                        'date': date,
                        'unique_users': len(users),
                        'total_events': daily_events[date]
                    }
                    for date, users in sorted(daily_users.items())
                ]
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get engagement metrics", tenant_id=tenant_id, error=str(e))
            raise BusinessLogicException(f"Failed to retrieve engagement metrics: {e}")
    
    async def track_event(
        self,
        user_id: str,
        tenant_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        module_id: Optional[str] = None,
        section_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Track a training portal analytics event.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            event_type: Type of event
            event_data: Event data
            module_id: Optional module ID
            section_id: Optional section ID
            session_id: Optional session ID
            ip_address: Optional IP address
            user_agent: Optional user agent
            
        Returns:
            True if event tracked successfully
        """
        try:
            analytics_event = TrainingAnalytics(
                user_id=user_id,
                tenant_id=tenant_id,
                session_id=session_id or 'unknown',
                event_type=event_type,
                event_data=event_data,
                module_id=module_id,
                section_id=section_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.add(analytics_event)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to track analytics event", user_id=user_id, event_type=event_type, error=str(e))
            return False
