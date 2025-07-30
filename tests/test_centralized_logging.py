"""
Tests for RegulensAI Centralized Logging System
Comprehensive testing of log aggregation, shipping, and ELK stack integration.
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

# Import logging components
from core_infra.logging.centralized_logging import (
    LogEntry,
    LogLevel,
    LogCategory,
    LogShipper,
    CentralizedLogger,
    LoggingManager,
    logging_manager,
    PerformanceLogger
)


class TestLogEntry:
    """Test log entry functionality."""
    
    def test_log_entry_creation(self):
        """Test log entry creation with all fields."""
        timestamp = datetime.utcnow()
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.INFO,
            category=LogCategory.APPLICATION,
            service="regulensai",
            message="Test message",
            logger_name="test_logger",
            module="test_module",
            function="test_function",
            line_number=42,
            thread_id="thread_123",
            process_id=1234,
            user_id="user_123",
            tenant_id="tenant_456",
            request_id="req_789",
            tags={"environment": "test"},
            extra_data={"key": "value"}
        )
        
        assert log_entry.timestamp == timestamp
        assert log_entry.level == LogLevel.INFO
        assert log_entry.category == LogCategory.APPLICATION
        assert log_entry.service == "regulensai"
        assert log_entry.message == "Test message"
        assert log_entry.user_id == "user_123"
        assert log_entry.tags["environment"] == "test"
        assert log_entry.extra_data["key"] == "value"
    
    def test_log_entry_to_dict(self):
        """Test log entry serialization to dictionary."""
        timestamp = datetime.utcnow()
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.ERROR,
            category=LogCategory.SECURITY,
            service="regulensai",
            message="Security alert",
            logger_name="security_logger",
            module="auth",
            function="login",
            line_number=100,
            thread_id="thread_456",
            process_id=5678
        )
        
        data = log_entry.to_dict()
        
        assert data["timestamp"] == timestamp.isoformat()
        assert data["@timestamp"] == timestamp.isoformat()  # Elasticsearch standard
        assert data["level"] == "ERROR"
        assert data["category"] == "security"
        assert data["message"] == "Security alert"
        assert data["module"] == "auth"
    
    def test_log_entry_to_json(self):
        """Test log entry serialization to JSON."""
        timestamp = datetime.utcnow()
        
        log_entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.WARNING,
            category=LogCategory.PERFORMANCE,
            service="regulensai",
            message="Performance warning",
            logger_name="perf_logger",
            module="api",
            function="process_request",
            line_number=200,
            thread_id="thread_789",
            process_id=9012,
            duration_ms=1500.5
        )
        
        json_str = log_entry.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["level"] == "WARNING"
        assert parsed["category"] == "performance"
        assert parsed["duration_ms"] == 1500.5
        assert "@timestamp" in parsed


class TestLogShipper:
    """Test log shipper functionality."""
    
    @pytest.fixture
    def log_shipper_config(self):
        """Create log shipper configuration for testing."""
        return {
            'buffer_size': 10,
            'flush_interval': 1,
            'retry_attempts': 2,
            'retry_delay': 1,
            'elasticsearch': {
                'enabled': False  # Disable for testing
            },
            'file_output': {
                'directory': '/tmp/test_logs'
            },
            'external_services': {
                'webhooks': [],
                'siem': {'enabled': False}
            }
        }
    
    @pytest.fixture
    def log_shipper(self, log_shipper_config):
        """Create log shipper instance for testing."""
        return LogShipper(log_shipper_config)
    
    @pytest.mark.asyncio
    async def test_log_shipper_initialization(self, log_shipper):
        """Test log shipper initialization."""
        assert log_shipper.buffer_size == 10
        assert log_shipper.flush_interval == 1
        assert log_shipper.retry_attempts == 2
        assert len(log_shipper.buffer) == 0
    
    @pytest.mark.asyncio
    async def test_log_shipper_start_stop(self, log_shipper):
        """Test log shipper start and stop."""
        await log_shipper.start()
        assert log_shipper.running is True
        assert log_shipper._flush_task is not None
        
        await log_shipper.stop()
        assert log_shipper.running is False
    
    @pytest.mark.asyncio
    async def test_ship_single_log(self, log_shipper):
        """Test shipping a single log entry."""
        log_entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            category=LogCategory.APPLICATION,
            service="test",
            message="Test log",
            logger_name="test",
            module="test",
            function="test",
            line_number=1,
            thread_id="1",
            process_id=1
        )
        
        await log_shipper.ship_log(log_entry)
        
        assert len(log_shipper.buffer) == 1
        assert log_shipper.buffer[0] == log_entry
    
    @pytest.mark.asyncio
    async def test_ship_multiple_logs(self, log_shipper):
        """Test shipping multiple log entries."""
        log_entries = []
        for i in range(5):
            log_entries.append(LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.INFO,
                category=LogCategory.APPLICATION,
                service="test",
                message=f"Test log {i}",
                logger_name="test",
                module="test",
                function="test",
                line_number=i,
                thread_id="1",
                process_id=1
            ))
        
        await log_shipper.ship_logs(log_entries)
        
        assert len(log_shipper.buffer) == 5
    
    @pytest.mark.asyncio
    async def test_buffer_flush_on_size(self, log_shipper):
        """Test buffer flush when size limit is reached."""
        # Mock file output
        with patch.object(log_shipper, '_ship_to_file', new_callable=AsyncMock) as mock_file:
            # Fill buffer to capacity
            for i in range(log_shipper.buffer_size):
                log_entry = LogEntry(
                    timestamp=datetime.utcnow(),
                    level=LogLevel.INFO,
                    category=LogCategory.APPLICATION,
                    service="test",
                    message=f"Test log {i}",
                    logger_name="test",
                    module="test",
                    function="test",
                    line_number=i,
                    thread_id="1",
                    process_id=1
                )
                await log_shipper.ship_log(log_entry)
            
            # Buffer should be flushed
            mock_file.assert_called()
            assert len(log_shipper.buffer) == 0
    
    @pytest.mark.asyncio
    async def test_elasticsearch_index_naming(self, log_shipper):
        """Test Elasticsearch index naming convention."""
        log_entry = LogEntry(
            timestamp=datetime(2023, 12, 25, 10, 30, 0),
            level=LogLevel.ERROR,
            category=LogCategory.SECURITY,
            service="test",
            message="Test log",
            logger_name="test",
            module="test",
            function="test",
            line_number=1,
            thread_id="1",
            process_id=1
        )
        
        index_name = log_shipper._get_elasticsearch_index(log_entry)
        assert index_name == "regulensai-security-2023.12.25"
    
    @pytest.mark.asyncio
    async def test_log_level_comparison(self, log_shipper):
        """Test log level comparison functionality."""
        assert log_shipper._compare_log_levels(LogLevel.DEBUG, LogLevel.INFO) == -1
        assert log_shipper._compare_log_levels(LogLevel.INFO, LogLevel.INFO) == 0
        assert log_shipper._compare_log_levels(LogLevel.ERROR, LogLevel.WARNING) == 1
    
    @pytest.mark.asyncio
    async def test_webhook_filtering(self, log_shipper):
        """Test webhook log filtering."""
        webhook_config = {
            'filters': {
                'min_level': 'WARNING',
                'categories': ['security', 'error'],
                'tags': {'environment': 'production'}
            }
        }
        
        logs = [
            LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.DEBUG,
                category=LogCategory.APPLICATION,
                service="test", message="Debug log", logger_name="test",
                module="test", function="test", line_number=1,
                thread_id="1", process_id=1
            ),
            LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.ERROR,
                category=LogCategory.SECURITY,
                service="test", message="Security error", logger_name="test",
                module="test", function="test", line_number=2,
                thread_id="1", process_id=1,
                tags={'environment': 'production'}
            ),
            LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.WARNING,
                category=LogCategory.PERFORMANCE,
                service="test", message="Performance warning", logger_name="test",
                module="test", function="test", line_number=3,
                thread_id="1", process_id=1
            )
        ]
        
        filtered = log_shipper._filter_logs_for_webhook(logs, webhook_config)
        
        # Only the security error should pass all filters
        assert len(filtered) == 1
        assert filtered[0].level == LogLevel.ERROR
        assert filtered[0].category == LogCategory.SECURITY


class TestCentralizedLogger:
    """Test centralized logger functionality."""
    
    @pytest.fixture
    def mock_log_shipper(self):
        """Create mock log shipper."""
        return AsyncMock(spec=LogShipper)
    
    @pytest.fixture
    def centralized_logger(self, mock_log_shipper):
        """Create centralized logger instance."""
        return CentralizedLogger("test_logger", mock_log_shipper)
    
    @pytest.mark.asyncio
    async def test_logger_basic_logging(self, centralized_logger, mock_log_shipper):
        """Test basic logging functionality."""
        await centralized_logger.info("Test info message")
        
        mock_log_shipper.ship_log.assert_called_once()
        call_args = mock_log_shipper.ship_log.call_args[0]
        log_entry = call_args[0]
        
        assert log_entry.level == LogLevel.INFO
        assert log_entry.message == "Test info message"
        assert log_entry.logger_name == "test_logger"
    
    @pytest.mark.asyncio
    async def test_logger_with_context(self, centralized_logger, mock_log_shipper):
        """Test logger with context."""
        context_logger = centralized_logger.with_context(
            user_id="user_123",
            tenant_id="tenant_456"
        )
        
        await context_logger.warning("Test warning with context")
        
        mock_log_shipper.ship_log.assert_called_once()
        call_args = mock_log_shipper.ship_log.call_args[0]
        log_entry = call_args[0]
        
        assert log_entry.level == LogLevel.WARNING
        assert log_entry.user_id == "user_123"
        assert log_entry.tenant_id == "tenant_456"
    
    @pytest.mark.asyncio
    async def test_logger_specialized_methods(self, centralized_logger, mock_log_shipper):
        """Test specialized logging methods."""
        # Test audit logging
        await centralized_logger.audit("Audit message", user_id="user_123", action="login")
        
        call_args = mock_log_shipper.ship_log.call_args[0]
        log_entry = call_args[0]
        
        assert log_entry.category == LogCategory.AUDIT
        assert log_entry.level == LogLevel.INFO
        
        # Test security logging
        await centralized_logger.security("Security alert", level=LogLevel.CRITICAL)
        
        call_args = mock_log_shipper.ship_log.call_args[0]
        log_entry = call_args[0]
        
        assert log_entry.category == LogCategory.SECURITY
        assert log_entry.level == LogLevel.CRITICAL
        
        # Test performance logging
        await centralized_logger.performance("Slow operation", duration_ms=2500.0)
        
        call_args = mock_log_shipper.ship_log.call_args[0]
        log_entry = call_args[0]
        
        assert log_entry.category == LogCategory.PERFORMANCE
        assert log_entry.duration_ms == 2500.0


class TestLoggingManager:
    """Test logging manager functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.elasticsearch_enabled = False
        settings.log_buffer_size = 100
        settings.log_flush_interval = 30
        settings.file_logging_enabled = True
        settings.log_directory = "/tmp/test_logs"
        return settings
    
    @pytest.mark.asyncio
    async def test_logging_manager_initialization(self, mock_settings):
        """Test logging manager initialization."""
        with patch('core_infra.logging.centralized_logging.get_settings', return_value=mock_settings):
            manager = LoggingManager()
            
            assert manager.config['buffer_size'] == 100
            assert manager.config['flush_interval'] == 30
            assert manager.config['elasticsearch']['enabled'] is False
    
    @pytest.mark.asyncio
    async def test_logging_manager_start_stop(self, mock_settings):
        """Test logging manager start and stop."""
        with patch('core_infra.logging.centralized_logging.get_settings', return_value=mock_settings):
            manager = LoggingManager()
            
            with patch.object(manager, '_load_logging_config') as mock_config:
                mock_config.return_value = {
                    'buffer_size': 100,
                    'flush_interval': 30,
                    'elasticsearch': {'enabled': False},
                    'file_output': {'enabled': True, 'directory': '/tmp'},
                    'external_services': {'webhooks': [], 'siem': {'enabled': False}}
                }
                
                await manager.start()
                assert manager.running is True
                assert manager.log_shipper is not None
                
                await manager.stop()
                assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_get_logger(self, mock_settings):
        """Test logger creation and retrieval."""
        with patch('core_infra.logging.centralized_logging.get_settings', return_value=mock_settings):
            manager = LoggingManager()
            manager.log_shipper = AsyncMock(spec=LogShipper)
            
            logger1 = manager.get_logger("test_logger")
            logger2 = manager.get_logger("test_logger")
            
            # Should return the same instance
            assert logger1 is logger2
            assert logger1.name == "test_logger"
            assert len(manager.loggers) == 1
    
    @pytest.mark.asyncio
    async def test_logging_statistics(self, mock_settings):
        """Test logging statistics collection."""
        with patch('core_infra.logging.centralized_logging.get_settings', return_value=mock_settings):
            manager = LoggingManager()
            manager.running = True
            manager.log_shipper = Mock()
            manager.log_shipper.buffer = [1, 2, 3]  # Mock buffer with 3 items
            manager.log_shipper.buffer_size = 1000
            manager.loggers = {"logger1": Mock(), "logger2": Mock()}
            
            stats = await manager.get_log_statistics()
            
            assert stats["status"] == "running"
            assert stats["buffer_size"] == 3
            assert stats["max_buffer_size"] == 1000
            assert stats["active_loggers"] == 2
            assert "logger1" in stats["logger_names"]
            assert "logger2" in stats["logger_names"]


class TestPerformanceLogger:
    """Test performance logging context manager."""
    
    @pytest.mark.asyncio
    async def test_performance_logger_success(self):
        """Test performance logger with successful operation."""
        mock_logger = AsyncMock(spec=CentralizedLogger)
        
        async with PerformanceLogger(mock_logger, "test_operation", user_id="user_123"):
            await asyncio.sleep(0.01)  # Simulate work
        
        # Should have called performance logging twice (start and complete)
        assert mock_logger.performance.call_count == 2
        
        # Check start call
        start_call = mock_logger.performance.call_args_list[0]
        assert "Starting test_operation" in start_call[0][0]
        
        # Check complete call
        complete_call = mock_logger.performance.call_args_list[1]
        assert "Completed test_operation" in complete_call[0][0]
        assert "duration_ms" in complete_call[1]
    
    @pytest.mark.asyncio
    async def test_performance_logger_error(self):
        """Test performance logger with error."""
        mock_logger = AsyncMock(spec=CentralizedLogger)
        
        with pytest.raises(ValueError):
            async with PerformanceLogger(mock_logger, "test_operation"):
                raise ValueError("Test error")
        
        # Should have called performance once (start) and error once
        assert mock_logger.performance.call_count == 1
        assert mock_logger.error.call_count == 1
        
        # Check error call
        error_call = mock_logger.error.call_args_list[0]
        assert "Failed test_operation" in error_call[0][0]
        assert "duration_ms" in error_call[1]
        assert "error" in error_call[1]


class TestELKStackIntegration:
    """Test ELK stack integration."""
    
    def test_elasticsearch_config_exists(self):
        """Test that Elasticsearch configuration exists."""
        config_path = Path(__file__).parent.parent / "deployment/logging/elasticsearch/config/elasticsearch.yml"
        assert config_path.exists()
    
    def test_logstash_config_exists(self):
        """Test that Logstash configuration exists."""
        config_path = Path(__file__).parent.parent / "deployment/logging/logstash/config/logstash.yml"
        assert config_path.exists()
        
        pipeline_path = Path(__file__).parent.parent / "deployment/logging/logstash/pipeline/regulensai.conf"
        assert pipeline_path.exists()
    
    def test_kibana_config_exists(self):
        """Test that Kibana configuration exists."""
        config_path = Path(__file__).parent.parent / "deployment/logging/kibana/config/kibana.yml"
        assert config_path.exists()
    
    def test_filebeat_config_exists(self):
        """Test that Filebeat configuration exists."""
        config_path = Path(__file__).parent.parent / "deployment/logging/filebeat/config/filebeat.yml"
        assert config_path.exists()
    
    def test_docker_compose_exists(self):
        """Test that Docker Compose configuration exists."""
        compose_path = Path(__file__).parent.parent / "deployment/logging/docker-compose.elk.yml"
        assert compose_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
