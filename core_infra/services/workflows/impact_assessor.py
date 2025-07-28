"""
Regulatory Impact Assessor
Automated assessment of regulatory changes impact on business operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json

from core_infra.database.connection import get_database
from core_infra.services.monitoring import track_operation
from core_infra.ai.embeddings import get_document_embeddings_manager
from core_infra.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ImpactLevel(Enum):
    """Impact severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ImpactCategory(Enum):
    """Categories of business impact."""
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    LEGAL = "legal"
    REPUTATIONAL = "reputational"
    STRATEGIC = "strategic"
    TECHNOLOGY = "technology"
    COMPLIANCE = "compliance"
    CUSTOMER = "customer"


@dataclass
class BusinessUnit:
    """Business unit definition."""
    id: str
    name: str
    function: str  # 'compliance', 'risk', 'operations', 'legal', etc.
    head_user_id: str
    stakeholders: List[str] = field(default_factory=list)
    systems: List[str] = field(default_factory=list)
    processes: List[str] = field(default_factory=list)


@dataclass
class RegulatoryImpact:
    """Assessed regulatory impact on business."""
    regulation_id: str
    regulation_title: str
    impact_level: ImpactLevel
    impact_categories: List[ImpactCategory]
    affected_business_units: List[str]
    affected_systems: List[str]
    affected_processes: List[str]
    implementation_effort: str  # 'low', 'medium', 'high', 'significant'
    estimated_cost: Optional[float]
    estimated_timeline: Optional[str]
    compliance_deadline: Optional[datetime]
    required_actions: List[str]
    risk_factors: List[str]
    mitigation_strategies: List[str]
    dependencies: List[str]
    confidence_score: float
    assessment_rationale: str
    similar_regulations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"


@dataclass
class ImpactAssessmentCriteria:
    """Criteria for impact assessment."""
    regulation_keywords: List[str]
    business_functions: List[str]
    compliance_areas: List[str]
    technology_systems: List[str]
    customer_segments: List[str]
    geographic_regions: List[str]
    impact_indicators: Dict[str, Any]


class ImpactAssessor:
    """
    Automated regulatory impact assessment system that analyzes
    regulatory changes and determines business impact.
    """
    
    def __init__(self):
        self.business_units: Dict[str, BusinessUnit] = {}
        self.assessment_criteria: Dict[str, ImpactAssessmentCriteria] = {}
        self.embeddings_manager = None
        self._load_business_configuration()
    
    async def _get_embeddings_manager(self):
        """Get embeddings manager (lazy initialization)."""
        if self.embeddings_manager is None:
            from core_infra.ai.embeddings import get_document_embeddings_manager
            self.embeddings_manager = get_document_embeddings_manager()
        return self.embeddings_manager
    
    def _load_business_configuration(self):
        """Load business unit and assessment criteria configuration."""
        # This would typically load from database or configuration files
        # For now, using default configuration
        
        self.business_units = {
            'compliance': BusinessUnit(
                id='compliance',
                name='Compliance Department',
                function='compliance',
                head_user_id='compliance_head',
                stakeholders=['compliance_officer', 'regulatory_analyst'],
                systems=['compliance_system', 'regulatory_reporting'],
                processes=['compliance_monitoring', 'regulatory_filing']
            ),
            'risk': BusinessUnit(
                id='risk',
                name='Risk Management',
                function='risk',
                head_user_id='risk_head',
                stakeholders=['risk_manager', 'risk_analyst'],
                systems=['risk_system', 'model_validation'],
                processes=['risk_assessment', 'stress_testing']
            ),
            'operations': BusinessUnit(
                id='operations',
                name='Operations',
                function='operations',
                head_user_id='operations_head',
                stakeholders=['operations_manager'],
                systems=['core_banking', 'transaction_processing'],
                processes=['daily_operations', 'customer_service']
            ),
            'legal': BusinessUnit(
                id='legal',
                name='Legal Department',
                function='legal',
                head_user_id='legal_head',
                stakeholders=['legal_counsel'],
                systems=['legal_system', 'contract_management'],
                processes=['legal_review', 'contract_approval']
            ),
            'technology': BusinessUnit(
                id='technology',
                name='Technology',
                function='technology',
                head_user_id='tech_head',
                stakeholders=['tech_lead', 'security_officer'],
                systems=['all_systems'],
                processes=['system_development', 'security_management']
            ),
            'finance': BusinessUnit(
                id='finance',
                name='Finance',
                function='finance',
                head_user_id='finance_head',
                stakeholders=['cfo', 'controller'],
                systems=['financial_reporting', 'accounting_system'],
                processes=['financial_reporting', 'budgeting']
            )
        }
        
        # Default assessment criteria
        self.assessment_criteria['default'] = ImpactAssessmentCriteria(
            regulation_keywords=[
                'capital requirements', 'liquidity', 'stress testing', 'aml', 'kyc',
                'cybersecurity', 'data privacy', 'consumer protection', 'market risk',
                'operational risk', 'credit risk', 'reporting', 'governance'
            ],
            business_functions=['compliance', 'risk', 'operations', 'legal', 'technology'],
            compliance_areas=['aml', 'kyc', 'capital', 'liquidity', 'reporting', 'governance'],
            technology_systems=['core_banking', 'risk_system', 'compliance_system'],
            customer_segments=['retail', 'commercial', 'institutional'],
            geographic_regions=['us', 'eu', 'uk', 'apac'],
            impact_indicators={
                'cost_keywords': ['fine', 'penalty', 'investment', 'implementation cost'],
                'urgency_keywords': ['immediate', 'urgent', 'emergency', 'deadline'],
                'scope_keywords': ['all banks', 'all institutions', 'systemically important']
            }
        )
    
    @track_operation("impact_assessor.assess_regulation")
    async def assess_regulatory_impact(self, regulation_id: str, 
                                     regulation_data: Dict[str, Any],
                                     force_reassessment: bool = False) -> RegulatoryImpact:
        """
        Perform comprehensive impact assessment of a regulatory change.
        
        Args:
            regulation_id: Unique identifier for the regulation
            regulation_data: Regulation document data
            force_reassessment: Force new assessment even if one exists
            
        Returns:
            RegulatoryImpact assessment result
        """
        try:
            # Check if assessment already exists
            if not force_reassessment:
                existing_assessment = await self._get_existing_assessment(regulation_id)
                if existing_assessment:
                    logger.info(f"Using existing impact assessment for {regulation_id}")
                    return existing_assessment
            
            logger.info(f"Starting impact assessment for regulation {regulation_id}")
            
            # Extract regulation content
            regulation_text = self._extract_regulation_text(regulation_data)
            regulation_title = regulation_data.get('title', '')
            
            # Perform parallel analysis
            analysis_tasks = [
                self._analyze_content_impact(regulation_text, regulation_title),
                self._analyze_business_unit_impact(regulation_text),
                self._analyze_system_impact(regulation_text),
                self._analyze_process_impact(regulation_text),
                self._estimate_implementation_effort(regulation_text),
                self._estimate_costs_and_timeline(regulation_text, regulation_data),
                self._identify_required_actions(regulation_text),
                self._assess_risk_factors(regulation_text),
                self._find_similar_regulations(regulation_text),
                self._extract_compliance_deadline(regulation_data)
            ]
            
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Process results
            (content_impact, business_units, systems, processes, effort,
             costs_timeline, actions, risks, similar_regs, deadline) = results
            
            # Handle any exceptions in results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Assessment task {i} failed: {result}")
            
            # Determine overall impact level
            overall_impact = self._determine_overall_impact(
                content_impact, regulation_text, regulation_data
            )
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(results, regulation_text)
            
            # Create impact assessment
            impact = RegulatoryImpact(
                regulation_id=regulation_id,
                regulation_title=regulation_title,
                impact_level=overall_impact['level'],
                impact_categories=overall_impact['categories'],
                affected_business_units=business_units if not isinstance(business_units, Exception) else [],
                affected_systems=systems if not isinstance(systems, Exception) else [],
                affected_processes=processes if not isinstance(processes, Exception) else [],
                implementation_effort=effort if not isinstance(effort, Exception) else 'medium',
                estimated_cost=costs_timeline.get('cost') if not isinstance(costs_timeline, Exception) else None,
                estimated_timeline=costs_timeline.get('timeline') if not isinstance(costs_timeline, Exception) else None,
                compliance_deadline=deadline if not isinstance(deadline, Exception) else None,
                required_actions=actions if not isinstance(actions, Exception) else [],
                risk_factors=risks if not isinstance(risks, Exception) else [],
                mitigation_strategies=self._generate_mitigation_strategies(overall_impact, risks),
                dependencies=self._identify_dependencies(business_units, systems),
                confidence_score=confidence,
                assessment_rationale=self._generate_assessment_rationale(overall_impact, results),
                similar_regulations=similar_regs if not isinstance(similar_regs, Exception) else []
            )
            
            # Store assessment
            await self._store_impact_assessment(impact)
            
            logger.info(f"Completed impact assessment for {regulation_id}: {overall_impact['level'].value}")
            
            return impact
            
        except Exception as e:
            logger.error(f"Failed to assess regulatory impact for {regulation_id}: {e}")
            raise
    
    def _extract_regulation_text(self, regulation_data: Dict[str, Any]) -> str:
        """Extract text content from regulation data."""
        content_parts = []
        
        if regulation_data.get('title'):
            content_parts.append(regulation_data['title'])
        
        if regulation_data.get('summary'):
            content_parts.append(regulation_data['summary'])
        
        if regulation_data.get('full_text'):
            content_parts.append(regulation_data['full_text'])
        
        return '\n\n'.join(content_parts)
    
    async def _analyze_content_impact(self, regulation_text: str, title: str) -> Dict[str, Any]:
        """Analyze regulation content to determine impact indicators."""
        try:
            impact_indicators = {
                'urgency_score': 0.0,
                'scope_score': 0.0,
                'complexity_score': 0.0,
                'cost_score': 0.0
            }
            
            text_lower = regulation_text.lower()
            title_lower = title.lower()
            
            # Urgency indicators
            urgency_keywords = [
                'immediate', 'urgent', 'emergency', 'deadline', 'effective immediately',
                'must comply', 'enforcement action', 'penalty', 'violation'
            ]
            urgency_count = sum(1 for keyword in urgency_keywords if keyword in text_lower)
            impact_indicators['urgency_score'] = min(urgency_count / 3.0, 1.0)
            
            # Scope indicators
            scope_keywords = [
                'all banks', 'all institutions', 'systemically important', 'large banks',
                'financial institutions', 'banking organizations', 'covered entities'
            ]
            scope_count = sum(1 for keyword in scope_keywords if keyword in text_lower)
            impact_indicators['scope_score'] = min(scope_count / 2.0, 1.0)
            
            # Complexity indicators
            complexity_keywords = [
                'implementation', 'procedures', 'policies', 'training', 'system changes',
                'process updates', 'documentation', 'reporting requirements'
            ]
            complexity_count = sum(1 for keyword in complexity_keywords if keyword in text_lower)
            impact_indicators['complexity_score'] = min(complexity_count / 4.0, 1.0)
            
            # Cost indicators
            cost_keywords = [
                'capital requirements', 'investment', 'resources', 'staffing',
                'technology upgrades', 'compliance costs', 'operational expenses'
            ]
            cost_count = sum(1 for keyword in cost_keywords if keyword in text_lower)
            impact_indicators['cost_score'] = min(cost_count / 3.0, 1.0)
            
            return impact_indicators
            
        except Exception as e:
            logger.error(f"Content impact analysis failed: {e}")
            return {'urgency_score': 0.5, 'scope_score': 0.5, 'complexity_score': 0.5, 'cost_score': 0.5}
    
    async def _analyze_business_unit_impact(self, regulation_text: str) -> List[str]:
        """Analyze which business units are affected by the regulation."""
        try:
            affected_units = []
            text_lower = regulation_text.lower()
            
            # Business function keywords mapping
            function_keywords = {
                'compliance': ['compliance', 'regulatory', 'supervision', 'examination', 'reporting'],
                'risk': ['risk management', 'credit risk', 'market risk', 'operational risk', 'stress test'],
                'operations': ['operations', 'transaction', 'customer service', 'business continuity'],
                'legal': ['legal', 'litigation', 'contracts', 'agreements', 'documentation'],
                'technology': ['technology', 'systems', 'cybersecurity', 'data', 'information security'],
                'finance': ['financial', 'accounting', 'capital', 'liquidity', 'earnings']
            }
            
            for unit_id, keywords in function_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    affected_units.append(unit_id)
            
            # Always include compliance for regulatory changes
            if 'compliance' not in affected_units:
                affected_units.append('compliance')
            
            return affected_units
            
        except Exception as e:
            logger.error(f"Business unit impact analysis failed: {e}")
            return ['compliance']
    
    async def _analyze_system_impact(self, regulation_text: str) -> List[str]:
        """Analyze which systems are affected by the regulation."""
        try:
            affected_systems = []
            text_lower = regulation_text.lower()
            
            # System keywords mapping
            system_keywords = {
                'core_banking': ['core banking', 'transaction processing', 'account management'],
                'risk_system': ['risk system', 'risk management', 'stress testing', 'model validation'],
                'compliance_system': ['compliance system', 'regulatory reporting', 'monitoring'],
                'trading_system': ['trading', 'market making', 'securities'],
                'payment_system': ['payments', 'wire transfers', 'ach', 'swift'],
                'customer_system': ['customer management', 'crm', 'customer data'],
                'reporting_system': ['reporting', 'data warehouse', 'analytics'],
                'security_system': ['cybersecurity', 'information security', 'access control']
            }
            
            for system_id, keywords in system_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    affected_systems.append(system_id)
            
            return affected_systems
            
        except Exception as e:
            logger.error(f"System impact analysis failed: {e}")
            return []
    
    async def _analyze_process_impact(self, regulation_text: str) -> List[str]:
        """Analyze which business processes are affected by the regulation."""
        try:
            affected_processes = []
            text_lower = regulation_text.lower()
            
            # Process keywords mapping
            process_keywords = {
                'customer_onboarding': ['customer onboarding', 'account opening', 'kyc'],
                'transaction_monitoring': ['transaction monitoring', 'aml monitoring', 'suspicious activity'],
                'risk_assessment': ['risk assessment', 'credit analysis', 'underwriting'],
                'regulatory_reporting': ['regulatory reporting', 'filing', 'submission'],
                'audit_process': ['audit', 'examination', 'review', 'assessment'],
                'incident_management': ['incident', 'breach', 'violation', 'remediation'],
                'change_management': ['change management', 'implementation', 'deployment'],
                'training_process': ['training', 'education', 'awareness']
            }
            
            for process_id, keywords in process_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    affected_processes.append(process_id)
            
            return affected_processes
            
        except Exception as e:
            logger.error(f"Process impact analysis failed: {e}")
            return []
    
    async def _estimate_implementation_effort(self, regulation_text: str) -> str:
        """Estimate implementation effort required."""
        try:
            text_lower = regulation_text.lower()
            effort_score = 0
            
            # High effort indicators
            high_effort_keywords = [
                'new system', 'system development', 'major changes', 'significant investment',
                'extensive training', 'process redesign', 'organizational changes'
            ]
            effort_score += sum(2 for keyword in high_effort_keywords if keyword in text_lower)
            
            # Medium effort indicators
            medium_effort_keywords = [
                'policy updates', 'procedure changes', 'reporting changes', 'training required',
                'system modifications', 'process improvements'
            ]
            effort_score += sum(1 for keyword in medium_effort_keywords if keyword in text_lower)
            
            # Low effort indicators
            low_effort_keywords = [
                'minor changes', 'documentation updates', 'clarification', 'guidance'
            ]
            if any(keyword in text_lower for keyword in low_effort_keywords):
                effort_score = max(effort_score - 1, 0)
            
            # Determine effort level
            if effort_score >= 6:
                return 'significant'
            elif effort_score >= 4:
                return 'high'
            elif effort_score >= 2:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Implementation effort estimation failed: {e}")
            return 'medium'
    
    async def _estimate_costs_and_timeline(self, regulation_text: str, regulation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate implementation costs and timeline."""
        try:
            # Extract deadline information
            effective_date = regulation_data.get('publication_date')
            compliance_deadline = regulation_data.get('compliance_deadline')
            
            # Calculate timeline based on deadline
            timeline = None
            if compliance_deadline:
                time_diff = compliance_deadline - datetime.utcnow()
                if time_diff.days <= 90:
                    timeline = '1-3 months'
                elif time_diff.days <= 180:
                    timeline = '3-6 months'
                elif time_diff.days <= 365:
                    timeline = '6-12 months'
                else:
                    timeline = '12+ months'
            else:
                # Default timeline based on complexity
                text_lower = regulation_text.lower()
                if any(keyword in text_lower for keyword in ['immediate', 'urgent', 'emergency']):
                    timeline = '1-3 months'
                elif any(keyword in text_lower for keyword in ['significant', 'major', 'substantial']):
                    timeline = '6-12 months'
                else:
                    timeline = '3-6 months'
            
            # Estimate costs (simplified model)
            cost_estimate = None
            text_lower = regulation_text.lower()
            
            cost_indicators = 0
            if 'system' in text_lower:
                cost_indicators += 2
            if 'training' in text_lower:
                cost_indicators += 1
            if 'staffing' in text_lower or 'personnel' in text_lower:
                cost_indicators += 2
            if 'capital' in text_lower:
                cost_indicators += 3
            
            # Basic cost estimation (would be more sophisticated in practice)
            if cost_indicators >= 5:
                cost_estimate = 1000000  # $1M+
            elif cost_indicators >= 3:
                cost_estimate = 500000   # $500K
            elif cost_indicators >= 1:
                cost_estimate = 100000   # $100K
            
            return {
                'cost': cost_estimate,
                'timeline': timeline
            }
            
        except Exception as e:
            logger.error(f"Cost and timeline estimation failed: {e}")
            return {'cost': None, 'timeline': '3-6 months'}
    
    async def _identify_required_actions(self, regulation_text: str) -> List[str]:
        """Identify required actions based on regulation content."""
        try:
            actions = []
            text_lower = regulation_text.lower()
            
            # Action indicators
            action_patterns = {
                'policy_update': ['policy', 'policies', 'procedure', 'procedures'],
                'system_change': ['system', 'technology', 'software', 'application'],
                'training': ['training', 'education', 'awareness', 'instruction'],
                'reporting': ['report', 'reporting', 'submission', 'filing'],
                'monitoring': ['monitor', 'monitoring', 'surveillance', 'oversight'],
                'documentation': ['document', 'documentation', 'record', 'records'],
                'assessment': ['assess', 'assessment', 'evaluation', 'review'],
                'testing': ['test', 'testing', 'validation', 'verification']
            }
            
            for action_type, keywords in action_patterns.items():
                if any(keyword in text_lower for keyword in keywords):
                    if action_type == 'policy_update':
                        actions.append('Update policies and procedures')
                    elif action_type == 'system_change':
                        actions.append('Implement system changes')
                    elif action_type == 'training':
                        actions.append('Conduct staff training')
                    elif action_type == 'reporting':
                        actions.append('Implement new reporting requirements')
                    elif action_type == 'monitoring':
                        actions.append('Establish monitoring processes')
                    elif action_type == 'documentation':
                        actions.append('Update documentation and records')
                    elif action_type == 'assessment':
                        actions.append('Conduct impact assessment')
                    elif action_type == 'testing':
                        actions.append('Perform testing and validation')
            
            # Remove duplicates
            actions = list(set(actions))
            
            return actions
            
        except Exception as e:
            logger.error(f"Required actions identification failed: {e}")
            return ['Review regulatory requirements', 'Assess compliance gaps', 'Develop implementation plan']
    
    async def _assess_risk_factors(self, regulation_text: str) -> List[str]:
        """Assess risk factors associated with the regulation."""
        try:
            risks = []
            text_lower = regulation_text.lower()
            
            # Risk indicators
            if any(keyword in text_lower for keyword in ['penalty', 'fine', 'enforcement']):
                risks.append('Regulatory penalties for non-compliance')
            
            if any(keyword in text_lower for keyword in ['system', 'technology', 'implementation']):
                risks.append('Technology implementation risks')
            
            if any(keyword in text_lower for keyword in ['deadline', 'timeline', 'effective date']):
                risks.append('Timeline and deadline risks')
            
            if any(keyword in text_lower for keyword in ['cost', 'investment', 'resources']):
                risks.append('Budget and resource allocation risks')
            
            if any(keyword in text_lower for keyword in ['training', 'personnel', 'staffing']):
                risks.append('Staff readiness and training risks')
            
            if any(keyword in text_lower for keyword in ['customer', 'client', 'service']):
                risks.append('Customer impact and service disruption risks')
            
            if any(keyword in text_lower for keyword in ['data', 'information', 'privacy']):
                risks.append('Data privacy and security risks')
            
            return risks
            
        except Exception as e:
            logger.error(f"Risk factor assessment failed: {e}")
            return ['Implementation complexity risks', 'Compliance deadline risks']
    
    async def _find_similar_regulations(self, regulation_text: str) -> List[str]:
        """Find similar regulations using semantic search."""
        try:
            embeddings_manager = await self._get_embeddings_manager()
            
            # Search for similar documents
            similar_docs = await embeddings_manager.search_similar_documents(
                query_text=regulation_text[:2000],  # Limit text for performance
                limit=5,
                filters=None
            )
            
            # Extract regulation IDs
            similar_regulation_ids = [
                doc.get('document_id') for doc in similar_docs 
                if doc.get('similarity_score', 0) > 0.7
            ]
            
            return similar_regulation_ids
            
        except Exception as e:
            logger.error(f"Similar regulations search failed: {e}")
            return []
    
    async def _extract_compliance_deadline(self, regulation_data: Dict[str, Any]) -> Optional[datetime]:
        """Extract compliance deadline from regulation data."""
        try:
            # Check explicit deadline fields
            if regulation_data.get('compliance_deadline'):
                return regulation_data['compliance_deadline']
            
            if regulation_data.get('effective_date'):
                return regulation_data['effective_date']
            
            # Try to extract from text
            text = regulation_data.get('full_text', '') + ' ' + regulation_data.get('summary', '')
            
            # Look for date patterns (simplified)
            import re
            from dateutil import parser
            
            date_patterns = [
                r'effective\s+(\w+\s+\d{1,2},?\s+\d{4})',
                r'compliance\s+by\s+(\w+\s+\d{1,2},?\s+\d{4})',
                r'must\s+comply\s+by\s+(\w+\s+\d{1,2},?\s+\d{4})'
            ]
            
            for pattern in date_patterns:
                matches = re.search(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        return parser.parse(matches.group(1))
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Compliance deadline extraction failed: {e}")
            return None
    
    def _determine_overall_impact(self, content_impact: Dict[str, Any], 
                                regulation_text: str, regulation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall impact level and categories."""
        try:
            # Calculate weighted impact score
            urgency_weight = 0.3
            scope_weight = 0.25
            complexity_weight = 0.25
            cost_weight = 0.2
            
            if isinstance(content_impact, Exception):
                overall_score = 0.5  # Default medium impact
            else:
                overall_score = (
                    content_impact.get('urgency_score', 0) * urgency_weight +
                    content_impact.get('scope_score', 0) * scope_weight +
                    content_impact.get('complexity_score', 0) * complexity_weight +
                    content_impact.get('cost_score', 0) * cost_weight
                )
            
            # Determine impact level
            if overall_score >= 0.8:
                impact_level = ImpactLevel.CRITICAL
            elif overall_score >= 0.6:
                impact_level = ImpactLevel.HIGH
            elif overall_score >= 0.4:
                impact_level = ImpactLevel.MEDIUM
            elif overall_score >= 0.2:
                impact_level = ImpactLevel.LOW
            else:
                impact_level = ImpactLevel.NONE
            
            # Determine impact categories
            categories = []
            text_lower = regulation_text.lower()
            
            category_keywords = {
                ImpactCategory.OPERATIONAL: ['operations', 'process', 'procedure', 'workflow'],
                ImpactCategory.FINANCIAL: ['financial', 'cost', 'capital', 'liquidity', 'earnings'],
                ImpactCategory.LEGAL: ['legal', 'litigation', 'compliance', 'regulatory'],
                ImpactCategory.REPUTATIONAL: ['reputation', 'public', 'media', 'customer trust'],
                ImpactCategory.STRATEGIC: ['strategic', 'business model', 'competitive'],
                ImpactCategory.TECHNOLOGY: ['technology', 'system', 'cybersecurity', 'data'],
                ImpactCategory.COMPLIANCE: ['compliance', 'regulatory', 'requirement', 'obligation'],
                ImpactCategory.CUSTOMER: ['customer', 'client', 'consumer', 'service']
            }
            
            for category, keywords in category_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    categories.append(category)
            
            # Always include compliance for regulatory changes
            if ImpactCategory.COMPLIANCE not in categories:
                categories.append(ImpactCategory.COMPLIANCE)
            
            return {
                'level': impact_level,
                'categories': categories,
                'score': overall_score
            }
            
        except Exception as e:
            logger.error(f"Overall impact determination failed: {e}")
            return {
                'level': ImpactLevel.MEDIUM,
                'categories': [ImpactCategory.COMPLIANCE],
                'score': 0.5
            }
    
    def _calculate_confidence_score(self, results: List[Any], regulation_text: str) -> float:
        """Calculate confidence score for the assessment."""
        try:
            # Count successful analyses
            successful_analyses = sum(1 for result in results if not isinstance(result, Exception))
            total_analyses = len(results)
            
            # Base confidence on success rate
            base_confidence = successful_analyses / total_analyses
            
            # Adjust based on text quality
            text_quality_score = min(len(regulation_text) / 1000, 1.0)  # More text = higher confidence
            
            # Combine scores
            confidence = (base_confidence * 0.7) + (text_quality_score * 0.3)
            
            return round(confidence, 2)
            
        except Exception as e:
            logger.error(f"Confidence score calculation failed: {e}")
            return 0.5
    
    def _generate_mitigation_strategies(self, overall_impact: Dict[str, Any], risks: List[str]) -> List[str]:
        """Generate mitigation strategies based on impact and risks."""
        strategies = []
        
        impact_level = overall_impact['level']
        categories = overall_impact['categories']
        
        # Impact level based strategies
        if impact_level in [ImpactLevel.CRITICAL, ImpactLevel.HIGH]:
            strategies.append('Establish dedicated project team with senior leadership oversight')
            strategies.append('Implement accelerated timeline with milestone tracking')
        
        if impact_level == ImpactLevel.CRITICAL:
            strategies.append('Consider external consulting support for specialized expertise')
            strategies.append('Implement contingency planning for potential delays')
        
        # Category based strategies
        if ImpactCategory.TECHNOLOGY in categories:
            strategies.append('Conduct thorough system testing in development environment')
            strategies.append('Plan for system rollback procedures')
        
        if ImpactCategory.OPERATIONAL in categories:
            strategies.append('Develop comprehensive training program for affected staff')
            strategies.append('Create detailed process documentation')
        
        if ImpactCategory.FINANCIAL in categories:
            strategies.append('Establish dedicated budget with contingency reserves')
            strategies.append('Monitor costs against budget throughout implementation')
        
        # Risk based strategies
        risk_text = ' '.join(risks).lower()
        if 'deadline' in risk_text:
            strategies.append('Create detailed project timeline with buffer time')
        
        if 'technology' in risk_text:
            strategies.append('Engage IT early in planning process')
        
        if 'training' in risk_text:
            strategies.append('Begin training development early in project lifecycle')
        
        # Remove duplicates
        return list(set(strategies))
    
    def _identify_dependencies(self, business_units: List[str], systems: List[str]) -> List[str]:
        """Identify implementation dependencies."""
        dependencies = []
        
        # Business unit dependencies
        if 'technology' in business_units and len(business_units) > 1:
            dependencies.append('Technology team coordination with business units')
        
        if 'legal' in business_units:
            dependencies.append('Legal review and approval of policy changes')
        
        if 'compliance' in business_units and 'risk' in business_units:
            dependencies.append('Alignment between compliance and risk management approaches')
        
        # System dependencies
        if systems:
            dependencies.append('System testing and validation completion')
            
            if len(systems) > 1:
                dependencies.append('Integration testing between affected systems')
        
        return dependencies
    
    def _generate_assessment_rationale(self, overall_impact: Dict[str, Any], results: List[Any]) -> str:
        """Generate human-readable rationale for the assessment."""
        try:
            impact_level = overall_impact['level']
            categories = overall_impact['categories']
            score = overall_impact['score']
            
            rationale_parts = []
            
            # Impact level explanation
            if impact_level == ImpactLevel.CRITICAL:
                rationale_parts.append("Assessed as CRITICAL impact due to high urgency, broad scope, or significant implementation requirements.")
            elif impact_level == ImpactLevel.HIGH:
                rationale_parts.append("Assessed as HIGH impact based on substantial operational or compliance requirements.")
            elif impact_level == ImpactLevel.MEDIUM:
                rationale_parts.append("Assessed as MEDIUM impact with moderate implementation effort required.")
            elif impact_level == ImpactLevel.LOW:
                rationale_parts.append("Assessed as LOW impact with minimal implementation requirements.")
            else:
                rationale_parts.append("Assessed as having minimal or no business impact.")
            
            # Category explanation
            if categories:
                category_names = [cat.value for cat in categories]
                rationale_parts.append(f"Primary impact areas: {', '.join(category_names)}.")
            
            # Score explanation
            rationale_parts.append(f"Overall impact score: {score:.2f} out of 1.0.")
            
            return ' '.join(rationale_parts)
            
        except Exception as e:
            logger.error(f"Assessment rationale generation failed: {e}")
            return "Automated assessment completed with standard methodology."
    
    async def _get_existing_assessment(self, regulation_id: str) -> Optional[RegulatoryImpact]:
        """Get existing impact assessment from database."""
        try:
            async with get_database() as db:
                query = """
                    SELECT * FROM regulatory_impact_assessments 
                    WHERE regulation_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """
                row = await db.fetchrow(query, regulation_id)
                
                if row:
                    return RegulatoryImpact(
                        regulation_id=row['regulation_id'],
                        regulation_title=row['regulation_title'],
                        impact_level=ImpactLevel(row['impact_level']),
                        impact_categories=[ImpactCategory(cat) for cat in json.loads(row['impact_categories'])],
                        affected_business_units=json.loads(row['affected_business_units']),
                        affected_systems=json.loads(row['affected_systems']),
                        affected_processes=json.loads(row['affected_processes']),
                        implementation_effort=row['implementation_effort'],
                        estimated_cost=row['estimated_cost'],
                        estimated_timeline=row['estimated_timeline'],
                        compliance_deadline=row['compliance_deadline'],
                        required_actions=json.loads(row['required_actions']),
                        risk_factors=json.loads(row['risk_factors']),
                        mitigation_strategies=json.loads(row['mitigation_strategies']),
                        dependencies=json.loads(row['dependencies']),
                        confidence_score=row['confidence_score'],
                        assessment_rationale=row['assessment_rationale'],
                        similar_regulations=json.loads(row['similar_regulations']),
                        created_at=row['created_at'],
                        created_by=row['created_by']
                    )
                
        except Exception as e:
            logger.error(f"Failed to get existing assessment for {regulation_id}: {e}")
        
        return None
    
    async def _store_impact_assessment(self, impact: RegulatoryImpact):
        """Store impact assessment in database."""
        try:
            async with get_database() as db:
                query = """
                    INSERT INTO regulatory_impact_assessments (
                        regulation_id, regulation_title, impact_level, impact_categories,
                        affected_business_units, affected_systems, affected_processes,
                        implementation_effort, estimated_cost, estimated_timeline,
                        compliance_deadline, required_actions, risk_factors,
                        mitigation_strategies, dependencies, confidence_score,
                        assessment_rationale, similar_regulations, created_at, created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                """
                
                await db.execute(
                    query,
                    impact.regulation_id,
                    impact.regulation_title,
                    impact.impact_level.value,
                    json.dumps([cat.value for cat in impact.impact_categories]),
                    json.dumps(impact.affected_business_units),
                    json.dumps(impact.affected_systems),
                    json.dumps(impact.affected_processes),
                    impact.implementation_effort,
                    impact.estimated_cost,
                    impact.estimated_timeline,
                    impact.compliance_deadline,
                    json.dumps(impact.required_actions),
                    json.dumps(impact.risk_factors),
                    json.dumps(impact.mitigation_strategies),
                    json.dumps(impact.dependencies),
                    impact.confidence_score,
                    impact.assessment_rationale,
                    json.dumps(impact.similar_regulations),
                    impact.created_at,
                    impact.created_by
                )
                
        except Exception as e:
            logger.error(f"Failed to store impact assessment: {e}")
            raise
    
    async def get_impact_assessments_by_level(self, impact_level: ImpactLevel, 
                                           limit: int = 50) -> List[RegulatoryImpact]:
        """Get impact assessments filtered by impact level."""
        try:
            async with get_database() as db:
                query = """
                    SELECT * FROM regulatory_impact_assessments 
                    WHERE impact_level = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """
                rows = await db.fetch(query, impact_level.value, limit)
                
                assessments = []
                for row in rows:
                    assessment = RegulatoryImpact(
                        regulation_id=row['regulation_id'],
                        regulation_title=row['regulation_title'],
                        impact_level=ImpactLevel(row['impact_level']),
                        impact_categories=[ImpactCategory(cat) for cat in json.loads(row['impact_categories'])],
                        affected_business_units=json.loads(row['affected_business_units']),
                        affected_systems=json.loads(row['affected_systems']),
                        affected_processes=json.loads(row['affected_processes']),
                        implementation_effort=row['implementation_effort'],
                        estimated_cost=row['estimated_cost'],
                        estimated_timeline=row['estimated_timeline'],
                        compliance_deadline=row['compliance_deadline'],
                        required_actions=json.loads(row['required_actions']),
                        risk_factors=json.loads(row['risk_factors']),
                        mitigation_strategies=json.loads(row['mitigation_strategies']),
                        dependencies=json.loads(row['dependencies']),
                        confidence_score=row['confidence_score'],
                        assessment_rationale=row['assessment_rationale'],
                        similar_regulations=json.loads(row['similar_regulations']),
                        created_at=row['created_at'],
                        created_by=row['created_by']
                    )
                    assessments.append(assessment)
                
                return assessments
                
        except Exception as e:
            logger.error(f"Failed to get impact assessments by level: {e}")
            return [] 