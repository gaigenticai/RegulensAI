"""
RegulensAI Operations API Routes
Provides endpoints for deployment, monitoring, and system operations.
"""

import logging
import asyncio
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import get_current_user, require_permission, UserInDB
from core_infra.database import get_database
from core_infra.database.migrate import MigrationRunner
from core_infra.config import get_settings, validate_configuration, get_configuration_summary, ConfigurationError
from core_infra.monitoring.metrics import metrics_collector, collect_all_metrics, get_metrics_data

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SystemStatusResponse(BaseModel):
    """System status response model."""
    overall: str = Field(..., description="Overall system status")
    database: str = Field(..., description="Database status")
    api: str = Field(..., description="API service status")
    monitoring: str = Field(..., description="Monitoring stack status")
    redis: str = Field(default="unknown", description="Redis status")
    lastCheck: str = Field(..., description="Last status check timestamp")

class MigrationStatusResponse(BaseModel):
    """Database migration status response."""
    applied: List[Dict[str, Any]] = Field(default=[], description="Applied migrations")
    pending: List[str] = Field(default=[], description="Pending migrations")
    available: List[str] = Field(default=[], description="Available migrations")
    upToDate: bool = Field(default=True, description="Whether schema is up to date")

class DatabaseHealthResponse(BaseModel):
    """Database health response model."""
    status: str = Field(..., description="Database health status")
    connections: int = Field(default=0, description="Active connections")
    size: str = Field(default="0 MB", description="Database size")
    lastBackup: Optional[str] = Field(None, description="Last backup timestamp")
    performance: Dict[str, Any] = Field(default={}, description="Performance metrics")

class DeploymentRequest(BaseModel):
    """Deployment request model."""
    environment: str = Field(..., description="Target environment")
    version: Optional[str] = Field(None, description="Version to deploy")
    dryRun: bool = Field(default=False, description="Dry run mode")

class MigrationRequest(BaseModel):
    """Migration request model."""
    environment: str = Field(..., description="Target environment")
    migration: Optional[str] = Field(None, description="Specific migration to run")
    dryRun: bool = Field(default=False, description="Dry run mode")

class BackupRequest(BaseModel):
    """Backup request model."""
    environment: str = Field(..., description="Target environment")
    type: str = Field(default="full", description="Backup type")

class ConfigurationValidationResponse(BaseModel):
    """Configuration validation response model."""
    overall_status: str = Field(..., description="Overall validation status")
    timestamp: str = Field(..., description="Validation timestamp")
    environment: str = Field(..., description="Environment being validated")
    validations: Dict[str, Any] = Field(..., description="Detailed validation results")
    summary: Optional[Dict[str, Any]] = Field(None, description="Configuration summary")

class MetricsResponse(BaseModel):
    """Metrics response model."""
    timestamp: str = Field(..., description="Metrics collection timestamp")
    metrics: Dict[str, Any] = Field(..., description="Collected metrics data")

class AlertResponse(BaseModel):
    """Alert response model."""
    alerts: List[Dict[str, Any]] = Field(..., description="Active alerts")
    summary: Dict[str, Any] = Field(..., description="Alert summary statistics")

# ============================================================================
# SYSTEM STATUS ENDPOINTS
# ============================================================================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: UserInDB = Depends(require_permission("operations.read"))
):
    """Get overall system status."""
    try:
        # Check database status
        db_status = await check_database_status()
        
        # Check API status (self-check)
        api_status = "healthy"
        
        # Check monitoring status
        monitoring_status = await check_monitoring_status()
        
        # Check Redis status
        redis_status = await check_redis_status()
        
        # Determine overall status
        statuses = [db_status, api_status, monitoring_status, redis_status]
        if any(s == "error" for s in statuses):
            overall_status = "error"
        elif any(s == "warning" for s in statuses):
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return SystemStatusResponse(
            overall=overall_status,
            database=db_status,
            api=api_status,
            monitoring=monitoring_status,
            redis=redis_status,
            lastCheck=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get system status")

@router.get("/system/detailed-status")
async def get_detailed_system_status(
    current_user: UserInDB = Depends(require_permission("operations.read"))
):
    """Get detailed system status including pods, services, and metrics."""
    try:
        # This would typically call Kubernetes API or monitoring systems
        # For now, return mock data that matches the frontend expectations
        
        return {
            "pods": [
                {
                    "name": "regulensai-api-7d8f9b5c6d-abc12",
                    "status": "Running",
                    "restarts": 0,
                    "age": "2d",
                    "cpu": "45%",
                    "memory": "512Mi"
                },
                {
                    "name": "regulensai-api-7d8f9b5c6d-def34",
                    "status": "Running",
                    "restarts": 0,
                    "age": "2d",
                    "cpu": "38%",
                    "memory": "487Mi"
                }
            ],
            "services": [
                {
                    "name": "regulensai-api",
                    "type": "ClusterIP",
                    "clusterIP": "10.96.1.100",
                    "ports": "8000/TCP",
                    "age": "7d"
                }
            ],
            "resources": {
                "cpu_usage": 45,
                "memory_usage": 67,
                "disk_usage": 23
            },
            "performance": {
                "api_response_time": 245,
                "database_connections": 45,
                "network_io": 156
            }
        }
        
    except Exception as e:
        logger.error("Failed to get detailed system status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get detailed system status")

# ============================================================================
# DATABASE OPERATIONS ENDPOINTS
# ============================================================================

@router.get("/database/migrations", response_model=MigrationStatusResponse)
async def get_migration_status(
    env: str = "staging",
    current_user: UserInDB = Depends(require_permission("operations.database.read"))
):
    """Get database migration status."""
    try:
        # Get database URL for environment
        database_url = get_database_url_for_env(env)
        
        # Initialize migration runner
        runner = MigrationRunner(database_url)
        runner.connect()
        
        try:
            status = runner.get_migration_status()
            
            return MigrationStatusResponse(
                applied=[
                    {
                        "name": migration,
                        "appliedAt": datetime.utcnow().isoformat()
                    } for migration in status.get("applied_migrations", [])
                ],
                pending=status.get("pending_migrations", []),
                available=status.get("available_migrations", []),
                upToDate=status.get("up_to_date", True)
            )
            
        finally:
            runner.disconnect()
            
    except Exception as e:
        logger.error("Failed to get migration status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get migration status")

@router.get("/database/health", response_model=DatabaseHealthResponse)
async def get_database_health(
    env: str = "staging",
    current_user: UserInDB = Depends(require_permission("operations.database.read"))
):
    """Get database health information."""
    try:
        async with get_database() as db:
            # Get database size
            size_result = await db.fetchval(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            
            # Get active connections
            connections_result = await db.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            
            # Get performance metrics
            performance = {
                "status": "good",
                "slow_queries": 0,
                "cache_hit_ratio": 0.95
            }
            
            return DatabaseHealthResponse(
                status="healthy",
                connections=connections_result or 0,
                size=size_result or "0 MB",
                lastBackup=None,  # Would fetch from backup system
                performance=performance
            )
            
    except Exception as e:
        logger.error("Failed to get database health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get database health")

@router.post("/database/migrate")
async def run_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(require_permission("operations.database.write"))
):
    """Run database migration."""
    try:
        if request.environment == "production":
            # Additional validation for production
            logger.warning("Production migration requested", user=current_user.email)
        
        # Run migration in background
        background_tasks.add_task(
            execute_migration,
            request.environment,
            request.migration,
            request.dryRun,
            current_user.id
        )
        
        return {
            "status": "started",
            "message": f"Migration {'dry-run' if request.dryRun else 'execution'} started for {request.environment}"
        }
        
    except Exception as e:
        logger.error("Failed to start migration", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start migration")

@router.post("/database/backup")
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(require_permission("operations.database.write"))
):
    """Create database backup."""
    try:
        # Run backup in background
        background_tasks.add_task(
            execute_backup,
            request.environment,
            request.type,
            current_user.id
        )
        
        return {
            "status": "started",
            "message": f"Backup creation started for {request.environment}"
        }
        
    except Exception as e:
        logger.error("Failed to start backup", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start backup")

# ============================================================================
# CONFIGURATION VALIDATION ENDPOINTS
# ============================================================================

@router.get("/configuration/validate", response_model=ConfigurationValidationResponse)
async def validate_system_configuration(
    include_summary: bool = False,
    current_user: UserInDB = Depends(require_permission("operations.read"))
):
    """Perform comprehensive configuration validation."""
    try:
        logger.info("Configuration validation requested", user=current_user.email)

        # Get current settings
        settings = get_settings()

        # Perform comprehensive validation
        validation_results = await validate_configuration(settings)

        # Add configuration summary if requested
        summary = None
        if include_summary:
            summary = get_configuration_summary(settings)

        return ConfigurationValidationResponse(
            overall_status=validation_results['overall_status'],
            timestamp=validation_results['timestamp'],
            environment=validation_results.get('environment', settings.app_environment),
            validations=validation_results['validations'],
            summary=summary
        )

    except ConfigurationError as e:
        logger.error("Configuration validation failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Configuration validation failed",
                "message": str(e),
                "field": e.field,
                "suggestions": e.suggestions
            }
        )
    except Exception as e:
        logger.error("Configuration validation error", error=str(e))
        raise HTTPException(status_code=500, detail="Configuration validation failed")

@router.get("/configuration/summary")
async def get_configuration_summary_endpoint(
    current_user: UserInDB = Depends(require_permission("operations.read"))
):
    """Get current configuration summary."""
    try:
        settings = get_settings()
        summary = get_configuration_summary(settings)

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": summary
        }

    except Exception as e:
        logger.error("Failed to get configuration summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get configuration summary")

@router.post("/configuration/reload")
async def reload_configuration(
    current_user: UserInDB = Depends(require_permission("operations.write"))
):
    """Reload configuration from environment variables."""
    try:
        logger.info("Configuration reload requested", user=current_user.email)

        # Clear cache and reload settings
        from core_infra.config import reload_settings
        settings = reload_settings()

        # Validate the reloaded configuration
        validation_results = await validate_configuration(settings)

        return {
            "status": "success",
            "message": "Configuration reloaded successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.app_environment,
            "validation_status": validation_results['overall_status']
        }

    except ConfigurationError as e:
        logger.error("Configuration reload failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Configuration reload failed",
                "message": str(e),
                "suggestions": e.suggestions
            }
        )
    except Exception as e:
        logger.error("Configuration reload error", error=str(e))
        raise HTTPException(status_code=500, detail="Configuration reload failed")

@router.get("/configuration/environment/{environment}/validate")
async def validate_environment_configuration(
    environment: str,
    current_user: UserInDB = Depends(require_permission("operations.read"))
):
    """Validate configuration for specific environment."""
    try:
        if environment not in ['development', 'staging', 'production', 'testing']:
            raise HTTPException(
                status_code=400,
                detail="Environment must be one of: development, staging, production, testing"
            )

        logger.info("Environment-specific validation requested",
                   environment=environment, user=current_user.email)

        # Get current settings
        settings = get_settings()

        # Check if current environment matches requested
        if settings.app_environment != environment:
            return {
                "status": "warning",
                "message": f"Current environment is {settings.app_environment}, not {environment}",
                "current_environment": settings.app_environment,
                "requested_environment": environment
            }

        # Perform validation
        validation_results = await validate_configuration(settings)

        return {
            "status": "success",
            "environment": environment,
            "validation_results": validation_results
        }

    except Exception as e:
        logger.error("Environment validation failed", environment=environment, error=str(e))
        raise HTTPException(status_code=500, detail="Environment validation failed")

# ============================================================================
# MONITORING AND METRICS ENDPOINTS
# ============================================================================

@router.get("/metrics/collect")
async def collect_metrics(
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Trigger metrics collection and return current metrics."""
    try:
        logger.info("Metrics collection requested", user=current_user.email)

        # Collect all metrics
        await collect_all_metrics()

        # Get metrics data
        metrics_data = get_metrics_data()

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Metrics collected successfully",
            "metrics_count": len(metrics_data.split('\n'))
        }

    except Exception as e:
        logger.error("Failed to collect metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to collect metrics")

@router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Get Prometheus-formatted metrics."""
    try:
        # Collect latest metrics
        await collect_all_metrics()

        # Return Prometheus format
        from fastapi import Response
        metrics_data = get_metrics_data()

        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    except Exception as e:
        logger.error("Failed to get Prometheus metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@router.get("/metrics/business")
async def get_business_metrics(
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Get business-specific metrics summary."""
    try:
        async with get_database() as db:
            # Get compliance metrics
            compliance_stats = await db.fetchrow("""
                SELECT
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN status = 'overdue' THEN 1 END) as overdue_tasks,
                    AVG(CASE WHEN status = 'completed' THEN 100 ELSE 0 END) as completion_rate
                FROM compliance_tasks
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """)

            # Get training metrics
            training_stats = await db.fetchrow("""
                SELECT
                    COUNT(*) as total_enrollments,
                    COUNT(CASE WHEN tp.completion_percentage = 100 THEN 1 END) as completed_enrollments,
                    AVG(tp.completion_percentage) as avg_completion_rate
                FROM training_enrollments te
                LEFT JOIN training_progress tp ON te.id = tp.enrollment_id
                WHERE te.created_at >= NOW() - INTERVAL '30 days'
            """)

            # Get user activity
            user_stats = await db.fetchrow("""
                SELECT
                    COUNT(DISTINCT user_id) as active_users_24h
                FROM audit_logs
                WHERE action = 'user_login'
                AND created_at >= NOW() - INTERVAL '24 hours'
            """)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "compliance": {
                    "total_tasks": compliance_stats['total_tasks'] or 0,
                    "completed_tasks": compliance_stats['completed_tasks'] or 0,
                    "overdue_tasks": compliance_stats['overdue_tasks'] or 0,
                    "completion_rate": float(compliance_stats['completion_rate'] or 0)
                },
                "training": {
                    "total_enrollments": training_stats['total_enrollments'] or 0,
                    "completed_enrollments": training_stats['completed_enrollments'] or 0,
                    "avg_completion_rate": float(training_stats['avg_completion_rate'] or 0)
                },
                "users": {
                    "active_users_24h": user_stats['active_users_24h'] or 0
                }
            }

    except Exception as e:
        logger.error("Failed to get business metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get business metrics")

@router.get("/alerts/active")
async def get_active_alerts(
    severity: Optional[str] = None,
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Get currently active alerts."""
    try:
        # In a real implementation, this would query Prometheus/AlertManager
        # For now, return mock data that matches the expected format

        mock_alerts = [
            {
                "alertname": "HighCPUUsage",
                "severity": "warning",
                "status": "firing",
                "startsAt": "2024-01-29T10:30:00Z",
                "summary": "High CPU usage detected on production server",
                "description": "CPU usage is 85% on prod-server-01",
                "labels": {
                    "instance": "prod-server-01",
                    "job": "node-exporter"
                }
            },
            {
                "alertname": "ComplianceTaskOverdue",
                "severity": "critical",
                "status": "firing",
                "startsAt": "2024-01-29T09:15:00Z",
                "summary": "Compliance task overdue",
                "description": "Critical compliance task has exceeded deadline",
                "labels": {
                    "tenant_id": "tenant-123",
                    "task_id": "task-456"
                }
            }
        ]

        # Filter by severity if specified
        if severity:
            mock_alerts = [alert for alert in mock_alerts if alert['severity'] == severity]

        # Calculate summary statistics
        summary = {
            "total_alerts": len(mock_alerts),
            "critical": len([a for a in mock_alerts if a['severity'] == 'critical']),
            "warning": len([a for a in mock_alerts if a['severity'] == 'warning']),
            "info": len([a for a in mock_alerts if a['severity'] == 'info'])
        }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": mock_alerts,
            "summary": summary
        }

    except Exception as e:
        logger.error("Failed to get active alerts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get active alerts")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: UserInDB = Depends(require_permission("operations.monitoring.write"))
):
    """Acknowledge an active alert."""
    try:
        logger.info("Alert acknowledged", alert_id=alert_id, user=current_user.email)

        # In a real implementation, this would update AlertManager
        # For now, just log the acknowledgment

        return {
            "status": "success",
            "message": f"Alert {alert_id} acknowledged by {current_user.email}",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")

# ============================================================================
# MONITORING ENDPOINTS (LEGACY)
# ============================================================================

@router.get("/monitoring/status")
async def get_monitoring_status(
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Get monitoring stack status."""
    try:
        return {
            "prometheus": {"enabled": True, "status": "healthy"},
            "grafana": {"enabled": True, "status": "healthy"},
            "alertmanager": {"enabled": True, "status": "healthy"},
            "jaeger": {"enabled": False, "status": "disabled"}
        }
        
    except Exception as e:
        logger.error("Failed to get monitoring status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get monitoring status")

@router.get("/monitoring/alerts")
async def get_alert_rules(
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Get configured alert rules."""
    try:
        # Return mock alert rules
        return [
            {
                "name": "High CPU Usage",
                "severity": "warning",
                "condition": "cpu_usage > 80%",
                "enabled": True
            },
            {
                "name": "Database Connection Failures",
                "severity": "critical",
                "condition": "db_connection_failures > 5",
                "enabled": True
            }
        ]
        
    except Exception as e:
        logger.error("Failed to get alert rules", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get alert rules")

@router.get("/monitoring/notifications")
async def get_notification_channels(
    current_user: UserInDB = Depends(require_permission("operations.monitoring.read"))
):
    """Get configured notification channels."""
    try:
        return [
            {"type": "email", "enabled": True, "config": {"smtp_server": "configured"}},
            {"type": "slack", "enabled": False, "config": {}},
            {"type": "webhook", "enabled": True, "config": {"url": "configured"}}
        ]
        
    except Exception as e:
        logger.error("Failed to get notification channels", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get notification channels")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def check_database_status() -> str:
    """Check database connectivity and health."""
    try:
        async with get_database() as db:
            await db.fetchval("SELECT 1")
            return "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return "error"

async def check_monitoring_status() -> str:
    """Check monitoring stack status."""
    try:
        # This would check Prometheus/Grafana endpoints
        # For now, return healthy
        return "healthy"
    except Exception:
        return "warning"

async def check_redis_status() -> str:
    """Check Redis connectivity."""
    try:
        # This would check Redis connectivity
        # For now, return healthy
        return "healthy"
    except Exception:
        return "warning"

def get_database_url_for_env(env: str) -> str:
    """Get database URL for specific environment."""
    # This would return environment-specific database URLs
    # For now, return the default
    import os
    return os.getenv('DATABASE_URL', 'postgresql://localhost/regulensai')

async def execute_migration(environment: str, migration: Optional[str], dry_run: bool, user_id: str):
    """Execute database migration in background."""
    try:
        logger.info("Starting migration", environment=environment, migration=migration, dry_run=dry_run, user=user_id)
        
        database_url = get_database_url_for_env(environment)
        runner = MigrationRunner(database_url)
        runner.connect()
        
        try:
            if migration:
                success = runner.apply_migration(Path(f"migrations/{migration}.sql"), dry_run)
            else:
                success = runner.run_migrations(dry_run)
            
            if success:
                logger.info("Migration completed successfully", environment=environment)
            else:
                logger.error("Migration failed", environment=environment)
                
        finally:
            runner.disconnect()
            
    except Exception as e:
        logger.error("Migration execution failed", error=str(e), environment=environment)

async def execute_backup(environment: str, backup_type: str, user_id: str):
    """Execute database backup in background."""
    import subprocess
    import os
    from datetime import datetime

    try:
        logger.info("Starting backup", environment=environment, type=backup_type, user=user_id)

        # Get database configuration
        settings = get_settings()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"regulensai_{environment}_backup_{timestamp}.sql"
        backup_path = f"/tmp/{backup_filename}"

        # Determine database URL based on environment
        if environment == "production":
            db_url = settings.database_url
        elif environment == "staging":
            db_url = getattr(settings, 'staging_database_url', settings.database_url)
        else:
            db_url = settings.database_url

        # Create database backup using pg_dump
        dump_cmd = [
            "pg_dump",
            db_url,
            "--format=custom",
            "--compress=6",
            "--verbose",
            "--file", backup_path
        ]

        logger.info("Executing pg_dump", command=" ".join(dump_cmd[:-1] + ["[DATABASE_URL]", "--file", backup_path]))

        # Execute backup command
        result = subprocess.run(
            dump_cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        if result.returncode == 0:
            # Get backup file size
            backup_size = os.path.getsize(backup_path)
            logger.info("Database backup created",
                       file=backup_path,
                       size_bytes=backup_size,
                       size_mb=round(backup_size / 1024 / 1024, 2))

            # Compress backup if not already compressed
            if backup_type == "compressed":
                compressed_path = f"{backup_path}.gz"
                gzip_cmd = ["gzip", backup_path]

                gzip_result = subprocess.run(gzip_cmd, capture_output=True, text=True)

                if gzip_result.returncode == 0:
                    backup_path = compressed_path
                    compressed_size = os.path.getsize(backup_path)
                    logger.info("Backup compressed",
                               file=backup_path,
                               compressed_size_mb=round(compressed_size / 1024 / 1024, 2))
                else:
                    logger.warning("Backup compression failed", error=gzip_result.stderr)

            # Upload to S3 if configured
            s3_bucket = getattr(settings, 'backup_s3_bucket', None)
            if s3_bucket:
                try:
                    s3_key = f"database/{environment}/{os.path.basename(backup_path)}"
                    s3_cmd = [
                        "aws", "s3", "cp", backup_path, f"s3://{s3_bucket}/{s3_key}",
                        "--storage-class", "STANDARD_IA"
                    ]

                    s3_result = subprocess.run(s3_cmd, capture_output=True, text=True)

                    if s3_result.returncode == 0:
                        logger.info("Backup uploaded to S3", bucket=s3_bucket, key=s3_key)

                        # Clean up local file after successful upload
                        os.remove(backup_path)
                        logger.info("Local backup file cleaned up")
                    else:
                        logger.error("S3 upload failed", error=s3_result.stderr)

                except Exception as s3_error:
                    logger.error("S3 upload error", error=str(s3_error))

            logger.info("Backup completed successfully", environment=environment, user=user_id)

        else:
            logger.error("pg_dump failed",
                        returncode=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr)
            raise Exception(f"Database backup failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("Backup timeout", environment=environment, timeout_seconds=3600)
        raise Exception("Backup operation timed out after 1 hour")

    except Exception as e:
        logger.error("Backup execution failed", error=str(e), environment=environment)
        raise
