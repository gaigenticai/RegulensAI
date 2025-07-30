"""
RegulensAI Application Performance Monitoring (APM) Integration
Enterprise-grade APM with multi-provider support, real-time error tracking, and performance regression detection.
"""

import asyncio
import time
import uuid
import traceback
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import structlog
import aiohttp
import asyncpg
from contextlib import asynccontextmanager

from core_infra.config import get_settings
from core_infra.logging.centralized_logging import get_centralized_logger, LogCategory
from core_infra.monitoring.metrics_collector import MetricsCollector
from core_infra.exceptions import SystemException


class APMProvider(str, Enum):
    """Supported APM providers."""
    ELASTIC_APM = "elastic_apm"
    NEW_RELIC = "new_relic"
    DATADOG = "datadog"
    CUSTOM = "custom"


class PerformanceMetricType(str, Enum):
    """Performance metric types."""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DATABASE_QUERY_TIME = "database_query_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    EXTERNAL_API_TIME = "external_api_time"


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    timestamp: datetime
    metric_type: PerformanceMetricType
    value: float
    unit: str
    service: str
    operation: str
    tags: Dict[str, str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ErrorEvent:
    """Error event data structure."""
    timestamp: datetime
    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    service: str
    operation: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    severity: str = "error"
    tags: Dict[str, str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.context is None:
            self.context = {}


@dataclass
class PerformanceBaseline:
    """Performance baseline for regression detection."""
    metric_type: PerformanceMetricType
    service: str
    operation: str
    baseline_value: float
    threshold_percentage: float
    measurement_window: timedelta
    last_updated: datetime
    sample_count: int


class DatabaseQueryTracker:
    """Advanced database query performance tracking."""
    
    def __init__(self):
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'avg_time': 0.0,
            'slow_queries': deque(maxlen=100),
            'errors': 0
        })
        self.slow_query_threshold = 1.0  # seconds
        self.connection_pool_stats = {
            'active_connections': 0,
            'idle_connections': 0,
            'total_connections': 0,
            'connection_errors': 0,
            'connection_timeouts': 0
        }
    
    async def track_query(self, query: str, execution_time: float, error: Optional[Exception] = None):
        """Track database query performance."""
        # Normalize query for grouping
        normalized_query = self._normalize_query(query)
        
        stats = self.query_stats[normalized_query]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['min_time'] = min(stats['min_time'], execution_time)
        stats['max_time'] = max(stats['max_time'], execution_time)
        stats['avg_time'] = stats['total_time'] / stats['count']
        
        if error:
            stats['errors'] += 1
        
        # Track slow queries
        if execution_time > self.slow_query_threshold:
            stats['slow_queries'].append({
                'query': query,
                'execution_time': execution_time,
                'timestamp': datetime.utcnow(),
                'error': str(error) if error else None
            })
    
    def _normalize_query(self, query: str) -> str:
        """Normalize SQL query for grouping similar queries."""
        # Simple normalization - replace parameters with placeholders
        import re
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Replace string literals
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        
        # Replace numeric literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Replace IN clauses with multiple values
        normalized = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', normalized, flags=re.IGNORECASE)
        
        return normalized.upper()
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries across all tracked queries."""
        all_slow_queries = []
        
        for query_pattern, stats in self.query_stats.items():
            for slow_query in stats['slow_queries']:
                all_slow_queries.append({
                    'pattern': query_pattern,
                    **slow_query
                })
        
        # Sort by execution time
        all_slow_queries.sort(key=lambda x: x['execution_time'], reverse=True)
        return all_slow_queries[:limit]
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics."""
        total_queries = sum(stats['count'] for stats in self.query_stats.values())
        total_time = sum(stats['total_time'] for stats in self.query_stats.values())
        total_errors = sum(stats['errors'] for stats in self.query_stats.values())
        
        return {
            'total_queries': total_queries,
            'total_execution_time': total_time,
            'average_query_time': total_time / total_queries if total_queries > 0 else 0,
            'error_rate': total_errors / total_queries if total_queries > 0 else 0,
            'slow_query_count': sum(len(stats['slow_queries']) for stats in self.query_stats.values()),
            'unique_query_patterns': len(self.query_stats),
            'connection_pool': self.connection_pool_stats
        }


class ErrorTracker:
    """Real-time error tracking and aggregation."""
    
    def __init__(self):
        self.error_buffer = deque(maxlen=10000)
        self.error_aggregates = defaultdict(lambda: {
            'count': 0,
            'first_seen': None,
            'last_seen': None,
            'affected_users': set(),
            'affected_tenants': set(),
            'stack_traces': deque(maxlen=10)
        })
        self.error_rate_window = deque(maxlen=300)  # 5 minutes at 1-second intervals
        
    async def track_error(self, error_event: ErrorEvent):
        """Track error event."""
        self.error_buffer.append(error_event)
        
        # Create error signature for aggregation
        error_signature = f"{error_event.error_type}:{error_event.service}:{error_event.operation}"
        
        aggregate = self.error_aggregates[error_signature]
        aggregate['count'] += 1
        
        if aggregate['first_seen'] is None:
            aggregate['first_seen'] = error_event.timestamp
        aggregate['last_seen'] = error_event.timestamp
        
        if error_event.user_id:
            aggregate['affected_users'].add(error_event.user_id)
        if error_event.tenant_id:
            aggregate['affected_tenants'].add(error_event.tenant_id)
        
        aggregate['stack_traces'].append({
            'timestamp': error_event.timestamp,
            'stack_trace': error_event.stack_trace,
            'context': error_event.context
        })
        
        # Update error rate
        self.error_rate_window.append(error_event.timestamp)
        
        # Send to centralized logging
        logger = await get_centralized_logger("error_tracker")
        await logger.error(
            f"Error tracked: {error_event.error_message}",
            category=LogCategory.SYSTEM,
            error_id=error_event.error_id,
            error_type=error_event.error_type,
            service=error_event.service,
            operation=error_event.operation,
            user_id=error_event.user_id,
            tenant_id=error_event.tenant_id,
            request_id=error_event.request_id,
            stack_trace=error_event.stack_trace,
            **error_event.tags
        )
    
    def get_error_rate(self, window_minutes: int = 5) -> float:
        """Get current error rate per minute."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_errors = [ts for ts in self.error_rate_window if ts > cutoff_time]
        return len(recent_errors) / window_minutes
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top errors by frequency."""
        sorted_errors = sorted(
            self.error_aggregates.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        result = []
        for error_signature, aggregate in sorted_errors[:limit]:
            result.append({
                'error_signature': error_signature,
                'count': aggregate['count'],
                'first_seen': aggregate['first_seen'],
                'last_seen': aggregate['last_seen'],
                'affected_users': len(aggregate['affected_users']),
                'affected_tenants': len(aggregate['affected_tenants']),
                'recent_stack_trace': list(aggregate['stack_traces'])[-1] if aggregate['stack_traces'] else None
            })
        
        return result


class PerformanceRegressionDetector:
    """Automated performance regression detection."""
    
    def __init__(self):
        self.baselines = {}
        self.recent_measurements = defaultdict(lambda: deque(maxlen=100))
        self.regression_alerts = deque(maxlen=1000)
        
    def set_baseline(self, baseline: PerformanceBaseline):
        """Set performance baseline."""
        key = f"{baseline.service}:{baseline.operation}:{baseline.metric_type.value}"
        self.baselines[key] = baseline
    
    async def check_performance(self, metric: PerformanceMetric) -> Optional[Dict[str, Any]]:
        """Check if performance metric indicates regression."""
        key = f"{metric.service}:{metric.operation}:{metric.metric_type.value}"
        
        # Store recent measurement
        self.recent_measurements[key].append(metric)
        
        # Check against baseline
        if key in self.baselines:
            baseline = self.baselines[key]
            
            # Calculate recent average
            recent_values = [m.value for m in list(self.recent_measurements[key])[-10:]]
            if len(recent_values) >= 5:  # Need at least 5 measurements
                recent_avg = sum(recent_values) / len(recent_values)
                
                # Check for regression
                threshold = baseline.baseline_value * (1 + baseline.threshold_percentage / 100)
                
                if recent_avg > threshold:
                    regression_alert = {
                        'timestamp': datetime.utcnow(),
                        'service': metric.service,
                        'operation': metric.operation,
                        'metric_type': metric.metric_type.value,
                        'baseline_value': baseline.baseline_value,
                        'current_value': recent_avg,
                        'threshold': threshold,
                        'regression_percentage': ((recent_avg - baseline.baseline_value) / baseline.baseline_value) * 100
                    }
                    
                    self.regression_alerts.append(regression_alert)
                    
                    # Send alert to centralized logging
                    logger = await get_centralized_logger("regression_detector")
                    await logger.warning(
                        f"Performance regression detected: {metric.service}.{metric.operation}",
                        category=LogCategory.PERFORMANCE,
                        **regression_alert
                    )
                    
                    return regression_alert
        
        return None
    
    def update_baseline(self, service: str, operation: str, metric_type: PerformanceMetricType):
        """Update baseline based on recent measurements."""
        key = f"{service}:{operation}:{metric_type.value}"
        
        if key in self.recent_measurements:
            recent_values = [m.value for m in self.recent_measurements[key]]
            
            if len(recent_values) >= 20:  # Need sufficient data
                # Use 95th percentile as baseline
                sorted_values = sorted(recent_values)
                baseline_value = sorted_values[int(len(sorted_values) * 0.95)]
                
                baseline = PerformanceBaseline(
                    metric_type=metric_type,
                    service=service,
                    operation=operation,
                    baseline_value=baseline_value,
                    threshold_percentage=20.0,  # 20% regression threshold
                    measurement_window=timedelta(hours=1),
                    last_updated=datetime.utcnow(),
                    sample_count=len(recent_values)
                )
                
                self.set_baseline(baseline)


class ResourceMonitor:
    """Application-level resource monitoring."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.resource_history = defaultdict(lambda: deque(maxlen=300))  # 5 minutes at 1-second intervals
        
    async def collect_resource_metrics(self) -> Dict[str, float]:
        """Collect current resource metrics."""
        try:
            # CPU metrics
            cpu_percent = self.process.cpu_percent()
            cpu_times = self.process.cpu_times()
            
            # Memory metrics
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # I/O metrics
            io_counters = self.process.io_counters()
            
            # Network metrics (system-wide)
            net_io = psutil.net_io_counters()
            
            # File descriptor count
            num_fds = self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
            
            metrics = {
                'cpu_percent': cpu_percent,
                'cpu_user_time': cpu_times.user,
                'cpu_system_time': cpu_times.system,
                'memory_rss': memory_info.rss / 1024 / 1024,  # MB
                'memory_vms': memory_info.vms / 1024 / 1024,  # MB
                'memory_percent': memory_percent,
                'io_read_bytes': io_counters.read_bytes,
                'io_write_bytes': io_counters.write_bytes,
                'io_read_count': io_counters.read_count,
                'io_write_count': io_counters.write_count,
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv,
                'network_packets_sent': net_io.packets_sent,
                'network_packets_recv': net_io.packets_recv,
                'file_descriptors': num_fds,
                'threads': self.process.num_threads()
            }
            
            # Store in history
            timestamp = datetime.utcnow()
            for metric_name, value in metrics.items():
                self.resource_history[metric_name].append((timestamp, value))
            
            return metrics
            
        except Exception as e:
            logger = await get_centralized_logger("resource_monitor")
            await logger.error(f"Failed to collect resource metrics: {e}")
            return {}
    
    def get_resource_trends(self, metric_name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Get resource trends for a specific metric."""
        if metric_name not in self.resource_history:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_data = [(ts, value) for ts, value in self.resource_history[metric_name] if ts > cutoff_time]
        
        if len(recent_data) < 2:
            return {}
        
        values = [value for _, value in recent_data]
        
        return {
            'current': values[-1],
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'trend': 'increasing' if values[-1] > values[0] else 'decreasing' if values[-1] < values[0] else 'stable'
        }


class APMProviderInterface:
    """Base interface for APM providers."""

    async def initialize(self, config: Dict[str, Any]):
        """Initialize APM provider."""
        raise NotImplementedError

    async def track_transaction(self, name: str, transaction_type: str, duration: float, **kwargs):
        """Track transaction performance."""
        raise NotImplementedError

    async def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track error occurrence."""
        raise NotImplementedError

    async def track_custom_metric(self, name: str, value: float, metric_type: str = "gauge", **kwargs):
        """Track custom metric."""
        raise NotImplementedError

    async def set_user_context(self, user_id: str, email: str = None, username: str = None):
        """Set user context for tracking."""
        raise NotImplementedError

    async def add_custom_data(self, key: str, value: Any):
        """Add custom data to current transaction."""
        raise NotImplementedError


class ElasticAPMProvider(APMProviderInterface):
    """Elastic APM provider implementation."""

    def __init__(self):
        self.client = None
        self.enabled = False

    async def initialize(self, config: Dict[str, Any]):
        """Initialize Elastic APM."""
        try:
            import elasticapm

            self.client = elasticapm.Client(
                service_name=config.get('service_name', 'regulensai'),
                server_url=config.get('server_url', 'http://localhost:8200'),
                secret_token=config.get('secret_token'),
                environment=config.get('environment', 'production'),
                capture_body='all',
                capture_headers=True,
                transaction_sample_rate=config.get('sample_rate', 1.0)
            )

            self.enabled = True

        except ImportError:
            logger = await get_centralized_logger("elastic_apm")
            await logger.warning("Elastic APM not available - install elastic-apm package")
        except Exception as e:
            logger = await get_centralized_logger("elastic_apm")
            await logger.error(f"Failed to initialize Elastic APM: {e}")

    async def track_transaction(self, name: str, transaction_type: str, duration: float, **kwargs):
        """Track transaction in Elastic APM."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.begin_transaction(transaction_type)
            # Simulate transaction duration
            await asyncio.sleep(0.001)  # Minimal delay
            self.client.end_transaction(name, 'success')
        except Exception as e:
            logger = await get_centralized_logger("elastic_apm")
            await logger.error(f"Failed to track transaction in Elastic APM: {e}")

    async def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track error in Elastic APM."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.capture_exception(
                exc_info=(type(error), error, error.__traceback__),
                context=context
            )
        except Exception as e:
            logger = await get_centralized_logger("elastic_apm")
            await logger.error(f"Failed to track error in Elastic APM: {e}")


class NewRelicProvider(APMProviderInterface):
    """New Relic APM provider implementation."""

    def __init__(self):
        self.enabled = False

    async def initialize(self, config: Dict[str, Any]):
        """Initialize New Relic APM."""
        try:
            import newrelic.agent

            newrelic.agent.initialize(
                config_file=config.get('config_file'),
                environment=config.get('environment', 'production')
            )

            self.enabled = True

        except ImportError:
            logger = await get_centralized_logger("newrelic_apm")
            await logger.warning("New Relic not available - install newrelic package")
        except Exception as e:
            logger = await get_centralized_logger("newrelic_apm")
            await logger.error(f"Failed to initialize New Relic: {e}")

    async def track_transaction(self, name: str, transaction_type: str, duration: float, **kwargs):
        """Track transaction in New Relic."""
        if not self.enabled:
            return

        try:
            import newrelic.agent

            @newrelic.agent.function_trace(name=name, group=transaction_type)
            async def tracked_operation():
                await asyncio.sleep(duration / 1000)  # Convert ms to seconds

            await tracked_operation()

        except Exception as e:
            logger = await get_centralized_logger("newrelic_apm")
            await logger.error(f"Failed to track transaction in New Relic: {e}")


class DatadogProvider(APMProviderInterface):
    """Datadog APM provider implementation."""

    def __init__(self):
        self.enabled = False

    async def initialize(self, config: Dict[str, Any]):
        """Initialize Datadog APM."""
        try:
            from ddtrace import tracer, patch_all

            # Auto-patch common libraries
            patch_all()

            # Configure tracer
            tracer.configure(
                hostname=config.get('hostname'),
                port=config.get('port', 8126),
                service=config.get('service_name', 'regulensai'),
                env=config.get('environment', 'production')
            )

            self.tracer = tracer
            self.enabled = True

        except ImportError:
            logger = await get_centralized_logger("datadog_apm")
            await logger.warning("Datadog not available - install ddtrace package")
        except Exception as e:
            logger = await get_centralized_logger("datadog_apm")
            await logger.error(f"Failed to initialize Datadog: {e}")

    async def track_transaction(self, name: str, transaction_type: str, duration: float, **kwargs):
        """Track transaction in Datadog."""
        if not self.enabled:
            return

        try:
            with self.tracer.trace(name, service=transaction_type) as span:
                span.set_tag('duration_ms', duration)
                for key, value in kwargs.items():
                    span.set_tag(key, value)
                await asyncio.sleep(0.001)  # Minimal delay

        except Exception as e:
            logger = await get_centralized_logger("datadog_apm")
            await logger.error(f"Failed to track transaction in Datadog: {e}")


class CustomAPMProvider(APMProviderInterface):
    """Custom APM provider for RegulensAI-specific metrics."""

    def __init__(self):
        self.metrics_collector = None
        self.enabled = False

    async def initialize(self, config: Dict[str, Any]):
        """Initialize custom APM provider."""
        try:
            self.metrics_collector = MetricsCollector()
            self.enabled = True

        except Exception as e:
            logger = await get_centralized_logger("custom_apm")
            await logger.error(f"Failed to initialize custom APM: {e}")

    async def track_transaction(self, name: str, transaction_type: str, duration: float, **kwargs):
        """Track transaction in custom metrics."""
        if not self.enabled or not self.metrics_collector:
            return

        try:
            # Record transaction metrics
            self.metrics_collector.api_request_duration.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=name,
                status_code=kwargs.get('status_code', '200')
            ).observe(duration / 1000)  # Convert ms to seconds

            self.metrics_collector.api_requests_total.labels(
                method=kwargs.get('method', 'unknown'),
                endpoint=name,
                status_code=kwargs.get('status_code', '200')
            ).inc()

        except Exception as e:
            logger = await get_centralized_logger("custom_apm")
            await logger.error(f"Failed to track transaction in custom APM: {e}")

    async def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track error in custom metrics."""
        if not self.enabled or not self.metrics_collector:
            return

        try:
            self.metrics_collector.api_errors_total.labels(
                error_type=type(error).__name__,
                service=context.get('service', 'unknown') if context else 'unknown'
            ).inc()

        except Exception as e:
            logger = await get_centralized_logger("custom_apm")
            await logger.error(f"Failed to track error in custom APM: {e}")


class APMManager:
    """
    Central APM manager coordinating multiple APM providers and performance monitoring.
    """

    def __init__(self):
        self.settings = get_settings()
        self.providers = {}
        self.database_tracker = DatabaseQueryTracker()
        self.error_tracker = ErrorTracker()
        self.regression_detector = PerformanceRegressionDetector()
        self.resource_monitor = ResourceMonitor()
        self.running = False

        # Performance monitoring tasks
        self._monitoring_tasks = []

        # Business metrics tracking
        self.business_metrics = {
            'compliance_processing_times': deque(maxlen=1000),
            'regulatory_data_ingestion_rates': deque(maxlen=1000),
            'user_session_durations': deque(maxlen=1000),
            'api_response_times': deque(maxlen=1000)
        }

    async def initialize(self):
        """Initialize APM manager and all configured providers."""
        try:
            # Initialize configured providers
            await self._initialize_providers()

            # Start monitoring tasks
            await self._start_monitoring_tasks()

            self.running = True

            logger = await get_centralized_logger("apm_manager")
            await logger.info("APM Manager initialized successfully",
                            category=LogCategory.SYSTEM,
                            providers=list(self.providers.keys()))

        except Exception as e:
            logger = await get_centralized_logger("apm_manager")
            await logger.error(f"APM Manager initialization failed: {e}",
                             category=LogCategory.SYSTEM)
            raise SystemException(f"APM initialization failed: {e}")

    async def shutdown(self):
        """Shutdown APM manager and cleanup resources."""
        self.running = False

        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger = await get_centralized_logger("apm_manager")
        await logger.info("APM Manager shutdown completed", category=LogCategory.SYSTEM)

    async def _initialize_providers(self):
        """Initialize all configured APM providers."""
        # Elastic APM
        if getattr(self.settings, 'elastic_apm_enabled', False):
            provider = ElasticAPMProvider()
            await provider.initialize({
                'service_name': getattr(self.settings, 'elastic_apm_service_name', 'regulensai'),
                'server_url': getattr(self.settings, 'elastic_apm_server_url', 'http://localhost:8200'),
                'secret_token': getattr(self.settings, 'elastic_apm_secret_token', None),
                'environment': getattr(self.settings, 'app_environment', 'production'),
                'sample_rate': getattr(self.settings, 'elastic_apm_sample_rate', 1.0)
            })
            self.providers[APMProvider.ELASTIC_APM] = provider

        # New Relic
        if getattr(self.settings, 'newrelic_enabled', False):
            provider = NewRelicProvider()
            await provider.initialize({
                'config_file': getattr(self.settings, 'newrelic_config_file', None),
                'environment': getattr(self.settings, 'app_environment', 'production')
            })
            self.providers[APMProvider.NEW_RELIC] = provider

        # Datadog
        if getattr(self.settings, 'datadog_apm_enabled', False):
            provider = DatadogProvider()
            await provider.initialize({
                'hostname': getattr(self.settings, 'datadog_hostname', None),
                'port': getattr(self.settings, 'datadog_port', 8126),
                'service_name': getattr(self.settings, 'datadog_service_name', 'regulensai'),
                'environment': getattr(self.settings, 'app_environment', 'production')
            })
            self.providers[APMProvider.DATADOG] = provider

        # Custom APM (always enabled)
        provider = CustomAPMProvider()
        await provider.initialize({})
        self.providers[APMProvider.CUSTOM] = provider

    async def _start_monitoring_tasks(self):
        """Start background monitoring tasks."""
        # Resource monitoring task
        self._monitoring_tasks.append(
            asyncio.create_task(self._resource_monitoring_loop())
        )

        # Performance baseline update task
        self._monitoring_tasks.append(
            asyncio.create_task(self._baseline_update_loop())
        )

        # Error rate monitoring task
        self._monitoring_tasks.append(
            asyncio.create_task(self._error_rate_monitoring_loop())
        )

    async def _resource_monitoring_loop(self):
        """Background task for resource monitoring."""
        while self.running:
            try:
                metrics = await self.resource_monitor.collect_resource_metrics()

                # Track resource metrics in APM providers
                for provider in self.providers.values():
                    if hasattr(provider, 'track_custom_metric'):
                        for metric_name, value in metrics.items():
                            await provider.track_custom_metric(
                                f"resource.{metric_name}",
                                value,
                                metric_type="gauge"
                            )

                # Check for resource alerts
                await self._check_resource_alerts(metrics)

                await asyncio.sleep(30)  # Collect every 30 seconds

            except Exception as e:
                logger = await get_centralized_logger("apm_manager")
                await logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _baseline_update_loop(self):
        """Background task for updating performance baselines."""
        while self.running:
            try:
                # Update baselines for key operations
                operations = [
                    ('api', 'get_regulations', PerformanceMetricType.RESPONSE_TIME),
                    ('api', 'create_compliance_report', PerformanceMetricType.RESPONSE_TIME),
                    ('database', 'query_regulations', PerformanceMetricType.DATABASE_QUERY_TIME),
                    ('cache', 'get_cached_data', PerformanceMetricType.CACHE_HIT_RATE)
                ]

                for service, operation, metric_type in operations:
                    self.regression_detector.update_baseline(service, operation, metric_type)

                await asyncio.sleep(3600)  # Update every hour

            except Exception as e:
                logger = await get_centralized_logger("apm_manager")
                await logger.error(f"Baseline update error: {e}")
                await asyncio.sleep(3600)

    async def _error_rate_monitoring_loop(self):
        """Background task for monitoring error rates."""
        while self.running:
            try:
                error_rate = self.error_tracker.get_error_rate()

                # Alert if error rate is too high
                if error_rate > 10:  # More than 10 errors per minute
                    logger = await get_centralized_logger("apm_manager")
                    await logger.critical(
                        f"High error rate detected: {error_rate:.2f} errors/minute",
                        category=LogCategory.SYSTEM,
                        error_rate=error_rate,
                        top_errors=self.error_tracker.get_top_errors(5)
                    )

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger = await get_centralized_logger("apm_manager")
                await logger.error(f"Error rate monitoring error: {e}")
                await asyncio.sleep(60)

    async def _check_resource_alerts(self, metrics: Dict[str, float]):
        """Check resource metrics for alert conditions."""
        alerts = []

        # CPU usage alert
        if metrics.get('cpu_percent', 0) > 80:
            alerts.append({
                'type': 'high_cpu_usage',
                'value': metrics['cpu_percent'],
                'threshold': 80
            })

        # Memory usage alert
        if metrics.get('memory_percent', 0) > 85:
            alerts.append({
                'type': 'high_memory_usage',
                'value': metrics['memory_percent'],
                'threshold': 85
            })

        # File descriptor alert
        if metrics.get('file_descriptors', 0) > 1000:
            alerts.append({
                'type': 'high_file_descriptor_usage',
                'value': metrics['file_descriptors'],
                'threshold': 1000
            })

        # Send alerts
        if alerts:
            logger = await get_centralized_logger("apm_manager")
            await logger.warning(
                "Resource usage alerts triggered",
                category=LogCategory.PERFORMANCE,
                alerts=alerts,
                all_metrics=metrics
            )

    @asynccontextmanager
    async def track_operation(
        self,
        operation_name: str,
        operation_type: str = "api",
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **context
    ):
        """Context manager for tracking operation performance."""
        start_time = time.time()
        error_occurred = None

        try:
            yield

        except Exception as e:
            error_occurred = e

            # Track error
            error_event = ErrorEvent(
                timestamp=datetime.utcnow(),
                error_id=str(uuid.uuid4()),
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                service=operation_type,
                operation=operation_name,
                user_id=user_id,
                tenant_id=tenant_id,
                context=context
            )

            await self.error_tracker.track_error(error_event)

            # Track error in APM providers
            for provider in self.providers.values():
                await provider.track_error(e, context)

            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Track performance metric
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                value=duration_ms,
                unit="milliseconds",
                service=operation_type,
                operation=operation_name,
                tags={
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'success': str(error_occurred is None)
                },
                metadata=context
            )

            # Check for performance regression
            await self.regression_detector.check_performance(metric)

            # Track in APM providers
            for provider in self.providers.values():
                await provider.track_transaction(
                    operation_name,
                    operation_type,
                    duration_ms,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    success=error_occurred is None,
                    **context
                )

    async def track_database_query(self, query: str, execution_time: float, error: Optional[Exception] = None):
        """Track database query performance."""
        await self.database_tracker.track_query(query, execution_time, error)

        # Track in APM providers
        for provider in self.providers.values():
            if hasattr(provider, 'track_custom_metric'):
                await provider.track_custom_metric(
                    "database.query_time",
                    execution_time,
                    metric_type="histogram",
                    query_type=self.database_tracker._normalize_query(query)[:50],
                    success=str(error is None)
                )

    async def track_business_metric(self, metric_name: str, value: float, **tags):
        """Track RegulensAI-specific business metrics."""
        if metric_name in self.business_metrics:
            self.business_metrics[metric_name].append({
                'timestamp': datetime.utcnow(),
                'value': value,
                'tags': tags
            })

        # Track in APM providers
        for provider in self.providers.values():
            if hasattr(provider, 'track_custom_metric'):
                await provider.track_custom_metric(
                    f"business.{metric_name}",
                    value,
                    metric_type="gauge",
                    **tags
                )

        # Send to centralized logging
        logger = await get_centralized_logger("apm_manager")
        await logger.info(
            f"Business metric tracked: {metric_name}",
            category=LogCategory.PERFORMANCE,
            metric_name=metric_name,
            value=value,
            **tags
        )

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            'database_stats': self.database_tracker.get_query_statistics(),
            'error_stats': {
                'error_rate': self.error_tracker.get_error_rate(),
                'top_errors': self.error_tracker.get_top_errors(10),
                'total_errors': len(self.error_tracker.error_buffer)
            },
            'resource_stats': await self.resource_monitor.collect_resource_metrics(),
            'business_metrics': {
                name: {
                    'count': len(metrics),
                    'latest': metrics[-1] if metrics else None,
                    'avg_last_hour': self._calculate_avg_last_hour(metrics)
                }
                for name, metrics in self.business_metrics.items()
            },
            'regression_alerts': list(self.regression_detector.regression_alerts)[-10:],  # Last 10 alerts
            'active_providers': list(self.providers.keys())
        }

    def _calculate_avg_last_hour(self, metrics: deque) -> Optional[float]:
        """Calculate average value for metrics in the last hour."""
        if not metrics:
            return None

        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_metrics = [
            m for m in metrics
            if isinstance(m, dict) and m.get('timestamp', datetime.min) > cutoff_time
        ]

        if not recent_metrics:
            return None

        values = [m['value'] for m in recent_metrics if 'value' in m]
        return sum(values) / len(values) if values else None


# Global APM manager instance
apm_manager = APMManager()


# Convenience functions and decorators
async def init_apm():
    """Initialize APM system."""
    await apm_manager.initialize()


async def shutdown_apm():
    """Shutdown APM system."""
    await apm_manager.shutdown()


def track_performance(operation_name: str, operation_type: str = "api"):
    """Decorator for automatic performance tracking."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with apm_manager.track_operation(operation_name, operation_type):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to handle differently
                # This is a simplified version - in production, you'd want proper sync support
                return func(*args, **kwargs)
            return sync_wrapper

    return decorator


async def track_database_operation(query: str, execution_time: float, error: Optional[Exception] = None):
    """Track database operation performance."""
    await apm_manager.track_database_query(query, execution_time, error)


async def track_compliance_processing_time(processing_time: float, regulation_type: str, tenant_id: str):
    """Track compliance processing time business metric."""
    await apm_manager.track_business_metric(
        'compliance_processing_times',
        processing_time,
        regulation_type=regulation_type,
        tenant_id=tenant_id
    )


async def track_regulatory_data_ingestion(records_processed: int, source: str, duration: float):
    """Track regulatory data ingestion rate business metric."""
    rate = records_processed / duration if duration > 0 else 0
    await apm_manager.track_business_metric(
        'regulatory_data_ingestion_rates',
        rate,
        source=source,
        records_processed=records_processed,
        duration=duration
    )


async def track_user_session_duration(duration: float, user_id: str, tenant_id: str):
    """Track user session duration business metric."""
    await apm_manager.track_business_metric(
        'user_session_durations',
        duration,
        user_id=user_id,
        tenant_id=tenant_id
    )


async def track_api_response_time(endpoint: str, method: str, response_time: float, status_code: int):
    """Track API response time business metric."""
    await apm_manager.track_business_metric(
        'api_response_times',
        response_time,
        endpoint=endpoint,
        method=method,
        status_code=str(status_code)
    )


# Database query tracking context manager
@asynccontextmanager
async def track_db_query(query: str):
    """Context manager for tracking database queries."""
    start_time = time.time()
    error_occurred = None

    try:
        yield
    except Exception as e:
        error_occurred = e
        raise
    finally:
        execution_time = time.time() - start_time
        await track_database_operation(query, execution_time, error_occurred)


# Custom APM decorators for RegulensAI operations
def track_compliance_operation(operation_name: str):
    """Decorator for tracking compliance operations."""
    return track_performance(operation_name, "compliance")


def track_regulatory_operation(operation_name: str):
    """Decorator for tracking regulatory operations."""
    return track_performance(operation_name, "regulatory")


def track_api_operation(operation_name: str):
    """Decorator for tracking API operations."""
    return track_performance(operation_name, "api")


def track_database_operation_decorator(operation_name: str):
    """Decorator for tracking database operations."""
    return track_performance(operation_name, "database")


# Error tracking utilities
async def track_error(error: Exception, context: Dict[str, Any] = None):
    """Track error occurrence."""
    error_event = ErrorEvent(
        timestamp=datetime.utcnow(),
        error_id=str(uuid.uuid4()),
        error_type=type(error).__name__,
        error_message=str(error),
        stack_trace=traceback.format_exc(),
        service=context.get('service', 'unknown') if context else 'unknown',
        operation=context.get('operation', 'unknown') if context else 'unknown',
        user_id=context.get('user_id') if context else None,
        tenant_id=context.get('tenant_id') if context else None,
        request_id=context.get('request_id') if context else None,
        context=context or {}
    )

    await apm_manager.error_tracker.track_error(error_event)


# Performance monitoring utilities
async def get_performance_summary() -> Dict[str, Any]:
    """Get comprehensive performance summary."""
    return await apm_manager.get_performance_summary()


async def get_database_performance() -> Dict[str, Any]:
    """Get database performance statistics."""
    return apm_manager.database_tracker.get_query_statistics()


async def get_error_statistics() -> Dict[str, Any]:
    """Get error tracking statistics."""
    return {
        'error_rate': apm_manager.error_tracker.get_error_rate(),
        'top_errors': apm_manager.error_tracker.get_top_errors(10),
        'total_errors': len(apm_manager.error_tracker.error_buffer)
    }


async def get_resource_metrics() -> Dict[str, float]:
    """Get current resource metrics."""
    return await apm_manager.resource_monitor.collect_resource_metrics()
