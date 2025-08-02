//! AML service data models and types

use chrono::{DateTime, Utc, NaiveDate};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

/// Customer onboarding request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CustomerOnboardingRequest {
    pub customer_type: CustomerType,
    
    #[validate(length(min = 1, max = 100))]
    pub first_name: String,
    
    #[validate(length(min = 1, max = 100))]
    pub last_name: String,
    
    pub date_of_birth: Option<NaiveDate>,
    
    #[validate(length(min = 2, max = 3))]
    pub nationality: Option<String>,
    
    #[validate(email)]
    pub email: String,
    
    pub identification_documents: Vec<IdentificationDocument>,
    pub address: AddressInfo,
    pub contact_info: ContactInfo,
    pub organization_id: Option<Uuid>,
}

/// Customer onboarding response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerOnboardingResponse {
    pub customer_id: Uuid,
    pub status: OnboardingStatus,
    pub risk_level: RiskLevel,
    pub kyc_status: KycStatus,
    pub sanctions_status: SanctionsStatus,
    pub alerts_generated: Vec<String>,
    pub next_steps: Vec<String>,
    pub compliance_notes: Option<String>,
}

/// Customer creation request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateCustomerRequest {
    pub customer_type: CustomerType,
    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: Option<NaiveDate>,
    pub nationality: Option<String>,
    pub identification_documents: Vec<IdentificationDocument>,
    pub address: AddressInfo,
    pub contact_info: ContactInfo,
    pub organization_id: Option<Uuid>,
}

/// Transaction creation request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateTransactionRequest {
    pub customer_id: Uuid,
    
    #[validate(length(min = 1, max = 50))]
    pub transaction_type: String,
    
    #[validate(range(min = 0.01))]
    pub amount: f64,
    
    #[validate(length(min = 3, max = 3))]
    pub currency: String,
    
    pub description: Option<String>,
    pub counterparty_name: Option<String>,
    pub counterparty_account: Option<String>,
    pub counterparty_bank: Option<String>,
    pub counterparty_country: Option<String>,
    pub transaction_date: DateTime<Utc>,
    pub value_date: Option<NaiveDate>,
    pub reference_number: Option<String>,
    pub channel: Option<String>,
}

/// Alert creation request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateAlertRequest {
    #[validate(length(min = 1, max = 50))]
    pub alert_type: String,
    
    pub severity: AlertSeverity,
    pub customer_id: Option<Uuid>,
    pub transaction_id: Option<Uuid>,
    pub rule_name: Option<String>,
    
    #[validate(length(min = 1))]
    pub description: String,
    
    pub risk_score: Option<f64>,
    pub metadata: serde_json::Value,
}

/// Customer types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "UPPERCASE")]
pub enum CustomerType {
    Individual,
    Business,
}

/// Onboarding status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum OnboardingStatus {
    Approved,
    Rejected,
    PendingReview,
    PendingDocuments,
}

/// Risk levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// KYC status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum KycStatus {
    Pending,
    InProgress,
    Approved,
    Rejected,
    Expired,
}

/// Sanctions status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum SanctionsStatus {
    Clear,
    Match,
    PendingReview,
}

/// Alert severity levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum AlertSeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// Identification document
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentificationDocument {
    pub document_type: String,
    pub document_number: String,
    pub issuing_country: String,
    pub issue_date: Option<NaiveDate>,
    pub expiry_date: Option<NaiveDate>,
    pub document_image_url: Option<String>,
}

/// Address information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressInfo {
    pub street_address: String,
    pub city: String,
    pub state_province: Option<String>,
    pub postal_code: Option<String>,
    pub country: String,
}

/// Contact information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContactInfo {
    pub email: String,
    pub phone: Option<String>,
    pub mobile: Option<String>,
}

/// Transaction monitoring result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionMonitoringResult {
    pub transaction_id: Uuid,
    pub is_suspicious: bool,
    pub risk_score: f64,
    pub risk_factors: Vec<String>,
    pub triggered_rules: Vec<TriggeredRule>,
    pub monitoring_timestamp: DateTime<Utc>,
}

/// Triggered monitoring rule
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggeredRule {
    pub rule_id: String,
    pub rule_name: String,
    pub rule_type: String,
    pub severity: AlertSeverity,
    pub description: String,
    pub risk_score: f64,
    pub threshold_value: Option<f64>,
    pub actual_value: Option<f64>,
}

/// Bulk monitoring result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BulkMonitoringResult {
    pub total_processed: usize,
    pub successful: usize,
    pub failed: usize,
    pub suspicious_transactions: usize,
    pub total_alerts_generated: usize,
    pub results: Vec<BulkMonitoringItem>,
}

/// Bulk monitoring item result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BulkMonitoringItem {
    pub transaction_id: Uuid,
    pub status: String,
    pub risk_score: f64,
    pub alerts_generated: usize,
    pub error: Option<String>,
}

/// Sanctions screening result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SanctionsScreeningResult {
    pub is_match: bool,
    pub match_score: f64,
    pub match_details: String,
    pub matched_lists: Vec<String>,
    pub screening_timestamp: DateTime<Utc>,
}

/// KYC verification result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KycVerificationResult {
    pub status: KycStatus,
    pub verification_score: f64,
    pub document_verification: DocumentVerificationResult,
    pub identity_verification: IdentityVerificationResult,
    pub address_verification: AddressVerificationResult,
    pub verification_timestamp: DateTime<Utc>,
}

/// Document verification result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentVerificationResult {
    pub is_valid: bool,
    pub confidence_score: f64,
    pub document_type: String,
    pub extracted_data: serde_json::Value,
    pub verification_notes: Option<String>,
}

/// Identity verification result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityVerificationResult {
    pub is_verified: bool,
    pub confidence_score: f64,
    pub biometric_match: Option<bool>,
    pub liveness_check: Option<bool>,
    pub verification_notes: Option<String>,
}

/// Address verification result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressVerificationResult {
    pub is_verified: bool,
    pub confidence_score: f64,
    pub address_match: bool,
    pub verification_method: String,
    pub verification_notes: Option<String>,
}

/// Risk assessment result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAssessment {
    pub customer_id: Uuid,
    pub risk_score: f64,
    pub risk_level: RiskLevel,
    pub risk_factors: Vec<RiskFactor>,
    pub assessment_timestamp: DateTime<Utc>,
    pub next_review_date: DateTime<Utc>,
}

/// Risk factor
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactor {
    pub factor_type: String,
    pub factor_name: String,
    pub weight: f64,
    pub score: f64,
    pub description: String,
}

/// SAR generation request
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct SarGenerationRequest {
    pub customer_id: Option<Uuid>,
    pub transaction_id: Option<Uuid>,
    pub alert_ids: Vec<Uuid>,
    pub suspicious_activity_description: String,
    pub filing_reason: String,
    pub reporter_id: Uuid,
}

/// SAR report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SarReport {
    pub sar_id: String,
    pub filing_date: DateTime<Utc>,
    pub customer_info: CustomerSarInfo,
    pub transaction_info: Vec<TransactionSarInfo>,
    pub suspicious_activity_description: String,
    pub filing_reason: String,
    pub reporter_info: ReporterInfo,
    pub status: SarStatus,
}

/// Customer information for SAR
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomerSarInfo {
    pub customer_id: Uuid,
    pub name: String,
    pub address: AddressInfo,
    pub identification: Vec<IdentificationDocument>,
    pub account_numbers: Vec<String>,
}

/// Transaction information for SAR
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionSarInfo {
    pub transaction_id: Uuid,
    pub date: DateTime<Utc>,
    pub amount: f64,
    pub currency: String,
    pub description: String,
    pub counterparty: Option<String>,
}

/// Reporter information for SAR
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReporterInfo {
    pub reporter_id: Uuid,
    pub name: String,
    pub title: String,
    pub contact_info: ContactInfo,
}

/// SAR status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "PascalCase")]
pub enum SarStatus {
    Draft,
    Submitted,
    Acknowledged,
    UnderReview,
    Closed,
}

/// Risk summary request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskSummaryRequest {
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
    pub organization_id: Option<Uuid>,
    pub risk_levels: Option<Vec<RiskLevel>>,
}

/// Risk summary report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskSummaryReport {
    pub report_period: DateRange,
    pub total_customers: usize,
    pub risk_distribution: RiskDistribution,
    pub high_risk_customers: Vec<HighRiskCustomerSummary>,
    pub suspicious_transactions: usize,
    pub alerts_generated: usize,
    pub sars_filed: usize,
    pub compliance_metrics: ComplianceMetrics,
}

/// Date range
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DateRange {
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
}

/// Risk distribution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskDistribution {
    pub low: usize,
    pub medium: usize,
    pub high: usize,
    pub critical: usize,
}

/// High-risk customer summary
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HighRiskCustomerSummary {
    pub customer_id: Uuid,
    pub name: String,
    pub risk_score: f64,
    pub risk_level: RiskLevel,
    pub last_review_date: DateTime<Utc>,
    pub alert_count: usize,
}

/// Compliance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceMetrics {
    pub kyc_completion_rate: f64,
    pub sanctions_screening_coverage: f64,
    pub alert_resolution_time_avg: f64,
    pub false_positive_rate: f64,
    pub regulatory_reporting_timeliness: f64,
}

/// Sanctions update result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SanctionsUpdateResult {
    pub update_timestamp: DateTime<Utc>,
    pub lists_updated: Vec<String>,
    pub total_entries_added: usize,
    pub total_entries_updated: usize,
    pub total_entries_removed: usize,
    pub update_status: String,
    pub errors: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_customer_onboarding_request_validation() {
        let valid_request = CustomerOnboardingRequest {
            customer_type: CustomerType::Individual,
            first_name: "John".to_string(),
            last_name: "Doe".to_string(),
            date_of_birth: Some(NaiveDate::from_ymd_opt(1990, 1, 1).unwrap()),
            nationality: Some("US".to_string()),
            email: "john.doe@example.com".to_string(),
            identification_documents: vec![],
            address: AddressInfo {
                street_address: "123 Main St".to_string(),
                city: "New York".to_string(),
                state_province: Some("NY".to_string()),
                postal_code: Some("10001".to_string()),
                country: "US".to_string(),
            },
            contact_info: ContactInfo {
                email: "john.doe@example.com".to_string(),
                phone: Some("+1234567890".to_string()),
                mobile: None,
            },
            organization_id: None,
        };

        assert!(valid_request.validate().is_ok());
    }

    #[test]
    fn test_risk_level_serialization() {
        let risk_level = RiskLevel::High;
        let json = serde_json::to_string(&risk_level).unwrap();
        assert_eq!(json, "\"High\"");

        let deserialized: RiskLevel = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized, RiskLevel::High);
    }

    #[test]
    fn test_alert_severity_ordering() {
        let low = AlertSeverity::Low;
        let critical = AlertSeverity::Critical;
        
        // Test that we can compare severity levels
        assert_ne!(low, critical);
    }
}
