"""
Celery application configuration for RegulensAI background tasks
"""

import os
from celery import Celery

# Initialize Celery app
app = Celery('regulens_ai')

# Configuration
app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'regulatory_monitor.*': {'queue': 'regulatory'},
        'compliance_engine.*': {'queue': 'compliance'},
        'ai_insights.*': {'queue': 'ai'},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'regulatory-monitoring': {
            'task': 'regulatory_monitor.check_updates',
            'schedule': 3600.0,  # Every hour
        },
        'compliance-assessment': {
            'task': 'compliance_engine.assess_compliance',
            'schedule': 7200.0,  # Every 2 hours
        },
    },
)

# Auto-discover tasks
app.autodiscover_tasks([
    'core_infra.services.regulatory_monitor',
    'core_infra.services.analytics',
    'core_infra.services.intelligent_automation',
])

if __name__ == '__main__':
    app.start() 