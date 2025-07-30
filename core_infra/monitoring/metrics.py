"""
RegulensAI Custom Prometheus Metrics
Provides business and application-specific metrics for monitoring and alerting.
"""

import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
import structlog
from sqlalchemy import text

from core_infra.database import get_database

logger = structlog.get_logger(__name__)

# Create custom registry for RegulensAI metrics
regulensai_registry = CollectorRegistry()

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# User activity metrics
user_logins_total = Counter(
    'regulensai_user_logins_total',
    'Total number of user logins',
    ['tenant_id', 'user_role'],
    registry=regulensai_registry
)

user_login_failures_total = Counter(
    'regulensai_user_login_failures_total',
    'Total number of failed login attempts',
    ['reason'],
    registry=regulensai_registry
)

user_registrations_total = Counter(
    'regulensai_user_registrations_total',
    'Total number of user registrations',
    ['tenant_id'],
    registry=regulensai_registry
)

user_activity_by_hour = Gauge(
    'regulensai_user_activity_by_hour',
    'User activity by hour of day',
    ['hour'],
    registry=regulensai_registry
)

# Compliance metrics
compliance_score = Gauge(
    'regulensai_compliance_score',
    'Overall compliance score percentage',
    ['tenant_id'],
    registry=regulensai_registry
)

compliance_tasks_total = Gauge(
    'regulensai_compliance_tasks_total',
    'Total compliance tasks by status',
    ['status', 'tenant_id'],
    registry=regulensai_registry
)

compliance_tasks_by_status = Gauge(
    'regulensai_compliance_tasks_by_status',
    'Compliance tasks grouped by status',
    ['status'],
    registry=regulensai_registry
)

compliance_tasks_overdue = Gauge(
    'regulensai_compliance_tasks_overdue',
    'Number of overdue compliance tasks',
    ['tenant_id'],
    registry=regulensai_registry
)

compliance_tasks_due_24h = Gauge(
    'regulensai_compliance_tasks_due_24h',
    'Number of compliance tasks due within 24 hours',
    ['tenant_id'],
    registry=regulensai_registry
)

# Training portal metrics
training_completion_rate = Gauge(
    'regulensai_training_completion_rate',
    'Training completion rate percentage',
    ['tenant_id'],
    registry=regulensai_registry
)

training_module_starts_total = Counter(
    'regulensai_training_module_starts_total',
    'Total training module starts',
    ['module_id', 'tenant_id'],
    registry=regulensai_registry
)

training_module_completions_total = Counter(
    'regulensai_training_module_completions_total',
    'Total training module completions',
    ['module_id', 'tenant_id'],
    registry=regulensai_registry
)

training_assessment_attempts_total = Counter(
    'regulensai_training_assessment_attempts_total',
    'Total training assessment attempts',
    ['assessment_id', 'tenant_id'],
    registry=regulensai_registry
)

training_certifications_expiring_7d = Gauge(
    'regulensai_training_certifications_expiring_7d',
    'Training certifications expiring within 7 days',
    ['tenant_id'],
    registry=regulensai_registry
)

# ============================================================================
# SYSTEM HEALTH METRICS
# ============================================================================

system_health_score = Gauge(
    'regulensai_system_health_score',
    'Overall system health score percentage',
    registry=regulensai_registry
)

# Database metrics
db_connections_active = Gauge(
    'regulensai_db_connections_active',
    'Number of active database connections',
    registry=regulensai_registry
)

db_connections_max = Gauge(
    'regulensai_db_connections_max',
    'Maximum number of database connections',
    registry=regulensai_registry
)

db_connections_failed_total = Counter(
    'regulensai_db_connections_failed_total',
    'Total number of failed database connections',
    registry=regulensai_registry
)

db_query_duration_seconds = Histogram(
    'regulensai_db_query_duration_seconds',
    'Database query duration in seconds',
    ['table', 'operation'],
    registry=regulensai_registry
)

# Cache metrics
cache_hits_total = Counter(
    'regulensai_cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=regulensai_registry
)

cache_misses_total = Counter(
    'regulensai_cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=regulensai_registry
)

# ============================================================================
# APPLICATION METRICS
# ============================================================================

# Document processing metrics
document_uploads_total = Counter(
    'regulensai_document_uploads_total',
    'Total document uploads',
    ['document_type', 'tenant_id'],
    registry=regulensai_registry
)

document_processing_total = Counter(
    'regulensai_document_processing_total',
    'Total documents processed',
    ['processing_type', 'status'],
    registry=regulensai_registry
)

document_analysis_total = Counter(
    'regulensai_document_analysis_total',
    'Total AI document analyses completed',
    ['analysis_type'],
    registry=regulensai_registry
)

# AI service metrics
openai_requests_total = Counter(
    'regulensai_openai_requests_total',
    'Total OpenAI API requests',
    ['model', 'status'],
    registry=regulensai_registry
)

claude_requests_total = Counter(
    'regulensai_claude_requests_total',
    'Total Claude API requests',
    ['model', 'status'],
    registry=regulensai_registry
)

embedding_requests_total = Counter(
    'regulensai_embedding_requests_total',
    'Total embedding requests',
    ['model'],
    registry=regulensai_registry
)

# Background job metrics
job_queue_size = Gauge(
    'regulensai_job_queue_size',
    'Number of jobs in the queue',
    ['queue_name'],
    registry=regulensai_registry
)

jobs_processed_total = Counter(
    'regulensai_jobs_processed_total',
    'Total jobs processed',
    ['job_type', 'status'],
    registry=regulensai_registry
)

jobs_failed_total = Counter(
    'regulensai_jobs_failed_total',
    'Total failed jobs',
    ['job_type', 'error_type'],
    registry=regulensai_registry
)

# Session metrics
session_duration_seconds = Histogram(
    'regulensai_session_duration_seconds',
    'User session duration in seconds',
    ['tenant_id'],
    registry=regulensai_registry
)

# ============================================================================
# ALERTING AND MONITORING METRICS
# ============================================================================

# Alert metrics
alert_resolution_duration_seconds = Histogram(
    'regulensai_alert_resolution_duration_seconds',
    'Time taken to resolve alerts',
    ['severity', 'category'],
    registry=regulensai_registry
)

alerts_by_escalation = Gauge(
    'regulensai_alerts_by_escalation',
    'Number of alerts by escalation level',
    ['escalation_level'],
    registry=regulensai_registry
)

mttd_seconds = Gauge(
    'regulensai_mttd_seconds',
    'Mean Time to Detection in seconds',
    registry=regulensai_registry
)

mttr_seconds = Gauge(
    'regulensai_mttr_seconds',
    'Mean Time to Resolution in seconds',
    registry=regulensai_registry
)

notification_channel_status = Gauge(
    'regulensai_notification_channel_status',
    'Status of notification channels (1=up, 0=down)',
    ['channel'],
    registry=regulensai_registry
)

# Regulatory and compliance metrics
regulatory_deadlines_missed = Counter(
    'regulensai_regulatory_deadlines_missed',
    'Number of missed regulatory deadlines',
    ['jurisdiction', 'regulation_type'],
    registry=regulensai_registry
)

audit_log_gaps = Gauge(
    'regulensai_audit_log_gaps',
    'Number of detected audit log gaps',
    registry=regulensai_registry
)

security_incidents = Counter(
    'regulensai_security_incidents',
    'Number of security incidents',
    ['incident_type', 'severity'],
    registry=regulensai_registry
)

# ============================================================================
# METRICS COLLECTION FUNCTIONS
# ============================================================================

class MetricsCollector:
    """Collects and updates RegulensAI-specific metrics."""
    
    def __init__(self):
        self.last_collection = datetime.utcnow()
    
    async def collect_business_metrics(self):
        """Collect business-related metrics from the database."""
        try:
            async with get_database() as db:
                # Compliance metrics
                compliance_data = await db.fetch("""
                    SELECT 
                        tenant_id,
                        status,
                        COUNT(*) as task_count,
                        COUNT(CASE WHEN due_date < NOW() THEN 1 END) as overdue_count,
                        COUNT(CASE WHEN due_date BETWEEN NOW() AND NOW() + INTERVAL '24 hours' THEN 1 END) as due_24h_count
                    FROM compliance_tasks 
                    GROUP BY tenant_id, status
                """)
                
                for row in compliance_data:
                    compliance_tasks_total.labels(
                        status=row['status'], 
                        tenant_id=row['tenant_id']
                    ).set(row['task_count'])
                    
                    if row['overdue_count'] > 0:
                        compliance_tasks_overdue.labels(
                            tenant_id=row['tenant_id']
                        ).set(row['overdue_count'])
                    
                    if row['due_24h_count'] > 0:
                        compliance_tasks_due_24h.labels(
                            tenant_id=row['tenant_id']
                        ).set(row['due_24h_count'])
                
                # Training metrics
                training_data = await db.fetch("""
                    SELECT 
                        te.tenant_id,
                        COUNT(CASE WHEN tp.completion_percentage = 100 THEN 1 END) * 100.0 / COUNT(*) as completion_rate
                    FROM training_enrollments te
                    LEFT JOIN training_progress tp ON te.id = tp.enrollment_id
                    WHERE te.created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY te.tenant_id
                """)
                
                for row in training_data:
                    training_completion_rate.labels(
                        tenant_id=row['tenant_id']
                    ).set(row['completion_rate'] or 0)
                
                # User activity metrics
                user_data = await db.fetch("""
                    SELECT 
                        tenant_id,
                        COUNT(*) as login_count
                    FROM audit_logs 
                    WHERE action = 'user_login' 
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY tenant_id
                """)
                
                for row in user_data:
                    user_logins_total.labels(
                        tenant_id=row['tenant_id'],
                        user_role='all'
                    ).inc(row['login_count'])
                
        except Exception as e:
            logger.error("Failed to collect business metrics", error=str(e))
    
    async def collect_system_metrics(self):
        """Collect system health and performance metrics."""
        try:
            async with get_database() as db:
                # Database connection metrics
                db_stats = await db.fetchrow("""
                    SELECT 
                        numbackends as active_connections,
                        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                if db_stats:
                    db_connections_active.set(db_stats['active_connections'])
                    db_connections_max.set(db_stats['max_connections'])
                
                # Calculate system health score
                health_score = await self._calculate_system_health_score()
                system_health_score.set(health_score)
                
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
    
    async def _calculate_system_health_score(self) -> float:
        """Calculate overall system health score."""
        try:
            # This is a simplified calculation - in practice, you'd want more sophisticated logic
            score = 100.0
            
            # Check various health indicators and reduce score accordingly
            # Database health, API response times, error rates, etc.
            
            return max(0.0, min(100.0, score))
        except Exception:
            return 0.0
    
    async def update_alert_metrics(self, alert_name: str, severity: str, resolution_time: float):
        """Update alert-related metrics."""
        alert_resolution_duration_seconds.labels(
            severity=severity,
            category='application'
        ).observe(resolution_time)
    
    def record_cache_hit(self, cache_type: str):
        """Record a cache hit."""
        cache_hits_total.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record a cache miss."""
        cache_misses_total.labels(cache_type=cache_type).inc()
    
    def record_document_upload(self, document_type: str, tenant_id: str):
        """Record a document upload."""
        document_uploads_total.labels(
            document_type=document_type,
            tenant_id=tenant_id
        ).inc()
    
    def record_ai_request(self, service: str, model: str, status: str):
        """Record an AI service request."""
        if service == 'openai':
            openai_requests_total.labels(model=model, status=status).inc()
        elif service == 'claude':
            claude_requests_total.labels(model=model, status=status).inc()


# Global metrics collector instance
metrics_collector = MetricsCollector()


async def collect_all_metrics():
    """Collect all RegulensAI metrics."""
    await metrics_collector.collect_business_metrics()
    await metrics_collector.collect_system_metrics()


def get_metrics_data() -> str:
    """Get Prometheus metrics data."""
    return generate_latest(regulensai_registry).decode('utf-8')
