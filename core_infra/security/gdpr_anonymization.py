"""
Regulens AI - GDPR Data Anonymization Framework
Enterprise-grade data anonymization and pseudonymization for GDPR compliance.
"""

import re
import uuid
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import structlog
from faker import Faker

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.security.encryption import encryption_manager
from core_infra.exceptions import DataValidationException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()
fake = Faker()

@dataclass
class AnonymizationRule:
    """Data anonymization rule configuration."""
    field_name: str
    anonymization_type: str  # mask, pseudonymize, generalize, suppress, encrypt
    pattern: Optional[str] = None
    replacement: Optional[str] = None
    preserve_format: bool = True
    preserve_length: bool = True

class GDPRAnonymizer:
    """Comprehensive GDPR-compliant data anonymization service."""
    
    def __init__(self):
        self.anonymization_rules = self._load_anonymization_rules()
        self.pseudonym_mapping = {}  # For consistent pseudonymization
        
    def _load_anonymization_rules(self) -> Dict[str, AnonymizationRule]:
        """Load anonymization rules for different data types."""
        return {
            # Personal identifiers
            'email': AnonymizationRule(
                field_name='email',
                anonymization_type='pseudonymize',
                preserve_format=True
            ),
            'phone': AnonymizationRule(
                field_name='phone',
                anonymization_type='pseudonymize',
                preserve_format=True
            ),
            'ssn': AnonymizationRule(
                field_name='ssn',
                anonymization_type='mask',
                pattern=r'(\d{3})\d{2}(\d{4})',
                replacement=r'\1XX\2'
            ),
            'passport_number': AnonymizationRule(
                field_name='passport_number',
                anonymization_type='pseudonymize',
                preserve_length=True
            ),
            'driver_license': AnonymizationRule(
                field_name='driver_license',
                anonymization_type='pseudonymize',
                preserve_length=True
            ),
            
            # Names
            'first_name': AnonymizationRule(
                field_name='first_name',
                anonymization_type='pseudonymize',
                preserve_format=True
            ),
            'last_name': AnonymizationRule(
                field_name='last_name',
                anonymization_type='pseudonymize',
                preserve_format=True
            ),
            'full_name': AnonymizationRule(
                field_name='full_name',
                anonymization_type='pseudonymize',
                preserve_format=True
            ),
            
            # Financial data
            'bank_account_number': AnonymizationRule(
                field_name='bank_account_number',
                anonymization_type='mask',
                pattern=r'(\d{4})\d+(\d{4})',
                replacement=r'\1****\2'
            ),
            'credit_card_number': AnonymizationRule(
                field_name='credit_card_number',
                anonymization_type='mask',
                pattern=r'(\d{4})\d+(\d{4})',
                replacement=r'\1****\2'
            ),
            'routing_number': AnonymizationRule(
                field_name='routing_number',
                anonymization_type='pseudonymize',
                preserve_length=True
            ),
            
            # Address information
            'address': AnonymizationRule(
                field_name='address',
                anonymization_type='generalize',
                preserve_format=True
            ),
            'postal_code': AnonymizationRule(
                field_name='postal_code',
                anonymization_type='generalize',
                pattern=r'(\d{3})\d{2}',
                replacement=r'\1XX'
            ),
            
            # Dates
            'date_of_birth': AnonymizationRule(
                field_name='date_of_birth',
                anonymization_type='generalize',
                preserve_format=True
            ),
            
            # IP addresses
            'ip_address': AnonymizationRule(
                field_name='ip_address',
                anonymization_type='pseudonymize',
                preserve_format=True
            ),
            
            # Free text fields
            'notes': AnonymizationRule(
                field_name='notes',
                anonymization_type='suppress',
                replacement='[REDACTED]'
            ),
            'comments': AnonymizationRule(
                field_name='comments',
                anonymization_type='suppress',
                replacement='[REDACTED]'
            ),
        }
    
    def anonymize_customer_data(self, customer_data: Dict[str, Any], 
                               anonymization_level: str = 'standard') -> Dict[str, Any]:
        """
        Anonymize customer data according to GDPR requirements.
        
        Args:
            customer_data: Customer data dictionary
            anonymization_level: 'minimal', 'standard', 'full'
            
        Returns:
            Anonymized customer data
        """
        try:
            anonymized_data = customer_data.copy()
            
            # Apply anonymization rules based on level
            fields_to_anonymize = self._get_fields_for_level(anonymization_level)
            
            for field_name in fields_to_anonymize:
                if field_name in anonymized_data and anonymized_data[field_name]:
                    rule = self.anonymization_rules.get(field_name)
                    if rule:
                        anonymized_data[field_name] = self._apply_anonymization_rule(
                            anonymized_data[field_name], rule
                        )
            
            # Add anonymization metadata
            anonymized_data['_anonymization_metadata'] = {
                'anonymized_at': datetime.utcnow().isoformat(),
                'anonymization_level': anonymization_level,
                'anonymized_fields': fields_to_anonymize,
                'anonymization_id': str(uuid.uuid4())
            }
            
            logger.info(f"Customer data anonymized: level={anonymization_level}, fields={len(fields_to_anonymize)}")
            return anonymized_data
            
        except Exception as e:
            logger.error(f"Customer data anonymization failed: {e}")
            raise DataValidationException("anonymization", str(customer_data), str(e))
    
    def anonymize_transaction_data(self, transaction_data: Dict[str, Any],
                                 anonymization_level: str = 'standard') -> Dict[str, Any]:
        """
        Anonymize transaction data for analytics while preserving utility.
        
        Args:
            transaction_data: Transaction data dictionary
            anonymization_level: 'minimal', 'standard', 'full'
            
        Returns:
            Anonymized transaction data
        """
        try:
            anonymized_data = transaction_data.copy()
            
            # Transaction-specific anonymization
            if anonymization_level in ['standard', 'full']:
                # Anonymize account numbers
                if 'account_number' in anonymized_data:
                    anonymized_data['account_number'] = self._mask_account_number(
                        anonymized_data['account_number']
                    )
                
                # Anonymize beneficiary information
                if 'beneficiary_name' in anonymized_data:
                    anonymized_data['beneficiary_name'] = self._pseudonymize_name(
                        anonymized_data['beneficiary_name']
                    )
                
                # Generalize amounts for privacy
                if 'amount' in anonymized_data and anonymization_level == 'full':
                    anonymized_data['amount'] = self._generalize_amount(
                        anonymized_data['amount']
                    )
            
            # Preserve analytical utility
            if 'amount' in anonymized_data:
                anonymized_data['amount_range'] = self._categorize_amount(
                    anonymized_data['amount']
                )
            
            if 'created_at' in anonymized_data:
                anonymized_data['transaction_month'] = anonymized_data['created_at'][:7]  # YYYY-MM
            
            # Add anonymization metadata
            anonymized_data['_anonymization_metadata'] = {
                'anonymized_at': datetime.utcnow().isoformat(),
                'anonymization_level': anonymization_level,
                'anonymization_id': str(uuid.uuid4())
            }
            
            return anonymized_data
            
        except Exception as e:
            logger.error(f"Transaction data anonymization failed: {e}")
            raise DataValidationException("anonymization", str(transaction_data), str(e))
    
    def _get_fields_for_level(self, level: str) -> List[str]:
        """Get fields to anonymize based on anonymization level."""
        if level == 'minimal':
            return ['ssn', 'passport_number', 'credit_card_number', 'bank_account_number']
        elif level == 'standard':
            return [
                'ssn', 'passport_number', 'credit_card_number', 'bank_account_number',
                'phone', 'email', 'driver_license', 'routing_number', 'ip_address'
            ]
        elif level == 'full':
            return list(self.anonymization_rules.keys())
        else:
            return []
    
    def _apply_anonymization_rule(self, value: Any, rule: AnonymizationRule) -> Any:
        """Apply specific anonymization rule to a value."""
        if value is None:
            return value
        
        value_str = str(value)
        
        if rule.anonymization_type == 'mask':
            return self._mask_value(value_str, rule)
        elif rule.anonymization_type == 'pseudonymize':
            return self._pseudonymize_value(value_str, rule)
        elif rule.anonymization_type == 'generalize':
            return self._generalize_value(value_str, rule)
        elif rule.anonymization_type == 'suppress':
            return rule.replacement or '[REDACTED]'
        elif rule.anonymization_type == 'encrypt':
            return encryption_manager.encrypt_sensitive_data(value_str, rule.field_name)
        else:
            return value
    
    def _mask_value(self, value: str, rule: AnonymizationRule) -> str:
        """Apply masking to a value."""
        if rule.pattern and rule.replacement:
            return re.sub(rule.pattern, rule.replacement, value)
        else:
            # Default masking - replace middle characters with X
            if len(value) <= 4:
                return 'X' * len(value)
            else:
                start = value[:2]
                end = value[-2:]
                middle = 'X' * (len(value) - 4)
                return start + middle + end
    
    def _pseudonymize_value(self, value: str, rule: AnonymizationRule) -> str:
        """Apply pseudonymization to a value."""
        hash_key = f"{rule.field_name}_{value}"
        
        if hash_key in self.pseudonym_mapping:
            return self.pseudonym_mapping[hash_key]
        
        if rule.field_name == 'first_name':
            pseudonym = fake.first_name()
        elif rule.field_name == 'last_name':
            pseudonym = fake.last_name()
        elif rule.field_name == 'full_name':
            pseudonym = fake.name()
        elif rule.field_name == 'email':
            pseudonym = fake.email()
        elif rule.field_name == 'phone':
            pseudonym = fake.phone_number()
        elif rule.field_name == 'ip_address':
            pseudonym = fake.ipv4()
        else:
            if rule.preserve_length:
                pseudonym = self._generate_pseudonym_with_length(value, rule.preserve_format)
            else:
                hash_value = hashlib.sha256(hash_key.encode()).hexdigest()
                pseudonym = f"ANON_{hash_value[:len(value)]}"
        
        self.pseudonym_mapping[hash_key] = pseudonym
        return pseudonym
    
    def _generalize_value(self, value: str, rule: AnonymizationRule) -> str:
        """Apply generalization to a value."""
        if rule.field_name == 'date_of_birth':
            # Generalize to year only
            try:
                date_obj = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return str(date_obj.year)
            except:
                return value[:4] if len(value) >= 4 else value
        
        elif rule.field_name == 'address':
            # Generalize to city/state only
            parts = value.split(',')
            if len(parts) >= 2:
                return f"{parts[-2].strip()}, {parts[-1].strip()}"
            return value
        
        elif rule.field_name == 'postal_code':
            # Generalize postal code
            if rule.pattern and rule.replacement:
                return re.sub(rule.pattern, rule.replacement, value)
            else:
                return value[:3] + 'XX' if len(value) >= 5 else value
        
        else:
            return value
    
    def _generate_pseudonym_with_length(self, original: str, preserve_format: bool) -> str:
        """Generate pseudonym preserving length and optionally format."""
        if preserve_format:
            # Preserve character types (letter/digit/special)
            result = []
            for char in original:
                if char.isalpha():
                    result.append(random.choice(string.ascii_letters))
                elif char.isdigit():
                    result.append(random.choice(string.digits))
                else:
                    result.append(char)
            return ''.join(result)
        else:
            return self._generate_random_string(len(original))
    
    def _generate_random_string(self, length: int) -> str:
        """Generate random alphanumeric string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def _mask_account_number(self, account_number: str) -> str:
        """Mask account number showing only first and last 4 digits."""
        if len(account_number) <= 8:
            return 'X' * len(account_number)
        return account_number[:4] + 'X' * (len(account_number) - 8) + account_number[-4:]
    
    def _pseudonymize_name(self, name: str) -> str:
        """Generate pseudonym for a name."""
        return fake.name()
    
    def _generalize_amount(self, amount: float) -> str:
        """Generalize transaction amount to ranges."""
        if amount < 100:
            return "< $100"
        elif amount < 1000:
            return "$100 - $1,000"
        elif amount < 10000:
            return "$1,000 - $10,000"
        elif amount < 100000:
            return "$10,000 - $100,000"
        else:
            return "> $100,000"
    
    def _categorize_amount(self, amount: float) -> str:
        """Categorize amount for analytical purposes."""
        if amount < 1000:
            return "small"
        elif amount < 10000:
            return "medium"
        elif amount < 100000:
            return "large"
        else:
            return "very_large"
    
    async def anonymize_customer_for_deletion(self, customer_id: str) -> Dict[str, Any]:
        """
        Anonymize customer data for GDPR right to be forgotten.
        
        Args:
            customer_id: Customer ID to anonymize
            
        Returns:
            Anonymization report
        """
        try:
            async with get_database() as db:
                # Get customer data
                customer = await db.fetchrow(
                    "SELECT * FROM customers WHERE id = $1",
                    uuid.UUID(customer_id)
                )
                
                if not customer:
                    raise DataValidationException("customer_id", customer_id, "Customer not found")
                
                # Anonymize customer data
                anonymized_customer = self.anonymize_customer_data(
                    dict(customer), 
                    anonymization_level='full'
                )
                
                # Update customer record
                await db.execute(
                    """
                    UPDATE customers 
                    SET first_name = $1, last_name = $2, email = $3, phone = $4,
                        date_of_birth = $5, address = $6, 
                        gdpr_anonymized = true, gdpr_anonymized_at = NOW()
                    WHERE id = $7
                    """,
                    anonymized_customer.get('first_name'),
                    anonymized_customer.get('last_name'),
                    anonymized_customer.get('email'),
                    anonymized_customer.get('phone'),
                    anonymized_customer.get('date_of_birth'),
                    anonymized_customer.get('address'),
                    uuid.UUID(customer_id)
                )
                
                # Anonymize related transaction data
                transactions = await db.fetch(
                    "SELECT id FROM transactions WHERE customer_id = $1",
                    uuid.UUID(customer_id)
                )
                
                anonymized_transactions = 0
                for transaction in transactions:
                    await self._anonymize_transaction_for_customer(db, transaction['id'])
                    anonymized_transactions += 1
                
                # Create anonymization log
                log_entry = {
                    'customer_id': customer_id,
                    'anonymization_type': 'gdpr_deletion',
                    'anonymized_at': datetime.utcnow().isoformat(),
                    'anonymized_records': {
                        'customer': 1,
                        'transactions': anonymized_transactions
                    },
                    'anonymization_id': str(uuid.uuid4())
                }
                
                await db.execute(
                    """
                    INSERT INTO gdpr_anonymization_log (
                        id, customer_id, anonymization_type, anonymized_at, 
                        anonymized_records, anonymization_metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(customer_id),
                    'gdpr_deletion',
                    datetime.utcnow(),
                    anonymized_transactions + 1,
                    log_entry
                )
                
                logger.info(f"Customer {customer_id} anonymized for GDPR deletion")
                return log_entry
                
        except Exception as e:
            logger.error(f"GDPR anonymization failed for customer {customer_id}: {e}")
            raise
    
    async def _anonymize_transaction_for_customer(self, db, transaction_id: str):
        """Anonymize transaction data for a specific customer."""
        transaction = await db.fetchrow(
            "SELECT * FROM transactions WHERE id = $1",
            uuid.UUID(transaction_id)
        )
        
        if transaction:
            anonymized_transaction = self.anonymize_transaction_data(
                dict(transaction),
                anonymization_level='full'
            )
            
            await db.execute(
                """
                UPDATE transactions 
                SET beneficiary_name = $1, reference_number = $2,
                    purpose_of_payment = $3, gdpr_anonymized = true
                WHERE id = $4
                """,
                anonymized_transaction.get('beneficiary_name'),
                anonymized_transaction.get('reference_number'),
                anonymized_transaction.get('purpose_of_payment'),
                uuid.UUID(transaction_id)
            )

# Global anonymizer instance
gdpr_anonymizer = GDPRAnonymizer()

# Convenience functions
def anonymize_for_analytics(data: Dict[str, Any], data_type: str = 'customer') -> Dict[str, Any]:
    """Convenience function for anonymizing data for analytics."""
    if data_type == 'customer':
        return gdpr_anonymizer.anonymize_customer_data(data, 'standard')
    elif data_type == 'transaction':
        return gdpr_anonymizer.anonymize_transaction_data(data, 'standard')
    else:
        return data

def anonymize_for_deletion(customer_id: str) -> Dict[str, Any]:
    """Convenience function for GDPR right to be forgotten."""
    import asyncio
    return asyncio.run(gdpr_anonymizer.anonymize_customer_for_deletion(customer_id))
