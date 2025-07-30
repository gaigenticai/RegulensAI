#!/usr/bin/env python3
"""
RegulensAI Backup Manager CLI
Command-line interface for managing database backups.
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_infra.services.backup_service import backup_service
from core_infra.config import get_settings
import structlog

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

logger = structlog.get_logger(__name__)


class BackupManagerCLI:
    """Command-line interface for backup management."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def create_backup(self, args):
        """Create a new backup."""
        try:
            print(f"Creating {args.type} backup for {args.environment} environment...")
            
            result = await backup_service.create_backup(
                environment=args.environment,
                backup_type=args.type,
                user_id=args.user or "cli"
            )
            
            if result["success"]:
                print("✅ Backup created successfully!")
                print(f"   Backup ID: {result['backup_id']}")
                print(f"   Filename: {result['filename']}")
                print(f"   Size: {result['size_mb']} MB")
                print(f"   Duration: {result['duration_seconds']} seconds")
                
                if result.get("s3_url"):
                    print(f"   S3 URL: {result['s3_url']}")
                
                return 0
            else:
                print("❌ Backup failed!")
                print(f"   Error: {result['error']}")
                return 1
                
        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            logger.error("Backup creation failed", error=str(e))
            return 1
    
    async def list_backups(self, args):
        """List available backups."""
        try:
            if not self.settings.backup_s3_bucket:
                print("❌ S3 bucket not configured for backup listing")
                return 1
            
            print(f"Listing backups from S3 bucket: {self.settings.backup_s3_bucket}")
            print(f"Environment: {args.environment}")
            print()
            
            # Use AWS CLI to list backups
            import subprocess
            
            cmd = [
                "aws", "s3", "ls", 
                f"s3://{self.settings.backup_s3_bucket}/database/{args.environment}/",
                "--recursive", "--human-readable"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    print("Available backups:")
                    print("-" * 80)
                    print(f"{'Date':<12} {'Time':<8} {'Size':<10} {'Filename'}")
                    print("-" * 80)
                    
                    for line in lines:
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 4:
                                date = parts[0]
                                time = parts[1]
                                size = parts[2]
                                filename = parts[3].split('/')[-1]
                                print(f"{date:<12} {time:<8} {size:<10} {filename}")
                else:
                    print("No backups found.")
            else:
                print(f"❌ Failed to list backups: {result.stderr}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to list backups: {e}")
            logger.error("Backup listing failed", error=str(e))
            return 1
    
    async def restore_backup(self, args):
        """Restore from backup."""
        try:
            if not args.force:
                print("⚠️  WARNING: This will replace all data in the current database!")
                print(f"   Environment: {args.environment}")
                print(f"   Backup file: {args.backup_file}")
                print()
                
                response = input("Are you sure you want to continue? (yes/no): ")
                if response.lower() != 'yes':
                    print("Restore cancelled.")
                    return 0
            
            print(f"Restoring from backup: {args.backup_file}")
            print("This may take several minutes...")
            
            # Use the restore script
            import subprocess
            
            script_path = Path(__file__).parent.parent / "deployment/training-portal/scripts/restore.sh"
            
            env = {
                **dict(os.environ),
                "DATABASE_URL": self._get_database_url(args.environment),
                "S3_BUCKET": self.settings.backup_s3_bucket or "",
                "ENVIRONMENT": args.environment
            }
            
            cmd = [str(script_path), args.backup_file]
            if args.force:
                cmd.append("--force")
            
            result = subprocess.run(cmd, env=env, text=True)
            
            if result.returncode == 0:
                print("✅ Restore completed successfully!")
                return 0
            else:
                print("❌ Restore failed!")
                return 1
                
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            logger.error("Restore failed", error=str(e))
            return 1
    
    async def show_status(self, args):
        """Show backup service status."""
        try:
            stats = backup_service.get_backup_stats()
            
            print("RegulensAI Backup Service Status")
            print("=" * 40)
            print(f"Service Status: {stats['service_status']}")
            print(f"Total Backups: {stats['total_backups']}")
            print(f"Successful: {stats['successful_backups']}")
            print(f"Failed: {stats['failed_backups']}")
            
            if stats['last_backup_time']:
                print(f"Last Backup: {stats['last_backup_time']}")
                print(f"Last Backup Size: {round(stats['last_backup_size'] / 1024 / 1024, 2)} MB")
            
            if stats['next_scheduled_backup']:
                print(f"Next Scheduled: {stats['next_scheduled_backup']}")
            
            print(f"Average Duration: {stats['average_backup_time']} seconds")
            print(f"Retention: {stats['retention_days']} days")
            print(f"S3 Bucket: {stats['s3_bucket'] or 'Not configured'}")
            print(f"Compression: {'Enabled' if stats['compression_enabled'] else 'Disabled'}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
            logger.error("Status check failed", error=str(e))
            return 1
    
    async def test_backup(self, args):
        """Test backup functionality."""
        try:
            print("Testing backup functionality...")
            
            # Test database connectivity
            print("1. Testing database connectivity...")
            import asyncpg
            
            db_url = self._get_database_url(args.environment)
            try:
                conn = await asyncpg.connect(db_url)
                await conn.close()
                print("   ✅ Database connection successful")
            except Exception as e:
                print(f"   ❌ Database connection failed: {e}")
                return 1
            
            # Test S3 connectivity
            if self.settings.backup_s3_bucket:
                print("2. Testing S3 connectivity...")
                import subprocess
                
                result = subprocess.run(
                    ["aws", "s3", "ls", f"s3://{self.settings.backup_s3_bucket}"],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    print("   ✅ S3 connection successful")
                else:
                    print(f"   ❌ S3 connection failed: {result.stderr}")
                    return 1
            else:
                print("2. S3 not configured, skipping test")
            
            # Test backup tools
            print("3. Testing backup tools...")
            tools = ["pg_dump", "pg_restore", "gzip"]
            
            for tool in tools:
                result = subprocess.run(
                    ["which", tool], 
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    print(f"   ✅ {tool} available")
                else:
                    print(f"   ❌ {tool} not found")
                    return 1
            
            print("\n✅ All backup tests passed!")
            return 0
            
        except Exception as e:
            print(f"❌ Backup test failed: {e}")
            logger.error("Backup test failed", error=str(e))
            return 1
    
    def _get_database_url(self, environment: str) -> str:
        """Get database URL for environment."""
        if environment == "staging" and self.settings.staging_database_url:
            return self.settings.staging_database_url
        else:
            return self.settings.database_url


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RegulensAI Backup Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create --environment production --type full
  %(prog)s list --environment production
  %(prog)s restore backup_file.sql.gz --environment staging
  %(prog)s status
  %(prog)s test --environment production
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create backup command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument("--environment", "-e", default="production",
                              choices=["production", "staging", "development"],
                              help="Target environment")
    create_parser.add_argument("--type", "-t", default="full",
                              choices=["full", "incremental", "compressed"],
                              help="Backup type")
    create_parser.add_argument("--user", "-u", help="User ID for audit trail")
    
    # List backups command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument("--environment", "-e", default="production",
                            choices=["production", "staging", "development"],
                            help="Target environment")
    
    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore")
    restore_parser.add_argument("--environment", "-e", default="production",
                               choices=["production", "staging", "development"],
                               help="Target environment")
    restore_parser.add_argument("--force", "-f", action="store_true",
                               help="Skip confirmation prompts")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show backup service status")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test backup functionality")
    test_parser.add_argument("--environment", "-e", default="production",
                            choices=["production", "staging", "development"],
                            help="Target environment")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = BackupManagerCLI()
    
    # Execute command
    if args.command == "create":
        return await cli.create_backup(args)
    elif args.command == "list":
        return await cli.list_backups(args)
    elif args.command == "restore":
        return await cli.restore_backup(args)
    elif args.command == "status":
        return await cli.show_status(args)
    elif args.command == "test":
        return await cli.test_backup(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    import os
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
