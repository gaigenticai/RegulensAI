"""
Notification Preferences Management for RegulensAI.
Manages user and tenant notification preferences, routing rules, and delivery schedules.
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, time
from enum import Enum
import structlog

from core_infra.database.connection import get_database
from core_infra.exceptions import ValidationException

logger = structlog.get_logger(__name__)


class NotificationFrequency(Enum):
    """Notification frequency options."""
    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationType(Enum):
    """Types of notifications."""
    ALERT = "alert"
    COMPLIANCE_VIOLATION = "compliance_violation"
    TRANSACTION_FLAG = "transaction_flag"
    SYSTEM_UPDATE = "system_update"
    USER_ACTION = "user_action"
    REPORT_READY = "report_ready"
    WORKFLOW_UPDATE = "workflow_update"
    SECURITY_EVENT = "security_event"


class NotificationPreferencesManager:
    """
    Manages notification preferences for users and tenants with advanced routing,
    scheduling, and escalation rules.
    """
    
    def __init__(self):
        self.default_preferences = self._get_default_preferences()
    
    async def get_user_preferences(
        self,
        user_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get notification preferences for a user."""
        try:
            async with get_database() as db:
                result = await db.fetchrow(
                    """
                    SELECT preferences, quiet_hours, escalation_rules, 
                           language, timezone, created_at, updated_at
                    FROM user_notification_preferences
                    WHERE user_id = $1 AND tenant_id = $2
                    """,
                    uuid.UUID(user_id), uuid.UUID(tenant_id)
                )
                
                if result:
                    return {
                        'user_id': user_id,
                        'tenant_id': tenant_id,
                        'preferences': json.loads(result['preferences']),
                        'quiet_hours': json.loads(result['quiet_hours']) if result['quiet_hours'] else None,
                        'escalation_rules': json.loads(result['escalation_rules']) if result['escalation_rules'] else [],
                        'language': result['language'],
                        'timezone': result['timezone'],
                        'created_at': result['created_at'],
                        'updated_at': result['updated_at']
                    }
                else:
                    # Return default preferences
                    return await self._create_default_user_preferences(user_id, tenant_id)
                    
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return self.default_preferences
    
    async def update_user_preferences(
        self,
        user_id: str,
        tenant_id: str,
        preferences: Dict[str, Any],
        quiet_hours: Optional[Dict[str, Any]] = None,
        escalation_rules: Optional[List[Dict[str, Any]]] = None,
        language: str = 'en',
        timezone: str = 'UTC'
    ) -> bool:
        """Update notification preferences for a user."""
        try:
            # Validate preferences
            self._validate_preferences(preferences)
            
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO user_notification_preferences (
                        user_id, tenant_id, preferences, quiet_hours, escalation_rules,
                        language, timezone, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ON CONFLICT (user_id, tenant_id) DO UPDATE SET
                        preferences = EXCLUDED.preferences,
                        quiet_hours = EXCLUDED.quiet_hours,
                        escalation_rules = EXCLUDED.escalation_rules,
                        language = EXCLUDED.language,
                        timezone = EXCLUDED.timezone,
                        updated_at = NOW()
                    """,
                    uuid.UUID(user_id),
                    uuid.UUID(tenant_id),
                    json.dumps(preferences),
                    json.dumps(quiet_hours) if quiet_hours else None,
                    json.dumps(escalation_rules) if escalation_rules else None,
                    language,
                    timezone
                )
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            return False
    
    async def get_tenant_preferences(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant-level notification preferences."""
        try:
            async with get_database() as db:
                result = await db.fetchrow(
                    """
                    SELECT default_preferences, routing_rules, escalation_matrix,
                           compliance_settings, created_at, updated_at
                    FROM tenant_notification_preferences
                    WHERE tenant_id = $1
                    """,
                    uuid.UUID(tenant_id)
                )
                
                if result:
                    return {
                        'tenant_id': tenant_id,
                        'default_preferences': json.loads(result['default_preferences']),
                        'routing_rules': json.loads(result['routing_rules']) if result['routing_rules'] else [],
                        'escalation_matrix': json.loads(result['escalation_matrix']) if result['escalation_matrix'] else {},
                        'compliance_settings': json.loads(result['compliance_settings']) if result['compliance_settings'] else {},
                        'created_at': result['created_at'],
                        'updated_at': result['updated_at']
                    }
                else:
                    # Create default tenant preferences
                    return await self._create_default_tenant_preferences(tenant_id)
                    
        except Exception as e:
            logger.error(f"Failed to get tenant preferences: {e}")
            return {}
    
    async def determine_notification_routing(
        self,
        notification_type: str,
        severity: str,
        user_id: str,
        tenant_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Determine how a notification should be routed based on preferences and rules.
        
        Returns:
            Routing configuration with channels, timing, and escalation
        """
        try:
            # Get user and tenant preferences
            user_prefs = await self.get_user_preferences(user_id, tenant_id)
            tenant_prefs = await self.get_tenant_preferences(tenant_id)
            
            # Determine base routing from user preferences
            notification_config = user_prefs['preferences'].get(notification_type, {})
            
            # Apply tenant routing rules
            routing_rules = tenant_prefs.get('routing_rules', [])
            for rule in routing_rules:
                if self._rule_matches(rule, notification_type, severity, metadata):
                    # Override with rule configuration
                    notification_config.update(rule.get('override_config', {}))
                    break
            
            # Check quiet hours
            if self._is_quiet_hours(user_prefs.get('quiet_hours'), user_prefs.get('timezone', 'UTC')):
                notification_config = self._apply_quiet_hours_rules(notification_config, severity)
            
            # Determine escalation
            escalation_config = self._determine_escalation(
                notification_type, severity, user_prefs, tenant_prefs
            )
            
            return {
                'channels': notification_config.get('channels', ['email']),
                'frequency': notification_config.get('frequency', 'immediate'),
                'language': user_prefs.get('language', 'en'),
                'timezone': user_prefs.get('timezone', 'UTC'),
                'escalation': escalation_config,
                'delay_minutes': notification_config.get('delay_minutes', 0),
                'template_overrides': notification_config.get('template_overrides', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to determine notification routing: {e}")
            return {
                'channels': ['email'],
                'frequency': 'immediate',
                'language': 'en',
                'timezone': 'UTC',
                'escalation': None
            }
    
    async def get_notification_recipients(
        self,
        notification_type: str,
        severity: str,
        tenant_id: str,
        entity_id: str = None,
        role_filter: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of users who should receive a notification."""
        try:
            async with get_database() as db:
                # Base query for active users in tenant
                query = """
                    SELECT u.id, u.email, u.phone, u.first_name, u.last_name,
                           u.role, u.is_active, unp.preferences
                    FROM users u
                    LEFT JOIN user_notification_preferences unp 
                        ON u.id = unp.user_id AND u.tenant_id = unp.tenant_id
                    WHERE u.tenant_id = $1 AND u.is_active = true
                """
                params = [uuid.UUID(tenant_id)]
                
                # Add role filter if specified
                if role_filter:
                    query += " AND u.role = ANY($2)"
                    params.append(role_filter)
                
                results = await db.fetch(query, *params)
                
                recipients = []
                for row in results:
                    user_prefs = json.loads(row['preferences']) if row['preferences'] else self.default_preferences['preferences']
                    
                    # Check if user wants this type of notification
                    notification_config = user_prefs.get(notification_type, {})
                    if notification_config.get('frequency') != 'never':
                        recipients.append({
                            'user_id': str(row['id']),
                            'email': row['email'],
                            'phone': row['phone'],
                            'name': f"{row['first_name']} {row['last_name']}",
                            'role': row['role'],
                            'notification_config': notification_config
                        })
                
                return recipients
                
        except Exception as e:
            logger.error(f"Failed to get notification recipients: {e}")
            return []
    
    def _validate_preferences(self, preferences: Dict[str, Any]):
        """Validate notification preferences structure."""
        valid_types = [t.value for t in NotificationType]
        valid_channels = [c.value for c in NotificationChannel]
        valid_frequencies = [f.value for f in NotificationFrequency]
        
        for notification_type, config in preferences.items():
            if notification_type not in valid_types:
                raise ValidationException(f"Invalid notification type: {notification_type}")
            
            if 'channels' in config:
                for channel in config['channels']:
                    if channel not in valid_channels:
                        raise ValidationException(f"Invalid channel: {channel}")
            
            if 'frequency' in config:
                if config['frequency'] not in valid_frequencies:
                    raise ValidationException(f"Invalid frequency: {config['frequency']}")
    
    def _rule_matches(
        self,
        rule: Dict[str, Any],
        notification_type: str,
        severity: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Check if a routing rule matches the notification."""
        conditions = rule.get('conditions', {})
        
        # Check notification type
        if 'notification_types' in conditions:
            if notification_type not in conditions['notification_types']:
                return False
        
        # Check severity
        if 'severities' in conditions:
            if severity not in conditions['severities']:
                return False
        
        # Check metadata conditions
        if 'metadata_conditions' in conditions and metadata:
            for key, expected_value in conditions['metadata_conditions'].items():
                if metadata.get(key) != expected_value:
                    return False
        
        return True
    
    def _is_quiet_hours(self, quiet_hours: Dict[str, Any], timezone: str) -> bool:
        """Check if current time is within quiet hours."""
        if not quiet_hours or not quiet_hours.get('enabled'):
            return False
        
        # For simplicity, using UTC time
        # In production, would convert to user's timezone
        current_time = datetime.utcnow().time()
        
        start_time = time.fromisoformat(quiet_hours.get('start_time', '22:00'))
        end_time = time.fromisoformat(quiet_hours.get('end_time', '08:00'))
        
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            return current_time >= start_time or current_time <= end_time
    
    def _apply_quiet_hours_rules(
        self,
        notification_config: Dict[str, Any],
        severity: str
    ) -> Dict[str, Any]:
        """Apply quiet hours rules to notification configuration."""
        # Critical alerts bypass quiet hours
        if severity == 'critical':
            return notification_config
        
        # For other severities, modify channels and timing
        modified_config = notification_config.copy()
        
        # Remove non-urgent channels during quiet hours
        quiet_channels = modified_config.get('channels', [])
        if 'email' in quiet_channels and severity in ['low', 'medium']:
            quiet_channels = ['in_app']  # Only in-app notifications
        
        modified_config['channels'] = quiet_channels
        modified_config['delay_minutes'] = modified_config.get('delay_minutes', 0) + 60  # Delay by 1 hour
        
        return modified_config
    
    def _determine_escalation(
        self,
        notification_type: str,
        severity: str,
        user_prefs: Dict[str, Any],
        tenant_prefs: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Determine escalation rules for notification."""
        # Check user escalation rules first
        user_escalation = user_prefs.get('escalation_rules', [])
        for rule in user_escalation:
            if (rule.get('notification_type') == notification_type and 
                rule.get('severity') == severity):
                return rule
        
        # Check tenant escalation matrix
        escalation_matrix = tenant_prefs.get('escalation_matrix', {})
        return escalation_matrix.get(f"{notification_type}_{severity}")
    
    async def _create_default_user_preferences(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Create default preferences for a new user."""
        default_prefs = self.default_preferences.copy()
        default_prefs['user_id'] = user_id
        default_prefs['tenant_id'] = tenant_id
        
        # Store in database
        await self.update_user_preferences(
            user_id, tenant_id, default_prefs['preferences'],
            default_prefs.get('quiet_hours'), default_prefs.get('escalation_rules'),
            default_prefs.get('language', 'en'), default_prefs.get('timezone', 'UTC')
        )
        
        return default_prefs
    
    async def _create_default_tenant_preferences(self, tenant_id: str) -> Dict[str, Any]:
        """Create default preferences for a new tenant."""
        default_tenant_prefs = {
            'tenant_id': tenant_id,
            'default_preferences': self.default_preferences['preferences'],
            'routing_rules': [],
            'escalation_matrix': {
                'alert_critical': {
                    'escalate_after_minutes': 15,
                    'escalate_to_roles': ['admin', 'compliance_officer'],
                    'escalate_channels': ['sms', 'email']
                },
                'compliance_violation_high': {
                    'escalate_after_minutes': 30,
                    'escalate_to_roles': ['compliance_officer'],
                    'escalate_channels': ['email', 'slack']
                }
            },
            'compliance_settings': {
                'require_acknowledgment': ['compliance_violation', 'security_event'],
                'retention_days': 2555  # 7 years
            }
        }
        
        # Store in database
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO tenant_notification_preferences (
                    tenant_id, default_preferences, routing_rules, escalation_matrix,
                    compliance_settings, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                """,
                uuid.UUID(tenant_id),
                json.dumps(default_tenant_prefs['default_preferences']),
                json.dumps(default_tenant_prefs['routing_rules']),
                json.dumps(default_tenant_prefs['escalation_matrix']),
                json.dumps(default_tenant_prefs['compliance_settings'])
            )
        
        return default_tenant_prefs
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default notification preferences."""
        return {
            'preferences': {
                'alert': {
                    'channels': ['email', 'in_app'],
                    'frequency': 'immediate'
                },
                'compliance_violation': {
                    'channels': ['email', 'in_app'],
                    'frequency': 'immediate'
                },
                'transaction_flag': {
                    'channels': ['email', 'in_app'],
                    'frequency': 'immediate'
                },
                'system_update': {
                    'channels': ['email'],
                    'frequency': 'daily'
                },
                'user_action': {
                    'channels': ['in_app'],
                    'frequency': 'immediate'
                },
                'report_ready': {
                    'channels': ['email', 'in_app'],
                    'frequency': 'immediate'
                },
                'workflow_update': {
                    'channels': ['in_app'],
                    'frequency': 'immediate'
                },
                'security_event': {
                    'channels': ['email', 'sms', 'in_app'],
                    'frequency': 'immediate'
                }
            },
            'quiet_hours': {
                'enabled': True,
                'start_time': '22:00',
                'end_time': '08:00',
                'timezone': 'UTC'
            },
            'escalation_rules': [],
            'language': 'en',
            'timezone': 'UTC'
        }


# Global preferences manager instance
preferences_manager = NotificationPreferencesManager()
