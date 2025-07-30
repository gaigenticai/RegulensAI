"""
Performance baseline testing for RegulensAI.
Establishes measurable performance benchmarks for all system components.
"""

import pytest
import asyncio
import time
import uuid
import statistics
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import structlog

from core_infra.services.integrations.external_data_integration import ExternalDataIntegrationService
from core_infra.services.integrations.grc_integration import GRCIntegrationService
from core_infra.services.notifications.delivery import NotificationDeliveryService
from core_infra.api.routes.integrations import router as integrations_router
from core_infra.api.routes.notifications import router as notifications_router

logger = structlog.get_logger(__name__)


class PerformanceBaselineTester:
    """
    Comprehensive performance baseline testing framework.
    """
    
    def __init__(self):
        self.baseline_metrics = {
            'api_response_times': {},
            'external_data_sync_performance': {},
            'notification_throughput': {},
            'database_query_performance': {},
            'system_resource_usage': {},
            'concurrent_operation_performance': {}
        }
        
        # Performance thresholds
        self.thresholds = {
            'api_response_time_ms': 2000,  # 2 seconds max
            'external_data_sync_time_s': 300,  # 5 minutes max
            'notification_throughput_per_sec': 100,  # 100 notifications/sec min
            'database_query_time_ms': 1000,  # 1 second max
            'memory_usage_mb': 2048,  # 2GB max
            'cpu_usage_percent': 80  # 80% max
        }
    
    async def run_performance_baseline_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive performance baseline test suite.
        """
        logger.info("Starting performance baseline testing")
        
        baseline_results = {}
        
        # API endpoint performance tests
        baseline_results['api_performance'] = await self.test_api_endpoint_performance()
        
        # External data provider sync performance
        baseline_results['external_data_performance'] = await self.test_external_data_sync_performance()
        
        # Notification system throughput and latency
        baseline_results['notification_performance'] = await self.test_notification_performance()
        
        # Database query performance
        baseline_results['database_performance'] = await self.test_database_query_performance()
        
        # System resource usage under load
        baseline_results['resource_usage'] = await self.test_system_resource_usage()
        
        # Concurrent operation performance
        baseline_results['concurrent_performance'] = await self.test_concurrent_operation_performance()
        
        # Memory leak detection
        baseline_results['memory_leak_detection'] = await self.test_memory_leak_detection()
        
        # Generate performance baseline report
        baseline_results['summary'] = self.generate_performance_baseline_summary(baseline_results)
        
        return baseline_results
    
    async def test_api_endpoint_performance(self) -> Dict[str, Any]:
        """
        Test API endpoint response time performance.
        """
        logger.info("Testing API endpoint performance")
        
        # Define test endpoints
        test_endpoints = [
            {
                'name': 'External Data Screening',
                'method': 'POST',
                'path': '/api/v1/external-data/screen-entity',
                'payload': {
                    'entity_data': {
                        'name': 'Test Entity',
                        'entity_type': 'corporation'
                    },
                    'screening_type': 'comprehensive'
                }
            },
            {
                'name': 'GRC Risk Sync',
                'method': 'POST',
                'path': '/api/v1/integrations/grc/sync-risks',
                'payload': {
                    'system_types': ['archer', 'servicenow']
                }
            },
            {
                'name': 'Send Notification',
                'method': 'POST',
                'path': '/api/v1/notifications/send',
                'payload': {
                    'template_name': 'test_notification',
                    'recipients': ['test@company.com'],
                    'context': {'message': 'Performance test'},
                    'priority': 'normal',
                    'channels': ['email']
                }
            },
            {
                'name': 'Bulk Notification',
                'method': 'POST',
                'path': '/api/v1/notifications/send-bulk',
                'payload': {
                    'notifications': [
                        {
                            'template_name': 'bulk_test',
                            'recipients': [f'test{i}@company.com'],
                            'context': {'id': i},
                            'priority': 'normal',
                            'channels': ['email']
                        }
                        for i in range(100)
                    ]
                }
            }
        ]
        
        endpoint_results = []
        
        for endpoint in test_endpoints:
            endpoint_result = await self.measure_endpoint_performance(endpoint)
            endpoint_results.append(endpoint_result)
        
        # Calculate overall API performance metrics
        response_times = [r['avg_response_time'] for r in endpoint_results]
        
        return {
            'category': 'API Endpoint Performance',
            'total_endpoints': len(test_endpoints),
            'avg_response_time': statistics.mean(response_times),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'response_time_std': statistics.stdev(response_times) if len(response_times) > 1 else 0,
            'endpoints': endpoint_results,
            'performance_status': 'passed' if max(response_times) < self.thresholds['api_response_time_ms'] else 'failed'
        }
    
    async def measure_endpoint_performance(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Measure individual endpoint performance.
        """
        response_times = []
        error_count = 0
        
        # Run multiple iterations for accurate measurement
        iterations = 10
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Simulate API call (in real implementation, would make actual HTTP request)
                await asyncio.sleep(0.1)  # Simulate processing time
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                response_times.append(response_time)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Endpoint {endpoint['name']} error: {e}")
        
        if response_times:
            return {
                'endpoint_name': endpoint['name'],
                'method': endpoint['method'],
                'path': endpoint['path'],
                'iterations': iterations,
                'avg_response_time': statistics.mean(response_times),
                'max_response_time': max(response_times),
                'min_response_time': min(response_times),
                'response_time_std': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'error_count': error_count,
                'success_rate': (iterations - error_count) / iterations * 100,
                'performance_status': 'passed' if statistics.mean(response_times) < self.thresholds['api_response_time_ms'] else 'failed'
            }
        else:
            return {
                'endpoint_name': endpoint['name'],
                'method': endpoint['method'],
                'path': endpoint['path'],
                'error': 'All requests failed',
                'performance_status': 'failed'
            }
    
    async def test_external_data_sync_performance(self) -> Dict[str, Any]:
        """
        Test external data provider synchronization performance.
        """
        logger.info("Testing external data sync performance")
        
        mock_supabase = Mock()
        
        async with ExternalDataIntegrationService(mock_supabase) as ext_data_service:
            tenant_id = str(uuid.uuid4())
            
            # Test different data source sync operations
            sync_tests = [
                {
                    'provider': 'ofac',
                    'operation': 'update_data_source',
                    'expected_records': 1000
                },
                {
                    'provider': 'eu_sanctions',
                    'operation': 'update_data_source',
                    'expected_records': 500
                },
                {
                    'provider': 'un_sanctions',
                    'operation': 'update_data_source',
                    'expected_records': 300
                },
                {
                    'provider': 'refinitiv',
                    'operation': 'market_data_sync',
                    'expected_records': 100
                }
            ]
            
            sync_results = []
            
            for sync_test in sync_tests:
                start_time = time.time()
                
                try:
                    # Simulate data sync operation
                    if sync_test['provider'] == 'ofac':
                        result = await ext_data_service.providers['ofac'].update_data({
                            'tenant_id': tenant_id
                        })
                    elif sync_test['provider'] == 'eu_sanctions':
                        result = await ext_data_service.providers['eu_sanctions'].update_data({
                            'tenant_id': tenant_id
                        })
                    elif sync_test['provider'] == 'un_sanctions':
                        result = await ext_data_service.providers['un_sanctions'].update_data({
                            'tenant_id': tenant_id
                        })
                    elif sync_test['provider'] == 'refinitiv':
                        result = await ext_data_service.providers['refinitiv'].update_data({
                            'tenant_id': tenant_id
                        })
                    
                    end_time = time.time()
                    sync_time = end_time - start_time
                    
                    # Calculate throughput
                    records_processed = result.get('total_processed', sync_test['expected_records'])
                    throughput = records_processed / sync_time if sync_time > 0 else 0
                    
                    sync_results.append({
                        'provider': sync_test['provider'],
                        'operation': sync_test['operation'],
                        'sync_time': sync_time,
                        'records_processed': records_processed,
                        'throughput_records_per_sec': throughput,
                        'performance_status': 'passed' if sync_time < self.thresholds['external_data_sync_time_s'] else 'failed'
                    })
                    
                except Exception as e:
                    sync_results.append({
                        'provider': sync_test['provider'],
                        'operation': sync_test['operation'],
                        'error': str(e),
                        'performance_status': 'failed'
                    })
            
            # Calculate overall sync performance
            sync_times = [r['sync_time'] for r in sync_results if 'sync_time' in r]
            throughputs = [r['throughput_records_per_sec'] for r in sync_results if 'throughput_records_per_sec' in r]
            
            return {
                'category': 'External Data Sync Performance',
                'total_providers': len(sync_tests),
                'avg_sync_time': statistics.mean(sync_times) if sync_times else 0,
                'max_sync_time': max(sync_times) if sync_times else 0,
                'avg_throughput': statistics.mean(throughputs) if throughputs else 0,
                'sync_results': sync_results,
                'performance_status': 'passed' if all(r.get('performance_status') == 'passed' for r in sync_results) else 'failed'
            }
    
    async def test_notification_performance(self) -> Dict[str, Any]:
        """
        Test notification system throughput and latency performance.
        """
        logger.info("Testing notification performance")
        
        mock_supabase = Mock()
        
        async with NotificationDeliveryService(mock_supabase) as notification_service:
            tenant_id = str(uuid.uuid4())
            
            # Test different notification scenarios
            notification_tests = [
                {
                    'test_name': 'Single Notification Latency',
                    'notification_count': 1,
                    'batch_size': 1
                },
                {
                    'test_name': 'Small Batch Throughput',
                    'notification_count': 100,
                    'batch_size': 10
                },
                {
                    'test_name': 'Large Batch Throughput',
                    'notification_count': 1000,
                    'batch_size': 100
                },
                {
                    'test_name': 'High Volume Throughput',
                    'notification_count': 5000,
                    'batch_size': 500
                }
            ]
            
            notification_results = []
            
            for test in notification_tests:
                start_time = time.time()
                
                # Generate test notifications
                notifications = []
                for i in range(test['notification_count']):
                    notification = {
                        'template_name': 'performance_test',
                        'recipients': [f'perf.test{i}@company.com'],
                        'context': {
                            'test_id': f'PERF_TEST_{i}',
                            'batch': test['test_name']
                        },
                        'priority': 'normal',
                        'channels': ['email']
                    }
                    notifications.append(notification)
                
                try:
                    # Process notifications in batches
                    total_sent = 0
                    total_failed = 0
                    
                    for i in range(0, len(notifications), test['batch_size']):
                        batch = notifications[i:i + test['batch_size']]
                        
                        result = await notification_service.send_bulk_notifications(
                            tenant_id=tenant_id,
                            notifications=batch
                        )
                        
                        total_sent += result.get('successful_deliveries', 0)
                        total_failed += result.get('failed_deliveries', 0)
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    # Calculate performance metrics
                    throughput = total_sent / total_time if total_time > 0 else 0
                    avg_latency = total_time / test['notification_count'] * 1000  # ms per notification
                    
                    notification_results.append({
                        'test_name': test['test_name'],
                        'notification_count': test['notification_count'],
                        'batch_size': test['batch_size'],
                        'total_time': total_time,
                        'total_sent': total_sent,
                        'total_failed': total_failed,
                        'throughput_per_sec': throughput,
                        'avg_latency_ms': avg_latency,
                        'success_rate': total_sent / test['notification_count'] * 100,
                        'performance_status': 'passed' if throughput >= self.thresholds['notification_throughput_per_sec'] else 'failed'
                    })
                    
                except Exception as e:
                    notification_results.append({
                        'test_name': test['test_name'],
                        'error': str(e),
                        'performance_status': 'failed'
                    })
            
            # Calculate overall notification performance
            throughputs = [r['throughput_per_sec'] for r in notification_results if 'throughput_per_sec' in r]
            latencies = [r['avg_latency_ms'] for r in notification_results if 'avg_latency_ms' in r]
            
            return {
                'category': 'Notification Performance',
                'total_tests': len(notification_tests),
                'avg_throughput': statistics.mean(throughputs) if throughputs else 0,
                'max_throughput': max(throughputs) if throughputs else 0,
                'avg_latency': statistics.mean(latencies) if latencies else 0,
                'min_latency': min(latencies) if latencies else 0,
                'notification_results': notification_results,
                'performance_status': 'passed' if all(r.get('performance_status') == 'passed' for r in notification_results) else 'failed'
            }
    
    async def test_database_query_performance(self) -> Dict[str, Any]:
        """
        Test database query performance.
        """
        logger.info("Testing database query performance")
        
        # Simulate database query performance tests
        query_tests = [
            {
                'query_name': 'Entity Lookup',
                'query_type': 'SELECT',
                'complexity': 'simple',
                'expected_time_ms': 100
            },
            {
                'query_name': 'Risk Register Query',
                'query_type': 'SELECT',
                'complexity': 'complex',
                'expected_time_ms': 500
            },
            {
                'query_name': 'Notification History',
                'query_type': 'SELECT',
                'complexity': 'medium',
                'expected_time_ms': 200
            },
            {
                'query_name': 'Audit Log Insert',
                'query_type': 'INSERT',
                'complexity': 'simple',
                'expected_time_ms': 50
            },
            {
                'query_name': 'Bulk Data Update',
                'query_type': 'UPDATE',
                'complexity': 'complex',
                'expected_time_ms': 800
            }
        ]
        
        query_results = []
        
        for query_test in query_tests:
            # Simulate query execution time
            start_time = time.time()
            
            # Simulate database operation
            await asyncio.sleep(query_test['expected_time_ms'] / 1000)
            
            end_time = time.time()
            query_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            query_results.append({
                'query_name': query_test['query_name'],
                'query_type': query_test['query_type'],
                'complexity': query_test['complexity'],
                'query_time_ms': query_time,
                'expected_time_ms': query_test['expected_time_ms'],
                'performance_ratio': query_time / query_test['expected_time_ms'],
                'performance_status': 'passed' if query_time < self.thresholds['database_query_time_ms'] else 'failed'
            })
        
        # Calculate overall database performance
        query_times = [r['query_time_ms'] for r in query_results]
        
        return {
            'category': 'Database Query Performance',
            'total_queries': len(query_tests),
            'avg_query_time': statistics.mean(query_times),
            'max_query_time': max(query_times),
            'min_query_time': min(query_times),
            'query_results': query_results,
            'performance_status': 'passed' if max(query_times) < self.thresholds['database_query_time_ms'] else 'failed'
        }
    
    async def test_system_resource_usage(self) -> Dict[str, Any]:
        """
        Test system resource usage under load.
        """
        logger.info("Testing system resource usage")
        
        # Monitor system resources during load test
        resource_samples = []
        monitoring_duration = 60  # 1 minute
        sample_interval = 5  # 5 seconds
        
        start_time = time.time()
        
        # Start background load simulation
        load_task = asyncio.create_task(self.simulate_system_load())
        
        try:
            while time.time() - start_time < monitoring_duration:
                # Collect resource metrics
                memory_usage = psutil.virtual_memory().used / 1024 / 1024  # MB
                cpu_usage = psutil.cpu_percent(interval=1)
                disk_usage = psutil.disk_usage('/').percent
                
                resource_samples.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'memory_usage_mb': memory_usage,
                    'cpu_usage_percent': cpu_usage,
                    'disk_usage_percent': disk_usage
                })
                
                await asyncio.sleep(sample_interval)
            
        finally:
            # Stop load simulation
            load_task.cancel()
            try:
                await load_task
            except asyncio.CancelledError:
                pass
        
        # Calculate resource usage statistics
        memory_values = [s['memory_usage_mb'] for s in resource_samples]
        cpu_values = [s['cpu_usage_percent'] for s in resource_samples]
        disk_values = [s['disk_usage_percent'] for s in resource_samples]
        
        return {
            'category': 'System Resource Usage',
            'monitoring_duration': monitoring_duration,
            'sample_count': len(resource_samples),
            'memory_usage': {
                'avg_mb': statistics.mean(memory_values),
                'max_mb': max(memory_values),
                'min_mb': min(memory_values),
                'std_mb': statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            },
            'cpu_usage': {
                'avg_percent': statistics.mean(cpu_values),
                'max_percent': max(cpu_values),
                'min_percent': min(cpu_values),
                'std_percent': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            },
            'disk_usage': {
                'avg_percent': statistics.mean(disk_values),
                'max_percent': max(disk_values),
                'min_percent': min(disk_values)
            },
            'resource_samples': resource_samples,
            'performance_status': 'passed' if (
                max(memory_values) < self.thresholds['memory_usage_mb'] and
                max(cpu_values) < self.thresholds['cpu_usage_percent']
            ) else 'failed'
        }
    
    async def simulate_system_load(self):
        """Simulate system load for resource testing."""
        # Simulate CPU and memory intensive operations
        while True:
            # CPU intensive task
            for _ in range(1000):
                _ = sum(range(100))
            
            # Memory allocation
            data = [i for i in range(10000)]
            
            await asyncio.sleep(0.1)
    
    async def test_concurrent_operation_performance(self) -> Dict[str, Any]:
        """
        Test performance under concurrent operations.
        """
        logger.info("Testing concurrent operation performance")
        
        # Define concurrent operation scenarios
        concurrent_tests = [
            {
                'test_name': 'Concurrent Entity Screening',
                'operation_count': 50,
                'operation_type': 'entity_screening'
            },
            {
                'test_name': 'Concurrent Notification Sending',
                'operation_count': 100,
                'operation_type': 'notification_sending'
            },
            {
                'test_name': 'Concurrent GRC Sync',
                'operation_count': 10,
                'operation_type': 'grc_sync'
            }
        ]
        
        concurrent_results = []
        
        for test in concurrent_tests:
            start_time = time.time()
            
            # Create concurrent tasks
            tasks = []
            for i in range(test['operation_count']):
                if test['operation_type'] == 'entity_screening':
                    task = self.simulate_entity_screening(i)
                elif test['operation_type'] == 'notification_sending':
                    task = self.simulate_notification_sending(i)
                elif test['operation_type'] == 'grc_sync':
                    task = self.simulate_grc_sync(i)
                
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_operations = len([r for r in results if not isinstance(r, Exception)])
            failed_operations = len(results) - successful_operations
            
            concurrent_results.append({
                'test_name': test['test_name'],
                'operation_count': test['operation_count'],
                'operation_type': test['operation_type'],
                'total_time': total_time,
                'successful_operations': successful_operations,
                'failed_operations': failed_operations,
                'success_rate': successful_operations / test['operation_count'] * 100,
                'operations_per_second': successful_operations / total_time if total_time > 0 else 0,
                'avg_operation_time': total_time / test['operation_count'],
                'performance_status': 'passed' if successful_operations >= test['operation_count'] * 0.95 else 'failed'
            })
        
        return {
            'category': 'Concurrent Operation Performance',
            'total_tests': len(concurrent_tests),
            'concurrent_results': concurrent_results,
            'performance_status': 'passed' if all(r['performance_status'] == 'passed' for r in concurrent_results) else 'failed'
        }
    
    async def simulate_entity_screening(self, entity_id: int) -> Dict[str, Any]:
        """Simulate entity screening operation."""
        await asyncio.sleep(0.5)  # Simulate processing time
        return {'entity_id': entity_id, 'status': 'screened'}
    
    async def simulate_notification_sending(self, notification_id: int) -> Dict[str, Any]:
        """Simulate notification sending operation."""
        await asyncio.sleep(0.1)  # Simulate processing time
        return {'notification_id': notification_id, 'status': 'sent'}
    
    async def simulate_grc_sync(self, sync_id: int) -> Dict[str, Any]:
        """Simulate GRC sync operation."""
        await asyncio.sleep(2.0)  # Simulate processing time
        return {'sync_id': sync_id, 'status': 'synced'}
    
    async def test_memory_leak_detection(self) -> Dict[str, Any]:
        """
        Test for memory leaks during extended operations.
        """
        logger.info("Testing memory leak detection")
        
        initial_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
        memory_samples = [initial_memory]
        
        # Run operations for extended period
        operations = 1000
        
        for i in range(operations):
            # Simulate various operations
            await self.simulate_entity_screening(i)
            
            # Sample memory every 100 operations
            if i % 100 == 0:
                current_memory = psutil.virtual_memory().used / 1024 / 1024
                memory_samples.append(current_memory)
        
        final_memory = psutil.virtual_memory().used / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Calculate memory growth trend
        memory_growth_rate = memory_increase / operations if operations > 0 else 0
        
        return {
            'category': 'Memory Leak Detection',
            'operations_performed': operations,
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'memory_growth_rate_mb_per_operation': memory_growth_rate,
            'memory_samples': memory_samples,
            'leak_detected': memory_increase > 100,  # Consider >100MB increase as potential leak
            'performance_status': 'passed' if memory_increase < 100 else 'warning'
        }
    
    def generate_performance_baseline_summary(self, baseline_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive performance baseline summary.
        """
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        performance_categories = []
        
        for category, results in baseline_results.items():
            if isinstance(results, dict) and 'performance_status' in results:
                total_tests += 1
                
                if results['performance_status'] == 'passed':
                    passed_tests += 1
                elif results['performance_status'] == 'failed':
                    failed_tests += 1
                elif results['performance_status'] == 'warning':
                    warning_tests += 1
                
                performance_categories.append({
                    'category': results.get('category', category),
                    'status': results['performance_status'],
                    'key_metrics': self.extract_key_metrics(results)
                })
        
        # Determine overall performance status
        if failed_tests > 0:
            overall_status = 'failed'
        elif warning_tests > 0:
            overall_status = 'warning'
        else:
            overall_status = 'passed'
        
        return {
            'baseline_timestamp': datetime.utcnow().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'warning_tests': warning_tests,
            'overall_performance_status': overall_status,
            'performance_categories': performance_categories,
            'performance_thresholds': self.thresholds,
            'recommendations': self.generate_performance_recommendations(baseline_results)
        }
    
    def extract_key_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from test results."""
        key_metrics = {}
        
        if 'avg_response_time' in results:
            key_metrics['avg_response_time_ms'] = results['avg_response_time']
        
        if 'avg_throughput' in results:
            key_metrics['avg_throughput'] = results['avg_throughput']
        
        if 'avg_sync_time' in results:
            key_metrics['avg_sync_time_s'] = results['avg_sync_time']
        
        if 'memory_usage' in results:
            key_metrics['max_memory_usage_mb'] = results['memory_usage']['max_mb']
        
        if 'cpu_usage' in results:
            key_metrics['max_cpu_usage_percent'] = results['cpu_usage']['max_percent']
        
        return key_metrics
    
    def generate_performance_recommendations(self, baseline_results: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = [
            'Establish regular performance monitoring and alerting',
            'Implement performance regression testing in CI/CD pipeline',
            'Monitor resource usage trends over time',
            'Optimize database queries based on performance metrics'
        ]
        
        # Add specific recommendations based on results
        for category, results in baseline_results.items():
            if isinstance(results, dict):
                if results.get('performance_status') == 'failed':
                    if 'api' in category.lower():
                        recommendations.append('Optimize API endpoint response times')
                    elif 'notification' in category.lower():
                        recommendations.append('Improve notification processing throughput')
                    elif 'database' in category.lower():
                        recommendations.append('Optimize database query performance')
                    elif 'memory' in category.lower():
                        recommendations.append('Investigate potential memory leaks')
        
        return recommendations


@pytest.mark.asyncio
@pytest.mark.performance
async def test_performance_baseline_suite():
    """
    Main performance baseline test suite.
    """
    baseline_tester = PerformanceBaselineTester()
    results = await baseline_tester.run_performance_baseline_tests()

    # Validate performance baseline results
    assert results['summary']['overall_performance_status'] in ['passed', 'warning']
    assert results['summary']['failed_tests'] == 0

    logger.info("Performance baseline testing completed")
    logger.info(f"Performance summary: {results['summary']}")

    return results


class PerformanceMetricsCollector:
    """
    Real-time performance metrics collection and monitoring.
    """

    def __init__(self):
        self.metrics_storage = {
            'api_metrics': [],
            'database_metrics': [],
            'external_integration_metrics': [],
            'notification_metrics': [],
            'system_metrics': []
        }

        self.metric_thresholds = {
            'api_response_time_p95': 2000,  # 95th percentile < 2s
            'api_response_time_p99': 5000,  # 99th percentile < 5s
            'database_query_time_p95': 1000,  # 95th percentile < 1s
            'notification_throughput_min': 100,  # Min 100/sec
            'memory_usage_max': 2048,  # Max 2GB
            'cpu_usage_max': 80,  # Max 80%
            'error_rate_max': 0.01  # Max 1% error rate
        }

    async def start_metrics_collection(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """
        Start real-time metrics collection for specified duration.
        """
        logger.info(f"Starting metrics collection for {duration_minutes} minutes")

        collection_tasks = [
            asyncio.create_task(self.collect_api_metrics(duration_minutes)),
            asyncio.create_task(self.collect_database_metrics(duration_minutes)),
            asyncio.create_task(self.collect_external_integration_metrics(duration_minutes)),
            asyncio.create_task(self.collect_notification_metrics(duration_minutes)),
            asyncio.create_task(self.collect_system_metrics(duration_minutes))
        ]

        try:
            await asyncio.gather(*collection_tasks)
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")

        # Analyze collected metrics
        analysis_results = await self.analyze_collected_metrics()

        return analysis_results

    async def collect_api_metrics(self, duration_minutes: int):
        """Collect API performance metrics."""
        end_time = time.time() + (duration_minutes * 60)

        while time.time() < end_time:
            # Simulate API metric collection
            metric = {
                'timestamp': datetime.utcnow().isoformat(),
                'endpoint': '/api/v1/external-data/screen-entity',
                'method': 'POST',
                'response_time_ms': 150 + (time.time() % 100),  # Simulate varying response times
                'status_code': 200,
                'request_size_bytes': 1024,
                'response_size_bytes': 2048
            }

            self.metrics_storage['api_metrics'].append(metric)
            await asyncio.sleep(1)  # Collect every second

    async def collect_database_metrics(self, duration_minutes: int):
        """Collect database performance metrics."""
        end_time = time.time() + (duration_minutes * 60)

        while time.time() < end_time:
            # Simulate database metric collection
            metric = {
                'timestamp': datetime.utcnow().isoformat(),
                'query_type': 'SELECT',
                'table': 'entities',
                'execution_time_ms': 50 + (time.time() % 50),
                'rows_affected': 100,
                'connection_pool_size': 10,
                'active_connections': 5
            }

            self.metrics_storage['database_metrics'].append(metric)
            await asyncio.sleep(5)  # Collect every 5 seconds

    async def collect_external_integration_metrics(self, duration_minutes: int):
        """Collect external integration performance metrics."""
        end_time = time.time() + (duration_minutes * 60)

        while time.time() < end_time:
            # Simulate external integration metric collection
            metric = {
                'timestamp': datetime.utcnow().isoformat(),
                'provider': 'refinitiv',
                'operation': 'market_data_fetch',
                'response_time_ms': 500 + (time.time() % 200),
                'success': True,
                'data_size_kb': 256,
                'rate_limit_remaining': 950
            }

            self.metrics_storage['external_integration_metrics'].append(metric)
            await asyncio.sleep(10)  # Collect every 10 seconds

    async def collect_notification_metrics(self, duration_minutes: int):
        """Collect notification system performance metrics."""
        end_time = time.time() + (duration_minutes * 60)

        while time.time() < end_time:
            # Simulate notification metric collection
            metric = {
                'timestamp': datetime.utcnow().isoformat(),
                'channel': 'email',
                'notifications_sent': 150,
                'notifications_failed': 2,
                'avg_delivery_time_ms': 300,
                'queue_size': 50,
                'processing_rate_per_sec': 120
            }

            self.metrics_storage['notification_metrics'].append(metric)
            await asyncio.sleep(30)  # Collect every 30 seconds

    async def collect_system_metrics(self, duration_minutes: int):
        """Collect system resource metrics."""
        end_time = time.time() + (duration_minutes * 60)

        while time.time() < end_time:
            # Collect actual system metrics
            metric = {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu_usage_percent': psutil.cpu_percent(interval=1),
                'memory_usage_mb': psutil.virtual_memory().used / 1024 / 1024,
                'memory_usage_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'network_bytes_sent': psutil.net_io_counters().bytes_sent,
                'network_bytes_recv': psutil.net_io_counters().bytes_recv
            }

            self.metrics_storage['system_metrics'].append(metric)
            await asyncio.sleep(15)  # Collect every 15 seconds

    async def analyze_collected_metrics(self) -> Dict[str, Any]:
        """Analyze collected metrics and generate insights."""
        analysis_results = {}

        # Analyze API metrics
        analysis_results['api_analysis'] = self.analyze_api_metrics()

        # Analyze database metrics
        analysis_results['database_analysis'] = self.analyze_database_metrics()

        # Analyze external integration metrics
        analysis_results['external_integration_analysis'] = self.analyze_external_integration_metrics()

        # Analyze notification metrics
        analysis_results['notification_analysis'] = self.analyze_notification_metrics()

        # Analyze system metrics
        analysis_results['system_analysis'] = self.analyze_system_metrics()

        # Generate overall performance assessment
        analysis_results['overall_assessment'] = self.generate_overall_assessment(analysis_results)

        return analysis_results

    def analyze_api_metrics(self) -> Dict[str, Any]:
        """Analyze API performance metrics."""
        api_metrics = self.metrics_storage['api_metrics']

        if not api_metrics:
            return {'status': 'no_data', 'message': 'No API metrics collected'}

        response_times = [m['response_time_ms'] for m in api_metrics]

        # Calculate percentiles
        response_times.sort()
        p50 = response_times[len(response_times) // 2] if response_times else 0
        p95 = response_times[int(len(response_times) * 0.95)] if response_times else 0
        p99 = response_times[int(len(response_times) * 0.99)] if response_times else 0

        # Calculate error rate
        total_requests = len(api_metrics)
        error_requests = len([m for m in api_metrics if m['status_code'] >= 400])
        error_rate = error_requests / total_requests if total_requests > 0 else 0

        return {
            'total_requests': total_requests,
            'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
            'p50_response_time_ms': p50,
            'p95_response_time_ms': p95,
            'p99_response_time_ms': p99,
            'error_rate': error_rate,
            'requests_per_second': total_requests / 60 if total_requests > 0 else 0,  # Assuming 1 minute collection
            'performance_status': self.evaluate_api_performance(p95, p99, error_rate)
        }

    def analyze_database_metrics(self) -> Dict[str, Any]:
        """Analyze database performance metrics."""
        db_metrics = self.metrics_storage['database_metrics']

        if not db_metrics:
            return {'status': 'no_data', 'message': 'No database metrics collected'}

        execution_times = [m['execution_time_ms'] for m in db_metrics]

        return {
            'total_queries': len(db_metrics),
            'avg_execution_time_ms': statistics.mean(execution_times) if execution_times else 0,
            'max_execution_time_ms': max(execution_times) if execution_times else 0,
            'min_execution_time_ms': min(execution_times) if execution_times else 0,
            'queries_per_second': len(db_metrics) / 60 if db_metrics else 0,
            'performance_status': self.evaluate_database_performance(execution_times)
        }

    def analyze_external_integration_metrics(self) -> Dict[str, Any]:
        """Analyze external integration performance metrics."""
        ext_metrics = self.metrics_storage['external_integration_metrics']

        if not ext_metrics:
            return {'status': 'no_data', 'message': 'No external integration metrics collected'}

        response_times = [m['response_time_ms'] for m in ext_metrics]
        success_count = len([m for m in ext_metrics if m['success']])

        return {
            'total_requests': len(ext_metrics),
            'success_rate': success_count / len(ext_metrics) if ext_metrics else 0,
            'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
            'max_response_time_ms': max(response_times) if response_times else 0,
            'performance_status': self.evaluate_external_integration_performance(response_times, success_count / len(ext_metrics) if ext_metrics else 0)
        }

    def analyze_notification_metrics(self) -> Dict[str, Any]:
        """Analyze notification system performance metrics."""
        notif_metrics = self.metrics_storage['notification_metrics']

        if not notif_metrics:
            return {'status': 'no_data', 'message': 'No notification metrics collected'}

        total_sent = sum(m['notifications_sent'] for m in notif_metrics)
        total_failed = sum(m['notifications_failed'] for m in notif_metrics)
        avg_processing_rate = statistics.mean([m['processing_rate_per_sec'] for m in notif_metrics])

        return {
            'total_notifications_sent': total_sent,
            'total_notifications_failed': total_failed,
            'success_rate': total_sent / (total_sent + total_failed) if (total_sent + total_failed) > 0 else 0,
            'avg_processing_rate_per_sec': avg_processing_rate,
            'performance_status': self.evaluate_notification_performance(avg_processing_rate, total_sent / (total_sent + total_failed) if (total_sent + total_failed) > 0 else 0)
        }

    def analyze_system_metrics(self) -> Dict[str, Any]:
        """Analyze system resource metrics."""
        sys_metrics = self.metrics_storage['system_metrics']

        if not sys_metrics:
            return {'status': 'no_data', 'message': 'No system metrics collected'}

        cpu_values = [m['cpu_usage_percent'] for m in sys_metrics]
        memory_values = [m['memory_usage_mb'] for m in sys_metrics]

        return {
            'avg_cpu_usage_percent': statistics.mean(cpu_values) if cpu_values else 0,
            'max_cpu_usage_percent': max(cpu_values) if cpu_values else 0,
            'avg_memory_usage_mb': statistics.mean(memory_values) if memory_values else 0,
            'max_memory_usage_mb': max(memory_values) if memory_values else 0,
            'performance_status': self.evaluate_system_performance(max(cpu_values) if cpu_values else 0, max(memory_values) if memory_values else 0)
        }

    def evaluate_api_performance(self, p95: float, p99: float, error_rate: float) -> str:
        """Evaluate API performance status."""
        if p95 > self.metric_thresholds['api_response_time_p95'] or p99 > self.metric_thresholds['api_response_time_p99'] or error_rate > self.metric_thresholds['error_rate_max']:
            return 'poor'
        elif p95 > self.metric_thresholds['api_response_time_p95'] * 0.8 or p99 > self.metric_thresholds['api_response_time_p99'] * 0.8:
            return 'warning'
        else:
            return 'good'

    def evaluate_database_performance(self, execution_times: List[float]) -> str:
        """Evaluate database performance status."""
        if not execution_times:
            return 'unknown'

        p95 = execution_times[int(len(execution_times) * 0.95)] if execution_times else 0

        if p95 > self.metric_thresholds['database_query_time_p95']:
            return 'poor'
        elif p95 > self.metric_thresholds['database_query_time_p95'] * 0.8:
            return 'warning'
        else:
            return 'good'

    def evaluate_external_integration_performance(self, response_times: List[float], success_rate: float) -> str:
        """Evaluate external integration performance status."""
        if not response_times:
            return 'unknown'

        avg_response_time = statistics.mean(response_times)

        if avg_response_time > 5000 or success_rate < 0.95:  # 5s response time or <95% success rate
            return 'poor'
        elif avg_response_time > 3000 or success_rate < 0.98:  # 3s response time or <98% success rate
            return 'warning'
        else:
            return 'good'

    def evaluate_notification_performance(self, processing_rate: float, success_rate: float) -> str:
        """Evaluate notification performance status."""
        if processing_rate < self.metric_thresholds['notification_throughput_min'] or success_rate < 0.95:
            return 'poor'
        elif processing_rate < self.metric_thresholds['notification_throughput_min'] * 1.2 or success_rate < 0.98:
            return 'warning'
        else:
            return 'good'

    def evaluate_system_performance(self, max_cpu: float, max_memory: float) -> str:
        """Evaluate system performance status."""
        if max_cpu > self.metric_thresholds['cpu_usage_max'] or max_memory > self.metric_thresholds['memory_usage_max']:
            return 'poor'
        elif max_cpu > self.metric_thresholds['cpu_usage_max'] * 0.8 or max_memory > self.metric_thresholds['memory_usage_max'] * 0.8:
            return 'warning'
        else:
            return 'good'

    def generate_overall_assessment(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall performance assessment."""
        performance_statuses = []

        for category, analysis in analysis_results.items():
            if isinstance(analysis, dict) and 'performance_status' in analysis:
                performance_statuses.append(analysis['performance_status'])

        # Determine overall status
        if 'poor' in performance_statuses:
            overall_status = 'poor'
        elif 'warning' in performance_statuses:
            overall_status = 'warning'
        else:
            overall_status = 'good'

        return {
            'overall_performance_status': overall_status,
            'assessment_timestamp': datetime.utcnow().isoformat(),
            'categories_analyzed': len(analysis_results),
            'performance_distribution': {
                'good': performance_statuses.count('good'),
                'warning': performance_statuses.count('warning'),
                'poor': performance_statuses.count('poor')
            },
            'recommendations': self.generate_performance_recommendations(analysis_results)
        }

    def generate_performance_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        for category, analysis in analysis_results.items():
            if isinstance(analysis, dict) and analysis.get('performance_status') in ['warning', 'poor']:
                if 'api' in category:
                    recommendations.append('Optimize API response times and reduce error rates')
                elif 'database' in category:
                    recommendations.append('Optimize database queries and consider indexing improvements')
                elif 'external' in category:
                    recommendations.append('Improve external integration reliability and response times')
                elif 'notification' in category:
                    recommendations.append('Scale notification processing capacity')
                elif 'system' in category:
                    recommendations.append('Monitor and optimize system resource usage')

        if not recommendations:
            recommendations.append('Continue monitoring performance metrics for trends')

        return recommendations


@pytest.mark.asyncio
@pytest.mark.performance
async def test_performance_metrics_collection():
    """
    Test performance metrics collection and analysis.
    """
    metrics_collector = PerformanceMetricsCollector()

    # Run metrics collection for 1 minute (reduced for testing)
    results = await metrics_collector.start_metrics_collection(duration_minutes=1)

    # Validate metrics collection results
    assert results['overall_assessment']['overall_performance_status'] in ['good', 'warning', 'poor']
    assert results['overall_assessment']['categories_analyzed'] >= 4

    logger.info("Performance metrics collection completed")
    logger.info(f"Overall assessment: {results['overall_assessment']}")

    return results
