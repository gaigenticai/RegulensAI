#!/usr/bin/env python3
"""
Database Migration Runner
Safely applies database migrations for the RegulensAI platform.
"""

import os
import sys
import psycopg2
import argparse
from pathlib import Path
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class MigrationRunner:
    """Database migration runner with safety checks and rollback capabilities."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.connection = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(self.database_url)
            self.connection.autocommit = False
            logger.info("Database connection established")
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations."""
        try:
            with self.connection.cursor() as cursor:
                # Check if migration_history table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'migration_history'
                    );
                """)
                
                if not cursor.fetchone()[0]:
                    logger.info("Migration history table does not exist, no migrations applied")
                    return []
                
                # Get applied migrations
                cursor.execute("SELECT migration_name FROM migration_history ORDER BY applied_at")
                applied = [row[0] for row in cursor.fetchall()]
                logger.info("Found applied migrations", count=len(applied), migrations=applied)
                return applied
                
        except Exception as e:
            logger.error("Failed to get applied migrations", error=str(e))
            raise
    
    def get_available_migrations(self) -> List[Path]:
        """Get list of available migration files."""
        try:
            migration_files = []
            for file_path in sorted(self.migrations_dir.glob("*.sql")):
                if file_path.is_file():
                    migration_files.append(file_path)
            
            logger.info("Found migration files", count=len(migration_files))
            return migration_files
            
        except Exception as e:
            logger.error("Failed to get available migrations", error=str(e))
            raise
    
    def get_pending_migrations(self) -> List[Path]:
        """Get list of pending migrations to apply."""
        applied = set(self.get_applied_migrations())
        available = self.get_available_migrations()
        
        pending = []
        for migration_file in available:
            migration_name = migration_file.stem
            if migration_name not in applied:
                pending.append(migration_file)
        
        logger.info("Found pending migrations", count=len(pending))
        return pending
    
    def validate_migration_file(self, migration_file: Path) -> bool:
        """Validate migration file format and content."""
        try:
            with open(migration_file, 'r') as f:
                content = f.read()
            
            # Basic validation checks
            if not content.strip():
                logger.error("Migration file is empty", file=str(migration_file))
                return False
            
            # Check for required elements
            required_elements = [
                "migration_history",  # Should reference migration tracking
                "COMMIT;"  # Should have explicit commit
            ]
            
            for element in required_elements:
                if element not in content:
                    logger.warning("Migration file missing recommended element", 
                                 file=str(migration_file), element=element)
            
            logger.info("Migration file validated", file=str(migration_file))
            return True
            
        except Exception as e:
            logger.error("Failed to validate migration file", file=str(migration_file), error=str(e))
            return False
    
    def apply_migration(self, migration_file: Path, dry_run: bool = False) -> bool:
        """Apply a single migration file."""
        try:
            migration_name = migration_file.stem
            logger.info("Applying migration", migration=migration_name, dry_run=dry_run)
            
            # Validate migration file
            if not self.validate_migration_file(migration_file):
                return False
            
            # Read migration content
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            if dry_run:
                logger.info("DRY RUN: Would apply migration", migration=migration_name)
                print(f"\n--- Migration: {migration_name} ---")
                print(migration_sql)
                print(f"--- End Migration: {migration_name} ---\n")
                return True
            
            # Apply migration in transaction
            with self.connection.cursor() as cursor:
                try:
                    cursor.execute(migration_sql)
                    self.connection.commit()
                    logger.info("Migration applied successfully", migration=migration_name)
                    return True
                    
                except Exception as e:
                    self.connection.rollback()
                    logger.error("Migration failed, rolled back", migration=migration_name, error=str(e))
                    raise
                    
        except Exception as e:
            logger.error("Failed to apply migration", migration=migration_file.stem, error=str(e))
            return False
    
    def run_migrations(self, dry_run: bool = False, target_migration: str = None) -> bool:
        """Run all pending migrations or up to a target migration."""
        try:
            pending_migrations = self.get_pending_migrations()
            
            if not pending_migrations:
                logger.info("No pending migrations to apply")
                return True
            
            # Filter to target migration if specified
            if target_migration:
                filtered_migrations = []
                for migration in pending_migrations:
                    filtered_migrations.append(migration)
                    if migration.stem == target_migration:
                        break
                pending_migrations = filtered_migrations
            
            logger.info("Starting migration run", 
                       count=len(pending_migrations), 
                       dry_run=dry_run,
                       target=target_migration)
            
            # Apply migrations
            for migration_file in pending_migrations:
                if not self.apply_migration(migration_file, dry_run):
                    logger.error("Migration failed, stopping", migration=migration_file.stem)
                    return False
            
            logger.info("All migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error("Migration run failed", error=str(e))
            return False
    
    def rollback_migration(self, migration_name: str, dry_run: bool = False) -> bool:
        """Rollback a specific migration."""
        try:
            logger.info("Rolling back migration", migration=migration_name, dry_run=dry_run)
            
            with self.connection.cursor() as cursor:
                # Get rollback SQL
                cursor.execute(
                    "SELECT rollback_sql FROM migration_history WHERE migration_name = %s",
                    (migration_name,)
                )
                result = cursor.fetchone()
                
                if not result:
                    logger.error("Migration not found in history", migration=migration_name)
                    return False
                
                rollback_sql = result[0]
                if not rollback_sql:
                    logger.error("No rollback SQL available", migration=migration_name)
                    return False
                
                if dry_run:
                    logger.info("DRY RUN: Would rollback migration", migration=migration_name)
                    print(f"\n--- Rollback: {migration_name} ---")
                    print(rollback_sql)
                    print(f"--- End Rollback: {migration_name} ---\n")
                    return True
                
                # Execute rollback
                cursor.execute(rollback_sql)
                
                # Remove from migration history
                cursor.execute(
                    "DELETE FROM migration_history WHERE migration_name = %s",
                    (migration_name,)
                )
                
                self.connection.commit()
                logger.info("Migration rolled back successfully", migration=migration_name)
                return True
                
        except Exception as e:
            self.connection.rollback()
            logger.error("Rollback failed", migration=migration_name, error=str(e))
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        try:
            applied = self.get_applied_migrations()
            available = self.get_available_migrations()
            pending = self.get_pending_migrations()
            
            status = {
                'applied_count': len(applied),
                'available_count': len(available),
                'pending_count': len(pending),
                'applied_migrations': applied,
                'pending_migrations': [m.stem for m in pending],
                'up_to_date': len(pending) == 0
            }
            
            return status
            
        except Exception as e:
            logger.error("Failed to get migration status", error=str(e))
            return {'error': str(e)}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='RegulensAI Database Migration Runner')
    parser.add_argument('--database-url', 
                       default=os.getenv('DATABASE_URL', 'postgresql://localhost/regulensai'),
                       help='Database connection URL')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without applying changes')
    parser.add_argument('--target', 
                       help='Target migration to run up to')
    parser.add_argument('--rollback',
                       help='Rollback specific migration')
    parser.add_argument('--status', action='store_true',
                       help='Show migration status')
    
    args = parser.parse_args()
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    runner = MigrationRunner(args.database_url)
    
    try:
        runner.connect()
        
        if args.status:
            status = runner.get_migration_status()
            print(f"Migration Status:")
            print(f"  Applied: {status['applied_count']}")
            print(f"  Available: {status['available_count']}")
            print(f"  Pending: {status['pending_count']}")
            print(f"  Up to date: {status['up_to_date']}")
            
            if status['pending_migrations']:
                print(f"  Pending migrations: {', '.join(status['pending_migrations'])}")
            
        elif args.rollback:
            success = runner.rollback_migration(args.rollback, args.dry_run)
            sys.exit(0 if success else 1)
            
        else:
            success = runner.run_migrations(args.dry_run, args.target)
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error("Migration runner failed", error=str(e))
        sys.exit(1)
        
    finally:
        runner.disconnect()


if __name__ == "__main__":
    main()
