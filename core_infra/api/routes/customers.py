"""
Customer Management API Routes
Provides endpoints for customer CRUD operations, KYC management, and risk assessment.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import structlog

from core_infra.database.connection import get_database
from core_infra.api.auth import get_current_user, require_permission, verify_tenant_access, UserInDB
from core_infra.exceptions import ResourceNotFoundException, DuplicateResourceException, exception_to_http_exception

logger = structlog.get_logger(__name__)
router = APIRouter()

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class CustomerResponse(BaseModel):
    """Customer response model."""
    id: str
    customer_type: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    date_of_birth: Optional[str]
    country: str
    risk_score: int
    risk_category: str
    kyc_status: str
    pep_status: bool
    sanctions_status: bool
    last_screening_date: Optional[str]
    created_at: str
    updated_at: str

class CustomerListResponse(BaseModel):
    """Customer list response with pagination."""
    customers: List[CustomerResponse]
    total: int
    page: int
    size: int
    total_pages: int

class CustomerCreateRequest(BaseModel):
    """Customer creation request model."""
    customer_type: str = Field(..., description="Customer type (individual, corporate)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")

# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@router.get("/", response_model=CustomerListResponse)
async def get_customers(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    risk_category: Optional[str] = Query(None, description="Filter by risk category"),
    kyc_status: Optional[str] = Query(None, description="Filter by KYC status"),
    country: Optional[str] = Query(None, description="Filter by country"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: UserInDB = Depends(require_permission("customers.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get list of customers with filtering and pagination.
    
    Requires permission: customers.read
    """
    try:
        async with get_database() as db:
            # Build dynamic query
            conditions = ["tenant_id = $1"]
            params = [uuid.UUID(tenant_id)]
            param_count = 1
            
            if risk_category:
                param_count += 1
                conditions.append(f"risk_category = ${param_count}")
                params.append(risk_category)
                
            if kyc_status:
                param_count += 1
                conditions.append(f"kyc_status = ${param_count}")
                params.append(kyc_status)
                
            if country:
                param_count += 1
                conditions.append(f"country = ${param_count}")
                params.append(country)
                
            if search:
                param_count += 1
                conditions.append(f"(first_name ILIKE ${param_count} OR last_name ILIKE ${param_count} OR email ILIKE ${param_count})")
                params.append(f"%{search}%")
            
            where_clause = " AND ".join(conditions)
            offset = (page - 1) * size
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM customers WHERE {where_clause}"
            total = await db.fetchval(count_query, *params)
            
            # Get customers
            query = f"""
                SELECT id, customer_type, first_name, last_name, email, phone,
                       date_of_birth, country, risk_score, risk_category, kyc_status,
                       pep_status, sanctions_status, last_screening_date, created_at, updated_at
                FROM customers
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            
            params.extend([size, offset])
            customers = await db.fetch(query, *params)
            
            customer_list = [
                CustomerResponse(
                    id=str(customer['id']),
                    customer_type=customer['customer_type'],
                    first_name=customer['first_name'],
                    last_name=customer['last_name'],
                    email=customer['email'],
                    phone=customer['phone'],
                    date_of_birth=customer['date_of_birth'].isoformat() if customer['date_of_birth'] else None,
                    country=customer['country'],
                    risk_score=customer['risk_score'] or 0,
                    risk_category=customer['risk_category'] or 'unknown',
                    kyc_status=customer['kyc_status'] or 'pending',
                    pep_status=customer['pep_status'] or False,
                    sanctions_status=customer['sanctions_status'] or False,
                    last_screening_date=customer['last_screening_date'].isoformat() if customer['last_screening_date'] else None,
                    created_at=customer['created_at'].isoformat(),
                    updated_at=customer['updated_at'].isoformat()
                )
                for customer in customers
            ]
            
            total_pages = (total + size - 1) // size
            
            return CustomerListResponse(
                customers=customer_list,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )
            
    except Exception as e:
        logger.error(f"Get customers failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get customers"
        )

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    current_user: UserInDB = Depends(require_permission("customers.read")),
    tenant_id: str = Depends(verify_tenant_access)
):
    """
    Get customer by ID.
    
    Requires permission: customers.read
    """
    try:
        async with get_database() as db:
            customer = await db.fetchrow(
                """
                SELECT id, customer_type, first_name, last_name, email, phone,
                       date_of_birth, country, risk_score, risk_category, kyc_status,
                       pep_status, sanctions_status, last_screening_date, created_at, updated_at
                FROM customers
                WHERE id = $1 AND tenant_id = $2
                """,
                uuid.UUID(customer_id),
                uuid.UUID(tenant_id)
            )
            
            if not customer:
                raise ResourceNotFoundException("customer", customer_id)
            
            return CustomerResponse(
                id=str(customer['id']),
                customer_type=customer['customer_type'],
                first_name=customer['first_name'],
                last_name=customer['last_name'],
                email=customer['email'],
                phone=customer['phone'],
                date_of_birth=customer['date_of_birth'].isoformat() if customer['date_of_birth'] else None,
                country=customer['country'],
                risk_score=customer['risk_score'] or 0,
                risk_category=customer['risk_category'] or 'unknown',
                kyc_status=customer['kyc_status'] or 'pending',
                pep_status=customer['pep_status'] or False,
                sanctions_status=customer['sanctions_status'] or False,
                last_screening_date=customer['last_screening_date'].isoformat() if customer['last_screening_date'] else None,
                created_at=customer['created_at'].isoformat(),
                updated_at=customer['updated_at'].isoformat()
            )
            
    except ResourceNotFoundException as e:
        raise exception_to_http_exception(e)
    except Exception as e:
        logger.error(f"Get customer failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get customer"
        )
