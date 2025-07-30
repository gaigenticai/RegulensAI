"""
Unit tests for notification delivery system.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from core_infra.services.notifications.delivery import (
    EmailChannel,
    SMSChannel,
    WebhookChannel,
    SlackChannel,
    TeamsChannel,
    NotificationDeliveryService,
    send_email,
    send_sms,
    send_webhook,
    send_slack,
    send_teams
)
from core_infra.exceptions import ExternalServiceException


class TestEmailChannel:
    """Test email notification channel."""
    
    @pytest.fixture
    def email_channel(self):
        """Create email channel for testing."""
        with patch('core_infra.services.notifications.delivery.get_settings') as mock_settings:
            mock_settings.return_value.smtp_host = "smtp.test.com"
            mock_settings.return_value.smtp_port = 587
            mock_settings.return_value.smtp_username = "test@test.com"
            mock_settings.return_value.smtp_password = Mock()
            mock_settings.return_value.smtp_password.get_secret_value.return_value = "password"
            mock_settings.return_value.email_from = "test@test.com"
            mock_settings.return_value.email_from_name = "Test System"
            return EmailChannel()
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, email_channel):
        """Test successful email sending."""
        notification = {
            'recipient': 'user@test.com',
            'subject': 'Test Subject',
            'text_content': 'Test message',
            'html_content': '<p>Test message</p>'
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await email_channel.send(notification)
            
            assert result['status'] == 'sent'
            assert result['channel'] == 'email'
            assert result['recipient'] == 'user@test.com'
            assert 'sent_at' in result
            
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_failure(self, email_channel):
        """Test email sending failure."""
        notification = {
            'recipient': 'user@test.com',
            'subject': 'Test Subject',
            'text_content': 'Test message'
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")
            
            result = await email_channel.send(notification)
            
            assert result['status'] == 'failed'
            assert result['channel'] == 'email'
            assert 'error' in result
            assert 'failed_at' in result


class TestSMSChannel:
    """Test SMS notification channel."""
    
    @pytest.fixture
    def sms_channel(self):
        """Create SMS channel for testing."""
        with patch('core_infra.services.notifications.delivery.get_settings') as mock_settings:
            mock_settings.return_value.twilio_account_sid = "test_sid"
            mock_settings.return_value.twilio_auth_token = "test_token"
            mock_settings.return_value.twilio_from_number = "+1234567890"
            
            with patch('core_infra.services.notifications.delivery.TwilioClient') as mock_client:
                channel = SMSChannel()
                channel.client = mock_client.return_value
                return channel
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self, sms_channel):
        """Test successful SMS sending."""
        notification = {
            'to_number': '+1987654321',
            'message': 'Test SMS message'
        }
        
        mock_message = Mock()
        mock_message.sid = 'test_message_sid'
        sms_channel.client.messages.create.return_value = mock_message
        
        result = await sms_channel.send(notification)
        
        assert result['status'] == 'sent'
        assert result['channel'] == 'sms'
        assert result['recipient'] == '+1987654321'
        assert result['message_sid'] == 'test_message_sid'
        assert 'sent_at' in result
        
        sms_channel.client.messages.create.assert_called_once_with(
            body='Test SMS message',
            from_='+1234567890',
            to='+1987654321'
        )
    
    @pytest.mark.asyncio
    async def test_send_sms_truncation(self, sms_channel):
        """Test SMS message truncation for long messages."""
        long_message = "A" * 1700  # Longer than 1600 character limit
        notification = {
            'to_number': '+1987654321',
            'message': long_message
        }
        
        mock_message = Mock()
        mock_message.sid = 'test_message_sid'
        sms_channel.client.messages.create.return_value = mock_message
        
        result = await sms_channel.send(notification)
        
        assert result['status'] == 'sent'
        
        # Check that message was truncated
        call_args = sms_channel.client.messages.create.call_args
        sent_message = call_args[1]['body']
        assert len(sent_message) == 1600
        assert sent_message.endswith("...")


class TestWebhookChannel:
    """Test webhook notification channel."""
    
    @pytest.fixture
    def webhook_channel(self):
        """Create webhook channel for testing."""
        return WebhookChannel()
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self, webhook_channel):
        """Test successful webhook sending."""
        notification = {
            'webhook_url': 'https://api.test.com/webhook',
            'payload': {'message': 'test'},
            'headers': {'Authorization': 'Bearer token'}
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='OK')
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await webhook_channel.send(notification)
            
            assert result['status'] == 'sent'
            assert result['channel'] == 'webhook'
            assert result['webhook_url'] == 'https://api.test.com/webhook'
            assert result['response_status'] == 200
            assert 'sent_at' in result


class TestNotificationDeliveryService:
    """Test main notification delivery service."""
    
    @pytest.fixture
    def delivery_service(self):
        """Create notification delivery service for testing."""
        return NotificationDeliveryService()
    
    @pytest.mark.asyncio
    async def test_send_multi_channel_notification(self, delivery_service):
        """Test sending notification through multiple channels."""
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['email', 'sms'],
            'recipient': 'user@test.com',
            'to_number': '+1987654321',
            'subject': 'Test Notification',
            'text_content': 'Test message'
        }
        
        # Mock database operations
        with patch('core_infra.services.notifications.delivery.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()
            
            # Mock channel sending
            with patch.object(delivery_service.channels['email'], 'send') as mock_email:
                with patch.object(delivery_service.channels['sms'], 'send') as mock_sms:
                    mock_email.return_value = {'status': 'sent', 'channel': 'email'}
                    mock_sms.return_value = {'status': 'sent', 'channel': 'sms'}
                    
                    result = await delivery_service.send_notification(notification)
                    
                    assert result['overall_status'] == 'delivered'
                    assert 'email' in result['delivery_results']
                    assert 'sms' in result['delivery_results']
                    assert result['delivery_results']['email']['status'] == 'sent'
                    assert result['delivery_results']['sms']['status'] == 'sent'
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, delivery_service):
        """Test retry logic for failed notifications."""
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['email'],
            'recipient': 'user@test.com',
            'subject': 'Test Notification',
            'text_content': 'Test message'
        }
        
        with patch('core_infra.services.notifications.delivery.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()
            
            # Mock channel to fail twice then succeed
            with patch.object(delivery_service.channels['email'], 'send') as mock_email:
                mock_email.side_effect = [
                    {'status': 'failed', 'error': 'Temporary failure'},
                    {'status': 'failed', 'error': 'Temporary failure'},
                    {'status': 'sent', 'channel': 'email'}
                ]
                
                # Mock sleep to speed up test
                with patch('asyncio.sleep'):
                    result = await delivery_service.send_notification(notification)
                    
                    assert result['overall_status'] == 'delivered'
                    assert mock_email.call_count == 3


class TestConvenienceFunctions:
    """Test convenience functions for sending notifications."""
    
    @pytest.mark.asyncio
    async def test_send_email_convenience(self):
        """Test send_email convenience function."""
        with patch('core_infra.services.notifications.delivery.notification_service') as mock_service:
            mock_service.send_notification = AsyncMock(return_value={'status': 'sent'})
            
            result = await send_email(
                recipient='user@test.com',
                subject='Test Subject',
                content='Test content',
                html_content='<p>Test content</p>'
            )
            
            assert result['status'] == 'sent'
            mock_service.send_notification.assert_called_once()
            
            call_args = mock_service.send_notification.call_args[0][0]
            assert call_args['channels'] == ['email']
            assert call_args['recipient'] == 'user@test.com'
            assert call_args['subject'] == 'Test Subject'


class TestNotificationTemplateEngine:
    """Test notification template engine."""

    @pytest.fixture
    def template_engine(self):
        """Create template engine for testing."""
        from core_infra.services.notifications.template_engine import NotificationTemplateEngine
        return NotificationTemplateEngine()

    @pytest.mark.asyncio
    async def test_render_default_template(self, template_engine):
        """Test rendering default template."""
        variables = {
            'title': 'Test Alert',
            'description': 'Test alert description',
            'severity': 'high',
            'alert_type': 'compliance',
            'created_at': '2024-01-29T10:00:00Z'
        }

        with patch('core_infra.services.notifications.template_engine.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.fetchrow = AsyncMock(return_value=None)

            result = await template_engine.render_template(
                template_name='alert_created',
                template_type='email',
                language='en',
                variables=variables
            )

            assert 'subject' in result
            assert 'text_content' in result
            assert 'Test Alert' in result['subject']
            assert 'Test alert description' in result['text_content']

    @pytest.mark.asyncio
    async def test_create_custom_template(self, template_engine):
        """Test creating custom template."""
        tenant_id = str(uuid.uuid4())

        with patch('core_infra.services.notifications.template_engine.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()

            template_id = await template_engine.create_custom_template(
                tenant_id=tenant_id,
                template_name='custom_alert',
                template_type='email',
                language='en',
                subject_template='Custom Alert: {{ title }}',
                text_template='Custom alert content: {{ description }}',
                metadata={'custom': True}
            )

            assert template_id.startswith(tenant_id)
            mock_db.return_value.__aenter__.return_value.execute.assert_called_once()


class TestNotificationPreferences:
    """Test notification preferences management."""

    @pytest.fixture
    def preferences_manager(self):
        """Create preferences manager for testing."""
        from core_infra.services.notifications.preferences import NotificationPreferencesManager
        return NotificationPreferencesManager()

    @pytest.mark.asyncio
    async def test_get_user_preferences_default(self, preferences_manager):
        """Test getting default user preferences."""
        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        with patch('core_infra.services.notifications.preferences.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.fetchrow = AsyncMock(return_value=None)
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()

            preferences = await preferences_manager.get_user_preferences(user_id, tenant_id)

            assert preferences['user_id'] == user_id
            assert preferences['tenant_id'] == tenant_id
            assert 'preferences' in preferences
            assert 'alert' in preferences['preferences']

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, preferences_manager):
        """Test updating user preferences."""
        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        new_preferences = {
            'alert': {
                'channels': ['email', 'sms'],
                'frequency': 'immediate'
            },
            'compliance_violation': {
                'channels': ['email'],
                'frequency': 'immediate'
            }
        }

        with patch('core_infra.services.notifications.preferences.get_database') as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = AsyncMock()

            result = await preferences_manager.update_user_preferences(
                user_id=user_id,
                tenant_id=tenant_id,
                preferences=new_preferences,
                language='en',
                timezone='UTC'
            )

            assert result is True
            mock_db.return_value.__aenter__.return_value.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_determine_notification_routing(self, preferences_manager):
        """Test notification routing determination."""
        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        mock_user_prefs = {
            'preferences': {
                'alert': {
                    'channels': ['email', 'sms'],
                    'frequency': 'immediate'
                }
            },
            'language': 'en',
            'timezone': 'UTC'
        }

        mock_tenant_prefs = {
            'routing_rules': [],
            'escalation_matrix': {}
        }

        with patch.object(preferences_manager, 'get_user_preferences', return_value=mock_user_prefs):
            with patch.object(preferences_manager, 'get_tenant_preferences', return_value=mock_tenant_prefs):
                routing = await preferences_manager.determine_notification_routing(
                    notification_type='alert',
                    severity='high',
                    user_id=user_id,
                    tenant_id=tenant_id
                )

                assert routing['channels'] == ['email', 'sms']
                assert routing['frequency'] == 'immediate'
                assert routing['language'] == 'en'
                assert routing['timezone'] == 'UTC'


class TestBulkNotifications:
    """Test bulk notification functionality."""

    @pytest.mark.asyncio
    async def test_send_bulk_notifications(self):
        """Test sending bulk notifications."""
        from core_infra.services.notifications.delivery import send_bulk_notifications

        notifications = [
            {
                'channels': ['email'],
                'recipient': f'user{i}@test.com',
                'subject': f'Test Subject {i}',
                'text_content': f'Test content {i}'
            }
            for i in range(5)
        ]

        with patch('core_infra.services.notifications.delivery.notification_service') as mock_service:
            mock_service.send_notification = AsyncMock(return_value={'overall_status': 'delivered'})

            result = await send_bulk_notifications(notifications, batch_size=2)

            assert result['status'] == 'completed'
            assert result['total_notifications'] == 5
            assert result['successful_deliveries'] == 5
            assert result['failed_deliveries'] == 0
            assert result['success_rate'] == 100.0
            assert len(result['batch_results']) == 3  # 5 notifications in batches of 2

    @pytest.mark.asyncio
    async def test_send_templated_notification(self):
        """Test sending templated notifications."""
        from core_infra.services.notifications.delivery import send_templated_notification

        template_variables = {
            'title': 'Test Alert',
            'description': 'Test description',
            'severity': 'high'
        }

        recipients = ['user1@test.com', 'user2@test.com']

        with patch('core_infra.services.notifications.template_engine.template_engine') as mock_template:
            mock_template.render_template = AsyncMock(return_value={
                'subject': 'Test Alert',
                'text_content': 'Test description',
                'html_content': '<p>Test description</p>'
            })

            with patch('core_infra.services.notifications.delivery.send_bulk_notifications') as mock_bulk:
                mock_bulk.return_value = {'status': 'completed', 'successful_deliveries': 2}

                result = await send_templated_notification(
                    template_name='alert_created',
                    template_variables=template_variables,
                    recipients=recipients,
                    channels=['email'],
                    language='en'
                )

                assert result['status'] == 'completed'
                mock_template.render_template.assert_called_once()
                mock_bulk.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_sms_convenience(self):
        """Test send_sms convenience function."""
        with patch('core_infra.services.notifications.delivery.notification_service') as mock_service:
            mock_service.send_notification = AsyncMock(return_value={'status': 'sent'})
            
            result = await send_sms(
                to_number='+1987654321',
                message='Test SMS'
            )
            
            assert result['status'] == 'sent'
            mock_service.send_notification.assert_called_once()
            
            call_args = mock_service.send_notification.call_args[0][0]
            assert call_args['channels'] == ['sms']
            assert call_args['to_number'] == '+1987654321'
            assert call_args['message'] == 'Test SMS'
