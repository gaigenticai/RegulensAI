"""
File Storage Service
Enterprise-grade file storage with AWS S3 integration and local fallback.
"""

import os
import boto3
import hashlib
import mimetypes
from typing import Dict, List, Any, Optional, BinaryIO
from datetime import datetime, timedelta
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger(__name__)


class FileStorage:
    """Enterprise file storage service with S3 and local storage support."""
    
    def __init__(self):
        self.storage_type = os.getenv('STORAGE_TYPE', 'local')  # 'local' or 's3'
        self.local_storage_path = os.getenv('LOCAL_STORAGE_PATH', '/tmp/regulensai_storage')
        
        # AWS S3 configuration
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-west-2')
        self.s3_bucket = os.getenv('S3_BUCKET_NAME', 'regulensai-storage')
        
        # Initialize storage
        self.s3_client = None
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize storage backend."""
        try:
            if self.storage_type == 's3':
                self._initialize_s3()
            else:
                self._initialize_local()
        except Exception as e:
            logger.error("Storage initialization failed", storage_type=self.storage_type, error=str(e))
            # Fallback to local storage
            self.storage_type = 'local'
            self._initialize_local()
    
    def _initialize_s3(self):
        """Initialize AWS S3 client."""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            # Test connection
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info("S3 storage initialized", bucket=self.s3_bucket)
            
        except Exception as e:
            logger.error("S3 initialization failed", error=str(e))
            raise
    
    def _initialize_local(self):
        """Initialize local file storage."""
        try:
            os.makedirs(self.local_storage_path, exist_ok=True)
            logger.info("Local storage initialized", path=self.local_storage_path)
        except Exception as e:
            logger.error("Local storage initialization failed", error=str(e))
            raise
    
    def upload_file(
        self,
        file_path: str,
        storage_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a file to storage.
        
        Args:
            file_path: Local path to file to upload
            storage_key: Storage key/path for the file
            content_type: MIME content type
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error("File not found for upload", file_path=file_path)
                return False
            
            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_path)
                content_type = content_type or 'application/octet-stream'
            
            if self.storage_type == 's3':
                return self._upload_to_s3(file_path, storage_key, content_type, metadata)
            else:
                return self._upload_to_local(file_path, storage_key, metadata)
                
        except Exception as e:
            logger.error("File upload failed", file_path=file_path, storage_key=storage_key, error=str(e))
            return False
    
    def upload_file_object(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: str = 'application/octet-stream',
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a file object to storage.
        
        Args:
            file_obj: File-like object to upload
            storage_key: Storage key/path for the file
            content_type: MIME content type
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            if self.storage_type == 's3':
                return self._upload_object_to_s3(file_obj, storage_key, content_type, metadata)
            else:
                return self._upload_object_to_local(file_obj, storage_key, metadata)
                
        except Exception as e:
            logger.error("File object upload failed", storage_key=storage_key, error=str(e))
            return False
    
    def download_file(self, storage_key: str, local_path: str) -> bool:
        """
        Download a file from storage to local path.
        
        Args:
            storage_key: Storage key/path of the file
            local_path: Local path to save the file
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            if self.storage_type == 's3':
                return self._download_from_s3(storage_key, local_path)
            else:
                return self._download_from_local(storage_key, local_path)
                
        except Exception as e:
            logger.error("File download failed", storage_key=storage_key, local_path=local_path, error=str(e))
            return False
    
    def get_file_url(
        self,
        storage_key: str,
        expires_in: int = 3600,
        public: bool = False
    ) -> Optional[str]:
        """
        Get a URL to access a file.
        
        Args:
            storage_key: Storage key/path of the file
            expires_in: URL expiration time in seconds
            public: Whether to generate a public URL
            
        Returns:
            File URL or None if failed
        """
        try:
            if self.storage_type == 's3':
                return self._get_s3_url(storage_key, expires_in, public)
            else:
                return self._get_local_url(storage_key)
                
        except Exception as e:
            logger.error("URL generation failed", storage_key=storage_key, error=str(e))
            return None
    
    def delete_file(self, storage_key: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            storage_key: Storage key/path of the file
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if self.storage_type == 's3':
                return self._delete_from_s3(storage_key)
            else:
                return self._delete_from_local(storage_key)
                
        except Exception as e:
            logger.error("File deletion failed", storage_key=storage_key, error=str(e))
            return False
    
    def file_exists(self, storage_key: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            storage_key: Storage key/path of the file
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            if self.storage_type == 's3':
                return self._s3_file_exists(storage_key)
            else:
                return self._local_file_exists(storage_key)
                
        except Exception as e:
            logger.error("File existence check failed", storage_key=storage_key, error=str(e))
            return False
    
    def get_file_info(self, storage_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file information.
        
        Args:
            storage_key: Storage key/path of the file
            
        Returns:
            File information dictionary or None if not found
        """
        try:
            if self.storage_type == 's3':
                return self._get_s3_file_info(storage_key)
            else:
                return self._get_local_file_info(storage_key)
                
        except Exception as e:
            logger.error("File info retrieval failed", storage_key=storage_key, error=str(e))
            return None
    
    # S3 implementation methods
    def _upload_to_s3(self, file_path: str, storage_key: str, content_type: str, metadata: Optional[Dict[str, str]]) -> bool:
        """Upload file to S3."""
        try:
            extra_args = {'ContentType': content_type}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(file_path, self.s3_bucket, storage_key, ExtraArgs=extra_args)
            logger.info("File uploaded to S3", storage_key=storage_key)
            return True
            
        except Exception as e:
            logger.error("S3 upload failed", storage_key=storage_key, error=str(e))
            return False
    
    def _upload_object_to_s3(self, file_obj: BinaryIO, storage_key: str, content_type: str, metadata: Optional[Dict[str, str]]) -> bool:
        """Upload file object to S3."""
        try:
            extra_args = {'ContentType': content_type}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(file_obj, self.s3_bucket, storage_key, ExtraArgs=extra_args)
            logger.info("File object uploaded to S3", storage_key=storage_key)
            return True
            
        except Exception as e:
            logger.error("S3 object upload failed", storage_key=storage_key, error=str(e))
            return False
    
    def _download_from_s3(self, storage_key: str, local_path: str) -> bool:
        """Download file from S3."""
        try:
            self.s3_client.download_file(self.s3_bucket, storage_key, local_path)
            logger.info("File downloaded from S3", storage_key=storage_key, local_path=local_path)
            return True
            
        except Exception as e:
            logger.error("S3 download failed", storage_key=storage_key, error=str(e))
            return False
    
    def _get_s3_url(self, storage_key: str, expires_in: int, public: bool) -> Optional[str]:
        """Get S3 file URL."""
        try:
            if public:
                return f"https://{self.s3_bucket}.s3.{self.aws_region}.amazonaws.com/{storage_key}"
            else:
                return self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.s3_bucket, 'Key': storage_key},
                    ExpiresIn=expires_in
                )
        except Exception as e:
            logger.error("S3 URL generation failed", storage_key=storage_key, error=str(e))
            return None
    
    def _delete_from_s3(self, storage_key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=storage_key)
            logger.info("File deleted from S3", storage_key=storage_key)
            return True
            
        except Exception as e:
            logger.error("S3 deletion failed", storage_key=storage_key, error=str(e))
            return False
    
    def _s3_file_exists(self, storage_key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=storage_key)
            return True
        except:
            return False
    
    def _get_s3_file_info(self, storage_key: str) -> Optional[Dict[str, Any]]:
        """Get S3 file information."""
        try:
            response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=storage_key)
            return {
                'size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
        except Exception as e:
            logger.error("S3 file info failed", storage_key=storage_key, error=str(e))
            return None
    
    # Local storage implementation methods
    def _upload_to_local(self, file_path: str, storage_key: str, metadata: Optional[Dict[str, str]]) -> bool:
        """Upload file to local storage."""
        try:
            local_file_path = os.path.join(self.local_storage_path, storage_key)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(file_path, local_file_path)
            
            # Store metadata if provided
            if metadata:
                metadata_path = local_file_path + '.metadata'
                import json
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f)
            
            logger.info("File uploaded to local storage", storage_key=storage_key)
            return True
            
        except Exception as e:
            logger.error("Local upload failed", storage_key=storage_key, error=str(e))
            return False
    
    def _upload_object_to_local(self, file_obj: BinaryIO, storage_key: str, metadata: Optional[Dict[str, str]]) -> bool:
        """Upload file object to local storage."""
        try:
            local_file_path = os.path.join(self.local_storage_path, storage_key)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            with open(local_file_path, 'wb') as f:
                f.write(file_obj.read())
            
            # Store metadata if provided
            if metadata:
                metadata_path = local_file_path + '.metadata'
                import json
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f)
            
            logger.info("File object uploaded to local storage", storage_key=storage_key)
            return True
            
        except Exception as e:
            logger.error("Local object upload failed", storage_key=storage_key, error=str(e))
            return False
    
    def _download_from_local(self, storage_key: str, local_path: str) -> bool:
        """Download file from local storage."""
        try:
            source_path = os.path.join(self.local_storage_path, storage_key)
            if not os.path.exists(source_path):
                return False
            
            import shutil
            shutil.copy2(source_path, local_path)
            logger.info("File downloaded from local storage", storage_key=storage_key)
            return True
            
        except Exception as e:
            logger.error("Local download failed", storage_key=storage_key, error=str(e))
            return False
    
    def _get_local_url(self, storage_key: str) -> Optional[str]:
        """Get local file URL."""
        # For local storage, return file path
        local_file_path = os.path.join(self.local_storage_path, storage_key)
        if os.path.exists(local_file_path):
            return f"file://{local_file_path}"
        return None
    
    def _delete_from_local(self, storage_key: str) -> bool:
        """Delete file from local storage."""
        try:
            local_file_path = os.path.join(self.local_storage_path, storage_key)
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
                
                # Remove metadata file if exists
                metadata_path = local_file_path + '.metadata'
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
                
                logger.info("File deleted from local storage", storage_key=storage_key)
                return True
            return False
            
        except Exception as e:
            logger.error("Local deletion failed", storage_key=storage_key, error=str(e))
            return False
    
    def _local_file_exists(self, storage_key: str) -> bool:
        """Check if file exists in local storage."""
        local_file_path = os.path.join(self.local_storage_path, storage_key)
        return os.path.exists(local_file_path)
    
    def _get_local_file_info(self, storage_key: str) -> Optional[Dict[str, Any]]:
        """Get local file information."""
        try:
            local_file_path = os.path.join(self.local_storage_path, storage_key)
            if not os.path.exists(local_file_path):
                return None
            
            stat = os.stat(local_file_path)
            content_type, _ = mimetypes.guess_type(local_file_path)
            
            # Load metadata if exists
            metadata = {}
            metadata_path = local_file_path + '.metadata'
            if os.path.exists(metadata_path):
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            return {
                'size': stat.st_size,
                'content_type': content_type,
                'last_modified': datetime.fromtimestamp(stat.st_mtime),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error("Local file info failed", storage_key=storage_key, error=str(e))
            return None
