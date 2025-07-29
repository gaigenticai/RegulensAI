"""
Regulens AI - File Upload Security Framework
Enterprise-grade file upload security with virus scanning and content validation.
"""

import os
import hashlib
import magic
import tempfile
import subprocess
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
import structlog

from core_infra.config import get_settings
from core_infra.api.validation import FileValidator, SecurityValidator
from core_infra.exceptions import DataValidationException, SecurityException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

# Security constants
QUARANTINE_DIR = "/tmp/quarantine"
SAFE_STORAGE_DIR = "/app/uploads"
MAX_SCAN_TIME = 30  # seconds
VIRUS_SCAN_ENABLED = os.getenv('VIRUS_SCAN_ENABLED', 'false').lower() == 'true'

# Dangerous file signatures (magic bytes)
DANGEROUS_SIGNATURES = {
    b'\x4D\x5A': 'Windows Executable',
    b'\x7F\x45\x4C\x46': 'Linux Executable',
    b'\xCA\xFE\xBA\xBE': 'Java Class File',
    b'\xFE\xED\xFA\xCE': 'Mach-O Binary',
    b'\xFE\xED\xFA\xCF': 'Mach-O Binary',
    b'\xCE\xFA\xED\xFE': 'Mach-O Binary',
    b'\xCF\xFA\xED\xFE': 'Mach-O Binary',
    b'\x50\x4B\x03\x04': 'ZIP Archive (potential)',  # Could contain executables
}

# Safe MIME types for document uploads
SAFE_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'text/plain',
    'text/csv',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

class SecurityException(Exception):
    """Security-related exception."""
    pass

class FileSecurityScanner:
    """Comprehensive file security scanning."""
    
    def __init__(self):
        self.quarantine_dir = Path(QUARANTINE_DIR)
        self.safe_storage_dir = Path(SAFE_STORAGE_DIR)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.safe_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions
        os.chmod(self.quarantine_dir, 0o700)
        os.chmod(self.safe_storage_dir, 0o755)
    
    async def scan_upload(self, file: UploadFile, 
                         allowed_types: List[str] = None) -> Dict[str, any]:
        """
        Comprehensive security scan of uploaded file.
        
        Returns:
            Dict containing scan results and file metadata
        """
        if allowed_types is None:
            allowed_types = ['document', 'image']
        
        scan_result = {
            'filename': file.filename,
            'content_type': file.content_type,
            'size': 0,
            'hash_md5': '',
            'hash_sha256': '',
            'mime_type_detected': '',
            'is_safe': False,
            'threats_detected': [],
            'scan_timestamp': '',
            'quarantined': False
        }
        
        try:
            # Read file content
            content = await file.read()
            scan_result['size'] = len(content)
            
            # Reset file pointer
            await file.seek(0)
            
            # Basic validation
            FileValidator.validate_file_size(len(content))
            FileValidator.validate_filename(file.filename)
            
            # Generate file hashes
            scan_result['hash_md5'] = hashlib.md5(content).hexdigest()
            scan_result['hash_sha256'] = hashlib.sha256(content).hexdigest()
            
            # Detect actual MIME type
            detected_mime = magic.from_buffer(content, mime=True)
            scan_result['mime_type_detected'] = detected_mime
            
            # Validate MIME type consistency
            if file.content_type != detected_mime:
                logger.warning(
                    f"MIME type mismatch: declared={file.content_type}, "
                    f"detected={detected_mime}, file={file.filename}"
                )
                scan_result['threats_detected'].append('MIME type mismatch')
            
            # Check if detected MIME type is safe
            if detected_mime not in SAFE_MIME_TYPES:
                scan_result['threats_detected'].append(f'Unsafe MIME type: {detected_mime}')
            
            # Validate against allowed types
            try:
                FileValidator.validate_file_type(file.filename, detected_mime, allowed_types)
            except DataValidationException as e:
                scan_result['threats_detected'].append(f'File type not allowed: {e.details}')
            
            # Check for dangerous file signatures
            threats = self._check_file_signatures(content)
            scan_result['threats_detected'].extend(threats)
            
            # Content-specific security checks
            content_threats = await self._scan_file_content(content, detected_mime)
            scan_result['threats_detected'].extend(content_threats)
            
            # Virus scan if enabled
            if VIRUS_SCAN_ENABLED:
                virus_threats = await self._virus_scan(content, file.filename)
                scan_result['threats_detected'].extend(virus_threats)
            
            # Determine if file is safe
            scan_result['is_safe'] = len(scan_result['threats_detected']) == 0
            
            # Quarantine if threats detected
            if not scan_result['is_safe']:
                quarantine_path = await self._quarantine_file(content, file.filename, scan_result)
                scan_result['quarantined'] = True
                logger.warning(
                    f"File quarantined: {file.filename}, "
                    f"threats: {scan_result['threats_detected']}, "
                    f"path: {quarantine_path}"
                )
            
            scan_result['scan_timestamp'] = str(datetime.utcnow())
            
            return scan_result
            
        except Exception as e:
            logger.error(f"File scan failed: {e}")
            scan_result['threats_detected'].append(f'Scan error: {str(e)}')
            scan_result['is_safe'] = False
            return scan_result
    
    def _check_file_signatures(self, content: bytes) -> List[str]:
        """Check for dangerous file signatures."""
        threats = []
        
        if len(content) < 4:
            return threats
        
        # Check first few bytes for known dangerous signatures
        for signature, description in DANGEROUS_SIGNATURES.items():
            if content.startswith(signature):
                threats.append(f'Dangerous file signature detected: {description}')
        
        # Check for embedded executables in ZIP files
        if content.startswith(b'\x50\x4B\x03\x04'):  # ZIP signature
            # This is a basic check - in production, you'd want more sophisticated ZIP analysis
            if b'.exe' in content or b'.bat' in content or b'.cmd' in content:
                threats.append('ZIP file contains potentially dangerous executables')
        
        return threats
    
    async def _scan_file_content(self, content: bytes, mime_type: str) -> List[str]:
        """Perform content-specific security scans."""
        threats = []
        
        try:
            # PDF-specific checks
            if mime_type == 'application/pdf':
                threats.extend(self._scan_pdf_content(content))
            
            # Image-specific checks
            elif mime_type.startswith('image/'):
                threats.extend(self._scan_image_content(content))
            
            # Text-specific checks
            elif mime_type.startswith('text/'):
                threats.extend(self._scan_text_content(content))
            
            # Office document checks
            elif 'officedocument' in mime_type or 'msword' in mime_type:
                threats.extend(self._scan_office_content(content))
            
        except Exception as e:
            logger.error(f"Content scan error: {e}")
            threats.append(f'Content scan error: {str(e)}')
        
        return threats
    
    def _scan_pdf_content(self, content: bytes) -> List[str]:
        """Scan PDF for security threats."""
        threats = []
        
        # Check for JavaScript in PDF
        if b'/JavaScript' in content or b'/JS' in content:
            threats.append('PDF contains JavaScript')
        
        # Check for forms
        if b'/AcroForm' in content:
            threats.append('PDF contains forms')
        
        # Check for external links
        if b'/URI' in content:
            threats.append('PDF contains external links')
        
        return threats
    
    def _scan_image_content(self, content: bytes) -> List[str]:
        """Scan image for security threats."""
        threats = []
        
        # Check for EXIF data that might contain sensitive information
        if b'Exif' in content:
            # In production, you'd parse EXIF data more thoroughly
            threats.append('Image contains EXIF metadata')
        
        # Check for embedded files (steganography detection would be more complex)
        if len(content) > 10 * 1024 * 1024:  # Unusually large image
            threats.append('Image file unusually large - possible embedded content')
        
        return threats
    
    def _scan_text_content(self, content: bytes) -> List[str]:
        """Scan text content for security threats."""
        threats = []
        
        try:
            text_content = content.decode('utf-8', errors='ignore')
            
            # Check for script content
            if '<script' in text_content.lower():
                threats.append('Text contains script tags')
            
            # Check for SQL injection patterns
            sql_patterns = ['drop table', 'delete from', 'insert into', 'update set']
            for pattern in sql_patterns:
                if pattern in text_content.lower():
                    threats.append('Text contains potential SQL injection')
                    break
            
        except Exception as e:
            threats.append(f'Text content scan error: {str(e)}')
        
        return threats
    
    def _scan_office_content(self, content: bytes) -> List[str]:
        """Scan Office documents for security threats."""
        threats = []
        
        # Check for macros (VBA)
        if b'vbaProject' in content or b'VBA' in content:
            threats.append('Office document contains macros')
        
        # Check for external links
        if b'http://' in content or b'https://' in content:
            threats.append('Office document contains external links')
        
        return threats
    
    async def _virus_scan(self, content: bytes, filename: str) -> List[str]:
        """Perform virus scan using ClamAV or similar."""
        threats = []
        
        try:
            # Create temporary file for scanning
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Run ClamAV scan (if available)
                result = subprocess.run(
                    ['clamscan', '--no-summary', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=MAX_SCAN_TIME
                )
                
                if result.returncode != 0:
                    threats.append(f'Virus scan detected threat: {result.stdout.strip()}')
                
            except subprocess.TimeoutExpired:
                threats.append('Virus scan timeout')
            except FileNotFoundError:
                # ClamAV not installed - log warning but don't fail
                logger.warning("ClamAV not available for virus scanning")
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Virus scan error: {e}")
            threats.append(f'Virus scan error: {str(e)}')
        
        return threats
    
    async def _quarantine_file(self, content: bytes, filename: str, 
                              scan_result: Dict) -> str:
        """Quarantine suspicious file."""
        # Generate unique quarantine filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_filename = SecurityValidator.validate_string_safety(filename, "filename")
        quarantine_filename = f"{timestamp}_{scan_result['hash_sha256'][:8]}_{safe_filename}"
        quarantine_path = self.quarantine_dir / quarantine_filename
        
        # Write file to quarantine
        with open(quarantine_path, 'wb') as f:
            f.write(content)
        
        # Write scan report
        report_path = quarantine_path.with_suffix('.report')
        with open(report_path, 'w') as f:
            f.write(f"Quarantine Report\n")
            f.write(f"Timestamp: {scan_result['scan_timestamp']}\n")
            f.write(f"Original Filename: {filename}\n")
            f.write(f"Size: {scan_result['size']} bytes\n")
            f.write(f"MD5: {scan_result['hash_md5']}\n")
            f.write(f"SHA256: {scan_result['hash_sha256']}\n")
            f.write(f"Detected MIME: {scan_result['mime_type_detected']}\n")
            f.write(f"Threats: {', '.join(scan_result['threats_detected'])}\n")
        
        # Set secure permissions
        os.chmod(quarantine_path, 0o600)
        os.chmod(report_path, 0o600)
        
        return str(quarantine_path)
    
    async def save_safe_file(self, content: bytes, filename: str, 
                           scan_result: Dict) -> str:
        """Save verified safe file to secure storage."""
        if not scan_result['is_safe']:
            raise SecurityException("Cannot save unsafe file")
        
        # Generate secure filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_filename = SecurityValidator.validate_string_safety(filename, "filename")
        storage_filename = f"{timestamp}_{scan_result['hash_sha256'][:8]}_{safe_filename}"
        storage_path = self.safe_storage_dir / storage_filename
        
        # Write file
        with open(storage_path, 'wb') as f:
            f.write(content)
        
        # Set appropriate permissions
        os.chmod(storage_path, 0o644)
        
        logger.info(f"Safe file saved: {storage_filename}")
        return str(storage_path)

# Global scanner instance
file_scanner = FileSecurityScanner()

async def secure_file_upload(file: UploadFile, 
                           allowed_types: List[str] = None) -> Dict[str, any]:
    """
    Secure file upload endpoint with comprehensive security scanning.
    
    Args:
        file: Uploaded file
        allowed_types: List of allowed file types
    
    Returns:
        Dict containing scan results and file information
    
    Raises:
        HTTPException: If file is deemed unsafe
    """
    try:
        # Perform security scan
        scan_result = await file_scanner.scan_upload(file, allowed_types)
        
        # Reject unsafe files
        if not scan_result['is_safe']:
            logger.warning(
                f"Unsafe file upload rejected: {file.filename}, "
                f"threats: {scan_result['threats_detected']}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "File upload rejected due to security threats",
                    "threats": scan_result['threats_detected'],
                    "filename": file.filename
                }
            )
        
        # Save safe file
        content = await file.read()
        storage_path = await file_scanner.save_safe_file(content, file.filename, scan_result)
        scan_result['storage_path'] = storage_path
        
        logger.info(f"Secure file upload successful: {file.filename}")
        return scan_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload security error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload security check failed"
        )
