//! User entity model

use chrono::{DateTime, Utc};
use sea_orm::entity::prelude::*;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

use regulateai_common::{Auditable, AuditInfo, Identifiable};

/// User entity
#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize, Validate)]
#[sea_orm(table_name = "users")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: Uuid,
    
    #[validate(email)]
    #[sea_orm(unique)]
    pub email: String,
    
    #[validate(length(min = 3, max = 100))]
    #[sea_orm(unique)]
    pub username: String,
    
    #[validate(length(min = 8))]
    pub password_hash: String,
    
    #[validate(length(min = 1, max = 100))]
    pub first_name: String,
    
    #[validate(length(min = 1, max = 100))]
    pub last_name: String,
    
    #[validate(length(min = 10, max = 20))]
    pub phone: Option<String>,
    
    pub is_active: bool,
    pub is_verified: bool,
    pub last_login_at: Option<DateTime<Utc>>,
    pub failed_login_attempts: i32,
    pub locked_until: Option<DateTime<Utc>>,
    pub password_changed_at: DateTime<Utc>,
    
    // Audit fields
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Option<Uuid>,
    pub updated_by: Option<Uuid>,
    pub version: i32,
    
    // Metadata as JSON
    pub metadata: Json,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(has_many = "super::user_role::Entity")]
    UserRoles,
    
    #[sea_orm(has_many = "super::organization::Entity")]
    OrganizationsCreated,
    
    #[sea_orm(has_many = "super::audit_log::Entity")]
    AuditLogs,
    
    #[sea_orm(has_many = "super::customer::Entity")]
    CustomersCreated,
    
    #[sea_orm(has_many = "super::transaction::Entity")]
    TransactionsCreated,
    
    #[sea_orm(has_many = "super::aml_alert::Entity")]
    AmlAlertsAssigned,
    
    #[sea_orm(has_many = "super::policy::Entity")]
    PoliciesOwned,
    
    #[sea_orm(has_many = "super::control::Entity")]
    ControlsOwned,
    
    #[sea_orm(has_many = "super::control_test::Entity")]
    ControlTestsConducted,
    
    #[sea_orm(has_many = "super::risk_assessment::Entity")]
    RiskAssessmentsConducted,
    
    #[sea_orm(has_many = "super::key_risk_indicator::Entity")]
    KrisOwned,
    
    #[sea_orm(has_many = "super::stress_test::Entity")]
    StressTestsExecuted,
    
    #[sea_orm(has_many = "super::fraud_alert::Entity")]
    FraudAlertsAssigned,
    
    #[sea_orm(has_many = "super::vulnerability::Entity")]
    VulnerabilitiesAssigned,
    
    #[sea_orm(has_many = "super::security_incident::Entity")]
    SecurityIncidentsAssigned,
    
    #[sea_orm(has_many = "super::ai_conversation::Entity")]
    AiConversations,
}

impl ActiveModelBehavior for ActiveModel {}

impl Identifiable for Model {
    fn id(&self) -> Uuid {
        self.id
    }
}

impl Auditable for Model {
    fn audit_info(&self) -> &AuditInfo {
        // Convert entity fields to AuditInfo structure
        static mut AUDIT_INFO_CACHE: Option<AuditInfo> = None;

        unsafe {
            AUDIT_INFO_CACHE = Some(AuditInfo {
                created_at: self.created_at,
                created_by: self.created_by.unwrap_or_default(),
                updated_at: Some(self.updated_at),
                updated_by: self.updated_by,
                version: self.version as u32,
            });
            AUDIT_INFO_CACHE.as_ref().unwrap()
        }
    }
    
    fn audit_info_mut(&mut self) -> &mut AuditInfo {
        // Create a mutable AuditInfo from the current fields
        // This implementation provides direct access to audit information
        static mut AUDIT_INFO: Option<AuditInfo> = None;

        unsafe {
            AUDIT_INFO = Some(AuditInfo {
                created_at: self.created_at,
                created_by: self.created_by.unwrap_or_default(),
                updated_at: Some(self.updated_at),
                updated_by: self.updated_by,
                version: self.version as u32,
            });
            AUDIT_INFO.as_mut().unwrap()
        }
    }
}

impl Model {
    /// Get the user's full name
    pub fn full_name(&self) -> String {
        format!("{} {}", self.first_name, self.last_name)
    }
    
    /// Check if the user account is locked
    pub fn is_locked(&self) -> bool {
        if let Some(locked_until) = self.locked_until {
            locked_until > Utc::now()
        } else {
            false
        }
    }
    
    /// Check if the user needs to change their password
    pub fn needs_password_change(&self, max_age_days: i64) -> bool {
        let max_age = chrono::Duration::days(max_age_days);
        Utc::now() - self.password_changed_at > max_age
    }
    
    /// Increment failed login attempts
    pub fn increment_failed_attempts(&mut self) {
        self.failed_login_attempts += 1;
    }
    
    /// Reset failed login attempts
    pub fn reset_failed_attempts(&mut self) {
        self.failed_login_attempts = 0;
        self.locked_until = None;
    }
    
    /// Lock the user account
    pub fn lock_account(&mut self, duration_minutes: i64) {
        self.locked_until = Some(Utc::now() + chrono::Duration::minutes(duration_minutes));
    }
    
    /// Update last login timestamp
    pub fn update_last_login(&mut self) {
        self.last_login_at = Some(Utc::now());
    }
    
    /// Check if user has a specific permission (simplified - would integrate with RBAC)
    pub fn has_permission(&self, _permission: &str) -> bool {
        // This would be implemented with proper RBAC integration
        self.is_active && !self.is_locked()
    }
}

/// User creation request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateUserRequest {
    #[validate(email)]
    pub email: String,
    
    #[validate(length(min = 3, max = 100))]
    pub username: String,
    
    #[validate(length(min = 8, max = 128))]
    pub password: String,
    
    #[validate(length(min = 1, max = 100))]
    pub first_name: String,
    
    #[validate(length(min = 1, max = 100))]
    pub last_name: String,
    
    #[validate(length(min = 10, max = 20))]
    pub phone: Option<String>,
    
    pub role_ids: Vec<Uuid>,
}

/// User update request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct UpdateUserRequest {
    #[validate(email)]
    pub email: Option<String>,
    
    #[validate(length(min = 1, max = 100))]
    pub first_name: Option<String>,
    
    #[validate(length(min = 1, max = 100))]
    pub last_name: Option<String>,
    
    #[validate(length(min = 10, max = 20))]
    pub phone: Option<String>,
    
    pub is_active: Option<bool>,
    pub is_verified: Option<bool>,
}

/// User response DTO
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserResponse {
    pub id: Uuid,
    pub email: String,
    pub username: String,
    pub first_name: String,
    pub last_name: String,
    pub full_name: String,
    pub phone: Option<String>,
    pub is_active: bool,
    pub is_verified: bool,
    pub is_locked: bool,
    pub last_login_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub roles: Vec<String>,
}

impl From<Model> for UserResponse {
    fn from(user: Model) -> Self {
        Self {
            id: user.id,
            email: user.email.clone(),
            username: user.username.clone(),
            first_name: user.first_name.clone(),
            last_name: user.last_name.clone(),
            full_name: user.full_name(),
            phone: user.phone.clone(),
            is_active: user.is_active,
            is_verified: user.is_verified,
            is_locked: user.is_locked(),
            last_login_at: user.last_login_at,
            created_at: user.created_at,
            updated_at: user.updated_at,
            roles: vec![], // Would be populated with actual roles
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_full_name() {
        let user = Model {
            id: Uuid::new_v4(),
            email: "test@example.com".to_string(),
            username: "testuser".to_string(),
            password_hash: "hashed_password".to_string(),
            first_name: "John".to_string(),
            last_name: "Doe".to_string(),
            phone: None,
            is_active: true,
            is_verified: true,
            last_login_at: None,
            failed_login_attempts: 0,
            locked_until: None,
            password_changed_at: Utc::now(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: None,
            updated_by: None,
            version: 1,
            metadata: Json::default(),
        };
        
        assert_eq!(user.full_name(), "John Doe");
    }

    #[test]
    fn test_user_is_locked() {
        let mut user = Model {
            id: Uuid::new_v4(),
            email: "test@example.com".to_string(),
            username: "testuser".to_string(),
            password_hash: "hashed_password".to_string(),
            first_name: "John".to_string(),
            last_name: "Doe".to_string(),
            phone: None,
            is_active: true,
            is_verified: true,
            last_login_at: None,
            failed_login_attempts: 0,
            locked_until: None,
            password_changed_at: Utc::now(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: None,
            updated_by: None,
            version: 1,
            metadata: Json::default(),
        };
        
        assert!(!user.is_locked());
        
        user.lock_account(15);
        assert!(user.is_locked());
    }

    #[test]
    fn test_create_user_request_validation() {
        let request = CreateUserRequest {
            email: "invalid-email".to_string(),
            username: "ab".to_string(), // Too short
            password: "short".to_string(), // Too short
            first_name: "".to_string(), // Empty
            last_name: "Doe".to_string(),
            phone: None,
            role_ids: vec![],
        };
        
        assert!(request.validate().is_err());
    }
}
