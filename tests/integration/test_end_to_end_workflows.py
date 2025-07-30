"""
End-to-end integration tests for RegulensAI workflows.
Tests cross-system integration between notifications, external data, and GRC systems.
"""

import pytest
import asyncio
import uuid
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import structlog

from core_infra.services.integrations.external_data_integration import ExternalDataIntegrationService
from core_infra.services.integrations.grc_integration import GRCIntegrationService
from core_infra.services.notifications.delivery import NotificationDeliveryService
from core_infra.services.notifications.template_engine import TemplateEngine
from core_infra.services.security.credential_manager import CredentialManager

logger = structlog.get_logger(__name__)


class TestEndToEndWorkflows:
    """
    Comprehensive end-to-end workflow testing for RegulensAI.
    Tests complete business processes across all integrated systems.
    """
    
    @pytest.fixture
    async def test_environment(self):
        """Set up test environment with all services."""
        mock_supabase = Mock()
        
        # Initialize all services
        services = {
            'external_data': ExternalDataIntegrationService(mock_supabase),
            'grc_integration': GRCIntegrationService(mock_supabase),
            'notifications': NotificationDeliveryService(mock_supabase),
            'template_engine': TemplateEngine(mock_supabase),
            'credentials': CredentialManager()
        }
        
        # Start all async services
        async with services['external_data'] as ext_data:
            async with services['grc_integration'] as grc:
                async with services['notifications'] as notifications:
                    yield {
                        'external_data': ext_data,
                        'grc_integration': grc,
                        'notifications': notifications,
                        'template_engine': services['template_engine'],
                        'credentials': services['credentials']
                    }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_sanctions_screening_workflow(self, test_environment):
        """
        Test complete sanctions screening workflow:
        1. Entity screening via external data providers
        2. Risk assessment and scoring
        3. GRC system notification if matches found
        4. Stakeholder notifications
        """
        tenant_id = str(uuid.uuid4())
        entity_data = {
            'name': 'Test Corporation Ltd',
            'address': '123 Business Street, London, UK',
            'entity_type': 'corporation',
            'business_registration': 'UK12345678'
        }
        
        # Step 1: Screen entity against all sanctions lists
        screening_results = await test_environment['external_data'].screen_entity(
            tenant_id=tenant_id,
            entity_data=entity_data,
            screening_type='comprehensive'
        )
        
        assert screening_results['status'] == 'success'
        assert 'provider_results' in screening_results
        assert len(screening_results['provider_results']) >= 3  # OFAC, EU, UN minimum
        
        # Step 2: If matches found, create risk record in GRC system
        if screening_results.get('total_matches', 0) > 0:
            risk_update = {
                'type': 'risk',
                'title': f'Sanctions Screening Alert: {entity_data["name"]}',
                'description': f'Potential sanctions match found for {entity_data["name"]}',
                'risk_level': 'high',
                'category': 'sanctions_compliance',
                'entity_data': entity_data,
                'screening_results': screening_results,
                'created_date': datetime.utcnow().isoformat()
            }
            
            # Push to GRC systems
            grc_results = await test_environment['grc_integration'].push_compliance_updates(
                tenant_id=tenant_id,
                updates=[risk_update]
            )
            
            assert grc_results['status'] == 'success'
            assert grc_results['successful_pushes'] >= 1
            
            # Step 3: Send notifications to stakeholders
            notification_data = {
                'template_name': 'sanctions_alert',
                'recipients': ['compliance@company.com', 'risk@company.com'],
                'context': {
                    'entity_name': entity_data['name'],
                    'match_count': screening_results['total_matches'],
                    'risk_level': 'HIGH',
                    'screening_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'grc_ticket_id': grc_results.get('ticket_ids', ['N/A'])[0]
                },
                'priority': 'high',
                'channels': ['email', 'webhook']
            }
            
            notification_results = await test_environment['notifications'].send_notification(
                tenant_id=tenant_id,
                notification_data=notification_data
            )
            
            assert notification_results['status'] == 'success'
            assert notification_results['delivery_status']['email'] == 'sent'
        
        # Verify end-to-end data consistency
        assert screening_results['tenant_id'] == tenant_id
        logger.info(f"Complete sanctions workflow test passed for tenant {tenant_id}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_grc_risk_sync_notification_workflow(self, test_environment):
        """
        Test GRC risk synchronization with notification workflow:
        1. Sync risks from GRC systems
        2. Identify high-priority risks
        3. Generate automated notifications
        4. Track notification delivery
        """
        tenant_id = str(uuid.uuid4())
        
        # Step 1: Sync risks from all GRC systems
        sync_results = await test_environment['grc_integration'].sync_risk_registers(
            tenant_id=tenant_id
        )
        
        assert sync_results['status'] == 'success'
        assert sync_results['total_risks_processed'] >= 0
        
        # Step 2: Process high-priority risks for notifications
        high_priority_risks = []
        for system_result in sync_results.get('system_results', []):
            if system_result.get('high_priority_count', 0) > 0:
                high_priority_risks.extend(system_result.get('high_priority_risks', []))
        
        # Step 3: Generate notifications for high-priority risks
        if high_priority_risks:
            for risk in high_priority_risks[:5]:  # Limit to 5 for testing
                notification_data = {
                    'template_name': 'high_priority_risk_alert',
                    'recipients': ['risk@company.com', 'management@company.com'],
                    'context': {
                        'risk_title': risk.get('title', 'Unknown Risk'),
                        'risk_level': risk.get('severity', 'Unknown'),
                        'source_system': risk.get('source_system', 'Unknown'),
                        'risk_owner': risk.get('owner', 'Unassigned'),
                        'due_date': risk.get('due_date', 'Not specified')
                    },
                    'priority': 'high',
                    'channels': ['email']
                }
                
                notification_result = await test_environment['notifications'].send_notification(
                    tenant_id=tenant_id,
                    notification_data=notification_data
                )
                
                assert notification_result['status'] == 'success'
        
        logger.info(f"GRC sync notification workflow test completed for tenant {tenant_id}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_external_data_update_cascade_workflow(self, test_environment):
        """
        Test external data update cascade workflow:
        1. Update external data sources
        2. Re-screen existing entities
        3. Identify new matches
        4. Update GRC systems
        5. Send notifications for changes
        """
        tenant_id = str(uuid.uuid4())
        
        # Step 1: Update all external data sources
        update_results = await test_environment['external_data'].update_all_data_sources(
            tenant_id=tenant_id
        )
        
        assert update_results['status'] == 'success'
        assert len(update_results['update_results']) >= 1
        
        # Step 2: Simulate re-screening of existing entities
        test_entities = [
            {'name': 'Test Entity 1', 'entity_id': 'ENT001'},
            {'name': 'Test Entity 2', 'entity_id': 'ENT002'}
        ]
        
        rescreening_results = []
        for entity in test_entities:
            result = await test_environment['external_data'].screen_entity(
                tenant_id=tenant_id,
                entity_data=entity,
                screening_type='comprehensive'
            )
            rescreening_results.append(result)
        
        # Step 3: Process any new matches
        new_matches = []
        for result in rescreening_results:
            if result.get('total_matches', 0) > 0:
                new_matches.append(result)
        
        # Step 4: Update GRC systems with new findings
        if new_matches:
            grc_updates = []
            for match_result in new_matches:
                update = {
                    'type': 'risk_update',
                    'title': f'Updated Sanctions Status: {match_result["entity_name"]}',
                    'description': 'New sanctions match identified during data refresh',
                    'risk_level': 'medium',
                    'category': 'sanctions_compliance_update',
                    'screening_results': match_result
                }
                grc_updates.append(update)
            
            grc_result = await test_environment['grc_integration'].push_compliance_updates(
                tenant_id=tenant_id,
                updates=grc_updates
            )
            
            assert grc_result['status'] == 'success'
        
        logger.info(f"External data update cascade workflow test completed for tenant {tenant_id}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_notification_template_personalization_workflow(self, test_environment):
        """
        Test notification template personalization workflow:
        1. Create personalized templates
        2. Send notifications with user preferences
        3. Validate template rendering
        4. Check delivery preferences
        """
        tenant_id = str(uuid.uuid4())
        
        # Step 1: Create personalized notification template
        template_data = {
            'name': 'personalized_risk_alert',
            'subject': 'Risk Alert for {{user.first_name}} - {{risk.title}}',
            'content': '''
            Dear {{user.first_name}} {{user.last_name}},
            
            A {{risk.severity}} priority risk has been identified:
            
            Risk: {{risk.title}}
            Category: {{risk.category}}
            Owner: {{risk.owner}}
            Due Date: {{risk.due_date}}
            
            {% if user.preferences.include_details %}
            Details: {{risk.description}}
            {% endif %}
            
            Please review and take appropriate action.
            
            Best regards,
            RegulensAI Compliance System
            ''',
            'template_type': 'email',
            'language': 'en'
        }
        
        template_result = await test_environment['template_engine'].create_template(
            tenant_id=tenant_id,
            template_data=template_data
        )
        
        assert template_result['status'] == 'success'
        
        # Step 2: Send personalized notifications
        users = [
            {
                'email': 'john.doe@company.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'preferences': {'include_details': True}
            },
            {
                'email': 'jane.smith@company.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'preferences': {'include_details': False}
            }
        ]
        
        risk_data = {
            'title': 'Operational Risk - System Downtime',
            'severity': 'high',
            'category': 'operational',
            'owner': 'IT Operations',
            'due_date': '2024-02-15',
            'description': 'Critical system experiencing intermittent downtime affecting business operations.'
        }
        
        for user in users:
            notification_data = {
                'template_name': 'personalized_risk_alert',
                'recipients': [user['email']],
                'context': {
                    'user': user,
                    'risk': risk_data
                },
                'priority': 'high',
                'channels': ['email']
            }
            
            result = await test_environment['notifications'].send_notification(
                tenant_id=tenant_id,
                notification_data=notification_data
            )
            
            assert result['status'] == 'success'
            
            # Validate template rendering
            rendered_content = result.get('rendered_content', '')
            assert user['first_name'] in rendered_content
            assert risk_data['title'] in rendered_content
            
            if user['preferences']['include_details']:
                assert risk_data['description'] in rendered_content
            else:
                assert risk_data['description'] not in rendered_content
        
        logger.info(f"Notification personalization workflow test completed for tenant {tenant_id}")


class TestLoadAndPerformance:
    """
    Load testing and performance validation for RegulensAI components.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_bulk_notification_processing(self):
        """
        Test bulk notification processing with 10K+ notifications.
        Validates throughput, latency, and system stability.
        """
        tenant_id = str(uuid.uuid4())
        mock_supabase = Mock()
        
        async with NotificationDeliveryService(mock_supabase) as notification_service:
            # Generate 10,000 test notifications
            notifications = []
            for i in range(10000):
                notification = {
                    'template_name': 'bulk_test_notification',
                    'recipients': [f'user{i}@company.com'],
                    'context': {
                        'user_id': f'USER{i:05d}',
                        'message': f'Bulk test notification {i}',
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    'priority': 'normal',
                    'channels': ['email']
                }
                notifications.append(notification)
            
            # Measure processing time
            start_time = time.time()
            
            # Process notifications in batches
            batch_size = 100
            results = []
            
            for i in range(0, len(notifications), batch_size):
                batch = notifications[i:i + batch_size]
                
                batch_result = await notification_service.send_bulk_notifications(
                    tenant_id=tenant_id,
                    notifications=batch
                )
                
                results.append(batch_result)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Validate performance metrics
            total_processed = sum(r.get('successful_deliveries', 0) for r in results)
            throughput = total_processed / processing_time  # notifications per second
            
            assert total_processed >= 9500  # 95% success rate minimum
            assert throughput >= 100  # Minimum 100 notifications per second
            assert processing_time <= 120  # Maximum 2 minutes for 10K notifications
            
            logger.info(f"Bulk notification test: {total_processed} notifications in {processing_time:.2f}s "
                       f"(throughput: {throughput:.2f} notifications/sec)")
    
    @pytest.mark.asyncio
    @pytest.mark.load_test
    async def test_concurrent_external_data_screening(self):
        """
        Test concurrent external data screening performance.
        Validates system behavior under high concurrent load.
        """
        tenant_id = str(uuid.uuid4())
        mock_supabase = Mock()
        
        async with ExternalDataIntegrationService(mock_supabase) as ext_data_service:
            # Generate test entities for concurrent screening
            test_entities = []
            for i in range(100):
                entity = {
                    'name': f'Test Entity {i}',
                    'entity_id': f'ENT{i:03d}',
                    'entity_type': 'corporation',
                    'address': f'{i} Test Street, Test City'
                }
                test_entities.append(entity)
            
            # Create concurrent screening tasks
            async def screen_entity(entity):
                return await ext_data_service.screen_entity(
                    tenant_id=tenant_id,
                    entity_data=entity,
                    screening_type='comprehensive'
                )
            
            start_time = time.time()
            
            # Execute concurrent screenings
            tasks = [screen_entity(entity) for entity in test_entities]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Analyze results
            successful_screenings = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
            error_count = len(results) - len(successful_screenings)
            
            # Validate performance
            assert len(successful_screenings) >= 95  # 95% success rate
            assert error_count <= 5  # Maximum 5% error rate
            assert processing_time <= 60  # Maximum 1 minute for 100 concurrent screenings
            
            avg_response_time = processing_time / len(test_entities)
            assert avg_response_time <= 1.0  # Average response time under 1 second
            
            logger.info(f"Concurrent screening test: {len(successful_screenings)} successful screenings "
                       f"in {processing_time:.2f}s (avg: {avg_response_time:.3f}s per screening)")


class TestFailoverScenarios:
    """
    Test system behavior during external dependency failures.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.failover_test
    async def test_external_api_failover(self):
        """
        Test system behavior when external APIs are unavailable.
        Validates graceful degradation and error handling.
        """
        tenant_id = str(uuid.uuid4())
        mock_supabase = Mock()
        
        async with ExternalDataIntegrationService(mock_supabase) as ext_data_service:
            entity_data = {
                'name': 'Test Entity',
                'entity_type': 'corporation'
            }
            
            # Simulate API failures for different providers
            with patch('aiohttp.ClientSession.get') as mock_get:
                with patch('aiohttp.ClientSession.post') as mock_post:
                    # Simulate network timeout
                    mock_get.side_effect = asyncio.TimeoutError()
                    mock_post.side_effect = asyncio.TimeoutError()
                    
                    result = await ext_data_service.screen_entity(
                        tenant_id=tenant_id,
                        entity_data=entity_data,
                        screening_type='comprehensive'
                    )
                    
                    # System should handle failures gracefully
                    assert result['status'] in ['partial_success', 'error']
                    assert 'error_details' in result
                    assert result.get('failed_providers', 0) > 0
                    
                    # Should still return available data
                    assert 'provider_results' in result
            
            logger.info("External API failover test completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.failover_test
    async def test_database_connection_failover(self):
        """
        Test system behavior during database connectivity issues.
        """
        tenant_id = str(uuid.uuid4())
        
        # Simulate database connection failure
        mock_supabase = Mock()
        mock_supabase.table.side_effect = Exception("Database connection failed")
        
        async with NotificationDeliveryService(mock_supabase) as notification_service:
            notification_data = {
                'template_name': 'test_notification',
                'recipients': ['test@company.com'],
                'context': {'message': 'Test message'},
                'priority': 'normal',
                'channels': ['email']
            }
            
            result = await notification_service.send_notification(
                tenant_id=tenant_id,
                notification_data=notification_data
            )
            
            # Should handle database failures gracefully
            assert result['status'] == 'error'
            assert 'database' in result.get('error', '').lower()
            
            logger.info("Database failover test completed successfully")
