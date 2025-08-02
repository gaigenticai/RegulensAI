//! Comprehensive authentication framework tests
//! 
//! This test suite validates the authentication and authorization framework
//! as required by the development rules.

use chrono::Utc;
use regulateai_auth::{
    JwtManager, PasswordHasher, Permission, RbacManager, Role, Session, SessionManager,
    AuthContext, LoginRequest, MfaMethodType, AuthEventType,
};
use regulateai_config::{SecurityConfig, PasswordPolicyConfig, SessionConfig};
use uuid::Uuid;

/// Test JWT token generation and validation
#[test]
fn test_jwt_token_lifecycle() {
    let config = SecurityConfig::default();
    let jwt_manager = JwtManager::new(config).unwrap();
    
    let user_id = Uuid::new_v4();
    let session_id = Uuid::new_v4();
    let roles = vec!["user".to_string(), "analyst".to_string()];
    let permissions = vec!["read".to_string(), "write".to_string()];
    
    // Generate access token
    let access_token = jwt_manager.generate_access_token(
        user_id,
        "test@example.com",
        roles.clone(),
        permissions.clone(),
        session_id,
        None,
    ).unwrap();
    
    // Validate token
    let claims = jwt_manager.validate_token(&access_token).unwrap();
    assert_eq!(claims.sub, user_id.to_string());
    assert_eq!(claims.email, "test@example.com");
    assert_eq!(claims.roles, roles);
    assert_eq!(claims.permissions, permissions);
    
    // Test permission checks
    assert!(jwt_manager.has_permission(&access_token, "read").unwrap());
    assert!(jwt_manager.has_permission(&access_token, "write").unwrap());
    assert!(!jwt_manager.has_permission(&access_token, "admin").unwrap());
    
    // Test role checks
    assert!(jwt_manager.has_role(&access_token, "user").unwrap());
    assert!(jwt_manager.has_role(&access_token, "analyst").unwrap());
    assert!(!jwt_manager.has_role(&access_token, "admin").unwrap());
    
    // Generate refresh token
    let refresh_token = jwt_manager.generate_refresh_token(user_id, session_id).unwrap();
    let refresh_claims = jwt_manager.validate_token(&refresh_token).unwrap();
    assert_eq!(refresh_claims.token_type, regulateai_auth::TokenType::Refresh);
}

/// Test password hashing and validation
#[test]
fn test_password_security() {
    let policy = PasswordPolicyConfig {
        min_length: 8,
        max_length: 128,
        require_uppercase: true,
        require_lowercase: true,
        require_digits: true,
        require_special_chars: true,
        allowed_special_chars: "!@#$%^&*()_+-=[]{}|;:,.<>?".to_string(),
        max_login_attempts: 5,
        lockout_duration: 900,
        password_expiry_days: 90,
        password_history_count: 5,
    };
    
    let hasher = PasswordHasher::new(policy);
    
    // Test strong password
    let strong_password = "SecureP@ssw0rd123!";
    assert!(hasher.validate_password(strong_password).is_ok());
    
    let hash = hasher.hash_password(strong_password).unwrap();
    assert!(hasher.verify_password(strong_password, &hash).unwrap());
    assert!(!hasher.verify_password("WrongPassword", &hash).unwrap());
    
    // Test weak passwords
    assert!(hasher.validate_password("weak").is_err()); // Too short
    assert!(hasher.validate_password("nouppercase123!").is_err()); // No uppercase
    assert!(hasher.validate_password("NOLOWERCASE123!").is_err()); // No lowercase
    assert!(hasher.validate_password("NoDigitsHere!").is_err()); // No digits
    assert!(hasher.validate_password("NoSpecialChars123").is_err()); // No special chars
    
    // Test password strength calculation
    let weak_score = hasher.calculate_password_strength("password");
    let strong_score = hasher.calculate_password_strength(strong_password);
    assert!(strong_score > weak_score);
    assert!(strong_score >= 70); // Strong passwords should score high
    
    // Test secure password generation
    let generated_password = hasher.generate_secure_password(16);
    assert_eq!(generated_password.len(), 16);
    assert!(hasher.validate_password(&generated_password).is_ok());
}

/// Test RBAC system
#[test]
fn test_rbac_system() {
    let mut rbac = RbacManager::new();
    
    // Create default roles
    rbac.create_default_roles().unwrap();
    
    // Test role creation
    let mut custom_role = Role::new("custom_role", Some("Custom Role".to_string()));
    custom_role.add_permission(Permission::new("documents", "read"));
    custom_role.add_permission(Permission::new("documents", "write"));
    let custom_role_id = custom_role.id;
    rbac.add_role(custom_role).unwrap();
    
    // Test user role assignment
    let user_id = Uuid::new_v4();
    rbac.assign_role_to_user(user_id, custom_role_id).unwrap();
    
    // Test permission checks
    let read_permission = Permission::new("documents", "read");
    let write_permission = Permission::new("documents", "write");
    let admin_permission = Permission::new("documents", "admin");
    
    assert!(rbac.user_has_permission(&user_id, &read_permission));
    assert!(rbac.user_has_permission(&user_id, &write_permission));
    assert!(!rbac.user_has_permission(&user_id, &admin_permission));
    
    // Test role inheritance
    let mut parent_role = Role::new("parent_role", None);
    parent_role.add_permission(Permission::new("reports", "read"));
    let parent_role_id = parent_role.id;
    rbac.add_role(parent_role).unwrap();
    
    let mut child_role = Role::new("child_role", None);
    child_role.add_permission(Permission::new("reports", "write"));
    child_role.add_parent_role(parent_role_id);
    let child_role_id = child_role.id;
    rbac.add_role(child_role).unwrap();
    
    let user2_id = Uuid::new_v4();
    rbac.assign_role_to_user(user2_id, child_role_id).unwrap();
    
    // User should have both parent and child permissions
    assert!(rbac.user_has_permission(&user2_id, &Permission::new("reports", "read")));
    assert!(rbac.user_has_permission(&user2_id, &Permission::new("reports", "write")));
    
    // Test wildcard permissions
    let super_admin_role = rbac.get_role_by_name("super_admin").unwrap();
    assert!(super_admin_role.has_permission(&Permission::new("anything", "anything")));
}

/// Test session management
#[test]
fn test_session_management() {
    let config = SessionConfig {
        timeout: 1800, // 30 minutes
        cookie_name: "test_session".to_string(),
        cookie_domain: None,
        cookie_path: "/".to_string(),
        cookie_secure: false,
        cookie_http_only: true,
        cookie_same_site: regulateai_config::SameSitePolicy::Lax,
        enable_rotation: true,
        rotation_interval: 300, // 5 minutes
    };
    
    let mut session_manager = SessionManager::new(config);
    let user_id = Uuid::new_v4();
    
    // Create session
    let session = session_manager.create_session(
        user_id,
        Some("127.0.0.1".to_string()),
        Some("Test Agent".to_string()),
        None,
    ).unwrap();
    
    let session_id = session.id;
    assert!(session.is_valid());
    
    // Validate session
    let validated_session = session_manager.validate_session(&session_id).unwrap();
    assert_eq!(validated_session.user_id, user_id);
    
    // Test session metadata
    if let Some(session) = session_manager.get_session_mut(&session_id) {
        session.add_metadata("test_key".to_string(), serde_json::Value::String("test_value".to_string()));
        assert!(session.get_metadata("test_key").is_some());
    }
    
    // Test session rotation
    if let Some(session) = session_manager.get_session_mut(&session_id) {
        let original_id = session.id;
        session.rotate_id();
        assert_ne!(session.id, original_id);
        assert_eq!(session.rotation_count, 1);
    }
    
    // Test session invalidation
    session_manager.invalidate_session(&session_id).unwrap();
    assert!(session_manager.get_session(&session_id).is_none());
    
    // Test multiple sessions for user
    let session1 = session_manager.create_session(user_id, None, None, None).unwrap();
    let session2 = session_manager.create_session(user_id, None, None, None).unwrap();
    
    let user_sessions = session_manager.get_user_sessions(&user_id);
    assert_eq!(user_sessions.len(), 2);
    
    // Test invalidate all user sessions
    session_manager.invalidate_user_sessions(&user_id).unwrap();
    let user_sessions_after = session_manager.get_user_sessions(&user_id);
    assert_eq!(user_sessions_after.len(), 0);
}

/// Test permission matching with conditions
#[test]
fn test_conditional_permissions() {
    let mut conditions = std::collections::HashMap::new();
    conditions.insert("organization_id".to_string(), serde_json::Value::String("org123".to_string()));
    conditions.insert("department".to_string(), serde_json::Value::Array(vec![
        serde_json::Value::String("finance".to_string()),
        serde_json::Value::String("compliance".to_string()),
    ]));
    
    let conditional_permission = Permission::with_conditions("documents", "read", conditions.clone());
    
    // Test exact match
    let required_permission = Permission::with_conditions("documents", "read", conditions);
    assert!(conditional_permission.matches(&required_permission));
    
    // Test partial match (should succeed)
    let mut partial_conditions = std::collections::HashMap::new();
    partial_conditions.insert("organization_id".to_string(), serde_json::Value::String("org123".to_string()));
    let partial_permission = Permission::with_conditions("documents", "read", partial_conditions);
    assert!(conditional_permission.matches(&partial_permission));
    
    // Test no match (different org)
    let mut wrong_conditions = std::collections::HashMap::new();
    wrong_conditions.insert("organization_id".to_string(), serde_json::Value::String("org456".to_string()));
    let wrong_permission = Permission::with_conditions("documents", "read", wrong_conditions);
    assert!(!conditional_permission.matches(&wrong_permission));
    
    // Test wildcard permission
    let wildcard_permission = Permission::new("*", "*");
    assert!(wildcard_permission.matches(&required_permission));
}

/// Test authentication context
#[test]
fn test_auth_context() {
    let user_id = Uuid::new_v4();
    let session_id = Uuid::new_v4();
    let org_id = Uuid::new_v4();
    
    let auth_context = AuthContext {
        user_id,
        session_id,
        email: "test@example.com".to_string(),
        roles: vec!["user".to_string(), "analyst".to_string()],
        permissions: vec!["read".to_string(), "write".to_string(), "analyze".to_string()],
        organization_id: Some(org_id),
    };
    
    // Test permission checks
    assert!(auth_context.has_permission("read"));
    assert!(auth_context.has_permission("write"));
    assert!(auth_context.has_permission("analyze"));
    assert!(!auth_context.has_permission("admin"));
    
    // Test role checks
    assert!(auth_context.has_role("user"));
    assert!(auth_context.has_role("analyst"));
    assert!(!auth_context.has_role("admin"));
    
    assert!(auth_context.has_any_role(&["user", "admin"]));
    assert!(!auth_context.has_any_role(&["admin", "super_admin"]));
    
    // Test organization check
    assert!(auth_context.belongs_to_organization(&org_id));
    assert!(!auth_context.belongs_to_organization(&Uuid::new_v4()));
}

/// Test login request validation
#[test]
fn test_login_request_validation() {
    use validator::Validate;
    
    // Valid login request
    let valid_request = LoginRequest {
        email: "test@example.com".to_string(),
        password: "SecurePassword123!".to_string(),
        remember_me: Some(true),
        organization_id: None,
        mfa_token: None,
    };
    assert!(valid_request.validate().is_ok());
    
    // Invalid email
    let invalid_email_request = LoginRequest {
        email: "invalid-email".to_string(),
        password: "SecurePassword123!".to_string(),
        remember_me: None,
        organization_id: None,
        mfa_token: None,
    };
    assert!(invalid_email_request.validate().is_err());
    
    // Empty password
    let empty_password_request = LoginRequest {
        email: "test@example.com".to_string(),
        password: "".to_string(),
        remember_me: None,
        organization_id: None,
        mfa_token: None,
    };
    assert!(empty_password_request.validate().is_err());
}

/// Integration test for complete authentication flow
#[test]
fn test_complete_auth_flow() {
    // Setup
    let security_config = SecurityConfig::default();
    let jwt_manager = JwtManager::new(security_config.clone()).unwrap();
    let password_hasher = PasswordHasher::new(security_config.password_policy.clone());
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles().unwrap();
    
    let mut session_manager = SessionManager::new(security_config.session);
    
    // Simulate user registration
    let user_id = Uuid::new_v4();
    let email = "test@example.com";
    let password = "SecureP@ssw0rd123!";
    let password_hash = password_hasher.hash_password(password).unwrap();
    
    // Assign role to user
    let user_role = rbac_manager.get_role_by_name("user").unwrap();
    rbac_manager.assign_role_to_user(user_id, user_role.id).unwrap();
    
    // Simulate login
    assert!(password_hasher.verify_password(password, &password_hash).unwrap());
    
    // Create session
    let session = session_manager.create_session(
        user_id,
        Some("127.0.0.1".to_string()),
        Some("Test Browser".to_string()),
        None,
    ).unwrap();
    
    // Get user permissions
    let user_permissions = rbac_manager.get_user_permissions(&user_id);
    let permission_strings: Vec<String> = user_permissions.iter().map(|p| p.name.clone()).collect();
    
    // Generate tokens
    let access_token = jwt_manager.generate_access_token(
        user_id,
        email,
        vec!["user".to_string()],
        permission_strings,
        session.id,
        None,
    ).unwrap();
    
    let refresh_token = jwt_manager.generate_refresh_token(user_id, session.id).unwrap();
    
    // Validate tokens
    let access_claims = jwt_manager.validate_token(&access_token).unwrap();
    let refresh_claims = jwt_manager.validate_token(&refresh_token).unwrap();
    
    assert_eq!(access_claims.sub, user_id.to_string());
    assert_eq!(refresh_claims.sub, user_id.to_string());
    assert_eq!(access_claims.session_id, session.id.to_string());
    assert_eq!(refresh_claims.session_id, session.id.to_string());
    
    // Test authorization
    assert!(jwt_manager.has_role(&access_token, "user").unwrap());
    
    // Simulate logout
    session_manager.invalidate_session(&session.id).unwrap();
    assert!(session_manager.get_session(&session.id).is_none());
}

/// Test security features
#[test]
fn test_security_features() {
    let policy = PasswordPolicyConfig::default();
    let hasher = PasswordHasher::new(policy);
    
    // Test common password detection
    assert!(hasher.validate_password("password123").is_err());
    assert!(hasher.validate_password("123456789").is_err());
    assert!(hasher.validate_password("qwerty123").is_err());
    
    // Test pattern detection
    let password_with_repetition = "aaaaaaa1!";
    assert!(hasher.validate_password(password_with_repetition).is_err());
    
    let password_with_sequence = "abc123!";
    assert!(hasher.validate_password(password_with_sequence).is_err());
    
    // Test secure password generation
    for _ in 0..10 {
        let generated = hasher.generate_secure_password(12);
        assert_eq!(generated.len(), 12);
        assert!(hasher.validate_password(&generated).is_ok());
        
        // Ensure passwords are different
        let another_generated = hasher.generate_secure_password(12);
        assert_ne!(generated, another_generated);
    }
}
