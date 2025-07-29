"""
Regulens AI - Database Migration Strategy for Blue-Green Deployments
Safe database migrations that support zero-downtime blue-green deployments.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import SystemException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class MigrationPhase(Enum):
    """Migration phase enumeration."""
    PREPARE = "prepare"
    MIGRATE = "migrate"
    VALIDATE = "validate"
    CLEANUP = "cleanup"
    ROLLBACK = "rollback"

class MigrationStatus(Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class MigrationStep:
    """Migration step data structure."""
    id: str
    name: str
    phase: MigrationPhase
    sql_forward: str
    sql_backward: str
    is_breaking: bool
    dependencies: List[str]
    timeout_seconds: int
    status: MigrationStatus
    executed_at: Optional[datetime]
    error_message: Optional[str]

class BlueGreenMigrationManager:
    """Manages database migrations for blue-green deployments."""
    
    def __init__(self):
        self.migration_table = "schema_migrations"
        self.deployment_table = "deployment_migrations"
        
    async def initialize(self):
        """Initialize migration management tables."""
        try:
            async with get_database() as db:
                # Create migration tracking tables
                await db.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.migration_table} (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        migration_id text UNIQUE NOT NULL,
                        name text NOT NULL,
                        phase text NOT NULL,
                        sql_forward text NOT NULL,
                        sql_backward text NOT NULL,
                        is_breaking boolean DEFAULT false,
                        dependencies jsonb DEFAULT '[]',
                        status text NOT NULL DEFAULT 'pending',
                        executed_at timestamp with time zone,
                        error_message text,
                        created_at timestamp with time zone DEFAULT now()
                    )
                """)
                
                await db.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.deployment_table} (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        deployment_id text UNIQUE NOT NULL,
                        slot text NOT NULL,
                        migration_batch_id text NOT NULL,
                        status text NOT NULL DEFAULT 'pending',
                        started_at timestamp with time zone DEFAULT now(),
                        completed_at timestamp with time zone,
                        error_message text
                    )
                """)
                
                # Create indexes
                await db.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_migrations_status 
                    ON {self.migration_table}(status)
                """)
                
                await db.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_deployments_slot 
                    ON {self.deployment_table}(slot, status)
                """)
                
                logger.info("Migration management tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize migration tables: {e}")
            raise SystemException(f"Migration initialization failed: {e}")
    
    async def plan_migration(self, deployment_id: str, slot: str, 
                           target_version: str) -> List[MigrationStep]:
        """Plan migrations for blue-green deployment."""
        try:
            # Get current schema version
            current_version = await self._get_current_schema_version()
            
            # Get required migrations
            migrations = await self._get_migrations_between_versions(current_version, target_version)
            
            # Separate into phases for blue-green compatibility
            migration_steps = []
            
            for migration in migrations:
                # Phase 1: Prepare (non-breaking changes)
                if not migration.get('is_breaking', False):
                    step = MigrationStep(
                        id=str(uuid.uuid4()),
                        name=f"prepare_{migration['name']}",
                        phase=MigrationPhase.PREPARE,
                        sql_forward=migration['sql_forward'],
                        sql_backward=migration['sql_backward'],
                        is_breaking=False,
                        dependencies=migration.get('dependencies', []),
                        timeout_seconds=migration.get('timeout', 300),
                        status=MigrationStatus.PENDING,
                        executed_at=None,
                        error_message=None
                    )
                    migration_steps.append(step)
                else:
                    # Breaking changes need special handling
                    step = MigrationStep(
                        id=str(uuid.uuid4()),
                        name=f"migrate_{migration['name']}",
                        phase=MigrationPhase.MIGRATE,
                        sql_forward=migration['sql_forward'],
                        sql_backward=migration['sql_backward'],
                        is_breaking=True,
                        dependencies=migration.get('dependencies', []),
                        timeout_seconds=migration.get('timeout', 600),
                        status=MigrationStatus.PENDING,
                        executed_at=None,
                        error_message=None
                    )
                    migration_steps.append(step)
            
            # Log migration plan
            await self._log_migration_plan(deployment_id, slot, migration_steps)
            
            return migration_steps
            
        except Exception as e:
            logger.error(f"Failed to plan migration: {e}")
            raise SystemException(f"Migration planning failed: {e}")
    
    async def execute_prepare_phase(self, deployment_id: str, slot: str,
                                  migration_steps: List[MigrationStep]) -> bool:
        """Execute prepare phase migrations (safe for both slots)."""
        try:
            prepare_steps = [step for step in migration_steps if step.phase == MigrationPhase.PREPARE]
            
            if not prepare_steps:
                logger.info("No prepare phase migrations to execute")
                return True
            
            logger.info(f"Executing {len(prepare_steps)} prepare phase migrations")
            
            async with get_database() as db:
                for step in prepare_steps:
                    try:
                        # Execute migration
                        await db.execute(step.sql_forward)
                        
                        # Update status
                        step.status = MigrationStatus.COMPLETED
                        step.executed_at = datetime.utcnow()
                        
                        # Log to database
                        await self._log_migration_step(db, deployment_id, step)
                        
                        logger.info(f"Completed prepare migration: {step.name}")
                        
                    except Exception as e:
                        step.status = MigrationStatus.FAILED
                        step.error_message = str(e)
                        
                        await self._log_migration_step(db, deployment_id, step)
                        
                        logger.error(f"Failed prepare migration {step.name}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Prepare phase execution failed: {e}")
            return False
    
    async def execute_migrate_phase(self, deployment_id: str, slot: str,
                                  migration_steps: List[MigrationStep]) -> bool:
        """Execute migrate phase (breaking changes during traffic switch)."""
        try:
            migrate_steps = [step for step in migration_steps if step.phase == MigrationPhase.MIGRATE]
            
            if not migrate_steps:
                logger.info("No migrate phase migrations to execute")
                return True
            
            logger.info(f"Executing {len(migrate_steps)} migrate phase migrations")
            
            async with get_database() as db:
                # Use transaction for breaking changes
                async with db.transaction():
                    for step in migrate_steps:
                        try:
                            # Execute migration
                            await db.execute(step.sql_forward)
                            
                            # Update status
                            step.status = MigrationStatus.COMPLETED
                            step.executed_at = datetime.utcnow()
                            
                            # Log to database
                            await self._log_migration_step(db, deployment_id, step)
                            
                            logger.info(f"Completed migrate migration: {step.name}")
                            
                        except Exception as e:
                            step.status = MigrationStatus.FAILED
                            step.error_message = str(e)
                            
                            await self._log_migration_step(db, deployment_id, step)
                            
                            logger.error(f"Failed migrate migration {step.name}: {e}")
                            raise  # Will trigger transaction rollback
            
            return True
            
        except Exception as e:
            logger.error(f"Migrate phase execution failed: {e}")
            return False
    
    async def validate_migration(self, deployment_id: str, slot: str,
                               migration_steps: List[MigrationStep]) -> bool:
        """Validate that migrations were applied correctly."""
        try:
            logger.info("Validating migration results")
            
            async with get_database() as db:
                # Check that all migrations are recorded
                for step in migration_steps:
                    if step.status != MigrationStatus.COMPLETED:
                        logger.error(f"Migration step {step.name} not completed")
                        return False
                
                # Run validation queries
                validation_results = await self._run_validation_checks(db)
                
                if not validation_results:
                    logger.error("Migration validation failed")
                    return False
                
                logger.info("Migration validation passed")
                return True
                
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False
    
    async def rollback_migration(self, deployment_id: str, slot: str,
                               migration_steps: List[MigrationStep]) -> bool:
        """Rollback migrations in reverse order."""
        try:
            logger.info("Rolling back migrations")
            
            # Get completed steps in reverse order
            completed_steps = [
                step for step in reversed(migration_steps)
                if step.status == MigrationStatus.COMPLETED
            ]
            
            async with get_database() as db:
                async with db.transaction():
                    for step in completed_steps:
                        try:
                            # Execute rollback SQL
                            await db.execute(step.sql_backward)
                            
                            # Update status
                            step.status = MigrationStatus.ROLLED_BACK
                            
                            # Log rollback
                            await self._log_migration_step(db, deployment_id, step)
                            
                            logger.info(f"Rolled back migration: {step.name}")
                            
                        except Exception as e:
                            logger.error(f"Failed to rollback migration {step.name}: {e}")
                            raise
            
            logger.info("Migration rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Migration rollback failed: {e}")
            return False
    
    async def _get_current_schema_version(self) -> str:
        """Get current schema version."""
        try:
            async with get_database() as db:
                result = await db.fetchval(
                    f"SELECT migration_id FROM {self.migration_table} "
                    f"WHERE status = 'completed' ORDER BY executed_at DESC LIMIT 1"
                )
                return result or "0.0.0"
        except Exception:
            return "0.0.0"
    
    async def _get_migrations_between_versions(self, current: str, target: str) -> List[Dict[str, Any]]:
        """Get migrations needed between versions."""
        # This would typically read from migration files or a registry
        # For now, return example migrations
        return [
            {
                'name': 'add_deployment_tracking',
                'sql_forward': '''
                    ALTER TABLE performance_metrics 
                    ADD COLUMN IF NOT EXISTS deployment_slot text;
                    
                    CREATE INDEX IF NOT EXISTS idx_performance_metrics_slot 
                    ON performance_metrics(deployment_slot);
                ''',
                'sql_backward': '''
                    DROP INDEX IF EXISTS idx_performance_metrics_slot;
                    ALTER TABLE performance_metrics DROP COLUMN IF EXISTS deployment_slot;
                ''',
                'is_breaking': False,
                'dependencies': [],
                'timeout': 300
            }
        ]
    
    async def _log_migration_plan(self, deployment_id: str, slot: str, 
                                migration_steps: List[MigrationStep]):
        """Log migration plan to database."""
        try:
            async with get_database() as db:
                await db.execute(
                    f"""
                    INSERT INTO {self.deployment_table} (
                        deployment_id, slot, migration_batch_id, status
                    ) VALUES ($1, $2, $3, $4)
                    """,
                    deployment_id,
                    slot,
                    f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "planned"
                )
        except Exception as e:
            logger.error(f"Failed to log migration plan: {e}")
    
    async def _log_migration_step(self, db, deployment_id: str, step: MigrationStep):
        """Log migration step execution."""
        try:
            await db.execute(
                f"""
                INSERT INTO {self.migration_table} (
                    migration_id, name, phase, sql_forward, sql_backward,
                    is_breaking, dependencies, status, executed_at, error_message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (migration_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    executed_at = EXCLUDED.executed_at,
                    error_message = EXCLUDED.error_message
                """,
                step.id,
                step.name,
                step.phase.value,
                step.sql_forward,
                step.sql_backward,
                step.is_breaking,
                step.dependencies,
                step.status.value,
                step.executed_at,
                step.error_message
            )
        except Exception as e:
            logger.error(f"Failed to log migration step: {e}")
    
    async def _run_validation_checks(self, db) -> bool:
        """Run post-migration validation checks."""
        try:
            # Check table existence
            tables_exist = await db.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN (
                    'tenants', 'users', 'customers', 'transactions',
                    'compliance_programs', 'performance_metrics'
                )
            """)
            
            if tables_exist < 6:
                logger.error(f"Expected 6 core tables, found {tables_exist}")
                return False
            
            # Check indexes
            indexes_exist = await db.fetchval("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
            """)
            
            if indexes_exist < 10:
                logger.warning(f"Expected at least 10 indexes, found {indexes_exist}")
            
            return True
            
        except Exception as e:
            logger.error(f"Validation checks failed: {e}")
            return False

# Global migration manager instance
migration_manager = BlueGreenMigrationManager()

# Convenience functions
async def plan_deployment_migration(deployment_id: str, slot: str, target_version: str) -> List[MigrationStep]:
    """Plan migrations for deployment."""
    return await migration_manager.plan_migration(deployment_id, slot, target_version)

async def execute_prepare_migrations(deployment_id: str, slot: str, steps: List[MigrationStep]) -> bool:
    """Execute prepare phase migrations."""
    return await migration_manager.execute_prepare_phase(deployment_id, slot, steps)

async def execute_migrate_migrations(deployment_id: str, slot: str, steps: List[MigrationStep]) -> bool:
    """Execute migrate phase migrations."""
    return await migration_manager.execute_migrate_phase(deployment_id, slot, steps)

async def validate_deployment_migration(deployment_id: str, slot: str, steps: List[MigrationStep]) -> bool:
    """Validate migration results."""
    return await migration_manager.validate_migration(deployment_id, slot, steps)

async def rollback_deployment_migration(deployment_id: str, slot: str, steps: List[MigrationStep]) -> bool:
    """Rollback deployment migrations."""
    return await migration_manager.rollback_migration(deployment_id, slot, steps)
