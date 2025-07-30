"""
Unit tests for external data integration services.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from core_infra.services.integrations.external_data_integration import (
    ExternalDataIntegrationService,
    OFACProvider,
    ExperianProvider,
    RefinitivProvider
)


class TestOFACProvider:
    """Test OFAC sanctions screening provider."""
    
    @pytest.fixture
    def ofac_provider(self):
        """Create OFAC provider for testing."""
        mock_supabase = Mock()
        return OFACProvider(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_screen_entity_with_match(self, ofac_provider):
        """Test OFAC screening with a match."""
        entity_data = {
            'name': 'Sanctioned Entity Corp',
            'address': '123 Main St',
            'date_of_birth': '1980-01-01'
        }
        
        source_config = {
            'tenant_id': str(uuid.uuid4()),
            'use_cache': True
        }
        
        # Mock OFAC data
        mock_ofac_data = {
            'sdn': [
                {
                    'uid': 'OFAC-12345',
                    'first_name': 'Sanctioned',
                    'last_name': 'Entity',
                    'title': 'Sanctioned Entity Corp',
                    'programs': ['COUNTER-TERRORISM'],
                    'sdn_type': 'individual',
                    'addresses': [],
                    'ids': [],
                    'remarks': 'Test entry'
                }
            ],
            'csl': [],
            'ssi': [],
            'version': '20240101',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        with patch.object(ofac_provider, '_get_ofac_data', return_value=mock_ofac_data):
            with patch.object(ofac_provider, '_log_screening_activity', return_value=None):
                with patch('fuzzywuzzy.fuzz.ratio', return_value=95):
                    result = await ofac_provider.screen_entity(source_config, entity_data)
        
        assert result['status'] == 'success'
        assert result['provider'] == 'ofac'
        assert len(result['matches']) > 0
        assert result['matches'][0]['match_type'] == 'exact_match'
        assert result['risk_score'] > 0.8
    
    @pytest.mark.asyncio
    async def test_screen_entity_no_match(self, ofac_provider):
        """Test OFAC screening with no match."""
        entity_data = {
            'name': 'Clean Entity Corp',
            'address': '456 Safe St'
        }
        
        source_config = {
            'tenant_id': str(uuid.uuid4())
        }
        
        mock_ofac_data = {
            'sdn': [],
            'csl': [],
            'ssi': [],
            'version': '20240101',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        with patch.object(ofac_provider, '_get_ofac_data', return_value=mock_ofac_data):
            with patch.object(ofac_provider, '_log_screening_activity', return_value=None):
                result = await ofac_provider.screen_entity(source_config, entity_data)
        
        assert result['status'] == 'success'
        assert result['provider'] == 'ofac'
        assert len(result['matches']) == 0
        assert result['risk_score'] == 0.0
    
    @pytest.mark.asyncio
    async def test_download_ofac_data(self, ofac_provider):
        """Test downloading OFAC data from official sources."""
        mock_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <sdnList>
            <sdnEntry uid="12345" sdnType="Individual">
                <firstName>Test</firstName>
                <lastName>Person</lastName>
                <program>TERRORISM</program>
            </sdnEntry>
        </sdnList>'''
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_xml_content)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            ofac_provider.session = mock_session.return_value.__aenter__.return_value
            
            result = await ofac_provider._download_ofac_data()
            
            assert 'sdn' in result
            assert 'csl' in result
            assert 'ssi' in result
            assert 'version' in result
    
    @pytest.mark.asyncio
    async def test_update_data(self, ofac_provider):
        """Test OFAC data update process."""
        mock_fresh_data = {
            'sdn': [{'uid': '1', 'title': 'Test Entity'}],
            'csl': [],
            'ssi': [],
            'version': '20240101'
        }
        
        with patch.object(ofac_provider, '_download_ofac_data', return_value=mock_fresh_data):
            with patch.object(ofac_provider, '_store_ofac_data', return_value=None):
                with patch.object(ofac_provider, '_cache_data', return_value=None):
                    result = await ofac_provider.update_data({'tenant_id': str(uuid.uuid4())})
        
        assert result['status'] == 'success'
        assert result['total_entries'] == 1
        assert result['sdn_entries'] == 1


class TestExperianProvider:
    """Test Experian credit bureau provider."""
    
    @pytest.fixture
    def experian_provider(self):
        """Create Experian provider for testing."""
        mock_supabase = Mock()
        return ExperianProvider(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, experian_provider):
        """Test successful Experian authentication."""
        source_config = {
            'experian_client_id': 'test_client_id',
            'experian_client_secret': 'test_client_secret',
            'use_sandbox': True
        }
        
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
            
            experian_provider.session = mock_session.return_value.__aenter__.return_value
            
            token = await experian_provider._authenticate(source_config)
            
            assert token == 'test_access_token'
    
    @pytest.mark.asyncio
    async def test_screen_entity_individual(self, experian_provider):
        """Test screening individual entity with Experian."""
        entity_data = {
            'name': 'John Doe',
            'first_name': 'John',
            'last_name': 'Doe',
            'ssn': '123-45-6789',
            'date_of_birth': '1980-01-01',
            'person_type': 'individual'
        }
        
        source_config = {
            'experian_client_id': 'test_id',
            'experian_client_secret': 'test_secret',
            'use_sandbox': True,
            'tenant_id': str(uuid.uuid4())
        }
        
        mock_credit_result = {
            'status': 'success',
            'credit_score': 750,
            'accounts': [],
            'inquiries': [],
            'public_records': []
        }
        
        mock_identity_result = {
            'status': 'success',
            'identity_verified': True,
            'confidence_score': 85
        }
        
        with patch.object(experian_provider, '_authenticate', return_value='test_token'):
            with patch.object(experian_provider, '_get_credit_profile', return_value=mock_credit_result):
                with patch.object(experian_provider, '_verify_identity', return_value=mock_identity_result):
                    with patch.object(experian_provider, '_detect_fraud', return_value={'status': 'success', 'fraud_score': 10}):
                        with patch.object(experian_provider, '_log_experian_screening', return_value=None):
                            result = await experian_provider.screen_entity(source_config, entity_data)
        
        assert result['status'] == 'success'
        assert result['provider'] == 'experian'
        assert 'credit_profile' in result
        assert 'identity_verification' in result
        assert 'risk_assessment' in result
    
    def test_determine_services_individual(self, experian_provider):
        """Test service determination for individual entities."""
        entity_data = {
            'person_type': 'individual',
            'ssn': '123-45-6789'
        }
        
        services = experian_provider._determine_services(entity_data)
        
        assert 'credit_profile' in services
        assert 'identity_verification' in services
        assert 'fraud_detection' in services
    
    def test_determine_services_business(self, experian_provider):
        """Test service determination for business entities."""
        entity_data = {
            'person_type': 'business',
            'ein': '12-3456789'
        }
        
        services = experian_provider._determine_services(entity_data)
        
        assert 'business_credit' in services
        assert 'identity_verification' in services


class TestExternalDataIntegrationService:
    """Test main external data integration service."""
    
    @pytest.fixture
    def integration_service(self):
        """Create integration service for testing."""
        mock_supabase = Mock()
        return ExternalDataIntegrationService(mock_supabase)
    
    @pytest.mark.asyncio
    async def test_screen_entity_comprehensive(self, integration_service):
        """Test comprehensive entity screening across multiple providers."""
        entity_data = {
            'name': 'Test Entity',
            'first_name': 'Test',
            'last_name': 'Entity',
            'ssn': '123-45-6789'
        }
        
        tenant_id = str(uuid.uuid4())
        screening_type = 'comprehensive'
        
        # Mock enabled data sources
        mock_sources = [
            {
                'id': str(uuid.uuid4()),
                'provider': 'ofac',
                'source_type': 'sanctions',
                'config': {'use_cache': True}
            },
            {
                'id': str(uuid.uuid4()),
                'provider': 'experian',
                'source_type': 'credit_bureau',
                'config': {'use_sandbox': True}
            }
        ]
        
        # Mock provider responses
        mock_ofac_result = {
            'provider': 'ofac',
            'status': 'success',
            'matches': [],
            'risk_score': 0.0
        }
        
        mock_experian_result = {
            'provider': 'experian',
            'status': 'success',
            'credit_profile': {'credit_score': 750},
            'risk_assessment': {'overall_risk_score': 0.2}
        }
        
        with patch.object(integration_service, '_get_enabled_data_sources', return_value=mock_sources):
            with patch.object(integration_service.providers['ofac'], 'screen_entity', return_value=mock_ofac_result):
                with patch.object(integration_service.providers['experian'], 'screen_entity', return_value=mock_experian_result):
                    with patch.object(integration_service, '_store_screening_results', return_value=None):
                        result = await integration_service.screen_entity(
                            tenant_id, entity_data, screening_type
                        )
        
        assert result['status'] == 'success'
        assert len(result['provider_results']) == 2
        assert 'ofac' in [r['provider'] for r in result['provider_results']]
        assert 'experian' in [r['provider'] for r in result['provider_results']]
        assert 'overall_risk_assessment' in result
    
    @pytest.mark.asyncio
    async def test_update_all_data_sources(self, integration_service):
        """Test updating all data sources."""
        tenant_id = str(uuid.uuid4())
        
        mock_sources = [
            {
                'id': str(uuid.uuid4()),
                'provider': 'ofac',
                'config': {'tenant_id': tenant_id}
            }
        ]
        
        mock_update_result = {
            'status': 'success',
            'total_entries': 1000,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        with patch.object(integration_service, '_get_all_data_sources', return_value=mock_sources):
            with patch.object(integration_service.providers['ofac'], 'update_data', return_value=mock_update_result):
                result = await integration_service.update_all_data_sources(tenant_id)
        
        assert result['status'] == 'success'
        assert len(result['update_results']) == 1
        assert result['update_results'][0]['provider'] == 'ofac'


class TestEUSanctionsProviderProduction:
    """Test production EU sanctions screening provider."""

    @pytest.fixture
    def eu_provider(self):
        """Create EU sanctions provider for testing."""
        mock_supabase = Mock()
        from core_infra.services.integrations.external_data_integration import EUSanctionsProvider
        return EUSanctionsProvider(mock_supabase)

    @pytest.mark.asyncio
    async def test_screen_entity_production(self, eu_provider):
        """Test production EU sanctions screening."""
        source_config = {
            'tenant_id': str(uuid.uuid4()),
            'use_cache': True
        }

        entity_data = {
            'name': 'Test Entity',
            'address': '123 Test Street',
            'date_of_birth': '1980-01-01'
        }

        mock_eu_data = {
            'consolidated': [
                {
                    'entity_id': 'EU001',
                    'names': [{'name': 'Different Entity', 'name_type': 'primary'}],
                    'sanctions_program': 'EU Consolidated'
                }
            ],
            'financial': [],
            'version': '20240129_120000'
        }

        with patch.object(eu_provider, '_get_eu_sanctions_data', return_value=mock_eu_data):
            with patch.object(eu_provider, '_screen_against_consolidated_list', return_value=[]):
                with patch.object(eu_provider, '_screen_against_financial_sanctions', return_value=[]):
                    result = await eu_provider.screen_entity(source_config, entity_data)

                    assert result['status'] == 'success'
                    assert result['provider'] == 'eu_sanctions'
                    assert result['entity_name'] == 'Test Entity'
                    assert result['screening_result'] == 'clear'
                    assert result['lists_checked'] == 2


class TestRefinitivProviderProduction:
    """Test production Refinitiv provider implementation."""

    @pytest.fixture
    def refinitiv_provider(self):
        """Create Refinitiv provider for testing."""
        mock_supabase = Mock()
        from core_infra.services.integrations.external_data_integration import RefinitivProvider
        return RefinitivProvider(mock_supabase)

    @pytest.mark.asyncio
    async def test_authenticate_refinitiv_success(self, refinitiv_provider):
        """Test successful Refinitiv authentication."""
        source_config = {
            'refinitiv_api_key': 'test_api_key',
            'refinitiv_username': 'test_user',
            'refinitiv_password': 'test_password',
            'refinitiv_app_id': 'RegulensAI'
        }

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

            refinitiv_provider.session = mock_session.return_value.__aenter__.return_value

            token = await refinitiv_provider._authenticate_refinitiv(source_config)

            assert token == 'test_access_token'
