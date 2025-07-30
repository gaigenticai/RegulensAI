"""
Unit tests for core banking system integration services.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

from core_infra.services.integrations.core_banking_integration import (
    CoreBankingIntegrationService,
    TemenosConnector,
    FlexcubeConnector,
    FinacleConnector
)


class TestTemenosConnector:
    """Test Temenos T24 connector."""
    
    @pytest.fixture
    def temenos_connector(self):
        """Create Temenos connector for testing."""
        mock_supabase = Mock()
        return TemenosConnector(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_authenticate_oauth_success(self, temenos_connector):
        """Test successful T24 OAuth authentication."""
        system_config = {
            't24_base_url': 'https://t24.bank.com',
            't24_auth_type': 'oauth',
            't24_client_id': 'test_client_id',
            't24_client_secret': 'test_client_secret'
        }
        
        mock_token_response = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_token_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            temenos_connector.session = mock_session.return_value.__aenter__.return_value
            
            await temenos_connector._authenticate_t24(system_config)
            
            assert temenos_connector.auth_token == 'test_access_token'
            assert 'Authorization' in temenos_connector.auth_headers
            assert temenos_connector.auth_headers['Authorization'] == 'Bearer test_access_token'
    
    @pytest.mark.asyncio
    async def test_fetch_t24_transactions(self, temenos_connector):
        """Test fetching transactions from T24."""
        system_config = {
            't24_base_url': 'https://t24.bank.com',
            'batch_size': 100
        }
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        mock_transactions_response = {
            'body': [
                {
                    'transactionId': 'T24-001',
                    'transactionReference': 'REF-001',
                    'accountId': '1234567890',
                    'transactionAmount': {
                        'amount': '5000.00',
                        'currency': 'USD'
                    },
                    'transactionType': 'TRANSFER',
                    'bookingDate': '2024-01-15',
                    'valueDate': '2024-01-15',
                    'counterpartyName': 'ABC Corp',
                    'narrative': 'Wire transfer payment'
                }
            ]
        }
        
        temenos_connector.auth_headers = {'Authorization': 'Bearer test_token'}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_transactions_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            temenos_connector.session = mock_session.return_value.__aenter__.return_value
            
            transactions = await temenos_connector._fetch_t24_transactions(system_config, start_date, end_date)
            
            assert len(transactions) == 1
            assert transactions[0]['transactionId'] == 'T24-001'
            assert transactions[0]['transactionAmount']['amount'] == '5000.00'
    
    @pytest.mark.asyncio
    async def test_normalize_t24_transaction(self, temenos_connector):
        """Test normalizing T24 transaction data."""
        t24_transaction = {
            'transactionId': 'T24-001',
            'transactionReference': 'REF-001',
            'accountId': '1234567890',
            'transactionAmount': {
                'amount': '5000.00',
                'currency': 'USD'
            },
            'transactionType': 'TRANSFER',
            'bookingDate': '2024-01-15',
            'valueDate': '2024-01-15',
            'counterpartyName': 'ABC Corp',
            'counterpartyAccount': '9876543210',
            'narrative': 'Wire transfer payment',
            'channelId': 'ONLINE',
            'companyCode': '001'
        }
        
        normalized = await temenos_connector._normalize_t24_transaction(t24_transaction)
        
        assert normalized['transaction_id'] == 'T24-001'
        assert normalized['external_reference'] == 'REF-001'
        assert normalized['account_number'] == '1234567890'
        assert normalized['amount'] == Decimal('5000.00')
        assert normalized['currency'] == 'USD'
        assert normalized['transaction_type'] == 'TRANSFER'
        assert normalized['counterparty_name'] == 'ABC Corp'
        assert normalized['source_system'] == 'temenos_t24'
    
    @pytest.mark.asyncio
    async def test_sync_transactions(self, temenos_connector):
        """Test complete transaction sync process."""
        system_config = {
            't24_base_url': 'https://t24.bank.com',
            'tenant_id': str(uuid.uuid4())
        }
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        mock_transactions = [
            {
                'transactionId': 'T24-001',
                'transactionAmount': {'amount': '5000.00', 'currency': 'USD'},
                'transactionType': 'TRANSFER'
            }
        ]
        
        with patch.object(temenos_connector, '_authenticate_t24', return_value=None):
            with patch.object(temenos_connector, '_fetch_t24_transactions', return_value=mock_transactions):
                with patch.object(temenos_connector, '_find_existing_transaction', return_value=None):
                    with patch.object(temenos_connector, '_create_transaction', return_value=str(uuid.uuid4())):
                        with patch.object(temenos_connector, '_check_transaction_risk_flags', return_value=False):
                            result = await temenos_connector.sync_transactions(system_config, start_date, end_date)
        
        assert result['total_processed'] == 1
        assert result['created'] == 1
        assert result['updated'] == 0
        assert result['flagged'] == 0


class TestFlexcubeConnector:
    """Test Oracle Flexcube connector."""
    
    @pytest.fixture
    def flexcube_connector(self):
        """Create Flexcube connector for testing."""
        mock_supabase = Mock()
        return FlexcubeConnector(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_authenticate_flexcube(self, flexcube_connector):
        """Test Flexcube SOAP authentication."""
        system_config = {
            'flexcube_base_url': 'https://flexcube.bank.com',
            'flexcube_username': 'test_user',
            'flexcube_password': 'test_password',
            'flexcube_branch_code': '001'
        }
        
        mock_soap_response = '''<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body>
                <fcg:FCGenericResponse>
                    <fcg:responseBody>
                        <fcg:sessionToken>test_session_token</fcg:sessionToken>
                    </fcg:responseBody>
                </fcg:FCGenericResponse>
            </soapenv:Body>
        </soapenv:Envelope>'''
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_soap_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            flexcube_connector.session = mock_session.return_value.__aenter__.return_value
            
            await flexcube_connector._authenticate_flexcube(system_config)
            
            assert flexcube_connector.session_token == 'test_session_token'
            assert 'Authorization' in flexcube_connector.auth_headers
    
    @pytest.mark.asyncio
    async def test_normalize_flexcube_transaction(self, flexcube_connector):
        """Test normalizing Flexcube transaction data."""
        flexcube_transaction = {
            'txnId': 'FC-001',
            'txnRef': 'REF-001',
            'accountNo': '1234567890',
            'txnAmount': '5000.00',
            'txnCurrency': 'USD',
            'txnType': 'TRANSFER',
            'txnDate': '2024-01-15',
            'valueDate': '2024-01-15',
            'counterpartyName': 'ABC Corp',
            'txnDescription': 'Wire transfer payment',
            'branchCode': '001'
        }
        
        normalized = await flexcube_connector._normalize_flexcube_transaction(flexcube_transaction)
        
        assert normalized['transaction_id'] == 'FC-001'
        assert normalized['external_reference'] == 'REF-001'
        assert normalized['account_number'] == '1234567890'
        assert normalized['amount'] == Decimal('5000.00')
        assert normalized['currency'] == 'USD'
        assert normalized['source_system'] == 'oracle_flexcube'


class TestFinacleConnector:
    """Test Infosys Finacle connector."""
    
    @pytest.fixture
    def finacle_connector(self):
        """Create Finacle connector for testing."""
        mock_supabase = Mock()
        return FinacleConnector(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_authenticate_finacle(self, finacle_connector):
        """Test Finacle JWT authentication."""
        system_config = {
            'finacle_base_url': 'https://finacle.bank.com',
            'finacle_username': 'test_user',
            'finacle_password': 'test_password',
            'finacle_branch_code': '001'
        }
        
        mock_auth_response = {
            'status': 'SUCCESS',
            'token': 'test_jwt_token',
            'sessionId': 'test_session_id'
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_auth_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            finacle_connector.session = mock_session.return_value.__aenter__.return_value
            
            await finacle_connector._authenticate_finacle(system_config)
            
            assert finacle_connector.jwt_token == 'test_jwt_token'
            assert finacle_connector.session_id == 'test_session_id'
            assert 'Authorization' in finacle_connector.auth_headers
            assert finacle_connector.auth_headers['Authorization'] == 'Bearer test_jwt_token'


class TestCoreBankingIntegrationService:
    """Test main core banking integration service."""
    
    @pytest.fixture
    def cbs_service(self):
        """Create core banking integration service for testing."""
        mock_supabase = Mock()
        return CoreBankingIntegrationService(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_sync_transactions_all_systems(self, cbs_service):
        """Test syncing transactions from all CBS systems."""
        tenant_id = str(uuid.uuid4())
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        mock_systems = [
            {
                'id': str(uuid.uuid4()),
                'system_name': 'T24 Production',
                'vendor': 'temenos',
                'config': {'t24_base_url': 'https://t24.bank.com'}
            },
            {
                'id': str(uuid.uuid4()),
                'system_name': 'Flexcube Core',
                'vendor': 'flexcube',
                'config': {'flexcube_base_url': 'https://flexcube.bank.com'}
            }
        ]
        
        mock_temenos_result = {
            'total_processed': 100,
            'created': 80,
            'updated': 15,
            'flagged': 5,
            'duplicates': 0
        }
        
        mock_flexcube_result = {
            'total_processed': 50,
            'created': 40,
            'updated': 8,
            'flagged': 2,
            'duplicates': 0
        }
        
        with patch.object(cbs_service, '_get_enabled_cbs_systems', return_value=mock_systems):
            with patch.object(cbs_service.connectors['temenos'], 'sync_transactions', return_value=mock_temenos_result):
                with patch.object(cbs_service.connectors['flexcube'], 'sync_transactions', return_value=mock_flexcube_result):
                    with patch.object(cbs_service, '_update_system_sync_time', return_value=None):
                        result = await cbs_service.sync_transactions(tenant_id, None, start_date, end_date)
        
        assert result['status'] == 'success'
        assert len(result['systems_synced']) == 2
        assert result['total_transactions_processed'] == 150
        assert result['transactions_created'] == 120
        assert result['transactions_updated'] == 23
        assert result['transactions_flagged'] == 7
