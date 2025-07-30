"""
Regulens AI - Notification Delivery System
Enterprise-grade notification delivery with multiple channels and reliability features.
"""

import asyncio
import smtplib
import ssl
import uuid
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiohttp
import structlog
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import ExternalServiceException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class NotificationChannel:
    """Base class for notification channels."""
    
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        self.is_enabled = True
        self.retry_count = 3
        self.retry_delay = 5  # seconds
    
    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification through this channel."""
        raise NotImplementedError
    
    async def validate_config(self) -> bool:
        """Validate channel configuration."""
        raise NotImplementedError

class EmailChannel(NotificationChannel):
    """Email notification channel using SMTP."""
    
    def __init__(self):
        super().__init__("email")
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password.get_secret_value() if settings.smtp_password else None
        self.email_from = settings.email_from
        self.email_from_name = settings.email_from_name
    
    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send email notification."""
        try:
            # Prepare email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification['subject']
            msg['From'] = f"{self.email_from_name} <{self.email_from}>"
            msg['To'] = notification['recipient']
            
            # Add text content
            if notification.get('text_content'):
                text_part = MIMEText(notification['text_content'], 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            if notification.get('html_content'):
                html_part = MIMEText(notification['html_content'], 'html')
                msg.attach(html_part)
            
            # Add attachments if any
            if notification.get('attachments'):
                for attachment in notification['attachments']:
                    await self._add_attachment(msg, attachment)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {notification['recipient']}")
            return {
                'status': 'sent',
                'channel': 'email',
                'recipient': notification['recipient'],
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return {
                'status': 'failed',
                'channel': 'email',
                'recipient': notification['recipient'],
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to add attachment {attachment.get('filename')}: {e}")
    
    async def validate_config(self) -> bool:
        """Validate email configuration."""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
            return True
        except Exception as e:
            logger.error(f"Email configuration validation failed: {e}")
            return False

class WebhookChannel(NotificationChannel):
    """Webhook notification channel for external integrations."""
    
    def __init__(self):
        super().__init__("webhook")
        self.timeout = 30  # seconds
    
    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook notification."""
        try:
            webhook_url = notification['webhook_url']
            payload = notification.get('payload', {})
            headers = notification.get('headers', {'Content-Type': 'application/json'})
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        logger.info(f"Webhook sent successfully to {webhook_url}")
                        return {
                            'status': 'sent',
                            'channel': 'webhook',
                            'webhook_url': webhook_url,
                            'response_status': response.status,
                            'sent_at': datetime.utcnow().isoformat()
                        }
                    else:
                        logger.error(f"Webhook failed with status {response.status}: {response_text}")
                        return {
                            'status': 'failed',
                            'channel': 'webhook',
                            'webhook_url': webhook_url,
                            'response_status': response.status,
                            'error': response_text,
                            'failed_at': datetime.utcnow().isoformat()
                        }
                        
        except Exception as e:
            logger.error(f"Webhook sending failed: {e}")
            return {
                'status': 'failed',
                'channel': 'webhook',
                'webhook_url': notification.get('webhook_url', 'unknown'),
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def validate_config(self) -> bool:
        """Validate webhook configuration."""
        # Webhook validation would be endpoint-specific
        return True

class SlackChannel(NotificationChannel):
    """Slack notification channel."""
    
    def __init__(self):
        super().__init__("slack")
        self.webhook_url = getattr(settings, 'slack_webhook_url', None)
    
    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack notification."""
        try:
            if not self.webhook_url:
                raise ExternalServiceException("Slack webhook URL not configured")
            
            payload = {
                'text': notification.get('text', ''),
                'channel': notification.get('channel', '#general'),
                'username': notification.get('username', 'Regulens AI'),
                'icon_emoji': notification.get('icon', ':robot_face:')
            }
            
            # Add rich formatting if provided
            if notification.get('blocks'):
                payload['blocks'] = notification['blocks']
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                        return {
                            'status': 'sent',
                            'channel': 'slack',
                            'sent_at': datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Slack notification failed: {error_text}")
                        return {
                            'status': 'failed',
                            'channel': 'slack',
                            'error': error_text,
                            'failed_at': datetime.utcnow().isoformat()
                        }
                        
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return {
                'status': 'failed',
                'channel': 'slack',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }
    
    async def validate_config(self) -> bool:
        """Validate Slack configuration."""
        return self.webhook_url is not None

class SMSChannel(NotificationChannel):
    """SMS notification channel using Twilio."""

    def __init__(self):
        super().__init__("sms")
        self.account_sid = getattr(settings, 'twilio_account_sid', None)
        self.auth_token = getattr(settings, 'twilio_auth_token', None)
        self.from_number = getattr(settings, 'twilio_from_number', None)
        self.client = None

        if self.account_sid and self.auth_token:
            try:
                self.client = TwilioClient(self.account_sid, self.auth_token)
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS notification."""
        try:
            if not self.client:
                raise ExternalServiceException("Twilio client not configured")

            to_number = notification['to_number']
            message_body = notification.get('message', notification.get('text_content', ''))

            # Truncate message if too long (SMS limit is 1600 characters)
            if len(message_body) > 1600:
                message_body = message_body[:1597] + "..."

            # Send SMS using Twilio
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=to_number
            )

            logger.info(f"SMS sent successfully to {to_number}, SID: {message.sid}")
            return {
                'status': 'sent',
                'channel': 'sms',
                'recipient': to_number,
                'message_sid': message.sid,
                'sent_at': datetime.utcnow().isoformat()
            }

        except TwilioException as e:
            logger.error(f"Twilio SMS sending failed: {e}")
            return {
                'status': 'failed',
                'channel': 'sms',
                'recipient': notification.get('to_number', 'unknown'),
                'error': str(e),
                'error_code': getattr(e, 'code', None),
                'failed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return {
                'status': 'failed',
                'channel': 'sms',
                'recipient': notification.get('to_number', 'unknown'),
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }

    async def validate_config(self) -> bool:
        """Validate SMS configuration."""
        try:
            if not self.client:
                return False

            # Test by fetching account info
            account = self.client.api.accounts(self.account_sid).fetch()
            return account.status == 'active'
        except Exception as e:
            logger.error(f"SMS configuration validation failed: {e}")
            return False

class TeamsChannel(NotificationChannel):
    """Microsoft Teams notification channel."""

    def __init__(self):
        super().__init__("teams")
        self.webhook_url = getattr(settings, 'teams_webhook_url', None)

    async def send(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send Teams notification."""
        try:
            if not self.webhook_url:
                raise ExternalServiceException("Teams webhook URL not configured")

            # Create Teams message card format
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": notification.get('color', '0076D7'),
                "summary": notification.get('subject', 'Regulens AI Notification'),
                "sections": [{
                    "activityTitle": notification.get('title', 'Regulens AI'),
                    "activitySubtitle": notification.get('subtitle', ''),
                    "activityImage": notification.get('image_url', ''),
                    "text": notification.get('text', ''),
                    "markdown": True
                }]
            }

            # Add action buttons if provided
            if notification.get('actions'):
                payload['potentialAction'] = notification['actions']

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        logger.info("Teams notification sent successfully")
                        return {
                            'status': 'sent',
                            'channel': 'teams',
                            'sent_at': datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Teams notification failed: {error_text}")
                        return {
                            'status': 'failed',
                            'channel': 'teams',
                            'error': error_text,
                            'failed_at': datetime.utcnow().isoformat()
                        }

        except Exception as e:
            logger.error(f"Teams notification failed: {e}")
            return {
                'status': 'failed',
                'channel': 'teams',
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            }

    async def validate_config(self) -> bool:
        """Validate Teams configuration."""
        return self.webhook_url is not None

class NotificationDeliveryService:
    """Main notification delivery service with multiple channels and reliability features."""
    
    def __init__(self):
        self.channels = {
            'email': EmailChannel(),
            'webhook': WebhookChannel(),
            'slack': SlackChannel(),
            'sms': SMSChannel(),
            'teams': TeamsChannel()
        }
        self.max_retries = 3
        self.retry_delays = [5, 15, 60]  # seconds
    
    async def send_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification through specified channels with retry logic.
        
        Args:
            notification: Notification data including channels, content, and recipients
            
        Returns:
            Delivery report with status for each channel
        """
        try:
            notification_id = notification.get('id', str(uuid.uuid4()))
            channels = notification.get('channels', ['email'])
            
            # Store notification in database
            await self._store_notification(notification_id, notification)
            
            delivery_results = {}
            
            # Send through each specified channel
            for channel_name in channels:
                if channel_name in self.channels:
                    channel = self.channels[channel_name]
                    
                    if channel.is_enabled:
                        result = await self._send_with_retry(channel, notification)
                        delivery_results[channel_name] = result
                        
                        # Update delivery status in database
                        await self._update_delivery_status(notification_id, channel_name, result)
                    else:
                        delivery_results[channel_name] = {
                            'status': 'skipped',
                            'reason': 'channel_disabled'
                        }
                else:
                    delivery_results[channel_name] = {
                        'status': 'failed',
                        'error': f'Unknown channel: {channel_name}'
                    }
            
            # Generate delivery report
            report = {
                'notification_id': notification_id,
                'delivery_results': delivery_results,
                'overall_status': self._determine_overall_status(delivery_results),
                'delivered_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Notification {notification_id} delivery completed: {report['overall_status']}")
            return report
            
        except Exception as e:
            logger.error(f"Notification delivery failed: {e}")
            raise ExternalServiceException(f"Notification delivery failed: {e}")
    
    async def _send_with_retry(self, channel: NotificationChannel, 
                              notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = await channel.send(notification)
                
                if result['status'] == 'sent':
                    return result
                else:
                    last_error = result.get('error', 'Unknown error')
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {channel.channel_type}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                await asyncio.sleep(delay)
        
        # All retries failed
        return {
            'status': 'failed',
            'channel': channel.channel_type,
            'error': last_error,
            'attempts': self.max_retries,
            'failed_at': datetime.utcnow().isoformat()
        }
    
    async def _store_notification(self, notification_id: str, notification: Dict[str, Any]):
        """Store notification in database for tracking."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO notifications (
                        id, tenant_id, notification_type, subject, content,
                        channels, recipients, metadata, status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                    uuid.UUID(notification_id),
                    uuid.UUID(notification.get('tenant_id', '00000000-0000-0000-0000-000000000000')),
                    notification.get('type', 'general'),
                    notification.get('subject', ''),
                    notification.get('content', ''),
                    notification.get('channels', []),
                    notification.get('recipients', []),
                    notification.get('metadata', {}),
                    'pending'
                )
        except Exception as e:
            logger.error(f"Failed to store notification {notification_id}: {e}")
    
    async def _update_delivery_status(self, notification_id: str, channel: str, 
                                    result: Dict[str, Any]):
        """Update delivery status in database."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO notification_deliveries (
                        id, notification_id, channel, status, delivered_at,
                        error_message, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(notification_id),
                    channel,
                    result['status'],
                    datetime.utcnow() if result['status'] == 'sent' else None,
                    result.get('error'),
                    result
                )
        except Exception as e:
            logger.error(f"Failed to update delivery status for {notification_id}: {e}")
    
    def _determine_overall_status(self, delivery_results: Dict[str, Dict]) -> str:
        """Determine overall delivery status."""
        if not delivery_results:
            return 'failed'
        
        statuses = [result['status'] for result in delivery_results.values()]
        
        if all(status == 'sent' for status in statuses):
            return 'delivered'
        elif any(status == 'sent' for status in statuses):
            return 'partial'
        else:
            return 'failed'
    
    async def get_delivery_status(self, notification_id: str) -> Dict[str, Any]:
        """Get delivery status for a notification."""
        try:
            async with get_database() as db:
                # Get notification details
                notification = await db.fetchrow(
                    "SELECT * FROM notifications WHERE id = $1",
                    uuid.UUID(notification_id)
                )
                
                if not notification:
                    raise ExternalServiceException(f"Notification {notification_id} not found")
                
                # Get delivery details
                deliveries = await db.fetch(
                    "SELECT * FROM notification_deliveries WHERE notification_id = $1",
                    uuid.UUID(notification_id)
                )
                
                return {
                    'notification_id': notification_id,
                    'notification': dict(notification),
                    'deliveries': [dict(delivery) for delivery in deliveries],
                    'overall_status': notification['status']
                }
                
        except Exception as e:
            logger.error(f"Failed to get delivery status for {notification_id}: {e}")
            raise ExternalServiceException(f"Failed to get delivery status: {e}")
    
    async def validate_channels(self) -> Dict[str, bool]:
        """Validate all notification channels."""
        validation_results = {}
        
        for channel_name, channel in self.channels.items():
            try:
                is_valid = await channel.validate_config()
                validation_results[channel_name] = is_valid
                logger.info(f"Channel {channel_name} validation: {'passed' if is_valid else 'failed'}")
            except Exception as e:
                validation_results[channel_name] = False
                logger.error(f"Channel {channel_name} validation error: {e}")
        
        return validation_results

# Global notification service instance
notification_service = NotificationDeliveryService()

# Convenience functions
async def send_email(recipient: str, subject: str, content: str, 
                    html_content: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for sending email notifications."""
    notification = {
        'id': str(uuid.uuid4()),
        'channels': ['email'],
        'recipient': recipient,
        'subject': subject,
        'text_content': content,
        'html_content': html_content
    }
    return await notification_service.send_notification(notification)

async def send_webhook(webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for sending webhook notifications."""
    notification = {
        'id': str(uuid.uuid4()),
        'channels': ['webhook'],
        'webhook_url': webhook_url,
        'payload': payload
    }
    return await notification_service.send_notification(notification)

async def send_sms(to_number: str, message: str) -> Dict[str, Any]:
    """Convenience function for sending SMS notifications."""
    notification = {
        'id': str(uuid.uuid4()),
        'channels': ['sms'],
        'to_number': to_number,
        'message': message
    }
    return await notification_service.send_notification(notification)

async def send_slack(channel: str, text: str, blocks: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Convenience function for sending Slack notifications."""
    notification = {
        'id': str(uuid.uuid4()),
        'channels': ['slack'],
        'channel': channel,
        'text': text,
        'blocks': blocks
    }
    return await notification_service.send_notification(notification)

async def send_teams(title: str, text: str, color: str = '0076D7',
                    actions: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Convenience function for sending Teams notifications."""
    notification = {
        'id': str(uuid.uuid4()),
        'channels': ['teams'],
        'title': title,
        'text': text,
        'color': color,
        'actions': actions
    }
    return await notification_service.send_notification(notification)

async def send_multi_channel(channels: List[str], subject: str, content: str,
                           **kwargs) -> Dict[str, Any]:
    """Convenience function for sending multi-channel notifications."""
    notification = {
        'id': str(uuid.uuid4()),
        'channels': channels,
        'subject': subject,
        'content': content,
        'text_content': content,
        **kwargs
    }
    return await notification_service.send_notification(notification)

async def send_bulk_notifications(
    notifications: List[Dict[str, Any]],
    batch_size: int = 50,
    delay_between_batches: float = 1.0
) -> Dict[str, Any]:
    """
    Send multiple notifications in batches with rate limiting.

    Args:
        notifications: List of notification dictionaries
        batch_size: Number of notifications to send per batch
        delay_between_batches: Delay in seconds between batches

    Returns:
        Bulk delivery report with overall statistics
    """
    try:
        total_notifications = len(notifications)
        successful_deliveries = 0
        failed_deliveries = 0
        batch_results = []

        logger.info(f"Starting bulk notification delivery: {total_notifications} notifications")

        # Process notifications in batches
        for i in range(0, total_notifications, batch_size):
            batch = notifications[i:i + batch_size]
            batch_number = (i // batch_size) + 1

            logger.info(f"Processing batch {batch_number}: {len(batch)} notifications")

            # Send batch concurrently
            batch_tasks = []
            for notification in batch:
                if 'id' not in notification:
                    notification['id'] = str(uuid.uuid4())
                task = notification_service.send_notification(notification)
                batch_tasks.append(task)

            # Wait for batch completion
            batch_results_raw = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results
            batch_success = 0
            batch_failed = 0

            for result in batch_results_raw:
                if isinstance(result, Exception):
                    batch_failed += 1
                    failed_deliveries += 1
                elif result.get('overall_status') in ['delivered', 'partial']:
                    batch_success += 1
                    successful_deliveries += 1
                else:
                    batch_failed += 1
                    failed_deliveries += 1

            batch_results.append({
                'batch_number': batch_number,
                'batch_size': len(batch),
                'successful': batch_success,
                'failed': batch_failed,
                'completion_time': datetime.utcnow().isoformat()
            })

            # Delay between batches (except for last batch)
            if i + batch_size < total_notifications:
                await asyncio.sleep(delay_between_batches)

        # Calculate overall statistics
        success_rate = (successful_deliveries / total_notifications) * 100 if total_notifications > 0 else 0

        bulk_report = {
            'status': 'completed',
            'total_notifications': total_notifications,
            'successful_deliveries': successful_deliveries,
            'failed_deliveries': failed_deliveries,
            'success_rate': round(success_rate, 2),
            'batch_count': len(batch_results),
            'batch_results': batch_results,
            'completed_at': datetime.utcnow().isoformat()
        }

        logger.info(f"Bulk notification delivery completed: {success_rate:.1f}% success rate")
        return bulk_report

    except Exception as e:
        logger.error(f"Bulk notification delivery failed: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.utcnow().isoformat()
        }

async def send_templated_notification(
    template_name: str,
    template_variables: Dict[str, Any],
    recipients: List[str],
    channels: List[str] = None,
    tenant_id: str = None,
    language: str = 'en'
) -> Dict[str, Any]:
    """
    Send notification using template engine with personalization.

    Args:
        template_name: Name of the template to use
        template_variables: Variables for template rendering
        recipients: List of recipient identifiers (user IDs or email addresses)
        channels: Notification channels to use
        tenant_id: Tenant ID for custom templates
        language: Language for template rendering

    Returns:
        Delivery report
    """
    try:
        from core_infra.services.notifications.template_engine import template_engine

        # Render template
        rendered_template = await template_engine.render_template(
            template_name=template_name,
            template_type='email',  # Default to email
            language=language,
            variables=template_variables,
            tenant_id=tenant_id
        )

        # Create notifications for each recipient
        notifications = []
        for recipient in recipients:
            notification = {
                'id': str(uuid.uuid4()),
                'channels': channels or ['email'],
                'recipient': recipient,
                'tenant_id': tenant_id,
                'template_name': template_name,
                'language': language,
                **rendered_template
            }
            notifications.append(notification)

        # Send bulk notifications
        return await send_bulk_notifications(notifications)

    except Exception as e:
        logger.error(f"Templated notification delivery failed: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.utcnow().isoformat()
        }
