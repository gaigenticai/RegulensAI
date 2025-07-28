"""
Intelligent Automation Service for Phase 6 Advanced AI & Automation

This module provides enterprise-grade intelligent automation capabilities including:
- RPA integration with UiPath, Blue Prism, Automation Anywhere
- End-to-end workflow automation
- Intelligent document processing
- Process orchestration and management
- Human-in-the-loop automation workflows

Key Features:
- Multi-RPA platform integration
- Workflow orchestration engine
- Quality controls and error handling
- Performance monitoring and analytics
- Compliance validation and audit trails
"""

from .automation_service import IntelligentAutomationService, AutomationRequest, AutomationResult
from .rpa_integrator import RPAIntegrator
from .workflow_orchestrator import WorkflowOrchestrator
from .process_monitor import ProcessMonitor
from .quality_controller import QualityController
from .automation_executor import AutomationExecutor

__all__ = [
    'IntelligentAutomationService',
    'AutomationRequest',
    'AutomationResult',
    'RPAIntegrator',
    'WorkflowOrchestrator',
    'ProcessMonitor',
    'QualityController',
    'AutomationExecutor'
]

__version__ = "1.0.0" 