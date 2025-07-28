"""
NLP (Natural Language Processing) Service for Phase 6 Advanced AI & Automation

This module provides enterprise-grade natural language processing capabilities including:
- Policy interpretation and analysis
- Contract analysis and extraction
- Regulatory Q&A chatbots
- Entity extraction and sentiment analysis
- Text classification and summarization

Key Features:
- Multi-provider support (OpenAI, Claude, HuggingFace, spaCy)
- Real-time processing with caching
- Confidence scoring and validation workflows
- Multi-language support
- Enterprise audit trails
"""

from .nlp_service import NLPService, NLPRequest, NLPResult, ModelProvider, ProcessingType
from .policy_interpreter import PolicyInterpreter
from .contract_analyzer import ContractAnalyzer
from .chatbot_engine import ChatbotEngine
from .entity_extractor import EntityExtractor
from .sentiment_analyzer import SentimentAnalyzer

__all__ = [
    'NLPService',
    'NLPRequest',
    'NLPResult',
    'ModelProvider',
    'ProcessingType',
    'PolicyInterpreter',
    'ContractAnalyzer', 
    'ChatbotEngine',
    'EntityExtractor',
    'SentimentAnalyzer'
]

__version__ = "1.0.0" 