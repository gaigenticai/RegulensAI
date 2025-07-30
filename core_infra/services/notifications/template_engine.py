"""
Notification Template Engine for RegulensAI.
Provides email templates, personalization, and multi-language support.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database

logger = structlog.get_logger(__name__)
settings = get_settings()


class NotificationTemplateEngine:
    """
    Advanced template engine for notifications with multi-language support,
    personalization, and dynamic content generation.
    """
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['datetime'] = self._format_datetime
        self.jinja_env.filters['phone'] = self._format_phone
        
        # Template cache
        self.template_cache = {}
        
        # Default templates
        self._create_default_templates()
    
    async def render_template(
        self,
        template_name: str,
        template_type: str = 'email',
        language: str = 'en',
        variables: Dict[str, Any] = None,
        tenant_id: str = None
    ) -> Dict[str, str]:
        """
        Render notification template with variables.
        
        Args:
            template_name: Name of the template
            template_type: Type (email, sms, slack, etc.)
            language: Language code (en, es, fr, etc.)
            variables: Template variables
            tenant_id: Tenant ID for custom templates
            
        Returns:
            Rendered template with subject, text, and html content
        """
        try:
            variables = variables or {}
            
            # Get template configuration
            template_config = await self._get_template_config(
                template_name, template_type, language, tenant_id
            )
            
            if not template_config:
                raise ValueError(f"Template not found: {template_name}")
            
            # Add default variables
            default_vars = await self._get_default_variables(tenant_id)
            variables.update(default_vars)
            
            # Render components
            rendered = {}
            
            if template_config.get('subject_template'):
                subject_template = Template(template_config['subject_template'])
                rendered['subject'] = subject_template.render(**variables)
            
            if template_config.get('text_template'):
                text_template = Template(template_config['text_template'])
                rendered['text_content'] = text_template.render(**variables)
            
            if template_config.get('html_template'):
                html_template = self.jinja_env.get_template(template_config['html_template'])
                rendered['html_content'] = html_template.render(**variables)
            
            if template_config.get('sms_template'):
                sms_template = Template(template_config['sms_template'])
                rendered['sms_content'] = sms_template.render(**variables)
            
            logger.info(f"Template rendered: {template_name} ({language})")
            return rendered
            
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise
    
    async def create_custom_template(
        self,
        tenant_id: str,
        template_name: str,
        template_type: str,
        language: str,
        subject_template: str = None,
        text_template: str = None,
        html_template: str = None,
        sms_template: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create custom template for tenant."""
        try:
            template_id = f"{tenant_id}_{template_name}_{template_type}_{language}"
            
            # Store template in database
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO notification_templates (
                        id, tenant_id, template_name, template_type, language,
                        subject_template, text_template, html_template, sms_template,
                        metadata, is_active, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
                    ON CONFLICT (tenant_id, template_name, template_type, language)
                    DO UPDATE SET
                        subject_template = EXCLUDED.subject_template,
                        text_template = EXCLUDED.text_template,
                        html_template = EXCLUDED.html_template,
                        sms_template = EXCLUDED.sms_template,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    template_id,
                    tenant_id,
                    template_name,
                    template_type,
                    language,
                    subject_template,
                    text_template,
                    html_template,
                    sms_template,
                    json.dumps(metadata or {}),
                    True
                )
            
            # Clear cache
            cache_key = f"{tenant_id}_{template_name}_{template_type}_{language}"
            self.template_cache.pop(cache_key, None)
            
            logger.info(f"Custom template created: {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Failed to create custom template: {e}")
            raise
    
    async def _get_template_config(
        self,
        template_name: str,
        template_type: str,
        language: str,
        tenant_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get template configuration from database or defaults."""
        try:
            cache_key = f"{tenant_id}_{template_name}_{template_type}_{language}"
            
            # Check cache first
            if cache_key in self.template_cache:
                return self.template_cache[cache_key]
            
            # Try to get custom template first
            if tenant_id:
                async with get_database() as db:
                    result = await db.fetchrow(
                        """
                        SELECT * FROM notification_templates
                        WHERE tenant_id = $1 AND template_name = $2 
                        AND template_type = $3 AND language = $4 AND is_active = true
                        """,
                        tenant_id, template_name, template_type, language
                    )
                    
                    if result:
                        config = dict(result)
                        self.template_cache[cache_key] = config
                        return config
            
            # Fall back to default templates
            default_config = self._get_default_template_config(template_name, template_type, language)
            if default_config:
                self.template_cache[cache_key] = default_config
                return default_config
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get template config: {e}")
            return None
    
    def _get_default_template_config(
        self,
        template_name: str,
        template_type: str,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """Get default template configuration."""
        
        default_templates = {
            'alert_created': {
                'email': {
                    'en': {
                        'subject_template': '[{{ severity|upper }}] {{ title }}',
                        'text_template': '''Alert: {{ title }}

Description: {{ description }}

Severity: {{ severity }}
Type: {{ alert_type }}
Created: {{ created_at|datetime }}

Please review this alert in the RegulensAI dashboard.''',
                        'html_template': 'alert_created.html'
                    }
                },
                'sms': {
                    'en': {
                        'sms_template': '[{{ severity|upper }}] {{ title }}: {{ description|truncate(100) }}'
                    }
                }
            },
            'compliance_violation': {
                'email': {
                    'en': {
                        'subject_template': 'Compliance Violation Detected - {{ violation_type }}',
                        'text_template': '''A compliance violation has been detected:

Violation Type: {{ violation_type }}
Entity: {{ entity_name }}
Risk Score: {{ risk_score }}
Detected: {{ detected_at|datetime }}

Details: {{ details }}

Please review and take appropriate action.''',
                        'html_template': 'compliance_violation.html'
                    }
                }
            },
            'transaction_flagged': {
                'email': {
                    'en': {
                        'subject_template': 'Transaction Flagged for Review - {{ transaction_id }}',
                        'text_template': '''A transaction has been flagged for review:

Transaction ID: {{ transaction_id }}
Amount: {{ amount|currency }}
Customer: {{ customer_name }}
Flagged: {{ flagged_at|datetime }}

Reason: {{ flag_reason }}

Please review in the transaction monitoring dashboard.''',
                        'html_template': 'transaction_flagged.html'
                    }
                }
            },
            'user_welcome': {
                'email': {
                    'en': {
                        'subject_template': 'Welcome to {{ company_name }}',
                        'text_template': '''Welcome {{ user_name }},

Your account has been created successfully.

Username: {{ username }}
Role: {{ role }}

Please log in to the RegulensAI platform to get started.''',
                        'html_template': 'user_welcome.html'
                    }
                }
            },
            'password_reset': {
                'email': {
                    'en': {
                        'subject_template': 'Password Reset Request',
                        'text_template': '''A password reset has been requested for your account.

Click the link below to reset your password:
{{ reset_link }}

This link will expire in 24 hours.

If you did not request this reset, please ignore this email.''',
                        'html_template': 'password_reset.html'
                    }
                }
            }
        }
        
        return (default_templates
                .get(template_name, {})
                .get(template_type, {})
                .get(language))
    
    async def _get_default_variables(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get default template variables."""
        variables = {
            'company_name': 'RegulensAI',
            'support_email': 'support@regulens.ai',
            'current_year': datetime.now().year,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'platform_url': settings.frontend_url if hasattr(settings, 'frontend_url') else 'https://app.regulens.ai'
        }
        
        # Add tenant-specific variables
        if tenant_id:
            try:
                async with get_database() as db:
                    tenant = await db.fetchrow(
                        "SELECT name, settings FROM tenants WHERE id = $1",
                        tenant_id
                    )
                    
                    if tenant:
                        variables['tenant_name'] = tenant['name']
                        tenant_settings = json.loads(tenant['settings']) if tenant['settings'] else {}
                        variables.update(tenant_settings.get('template_variables', {}))
                        
            except Exception as e:
                logger.warning(f"Failed to get tenant variables: {e}")
        
        return variables
    
    def _format_currency(self, amount: float, currency: str = 'USD') -> str:
        """Format currency amount."""
        if currency == 'USD':
            return f"${amount:,.2f}"
        elif currency == 'EUR':
            return f"€{amount:,.2f}"
        elif currency == 'GBP':
            return f"£{amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    
    def _format_datetime(self, dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S UTC') -> str:
        """Format datetime."""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number."""
        # Simple US phone formatting
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone
    
    def _create_default_templates(self):
        """Create default HTML template files."""
        templates = {
            'alert_created.html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Alert Created</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .alert-high { border-left: 4px solid #dc3545; }
        .alert-medium { border-left: 4px solid #ffc107; }
        .alert-low { border-left: 4px solid #28a745; }
        .alert-critical { border-left: 4px solid #6f42c1; }
    </style>
</head>
<body>
    <div class="header alert-{{ severity }}">
        <h2>{{ title }}</h2>
        <p><strong>Severity:</strong> {{ severity|upper }}</p>
        <p><strong>Type:</strong> {{ alert_type }}</p>
        <p><strong>Created:</strong> {{ created_at|datetime }}</p>
    </div>
    
    <div class="content">
        <h3>Description</h3>
        <p>{{ description }}</p>
        
        {% if metadata %}
        <h3>Additional Information</h3>
        <ul>
        {% for key, value in metadata.items() %}
            <li><strong>{{ key }}:</strong> {{ value }}</li>
        {% endfor %}
        </ul>
        {% endif %}
    </div>
    
    <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        <p>Please review this alert in the <a href="{{ platform_url }}">RegulensAI dashboard</a>.</p>
        <p><small>This is an automated message from {{ company_name }}.</small></p>
    </div>
</body>
</html>''',
            
            'compliance_violation.html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Compliance Violation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .risk-high { background: #dc3545; }
        .risk-medium { background: #ffc107; }
        .risk-low { background: #28a745; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Compliance Violation Detected</h2>
        <p><strong>Type:</strong> {{ violation_type }}</p>
        <p><strong>Risk Score:</strong> {{ risk_score }}</p>
    </div>
    
    <div class="content">
        <h3>Entity Information</h3>
        <p><strong>Name:</strong> {{ entity_name }}</p>
        <p><strong>Type:</strong> {{ entity_type }}</p>
        <p><strong>Detected:</strong> {{ detected_at|datetime }}</p>
        
        <h3>Violation Details</h3>
        <p>{{ details }}</p>
        
        <h3>Recommended Actions</h3>
        <ul>
            <li>Review entity profile and transaction history</li>
            <li>Conduct enhanced due diligence if required</li>
            <li>Document investigation findings</li>
            <li>Report to relevant authorities if necessary</li>
        </ul>
    </div>
    
    <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        <p>Access the <a href="{{ platform_url }}">RegulensAI platform</a> for detailed analysis.</p>
        <p><small>This is an automated compliance alert from {{ company_name }}.</small></p>
    </div>
</body>
</html>'''
        }
        
        for filename, content in templates.items():
            template_path = self.templates_dir / filename
            if not template_path.exists():
                template_path.write_text(content.strip())


# Global template engine instance
template_engine = NotificationTemplateEngine()
