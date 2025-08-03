//! Test Data Factories
//! 
//! Provides factories for generating test data with realistic values
//! and proper relationships between entities.

use fake::{Fake, Faker};
use fake::faker::internet::en::*;
use fake::faker::name::en::*;
use fake::faker::company::en::*;
use fake::faker::address::en::*;
use fake::faker::chrono::en::*;
use fake::faker::finance::en::*;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Test data factory for creating realistic test entities
pub struct TestDataFactory {
    config: FactoryConfig,
}

/// Factory configuration
#[derive(Debug, Clone)]
pub struct FactoryConfig {
    pub seed: Option<u64>,
    pub locale: String,
    pub realistic_data: bool,
    pub consistent_relationships: bool,
}

/// Entity factory trait
pub trait EntityFactory<T> {
    fn create(&self) -> T;
    fn create_batch(&self, count: usize) -> Vec<T>;
    fn create_with_overrides(&self, overrides: HashMap<String, serde_json::Value>) -> T;
}

impl TestDataFactory {
    /// Create a new test data factory
    pub fn new(config: FactoryConfig) -> Self {
        Self { config }
    }

    /// Create customer factory
    pub fn customers(&self) -> CustomerFactory {
        CustomerFactory::new(self.config.clone())
    }

    /// Create transaction factory
    pub fn transactions(&self) -> TransactionFactory {
        TransactionFactory::new(self.config.clone())
    }

    /// Create compliance policy factory
    pub fn compliance_policies(&self) -> CompliancePolicyFactory {
        CompliancePolicyFactory::new(self.config.clone())
    }

    /// Create audit log factory
    pub fn audit_logs(&self) -> AuditLogFactory {
        AuditLogFactory::new(self.config.clone())
    }

    /// Create risk assessment factory
    pub fn risk_assessments(&self) -> RiskAssessmentFactory {
        RiskAssessmentFactory::new(self.config.clone())
    }
}

/// Customer factory
pub struct CustomerFactory {
    config: FactoryConfig,
}

impl CustomerFactory {
    pub fn new(config: FactoryConfig) -> Self {
        Self { config }
    }
}

impl EntityFactory<TestCustomer> for CustomerFactory {
    fn create(&self) -> TestCustomer {
        TestCustomer {
            id: Uuid::new_v4(),
            name: Name().fake(),
            email: SafeEmail().fake(),
            date_of_birth: DateTimeBetween(
                chrono::NaiveDate::from_ymd_opt(1950, 1, 1).unwrap().and_hms_opt(0, 0, 0).unwrap(),
                chrono::NaiveDate::from_ymd_opt(2000, 12, 31).unwrap().and_hms_opt(23, 59, 59).unwrap()
            ).fake(),
            country_code: CountryCode().fake(),
            phone: PhoneNumber().fake(),
            address: TestAddress {
                street: StreetName().fake(),
                city: CityName().fake(),
                state: StateName().fake(),
                postal_code: PostCode().fake(),
                country: CountryName().fake(),
            },
            kyc_status: ["PENDING", "IN_PROGRESS", "COMPLETED", "REJECTED"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            risk_level: ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    fn create_batch(&self, count: usize) -> Vec<TestCustomer> {
        (0..count).map(|_| self.create()).collect()
    }

    fn create_with_overrides(&self, overrides: HashMap<String, serde_json::Value>) -> TestCustomer {
        let mut customer = self.create();
        
        for (key, value) in overrides {
            match key.as_str() {
                "name" => {
                    if let Some(name) = value.as_str() {
                        customer.name = name.to_string();
                    }
                }
                "email" => {
                    if let Some(email) = value.as_str() {
                        customer.email = email.to_string();
                    }
                }
                "kyc_status" => {
                    if let Some(status) = value.as_str() {
                        customer.kyc_status = status.to_string();
                    }
                }
                "risk_level" => {
                    if let Some(level) = value.as_str() {
                        customer.risk_level = level.to_string();
                    }
                }
                _ => {}
            }
        }
        
        customer
    }
}

/// Transaction factory
pub struct TransactionFactory {
    config: FactoryConfig,
}

impl TransactionFactory {
    pub fn new(config: FactoryConfig) -> Self {
        Self { config }
    }
}

impl EntityFactory<TestTransaction> for TransactionFactory {
    fn create(&self) -> TestTransaction {
        let amount: f64 = (1.0..1_000_000.0).fake();
        
        TestTransaction {
            id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            amount,
            currency: ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            transaction_type: ["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            status: ["PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            description: CompanyName().fake(),
            reference_number: format!("TXN-{}", (100000..999999).fake::<u32>()),
            source_account: Bic().fake(),
            destination_account: Bic().fake(),
            risk_score: (0.0..100.0).fake(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    fn create_batch(&self, count: usize) -> Vec<TestTransaction> {
        (0..count).map(|_| self.create()).collect()
    }

    fn create_with_overrides(&self, overrides: HashMap<String, serde_json::Value>) -> TestTransaction {
        let mut transaction = self.create();
        
        for (key, value) in overrides {
            match key.as_str() {
                "amount" => {
                    if let Some(amount) = value.as_f64() {
                        transaction.amount = amount;
                    }
                }
                "currency" => {
                    if let Some(currency) = value.as_str() {
                        transaction.currency = currency.to_string();
                    }
                }
                "customer_id" => {
                    if let Some(id_str) = value.as_str() {
                        if let Ok(id) = Uuid::parse_str(id_str) {
                            transaction.customer_id = id;
                        }
                    }
                }
                "status" => {
                    if let Some(status) = value.as_str() {
                        transaction.status = status.to_string();
                    }
                }
                _ => {}
            }
        }
        
        transaction
    }
}

/// Compliance policy factory
pub struct CompliancePolicyFactory {
    config: FactoryConfig,
}

impl CompliancePolicyFactory {
    pub fn new(config: FactoryConfig) -> Self {
        Self { config }
    }
}

impl EntityFactory<TestCompliancePolicy> for CompliancePolicyFactory {
    fn create(&self) -> TestCompliancePolicy {
        TestCompliancePolicy {
            id: Uuid::new_v4(),
            name: format!("{} Policy", CompanyName().fake::<String>()),
            description: CatchPhase().fake(),
            policy_type: ["AML", "KYC", "GDPR", "SOX", "PCI_DSS", "HIPAA"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            version: format!("{}.{}.{}", 
                (1..10).fake::<u8>(), 
                (0..20).fake::<u8>(), 
                (0..100).fake::<u8>()
            ),
            status: ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            effective_date: Utc::now(),
            expiry_date: Some(Utc::now() + chrono::Duration::days(365)),
            created_by: Uuid::new_v4(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    fn create_batch(&self, count: usize) -> Vec<TestCompliancePolicy> {
        (0..count).map(|_| self.create()).collect()
    }

    fn create_with_overrides(&self, overrides: HashMap<String, serde_json::Value>) -> TestCompliancePolicy {
        let mut policy = self.create();
        
        for (key, value) in overrides {
            match key.as_str() {
                "name" => {
                    if let Some(name) = value.as_str() {
                        policy.name = name.to_string();
                    }
                }
                "policy_type" => {
                    if let Some(policy_type) = value.as_str() {
                        policy.policy_type = policy_type.to_string();
                    }
                }
                "status" => {
                    if let Some(status) = value.as_str() {
                        policy.status = status.to_string();
                    }
                }
                _ => {}
            }
        }
        
        policy
    }
}

/// Audit log factory
pub struct AuditLogFactory {
    config: FactoryConfig,
}

impl AuditLogFactory {
    pub fn new(config: FactoryConfig) -> Self {
        Self { config }
    }
}

impl EntityFactory<TestAuditLog> for AuditLogFactory {
    fn create(&self) -> TestAuditLog {
        TestAuditLog {
            id: Uuid::new_v4(),
            user_id: Some(Uuid::new_v4()),
            action: ["CREATE", "UPDATE", "DELETE", "VIEW", "APPROVE", "REJECT"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            resource_type: ["CUSTOMER", "TRANSACTION", "POLICY", "ASSESSMENT", "ALERT"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            resource_id: Uuid::new_v4(),
            details: serde_json::json!({
                "field_changes": {
                    "status": {
                        "old": "PENDING",
                        "new": "APPROVED"
                    }
                },
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }),
            timestamp: Utc::now(),
        }
    }

    fn create_batch(&self, count: usize) -> Vec<TestAuditLog> {
        (0..count).map(|_| self.create()).collect()
    }

    fn create_with_overrides(&self, overrides: HashMap<String, serde_json::Value>) -> TestAuditLog {
        let mut log = self.create();
        
        for (key, value) in overrides {
            match key.as_str() {
                "action" => {
                    if let Some(action) = value.as_str() {
                        log.action = action.to_string();
                    }
                }
                "resource_type" => {
                    if let Some(resource_type) = value.as_str() {
                        log.resource_type = resource_type.to_string();
                    }
                }
                _ => {}
            }
        }
        
        log
    }
}

/// Risk assessment factory
pub struct RiskAssessmentFactory {
    config: FactoryConfig,
}

impl RiskAssessmentFactory {
    pub fn new(config: FactoryConfig) -> Self {
        Self { config }
    }
}

impl EntityFactory<TestRiskAssessment> for RiskAssessmentFactory {
    fn create(&self) -> TestRiskAssessment {
        TestRiskAssessment {
            id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            assessment_type: ["ONBOARDING", "PERIODIC", "TRANSACTION_BASED", "EVENT_DRIVEN"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            risk_score: (0.0..100.0).fake(),
            risk_level: ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                .choose(&mut rand::thread_rng())
                .unwrap()
                .to_string(),
            factors: serde_json::json!({
                "geographic_risk": (0.0..100.0).fake::<f64>(),
                "transaction_volume": (0.0..100.0).fake::<f64>(),
                "customer_profile": (0.0..100.0).fake::<f64>(),
                "regulatory_risk": (0.0..100.0).fake::<f64>()
            }),
            recommendations: vec![
                "Enhanced due diligence required".to_string(),
                "Monitor transaction patterns".to_string(),
                "Review customer documentation".to_string(),
            ],
            assessed_by: Uuid::new_v4(),
            assessed_at: Utc::now(),
            valid_until: Utc::now() + chrono::Duration::days(90),
        }
    }

    fn create_batch(&self, count: usize) -> Vec<TestRiskAssessment> {
        (0..count).map(|_| self.create()).collect()
    }

    fn create_with_overrides(&self, overrides: HashMap<String, serde_json::Value>) -> TestRiskAssessment {
        let mut assessment = self.create();
        
        for (key, value) in overrides {
            match key.as_str() {
                "risk_score" => {
                    if let Some(score) = value.as_f64() {
                        assessment.risk_score = score;
                    }
                }
                "risk_level" => {
                    if let Some(level) = value.as_str() {
                        assessment.risk_level = level.to_string();
                    }
                }
                "assessment_type" => {
                    if let Some(assessment_type) = value.as_str() {
                        assessment.assessment_type = assessment_type.to_string();
                    }
                }
                _ => {}
            }
        }
        
        assessment
    }
}

// Test entity definitions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCustomer {
    pub id: Uuid,
    pub name: String,
    pub email: String,
    pub date_of_birth: DateTime<Utc>,
    pub country_code: String,
    pub phone: String,
    pub address: TestAddress,
    pub kyc_status: String,
    pub risk_level: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestAddress {
    pub street: String,
    pub city: String,
    pub state: String,
    pub postal_code: String,
    pub country: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestTransaction {
    pub id: Uuid,
    pub customer_id: Uuid,
    pub amount: f64,
    pub currency: String,
    pub transaction_type: String,
    pub status: String,
    pub description: String,
    pub reference_number: String,
    pub source_account: String,
    pub destination_account: String,
    pub risk_score: f64,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCompliancePolicy {
    pub id: Uuid,
    pub name: String,
    pub description: String,
    pub policy_type: String,
    pub version: String,
    pub status: String,
    pub effective_date: DateTime<Utc>,
    pub expiry_date: Option<DateTime<Utc>>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestAuditLog {
    pub id: Uuid,
    pub user_id: Option<Uuid>,
    pub action: String,
    pub resource_type: String,
    pub resource_id: Uuid,
    pub details: serde_json::Value,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestRiskAssessment {
    pub id: Uuid,
    pub customer_id: Uuid,
    pub assessment_type: String,
    pub risk_score: f64,
    pub risk_level: String,
    pub factors: serde_json::Value,
    pub recommendations: Vec<String>,
    pub assessed_by: Uuid,
    pub assessed_at: DateTime<Utc>,
    pub valid_until: DateTime<Utc>,
}

impl Default for FactoryConfig {
    fn default() -> Self {
        Self {
            seed: None,
            locale: "en".to_string(),
            realistic_data: true,
            consistent_relationships: true,
        }
    }
}

// Add missing imports
use rand::seq::SliceRandom;
