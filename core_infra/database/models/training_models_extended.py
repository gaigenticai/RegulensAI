"""
Training Portal Database Models (Extended)
Additional SQLAlchemy models for the training portal functionality.
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
from core_infra.database.models.training_models import TrainingModule, TrainingSection, TrainingEnrollment, TrainingAssessment


class TrainingSectionProgress(BaseModel):
    """Detailed progress tracking through training sections."""
    
    __tablename__ = 'training_section_progress'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('training_enrollments.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey('training_sections.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, nullable=False, default='not_started')
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    time_spent_minutes = Column(Integer, default=0)
    last_position = Column(String)
    notes = Column(Text)
    interactions = Column(JSONB, default=dict)
    
    # Relationships
    enrollment = relationship("TrainingEnrollment", back_populates="section_progress")
    section = relationship("TrainingSection", back_populates="progress_records")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('enrollment_id', 'section_id', name='uq_training_section_progress_enrollment_section'),
        CheckConstraint(
            status.in_(['not_started', 'in_progress', 'completed', 'skipped']),
            name='chk_training_section_progress_status'
        ),
        Index('idx_training_section_progress_enrollment', 'enrollment_id'),
        Index('idx_training_section_progress_section', 'section_id'),
        Index('idx_training_section_progress_status', 'status'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['not_started', 'in_progress', 'completed', 'skipped']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'enrollment_id': str(self.enrollment_id),
            'section_id': str(self.section_id),
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_spent_minutes': self.time_spent_minutes,
            'last_position': self.last_position,
            'notes': self.notes,
            'interactions': self.interactions
        }


class TrainingAssessmentAttempt(BaseModel):
    """Assessment attempts and results with detailed scoring."""
    
    __tablename__ = 'training_assessment_attempts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('training_enrollments.id', ondelete='CASCADE'), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey('training_assessments.id', ondelete='CASCADE'), nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    time_spent_minutes = Column(Integer)
    answers = Column(JSONB, default=dict)
    score = Column(Numeric(5, 2))
    passed = Column(Boolean, default=False)
    feedback = Column(JSONB, default=dict)
    status = Column(String, nullable=False, default='in_progress')
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # Relationships
    enrollment = relationship("TrainingEnrollment", back_populates="assessment_attempts")
    assessment = relationship("TrainingAssessment", back_populates="attempts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            status.in_(['in_progress', 'completed', 'abandoned', 'expired']),
            name='chk_training_assessment_attempt_status'
        ),
        CheckConstraint(
            'score IS NULL OR (score >= 0.0 AND score <= 100.0)',
            name='chk_training_assessment_attempt_score'
        ),
        Index('idx_training_assessment_attempts_enrollment', 'enrollment_id'),
        Index('idx_training_assessment_attempts_assessment', 'assessment_id'),
        Index('idx_training_assessment_attempts_completed', 'completed_at'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['in_progress', 'completed', 'abandoned', 'expired']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return status
    
    @validates('score')
    def validate_score(self, key, score):
        if score is not None and (score < 0.0 or score > 100.0):
            raise ValueError("Score must be between 0.0 and 100.0")
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'enrollment_id': str(self.enrollment_id),
            'assessment_id': str(self.assessment_id),
            'attempt_number': self.attempt_number,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_spent_minutes': self.time_spent_minutes,
            'answers': self.answers,
            'score': float(self.score) if self.score else None,
            'passed': self.passed,
            'feedback': self.feedback,
            'status': self.status,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent
        }


class TrainingBookmark(BaseModel):
    """User bookmarks and favorites for training content."""
    
    __tablename__ = 'training_bookmarks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id', ondelete='CASCADE'))
    section_id = Column(UUID(as_uuid=True), ForeignKey('training_sections.id', ondelete='CASCADE'))
    bookmark_type = Column(String, nullable=False, default='section')
    title = Column(String, nullable=False)
    description = Column(Text)
    position_data = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    is_private = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    module = relationship("TrainingModule", back_populates="bookmarks")
    section = relationship("TrainingSection", back_populates="bookmarks")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            bookmark_type.in_(['module', 'section', 'position']),
            name='chk_training_bookmark_type'
        ),
        Index('idx_training_bookmarks_user', 'user_id'),
        Index('idx_training_bookmarks_module', 'module_id'),
        Index('idx_training_bookmarks_section', 'section_id'),
    )
    
    @validates('bookmark_type')
    def validate_bookmark_type(self, key, bookmark_type):
        valid_types = ['module', 'section', 'position']
        if bookmark_type not in valid_types:
            raise ValueError(f"Invalid bookmark type. Must be one of: {valid_types}")
        return bookmark_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'module_id': str(self.module_id) if self.module_id else None,
            'section_id': str(self.section_id) if self.section_id else None,
            'bookmark_type': self.bookmark_type,
            'title': self.title,
            'description': self.description,
            'position_data': self.position_data,
            'tags': self.tags,
            'is_private': self.is_private,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TrainingCertificate(BaseModel):
    """Training completion certificates with verification."""
    
    __tablename__ = 'training_certificates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey('training_modules.id', ondelete='CASCADE'), nullable=False)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('training_enrollments.id', ondelete='CASCADE'), nullable=False)
    certificate_number = Column(String, unique=True, nullable=False)
    certificate_type = Column(String, nullable=False, default='completion')
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    final_score = Column(Numeric(5, 2))
    certificate_data = Column(JSONB, default=dict)
    verification_code = Column(String, unique=True, nullable=False)
    is_valid = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True))
    revoked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    revocation_reason = Column(Text)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    module = relationship("TrainingModule", back_populates="certificates")
    enrollment = relationship("TrainingEnrollment", back_populates="certificates")
    revoking_user = relationship("User", foreign_keys=[revoked_by])
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            certificate_type.in_(['completion', 'proficiency', 'mastery', 'participation']),
            name='chk_training_certificate_type'
        ),
        Index('idx_training_certificates_user', 'user_id'),
        Index('idx_training_certificates_module', 'module_id'),
        Index('idx_training_certificates_issued', 'issued_at'),
        Index('idx_training_certificates_verification', 'verification_code'),
    )
    
    @validates('certificate_type')
    def validate_certificate_type(self, key, certificate_type):
        valid_types = ['completion', 'proficiency', 'mastery', 'participation']
        if certificate_type not in valid_types:
            raise ValueError(f"Invalid certificate type. Must be one of: {valid_types}")
        return certificate_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'module_id': str(self.module_id),
            'enrollment_id': str(self.enrollment_id),
            'certificate_number': self.certificate_number,
            'certificate_type': self.certificate_type,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'final_score': float(self.final_score) if self.final_score else None,
            'certificate_data': self.certificate_data,
            'verification_code': self.verification_code,
            'is_valid': self.is_valid,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'revoked_by': str(self.revoked_by) if self.revoked_by else None,
            'revocation_reason': self.revocation_reason
        }
