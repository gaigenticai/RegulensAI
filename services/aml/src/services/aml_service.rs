//! Main AML service orchestrator

use async_trait::async_trait;
use sea_orm::DatabaseConnection;
use std::sync::Arc;
use tracing::{info, error, warn};
use uuid::Uuid;

use regulateai_config::{ExternalServicesConfig, AmlServiceConfig};
use regulateai_errors::RegulateAIError;
use regulateai_database::entities::{Customer, Transaction, AmlAlert};

use crate::models::*;
use crate::repositories::*;
use crate::screening::SanctionsScreener;
use crate::monitoring::TransactionMonitor;
use crate::risk_scoring::RiskScorer;
use crate::reporting::ReportGenerator;

use super::{
    CustomerService, TransactionService, AlertService, 
    SanctionsService, KycService, RiskService
};

/// Main AML service that orchestrates all AML-related operations
pub struct AmlService {
    // Core services
    customer_service: Arc<CustomerService>,
    transaction_service: Arc<TransactionService>,
    alert_service: Arc<AlertService>,
    sanctions_service: Arc<SanctionsService>,
    kyc_service: Arc<KycService>,
    risk_service: Arc<RiskService>,
    
    // Specialized components
    sanctions_screener: Arc<SanctionsScreener>,
    transaction_monitor: Arc<TransactionMonitor>,
    risk_scorer: Arc<RiskScorer>,
    report_generator: Arc<ReportGenerator>,
    
    // Configuration
    config: AmlServiceConfig,
    
    // Database connection
    db: DatabaseConnection,
}

impl AmlService {
    /// Create a new AML service instance
    pub async fn new(
        db: DatabaseConnection,
        external_config: ExternalServicesConfig,
        aml_config: AmlServiceConfig,
    ) -> Result<Self, RegulateAIError> {
        info!("Initializing AML Service");

        // Initialize repositories
        let customer_repo = Arc::new(CustomerRepository::new(db.clone()));
        let transaction_repo = Arc::new(TransactionRepository::new(db.clone()));
        let alert_repo = Arc::new(AlertRepository::new(db.clone()));
        let sanctions_repo = Arc::new(SanctionsRepository::new(db.clone()));

        // Initialize core services
        let customer_service = Arc::new(CustomerService::new(customer_repo.clone()));
        let transaction_service = Arc::new(TransactionService::new(transaction_repo.clone()));
        let alert_service = Arc::new(AlertService::new(alert_repo.clone()));
        let sanctions_service = Arc::new(SanctionsService::new(sanctions_repo.clone()));
        let kyc_service = Arc::new(KycService::new(external_config.kyc.clone()));
        let risk_service = Arc::new(RiskService::new(db.clone()));

        // Initialize specialized components
        let sanctions_screener = Arc::new(SanctionsScreener::new(
            sanctions_repo.clone(),
            external_config.ofac.clone(),
        ));
        
        let transaction_monitor = Arc::new(TransactionMonitor::new(
            transaction_repo.clone(),
            alert_repo.clone(),
            aml_config.clone(),
        ));
        
        let risk_scorer = Arc::new(RiskScorer::new(
            customer_repo.clone(),
            transaction_repo.clone(),
            aml_config.clone(),
        ));
        
        let report_generator = Arc::new(ReportGenerator::new(
            db.clone(),
            aml_config.clone(),
        ));

        info!("AML Service initialized successfully");

        Ok(Self {
            customer_service,
            transaction_service,
            alert_service,
            sanctions_service,
            kyc_service,
            risk_service,
            sanctions_screener,
            transaction_monitor,
            risk_scorer,
            report_generator,
            config: aml_config,
            db,
        })
    }

    /// Perform comprehensive customer onboarding with AML checks
    pub async fn onboard_customer(&self, request: CustomerOnboardingRequest) -> Result<CustomerOnboardingResponse, RegulateAIError> {
        info!("Starting customer onboarding for: {}", request.email);

        // Step 1: Create customer record
        let customer = self.customer_service.create_customer(CreateCustomerRequest {
            customer_type: request.customer_type.clone(),
            first_name: request.first_name.clone(),
            last_name: request.last_name.clone(),
            date_of_birth: request.date_of_birth,
            nationality: request.nationality.clone(),
            identification_documents: request.identification_documents.clone(),
            address: request.address.clone(),
            contact_info: request.contact_info.clone(),
            organization_id: request.organization_id,
        }).await?;

        // Step 2: Perform sanctions screening
        let sanctions_result = self.sanctions_screener.screen_customer(&customer).await?;
        
        if sanctions_result.is_match {
            warn!("Sanctions match found for customer: {}", customer.id);
            
            // Create high-priority alert
            self.alert_service.create_alert(CreateAlertRequest {
                alert_type: "SANCTIONS_MATCH".to_string(),
                severity: AlertSeverity::Critical,
                customer_id: Some(customer.id),
                transaction_id: None,
                rule_name: Some("Sanctions Screening".to_string()),
                description: format!("Potential sanctions match: {}", sanctions_result.match_details),
                risk_score: Some(100.0),
                metadata: serde_json::json!({
                    "sanctions_result": sanctions_result,
                    "screening_timestamp": chrono::Utc::now()
                }),
            }).await?;

            return Ok(CustomerOnboardingResponse {
                customer_id: customer.id,
                status: OnboardingStatus::Rejected,
                risk_level: RiskLevel::Critical,
                kyc_status: KycStatus::Failed,
                sanctions_status: SanctionsStatus::Match,
                alerts_generated: vec!["SANCTIONS_MATCH".to_string()],
                next_steps: vec!["Manual review required due to sanctions match".to_string()],
                compliance_notes: Some("Customer flagged in sanctions screening".to_string()),
            });
        }

        // Step 3: Perform KYC verification
        let kyc_result = self.kyc_service.verify_customer(&customer, &request.identification_documents).await?;
        
        // Step 4: Calculate risk score
        let risk_assessment = self.risk_scorer.assess_customer_risk(&customer, None).await?;

        // Step 5: Determine onboarding decision
        let (status, next_steps) = self.determine_onboarding_decision(&kyc_result, &risk_assessment, &sanctions_result);

        // Step 6: Update customer with final risk assessment
        self.customer_service.update_customer_risk(customer.id, risk_assessment.risk_score, risk_assessment.risk_level.clone()).await?;

        info!("Customer onboarding completed for: {} with status: {:?}", customer.id, status);

        Ok(CustomerOnboardingResponse {
            customer_id: customer.id,
            status,
            risk_level: risk_assessment.risk_level,
            kyc_status: kyc_result.status,
            sanctions_status: if sanctions_result.is_match { SanctionsStatus::Match } else { SanctionsStatus::Clear },
            alerts_generated: vec![], // Would be populated based on findings
            next_steps,
            compliance_notes: Some(format!("Risk score: {:.2}", risk_assessment.risk_score)),
        })
    }

    /// Monitor a transaction for suspicious activity
    pub async fn monitor_transaction(&self, transaction_id: Uuid) -> Result<TransactionMonitoringResult, RegulateAIError> {
        info!("Monitoring transaction: {}", transaction_id);

        // Get transaction details
        let transaction = self.transaction_service.get_transaction(transaction_id).await?;
        
        // Get customer details
        let customer = self.customer_service.get_customer(transaction.customer_id).await?;

        // Run transaction monitoring rules
        let monitoring_result = self.transaction_monitor.monitor_transaction(&transaction, &customer).await?;

        // If suspicious patterns detected, create alerts
        if !monitoring_result.triggered_rules.is_empty() {
            for rule in &monitoring_result.triggered_rules {
                self.alert_service.create_alert(CreateAlertRequest {
                    alert_type: rule.rule_type.clone(),
                    severity: rule.severity.clone(),
                    customer_id: Some(customer.id),
                    transaction_id: Some(transaction.id),
                    rule_name: Some(rule.rule_name.clone()),
                    description: rule.description.clone(),
                    risk_score: Some(rule.risk_score),
                    metadata: serde_json::json!({
                        "rule_details": rule,
                        "transaction_amount": transaction.amount,
                        "customer_risk_level": customer.risk_level
                    }),
                }).await?;
            }

            info!("Created {} alerts for transaction: {}", monitoring_result.triggered_rules.len(), transaction_id);
        }

        // Update transaction risk score
        self.transaction_service.update_transaction_risk(
            transaction_id,
            monitoring_result.risk_score,
            monitoring_result.risk_factors.clone(),
            monitoring_result.is_suspicious,
        ).await?;

        Ok(monitoring_result)
    }

    /// Perform bulk transaction monitoring
    pub async fn bulk_monitor_transactions(&self, transaction_ids: Vec<Uuid>) -> Result<BulkMonitoringResult, RegulateAIError> {
        info!("Bulk monitoring {} transactions", transaction_ids.len());

        let mut results = Vec::new();
        let mut total_alerts = 0;
        let mut suspicious_count = 0;

        for transaction_id in transaction_ids {
            match self.monitor_transaction(transaction_id).await {
                Ok(result) => {
                    if result.is_suspicious {
                        suspicious_count += 1;
                    }
                    total_alerts += result.triggered_rules.len();
                    results.push(BulkMonitoringItem {
                        transaction_id,
                        status: "completed".to_string(),
                        risk_score: result.risk_score,
                        alerts_generated: result.triggered_rules.len(),
                        error: None,
                    });
                }
                Err(e) => {
                    error!("Failed to monitor transaction {}: {}", transaction_id, e);
                    results.push(BulkMonitoringItem {
                        transaction_id,
                        status: "failed".to_string(),
                        risk_score: 0.0,
                        alerts_generated: 0,
                        error: Some(e.to_string()),
                    });
                }
            }
        }

        Ok(BulkMonitoringResult {
            total_processed: results.len(),
            successful: results.iter().filter(|r| r.status == "completed").count(),
            failed: results.iter().filter(|r| r.status == "failed").count(),
            suspicious_transactions: suspicious_count,
            total_alerts_generated: total_alerts,
            results,
        })
    }

    /// Generate Suspicious Activity Report (SAR)
    pub async fn generate_sar(&self, request: SarGenerationRequest) -> Result<SarReport, RegulateAIError> {
        info!("Generating SAR for customer: {:?}, transaction: {:?}", request.customer_id, request.transaction_id);

        self.report_generator.generate_sar(request).await
    }

    /// Get comprehensive risk summary report
    pub async fn get_risk_summary_report(&self, request: RiskSummaryRequest) -> Result<RiskSummaryReport, RegulateAIError> {
        info!("Generating risk summary report");

        self.report_generator.generate_risk_summary(request).await
    }

    /// Update sanctions lists from external sources
    pub async fn update_sanctions_lists(&self) -> Result<SanctionsUpdateResult, RegulateAIError> {
        info!("Updating sanctions lists");

        self.sanctions_service.update_from_external_sources().await
    }

    /// Health check for the AML service
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        // Check database connectivity
        use sea_orm::Statement;
        
        let result = self.db.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            "SELECT 1".to_string(),
        )).await;

        Ok(result.is_ok())
    }

    /// Determine onboarding decision based on various checks
    fn determine_onboarding_decision(
        &self,
        kyc_result: &KycVerificationResult,
        risk_assessment: &RiskAssessment,
        sanctions_result: &SanctionsScreeningResult,
    ) -> (OnboardingStatus, Vec<String>) {
        let mut next_steps = Vec::new();

        // Check for immediate rejection criteria
        if sanctions_result.is_match {
            return (OnboardingStatus::Rejected, vec!["Sanctions match - manual review required".to_string()]);
        }

        if kyc_result.status == KycStatus::Failed {
            return (OnboardingStatus::Rejected, vec!["KYC verification failed".to_string()]);
        }

        // Determine status based on risk level
        match risk_assessment.risk_level {
            RiskLevel::Critical => {
                next_steps.push("Enhanced due diligence required".to_string());
                next_steps.push("Senior management approval needed".to_string());
                (OnboardingStatus::PendingReview, next_steps)
            }
            RiskLevel::High => {
                next_steps.push("Additional documentation required".to_string());
                next_steps.push("Compliance team review".to_string());
                (OnboardingStatus::PendingReview, next_steps)
            }
            RiskLevel::Medium => {
                if kyc_result.status == KycStatus::Approved {
                    next_steps.push("Standard monitoring applies".to_string());
                    (OnboardingStatus::Approved, next_steps)
                } else {
                    next_steps.push("Complete KYC verification".to_string());
                    (OnboardingStatus::PendingDocuments, next_steps)
                }
            }
            RiskLevel::Low => {
                if kyc_result.status == KycStatus::Approved {
                    next_steps.push("Account activated".to_string());
                    (OnboardingStatus::Approved, next_steps)
                } else {
                    next_steps.push("Complete KYC verification".to_string());
                    (OnboardingStatus::PendingDocuments, next_steps)
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use regulateai_config::{AppSettings, ExternalServicesConfig};

    async fn create_test_aml_service() -> AmlService {
        let settings = AppSettings::default();
        let db = regulateai_database::create_test_connection().await.unwrap();
        
        AmlService::new(
            db,
            settings.external_services,
            settings.services.aml,
        ).await.unwrap()
    }

    #[tokio::test]
    async fn test_aml_service_creation() {
        let service = create_test_aml_service().await;
        assert!(service.health_check().await.unwrap());
    }

    #[tokio::test]
    async fn test_health_check() {
        let service = create_test_aml_service().await;
        let health = service.health_check().await;
        assert!(health.is_ok());
        assert!(health.unwrap());
    }
}
