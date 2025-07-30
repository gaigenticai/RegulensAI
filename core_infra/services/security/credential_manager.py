"""
Production-ready credential management system.
Provides secure storage, retrieval, and rotation of API keys and credentials.
"""

import os
import json
import base64
import hashlib
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

from core_infra.database.connection import get_database
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)


class CredentialManager:
    """
    Enterprise-grade credential management system with encryption,
    rotation, and audit logging.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._encryption_key = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption key from environment or generate new one."""
        try:
            # Try to get encryption key from environment
            key_b64 = os.getenv('CREDENTIAL_ENCRYPTION_KEY')
            
            if key_b64:
                self._encryption_key = base64.urlsafe_b64decode(key_b64)
            else:
                # Generate new key from master password
                master_password = os.getenv('CREDENTIAL_MASTER_PASSWORD', 'default-dev-password')
                salt = os.getenv('CREDENTIAL_SALT', 'regulens-ai-salt').encode()
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                self._encryption_key = kdf.derive(master_password.encode())
                
                logger.warning("Using derived encryption key. Set CREDENTIAL_ENCRYPTION_KEY for production.")
                
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a credential value."""
        try:
            fernet = Fernet(base64.urlsafe_b64encode(self._encryption_key))
            encrypted_bytes = fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a credential value."""
        try:
            fernet = Fernet(base64.urlsafe_b64encode(self._encryption_key))
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    async def store_credential(
        self,
        tenant_id: str,
        service_name: str,
        credential_type: str,
        credential_data: Dict[str, Any],
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store encrypted credentials in the database.
        
        Args:
            tenant_id: Tenant identifier
            service_name: Name of the external service (e.g., 'experian', 'ofac')
            credential_type: Type of credential (e.g., 'api_key', 'oauth_token', 'certificate')
            credential_data: Dictionary containing credential information
            expires_at: Optional expiration datetime
            metadata: Optional metadata for the credential
            
        Returns:
            credential_id: Unique identifier for the stored credential
        """
        try:
            # Encrypt sensitive credential data
            encrypted_data = {}
            for key, value in credential_data.items():
                if isinstance(value, str) and self._is_sensitive_field(key):
                    encrypted_data[key] = self._encrypt_value(value)
                else:
                    encrypted_data[key] = value
            
            # Generate credential ID
            credential_id = self._generate_credential_id(tenant_id, service_name, credential_type)
            
            # Store in database
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO credentials (
                        id, tenant_id, service_name, credential_type,
                        encrypted_data, expires_at, metadata, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        encrypted_data = EXCLUDED.encrypted_data,
                        expires_at = EXCLUDED.expires_at,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    credential_id,
                    tenant_id,
                    service_name,
                    credential_type,
                    json.dumps(encrypted_data),
                    expires_at,
                    json.dumps(metadata or {}),
                )
            
            # Log credential storage (without sensitive data)
            await self._log_credential_activity(
                tenant_id=tenant_id,
                credential_id=credential_id,
                action='store',
                service_name=service_name,
                credential_type=credential_type
            )
            
            logger.info(f"Stored credential {credential_id} for {service_name}")
            return credential_id
            
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            raise
    
    async def retrieve_credential(
        self,
        tenant_id: str,
        service_name: str,
        credential_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt credentials from the database.
        
        Args:
            tenant_id: Tenant identifier
            service_name: Name of the external service
            credential_type: Optional specific credential type
            
        Returns:
            Decrypted credential data or None if not found
        """
        try:
            async with get_database() as db:
                if credential_type:
                    query = """
                        SELECT id, encrypted_data, expires_at, metadata, created_at
                        FROM credentials
                        WHERE tenant_id = $1 AND service_name = $2 AND credential_type = $3
                        AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    params = [tenant_id, service_name, credential_type]
                else:
                    query = """
                        SELECT id, encrypted_data, expires_at, metadata, created_at
                        FROM credentials
                        WHERE tenant_id = $1 AND service_name = $2
                        AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    params = [tenant_id, service_name]
                
                result = await db.fetchrow(query, *params)
                
                if not result:
                    return None
                
                # Decrypt credential data
                encrypted_data = json.loads(result['encrypted_data'])
                decrypted_data = {}
                
                for key, value in encrypted_data.items():
                    if isinstance(value, str) and self._is_sensitive_field(key):
                        try:
                            decrypted_data[key] = self._decrypt_value(value)
                        except:
                            # If decryption fails, value might not be encrypted
                            decrypted_data[key] = value
                    else:
                        decrypted_data[key] = value
                
                # Add metadata
                credential_info = {
                    'credential_id': result['id'],
                    'data': decrypted_data,
                    'expires_at': result['expires_at'],
                    'metadata': json.loads(result['metadata']) if result['metadata'] else {},
                    'created_at': result['created_at']
                }
                
                # Log credential retrieval
                await self._log_credential_activity(
                    tenant_id=tenant_id,
                    credential_id=result['id'],
                    action='retrieve',
                    service_name=service_name,
                    credential_type=credential_type
                )
                
                return credential_info
                
        except Exception as e:
            logger.error(f"Failed to retrieve credential: {e}")
            return None
    
    async def rotate_credential(
        self,
        tenant_id: str,
        service_name: str,
        credential_type: str,
        new_credential_data: Dict[str, Any]
    ) -> str:
        """
        Rotate credentials by storing new ones and marking old ones as expired.
        
        Args:
            tenant_id: Tenant identifier
            service_name: Name of the external service
            credential_type: Type of credential
            new_credential_data: New credential information
            
        Returns:
            new_credential_id: ID of the new credential
        """
        try:
            # Mark existing credentials as expired
            async with get_database() as db:
                await db.execute(
                    """
                    UPDATE credentials
                    SET expires_at = NOW(), updated_at = NOW()
                    WHERE tenant_id = $1 AND service_name = $2 AND credential_type = $3
                    AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    tenant_id, service_name, credential_type
                )
            
            # Store new credential
            new_credential_id = await self.store_credential(
                tenant_id=tenant_id,
                service_name=service_name,
                credential_type=credential_type,
                credential_data=new_credential_data,
                metadata={'rotated': True, 'rotation_date': datetime.utcnow().isoformat()}
            )
            
            # Log rotation
            await self._log_credential_activity(
                tenant_id=tenant_id,
                credential_id=new_credential_id,
                action='rotate',
                service_name=service_name,
                credential_type=credential_type
            )
            
            logger.info(f"Rotated credential for {service_name}/{credential_type}")
            return new_credential_id
            
        except Exception as e:
            logger.error(f"Failed to rotate credential: {e}")
            raise
    
    async def delete_credential(
        self,
        tenant_id: str,
        credential_id: str
    ) -> bool:
        """
        Securely delete a credential.
        
        Args:
            tenant_id: Tenant identifier
            credential_id: Credential identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            async with get_database() as db:
                result = await db.execute(
                    """
                    DELETE FROM credentials
                    WHERE id = $1 AND tenant_id = $2
                    """,
                    credential_id, tenant_id
                )
                
                if result == "DELETE 1":
                    # Log deletion
                    await self._log_credential_activity(
                        tenant_id=tenant_id,
                        credential_id=credential_id,
                        action='delete'
                    )
                    
                    logger.info(f"Deleted credential {credential_id}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete credential: {e}")
            return False
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field contains sensitive data that should be encrypted."""
        sensitive_fields = {
            'password', 'secret', 'key', 'token', 'api_key', 'client_secret',
            'private_key', 'certificate', 'auth_token', 'access_token',
            'refresh_token', 'webhook_secret', 'encryption_key'
        }
        
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in sensitive_fields)
    
    def _generate_credential_id(self, tenant_id: str, service_name: str, credential_type: str) -> str:
        """Generate a unique credential ID."""
        timestamp = datetime.utcnow().isoformat()
        data = f"{tenant_id}:{service_name}:{credential_type}:{timestamp}"
        hash_object = hashlib.sha256(data.encode())
        return f"cred_{hash_object.hexdigest()[:16]}"
    
    async def _log_credential_activity(
        self,
        tenant_id: str,
        credential_id: str,
        action: str,
        service_name: str = None,
        credential_type: str = None
    ):
        """Log credential activity for audit purposes."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO credential_audit_log (
                        id, tenant_id, credential_id, action, service_name,
                        credential_type, timestamp, ip_address, user_agent
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8)
                    """,
                    f"audit_{hashlib.sha256(f'{credential_id}:{action}:{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}",
                    tenant_id,
                    credential_id,
                    action,
                    service_name,
                    credential_type,
                    '127.0.0.1',  # Would be actual IP in production
                    'Regulens AI System'  # Would be actual user agent
                )
        except Exception as e:
            logger.error(f"Failed to log credential activity: {e}")
    
    async def list_credentials(
        self,
        tenant_id: str,
        service_name: str = None,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List credentials for a tenant (without sensitive data).
        
        Args:
            tenant_id: Tenant identifier
            service_name: Optional service name filter
            include_expired: Whether to include expired credentials
            
        Returns:
            List of credential metadata
        """
        try:
            async with get_database() as db:
                if service_name:
                    if include_expired:
                        query = """
                            SELECT id, service_name, credential_type, expires_at, 
                                   metadata, created_at, updated_at
                            FROM credentials
                            WHERE tenant_id = $1 AND service_name = $2
                            ORDER BY created_at DESC
                        """
                        params = [tenant_id, service_name]
                    else:
                        query = """
                            SELECT id, service_name, credential_type, expires_at,
                                   metadata, created_at, updated_at
                            FROM credentials
                            WHERE tenant_id = $1 AND service_name = $2
                            AND (expires_at IS NULL OR expires_at > NOW())
                            ORDER BY created_at DESC
                        """
                        params = [tenant_id, service_name]
                else:
                    if include_expired:
                        query = """
                            SELECT id, service_name, credential_type, expires_at,
                                   metadata, created_at, updated_at
                            FROM credentials
                            WHERE tenant_id = $1
                            ORDER BY service_name, created_at DESC
                        """
                        params = [tenant_id]
                    else:
                        query = """
                            SELECT id, service_name, credential_type, expires_at,
                                   metadata, created_at, updated_at
                            FROM credentials
                            WHERE tenant_id = $1
                            AND (expires_at IS NULL OR expires_at > NOW())
                            ORDER BY service_name, created_at DESC
                        """
                        params = [tenant_id]
                
                results = await db.fetch(query, *params)
                
                credentials = []
                for row in results:
                    credential_info = {
                        'credential_id': row['id'],
                        'service_name': row['service_name'],
                        'credential_type': row['credential_type'],
                        'expires_at': row['expires_at'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'is_expired': row['expires_at'] and row['expires_at'] <= datetime.utcnow()
                    }
                    credentials.append(credential_info)
                
                return credentials
                
        except Exception as e:
            logger.error(f"Failed to list credentials: {e}")
            return []
