"""
Authentication and authorization module for RegulensAI
"""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from typing import Optional, Dict, Any

security = HTTPBearer(auto_error=False)

async def get_current_user(token: Optional[str] = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user - stub implementation"""
    # For production, implement proper JWT validation
    return {
        "id": "user_123",
        "email": "admin@regulens.ai",
        "role": "admin",
        "tenant_id": "tenant_123"
    }

async def verify_tenant_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> bool:
    """Verify tenant access - stub implementation"""
    # For production, implement proper tenant validation
    return True 