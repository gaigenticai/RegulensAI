"""
Regulens AI - Alert Management System
Enterprise-grade alert management with escalation, deduplication, and intelligent routing.
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, asdict
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.services.notifications.delivery import notification_service
from core_infra.exceptions import BusinessLogicException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status values."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    description: str
    condition: str
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 60
    escalation_minutes: int = 30
    notification_channels: List[str] = None
    assignee_groups: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class Alert:
    """Alert data structure."""
    id: str
    tenant_id: str
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    status: AlertStatus = AlertStatus.OPEN
    assigned_to: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    fingerprint: Optional[str] = None

class AlertManager:
    """Comprehensive alert management system."""
    
    def __init__(self):
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_fingerprints = set()
        self.escalation_rules = {}
        
    async def initialize(self):
        """Initialize alert manager with rules from database."""
        try:
            await self._load_alert_rules()
            await self._load_escalation_rules()
            await self._load_active_alerts()
            logger.info("Alert manager initialized successfully")
        except Exception as e:
            logger.error(f"Alert manager initialization failed: {e}")
            raise
    
    async def create_alert(self, alert_data: Dict[str, Any]) -> str:
        """
        Create a new alert with deduplication and routing.
        
        Args:
            alert_data: Alert information
            
        Returns:
            Alert ID
        """
        try:
            # Generate alert fingerprint for deduplication
            fingerprint = self._generate_fingerprint(alert_data)
            
            # Check for duplicate alerts
            if await self._is_duplicate_alert(fingerprint):
                existing_alert_id = await self._get_alert_by_fingerprint(fingerprint)
                logger.info(f"Duplicate alert detected, updating existing alert: {existing_alert_id}")
                await self._update_alert_count(existing_alert_id)
                return existing_alert_id
            
            # Create new alert
            alert_id = str(uuid.uuid4())
            alert = Alert(
                id=alert_id,
                tenant_id=alert_data['tenant_id'],
                alert_type=alert_data['alert_type'],
                severity=AlertSeverity(alert_data.get('severity', 'medium')),
                title=alert_data['title'],
                description=alert_data['description'],
                entity_type=alert_data.get('entity_type'),
                entity_id=alert_data.get('entity_id'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=alert_data.get('metadata', {}),
                fingerprint=fingerprint
            )
            
            # Store alert in database
            await self._store_alert(alert)
            
            # Add to active alerts
            self.active_alerts[alert_id] = alert
            self.alert_fingerprints.add(fingerprint)
            
            # Apply alert routing and assignment
            await self._route_alert(alert)
            
            # Send notifications
            await self._send_alert_notifications(alert)
            
            # Schedule escalation if needed
            await self._schedule_escalation(alert)
            
            logger.info(f"Alert created: {alert_id} - {alert.title}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Alert creation failed: {e}")
            raise BusinessLogicException(f"Alert creation failed: {e}")
    
    async def acknowledge_alert(self, alert_id: str, user_id: str, 
                              notes: Optional[str] = None) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            user_id: User acknowledging the alert
            notes: Optional acknowledgment notes
            
        Returns:
            Success status
        """
        try:
            async with get_database() as db:
                # Update alert status
                result = await db.execute(
                    """
                    UPDATE alerts 
                    SET status = $1, acknowledged_at = $2, assigned_to = $3, updated_at = $4
                    WHERE id = $5 AND status = $6
                    """,
                    AlertStatus.ACKNOWLEDGED.value,
                    datetime.utcnow(),
                    uuid.UUID(user_id),
                    datetime.utcnow(),
                    uuid.UUID(alert_id),
                    AlertStatus.OPEN.value
                )
                
                if result == "UPDATE 0":
                    return False
                
                # Log acknowledgment
                await db.execute(
                    """
                    INSERT INTO alert_history (
                        id, alert_id, action, user_id, notes, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(alert_id),
                    'acknowledged',
                    uuid.UUID(user_id),
                    notes,
                    datetime.utcnow()
                )
                
                # Update in-memory alert
                if alert_id in self.active_alerts:
                    self.active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
                    self.active_alerts[alert_id].acknowledged_at = datetime.utcnow()
                    self.active_alerts[alert_id].assigned_to = user_id
                
                # Send acknowledgment notification
                await self._send_acknowledgment_notification(alert_id, user_id)
                
                logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Alert acknowledgment failed: {e}")
            raise BusinessLogicException(f"Alert acknowledgment failed: {e}")
    
    async def resolve_alert(self, alert_id: str, user_id: str, 
                          resolution_notes: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID
            user_id: User resolving the alert
            resolution_notes: Resolution notes
            
        Returns:
            Success status
        """
        try:
            async with get_database() as db:
                # Update alert status
                result = await db.execute(
                    """
                    UPDATE alerts 
                    SET status = $1, resolved_at = $2, updated_at = $3
                    WHERE id = $4 AND status IN ($5, $6, $7)
                    """,
                    AlertStatus.RESOLVED.value,
                    datetime.utcnow(),
                    datetime.utcnow(),
                    uuid.UUID(alert_id),
                    AlertStatus.OPEN.value,
                    AlertStatus.ACKNOWLEDGED.value,
                    AlertStatus.IN_PROGRESS.value
                )
                
                if result == "UPDATE 0":
                    return False
                
                # Log resolution
                await db.execute(
                    """
                    INSERT INTO alert_history (
                        id, alert_id, action, user_id, notes, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(alert_id),
                    'resolved',
                    uuid.UUID(user_id),
                    resolution_notes,
                    datetime.utcnow()
                )
                
                # Update in-memory alert
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.utcnow()
                    
                    # Remove from active alerts
                    del self.active_alerts[alert_id]
                    if alert.fingerprint:
                        self.alert_fingerprints.discard(alert.fingerprint)
                
                # Send resolution notification
                await self._send_resolution_notification(alert_id, user_id, resolution_notes)
                
                logger.info(f"Alert {alert_id} resolved by user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Alert resolution failed: {e}")
            raise BusinessLogicException(f"Alert resolution failed: {e}")
    
    async def escalate_alert(self, alert_id: str) -> bool:
        """
        Escalate an alert to higher severity or different team.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Success status
        """
        try:
            alert = self.active_alerts.get(alert_id)
            if not alert:
                return False
            
            # Determine escalation action
            escalation_rule = self.escalation_rules.get(alert.alert_type)
            if not escalation_rule:
                return False
            
            # Increase severity if possible
            if alert.severity != AlertSeverity.CRITICAL:
                new_severity = self._get_next_severity(alert.severity)
                await self._update_alert_severity(alert_id, new_severity)
                alert.severity = new_severity
            
            # Reassign to escalation team
            if escalation_rule.get('escalation_team'):
                await self._reassign_alert(alert_id, escalation_rule['escalation_team'])
            
            # Send escalation notifications
            await self._send_escalation_notification(alert)
            
            logger.warning(f"Alert {alert_id} escalated to {alert.severity.value}")
            return True
            
        except Exception as e:
            logger.error(f"Alert escalation failed: {e}")
            return False
    
    async def get_alerts(self, tenant_id: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering.
        
        Args:
            tenant_id: Tenant ID
            filters: Optional filters (status, severity, alert_type, etc.)
            
        Returns:
            List of alerts
        """
        try:
            async with get_database() as db:
                # Build query conditions
                conditions = ["tenant_id = $1"]
                params = [uuid.UUID(tenant_id)]
                param_count = 1
                
                if filters:
                    if filters.get('status'):
                        param_count += 1
                        conditions.append(f"status = ${param_count}")
                        params.append(filters['status'])
                    
                    if filters.get('severity'):
                        param_count += 1
                        conditions.append(f"severity = ${param_count}")
                        params.append(filters['severity'])
                    
                    if filters.get('alert_type'):
                        param_count += 1
                        conditions.append(f"alert_type = ${param_count}")
                        params.append(filters['alert_type'])
                    
                    if filters.get('assigned_to'):
                        param_count += 1
                        conditions.append(f"assigned_to = ${param_count}")
                        params.append(uuid.UUID(filters['assigned_to']))
                
                where_clause = " AND ".join(conditions)
                
                query = f"""
                    SELECT a.*, u.full_name as assigned_to_name
                    FROM alerts a
                    LEFT JOIN users u ON a.assigned_to = u.id
                    WHERE {where_clause}
                    ORDER BY a.created_at DESC
                    LIMIT 1000
                """
                
                alerts = await db.fetch(query, *params)
                return [dict(alert) for alert in alerts]
                
        except Exception as e:
            logger.error(f"Get alerts failed: {e}")
            raise BusinessLogicException(f"Get alerts failed: {e}")
    
    def _generate_fingerprint(self, alert_data: Dict[str, Any]) -> str:
        """Generate unique fingerprint for alert deduplication."""
        fingerprint_data = f"{alert_data['alert_type']}:{alert_data.get('entity_type', '')}:{alert_data.get('entity_id', '')}:{alert_data['title']}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    async def _is_duplicate_alert(self, fingerprint: str) -> bool:
        """Check if alert with same fingerprint exists."""
        return fingerprint in self.alert_fingerprints
    
    async def _get_alert_by_fingerprint(self, fingerprint: str) -> Optional[str]:
        """Get alert ID by fingerprint."""
        for alert_id, alert in self.active_alerts.items():
            if alert.fingerprint == fingerprint:
                return alert_id
        return None
    
    async def _update_alert_count(self, alert_id: str):
        """Update alert occurrence count."""
        async with get_database() as db:
            await db.execute(
                """
                UPDATE alerts 
                SET occurrence_count = occurrence_count + 1, updated_at = $1
                WHERE id = $2
                """,
                datetime.utcnow(),
                uuid.UUID(alert_id)
            )
    
    async def _store_alert(self, alert: Alert):
        """Store alert in database."""
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO alerts (
                    id, tenant_id, alert_type, severity, title, description,
                    entity_type, entity_id, status, metadata, fingerprint,
                    occurrence_count, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                uuid.UUID(alert.id),
                uuid.UUID(alert.tenant_id),
                alert.alert_type,
                alert.severity.value,
                alert.title,
                alert.description,
                alert.entity_type,
                uuid.UUID(alert.entity_id) if alert.entity_id else None,
                alert.status.value,
                alert.metadata,
                alert.fingerprint,
                1,  # Initial occurrence count
                alert.created_at,
                alert.updated_at
            )
    
    async def _route_alert(self, alert: Alert):
        """Route alert to appropriate team/user."""
        try:
            # Route based on alert type and severity
            routing_rules = {
                'security': 'security-team',
                'compliance': 'compliance-team',
                'performance': 'ops-team',
                'availability': 'ops-team',
                'data_integrity': 'data-team'
            }
            
            # Get team for alert type
            team = routing_rules.get(alert.alert_type, 'ops-team')
            
            # Add routing metadata
            alert.metadata['assigned_team'] = team
            
            # For critical alerts, also route to management
            if alert.severity == AlertSeverity.CRITICAL:
                alert.metadata['escalated_to'] = 'management'
                
            # Update alert in database with routing info
            async with get_database() as db:
                await db.execute(
                    """
                    UPDATE alerts 
                    SET metadata = metadata || $1
                    WHERE id = $2
                    """,
                    json.dumps({'assigned_team': team}),
                    alert.id
                )
                
            logger.info(f"Alert {alert.id} routed to {team}")
            
        except Exception as e:
            logger.error(f"Failed to route alert {alert.id}: {e}")
            # Continue processing even if routing fails
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send notifications for new alert."""
        try:
            notification = {
                'id': str(uuid.uuid4()),
                'tenant_id': alert.tenant_id,
                'type': 'alert_created',
                'channels': ['email', 'slack'],
                'subject': f"[{alert.severity.value.upper()}] {alert.title}",
                'text_content': f"Alert: {alert.title}\n\nDescription: {alert.description}\n\nSeverity: {alert.severity.value}\nType: {alert.alert_type}",
                'metadata': {
                    'alert_id': alert.id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity.value
                }
            }
            
            await notification_service.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to send alert notifications: {e}")
    
    async def _schedule_escalation(self, alert: Alert):
        """Schedule alert escalation if not acknowledged."""
        try:
            # Define escalation timeframes based on severity
            escalation_delays = {
                AlertSeverity.CRITICAL: timedelta(minutes=15),
                AlertSeverity.HIGH: timedelta(minutes=30),
                AlertSeverity.MEDIUM: timedelta(hours=1),
                AlertSeverity.LOW: timedelta(hours=4)
            }
            
            delay = escalation_delays.get(alert.severity, timedelta(hours=1))
            escalation_time = alert.created_at + delay
            
            # Store escalation schedule in database
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO alert_escalations (
                        id, alert_id, scheduled_time, escalation_level, status
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (alert_id, escalation_level) DO UPDATE
                    SET scheduled_time = $3, status = $5
                    """,
                    str(uuid.uuid4()),
                    alert.id,
                    escalation_time,
                    1,  # First level escalation
                    'scheduled'
                )
            
            logger.info(f"Scheduled escalation for alert {alert.id} at {escalation_time}")
            
        except Exception as e:
            logger.error(f"Failed to schedule escalation for alert {alert.id}: {e}")
            # Non-critical - alert processing continues
    
    async def _load_alert_rules(self):
        """Load alert rules from database."""
        try:
            async with get_database() as db:
                rules = await db.fetch(
                    """
                    SELECT id, name, rule_type, conditions, actions, 
                           severity, enabled, metadata
                    FROM alert_rules
                    WHERE enabled = true
                    ORDER BY severity DESC, created_at ASC
                    """
                )
                
                self.alert_rules = {}
                for rule in rules:
                    self.alert_rules[rule['id']] = {
                        'name': rule['name'],
                        'rule_type': rule['rule_type'],
                        'conditions': json.loads(rule['conditions']) if rule['conditions'] else {},
                        'actions': json.loads(rule['actions']) if rule['actions'] else [],
                        'severity': rule['severity'],
                        'metadata': json.loads(rule['metadata']) if rule['metadata'] else {}
                    }
                
                logger.info(f"Loaded {len(self.alert_rules)} alert rules")
                
        except Exception as e:
            logger.error(f"Failed to load alert rules: {e}")
            # Initialize with empty rules if loading fails
            self.alert_rules = {}
    
    async def _load_escalation_rules(self):
        """Load escalation rules from database."""
        try:
            async with get_database() as db:
                rules = await db.fetch(
                    """
                    SELECT id, alert_type, severity, escalation_levels,
                           notification_channels, metadata
                    FROM escalation_rules
                    WHERE enabled = true
                    ORDER BY severity DESC
                    """
                )
                
                self.escalation_rules = {}
                for rule in rules:
                    key = f"{rule['alert_type']}_{rule['severity']}"
                    self.escalation_rules[key] = {
                        'id': rule['id'],
                        'levels': json.loads(rule['escalation_levels']) if rule['escalation_levels'] else [],
                        'channels': json.loads(rule['notification_channels']) if rule['notification_channels'] else ['email'],
                        'metadata': json.loads(rule['metadata']) if rule['metadata'] else {}
                    }
                
                logger.info(f"Loaded {len(self.escalation_rules)} escalation rules")
                
        except Exception as e:
            logger.error(f"Failed to load escalation rules: {e}")
            # Initialize with default escalation rules if loading fails
            self.escalation_rules = {
                'default_critical': {
                    'levels': [
                        {'delay_minutes': 15, 'notify': ['team_lead']},
                        {'delay_minutes': 30, 'notify': ['manager']},
                        {'delay_minutes': 60, 'notify': ['director']}
                    ],
                    'channels': ['email', 'sms', 'slack']
                }
            }
    
    async def _load_active_alerts(self):
        """Load active alerts from database."""
        try:
            async with get_database() as db:
                alerts = await db.fetch(
                    "SELECT * FROM alerts WHERE status IN ('open', 'acknowledged', 'in_progress')"
                )
                
                for alert_record in alerts:
                    alert = Alert(
                        id=str(alert_record['id']),
                        tenant_id=str(alert_record['tenant_id']),
                        alert_type=alert_record['alert_type'],
                        severity=AlertSeverity(alert_record['severity']),
                        title=alert_record['title'],
                        description=alert_record['description'],
                        entity_type=alert_record['entity_type'],
                        entity_id=str(alert_record['entity_id']) if alert_record['entity_id'] else None,
                        status=AlertStatus(alert_record['status']),
                        assigned_to=str(alert_record['assigned_to']) if alert_record['assigned_to'] else None,
                        created_at=alert_record['created_at'],
                        updated_at=alert_record['updated_at'],
                        acknowledged_at=alert_record['acknowledged_at'],
                        resolved_at=alert_record['resolved_at'],
                        metadata=alert_record['metadata'],
                        fingerprint=alert_record['fingerprint']
                    )
                    
                    self.active_alerts[alert.id] = alert
                    if alert.fingerprint:
                        self.alert_fingerprints.add(alert.fingerprint)
                        
        except Exception as e:
            logger.error(f"Failed to load active alerts: {e}")

# Global alert manager instance
alert_manager = AlertManager()

# Convenience functions
async def create_compliance_alert(tenant_id: str, title: str, description: str,
                                severity: str = 'medium', entity_type: str = None,
                                entity_id: str = None) -> str:
    """Convenience function for creating compliance alerts."""
    alert_data = {
        'tenant_id': tenant_id,
        'alert_type': 'compliance',
        'title': title,
        'description': description,
        'severity': severity,
        'entity_type': entity_type,
        'entity_id': entity_id
    }
    return await alert_manager.create_alert(alert_data)

async def create_aml_alert(tenant_id: str, customer_id: str, transaction_id: str,
                         title: str, description: str, severity: str = 'high') -> str:
    """Convenience function for creating AML alerts."""
    alert_data = {
        'tenant_id': tenant_id,
        'alert_type': 'aml_violation',
        'title': title,
        'description': description,
        'severity': severity,
        'entity_type': 'transaction',
        'entity_id': transaction_id,
        'metadata': {
            'customer_id': customer_id,
            'transaction_id': transaction_id
        }
    }
    return await alert_manager.create_alert(alert_data)
