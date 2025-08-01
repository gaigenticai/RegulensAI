"""
Regulens AI - Compliance Management Routes
Enterprise-grade compliance program and requirement management endpoints.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import (
    get_current_user,
    verify_tenant_access,
    require_permission,
    UserInDB
)
from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import (
    ResourceNotFoundException,
    DuplicateResourceException,
    exception_to_http_exception
)

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["Compliance Management"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ComplianceProgramCreate(BaseModel):
    """Compliance program creation request model."""
    name: str = Field(..., min_length=2, max_length=200, description="Program name")
    description: str = Field(..., min_length=10, description="Program description")
    framework: str = Field(..., description="Regulatory framework (e.g., SOX, GDPR, Basel III)")
    jurisdiction: str = Field(..., description="Regulatory jurisdiction")
    effective_date: datetime = Field(..., description="Program effective date")
    review_frequency: int = Field(..., ge=1, le=365, description="Review frequency in days")
    owner_id: str = Field(..., description="Program owner user ID")
    is_active: bool = Field(default=True, description="Program active status")

class ComplianceProgramUpdate(BaseModel):
    """Compliance program update request model."""
    name: Optional[str] = Field(None, min_length=2, max_length=200, description="Program name")
    description: Optional[str] = Field(None, min_length=10, description="Program description")
    framework: Optional[str] = Field(None, description="Regulatory framework")
    jurisdiction: Optional[str] = Field(None, description="Regulatory jurisdiction")
    effective_date: Optional[datetime] = Field(None, description="Program effective date")
    review_frequency: Optional[int] = Field(None, ge=1, le=365, description="Review frequency in days")
    owner_id: Optional[str] = Field(None, description="Program owner user ID")
    is_active: Optional[bool] = Field(None, description="Program active status")

class ComplianceRequirementCreate(BaseModel):
    """Compliance requirement creation request model."""
    program_id: str = Field(..., description="Parent compliance program ID")
    title: str = Field(..., min_length=2, max_length=200, description="Requirement title")
    description: str = Field(..., min_length=10, description="Requirement description")
    requirement_type: str = Field(..., description="Type of requirement")
    priority: str = Field(..., description="Priority level (low, medium, high, critical)")
    due_date: Optional[datetime] = Field(None, description="Due date for compliance")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    evidence_required: bool = Field(default=True, description="Whether evidence is required")
    automation_possible: bool = Field(default=False, description="Whether requirement can be automated")

class ComplianceRequirementUpdate(BaseModel):
    """Compliance requirement update request model."""
    title: Optional[str] = Field(None, min_length=2, max_length=200, description="Requirement title")
    description: Optional[str] = Field(None, min_length=10, description="Requirement description")
    requirement_type: Optional[str] = Field(None, description="Type of requirement")
    priority: Optional[str] = Field(None, description="Priority level")
    due_date: Optional[datetime] = Field(None, description="Due date for compliance")
    assigned_to: Optional[str] = Field(None, description="Assigned user ID")
    status: Optional[str] = Field(None, description="Requirement status")
    evidence_required: Optional[bool] = Field(None, description="Whether evidence is required")
    automation_possible: Optional[bool] = Field(None, description="Whether requirement can be automated")

class ComplianceProgramResponse(BaseModel):
    """Compliance program response model."""
    id: str
    name: str
    description: str
    framework: str
    jurisdiction: str
    effective_date: str
    review_frequency: int
    owner_id: str
    owner_name: str
    is_active: bool
    requirement_count: int
    completion_rate: float
    last_review_date: Optional[str]
    next_review_date: str
    created_at: str
    updated_at: str

class ComplianceRequirementResponse(BaseModel):
    """Compliance requirement response model."""
    id: str
    program_id: str
    program_name: str
    title: str
    description: str
    requirement_type: str
    priority: str
    status: str
    due_date: Optional[str]
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    evidence_required: bool
    automation_possible: bool
    completion_percentage: float
    created_at: str
    updated_at: str

# ============================================================================
# COMPLIANCE PROGRAM ENDPOINTS
# ============================================================================

@router.get("/programs", response_model=List[ComplianceProgramResponse])
async def get_compliance_programs(
    framework: Optional[str] = Query(None, description="Filter by framework"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: UserInDB = Depends(require_permission("compliance.programs.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get list of compliance programs.
    
    Requires permission: compliance.programs.read
    """
    try:
        async with get_database() as db:
            # Build query conditions
            conditions = ["cp.tenant_id = $1"]
            params = [uuid.UUID(tenant_id)]
            param_count = 1
            
            if framework:
                param_count += 1
                conditions.append(f"cp.framework = ${param_count}")
                params.append(framework)
            
            if jurisdiction:
                param_count += 1
                conditions.append(f"cp.jurisdiction = ${param_count}")
                params.append(jurisdiction)
            
            if is_active is not None:
                param_count += 1
                conditions.append(f"cp.is_active = ${param_count}")
                params.append(is_active)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT cp.*, 
                       u.full_name as owner_name,
                       COALESCE(req_stats.requirement_count, 0) as requirement_count,
                       COALESCE(req_stats.completion_rate, 0) as completion_rate,
                       cp.effective_date + (cp.review_frequency || ' days')::interval as next_review_date
                FROM compliance_programs cp
                LEFT JOIN users u ON cp.owner_id = u.id
                LEFT JOIN (
                    SELECT program_id,
                           COUNT(*) as requirement_count,
                           ROUND(AVG(CASE WHEN status = 'completed' THEN 100 ELSE 0 END), 2) as completion_rate
                    FROM compliance_requirements
                    GROUP BY program_id
                ) req_stats ON cp.id = req_stats.program_id
                WHERE {where_clause}
                ORDER BY cp.created_at DESC
            """
            
            programs = await db.fetch(query, *params)
            
            return [
                ComplianceProgramResponse(
                    id=str(program['id']),
                    name=program['name'],
                    description=program['description'],
                    framework=program['framework'],
                    jurisdiction=program['jurisdiction'],
                    effective_date=program['effective_date'].isoformat(),
                    review_frequency=program['review_frequency'],
                    owner_id=str(program['owner_id']),
                    owner_name=program['owner_name'] or "Unknown",
                    is_active=program['is_active'],
                    requirement_count=program['requirement_count'],
                    completion_rate=program['completion_rate'],
                    last_review_date=program['last_review_date'].isoformat() if program['last_review_date'] else None,
                    next_review_date=program['next_review_date'].isoformat(),
                    created_at=program['created_at'].isoformat(),
                    updated_at=program['updated_at'].isoformat()
                )
                for program in programs
            ]
            
    except Exception as e:
        logger.error(f"Get compliance programs failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve compliance programs"
        )

@router.post("/programs", response_model=ComplianceProgramResponse)
async def create_compliance_program(
    program_data: ComplianceProgramCreate,
    current_user: UserInDB = Depends(require_permission("compliance.programs.create")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Create a new compliance program.
    
    Requires permission: compliance.programs.create
    """
    try:
        async with get_database() as db:
            # Check if program name already exists
            existing_program = await db.fetchrow(
                "SELECT id FROM compliance_programs WHERE name = $1 AND tenant_id = $2",
                program_data.name,
                uuid.UUID(tenant_id)
            )
            
            if existing_program:
                raise DuplicateResourceException("compliance_program", program_data.name)
            
            # Verify owner exists
            owner = await db.fetchrow(
                "SELECT id, full_name FROM users WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(program_data.owner_id),
                uuid.UUID(tenant_id)
            )
            
            if not owner:
                raise ResourceNotFoundException("user", program_data.owner_id)
            
            # Create program
            program_id = uuid.uuid4()
            next_review_date = program_data.effective_date + timedelta(days=program_data.review_frequency)
            
            program_record = await db.fetchrow(
                """
                INSERT INTO compliance_programs (
                    id, tenant_id, name, description, framework, jurisdiction,
                    effective_date, review_frequency, owner_id, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                program_id,
                uuid.UUID(tenant_id),
                program_data.name,
                program_data.description,
                program_data.framework,
                program_data.jurisdiction,
                program_data.effective_date,
                program_data.review_frequency,
                uuid.UUID(program_data.owner_id),
                program_data.is_active
            )
            
            logger.info(f"Compliance program created: {program_data.name} by {current_user.email}")
            
            return ComplianceProgramResponse(
                id=str(program_record['id']),
                name=program_record['name'],
                description=program_record['description'],
                framework=program_record['framework'],
                jurisdiction=program_record['jurisdiction'],
                effective_date=program_record['effective_date'].isoformat(),
                review_frequency=program_record['review_frequency'],
                owner_id=str(program_record['owner_id']),
                owner_name=owner['full_name'],
                is_active=program_record['is_active'],
                requirement_count=0,
                completion_rate=0.0,
                last_review_date=None,
                next_review_date=next_review_date.isoformat(),
                created_at=program_record['created_at'].isoformat(),
                updated_at=program_record['updated_at'].isoformat()
            )
            
    except (DuplicateResourceException, ResourceNotFoundException) as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Create compliance program failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create compliance program"
        )

@router.get("/programs/{program_id}", response_model=ComplianceProgramResponse)
async def get_compliance_program(
    program_id: str,
    current_user: UserInDB = Depends(require_permission("compliance.programs.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get compliance program by ID.
    
    Requires permission: compliance.programs.read
    """
    try:
        async with get_database() as db:
            query = """
                SELECT cp.*, 
                       u.full_name as owner_name,
                       COALESCE(req_stats.requirement_count, 0) as requirement_count,
                       COALESCE(req_stats.completion_rate, 0) as completion_rate,
                       cp.effective_date + (cp.review_frequency || ' days')::interval as next_review_date
                FROM compliance_programs cp
                LEFT JOIN users u ON cp.owner_id = u.id
                LEFT JOIN (
                    SELECT program_id,
                           COUNT(*) as requirement_count,
                           ROUND(AVG(CASE WHEN status = 'completed' THEN 100 ELSE 0 END), 2) as completion_rate
                    FROM compliance_requirements
                    WHERE program_id = $1
                    GROUP BY program_id
                ) req_stats ON cp.id = req_stats.program_id
                WHERE cp.id = $1 AND cp.tenant_id = $2
            """
            
            program = await db.fetchrow(query, uuid.UUID(program_id), uuid.UUID(tenant_id))
            
            if not program:
                raise ResourceNotFoundException("compliance_program", program_id)
            
            return ComplianceProgramResponse(
                id=str(program['id']),
                name=program['name'],
                description=program['description'],
                framework=program['framework'],
                jurisdiction=program['jurisdiction'],
                effective_date=program['effective_date'].isoformat(),
                review_frequency=program['review_frequency'],
                owner_id=str(program['owner_id']),
                owner_name=program['owner_name'] or "Unknown",
                is_active=program['is_active'],
                requirement_count=program['requirement_count'],
                completion_rate=program['completion_rate'],
                last_review_date=program['last_review_date'].isoformat() if program['last_review_date'] else None,
                next_review_date=program['next_review_date'].isoformat(),
                created_at=program['created_at'].isoformat(),
                updated_at=program['updated_at'].isoformat()
            )
            
    except ResourceNotFoundException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Get compliance program failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve compliance program"
        )
