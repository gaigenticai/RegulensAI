"""
Regulens AI - User Management Routes
Enterprise-grade user management with RBAC and comprehensive audit trails.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, EmailStr
import structlog

from core_infra.api.auth import (
    get_current_user,
    verify_tenant_access,
    require_permission,
    get_password_hash,
    UserInDB
)
from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Initialize logging and settings
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter(tags=["User Management"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserCreate(BaseModel):
    """User creation request model."""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    role: str = Field(..., description="User role")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    password: str = Field(..., min_length=8, description="Initial password")
    permissions: List[str] = Field(default=[], description="List of permission names")
    is_active: bool = Field(default=True, description="Account active status")

class UserUpdate(BaseModel):
    """User update request model."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Full name")
    role: Optional[str] = Field(None, description="User role")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    is_active: Optional[bool] = Field(None, description="Account active status")

class UserPermissionUpdate(BaseModel):
    """User permission update request model."""
    permissions: List[str] = Field(..., description="List of permission names to assign")

class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    full_name: str
    role: str
    department: Optional[str]
    tenant_id: str
    permissions: List[str]
    is_active: bool
    last_login: Optional[str]
    created_at: str
    updated_at: str

class UserListResponse(BaseModel):
    """User list response model."""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int

# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    role: Optional[str] = Query(None, description="Filter by role"),
    department: Optional[str] = Query(None, description="Filter by department"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: UserInDB = Depends(require_permission("users.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get list of users with pagination and filtering.
    
    Requires permission: users.read
    """
    try:
        offset = (page - 1) * size
        
        # Build query conditions
        conditions = ["u.tenant_id = $1"]
        params = [uuid.UUID(tenant_id)]
        param_count = 1
        
        if role:
            param_count += 1
            conditions.append(f"u.role = ${param_count}")
            params.append(role)
        
        if department:
            param_count += 1
            conditions.append(f"u.department = ${param_count}")
            params.append(department)
        
        if is_active is not None:
            param_count += 1
            conditions.append(f"u.is_active = ${param_count}")
            params.append(is_active)
        
        if search:
            param_count += 1
            conditions.append(f"(u.full_name ILIKE ${param_count} OR u.email ILIKE ${param_count})")
            params.append(f"%{search}%")
        
        where_clause = " AND ".join(conditions)
        
        async with get_database() as db:
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM users u
                WHERE {where_clause}
            """
            total_result = await db.fetchrow(count_query, *params)
            total = total_result['total']
            
            # Get users with permissions
            users_query = f"""
                SELECT u.*, array_agg(DISTINCT p.permission_name) as permissions
                FROM users u
                LEFT JOIN user_permissions up ON u.id = up.user_id
                LEFT JOIN permissions p ON up.permission_id = p.id
                WHERE {where_clause}
                GROUP BY u.id
                ORDER BY u.created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([size, offset])
            
            users_records = await db.fetch(users_query, *params)
            
            # Format response
            users = []
            for record in users_records:
                user_data = UserResponse(
                    id=str(record['id']),
                    email=record['email'],
                    full_name=record['full_name'],
                    role=record['role'],
                    department=record['department'],
                    tenant_id=str(record['tenant_id']),
                    permissions=record['permissions'] or [],
                    is_active=record['is_active'],
                    last_login=record['last_login'].isoformat() if record['last_login'] else None,
                    created_at=record['created_at'].isoformat(),
                    updated_at=record['updated_at'].isoformat()
                )
                users.append(user_data)
            
            pages = (total + size - 1) // size
            
            return UserListResponse(
                users=users,
                total=total,
                page=page,
                size=size,
                pages=pages
            )
            
    except Exception as e:
        logger.error(f"Get users failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: UserInDB = Depends(require_permission("users.create")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Create a new user.
    
    Requires permission: users.create
    """
    try:
        async with get_database() as db:
            # Check if email already exists
            existing_user = await db.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                user_data.email
            )
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Validate permissions exist
            if user_data.permissions:
                permission_query = """
                    SELECT permission_name FROM permissions 
                    WHERE permission_name = ANY($1) AND is_active = true
                """
                valid_permissions = await db.fetch(permission_query, user_data.permissions)
                valid_permission_names = [p['permission_name'] for p in valid_permissions]
                
                invalid_permissions = set(user_data.permissions) - set(valid_permission_names)
                if invalid_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid permissions: {', '.join(invalid_permissions)}"
                    )
            
            # Create user
            user_id = uuid.uuid4()
            user_insert_query = """
                INSERT INTO users (
                    id, tenant_id, email, full_name, role, department, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
            """
            
            user_record = await db.fetchrow(
                user_insert_query,
                user_id,
                uuid.UUID(tenant_id),
                user_data.email,
                user_data.full_name,
                user_data.role,
                user_data.department,
                user_data.is_active
            )
            
            # Create user credentials
            password_hash = get_password_hash(user_data.password)
            credentials_query = """
                INSERT INTO user_credentials (user_id, password_hash)
                VALUES ($1, $2)
            """
            await db.execute(credentials_query, user_id, password_hash)
            
            # Assign permissions
            if user_data.permissions:
                # Get permission IDs
                permission_ids_query = """
                    SELECT id, permission_name FROM permissions 
                    WHERE permission_name = ANY($1)
                """
                permission_records = await db.fetch(permission_ids_query, user_data.permissions)
                
                # Insert user permissions
                for perm_record in permission_records:
                    await db.execute(
                        """
                        INSERT INTO user_permissions (user_id, permission_id, granted_by)
                        VALUES ($1, $2, $3)
                        """,
                        user_id,
                        perm_record['id'],
                        uuid.UUID(current_user.id)
                    )
            
            logger.info(f"User created: {user_data.email} by {current_user.email}")
            
            # Return created user
            return UserResponse(
                id=str(user_record['id']),
                email=user_record['email'],
                full_name=user_record['full_name'],
                role=user_record['role'],
                department=user_record['department'],
                tenant_id=str(user_record['tenant_id']),
                permissions=user_data.permissions,
                is_active=user_record['is_active'],
                last_login=None,
                created_at=user_record['created_at'].isoformat(),
                updated_at=user_record['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserInDB = Depends(require_permission("users.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get user by ID.
    
    Requires permission: users.read
    """
    try:
        async with get_database() as db:
            query = """
                SELECT u.*, array_agg(DISTINCT p.permission_name) as permissions
                FROM users u
                LEFT JOIN user_permissions up ON u.id = up.user_id
                LEFT JOIN permissions p ON up.permission_id = p.id
                WHERE u.id = $1 AND u.tenant_id = $2
                GROUP BY u.id
            """
            
            user_record = await db.fetchrow(query, uuid.UUID(user_id), uuid.UUID(tenant_id))
            
            if not user_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse(
                id=str(user_record['id']),
                email=user_record['email'],
                full_name=user_record['full_name'],
                role=user_record['role'],
                department=user_record['department'],
                tenant_id=str(user_record['tenant_id']),
                permissions=user_record['permissions'] or [],
                is_active=user_record['is_active'],
                last_login=user_record['last_login'].isoformat() if user_record['last_login'] else None,
                created_at=user_record['created_at'].isoformat(),
                updated_at=user_record['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: UserInDB = Depends(require_permission("users.update")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Update user information.
    
    Requires permission: users.update
    """
    try:
        async with get_database() as db:
            # Check if user exists
            existing_user = await db.fetchrow(
                "SELECT id FROM users WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(user_id),
                uuid.UUID(tenant_id)
            )
            
            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Build update query
            update_fields = []
            params = []
            param_count = 0
            
            if user_data.full_name is not None:
                param_count += 1
                update_fields.append(f"full_name = ${param_count}")
                params.append(user_data.full_name)
            
            if user_data.role is not None:
                param_count += 1
                update_fields.append(f"role = ${param_count}")
                params.append(user_data.role)
            
            if user_data.department is not None:
                param_count += 1
                update_fields.append(f"department = ${param_count}")
                params.append(user_data.department)
            
            if user_data.is_active is not None:
                param_count += 1
                update_fields.append(f"is_active = ${param_count}")
                params.append(user_data.is_active)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            # Add updated_at
            param_count += 1
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            
            # Add WHERE conditions
            param_count += 1
            params.append(uuid.UUID(user_id))
            param_count += 1
            params.append(uuid.UUID(tenant_id))
            
            update_query = f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count - 1} AND tenant_id = ${param_count}
                RETURNING *
            """
            
            updated_user = await db.fetchrow(update_query, *params)
            
            # Get user permissions
            permissions_query = """
                SELECT array_agg(p.permission_name) as permissions
                FROM user_permissions up
                JOIN permissions p ON up.permission_id = p.id
                WHERE up.user_id = $1
            """
            permissions_result = await db.fetchrow(permissions_query, uuid.UUID(user_id))
            permissions = permissions_result['permissions'] or []
            
            logger.info(f"User updated: {updated_user['email']} by {current_user.email}")
            
            return UserResponse(
                id=str(updated_user['id']),
                email=updated_user['email'],
                full_name=updated_user['full_name'],
                role=updated_user['role'],
                department=updated_user['department'],
                tenant_id=str(updated_user['tenant_id']),
                permissions=permissions,
                is_active=updated_user['is_active'],
                last_login=updated_user['last_login'].isoformat() if updated_user['last_login'] else None,
                created_at=updated_user['created_at'].isoformat(),
                updated_at=updated_user['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(require_permission("users.delete")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Delete user (soft delete by deactivating).

    Requires permission: users.delete
    """
    try:
        async with get_database() as db:
            # Check if user exists
            existing_user = await db.fetchrow(
                "SELECT id, email FROM users WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(user_id),
                uuid.UUID(tenant_id)
            )

            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Prevent self-deletion
            if user_id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete your own account"
                )

            # Soft delete by deactivating
            await db.execute(
                "UPDATE users SET is_active = false, updated_at = $1 WHERE id = $2",
                datetime.utcnow(),
                uuid.UUID(user_id)
            )

            logger.info(f"User deleted: {existing_user['email']} by {current_user.email}")

            return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

@router.put("/{user_id}/permissions", response_model=UserResponse)
async def update_user_permissions(
    user_id: str,
    permission_data: UserPermissionUpdate,
    current_user: UserInDB = Depends(require_permission("users.manage_permissions")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Update user permissions.

    Requires permission: users.manage_permissions
    """
    try:
        async with get_database() as db:
            # Check if user exists
            existing_user = await db.fetchrow(
                "SELECT id, email FROM users WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(user_id),
                uuid.UUID(tenant_id)
            )

            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Validate permissions exist
            if permission_data.permissions:
                permission_query = """
                    SELECT id, permission_name FROM permissions
                    WHERE permission_name = ANY($1) AND is_active = true
                """
                valid_permissions = await db.fetch(permission_query, permission_data.permissions)
                valid_permission_names = [p['permission_name'] for p in valid_permissions]

                invalid_permissions = set(permission_data.permissions) - set(valid_permission_names)
                if invalid_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid permissions: {', '.join(invalid_permissions)}"
                    )

            # Remove existing permissions
            await db.execute(
                "DELETE FROM user_permissions WHERE user_id = $1",
                uuid.UUID(user_id)
            )

            # Add new permissions
            if permission_data.permissions:
                permission_map = {p['permission_name']: p['id'] for p in valid_permissions}

                for permission_name in permission_data.permissions:
                    await db.execute(
                        """
                        INSERT INTO user_permissions (user_id, permission_id, granted_by)
                        VALUES ($1, $2, $3)
                        """,
                        uuid.UUID(user_id),
                        permission_map[permission_name],
                        uuid.UUID(current_user.id)
                    )

            # Get updated user data
            user_query = """
                SELECT u.*, array_agg(DISTINCT p.permission_name) as permissions
                FROM users u
                LEFT JOIN user_permissions up ON u.id = up.user_id
                LEFT JOIN permissions p ON up.permission_id = p.id
                WHERE u.id = $1
                GROUP BY u.id
            """

            updated_user = await db.fetchrow(user_query, uuid.UUID(user_id))

            logger.info(f"Permissions updated for user: {existing_user['email']} by {current_user.email}")

            return UserResponse(
                id=str(updated_user['id']),
                email=updated_user['email'],
                full_name=updated_user['full_name'],
                role=updated_user['role'],
                department=updated_user['department'],
                tenant_id=str(updated_user['tenant_id']),
                permissions=updated_user['permissions'] or [],
                is_active=updated_user['is_active'],
                last_login=updated_user['last_login'].isoformat() if updated_user['last_login'] else None,
                created_at=updated_user['created_at'].isoformat(),
                updated_at=updated_user['updated_at'].isoformat()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user permissions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user permissions"
        )

@router.get("/permissions/available", response_model=List[Dict[str, Any]])
async def get_available_permissions(
    current_user: UserInDB = Depends(require_permission("users.read"))
):
    """
    Get list of available permissions.

    Requires permission: users.read
    """
    try:
        async with get_database() as db:
            query = """
                SELECT permission_name, description, category
                FROM permissions
                WHERE is_active = true
                ORDER BY category, permission_name
            """

            permissions = await db.fetch(query)

            return [
                {
                    "name": perm['permission_name'],
                    "description": perm['description'],
                    "category": perm['category']
                }
                for perm in permissions
            ]

    except Exception as e:
        logger.error(f"Get available permissions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permissions"
        )
