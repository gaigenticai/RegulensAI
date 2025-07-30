"""
RegulensAI Backup Service
Enterprise-grade backup management with scheduling, monitoring, and S3 integration.
"""

import asyncio
import subprocess
import os
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import SystemException

logger = structlog.get_logger(__name__)


class BackupService:
    """
    Enterprise backup service with automated scheduling and monitoring.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.backup_dir = Path("/tmp/backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Backup configuration
        self.s3_bucket = self.settings.backup_s3_bucket
        self.retention_days = self.settings.backup_retention_days
        self.compression_enabled = self.settings.backup_compression_enabled
        self.notification_webhook = self.settings.backup_notification_webhook
        
        # Backup statistics
        self.backup_stats = {
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "last_backup_time": None,
            "last_backup_size": 0,
            "average_backup_time": 0
        }
    
    async def start(self):
        """Start the backup service with scheduled jobs."""
        try:
            logger.info("Starting backup service")
            
            # Add scheduled backup job
            if self.settings.backup_enabled:
                self.scheduler.add_job(
                    self.execute_scheduled_backup,
                    CronTrigger.from_crontab(self.settings.backup_schedule),
                    id="scheduled_backup",
                    name="Scheduled Database Backup",
                    max_instances=1,
                    coalesce=True
                )
                
                logger.info("Scheduled backup job added", 
                           schedule=self.settings.backup_schedule)
            
            # Add cleanup job (daily at 3 AM)
            self.scheduler.add_job(
                self.cleanup_old_backups,
                CronTrigger(hour=3, minute=0),
                id="backup_cleanup",
                name="Backup Cleanup",
                max_instances=1
            )
            
            # Start scheduler
            self.scheduler.start()
            logger.info("Backup service started successfully")
            
        except Exception as e:
            logger.error("Failed to start backup service", error=str(e))
            raise SystemException("backup_service_start_failed", str(e))
    
    async def stop(self):
        """Stop the backup service."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            logger.info("Backup service stopped")
        except Exception as e:
            logger.error("Error stopping backup service", error=str(e))
    
    async def execute_scheduled_backup(self):
        """Execute scheduled backup."""
        try:
            logger.info("Starting scheduled backup")
            
            result = await self.create_backup(
                environment="production",
                backup_type="full",
                user_id="system"
            )
            
            if result["success"]:
                logger.info("Scheduled backup completed successfully")
                await self._send_notification("SUCCESS", "Scheduled backup completed successfully")
            else:
                logger.error("Scheduled backup failed", error=result.get("error"))
                await self._send_notification("FAILED", f"Scheduled backup failed: {result.get('error')}")
                
        except Exception as e:
            logger.error("Scheduled backup error", error=str(e))
            await self._send_notification("FAILED", f"Scheduled backup error: {str(e)}")
    
    async def create_backup(
        self, 
        environment: str = "production", 
        backup_type: str = "full",
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Create database backup.
        
        Args:
            environment: Target environment (production, staging, development)
            backup_type: Type of backup (full, incremental, compressed)
            user_id: User ID requesting the backup
            
        Returns:
            Dict containing backup result and metadata
        """
        start_time = datetime.utcnow()
        backup_id = f"backup_{int(start_time.timestamp())}"
        
        try:
            logger.info("Creating backup", 
                       backup_id=backup_id,
                       environment=environment, 
                       type=backup_type, 
                       user=user_id)
            
            # Update statistics
            self.backup_stats["total_backups"] += 1
            
            # Determine database URL
            db_url = self._get_database_url(environment)
            
            # Create backup filename
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"regulensai_{environment}_{backup_type}_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Execute pg_dump
            backup_size = await self._execute_pg_dump(db_url, backup_path)
            
            # Compress if enabled
            if self.compression_enabled or backup_type == "compressed":
                backup_path = await self._compress_backup(backup_path)
                backup_size = backup_path.stat().st_size
            
            # Upload to S3 if configured
            s3_url = None
            if self.s3_bucket:
                s3_url = await self._upload_to_s3(backup_path, environment)
                
                # Clean up local file after successful upload
                backup_path.unlink()
                logger.info("Local backup file cleaned up", file=str(backup_path))
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Update statistics
            self.backup_stats["successful_backups"] += 1
            self.backup_stats["last_backup_time"] = end_time.isoformat()
            self.backup_stats["last_backup_size"] = backup_size
            
            # Calculate average backup time
            if self.backup_stats["successful_backups"] > 0:
                current_avg = self.backup_stats["average_backup_time"]
                new_avg = (current_avg * (self.backup_stats["successful_backups"] - 1) + duration) / self.backup_stats["successful_backups"]
                self.backup_stats["average_backup_time"] = round(new_avg, 2)
            
            result = {
                "success": True,
                "backup_id": backup_id,
                "filename": backup_path.name if not s3_url else backup_filename,
                "size_bytes": backup_size,
                "size_mb": round(backup_size / 1024 / 1024, 2),
                "duration_seconds": round(duration, 2),
                "s3_url": s3_url,
                "environment": environment,
                "type": backup_type,
                "timestamp": end_time.isoformat()
            }
            
            logger.info("Backup created successfully", **result)
            return result
            
        except Exception as e:
            # Update failure statistics
            self.backup_stats["failed_backups"] += 1
            
            error_msg = str(e)
            logger.error("Backup creation failed", 
                        backup_id=backup_id,
                        error=error_msg,
                        environment=environment)
            
            return {
                "success": False,
                "backup_id": backup_id,
                "error": error_msg,
                "environment": environment,
                "type": backup_type,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_pg_dump(self, db_url: str, backup_path: Path) -> int:
        """Execute pg_dump command."""
        cmd = [
            "pg_dump",
            db_url,
            "--format=custom",
            "--compress=0",  # We'll compress separately if needed
            "--verbose",
            "--file", str(backup_path)
        ]
        
        logger.info("Executing pg_dump", file=str(backup_path))
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            backup_size = backup_path.stat().st_size
            logger.info("pg_dump completed successfully", 
                       size_bytes=backup_size,
                       size_mb=round(backup_size / 1024 / 1024, 2))
            return backup_size
        else:
            error_msg = stderr.decode() if stderr else "Unknown pg_dump error"
            raise Exception(f"pg_dump failed: {error_msg}")
    
    async def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file using gzip."""
        compressed_path = backup_path.with_suffix(backup_path.suffix + '.gz')
        
        logger.info("Compressing backup", 
                   source=str(backup_path),
                   target=str(compressed_path))
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb', compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        backup_path.unlink()
        
        compressed_size = compressed_path.stat().st_size
        logger.info("Backup compressed successfully",
                   file=str(compressed_path),
                   size_mb=round(compressed_size / 1024 / 1024, 2))
        
        return compressed_path
    
    async def _upload_to_s3(self, backup_path: Path, environment: str) -> str:
        """Upload backup to S3."""
        s3_key = f"database/{environment}/{backup_path.name}"
        s3_url = f"s3://{self.s3_bucket}/{s3_key}"
        
        cmd = [
            "aws", "s3", "cp", str(backup_path), s3_url,
            "--storage-class", "STANDARD_IA",
            "--metadata", f"environment={environment},timestamp={datetime.utcnow().isoformat()}"
        ]
        
        logger.info("Uploading to S3", s3_url=s3_url)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("S3 upload completed successfully", s3_url=s3_url)
            return s3_url
        else:
            error_msg = stderr.decode() if stderr else "Unknown S3 upload error"
            raise Exception(f"S3 upload failed: {error_msg}")
    
    async def cleanup_old_backups(self):
        """Clean up old backups based on retention policy."""
        try:
            logger.info("Starting backup cleanup", retention_days=self.retention_days)
            
            if self.s3_bucket:
                await self._cleanup_s3_backups()
            
            # Clean up local backups
            await self._cleanup_local_backups()
            
            logger.info("Backup cleanup completed")
            
        except Exception as e:
            logger.error("Backup cleanup failed", error=str(e))
    
    async def _cleanup_s3_backups(self):
        """Clean up old S3 backups."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # List objects in S3 bucket
        cmd = [
            "aws", "s3api", "list-objects-v2",
            "--bucket", self.s3_bucket,
            "--prefix", "database/",
            "--query", f"Contents[?LastModified<='{cutoff_date.isoformat()}'].Key",
            "--output", "text"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and stdout:
            old_keys = stdout.decode().strip().split('\n')
            
            for key in old_keys:
                if key and key != "None":
                    delete_cmd = ["aws", "s3", "rm", f"s3://{self.s3_bucket}/{key}"]
                    
                    delete_process = await asyncio.create_subprocess_exec(
                        *delete_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    await delete_process.communicate()
                    
                    if delete_process.returncode == 0:
                        logger.info("Deleted old S3 backup", key=key)
                    else:
                        logger.warning("Failed to delete S3 backup", key=key)
    
    async def _cleanup_local_backups(self):
        """Clean up old local backups."""
        cutoff_time = datetime.utcnow() - timedelta(days=7)  # Keep local backups for 7 days
        
        for backup_file in self.backup_dir.glob("regulensai_*.sql*"):
            if backup_file.stat().st_mtime < cutoff_time.timestamp():
                backup_file.unlink()
                logger.info("Deleted old local backup", file=str(backup_file))
    
    def _get_database_url(self, environment: str) -> str:
        """Get database URL for environment."""
        if environment == "staging" and self.settings.staging_database_url:
            return self.settings.staging_database_url
        else:
            return self.settings.database_url
    
    async def _send_notification(self, status: str, message: str):
        """Send backup notification."""
        if not self.notification_webhook:
            return
        
        try:
            import aiohttp
            
            payload = {
                "text": f"RegulensAI Backup {status}",
                "attachments": [{
                    "color": "good" if status == "SUCCESS" else "danger",
                    "fields": [{
                        "title": "Status",
                        "value": status,
                        "short": True
                    }, {
                        "title": "Timestamp",
                        "value": datetime.utcnow().isoformat(),
                        "short": True
                    }, {
                        "title": "Message",
                        "value": message,
                        "short": False
                    }]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.notification_webhook, json=payload) as response:
                    if response.status == 200:
                        logger.info("Notification sent successfully")
                    else:
                        logger.warning("Failed to send notification", status=response.status)
                        
        except Exception as e:
            logger.error("Notification error", error=str(e))
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup service statistics."""
        return {
            **self.backup_stats,
            "service_status": "running" if self.scheduler.running else "stopped",
            "next_scheduled_backup": self._get_next_backup_time(),
            "retention_days": self.retention_days,
            "s3_bucket": self.s3_bucket,
            "compression_enabled": self.compression_enabled
        }
    
    def _get_next_backup_time(self) -> Optional[str]:
        """Get next scheduled backup time."""
        try:
            job = self.scheduler.get_job("scheduled_backup")
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except:
            pass
        return None


# Global backup service instance
backup_service = BackupService()
