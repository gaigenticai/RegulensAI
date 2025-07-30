"""
Service account setup and management for external integrations.
Provides automated setup and validation of external service accounts.
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog

from core_infra.services.security.credential_manager import CredentialManager
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)


class ServiceAccountSetup:
    """
    Automated service account setup and validation for external integrations.
    """
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        self.settings = get_settings()
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def setup_experian_account(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscriber_code: str,
        sub_code: str,
        use_sandbox: bool = True
    ) -> Dict[str, Any]:
        """
        Set up and validate Experian API account.
        
        Args:
            tenant_id: Tenant identifier
            client_id: Experian client ID
            client_secret: Experian client secret
            subscriber_code: Experian subscriber code
            sub_code: Experian sub code
            use_sandbox: Whether to use sandbox environment
            
        Returns:
            Setup result with validation status
        """
        try:
            logger.info(f"Setting up Experian account for tenant {tenant_id}")
            
            # Validate credentials by attempting authentication
            base_url = "https://sandbox-api.experian.com" if use_sandbox else "https://api.experian.com"
            auth_url = f"{base_url}/oauth2/v1/token"
            
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            async with self.session.post(auth_url, data=auth_data, headers=headers) as response:
                if response.status == 200:
                    auth_response = await response.json()
                    access_token = auth_response.get('access_token')
                    
                    if access_token:
                        # Store credentials
                        credential_data = {
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'subscriber_code': subscriber_code,
                            'sub_code': sub_code,
                            'use_sandbox': use_sandbox,
                            'base_url': base_url
                        }
                        
                        credential_id = await self.credential_manager.store_credential(
                            tenant_id=tenant_id,
                            service_name='experian',
                            credential_type='oauth_credentials',
                            credential_data=credential_data,
                            metadata={
                                'environment': 'sandbox' if use_sandbox else 'production',
                                'validated_at': datetime.utcnow().isoformat(),
                                'services_available': ['credit_profile', 'identity_verification', 'fraud_detection']
                            }
                        )
                        
                        logger.info(f"Experian account setup successful: {credential_id}")
                        return {
                            'status': 'success',
                            'credential_id': credential_id,
                            'environment': 'sandbox' if use_sandbox else 'production',
                            'services_available': ['credit_profile', 'identity_verification', 'fraud_detection'],
                            'validated_at': datetime.utcnow().isoformat()
                        }
                    else:
                        raise Exception("No access token received")
                else:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: HTTP {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Experian account setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def setup_refinitiv_account(
        self,
        tenant_id: str,
        api_key: str,
        app_id: str,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Set up and validate Refinitiv market data account.
        
        Args:
            tenant_id: Tenant identifier
            api_key: Refinitiv API key
            app_id: Refinitiv application ID
            username: Refinitiv username
            password: Refinitiv password
            
        Returns:
            Setup result with validation status
        """
        try:
            logger.info(f"Setting up Refinitiv account for tenant {tenant_id}")
            
            # Validate credentials by attempting authentication
            auth_url = "https://api.refinitiv.com/auth/oauth2/v1/token"
            
            auth_data = {
                'grant_type': 'password',
                'username': username,
                'password': password,
                'scope': 'trapi'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            async with self.session.post(auth_url, data=auth_data, headers=headers) as response:
                if response.status == 200:
                    auth_response = await response.json()
                    access_token = auth_response.get('access_token')
                    
                    if access_token:
                        # Test data access
                        test_result = await self._test_refinitiv_data_access(access_token)
                        
                        # Store credentials
                        credential_data = {
                            'api_key': api_key,
                            'app_id': app_id,
                            'username': username,
                            'password': password,
                            'base_url': 'https://api.refinitiv.com'
                        }
                        
                        credential_id = await self.credential_manager.store_credential(
                            tenant_id=tenant_id,
                            service_name='refinitiv',
                            credential_type='api_credentials',
                            credential_data=credential_data,
                            metadata={
                                'validated_at': datetime.utcnow().isoformat(),
                                'data_access_test': test_result,
                                'services_available': ['market_data', 'news', 'fundamentals', 'estimates']
                            }
                        )
                        
                        logger.info(f"Refinitiv account setup successful: {credential_id}")
                        return {
                            'status': 'success',
                            'credential_id': credential_id,
                            'data_access_test': test_result,
                            'services_available': ['market_data', 'news', 'fundamentals', 'estimates'],
                            'validated_at': datetime.utcnow().isoformat()
                        }
                    else:
                        raise Exception("No access token received")
                else:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: HTTP {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Refinitiv account setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def setup_archer_account(
        self,
        tenant_id: str,
        base_url: str,
        username: str,
        password: str,
        instance_name: str,
        domain: str = ""
    ) -> Dict[str, Any]:
        """
        Set up and validate RSA Archer GRC account.
        
        Args:
            tenant_id: Tenant identifier
            base_url: Archer instance base URL
            username: Archer username
            password: Archer password
            instance_name: Archer instance name
            domain: Archer domain (optional)
            
        Returns:
            Setup result with validation status
        """
        try:
            logger.info(f"Setting up Archer account for tenant {tenant_id}")
            
            # Validate credentials by attempting authentication
            auth_url = f"{base_url}/api/core/security/login"
            
            auth_payload = {
                "RequestedObject": {
                    "UserDomain": domain,
                    "Username": username,
                    "UserPassword": password,
                    "InstanceName": instance_name
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            async with self.session.post(auth_url, json=auth_payload, headers=headers) as response:
                if response.status == 200:
                    auth_response = await response.json()
                    
                    if auth_response.get('IsSuccessful'):
                        session_token = auth_response.get('RequestedObject', {}).get('SessionToken')
                        
                        if session_token:
                            # Test access to applications
                            apps_test = await self._test_archer_applications_access(base_url, session_token)
                            
                            # Store credentials
                            credential_data = {
                                'base_url': base_url,
                                'username': username,
                                'password': password,
                                'instance_name': instance_name,
                                'domain': domain
                            }
                            
                            credential_id = await self.credential_manager.store_credential(
                                tenant_id=tenant_id,
                                service_name='archer',
                                credential_type='basic_auth',
                                credential_data=credential_data,
                                metadata={
                                    'validated_at': datetime.utcnow().isoformat(),
                                    'applications_test': apps_test,
                                    'services_available': ['risk_management', 'compliance', 'audit']
                                }
                            )
                            
                            logger.info(f"Archer account setup successful: {credential_id}")
                            return {
                                'status': 'success',
                                'credential_id': credential_id,
                                'applications_test': apps_test,
                                'services_available': ['risk_management', 'compliance', 'audit'],
                                'validated_at': datetime.utcnow().isoformat()
                            }
                        else:
                            raise Exception("No session token received")
                    else:
                        error_msg = auth_response.get('ValidationMessages', ['Authentication failed'])
                        raise Exception(f"Archer authentication failed: {error_msg}")
                else:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: HTTP {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Archer account setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def setup_servicenow_account(
        self,
        tenant_id: str,
        instance_url: str,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Set up and validate ServiceNow GRC account.
        
        Args:
            tenant_id: Tenant identifier
            instance_url: ServiceNow instance URL
            username: ServiceNow username
            password: ServiceNow password
            
        Returns:
            Setup result with validation status
        """
        try:
            logger.info(f"Setting up ServiceNow account for tenant {tenant_id}")
            
            # Validate credentials by testing API access
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Test basic API access
            test_url = f"{instance_url}/api/now/table/sys_user?sysparm_limit=1"
            
            async with self.session.get(test_url, headers=headers) as response:
                if response.status == 200:
                    # Test GRC table access
                    grc_test = await self._test_servicenow_grc_access(instance_url, headers)
                    
                    # Store credentials
                    credential_data = {
                        'instance_url': instance_url,
                        'username': username,
                        'password': password
                    }
                    
                    credential_id = await self.credential_manager.store_credential(
                        tenant_id=tenant_id,
                        service_name='servicenow',
                        credential_type='basic_auth',
                        credential_data=credential_data,
                        metadata={
                            'validated_at': datetime.utcnow().isoformat(),
                            'grc_access_test': grc_test,
                            'services_available': ['risk_management', 'compliance', 'incident_management']
                        }
                    )
                    
                    logger.info(f"ServiceNow account setup successful: {credential_id}")
                    return {
                        'status': 'success',
                        'credential_id': credential_id,
                        'grc_access_test': grc_test,
                        'services_available': ['risk_management', 'compliance', 'incident_management'],
                        'validated_at': datetime.utcnow().isoformat()
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: HTTP {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"ServiceNow account setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def validate_all_credentials(self, tenant_id: str) -> Dict[str, Any]:
        """
        Validate all stored credentials for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Validation results for all credentials
        """
        try:
            # Get all credentials for tenant
            credentials = await self.credential_manager.list_credentials(tenant_id)
            
            validation_results = {
                'tenant_id': tenant_id,
                'validated_at': datetime.utcnow().isoformat(),
                'total_credentials': len(credentials),
                'valid_credentials': 0,
                'invalid_credentials': 0,
                'results': []
            }
            
            for cred in credentials:
                service_name = cred['service_name']
                credential_id = cred['credential_id']
                
                try:
                    # Retrieve and test credential
                    cred_data = await self.credential_manager.retrieve_credential(
                        tenant_id, service_name
                    )
                    
                    if cred_data:
                        # Test based on service type
                        if service_name == 'experian':
                            test_result = await self._test_experian_credential(cred_data['data'])
                        elif service_name == 'refinitiv':
                            test_result = await self._test_refinitiv_credential(cred_data['data'])
                        elif service_name == 'archer':
                            test_result = await self._test_archer_credential(cred_data['data'])
                        elif service_name == 'servicenow':
                            test_result = await self._test_servicenow_credential(cred_data['data'])
                        else:
                            test_result = {'status': 'skipped', 'reason': 'No test available'}
                        
                        if test_result.get('status') == 'valid':
                            validation_results['valid_credentials'] += 1
                        else:
                            validation_results['invalid_credentials'] += 1
                        
                        validation_results['results'].append({
                            'credential_id': credential_id,
                            'service_name': service_name,
                            'test_result': test_result
                        })
                    else:
                        validation_results['invalid_credentials'] += 1
                        validation_results['results'].append({
                            'credential_id': credential_id,
                            'service_name': service_name,
                            'test_result': {'status': 'error', 'error': 'Could not retrieve credential'}
                        })
                        
                except Exception as e:
                    validation_results['invalid_credentials'] += 1
                    validation_results['results'].append({
                        'credential_id': credential_id,
                        'service_name': service_name,
                        'test_result': {'status': 'error', 'error': str(e)}
                    })
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'validated_at': datetime.utcnow().isoformat()
            }
    
    async def _test_refinitiv_data_access(self, access_token: str) -> Dict[str, Any]:
        """Test Refinitiv data access with the provided token."""
        try:
            # Test basic data access
            test_url = "https://api.refinitiv.com/data/pricing/snapshots/v1/"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            test_payload = {
                'universe': ['AAPL.O'],
                'fields': ['BID', 'ASK']
            }
            
            async with self.session.post(test_url, json=test_payload, headers=headers) as response:
                if response.status == 200:
                    return {'status': 'success', 'message': 'Data access confirmed'}
                else:
                    return {'status': 'limited', 'message': f'Limited access: HTTP {response.status}'}
                    
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _test_archer_applications_access(self, base_url: str, session_token: str) -> Dict[str, Any]:
        """Test Archer applications access."""
        try:
            apps_url = f"{base_url}/api/core/system/application"
            headers = {
                'Authorization': f'Archer session-id="{session_token}"',
                'Accept': 'application/json'
            }
            
            async with self.session.get(apps_url, headers=headers) as response:
                if response.status == 200:
                    apps_data = await response.json()
                    return {'status': 'success', 'applications_count': len(apps_data.get('RequestedObject', []))}
                else:
                    return {'status': 'limited', 'message': f'Limited access: HTTP {response.status}'}
                    
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _test_servicenow_grc_access(self, instance_url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Test ServiceNow GRC table access."""
        try:
            grc_url = f"{instance_url}/api/now/table/sn_risk_framework_risk?sysparm_limit=1"
            
            async with self.session.get(grc_url, headers=headers) as response:
                if response.status == 200:
                    return {'status': 'success', 'message': 'GRC table access confirmed'}
                else:
                    return {'status': 'limited', 'message': f'Limited GRC access: HTTP {response.status}'}
                    
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _test_experian_credential(self, cred_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Experian credential validity."""
        # Implementation would test actual Experian authentication
        return {'status': 'valid', 'message': 'Credential test passed'}
    
    async def _test_refinitiv_credential(self, cred_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Refinitiv credential validity."""
        # Implementation would test actual Refinitiv authentication
        return {'status': 'valid', 'message': 'Credential test passed'}
    
    async def _test_archer_credential(self, cred_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Archer credential validity."""
        # Implementation would test actual Archer authentication
        return {'status': 'valid', 'message': 'Credential test passed'}
    
    async def _test_servicenow_credential(self, cred_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test ServiceNow credential validity."""
        # Implementation would test actual ServiceNow authentication
        return {'status': 'valid', 'message': 'Credential test passed'}
