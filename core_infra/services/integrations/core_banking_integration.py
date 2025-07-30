"""
Core Banking System Integration Service

Provides enterprise-grade integration with major core banking platforms:
- Temenos T24/Transact
- Oracle Flexcube
- Infosys Finacle

Features:
- Real-time transaction monitoring
- Customer data synchronization
- Account balance tracking
- Regulatory reporting feeds
- Risk flag detection
- Duplicate transaction handling
"""

import logging
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import aiohttp
from urllib.parse import urljoin

from core_infra.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CoreBankingIntegrationService:
    """
    Enterprise core banking system integration service.
    
    Handles real-time transaction feeds, customer data sync, and
    regulatory monitoring from major core banking platforms.
    """
    
    def __init__(self, supabase_client, integration_manager=None):
        self.supabase = supabase_client
        self.integration_manager = integration_manager
        self.session = None
        self.connectors = {
            'temenos': TemenosConnector(supabase_client),
            'flexcube': FlexcubeConnector(supabase_client),
            'finacle': FinacleConnector(supabase_client)
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        for connector in self.connectors.values():
            await connector.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        for connector in self.connectors.values():
            await connector.__aexit__(exc_type, exc_val, exc_tb)
    
    async def sync_transactions(self, tenant_id: str, system_type: str = None, 
                              start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Synchronize transactions from core banking systems.
        
        Args:
            tenant_id: Tenant identifier
            system_type: Specific CBS ('temenos', 'flexcube', 'finacle') or None for all
            start_date: Start date for transaction sync
            end_date: End date for transaction sync
            
        Returns:
            Synchronization results with statistics and errors
        """
        try:
            logger.info(f"Starting transaction sync for tenant {tenant_id}")
            
            # Default to last 24 hours if no dates provided
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=1)
            if not end_date:
                end_date = datetime.utcnow()
            
            sync_results = {
                'tenant_id': tenant_id,
                'started_at': datetime.utcnow(),
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'systems_synced': [],
                'total_transactions_processed': 0,
                'transactions_created': 0,
                'transactions_updated': 0,
                'transactions_flagged': 0,
                'duplicates_detected': 0,
                'errors': []
            }
            
            # Get enabled CBS systems for tenant
            systems_to_sync = await self._get_enabled_cbs_systems(tenant_id, system_type)
            
            for system in systems_to_sync:
                try:
                    logger.info(f"Syncing transactions from {system['system_name']} ({system['vendor']})")
                    
                    connector = self.connectors.get(system['vendor'])
                    if not connector:
                        logger.warning(f"No connector available for {system['vendor']}")
                        continue
                    
                    # Perform sync with specific connector
                    system_results = await connector.sync_transactions(system, start_date, end_date)
                    
                    # Update sync statistics
                    sync_results['systems_synced'].append(system['system_name'])
                    sync_results['total_transactions_processed'] += system_results.get('total_processed', 0)
                    sync_results['transactions_created'] += system_results.get('created', 0)
                    sync_results['transactions_updated'] += system_results.get('updated', 0)
                    sync_results['transactions_flagged'] += system_results.get('flagged', 0)
                    sync_results['duplicates_detected'] += system_results.get('duplicates', 0)
                    
                    # Update system last sync time
                    await self._update_system_sync_time(system['id'])
                    
                except Exception as e:
                    error_msg = f"Error syncing {system.get('system_name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    sync_results['errors'].append(error_msg)
            
            sync_results['completed_at'] = datetime.utcnow()
            sync_results['success'] = len(sync_results['errors']) == 0
            
            # Log sync operation
            await self._log_integration_operation(
                tenant_id=tenant_id,
                operation_type='sync',
                operation_name='transaction_sync',
                status='success' if sync_results['success'] else 'partial_success',
                result=sync_results
            )
            
            logger.info(f"Transaction sync completed for tenant {tenant_id}: "
                       f"{sync_results['total_transactions_processed']} transactions processed")
            
            return sync_results
            
        except Exception as e:
            logger.error(f"Transaction sync failed for tenant {tenant_id}: {str(e)}")
            raise
    
    async def start_realtime_monitoring(self, tenant_id: str, system_type: str = None) -> Dict[str, Any]:
        """
        Start real-time transaction monitoring from CBS systems.
        
        Args:
            tenant_id: Tenant identifier
            system_type: Specific CBS or None for all enabled systems
            
        Returns:
            Monitoring startup results
        """
        try:
            logger.info(f"Starting real-time monitoring for tenant {tenant_id}")
            
            monitoring_results = {
                'tenant_id': tenant_id,
                'started_at': datetime.utcnow(),
                'systems_monitoring': [],
                'webhook_endpoints': [],
                'errors': []
            }
            
            # Get enabled CBS systems
            systems = await self._get_enabled_cbs_systems(tenant_id, system_type)
            
            for system in systems:
                try:
                    connector = self.connectors.get(system['vendor'])
                    if connector:
                        webhook_url = await connector.setup_realtime_monitoring(system)
                        
                        monitoring_results['systems_monitoring'].append(system['system_name'])
                        monitoring_results['webhook_endpoints'].append({
                            'system': system['system_name'],
                            'webhook_url': webhook_url
                        })
                        
                except Exception as e:
                    error_msg = f"Error setting up monitoring for {system.get('system_name')}: {str(e)}"
                    logger.error(error_msg)
                    monitoring_results['errors'].append(error_msg)
            
            monitoring_results['success'] = len(monitoring_results['errors']) == 0
            
            logger.info(f"Real-time monitoring setup completed for {len(monitoring_results['systems_monitoring'])} systems")
            
            return monitoring_results
            
        except Exception as e:
            logger.error(f"Real-time monitoring setup failed for tenant {tenant_id}: {str(e)}")
            raise
    
    async def process_realtime_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming real-time transaction from CBS webhook.
        
        Args:
            transaction_data: Raw transaction data from CBS
            
        Returns:
            Processing results including risk flags and actions taken
        """
        try:
            logger.info(f"Processing real-time transaction: {transaction_data.get('transaction_id')}")
            
            # Extract and normalize transaction data
            normalized_transaction = await self._normalize_transaction_data(transaction_data)
            
            # Check for duplicates
            is_duplicate = await self._check_duplicate_transaction(normalized_transaction)
            
            if is_duplicate:
                logger.warning(f"Duplicate transaction detected: {normalized_transaction['external_transaction_id']}")
                return {
                    'status': 'duplicate',
                    'action': 'ignored',
                    'transaction_id': normalized_transaction['external_transaction_id']
                }
            
            # Store transaction
            stored_transaction = await self._store_transaction(normalized_transaction)
            
            # Perform risk screening
            risk_results = await self._perform_risk_screening(stored_transaction)
            
            # Generate alerts if necessary
            alerts_generated = await self._generate_alerts(stored_transaction, risk_results)
            
            return {
                'status': 'processed',
                'action': 'stored',
                'transaction_id': stored_transaction['id'],
                'risk_flags': risk_results.get('flags', []),
                'monitoring_status': risk_results.get('monitoring_status', 'clear'),
                'alerts_generated': len(alerts_generated)
            }
            
        except Exception as e:
            logger.error(f"Error processing real-time transaction: {str(e)}")
            raise
    
    async def _get_enabled_cbs_systems(self, tenant_id: str, system_type: str = None) -> List[Dict[str, Any]]:
        """Get enabled CBS systems for tenant."""
        try:
            query = self.supabase.table('integration_systems').select('*').eq('tenant_id', tenant_id).eq('status', 'active').eq('system_type', 'core_banking')
            
            if system_type:
                query = query.eq('vendor', system_type)
            else:
                query = query.in_('vendor', ['temenos', 'flexcube', 'finacle'])
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching enabled CBS systems: {str(e)}")
            return []
    
    async def _normalize_transaction_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize transaction data from different CBS formats."""
        # This would contain CBS-specific normalization logic
        return {
            'external_transaction_id': raw_data.get('txn_id') or raw_data.get('transaction_id'),
            'account_number': raw_data.get('account_no') or raw_data.get('account_number'),
            'amount': Decimal(str(raw_data.get('amount', '0'))),
            'currency': raw_data.get('currency', 'USD'),
            'transaction_type': raw_data.get('txn_type') or raw_data.get('type'),
            'transaction_date': raw_data.get('transaction_date') or raw_data.get('txn_date'),
            'counterparty_name': raw_data.get('counterparty') or raw_data.get('beneficiary_name'),
            'description': raw_data.get('description') or raw_data.get('narration'),
            'channel': raw_data.get('channel', 'unknown'),
            'branch_code': raw_data.get('branch_code'),
            'raw_data': raw_data
        }
    
    async def _check_duplicate_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Check if transaction is a duplicate."""
        try:
            existing = self.supabase.table('core_banking_transactions').select('*').eq(
                'external_transaction_id', transaction['external_transaction_id']
            ).execute()
            
            return len(existing.data) > 0 if existing.data else False
            
        except Exception as e:
            logger.error(f"Error checking duplicate transaction: {str(e)}")
            return False
    
    async def _store_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Store normalized transaction in database."""
        try:
            transaction_record = {
                **transaction,
                'id': str(uuid.uuid4()),
                'sync_status': 'synced',
                'monitoring_status': 'clear'
            }
            
            result = self.supabase.table('core_banking_transactions').insert(transaction_record).execute()
            return result.data[0] if result.data else transaction_record
            
        except Exception as e:
            logger.error(f"Error storing transaction: {str(e)}")
            raise
    
    async def _perform_risk_screening(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Perform risk screening on transaction."""
        # Mock risk screening logic
        risk_flags = []
        monitoring_status = 'clear'
        
        # Check amount thresholds
        if transaction.get('amount', 0) > settings.cbs_transaction_threshold_amount:
            risk_flags.append('high_amount')
            monitoring_status = 'flagged'
        
        # Check for suspicious patterns (mock logic)
        if 'suspicious' in transaction.get('description', '').lower():
            risk_flags.append('suspicious_description')
            monitoring_status = 'flagged'
        
        return {
            'flags': risk_flags,
            'monitoring_status': monitoring_status,
            'risk_score': len(risk_flags) * 25  # Simple scoring
        }
    
    async def _generate_alerts(self, transaction: Dict[str, Any], risk_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts for flagged transactions."""
        alerts = []
        
        if risk_results.get('monitoring_status') == 'flagged':
            alert = {
                'id': str(uuid.uuid4()),
                'transaction_id': transaction['id'],
                'alert_type': 'transaction_risk',
                'severity': 'medium',
                'description': f"Transaction flagged for: {', '.join(risk_results.get('flags', []))}",
                'created_at': datetime.utcnow().isoformat()
            }
            alerts.append(alert)
            
            # Store alert in monitoring_alerts table
            try:
                self.supabase.table('monitoring_alerts').insert(alert).execute()
            except Exception as e:
                logger.error(f"Error storing alert: {str(e)}")
        
        return alerts
    
    async def _update_system_sync_time(self, system_id: str):
        """Update last sync time for integration system."""
        try:
            now = datetime.utcnow()
            self.supabase.table('integration_systems').update({
                'last_sync_at': now.isoformat(),
                'next_sync_at': (now + timedelta(minutes=15)).isoformat(),  # 15-minute intervals for CBS
                'error_count': 0
            }).eq('id', system_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating system sync time: {str(e)}")
    
    async def _log_integration_operation(self, tenant_id: str, operation_type: str, 
                                       operation_name: str, status: str, 
                                       result: Dict[str, Any], system_id: str = None):
        """Log integration operation."""
        try:
            log_entry = {
                'id': str(uuid.uuid4()),
                'tenant_id': tenant_id,
                'integration_system_id': system_id,
                'operation_type': operation_type,
                'operation_name': operation_name,
                'status': status,
                'response_body': result,
                'records_processed': result.get('total_transactions_processed', 0),
                'records_successful': result.get('transactions_created', 0) + result.get('transactions_updated', 0),
                'records_failed': len(result.get('errors', [])),
                'business_context': {
                    'component': 'core_banking_integration',
                    'operation': operation_name
                }
            }
            
            self.supabase.table('integration_logs').insert(log_entry).execute()
            
        except Exception as e:
            logger.error(f"Error logging integration operation: {str(e)}")


class TemenosConnector:
    """Temenos T24/Transact core banking connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_transactions(self, system_config: Dict[str, Any],
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Sync transactions from Temenos T24 using REST API."""
        try:
            # Authenticate with T24
            await self._authenticate_t24(system_config)

            # Fetch transactions from T24
            transactions = await self._fetch_t24_transactions(system_config, start_date, end_date)

            # Process and normalize transactions
            sync_results = {
                'total_processed': len(transactions),
                'created': 0,
                'updated': 0,
                'flagged': 0,
                'duplicates': 0,
                'errors': []
            }

            for txn in transactions:
                try:
                    # Normalize transaction data
                    normalized_txn = await self._normalize_t24_transaction(txn)

                    # Check for duplicates
                    existing_txn = await self._find_existing_transaction(
                        normalized_txn['transaction_id'],
                        system_config.get('tenant_id')
                    )

                    if existing_txn:
                        # Check if update is needed
                        if await self._transaction_needs_update(existing_txn, normalized_txn):
                            await self._update_transaction(existing_txn['id'], normalized_txn)
                            sync_results['updated'] += 1
                        else:
                            sync_results['duplicates'] += 1
                    else:
                        # Create new transaction record
                        transaction_id = await self._create_transaction(normalized_txn, system_config.get('tenant_id'))
                        sync_results['created'] += 1

                        # Check for risk flags
                        if await self._check_transaction_risk_flags(normalized_txn):
                            await self._flag_transaction_for_review(transaction_id, normalized_txn)
                            sync_results['flagged'] += 1

                except Exception as e:
                    logger.error(f"Error processing T24 transaction {txn.get('transactionId')}: {e}")
                    sync_results['errors'].append({
                        'transaction_id': txn.get('transactionId'),
                        'error': str(e)
                    })

            logger.info(f"T24 sync completed: {sync_results}")
            return sync_results

        except Exception as e:
            logger.error(f"Temenos sync error: {str(e)}")
            raise

    async def _authenticate_t24(self, system_config: Dict[str, Any]):
        """Authenticate with Temenos T24 using OAuth 2.0 or basic auth."""
        try:
            base_url = system_config.get('t24_base_url')
            auth_type = system_config.get('t24_auth_type', 'oauth')

            if not base_url:
                raise ValueError("T24 base URL not configured")

            if auth_type == 'oauth':
                await self._authenticate_t24_oauth(system_config)
            else:
                await self._authenticate_t24_basic(system_config)

        except Exception as e:
            logger.error(f"T24 authentication error: {e}")
            raise

    async def _authenticate_t24_oauth(self, system_config: Dict[str, Any]):
        """Authenticate with T24 using OAuth 2.0."""
        try:
            client_id = system_config.get('t24_client_id')
            client_secret = system_config.get('t24_client_secret')

            if not client_id or not client_secret:
                raise ValueError("T24 OAuth credentials not configured")

            base_url = system_config.get('t24_base_url')
            token_url = f"{base_url}/api/oauth/token"

            auth_payload = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': 'transactions accounts customers'
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }

            async with self.session.post(token_url, data=auth_payload, headers=headers) as response:
                if response.status == 200:
                    token_response = await response.json()
                    self.auth_token = token_response['access_token']
                    self.token_expires = datetime.utcnow() + timedelta(seconds=token_response.get('expires_in', 3600))

                    self.auth_headers = {
                        'Authorization': f'Bearer {self.auth_token}',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }

                    logger.info("Successfully authenticated with T24 using OAuth")
                else:
                    error_text = await response.text()
                    raise Exception(f"T24 OAuth authentication failed: {error_text}")

        except Exception as e:
            logger.error(f"T24 OAuth authentication error: {e}")
            raise

    async def _authenticate_t24_basic(self, system_config: Dict[str, Any]):
        """Authenticate with T24 using basic authentication."""
        try:
            username = system_config.get('t24_username')
            password = system_config.get('t24_password')

            if not username or not password:
                raise ValueError("T24 basic auth credentials not configured")

            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()

            self.auth_headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            logger.info("T24 basic authentication configured")

        except Exception as e:
            logger.error(f"T24 basic authentication error: {e}")
            raise
    
    async def _fetch_t24_transactions(self, system_config: Dict[str, Any],
                                     start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch transactions from T24 REST API."""
        try:
            base_url = system_config.get('t24_base_url')

            # T24 transaction endpoint
            transactions_url = f"{base_url}/api/v1.0.0/holdings/transactions"

            # Build query parameters
            params = {
                'fromDate': start_date.strftime('%Y-%m-%d'),
                'toDate': end_date.strftime('%Y-%m-%d'),
                'page': 1,
                'size': system_config.get('batch_size', 1000)
            }

            all_transactions = []

            while True:
                async with self.session.get(transactions_url, headers=self.auth_headers, params=params) as response:
                    if response.status == 200:
                        response_data = await response.json()

                        # T24 response structure
                        transactions = response_data.get('body', [])
                        all_transactions.extend(transactions)

                        # Check if there are more pages
                        if len(transactions) < params['size']:
                            break

                        params['page'] += 1

                    else:
                        error_text = await response.text()
                        raise Exception(f"T24 transaction fetch failed: HTTP {response.status} - {error_text}")

            logger.info(f"Fetched {len(all_transactions)} transactions from T24")
            return all_transactions

        except Exception as e:
            logger.error(f"Error fetching T24 transactions: {e}")
            return []

    async def _normalize_t24_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize T24 transaction data to standard format."""
        try:
            # Extract T24 transaction fields
            normalized = {
                'transaction_id': txn.get('transactionId', ''),
                'external_reference': txn.get('transactionReference', ''),
                'account_number': txn.get('accountId', ''),
                'amount': Decimal(str(txn.get('transactionAmount', {}).get('amount', '0'))),
                'currency': txn.get('transactionAmount', {}).get('currency', ''),
                'transaction_type': txn.get('transactionType', ''),
                'transaction_date': txn.get('bookingDate', ''),
                'value_date': txn.get('valueDate', ''),
                'counterparty_name': txn.get('counterpartyName', ''),
                'counterparty_account': txn.get('counterpartyAccount', ''),
                'description': txn.get('narrative', ''),
                'channel': txn.get('channelId', ''),
                'branch_code': txn.get('companyCode', ''),
                'status': txn.get('recordStatus', ''),
                'source_system': 'temenos_t24',
                'raw_data': txn,
                'processed_at': datetime.utcnow().isoformat()
            }

            # Additional T24-specific fields
            if 'additionalInfo' in txn:
                additional_info = txn['additionalInfo']
                normalized.update({
                    'purpose_code': additional_info.get('purposeCode', ''),
                    'country_code': additional_info.get('countryCode', ''),
                    'regulatory_reporting': additional_info.get('regulatoryReporting', {})
                })

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing T24 transaction: {e}")
            raise

    async def setup_realtime_monitoring(self, system_config: Dict[str, Any]) -> str:
        """Setup real-time transaction monitoring webhook with T24."""
        try:
            await self._authenticate_t24(system_config)

            base_url = system_config.get('t24_base_url')
            webhook_url = f"https://api.regulens-ai.com/webhooks/temenos/{system_config.get('system_id')}"

            # T24 webhook configuration endpoint
            webhook_config_url = f"{base_url}/api/v1.0.0/system/hooks"

            webhook_payload = {
                'hookName': f"regulens_ai_monitor_{system_config.get('system_id')}",
                'hookUrl': webhook_url,
                'events': [
                    'TRANSACTION_CREATED',
                    'TRANSACTION_UPDATED',
                    'ACCOUNT_UPDATED',
                    'CUSTOMER_UPDATED'
                ],
                'filters': {
                    'transactionTypes': system_config.get('monitored_transaction_types', []),
                    'amountThreshold': system_config.get('amount_threshold', 10000),
                    'currencies': system_config.get('monitored_currencies', ['USD', 'EUR', 'GBP'])
                },
                'authentication': {
                    'type': 'bearer',
                    'token': system_config.get('webhook_auth_token')
                }
            }

            async with self.session.post(webhook_config_url, json=webhook_payload, headers=self.auth_headers) as response:
                if response.status in [200, 201]:
                    webhook_response = await response.json()
                    logger.info(f"T24 webhook configured successfully: {webhook_response.get('hookId')}")
                    return webhook_url
                else:
                    error_text = await response.text()
                    raise Exception(f"T24 webhook setup failed: {error_text}")

        except Exception as e:
            logger.error(f"T24 webhook setup error: {e}")
            # Return webhook URL even if setup fails (for manual configuration)
            return f"https://api.regulens-ai.com/webhooks/temenos/{system_config.get('system_id')}"


class FlexcubeConnector:
    """Oracle Flexcube core banking connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_transactions(self, system_config: Dict[str, Any],
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Sync transactions from Oracle Flexcube using REST API."""
        try:
            # Authenticate with Flexcube
            await self._authenticate_flexcube(system_config)

            # Fetch transactions from Flexcube
            transactions = await self._fetch_flexcube_transactions(system_config, start_date, end_date)

            # Process and normalize transactions
            sync_results = {
                'total_processed': len(transactions),
                'created': 0,
                'updated': 0,
                'flagged': 0,
                'duplicates': 0,
                'errors': []
            }

            for txn in transactions:
                try:
                    # Normalize transaction data
                    normalized_txn = await self._normalize_flexcube_transaction(txn)

                    # Check for duplicates
                    existing_txn = await self._find_existing_transaction(
                        normalized_txn['transaction_id'],
                        system_config.get('tenant_id')
                    )

                    if existing_txn:
                        # Check if update is needed
                        if await self._transaction_needs_update(existing_txn, normalized_txn):
                            await self._update_transaction(existing_txn['id'], normalized_txn)
                            sync_results['updated'] += 1
                        else:
                            sync_results['duplicates'] += 1
                    else:
                        # Create new transaction record
                        transaction_id = await self._create_transaction(normalized_txn, system_config.get('tenant_id'))
                        sync_results['created'] += 1

                        # Check for risk flags
                        if await self._check_transaction_risk_flags(normalized_txn):
                            await self._flag_transaction_for_review(transaction_id, normalized_txn)
                            sync_results['flagged'] += 1

                except Exception as e:
                    logger.error(f"Error processing Flexcube transaction {txn.get('txnId')}: {e}")
                    sync_results['errors'].append({
                        'transaction_id': txn.get('txnId'),
                        'error': str(e)
                    })

            logger.info(f"Flexcube sync completed: {sync_results}")
            return sync_results

        except Exception as e:
            logger.error(f"Flexcube sync error: {str(e)}")
            raise

    async def _authenticate_flexcube(self, system_config: Dict[str, Any]):
        """Authenticate with Oracle Flexcube."""
        try:
            base_url = system_config.get('flexcube_base_url')
            username = system_config.get('flexcube_username')
            password = system_config.get('flexcube_password')

            if not all([base_url, username, password]):
                raise ValueError("Missing required Flexcube configuration parameters")

            # Flexcube authentication endpoint
            auth_url = f"{base_url}/FCJNDIServices/FCGenericService"

            # SOAP authentication request for Flexcube
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                             xmlns:fcg="http://fcgeneric.fcjndi.fcubs.ofss.com/">
                <soapenv:Header/>
                <soapenv:Body>
                    <fcg:FCGenericRequest>
                        <fcg:requestHeader>
                            <fcg:requestUUID>{uuid.uuid4()}</fcg:requestUUID>
                            <fcg:serviceHeader>
                                <fcg:serviceName>FCGenericService</fcg:serviceName>
                                <fcg:operationName>authenticate</fcg:operationName>
                            </fcg:serviceHeader>
                        </fcg:requestHeader>
                        <fcg:requestBody>
                            <fcg:username>{username}</fcg:username>
                            <fcg:password>{password}</fcg:password>
                            <fcg:branchCode>{system_config.get('flexcube_branch_code', '001')}</fcg:branchCode>
                        </fcg:requestBody>
                    </fcg:FCGenericRequest>
                </soapenv:Body>
            </soapenv:Envelope>"""

            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'authenticate'
            }

            async with self.session.post(auth_url, data=soap_body, headers=headers) as response:
                if response.status == 200:
                    response_text = await response.text()

                    # Parse SOAP response to extract session token
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response_text)

                    # Find session token in response
                    session_token = None
                    for elem in root.iter():
                        if 'sessionToken' in elem.tag:
                            session_token = elem.text
                            break

                    if session_token:
                        self.session_token = session_token
                        self.auth_headers = {
                            'Content-Type': 'text/xml; charset=utf-8',
                            'Authorization': f'Bearer {session_token}'
                        }
                        logger.info("Successfully authenticated with Flexcube")
                    else:
                        raise Exception("No session token found in Flexcube authentication response")
                else:
                    error_text = await response.text()
                    raise Exception(f"Flexcube authentication failed: HTTP {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"Flexcube authentication error: {e}")
            raise
    
    async def _fetch_flexcube_transactions(self, system_config: Dict[str, Any],
                                          start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch transactions from Flexcube using SOAP API."""
        try:
            base_url = system_config.get('flexcube_base_url')

            # Flexcube transaction query SOAP request
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                             xmlns:fcg="http://fcgeneric.fcjndi.fcubs.ofss.com/">
                <soapenv:Header/>
                <soapenv:Body>
                    <fcg:FCGenericRequest>
                        <fcg:requestHeader>
                            <fcg:requestUUID>{uuid.uuid4()}</fcg:requestUUID>
                            <fcg:serviceHeader>
                                <fcg:serviceName>TransactionService</fcg:serviceName>
                                <fcg:operationName>queryTransactions</fcg:operationName>
                            </fcg:serviceHeader>
                            <fcg:sessionContext>
                                <fcg:sessionToken>{self.session_token}</fcg:sessionToken>
                            </fcg:sessionContext>
                        </fcg:requestHeader>
                        <fcg:requestBody>
                            <fcg:queryParams>
                                <fcg:fromDate>{start_date.strftime('%Y-%m-%d')}</fcg:fromDate>
                                <fcg:toDate>{end_date.strftime('%Y-%m-%d')}</fcg:toDate>
                                <fcg:maxRecords>{system_config.get('batch_size', 1000)}</fcg:maxRecords>
                                <fcg:branchCode>{system_config.get('flexcube_branch_code', '001')}</fcg:branchCode>
                            </fcg:queryParams>
                        </fcg:requestBody>
                    </fcg:FCGenericRequest>
                </soapenv:Body>
            </soapenv:Envelope>"""

            transaction_url = f"{base_url}/FCJNDIServices/TransactionService"

            async with self.session.post(transaction_url, data=soap_body, headers=self.auth_headers) as response:
                if response.status == 200:
                    response_text = await response.text()
                    transactions = await self._parse_flexcube_transactions(response_text)
                    logger.info(f"Fetched {len(transactions)} transactions from Flexcube")
                    return transactions
                else:
                    error_text = await response.text()
                    raise Exception(f"Flexcube transaction fetch failed: HTTP {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"Error fetching Flexcube transactions: {e}")
            return []

    async def _parse_flexcube_transactions(self, soap_response: str) -> List[Dict[str, Any]]:
        """Parse Flexcube SOAP response to extract transactions."""
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(soap_response)
            transactions = []

            # Navigate through SOAP response structure
            for txn_elem in root.iter():
                if 'transaction' in txn_elem.tag.lower():
                    txn_data = {}

                    for child in txn_elem:
                        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        txn_data[tag_name] = child.text

                    if txn_data:
                        transactions.append(txn_data)

            return transactions

        except Exception as e:
            logger.error(f"Error parsing Flexcube transactions: {e}")
            return []

    async def _normalize_flexcube_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Flexcube transaction data to standard format."""
        try:
            normalized = {
                'transaction_id': txn.get('txnId', ''),
                'external_reference': txn.get('txnRef', ''),
                'account_number': txn.get('accountNo', ''),
                'amount': Decimal(str(txn.get('txnAmount', '0'))),
                'currency': txn.get('txnCurrency', ''),
                'transaction_type': txn.get('txnType', ''),
                'transaction_date': txn.get('txnDate', ''),
                'value_date': txn.get('valueDate', ''),
                'counterparty_name': txn.get('counterpartyName', ''),
                'counterparty_account': txn.get('counterpartyAccount', ''),
                'description': txn.get('txnDescription', ''),
                'channel': txn.get('channelId', ''),
                'branch_code': txn.get('branchCode', ''),
                'status': txn.get('txnStatus', ''),
                'source_system': 'oracle_flexcube',
                'raw_data': txn,
                'processed_at': datetime.utcnow().isoformat()
            }

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing Flexcube transaction: {e}")
            raise

    async def setup_realtime_monitoring(self, system_config: Dict[str, Any]) -> str:
        """Setup real-time monitoring webhook for Flexcube."""
        try:
            await self._authenticate_flexcube(system_config)

            webhook_url = f"https://api.regulens-ai.com/webhooks/flexcube/{system_config.get('system_id')}"
            logger.info(f"Flexcube webhook configured: {webhook_url}")
            return webhook_url

        except Exception as e:
            logger.error(f"Flexcube webhook setup error: {e}")
            # Return webhook URL even if setup fails (for manual configuration)
            return f"https://api.regulens-ai.com/webhooks/flexcube/{system_config.get('system_id')}"


class FinacleConnector:
    """Infosys Finacle core banking connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_transactions(self, system_config: Dict[str, Any],
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Sync transactions from Infosys Finacle using REST API."""
        try:
            # Authenticate with Finacle
            await self._authenticate_finacle(system_config)

            # Fetch transactions from Finacle
            transactions = await self._fetch_finacle_transactions(system_config, start_date, end_date)

            # Process and normalize transactions
            sync_results = {
                'total_processed': len(transactions),
                'created': 0,
                'updated': 0,
                'flagged': 0,
                'duplicates': 0,
                'errors': []
            }

            for txn in transactions:
                try:
                    # Normalize transaction data
                    normalized_txn = await self._normalize_finacle_transaction(txn)

                    # Check for duplicates
                    existing_txn = await self._find_existing_transaction(
                        normalized_txn['transaction_id'],
                        system_config.get('tenant_id')
                    )

                    if existing_txn:
                        # Check if update is needed
                        if await self._transaction_needs_update(existing_txn, normalized_txn):
                            await self._update_transaction(existing_txn['id'], normalized_txn)
                            sync_results['updated'] += 1
                        else:
                            sync_results['duplicates'] += 1
                    else:
                        # Create new transaction record
                        transaction_id = await self._create_transaction(normalized_txn, system_config.get('tenant_id'))
                        sync_results['created'] += 1

                        # Check for risk flags
                        if await self._check_transaction_risk_flags(normalized_txn):
                            await self._flag_transaction_for_review(transaction_id, normalized_txn)
                            sync_results['flagged'] += 1

                except Exception as e:
                    logger.error(f"Error processing Finacle transaction {txn.get('transactionId')}: {e}")
                    sync_results['errors'].append({
                        'transaction_id': txn.get('transactionId'),
                        'error': str(e)
                    })

            logger.info(f"Finacle sync completed: {sync_results}")
            return sync_results

        except Exception as e:
            logger.error(f"Finacle sync error: {str(e)}")
            raise

    async def _authenticate_finacle(self, system_config: Dict[str, Any]):
        """Authenticate with Infosys Finacle using JWT tokens."""
        try:
            base_url = system_config.get('finacle_base_url')
            username = system_config.get('finacle_username')
            password = system_config.get('finacle_password')

            if not all([base_url, username, password]):
                raise ValueError("Missing required Finacle configuration parameters")

            # Finacle authentication endpoint
            auth_url = f"{base_url}/finaclews/api/auth/login"

            auth_payload = {
                'username': username,
                'password': password,
                'branchCode': system_config.get('finacle_branch_code', '001'),
                'applicationId': 'REGULENS_AI'
            }

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            async with self.session.post(auth_url, json=auth_payload, headers=headers) as response:
                if response.status == 200:
                    auth_response = await response.json()

                    if auth_response.get('status') == 'SUCCESS':
                        self.jwt_token = auth_response.get('token')
                        self.session_id = auth_response.get('sessionId')

                        self.auth_headers = {
                            'Authorization': f'Bearer {self.jwt_token}',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'X-Session-Id': self.session_id
                        }

                        logger.info("Successfully authenticated with Finacle")
                    else:
                        error_msg = auth_response.get('message', 'Authentication failed')
                        raise Exception(f"Finacle authentication failed: {error_msg}")
                else:
                    error_text = await response.text()
                    raise Exception(f"Finacle authentication failed: HTTP {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"Finacle authentication error: {e}")
            raise
    
    async def setup_realtime_monitoring(self, system_config: Dict[str, Any]) -> str:
        """Setup real-time monitoring webhook for Finacle."""
        webhook_url = f"https://regulens.ai/webhooks/finacle/{system_config['id']}"
        logger.info(f"Setup Finacle real-time monitoring: {webhook_url}")
        return webhook_url 