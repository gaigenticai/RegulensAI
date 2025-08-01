"""
Base model classes for RegulensAI database models.
"""

from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel as PydanticBaseModel, Field
import uuid


class BaseModel(PydanticBaseModel):
    """Base model for all database entities."""
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return super().dict(**kwargs)


class TenantBaseModel(BaseModel):
    """Base model for tenant-scoped entities."""
    
    tenant_id: str = Field(..., description="Tenant identifier for multi-tenancy")


class AuditableModel(BaseModel):
    """Base model with audit fields."""
    
    created_by: Optional[str] = Field(None, description="User who created this record")
    updated_by: Optional[str] = Field(None, description="User who last updated this record")
    version: int = Field(default=1, description="Version number for optimistic locking")


class SoftDeleteModel(BaseModel):
    """Base model with soft delete capability."""
    
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    deleted_by: Optional[str] = Field(None, description="User who deleted this record")
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None


class FullAuditModel(TenantBaseModel, AuditableModel, SoftDeleteModel):
    """Complete base model with all audit and tenant features."""
    pass
