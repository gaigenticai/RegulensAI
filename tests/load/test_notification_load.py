"""
Load testing framework for RegulensAI notification system.
Tests bulk notification processing, throughput, and system limits.
"""

import pytest
import asyncio
import time
import uuid
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import structlog

from core_infra.services.notifications.delivery import NotificationDeliveryService
from core_infra.services.notifications.bulk_processor import BulkNotificationProcessor
from core_infra.services.notifications.template_engine import TemplateEngine

logger = structlog.get_logger(__name__)


class NotificationLoadTester:
    """
    Comprehensive load testing for notification system.
    """
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.metrics = {
            'total_sent': 0,
            'total_failed': 0,
            'response_times': [],
            'throughput_samples': [],
            'error_rates': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    
    async def run_load_test_suite(self, tenant_id: str) -> Dict[str, Any]:
        """
        Run comprehensive load test suite.
        """
        logger.info("Starting notification load test suite")
        
        test_results = {}
        
        # Test 1: Baseline performance (1K notifications)
        test_results['baseline_1k'] = await self.test_baseline_performance(tenant_id, 1000)
        
        # Test 2: High volume (10K notifications)
        test_results['high_volume_10k'] = await self.test_high_volume_processing(tenant_id, 10000)
        
        # Test 3: Extreme load (50K notifications)
        test_results['extreme_load_50k'] = await self.test_extreme_load(tenant_id, 50000)
        
        # Test 4: Concurrent batch processing
        test_results['concurrent_batches'] = await self.test_concurrent_batch_processing(tenant_id)
        
        # Test 5: Sustained load over time
        test_results['sustained_load'] = await self.test_sustained_load(tenant_id)
        
        # Test 6: Memory and resource usage
        test_results['resource_usage'] = await self.test_resource_usage(tenant_id)
        
        # Generate comprehensive report
        test_results['summary'] = self.generate_performance_summary()
        
        return test_results
    
    async def test_baseline_performance(self, tenant_id: str, notification_count: int) -> Dict[str, Any]:
        """
        Test baseline performance with moderate load.
        """
        logger.info(f"Running baseline performance test with {notification_count} notifications")
        
        async with NotificationDeliveryService(self.supabase) as notification_service:
            # Generate test notifications
            notifications = self.generate_test_notifications(notification_count)
            
            # Measure processing time
            start_time = time.time()
            start_memory = self.get_memory_usage()
            
            # Process notifications in optimal batch size
            batch_size = 100
            results = []
            
            for i in range(0, len(notifications), batch_size):
                batch = notifications[i:i + batch_size]
                batch_start = time.time()
                
                batch_result = await notification_service.send_bulk_notifications(
                    tenant_id=tenant_id,
                    notifications=batch
                )
                
                batch_end = time.time()
                batch_time = batch_end - batch_start
                
                results.append(batch_result)
                self.metrics['response_times'].append(batch_time)
                
                # Calculate throughput for this batch
                batch_throughput = len(batch) / batch_time
                self.metrics['throughput_samples'].append(batch_throughput)
            
            end_time = time.time()
            end_memory = self.get_memory_usage()
            
            # Calculate metrics
            total_time = end_time - start_time
            total_processed = sum(r.get('successful_deliveries', 0) for r in results)
            total_failed = sum(r.get('failed_deliveries', 0) for r in results)
            
            throughput = total_processed / total_time
            error_rate = total_failed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0
            memory_delta = end_memory - start_memory
            
            return {
                'notification_count': notification_count,
                'total_time': total_time,
                'total_processed': total_processed,
                'total_failed': total_failed,
                'throughput': throughput,
                'error_rate': error_rate,
                'avg_response_time': statistics.mean(self.metrics['response_times'][-len(results):]),
                'memory_usage_mb': memory_delta,
                'status': 'passed' if error_rate < 0.05 and throughput > 50 else 'failed'
            }
    
    async def test_high_volume_processing(self, tenant_id: str, notification_count: int) -> Dict[str, Any]:
        """
        Test high volume notification processing (10K+ notifications).
        """
        logger.info(f"Running high volume test with {notification_count} notifications")
        
        async with BulkNotificationProcessor(self.supabase) as bulk_processor:
            # Generate test notifications with varied priorities
            notifications = self.generate_varied_notifications(notification_count)
            
            start_time = time.time()
            
            # Use bulk processor for high volume
            result = await bulk_processor.process_bulk_notifications(
                tenant_id=tenant_id,
                notifications=notifications,
                batch_size=500,  # Larger batch size for high volume
                max_concurrent_batches=10
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Validate performance requirements
            throughput = result['total_processed'] / total_time
            error_rate = result['total_failed'] / result['total_notifications']
            
            # Performance thresholds for high volume
            min_throughput = 200  # notifications per second
            max_error_rate = 0.02  # 2% maximum error rate
            max_processing_time = 300  # 5 minutes maximum
            
            status = 'passed' if (
                throughput >= min_throughput and
                error_rate <= max_error_rate and
                total_time <= max_processing_time
            ) else 'failed'
            
            return {
                'notification_count': notification_count,
                'total_time': total_time,
                'throughput': throughput,
                'error_rate': error_rate,
                'batch_processing_time': result.get('avg_batch_time', 0),
                'concurrent_batches': result.get('max_concurrent_batches', 0),
                'status': status,
                'performance_thresholds': {
                    'min_throughput': min_throughput,
                    'max_error_rate': max_error_rate,
                    'max_processing_time': max_processing_time
                }
            }
    
    async def test_extreme_load(self, tenant_id: str, notification_count: int) -> Dict[str, Any]:
        """
        Test system behavior under extreme load (50K+ notifications).
        """
        logger.info(f"Running extreme load test with {notification_count} notifications")
        
        async with BulkNotificationProcessor(self.supabase) as bulk_processor:
            # Configure for extreme load
            bulk_processor.configure_for_extreme_load(
                batch_size=1000,
                max_concurrent_batches=20,
                rate_limit_per_second=1000,
                circuit_breaker_threshold=0.1
            )
            
            notifications = self.generate_test_notifications(notification_count)
            
            start_time = time.time()
            start_memory = self.get_memory_usage()
            
            # Monitor system resources during processing
            resource_monitor = asyncio.create_task(
                self.monitor_system_resources(duration=600)  # 10 minutes
            )
            
            try:
                result = await bulk_processor.process_bulk_notifications(
                    tenant_id=tenant_id,
                    notifications=notifications,
                    enable_monitoring=True
                )
                
                end_time = time.time()
                end_memory = self.get_memory_usage()
                
                # Stop resource monitoring
                resource_monitor.cancel()
                
                total_time = end_time - start_time
                throughput = result['total_processed'] / total_time
                error_rate = result['total_failed'] / result['total_notifications']
                memory_delta = end_memory - start_memory
                
                # Extreme load thresholds (more lenient)
                min_throughput = 100  # notifications per second
                max_error_rate = 0.05  # 5% maximum error rate
                max_memory_usage = 2048  # 2GB maximum memory increase
                
                status = 'passed' if (
                    throughput >= min_throughput and
                    error_rate <= max_error_rate and
                    memory_delta <= max_memory_usage
                ) else 'failed'
                
                return {
                    'notification_count': notification_count,
                    'total_time': total_time,
                    'throughput': throughput,
                    'error_rate': error_rate,
                    'memory_usage_mb': memory_delta,
                    'peak_concurrent_batches': result.get('peak_concurrent_batches', 0),
                    'circuit_breaker_trips': result.get('circuit_breaker_trips', 0),
                    'status': status
                }
                
            except Exception as e:
                resource_monitor.cancel()
                logger.error(f"Extreme load test failed: {e}")
                return {
                    'notification_count': notification_count,
                    'status': 'failed',
                    'error': str(e)
                }
    
    async def test_concurrent_batch_processing(self, tenant_id: str) -> Dict[str, Any]:
        """
        Test concurrent batch processing capabilities.
        """
        logger.info("Running concurrent batch processing test")
        
        async with NotificationDeliveryService(self.supabase) as notification_service:
            # Create multiple batches for concurrent processing
            batch_sizes = [500, 750, 1000, 1250, 1500]
            batches = []
            
            for size in batch_sizes:
                batch = self.generate_test_notifications(size)
                batches.append(batch)
            
            # Process all batches concurrently
            async def process_batch(batch_notifications, batch_id):
                start_time = time.time()
                result = await notification_service.send_bulk_notifications(
                    tenant_id=tenant_id,
                    notifications=batch_notifications
                )
                end_time = time.time()
                
                return {
                    'batch_id': batch_id,
                    'batch_size': len(batch_notifications),
                    'processing_time': end_time - start_time,
                    'result': result
                }
            
            start_time = time.time()
            
            # Execute all batches concurrently
            tasks = [
                process_batch(batch, i) 
                for i, batch in enumerate(batches)
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze concurrent processing results
            successful_batches = [
                r for r in batch_results 
                if isinstance(r, dict) and not isinstance(r, Exception)
            ]
            
            total_notifications = sum(r['batch_size'] for r in successful_batches)
            total_processed = sum(
                r['result'].get('successful_deliveries', 0) 
                for r in successful_batches
            )
            
            concurrent_throughput = total_processed / total_time
            
            return {
                'total_batches': len(batches),
                'successful_batches': len(successful_batches),
                'total_notifications': total_notifications,
                'total_processed': total_processed,
                'total_time': total_time,
                'concurrent_throughput': concurrent_throughput,
                'avg_batch_time': statistics.mean([r['processing_time'] for r in successful_batches]),
                'status': 'passed' if len(successful_batches) == len(batches) else 'failed'
            }
    
    async def test_sustained_load(self, tenant_id: str, duration_minutes: int = 10) -> Dict[str, Any]:
        """
        Test sustained load over extended period.
        """
        logger.info(f"Running sustained load test for {duration_minutes} minutes")
        
        async with NotificationDeliveryService(self.supabase) as notification_service:
            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)
            
            total_processed = 0
            total_failed = 0
            throughput_samples = []
            
            while time.time() < end_time:
                # Generate batch of notifications
                batch = self.generate_test_notifications(100)
                
                batch_start = time.time()
                result = await notification_service.send_bulk_notifications(
                    tenant_id=tenant_id,
                    notifications=batch
                )
                batch_end = time.time()
                
                batch_time = batch_end - batch_start
                batch_throughput = len(batch) / batch_time
                
                total_processed += result.get('successful_deliveries', 0)
                total_failed += result.get('failed_deliveries', 0)
                throughput_samples.append(batch_throughput)
                
                # Small delay to simulate realistic load
                await asyncio.sleep(1)
            
            actual_duration = time.time() - start_time
            avg_throughput = total_processed / actual_duration
            error_rate = total_failed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0
            
            return {
                'duration_minutes': actual_duration / 60,
                'total_processed': total_processed,
                'total_failed': total_failed,
                'avg_throughput': avg_throughput,
                'error_rate': error_rate,
                'throughput_stability': statistics.stdev(throughput_samples) if len(throughput_samples) > 1 else 0,
                'status': 'passed' if error_rate < 0.05 and avg_throughput > 50 else 'failed'
            }
    
    def generate_test_notifications(self, count: int) -> List[Dict[str, Any]]:
        """Generate test notifications for load testing."""
        notifications = []
        
        for i in range(count):
            notification = {
                'template_name': 'load_test_notification',
                'recipients': [f'loadtest{i}@company.com'],
                'context': {
                    'notification_id': f'LOAD_TEST_{i:06d}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'test_data': f'Load test notification {i}'
                },
                'priority': 'normal',
                'channels': ['email']
            }
            notifications.append(notification)
        
        return notifications
    
    def generate_varied_notifications(self, count: int) -> List[Dict[str, Any]]:
        """Generate notifications with varied priorities and channels."""
        notifications = []
        priorities = ['low', 'normal', 'high', 'urgent']
        channels = [['email'], ['sms'], ['webhook'], ['email', 'sms']]
        
        for i in range(count):
            notification = {
                'template_name': 'varied_test_notification',
                'recipients': [f'variedtest{i}@company.com'],
                'context': {
                    'notification_id': f'VARIED_TEST_{i:06d}',
                    'priority_level': priorities[i % len(priorities)],
                    'test_iteration': i
                },
                'priority': priorities[i % len(priorities)],
                'channels': channels[i % len(channels)]
            }
            notifications.append(notification)
        
        return notifications
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    async def monitor_system_resources(self, duration: int):
        """Monitor system resources during load testing."""
        import psutil
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            memory_usage = self.get_memory_usage()
            cpu_usage = psutil.cpu_percent()
            
            self.metrics['memory_usage'].append(memory_usage)
            self.metrics['cpu_usage'].append(cpu_usage)
            
            await asyncio.sleep(5)  # Sample every 5 seconds
    
    def generate_performance_summary(self) -> Dict[str, Any]:
        """Generate comprehensive performance summary."""
        return {
            'total_notifications_sent': self.metrics['total_sent'],
            'total_failures': self.metrics['total_failed'],
            'overall_error_rate': self.metrics['total_failed'] / (self.metrics['total_sent'] + self.metrics['total_failed']) if (self.metrics['total_sent'] + self.metrics['total_failed']) > 0 else 0,
            'avg_response_time': statistics.mean(self.metrics['response_times']) if self.metrics['response_times'] else 0,
            'max_response_time': max(self.metrics['response_times']) if self.metrics['response_times'] else 0,
            'avg_throughput': statistics.mean(self.metrics['throughput_samples']) if self.metrics['throughput_samples'] else 0,
            'peak_throughput': max(self.metrics['throughput_samples']) if self.metrics['throughput_samples'] else 0,
            'avg_memory_usage': statistics.mean(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0,
            'peak_memory_usage': max(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0,
            'avg_cpu_usage': statistics.mean(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0,
            'peak_cpu_usage': max(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0
        }


@pytest.mark.asyncio
@pytest.mark.load_test
async def test_notification_load_suite():
    """
    Main load test suite for notification system.
    """
    from unittest.mock import Mock
    
    mock_supabase = Mock()
    tenant_id = str(uuid.uuid4())
    
    load_tester = NotificationLoadTester(mock_supabase)
    results = await load_tester.run_load_test_suite(tenant_id)
    
    # Validate overall test results
    assert results['baseline_1k']['status'] == 'passed'
    assert results['high_volume_10k']['status'] == 'passed'
    assert results['concurrent_batches']['status'] == 'passed'
    assert results['sustained_load']['status'] == 'passed'
    
    # Log comprehensive results
    logger.info("Load test suite completed successfully")
    logger.info(f"Performance summary: {results['summary']}")
    
    return results
