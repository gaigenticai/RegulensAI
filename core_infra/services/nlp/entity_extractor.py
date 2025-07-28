"""
Entity Extractor for NLP Service
Provides production-ready entity extraction using multiple NLP providers
with comprehensive error handling and audit trails.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

import spacy
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import openai
import anthropic
from supabase import Client

from core_infra.config import get_settings

logger = logging.getLogger(__name__)

class EntityType(Enum):
    """Supported entity types for financial compliance"""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    MONEY = "MONEY"
    DATE = "DATE"
    ACCOUNT_NUMBER = "ACCOUNT_NUMBER"
    TRANSACTION_ID = "TRANSACTION_ID"
    REGULATION_REF = "REGULATION_REF"
    COMPLIANCE_TERM = "COMPLIANCE_TERM"
    FINANCIAL_INSTRUMENT = "FINANCIAL_INSTRUMENT"

@dataclass
class EntityMatch:
    """Structure for extracted entity"""
    entity_type: str
    entity_value: str
    confidence_score: float
    start_position: int
    end_position: int
    context: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ExtractionResult:
    """Result structure for entity extraction"""
    entities: List[EntityMatch]
    total_entities: int
    processing_time_ms: int
    confidence_score: float
    provider_used: str

class EntityExtractor:
    """
    Production-ready entity extraction service for financial compliance documents.
    Supports multiple NLP providers with fallback mechanisms and comprehensive logging.
    """
    
    def __init__(self, supabase_client: Client):
        self.settings = get_settings()
        self.supabase = supabase_client
        
        # Initialize NLP models
        self.spacy_model = None
        self.hf_tokenizer = None
        self.hf_model = None
        self.hf_pipeline = None
        
        # Financial compliance patterns
        self.financial_patterns = {
            'account_number': re.compile(r'\b\d{8,16}\b'),
            'swift_code': re.compile(r'\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\b'),
            'iban': re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'),
            'transaction_id': re.compile(r'\b[A-Z0-9]{8,32}\b'),
            'regulation_ref': re.compile(r'\b(Basel\s*(III|II|I)|MiFID\s*(II|I)|GDPR|PCI\s*DSS|SOX)\b', re.IGNORECASE)
        }
        
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize NLP models with error handling"""
        try:
            # Initialize spaCy model for general NER
            try:
                self.spacy_model = spacy.load("en_core_web_sm")
                logger.info("SpaCy model loaded successfully")
            except OSError:
                logger.warning("SpaCy model not available, will use regex-based extraction")
                
            # Initialize HuggingFace model for financial NER if API key available
            if hasattr(self.settings, 'HUGGINGFACE_API_KEY') and self.settings.HUGGINGFACE_API_KEY:
                try:
                    model_name = getattr(self.settings, 'HUGGINGFACE_NER_MODEL', 'dbmdz/bert-large-cased-finetuned-conll03-english')
                    self.hf_pipeline = pipeline("ner", model=model_name, aggregation_strategy="simple")
                    logger.info("HuggingFace NER model loaded successfully")
                except Exception as e:
                    logger.error(f"Failed to load HuggingFace model: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error initializing entity extractor models: {str(e)}")
            
    async def extract_entities(self, text: str, tenant_id: UUID, 
                             provider: str = "auto", 
                             entity_types: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract entities from text using multiple approaches
        
        Args:
            text: Input text to process
            tenant_id: Tenant identifier for audit logging
            provider: Preferred NLP provider ("auto", "spacy", "huggingface", "regex")
            entity_types: Specific entity types to extract (optional)
            
        Returns:
            ExtractionResult with extracted entities and metadata
        """
        start_time = datetime.now(timezone.utc)
        processing_start = time.time()
        
        try:
            logger.info(f"Starting entity extraction for tenant {tenant_id}")
            
            all_entities = []
            provider_used = provider
            
            # Auto-select provider if needed
            if provider == "auto":
                if self.spacy_model:
                    provider_used = "spacy"
                elif self.hf_pipeline:
                    provider_used = "huggingface"
                else:
                    provider_used = "regex"
                    
            # Extract using selected provider
            if provider_used == "spacy" and self.spacy_model:
                entities = await self._extract_with_spacy(text, entity_types)
                all_entities.extend(entities)
                
            elif provider_used == "huggingface" and self.hf_pipeline:
                entities = await self._extract_with_huggingface(text, entity_types)
                all_entities.extend(entities)
                
            # Always run regex patterns for financial entities
            regex_entities = await self._extract_with_regex(text)
            all_entities.extend(regex_entities)
            
            # Remove duplicates and calculate confidence
            unique_entities = self._deduplicate_entities(all_entities)
            
            processing_time_ms = int((time.time() - processing_start) * 1000)
            
            # Calculate overall confidence
            confidence_score = sum(e.confidence_score for e in unique_entities) / len(unique_entities) if unique_entities else 0.0
            
            result = ExtractionResult(
                entities=unique_entities,
                total_entities=len(unique_entities),
                processing_time_ms=processing_time_ms,
                confidence_score=confidence_score,
                provider_used=provider_used
            )
            
            # Log to database
            await self._log_extraction(tenant_id, text, result, start_time)
            
            logger.info(f"Entity extraction completed: {len(unique_entities)} entities found")
            return result
            
        except Exception as e:
            logger.error(f"Error in entity extraction: {str(e)}", exc_info=True)
            
            # Log error to database
            await self._log_error(tenant_id, str(e), start_time)
            
            # Return empty result with error metadata
            return ExtractionResult(
                entities=[],
                total_entities=0,
                processing_time_ms=int((time.time() - processing_start) * 1000),
                confidence_score=0.0,
                provider_used=provider_used
            )
            
    async def _extract_with_spacy(self, text: str, entity_types: Optional[List[str]] = None) -> List[EntityMatch]:
        """Extract entities using spaCy NER"""
        entities = []
        
        try:
            doc = self.spacy_model(text)
            
            for ent in doc.ents:
                if entity_types is None or ent.label_ in entity_types:
                    entities.append(EntityMatch(
                        entity_type=ent.label_,
                        entity_value=ent.text,
                        confidence_score=0.85,  # spaCy doesn't provide confidence scores
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        context=text[max(0, ent.start_char-50):ent.end_char+50],
                        metadata={'provider': 'spacy', 'spacy_label': ent.label_}
                    ))
                    
        except Exception as e:
            logger.error(f"Error in spaCy entity extraction: {str(e)}")
            
        return entities
        
    async def _extract_with_huggingface(self, text: str, entity_types: Optional[List[str]] = None) -> List[EntityMatch]:
        """Extract entities using HuggingFace transformers"""
        entities = []
        
        try:
            # Process in chunks if text is too long
            max_length = 512
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            
            for chunk_start, chunk in enumerate(chunks):
                chunk_offset = chunk_start * max_length
                results = self.hf_pipeline(chunk)
                
                for result in results:
                    if entity_types is None or result['entity_group'] in entity_types:
                        entities.append(EntityMatch(
                            entity_type=result['entity_group'],
                            entity_value=result['word'],
                            confidence_score=result['score'],
                            start_position=result['start'] + chunk_offset,
                            end_position=result['end'] + chunk_offset,
                            context=text[max(0, result['start']+chunk_offset-50):result['end']+chunk_offset+50],
                            metadata={'provider': 'huggingface', 'model_confidence': result['score']}
                        ))
                        
        except Exception as e:
            logger.error(f"Error in HuggingFace entity extraction: {str(e)}")
            
        return entities
        
    async def _extract_with_regex(self, text: str) -> List[EntityMatch]:
        """Extract financial entities using regex patterns"""
        entities = []
        
        try:
            for entity_type, pattern in self.financial_patterns.items():
                matches = pattern.finditer(text)
                
                for match in matches:
                    entities.append(EntityMatch(
                        entity_type=entity_type.upper(),
                        entity_value=match.group(),
                        confidence_score=0.90,  # High confidence for pattern matches
                        start_position=match.start(),
                        end_position=match.end(),
                        context=text[max(0, match.start()-50):match.end()+50],
                        metadata={'provider': 'regex', 'pattern': entity_type}
                    ))
                    
        except Exception as e:
            logger.error(f"Error in regex entity extraction: {str(e)}")
            
        return entities
        
    def _deduplicate_entities(self, entities: List[EntityMatch]) -> List[EntityMatch]:
        """Remove duplicate entities based on position and value"""
        unique_entities = []
        seen_positions = set()
        
        # Sort by confidence score (highest first)
        entities.sort(key=lambda x: x.confidence_score, reverse=True)
        
        for entity in entities:
            position_key = (entity.start_position, entity.end_position, entity.entity_value.lower())
            
            if position_key not in seen_positions:
                unique_entities.append(entity)
                seen_positions.add(position_key)
                
        return unique_entities
        
    async def _log_extraction(self, tenant_id: UUID, text: str, result: ExtractionResult, start_time: datetime):
        """Log extraction results to database"""
        try:
            log_data = {
                'tenant_id': str(tenant_id),
                'processing_type': 'entity_extraction',
                'input_text_length': len(text),
                'entities_found': result.total_entities,
                'confidence_score': result.confidence_score,
                'processing_time_ms': result.processing_time_ms,
                'provider_used': result.provider_used,
                'created_at': start_time.isoformat(),
                'model_type': 'entity_extractor'
            }
            
            # Insert into nlp_processing_results table
            self.supabase.table('nlp_processing_results').insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging extraction results: {str(e)}")
            
    async def _log_error(self, tenant_id: UUID, error_message: str, start_time: datetime):
        """Log errors to database"""
        try:
            error_data = {
                'tenant_id': str(tenant_id),
                'processing_type': 'entity_extraction',
                'error_message': error_message,
                'created_at': start_time.isoformat(),
                'model_type': 'entity_extractor'
            }
            
            self.supabase.table('nlp_processing_results').insert(error_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging extraction error: {str(e)}") 