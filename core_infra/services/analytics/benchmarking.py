"""
Performance Benchmarking Service

Provides comprehensive performance benchmarking capabilities
for compliance, risk management, and operational metrics.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from scipy import stats

from core_infra.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PerformanceBenchmarkingService:
    """
    Enterprise-grade performance benchmarking service.
    
    Provides:
    - Industry benchmarking and peer comparison
    - Performance gap analysis and improvement opportunities
    - Competitive intelligence and market positioning
    - Trend analysis and performance forecasting
    - Best practice identification and recommendation
    """
    
    def __init__(self, supabase_client, vector_store=None):
        """Initialize the performance benchmarking service."""
        self.supabase = supabase_client
        self.vector_store = vector_store
        self.benchmark_cache = {}
        self.industry_data = {}
        
        # Load industry benchmark data
        self._load_industry_benchmarks()
    
    async def create_comprehensive_benchmark_analysis(
        self,
        tenant_id: str,
        industry_sector: str,
        institution_size: str,
        benchmark_categories: List[str] = None,
        comparison_period: str = 'annual'
    ) -> Dict[str, Any]:
        """
        Create comprehensive benchmark analysis across multiple categories.
        
        Args:
            tenant_id: Tenant UUID
            industry_sector: Industry sector for comparison
            institution_size: Size category for peer grouping
            benchmark_categories: Categories to benchmark
            comparison_period: Period for comparison
            
        Returns:
            Comprehensive benchmark analysis with insights and recommendations
        """
        try:
            logger.info(f"Creating comprehensive benchmark analysis for {industry_sector}")
            
            if not benchmark_categories:
                benchmark_categories = [
                    'compliance_efficiency', 'risk_management',
                    'operational_performance', 'regulatory_readiness',
                    'financial_performance'
                ]
            
            # Get organization's performance data
            org_performance = await self._get_organization_performance_data(
                tenant_id, benchmark_categories, comparison_period
            )
            
            # Get industry benchmark data
            industry_benchmarks = await self._get_industry_benchmark_data(
                industry_sector, institution_size, benchmark_categories
            )
            
            # Perform detailed analysis for each category
            category_analyses = {}
            for category in benchmark_categories:
                analysis = await self._analyze_category_performance(
                    tenant_id, category, org_performance.get(category, {}),
                    industry_benchmarks.get(category, {})
                )
                category_analyses[category] = analysis
            
            # Calculate overall performance scores
            overall_analysis = await self._calculate_overall_performance_analysis(
                category_analyses, org_performance, industry_benchmarks
            )
            
            # Identify improvement opportunities
            improvement_opportunities = await self._identify_comprehensive_improvement_opportunities(
                category_analyses, overall_analysis
            )
            
            # Generate strategic recommendations
            strategic_recommendations = await self._generate_strategic_recommendations(
                category_analyses, improvement_opportunities, industry_sector
            )
            
            # Create performance insights
            performance_insights = await self._generate_performance_insights(
                overall_analysis, category_analyses, improvement_opportunities
            )
            
            # Store benchmark results
            for category in benchmark_categories:
                await self._store_benchmark_result(
                    tenant_id, category, industry_sector, institution_size,
                    category_analyses[category], org_performance.get(category, {})
                )
            
            return {
                'tenant_id': tenant_id,
                'industry_sector': industry_sector,
                'institution_size': institution_size,
                'comparison_period': comparison_period,
                'benchmark_date': datetime.utcnow().date().isoformat(),
                'overall_analysis': overall_analysis,
                'category_analyses': category_analyses,
                'improvement_opportunities': improvement_opportunities,
                'strategic_recommendations': strategic_recommendations,
                'performance_insights': performance_insights,
                'peer_group_size': industry_benchmarks.get('peer_group_size', 0)
            }
            
        except Exception as e:
            logger.error(f"Error creating comprehensive benchmark analysis: {str(e)}")
            raise
    
    async def generate_peer_comparison_report(
        self,
        tenant_id: str,
        specific_metrics: List[str],
        peer_group_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate detailed peer comparison report for specific metrics.
        
        Args:
            tenant_id: Tenant UUID
            specific_metrics: Specific metrics to compare
            peer_group_criteria: Criteria for peer selection
            
        Returns:
            Detailed peer comparison with ranking and analysis
        """
        try:
            logger.info(f"Generating peer comparison for {len(specific_metrics)} metrics")
            
            # Get organization's metric values
            org_metrics = await self._get_organization_metrics(tenant_id, specific_metrics)
            
            # Get peer group data
            peer_data = await self._get_peer_group_data(peer_group_criteria, specific_metrics)
            
            # Perform peer comparison analysis
            comparison_results = {}
            for metric in specific_metrics:
                comparison = await self._compare_metric_with_peers(
                    metric, org_metrics.get(metric), peer_data.get(metric, [])
                )
                comparison_results[metric] = comparison
            
            # Calculate overall peer ranking
            overall_ranking = await self._calculate_overall_peer_ranking(
                comparison_results, peer_data
            )
            
            # Identify performance leaders and laggards
            performance_analysis = await self._analyze_performance_distribution(
                comparison_results, peer_data
            )
            
            # Generate improvement roadmap
            improvement_roadmap = await self._generate_peer_based_improvement_roadmap(
                comparison_results, performance_analysis
            )
            
            return {
                'tenant_id': tenant_id,
                'peer_group_criteria': peer_group_criteria,
                'metrics_analyzed': specific_metrics,
                'peer_group_size': len(peer_data.get(specific_metrics[0], [])) if specific_metrics else 0,
                'comparison_results': comparison_results,
                'overall_ranking': overall_ranking,
                'performance_analysis': performance_analysis,
                'improvement_roadmap': improvement_roadmap,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating peer comparison report: {str(e)}")
            raise
    
    async def track_performance_trends(
        self,
        tenant_id: str,
        tracking_metrics: List[str],
        trend_period_months: int = 12
    ) -> Dict[str, Any]:
        """
        Track performance trends over time with benchmark comparison.
        
        Args:
            tenant_id: Tenant UUID
            tracking_metrics: Metrics to track over time
            trend_period_months: Period for trend analysis
            
        Returns:
            Performance trend analysis with benchmark context
        """
        try:
            logger.info(f"Tracking performance trends for {trend_period_months} months")
            
            # Get historical performance data
            historical_data = await self._get_historical_performance_data(
                tenant_id, tracking_metrics, trend_period_months
            )
            
            # Get historical benchmark data for comparison
            historical_benchmarks = await self._get_historical_benchmark_data(
                tracking_metrics, trend_period_months
            )
            
            # Analyze trends for each metric
            trend_analyses = {}
            for metric in tracking_metrics:
                trend = await self._analyze_metric_trend(
                    metric,
                    historical_data.get(metric, []),
                    historical_benchmarks.get(metric, [])
                )
                trend_analyses[metric] = trend
            
            # Identify performance patterns
            performance_patterns = await self._identify_performance_patterns(
                trend_analyses, historical_data
            )
            
            # Generate trend forecasts
            trend_forecasts = await self._generate_trend_forecasts(
                trend_analyses, performance_patterns
            )
            
            # Create improvement tracking
            improvement_tracking = await self._track_improvement_progress(
                trend_analyses, historical_benchmarks
            )
            
            return {
                'tenant_id': tenant_id,
                'tracking_period_months': trend_period_months,
                'metrics_tracked': tracking_metrics,
                'trend_analyses': trend_analyses,
                'performance_patterns': performance_patterns,
                'trend_forecasts': trend_forecasts,
                'improvement_tracking': improvement_tracking,
                'analysis_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error tracking performance trends: {str(e)}")
            raise
    
    async def generate_best_practices_analysis(
        self,
        industry_sector: str,
        performance_area: str,
        top_performers_count: int = 10
    ) -> Dict[str, Any]:
        """
        Generate best practices analysis from top performers.
        
        Args:
            industry_sector: Industry sector to analyze
            performance_area: Specific area for best practices
            top_performers_count: Number of top performers to analyze
            
        Returns:
            Best practices analysis with actionable insights
        """
        try:
            logger.info(f"Generating best practices analysis for {performance_area}")
            
            # Identify top performers in the sector
            top_performers = await self._identify_top_performers(
                industry_sector, performance_area, top_performers_count
            )
            
            # Analyze common characteristics of top performers
            common_characteristics = await self._analyze_top_performer_characteristics(
                top_performers, performance_area
            )
            
            # Extract best practices
            best_practices = await self._extract_best_practices(
                top_performers, common_characteristics
            )
            
            # Analyze implementation patterns
            implementation_patterns = await self._analyze_implementation_patterns(
                best_practices, top_performers
            )
            
            # Generate adoption recommendations
            adoption_recommendations = await self._generate_adoption_recommendations(
                best_practices, implementation_patterns, industry_sector
            )
            
            return {
                'industry_sector': industry_sector,
                'performance_area': performance_area,
                'top_performers_analyzed': len(top_performers),
                'common_characteristics': common_characteristics,
                'best_practices': best_practices,
                'implementation_patterns': implementation_patterns,
                'adoption_recommendations': adoption_recommendations,
                'analysis_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating best practices analysis: {str(e)}")
            raise
    
    async def create_competitive_intelligence_report(
        self,
        tenant_id: str,
        competitor_analysis_scope: Dict[str, Any],
        intelligence_categories: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create competitive intelligence report with market positioning.
        
        Args:
            tenant_id: Tenant UUID
            competitor_analysis_scope: Scope for competitor analysis
            intelligence_categories: Categories for intelligence gathering
            
        Returns:
            Competitive intelligence report with strategic insights
        """
        try:
            logger.info("Creating competitive intelligence report")
            
            if not intelligence_categories:
                intelligence_categories = [
                    'market_position', 'compliance_capabilities',
                    'operational_efficiency', 'innovation_index'
                ]
            
            # Get organization's competitive profile
            org_profile = await self._get_organization_competitive_profile(
                tenant_id, intelligence_categories
            )
            
            # Analyze competitive landscape
            competitive_landscape = await self._analyze_competitive_landscape(
                competitor_analysis_scope, intelligence_categories
            )
            
            # Determine market positioning
            market_positioning = await self._determine_market_positioning(
                org_profile, competitive_landscape
            )
            
            # Identify competitive advantages and gaps
            competitive_analysis = await self._analyze_competitive_position(
                org_profile, competitive_landscape, market_positioning
            )
            
            # Generate strategic insights
            strategic_insights = await self._generate_competitive_strategic_insights(
                competitive_analysis, market_positioning
            )
            
            # Create action recommendations
            action_recommendations = await self._generate_competitive_action_recommendations(
                competitive_analysis, strategic_insights
            )
            
            return {
                'tenant_id': tenant_id,
                'analysis_scope': competitor_analysis_scope,
                'intelligence_categories': intelligence_categories,
                'organization_profile': org_profile,
                'competitive_landscape': competitive_landscape,
                'market_positioning': market_positioning,
                'competitive_analysis': competitive_analysis,
                'strategic_insights': strategic_insights,
                'action_recommendations': action_recommendations,
                'report_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating competitive intelligence report: {str(e)}")
            raise
    
    # Private helper methods
    
    def _load_industry_benchmarks(self):
        """Load industry benchmark data."""
        # In production, load from external data sources or databases
        self.industry_data = {
            'banking': {
                'compliance_efficiency': {
                    'industry_average': 82.5,
                    'top_quartile': 92.0,
                    'bottom_quartile': 75.0,
                    'best_in_class': 96.5
                },
                'risk_management': {
                    'industry_average': 78.3,
                    'top_quartile': 88.0,
                    'bottom_quartile': 70.0,
                    'best_in_class': 94.2
                }
            },
            'insurance': {
                'compliance_efficiency': {
                    'industry_average': 79.8,
                    'top_quartile': 89.5,
                    'bottom_quartile': 72.0,
                    'best_in_class': 95.1
                }
            }
        }
    
    async def _get_organization_performance_data(
        self,
        tenant_id: str,
        categories: List[str],
        period: str
    ) -> Dict[str, Any]:
        """Get organization's performance data for benchmarking."""
        performance_data = {}
        
        for category in categories:
            # Get relevant metrics for this category
            category_metrics = await self._get_category_metrics(tenant_id, category, period)
            performance_data[category] = category_metrics
        
        return performance_data
    
    async def _get_category_metrics(
        self,
        tenant_id: str,
        category: str,
        period: str
    ) -> Dict[str, Any]:
        """Get metrics for a specific performance category."""
        if category == 'compliance_efficiency':
            return await self._get_compliance_efficiency_metrics(tenant_id, period)
        elif category == 'risk_management':
            return await self._get_risk_management_metrics(tenant_id, period)
        elif category == 'operational_performance':
            return await self._get_operational_performance_metrics(tenant_id, period)
        elif category == 'regulatory_readiness':
            return await self._get_regulatory_readiness_metrics(tenant_id, period)
        elif category == 'financial_performance':
            return await self._get_financial_performance_metrics(tenant_id, period)
        else:
            return {}
    
    async def _get_compliance_efficiency_metrics(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """Get compliance efficiency metrics."""
        # Get compliance task completion rates
        tasks_result = self.supabase.table('compliance_tasks').select('*').eq('tenant_id', tenant_id).execute()
        tasks = tasks_result.data if tasks_result.data else []
        
        completed_tasks = [t for t in tasks if t['status'] == 'completed']
        total_tasks = len(tasks)
        
        completion_rate = (len(completed_tasks) / max(total_tasks, 1)) * 100
        
        # Calculate average completion time
        completion_times = []
        for task in completed_tasks:
            if task.get('completed_date') and task.get('created_at'):
                completed = datetime.fromisoformat(task['completed_date'].replace('Z', '+00:00'))
                created = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
                completion_times.append((completed - created).days)
        
        avg_completion_time = np.mean(completion_times) if completion_times else 0
        
        # Get compliance metrics
        metrics_result = self.supabase.table('compliance_metrics').select('*').eq('tenant_id', tenant_id).execute()
        metrics = metrics_result.data if metrics_result.data else []
        
        # Calculate overall compliance score
        normal_metrics = [m for m in metrics if m.get('status') == 'normal']
        compliance_score = (len(normal_metrics) / max(len(metrics), 1)) * 100
        
        return {
            'task_completion_rate': float(completion_rate),
            'average_completion_time_days': float(avg_completion_time),
            'compliance_score': float(compliance_score),
            'total_metrics': len(metrics),
            'calculation_date': datetime.utcnow().isoformat()
        }
    
    async def _get_risk_management_metrics(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """Get risk management metrics."""
        # Get risk scores
        risk_scores_result = self.supabase.table('customer_risk_scores').select('*').eq('tenant_id', tenant_id).execute()
        risk_scores = risk_scores_result.data if risk_scores_result.data else []
        
        if risk_scores:
            avg_risk_score = np.mean([float(r['overall_risk_score']) for r in risk_scores])
            high_risk_count = len([r for r in risk_scores if r['risk_category'] == 'high'])
            risk_coverage = len(risk_scores)  # Number of customers with risk scores
        else:
            avg_risk_score = 0
            high_risk_count = 0
            risk_coverage = 0
        
        # Get transaction monitoring coverage
        transactions_result = self.supabase.table('transactions').select('id').eq('tenant_id', tenant_id).execute()
        total_transactions = len(transactions_result.data) if transactions_result.data else 0
        
        monitored_result = self.supabase.table('transaction_risk_scores').select('transaction_id').eq('tenant_id', tenant_id).execute()
        monitored_transactions = len(monitored_result.data) if monitored_result.data else 0
        
        monitoring_coverage = (monitored_transactions / max(total_transactions, 1)) * 100
        
        return {
            'average_risk_score': float(avg_risk_score),
            'high_risk_customer_percentage': float((high_risk_count / max(len(risk_scores), 1)) * 100),
            'transaction_monitoring_coverage': float(monitoring_coverage),
            'risk_assessment_coverage': float(risk_coverage),
            'calculation_date': datetime.utcnow().isoformat()
        }
    
    async def _get_operational_performance_metrics(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """Get operational performance metrics."""
        # Mock operational metrics - in production, calculate from actual data
        return {
            'process_automation_rate': float(np.random.uniform(65, 85)),
            'system_uptime_percentage': float(np.random.uniform(98, 99.9)),
            'user_satisfaction_score': float(np.random.uniform(7.5, 9.2)),
            'incident_resolution_time_hours': float(np.random.uniform(2, 12)),
            'calculation_date': datetime.utcnow().isoformat()
        }
    
    async def _get_regulatory_readiness_metrics(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """Get regulatory readiness metrics."""
        # Get regulatory impact assessments
        assessments_result = self.supabase.table('regulatory_impact_assessments').select('*').eq('tenant_id', tenant_id).execute()
        assessments = assessments_result.data if assessments_result.data else []
        
        completed_assessments = [a for a in assessments if a.get('status') == 'implemented']
        readiness_score = (len(completed_assessments) / max(len(assessments), 1)) * 100
        
        # Calculate average assessment time
        assessment_times = []
        for assessment in completed_assessments:
            if assessment.get('created_at') and assessment.get('updated_at'):
                created = datetime.fromisoformat(assessment['created_at'].replace('Z', '+00:00'))
                updated = datetime.fromisoformat(assessment['updated_at'].replace('Z', '+00:00'))
                assessment_times.append((updated - created).days)
        
        avg_assessment_time = np.mean(assessment_times) if assessment_times else 0
        
        return {
            'regulatory_readiness_score': float(readiness_score),
            'average_assessment_time_days': float(avg_assessment_time),
            'total_assessments': len(assessments),
            'proactive_assessments_percentage': float(np.random.uniform(60, 85)),
            'calculation_date': datetime.utcnow().isoformat()
        }
    
    async def _get_financial_performance_metrics(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """Get financial performance metrics related to compliance."""
        # Mock financial metrics - in production, integrate with financial systems
        return {
            'compliance_cost_efficiency': float(np.random.uniform(70, 90)),
            'regulatory_penalty_cost': float(np.random.uniform(0, 50000)),
            'compliance_roi': float(np.random.uniform(15, 35)),
            'cost_per_compliance_task': float(np.random.uniform(500, 2000)),
            'calculation_date': datetime.utcnow().isoformat()
        }
    
    async def _get_industry_benchmark_data(
        self,
        industry_sector: str,
        institution_size: str,
        categories: List[str]
    ) -> Dict[str, Any]:
        """Get industry benchmark data for comparison."""
        benchmark_data = {}
        
        industry_benchmarks = self.industry_data.get(industry_sector, {})
        
        for category in categories:
            category_benchmarks = industry_benchmarks.get(category, {})
            
            # Adjust benchmarks based on institution size
            size_multiplier = self._get_size_adjustment_multiplier(institution_size)
            
            adjusted_benchmarks = {}
            for benchmark_type, value in category_benchmarks.items():
                adjusted_benchmarks[benchmark_type] = value * size_multiplier
            
            benchmark_data[category] = adjusted_benchmarks
        
        # Add sample size and confidence intervals
        benchmark_data['metadata'] = {
            'peer_group_size': np.random.randint(50, 200),
            'confidence_interval': 0.95,
            'data_collection_period': 'annual',
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return benchmark_data
    
    def _get_size_adjustment_multiplier(self, institution_size: str) -> float:
        """Get adjustment multiplier based on institution size."""
        size_multipliers = {
            'small': 0.95,
            'medium': 1.0,
            'large': 1.05,
            'enterprise': 1.1,
            'multinational': 1.15
        }
        return size_multipliers.get(institution_size, 1.0)
    
    async def _analyze_category_performance(
        self,
        tenant_id: str,
        category: str,
        org_performance: Dict[str, Any],
        industry_benchmarks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze performance for a specific category."""
        analysis = {
            'category': category,
            'analysis_date': datetime.utcnow().isoformat()
        }
        
        # Calculate key metric comparisons
        metric_comparisons = {}
        
        for metric_name, org_value in org_performance.items():
            if isinstance(org_value, (int, float)) and metric_name != 'calculation_date':
                industry_avg = industry_benchmarks.get('industry_average', 0)
                top_quartile = industry_benchmarks.get('top_quartile', 0)
                
                # Calculate percentile rank
                percentile_rank = self._calculate_percentile_rank(
                    org_value, industry_avg, industry_benchmarks
                )
                
                # Determine performance level
                performance_level = self._determine_performance_level(
                    org_value, industry_benchmarks
                )
                
                # Calculate gap to top quartile
                gap_to_top_quartile = max(0, top_quartile - org_value)
                
                metric_comparisons[metric_name] = {
                    'organization_value': float(org_value),
                    'industry_average': float(industry_avg),
                    'percentile_rank': float(percentile_rank),
                    'performance_level': performance_level,
                    'gap_to_top_quartile': float(gap_to_top_quartile),
                    'improvement_potential': float(gap_to_top_quartile / max(org_value, 1) * 100)
                }
        
        analysis['metric_comparisons'] = metric_comparisons
        
        # Calculate overall category performance
        if metric_comparisons:
            avg_percentile = np.mean([m['percentile_rank'] for m in metric_comparisons.values()])
            analysis['overall_percentile_rank'] = float(avg_percentile)
            analysis['overall_performance_grade'] = self._calculate_performance_grade(avg_percentile)
        
        return analysis
    
    def _calculate_percentile_rank(
        self,
        org_value: float,
        industry_avg: float,
        benchmarks: Dict[str, Any]
    ) -> float:
        """Calculate percentile rank for organization value."""
        # Simple percentile calculation based on industry distribution
        # In production, use actual distribution data
        
        bottom_quartile = benchmarks.get('bottom_quartile', industry_avg * 0.9)
        top_quartile = benchmarks.get('top_quartile', industry_avg * 1.1)
        
        if org_value <= bottom_quartile:
            return 25.0
        elif org_value >= top_quartile:
            return 75.0
        else:
            # Linear interpolation between quartiles
            range_size = top_quartile - bottom_quartile
            position = org_value - bottom_quartile
            return 25.0 + (position / range_size) * 50.0
    
    def _determine_performance_level(self, org_value: float, benchmarks: Dict[str, Any]) -> str:
        """Determine performance level based on benchmarks."""
        industry_avg = benchmarks.get('industry_average', 0)
        top_quartile = benchmarks.get('top_quartile', industry_avg * 1.1)
        best_in_class = benchmarks.get('best_in_class', industry_avg * 1.2)
        
        if org_value >= best_in_class * 0.95:
            return 'best_in_class'
        elif org_value >= top_quartile:
            return 'top_quartile'
        elif org_value >= industry_avg:
            return 'above_average'
        elif org_value >= industry_avg * 0.9:
            return 'average'
        else:
            return 'below_average'
    
    def _calculate_performance_grade(self, percentile_rank: float) -> str:
        """Calculate letter grade based on percentile rank."""
        if percentile_rank >= 95:
            return 'A+'
        elif percentile_rank >= 90:
            return 'A'
        elif percentile_rank >= 85:
            return 'A-'
        elif percentile_rank >= 80:
            return 'B+'
        elif percentile_rank >= 75:
            return 'B'
        elif percentile_rank >= 70:
            return 'B-'
        elif percentile_rank >= 65:
            return 'C+'
        elif percentile_rank >= 60:
            return 'C'
        elif percentile_rank >= 50:
            return 'C-'
        elif percentile_rank >= 40:
            return 'D'
        else:
            return 'F'
    
    async def _calculate_overall_performance_analysis(
        self,
        category_analyses: Dict[str, Any],
        org_performance: Dict[str, Any],
        industry_benchmarks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall performance analysis across categories."""
        # Calculate weighted overall score
        category_weights = {
            'compliance_efficiency': 0.3,
            'risk_management': 0.25,
            'operational_performance': 0.2,
            'regulatory_readiness': 0.15,
            'financial_performance': 0.1
        }
        
        weighted_scores = []
        category_grades = []
        
        for category, analysis in category_analyses.items():
            percentile_rank = analysis.get('overall_percentile_rank', 50.0)
            weight = category_weights.get(category, 0.2)
            
            weighted_scores.append(percentile_rank * weight)
            category_grades.append(analysis.get('overall_performance_grade', 'C'))
        
        overall_percentile = sum(weighted_scores) / sum(category_weights.values())
        overall_grade = self._calculate_performance_grade(overall_percentile)
        
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for category, analysis in category_analyses.items():
            percentile = analysis.get('overall_percentile_rank', 50.0)
            if percentile >= 75:
                strengths.append(category)
            elif percentile <= 40:
                weaknesses.append(category)
        
        return {
            'overall_percentile_rank': float(overall_percentile),
            'overall_performance_grade': overall_grade,
            'category_grades': category_grades,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'competitive_position': self._determine_competitive_position(overall_percentile),
            'improvement_priority': weaknesses[0] if weaknesses else None
        }
    
    def _determine_competitive_position(self, overall_percentile: float) -> str:
        """Determine competitive position based on overall percentile."""
        if overall_percentile >= 90:
            return 'market_leader'
        elif overall_percentile >= 75:
            return 'strong_performer'
        elif overall_percentile >= 60:
            return 'average_performer'
        elif overall_percentile >= 40:
            return 'below_average'
        else:
            return 'laggard'
    
    async def _identify_comprehensive_improvement_opportunities(
        self,
        category_analyses: Dict[str, Any],
        overall_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify comprehensive improvement opportunities."""
        opportunities = []
        
        # Identify category-level opportunities
        for category, analysis in category_analyses.items():
            percentile = analysis.get('overall_percentile_rank', 50.0)
            
            if percentile < 75:  # Below top quartile
                metric_comparisons = analysis.get('metric_comparisons', {})
                
                # Find metrics with highest improvement potential
                for metric_name, comparison in metric_comparisons.items():
                    improvement_potential = comparison.get('improvement_potential', 0)
                    
                    if improvement_potential > 10:  # More than 10% improvement potential
                        opportunities.append({
                            'category': category,
                            'metric': metric_name,
                            'current_value': comparison['organization_value'],
                            'target_value': comparison['organization_value'] + comparison['gap_to_top_quartile'],
                            'improvement_potential_percent': improvement_potential,
                            'priority': 'high' if improvement_potential > 25 else 'medium',
                            'estimated_effort': self._estimate_improvement_effort(improvement_potential),
                            'expected_timeline': self._estimate_improvement_timeline(improvement_potential)
                        })
        
        # Sort by improvement potential
        opportunities.sort(key=lambda x: x['improvement_potential_percent'], reverse=True)
        
        return opportunities[:10]  # Top 10 opportunities
    
    def _estimate_improvement_effort(self, improvement_potential: float) -> str:
        """Estimate effort required for improvement."""
        if improvement_potential > 50:
            return 'high'
        elif improvement_potential > 25:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_improvement_timeline(self, improvement_potential: float) -> str:
        """Estimate timeline for improvement."""
        if improvement_potential > 50:
            return '12-18_months'
        elif improvement_potential > 25:
            return '6-12_months'
        else:
            return '3-6_months'
    
    async def _store_benchmark_result(
        self,
        tenant_id: str,
        category: str,
        industry_sector: str,
        institution_size: str,
        analysis: Dict[str, Any],
        org_performance: Dict[str, Any]
    ) -> None:
        """Store benchmark result in database."""
        try:
            # Get the primary metric for this category
            metric_comparisons = analysis.get('metric_comparisons', {})
            if not metric_comparisons:
                return
            
            # Use the first metric as representative
            primary_metric = list(metric_comparisons.keys())[0]
            primary_comparison = metric_comparisons[primary_metric]
            
            benchmark_data = {
                'tenant_id': tenant_id,
                'benchmark_name': f'{category}_benchmark',
                'benchmark_category': category,
                'industry_sector': industry_sector,
                'institution_size': institution_size,
                'metric_definition': f'Performance benchmark for {category}',
                'calculation_methodology': 'Percentile ranking against industry peers',
                'industry_average': primary_comparison.get('industry_average', 0),
                'industry_median': primary_comparison.get('industry_average', 0),  # Mock median
                'top_quartile': primary_comparison.get('industry_average', 0) * 1.1,  # Mock top quartile
                'bottom_quartile': primary_comparison.get('industry_average', 0) * 0.9,  # Mock bottom quartile
                'best_in_class': primary_comparison.get('industry_average', 0) * 1.2,  # Mock best in class
                'organization_value': primary_comparison.get('organization_value', 0),
                'percentile_rank': analysis.get('overall_percentile_rank', 50.0),
                'performance_grade': analysis.get('overall_performance_grade', 'C'),
                'gap_analysis': json.dumps({
                    'gaps_identified': len([m for m in metric_comparisons.values() if m.get('improvement_potential', 0) > 10]),
                    'primary_gap': primary_metric,
                    'improvement_potential': primary_comparison.get('improvement_potential', 0)
                }),
                'improvement_opportunities': json.dumps([
                    f'Improve {metric}' for metric, comp in metric_comparisons.items() 
                    if comp.get('improvement_potential', 0) > 15
                ][:3]),
                'data_source': 'industry_benchmark_analysis',
                'sample_size': np.random.randint(50, 200),  # Mock sample size
                'confidence_interval': 0.95,
                'benchmark_date': datetime.utcnow().date().isoformat(),
                'next_update_date': (datetime.utcnow() + timedelta(days=90)).date().isoformat()
            }
            
            # Store in database
            self.supabase.table('performance_benchmarks').insert(benchmark_data).execute()
            
        except Exception as e:
            logger.error(f"Error storing benchmark result: {str(e)}")
    
    # Additional helper methods for other benchmarking functions...
    # (Peer comparison, trend tracking, best practices, competitive intelligence)
    
    async def _get_organization_metrics(self, tenant_id: str, metrics: List[str]) -> Dict[str, float]:
        """Get organization's metric values."""
        # Mock implementation - in production, fetch actual metrics
        return {metric: float(np.random.uniform(50, 90)) for metric in metrics}
    
    async def _get_peer_group_data(
        self,
        criteria: Dict[str, Any],
        metrics: List[str]
    ) -> Dict[str, List[float]]:
        """Get peer group data for comparison."""
        # Mock peer data - in production, fetch from benchmark database
        peer_data = {}
        for metric in metrics:
            # Generate realistic peer distribution
            peer_values = np.random.normal(75, 15, 50).tolist()  # 50 peers
            peer_data[metric] = [max(0, min(100, v)) for v in peer_values]
        
        return peer_data
    
    async def _compare_metric_with_peers(
        self,
        metric: str,
        org_value: float,
        peer_values: List[float]
    ) -> Dict[str, Any]:
        """Compare organization's metric with peer values."""
        if not peer_values or org_value is None:
            return {'error': 'Insufficient data for comparison'}
        
        # Calculate statistics
        peer_mean = float(np.mean(peer_values))
        peer_median = float(np.median(peer_values))
        peer_std = float(np.std(peer_values))
        
        # Calculate percentile rank
        percentile_rank = float(stats.percentileofscore(peer_values, org_value))
        
        # Determine quartile
        q1 = float(np.percentile(peer_values, 25))
        q3 = float(np.percentile(peer_values, 75))
        
        if org_value >= q3:
            quartile = 'top'
        elif org_value >= peer_median:
            quartile = 'upper_middle'
        elif org_value >= q1:
            quartile = 'lower_middle'
        else:
            quartile = 'bottom'
        
        return {
            'metric': metric,
            'organization_value': float(org_value),
            'peer_mean': peer_mean,
            'peer_median': peer_median,
            'peer_std': peer_std,
            'percentile_rank': percentile_rank,
            'quartile': quartile,
            'z_score': float((org_value - peer_mean) / max(peer_std, 1)),
            'gap_to_median': float(peer_median - org_value),
            'gap_to_top_quartile': float(q3 - org_value),
            'peer_group_size': len(peer_values)
        }
    
    # More helper methods for other benchmarking functionality would be implemented here... 