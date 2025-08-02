//! Authentication and authorization type definitions

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

/// Login request structure
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct LoginRequest {
    #[validate(email)]
    pub email: String,
    
    #[validate(length(min = 1))]
    pub password: String,
    
    pub remember_me: Option<bool>,
    
    /// Optional organization ID for multi-tenant systems
    pub organization_id: Option<Uuid>,
    
    /// Optional MFA token
    pub mfa_token: Option<String>,
}

/// Login response structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoginResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: i64,
    pub refresh_expires_in: i64,
    pub user: UserInfo,
    pub session_id: Uuid,
    pub requires_mfa: bool,
    pub mfa_methods: Vec<MfaMethod>,
}

/// User information included in login response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserInfo {
    pub id: Uuid,
    pub email: String,
    pub username: String,
    pub first_name: String,
    pub last_name: String,
    pub full_name: String,
    pub roles: Vec<String>,
    pub permissions: Vec<String>,
    pub organization_id: Option<Uuid>,
    pub organization_name: Option<String>,
    pub last_login_at: Option<DateTime<Utc>>,
    pub is_verified: bool,
    pub profile_picture_url: Option<String>,
}

/// Logout request structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogoutRequest {
    pub refresh_token: Option<String>,
    pub logout_all_sessions: Option<bool>,
}

/// Token refresh request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RefreshTokenRequest {
    #[validate(length(min = 1))]
    pub refresh_token: String,
}

/// Token refresh response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RefreshTokenResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: i64,
    pub refresh_expires_in: i64,
}

/// Password change request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ChangePasswordRequest {
    #[validate(length(min = 1))]
    pub current_password: String,
    
    #[validate(length(min = 8, max = 128))]
    pub new_password: String,
    
    #[validate(must_match(other = "new_password"))]
    pub confirm_password: String,
}

/// Password reset request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct PasswordResetRequest {
    #[validate(email)]
    pub email: String,
    
    pub organization_id: Option<Uuid>,
}

/// Password reset confirmation
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct PasswordResetConfirmRequest {
    #[validate(length(min = 1))]
    pub reset_token: String,
    
    #[validate(length(min = 8, max = 128))]
    pub new_password: String,
    
    #[validate(must_match(other = "new_password"))]
    pub confirm_password: String,
}

/// Multi-factor authentication method
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MfaMethod {
    pub method_type: MfaMethodType,
    pub is_enabled: bool,
    pub is_primary: bool,
    pub display_name: String,
    pub last_used_at: Option<DateTime<Utc>>,
}

/// MFA method types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum MfaMethodType {
    Totp,
    Sms,
    Email,
    BackupCodes,
    Hardware,
}

/// MFA setup request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct MfaSetupRequest {
    pub method_type: MfaMethodType,
    pub phone_number: Option<String>,
    pub backup_email: Option<String>,
}

/// MFA setup response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MfaSetupResponse {
    pub method_type: MfaMethodType,
    pub secret_key: Option<String>, // For TOTP
    pub qr_code_url: Option<String>, // For TOTP
    pub backup_codes: Option<Vec<String>>,
    pub verification_required: bool,
}

/// MFA verification request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct MfaVerificationRequest {
    pub method_type: MfaMethodType,
    
    #[validate(length(min = 1))]
    pub code: String,
    
    pub remember_device: Option<bool>,
}

/// Account verification request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct AccountVerificationRequest {
    #[validate(length(min = 1))]
    pub verification_token: String,
}

/// Session information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionInfo {
    pub id: Uuid,
    pub user_id: Uuid,
    pub created_at: DateTime<Utc>,
    pub last_activity: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub is_current: bool,
    pub device_info: Option<DeviceInfo>,
    pub location_info: Option<LocationInfo>,
}

/// Device information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub device_type: String,
    pub browser: Option<String>,
    pub operating_system: Option<String>,
    pub is_mobile: bool,
    pub is_trusted: bool,
}

/// Location information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationInfo {
    pub country: Option<String>,
    pub region: Option<String>,
    pub city: Option<String>,
    pub timezone: Option<String>,
    pub is_suspicious: bool,
}

/// Authentication event types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum AuthEventType {
    Login,
    Logout,
    LoginFailed,
    PasswordChanged,
    PasswordReset,
    MfaEnabled,
    MfaDisabled,
    MfaVerified,
    MfaFailed,
    AccountLocked,
    AccountUnlocked,
    SessionExpired,
    SuspiciousActivity,
}

/// Authentication event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthEvent {
    pub id: Uuid,
    pub user_id: Option<Uuid>,
    pub event_type: AuthEventType,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub success: bool,
    pub failure_reason: Option<String>,
    pub metadata: serde_json::Value,
    pub created_at: DateTime<Utc>,
}

/// Permission check request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct PermissionCheckRequest {
    pub user_id: Uuid,
    
    #[validate(length(min = 1))]
    pub permission: String,
    
    pub resource_id: Option<String>,
    pub organization_id: Option<Uuid>,
}

/// Permission check response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionCheckResponse {
    pub has_permission: bool,
    pub reason: Option<String>,
    pub conditions: Option<serde_json::Value>,
}

/// Role assignment request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RoleAssignmentRequest {
    pub user_id: Uuid,
    pub role_ids: Vec<Uuid>,
    pub organization_id: Option<Uuid>,
    pub expires_at: Option<DateTime<Utc>>,
}

/// API key creation request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ApiKeyCreateRequest {
    #[validate(length(min = 1, max = 100))]
    pub name: String,
    
    pub description: Option<String>,
    pub permissions: Vec<String>,
    pub expires_at: Option<DateTime<Utc>>,
    pub rate_limit: Option<u32>,
    pub allowed_ips: Option<Vec<String>>,
}

/// API key response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKeyResponse {
    pub id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub key_prefix: String,
    pub permissions: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
    pub last_used_at: Option<DateTime<Utc>>,
    pub is_active: bool,
    pub rate_limit: Option<u32>,
    pub allowed_ips: Option<Vec<String>>,
}

/// API key creation response (includes the actual key)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKeyCreateResponse {
    pub api_key: ApiKeyResponse,
    pub secret_key: String, // Only returned once during creation
}

/// Authentication configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    pub password_policy: PasswordPolicyInfo,
    pub session_config: SessionConfigInfo,
    pub mfa_config: MfaConfigInfo,
    pub security_features: SecurityFeaturesInfo,
}

/// Password policy information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PasswordPolicyInfo {
    pub min_length: usize,
    pub max_length: usize,
    pub require_uppercase: bool,
    pub require_lowercase: bool,
    pub require_digits: bool,
    pub require_special_chars: bool,
    pub allowed_special_chars: String,
    pub max_login_attempts: u32,
    pub lockout_duration_minutes: u32,
    pub password_expiry_days: u32,
    pub password_history_count: u32,
}

/// Session configuration information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionConfigInfo {
    pub timeout_minutes: u32,
    pub enable_rotation: bool,
    pub rotation_interval_minutes: u32,
    pub max_concurrent_sessions: Option<u32>,
}

/// MFA configuration information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MfaConfigInfo {
    pub is_required: bool,
    pub available_methods: Vec<MfaMethodType>,
    pub backup_codes_count: u32,
    pub totp_issuer: String,
}

/// Security features information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityFeaturesInfo {
    pub rate_limiting_enabled: bool,
    pub suspicious_activity_detection: bool,
    pub device_tracking: bool,
    pub location_tracking: bool,
    pub breach_detection: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_login_request_validation() {
        let valid_request = LoginRequest {
            email: "test@example.com".to_string(),
            password: "password123".to_string(),
            remember_me: Some(true),
            organization_id: None,
            mfa_token: None,
        };
        
        assert!(valid_request.validate().is_ok());

        let invalid_request = LoginRequest {
            email: "invalid-email".to_string(),
            password: "".to_string(),
            remember_me: None,
            organization_id: None,
            mfa_token: None,
        };
        
        assert!(invalid_request.validate().is_err());
    }

    #[test]
    fn test_mfa_method_serialization() {
        let method = MfaMethod {
            method_type: MfaMethodType::Totp,
            is_enabled: true,
            is_primary: true,
            display_name: "Authenticator App".to_string(),
            last_used_at: Some(Utc::now()),
        };

        let json = serde_json::to_string(&method).unwrap();
        let deserialized: MfaMethod = serde_json::from_str(&json).unwrap();
        
        assert_eq!(method.method_type, deserialized.method_type);
        assert_eq!(method.is_enabled, deserialized.is_enabled);
    }

    #[test]
    fn test_auth_event_creation() {
        let event = AuthEvent {
            id: Uuid::new_v4(),
            user_id: Some(Uuid::new_v4()),
            event_type: AuthEventType::Login,
            ip_address: Some("127.0.0.1".to_string()),
            user_agent: Some("Test Agent".to_string()),
            success: true,
            failure_reason: None,
            metadata: serde_json::json!({"test": "data"}),
            created_at: Utc::now(),
        };

        assert_eq!(event.event_type, AuthEventType::Login);
        assert!(event.success);
    }
}
