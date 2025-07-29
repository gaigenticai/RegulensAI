"""
Regulens AI - UI Portal Framework
Enterprise-grade UI portal management with session handling, testing capabilities, and analytics.
"""

import asyncio
import structlog
from typing import Dict, Any

from core_infra.ui.portal_manager import (
    portal_session_manager,
    portal_search_manager,
    portal_analytics_manager,
    PortalType,
    EventType
)
from core_infra.ui.testing_portal import (
    api_test_executor,
    test_suite_manager,
    performance_test_manager,
    test_report_generator,
    TestType,
    TestStatus
)

# Initialize logging
logger = structlog.get_logger(__name__)

class UIPortalFramework:
    """Main UI portal framework coordinator."""
    
    def __init__(self):
        self.initialized = False
        self.components = {
            'portal_session_manager': portal_session_manager,
            'portal_search_manager': portal_search_manager,
            'portal_analytics_manager': portal_analytics_manager,
            'api_test_executor': api_test_executor,
            'test_suite_manager': test_suite_manager,
            'performance_test_manager': performance_test_manager,
            'test_report_generator': test_report_generator
        }
    
    async def initialize(self):
        """Initialize all UI portal components."""
        try:
            if self.initialized:
                logger.info("UI portal framework already initialized")
                return
            
            # Initialize portal session manager
            await portal_session_manager.initialize()
            logger.info("Portal session manager initialized")
            
            # Initialize other components (they don't require explicit initialization)
            logger.info("UI portal framework components initialized")
            
            self.initialized = True
            logger.info("UI portal framework initialization completed successfully")
            
        except Exception as e:
            logger.error(f"UI portal framework initialization failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all UI portal components."""
        try:
            health_status = {
                'overall_status': 'healthy',
                'components': {},
                'timestamp': None
            }
            
            # Check each component
            for component_name, component in self.components.items():
                try:
                    # Basic health check - verify component exists and is accessible
                    if hasattr(component, 'health_check'):
                        component_health = await component.health_check()
                    else:
                        # Default health check
                        component_health = {
                            'status': 'healthy',
                            'initialized': True
                        }
                    
                    health_status['components'][component_name] = component_health
                    
                except Exception as e:
                    health_status['components'][component_name] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
                    health_status['overall_status'] = 'degraded'
            
            # Check if any components are unhealthy
            unhealthy_components = [
                name for name, status in health_status['components'].items()
                if status.get('status') != 'healthy'
            ]
            
            if len(unhealthy_components) > len(self.components) / 2:
                health_status['overall_status'] = 'unhealthy'
            elif unhealthy_components:
                health_status['overall_status'] = 'degraded'
            
            health_status['timestamp'] = asyncio.get_event_loop().time()
            return health_status
            
        except Exception as e:
            logger.error(f"UI portal health check failed: {e}")
            return {
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }
    
    def get_component_info(self) -> Dict[str, Any]:
        """Get information about all UI portal components."""
        return {
            'framework_version': '1.0.0',
            'initialized': self.initialized,
            'components': {
                'portal_session_manager': {
                    'description': 'Manages UI portal sessions with analytics tracking',
                    'features': ['session_creation', 'activity_tracking', 'auto_cleanup']
                },
                'portal_search_manager': {
                    'description': 'Advanced search functionality for documentation portal',
                    'features': ['full_text_search', 'faceted_search', 'search_analytics']
                },
                'portal_analytics_manager': {
                    'description': 'Comprehensive analytics for portal usage',
                    'features': ['usage_metrics', 'engagement_tracking', 'performance_analytics']
                },
                'api_test_executor': {
                    'description': 'API testing with comprehensive validation',
                    'features': ['endpoint_testing', 'response_validation', 'performance_metrics']
                },
                'test_suite_manager': {
                    'description': 'Test suite management and execution',
                    'features': ['suite_creation', 'batch_execution', 'result_aggregation']
                },
                'performance_test_manager': {
                    'description': 'Load testing and performance validation',
                    'features': ['load_testing', 'concurrent_execution', 'performance_metrics']
                },
                'test_report_generator': {
                    'description': 'Comprehensive test reporting and analytics',
                    'features': ['execution_reports', 'trend_analysis', 'performance_insights']
                }
            },
            'supported_portal_types': [portal_type.value for portal_type in PortalType],
            'supported_test_types': [test_type.value for test_type in TestType],
            'supported_event_types': [event_type.value for event_type in EventType]
        }

# Global UI portal framework instance
ui_portal_framework = UIPortalFramework()

# Convenience functions for external use
async def initialize_ui_portals():
    """Initialize the UI portal framework."""
    await ui_portal_framework.initialize()

async def get_ui_portal_health() -> Dict[str, Any]:
    """Get UI portal framework health status."""
    return await ui_portal_framework.health_check()

def get_ui_portal_info() -> Dict[str, Any]:
    """Get UI portal framework information."""
    return ui_portal_framework.get_component_info()

# Export main classes and enums for external use
__all__ = [
    # Framework
    'UIPortalFramework',
    'ui_portal_framework',
    'initialize_ui_portals',
    'get_ui_portal_health',
    'get_ui_portal_info',
    
    # Portal Management
    'portal_session_manager',
    'portal_search_manager',
    'portal_analytics_manager',
    'PortalType',
    'EventType',
    
    # Testing Portal
    'api_test_executor',
    'test_suite_manager',
    'performance_test_manager',
    'test_report_generator',
    'TestType',
    'TestStatus',
    
    # Convenience functions from portal_manager
    'create_portal_session',
    'search_documentation',
    'get_portal_analytics',
    
    # Convenience functions from testing_portal
    'execute_api_test',
    'execute_test_suite',
    'execute_load_test',
    'generate_test_report'
]

# Re-export convenience functions
from core_infra.ui.portal_manager import (
    create_portal_session,
    search_documentation,
    get_portal_analytics
)

from core_infra.ui.testing_portal import (
    execute_api_test,
    execute_test_suite,
    execute_load_test,
    generate_test_report
)
