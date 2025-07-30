"""
Training Portal Authentication & Authorization
Enhanced authentication and authorization specifically for training portal endpoints.
"""

from typing import Dict, List, Any, Optional
from fastapi import Depends, HTTPException, status
from functools import wraps
import structlog

from core_infra.api.auth import get_current_user, UserInDB
from core_infra.database.models import User, TrainingModule, TrainingEnrollment, db
from core_infra.exceptions import AuthenticationException, AuthorizationException

logger = structlog.get_logger(__name__)


class TrainingPortalAuth:
    """Enhanced authentication and authorization for training portal."""
    
    def __init__(self):
        self.permission_hierarchy = {
            'admin': [
                'training.modules.read', 'training.modules.create', 'training.modules.update', 'training.modules.delete',
                'training.enrollments.read', 'training.enrollments.create', 'training.enrollments.update', 'training.enrollments.delete',
                'training.assessments.read', 'training.assessments.take', 'training.assessments.grade',
                'training.certificates.read', 'training.certificates.generate', 'training.certificates.revoke',
                'training.discussions.read', 'training.discussions.create', 'training.discussions.moderate',
                'training.analytics.read', 'training.analytics.admin',
                'training.reports.read', 'training.reports.generate'
            ],
            'training_manager': [
                'training.modules.read', 'training.modules.create', 'training.modules.update',
                'training.enrollments.read', 'training.enrollments.create', 'training.enrollments.update',
                'training.assessments.read', 'training.assessments.grade',
                'training.certificates.read', 'training.certificates.generate',
                'training.discussions.read', 'training.discussions.create', 'training.discussions.moderate',
                'training.analytics.read',
                'training.reports.read', 'training.reports.generate'
            ],
            'compliance_officer': [
                'training.modules.read',
                'training.enrollments.read', 'training.enrollments.create',
                'training.assessments.read', 'training.assessments.take',
                'training.certificates.read',
                'training.discussions.read', 'training.discussions.create',
                'training.analytics.read',
                'training.reports.read'
            ],
            'user': [
                'training.modules.read',
                'training.enrollments.read', 'training.enrollments.create',
                'training.assessments.read', 'training.assessments.take',
                'training.certificates.read',
                'training.discussions.read', 'training.discussions.create'
            ]
        }
    
    def get_user_permissions(self, user: UserInDB) -> List[str]:
        """Get all permissions for a user based on their role."""
        try:
            user_role = user.role.lower()
            
            # Get base permissions for role
            permissions = set()
            
            # Add role-based permissions
            if user_role in self.permission_hierarchy:
                permissions.update(self.permission_hierarchy[user_role])
            else:
                # Default to basic user permissions
                permissions.update(self.permission_hierarchy['user'])
            
            # Add admin permissions if user is admin
            if 'admin' in user_role:
                permissions.update(self.permission_hierarchy['admin'])
            
            return list(permissions)
            
        except Exception as e:
            logger.error("Failed to get user permissions", user_id=user.id, error=str(e))
            return self.permission_hierarchy['user']  # Fallback to basic permissions
    
    def has_permission(self, user: UserInDB, permission: str) -> bool:
        """Check if user has a specific permission."""
        try:
            user_permissions = self.get_user_permissions(user)
            return permission in user_permissions
            
        except Exception as e:
            logger.error("Permission check failed", user_id=user.id, permission=permission, error=str(e))
            return False
    
    def check_module_access(self, user: UserInDB, module_id: str) -> bool:
        """Check if user has access to a specific training module."""
        try:
            # Get module
            module = TrainingModule.query.filter(
                TrainingModule.id == module_id,
                TrainingModule.tenant_id == user.tenant_id,
                TrainingModule.is_active == True
            ).first()
            
            if not module:
                return False
            
            # Check if user is enrolled or has admin access
            if self.has_permission(user, 'training.modules.update'):
                return True
            
            # Check enrollment
            enrollment = TrainingEnrollment.query.filter(
                TrainingEnrollment.user_id == user.id,
                TrainingEnrollment.module_id == module_id
            ).first()
            
            return enrollment is not None
            
        except Exception as e:
            logger.error("Module access check failed", user_id=user.id, module_id=module_id, error=str(e))
            return False
    
    def check_enrollment_ownership(self, user: UserInDB, enrollment_id: str) -> bool:
        """Check if user owns a specific enrollment."""
        try:
            enrollment = TrainingEnrollment.query.filter(
                TrainingEnrollment.id == enrollment_id,
                TrainingEnrollment.user_id == user.id
            ).first()
            
            return enrollment is not None
            
        except Exception as e:
            logger.error("Enrollment ownership check failed", user_id=user.id, enrollment_id=enrollment_id, error=str(e))
            return False
    
    def check_tenant_isolation(self, user: UserInDB, resource_tenant_id: str) -> bool:
        """Ensure proper tenant isolation for resources."""
        return str(user.tenant_id) == str(resource_tenant_id)


# Global auth instance
training_auth = TrainingPortalAuth()


def require_training_permission(permission: str):
    """Decorator to require specific training portal permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from dependencies
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserInDB):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permission
            if not training_auth.has_permission(current_user, permission):
                logger.warning("Permission denied", 
                             user_id=current_user.id, 
                             permission=permission,
                             user_role=current_user.role)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_module_access(module_id_param: str = "module_id"):
    """Decorator to require access to a specific training module."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user and module ID
            current_user = None
            module_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, UserInDB):
                    current_user = value
                elif key == module_id_param:
                    module_id = value
            
            if not current_user or not module_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters"
                )
            
            # Check module access
            if not training_auth.check_module_access(current_user, module_id):
                logger.warning("Module access denied", 
                             user_id=current_user.id, 
                             module_id=module_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to training module"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_enrollment_ownership(enrollment_id_param: str = "enrollment_id"):
    """Decorator to require ownership of a specific enrollment."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user and enrollment ID
            current_user = None
            enrollment_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, UserInDB):
                    current_user = value
                elif key == enrollment_id_param:
                    enrollment_id = value
            
            if not current_user or not enrollment_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters"
                )
            
            # Check enrollment ownership (or admin access)
            if not (training_auth.check_enrollment_ownership(current_user, enrollment_id) or 
                   training_auth.has_permission(current_user, 'training.enrollments.update')):
                logger.warning("Enrollment access denied", 
                             user_id=current_user.id, 
                             enrollment_id=enrollment_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to enrollment"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def get_training_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get current user with training portal context."""
    try:
        # Verify user is active
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Add training-specific context
        current_user.training_permissions = training_auth.get_user_permissions(current_user)
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get training user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def require_training_admin(current_user: UserInDB = Depends(get_training_user)) -> UserInDB:
    """Require training administrator permissions."""
    if not training_auth.has_permission(current_user, 'training.analytics.admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training administrator permissions required"
        )
    return current_user


async def require_training_manager(current_user: UserInDB = Depends(get_training_user)) -> UserInDB:
    """Require training manager permissions."""
    if not (training_auth.has_permission(current_user, 'training.modules.create') or
           training_auth.has_permission(current_user, 'training.analytics.admin')):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training manager permissions required"
        )
    return current_user


def log_training_access(action: str, resource_type: str, resource_id: str = None):
    """Decorator to log training portal access for audit purposes."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserInDB):
                    current_user = value
                    break
            
            # Log access attempt
            logger.info("Training portal access",
                       action=action,
                       resource_type=resource_type,
                       resource_id=resource_id or kwargs.get('module_id') or kwargs.get('enrollment_id'),
                       user_id=current_user.id if current_user else None,
                       tenant_id=current_user.tenant_id if current_user else None)
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful access
                logger.info("Training portal access successful",
                           action=action,
                           resource_type=resource_type,
                           user_id=current_user.id if current_user else None)
                
                return result
                
            except Exception as e:
                # Log failed access
                logger.warning("Training portal access failed",
                              action=action,
                              resource_type=resource_type,
                              user_id=current_user.id if current_user else None,
                              error=str(e))
                raise
                
        return wrapper
    return decorator
