"""
Unit tests for credential management system.
"""

import pytest
import asyncio
import uuid
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from core_infra.services.security.credential_manager import CredentialManager
from core_infra.services.security.service_account_setup import ServiceAccountSetup


class TestCredentialManager:
    """Test credential manager functionality."""
    
    @pytest.fixture
    def credential_manager(self):
        """Create credential manager for testing."""
        with patch('core_infra.services.security.credential_manager.get_settings'):
            with patch.dict('os.environ', {
                'CREDENTIAL_MASTER_PASSWORD': 'test-password',
                'CREDENTIAL_SALT': 'test-salt'
            }):
                return CredentialManager()
    
    def test_encryption_decryption(self, credential_manager):
        """Test credential encryption and decryption."""
        test_value = "super-secret-api-key-12345"
        
        # Encrypt the value
        encrypted = credential_manager._encrypt_value(test_value)
        assert encrypted != test_value
        assert isinstance(encrypted, str)
        
        # Decrypt the value
        decrypted = credential_manager._decrypt_value(encrypted)
        assert decrypted == test_value
    
    def test_is_sensitive_field(self, credential_manager):
        """Test sensitive field detection."""
        # Sensitive fields
        assert credential_manager._is_sensitive_field('password') is True
        assert credential_manager._is_sensitive_field('api_key') is True
        assert credential_manager._is_sensitive_field('client_secret') is True
        assert credential_manager._is_sensitive_field('access_token') is True
        assert credential_manager._is_sensitive_field('private_key') is True
        
        # Non-sensitive fields
        assert credential_manager._is_sensitive_field('username') is False
        assert credential_manager._is_sensitive_field('base_url') is False
        assert credential_manager._is_sensitive_field('client_id') is False
        assert credential_manager._is_sensitive_field('environment') is False
    
    def test_generate_credential_id(self, credential_manager):
        """Test credential ID generation."""
        tenant_id = str(uuid.uuid4())
        service_name = "experian"
        credential_type = "oauth_credentials"
        
        cred_id = credential_manager._generate_credential_id(tenant_id, service_name, credential_type)
        
        assert cred_id.startswith('cred_')
        assert len(cred_id) == 21  # 'cred_' + 16 hex characters
        
        # Should be deterministic for same inputs at same time
        cred_id2 = credential_manager._generate_credential_id(tenant_id, service_name, credential_type)
        # Note: These will be different due to timestamp, which is expected
    
    @pytest.mark.asyncio
    async def test_store_credential(self, credential_manager):
        """Test storing credentials."""
        tenant_id = str(uuid.uuid4())
        service_name = "experian"
        credential_type = "oauth_credentials"
        
        credential_data = {
            'client_id': 'test_client_id',
            'client_secret': 'super_secret_value',
            'base_url': 'https://api.experian.com',
            'environment': 'sandbox'
        }
        
        metadata = {
            'environment': 'sandbox',
            'created_by': 'test_user'
        }
        
        with patch('core_infra.services.security.credential_manager.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()
            
            credential_id = await credential_manager.store_credential(
                tenant_id=tenant_id,
                service_name=service_name,
                credential_type=credential_type,
                credential_data=credential_data,
                metadata=metadata
            )
            
            assert credential_id.startswith('cred_')
            mock_db.return_value.__aenter__.return_value.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_retrieve_credential(self, credential_manager):
        """Test retrieving credentials."""
        tenant_id = str(uuid.uuid4())
        service_name = "experian"
        credential_type = "oauth_credentials"
        
        # Mock database response
        mock_row = {
            'id': 'cred_test123',
            'encrypted_data': json.dumps({
                'client_id': 'test_client_id',
                'client_secret': credential_manager._encrypt_value('super_secret_value'),
                'base_url': 'https://api.experian.com'
            }),
            'expires_at': None,
            'metadata': json.dumps({'environment': 'sandbox'}),
            'created_at': datetime.utcnow()
        }
        
        with patch('core_infra.services.security.credential_manager.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.fetchrow = AsyncMock(return_value=mock_row)
            
            result = await credential_manager.retrieve_credential(
                tenant_id=tenant_id,
                service_name=service_name,
                credential_type=credential_type
            )
            
            assert result is not None
            assert result['credential_id'] == 'cred_test123'
            assert result['data']['client_id'] == 'test_client_id'
            assert result['data']['client_secret'] == 'super_secret_value'  # Should be decrypted
            assert result['data']['base_url'] == 'https://api.experian.com'
            assert result['metadata']['environment'] == 'sandbox'
    
    @pytest.mark.asyncio
    async def test_rotate_credential(self, credential_manager):
        """Test credential rotation."""
        tenant_id = str(uuid.uuid4())
        service_name = "experian"
        credential_type = "oauth_credentials"
        
        new_credential_data = {
            'client_id': 'new_client_id',
            'client_secret': 'new_super_secret_value',
            'base_url': 'https://api.experian.com'
        }
        
        with patch('core_infra.services.security.credential_manager.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()
            
            with patch.object(credential_manager, 'store_credential') as mock_store:
                mock_store.return_value = 'cred_new123'
                
                new_credential_id = await credential_manager.rotate_credential(
                    tenant_id=tenant_id,
                    service_name=service_name,
                    credential_type=credential_type,
                    new_credential_data=new_credential_data
                )
                
                assert new_credential_id == 'cred_new123'
                
                # Should have marked old credentials as expired
                mock_db.return_value.__aenter__.return_value.execute.assert_called()
                
                # Should have stored new credential
                mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_credentials(self, credential_manager):
        """Test listing credentials."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database response
        mock_rows = [
            {
                'id': 'cred_test123',
                'service_name': 'experian',
                'credential_type': 'oauth_credentials',
                'expires_at': None,
                'metadata': json.dumps({'environment': 'sandbox'}),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'id': 'cred_test456',
                'service_name': 'refinitiv',
                'credential_type': 'api_credentials',
                'expires_at': datetime.utcnow() + timedelta(days=30),
                'metadata': json.dumps({'environment': 'production'}),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        
        with patch('core_infra.services.security.credential_manager.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.fetch = AsyncMock(return_value=mock_rows)
            
            credentials = await credential_manager.list_credentials(tenant_id)
            
            assert len(credentials) == 2
            assert credentials[0]['credential_id'] == 'cred_test123'
            assert credentials[0]['service_name'] == 'experian'
            assert credentials[0]['is_expired'] is False
            
            assert credentials[1]['credential_id'] == 'cred_test456'
            assert credentials[1]['service_name'] == 'refinitiv'
            assert credentials[1]['is_expired'] is False


class TestServiceAccountSetup:
    """Test service account setup functionality."""
    
    @pytest.fixture
    def service_setup(self):
        """Create service account setup for testing."""
        return ServiceAccountSetup()
    
    @pytest.mark.asyncio
    async def test_setup_experian_account_success(self, service_setup):
        """Test successful Experian account setup."""
        tenant_id = str(uuid.uuid4())
        client_id = "test_client_id"
        client_secret = "test_client_secret"
        subscriber_code = "TEST123"
        sub_code = "SUB456"
        
        # Mock successful authentication response
        mock_auth_response = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_auth_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            service_setup.session = mock_session.return_value.__aenter__.return_value
            
            with patch.object(service_setup.credential_manager, 'store_credential') as mock_store:
                mock_store.return_value = 'cred_experian123'
                
                result = await service_setup.setup_experian_account(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    subscriber_code=subscriber_code,
                    sub_code=sub_code,
                    use_sandbox=True
                )
                
                assert result['status'] == 'success'
                assert result['credential_id'] == 'cred_experian123'
                assert result['environment'] == 'sandbox'
                assert 'services_available' in result
                
                # Should have stored credentials
                mock_store.assert_called_once()
                store_args = mock_store.call_args
                assert store_args[1]['service_name'] == 'experian'
                assert store_args[1]['credential_type'] == 'oauth_credentials'
    
    @pytest.mark.asyncio
    async def test_setup_experian_account_failure(self, service_setup):
        """Test failed Experian account setup."""
        tenant_id = str(uuid.uuid4())
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value='Unauthorized')
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            service_setup.session = mock_session.return_value.__aenter__.return_value
            
            result = await service_setup.setup_experian_account(
                tenant_id=tenant_id,
                client_id="invalid_id",
                client_secret="invalid_secret",
                subscriber_code="TEST123",
                sub_code="SUB456"
            )
            
            assert result['status'] == 'error'
            assert 'error' in result
            assert 'failed_at' in result
    
    @pytest.mark.asyncio
    async def test_setup_servicenow_account_success(self, service_setup):
        """Test successful ServiceNow account setup."""
        tenant_id = str(uuid.uuid4())
        instance_url = "https://test.service-now.com"
        username = "test_user"
        password = "test_password"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'result': []})
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            service_setup.session = mock_session.return_value.__aenter__.return_value
            
            with patch.object(service_setup, '_test_servicenow_grc_access') as mock_grc_test:
                mock_grc_test.return_value = {'status': 'success', 'message': 'GRC access confirmed'}
                
                with patch.object(service_setup.credential_manager, 'store_credential') as mock_store:
                    mock_store.return_value = 'cred_servicenow123'
                    
                    result = await service_setup.setup_servicenow_account(
                        tenant_id=tenant_id,
                        instance_url=instance_url,
                        username=username,
                        password=password
                    )
                    
                    assert result['status'] == 'success'
                    assert result['credential_id'] == 'cred_servicenow123'
                    assert 'grc_access_test' in result
                    assert 'services_available' in result
    
    @pytest.mark.asyncio
    async def test_validate_all_credentials(self, service_setup):
        """Test validating all credentials for a tenant."""
        tenant_id = str(uuid.uuid4())
        
        # Mock credentials list
        mock_credentials = [
            {
                'credential_id': 'cred_experian123',
                'service_name': 'experian',
                'credential_type': 'oauth_credentials'
            },
            {
                'credential_id': 'cred_servicenow456',
                'service_name': 'servicenow',
                'credential_type': 'basic_auth'
            }
        ]
        
        with patch.object(service_setup.credential_manager, 'list_credentials') as mock_list:
            mock_list.return_value = mock_credentials
            
            with patch.object(service_setup.credential_manager, 'retrieve_credential') as mock_retrieve:
                mock_retrieve.return_value = {
                    'data': {'client_id': 'test', 'client_secret': 'secret'}
                }
                
                with patch.object(service_setup, '_test_experian_credential') as mock_test_exp:
                    mock_test_exp.return_value = {'status': 'valid', 'message': 'Test passed'}
                    
                    with patch.object(service_setup, '_test_servicenow_credential') as mock_test_sn:
                        mock_test_sn.return_value = {'status': 'valid', 'message': 'Test passed'}
                        
                        result = await service_setup.validate_all_credentials(tenant_id)
                        
                        assert result['tenant_id'] == tenant_id
                        assert result['total_credentials'] == 2
                        assert result['valid_credentials'] == 2
                        assert result['invalid_credentials'] == 0
                        assert len(result['results']) == 2
    
    @pytest.mark.asyncio
    async def test_test_refinitiv_data_access(self, service_setup):
        """Test Refinitiv data access testing."""
        access_token = "test_access_token"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            service_setup.session = mock_session.return_value.__aenter__.return_value
            
            result = await service_setup._test_refinitiv_data_access(access_token)
            
            assert result['status'] == 'success'
            assert result['message'] == 'Data access confirmed'
