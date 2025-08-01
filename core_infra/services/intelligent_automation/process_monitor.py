"""Process Monitor for Intelligent Automation

This module provides real-time monitoring and analytics for automated processes,
ensuring compliance and performance optimization.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import statistics
import uuid

from core_infra.config import settings
from core_infra.exceptions import SystemException
from core_infra.monitoring.observability import monitor_performance

logger = logging.getLogger(__name__)


class ProcessHealth(Enum):
    """Process health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of process metrics."""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    QUEUE_DEPTH = "queue_depth"


class ProcessMonitor:
    """
    Real-time process monitoring and analytics service.
    
    Features:
    - Real-time performance monitoring
    - Anomaly detection
    - Alert generation and management
    - Historical analytics
    - Resource optimization recommendations
    """
    
    def __init__(self):
        """Initialize process monitor."""
        self.active_monitors = {}
        self.metrics_buffer = []
        self.alerts = {}
        self.thresholds = {
            'execution_time': {'warning': 300, 'critical': 600},
            'success_rate': {'warning': 0.95, 'critical': 0.90},
            'error_rate': {'warning': 0.05, 'critical': 0.10},
            'throughput': {'warning': 10, 'critical': 5},
            'queue_depth': {'warning': 100, 'critical': 500}
        }
        self._background_tasks_started = False
        logger.info("Process monitor initialized")

    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        if self._background_tasks_started:
            return
        try:
            # Only start tasks if we're in an async context
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._metrics_aggregator())
            asyncio.create_task(self._anomaly_detector())
            self._background_tasks_started = True
        except RuntimeError:
            # No event loop running, tasks will be started later
            pass
    
    @monitor_performance
    async def start_monitoring(self, process_id: str, config: Dict[str, Any] = None) -> bool:
        """Start monitoring a process."""
        try:
            if process_id in self.active_monitors:
                logger.warning(f"Process {process_id} is already being monitored")
                return True
            
            self.active_monitors[process_id] = {
                'process_id': process_id,
                'started_at': datetime.utcnow(),
                'config': config or {},
                'metrics': [],
                'health': ProcessHealth.UNKNOWN
            }
            
            logger.info(f"Started monitoring process: {process_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise SystemException(f"Failed to start monitoring: {str(e)}")
    
    async def stop_monitoring(self, process_id: str) -> bool:
        """Stop monitoring a process."""
        if process_id not in self.active_monitors:
            return False
        
        del self.active_monitors[process_id]
        self.alerts = {k: v for k, v in self.alerts.items() if v.get('process_id') != process_id}
        
        logger.info(f"Stopped monitoring process: {process_id}")
        return True
    
    async def record_execution(
        self,
        process_id: str,
        execution_id: str,
        status: str,
        duration_seconds: float,
        resource_usage: Dict[str, float] = None
    ):
        """Record a process execution."""
        if process_id not in self.active_monitors:
            await self.start_monitoring(process_id)
        
        metric = {
            'process_id': process_id,
            'execution_id': execution_id,
            'timestamp': datetime.utcnow(),
            'status': status,
            'duration_seconds': duration_seconds,
            'resource_usage': resource_usage or {}
        }
        
        self.metrics_buffer.append(metric)
        
        monitor = self.active_monitors[process_id]
        monitor['metrics'].append(metric)
        
        # Limit in-memory metrics
        if len(monitor['metrics']) > 1000:
            monitor['metrics'] = monitor['metrics'][-1000:]
    
    async def get_process_health(self, process_id: str) -> Dict[str, Any]:
        """Get current health status of a process."""
        if process_id not in self.active_monitors:
            return {
                'process_id': process_id,
                'health': ProcessHealth.UNKNOWN.value,
                'message': 'Process not monitored'
            }
        
        monitor = self.active_monitors[process_id]
        metrics = self._calculate_current_metrics(process_id)
        health = self._determine_health(metrics)
        
        return {
            'process_id': process_id,
            'health': health.value,
            'metrics': metrics,
            'monitoring_duration': (datetime.utcnow() - monitor['started_at']).total_seconds(),
            'active_alerts': len([a for a in self.alerts.values() if a.get('process_id') == process_id and not a.get('resolved')])
        }
    
    async def get_process_metrics(
        self,
        process_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get detailed metrics for a process."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()
        
        if process_id not in self.active_monitors:
            return {'process_id': process_id, 'error': 'Process not monitored'}
        
        monitor = self.active_monitors[process_id]
        
        # Filter metrics by time range
        filtered_metrics = [
            m for m in monitor['metrics']
            if start_time <= m['timestamp'] <= end_time
        ]
        
        if not filtered_metrics:
            return {
                'process_id': process_id,
                'execution_count': 0,
                'success_rate': 0,
                'average_duration': 0,
                'error_rate': 0
            }
        
        # Calculate aggregated metrics
        execution_count = len(filtered_metrics)
        success_count = sum(1 for m in filtered_metrics if m['status'] == 'success')
        
        durations = [m['duration_seconds'] for m in filtered_metrics]
        avg_duration = statistics.mean(durations) if durations else 0
        
        time_range = (end_time - start_time).total_seconds()
        throughput = execution_count / (time_range / 60) if time_range > 0 else 0
        
        error_rate = (execution_count - success_count) / execution_count if execution_count > 0 else 0
        
        return {
            'process_id': process_id,
            'timestamp': end_time,
            'execution_count': execution_count,
            'success_count': success_count,
            'success_rate': success_count / execution_count if execution_count > 0 else 0,
            'average_duration': avg_duration,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'throughput': throughput,
            'error_rate': error_rate
        }
    
    def _calculate_current_metrics(self, process_id: str) -> Dict[str, Any]:
        """Calculate current metrics from in-memory data."""
        if process_id not in self.active_monitors:
            return {}
        
        monitor = self.active_monitors[process_id]
        recent_metrics = monitor['metrics'][-100:]  # Last 100 executions
        
        if not recent_metrics:
            return {
                'execution_count': 0,
                'success_rate': 0,
                'error_rate': 0,
                'average_duration': 0,
                'throughput': 0
            }
        
        execution_count = len(recent_metrics)
        success_count = sum(1 for m in recent_metrics if m['status'] == 'success')
        
        durations = [m['duration_seconds'] for m in recent_metrics]
        avg_duration = statistics.mean(durations)
        
        # Calculate throughput
        if len(recent_metrics) > 1:
            time_range = (recent_metrics[-1]['timestamp'] - recent_metrics[0]['timestamp']).total_seconds()
            throughput = execution_count / (time_range / 60) if time_range > 0 else 0
        else:
            throughput = 0
        
        return {
            'execution_count': execution_count,
            'success_rate': success_count / execution_count if execution_count > 0 else 0,
            'error_rate': (execution_count - success_count) / execution_count if execution_count > 0 else 0,
            'average_duration': avg_duration,
            'throughput': throughput
        }
    
    def _determine_health(self, metrics: Dict[str, Any]) -> ProcessHealth:
        """Determine process health based on metrics."""
        if not metrics or metrics.get('execution_count', 0) == 0:
            return ProcessHealth.UNKNOWN
        
        issues = 0
        
        # Check success rate
        if metrics.get('success_rate', 0) < self.thresholds['success_rate']['critical']:
            issues += 2
        elif metrics.get('success_rate', 0) < self.thresholds['success_rate']['warning']:
            issues += 1
        
        # Check error rate
        if metrics.get('error_rate', 0) > self.thresholds['error_rate']['critical']:
            issues += 2
        elif metrics.get('error_rate', 0) > self.thresholds['error_rate']['warning']:
            issues += 1
        
        # Check execution time
        if metrics.get('average_duration', 0) > self.thresholds['execution_time']['critical']:
            issues += 2
        elif metrics.get('average_duration', 0) > self.thresholds['execution_time']['warning']:
            issues += 1
        
        # Determine health
        if issues >= 4:
            return ProcessHealth.CRITICAL
        elif issues >= 2:
            return ProcessHealth.WARNING
        else:
            return ProcessHealth.HEALTHY
    
    async def _metrics_aggregator(self):
        """Background task to aggregate and persist metrics."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                if self.metrics_buffer:
                    # In production, save to database
                    logger.info(f"Aggregated {len(self.metrics_buffer)} metrics")
                    self.metrics_buffer.clear()
                    
            except Exception as e:
                logger.error(f"Metrics aggregation failed: {e}")
    
    async def _anomaly_detector(self):
        """Background task to detect anomalies in process metrics."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                for process_id in list(self.active_monitors.keys()):
                    metrics = self._calculate_current_metrics(process_id)
                    
                    # Check thresholds and create alerts
                    await self._check_thresholds(process_id, metrics)
                    
            except Exception as e:
                logger.error(f"Anomaly detection failed: {e}")
    
    async def _check_thresholds(self, process_id: str, metrics: Dict[str, Any]):
        """Check if metrics exceed defined thresholds."""
        # Check execution time
        if metrics.get('average_duration', 0) > self.thresholds['execution_time']['critical']:
            await self._create_alert(
                process_id, 'critical', MetricType.EXECUTION_TIME,
                f"Average execution time ({metrics['average_duration']:.1f}s) exceeds critical threshold"
            )
        
        # Check error rate
        if metrics.get('error_rate', 0) > self.thresholds['error_rate']['critical']:
            await self._create_alert(
                process_id, 'critical', MetricType.ERROR_RATE,
                f"Error rate ({metrics['error_rate']*100:.1f}%) exceeds critical threshold"
            )
        
        # Check throughput
        if metrics.get('throughput', float('inf')) < self.thresholds['throughput']['critical']:
            await self._create_alert(
                process_id, 'critical', MetricType.THROUGHPUT,
                f"Throughput ({metrics['throughput']:.1f}/min) below critical threshold"
            )
    
    async def _create_alert(self, process_id: str, severity: str, metric_type: MetricType, message: str):
        """Create a monitoring alert."""
        alert_id = str(uuid.uuid4())
        
        self.alerts[alert_id] = {
            'alert_id': alert_id,
            'process_id': process_id,
            'severity': severity,
            'metric_type': metric_type.value,
            'message': message,
            'timestamp': datetime.utcnow(),
            'resolved': False
        }
        
        logger.warning(f"Alert created: {message}")
    
    async def get_recommendations(self, process_id: str) -> List[Dict[str, Any]]:
        """Get optimization recommendations for a process."""
        metrics = self._calculate_current_metrics(process_id)
        recommendations = []
        
        if not metrics:
            return recommendations
        
        # Execution time recommendations
        if metrics.get('average_duration', 0) > 300:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'title': 'Optimize Process Execution Time',
                'description': f'Average execution time is {metrics["average_duration"]:.1f}s. Consider parallelizing tasks.',
                'potential_impact': 'Reduce execution time by up to 50%'
            })
        
        # Error rate recommendations
        if metrics.get('error_rate', 0) > 0.05:
            recommendations.append({
                'type': 'reliability',
                'priority': 'high',
                'title': 'Reduce Error Rate',
                'description': f'Error rate is {metrics["error_rate"]*100:.1f}%. Implement better error handling.',
                'potential_impact': 'Improve success rate to >95%'
            })
        
        # Throughput recommendations
        if metrics.get('throughput', 0) < 10:
            recommendations.append({
                'type': 'scalability',
                'priority': 'medium',
                'title': 'Improve Process Throughput',
                'description': 'Current throughput is low. Consider scaling or optimizing the process.',
                'potential_impact': 'Increase throughput by 2-3x'
            })
        
        return recommendations


# Global process monitor instance
process_monitor = ProcessMonitor()