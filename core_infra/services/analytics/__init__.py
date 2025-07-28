"""
Analytics Services Package

Provides advanced analytics and intelligence capabilities for financial compliance:
- Risk scoring models and customer/transaction risk assessment
- Predictive analytics and forecasting
- Compliance metrics and KPI monitoring
- Business intelligence dashboards
- Regulatory intelligence and insights
- Performance benchmarking
"""

from .risk_scoring import RiskScoringService
from .predictive_analytics import PredictiveAnalyticsService
from .compliance_metrics import ComplianceMetricsService
from .intelligence import RegulatoryIntelligenceService
from .benchmarking import PerformanceBenchmarkingService

__all__ = [
    'RiskScoringService',
    'PredictiveAnalyticsService', 
    'ComplianceMetricsService',
    'RegulatoryIntelligenceService',
    'PerformanceBenchmarkingService'
] 