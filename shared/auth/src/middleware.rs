//! Authentication and authorization middleware for Axum

use axum::{
    extract::{Request, State},
    http::{header::AUTHORIZATION, HeaderMap, StatusCode},
    middleware::Next,
    response::Response,
};
use std::sync::Arc;
use uuid::Uuid;

use crate::{JwtManager, Permission, RbacManager};
use regulateai_errors::RegulateAIError;

/// Authentication context extracted from request
#[derive(Debug, Clone)]
pub struct AuthContext {
    pub user_id: Uuid,
    pub session_id: Uuid,
    pub email: String,
    pub roles: Vec<String>,
    pub permissions: Vec<String>,
    pub organization_id: Option<Uuid>,
}

impl AuthContext {
    /// Check if the user has a specific permission
    pub fn has_permission(&self, permission: &str) -> bool {
        self.permissions.contains(&permission.to_string()) || 
        self.permissions.contains(&"*".to_string())
    }

    /// Check if the user has a specific role
    pub fn has_role(&self, role: &str) -> bool {
        self.roles.contains(&role.to_string())
    }

    /// Check if the user has any of the specified roles
    pub fn has_any_role(&self, roles: &[&str]) -> bool {
        roles.iter().any(|role| self.has_role(role))
    }

    /// Check if the user belongs to a specific organization
    pub fn belongs_to_organization(&self, org_id: &Uuid) -> bool {
        self.organization_id.as_ref() == Some(org_id)
    }
}

/// Shared authentication state
#[derive(Clone)]
pub struct AuthState {
    pub jwt_manager: Arc<JwtManager>,
    pub rbac_manager: Arc<RbacManager>,
}

impl AuthState {
    pub fn new(jwt_manager: JwtManager, rbac_manager: RbacManager) -> Self {
        Self {
            jwt_manager: Arc::new(jwt_manager),
            rbac_manager: Arc::new(rbac_manager),
        }
    }
}

/// Authentication middleware that validates JWT tokens
pub async fn auth_middleware(
    State(auth_state): State<AuthState>,
    mut request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // Extract token from Authorization header
    let token = extract_token_from_headers(request.headers())
        .map_err(|_| StatusCode::UNAUTHORIZED)?;

    // Validate token and extract claims
    let claims = auth_state.jwt_manager.validate_token(&token)
        .map_err(|_| StatusCode::UNAUTHORIZED)?;

    // Create auth context
    let auth_context = AuthContext {
        user_id: Uuid::parse_str(&claims.sub).map_err(|_| StatusCode::UNAUTHORIZED)?,
        session_id: Uuid::parse_str(&claims.session_id).map_err(|_| StatusCode::UNAUTHORIZED)?,
        email: claims.email,
        roles: claims.roles,
        permissions: claims.permissions,
        organization_id: claims.org_id.and_then(|id| Uuid::parse_str(&id).ok()),
    };

    // Add auth context to request extensions
    request.extensions_mut().insert(auth_context);

    // Continue to next middleware/handler
    Ok(next.run(request).await)
}

/// Authorization middleware that checks for required permissions
pub fn require_permission(required_permission: &'static str) -> impl Fn(Request, Next) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Response, StatusCode>> + Send>> + Clone {
    move |request: Request, next: Next| {
        let permission = required_permission;
        Box::pin(async move {
            // Get auth context from request extensions
            let auth_context = request.extensions().get::<AuthContext>()
                .ok_or(StatusCode::UNAUTHORIZED)?;

            // Check permission
            if !auth_context.has_permission(permission) {
                return Err(StatusCode::FORBIDDEN);
            }

            Ok(next.run(request).await)
        })
    }
}

/// Authorization middleware that checks for required roles
pub fn require_role(required_role: &'static str) -> impl Fn(Request, Next) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Response, StatusCode>> + Send>> + Clone {
    move |request: Request, next: Next| {
        let role = required_role;
        Box::pin(async move {
            // Get auth context from request extensions
            let auth_context = request.extensions().get::<AuthContext>()
                .ok_or(StatusCode::UNAUTHORIZED)?;

            // Check role
            if !auth_context.has_role(role) {
                return Err(StatusCode::FORBIDDEN);
            }

            Ok(next.run(request).await)
        })
    }
}

/// Authorization middleware that checks for any of the required roles
pub fn require_any_role(required_roles: &'static [&'static str]) -> impl Fn(Request, Next) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Response, StatusCode>> + Send>> + Clone {
    move |request: Request, next: Next| {
        let roles = required_roles;
        Box::pin(async move {
            // Get auth context from request extensions
            let auth_context = request.extensions().get::<AuthContext>()
                .ok_or(StatusCode::UNAUTHORIZED)?;

            // Check roles
            if !auth_context.has_any_role(roles) {
                return Err(StatusCode::FORBIDDEN);
            }

            Ok(next.run(request).await)
        })
    }
}

/// Organization-based authorization middleware
pub fn require_organization_access() -> impl Fn(Request, Next) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Response, StatusCode>> + Send>> + Clone {
    move |request: Request, next: Next| {
        Box::pin(async move {
            // Get auth context from request extensions
            let auth_context = request.extensions().get::<AuthContext>()
                .ok_or(StatusCode::UNAUTHORIZED)?;

            // Extract organization ID from path parameters (this would need to be implemented based on your routing)
            // For now, we'll assume the organization ID is available in the request
            // In a real implementation, you'd extract this from the path or query parameters
            
            // This is a placeholder - you'd implement organization extraction based on your needs
            let _required_org_id = extract_organization_from_request(&request);

            // For now, just check that the user has an organization
            if auth_context.organization_id.is_none() {
                return Err(StatusCode::FORBIDDEN);
            }

            Ok(next.run(request).await)
        })
    }
}

/// Optional authentication middleware that doesn't fail if no token is provided
pub async fn optional_auth_middleware(
    State(auth_state): State<AuthState>,
    mut request: Request,
    next: Next,
) -> Response {
    // Try to extract token from Authorization header
    if let Ok(token) = extract_token_from_headers(request.headers()) {
        // Try to validate token and extract claims
        if let Ok(claims) = auth_state.jwt_manager.validate_token(&token) {
            // Create auth context if token is valid
            if let (Ok(user_id), Ok(session_id)) = (
                Uuid::parse_str(&claims.sub),
                Uuid::parse_str(&claims.session_id)
            ) {
                let auth_context = AuthContext {
                    user_id,
                    session_id,
                    email: claims.email,
                    roles: claims.roles,
                    permissions: claims.permissions,
                    organization_id: claims.org_id.and_then(|id| Uuid::parse_str(&id).ok()),
                };

                // Add auth context to request extensions
                request.extensions_mut().insert(auth_context);
            }
        }
    }

    // Continue to next middleware/handler regardless of authentication status
    next.run(request).await
}

/// Extract JWT token from Authorization header
fn extract_token_from_headers(headers: &HeaderMap) -> Result<String, RegulateAIError> {
    let auth_header = headers.get(AUTHORIZATION)
        .ok_or_else(|| RegulateAIError::Authentication {
            message: "Missing Authorization header".to_string(),
            code: "MISSING_AUTH_HEADER".to_string(),
        })?;

    let auth_str = auth_header.to_str()
        .map_err(|_| RegulateAIError::Authentication {
            message: "Invalid Authorization header format".to_string(),
            code: "INVALID_AUTH_HEADER".to_string(),
        })?;

    if !auth_str.starts_with("Bearer ") {
        return Err(RegulateAIError::Authentication {
            message: "Authorization header must start with 'Bearer '".to_string(),
            code: "INVALID_AUTH_SCHEME".to_string(),
        });
    }

    Ok(auth_str[7..].to_string()) // Remove "Bearer " prefix
}

/// Extract organization ID from request (placeholder implementation)
fn extract_organization_from_request(_request: &Request) -> Option<Uuid> {
    // This would be implemented based on your routing structure
    // For example, extracting from path parameters like /api/v1/organizations/{org_id}/...
    // or from query parameters, headers, etc.
    None
}

/// Utility function to get auth context from request extensions
pub fn get_auth_context(request: &Request) -> Option<&AuthContext> {
    request.extensions().get::<AuthContext>()
}

/// Utility function to require auth context (returns error if not authenticated)
pub fn require_auth_context(request: &Request) -> Result<&AuthContext, RegulateAIError> {
    get_auth_context(request).ok_or_else(|| RegulateAIError::Authentication {
        message: "Authentication required".to_string(),
        code: "AUTHENTICATION_REQUIRED".to_string(),
    })
}

/// Rate limiting middleware (placeholder implementation)
pub async fn rate_limit_middleware(
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // This would implement rate limiting logic
    // For now, just pass through
    Ok(next.run(request).await)
}

/// CORS middleware (placeholder implementation)
pub async fn cors_middleware(
    request: Request,
    next: Next,
) -> Response {
    let response = next.run(request).await;
    
    // Add CORS headers
    // This would be implemented based on your CORS configuration
    response
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::{HeaderMap, HeaderValue};

    #[test]
    fn test_extract_token_from_headers() {
        let mut headers = HeaderMap::new();
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_static("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...")
        );

        let token = extract_token_from_headers(&headers).unwrap();
        assert_eq!(token, "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...");
    }

    #[test]
    fn test_extract_token_missing_header() {
        let headers = HeaderMap::new();
        let result = extract_token_from_headers(&headers);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_token_invalid_scheme() {
        let mut headers = HeaderMap::new();
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_static("Basic dXNlcjpwYXNz")
        );

        let result = extract_token_from_headers(&headers);
        assert!(result.is_err());
    }

    #[test]
    fn test_auth_context_permissions() {
        let auth_context = AuthContext {
            user_id: Uuid::new_v4(),
            session_id: Uuid::new_v4(),
            email: "test@example.com".to_string(),
            roles: vec!["user".to_string()],
            permissions: vec!["read".to_string(), "write".to_string()],
            organization_id: None,
        };

        assert!(auth_context.has_permission("read"));
        assert!(auth_context.has_permission("write"));
        assert!(!auth_context.has_permission("admin"));
    }

    #[test]
    fn test_auth_context_roles() {
        let auth_context = AuthContext {
            user_id: Uuid::new_v4(),
            session_id: Uuid::new_v4(),
            email: "test@example.com".to_string(),
            roles: vec!["user".to_string(), "analyst".to_string()],
            permissions: vec![],
            organization_id: None,
        };

        assert!(auth_context.has_role("user"));
        assert!(auth_context.has_role("analyst"));
        assert!(!auth_context.has_role("admin"));

        assert!(auth_context.has_any_role(&["user", "admin"]));
        assert!(!auth_context.has_any_role(&["admin", "super_admin"]));
    }
}
