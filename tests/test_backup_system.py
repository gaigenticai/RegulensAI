"""
Tests for RegulensAI Backup System
Comprehensive testing of backup creation, scheduling, and restoration.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Import backup components
from core_infra.services.backup_service import BackupService
from core_infra.config import get_settings


class TestBackupService:
    """Test backup service functionality."""
    
    @pytest.fixture
    def backup_service(self):
        """Create backup service instance for testing."""
        with patch('core_infra.services.backup_service.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                backup_enabled=True,
                backup_s3_bucket="test-bucket",
                backup_retention_days=30,
                backup_schedule="0 2 * * *",
                backup_compression_enabled=True,
                backup_notification_webhook=None,
                database_url="postgresql://test:test@localhost:5432/test",
                staging_database_url=None
            )
            
            service = BackupService()
            yield service
    
    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()
            yield backup_dir
    
    @pytest.mark.asyncio
    async def test_backup_service_initialization(self, backup_service):
        """Test backup service initialization."""
        assert backup_service.s3_bucket == "test-bucket"
        assert backup_service.retention_days == 30
        assert backup_service.compression_enabled is True
        assert backup_service.backup_stats["total_backups"] == 0
    
    @pytest.mark.asyncio
    async def test_create_backup_success(self, backup_service, temp_backup_dir):
        """Test successful backup creation."""
        backup_service.backup_dir = temp_backup_dir
        
        # Mock pg_dump execution
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful pg_dump
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"", b"")
            mock_subprocess.return_value = mock_process
            
            # Create a fake backup file
            backup_file = temp_backup_dir / "test_backup.sql"
            backup_file.write_text("-- Test backup content")
            
            # Mock file operations
            with patch.object(Path, 'stat') as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024  # 1MB
                
                with patch.object(backup_service, '_upload_to_s3') as mock_upload:
                    mock_upload.return_value = "s3://test-bucket/backup.sql.gz"
                    
                    result = await backup_service.create_backup(
                        environment="test",
                        backup_type="full",
                        user_id="test_user"
                    )
        
        assert result["success"] is True
        assert result["environment"] == "test"
        assert result["type"] == "full"
        assert "backup_id" in result
        assert "size_mb" in result
        assert backup_service.backup_stats["successful_backups"] == 1
    
    @pytest.mark.asyncio
    async def test_create_backup_pg_dump_failure(self, backup_service, temp_backup_dir):
        """Test backup creation with pg_dump failure."""
        backup_service.backup_dir = temp_backup_dir
        
        # Mock pg_dump failure
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"pg_dump: error message")
            mock_subprocess.return_value = mock_process
            
            result = await backup_service.create_backup(
                environment="test",
                backup_type="full",
                user_id="test_user"
            )
        
        assert result["success"] is False
        assert "error" in result
        assert backup_service.backup_stats["failed_backups"] == 1
    
    @pytest.mark.asyncio
    async def test_backup_compression(self, backup_service, temp_backup_dir):
        """Test backup compression functionality."""
        backup_service.backup_dir = temp_backup_dir
        
        # Create test backup file
        test_content = "-- Test backup content\n" * 1000
        backup_file = temp_backup_dir / "test_backup.sql"
        backup_file.write_text(test_content)
        
        # Test compression
        compressed_file = await backup_service._compress_backup(backup_file)
        
        assert compressed_file.suffix == ".gz"
        assert compressed_file.exists()
        assert not backup_file.exists()  # Original should be removed
        assert compressed_file.stat().st_size < len(test_content.encode())
    
    @pytest.mark.asyncio
    async def test_s3_upload_success(self, backup_service, temp_backup_dir):
        """Test successful S3 upload."""
        # Create test file
        test_file = temp_backup_dir / "test_backup.sql.gz"
        test_file.write_text("compressed backup content")
        
        # Mock successful AWS CLI
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"", b"")
            mock_subprocess.return_value = mock_process
            
            s3_url = await backup_service._upload_to_s3(test_file, "production")
        
        assert s3_url == "s3://test-bucket/database/production/test_backup.sql.gz"
    
    @pytest.mark.asyncio
    async def test_s3_upload_failure(self, backup_service, temp_backup_dir):
        """Test S3 upload failure."""
        # Create test file
        test_file = temp_backup_dir / "test_backup.sql.gz"
        test_file.write_text("compressed backup content")
        
        # Mock failed AWS CLI
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"S3 upload failed")
            mock_subprocess.return_value = mock_process
            
            with pytest.raises(Exception, match="S3 upload failed"):
                await backup_service._upload_to_s3(test_file, "production")
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, backup_service, temp_backup_dir):
        """Test cleanup of old backup files."""
        backup_service.backup_dir = temp_backup_dir
        
        # Create old backup files
        old_time = datetime.utcnow() - timedelta(days=10)
        old_timestamp = old_time.timestamp()
        
        old_backup = temp_backup_dir / "regulensai_old_backup.sql.gz"
        old_backup.write_text("old backup")
        os.utime(old_backup, (old_timestamp, old_timestamp))
        
        # Create recent backup file
        recent_backup = temp_backup_dir / "regulensai_recent_backup.sql.gz"
        recent_backup.write_text("recent backup")
        
        # Mock S3 cleanup
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"old_backup.sql.gz", b"")
            mock_subprocess.return_value = mock_process
            
            await backup_service.cleanup_old_backups()
        
        # Old local backup should be removed, recent should remain
        assert not old_backup.exists()
        assert recent_backup.exists()
    
    @pytest.mark.asyncio
    async def test_backup_statistics(self, backup_service):
        """Test backup statistics tracking."""
        # Initial stats
        stats = backup_service.get_backup_stats()
        assert stats["total_backups"] == 0
        assert stats["successful_backups"] == 0
        assert stats["failed_backups"] == 0
        
        # Update stats manually for testing
        backup_service.backup_stats["total_backups"] = 10
        backup_service.backup_stats["successful_backups"] = 8
        backup_service.backup_stats["failed_backups"] = 2
        backup_service.backup_stats["last_backup_time"] = datetime.utcnow().isoformat()
        backup_service.backup_stats["last_backup_size"] = 1024 * 1024
        backup_service.backup_stats["average_backup_time"] = 45.5
        
        stats = backup_service.get_backup_stats()
        assert stats["total_backups"] == 10
        assert stats["successful_backups"] == 8
        assert stats["failed_backups"] == 2
        assert stats["last_backup_time"] is not None
        assert stats["last_backup_size"] == 1024 * 1024
        assert stats["average_backup_time"] == 45.5
        assert stats["retention_days"] == 30
        assert stats["s3_bucket"] == "test-bucket"
    
    @pytest.mark.asyncio
    async def test_database_url_selection(self, backup_service):
        """Test database URL selection for different environments."""
        # Test production environment
        db_url = backup_service._get_database_url("production")
        assert db_url == "postgresql://test:test@localhost:5432/test"
        
        # Test staging environment (should fall back to production)
        db_url = backup_service._get_database_url("staging")
        assert db_url == "postgresql://test:test@localhost:5432/test"
        
        # Test with staging URL configured
        backup_service.settings.staging_database_url = "postgresql://staging:test@localhost:5432/staging"
        db_url = backup_service._get_database_url("staging")
        assert db_url == "postgresql://staging:test@localhost:5432/staging"
    
    @pytest.mark.asyncio
    async def test_notification_sending(self, backup_service):
        """Test backup notification sending."""
        backup_service.notification_webhook = "https://hooks.slack.com/test"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await backup_service._send_notification("SUCCESS", "Test message")
            
            # Verify notification was sent
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "json" in call_args.kwargs
            payload = call_args.kwargs["json"]
            assert "RegulensAI Backup SUCCESS" in payload["text"]


class TestBackupAPI:
    """Test backup API endpoints."""
    
    @pytest.mark.asyncio
    async def test_backup_api_endpoint(self):
        """Test backup API endpoint functionality."""
        from core_infra.api.routes.operations import execute_backup
        
        # Mock the backup execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            
            with patch('os.path.getsize') as mock_getsize:
                mock_getsize.return_value = 1024 * 1024  # 1MB
                
                with patch('os.remove'):
                    # Test should not raise exception
                    await execute_backup("production", "full", "test_user")


class TestBackupCLI:
    """Test backup CLI functionality."""
    
    def test_cli_help(self):
        """Test CLI help functionality."""
        import subprocess
        
        result = subprocess.run(
            ["python", "scripts/backup_manager.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0
        assert "RegulensAI Backup Manager" in result.stdout
        assert "create" in result.stdout
        assert "list" in result.stdout
        assert "restore" in result.stdout
        assert "status" in result.stdout


class TestBackupScripts:
    """Test backup shell scripts."""
    
    def test_backup_script_exists(self):
        """Test that backup script exists and is executable."""
        script_path = Path(__file__).parent.parent / "deployment/training-portal/scripts/backup.sh"
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)
    
    def test_restore_script_exists(self):
        """Test that restore script exists and is executable."""
        script_path = Path(__file__).parent.parent / "deployment/training-portal/scripts/restore.sh"
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)
    
    def test_backup_script_help(self):
        """Test backup script help functionality."""
        script_path = Path(__file__).parent.parent / "deployment/training-portal/scripts/backup.sh"
        
        result = subprocess.run(
            [str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "RegulensAI Database Backup Script" in result.stdout
    
    def test_restore_script_help(self):
        """Test restore script help functionality."""
        script_path = Path(__file__).parent.parent / "deployment/training-portal/scripts/restore.sh"
        
        result = subprocess.run(
            [str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "RegulensAI Database Restore Script" in result.stdout


class TestBackupDocker:
    """Test backup Docker configuration."""
    
    def test_backup_dockerfile_exists(self):
        """Test that backup Dockerfile exists."""
        dockerfile_path = Path(__file__).parent.parent / "deployment/training-portal/Dockerfile.backup"
        assert dockerfile_path.exists()
    
    def test_backup_dockerfile_content(self):
        """Test backup Dockerfile content."""
        dockerfile_path = Path(__file__).parent.parent / "deployment/training-portal/Dockerfile.backup"
        content = dockerfile_path.read_text()
        
        assert "postgresql15-client" in content
        assert "aws-cli" in content
        assert "dcron" in content
        assert "backup.sh" in content
        assert "restore.sh" in content
        assert "HEALTHCHECK" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
