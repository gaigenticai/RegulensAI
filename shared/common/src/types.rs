//! Common types used across RegulateAI services

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;
use validator::Validate;

/// Standard API response wrapper
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
    pub timestamp: DateTime<Utc>,
    pub request_id: Uuid,
}

impl<T> ApiResponse<T> {
    pub fn success(data: T, request_id: Uuid) -> Self {
        Self {
            success: true,
            data: Some(data),
            error: None,
            timestamp: Utc::now(),
            request_id,
        }
    }

    pub fn error(error: String, request_id: Uuid) -> Self {
        Self {
            success: false,
            data: None,
            error: Some(error),
            timestamp: Utc::now(),
            request_id,
        }
    }
}

/// Pagination parameters for API requests
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct PaginationParams {
    #[validate(range(min = 1, max = 1000))]
    pub limit: Option<u32>,
    #[validate(range(min = 0))]
    pub offset: Option<u32>,
    pub sort_by: Option<String>,
    pub sort_order: Option<SortOrder>,
}

impl Default for PaginationParams {
    fn default() -> Self {
        Self {
            limit: Some(50),
            offset: Some(0),
            sort_by: None,
            sort_order: Some(SortOrder::Asc),
        }
    }
}

/// Sort order enumeration
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SortOrder {
    Asc,
    Desc,
}

/// Paginated response wrapper
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedResponse<T> {
    pub items: Vec<T>,
    pub total_count: u64,
    pub limit: u32,
    pub offset: u32,
    pub has_more: bool,
}

/// Risk level enumeration used across services
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "UPPERCASE")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

impl RiskLevel {
    pub fn from_score(score: f64) -> Self {
        match score {
            s if s < 25.0 => RiskLevel::Low,
            s if s < 50.0 => RiskLevel::Medium,
            s if s < 75.0 => RiskLevel::High,
            _ => RiskLevel::Critical,
        }
    }

    pub fn to_score_range(&self) -> (f64, f64) {
        match self {
            RiskLevel::Low => (0.0, 25.0),
            RiskLevel::Medium => (25.0, 50.0),
            RiskLevel::High => (50.0, 75.0),
            RiskLevel::Critical => (75.0, 100.0),
        }
    }
}

/// Status enumeration for various entities
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "UPPERCASE")]
pub enum Status {
    Active,
    Inactive,
    Pending,
    Suspended,
    Archived,
}

/// Priority levels for tasks, alerts, and incidents
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "UPPERCASE")]
pub enum Priority {
    Low,
    Medium,
    High,
    Urgent,
    Critical,
}

/// Geographic region enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "UPPERCASE")]
pub enum Region {
    NorthAmerica,
    SouthAmerica,
    Europe,
    Asia,
    Africa,
    Oceania,
    MiddleEast,
}

/// Currency codes (ISO 4217)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Currency {
    pub code: String,
    pub name: String,
    pub symbol: String,
}

/// Money amount with currency
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoneyAmount {
    pub amount: rust_decimal::Decimal,
    pub currency: Currency,
}

/// Address structure for entities
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct Address {
    #[validate(length(min = 1, max = 255))]
    pub street_address: String,
    #[validate(length(min = 1, max = 100))]
    pub city: String,
    #[validate(length(min = 1, max = 100))]
    pub state_province: String,
    #[validate(length(min = 1, max = 20))]
    pub postal_code: String,
    #[validate(length(min = 2, max = 3))]
    pub country_code: String,
}

/// Contact information structure
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ContactInfo {
    #[validate(email)]
    pub email: Option<String>,
    #[validate(length(min = 10, max = 20))]
    pub phone: Option<String>,
    pub address: Option<Address>,
}

/// Audit trail information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditInfo {
    pub created_at: DateTime<Utc>,
    pub created_by: Uuid,
    pub updated_at: Option<DateTime<Utc>>,
    pub updated_by: Option<Uuid>,
    pub version: u32,
}

impl AuditInfo {
    pub fn new(user_id: Uuid) -> Self {
        Self {
            created_at: Utc::now(),
            created_by: user_id,
            updated_at: None,
            updated_by: None,
            version: 1,
        }
    }

    pub fn update(&mut self, user_id: Uuid) {
        self.updated_at = Some(Utc::now());
        self.updated_by = Some(user_id);
        self.version += 1;
    }
}

/// Metadata key-value pairs
pub type Metadata = HashMap<String, serde_json::Value>;

/// Health check status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub service: String,
    pub status: ServiceStatus,
    pub timestamp: DateTime<Utc>,
    pub version: String,
    pub dependencies: Vec<DependencyStatus>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ServiceStatus {
    Healthy,
    Degraded,
    Unhealthy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencyStatus {
    pub name: String,
    pub status: ServiceStatus,
    pub response_time_ms: Option<u64>,
    pub error: Option<String>,
}
