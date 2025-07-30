"""
Training Portal Performance Monitoring Service
Comprehensive performance monitoring and optimization for training portal.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
from contextlib import asynccontextmanager
import structlog
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from core_infra.utils.metrics import MetricsCollector
from core_infra.database.connection import get_db_session
from core_infra.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestMetrics:
    """Request-level performance metrics."""
    endpoint: str
    method: str
    duration: float
    status_code: int
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    cache_hit: bool = False
    db_queries: int = 0
    db_time: float = 0.0
    memory_usage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TrainingPerformanceService:
    """Advanced performance monitoring service for training portal."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.request_metrics = deque(maxlen=10000)  # Keep last 10k requests
        self.endpoint_stats = defaultdict(list)
        self.user_stats = defaultdict(list)
        self.performance_thresholds = {
            'api_response_time': 2.0,  # seconds
            'db_query_time': 0.5,      # seconds
            'cache_hit_rate': 0.8,     # 80%
            'memory_usage': 512,       # MB
            'concurrent_users': 1000
        }
        
        # Performance alerts
        self.alert_callbacks = []
        self.performance_issues = deque(maxlen=1000)
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback for performance alerts."""
        self.alert_callbacks.append(callback)
    
    async def record_request_metrics(self, metrics: RequestMetrics):
        """Record metrics for a request."""
        try:
            self.request_metrics.append(metrics)
            self.endpoint_stats[f"{metrics.method} {metrics.endpoint}"].append(metrics.duration)
            
            if metrics.user_id:
                self.user_stats[metrics.user_id].append(metrics.duration)
            
            # Check for performance issues
            await self._check_performance_thresholds(metrics)
            
            # Send to metrics collector
            await self.metrics_collector.record_metric(
                name="training_portal_request_duration",
                value=metrics.duration,
                tags={
                    "endpoint": metrics.endpoint,
                    "method": metrics.method,
                    "status_code": str(metrics.status_code),
                    "cache_hit": str(metrics.cache_hit)
                }
            )
            
        except Exception as e:
            logger.error("Failed to record request metrics", error=str(e))
    
    async def _check_performance_thresholds(self, metrics: RequestMetrics):
        """Check if metrics exceed performance thresholds."""
        issues = []
        
        if metrics.duration > self.performance_thresholds['api_response_time']:
            issues.append({
                'type': 'slow_response',
                'endpoint': metrics.endpoint,
                'duration': metrics.duration,
                'threshold': self.performance_thresholds['api_response_time']
            })
        
        if metrics.db_time > self.performance_thresholds['db_query_time']:
            issues.append({
                'type': 'slow_db_query',
                'endpoint': metrics.endpoint,
                'db_time': metrics.db_time,
                'threshold': self.performance_thresholds['db_query_time']
            })
        
        if metrics.memory_usage > self.performance_thresholds['memory_usage']:
            issues.append({
                'type': 'high_memory_usage',
                'endpoint': metrics.endpoint,
                'memory_usage': metrics.memory_usage,
                'threshold': self.performance_thresholds['memory_usage']
            })
        
        for issue in issues:
            issue['timestamp'] = datetime.utcnow()
            issue['user_id'] = metrics.user_id
            issue['tenant_id'] = metrics.tenant_id
            
            self.performance_issues.append(issue)
            
            # Trigger alerts
            for callback in self.alert_callbacks:
                try:
                    await callback(issue)
                except Exception as e:
                    logger.error("Alert callback failed", error=str(e))
    
    async def get_performance_summary(self, time_window: timedelta = None) -> Dict[str, Any]:
        """Get performance summary for the specified time window."""
        try:
            if time_window is None:
                time_window = timedelta(hours=1)
            
            cutoff_time = datetime.utcnow() - time_window
            recent_metrics = [
                m for m in self.request_metrics 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"message": "No metrics available for the specified time window"}
            
            # Calculate summary statistics
            durations = [m.duration for m in recent_metrics]
            cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
            db_times = [m.db_time for m in recent_metrics if m.db_time > 0]
            
            summary = {
                'time_window': str(time_window),
                'total_requests': len(recent_metrics),
                'avg_response_time': statistics.mean(durations),
                'median_response_time': statistics.median(durations),
                'p95_response_time': self._percentile(durations, 95),
                'p99_response_time': self._percentile(durations, 99),
                'cache_hit_rate': cache_hits / len(recent_metrics) if recent_metrics else 0,
                'avg_db_time': statistics.mean(db_times) if db_times else 0,
                'total_db_queries': sum(m.db_queries for m in recent_metrics),
                'error_rate': sum(1 for m in recent_metrics if m.status_code >= 400) / len(recent_metrics),
                'unique_users': len(set(m.user_id for m in recent_metrics if m.user_id)),
                'unique_tenants': len(set(m.tenant_id for m in recent_metrics if m.tenant_id))
            }
            
            # Endpoint breakdown
            endpoint_breakdown = {}
            for endpoint, times in self.endpoint_stats.items():
                recent_times = [t for t in times[-100:]]  # Last 100 requests per endpoint
                if recent_times:
                    endpoint_breakdown[endpoint] = {
                        'avg_time': statistics.mean(recent_times),
                        'request_count': len(recent_times),
                        'p95_time': self._percentile(recent_times, 95)
                    }
            
            summary['endpoint_breakdown'] = endpoint_breakdown
            
            # Recent performance issues
            recent_issues = [
                issue for issue in self.performance_issues
                if issue['timestamp'] >= cutoff_time
            ]
            summary['recent_issues'] = recent_issues[-10:]  # Last 10 issues
            
            return summary
            
        except Exception as e:
            logger.error("Failed to get performance summary", error=str(e))
            return {"error": "Failed to generate performance summary"}
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    async def get_slow_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest endpoints."""
        try:
            endpoint_averages = []
            for endpoint, times in self.endpoint_stats.items():
                if times:
                    recent_times = times[-100:]  # Last 100 requests
                    avg_time = statistics.mean(recent_times)
                    endpoint_averages.append({
                        'endpoint': endpoint,
                        'avg_response_time': avg_time,
                        'request_count': len(recent_times),
                        'p95_response_time': self._percentile(recent_times, 95)
                    })
            
            # Sort by average response time
            endpoint_averages.sort(key=lambda x: x['avg_response_time'], reverse=True)
            return endpoint_averages[:limit]
            
        except Exception as e:
            logger.error("Failed to get slow endpoints", error=str(e))
            return []
    
    async def get_user_performance_stats(self, user_id: str) -> Dict[str, Any]:
        """Get performance statistics for a specific user."""
        try:
            user_metrics = [
                m for m in self.request_metrics 
                if m.user_id == user_id and m.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            if not user_metrics:
                return {"message": "No metrics available for this user"}
            
            durations = [m.duration for m in user_metrics]
            
            return {
                'user_id': user_id,
                'total_requests': len(user_metrics),
                'avg_response_time': statistics.mean(durations),
                'median_response_time': statistics.median(durations),
                'cache_hit_rate': sum(1 for m in user_metrics if m.cache_hit) / len(user_metrics),
                'error_rate': sum(1 for m in user_metrics if m.status_code >= 400) / len(user_metrics),
                'most_used_endpoints': self._get_top_endpoints_for_user(user_metrics)
            }
            
        except Exception as e:
            logger.error("Failed to get user performance stats", user_id=user_id, error=str(e))
            return {"error": "Failed to get user performance statistics"}
    
    def _get_top_endpoints_for_user(self, user_metrics: List[RequestMetrics]) -> List[Dict[str, Any]]:
        """Get most frequently used endpoints for a user."""
        endpoint_counts = defaultdict(int)
        for metric in user_metrics:
            endpoint_counts[f"{metric.method} {metric.endpoint}"] += 1
        
        sorted_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"endpoint": endpoint, "count": count} for endpoint, count in sorted_endpoints[:5]]
    
    async def optimize_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations."""
        try:
            recommendations = []
            
            # Analyze recent performance data
            recent_metrics = [
                m for m in self.request_metrics 
                if m.timestamp >= datetime.utcnow() - timedelta(hours=1)
            ]
            
            if not recent_metrics:
                return recommendations
            
            # Check cache hit rate
            cache_hit_rate = sum(1 for m in recent_metrics if m.cache_hit) / len(recent_metrics)
            if cache_hit_rate < self.performance_thresholds['cache_hit_rate']:
                recommendations.append({
                    'type': 'caching',
                    'priority': 'high',
                    'description': f'Cache hit rate is {cache_hit_rate:.2%}, below threshold of {self.performance_thresholds["cache_hit_rate"]:.2%}',
                    'suggestion': 'Consider implementing more aggressive caching strategies for frequently accessed data'
                })
            
            # Check for slow endpoints
            slow_endpoints = await self.get_slow_endpoints(5)
            if slow_endpoints and slow_endpoints[0]['avg_response_time'] > self.performance_thresholds['api_response_time']:
                recommendations.append({
                    'type': 'endpoint_optimization',
                    'priority': 'medium',
                    'description': f'Slowest endpoint: {slow_endpoints[0]["endpoint"]} ({slow_endpoints[0]["avg_response_time"]:.2f}s)',
                    'suggestion': 'Optimize database queries, add caching, or implement pagination for this endpoint'
                })
            
            # Check database performance
            db_times = [m.db_time for m in recent_metrics if m.db_time > 0]
            if db_times and statistics.mean(db_times) > self.performance_thresholds['db_query_time']:
                recommendations.append({
                    'type': 'database',
                    'priority': 'high',
                    'description': f'Average database query time is {statistics.mean(db_times):.2f}s',
                    'suggestion': 'Review database indexes, optimize queries, or consider read replicas'
                })
            
            # Check error rates
            error_rate = sum(1 for m in recent_metrics if m.status_code >= 400) / len(recent_metrics)
            if error_rate > 0.05:  # 5% error rate threshold
                recommendations.append({
                    'type': 'error_handling',
                    'priority': 'high',
                    'description': f'Error rate is {error_rate:.2%}',
                    'suggestion': 'Investigate and fix the root causes of errors to improve user experience'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to generate optimization recommendations", error=str(e))
            return []


@asynccontextmanager
async def performance_monitor(
    endpoint: str,
    method: str = "GET",
    user_id: str = None,
    tenant_id: str = None,
    performance_service: TrainingPerformanceService = None
):
    """Context manager for monitoring request performance."""
    start_time = time.time()
    db_start_time = time.time()
    db_queries = 0
    
    try:
        yield
        status_code = 200
    except Exception as e:
        status_code = 500
        raise
    finally:
        end_time = time.time()
        duration = end_time - start_time
        
        if performance_service:
            metrics = RequestMetrics(
                endpoint=endpoint,
                method=method,
                duration=duration,
                status_code=status_code,
                user_id=user_id,
                tenant_id=tenant_id,
                db_time=end_time - db_start_time,
                db_queries=db_queries
            )
            
            await performance_service.record_request_metrics(metrics)


def monitor_performance(
    endpoint: str = None,
    method: str = "GET",
    performance_service: TrainingPerformanceService = None
):
    """Decorator for monitoring function performance."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            endpoint_name = endpoint or f"{func.__module__}.{func.__name__}"
            
            async with performance_monitor(
                endpoint=endpoint_name,
                method=method,
                performance_service=performance_service
            ):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global performance service instance
training_performance_service = TrainingPerformanceService()
