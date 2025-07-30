"""
Regulatory Analyzer - AI-Powered Document Analysis
Extracts obligations, assesses impact, and generates regulatory insights.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
import openai
from anthropic import Anthropic
import re

from core_infra.database.connection import get_database
from core_infra.services.monitoring import track_operation
from core_infra.config import get_settings
from core_infra.ai.embeddings import get_embeddings_client
from core_infra.ai.vector_store import get_vector_store

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class RegulatoryObligation:
    """Extracted regulatory obligation."""
    text: str
    obligation_type: str  # 'mandatory', 'conditional', 'best_practice'
    compliance_deadline: Optional[datetime]
    penalty_description: Optional[str]
    applicable_entities: List[str]
    section_reference: str
    confidence_score: float


@dataclass
class DocumentInsight:
    """AI-generated insight about a regulatory document."""
    insight_type: str  # 'summary', 'key_changes', 'impact_analysis', 'compliance_guidance'
    insight_text: str
    confidence_level: float
    supporting_evidence: List[str]


@dataclass
class ImpactAssessment:
    """Regulatory impact assessment."""
    business_impact_level: str  # 'critical', 'high', 'medium', 'low', 'none'
    customer_impact_level: str
    cost_impact_estimate: Optional[float]
    implementation_effort: str  # 'low', 'medium', 'high', 'significant'
    implementation_timeline: str
    affected_business_units: List[str]
    affected_systems: List[str]
    required_actions: List[str]
    dependencies: List[str]
    risk_factors: List[str]


class RegulatoryAnalyzer:
    """
    AI-powered regulatory document analyzer that extracts obligations,
    assesses impact, and generates actionable insights.
    """
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.embeddings_client = None
        self.vector_store = None
        self._initialize_ai_clients()
        
    def _initialize_ai_clients(self):
        """Initialize AI service clients."""
        try:
            if settings.openai_api_key:
                openai.api_key = settings.openai_api_key.get_secret_value()
                self.openai_client = openai
                
            if settings.claude_api_key:
                self.anthropic_client = Anthropic(
                    api_key=settings.claude_api_key.get_secret_value()
                )
                
            self.embeddings_client = get_embeddings_client()
            self.vector_store = get_vector_store()
            
        except Exception as e:
            logger.warning(f"Failed to initialize some AI clients: {e}")
    
    @track_operation("regulatory_analyzer.analyze_document")
    async def analyze_document(self, document_id: str, document_data: Dict[str, Any]):
        """Perform comprehensive AI analysis of a regulatory document."""
        try:
            logger.info(f"Starting AI analysis of document {document_id}")
            
            # Record AI model run
            model_run_id = await self._record_model_run(document_id, document_data)
            
            # Extract text content
            text_content = self._extract_text_content(document_data)
            if not text_content:
                logger.warning(f"No text content found for document {document_id}")
                return
            
            # Perform parallel analysis tasks
            analysis_tasks = [
                self._extract_obligations(text_content, document_data),
                self._generate_summary(text_content, document_data),
                self._assess_impact(text_content, document_data),
                self._identify_key_changes(text_content, document_data),
                self._generate_compliance_guidance(text_content, document_data),
                self._extract_entities_and_dates(text_content),
                self._classify_document_topics(text_content),
                self._assess_urgency(text_content, document_data)
            ]
            
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Process results
            obligations, summary, impact, key_changes, guidance, entities_dates, topics, urgency = results
            
            # Store analysis results
            await self._store_analysis_results(
                document_id, model_run_id, obligations, summary, impact, 
                key_changes, guidance, entities_dates, topics, urgency
            )
            
            # Generate vector embeddings for similarity search
            await self._generate_document_embeddings(document_id, text_content, document_data)
            
            # Update model run status
            await self._update_model_run_status(model_run_id, "completed")
            
            logger.info(f"Completed AI analysis of document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to analyze document {document_id}: {e}", exc_info=True)
            if 'model_run_id' in locals():
                await self._update_model_run_status(model_run_id, "failed", str(e))
            raise
    
    def _extract_text_content(self, document_data: Dict[str, Any]) -> str:
        """Extract clean text content from document data."""
        full_text = document_data.get('full_text', '')
        summary = document_data.get('summary', '')
        title = document_data.get('title', '')
        
        # Combine all text content
        content_parts = [title, summary, full_text]
        return '\n\n'.join(part for part in content_parts if part)
    
    async def _extract_obligations(self, text: str, document_data: Dict[str, Any]) -> List[RegulatoryObligation]:
        """Extract regulatory obligations from document text using AI."""
        try:
            prompt = self._build_obligations_prompt(text, document_data)
            
            if self.openai_client:
                response = await self._call_openai_gpt4(prompt, max_tokens=2000)
                obligations = self._parse_obligations_response(response)
            elif self.anthropic_client:
                response = await self._call_claude(prompt, max_tokens=2000)
                obligations = self._parse_obligations_response(response)
            else:
                # Fallback to rule-based extraction
                obligations = self._extract_obligations_rule_based(text)
            
            logger.info(f"Extracted {len(obligations)} obligations")
            return obligations
            
        except Exception as e:
            logger.error(f"Failed to extract obligations: {e}")
            return []
    
    def _build_obligations_prompt(self, text: str, document_data: Dict[str, Any]) -> str:
        """Build prompt for obligation extraction."""
        document_type = document_data.get('document_type', 'document')
        jurisdiction = document_data.get('jurisdiction', 'unknown')
        
        return f"""
You are a regulatory compliance expert analyzing a {document_type} from {jurisdiction}.

Extract all specific regulatory obligations from the following document. For each obligation, provide:

1. The exact text of the obligation
2. Whether it's mandatory, conditional, or a best practice
3. Any compliance deadlines mentioned
4. Penalties or consequences for non-compliance
5. Which types of entities this applies to (banks, fintech, all financial institutions, etc.)
6. The section or paragraph reference
7. Your confidence level (0.0 to 1.0) in this extraction

Document text:
{text[:4000]}  # Limit to avoid token limits

Format your response as a JSON array of obligations with the following structure:
{{
  "obligations": [
    {{
      "text": "exact obligation text",
      "type": "mandatory|conditional|best_practice",
      "deadline": "YYYY-MM-DD or null",
      "penalty": "penalty description or null",
      "applicable_entities": ["entity type 1", "entity type 2"],
      "section_reference": "section reference",
      "confidence_score": 0.95
    }}
  ]
}}

Only extract clear, specific obligations. Do not include general statements or background information.
"""
    
    async def _call_openai_gpt4(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call OpenAI GPT-4 API."""
        try:
            response = await self.openai_client.ChatCompletion.acreate(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a regulatory compliance expert specializing in financial services."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=settings.openai_temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    async def _call_claude(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call Anthropic Claude API."""
        try:
            response = await self.anthropic_client.messages.create(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                temperature=settings.openai_temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise
    
    def _parse_obligations_response(self, response: str) -> List[RegulatoryObligation]:
        """Parse AI response into RegulatoryObligation objects."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in obligations response")
                return []
            
            data = json.loads(json_match.group())
            obligations = []
            
            for item in data.get('obligations', []):
                deadline = None
                if item.get('deadline'):
                    try:
                        deadline = datetime.fromisoformat(item['deadline'])
                    except:
                        pass
                
                obligation = RegulatoryObligation(
                    text=item.get('text', ''),
                    obligation_type=item.get('type', 'mandatory'),
                    compliance_deadline=deadline,
                    penalty_description=item.get('penalty'),
                    applicable_entities=item.get('applicable_entities', []),
                    section_reference=item.get('section_reference', ''),
                    confidence_score=float(item.get('confidence_score', 0.5))
                )
                obligations.append(obligation)
            
            return obligations
            
        except Exception as e:
            logger.error(f"Failed to parse obligations response: {e}")
            return []
    
    def _extract_obligations_rule_based(self, text: str) -> List[RegulatoryObligation]:
        """Fallback rule-based obligation extraction."""
        obligations = []
        
        # Simple pattern matching for obligations
        obligation_patterns = [
            r'(must|shall|required to|obligated to)\s+([^.]+)',
            r'(banks|institutions|entities)\s+(must|shall)\s+([^.]+)',
            r'(compliance|conformance)\s+with\s+([^.]+)\s+(is required|mandatory)'
        ]
        
        for pattern in obligation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                obligation = RegulatoryObligation(
                    text=match.group(0),
                    obligation_type='mandatory',
                    compliance_deadline=None,
                    penalty_description=None,
                    applicable_entities=['financial institutions'],
                    section_reference='',
                    confidence_score=0.6
                )
                obligations.append(obligation)
        
        return obligations[:10]  # Limit to avoid noise
    
    async def _generate_summary(self, text: str, document_data: Dict[str, Any]) -> str:
        """Generate AI-powered summary of the regulatory document."""
        try:
            prompt = f"""
Provide a concise executive summary of this regulatory document focusing on:
1. Key regulatory changes
2. Who is affected
3. Important deadlines
4. Compliance requirements
5. Business impact

Document: {text[:3000]}

Summary (max 200 words):
"""
            
            if self.openai_client:
                return await self._call_openai_gpt4(prompt, max_tokens=300)
            elif self.anthropic_client:
                return await self._call_claude(prompt, max_tokens=300)
            else:
                return self._generate_summary_rule_based(text, document_data)
                
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return document_data.get('summary', '')[:500]
    
    def _generate_summary_rule_based(self, text: str, document_data: Dict[str, Any]) -> str:
        """Generate rule-based summary as fallback."""
        # Extract first few sentences as summary
        sentences = re.split(r'[.!?]+', text)
        summary_sentences = sentences[:3]
        return '. '.join(s.strip() for s in summary_sentences if s.strip()) + '.'
    
    async def _assess_impact(self, text: str, document_data: Dict[str, Any]) -> ImpactAssessment:
        """Assess the business impact of the regulatory document."""
        try:
            prompt = f"""
Assess the business impact of this regulatory document. Consider:

1. Business impact level (critical/high/medium/low/none)
2. Customer impact level
3. Estimated implementation cost (if mentioned)
4. Implementation effort required
5. Timeline for implementation
6. Affected business units
7. Affected systems
8. Required actions
9. Dependencies
10. Risk factors

Document: {text[:2500]}

Provide assessment as JSON:
{{
  "business_impact_level": "high",
  "customer_impact_level": "medium",
  "cost_impact_estimate": null,
  "implementation_effort": "significant",
  "implementation_timeline": "6-12 months",
  "affected_business_units": ["compliance", "risk", "operations"],
  "affected_systems": ["core banking", "reporting"],
  "required_actions": ["update policies", "train staff"],
  "dependencies": ["vendor updates", "system changes"],
  "risk_factors": ["regulatory penalties", "operational risk"]
}}
"""
            
            if self.openai_client:
                response = await self._call_openai_gpt4(prompt, max_tokens=800)
                return self._parse_impact_assessment(response)
            elif self.anthropic_client:
                response = await self._call_claude(prompt, max_tokens=800)
                return self._parse_impact_assessment(response)
            else:
                return self._assess_impact_rule_based(text, document_data)
                
        except Exception as e:
            logger.error(f"Failed to assess impact: {e}")
            return self._get_default_impact_assessment()
    
    def _parse_impact_assessment(self, response: str) -> ImpactAssessment:
        """Parse AI response into ImpactAssessment object."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return self._get_default_impact_assessment()
            
            data = json.loads(json_match.group())
            
            return ImpactAssessment(
                business_impact_level=data.get('business_impact_level', 'medium'),
                customer_impact_level=data.get('customer_impact_level', 'low'),
                cost_impact_estimate=data.get('cost_impact_estimate'),
                implementation_effort=data.get('implementation_effort', 'medium'),
                implementation_timeline=data.get('implementation_timeline', '3-6 months'),
                affected_business_units=data.get('affected_business_units', []),
                affected_systems=data.get('affected_systems', []),
                required_actions=data.get('required_actions', []),
                dependencies=data.get('dependencies', []),
                risk_factors=data.get('risk_factors', [])
            )
            
        except Exception as e:
            logger.error(f"Failed to parse impact assessment: {e}")
            return self._get_default_impact_assessment()
    
    def _assess_impact_rule_based(self, text: str, document_data: Dict[str, Any]) -> ImpactAssessment:
        """Rule-based impact assessment as fallback."""
        doc_type = document_data.get('document_type', '')
        title = document_data.get('title', '').lower()
        
        # Determine impact based on document type and keywords
        if doc_type == 'enforcement' or 'penalty' in title:
            business_impact = 'critical'
        elif doc_type == 'regulation' or 'final rule' in title:
            business_impact = 'high'
        elif doc_type == 'guidance':
            business_impact = 'medium'
        else:
            business_impact = 'low'
        
        return ImpactAssessment(
            business_impact_level=business_impact,
            customer_impact_level='medium',
            cost_impact_estimate=None,
            implementation_effort='medium',
            implementation_timeline='3-6 months',
            affected_business_units=['compliance', 'risk'],
            affected_systems=[],
            required_actions=['review requirements', 'update procedures'],
            dependencies=[],
            risk_factors=['regulatory penalties']
        )
    
    def _get_default_impact_assessment(self) -> ImpactAssessment:
        """Get default impact assessment."""
        return ImpactAssessment(
            business_impact_level='medium',
            customer_impact_level='low',
            cost_impact_estimate=None,
            implementation_effort='medium',
            implementation_timeline='3-6 months',
            affected_business_units=['compliance'],
            affected_systems=[],
            required_actions=['review document'],
            dependencies=[],
            risk_factors=[]
        )
    
    async def _identify_key_changes(self, text: str, document_data: Dict[str, Any]) -> List[str]:
        """Identify key regulatory changes in the document."""
        try:
            prompt = f"""
Identify the key regulatory changes introduced in this document. Focus on:
1. New requirements
2. Modified existing requirements
3. Removed requirements
4. Changed deadlines
5. Updated procedures

Document: {text[:2500]}

List the key changes (max 5):
"""
            
            if self.openai_client:
                response = await self._call_openai_gpt4(prompt, max_tokens=400)
                return self._extract_changes_from_response(response)
            elif self.anthropic_client:
                response = await self._call_claude(prompt, max_tokens=400)
                return self._extract_changes_from_response(response)
            else:
                return self._identify_changes_rule_based(text)
                
        except Exception as e:
            logger.error(f"Failed to identify key changes: {e}")
            return []
    
    def _extract_changes_from_response(self, response: str) -> List[str]:
        """Extract changes list from AI response."""
        changes = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                # Remove list markers
                change = re.sub(r'^[-•\d.\s]+', '', line).strip()
                if change:
                    changes.append(change)
        
        return changes[:5]  # Limit to 5 key changes
    
    def _identify_changes_rule_based(self, text: str) -> List[str]:
        """Rule-based change identification as fallback."""
        changes = []
        
        # Look for change-indicating keywords
        change_patterns = [
            r'(new|introduce[ds]?|establish[es]?)\s+([^.]{20,100})',
            r'(modify|modifies|amend[s]?|change[s]?)\s+([^.]{20,100})',
            r'(effective|beginning)\s+([^.]{20,100})',
            r'(require[ds]?|must|shall)\s+([^.]{20,100})'
        ]
        
        for pattern in change_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                change = match.group(0)
                if len(change) > 30:  # Filter out very short matches
                    changes.append(change)
                if len(changes) >= 5:
                    break
        
        return changes
    
    async def _generate_compliance_guidance(self, text: str, document_data: Dict[str, Any]) -> str:
        """Generate compliance guidance based on the document."""
        try:
            prompt = f"""
Provide practical compliance guidance for financial institutions based on this regulatory document:

1. Immediate actions required
2. Steps to ensure compliance
3. Best practices
4. Common pitfalls to avoid
5. Recommended timeline

Document: {text[:2500]}

Compliance Guidance:
"""
            
            if self.openai_client:
                return await self._call_openai_gpt4(prompt, max_tokens=500)
            elif self.anthropic_client:
                return await self._call_claude(prompt, max_tokens=500)
            else:
                return "Review document and assess compliance requirements with legal counsel."
                
        except Exception as e:
            logger.error(f"Failed to generate compliance guidance: {e}")
            return "Consult with compliance team to assess requirements."
    
    async def _extract_entities_and_dates(self, text: str) -> Dict[str, List[str]]:
        """Extract entities and important dates from the document."""
        entities = {
            'organizations': [],
            'dates': [],
            'regulations': [],
            'financial_terms': []
        }
        
        # Simple regex patterns for entity extraction
        org_pattern = r'\b[A-Z][A-Za-z\s&]{5,30}(?:Bank|Corporation|Authority|Commission|Board|Agency|Institution)\b'
        date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        regulation_pattern = r'\b(?:Section|Part|Rule|Regulation)\s+\d+[A-Za-z]?\b'
        
        entities['organizations'] = list(set(re.findall(org_pattern, text)))[:10]
        entities['dates'] = list(set(re.findall(date_pattern, text)))[:10]
        entities['regulations'] = list(set(re.findall(regulation_pattern, text)))[:10]
        
        return entities
    
    async def _classify_document_topics(self, text: str) -> List[str]:
        """Classify document into regulatory topics."""
        topics = []
        
        topic_keywords = {
            'anti_money_laundering': ['anti-money laundering', 'aml', 'suspicious activity', 'customer due diligence'],
            'know_your_customer': ['know your customer', 'kyc', 'customer identification'],
            'capital_requirements': ['capital', 'tier 1', 'common equity', 'capital ratio'],
            'liquidity': ['liquidity', 'liquid assets', 'liquidity coverage ratio'],
            'stress_testing': ['stress test', 'stress testing', 'ccar', 'dfast'],
            'cybersecurity': ['cybersecurity', 'cyber security', 'data security', 'incident response'],
            'consumer_protection': ['consumer protection', 'fair lending', 'unfair practices'],
            'market_risk': ['market risk', 'trading', 'value at risk', 'var'],
            'operational_risk': ['operational risk', 'business continuity', 'vendor management'],
            'credit_risk': ['credit risk', 'loan loss', 'allowance', 'provisioning']
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    async def _assess_urgency(self, text: str, document_data: Dict[str, Any]) -> str:
        """Assess urgency level of the regulatory document."""
        text_lower = text.lower()
        doc_type = document_data.get('document_type', '')
        
        # High urgency indicators
        urgent_terms = ['immediate', 'emergency', 'urgent', 'cease and desist', 'enforcement action']
        
        if doc_type == 'enforcement' or any(term in text_lower for term in urgent_terms):
            return 'urgent'
        elif doc_type == 'regulation':
            return 'high'
        elif doc_type == 'guidance':
            return 'medium'
        else:
            return 'normal'
    
    async def _generate_document_embeddings(self, document_id: str, text: str, document_data: Dict[str, Any]):
        """Generate vector embeddings for document similarity search."""
        try:
            if not self.embeddings_client:
                return
            
            # Generate embeddings for the document
            embeddings = await self.embeddings_client.generate_embeddings(text)
            
            # Store in vector database
            metadata = {
                'document_id': document_id,
                'title': document_data.get('title', ''),
                'document_type': document_data.get('document_type', ''),
                'jurisdiction': document_data.get('jurisdiction', ''),
                'publication_date': document_data.get('publication_date', '').isoformat() if document_data.get('publication_date') else None
            }
            
            await self.vector_store.store_document(
                document_id=document_id,
                embeddings=embeddings,
                metadata=metadata,
                text=text[:1000]  # Store first 1000 chars for context
            )
            
        except Exception as e:
            logger.error(f"Failed to generate document embeddings: {e}")
    
    async def _record_model_run(self, document_id: str, document_data: Dict[str, Any]) -> str:
        """Record AI model run in database."""
        async with get_database() as db:
            query = """
                INSERT INTO ai_model_runs (
                    model_name, model_version, input_data, status, created_at
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """
            
            input_data = {
                'document_id': document_id,
                'document_title': document_data.get('title', ''),
                'document_type': document_data.get('document_type', ''),
                'analysis_type': 'regulatory_document_analysis'
            }
            
            result = await db.fetchrow(
                query, 'regulatory_analyzer', '1.0', 
                json.dumps(input_data), 'pending', datetime.utcnow()
            )
            return result['id']
    
    async def _update_model_run_status(self, model_run_id: str, status: str, error_message: str = None):
        """Update AI model run status."""
        async with get_database() as db:
            # First get the start time of the model run
            start_time_query = """
                SELECT created_at FROM ai_model_runs WHERE id = $1
            """
            start_time_row = await db.fetchrow(start_time_query, model_run_id)
            
            # Calculate actual processing time
            if start_time_row and start_time_row['created_at']:
                start_time = start_time_row['created_at']
                end_time = datetime.utcnow()
                processing_time = int((end_time - start_time).total_seconds() * 1000)  # Convert to milliseconds
            else:
                processing_time = 0  # Default if we can't calculate
            
            # Update the model run with status and processing time
            query = """
                UPDATE ai_model_runs 
                SET status = $1, error_message = $2, processing_time_ms = $3, updated_at = $4
                WHERE id = $5
            """
            await db.execute(query, status, error_message, processing_time, datetime.utcnow(), model_run_id)
    
    async def _store_analysis_results(self, document_id: str, model_run_id: str, 
                                    obligations: List[RegulatoryObligation],
                                    summary: str, impact: ImpactAssessment,
                                    key_changes: List[str], guidance: str,
                                    entities_dates: Dict[str, List[str]],
                                    topics: List[str], urgency: str):
        """Store all analysis results in database."""
        try:
            async with get_database() as db:
                # Store regulatory obligations
                for obligation in obligations:
                    await db.execute("""
                        INSERT INTO regulatory_obligations (
                            document_id, obligation_text, obligation_type,
                            compliance_deadline, penalty_description,
                            applicable_entities, section_reference
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, document_id, obligation.text, obligation.obligation_type,
                         obligation.compliance_deadline, obligation.penalty_description,
                         json.dumps(obligation.applicable_entities), obligation.section_reference)
                
                # Store regulatory insights
                insights = [
                    ('summary', summary),
                    ('compliance_guidance', guidance),
                    ('key_changes', '\n'.join(key_changes)),
                    ('entities_and_dates', json.dumps(entities_dates)),
                    ('topics', json.dumps(topics)),
                    ('urgency_assessment', urgency)
                ]
                
                for insight_type, insight_text in insights:
                    if insight_text:
                        await db.execute("""
                            INSERT INTO regulatory_insights (
                                document_id, insight_type, insight_text,
                                confidence_level, ai_model_run_id
                            ) VALUES ($1, $2, $3, $4, $5)
                        """, document_id, insight_type, insight_text, 0.8, model_run_id)
                
                # Update document with AI analysis
                await db.execute("""
                    UPDATE regulatory_documents 
                    SET ai_analysis = $1, impact_level = $2
                    WHERE id = $3
                """, json.dumps({
                    'summary': summary,
                    'impact_assessment': impact.__dict__,
                    'key_changes': key_changes,
                    'topics': topics,
                    'urgency': urgency
                }), impact.business_impact_level, document_id)
                
        except Exception as e:
            logger.error(f"Failed to store analysis results: {e}")
            raise
    
    async def find_similar_documents(self, document_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar regulatory documents using vector similarity."""
        try:
            if not self.vector_store:
                return []
            
            # Get document embeddings
            similar_docs = await self.vector_store.find_similar(document_id, limit=limit)
            return similar_docs
            
        except Exception as e:
            logger.error(f"Failed to find similar documents: {e}")
            return []
    
    async def get_document_insights(self, document_id: str) -> List[DocumentInsight]:
        """Get all AI-generated insights for a document."""
        try:
            async with get_database() as db:
                query = """
                    SELECT insight_type, insight_text, confidence_level
                    FROM regulatory_insights
                    WHERE document_id = $1
                    ORDER BY created_at DESC
                """
                rows = await db.fetch(query, document_id)
                
                insights = []
                for row in rows:
                    insight = DocumentInsight(
                        insight_type=row['insight_type'],
                        insight_text=row['insight_text'],
                        confidence_level=row['confidence_level'],
                        supporting_evidence=[]  # Could be populated from additional analysis
                    )
                    insights.append(insight)
                
                return insights
                
        except Exception as e:
            logger.error(f"Failed to get document insights: {e}")
            return [] 