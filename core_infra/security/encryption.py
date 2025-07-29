"""
Regulens AI - Encryption at Rest Framework
Enterprise-grade encryption for sensitive data storage and transmission.
"""

import os
import base64
import hashlib
from typing import Union, Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import structlog

from core_infra.config import get_settings
from core_infra.exceptions import SecurityException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class EncryptionManager:
    """Comprehensive encryption manager for data at rest and in transit."""
    
    def __init__(self):
        self.master_key = self._get_master_key()
        self.fernet = Fernet(self.master_key)
        self._field_encryption_keys = {}
    
    def _get_master_key(self) -> bytes:
        """Get or generate master encryption key."""
        try:
            # Get encryption key from settings
            encryption_key = settings.encryption_key.get_secret_value()
            
            # Derive a proper Fernet key from the encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'regulens_ai_salt',  # In production, use a random salt stored securely
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            
            logger.info("Master encryption key initialized")
            return key
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption key: {e}")
            raise SecurityException("Encryption initialization failed")
    
    def encrypt_sensitive_data(self, data: Union[str, bytes], 
                             field_name: Optional[str] = None) -> str:
        """
        Encrypt sensitive data with optional field-specific encryption.
        
        Args:
            data: Data to encrypt
            field_name: Optional field name for field-specific encryption
            
        Returns:
            Base64 encoded encrypted data
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Use field-specific encryption if specified
            if field_name:
                encrypted_data = self._encrypt_with_field_key(data, field_name)
            else:
                encrypted_data = self.fernet.encrypt(data)
            
            # Return base64 encoded for storage
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed for field {field_name}: {e}")
            raise SecurityException("Data encryption failed")
    
    def decrypt_sensitive_data(self, encrypted_data: str, 
                             field_name: Optional[str] = None) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            field_name: Optional field name for field-specific decryption
            
        Returns:
            Decrypted data as string
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Use field-specific decryption if specified
            if field_name:
                decrypted_data = self._decrypt_with_field_key(encrypted_bytes, field_name)
            else:
                decrypted_data = self.fernet.decrypt(encrypted_bytes)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed for field {field_name}: {e}")
            raise SecurityException("Data decryption failed")
    
    def _encrypt_with_field_key(self, data: bytes, field_name: str) -> bytes:
        """Encrypt data with field-specific key."""
        field_key = self._get_field_key(field_name)
        field_fernet = Fernet(field_key)
        return field_fernet.encrypt(data)
    
    def _decrypt_with_field_key(self, encrypted_data: bytes, field_name: str) -> bytes:
        """Decrypt data with field-specific key."""
        field_key = self._get_field_key(field_name)
        field_fernet = Fernet(field_key)
        return field_fernet.decrypt(encrypted_data)
    
    def _get_field_key(self, field_name: str) -> bytes:
        """Get or generate field-specific encryption key."""
        if field_name not in self._field_encryption_keys:
            # Derive field-specific key from master key and field name
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=f"regulens_field_{field_name}".encode()[:16].ljust(16, b'0'),
                iterations=100000,
            )
            
            master_key_bytes = base64.urlsafe_b64decode(self.master_key)
            field_key = base64.urlsafe_b64encode(kdf.derive(master_key_bytes))
            self._field_encryption_keys[field_name] = field_key
            
        return self._field_encryption_keys[field_name]
    
    def encrypt_pii_data(self, pii_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt personally identifiable information (PII) data.
        
        Args:
            pii_data: Dictionary containing PII fields
            
        Returns:
            Dictionary with encrypted PII fields
        """
        pii_fields = [
            'ssn', 'social_security_number', 'tax_id', 'passport_number',
            'driver_license', 'credit_card_number', 'bank_account_number',
            'phone', 'email', 'date_of_birth', 'address', 'full_name'
        ]
        
        encrypted_data = pii_data.copy()
        
        for field in pii_fields:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    encrypted_data[field] = self.encrypt_sensitive_data(
                        str(encrypted_data[field]), 
                        field_name=f"pii_{field}"
                    )
                    logger.debug(f"Encrypted PII field: {field}")
                except Exception as e:
                    logger.error(f"Failed to encrypt PII field {field}: {e}")
                    # Don't fail the entire operation for one field
                    continue
        
        return encrypted_data
    
    def decrypt_pii_data(self, encrypted_pii_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt personally identifiable information (PII) data.
        
        Args:
            encrypted_pii_data: Dictionary containing encrypted PII fields
            
        Returns:
            Dictionary with decrypted PII fields
        """
        pii_fields = [
            'ssn', 'social_security_number', 'tax_id', 'passport_number',
            'driver_license', 'credit_card_number', 'bank_account_number',
            'phone', 'email', 'date_of_birth', 'address', 'full_name'
        ]
        
        decrypted_data = encrypted_pii_data.copy()
        
        for field in pii_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt_sensitive_data(
                        decrypted_data[field], 
                        field_name=f"pii_{field}"
                    )
                    logger.debug(f"Decrypted PII field: {field}")
                except Exception as e:
                    logger.error(f"Failed to decrypt PII field {field}: {e}")
                    # Keep encrypted value if decryption fails
                    continue
        
        return decrypted_data
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> str:
        """
        Create a secure hash of sensitive data for indexing/searching.
        
        Args:
            data: Data to hash
            salt: Optional salt (uses default if not provided)
            
        Returns:
            Hex encoded hash
        """
        try:
            if salt is None:
                salt = "regulens_ai_hash_salt"
            
            # Use PBKDF2 for secure hashing
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            
            hash_bytes = kdf.derive(data.encode())
            return hash_bytes.hex()
            
        except Exception as e:
            logger.error(f"Hashing failed: {e}")
            raise SecurityException("Data hashing failed")
    
    def generate_key_pair(self) -> tuple[bytes, bytes]:
        """
        Generate RSA key pair for asymmetric encryption.
        
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            logger.info("RSA key pair generated")
            return private_pem, public_pem
            
        except Exception as e:
            logger.error(f"Key pair generation failed: {e}")
            raise SecurityException("Key pair generation failed")
    
    def encrypt_with_public_key(self, data: str, public_key_pem: bytes) -> str:
        """
        Encrypt data with RSA public key.
        
        Args:
            data: Data to encrypt
            public_key_pem: Public key in PEM format
            
        Returns:
            Base64 encoded encrypted data
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(public_key_pem)
            
            # Encrypt data
            encrypted_data = public_key.encrypt(
                data.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Public key encryption failed: {e}")
            raise SecurityException("Public key encryption failed")
    
    def decrypt_with_private_key(self, encrypted_data: str, private_key_pem: bytes) -> str:
        """
        Decrypt data with RSA private key.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            private_key_pem: Private key in PEM format
            
        Returns:
            Decrypted data
        """
        try:
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
            )
            
            # Decode and decrypt data
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Private key decryption failed: {e}")
            raise SecurityException("Private key decryption failed")

class DatabaseEncryption:
    """Database-specific encryption utilities."""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
    
    def encrypt_customer_data(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive customer data before database storage."""
        encrypted_data = customer_data.copy()
        
        # Encrypt PII fields
        encrypted_data = self.encryption_manager.encrypt_pii_data(encrypted_data)
        
        # Encrypt additional sensitive fields
        sensitive_fields = ['notes', 'comments', 'internal_notes']
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encryption_manager.encrypt_sensitive_data(
                    str(encrypted_data[field]),
                    field_name=f"customer_{field}"
                )
        
        return encrypted_data
    
    def decrypt_customer_data(self, encrypted_customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt customer data after database retrieval."""
        decrypted_data = encrypted_customer_data.copy()
        
        # Decrypt PII fields
        decrypted_data = self.encryption_manager.decrypt_pii_data(decrypted_data)
        
        # Decrypt additional sensitive fields
        sensitive_fields = ['notes', 'comments', 'internal_notes']
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.encryption_manager.decrypt_sensitive_data(
                        decrypted_data[field],
                        field_name=f"customer_{field}"
                    )
                except Exception as e:
                    logger.error(f"Failed to decrypt customer field {field}: {e}")
                    continue
        
        return decrypted_data
    
    def encrypt_transaction_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive transaction data before database storage."""
        encrypted_data = transaction_data.copy()
        
        # Encrypt sensitive transaction fields
        sensitive_fields = [
            'account_number', 'routing_number', 'reference_number',
            'beneficiary_name', 'beneficiary_account', 'purpose_of_payment'
        ]
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encryption_manager.encrypt_sensitive_data(
                    str(encrypted_data[field]),
                    field_name=f"transaction_{field}"
                )
        
        return encrypted_data
    
    def decrypt_transaction_data(self, encrypted_transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt transaction data after database retrieval."""
        decrypted_data = encrypted_transaction_data.copy()
        
        # Decrypt sensitive transaction fields
        sensitive_fields = [
            'account_number', 'routing_number', 'reference_number',
            'beneficiary_name', 'beneficiary_account', 'purpose_of_payment'
        ]
        
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.encryption_manager.decrypt_sensitive_data(
                        decrypted_data[field],
                        field_name=f"transaction_{field}"
                    )
                except Exception as e:
                    logger.error(f"Failed to decrypt transaction field {field}: {e}")
                    continue
        
        return decrypted_data

# Global encryption manager instance
encryption_manager = EncryptionManager()
database_encryption = DatabaseEncryption(encryption_manager)

# Convenience functions
def encrypt_sensitive_data(data: Union[str, bytes], field_name: Optional[str] = None) -> str:
    """Convenience function for encrypting sensitive data."""
    return encryption_manager.encrypt_sensitive_data(data, field_name)

def decrypt_sensitive_data(encrypted_data: str, field_name: Optional[str] = None) -> str:
    """Convenience function for decrypting sensitive data."""
    return encryption_manager.decrypt_sensitive_data(encrypted_data, field_name)

def hash_for_indexing(data: str, salt: Optional[str] = None) -> str:
    """Convenience function for creating searchable hashes."""
    return encryption_manager.hash_sensitive_data(data, salt)
