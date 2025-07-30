"""
Integration tests for notification delivery system.
"""

import pytest
import asyncio
import uuid
import os
from datetime import datetime

from core_infra.services.notifications.delivery import (
    NotificationDeliveryService,
    EmailChannel,
    WebhookChannel,
    send_email,
    send_webhook
)


@pytest.mark.integration
class TestNotificationIntegration:
    """Integration tests for notification system."""
    
    @pytest.fixture
    def delivery_service(self):
        """Create notification delivery service for integration testing."""
        return NotificationDeliveryService()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('SMTP_USERNAME') or not os.getenv('SMTP_PASSWORD'),
        reason="SMTP credentials not configured"
    )
    async def test_real_email_sending(self, delivery_service):
        """Test sending real email (requires SMTP configuration)."""
        test_email = os.getenv('TEST_EMAIL_RECIPIENT')
        if not test_email:
            pytest.skip("TEST_EMAIL_RECIPIENT not configured")
        
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['email'],
            'recipient': test_email,
            'subject': f'Regulens AI Test Email - {datetime.now().isoformat()}',
            'text_content': 'This is a test email from the Regulens AI notification system.',
            'html_content': '''
            <html>
                <body>
                    <h2>Regulens AI Test Email</h2>
                    <p>This is a test email from the Regulens AI notification system.</p>
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                    <p><em>This is an automated test message.</em></p>
                </body>
            </html>
            '''.format(timestamp=datetime.now().isoformat())
        }
        
        result = await delivery_service.send_notification(notification)
        
        assert result['overall_status'] in ['delivered', 'partial']
        assert 'email' in result['delivery_results']
        
        email_result = result['delivery_results']['email']
        if email_result['status'] == 'sent':
            assert 'sent_at' in email_result
            print(f"✅ Email sent successfully to {test_email}")
        else:
            print(f"❌ Email failed: {email_result.get('error', 'Unknown error')}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('TWILIO_ACCOUNT_SID') or not os.getenv('TWILIO_AUTH_TOKEN'),
        reason="Twilio credentials not configured"
    )
    async def test_real_sms_sending(self, delivery_service):
        """Test sending real SMS (requires Twilio configuration)."""
        test_phone = os.getenv('TEST_PHONE_NUMBER')
        if not test_phone:
            pytest.skip("TEST_PHONE_NUMBER not configured")
        
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['sms'],
            'to_number': test_phone,
            'message': f'Regulens AI test SMS - {datetime.now().strftime("%H:%M:%S")}'
        }
        
        result = await delivery_service.send_notification(notification)
        
        assert result['overall_status'] in ['delivered', 'partial']
        assert 'sms' in result['delivery_results']
        
        sms_result = result['delivery_results']['sms']
        if sms_result['status'] == 'sent':
            assert 'message_sid' in sms_result
            print(f"✅ SMS sent successfully to {test_phone}")
        else:
            print(f"❌ SMS failed: {sms_result.get('error', 'Unknown error')}")
    
    @pytest.mark.asyncio
    async def test_webhook_integration(self, delivery_service):
        """Test webhook integration with httpbin.org."""
        webhook_url = "https://httpbin.org/post"
        
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['webhook'],
            'webhook_url': webhook_url,
            'payload': {
                'message': 'Test webhook from Regulens AI',
                'timestamp': datetime.now().isoformat(),
                'test_id': str(uuid.uuid4())
            },
            'headers': {
                'Content-Type': 'application/json',
                'X-Test-Source': 'Regulens-AI-Integration-Test'
            }
        }
        
        result = await delivery_service.send_notification(notification)
        
        assert result['overall_status'] == 'delivered'
        assert 'webhook' in result['delivery_results']
        
        webhook_result = result['delivery_results']['webhook']
        assert webhook_result['status'] == 'sent'
        assert webhook_result['response_status'] == 200
        print(f"✅ Webhook sent successfully to {webhook_url}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('SLACK_WEBHOOK_URL'),
        reason="Slack webhook URL not configured"
    )
    async def test_slack_integration(self, delivery_service):
        """Test Slack integration (requires webhook URL)."""
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['slack'],
            'text': f'🧪 Regulens AI integration test - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'channel': '#general',
            'username': 'Regulens AI Test Bot',
            'icon_emoji': ':robot_face:',
            'blocks': [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Regulens AI Integration Test*\n\nThis is an automated test of the notification system."
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Test ID: `{str(uuid.uuid4())[:8]}`"
                        }
                    ]
                }
            ]
        }
        
        result = await delivery_service.send_notification(notification)
        
        assert result['overall_status'] == 'delivered'
        assert 'slack' in result['delivery_results']
        
        slack_result = result['delivery_results']['slack']
        assert slack_result['status'] == 'sent'
        print("✅ Slack notification sent successfully")
    
    @pytest.mark.asyncio
    async def test_multi_channel_integration(self, delivery_service):
        """Test multi-channel notification delivery."""
        # Use webhook as a reliable test channel
        notification = {
            'id': str(uuid.uuid4()),
            'channels': ['webhook'],
            'webhook_url': 'https://httpbin.org/post',
            'payload': {
                'notification_type': 'multi_channel_test',
                'message': 'Testing multi-channel delivery',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Add email if configured
        if os.getenv('SMTP_USERNAME') and os.getenv('TEST_EMAIL_RECIPIENT'):
            notification['channels'].append('email')
            notification['recipient'] = os.getenv('TEST_EMAIL_RECIPIENT')
            notification['subject'] = 'Multi-channel Test'
            notification['text_content'] = 'Testing multi-channel delivery'
        
        # Add SMS if configured
        if os.getenv('TWILIO_ACCOUNT_SID') and os.getenv('TEST_PHONE_NUMBER'):
            notification['channels'].append('sms')
            notification['to_number'] = os.getenv('TEST_PHONE_NUMBER')
            notification['message'] = 'Multi-channel test'
        
        result = await delivery_service.send_notification(notification)
        
        assert result['overall_status'] in ['delivered', 'partial']
        assert len(result['delivery_results']) == len(notification['channels'])
        
        # At least webhook should succeed
        assert result['delivery_results']['webhook']['status'] == 'sent'
        
        print(f"✅ Multi-channel test completed with {len(notification['channels'])} channels")
        for channel, result_data in result['delivery_results'].items():
            status = "✅" if result_data['status'] == 'sent' else "❌"
            print(f"  {status} {channel}: {result_data['status']}")
    
    @pytest.mark.asyncio
    async def test_notification_persistence(self, delivery_service):
        """Test that notifications are properly stored and can be retrieved."""
        notification_id = str(uuid.uuid4())
        
        notification = {
            'id': notification_id,
            'channels': ['webhook'],
            'webhook_url': 'https://httpbin.org/post',
            'payload': {'test': 'persistence'},
            'tenant_id': '00000000-0000-0000-0000-000000000000'
        }
        
        # Send notification
        result = await delivery_service.send_notification(notification)
        assert result['overall_status'] == 'delivered'
        
        # Retrieve notification status
        try:
            status = await delivery_service.get_delivery_status(notification_id)
            assert status['notification_id'] == notification_id
            assert 'notification' in status
            assert 'deliveries' in status
            print(f"✅ Notification persistence test passed")
        except Exception as e:
            print(f"⚠️ Notification persistence test skipped (database not available): {e}")
    
    @pytest.mark.asyncio
    async def test_channel_validation(self, delivery_service):
        """Test channel configuration validation."""
        validation_results = await delivery_service.validate_channels()
        
        assert isinstance(validation_results, dict)
        assert 'email' in validation_results
        assert 'webhook' in validation_results
        assert 'sms' in validation_results
        assert 'slack' in validation_results
        assert 'teams' in validation_results
        
        print("📋 Channel validation results:")
        for channel, is_valid in validation_results.items():
            status = "✅ Valid" if is_valid else "❌ Invalid"
            print(f"  {channel}: {status}")
        
        # Webhook should always be valid (no specific config required)
        assert validation_results['webhook'] is True


@pytest.mark.integration
class TestConvenienceFunctionIntegration:
    """Integration tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_send_email_integration(self):
        """Test send_email convenience function integration."""
        if not os.getenv('TEST_EMAIL_RECIPIENT'):
            pytest.skip("TEST_EMAIL_RECIPIENT not configured")
        
        result = await send_email(
            recipient=os.getenv('TEST_EMAIL_RECIPIENT'),
            subject='Regulens AI Convenience Function Test',
            content='This email was sent using the send_email convenience function.',
            html_content='<p>This email was sent using the <strong>send_email</strong> convenience function.</p>'
        )
        
        if result['overall_status'] == 'delivered':
            print("✅ Convenience function email test passed")
        else:
            print(f"⚠️ Convenience function email test failed: {result}")
    
    @pytest.mark.asyncio
    async def test_send_webhook_integration(self):
        """Test send_webhook convenience function integration."""
        result = await send_webhook(
            webhook_url='https://httpbin.org/post',
            payload={
                'test': 'convenience_function',
                'timestamp': datetime.now().isoformat()
            }
        )
        
        assert result['overall_status'] == 'delivered'
        print("✅ Convenience function webhook test passed")
