"""
Database Models Package
Central import point for all SQLAlchemy models in the RegulensAI platform.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import os

# Create declarative base
Base = declarative_base()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/regulensai')

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = scoped_session(SessionLocal)

# Import base models first
try:
    from .base import BaseModel
except ImportError:
    # Create a simple base model if not exists
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Column, DateTime
    from sqlalchemy.sql import func
    
    BaseModel = declarative_base()
    BaseModel.metadata.bind = engine

# Import core models
try:
    from .user_models import User
except ImportError:
    # Create placeholder User model if not exists
    from sqlalchemy import Column, String, Boolean, Text
    from sqlalchemy.dialects.postgresql import UUID
    import uuid
    
    class User(BaseModel):
        __tablename__ = 'users'
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        email = Column(String, unique=True, nullable=False)
        full_name = Column(String, nullable=False)
        role = Column(String, nullable=False, default='compliance_officer')
        department = Column(String)
        is_active = Column(Boolean, default=True)
        tenant_id = Column(UUID(as_uuid=True), nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

try:
    from .tenant_models import Tenant
except ImportError:
    # Create placeholder Tenant model if not exists
    from sqlalchemy import Column, String, Boolean, Text
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    import uuid
    
    class Tenant(BaseModel):
        __tablename__ = 'tenants'
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        name = Column(String, nullable=False)
        domain = Column(String, unique=True, nullable=False)
        industry = Column(String, nullable=False)
        country_code = Column(String, nullable=False)
        regulatory_jurisdictions = Column(JSONB, default=list)
        subscription_tier = Column(String, default='enterprise')
        settings = Column(JSONB, default=dict)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Import training portal models
from .training_models import (
    TrainingModule,
    TrainingSection,
    TrainingAssessment,
    TrainingEnrollment
)

from .training_models_extended import (
    TrainingSectionProgress,
    TrainingAssessmentAttempt,
    TrainingBookmark,
    TrainingCertificate
)

from .training_models_final import (
    TrainingAchievement,
    TrainingDiscussion,
    TrainingDiscussionVote,
    TrainingAnalytics,
    TrainingReport
)

# Add relationships to existing models
def setup_relationships():
    """Setup relationships between models after all imports."""
    try:
        # Add training_modules relationship to Tenant
        if hasattr(Tenant, '__table__') and not hasattr(Tenant, 'training_modules'):
            from sqlalchemy.orm import relationship
            Tenant.training_modules = relationship("TrainingModule", back_populates="tenant")
    except Exception as e:
        print(f"Warning: Could not setup tenant relationships: {e}")

# Setup relationships
setup_relationships()

# Export all models
__all__ = [
    'db',
    'engine',
    'SessionLocal',
    'Base',
    'BaseModel',
    'User',
    'Tenant',
    'TrainingModule',
    'TrainingSection',
    'TrainingAssessment',
    'TrainingEnrollment',
    'TrainingSectionProgress',
    'TrainingAssessmentAttempt',
    'TrainingBookmark',
    'TrainingCertificate',
    'TrainingAchievement',
    'TrainingDiscussion',
    'TrainingDiscussionVote',
    'TrainingAnalytics',
    'TrainingReport'
]

# Create all tables
def create_tables():
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️ Error creating database tables: {e}")

# Initialize database if needed
def init_db():
    """Initialize database with tables."""
    create_tables()

if __name__ == "__main__":
    init_db()
