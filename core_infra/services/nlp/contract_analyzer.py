"""
Contract Analyzer for NLP Service

Provides specialized contract analysis and key information extraction
capabilities for legal and financial documents.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContractAnalysisResult:
    """Result structure for contract analysis"""
    contract_type: str
    parties: List[Dict[str, str]]
    key_terms: List[str]
    obligations: List[Dict[str, Any]]
    important_dates: List[Dict[str, Any]]
    financial_details: List[Dict[str, Any]]
    risk_factors: List[str]
    confidence_score: float

class ContractAnalyzer:
    """
    Specialized contract analyzer for legal and financial documents
    """
    
    def __init__(self):
        self.contract_patterns = self._load_contract_patterns()
        
    def _load_contract_patterns(self) -> Dict[str, Any]:
        """Load contract analysis patterns"""
        return {
            "party_keywords": [
                "party", "parties", "entity", "company", "corporation",
                "individual", "person", "organization", "client"
            ],
            "obligation_keywords": [
                "shall", "must", "agree", "covenant", "undertake",
                "commit", "promise", "guarantee", "warrant"
            ],
            "financial_keywords": [
                "payment", "fee", "cost", "price", "amount", "sum",
                "consideration", "compensation", "salary", "wage"
            ],
            "date_keywords": [
                "date", "deadline", "due", "expire", "term", "period",
                "commencement", "termination", "renewal"
            ]
        }
        
    async def analyze_contract(self, contract_text: str, metadata: Optional[Dict[str, Any]] = None) -> ContractAnalysisResult:
        """
        Analyze contract document and extract key information
        
        Args:
            contract_text: The contract document text
            metadata: Additional metadata about the document
            
        Returns:
            ContractAnalysisResult with extracted information
        """
        try:
            contract_type = self._classify_contract_type(contract_text)
            parties = self._extract_parties(contract_text)
            key_terms = self._extract_key_terms(contract_text)
            obligations = self._extract_obligations(contract_text)
            important_dates = self._extract_dates(contract_text)
            financial_details = self._extract_financial_details(contract_text)
            risk_factors = self._identify_risk_factors(contract_text)
            confidence_score = 0.85  # Basic confidence score
            
            return ContractAnalysisResult(
                contract_type=contract_type,
                parties=parties,
                key_terms=key_terms,
                obligations=obligations,
                important_dates=important_dates,
                financial_details=financial_details,
                risk_factors=risk_factors,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Contract analysis error: {str(e)}")
            raise
            
    def _classify_contract_type(self, text: str) -> str:
        """Classify the type of contract"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['loan', 'credit', 'lending']):
            return 'loan_agreement'
        elif any(word in text_lower for word in ['employment', 'job', 'position']):
            return 'employment_contract'
        elif any(word in text_lower for word in ['service', 'consulting', 'professional']):
            return 'service_agreement'
        elif any(word in text_lower for word in ['lease', 'rental', 'rent']):
            return 'lease_agreement'
        elif any(word in text_lower for word in ['sale', 'purchase', 'buy', 'sell']):
            return 'sales_contract'
        elif any(word in text_lower for word in ['partnership', 'joint venture']):
            return 'partnership_agreement'
        else:
            return 'general_contract'
            
    def _extract_parties(self, text: str) -> List[Dict[str, str]]:
        """Extract contract parties"""
        parties = []
        lines = text.split('\n')
        
        for line in lines[:20]:  # Check first 20 lines
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in self.contract_patterns["party_keywords"]):
                if len(line.strip()) > 10:
                    parties.append({
                        'text': line.strip(),
                        'type': 'party_reference'
                    })
                    
        return parties[:5]  # Return top 5 party references
        
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key contract terms"""
        terms = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            # Look for important terms and definitions
            if any(word in sentence_lower for word in ['define', 'means', 'include', 'exclude']):
                if len(sentence.strip()) > 20:
                    terms.append(sentence.strip())
                    
        return terms[:10]  # Return top 10 terms
        
    def _extract_obligations(self, text: str) -> List[Dict[str, Any]]:
        """Extract contract obligations"""
        obligations = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in self.contract_patterns["obligation_keywords"]):
                if len(sentence.strip()) > 20:
                    # Determine which party has the obligation
                    party = "unspecified"
                    if "party a" in sentence_lower or "first party" in sentence_lower:
                        party = "party_a"
                    elif "party b" in sentence_lower or "second party" in sentence_lower:
                        party = "party_b"
                    
                    obligations.append({
                        'text': sentence.strip(),
                        'party': party,
                        'type': 'contractual_obligation'
                    })
                    
        return obligations[:10]  # Return top 10 obligations
        
    def _extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract important dates from contract"""
        dates = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in self.contract_patterns["date_keywords"]):
                if len(sentence.strip()) > 15:
                    # Try to identify date type
                    date_type = "general"
                    if "commence" in sentence_lower or "start" in sentence_lower:
                        date_type = "commencement"
                    elif "terminate" in sentence_lower or "end" in sentence_lower:
                        date_type = "termination"
                    elif "due" in sentence_lower or "deadline" in sentence_lower:
                        date_type = "deadline"
                    elif "expire" in sentence_lower:
                        date_type = "expiration"
                    
                    dates.append({
                        'text': sentence.strip(),
                        'type': date_type,
                        'importance': 'high' if date_type in ['commencement', 'termination'] else 'medium'
                    })
                    
        return dates[:8]  # Return top 8 dates
        
    def _extract_financial_details(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial information from contract"""
        financial_details = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in self.contract_patterns["financial_keywords"]):
                if len(sentence.strip()) > 15:
                    # Try to identify financial detail type
                    detail_type = "general"
                    if "payment" in sentence_lower:
                        detail_type = "payment_terms"
                    elif "fee" in sentence_lower:
                        detail_type = "fees"
                    elif "penalty" in sentence_lower:
                        detail_type = "penalties"
                    elif "interest" in sentence_lower:
                        detail_type = "interest"
                    
                    financial_details.append({
                        'text': sentence.strip(),
                        'type': detail_type,
                        'category': 'financial_obligation'
                    })
                    
        return financial_details[:8]  # Return top 8 financial details
        
    def _identify_risk_factors(self, text: str) -> List[str]:
        """Identify potential risk factors in the contract"""
        risk_factors = []
        text_lower = text.lower()
        
        risk_indicators = [
            ('unlimited liability', 'High financial risk due to unlimited liability'),
            ('personal guarantee', 'Personal assets at risk due to personal guarantee'),
            ('no termination clause', 'Cannot terminate contract easily'),
            ('automatic renewal', 'Contract may auto-renew unexpectedly'),
            ('penalty clause', 'Penalties for non-compliance'),
            ('indemnification', 'Potential liability for third-party claims'),
            ('liquidated damages', 'Pre-determined damages for breach'),
            ('force majeure', 'Limited protection for unforeseeable events'),
            ('governing law', 'Potential jurisdictional complications'),
            ('arbitration', 'Limited legal recourse options')
        ]
        
        for indicator, description in risk_indicators:
            if indicator in text_lower:
                risk_factors.append(description)
                
        return risk_factors[:6]  # Return top 6 risk factors 