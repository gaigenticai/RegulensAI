"""
Unit tests for GRC system integration services.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from core_infra.services.integrations.grc_integration import (
    GRCIntegrationService,
    ArcherConnector,
    ServiceNowConnector,
    MetricStreamConnector
)


class TestArcherConnector:
    """Test RSA Archer GRC connector."""
    
    @pytest.fixture
    def archer_connector(self):
        """Create Archer connector for testing."""
        mock_supabase = Mock()
        return ArcherConnector(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, archer_connector):
        """Test successful Archer authentication."""
        system_config = {
            'archer_base_url': 'https://archer.company.com',
            'archer_username': 'test_user',
            'archer_password': 'test_password',
            'archer_instance_name': 'Default',
            'archer_domain': 'COMPANY'
        }
        
        mock_auth_response = {
            'IsSuccessful': True,
            'RequestedObject': {
                'SessionToken': 'test_session_token',
                'SessionTimeout': 30
            }
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_auth_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            archer_connector.session = mock_session.return_value.__aenter__.return_value
            
            token = await archer_connector._authenticate(system_config)
            
            assert token == 'test_session_token'
            assert archer_connector.auth_token == 'test_session_token'
            assert archer_connector.session_timeout == 30
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, archer_connector):
        """Test Archer authentication failure."""
        system_config = {
            'archer_base_url': 'https://archer.company.com',
            'archer_username': 'test_user',
            'archer_password': 'wrong_password',
            'archer_instance_name': 'Default'
        }
        
        mock_auth_response = {
            'IsSuccessful': False,
            'ValidationMessages': ['Invalid credentials']
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_auth_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            archer_connector.session = mock_session.return_value.__aenter__.return_value
            
            with pytest.raises(Exception) as exc_info:
                await archer_connector._authenticate(system_config)
            
            assert "Authentication failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fetch_archer_risks(self, archer_connector):
        """Test fetching risks from Archer."""
        system_config = {
            'archer_base_url': 'https://archer.company.com',
            'archer_risk_application_id': '123',
            'risk_title_field_id': '456',
            'risk_description_field_id': '457',
            'risk_category_field_id': '458',
            'risk_severity_field_id': '459',
            'max_records': 100
        }
        
        mock_search_response = {
            'IsSuccessful': True,
            'RequestedObject': {
                'Records': [
                    {
                        'Id': '1001',
                        'TrackingId': 'RISK-001',
                        'DateCreated': '2024-01-15T10:00:00Z',
                        'FieldContents': {
                            '456': {'Value': 'Operational Risk'},
                            '457': {'Value': 'Risk description'},
                            '458': {'Value': 'Operational'},
                            '459': {'Value': 'High'}
                        }
                    }
                ]
            }
        }
        
        with patch.object(archer_connector, '_ensure_authenticated', return_value=None):
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_search_response)
                
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                
                archer_connector.session = mock_session.return_value.__aenter__.return_value
                archer_connector.auth_token = 'test_token'
                
                risks = await archer_connector._fetch_archer_risks(system_config)
                
                assert len(risks) == 1
                assert risks[0]['id'] == '1001'
                assert risks[0]['tracking_id'] == 'RISK-001'
                assert risks[0]['title'] == 'Operational Risk'
                assert risks[0]['severity'] == 'High'
    
    @pytest.mark.asyncio
    async def test_create_archer_risk(self, archer_connector):
        """Test creating a new risk in Archer."""
        system_config = {
            'archer_base_url': 'https://archer.company.com',
            'archer_risk_application_id': '123',
            'risk_title_field_id': '456',
            'risk_description_field_id': '457'
        }
        
        risk_data = {
            'title': 'New Risk',
            'description': 'Risk description',
            'category': 'Operational',
            'severity': 'Medium'
        }
        
        mock_create_response = {
            'IsSuccessful': True,
            'RequestedObject': {
                'Id': '1002',
                'TrackingId': 'RISK-002'
            }
        }
        
        with patch.object(archer_connector, '_ensure_authenticated', return_value=None):
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 201
                mock_response.json = AsyncMock(return_value=mock_create_response)
                
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                
                archer_connector.session = mock_session.return_value.__aenter__.return_value
                archer_connector.auth_token = 'test_token'
                
                result = await archer_connector._create_archer_risk(system_config, risk_data)
                
                assert result['status'] == 'success'
                assert result['archer_id'] == '1002'
                assert result['tracking_id'] == 'RISK-002'
    
    def test_is_session_expired(self, archer_connector):
        """Test session expiration check."""
        # Test with no auth time
        assert archer_connector._is_session_expired() is True
        
        # Test with recent auth time
        archer_connector.auth_time = datetime.utcnow()
        archer_connector.session_timeout = 30
        assert archer_connector._is_session_expired() is False
        
        # Test with expired session
        from datetime import timedelta
        archer_connector.auth_time = datetime.utcnow() - timedelta(minutes=35)
        assert archer_connector._is_session_expired() is True


class TestServiceNowConnector:
    """Test ServiceNow GRC connector."""
    
    @pytest.fixture
    def servicenow_connector(self):
        """Create ServiceNow connector for testing."""
        mock_supabase = Mock()
        return ServiceNowConnector(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, servicenow_connector):
        """Test successful ServiceNow authentication."""
        system_config = {
            'servicenow_instance_url': 'https://company.service-now.com',
            'servicenow_username': 'test_user',
            'servicenow_password': 'test_password'
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'result': []})
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            servicenow_connector.session = mock_session.return_value.__aenter__.return_value
            
            result = await servicenow_connector._authenticate(system_config)
            
            assert result is True
            assert 'Authorization' in servicenow_connector.auth_headers
            assert servicenow_connector.auth_headers['Authorization'].startswith('Basic ')
    
    @pytest.mark.asyncio
    async def test_fetch_servicenow_risks(self, servicenow_connector):
        """Test fetching risks from ServiceNow."""
        system_config = {
            'servicenow_instance_url': 'https://company.service-now.com',
            'servicenow_risk_table': 'sn_risk_framework_risk',
            'max_records': 100
        }
        
        mock_risks_response = {
            'result': [
                {
                    'sys_id': 'risk-001',
                    'number': 'RISK0001',
                    'short_description': 'Test Risk',
                    'description': 'Test risk description',
                    'risk_category': {'display_value': 'Operational'},
                    'risk_level': {'display_value': 'High'},
                    'state': {'display_value': 'Open'},
                    'assigned_to': {'display_value': 'John Doe'},
                    'opened_at': '2024-01-15 10:00:00',
                    'updated_on': '2024-01-15 15:00:00'
                }
            ]
        }
        
        servicenow_connector.auth_headers = {'Authorization': 'Basic test'}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_risks_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            servicenow_connector.session = mock_session.return_value.__aenter__.return_value
            
            risks = await servicenow_connector._fetch_servicenow_risks(system_config)
            
            assert len(risks) == 1
            assert risks[0]['id'] == 'risk-001'
            assert risks[0]['tracking_id'] == 'RISK0001'
            assert risks[0]['title'] == 'Test Risk'
            assert risks[0]['severity'] == 'High'
            assert risks[0]['source_system'] == 'servicenow'
    
    @pytest.mark.asyncio
    async def test_sync_risk_register(self, servicenow_connector):
        """Test syncing risk register from ServiceNow."""
        system_config = {
            'servicenow_instance_url': 'https://company.service-now.com',
            'tenant_id': str(uuid.uuid4())
        }
        
        mock_risks = [
            {
                'id': 'risk-001',
                'tracking_id': 'RISK0001',
                'title': 'Test Risk',
                'description': 'Test description',
                'source_system': 'servicenow'
            }
        ]
        
        with patch.object(servicenow_connector, '_authenticate', return_value=True):
            with patch.object(servicenow_connector, '_fetch_servicenow_risks', return_value=mock_risks):
                with patch.object(servicenow_connector, '_find_existing_risk', return_value=None):
                    with patch.object(servicenow_connector, '_create_risk_record', return_value=None):
                        result = await servicenow_connector.sync_risk_register(system_config)
        
        assert result['total_processed'] == 1
        assert result['created'] == 1
        assert result['updated'] == 0
        assert len(result['errors']) == 0


class TestGRCIntegrationService:
    """Test main GRC integration service."""
    
    @pytest.fixture
    def grc_service(self):
        """Create GRC integration service for testing."""
        mock_supabase = Mock()
        return GRCIntegrationService(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_sync_all_systems(self, grc_service):
        """Test syncing all GRC systems."""
        tenant_id = str(uuid.uuid4())
        
        mock_systems = [
            {
                'id': str(uuid.uuid4()),
                'system_type': 'archer',
                'config': {'archer_base_url': 'https://archer.test.com'}
            },
            {
                'id': str(uuid.uuid4()),
                'system_type': 'servicenow',
                'config': {'servicenow_instance_url': 'https://test.service-now.com'}
            }
        ]
        
        mock_archer_result = {
            'total_processed': 5,
            'created': 2,
            'updated': 3,
            'conflicts': 0
        }
        
        mock_servicenow_result = {
            'total_processed': 3,
            'created': 1,
            'updated': 2,
            'conflicts': 0
        }
        
        with patch.object(grc_service, '_get_enabled_systems', return_value=mock_systems):
            with patch.object(grc_service.connectors['archer'], 'sync_risk_register', return_value=mock_archer_result):
                with patch.object(grc_service.connectors['servicenow'], 'sync_risk_register', return_value=mock_servicenow_result):
                    result = await grc_service.sync_all_systems(tenant_id)
        
        assert result['status'] == 'success'
        assert len(result['sync_results']) == 2
        assert result['summary']['total_processed'] == 8
        assert result['summary']['total_created'] == 3
        assert result['summary']['total_updated'] == 5


class TestMetricStreamConnectorProduction:
    """Test production MetricStream connector implementation."""

    @pytest.fixture
    def metricstream_connector(self):
        """Create MetricStream connector for testing."""
        mock_supabase = Mock()
        from core_infra.services.integrations.grc_integration import MetricStreamConnector
        return MetricStreamConnector(mock_supabase)

    @pytest.mark.asyncio
    async def test_authenticate_metricstream_api_key(self, metricstream_connector):
        """Test MetricStream API key authentication."""
        system_config = {
            'metricstream_base_url': 'https://company.metricstream.com',
            'metricstream_api_key': 'test_api_key',
            'metricstream_auth_type': 'api_key'
        }

        with patch.object(metricstream_connector, '_test_metricstream_connection', return_value=None):
            await metricstream_connector._authenticate_metricstream(system_config)

            assert hasattr(metricstream_connector, 'auth_headers')
            assert metricstream_connector.auth_headers['Authorization'] == 'Bearer test_api_key'

    @pytest.mark.asyncio
    async def test_sync_risk_register_production(self, metricstream_connector):
        """Test production MetricStream risk register sync."""
        system_config = {
            'system_name': 'MetricStream Production',
            'metricstream_base_url': 'https://company.metricstream.com',
            'metricstream_api_key': 'test_api_key',
            'metricstream_auth_type': 'api_key',
            'tenant_id': str(uuid.uuid4())
        }

        mock_metricstream_risks = [
            {
                'id': 'MS-001',
                'title': 'Operational Risk 1',
                'description': 'Test operational risk',
                'category': 'operational',
                'severity': 'high',
                'owner': 'risk.manager@company.com',
                'last_modified': '2024-01-29T10:00:00Z'
            }
        ]

        with patch.object(metricstream_connector, '_authenticate_metricstream', return_value=None):
            with patch.object(metricstream_connector, '_fetch_metricstream_risks', return_value=mock_metricstream_risks):
                with patch.object(metricstream_connector, '_normalize_metricstream_risk') as mock_normalize:
                    with patch.object(metricstream_connector, '_find_existing_risk', return_value=None):
                        with patch.object(metricstream_connector, '_create_risk_record', return_value=str(uuid.uuid4())):
                            mock_normalize.return_value = {
                                'external_id': 'MS-001',
                                'title': 'Operational Risk 1',
                                'description': 'Test operational risk',
                                'risk_category': 'operational',
                                'risk_level': 'high'
                            }

                            result = await metricstream_connector.sync_risk_register(system_config)

                            assert result['total_processed'] == 1
                            assert result['created'] == 1
                            assert result['updated'] == 0
                            assert len(result['errors']) == 0
