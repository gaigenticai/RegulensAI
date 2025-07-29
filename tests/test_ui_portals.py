"""
Test suite for UI Portal functionality
Comprehensive tests for portal management, testing capabilities, and analytics.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from core_infra.ui.portal_manager import (
    PortalSessionManager, PortalSearchManager, PortalAnalyticsManager,
    PortalType, EventType, PortalSession
)
from core_infra.ui.testing_portal import (
    APITestExecutor, TestSuiteManager, PerformanceTestManager, TestReportGenerator,
    TestType, TestStatus, TestExecution, TestSuite
)
from core_infra.ui import UIPortalFramework, initialize_ui_portals


class TestPortalSessionManager:
    """Test portal session management functionality."""
    
    @pytest.fixture
    def session_manager(self):
        return PortalSessionManager()
    
    @pytest.fixture
    def mock_database(self):
        with patch('core_infra.ui.portal_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            yield mock_conn
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, mock_database):
        """Test creating a new portal session."""
        # Mock database execution
        mock_database.execute = AsyncMock()
        
        # Create session
        session = await session_manager.create_session(
            portal_type=PortalType.DOCUMENTATION,
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        
        # Verify session properties
        assert session.portal_type == PortalType.DOCUMENTATION
        assert session.user_id == "test-user-id"
        assert session.tenant_id == "test-tenant-id"
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Test Browser"
        assert session.is_active is True
        assert session.session_id is not None
        
        # Verify database call
        mock_database.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_from_cache(self, session_manager):
        """Test retrieving session from cache."""
        # Create a mock session in cache
        session_id = "test-session-id"
        mock_session = PortalSession(
            id="test-id",
            session_id=session_id,
            portal_type=PortalType.TESTING,
            user_id="test-user",
            tenant_id="test-tenant",
            ip_address=None,
            user_agent=None,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True,
            session_data={}
        )
        
        session_manager.active_sessions[session_id] = mock_session
        
        # Retrieve session
        retrieved_session = await session_manager.get_session(session_id)
        
        # Verify session
        assert retrieved_session is not None
        assert retrieved_session.session_id == session_id
        assert retrieved_session.portal_type == PortalType.TESTING
    
    @pytest.mark.asyncio
    async def test_update_session_activity(self, session_manager, mock_database):
        """Test updating session activity."""
        # Mock database execution
        mock_database.execute = AsyncMock()
        
        # Create session in cache
        session_id = "test-session-id"
        mock_session = PortalSession(
            id="test-id",
            session_id=session_id,
            portal_type=PortalType.TESTING,
            user_id="test-user",
            tenant_id="test-tenant",
            ip_address=None,
            user_agent=None,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow() - timedelta(minutes=5),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True,
            session_data={}
        )
        
        session_manager.active_sessions[session_id] = mock_session
        
        # Update activity
        session_data = {"last_page": "/documentation/api"}
        success = await session_manager.update_session_activity(session_id, session_data)
        
        # Verify update
        assert success is True
        assert session_manager.active_sessions[session_id].session_data == session_data
        mock_database.execute.assert_called_once()


class TestPortalSearchManager:
    """Test portal search functionality."""
    
    @pytest.fixture
    def search_manager(self):
        return PortalSearchManager()
    
    @pytest.fixture
    def mock_database(self):
        with patch('core_infra.ui.portal_manager.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            yield mock_conn
    
    @pytest.mark.asyncio
    async def test_search_documentation(self, search_manager, mock_database):
        """Test documentation search functionality."""
        # Mock database execution
        mock_database.execute = AsyncMock()
        
        # Mock cache manager
        with patch('core_infra.ui.portal_manager.cache_manager') as mock_cache:
            mock_cache.get_cached_data = AsyncMock(return_value=None)
            mock_cache.set_cached_data = AsyncMock()
            
            # Perform search
            result = await search_manager.search_documentation(
                query="authentication",
                search_type="api",
                filters={"category": "security"},
                session_id="test-session",
                tenant_id="test-tenant"
            )
            
            # Verify result structure
            assert "query" in result
            assert "results" in result
            assert "execution_time_ms" in result
            assert "total_count" in result
            assert result["query"] == "authentication"
            
            # Verify cache calls
            mock_cache.get_cached_data.assert_called_once()
            mock_cache.set_cached_data.assert_called_once()
            
            # Verify database logging
            mock_database.execute.assert_called_once()


class TestAPITestExecutor:
    """Test API testing functionality."""
    
    @pytest.fixture
    def test_executor(self):
        return APITestExecutor()
    
    @pytest.fixture
    def mock_database(self):
        with patch('core_infra.ui.testing_portal.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            yield mock_conn
    
    @pytest.mark.asyncio
    async def test_execute_api_test_success(self, test_executor, mock_database):
        """Test successful API test execution."""
        # Mock database execution
        mock_database.execute = AsyncMock()
        
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_type = 'application/json'
        mock_response.json = AsyncMock(return_value={"status": "success"})
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            # Mock observability manager
            with patch('core_infra.ui.testing_portal.observability_manager') as mock_obs:
                mock_obs.metrics_collector.record_timer = AsyncMock()
                
                # Execute test
                result = await test_executor.execute_api_test(
                    session_id="test-session",
                    tenant_id="test-tenant",
                    endpoint_path="/api/v1/health",
                    http_method="GET",
                    request_data={}
                )
                
                # Verify result
                assert isinstance(result, TestExecution)
                assert result.success is True
                assert result.response_status_code == 200
                assert result.response_time_ms is not None
                assert result.error_message is None
                
                # Verify database call
                mock_database.execute.assert_called_once()
                
                # Verify metrics recording
                mock_obs.metrics_collector.record_timer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_api_test_failure(self, test_executor, mock_database):
        """Test API test execution with failure."""
        # Mock database execution
        mock_database.execute = AsyncMock()
        
        # Mock HTTP response with error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.content_type = 'application/json'
        mock_response.json = AsyncMock(return_value={"error": "Internal server error"})
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            # Mock observability manager
            with patch('core_infra.ui.testing_portal.observability_manager') as mock_obs:
                mock_obs.metrics_collector.record_timer = AsyncMock()
                
                # Execute test
                result = await test_executor.execute_api_test(
                    session_id="test-session",
                    tenant_id="test-tenant",
                    endpoint_path="/api/v1/error",
                    http_method="GET",
                    request_data={}
                )
                
                # Verify result
                assert isinstance(result, TestExecution)
                assert result.success is False
                assert result.response_status_code == 500
                assert result.response_time_ms is not None


class TestTestSuiteManager:
    """Test test suite management functionality."""
    
    @pytest.fixture
    def suite_manager(self):
        return TestSuiteManager()
    
    @pytest.fixture
    def mock_database(self):
        with patch('core_infra.ui.testing_portal.get_database') as mock_db:
            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn
            yield mock_conn
    
    @pytest.mark.asyncio
    async def test_create_test_suite(self, suite_manager, mock_database):
        """Test creating a new test suite."""
        # Mock database execution
        mock_database.execute = AsyncMock()
        
        # Mock cache manager
        with patch('core_infra.ui.testing_portal.cache_manager') as mock_cache:
            mock_cache.set_cached_data = AsyncMock()
            
            # Create test suite
            tests = [
                {
                    "name": "Health Check",
                    "endpoint_path": "/api/v1/health",
                    "http_method": "GET",
                    "request_data": {}
                }
            ]
            
            suite = await suite_manager.create_test_suite(
                name="API Health Tests",
                description="Basic health check tests",
                tests=tests,
                tenant_id="test-tenant",
                created_by="test-user"
            )
            
            # Verify suite
            assert isinstance(suite, TestSuite)
            assert suite.name == "API Health Tests"
            assert suite.description == "Basic health check tests"
            assert len(suite.tests) == 1
            assert suite.tenant_id == "test-tenant"
            assert suite.created_by == "test-user"
            
            # Verify database and cache calls
            mock_database.execute.assert_called_once()
            mock_cache.set_cached_data.assert_called_once()


class TestUIPortalFramework:
    """Test UI portal framework integration."""
    
    @pytest.fixture
    def framework(self):
        return UIPortalFramework()
    
    @pytest.mark.asyncio
    async def test_framework_initialization(self, framework):
        """Test framework initialization."""
        # Mock portal session manager initialization
        with patch('core_infra.ui.portal_manager.portal_session_manager') as mock_manager:
            mock_manager.initialize = AsyncMock()
            
            # Initialize framework
            await framework.initialize()
            
            # Verify initialization
            assert framework.initialized is True
            mock_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, framework):
        """Test framework health check."""
        # Initialize framework
        framework.initialized = True
        
        # Perform health check
        health_status = await framework.health_check()
        
        # Verify health status structure
        assert "overall_status" in health_status
        assert "components" in health_status
        assert "timestamp" in health_status
        
        # Verify all components are checked
        expected_components = [
            'portal_session_manager',
            'portal_search_manager',
            'portal_analytics_manager',
            'api_test_executor',
            'test_suite_manager',
            'performance_test_manager',
            'test_report_generator'
        ]
        
        for component in expected_components:
            assert component in health_status['components']
    
    def test_get_component_info(self, framework):
        """Test getting component information."""
        info = framework.get_component_info()
        
        # Verify info structure
        assert "framework_version" in info
        assert "initialized" in info
        assert "components" in info
        assert "supported_portal_types" in info
        assert "supported_test_types" in info
        assert "supported_event_types" in info
        
        # Verify portal types
        expected_portal_types = ['documentation', 'testing', 'analytics', 'admin']
        assert all(pt in info['supported_portal_types'] for pt in expected_portal_types)


class TestUIPortalIntegration:
    """Integration tests for UI portal functionality."""
    
    @pytest.mark.asyncio
    async def test_full_portal_workflow(self):
        """Test complete portal workflow from session creation to analytics."""
        # This would be a comprehensive integration test
        # For now, just verify the main functions are importable and callable
        
        from core_infra.ui import (
            initialize_ui_portals,
            get_ui_portal_health,
            get_ui_portal_info
        )
        
        # Verify functions exist and are callable
        assert callable(initialize_ui_portals)
        assert callable(get_ui_portal_health)
        assert callable(get_ui_portal_info)
        
        # Test component info
        info = get_ui_portal_info()
        assert isinstance(info, dict)
        assert "framework_version" in info


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
