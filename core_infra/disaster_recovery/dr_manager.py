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
        # Check backup exists for different component types
        if self.component_name == "api":
            # Check API state snapshots
            backup_path = Path(f"/backups/api/{datetime.utcnow().strftime('%Y%m%d')}")
            return backup_path.exists() and any(backup_path.glob("*.snapshot"))
        elif self.component_name == "config":
            # Check configuration backups
            backup_path = Path(f"/backups/config/latest")
            return backup_path.exists() and (backup_path / "config.json").exists()
        elif self.component_name == "logs":
            # Check log archives
            backup_path = Path(f"/backups/logs/{datetime.utcnow().strftime('%Y%m%d')}")
            return backup_path.exists()
        else:
            # For unknown components, check generic backup directory
            backup_path = Path(f"/backups/{self.component_name}")
            return backup_path.exists() and any(backup_path.glob("*"))
    
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
        
        # Check backup age for non-database components
        backup_path = None
        
        if self.component_name == "api":
            backup_paths = list(Path(f"/backups/api").glob("*/latest.timestamp"))
        elif self.component_name == "config":
            backup_paths = [Path(f"/backups/config/latest/timestamp")]
        elif self.component_name == "logs":
            backup_paths = list(Path(f"/backups/logs").glob("*/timestamp"))
        else:
            backup_paths = list(Path(f"/backups/{self.component_name}").glob("*/timestamp"))
        
        # Find most recent backup timestamp
        latest_backup_time = None
        for timestamp_file in backup_paths:
            if timestamp_file.exists():
                try:
                    async with aiofiles.open(timestamp_file, 'r') as f:
                        timestamp_str = await f.read()
                        backup_time = datetime.fromisoformat(timestamp_str.strip())
                        if latest_backup_time is None or backup_time > latest_backup_time:
                            latest_backup_time = backup_time
                except Exception:
                    continue
        
        if latest_backup_time:
            age_minutes = (datetime.utcnow() - latest_backup_time).total_seconds() / 60
            return age_minutes <= self.dr_objectives.rpo_minutes
        
        return False  # No valid backup found
    
    async def _validate_backup_completeness(self) -> bool:
        """Validate backup contains all required data."""
        try:
            if self.component_name == "database":
                # Check database backup has all tables
                return await backup_service.validate_backup_completeness()
            elif self.component_name == "api":
                # Check API state backup has required components
                backup_path = Path(f"/backups/api/latest")
                required_files = ["routes.json", "middleware.json", "config.json"]
                return all((backup_path / f).exists() for f in required_files)
            elif self.component_name == "config":
                # Check configuration backup completeness
                backup_path = Path(f"/backups/config/latest")
                required_files = ["config.json", "secrets.enc", "env.json"]
                return all((backup_path / f).exists() for f in required_files)
            elif self.component_name == "logs":
                # Check log backup has all log types
                backup_path = Path(f"/backups/logs/latest")
                log_types = ["application.log", "error.log", "access.log"]
                return any((backup_path / lt).exists() for lt in log_types)
            else:
                # Generic completeness check
                backup_path = Path(f"/backups/{self.component_name}/latest")
                return backup_path.exists() and any(backup_path.iterdir())
        except Exception as e:
            logger.error(f"Backup completeness validation failed: {e}")
            return False
    
    async def _run_pre_failover_checks(self) -> bool:
        """Run pre-failover validation checks."""
        try:
            checks_passed = True
            
            # Check system resources
            if self.component_name == "database":
                # Check replica status
                replica_status = await backup_service.check_replica_status()
                checks_passed &= replica_status.get("is_healthy", False)
                checks_passed &= replica_status.get("lag_seconds", float('inf')) < 60
            
            # Check network connectivity to failover target
            failover_endpoint = get_settings().dr_config.get(f"{self.component_name}_failover_endpoint")
            if failover_endpoint:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(f"{failover_endpoint}/health", timeout=5) as resp:
                            checks_passed &= resp.status == 200
                    except Exception:
                        checks_passed = False
            
            # Check no active transactions or operations
            if self.component_name in ["database", "api"]:
                active_connections = await self._get_active_connections()
                checks_passed &= active_connections < 100  # Threshold
            
            # Verify backup availability
            checks_passed &= await self._check_backup_exists()
            
            return checks_passed
            
        except Exception as e:
            logger.error(f"Pre-failover checks failed: {e}")
            return False
    
    async def _simulate_failover(self) -> bool:
        """Simulate failover procedure."""
        await asyncio.sleep(1)  # Simulate failover time
        return True
    
    async def _execute_failover(self) -> bool:
        """Execute actual failover procedure."""
        try:
            if self.component_name == "database":
                # Promote replica to primary
                return await backup_service.promote_replica()
            
            elif self.component_name == "api":
                # Switch to secondary API cluster
                settings = get_settings()
                primary_url = settings.api_primary_url
                secondary_url = settings.api_secondary_url
                
                # Update load balancer configuration
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "action": "failover",
                        "from": primary_url,
                        "to": secondary_url
                    }
                    async with session.post(
                        f"{settings.load_balancer_api}/failover",
                        json=payload
                    ) as resp:
                        return resp.status == 200
            
            elif self.component_name == "cache":
                # Switch to backup cache cluster
                cache_config = get_settings().cache_config
                return await self._switch_cache_cluster(
                    cache_config["primary"],
                    cache_config["secondary"]
                )
            
            else:
                # Generic failover - update DNS/routing
                return await self._update_routing_table(self.component_name)
                
        except Exception as e:
            logger.error(f"Failover execution failed: {e}")
            return False
    
    async def _run_post_failover_checks(self) -> bool:
        """Run post-failover validation checks."""
        try:
            checks_passed = True
            
            # Verify component is responding
            failover_endpoint = get_settings().dr_config.get(f"{self.component_name}_failover_endpoint")
            if failover_endpoint:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(f"{failover_endpoint}/health", timeout=10) as resp:
                            checks_passed &= resp.status == 200
                            health_data = await resp.json()
                            checks_passed &= health_data.get("status") == "healthy"
                    except Exception:
                        checks_passed = False
            
            # Verify data consistency
            if self.component_name == "database":
                # Check row counts match
                consistency_check = await backup_service.verify_data_consistency()
                checks_passed &= consistency_check.get("is_consistent", False)
            
            # Check performance metrics
            if self.component_name in ["api", "database"]:
                metrics = await self._get_performance_metrics()
                # Ensure performance is within acceptable range
                checks_passed &= metrics.get("response_time_ms", float('inf')) < 1000
                checks_passed &= metrics.get("error_rate", 1.0) < 0.05
            
            # Verify all dependent services can connect
            dependent_services = get_settings().dr_config.get(f"{self.component_name}_dependents", [])
            for service in dependent_services:
                service_check = await self._check_service_connectivity(service)
                checks_passed &= service_check
            
            return checks_passed
            
        except Exception as e:
            logger.error(f"Post-failover checks failed: {e}")
            return False
    
    async def _validate_recovery_backup(self, backup_timestamp: Optional[datetime]) -> bool:
        """Validate backup for recovery operation."""
        try:
            # Check backup exists
            if not await self._check_backup_exists():
                return False
            
            # If specific timestamp requested, validate it exists
            if backup_timestamp:
                backup_dir = Path(f"/backups/{self.component_name}/{backup_timestamp.strftime('%Y%m%d_%H%M%S')}")
                if not backup_dir.exists():
                    logger.error(f"Backup not found for timestamp: {backup_timestamp}")
                    return False
                
                # Verify backup metadata
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    async with aiofiles.open(metadata_file, 'r') as f:
                        metadata = json.loads(await f.read())
                        # Check backup is complete
                        if not metadata.get("is_complete", False):
                            return False
                        # Check backup is not corrupted
                        if metadata.get("is_corrupted", False):
                            return False
            
            # Validate backup integrity
            integrity_valid = await self._validate_backup_integrity()
            if not integrity_valid:
                return False
            
            # Validate backup completeness
            completeness_valid = await self._validate_backup_completeness()
            
            return completeness_valid
            
        except Exception as e:
            logger.error(f"Recovery backup validation failed: {e}")
            return False
    
    async def _execute_recovery(self, backup_timestamp: Optional[datetime]) -> bool:
        """Execute recovery from backup."""
        try:
            if self.component_name == "database":
                # Restore database from backup
                return await backup_service.restore_from_backup(backup_timestamp)
            
            elif self.component_name == "api":
                # Restore API configuration and state
                backup_dir = self._get_backup_directory(backup_timestamp)
                
                # Stop API service
                await self._stop_service("api")
                
                # Restore configuration files
                config_files = ["routes.json", "middleware.json", "config.json"]
                for config_file in config_files:
                    src = backup_dir / config_file
                    dst = Path(f"/app/config/{config_file}")
                    if src.exists():
                        async with aiofiles.open(src, 'rb') as sf:
                            async with aiofiles.open(dst, 'wb') as df:
                                await df.write(await sf.read())
                
                # Restart API service
                return await self._start_service("api")
            
            elif self.component_name == "config":
                # Restore configuration files
                backup_dir = self._get_backup_directory(backup_timestamp)
                config_dir = Path("/app/config")
                
                # Backup current config
                await self._backup_current_config()
                
                # Restore all config files
                for config_file in backup_dir.glob("*"):
                    if config_file.is_file():
                        dst = config_dir / config_file.name
                        async with aiofiles.open(config_file, 'rb') as sf:
                            async with aiofiles.open(dst, 'wb') as df:
                                await df.write(await sf.read())
                
                # Reload configuration
                return await self._reload_configuration()
            
            else:
                # Generic recovery process
                backup_dir = self._get_backup_directory(backup_timestamp)
                target_dir = Path(f"/app/{self.component_name}")
                
                # Restore files
                import shutil
                shutil.copytree(backup_dir, target_dir, dirs_exist_ok=True)
                
                # Restart component
                return await self._restart_component(self.component_name)
                
        except Exception as e:
            logger.error(f"Recovery execution failed: {e}")
            return False
    
    async def _validate_data_integrity(self) -> bool:
        """Validate data integrity after recovery."""
        try:
            if self.component_name == "database":
                # Run database integrity checks
                integrity_result = await backup_service.check_data_integrity()
                return integrity_result.get("is_valid", False)
            
            elif self.component_name == "api":
                # Verify API endpoints are responding correctly
                test_endpoints = ["/health", "/api/v1/status", "/api/v1/config"]
                api_url = get_settings().api_url
                
                async with aiohttp.ClientSession() as session:
                    for endpoint in test_endpoints:
                        try:
                            async with session.get(f"{api_url}{endpoint}", timeout=5) as resp:
                                if resp.status != 200:
                                    return False
                        except Exception:
                            return False
                return True
            
            elif self.component_name == "config":
                # Validate configuration files
                config_dir = Path("/app/config")
                required_configs = ["config.json", "env.json"]
                
                for config_file in required_configs:
                    config_path = config_dir / config_file
                    if not config_path.exists():
                        return False
                    
                    # Validate JSON format
                    try:
                        async with aiofiles.open(config_path, 'r') as f:
                            json.loads(await f.read())
                    except json.JSONDecodeError:
                        return False
                
                return True
            
            else:
                # Generic integrity check - verify key files exist
                component_dir = Path(f"/app/{self.component_name}")
                return component_dir.exists() and any(component_dir.iterdir())
                
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            return False
    
    async def _get_active_connections(self) -> int:
        """Get number of active connections to the component."""
        try:
            if self.component_name == "database":
                result = await backup_service.get_connection_count()
                return result.get("count", 0)
            elif self.component_name == "api":
                # Query API metrics endpoint
                api_url = get_settings().api_url
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{api_url}/metrics/connections") as resp:
                        data = await resp.json()
                        return data.get("active_connections", 0)
            return 0
        except Exception:
            return 0
    
    async def _switch_cache_cluster(self, primary: str, secondary: str) -> bool:
        """Switch from primary to secondary cache cluster."""
        try:
            settings = get_settings()
            cache_manager_url = settings.cache_manager_url
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "action": "switch_cluster",
                    "from_cluster": primary,
                    "to_cluster": secondary
                }
                async with session.post(f"{cache_manager_url}/switch", json=payload) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Cache cluster switch failed: {e}")
            return False
    
    async def _update_routing_table(self, component: str) -> bool:
        """Update routing table for component failover."""
        try:
            settings = get_settings()
            routing_api = settings.routing_service_url
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "component": component,
                    "action": "failover",
                    "target": "secondary"
                }
                async with session.put(f"{routing_api}/routes", json=payload) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Routing table update failed: {e}")
            return False
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for the component."""
        try:
            if self.component_name in ["api", "database"]:
                metrics_url = get_settings().metrics_service_url
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{metrics_url}/components/{self.component_name}"
                    ) as resp:
                        return await resp.json()
            return {"response_time_ms": 0, "error_rate": 0}
        except Exception:
            return {"response_time_ms": 0, "error_rate": 0}
    
    async def _check_service_connectivity(self, service: str) -> bool:
        """Check if a service can connect to the component."""
        try:
            service_url = get_settings().service_urls.get(service)
            if not service_url:
                return True  # Unknown service, assume OK
            
            async with aiohttp.ClientSession() as session:
                payload = {"target": self.component_name}
                async with session.post(
                    f"{service_url}/connectivity/check",
                    json=payload,
                    timeout=10
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    def _get_backup_directory(self, timestamp: Optional[datetime]) -> Path:
        """Get backup directory path for given timestamp."""
        if timestamp:
            return Path(f"/backups/{self.component_name}/{timestamp.strftime('%Y%m%d_%H%M%S')}")
        else:
            return Path(f"/backups/{self.component_name}/latest")
    
    async def _stop_service(self, service: str) -> bool:
        """Stop a service."""
        try:
            control_url = get_settings().service_control_url
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{control_url}/services/{service}/stop") as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def _start_service(self, service: str) -> bool:
        """Start a service."""
        try:
            control_url = get_settings().service_control_url
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{control_url}/services/{service}/start") as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def _backup_current_config(self) -> bool:
        """Backup current configuration before recovery."""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_dir = Path(f"/backups/config/pre_recovery_{timestamp}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            config_dir = Path("/app/config")
            for config_file in config_dir.glob("*"):
                if config_file.is_file():
                    dst = backup_dir / config_file.name
                    async with aiofiles.open(config_file, 'rb') as sf:
                        async with aiofiles.open(dst, 'wb') as df:
                            await df.write(await sf.read())
            return True
        except Exception:
            return False
    
    async def _reload_configuration(self) -> bool:
        """Reload configuration after recovery."""
        try:
            reload_url = get_settings().config_service_url
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{reload_url}/reload") as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def _restart_component(self, component: str) -> bool:
        """Restart a component."""
        try:
            await self._stop_service(component)
            await asyncio.sleep(2)  # Wait for shutdown
            return await self._start_service(component)
        except Exception:
            return False


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
                logger.info(f"Task cancelled: {task}")

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
