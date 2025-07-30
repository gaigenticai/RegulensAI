"""
Tests for RegulensAI Disaster Recovery System
Comprehensive testing of DR procedures, automation, and monitoring.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

# Import DR components
from core_infra.disaster_recovery.dr_manager import (
    DRObjective,
    DREvent,
    DRTestResult,
    DRStatus,
    DRTestType,
    DRSeverity,
    DRComponentManager,
    DisasterRecoveryManager,
    dr_manager
)


class TestDRObjective:
    """Test DR objective functionality."""
    
    def test_dr_objective_creation(self):
        """Test DR objective creation."""
        objective = DRObjective(
            component="database",
            rto_minutes=15,
            rpo_minutes=5,
            priority=1,
            dependencies=[],
            automated_recovery=True,
            manual_steps_required=False,
            validation_checks=["data_integrity", "connection_test"]
        )
        
        assert objective.component == "database"
        assert objective.rto_minutes == 15
        assert objective.rpo_minutes == 5
        assert objective.priority == 1
        assert objective.automated_recovery is True
        assert objective.manual_steps_required is False
        assert "data_integrity" in objective.validation_checks


class TestDREvent:
    """Test DR event functionality."""
    
    def test_dr_event_creation(self):
        """Test DR event creation."""
        timestamp = datetime.utcnow()
        
        event = DREvent(
            event_id="event_123",
            timestamp=timestamp,
            event_type="backup_validation_failed",
            severity=DRSeverity.CRITICAL,
            component="database",
            description="Backup validation failed",
            status=DRStatus.CRITICAL,
            recovery_actions=["Check backup service", "Verify storage"]
        )
        
        assert event.event_id == "event_123"
        assert event.timestamp == timestamp
        assert event.event_type == "backup_validation_failed"
        assert event.severity == DRSeverity.CRITICAL
        assert event.component == "database"
        assert event.status == DRStatus.CRITICAL
        assert len(event.recovery_actions) == 2


class TestDRTestResult:
    """Test DR test result functionality."""
    
    def test_dr_test_result_creation(self):
        """Test DR test result creation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=5)
        
        result = DRTestResult(
            test_id="test_123",
            test_type=DRTestType.BACKUP_VALIDATION,
            component="database",
            start_time=start_time,
            end_time=end_time,
            status="passed",
            duration_minutes=5.0,
            rto_achieved=True,
            rpo_achieved=True,
            validation_results={"backup_exists": True, "backup_integrity": True},
            error_messages=[],
            recommendations=[]
        )
        
        assert result.test_id == "test_123"
        assert result.test_type == DRTestType.BACKUP_VALIDATION
        assert result.component == "database"
        assert result.status == "passed"
        assert result.duration_minutes == 5.0
        assert result.rto_achieved is True
        assert result.rpo_achieved is True
        assert result.validation_results["backup_exists"] is True


class TestDRComponentManager:
    """Test DR component manager functionality."""
    
    @pytest.fixture
    def dr_objective(self):
        """Create DR objective for testing."""
        return DRObjective(
            component="database",
            rto_minutes=15,
            rpo_minutes=5,
            priority=1,
            dependencies=[],
            automated_recovery=True,
            manual_steps_required=False,
            validation_checks=["data_integrity", "connection_test"]
        )
    
    @pytest.fixture
    def component_manager(self, dr_objective):
        """Create component manager instance."""
        return DRComponentManager("database", dr_objective)
    
    @pytest.mark.asyncio
    async def test_validate_backup(self, component_manager):
        """Test backup validation."""
        # Mock the internal methods
        component_manager._check_backup_exists = AsyncMock(return_value=True)
        component_manager._validate_backup_integrity = AsyncMock(return_value=True)
        component_manager._check_backup_age = AsyncMock(return_value=True)
        component_manager._validate_backup_completeness = AsyncMock(return_value=True)
        
        result = await component_manager.validate_backup()
        
        assert result.test_type == DRTestType.BACKUP_VALIDATION
        assert result.component == "database"
        assert result.status == "passed"
        assert result.validation_results["backup_exists"] is True
        assert result.validation_results["backup_integrity"] is True
        assert result.validation_results["backup_age"] is True
        assert result.validation_results["backup_complete"] is True
    
    @pytest.mark.asyncio
    async def test_validate_backup_failure(self, component_manager):
        """Test backup validation failure."""
        # Mock backup doesn't exist
        component_manager._check_backup_exists = AsyncMock(return_value=False)
        
        result = await component_manager.validate_backup()
        
        assert result.status == "failed"
        assert result.validation_results["backup_exists"] is False
        assert "No recent backup found" in result.error_messages
    
    @pytest.mark.asyncio
    async def test_test_failover_dry_run(self, component_manager):
        """Test failover test in dry run mode."""
        # Mock the internal methods
        component_manager._run_pre_failover_checks = AsyncMock(return_value=True)
        component_manager._simulate_failover = AsyncMock(return_value=True)
        component_manager._run_post_failover_checks = AsyncMock(return_value=True)
        
        result = await component_manager.test_failover(dry_run=True)
        
        assert result.test_type == DRTestType.FAILOVER_TEST
        assert result.component == "database"
        assert result.status == "passed"
        assert result.metadata["dry_run"] is True
        assert result.validation_results["pre_checks"] is True
        assert result.validation_results["failover_execution"] is True
        assert result.validation_results["post_checks"] is True
    
    @pytest.mark.asyncio
    async def test_test_failover_rto_exceeded(self, component_manager):
        """Test failover test with RTO exceeded."""
        # Mock slow failover
        async def slow_simulate_failover():
            await asyncio.sleep(0.1)  # Simulate slow failover
            return True
        
        component_manager._run_pre_failover_checks = AsyncMock(return_value=True)
        component_manager._simulate_failover = slow_simulate_failover
        component_manager._run_post_failover_checks = AsyncMock(return_value=True)
        
        # Set very low RTO for testing
        component_manager.dr_objectives.rto_minutes = 0.001  # Very low RTO
        
        result = await component_manager.test_failover(dry_run=True)
        
        assert result.rto_achieved is False
        assert "exceeds RTO" in result.recommendations[0]
    
    @pytest.mark.asyncio
    async def test_test_recovery(self, component_manager):
        """Test recovery test."""
        backup_timestamp = datetime.utcnow() - timedelta(minutes=30)
        
        # Mock the internal methods
        component_manager._validate_recovery_backup = AsyncMock(return_value=True)
        component_manager._execute_recovery = AsyncMock(return_value=True)
        component_manager._validate_data_integrity = AsyncMock(return_value=True)
        
        result = await component_manager.test_recovery(backup_timestamp)
        
        assert result.test_type == DRTestType.RECOVERY_TEST
        assert result.component == "database"
        assert result.status == "passed"
        assert result.validation_results["backup_valid"] is True
        assert result.validation_results["recovery_execution"] is True
        assert result.validation_results["data_integrity"] is True


class TestDisasterRecoveryManager:
    """Test disaster recovery manager functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        return settings
    
    @pytest.mark.asyncio
    async def test_dr_manager_initialization(self, mock_settings):
        """Test DR manager initialization."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            # Check that components are initialized
            assert "database" in manager.components
            assert "api_services" in manager.components
            assert "web_ui" in manager.components
            assert "monitoring" in manager.components
            assert "file_storage" in manager.components
            
            # Check component priorities
            assert manager.components["database"].dr_objectives.priority == 1
            assert manager.components["api_services"].dr_objectives.priority == 2
            assert manager.components["web_ui"].dr_objectives.priority == 3
    
    @pytest.mark.asyncio
    async def test_dr_manager_start_stop(self, mock_settings):
        """Test DR manager start and stop."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            await manager.start()
            assert manager.running is True
            assert len(manager._monitoring_tasks) > 0
            
            await manager.stop()
            assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_get_dr_status(self, mock_settings):
        """Test DR status retrieval."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            status = await manager.get_dr_status()
            
            assert "overall_status" in status
            assert "health_score" in status
            assert "components" in status
            assert "recent_events" in status
            assert "recent_tests" in status
            assert "last_updated" in status
            
            # Check component data
            assert "database" in status["components"]
            db_component = status["components"]["database"]
            assert "status" in db_component
            assert "rto_minutes" in db_component
            assert "rpo_minutes" in db_component
            assert "priority" in db_component
    
    @pytest.mark.asyncio
    async def test_run_dr_test(self, mock_settings):
        """Test running DR test."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            # Mock component manager methods
            component_manager = manager.components["database"]
            component_manager.validate_backup = AsyncMock()
            
            # Create mock test result
            mock_result = DRTestResult(
                test_id="test_123",
                test_type=DRTestType.BACKUP_VALIDATION,
                component="database",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                status="passed",
                duration_minutes=2.0,
                rto_achieved=True,
                rpo_achieved=True,
                validation_results={"backup_exists": True},
                error_messages=[],
                recommendations=[]
            )
            
            component_manager.validate_backup.return_value = mock_result
            
            result = await manager.run_dr_test("database", DRTestType.BACKUP_VALIDATION, dry_run=True)
            
            assert result.test_id == "test_123"
            assert result.component == "database"
            assert result.status == "passed"
            assert len(manager.test_results) == 1
    
    @pytest.mark.asyncio
    async def test_run_full_dr_test(self, mock_settings):
        """Test running full DR test."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            # Mock all component test methods
            for component_name, component_manager in manager.components.items():
                component_manager.validate_backup = AsyncMock()
                component_manager.test_failover = AsyncMock()
                component_manager.test_recovery = AsyncMock()
                
                # Create mock results
                backup_result = DRTestResult(
                    test_id=f"backup_{component_name}",
                    test_type=DRTestType.BACKUP_VALIDATION,
                    component=component_name,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    status="passed",
                    duration_minutes=1.0,
                    rto_achieved=True,
                    rpo_achieved=True,
                    validation_results={},
                    error_messages=[],
                    recommendations=[]
                )
                
                failover_result = DRTestResult(
                    test_id=f"failover_{component_name}",
                    test_type=DRTestType.FAILOVER_TEST,
                    component=component_name,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    status="passed",
                    duration_minutes=2.0,
                    rto_achieved=True,
                    rpo_achieved=True,
                    validation_results={},
                    error_messages=[],
                    recommendations=[]
                )
                
                recovery_result = DRTestResult(
                    test_id=f"recovery_{component_name}",
                    test_type=DRTestType.RECOVERY_TEST,
                    component=component_name,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    status="passed",
                    duration_minutes=3.0,
                    rto_achieved=True,
                    rpo_achieved=True,
                    validation_results={},
                    error_messages=[],
                    recommendations=[]
                )
                
                component_manager.validate_backup.return_value = backup_result
                component_manager.test_failover.return_value = failover_result
                component_manager.test_recovery.return_value = recovery_result
            
            results = await manager.run_full_dr_test(dry_run=True)
            
            # Should have 3 tests per component (backup, failover, recovery)
            expected_tests = len(manager.components) * 3
            assert len(results) == expected_tests
            
            # All tests should pass
            passed_tests = sum(1 for r in results.values() if r.status == "passed")
            assert passed_tests == expected_tests
    
    @pytest.mark.asyncio
    async def test_calculate_dr_health_score(self, mock_settings):
        """Test DR health score calculation."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            # Set all components to healthy
            for component_manager in manager.components.values():
                component_manager.current_status = DRStatus.HEALTHY
                component_manager.last_test_time = datetime.utcnow() - timedelta(days=1)
            
            health_score = await manager._calculate_dr_health_score()
            
            # Should be high score for all healthy components
            assert health_score > 80.0
            
            # Set one component to critical
            manager.components["database"].current_status = DRStatus.CRITICAL
            
            health_score_critical = await manager._calculate_dr_health_score()
            
            # Score should be lower with critical component
            assert health_score_critical < health_score
    
    @pytest.mark.asyncio
    async def test_dr_event_recording(self, mock_settings):
        """Test DR event recording."""
        with patch('core_infra.disaster_recovery.dr_manager.get_settings', return_value=mock_settings):
            manager = DisasterRecoveryManager()
            
            event = DREvent(
                event_id="event_123",
                timestamp=datetime.utcnow(),
                event_type="test_event",
                severity=DRSeverity.WARNING,
                component="database",
                description="Test event",
                status=DRStatus.WARNING
            )
            
            await manager._record_dr_event(event)
            
            assert len(manager.dr_events) == 1
            assert manager.dr_events[0] == event


class TestDRIntegration:
    """Test DR system integration."""
    
    @pytest.mark.asyncio
    async def test_dr_api_integration(self):
        """Test DR API integration."""
        # This would test the actual API endpoints
        # For now, just verify the API routes exist
        from core_infra.api.routes.disaster_recovery import router
        
        assert router is not None
        
        # Check that key routes are defined
        route_paths = [route.path for route in router.routes]
        assert "/status" in route_paths
        assert "/components" in route_paths
        assert "/test" in route_paths
    
    def test_dr_cli_exists(self):
        """Test that DR CLI exists and is importable."""
        import scripts.dr_manager
        assert scripts.dr_manager is not None
    
    def test_dr_frontend_components_exist(self):
        """Test that DR frontend components exist."""
        from pathlib import Path
        
        frontend_dr_path = Path(__file__).parent.parent / "frontend/src/components/DisasterRecovery"
        
        # Check that key components exist
        assert (frontend_dr_path / "DRDashboard.tsx").exists()
        assert (frontend_dr_path / "DRComponentList.tsx").exists()
        
        # Check API service exists
        api_service_path = Path(__file__).parent.parent / "frontend/src/services/api/disasterRecovery.ts"
        assert api_service_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
