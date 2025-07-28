"""
Policy Interpreter for NLP Service

Provides specialized policy analysis and interpretation capabilities
for regulatory and compliance documents.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PolicyAnalysisResult:
    """Result structure for policy analysis"""
    policy_type: str
    key_requirements: List[str]
    compliance_obligations: List[str]
    deadlines: List[Dict[str, Any]]
    penalties: List[str]
    applicability: Dict[str, Any]
    risk_level: str
    confidence_score: float

class PolicyInterpreter:
    """
    Specialized policy interpreter for regulatory and compliance documents
    """
    
    def __init__(self):
        self.policy_patterns = self._load_policy_patterns()
        
    def _load_policy_patterns(self) -> Dict[str, Any]:
        """Load policy analysis patterns"""
        return {
            "requirement_keywords": [
                "shall", "must", "required", "mandatory", "obligated",
                "prohibited", "forbidden", "not permitted"
            ],
            "deadline_keywords": [
                "deadline", "due date", "by", "within", "before",
                "no later than", "effective date"
            ],
            "penalty_keywords": [
                "penalty", "fine", "sanctions", "enforcement",
                "violation", "breach", "non-compliance"
            ]
        }
        
    async def analyze_policy(self, policy_text: str, metadata: Optional[Dict[str, Any]] = None) -> PolicyAnalysisResult:
        """
        Analyze policy document and extract key information
        
        Args:
            policy_text: The policy document text
            metadata: Additional metadata about the document
            
        Returns:
            PolicyAnalysisResult with extracted information
        """
        try:
            # Basic policy analysis implementation
            policy_type = self._classify_policy_type(policy_text)
            key_requirements = self._extract_requirements(policy_text)
            compliance_obligations = self._extract_obligations(policy_text)
            deadlines = self._extract_deadlines(policy_text)
            penalties = self._extract_penalties(policy_text)
            applicability = self._determine_applicability(policy_text, metadata)
            risk_level = self._assess_risk_level(policy_text)
            confidence_score = 0.8  # Basic confidence score
            
            return PolicyAnalysisResult(
                policy_type=policy_type,
                key_requirements=key_requirements,
                compliance_obligations=compliance_obligations,
                deadlines=deadlines,
                penalties=penalties,
                applicability=applicability,
                risk_level=risk_level,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Policy analysis error: {str(e)}")
            raise
            
    def _classify_policy_type(self, text: str) -> str:
        """Classify the type of policy document"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['aml', 'anti-money laundering', 'kyc']):
            return 'aml_kyc'
        elif any(word in text_lower for word in ['gdpr', 'data protection', 'privacy']):
            return 'data_protection'
        elif any(word in text_lower for word in ['sox', 'sarbanes-oxley', 'financial reporting']):
            return 'financial_reporting'
        elif any(word in text_lower for word in ['mifid', 'markets in financial instruments']):
            return 'investment_services'
        else:
            return 'general_compliance'
            
    def _extract_requirements(self, text: str) -> List[str]:
        """Extract key requirements from policy text"""
        requirements = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in self.policy_patterns["requirement_keywords"]):
                if len(sentence.strip()) > 20:  # Filter out very short sentences
                    requirements.append(sentence.strip())
                    
        return requirements[:10]  # Return top 10 requirements
        
    def _extract_obligations(self, text: str) -> List[str]:
        """Extract compliance obligations"""
        obligations = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(word in sentence_lower for word in ['obligation', 'duty', 'responsibility', 'liable']):
                if len(sentence.strip()) > 20:
                    obligations.append(sentence.strip())
                    
        return obligations[:5]  # Return top 5 obligations
        
    def _extract_deadlines(self, text: str) -> List[Dict[str, Any]]:
        """Extract deadlines and important dates"""
        deadlines = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in self.policy_patterns["deadline_keywords"]):
                deadlines.append({
                    'text': sentence.strip(),
                    'type': 'compliance_deadline',
                    'urgency': 'medium'
                })
                
        return deadlines[:5]  # Return top 5 deadlines
        
    def _extract_penalties(self, text: str) -> List[str]:
        """Extract penalty information"""
        penalties = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in self.policy_patterns["penalty_keywords"]):
                if len(sentence.strip()) > 20:
                    penalties.append(sentence.strip())
                    
        return penalties[:5]  # Return top 5 penalties
        
    def _determine_applicability(self, text: str, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine policy applicability"""
        applicability = {
            'entity_types': [],
            'geographic_scope': [],
            'industry_sectors': [],
            'asset_size_threshold': None
        }
        
        text_lower = text.lower()
        
        # Entity types
        if 'bank' in text_lower:
            applicability['entity_types'].append('banks')
        if 'investment' in text_lower:
            applicability['entity_types'].append('investment_firms')
        if 'insurance' in text_lower:
            applicability['entity_types'].append('insurance_companies')
            
        # Geographic scope
        if any(region in text_lower for region in ['eu', 'european union', 'europe']):
            applicability['geographic_scope'].append('EU')
        if any(country in text_lower for country in ['us', 'united states', 'america']):
            applicability['geographic_scope'].append('US')
            
        return applicability
        
    def _assess_risk_level(self, text: str) -> str:
        """Assess the risk level of non-compliance"""
        text_lower = text.lower()
        
        # High risk indicators
        if any(word in text_lower for word in ['criminal', 'prosecution', 'imprisonment', 'license revocation']):
            return 'high'
        elif any(word in text_lower for word in ['significant penalty', 'substantial fine', 'regulatory action']):
            return 'high'
        elif any(word in text_lower for word in ['penalty', 'fine', 'sanctions']):
            return 'medium'
        else:
            return 'low' 