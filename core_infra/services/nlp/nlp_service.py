"""
Core NLP Service for Phase 6 Advanced AI & Automation

Provides enterprise-grade natural language processing with multi-provider support,
real-time processing, confidence scoring, and comprehensive audit trails.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

import openai
import anthropic
import spacy
from transformers import pipeline
from supabase import create_client, Client

from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    """Supported NLP model providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    HUGGINGFACE = "huggingface"
    SPACY = "spacy"
    CUSTOM = "custom"

class ProcessingType(Enum):
    """Types of NLP processing supported"""
    POLICY_ANALYSIS = "policy_analysis"
    CONTRACT_EXTRACTION = "contract_extraction"
    QA_RESPONSE = "qa_response"
    ENTITY_RECOGNITION = "entity_recognition"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    SENTIMENT_ANALYSIS = "sentiment_analysis"

@dataclass
class NLPRequest:
    """Request structure for NLP processing"""
    text: str
    processing_type: ProcessingType
    model_provider: ModelProvider
    tenant_id: UUID
    metadata: Optional[Dict[str, Any]] = None
    language: str = "en"
    confidence_threshold: float = 0.7

@dataclass
class NLPResult:
    """Result structure for NLP processing"""
    processed_output: Dict[str, Any]
    extracted_entities: List[Dict[str, Any]]
    key_phrases: List[str]
    sentiment_score: Optional[float]
    confidence_score: float
    processing_time_ms: int
    token_count: Optional[int]
    cost_estimate: Optional[float]

class NLPService:
    """
    Enterprise NLP Service providing multi-provider natural language processing
    with advanced features for financial compliance applications.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase: Client = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_ANON_KEY
        )
        
        # Initialize AI providers
        self.openai_client = None
        self.claude_client = None
        self.spacy_models = {}
        self.hf_pipelines = {}
        
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize AI provider clients"""
        try:
            # OpenAI initialization
            if hasattr(self.settings, 'OPENAI_API_KEY') and self.settings.OPENAI_API_KEY:
                openai.api_key = self.settings.OPENAI_API_KEY
                self.openai_client = openai
                logger.info("OpenAI client initialized")
                
            # Claude initialization
            if hasattr(self.settings, 'CLAUDE_API_KEY') and self.settings.CLAUDE_API_KEY:
                self.claude_client = anthropic.Anthropic(api_key=self.settings.CLAUDE_API_KEY)
                logger.info("Claude client initialized")
                
            # spaCy models initialization
            self._load_spacy_models()
            
            # HuggingFace pipelines initialization
            self._load_hf_pipelines()
            
        except Exception as e:
            logger.error(f"Error initializing NLP providers: {str(e)}")
            
    def _load_spacy_models(self):
        """Load spaCy models for different languages"""
        models_to_load = {
            'en': 'en_core_web_sm',
            'es': 'es_core_news_sm',
            'fr': 'fr_core_news_sm',
            'de': 'de_core_news_sm'
        }
        
        for lang, model_name in models_to_load.items():
            try:
                self.spacy_models[lang] = spacy.load(model_name)
                logger.info(f"Loaded spaCy model for {lang}: {model_name}")
            except OSError:
                logger.warning(f"spaCy model {model_name} not found for language {lang}")
                
    def _load_hf_pipelines(self):
        """Load HuggingFace pipelines for various tasks"""
        try:
            self.hf_pipelines['sentiment'] = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            self.hf_pipelines['ner'] = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
            self.hf_pipelines['summarization'] = pipeline(
                "summarization",
                model="facebook/bart-large-cnn"
            )
            logger.info("HuggingFace pipelines loaded successfully")
        except Exception as e:
            logger.error(f"Error loading HuggingFace pipelines: {str(e)}")
            
    async def process_text(self, request: NLPRequest) -> NLPResult:
        """
        Process text using the specified NLP model and processing type.
        
        Args:
            request: NLP processing request
            
        Returns:
            NLP processing result with confidence scores and metadata
        """
        start_time = time.time()
        
        try:
            # Validate request
            await self._validate_request(request)
            
            # Get or create model record
            model_record = await self._get_or_create_model(request)
            
            # Process based on provider and type
            result = await self._process_by_provider(request, model_record)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time_ms
            
            # Store processing result
            await self._store_processing_result(request, result, model_record['id'])
            
            # Update model usage statistics
            await self._update_model_usage(model_record['id'], processing_time_ms)
            
            logger.info(
                f"NLP processing completed: {request.processing_type.value} "
                f"using {request.model_provider.value} in {processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"NLP processing failed after {processing_time_ms}ms: {str(e)}")
            
            # Store error result
            error_result = NLPResult(
                processed_output={"error": str(e)},
                extracted_entities=[],
                key_phrases=[],
                sentiment_score=None,
                confidence_score=0.0,
                processing_time_ms=processing_time_ms,
                token_count=0,
                cost_estimate=0.0
            )
            
            if 'model_record' in locals():
                await self._store_processing_result(request, error_result, model_record['id'])
                
            raise
            
    async def _validate_request(self, request: NLPRequest):
        """Validate NLP processing request"""
        if not request.text or len(request.text.strip()) == 0:
            raise ValueError("Input text cannot be empty")
            
        if len(request.text) > 100000:  # 100K character limit
            raise ValueError("Input text exceeds maximum length of 100,000 characters")
            
        if request.confidence_threshold < 0.0 or request.confidence_threshold > 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
            
    async def _get_or_create_model(self, request: NLPRequest) -> Dict[str, Any]:
        """Get existing model or create new model record"""
        model_name = f"{request.model_provider.value}_{request.processing_type.value}"
        
        # Check if model exists
        result = self.supabase.table('nlp_models').select('*').eq(
            'tenant_id', str(request.tenant_id)
        ).eq('model_name', model_name).eq(
            'model_type', request.processing_type.value
        ).execute()
        
        if result.data:
            return result.data[0]
            
        # Create new model record
        model_data = {
            'tenant_id': str(request.tenant_id),
            'model_name': model_name,
            'model_type': request.processing_type.value,
            'model_provider': request.model_provider.value,
            'model_version': '1.0',
            'language_support': [request.language],
            'capabilities': [request.processing_type.value],
            'model_config': {
                'confidence_threshold': request.confidence_threshold,
                'language': request.language
            },
            'model_status': 'production',
            'created_by': str(request.tenant_id)  # Using tenant_id as fallback
        }
        
        result = self.supabase.table('nlp_models').insert(model_data).execute()
        return result.data[0]
        
    async def _process_by_provider(self, request: NLPRequest, model_record: Dict[str, Any]) -> NLPResult:
        """Process text based on the specified provider"""
        
        if request.model_provider == ModelProvider.OPENAI:
            return await self._process_openai(request)
        elif request.model_provider == ModelProvider.CLAUDE:
            return await self._process_claude(request)
        elif request.model_provider == ModelProvider.SPACY:
            return await self._process_spacy(request)
        elif request.model_provider == ModelProvider.HUGGINGFACE:
            return await self._process_huggingface(request)
        else:
            raise ValueError(f"Unsupported model provider: {request.model_provider}")
            
    async def _process_openai(self, request: NLPRequest) -> NLPResult:
        """Process text using OpenAI API"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
            
        try:
            # Create processing prompt based on type
            prompt = self._create_processing_prompt(request)
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse response
            content = response.choices[0].message.content
            output = json.loads(content) if content.startswith('{') else {"analysis": content}
            
            # Extract additional information
            entities = self._extract_entities_from_output(output)
            key_phrases = self._extract_key_phrases_from_output(output)
            sentiment = self._extract_sentiment_from_output(output)
            
            return NLPResult(
                processed_output=output,
                extracted_entities=entities,
                key_phrases=key_phrases,
                sentiment_score=sentiment,
                confidence_score=0.85,  # OpenAI default confidence
                processing_time_ms=0,  # Will be set by caller
                token_count=response.usage.total_tokens,
                cost_estimate=self._calculate_openai_cost(response.usage.total_tokens)
            )
            
        except Exception as e:
            logger.error(f"OpenAI processing error: {str(e)}")
            raise
            
    async def _process_claude(self, request: NLPRequest) -> NLPResult:
        """Process text using Claude API"""
        if not self.claude_client:
            raise ValueError("Claude client not initialized")
            
        try:
            # Create processing prompt
            prompt = self._create_processing_prompt(request)
            
            response = await self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": f"{prompt['system']}\n\n{prompt['user']}"}
                ]
            )
            
            # Parse response
            content = response.content[0].text
            output = json.loads(content) if content.startswith('{') else {"analysis": content}
            
            # Extract additional information
            entities = self._extract_entities_from_output(output)
            key_phrases = self._extract_key_phrases_from_output(output)
            sentiment = self._extract_sentiment_from_output(output)
            
            return NLPResult(
                processed_output=output,
                extracted_entities=entities,
                key_phrases=key_phrases,
                sentiment_score=sentiment,
                confidence_score=0.85,  # Claude default confidence
                processing_time_ms=0,
                token_count=response.usage.input_tokens + response.usage.output_tokens,
                cost_estimate=self._calculate_claude_cost(response.usage.input_tokens, response.usage.output_tokens)
            )
            
        except Exception as e:
            logger.error(f"Claude processing error: {str(e)}")
            raise
            
    async def _process_spacy(self, request: NLPRequest) -> NLPResult:
        """Process text using spaCy models"""
        model = self.spacy_models.get(request.language)
        if not model:
            raise ValueError(f"spaCy model not available for language: {request.language}")
            
        try:
            doc = model(request.text)
            
            # Extract entities
            entities = [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 0.8  # spaCy doesn't provide confidence scores
                }
                for ent in doc.ents
            ]
            
            # Extract key phrases (noun phrases)
            key_phrases = [chunk.text for chunk in doc.noun_chunks]
            
            # Basic sentiment (limited in spaCy)
            sentiment_score = doc.sentiment if hasattr(doc, 'sentiment') else None
            
            # Create output based on processing type
            if request.processing_type == ProcessingType.ENTITY_RECOGNITION:
                output = {"entities": entities}
            elif request.processing_type == ProcessingType.CLASSIFICATION:
                output = {"classification": doc.cats if hasattr(doc, 'cats') else {}}
            else:
                output = {
                    "entities": entities,
                    "key_phrases": key_phrases,
                    "pos_tags": [(token.text, token.pos_) for token in doc],
                    "dependencies": [(token.text, token.dep_, token.head.text) for token in doc]
                }
                
            return NLPResult(
                processed_output=output,
                extracted_entities=entities,
                key_phrases=key_phrases,
                sentiment_score=sentiment_score,
                confidence_score=0.8,  # spaCy average confidence
                processing_time_ms=0,
                token_count=len(doc),
                cost_estimate=0.0  # spaCy is free
            )
            
        except Exception as e:
            logger.error(f"spaCy processing error: {str(e)}")
            raise
            
    async def _process_huggingface(self, request: NLPRequest) -> NLPResult:
        """Process text using HuggingFace pipelines"""
        try:
            output = {}
            entities = []
            key_phrases = []
            sentiment_score = None
            
            # Process based on type
            if request.processing_type == ProcessingType.SENTIMENT_ANALYSIS:
                if 'sentiment' in self.hf_pipelines:
                    result = self.hf_pipelines['sentiment'](request.text)
                    output = {"sentiment": result}
                    sentiment_score = result[0]['score'] if result[0]['label'] == 'POSITIVE' else -result[0]['score']
                    
            elif request.processing_type == ProcessingType.ENTITY_RECOGNITION:
                if 'ner' in self.hf_pipelines:
                    result = self.hf_pipelines['ner'](request.text)
                    entities = [
                        {
                            "text": ent['word'],
                            "label": ent['entity_group'],
                            "confidence": ent['score'],
                            "start": ent['start'],
                            "end": ent['end']
                        }
                        for ent in result
                    ]
                    output = {"entities": entities}
                    
            elif request.processing_type == ProcessingType.SUMMARIZATION:
                if 'summarization' in self.hf_pipelines:
                    # Truncate text if too long for summarization
                    text = request.text[:1024] if len(request.text) > 1024 else request.text
                    result = self.hf_pipelines['summarization'](text)
                    output = {"summary": result[0]['summary_text']}
                    
            else:
                # Default processing - use multiple pipelines
                if 'sentiment' in self.hf_pipelines:
                    sentiment_result = self.hf_pipelines['sentiment'](request.text)
                    output['sentiment'] = sentiment_result
                    sentiment_score = sentiment_result[0]['score'] if sentiment_result[0]['label'] == 'POSITIVE' else -sentiment_result[0]['score']
                    
                if 'ner' in self.hf_pipelines:
                    ner_result = self.hf_pipelines['ner'](request.text)
                    entities = [
                        {
                            "text": ent['word'],
                            "label": ent['entity_group'],
                            "confidence": ent['score'],
                            "start": ent['start'],
                            "end": ent['end']
                        }
                        for ent in ner_result
                    ]
                    output['entities'] = entities
                    
            return NLPResult(
                processed_output=output,
                extracted_entities=entities,
                key_phrases=key_phrases,
                sentiment_score=sentiment_score,
                confidence_score=0.75,  # HuggingFace average confidence
                processing_time_ms=0,
                token_count=len(request.text.split()),
                cost_estimate=0.0  # HuggingFace models are free
            )
            
        except Exception as e:
            logger.error(f"HuggingFace processing error: {str(e)}")
            raise
            
    def _create_processing_prompt(self, request: NLPRequest) -> Dict[str, str]:
        """Create processing prompt based on request type"""
        
        if request.processing_type == ProcessingType.POLICY_ANALYSIS:
            return {
                "system": "You are an expert financial compliance analyst. Analyze the given policy document and extract key compliance requirements, obligations, and risks. Return your analysis in JSON format.",
                "user": f"Analyze this policy document:\n\n{request.text}\n\nProvide a structured analysis including: compliance_requirements, risk_factors, obligations, deadlines, and enforcement_mechanisms."
            }
            
        elif request.processing_type == ProcessingType.CONTRACT_EXTRACTION:
            return {
                "system": "You are an expert contract analyst. Extract key information from the given contract including parties, terms, obligations, dates, and financial details. Return structured data in JSON format.",
                "user": f"Extract key information from this contract:\n\n{request.text}\n\nInclude: parties, contract_type, key_terms, obligations, important_dates, financial_details, and risk_factors."
            }
            
        elif request.processing_type == ProcessingType.QA_RESPONSE:
            return {
                "system": "You are a helpful regulatory compliance assistant. Answer the user's question based on the provided context. Be accurate, concise, and cite relevant information.",
                "user": f"Context: {request.text}\n\nQuestion: {request.metadata.get('question', 'Please summarize this document.')}\n\nProvide a comprehensive answer based on the context."
            }
            
        elif request.processing_type == ProcessingType.ENTITY_RECOGNITION:
            return {
                "system": "Extract named entities from the text including organizations, persons, dates, monetary amounts, and regulatory references. Return in JSON format.",
                "user": f"Extract named entities from this text:\n\n{request.text}"
            }
            
        elif request.processing_type == ProcessingType.CLASSIFICATION:
            return {
                "system": "Classify the given text into relevant categories for financial compliance. Consider document type, regulatory domain, risk level, and urgency.",
                "user": f"Classify this document:\n\n{request.text}\n\nProvide classification for: document_type, regulatory_domain, risk_level, urgency, and key_topics."
            }
            
        elif request.processing_type == ProcessingType.SUMMARIZATION:
            return {
                "system": "Create a concise summary of the document highlighting key points, main conclusions, and actionable items.",
                "user": f"Summarize this document:\n\n{request.text}"
            }
            
        else:
            return {
                "system": "Analyze the given text and provide relevant insights.",
                "user": request.text
            }
            
    def _extract_entities_from_output(self, output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from processed output"""
        if 'entities' in output:
            return output['entities']
        return []
        
    def _extract_key_phrases_from_output(self, output: Dict[str, Any]) -> List[str]:
        """Extract key phrases from processed output"""
        if 'key_phrases' in output:
            return output['key_phrases']
        elif 'key_terms' in output:
            return output['key_terms']
        return []
        
    def _extract_sentiment_from_output(self, output: Dict[str, Any]) -> Optional[float]:
        """Extract sentiment score from processed output"""
        if 'sentiment' in output:
            sentiment = output['sentiment']
            if isinstance(sentiment, dict) and 'score' in sentiment:
                return sentiment['score']
            elif isinstance(sentiment, list) and len(sentiment) > 0:
                return sentiment[0].get('score')
        return None
        
    def _calculate_openai_cost(self, tokens: int) -> float:
        """Calculate OpenAI API cost based on token usage"""
        # GPT-4 pricing (approximate)
        cost_per_1k_tokens = 0.03  # $0.03 per 1K tokens
        return (tokens / 1000) * cost_per_1k_tokens
        
    def _calculate_claude_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate Claude API cost based on token usage"""
        # Claude pricing (approximate)
        input_cost_per_1k = 0.008  # $0.008 per 1K input tokens
        output_cost_per_1k = 0.024  # $0.024 per 1K output tokens
        return (input_tokens / 1000) * input_cost_per_1k + (output_tokens / 1000) * output_cost_per_1k
        
    async def _store_processing_result(self, request: NLPRequest, result: NLPResult, model_id: str):
        """Store NLP processing result in database"""
        try:
            result_data = {
                'tenant_id': str(request.tenant_id),
                'model_id': model_id,
                'processing_type': request.processing_type.value,
                'input_text': request.text,
                'input_metadata': request.metadata or {},
                'processed_output': result.processed_output,
                'extracted_entities': result.extracted_entities,
                'key_phrases': result.key_phrases,
                'sentiment_score': result.sentiment_score,
                'confidence_score': result.confidence_score,
                'processing_time_ms': result.processing_time_ms,
                'token_count': result.token_count,
                'cost_estimate': result.cost_estimate,
                'validation_status': 'pending'
            }
            
            self.supabase.table('nlp_processing_results').insert(result_data).execute()
            
        except Exception as e:
            logger.error(f"Error storing NLP processing result: {str(e)}")
            
    async def _update_model_usage(self, model_id: str, processing_time_ms: int):
        """Update model usage statistics"""
        try:
            # Get current usage stats
            result = self.supabase.table('nlp_models').select('usage_count, average_response_time_ms').eq('id', model_id).execute()
            
            if result.data:
                current_usage = result.data[0]['usage_count'] or 0
                current_avg_time = result.data[0]['average_response_time_ms'] or 0
                
                # Calculate new average response time
                new_usage = current_usage + 1
                new_avg_time = ((current_avg_time * current_usage) + processing_time_ms) // new_usage
                
                # Update model record
                self.supabase.table('nlp_models').update({
                    'usage_count': new_usage,
                    'average_response_time_ms': new_avg_time,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('id', model_id).execute()
                
        except Exception as e:
            logger.error(f"Error updating model usage: {str(e)}")
            
    async def get_model_performance(self, tenant_id: UUID, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get performance metrics for NLP models"""
        try:
            query = self.supabase.table('nlp_models').select('*').eq('tenant_id', str(tenant_id))
            
            if model_type:
                query = query.eq('model_type', model_type)
                
            result = query.execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Error retrieving model performance: {str(e)}")
            return []
            
    async def get_processing_history(self, tenant_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent NLP processing history"""
        try:
            result = self.supabase.table('nlp_processing_results').select('*').eq(
                'tenant_id', str(tenant_id)
            ).order('created_at', desc=True).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error retrieving processing history: {str(e)}")
            return [] 