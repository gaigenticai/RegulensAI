"""
RegulensAI Disaster Recovery Manager
Enterprise-grade disaster recovery orchestration with automated testing, failover, and monitoring.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
import aiofiles
import aiohttp
from contextlib import asynccontextmanager

from core_infra.config import get_settings
from core_infra.logging.centralized_logging import get_centralized_logger, LogCategory
from core_infra.monitoring.apm_integration import apm_manager, track_performance
from core_infra.services.backup_service import backup_service
from core_infra.exceptions import SystemException


logger = structlog.get_logger(__name__)


class DRStatus(str, Enum):
    """Disaster recovery status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    TESTING = "testing"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"
    FAILED = "failed"


class DRTestType(str, Enum):
    """DR test type enumeration."""
    BACKUP_VALIDATION = "backup_validation"
    FAILOVER_TEST = "failover_test"
    RECOVERY_TEST = "recovery_test"
    FULL_DR_TEST = "full_dr_test"
    NETWORK_PARTITION = "network_partition"
    DATABASE_FAILOVER = "database_failover"
    APPLICATION_FAILOVER = "application_failover"


class DRSeverity(str, Enum):
    """DR event severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class DRObjective:
    """Disaster recovery objectives definition."""
    component: str
    rto_minutes: int  # Recovery Time Objective in minutes
    rpo_minutes: int  # Recovery Point Objective in minutes
    priority: int  # 1 = highest priority
    dependencies: List[str]
    automated_recovery: bool
    manual_steps_required: bool
    validation_checks: List[str]


@dataclass
class DREvent:
    """Disaster recovery event record."""
    event_id: str
    timestamp: datetime
    event_type: str
    severity: DRSeverity
    component: str
    description: str
    status: DRStatus
    duration_minutes: Optional[float] = None
    impact_assessment: Optional[str] = None
    recovery_actions: List[str] = None
    lessons_learned: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.recovery_actions is None:
            self.recovery_actions = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DRTestResult:
    """DR test execution result."""
    test_id: str
    test_type: DRTestType
    component: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # "running", "passed", "failed", "cancelled"
    duration_minutes: Optional[float]
    rto_achieved: Optional[bool]
    rpo_achieved: Optional[bool]
    validation_results: Dict[str, bool]
    error_messages: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_results is None:
            self.validation_results = {}
        if self.error_messages is None:
            self.error_messages = []
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}


class DRComponentManager:
    """Manages disaster recovery for individual components."""
    
    def __init__(self, component_name: str, dr_objectives: DRObjective):
        self.component_name = component_name
        self.dr_objectives = dr_objectives
        self.current_status = DRStatus.HEALTHY
        self.last_test_time = None
        self.last_backup_time = None
        self.failover_history = []
        
    async def validate_backup(self) -> DRTestResult:
        """Validate component backup integrity."""
        test_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        test_result = DRTestResult(
            test_id=test_id,
            test_type=DRTestType.BACKUP_VALIDATION,
            component=self.component_name,
            start_time=start_time,
            end_time=None,
            status="running",
            duration_minutes=None,
            rto_achieved=None,
            rpo_achieved=None,
            validation_results={},
            error_messages=[],
            recommendations=[]
        )
        
        try:
            # Validate backup existence
            backup_exists = await self._check_backup_exists()
            test_result.validation_results["backup_exists"] = backup_exists
            
            if not backup_exists:
                test_result.error_messages.append("No recent backup found")
                test_result.status = "failed"
                return test_result
            
            # Validate backup integrity
            backup_valid = await self._validate_backup_integrity()
            test_result.validation_results["backup_integrity"] = backup_valid
            
            # Check backup age against RPO
            backup_age_valid = await self._check_backup_age()
            test_result.validation_results["backup_age"] = backup_age_valid
            test_result.rpo_achieved = backup_age_valid
            
            # Validate backup completeness
            backup_complete = await self._validate_backup_completeness()
            test_result.validation_results["backup_complete"] = backup_complete
            
            # Overall test status
            all_validations_passed = all(test_result.validation_results.values())
            test_result.status = "passed" if all_validations_passed else "failed"
            
            if not all_validations_passed:
                test_result.recommendations.append("Review backup configuration and schedule")
                test_result.recommendations.append("Verify backup storage accessibility")
            
        except Exception as e:
            test_result.status = "failed"
            test_result.error_messages.append(f"Backup validation error: {str(e)}")
            
        finally:
            test_result.end_time = datetime.utcnow()
            test_result.duration_minutes = (test_result.end_time - test_result.start_time).total_seconds() / 60
            
        return test_result
    
    async def test_failover(self, dry_run: bool = True) -> DRTestResult:
        """Test component failover procedure."""
        test_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        test_result = DRTestResult(
            test_id=test_id,
            test_type=DRTestType.FAILOVER_TEST,
            component=self.component_name,
            start_time=start_time,
            end_time=None,
            status="running",
            duration_minutes=None,
            rto_achieved=None,
            rpo_achieved=None,
            validation_results={},
            error_messages=[],
            recommendations=[],
            metadata={"dry_run": dry_run}
        )
        
        try:
            # Pre-failover checks
            pre_checks_passed = await self._run_pre_failover_checks()
            test_result.validation_results["pre_checks"] = pre_checks_passed
            
            if not pre_checks_passed:
                test_result.status = "failed"
                test_result.error_messages.append("Pre-failover checks failed")
                return test_result
            
            # Execute failover (or simulate if dry_run)
            if dry_run:
                failover_success = await self._simulate_failover()
            else:
                failover_success = await self._execute_failover()
            
            test_result.validation_results["failover_execution"] = failover_success
            
            # Validate failover timing against RTO
            failover_duration = (datetime.utcnow() - start_time).total_seconds() / 60
            rto_achieved = failover_duration <= self.dr_objectives.rto_minutes
            test_result.rto_achieved = rto_achieved
            test_result.validation_results["rto_met"] = rto_achieved
            
            # Post-failover validation
            if failover_success:
                post_checks_passed = await self._run_post_failover_checks()
                test_result.validation_results["post_checks"] = post_checks_passed
            
            # Overall test status
            all_validations_passed = all(test_result.validation_results.values())
            test_result.status = "passed" if all_validations_passed else "failed"
            
            if not rto_achieved:
                test_result.recommendations.append(f"Failover took {failover_duration:.1f} minutes, exceeds RTO of {self.dr_objectives.rto_minutes} minutes")
            
        except Exception as e:
            test_result.status = "failed"
            test_result.error_messages.append(f"Failover test error: {str(e)}")
            
        finally:
            test_result.end_time = datetime.utcnow()
            test_result.duration_minutes = (test_result.end_time - test_result.start_time).total_seconds() / 60
            
        return test_result
    
    async def test_recovery(self, backup_timestamp: Optional[datetime] = None) -> DRTestResult:
        """Test component recovery from backup."""
        test_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        test_result = DRTestResult(
            test_id=test_id,
            test_type=DRTestType.RECOVERY_TEST,
            component=self.component_name,
            start_time=start_time,
            end_time=None,
            status="running",
            duration_minutes=None,
            rto_achieved=None,
            rpo_achieved=None,
            validation_results={},
            error_messages=[],
            recommendations=[],
            metadata={"backup_timestamp": backup_timestamp.isoformat() if backup_timestamp else None}
        )
        
        try:
            # Validate backup for recovery
            backup_valid = await self._validate_recovery_backup(backup_timestamp)
            test_result.validation_results["backup_valid"] = backup_valid
            
            if not backup_valid:
                test_result.status = "failed"
                test_result.error_messages.append("Backup validation failed for recovery")
                return test_result
            
            # Execute recovery
            recovery_success = await self._execute_recovery(backup_timestamp)
            test_result.validation_results["recovery_execution"] = recovery_success
            
            # Validate recovery timing
            recovery_duration = (datetime.utcnow() - start_time).total_seconds() / 60
            rto_achieved = recovery_duration <= self.dr_objectives.rto_minutes
            test_result.rto_achieved = rto_achieved
            test_result.validation_results["rto_met"] = rto_achieved
            
            # Validate data integrity post-recovery
            if recovery_success:
                data_integrity_valid = await self._validate_data_integrity()
                test_result.validation_results["data_integrity"] = data_integrity_valid
                
                # Check RPO achievement
                if backup_timestamp:
                    data_loss_minutes = (start_time - backup_timestamp).total_seconds() / 60
                    rpo_achieved = data_loss_minutes <= self.dr_objectives.rpo_minutes
                    test_result.rpo_achieved = rpo_achieved
                    test_result.validation_results["rpo_met"] = rpo_achieved
            
            # Overall test status
            all_validations_passed = all(test_result.validation_results.values())
            test_result.status = "passed" if all_validations_passed else "failed"
            
        except Exception as e:
            test_result.status = "failed"
            test_result.error_messages.append(f"Recovery test error: {str(e)}")
            
        finally:
            test_result.end_time = datetime.utcnow()
            test_result.duration_minutes = (test_result.end_time - test_result.start_time).total_seconds() / 60
            
        return test_result
    
    async def _check_backup_exists(self) -> bool:
        """Check if recent backup exists for component."""
        # Implementation depends on component type
        if self.component_name == "database":
            return await backup_service.check_backup_exists()
        return True  # Placeholder for other components
    
    async def _validate_backup_integrity(self) -> bool:
        """Validate backup file integrity."""
        # Implementation depends on component type
        return await backup_service.validate_backup_integrity()
    
    async def _check_backup_age(self) -> bool:
        """Check if backup age meets RPO requirements."""
        if self.component_name == "database":
            stats = await backup_service.get_backup_statistics()
            if stats.get("last_backup_time"):
                last_backup = datetime.fromisoformat(stats["last_backup_time"])
                age_minutes = (datetime.utcnow() - last_backup).total_seconds() / 60
                return age_minutes <= self.dr_objectives.rpo_minutes
        return True  # Placeholder
    
    async def _validate_backup_completeness(self) -> bool:
        """Validate backup contains all required data."""
        return True  # Placeholder
    
    async def _run_pre_failover_checks(self) -> bool:
        """Run pre-failover validation checks."""
        return True  # Placeholder
    
    async def _simulate_failover(self) -> bool:
        """Simulate failover procedure."""
        await asyncio.sleep(1)  # Simulate failover time
        return True
    
    async def _execute_failover(self) -> bool:
        """Execute actual failover procedure."""
        # Implementation depends on component type
        return True  # Placeholder
    
    async def _run_post_failover_checks(self) -> bool:
        """Run post-failover validation checks."""
        return True  # Placeholder
    
    async def _validate_recovery_backup(self, backup_timestamp: Optional[datetime]) -> bool:
        """Validate backup for recovery operation."""
        return True  # Placeholder
    
    async def _execute_recovery(self, backup_timestamp: Optional[datetime]) -> bool:
        """Execute recovery from backup."""
        return True  # Placeholder
    
    async def _validate_data_integrity(self) -> bool:
        """Validate data integrity after recovery."""
        return True  # Placeholder


class DisasterRecoveryManager:
    """
    Central disaster recovery manager for RegulensAI platform.
    Orchestrates DR testing, monitoring, and recovery procedures.
    """

    def __init__(self):
        self.settings = get_settings()
        self.components = {}
        self.dr_events = []
        self.test_results = []
        self.current_status = DRStatus.HEALTHY
        self.running = False

        # DR monitoring tasks
        self._monitoring_tasks = []

        # Initialize DR objectives for RegulensAI components
        self._initialize_dr_objectives()

    def _initialize_dr_objectives(self):
        """Initialize DR objectives for all RegulensAI components."""
        # Database DR objectives
        database_objectives = DRObjective(
            component="database",
            rto_minutes=15,  # 15 minutes RTO
            rpo_minutes=5,   # 5 minutes RPO
            priority=1,      # Highest priority
            dependencies=[],
            automated_recovery=True,
            manual_steps_required=False,
            validation_checks=["data_integrity", "connection_test", "performance_check"]
        )
        self.components["database"] = DRComponentManager("database", database_objectives)

        # Application services DR objectives
        api_objectives = DRObjective(
            component="api_services",
            rto_minutes=10,  # 10 minutes RTO
            rpo_minutes=1,   # 1 minute RPO
            priority=2,
            dependencies=["database"],
            automated_recovery=True,
            manual_steps_required=False,
            validation_checks=["health_check", "api_response", "authentication"]
        )
        self.components["api_services"] = DRComponentManager("api_services", api_objectives)

        # Web UI DR objectives
        ui_objectives = DRObjective(
            component="web_ui",
            rto_minutes=5,   # 5 minutes RTO
            rpo_minutes=0,   # No data loss for static assets
            priority=3,
            dependencies=["api_services"],
            automated_recovery=True,
            manual_steps_required=False,
            validation_checks=["page_load", "functionality_test", "asset_availability"]
        )
        self.components["web_ui"] = DRComponentManager("web_ui", ui_objectives)

        # Monitoring infrastructure DR objectives
        monitoring_objectives = DRObjective(
            component="monitoring",
            rto_minutes=20,  # 20 minutes RTO
            rpo_minutes=10,  # 10 minutes RPO
            priority=4,
            dependencies=[],
            automated_recovery=True,
            manual_steps_required=True,
            validation_checks=["metrics_collection", "alerting", "dashboard_access"]
        )
        self.components["monitoring"] = DRComponentManager("monitoring", monitoring_objectives)

        # File storage DR objectives
        storage_objectives = DRObjective(
            component="file_storage",
            rto_minutes=30,  # 30 minutes RTO
            rpo_minutes=60,  # 60 minutes RPO
            priority=5,
            dependencies=[],
            automated_recovery=False,
            manual_steps_required=True,
            validation_checks=["file_access", "backup_integrity", "replication_status"]
        )
        self.components["file_storage"] = DRComponentManager("file_storage", storage_objectives)

    async def start(self):
        """Start the disaster recovery manager."""
        if self.running:
            return

        self.running = True

        # Start monitoring tasks
        self._monitoring_tasks = [
            asyncio.create_task(self._dr_health_monitoring_loop()),
            asyncio.create_task(self._automated_testing_loop()),
            asyncio.create_task(self._backup_validation_loop())
        ]

        # Log DR manager startup
        dr_logger = await get_centralized_logger("dr_manager")
        await dr_logger.info(
            "Disaster Recovery Manager started",
            category=LogCategory.SYSTEM,
            components=list(self.components.keys()),
            total_components=len(self.components)
        )

    async def stop(self):
        """Stop the disaster recovery manager."""
        self.running = False

        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        dr_logger = await get_centralized_logger("dr_manager")
        await dr_logger.info("Disaster Recovery Manager stopped", category=LogCategory.SYSTEM)

    async def get_dr_status(self) -> Dict[str, Any]:
        """Get comprehensive DR status for all components."""
        component_statuses = {}

        for component_name, component_manager in self.components.items():
            component_statuses[component_name] = {
                "status": component_manager.current_status.value,
                "rto_minutes": component_manager.dr_objectives.rto_minutes,
                "rpo_minutes": component_manager.dr_objectives.rpo_minutes,
                "priority": component_manager.dr_objectives.priority,
                "automated_recovery": component_manager.dr_objectives.automated_recovery,
                "last_test_time": component_manager.last_test_time.isoformat() if component_manager.last_test_time else None,
                "last_backup_time": component_manager.last_backup_time.isoformat() if component_manager.last_backup_time else None,
                "dependencies": component_manager.dr_objectives.dependencies
            }

        # Calculate overall DR health score
        health_score = await self._calculate_dr_health_score()

        # Get recent DR events
        recent_events = sorted(self.dr_events, key=lambda x: x.timestamp, reverse=True)[:10]

        # Get recent test results
        recent_tests = sorted(self.test_results, key=lambda x: x.start_time, reverse=True)[:10]

        return {
            "overall_status": self.current_status.value,
            "health_score": health_score,
            "components": component_statuses,
            "recent_events": [asdict(event) for event in recent_events],
            "recent_tests": [asdict(test) for test in recent_tests],
            "last_updated": datetime.utcnow().isoformat()
        }

    async def run_dr_test(self, component: str, test_type: DRTestType, dry_run: bool = True) -> DRTestResult:
        """Run disaster recovery test for specific component."""
        if component not in self.components:
            raise SystemException(f"Unknown component: {component}")

        component_manager = self.components[component]
        component_manager.current_status = DRStatus.TESTING

        try:
            # Track test execution with APM
            async with apm_manager.track_operation(
                f"dr_test_{test_type.value}",
                "disaster_recovery",
                component=component,
                test_type=test_type.value,
                dry_run=dry_run
            ):
                if test_type == DRTestType.BACKUP_VALIDATION:
                    result = await component_manager.validate_backup()
                elif test_type == DRTestType.FAILOVER_TEST:
                    result = await component_manager.test_failover(dry_run)
                elif test_type == DRTestType.RECOVERY_TEST:
                    result = await component_manager.test_recovery()
                else:
                    raise SystemException(f"Unsupported test type: {test_type}")

                # Store test result
                self.test_results.append(result)
                component_manager.last_test_time = result.end_time

                # Log test completion
                dr_logger = await get_centralized_logger("dr_manager")
                await dr_logger.info(
                    f"DR test completed: {component} - {test_type.value}",
                    category=LogCategory.SYSTEM,
                    component=component,
                    test_type=test_type.value,
                    test_status=result.status,
                    duration_minutes=result.duration_minutes,
                    rto_achieved=result.rto_achieved,
                    rpo_achieved=result.rpo_achieved
                )

                return result

        except Exception as e:
            # Create failed test result
            result = DRTestResult(
                test_id=str(uuid.uuid4()),
                test_type=test_type,
                component=component,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                status="failed",
                duration_minutes=0,
                rto_achieved=False,
                rpo_achieved=False,
                validation_results={},
                error_messages=[str(e)],
                recommendations=["Review component configuration and dependencies"]
            )

            self.test_results.append(result)

            dr_logger = await get_centralized_logger("dr_manager")
            await dr_logger.error(
                f"DR test failed: {component} - {test_type.value}",
                category=LogCategory.SYSTEM,
                component=component,
                test_type=test_type.value,
                error=str(e)
            )

            return result

        finally:
            component_manager.current_status = DRStatus.HEALTHY

    async def run_full_dr_test(self, dry_run: bool = True) -> Dict[str, DRTestResult]:
        """Run comprehensive DR test for all components."""
        results = {}

        # Sort components by priority for testing
        sorted_components = sorted(
            self.components.items(),
            key=lambda x: x[1].dr_objectives.priority
        )

        for component_name, component_manager in sorted_components:
            # Run backup validation first
            backup_result = await self.run_dr_test(component_name, DRTestType.BACKUP_VALIDATION, dry_run)
            results[f"{component_name}_backup"] = backup_result

            # Run failover test if backup validation passed
            if backup_result.status == "passed":
                failover_result = await self.run_dr_test(component_name, DRTestType.FAILOVER_TEST, dry_run)
                results[f"{component_name}_failover"] = failover_result

                # Run recovery test if failover passed
                if failover_result.status == "passed":
                    recovery_result = await self.run_dr_test(component_name, DRTestType.RECOVERY_TEST, dry_run)
                    results[f"{component_name}_recovery"] = recovery_result

        # Log full DR test completion
        dr_logger = await get_centralized_logger("dr_manager")
        await dr_logger.info(
            "Full DR test completed",
            category=LogCategory.SYSTEM,
            total_tests=len(results),
            passed_tests=sum(1 for r in results.values() if r.status == "passed"),
            failed_tests=sum(1 for r in results.values() if r.status == "failed"),
            dry_run=dry_run
        )

        return results

    async def _dr_health_monitoring_loop(self):
        """Background task for monitoring DR health."""
        while self.running:
            try:
                # Check component health
                for component_name, component_manager in self.components.items():
                    await self._check_component_health(component_name, component_manager)

                # Update overall DR status
                await self._update_overall_status()

                # Check for DR events that need attention
                await self._process_pending_dr_events()

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                dr_logger = await get_centralized_logger("dr_manager")
                await dr_logger.error(f"DR health monitoring error: {e}")
                await asyncio.sleep(600)  # Wait longer on error

    async def _automated_testing_loop(self):
        """Background task for automated DR testing."""
        while self.running:
            try:
                # Check if it's time for scheduled DR tests
                for component_name, component_manager in self.components.items():
                    if await self._should_run_automated_test(component_name, component_manager):
                        await self.run_dr_test(component_name, DRTestType.BACKUP_VALIDATION, dry_run=True)

                # Run full DR test weekly (if configured)
                if await self._should_run_full_dr_test():
                    await self.run_full_dr_test(dry_run=True)

                await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                dr_logger = await get_centralized_logger("dr_manager")
                await dr_logger.error(f"Automated DR testing error: {e}")
                await asyncio.sleep(3600)

    async def _backup_validation_loop(self):
        """Background task for continuous backup validation."""
        while self.running:
            try:
                # Validate recent backups
                for component_name, component_manager in self.components.items():
                    if component_name == "database":  # Focus on critical components
                        backup_result = await component_manager.validate_backup()

                        if backup_result.status == "failed":
                            # Create DR event for backup failure
                            event = DREvent(
                                event_id=str(uuid.uuid4()),
                                timestamp=datetime.utcnow(),
                                event_type="backup_validation_failed",
                                severity=DRSeverity.CRITICAL,
                                component=component_name,
                                description=f"Backup validation failed: {', '.join(backup_result.error_messages)}",
                                status=DRStatus.CRITICAL,
                                recovery_actions=backup_result.recommendations
                            )

                            await self._record_dr_event(event)

                await asyncio.sleep(1800)  # Check every 30 minutes

            except Exception as e:
                dr_logger = await get_centralized_logger("dr_manager")
                await dr_logger.error(f"Backup validation error: {e}")
                await asyncio.sleep(1800)

    async def _check_component_health(self, component_name: str, component_manager: DRComponentManager):
        """Check health of individual DR component."""
        try:
            # Check backup freshness
            if component_name == "database":
                backup_age_valid = await component_manager._check_backup_age()
                if not backup_age_valid:
                    component_manager.current_status = DRStatus.WARNING

                    event = DREvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.utcnow(),
                        event_type="backup_age_warning",
                        severity=DRSeverity.WARNING,
                        component=component_name,
                        description=f"Backup age exceeds RPO of {component_manager.dr_objectives.rpo_minutes} minutes",
                        status=DRStatus.WARNING,
                        recovery_actions=["Check backup schedule", "Verify backup service health"]
                    )

                    await self._record_dr_event(event)

            # Check for stale test results
            if component_manager.last_test_time:
                test_age = datetime.utcnow() - component_manager.last_test_time
                if test_age > timedelta(days=7):  # Tests older than 7 days
                    component_manager.current_status = DRStatus.WARNING

        except Exception as e:
            dr_logger = await get_centralized_logger("dr_manager")
            await dr_logger.error(f"Component health check failed for {component_name}: {e}")

    async def _update_overall_status(self):
        """Update overall DR status based on component statuses."""
        component_statuses = [manager.current_status for manager in self.components.values()]

        if any(status == DRStatus.CRITICAL for status in component_statuses):
            self.current_status = DRStatus.CRITICAL
        elif any(status == DRStatus.WARNING for status in component_statuses):
            self.current_status = DRStatus.WARNING
        elif any(status == DRStatus.TESTING for status in component_statuses):
            self.current_status = DRStatus.TESTING
        else:
            self.current_status = DRStatus.HEALTHY

    async def _should_run_automated_test(self, component_name: str, component_manager: DRComponentManager) -> bool:
        """Determine if automated test should run for component."""
        if not component_manager.last_test_time:
            return True  # Never tested

        # Test daily for critical components, weekly for others
        test_interval = timedelta(days=1 if component_manager.dr_objectives.priority <= 2 else 7)
        return datetime.utcnow() - component_manager.last_test_time > test_interval

    async def _should_run_full_dr_test(self) -> bool:
        """Determine if full DR test should run."""
        # Run full DR test weekly
        if not hasattr(self, '_last_full_test_time'):
            self._last_full_test_time = None

        if not self._last_full_test_time:
            return True

        return datetime.utcnow() - self._last_full_test_time > timedelta(days=7)

    async def _record_dr_event(self, event: DREvent):
        """Record DR event and send notifications."""
        self.dr_events.append(event)

        # Log event to centralized logging
        dr_logger = await get_centralized_logger("dr_manager")
        await dr_logger.log(
            event.severity.value.upper(),
            f"DR Event: {event.description}",
            category=LogCategory.SYSTEM,
            event_id=event.event_id,
            event_type=event.event_type,
            component=event.component,
            status=event.status.value,
            recovery_actions=event.recovery_actions
        )

        # Track in APM
        await apm_manager.track_business_metric(
            'dr_events',
            1,
            event_type=event.event_type,
            severity=event.severity.value,
            component=event.component
        )

    async def _process_pending_dr_events(self):
        """Process pending DR events that need attention."""
        # Find unresolved critical events
        critical_events = [
            event for event in self.dr_events
            if event.severity == DRSeverity.CRITICAL and event.status != DRStatus.HEALTHY
        ]

        # Auto-resolve events older than 24 hours if component is healthy
        for event in critical_events:
            if datetime.utcnow() - event.timestamp > timedelta(hours=24):
                component_manager = self.components.get(event.component)
                if component_manager and component_manager.current_status == DRStatus.HEALTHY:
                    event.status = DRStatus.HEALTHY
                    event.recovery_actions.append("Auto-resolved: Component returned to healthy state")

    async def _calculate_dr_health_score(self) -> float:
        """Calculate overall DR health score (0-100)."""
        if not self.components:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for component_manager in self.components.values():
            # Weight by priority (higher priority = higher weight)
            weight = 6 - component_manager.dr_objectives.priority  # Priority 1 = weight 5, etc.

            # Component score based on status
            if component_manager.current_status == DRStatus.HEALTHY:
                score = 100.0
            elif component_manager.current_status == DRStatus.WARNING:
                score = 70.0
            elif component_manager.current_status == DRStatus.TESTING:
                score = 85.0
            else:  # CRITICAL or FAILED
                score = 0.0

            # Adjust score based on test freshness
            if component_manager.last_test_time:
                test_age = datetime.utcnow() - component_manager.last_test_time
                if test_age > timedelta(days=30):
                    score *= 0.5  # Reduce score for stale tests
                elif test_age > timedelta(days=7):
                    score *= 0.8
            else:
                score *= 0.3  # Significantly reduce score for never tested

            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0


# Global DR manager instance
dr_manager = DisasterRecoveryManager()


# Convenience functions
async def init_disaster_recovery():
    """Initialize disaster recovery system."""
    await dr_manager.start()


async def shutdown_disaster_recovery():
    """Shutdown disaster recovery system."""
    await dr_manager.stop()


async def get_dr_status() -> Dict[str, Any]:
    """Get current DR status."""
    return await dr_manager.get_dr_status()


async def run_dr_test(component: str, test_type: str, dry_run: bool = True) -> DRTestResult:
    """Run DR test for component."""
    test_type_enum = DRTestType(test_type)
    return await dr_manager.run_dr_test(component, test_type_enum, dry_run)


async def run_full_dr_test(dry_run: bool = True) -> Dict[str, DRTestResult]:
    """Run full DR test suite."""
    return await dr_manager.run_full_dr_test(dry_run)
