"""
Regulens AI - Tenant Management Routes
Enterprise-grade multi-tenant organization management with comprehensive settings.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
import structlog

from core_infra.api.auth import (
    get_current_user,
    require_permission,
    UserInDB
)
from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["Tenant Management"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TenantCreate(BaseModel):
    """Tenant creation request model."""
    name: str = Field(..., min_length=2, max_length=100, description="Organization name")
    domain: str = Field(..., min_length=2, max_length=100, description="Organization domain")
    industry: Optional[str] = Field(None, max_length=50, description="Industry sector")
    country: str = Field(..., min_length=2, max_length=2, description="Country code (ISO 3166-1 alpha-2)")
    timezone: str = Field(default="UTC", description="Default timezone")
    settings: Dict[str, Any] = Field(default={}, description="Tenant-specific settings")
    is_active: bool = Field(default=True, description="Tenant active status")

class TenantUpdate(BaseModel):
    """Tenant update request model."""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Organization name")
    domain: Optional[str] = Field(None, min_length=2, max_length=100, description="Organization domain")
    industry: Optional[str] = Field(None, max_length=50, description="Industry sector")
    country: Optional[str] = Field(None, min_length=2, max_length=2, description="Country code")
    timezone: Optional[str] = Field(None, description="Default timezone")
    is_active: Optional[bool] = Field(None, description="Tenant active status")

class TenantSettingsUpdate(BaseModel):
    """Tenant settings update request model."""
    settings: Dict[str, Any] = Field(..., description="Tenant-specific settings")

class TenantResponse(BaseModel):
    """Tenant response model."""
    id: str
    name: str
    domain: str
    industry: Optional[str]
    country: str
    timezone: str
    settings: Dict[str, Any]
    is_active: bool
    user_count: int
    created_at: str
    updated_at: str

class TenantListResponse(BaseModel):
    """Tenant list response model."""
    tenants: List[TenantResponse]
    total: int
    page: int
    size: int
    pages: int

# ============================================================================
# TENANT MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/", response_model=TenantListResponse)
async def get_tenants(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or domain"),
    current_user: UserInDB = Depends(require_permission("tenants.read"))
):
    """
    Get list of tenants with pagination and filtering.
    
    Requires permission: tenants.read
    """
    try:
        offset = (page - 1) * size
        
        # Build query conditions
        conditions = []
        params = []
        param_count = 0
        
        if industry:
            param_count += 1
            conditions.append(f"t.industry = ${param_count}")
            params.append(industry)
        
        if country:
            param_count += 1
            conditions.append(f"t.country = ${param_count}")
            params.append(country)
        
        if is_active is not None:
            param_count += 1
            conditions.append(f"t.is_active = ${param_count}")
            params.append(is_active)
        
        if search:
            param_count += 1
            conditions.append(f"(t.name ILIKE ${param_count} OR t.domain ILIKE ${param_count})")
            params.append(f"%{search}%")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        async with get_database() as db:
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM tenants t
                {where_clause}
            """
            total_result = await db.fetchrow(count_query, *params)
            total = total_result['total']
            
            # Get tenants with user counts
            tenants_query = f"""
                SELECT t.*, 
                       COALESCE(u.user_count, 0) as user_count
                FROM tenants t
                LEFT JOIN (
                    SELECT tenant_id, COUNT(*) as user_count
                    FROM users
                    WHERE is_active = true
                    GROUP BY tenant_id
                ) u ON t.id = u.tenant_id
                {where_clause}
                ORDER BY t.created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([size, offset])
            
            tenants_records = await db.fetch(tenants_query, *params)
            
            # Format response
            tenants = []
            for record in tenants_records:
                tenant_data = TenantResponse(
                    id=str(record['id']),
                    name=record['name'],
                    domain=record['domain'],
                    industry=record['industry'],
                    country=record['country'],
                    timezone=record['timezone'],
                    settings=record['settings'] or {},
                    is_active=record['is_active'],
                    user_count=record['user_count'],
                    created_at=record['created_at'].isoformat(),
                    updated_at=record['updated_at'].isoformat()
                )
                tenants.append(tenant_data)
            
            pages = (total + size - 1) // size
            
            return TenantListResponse(
                tenants=tenants,
                total=total,
                page=page,
                size=size,
                pages=pages
            )
            
    except Exception as e:
        logger.error(f"Get tenants failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenants"
        )

@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: UserInDB = Depends(require_permission("tenants.create"))
):
    """
    Create a new tenant.
    
    Requires permission: tenants.create
    """
    try:
        async with get_database() as db:
            # Check if domain already exists
            existing_tenant = await db.fetchrow(
                "SELECT id FROM tenants WHERE domain = $1",
                tenant_data.domain
            )
            
            if existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Domain already registered"
                )
            
            # Create tenant
            tenant_id = uuid.uuid4()
            tenant_insert_query = """
                INSERT INTO tenants (
                    id, name, domain, industry, country, timezone, settings, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """
            
            tenant_record = await db.fetchrow(
                tenant_insert_query,
                tenant_id,
                tenant_data.name,
                tenant_data.domain,
                tenant_data.industry,
                tenant_data.country,
                tenant_data.timezone,
                tenant_data.settings,
                tenant_data.is_active
            )
            
            logger.info(f"Tenant created: {tenant_data.name} ({tenant_data.domain}) by {current_user.email}")
            
            # Return created tenant
            return TenantResponse(
                id=str(tenant_record['id']),
                name=tenant_record['name'],
                domain=tenant_record['domain'],
                industry=tenant_record['industry'],
                country=tenant_record['country'],
                timezone=tenant_record['timezone'],
                settings=tenant_record['settings'] or {},
                is_active=tenant_record['is_active'],
                user_count=0,
                created_at=tenant_record['created_at'].isoformat(),
                updated_at=tenant_record['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create tenant failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant"
        )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: UserInDB = Depends(require_permission("tenants.read"))
):
    """
    Get tenant by ID.
    
    Requires permission: tenants.read
    """
    try:
        async with get_database() as db:
            query = """
                SELECT t.*, 
                       COALESCE(u.user_count, 0) as user_count
                FROM tenants t
                LEFT JOIN (
                    SELECT tenant_id, COUNT(*) as user_count
                    FROM users
                    WHERE is_active = true
                    GROUP BY tenant_id
                ) u ON t.id = u.tenant_id
                WHERE t.id = $1
            """
            
            tenant_record = await db.fetchrow(query, uuid.UUID(tenant_id))
            
            if not tenant_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            return TenantResponse(
                id=str(tenant_record['id']),
                name=tenant_record['name'],
                domain=tenant_record['domain'],
                industry=tenant_record['industry'],
                country=tenant_record['country'],
                timezone=tenant_record['timezone'],
                settings=tenant_record['settings'] or {},
                is_active=tenant_record['is_active'],
                user_count=tenant_record['user_count'],
                created_at=tenant_record['created_at'].isoformat(),
                updated_at=tenant_record['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tenant failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant"
        )

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    current_user: UserInDB = Depends(require_permission("tenants.update"))
):
    """
    Update tenant information.
    
    Requires permission: tenants.update
    """
    try:
        async with get_database() as db:
            # Check if tenant exists
            existing_tenant = await db.fetchrow(
                "SELECT id FROM tenants WHERE id = $1",
                uuid.UUID(tenant_id)
            )
            
            if not existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            # Check domain uniqueness if updating domain
            if tenant_data.domain:
                domain_check = await db.fetchrow(
                    "SELECT id FROM tenants WHERE domain = $1 AND id != $2",
                    tenant_data.domain,
                    uuid.UUID(tenant_id)
                )
                
                if domain_check:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Domain already registered"
                    )
            
            # Build update query
            update_fields = []
            params = []
            param_count = 0
            
            if tenant_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(tenant_data.name)
            
            if tenant_data.domain is not None:
                param_count += 1
                update_fields.append(f"domain = ${param_count}")
                params.append(tenant_data.domain)
            
            if tenant_data.industry is not None:
                param_count += 1
                update_fields.append(f"industry = ${param_count}")
                params.append(tenant_data.industry)
            
            if tenant_data.country is not None:
                param_count += 1
                update_fields.append(f"country = ${param_count}")
                params.append(tenant_data.country)
            
            if tenant_data.timezone is not None:
                param_count += 1
                update_fields.append(f"timezone = ${param_count}")
                params.append(tenant_data.timezone)
            
            if tenant_data.is_active is not None:
                param_count += 1
                update_fields.append(f"is_active = ${param_count}")
                params.append(tenant_data.is_active)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            # Add updated_at
            param_count += 1
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            
            # Add WHERE condition
            param_count += 1
            params.append(uuid.UUID(tenant_id))
            
            update_query = f"""
                UPDATE tenants 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING *
            """
            
            updated_tenant = await db.fetchrow(update_query, *params)
            
            # Get user count
            user_count_result = await db.fetchrow(
                "SELECT COUNT(*) as count FROM users WHERE tenant_id = $1 AND is_active = true",
                uuid.UUID(tenant_id)
            )
            user_count = user_count_result['count']
            
            logger.info(f"Tenant updated: {updated_tenant['name']} by {current_user.email}")
            
            return TenantResponse(
                id=str(updated_tenant['id']),
                name=updated_tenant['name'],
                domain=updated_tenant['domain'],
                industry=updated_tenant['industry'],
                country=updated_tenant['country'],
                timezone=updated_tenant['timezone'],
                settings=updated_tenant['settings'] or {},
                is_active=updated_tenant['is_active'],
                user_count=user_count,
                created_at=updated_tenant['created_at'].isoformat(),
                updated_at=updated_tenant['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update tenant failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant"
        )

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: UserInDB = Depends(require_permission("tenants.delete"))
):
    """
    Delete tenant (soft delete by deactivating).

    Requires permission: tenants.delete
    """
    try:
        async with get_database() as db:
            # Check if tenant exists
            existing_tenant = await db.fetchrow(
                "SELECT id, name FROM tenants WHERE id = $1",
                uuid.UUID(tenant_id)
            )

            if not existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )

            # Prevent deletion of current user's tenant
            if tenant_id == current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete your own tenant"
                )

            # Check if tenant has active users
            user_count_result = await db.fetchrow(
                "SELECT COUNT(*) as count FROM users WHERE tenant_id = $1 AND is_active = true",
                uuid.UUID(tenant_id)
            )

            if user_count_result['count'] > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete tenant with active users"
                )

            # Soft delete by deactivating
            await db.execute(
                "UPDATE tenants SET is_active = false, updated_at = $1 WHERE id = $2",
                datetime.utcnow(),
                uuid.UUID(tenant_id)
            )

            logger.info(f"Tenant deleted: {existing_tenant['name']} by {current_user.email}")

            return {"message": "Tenant deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete tenant failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant"
        )

@router.put("/{tenant_id}/settings", response_model=TenantResponse)
async def update_tenant_settings(
    tenant_id: str,
    settings_data: TenantSettingsUpdate,
    current_user: UserInDB = Depends(require_permission("tenants.manage_settings"))
):
    """
    Update tenant settings.

    Requires permission: tenants.manage_settings
    """
    try:
        async with get_database() as db:
            # Check if tenant exists
            existing_tenant = await db.fetchrow(
                "SELECT id, settings FROM tenants WHERE id = $1",
                uuid.UUID(tenant_id)
            )

            if not existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )

            # Merge settings (preserve existing settings not being updated)
            current_settings = existing_tenant['settings'] or {}
            updated_settings = {**current_settings, **settings_data.settings}

            # Update settings
            updated_tenant = await db.fetchrow(
                """
                UPDATE tenants
                SET settings = $1, updated_at = $2
                WHERE id = $3
                RETURNING *
                """,
                updated_settings,
                datetime.utcnow(),
                uuid.UUID(tenant_id)
            )

            # Get user count
            user_count_result = await db.fetchrow(
                "SELECT COUNT(*) as count FROM users WHERE tenant_id = $1 AND is_active = true",
                uuid.UUID(tenant_id)
            )
            user_count = user_count_result['count']

            logger.info(f"Tenant settings updated: {updated_tenant['name']} by {current_user.email}")

            return TenantResponse(
                id=str(updated_tenant['id']),
                name=updated_tenant['name'],
                domain=updated_tenant['domain'],
                industry=updated_tenant['industry'],
                country=updated_tenant['country'],
                timezone=updated_tenant['timezone'],
                settings=updated_tenant['settings'] or {},
                is_active=updated_tenant['is_active'],
                user_count=user_count,
                created_at=updated_tenant['created_at'].isoformat(),
                updated_at=updated_tenant['updated_at'].isoformat()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update tenant settings failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant settings"
        )

@router.get("/{tenant_id}/users", response_model=List[Dict[str, Any]])
async def get_tenant_users(
    tenant_id: str,
    current_user: UserInDB = Depends(require_permission("tenants.read"))
):
    """
    Get users belonging to a tenant.

    Requires permission: tenants.read
    """
    try:
        async with get_database() as db:
            # Check if tenant exists
            existing_tenant = await db.fetchrow(
                "SELECT id FROM tenants WHERE id = $1",
                uuid.UUID(tenant_id)
            )

            if not existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )

            # Get tenant users
            users_query = """
                SELECT id, email, full_name, role, department, is_active, last_login, created_at
                FROM users
                WHERE tenant_id = $1
                ORDER BY created_at DESC
            """

            users_records = await db.fetch(users_query, uuid.UUID(tenant_id))

            users = []
            for record in users_records:
                user_data = {
                    "id": str(record['id']),
                    "email": record['email'],
                    "full_name": record['full_name'],
                    "role": record['role'],
                    "department": record['department'],
                    "is_active": record['is_active'],
                    "last_login": record['last_login'].isoformat() if record['last_login'] else None,
                    "created_at": record['created_at'].isoformat()
                }
                users.append(user_data)

            return users

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tenant users failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant users"
        )
