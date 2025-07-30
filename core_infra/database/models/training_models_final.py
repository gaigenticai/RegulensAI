"""
Training Portal Database Models (Final)
Final set of SQLAlchemy models for the training portal functionality.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Numeric, 
    ForeignKey, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import uuid

from core_infra.database.models.base import BaseModel
from core_infra.database.models.user_models import User
from core_infra.database.models.tenant_models import Tenant
from core_infra.database.models.training_models import TrainingModule, TrainingSection


class TrainingAchievement(BaseModel):
    """User achievements and badges for training milestones."""
    
    __tablename__ = 'training_achievements'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    achievement_type = Column(String, nullable=False)
    achievement_name = Column(String, nullable=False)
    description = Column(Text)
    icon_url = Column(String)
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    related_module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id'))
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User")
    related_module = relationship("TrainingModule")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            achievement_type.in_(['first_completion', 'perfect_score', 'speed_learner', 'helping_hand', 
                                'streak_7', 'streak_14', 'streak_30', 'category_master', 'mentor']),
            name='chk_training_achievement_type'
        ),
        Index('idx_training_achievements_user', 'user_id'),
        Index('idx_training_achievements_type', 'achievement_type'),
        Index('idx_training_achievements_earned', 'earned_at'),
    )
    
    @validates('achievement_type')
    def validate_achievement_type(self, key, achievement_type):
        valid_types = ['first_completion', 'perfect_score', 'speed_learner', 'helping_hand', 
                      'streak_7', 'streak_14', 'streak_30', 'category_master', 'mentor']
        if achievement_type not in valid_types:
            raise ValueError(f"Invalid achievement type. Must be one of: {valid_types}")
        return achievement_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'achievement_type': self.achievement_type,
            'achievement_name': self.achievement_name,
            'description': self.description,
            'icon_url': self.icon_url,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'related_module_id': str(self.related_module_id) if self.related_module_id else None,
            'metadata': self.metadata
        }


class TrainingDiscussion(BaseModel):
    """Discussion forums and Q&A for training modules."""
    
    __tablename__ = 'training_discussions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey('training_sections.id', ondelete='CASCADE'))
    parent_id = Column(UUID(as_uuid=True), ForeignKey('training_discussions.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String)
    content = Column(Text, nullable=False)
    discussion_type = Column(String, nullable=False, default='question')
    is_pinned = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    module = relationship("TrainingModule", back_populates="discussions")
    section = relationship("TrainingSection", back_populates="discussions")
    user = relationship("User")
    parent = relationship("TrainingDiscussion", remote_side=[id])
    replies = relationship("TrainingDiscussion", back_populates="parent", cascade="all, delete-orphan")
    votes = relationship("TrainingDiscussionVote", back_populates="discussion", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            discussion_type.in_(['question', 'comment', 'answer', 'tip', 'announcement']),
            name='chk_training_discussion_type'
        ),
        Index('idx_training_discussions_module', 'module_id'),
        Index('idx_training_discussions_section', 'section_id'),
        Index('idx_training_discussions_parent', 'parent_id'),
        Index('idx_training_discussions_user', 'user_id'),
        Index('idx_training_discussions_created', 'created_at'),
    )
    
    @validates('discussion_type')
    def validate_discussion_type(self, key, discussion_type):
        valid_types = ['question', 'comment', 'answer', 'tip', 'announcement']
        if discussion_type not in valid_types:
            raise ValueError(f"Invalid discussion type. Must be one of: {valid_types}")
        return discussion_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'module_id': str(self.module_id),
            'section_id': str(self.section_id) if self.section_id else None,
            'parent_id': str(self.parent_id) if self.parent_id else None,
            'user_id': str(self.user_id),
            'title': self.title,
            'content': self.content,
            'discussion_type': self.discussion_type,
            'is_pinned': self.is_pinned,
            'is_resolved': self.is_resolved,
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TrainingDiscussionVote(BaseModel):
    """Voting system for training discussions."""
    
    __tablename__ = 'training_discussion_votes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discussion_id = Column(UUID(as_uuid=True), ForeignKey('training_discussions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    vote_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    discussion = relationship("TrainingDiscussion", back_populates="votes")
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('discussion_id', 'user_id', name='uq_training_discussion_votes_discussion_user'),
        CheckConstraint(
            vote_type.in_(['upvote', 'downvote']),
            name='chk_training_discussion_vote_type'
        ),
    )
    
    @validates('vote_type')
    def validate_vote_type(self, key, vote_type):
        valid_types = ['upvote', 'downvote']
        if vote_type not in valid_types:
            raise ValueError(f"Invalid vote type. Must be one of: {valid_types}")
        return vote_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'discussion_id': str(self.discussion_id),
            'user_id': str(self.user_id),
            'vote_type': self.vote_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TrainingAnalytics(BaseModel):
    """Analytics events for training portal usage tracking."""
    
    __tablename__ = 'training_analytics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSONB, default=dict)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id'))
    section_id = Column(UUID(as_uuid=True), ForeignKey('training_sections.id'))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User")
    tenant = relationship("Tenant")
    module = relationship("TrainingModule", back_populates="analytics")
    section = relationship("TrainingSection", back_populates="analytics")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            event_type.in_(['page_view', 'section_start', 'section_complete', 'assessment_start', 
                           'assessment_complete', 'bookmark_create', 'bookmark_delete', 'discussion_post', 
                           'search_query', 'download', 'print', 'share']),
            name='chk_training_analytics_event_type'
        ),
        Index('idx_training_analytics_user', 'user_id'),
        Index('idx_training_analytics_tenant', 'tenant_id'),
        Index('idx_training_analytics_timestamp', 'timestamp'),
        Index('idx_training_analytics_event_type', 'event_type'),
        Index('idx_training_analytics_module', 'module_id'),
    )
    
    @validates('event_type')
    def validate_event_type(self, key, event_type):
        valid_types = ['page_view', 'section_start', 'section_complete', 'assessment_start', 
                      'assessment_complete', 'bookmark_create', 'bookmark_delete', 'discussion_post', 
                      'search_query', 'download', 'print', 'share']
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type. Must be one of: {valid_types}")
        return event_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'tenant_id': str(self.tenant_id),
            'session_id': self.session_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'module_id': str(self.module_id) if self.module_id else None,
            'section_id': str(self.section_id) if self.section_id else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent
        }


class TrainingReport(BaseModel):
    """Generated training reports and analytics summaries."""
    
    __tablename__ = 'training_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    report_type = Column(String, nullable=False)
    report_name = Column(String, nullable=False)
    parameters = Column(JSONB, default=dict)
    generated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    report_data = Column(JSONB, default=dict)
    file_path = Column(String)
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    tenant = relationship("Tenant")
    generator = relationship("User")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            report_type.in_(['completion_summary', 'progress_report', 'assessment_analysis', 
                           'engagement_metrics', 'certificate_report']),
            name='chk_training_report_type'
        ),
        Index('idx_training_reports_tenant', 'tenant_id'),
        Index('idx_training_reports_type', 'report_type'),
        Index('idx_training_reports_generated', 'generated_at'),
    )
    
    @validates('report_type')
    def validate_report_type(self, key, report_type):
        valid_types = ['completion_summary', 'progress_report', 'assessment_analysis', 
                      'engagement_metrics', 'certificate_report']
        if report_type not in valid_types:
            raise ValueError(f"Invalid report type. Must be one of: {valid_types}")
        return report_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'report_type': self.report_type,
            'report_name': self.report_name,
            'parameters': self.parameters,
            'generated_by': str(self.generated_by),
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'report_data': self.report_data,
            'file_path': self.file_path,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
