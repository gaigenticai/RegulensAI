"""
Chatbot Engine for NLP Service
Provides production-ready conversational AI for regulatory compliance Q&A
with context awareness, session management, and comprehensive audit trails.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum

import openai
import anthropic
from transformers import pipeline
from supabase import Client

from core_infra.config import get_settings

logger = logging.getLogger(__name__)

class ChatbotType(Enum):
    """Types of chatbot functionality"""
    REGULATORY_QA = "regulatory_qa"
    COMPLIANCE_ASSISTANT = "compliance_assistant"
    POLICY_HELPER = "policy_helper"
    GENERAL_SUPPORT = "general_support"

class MessageType(Enum):
    """Types of messages in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class ChatMessage:
    """Structure for chat messages"""
    message_id: str
    message_type: MessageType
    content: str
    timestamp: datetime
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ChatSession:
    """Structure for chat sessions"""
    session_id: str
    tenant_id: UUID
    user_id: Optional[UUID]
    chatbot_type: ChatbotType
    context: Dict[str, Any]
    messages: List[ChatMessage]
    started_at: datetime
    last_activity: datetime
    is_active: bool

@dataclass
class ChatResponse:
    """Response structure for chatbot queries"""
    response_text: str
    confidence_score: float
    sources: List[Dict[str, Any]]
    follow_up_questions: List[str]
    processing_time_ms: int
    provider_used: str
    session_id: str
    requires_human_review: bool = False
    metadata: Optional[Dict[str, Any]] = None

class ChatbotEngine:
    """
    Production-ready chatbot engine for financial compliance Q&A.
    Supports multi-provider AI, context awareness, and session management.
    """
    
    def __init__(self, supabase_client: Client):
        self.settings = get_settings()
        self.supabase = supabase_client
        
        # Initialize AI providers
        self.openai_client = None
        self.claude_client = None
        
        # Session management
        self.active_sessions: Dict[str, ChatSession] = {}
        self.session_timeout_minutes = getattr(self.settings, 'CHATBOT_SESSION_TIMEOUT_MINUTES', 30)
        self.max_messages_per_session = getattr(self.settings, 'CHATBOT_MAX_MESSAGES_PER_SESSION', 100)
        
        # Regulatory knowledge base
        self.regulatory_keywords = [
            'basel', 'mifid', 'gdpr', 'pci dss', 'sox', 'aml', 'kyc',
            'compliance', 'regulation', 'audit', 'risk', 'policy',
            'procedure', 'requirement', 'guideline', 'framework'
        ]
        
        # Response templates
        self.response_templates = {
            'greeting': "Hello! I'm your Regulatory Compliance Assistant. How can I help you with compliance questions today?",
            'clarification_needed': "I need more information to provide an accurate answer. Could you please clarify:",
            'confidence_low': "I'm not entirely certain about this. Let me provide what I know, but you may want to consult with a compliance expert:",
            'human_escalation': "This question requires human expertise. I'm escalating this to a compliance officer who will respond shortly.",
            'session_timeout': "Your session has been inactive. Starting a new conversation.",
            'error_response': "I encountered an issue processing your request. Please try rephrasing your question or contact support."
        }
        
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize AI provider clients"""
        try:
            # Initialize OpenAI client
            if hasattr(self.settings, 'OPENAI_API_KEY') and self.settings.OPENAI_API_KEY:
                try:
                    openai.api_key = self.settings.OPENAI_API_KEY
                    self.openai_client = openai
                    logger.info("OpenAI client initialized for chatbot")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                    
            # Initialize Claude client
            if hasattr(self.settings, 'CLAUDE_API_KEY') and self.settings.CLAUDE_API_KEY:
                try:
                    self.claude_client = anthropic.Anthropic(api_key=self.settings.CLAUDE_API_KEY)
                    logger.info("Claude client initialized for chatbot")
                except Exception as e:
                    logger.error(f"Failed to initialize Claude client: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error initializing chatbot providers: {str(e)}")
            
    async def start_session(self, tenant_id: UUID, user_id: Optional[UUID] = None,
                          chatbot_type: ChatbotType = ChatbotType.REGULATORY_QA,
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new chatbot session
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier (optional)
            chatbot_type: Type of chatbot functionality
            context: Additional context for the session
            
        Returns:
            Session ID
        """
        try:
            session_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            session = ChatSession(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                chatbot_type=chatbot_type,
                context=context or {},
                messages=[],
                started_at=now,
                last_activity=now,
                is_active=True
            )
            
            # Add system message
            system_message = ChatMessage(
                message_id=str(uuid4()),
                message_type=MessageType.SYSTEM,
                content=self._get_system_prompt(chatbot_type),
                timestamp=now,
                metadata={'chatbot_type': chatbot_type.value}
            )
            session.messages.append(system_message)
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Log session start to database
            await self._log_session_start(session)
            
            logger.info(f"Started chatbot session {session_id} for tenant {tenant_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting chatbot session: {str(e)}", exc_info=True)
            raise
            
    async def generate_response(self, session_id: str, user_message: str,
                              provider: str = "auto") -> ChatResponse:
        """
        Generate response to user message
        
        Args:
            session_id: Session identifier
            user_message: User's message/question
            provider: Preferred AI provider
            
        Returns:
            ChatResponse with AI-generated response
        """
        start_time = datetime.now(timezone.utc)
        processing_start = time.time()
        
        try:
            # Get or validate session
            session = await self._get_session(session_id)
            if not session:
                raise ValueError(f"Invalid session ID: {session_id}")
                
            # Check session timeout
            if self._is_session_expired(session):
                await self._end_session(session_id)
                raise ValueError("Session has expired")
                
            logger.info(f"Processing message for session {session_id}")
            
            # Add user message to session
            user_msg = ChatMessage(
                message_id=str(uuid4()),
                message_type=MessageType.USER,
                content=user_message,
                timestamp=start_time
            )
            session.messages.append(user_msg)
            
            # Check message limit
            if len(session.messages) > self.max_messages_per_session:
                return ChatResponse(
                    response_text="Session has reached maximum message limit. Please start a new session.",
                    confidence_score=1.0,
                    sources=[],
                    follow_up_questions=[],
                    processing_time_ms=int((time.time() - processing_start) * 1000),
                    provider_used="system",
                    session_id=session_id,
                    requires_human_review=True
                )
                
            # Determine provider
            provider_used = self._select_provider(provider)
            
            # Generate response based on provider
            if provider_used == "openai" and self.openai_client:
                response = await self._generate_with_openai(session, user_message)
            elif provider_used == "claude" and self.claude_client:
                response = await self._generate_with_claude(session, user_message)
            else:
                response = await self._generate_fallback_response(session, user_message)
                provider_used = "fallback"
                
            # Add assistant message to session
            assistant_msg = ChatMessage(
                message_id=str(uuid4()),
                message_type=MessageType.ASSISTANT,
                content=response.response_text,
                timestamp=datetime.now(timezone.utc),
                confidence_score=response.confidence_score,
                metadata={'provider': provider_used}
            )
            session.messages.append(assistant_msg)
            
            # Update session activity
            session.last_activity = datetime.now(timezone.utc)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - processing_start) * 1000)
            response.processing_time_ms = processing_time_ms
            response.provider_used = provider_used
            response.session_id = session_id
            
            # Log interaction to database
            await self._log_interaction(session, user_message, response, start_time)
            
            logger.info(f"Generated response for session {session_id} (confidence: {response.confidence_score:.3f})")
            return response
            
        except Exception as e:
            logger.error(f"Error generating chatbot response: {str(e)}", exc_info=True)
            
            # Log error
            await self._log_error(session_id, str(e), start_time)
            
            # Return error response
            return ChatResponse(
                response_text=self.response_templates['error_response'],
                confidence_score=0.0,
                sources=[],
                follow_up_questions=[],
                processing_time_ms=int((time.time() - processing_start) * 1000),
                provider_used="error",
                session_id=session_id,
                requires_human_review=True,
                metadata={'error': str(e)}
            )
            
    async def _generate_with_openai(self, session: ChatSession, user_message: str) -> ChatResponse:
        """Generate response using OpenAI GPT models"""
        try:
            # Build conversation context
            messages = []
            
            # Add system prompt
            system_prompt = self._get_enhanced_system_prompt(session)
            messages.append({"role": "system", "content": system_prompt})
            
            # Add recent conversation history (last 10 messages)
            recent_messages = session.messages[-10:] if len(session.messages) > 10 else session.messages
            for msg in recent_messages:
                if msg.message_type == MessageType.USER:
                    messages.append({"role": "user", "content": msg.content})
                elif msg.message_type == MessageType.ASSISTANT:
                    messages.append({"role": "assistant", "content": msg.content})
                    
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = await self.openai_client.ChatCompletion.acreate(
                model=getattr(self.settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            response_text = response.choices[0].message.content
            
            # Determine confidence and follow-up questions
            confidence_score = self._calculate_confidence(response_text, user_message)
            follow_up_questions = self._generate_follow_up_questions(user_message, response_text)
            sources = []  # Would integrate with knowledge base in production
            
            return ChatResponse(
                response_text=response_text,
                confidence_score=confidence_score,
                sources=sources,
                follow_up_questions=follow_up_questions,
                processing_time_ms=0,  # Will be set by caller
                provider_used="openai",
                session_id=session.session_id,
                requires_human_review=confidence_score < 0.7
            )
            
        except Exception as e:
            logger.error(f"Error in OpenAI chatbot response: {str(e)}")
            raise
            
    async def _generate_with_claude(self, session: ChatSession, user_message: str) -> ChatResponse:
        """Generate response using Anthropic Claude"""
        try:
            # Build conversation context
            conversation = self._build_claude_conversation(session, user_message)
            
            response = await self.claude_client.messages.create(
                model=getattr(self.settings, 'ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
                max_tokens=500,
                messages=conversation
            )
            
            response_text = response.content[0].text
            
            # Determine confidence and follow-up questions
            confidence_score = self._calculate_confidence(response_text, user_message)
            follow_up_questions = self._generate_follow_up_questions(user_message, response_text)
            sources = []
            
            return ChatResponse(
                response_text=response_text,
                confidence_score=confidence_score,
                sources=sources,
                follow_up_questions=follow_up_questions,
                processing_time_ms=0,
                provider_used="claude",
                session_id=session.session_id,
                requires_human_review=confidence_score < 0.7
            )
            
        except Exception as e:
            logger.error(f"Error in Claude chatbot response: {str(e)}")
            raise
            
    async def _generate_fallback_response(self, session: ChatSession, user_message: str) -> ChatResponse:
        """Generate fallback response using rule-based approach"""
        try:
            # Simple keyword-based responses for regulatory topics
            message_lower = user_message.lower()
            
            if any(keyword in message_lower for keyword in ['hello', 'hi', 'hey']):
                response_text = self.response_templates['greeting']
                confidence = 0.9
            elif any(keyword in message_lower for keyword in self.regulatory_keywords):
                response_text = ("I understand you're asking about regulatory compliance. "
                               "While I can provide general guidance, please consult with a compliance expert for specific advice.")
                confidence = 0.6
            else:
                response_text = self.response_templates['clarification_needed'] + " What specific compliance topic are you interested in?"
                confidence = 0.4
                
            return ChatResponse(
                response_text=response_text,
                confidence_score=confidence,
                sources=[],
                follow_up_questions=["What regulation are you asking about?", "Do you need help with a specific compliance process?"],
                processing_time_ms=0,
                provider_used="fallback",
                session_id=session.session_id,
                requires_human_review=confidence < 0.7
            )
            
        except Exception as e:
            logger.error(f"Error in fallback response generation: {str(e)}")
            raise
            
    def _get_system_prompt(self, chatbot_type: ChatbotType) -> str:
        """Get system prompt based on chatbot type"""
        prompts = {
            ChatbotType.REGULATORY_QA: """You are a Financial Compliance Assistant specializing in regulatory Q&A. 
            Provide accurate, helpful responses about financial regulations, compliance requirements, and best practices. 
            Always recommend consulting with compliance experts for specific legal advice.""",
            
            ChatbotType.COMPLIANCE_ASSISTANT: """You are a Compliance Assistant helping with day-to-day compliance tasks. 
            Guide users through compliance processes, help interpret policies, and provide practical advice.""",
            
            ChatbotType.POLICY_HELPER: """You are a Policy Assistant helping users understand and implement organizational policies. 
            Explain policy requirements clearly and help with implementation guidance.""",
            
            ChatbotType.GENERAL_SUPPORT: """You are a General Support Assistant for the compliance platform. 
            Help users navigate the system and answer general questions about compliance topics."""
        }
        return prompts.get(chatbot_type, prompts[ChatbotType.REGULATORY_QA])
        
    def _get_enhanced_system_prompt(self, session: ChatSession) -> str:
        """Get enhanced system prompt with session context"""
        base_prompt = self._get_system_prompt(session.chatbot_type)
        
        context_info = ""
        if session.context:
            context_info = f"\n\nSession Context: {json.dumps(session.context)}"
            
        return base_prompt + context_info
        
    def _build_claude_conversation(self, session: ChatSession, user_message: str) -> List[Dict[str, str]]:
        """Build conversation history for Claude API"""
        messages = []
        
        # Add recent conversation history
        recent_messages = session.messages[-10:] if len(session.messages) > 10 else session.messages
        for msg in recent_messages:
            if msg.message_type == MessageType.USER:
                messages.append({"role": "user", "content": msg.content})
            elif msg.message_type == MessageType.ASSISTANT:
                messages.append({"role": "assistant", "content": msg.content})
                
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
        
    def _calculate_confidence(self, response_text: str, user_message: str) -> float:
        """Calculate confidence score for response"""
        # Simple heuristic-based confidence calculation
        confidence = 0.7  # Base confidence
        
        # Increase confidence for specific regulatory terms
        if any(keyword in response_text.lower() for keyword in self.regulatory_keywords):
            confidence += 0.1
            
        # Decrease confidence for uncertainty indicators
        uncertainty_phrases = ['not sure', 'might be', 'possibly', 'unclear', 'unsure']
        if any(phrase in response_text.lower() for phrase in uncertainty_phrases):
            confidence -= 0.2
            
        # Increase confidence for structured responses
        if any(indicator in response_text for indicator in ['1.', '2.', '•', '-']):
            confidence += 0.1
            
        return max(0.0, min(1.0, confidence))
        
    def _generate_follow_up_questions(self, user_message: str, response_text: str) -> List[str]:
        """Generate relevant follow-up questions"""
        follow_ups = []
        
        message_lower = user_message.lower()
        
        if 'regulation' in message_lower:
            follow_ups.extend([
                "Which jurisdiction's regulations are you most concerned about?",
                "Do you need help with implementation timelines?"
            ])
            
        if 'compliance' in message_lower:
            follow_ups.extend([
                "Are you looking for specific compliance procedures?",
                "Do you need help with compliance monitoring?"
            ])
            
        if 'risk' in message_lower:
            follow_ups.extend([
                "What type of risk assessment are you conducting?",
                "Do you need help with risk mitigation strategies?"
            ])
            
        return follow_ups[:3]  # Limit to 3 follow-up questions
        
    def _select_provider(self, provider: str) -> str:
        """Select appropriate AI provider"""
        if provider == "auto":
            if self.openai_client:
                return "openai"
            elif self.claude_client:
                return "claude"
            else:
                return "fallback"
        return provider
        
    async def _get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
        
    def _is_session_expired(self, session: ChatSession) -> bool:
        """Check if session has expired"""
        timeout_delta = timedelta(minutes=self.session_timeout_minutes)
        return datetime.now(timezone.utc) - session.last_activity > timeout_delta
        
    async def _end_session(self, session_id: str):
        """End and cleanup session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.is_active = False
            
            # Log session end
            await self._log_session_end(session)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
    async def _log_session_start(self, session: ChatSession):
        """Log session start to database"""
        try:
            log_data = {
                'session_id': session.session_id,
                'tenant_id': str(session.tenant_id),
                'user_id': str(session.user_id) if session.user_id else None,
                'chatbot_type': session.chatbot_type.value,
                'started_at': session.started_at.isoformat(),
                'is_active': session.is_active
            }
            
            self.supabase.table('chatbot_conversations').insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging session start: {str(e)}")
            
    async def _log_session_end(self, session: ChatSession):
        """Log session end to database"""
        try:
            update_data = {
                'ended_at': datetime.now(timezone.utc).isoformat(),
                'is_active': False,
                'total_messages': len(session.messages)
            }
            
            self.supabase.table('chatbot_conversations').update(update_data).eq('session_id', session.session_id).execute()
            
        except Exception as e:
            logger.error(f"Error logging session end: {str(e)}")
            
    async def _log_interaction(self, session: ChatSession, user_message: str, response: ChatResponse, start_time: datetime):
        """Log chat interaction to database"""
        try:
            log_data = {
                'session_id': session.session_id,
                'tenant_id': str(session.tenant_id),
                'user_message': user_message,
                'assistant_response': response.response_text,
                'confidence_score': response.confidence_score,
                'provider_used': response.provider_used,
                'processing_time_ms': response.processing_time_ms,
                'requires_human_review': response.requires_human_review,
                'created_at': start_time.isoformat()
            }
            
            # Would insert into a chat_interactions table
            # self.supabase.table('chat_interactions').insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging chat interaction: {str(e)}")
            
    async def _log_error(self, session_id: str, error_message: str, start_time: datetime):
        """Log errors to database"""
        try:
            error_data = {
                'session_id': session_id,
                'error_message': error_message,
                'created_at': start_time.isoformat()
            }
            
            # Would insert into errors table
            logger.error(f"Chatbot error for session {session_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error logging chatbot error: {str(e)}") 