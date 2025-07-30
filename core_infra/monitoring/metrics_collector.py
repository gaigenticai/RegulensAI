"""
Prometheus Metrics Collector for RegulensAI.
Collects and exposes metrics for all services and integrations.
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
import structlog
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_client.multiprocess import MultiProcessCollector
import psutil

logger = structlog.get_logger(__name__)


class RegulensAIMetricsCollector:
    """
    Comprehensive metrics collector for RegulensAI platform.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._initialize_metrics()
        
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""
        
        # API Metrics
        self.api_requests_total = Counter(
            'regulensai_api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code', 'tenant_id'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'regulensai_api_request_duration_seconds',
            'API request duration in seconds',
            ['method', 'endpoint', 'tenant_id'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.api_active_requests = Gauge(
            'regulensai_api_active_requests',
            'Number of active API requests',
            ['endpoint'],
            registry=self.registry
        )
        
        # External Data Integration Metrics
        self.external_data_requests_total = Counter(
            'regulensai_external_data_requests_total',
            'Total external data provider requests',
            ['provider', 'operation', 'status'],
            registry=self.registry
        )
        
        self.external_data_request_duration = Histogram(
            'regulensai_external_data_request_duration_seconds',
            'External data request duration in seconds',
            ['provider', 'operation'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.external_data_cache_hits = Counter(
            'regulensai_external_data_cache_hits_total',
            'External data cache hits',
            ['provider'],
            registry=self.registry
        )
        
        self.external_data_cache_misses = Counter(
            'regulensai_external_data_cache_misses_total',
            'External data cache misses',
            ['provider'],
            registry=self.registry
        )
        
        self.external_data_rate_limits = Counter(
            'regulensai_external_data_rate_limits_total',
            'External data rate limit hits',
            ['provider'],
            registry=self.registry
        )
        
        # Notification System Metrics
        self.notifications_sent_total = Counter(
            'regulensai_notifications_sent_total',
            'Total notifications sent',
            ['channel', 'template', 'status', 'tenant_id'],
            registry=self.registry
        )
        
        self.notification_processing_duration = Histogram(
            'regulensai_notification_processing_duration_seconds',
            'Notification processing duration in seconds',
            ['channel', 'template'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.notification_queue_size = Gauge(
            'regulensai_notification_queue_size',
            'Current notification queue size',
            ['priority'],
            registry=self.registry
        )
        
        self.notification_delivery_attempts = Counter(
            'regulensai_notification_delivery_attempts_total',
            'Total notification delivery attempts',
            ['channel', 'attempt_number'],
            registry=self.registry
        )
        
        # GRC Integration Metrics
        self.grc_sync_operations_total = Counter(
            'regulensai_grc_sync_operations_total',
            'Total GRC sync operations',
            ['system_type', 'operation', 'status'],
            registry=self.registry
        )
        
        self.grc_sync_duration = Histogram(
            'regulensai_grc_sync_duration_seconds',
            'GRC sync operation duration in seconds',
            ['system_type', 'operation'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
            registry=self.registry
        )
        
        self.grc_records_processed = Counter(
            'regulensai_grc_records_processed_total',
            'Total GRC records processed',
            ['system_type', 'record_type', 'operation'],
            registry=self.registry
        )
        
        self.grc_sync_errors = Counter(
            'regulensai_grc_sync_errors_total',
            'GRC sync errors',
            ['system_type', 'error_type'],
            registry=self.registry
        )
        
        # Database Metrics
        self.database_queries_total = Counter(
            'regulensai_database_queries_total',
            'Total database queries',
            ['operation', 'table', 'status'],
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'regulensai_database_query_duration_seconds',
            'Database query duration in seconds',
            ['operation', 'table'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.database_connections_active = Gauge(
            'regulensai_database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.database_connections_pool_size = Gauge(
            'regulensai_database_connections_pool_size',
            'Database connection pool size',
            registry=self.registry
        )
        
        # Cache Metrics
        self.cache_operations_total = Counter(
            'regulensai_cache_operations_total',
            'Total cache operations',
            ['operation', 'cache_type', 'status'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'regulensai_cache_hit_ratio',
            'Cache hit ratio',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_size_bytes = Gauge(
            'regulensai_cache_size_bytes',
            'Cache size in bytes',
            ['cache_type'],
            registry=self.registry
        )
        
        # System Resource Metrics
        self.system_cpu_usage = Gauge(
            'regulensai_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'regulensai_system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )
        
        self.system_memory_total = Gauge(
            'regulensai_system_memory_total_bytes',
            'Total system memory in bytes',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'regulensai_system_disk_usage_bytes',
            'System disk usage in bytes',
            ['device'],
            registry=self.registry
        )
        
        # Business Metrics
        self.entities_screened_total = Counter(
            'regulensai_entities_screened_total',
            'Total entities screened',
            ['entity_type', 'screening_type', 'result', 'tenant_id'],
            registry=self.registry
        )
        
        self.compliance_violations_total = Counter(
            'regulensai_compliance_violations_total',
            'Total compliance violations detected',
            ['violation_type', 'severity', 'tenant_id'],
            registry=self.registry
        )
        
        self.risk_assessments_total = Counter(
            'regulensai_risk_assessments_total',
            'Total risk assessments performed',
            ['risk_type', 'risk_level', 'tenant_id'],
            registry=self.registry
        )
        
        # Feature Flag Metrics
        self.feature_flag_evaluations_total = Counter(
            'regulensai_feature_flag_evaluations_total',
            'Total feature flag evaluations',
            ['flag_name', 'result', 'tenant_id'],
            registry=self.registry
        )
        
        # Application Info
        self.application_info = Info(
            'regulensai_application_info',
            'Application information',
            registry=self.registry
        )
        
        # Set application info
        self.application_info.info({
            'version': '1.0.0',
            'environment': 'production',
            'build_date': datetime.utcnow().isoformat()
        })
    
    def track_api_request(self, method: str, endpoint: str, tenant_id: str = "unknown"):
        """Decorator to track API request metrics."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status_code = "200"
                
                # Increment active requests
                self.api_active_requests.labels(endpoint=endpoint).inc()
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    status_code = "500"
                    raise
                    
                finally:
                    # Record metrics
                    duration = time.time() - start_time
                    
                    self.api_requests_total.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code=status_code,
                        tenant_id=tenant_id
                    ).inc()
                    
                    self.api_request_duration.labels(
                        method=method,
                        endpoint=endpoint,
                        tenant_id=tenant_id
                    ).observe(duration)
                    
                    # Decrement active requests
                    self.api_active_requests.labels(endpoint=endpoint).dec()
            
            return wrapper
        return decorator
    
    def track_external_data_request(self, provider: str, operation: str):
        """Decorator to track external data request metrics."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    status = "error"
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    
                    self.external_data_requests_total.labels(
                        provider=provider,
                        operation=operation,
                        status=status
                    ).inc()
                    
                    self.external_data_request_duration.labels(
                        provider=provider,
                        operation=operation
                    ).observe(duration)
            
            return wrapper
        return decorator
    
    def track_notification_processing(self, channel: str, template: str):
        """Decorator to track notification processing metrics."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                tenant_id = kwargs.get('tenant_id', 'unknown')
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    status = "error"
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    
                    self.notifications_sent_total.labels(
                        channel=channel,
                        template=template,
                        status=status,
                        tenant_id=tenant_id
                    ).inc()
                    
                    self.notification_processing_duration.labels(
                        channel=channel,
                        template=template
                    ).observe(duration)
            
            return wrapper
        return decorator
    
    def track_grc_sync(self, system_type: str, operation: str):
        """Decorator to track GRC sync metrics."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Track records processed if available in result
                    if isinstance(result, dict):
                        records_processed = result.get('total_processed', 0)
                        if records_processed > 0:
                            self.grc_records_processed.labels(
                                system_type=system_type,
                                record_type="risk",
                                operation=operation
                            ).inc(records_processed)
                    
                    return result
                    
                except Exception as e:
                    status = "error"
                    self.grc_sync_errors.labels(
                        system_type=system_type,
                        error_type=type(e).__name__
                    ).inc()
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    
                    self.grc_sync_operations_total.labels(
                        system_type=system_type,
                        operation=operation,
                        status=status
                    ).inc()
                    
                    self.grc_sync_duration.labels(
                        system_type=system_type,
                        operation=operation
                    ).observe(duration)
            
            return wrapper
        return decorator
    
    def track_database_query(self, operation: str, table: str):
        """Decorator to track database query metrics."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    status = "error"
                    raise
                    
                finally:
                    duration = time.time() - start_time
                    
                    self.database_queries_total.labels(
                        operation=operation,
                        table=table,
                        status=status
                    ).inc()
                    
                    self.database_query_duration.labels(
                        operation=operation,
                        table=table
                    ).observe(duration)
            
            return wrapper
        return decorator
    
    def record_cache_operation(self, operation: str, cache_type: str, hit: bool = False):
        """Record cache operation metrics."""
        status = "hit" if hit else "miss"
        
        self.cache_operations_total.labels(
            operation=operation,
            cache_type=cache_type,
            status=status
        ).inc()
        
        if operation == "get":
            if hit:
                self.external_data_cache_hits.labels(cache_type).inc()
            else:
                self.external_data_cache_misses.labels(cache_type).inc()
    
    def record_entity_screening(
        self,
        entity_type: str,
        screening_type: str,
        result: str,
        tenant_id: str
    ):
        """Record entity screening metrics."""
        self.entities_screened_total.labels(
            entity_type=entity_type,
            screening_type=screening_type,
            result=result,
            tenant_id=tenant_id
        ).inc()
    
    def record_compliance_violation(
        self,
        violation_type: str,
        severity: str,
        tenant_id: str
    ):
        """Record compliance violation metrics."""
        self.compliance_violations_total.labels(
            violation_type=violation_type,
            severity=severity,
            tenant_id=tenant_id
        ).inc()
    
    def record_feature_flag_evaluation(
        self,
        flag_name: str,
        result: bool,
        tenant_id: str
    ):
        """Record feature flag evaluation metrics."""
        self.feature_flag_evaluations_total.labels(
            flag_name=flag_name,
            result=str(result).lower(),
            tenant_id=tenant_id
        ).inc()
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)
            self.system_memory_total.set(memory.total)
            
            # Disk usage
            for disk in psutil.disk_partitions():
                try:
                    disk_usage = psutil.disk_usage(disk.mountpoint)
                    self.system_disk_usage.labels(device=disk.device).set(disk_usage.used)
                except (PermissionError, OSError):
                    # Skip inaccessible disks
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def update_queue_metrics(self, queue_sizes: Dict[str, int]):
        """Update queue size metrics."""
        for priority, size in queue_sizes.items():
            self.notification_queue_size.labels(priority=priority).set(size)
    
    def update_database_connection_metrics(self, active_connections: int, pool_size: int):
        """Update database connection metrics."""
        self.database_connections_active.set(active_connections)
        self.database_connections_pool_size.set(pool_size)
    
    def update_cache_metrics(self, cache_stats: Dict[str, Dict[str, Any]]):
        """Update cache metrics."""
        for cache_type, stats in cache_stats.items():
            if 'hit_ratio' in stats:
                self.cache_hit_ratio.labels(cache_type=cache_type).set(stats['hit_ratio'])
            
            if 'size_bytes' in stats:
                self.cache_size_bytes.labels(cache_type=cache_type).set(stats['size_bytes'])
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    async def start_background_collection(self, interval: int = 30):
        """Start background metrics collection."""
        logger.info(f"Starting background metrics collection (interval: {interval}s)")
        
        while True:
            try:
                self.update_system_metrics()
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in background metrics collection: {e}")
                await asyncio.sleep(interval)


# Global metrics collector instance
metrics_collector = RegulensAIMetricsCollector()
