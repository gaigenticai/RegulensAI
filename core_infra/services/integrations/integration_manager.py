"""
Integration Manager Service

Centralized management service for all enterprise integrations:
- Health monitoring and circuit breaker patterns
- Rate limiting and quota management
- Error handling and retry logic
- Performance monitoring and SLA tracking
- Cost tracking and optimization
- Integration orchestration

Features:
- Unified integration dashboard
- Real-time health monitoring
- Automated failover and recovery
- Performance analytics
- Cost optimization recommendations
- Vendor SLA monitoring
"""

import logging
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import aiohttp
from dataclasses import dataclass
from enum import Enum

from core_infra.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class IntegrationStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    OFFLINE = "offline"


@dataclass
class IntegrationHealth:
    system_id: str
    status: IntegrationStatus
    response_time_ms: int
    error_rate: float
    last_check: datetime
    message: str


class IntegrationManagerService:
    """
    Central integration management service for enterprise systems.
    
    Provides unified monitoring, management, and orchestration of all
    external system integrations with comprehensive health tracking.
    """
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        self.circuit_breakers = {}
        self.rate_limiters = {}
        self.health_cache = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_integration_dashboard(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive integration dashboard data.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dashboard data with health, performance, and cost metrics
        """
        try:
            logger.info(f"Generating integration dashboard for tenant {tenant_id}")
            
            dashboard_data = {
                'tenant_id': tenant_id,
                'generated_at': datetime.utcnow(),
                'overview': {
                    'total_integrations': 0,
                    'healthy_integrations': 0,
                    'degraded_integrations': 0,
                    'failing_integrations': 0,
                    'offline_integrations': 0
                },
                'health_summary': [],
                'performance_metrics': {},
                'cost_summary': {},
                'recent_alerts': [],
                'sla_compliance': {},
                'recommendations': []
            }
            
            # Get all integration systems for tenant
            systems = await self._get_tenant_integrations(tenant_id)
            dashboard_data['overview']['total_integrations'] = len(systems)
            
            # Check health of each system
            health_checks = []
            for system in systems:
                health_check = asyncio.create_task(self._check_system_health(system))
                health_checks.append((system, health_check))
            
            # Wait for all health checks
            for system, health_task in health_checks:
                try:
                    health = await health_task
                    dashboard_data['health_summary'].append(health.__dict__)
                    
                    # Update overview counts
                    if health.status == IntegrationStatus.HEALTHY:
                        dashboard_data['overview']['healthy_integrations'] += 1
                    elif health.status == IntegrationStatus.DEGRADED:
                        dashboard_data['overview']['degraded_integrations'] += 1
                    elif health.status == IntegrationStatus.FAILING:
                        dashboard_data['overview']['failing_integrations'] += 1
                    else:
                        dashboard_data['overview']['offline_integrations'] += 1
                        
                except Exception as e:
                    logger.error(f"Health check failed for {system['system_name']}: {str(e)}")
                    dashboard_data['overview']['offline_integrations'] += 1
            
            # Get performance metrics
            dashboard_data['performance_metrics'] = await self._get_performance_metrics(tenant_id)
            
            # Get cost summary
            dashboard_data['cost_summary'] = await self._get_cost_summary(tenant_id)
            
            # Get recent alerts
            dashboard_data['recent_alerts'] = await self._get_recent_alerts(tenant_id)
            
            # Get SLA compliance
            dashboard_data['sla_compliance'] = await self._get_sla_compliance(tenant_id)
            
            # Generate recommendations
            dashboard_data['recommendations'] = await self._generate_recommendations(tenant_id, systems)
            
            logger.info(f"Integration dashboard generated with {len(systems)} systems")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to generate integration dashboard: {str(e)}")
            raise
    
    async def monitor_integration_health(self, tenant_id: str) -> Dict[str, Any]:
        """
        Continuously monitor integration health and handle failures.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Monitoring results with actions taken
        """
        try:
            logger.info(f"Starting integration health monitoring for tenant {tenant_id}")
            
            monitoring_results = {
                'tenant_id': tenant_id,
                'started_at': datetime.utcnow(),
                'systems_monitored': [],
                'health_checks_performed': 0,
                'alerts_generated': 0,
                'circuit_breakers_triggered': 0,
                'failovers_executed': 0,
                'actions_taken': []
            }
            
            # Get all integration systems
            systems = await self._get_tenant_integrations(tenant_id)
            
            for system in systems:
                try:
                    # Perform health check
                    health = await self._check_system_health(system)
                    monitoring_results['health_checks_performed'] += 1
                    monitoring_results['systems_monitored'].append(system['system_name'])
                    
                    # Handle unhealthy systems
                    if health.status != IntegrationStatus.HEALTHY:
                        actions = await self._handle_unhealthy_system(system, health)
                        monitoring_results['actions_taken'].extend(actions)
                        
                        if any('circuit_breaker' in action for action in actions):
                            monitoring_results['circuit_breakers_triggered'] += 1
                        
                        if any('failover' in action for action in actions):
                            monitoring_results['failovers_executed'] += 1
                    
                    # Update health cache
                    self.health_cache[system['id']] = health
                    
                except Exception as e:
                    logger.error(f"Monitoring error for {system['system_name']}: {str(e)}")
                    
                    # Generate alert for monitoring failure
                    await self._generate_alert(system, 'monitoring_failure', str(e))
                    monitoring_results['alerts_generated'] += 1
            
            monitoring_results['completed_at'] = datetime.utcnow()
            
            logger.info(f"Health monitoring completed: {monitoring_results['health_checks_performed']} checks, "
                       f"{monitoring_results['alerts_generated']} alerts, "
                       f"{monitoring_results['circuit_breakers_triggered']} circuit breakers")
            
            return monitoring_results
            
        except Exception as e:
            logger.error(f"Integration health monitoring failed: {str(e)}")
            raise
    
    async def manage_integration_costs(self, tenant_id: str) -> Dict[str, Any]:
        """
        Manage and optimize integration costs.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Cost management results with optimization recommendations
        """
        try:
            logger.info(f"Starting cost management for tenant {tenant_id}")
            
            cost_results = {
                'tenant_id': tenant_id,
                'analysis_date': datetime.utcnow(),
                'total_monthly_cost': Decimal('0.00'),
                'cost_by_system': {},
                'cost_by_category': {},
                'usage_analysis': {},
                'optimization_opportunities': [],
                'budget_alerts': [],
                'cost_trends': {}
            }
            
            # Get integration systems with cost tracking
            systems = await self._get_tenant_integrations(tenant_id)
            
            for system in systems:
                # Calculate system costs
                system_costs = await self._calculate_system_costs(system)
                cost_results['cost_by_system'][system['system_name']] = system_costs
                cost_results['total_monthly_cost'] += system_costs['monthly_cost']
                
                # Categorize costs
                category = self._get_cost_category(system['system_type'])
                if category not in cost_results['cost_by_category']:
                    cost_results['cost_by_category'][category] = Decimal('0.00')
                cost_results['cost_by_category'][category] += system_costs['monthly_cost']
                
                # Analyze usage patterns
                usage_analysis = await self._analyze_system_usage(system)
                cost_results['usage_analysis'][system['system_name']] = usage_analysis
                
                # Identify optimization opportunities
                optimizations = self._identify_cost_optimizations(system, system_costs, usage_analysis)
                cost_results['optimization_opportunities'].extend(optimizations)
            
            # Check budget alerts
            cost_results['budget_alerts'] = await self._check_budget_alerts(tenant_id, cost_results['total_monthly_cost'])
            
            # Generate cost trends
            cost_results['cost_trends'] = await self._generate_cost_trends(tenant_id)
            
            logger.info(f"Cost management completed: ${cost_results['total_monthly_cost']} total monthly cost")
            
            return cost_results
            
        except Exception as e:
            logger.error(f"Cost management failed: {str(e)}")
            raise
    
    async def _get_tenant_integrations(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all integration systems for tenant."""
        try:
            result = self.supabase.table('integration_systems').select('*').eq('tenant_id', tenant_id).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching tenant integrations: {str(e)}")
            return []
    
    async def _check_system_health(self, system: Dict[str, Any]) -> IntegrationHealth:
        """Check health of individual integration system."""
        try:
            system_id = system['id']
            system_name = system['system_name']
            
            start_time = datetime.utcnow()
            
            # Perform health check (mock implementation)
            if system.get('health_check_url'):
                # Would make actual HTTP request to health endpoint
                response_time_ms = 150
                is_healthy = True
                message = "Health check passed"
            else:
                # Check based on recent errors and sync status
                error_count = system.get('error_count', 0)
                last_sync = system.get('last_sync_at')
                
                if error_count > 5:
                    response_time_ms = 0
                    is_healthy = False
                    message = f"High error count: {error_count}"
                elif last_sync and (datetime.utcnow() - datetime.fromisoformat(last_sync)) > timedelta(hours=2):
                    response_time_ms = 0
                    is_healthy = False
                    message = "Sync overdue"
                else:
                    response_time_ms = 100
                    is_healthy = True
                    message = "System operational"
            
            # Determine status
            if not is_healthy:
                status = IntegrationStatus.FAILING
            elif response_time_ms > 1000:
                status = IntegrationStatus.DEGRADED
            else:
                status = IntegrationStatus.HEALTHY
            
            return IntegrationHealth(
                system_id=system_id,
                status=status,
                response_time_ms=response_time_ms,
                error_rate=min(system.get('error_count', 0) / 100.0, 1.0),
                last_check=datetime.utcnow(),
                message=message
            )
            
        except Exception as e:
            logger.error(f"Health check failed for {system.get('system_name')}: {str(e)}")
            return IntegrationHealth(
                system_id=system['id'],
                status=IntegrationStatus.OFFLINE,
                response_time_ms=0,
                error_rate=1.0,
                last_check=datetime.utcnow(),
                message=f"Health check error: {str(e)}"
            )
    
    async def _handle_unhealthy_system(self, system: Dict[str, Any], health: IntegrationHealth) -> List[str]:
        """Handle unhealthy integration system."""
        actions_taken = []
        
        try:
            system_id = system['id']
            system_name = system['system_name']
            
            # Generate alert
            await self._generate_alert(system, 'health_degraded', health.message)
            actions_taken.append(f"Generated health alert for {system_name}")
            
            # Circuit breaker logic
            if health.status == IntegrationStatus.FAILING:
                if system_id not in self.circuit_breakers:
                    self.circuit_breakers[system_id] = {
                        'state': 'closed',
                        'failure_count': 0,
                        'last_failure': None
                    }
                
                breaker = self.circuit_breakers[system_id]
                breaker['failure_count'] += 1
                breaker['last_failure'] = datetime.utcnow()
                
                if breaker['failure_count'] >= 3 and breaker['state'] != 'open':
                    breaker['state'] = 'open'
                    actions_taken.append(f"Opened circuit breaker for {system_name}")
                    
                    # Disable system temporarily
                    await self._disable_system_temporarily(system_id)
                    actions_taken.append(f"Temporarily disabled {system_name}")
            
            # Auto-recovery logic
            elif health.status == IntegrationStatus.HEALTHY:
                if system_id in self.circuit_breakers:
                    breaker = self.circuit_breakers[system_id]
                    if breaker['state'] == 'open':
                        breaker['state'] = 'closed'
                        breaker['failure_count'] = 0
                        actions_taken.append(f"Closed circuit breaker for {system_name}")
                        
                        # Re-enable system
                        await self._enable_system(system_id)
                        actions_taken.append(f"Re-enabled {system_name}")
            
        except Exception as e:
            logger.error(f"Error handling unhealthy system {system.get('system_name')}: {str(e)}")
            actions_taken.append(f"Error handling {system.get('system_name')}: {str(e)}")
        
        return actions_taken
    
    async def _generate_alert(self, system: Dict[str, Any], alert_type: str, message: str):
        """Generate monitoring alert."""
        try:
            alert = {
                'id': str(uuid.uuid4()),
                'alert_type': alert_type,
                'severity': 'high' if 'failing' in alert_type else 'medium',
                'title': f"Integration Alert: {system['system_name']}",
                'description': message,
                'source_id': system['id'],
                'status': 'active',
                'alert_data': {
                    'system_name': system['system_name'],
                    'system_type': system['system_type'],
                    'vendor': system['vendor']
                }
            }
            
            self.supabase.table('monitoring_alerts').insert(alert).execute()
            
        except Exception as e:
            logger.error(f"Error generating alert: {str(e)}")
    
    async def _get_performance_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """Get performance metrics for integrations."""
        # Mock implementation
        return {
            'average_response_time_ms': 250,
            'total_requests_24h': 15000,
            'success_rate_percentage': 99.2,
            'data_volume_gb_24h': 5.2,
            'peak_usage_hour': '14:00-15:00'
        }
    
    async def _get_cost_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get cost summary for integrations."""
        # Mock implementation
        return {
            'monthly_total': 2500.00,
            'daily_average': 83.33,
            'top_cost_driver': 'External Data Feeds',
            'cost_trend': 'stable',
            'budget_utilization_percentage': 75.5
        }
    
    async def _get_recent_alerts(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get recent integration alerts."""
        try:
            # Get alerts from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            result = self.supabase.table('monitoring_alerts').select('*').gte('created_at', yesterday.isoformat()).limit(10).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching recent alerts: {str(e)}")
            return []
    
    async def _get_sla_compliance(self, tenant_id: str) -> Dict[str, Any]:
        """Get SLA compliance metrics."""
        # Mock implementation
        return {
            'overall_sla_compliance': 98.5,
            'systems_meeting_sla': 8,
            'systems_missing_sla': 1,
            'worst_performer': 'Legacy System A',
            'best_performer': 'Modern API B'
        }
    
    async def _generate_recommendations(self, tenant_id: str, systems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Performance recommendations
        if len(systems) > 10:
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'title': 'Consider API Gateway',
                'description': 'With multiple integrations, an API gateway could improve performance and monitoring'
            })
        
        # Cost optimization
        recommendations.append({
            'type': 'cost',
            'priority': 'low',
            'title': 'Review Data Retention',
            'description': 'Some external data sources may have overly long retention periods'
        })
        
        return recommendations
    
    async def _calculate_system_costs(self, system: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate costs for individual system."""
        # Mock cost calculation
        base_cost = 100.0
        usage_multiplier = 1.5
        
        return {
            'monthly_cost': Decimal(str(base_cost * usage_multiplier)),
            'api_calls_cost': Decimal('50.00'),
            'data_volume_cost': Decimal('30.00'),
            'support_cost': Decimal('20.00'),
            'usage_this_month': 1500
        }
    
    def _get_cost_category(self, system_type: str) -> str:
        """Get cost category for system type."""
        category_map = {
            'grc': 'Governance & Risk',
            'core_banking': 'Banking Operations',
            'external_data': 'Data Feeds',
            'document_management': 'Document Storage'
        }
        return category_map.get(system_type, 'Other')
    
    async def _analyze_system_usage(self, system: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system usage patterns."""
        # Mock usage analysis
        return {
            'daily_average_calls': 500,
            'peak_hour_calls': 150,
            'off_peak_calls': 25,
            'weekend_usage_ratio': 0.3,
            'growth_trend': 'stable'
        }
    
    def _identify_cost_optimizations(self, system: Dict[str, Any], costs: Dict[str, Any], 
                                   usage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify cost optimization opportunities."""
        optimizations = []
        
        # Check for overprovisioning
        if usage['daily_average_calls'] < 100:
            optimizations.append({
                'system': system['system_name'],
                'type': 'underutilization',
                'description': 'Low usage detected - consider downgrading plan',
                'potential_savings': '20%'
            })
        
        return optimizations
    
    async def _check_budget_alerts(self, tenant_id: str, current_cost: Decimal) -> List[Dict[str, Any]]:
        """Check for budget threshold alerts."""
        alerts = []
        
        # Mock budget checking
        monthly_budget = Decimal('3000.00')
        utilization = (current_cost / monthly_budget) * 100
        
        if utilization > 80:
            alerts.append({
                'type': 'budget_warning',
                'message': f'Integration costs at {utilization:.1f}% of budget',
                'current_cost': float(current_cost),
                'budget': float(monthly_budget)
            })
        
        return alerts
    
    async def _generate_cost_trends(self, tenant_id: str) -> Dict[str, Any]:
        """Generate cost trend analysis."""
        # Mock trend data
        return {
            'last_3_months': [2200.00, 2350.00, 2500.00],
            'projected_next_month': 2600.00,
            'year_over_year_growth': 15.5,
            'seasonal_patterns': 'Higher costs in Q4 due to compliance reporting'
        }
    
    async def _disable_system_temporarily(self, system_id: str):
        """Temporarily disable integration system."""
        try:
            self.supabase.table('integration_systems').update({
                'status': 'maintenance',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', system_id).execute()
            
        except Exception as e:
            logger.error(f"Error disabling system: {str(e)}")
    
    async def _enable_system(self, system_id: str):
        """Re-enable integration system."""
        try:
            self.supabase.table('integration_systems').update({
                'status': 'active',
                'error_count': 0,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', system_id).execute()
            
        except Exception as e:
            logger.error(f"Error enabling system: {str(e)}") 