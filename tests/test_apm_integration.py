"""
Tests for RegulensAI Application Performance Monitoring (APM) Integration
Comprehensive testing of APM providers, performance tracking, error monitoring, and regression detection.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

# Import APM components
from core_infra.monitoring.apm_integration import (
    PerformanceMetric,
    PerformanceMetricType,
    ErrorEvent,
    PerformanceBaseline,
    DatabaseQueryTracker,
    ErrorTracker,
    PerformanceRegressionDetector,
    ResourceMonitor,
    APMManager,
    ElasticAPMProvider,
    CustomAPMProvider,
    apm_manager,
    track_performance,
    track_compliance_processing_time,
    track_database_operation
)
from core_infra.monitoring.apm_database import APMDatabaseConnection, APMDatabasePool


class TestPerformanceMetric:
    """Test performance metric functionality."""
    
    def test_performance_metric_creation(self):
        """Test performance metric creation."""
        timestamp = datetime.utcnow()
        
        metric = PerformanceMetric(
            timestamp=timestamp,
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            value=150.5,
            unit="milliseconds",
            service="api",
            operation="get_regulations",
            tags={"endpoint": "/api/v1/regulations"},
            metadata={"user_id": "user_123"}
        )
        
        assert metric.timestamp == timestamp
        assert metric.metric_type == PerformanceMetricType.RESPONSE_TIME
        assert metric.value == 150.5
        assert metric.unit == "milliseconds"
        assert metric.service == "api"
        assert metric.operation == "get_regulations"
        assert metric.tags["endpoint"] == "/api/v1/regulations"
        assert metric.metadata["user_id"] == "user_123"


class TestErrorEvent:
    """Test error event functionality."""
    
    def test_error_event_creation(self):
        """Test error event creation."""
        timestamp = datetime.utcnow()
        
        error_event = ErrorEvent(
            timestamp=timestamp,
            error_id="error_123",
            error_type="ValueError",
            error_message="Invalid input",
            stack_trace="Traceback...",
            service="api",
            operation="validate_input",
            user_id="user_123",
            tenant_id="tenant_456",
            severity="error",
            tags={"endpoint": "/api/v1/validate"},
            context={"input_data": "invalid"}
        )
        
        assert error_event.timestamp == timestamp
        assert error_event.error_id == "error_123"
        assert error_event.error_type == "ValueError"
        assert error_event.error_message == "Invalid input"
        assert error_event.service == "api"
        assert error_event.user_id == "user_123"
        assert error_event.tenant_id == "tenant_456"
        assert error_event.tags["endpoint"] == "/api/v1/validate"
        assert error_event.context["input_data"] == "invalid"


class TestDatabaseQueryTracker:
    """Test database query tracking functionality."""
    
    @pytest.fixture
    def query_tracker(self):
        """Create database query tracker instance."""
        return DatabaseQueryTracker()
    
    @pytest.mark.asyncio
    async def test_track_query(self, query_tracker):
        """Test query tracking."""
        query = "SELECT * FROM regulations WHERE id = $1"
        execution_time = 0.15
        
        await query_tracker.track_query(query, execution_time)
        
        normalized_query = query_tracker._normalize_query(query)
        assert normalized_query in query_tracker.query_stats
        
        stats = query_tracker.query_stats[normalized_query]
        assert stats['count'] == 1
        assert stats['total_time'] == execution_time
        assert stats['avg_time'] == execution_time
        assert stats['min_time'] == execution_time
        assert stats['max_time'] == execution_time
        assert stats['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_track_query_with_error(self, query_tracker):
        """Test query tracking with error."""
        query = "SELECT * FROM invalid_table"
        execution_time = 0.05
        error = Exception("Table does not exist")
        
        await query_tracker.track_query(query, execution_time, error)
        
        normalized_query = query_tracker._normalize_query(query)
        stats = query_tracker.query_stats[normalized_query]
        assert stats['count'] == 1
        assert stats['errors'] == 1
    
    def test_normalize_query(self, query_tracker):
        """Test query normalization."""
        # Test string literal replacement
        query1 = "SELECT * FROM users WHERE name = 'John Doe'"
        normalized1 = query_tracker._normalize_query(query1)
        assert "'JOHN DOE'" not in normalized1
        assert "'?'" in normalized1
        
        # Test numeric literal replacement
        query2 = "SELECT * FROM orders WHERE amount > 100"
        normalized2 = query_tracker._normalize_query(query2)
        assert "100" not in normalized2
        assert "?" in normalized2
        
        # Test parameter placeholder replacement
        query3 = "SELECT * FROM users WHERE id = $1 AND status = $2"
        normalized3 = query_tracker._normalize_query(query3)
        assert "$1" not in normalized3
        assert "$2" not in normalized3
        assert "$?" in normalized3
    
    @pytest.mark.asyncio
    async def test_get_slow_queries(self, query_tracker):
        """Test slow query retrieval."""
        # Add some queries with different execution times
        queries = [
            ("SELECT * FROM fast_table", 0.01),
            ("SELECT * FROM slow_table", 2.5),
            ("SELECT * FROM medium_table", 0.8),
            ("SELECT * FROM very_slow_table", 5.0)
        ]
        
        for query, execution_time in queries:
            await query_tracker.track_query(query, execution_time)
        
        slow_queries = query_tracker.get_slow_queries(limit=2)
        
        assert len(slow_queries) <= 2
        # Should be sorted by execution time (descending)
        if len(slow_queries) > 1:
            assert slow_queries[0]['execution_time'] >= slow_queries[1]['execution_time']
    
    def test_get_query_statistics(self, query_tracker):
        """Test query statistics calculation."""
        # Initially empty
        stats = query_tracker.get_query_statistics()
        assert stats['total_queries'] == 0
        assert stats['total_execution_time'] == 0
        assert stats['average_query_time'] == 0
        assert stats['error_rate'] == 0


class TestErrorTracker:
    """Test error tracking functionality."""
    
    @pytest.fixture
    def error_tracker(self):
        """Create error tracker instance."""
        return ErrorTracker()
    
    @pytest.mark.asyncio
    async def test_track_error(self, error_tracker):
        """Test error tracking."""
        error_event = ErrorEvent(
            timestamp=datetime.utcnow(),
            error_id="error_123",
            error_type="ValueError",
            error_message="Test error",
            stack_trace="Traceback...",
            service="api",
            operation="test_operation",
            user_id="user_123",
            tenant_id="tenant_456"
        )
        
        await error_tracker.track_error(error_event)
        
        assert len(error_tracker.error_buffer) == 1
        assert error_tracker.error_buffer[0] == error_event
        
        # Check aggregation
        error_signature = f"{error_event.error_type}:{error_event.service}:{error_event.operation}"
        assert error_signature in error_tracker.error_aggregates
        
        aggregate = error_tracker.error_aggregates[error_signature]
        assert aggregate['count'] == 1
        assert aggregate['first_seen'] == error_event.timestamp
        assert aggregate['last_seen'] == error_event.timestamp
        assert error_event.user_id in aggregate['affected_users']
        assert error_event.tenant_id in aggregate['affected_tenants']
    
    def test_get_error_rate(self, error_tracker):
        """Test error rate calculation."""
        # Add some errors
        now = datetime.utcnow()
        for i in range(5):
            error_tracker.error_rate_window.append(now - timedelta(minutes=i))
        
        error_rate = error_tracker.get_error_rate(window_minutes=10)
        assert error_rate == 0.5  # 5 errors in 10 minutes = 0.5 errors/minute
    
    def test_get_top_errors(self, error_tracker):
        """Test top errors retrieval."""
        # Create error aggregates manually for testing
        error_tracker.error_aggregates["ValueError:api:operation1"] = {
            'count': 10,
            'first_seen': datetime.utcnow(),
            'last_seen': datetime.utcnow(),
            'affected_users': {'user1', 'user2'},
            'affected_tenants': {'tenant1'},
            'stack_traces': []
        }
        
        error_tracker.error_aggregates["TypeError:api:operation2"] = {
            'count': 5,
            'first_seen': datetime.utcnow(),
            'last_seen': datetime.utcnow(),
            'affected_users': {'user3'},
            'affected_tenants': {'tenant2'},
            'stack_traces': []
        }
        
        top_errors = error_tracker.get_top_errors(limit=2)
        
        assert len(top_errors) == 2
        # Should be sorted by count (descending)
        assert top_errors[0]['count'] >= top_errors[1]['count']
        assert top_errors[0]['error_signature'] == "ValueError:api:operation1"


class TestPerformanceRegressionDetector:
    """Test performance regression detection."""
    
    @pytest.fixture
    def regression_detector(self):
        """Create regression detector instance."""
        return PerformanceRegressionDetector()
    
    def test_set_baseline(self, regression_detector):
        """Test baseline setting."""
        baseline = PerformanceBaseline(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            service="api",
            operation="get_regulations",
            baseline_value=100.0,
            threshold_percentage=20.0,
            measurement_window=timedelta(hours=1),
            last_updated=datetime.utcnow(),
            sample_count=100
        )
        
        regression_detector.set_baseline(baseline)
        
        key = f"{baseline.service}:{baseline.operation}:{baseline.metric_type.value}"
        assert key in regression_detector.baselines
        assert regression_detector.baselines[key] == baseline
    
    @pytest.mark.asyncio
    async def test_check_performance_no_regression(self, regression_detector):
        """Test performance check without regression."""
        # Set baseline
        baseline = PerformanceBaseline(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            service="api",
            operation="test_operation",
            baseline_value=100.0,
            threshold_percentage=20.0,
            measurement_window=timedelta(hours=1),
            last_updated=datetime.utcnow(),
            sample_count=100
        )
        regression_detector.set_baseline(baseline)
        
        # Add measurements within acceptable range
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                value=110.0,  # 10% increase, within 20% threshold
                unit="milliseconds",
                service="api",
                operation="test_operation"
            )
            
            result = await regression_detector.check_performance(metric)
            
        # Should not detect regression
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_performance_with_regression(self, regression_detector):
        """Test performance check with regression."""
        # Set baseline
        baseline = PerformanceBaseline(
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            service="api",
            operation="test_operation",
            baseline_value=100.0,
            threshold_percentage=20.0,
            measurement_window=timedelta(hours=1),
            last_updated=datetime.utcnow(),
            sample_count=100
        )
        regression_detector.set_baseline(baseline)
        
        # Add measurements that exceed threshold
        for i in range(10):
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                metric_type=PerformanceMetricType.RESPONSE_TIME,
                value=150.0,  # 50% increase, exceeds 20% threshold
                unit="milliseconds",
                service="api",
                operation="test_operation"
            )
            
            result = await regression_detector.check_performance(metric)
        
        # Should detect regression after enough measurements
        assert result is not None
        assert result['service'] == "api"
        assert result['operation'] == "test_operation"
        assert result['regression_percentage'] > 20.0


class TestResourceMonitor:
    """Test resource monitoring functionality."""
    
    @pytest.fixture
    def resource_monitor(self):
        """Create resource monitor instance."""
        return ResourceMonitor()
    
    @pytest.mark.asyncio
    async def test_collect_resource_metrics(self, resource_monitor):
        """Test resource metrics collection."""
        metrics = await resource_monitor.collect_resource_metrics()
        
        # Check that expected metrics are present
        expected_metrics = [
            'cpu_percent', 'memory_rss', 'memory_vms', 'memory_percent',
            'io_read_bytes', 'io_write_bytes', 'threads'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))
    
    def test_get_resource_trends(self, resource_monitor):
        """Test resource trend analysis."""
        # Add some test data
        now = datetime.utcnow()
        test_data = [
            (now - timedelta(minutes=5), 50.0),
            (now - timedelta(minutes=4), 55.0),
            (now - timedelta(minutes=3), 60.0),
            (now - timedelta(minutes=2), 65.0),
            (now - timedelta(minutes=1), 70.0),
        ]
        
        resource_monitor.resource_history['cpu_percent'].extend(test_data)
        
        trends = resource_monitor.get_resource_trends('cpu_percent', window_minutes=10)
        
        assert 'current' in trends
        assert 'min' in trends
        assert 'max' in trends
        assert 'avg' in trends
        assert 'trend' in trends
        
        assert trends['current'] == 70.0
        assert trends['min'] == 50.0
        assert trends['max'] == 70.0
        assert trends['trend'] == 'increasing'


class TestAPMProviders:
    """Test APM provider implementations."""
    
    @pytest.mark.asyncio
    async def test_elastic_apm_provider_initialization(self):
        """Test Elastic APM provider initialization."""
        provider = ElasticAPMProvider()
        
        # Test initialization without elastic-apm package
        config = {
            'service_name': 'test_service',
            'server_url': 'http://localhost:8200',
            'environment': 'test'
        }
        
        await provider.initialize(config)
        
        # Should handle missing package gracefully
        assert provider.enabled is False
    
    @pytest.mark.asyncio
    async def test_custom_apm_provider(self):
        """Test custom APM provider."""
        provider = CustomAPMProvider()
        
        await provider.initialize({})
        
        assert provider.enabled is True
        
        # Test transaction tracking
        await provider.track_transaction(
            "test_operation",
            "api",
            150.0,
            method="GET",
            status_code="200"
        )
        
        # Test error tracking
        test_error = ValueError("Test error")
        await provider.track_error(test_error, {"service": "test"})


class TestAPMManager:
    """Test APM manager functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.elastic_apm_enabled = False
        settings.newrelic_enabled = False
        settings.datadog_apm_enabled = False
        settings.performance_monitoring_enabled = True
        settings.db_performance_monitoring_enabled = True
        settings.error_tracking_enabled = True
        settings.resource_monitoring_enabled = True
        settings.business_metrics_enabled = True
        return settings
    
    @pytest.mark.asyncio
    async def test_apm_manager_initialization(self, mock_settings):
        """Test APM manager initialization."""
        with patch('core_infra.monitoring.apm_integration.get_settings', return_value=mock_settings):
            manager = APMManager()
            
            await manager.initialize()
            
            assert manager.running is True
            assert len(manager.providers) > 0  # Should have at least custom provider
            assert len(manager._monitoring_tasks) > 0
    
    @pytest.mark.asyncio
    async def test_apm_manager_track_operation(self, mock_settings):
        """Test operation tracking."""
        with patch('core_infra.monitoring.apm_integration.get_settings', return_value=mock_settings):
            manager = APMManager()
            await manager.initialize()
            
            # Test successful operation
            async with manager.track_operation("test_operation", "api", user_id="user_123"):
                await asyncio.sleep(0.01)  # Simulate work
            
            # Test operation with error
            with pytest.raises(ValueError):
                async with manager.track_operation("failing_operation", "api"):
                    raise ValueError("Test error")
            
            # Check that error was tracked
            assert len(manager.error_tracker.error_buffer) > 0
    
    @pytest.mark.asyncio
    async def test_track_business_metric(self, mock_settings):
        """Test business metric tracking."""
        with patch('core_infra.monitoring.apm_integration.get_settings', return_value=mock_settings):
            manager = APMManager()
            await manager.initialize()
            
            await manager.track_business_metric(
                'compliance_processing_times',
                25.5,
                regulation_type='basel_iii',
                tenant_id='tenant_123'
            )
            
            # Check that metric was stored
            assert len(manager.business_metrics['compliance_processing_times']) > 0
    
    @pytest.mark.asyncio
    async def test_get_performance_summary(self, mock_settings):
        """Test performance summary generation."""
        with patch('core_infra.monitoring.apm_integration.get_settings', return_value=mock_settings):
            manager = APMManager()
            await manager.initialize()
            
            summary = await manager.get_performance_summary()
            
            assert 'database_stats' in summary
            assert 'error_stats' in summary
            assert 'resource_stats' in summary
            assert 'business_metrics' in summary
            assert 'active_providers' in summary


class TestAPMDecorators:
    """Test APM decorators and utility functions."""
    
    @pytest.mark.asyncio
    async def test_track_performance_decorator(self):
        """Test performance tracking decorator."""
        @track_performance("test_operation", "api")
        async def test_function():
            await asyncio.sleep(0.01)
            return "success"
        
        # Mock the APM manager to avoid initialization
        with patch('core_infra.monitoring.apm_integration.apm_manager') as mock_manager:
            mock_manager.track_operation = AsyncMock()
            
            result = await test_function()
            
            assert result == "success"
            # Decorator should have called track_operation
            mock_manager.track_operation.assert_called()
    
    @pytest.mark.asyncio
    async def test_track_compliance_processing_time(self):
        """Test compliance processing time tracking."""
        with patch('core_infra.monitoring.apm_integration.apm_manager') as mock_manager:
            mock_manager.track_business_metric = AsyncMock()
            
            await track_compliance_processing_time(
                15.5,
                "mifid_ii",
                "tenant_123"
            )
            
            mock_manager.track_business_metric.assert_called_with(
                'compliance_processing_times',
                15.5,
                regulation_type="mifid_ii",
                tenant_id="tenant_123"
            )
    
    @pytest.mark.asyncio
    async def test_track_database_operation(self):
        """Test database operation tracking."""
        with patch('core_infra.monitoring.apm_integration.apm_manager') as mock_manager:
            mock_manager.track_database_query = AsyncMock()
            
            await track_database_operation(
                "SELECT * FROM regulations",
                0.15,
                None
            )
            
            mock_manager.track_database_query.assert_called_with(
                "SELECT * FROM regulations",
                0.15,
                None
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
