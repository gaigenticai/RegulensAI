"""
Training Portal Database Models
SQLAlchemy models for the training portal functionality.
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


class TrainingModule(BaseModel):
    """Training modules/courses with content and metadata."""
    
    __tablename__ = 'training_modules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    module_code = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False)
    difficulty_level = Column(String, nullable=False, default='beginner')
    estimated_duration_minutes = Column(Integer, nullable=False, default=60)
    prerequisites = Column(JSONB, default=list)
    learning_objectives = Column(JSONB, default=list)
    content_type = Column(String, nullable=False, default='interactive')
    content_url = Column(String)
    content_data = Column(JSONB, default=dict)
    is_mandatory = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    version = Column(String, nullable=False, default='1.0')
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="training_modules")
    creator = relationship("User", foreign_keys=[created_by])
    sections = relationship("TrainingSection", back_populates="module", cascade="all, delete-orphan")
    assessments = relationship("TrainingAssessment", back_populates="module", cascade="all, delete-orphan")
    enrollments = relationship("TrainingEnrollment", back_populates="module", cascade="all, delete-orphan")
    certificates = relationship("TrainingCertificate", back_populates="module")
    discussions = relationship("TrainingDiscussion", back_populates="module")
    bookmarks = relationship("TrainingBookmark", back_populates="module")
    analytics = relationship("TrainingAnalytics", back_populates="module")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            category.in_(['notification_management', 'external_data', 'operational_procedures', 
                         'api_usage', 'compliance', 'security', 'general']),
            name='chk_training_module_category'
        ),
        CheckConstraint(
            difficulty_level.in_(['beginner', 'intermediate', 'advanced', 'expert']),
            name='chk_training_module_difficulty'
        ),
        CheckConstraint(
            content_type.in_(['interactive', 'video', 'document', 'hands_on', 'mixed']),
            name='chk_training_module_content_type'
        ),
        Index('idx_training_modules_tenant', 'tenant_id'),
        Index('idx_training_modules_category', 'category'),
        Index('idx_training_modules_active', 'is_active'),
        Index('idx_training_modules_difficulty', 'difficulty_level'),
    )
    
    @validates('category')
    def validate_category(self, key, category):
        valid_categories = ['notification_management', 'external_data', 'operational_procedures', 
                           'api_usage', 'compliance', 'security', 'general']
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {valid_categories}")
        return category
    
    @validates('difficulty_level')
    def validate_difficulty(self, key, difficulty):
        valid_levels = ['beginner', 'intermediate', 'advanced', 'expert']
        if difficulty not in valid_levels:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_levels}")
        return difficulty
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'module_code': self.module_code,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'difficulty_level': self.difficulty_level,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'prerequisites': self.prerequisites,
            'learning_objectives': self.learning_objectives,
            'content_type': self.content_type,
            'content_url': self.content_url,
            'content_data': self.content_data,
            'is_mandatory': self.is_mandatory,
            'is_active': self.is_active,
            'version': self.version,
            'created_by': str(self.created_by),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TrainingSection(BaseModel):
    """Individual sections within training modules."""
    
    __tablename__ = 'training_sections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id', ondelete='CASCADE'), nullable=False)
    section_code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    content_markdown = Column(Text)
    content_html = Column(Text)
    section_order = Column(Integer, nullable=False, default=1)
    estimated_duration_minutes = Column(Integer, default=15)
    is_interactive = Column(Boolean, default=False)
    interactive_elements = Column(JSONB, default=dict)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    module = relationship("TrainingModule", back_populates="sections")
    progress_records = relationship("TrainingSectionProgress", back_populates="section", cascade="all, delete-orphan")
    assessments = relationship("TrainingAssessment", back_populates="section")
    discussions = relationship("TrainingDiscussion", back_populates="section")
    bookmarks = relationship("TrainingBookmark", back_populates="section")
    analytics = relationship("TrainingAnalytics", back_populates="section")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('module_id', 'section_code', name='uq_training_sections_module_code'),
        Index('idx_training_sections_module', 'module_id'),
        Index('idx_training_sections_order', 'module_id', 'section_order'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'module_id': str(self.module_id),
            'section_code': self.section_code,
            'title': self.title,
            'description': self.description,
            'content_markdown': self.content_markdown,
            'content_html': self.content_html,
            'section_order': self.section_order,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'is_interactive': self.is_interactive,
            'interactive_elements': self.interactive_elements,
            'is_required': self.is_required,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TrainingAssessment(BaseModel):
    """Quizzes and assessments for training modules."""
    
    __tablename__ = 'training_assessments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey('training_sections.id', ondelete='CASCADE'))
    assessment_code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    assessment_type = Column(String, nullable=False, default='quiz')
    passing_score = Column(Integer, nullable=False, default=80)
    max_attempts = Column(Integer, default=3)
    time_limit_minutes = Column(Integer, default=30)
    questions = Column(JSONB, nullable=False, default=list)
    is_required = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    module = relationship("TrainingModule", back_populates="assessments")
    section = relationship("TrainingSection", back_populates="assessments")
    attempts = relationship("TrainingAssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('module_id', 'assessment_code', name='uq_training_assessments_module_code'),
        CheckConstraint(
            assessment_type.in_(['quiz', 'practical', 'essay', 'hands_on', 'survey']),
            name='chk_training_assessment_type'
        ),
        CheckConstraint(
            'passing_score >= 0 AND passing_score <= 100',
            name='chk_training_assessment_passing_score'
        ),
        Index('idx_training_assessments_module', 'module_id'),
        Index('idx_training_assessments_section', 'section_id'),
        Index('idx_training_assessments_active', 'is_active'),
    )
    
    @validates('assessment_type')
    def validate_assessment_type(self, key, assessment_type):
        valid_types = ['quiz', 'practical', 'essay', 'hands_on', 'survey']
        if assessment_type not in valid_types:
            raise ValueError(f"Invalid assessment type. Must be one of: {valid_types}")
        return assessment_type
    
    @validates('passing_score')
    def validate_passing_score(self, key, score):
        if score < 0 or score > 100:
            raise ValueError("Passing score must be between 0 and 100")
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'module_id': str(self.module_id),
            'section_id': str(self.section_id) if self.section_id else None,
            'assessment_code': self.assessment_code,
            'title': self.title,
            'description': self.description,
            'assessment_type': self.assessment_type,
            'passing_score': self.passing_score,
            'max_attempts': self.max_attempts,
            'time_limit_minutes': self.time_limit_minutes,
            'questions': self.questions,
            'is_required': self.is_required,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TrainingEnrollment(BaseModel):
    """User enrollment and progress tracking for training modules."""

    __tablename__ = 'training_enrollments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id', ondelete='CASCADE'), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    enrolled_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    target_completion_date = Column(DateTime(timezone=True))
    status = Column(String, nullable=False, default='enrolled')
    completion_percentage = Column(Numeric(5, 2), default=0.0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    last_accessed_at = Column(DateTime(timezone=True))
    total_time_spent_minutes = Column(Integer, default=0)
    notes = Column(Text)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    enrolling_user = relationship("User", foreign_keys=[enrolled_by])
    module = relationship("TrainingModule", back_populates="enrollments")
    section_progress = relationship("TrainingSectionProgress", back_populates="enrollment", cascade="all, delete-orphan")
    assessment_attempts = relationship("TrainingAssessmentAttempt", back_populates="enrollment", cascade="all, delete-orphan")
    certificates = relationship("TrainingCertificate", back_populates="enrollment")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'module_id', name='uq_training_enrollments_user_module'),
        CheckConstraint(
            status.in_(['enrolled', 'in_progress', 'completed', 'failed', 'expired', 'withdrawn']),
            name='chk_training_enrollment_status'
        ),
        CheckConstraint(
            'completion_percentage >= 0.0 AND completion_percentage <= 100.0',
            name='chk_training_enrollment_completion_percentage'
        ),
        Index('idx_training_enrollments_user', 'user_id'),
        Index('idx_training_enrollments_module', 'module_id'),
        Index('idx_training_enrollments_status', 'status'),
        Index('idx_training_enrollments_completion', 'completed_at'),
    )

    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['enrolled', 'in_progress', 'completed', 'failed', 'expired', 'withdrawn']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return status

    @validates('completion_percentage')
    def validate_completion_percentage(self, key, percentage):
        if percentage < 0.0 or percentage > 100.0:
            raise ValueError("Completion percentage must be between 0.0 and 100.0")
        return percentage

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'module_id': str(self.module_id),
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None,
            'enrolled_by': str(self.enrolled_by) if self.enrolled_by else None,
            'target_completion_date': self.target_completion_date.isoformat() if self.target_completion_date else None,
            'status': self.status,
            'completion_percentage': float(self.completion_percentage) if self.completion_percentage else 0.0,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'total_time_spent_minutes': self.total_time_spent_minutes,
            'notes': self.notes
        }
