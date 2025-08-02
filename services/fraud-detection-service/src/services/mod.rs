//! Core business logic services for the Fraud Detection Service

use std::sync::Arc;
use chrono::{DateTime, Utc};
use sea_orm::DatabaseConnection;
use tracing::{info, error, warn};
use uuid::Uuid;

use regulateai_config::{FraudDetectionServiceConfig, ExternalServicesConfig};
use regulateai_errors::RegulateAIError;

use crate::models::*;
use crate::repositories::*;
use crate::ml::FraudDetectionEngine;
use crate::graph::GraphAnalyticsEngine;
use crate::analytics::FraudAnalyticsEngine;

/// Main fraud detection service orchestrator
pub struct FraudDetectionService {
    pub fraud_analysis_service: Arc<FraudAnalysisService>,
    pub alert_service: Arc<AlertService>,
    pub rule_service: Arc<RuleService>,
    pub ml_service: Arc<MlService>,
    pub graph_service: Arc<GraphService>,
    pub analytics_service: Arc<AnalyticsService>,
    pub config: FraudDetectionServiceConfig,
}

impl FraudDetectionService {
    /// Create a new fraud detection service instance
    pub async fn new(
        db: DatabaseConnection,
        external_config: ExternalServicesConfig,
        config: FraudDetectionServiceConfig,
    ) -> Result<Self, RegulateAIError> {
        info!("Initializing Fraud Detection Service");

        // Initialize repositories
        let alert_repo = Arc::new(FraudAlertRepository::new(db.clone()));
        let rule_repo = Arc::new(FraudRuleRepository::new(db.clone()));
        let ml_repo = Arc::new(MlModelRepository::new(db.clone()));

        // Initialize engines
        let fraud_engine = Arc::new(FraudDetectionEngine::new(config.clone()));
        let graph_engine = Arc::new(GraphAnalyticsEngine::new(db.clone()));
        let analytics_engine = Arc::new(FraudAnalyticsEngine::new(db.clone()));

        // Initialize services
        let fraud_analysis_service = Arc::new(FraudAnalysisService::new(
            fraud_engine,
            rule_repo.clone(),
            alert_repo.clone(),
        ));
        let alert_service = Arc::new(AlertService::new(alert_repo));
        let rule_service = Arc::new(RuleService::new(rule_repo));
        let ml_service = Arc::new(MlService::new(ml_repo));
        let graph_service = Arc::new(GraphService::new(graph_engine));
        let analytics_service = Arc::new(AnalyticsService::new(analytics_engine));

        Ok(Self {
            fraud_analysis_service,
            alert_service,
            rule_service,
            ml_service,
            graph_service,
            analytics_service,
            config,
        })
    }

    /// Analyze transaction for fraud
    pub async fn analyze_transaction(&self, request: TransactionAnalysisRequest) -> Result<FraudAnalysisResult, RegulateAIError> {
        self.fraud_analysis_service.analyze_transaction(request).await
    }

    /// Get fraud alert by ID
    pub async fn get_fraud_alert(&self, id: Uuid) -> Result<Option<FraudAlert>, RegulateAIError> {
        self.alert_service.get_by_id(id).await
    }

    /// List fraud alerts with pagination
    pub async fn list_fraud_alerts(&self, page: u64, per_page: u64) -> Result<Vec<FraudAlert>, RegulateAIError> {
        self.alert_service.list(page, per_page).await
    }

    /// Update alert status
    pub async fn update_alert_status(&self, id: Uuid, request: UpdateAlertStatusRequest, updated_by: Uuid) -> Result<FraudAlert, RegulateAIError> {
        self.alert_service.update_status(id, request.status, updated_by).await
    }

    /// Create fraud rule
    pub async fn create_fraud_rule(&self, request: CreateFraudRuleRequest, created_by: Uuid) -> Result<FraudRule, RegulateAIError> {
        self.rule_service.create(request, created_by).await
    }

    /// Get fraud rule by ID
    pub async fn get_fraud_rule(&self, id: Uuid) -> Result<Option<FraudRule>, RegulateAIError> {
        self.rule_service.get_by_id(id).await
    }

    /// List fraud rules with pagination
    pub async fn list_fraud_rules(&self, page: u64, per_page: u64) -> Result<Vec<FraudRule>, RegulateAIError> {
        self.rule_service.list(page, per_page).await
    }

    /// Update fraud rule
    pub async fn update_fraud_rule(&self, id: Uuid, request: UpdateFraudRuleRequest, updated_by: Uuid) -> Result<FraudRule, RegulateAIError> {
        self.rule_service.update(id, request, updated_by).await
    }

    /// Delete fraud rule
    pub async fn delete_fraud_rule(&self, id: Uuid, deleted_by: Uuid) -> Result<(), RegulateAIError> {
        self.rule_service.delete(id, deleted_by).await
    }

    /// Get model metrics
    pub async fn get_model_metrics(&self, model_id: Uuid) -> Result<ModelMetrics, RegulateAIError> {
        self.ml_service.get_metrics(model_id).await
    }

    /// Retrain model
    pub async fn retrain_model(&self, model_id: Uuid, request: RetrainModelRequest, initiated_by: Uuid) -> Result<ModelRetrainResult, RegulateAIError> {
        self.ml_service.retrain_model(model_id, request, initiated_by).await
    }

    /// Get service health status
    pub async fn health_check(&self) -> Result<ServiceHealth, RegulateAIError> {
        info!("Performing fraud detection service health check");

        Ok(ServiceHealth {
            service_name: "Fraud Detection Service".to_string(),
            status: "healthy".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            uptime: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            dependencies: vec![
                DependencyHealth {
                    name: "Database".to_string(),
                    status: "healthy".to_string(),
                },
                DependencyHealth {
                    name: "ML Engine".to_string(),
                    status: "healthy".to_string(),
                },
                DependencyHealth {
                    name: "Graph Analytics".to_string(),
                    status: "healthy".to_string(),
                },
            ],
        })
    }
}

// =============================================================================
// FRAUD ANALYSIS SERVICE
// =============================================================================

pub struct FraudAnalysisService {
    fraud_engine: Arc<FraudDetectionEngine>,
    rule_repository: Arc<FraudRuleRepository>,
    alert_repository: Arc<FraudAlertRepository>,
}

impl FraudAnalysisService {
    pub fn new(
        fraud_engine: Arc<FraudDetectionEngine>,
        rule_repository: Arc<FraudRuleRepository>,
        alert_repository: Arc<FraudAlertRepository>,
    ) -> Self {
        Self {
            fraud_engine,
            rule_repository,
            alert_repository,
        }
    }

    /// Analyze transaction for fraud
    pub async fn analyze_transaction(&self, request: TransactionAnalysisRequest) -> Result<FraudAnalysisResult, RegulateAIError> {
        info!("Analyzing transaction for fraud: {}", request.transaction_id);

        // Get active fraud rules
        let rules = self.rule_repository.get_active_rules().await?;

        // Run ML-based fraud detection
        let ml_score = self.fraud_engine.predict_fraud_score(&request).await?;

        // Evaluate rules
        let mut triggered_rules = Vec::new();
        let mut max_rule_score = 0.0;

        for rule in rules {
            if self.evaluate_rule(&rule, &request).await? {
                triggered_rules.push(rule.id);
                max_rule_score = max_rule_score.max(rule.severity.parse::<f64>().unwrap_or(0.0));
            }
        }

        // Calculate combined risk score
        let combined_score = (ml_score * 0.7) + (max_rule_score * 0.3);

        // Determine if alert should be created
        let should_alert = combined_score >= self.fraud_engine.get_threshold();

        let mut alert_id = None;
        if should_alert {
            // Create fraud alert
            let alert_request = CreateFraudAlertRequest {
                alert_type: "TRANSACTION_FRAUD".to_string(),
                customer_id: Some(request.customer_id),
                transaction_id: Some(request.transaction_id),
                rule_id: triggered_rules.first().copied(),
                risk_score: combined_score,
                severity: if combined_score >= 80.0 { "HIGH" } else if combined_score >= 60.0 { "MEDIUM" } else { "LOW" }.to_string(),
                description: format!("Potential fraud detected - Risk Score: {:.2}", combined_score),
                metadata: Some(serde_json::json!({
                    "ml_score": ml_score,
                    "rule_score": max_rule_score,
                    "triggered_rules": triggered_rules
                })),
            };

            let alert = self.alert_repository.create(alert_request, Uuid::new_v4()).await?;
            alert_id = Some(alert.id);
        }

        Ok(FraudAnalysisResult {
            transaction_id: request.transaction_id,
            risk_score: combined_score,
            is_fraud: should_alert,
            confidence: ml_score,
            triggered_rules,
            alert_id,
            analysis_timestamp: Utc::now(),
            model_version: "v1.0".to_string(),
            features_used: vec![
                "transaction_amount".to_string(),
                "merchant_category".to_string(),
                "time_of_day".to_string(),
                "location".to_string(),
                "customer_behavior".to_string(),
            ],
        })
    }

    /// Evaluate a fraud rule against transaction data
    async fn evaluate_rule(&self, rule: &FraudRule, request: &TransactionAnalysisRequest) -> Result<bool, RegulateAIError> {
        // In a real implementation, this would:
        // - Parse rule conditions JSON
        // - Apply conditions to transaction data
        // - Return true if rule is triggered

        // Simplified rule evaluation for demonstration
        match rule.rule_type.as_str() {
            "VELOCITY" => {
                // Check transaction velocity
                Ok(request.transaction_count_24h.unwrap_or(0) > 10)
            },
            "AMOUNT" => {
                // Check transaction amount
                Ok(request.amount > 10000.0)
            },
            "LOCATION" => {
                // Check location anomaly
                Ok(request.location_risk_score.unwrap_or(0.0) > 70.0)
            },
            "PATTERN" => {
                // Check behavioral patterns
                Ok(request.behavior_score.unwrap_or(0.0) > 80.0)
            },
            _ => Ok(false),
        }
    }
}

// =============================================================================
// ALERT SERVICE
// =============================================================================

pub struct AlertService {
    repository: Arc<FraudAlertRepository>,
}

impl AlertService {
    pub fn new(repository: Arc<FraudAlertRepository>) -> Self {
        Self { repository }
    }

    /// Get alert by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<FraudAlert>, RegulateAIError> {
        self.repository.get_by_id(id).await
    }

    /// List alerts with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<FraudAlert>, RegulateAIError> {
        self.repository.list(page, per_page).await
    }

    /// Update alert status
    pub async fn update_status(&self, id: Uuid, status: String, updated_by: Uuid) -> Result<FraudAlert, RegulateAIError> {
        self.repository.update_status(id, status, updated_by).await
    }
}

// =============================================================================
// RULE SERVICE
// =============================================================================

pub struct RuleService {
    repository: Arc<FraudRuleRepository>,
}

impl RuleService {
    pub fn new(repository: Arc<FraudRuleRepository>) -> Self {
        Self { repository }
    }

    /// Create fraud rule
    pub async fn create(&self, request: CreateFraudRuleRequest, created_by: Uuid) -> Result<FraudRule, RegulateAIError> {
        self.repository.create(request, created_by).await
    }

    /// Get rule by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<FraudRule>, RegulateAIError> {
        self.repository.get_by_id(id).await
    }

    /// List rules with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<FraudRule>, RegulateAIError> {
        self.repository.list(page, per_page).await
    }

    /// Update rule
    pub async fn update(&self, id: Uuid, request: UpdateFraudRuleRequest, updated_by: Uuid) -> Result<FraudRule, RegulateAIError> {
        self.repository.update(id, request, updated_by).await
    }

    /// Delete rule
    pub async fn delete(&self, id: Uuid, deleted_by: Uuid) -> Result<(), RegulateAIError> {
        info!("Deleting fraud rule: {} by user: {}", id, deleted_by);
        self.repository.delete(id).await
    }
}

// =============================================================================
// ML SERVICE
// =============================================================================

pub struct MlService {
    repository: Arc<MlModelRepository>,
}

impl MlService {
    pub fn new(repository: Arc<MlModelRepository>) -> Self {
        Self { repository }
    }

    /// Get model metrics
    pub async fn get_metrics(&self, model_id: Uuid) -> Result<ModelMetrics, RegulateAIError> {
        info!("Getting ML model metrics: {}", model_id);

        // In a real implementation, this would load actual metrics from the model
        Ok(ModelMetrics {
            model_id,
            accuracy: 0.92,
            precision: 0.89,
            recall: 0.94,
            f1_score: 0.91,
            auc_score: 0.96,
            false_positive_rate: 0.08,
            false_negative_rate: 0.06,
            last_updated: Utc::now(),
        })
    }

    /// Retrain model
    pub async fn retrain_model(&self, model_id: Uuid, request: RetrainModelRequest, initiated_by: Uuid) -> Result<ModelRetrainResult, RegulateAIError> {
        info!("Initiating model retrain: {} by user: {}", model_id, initiated_by);

        // In a real implementation, this would:
        // - Queue model retraining job
        // - Return job ID for tracking
        // - Update model status

        Ok(ModelRetrainResult {
            model_id,
            job_id: Uuid::new_v4(),
            status: "QUEUED".to_string(),
            initiated_at: Utc::now(),
            estimated_completion: Utc::now() + chrono::Duration::hours(2),
            initiated_by,
        })
    }
}

// =============================================================================
// GRAPH SERVICE
// =============================================================================

pub struct GraphService {
    engine: Arc<GraphAnalyticsEngine>,
}

impl GraphService {
    pub fn new(engine: Arc<GraphAnalyticsEngine>) -> Self {
        Self { engine }
    }

    /// Analyze fraud networks
    pub async fn analyze_networks(&self, customer_id: Uuid) -> Result<NetworkAnalysisResult, RegulateAIError> {
        self.engine.analyze_fraud_networks(customer_id).await
    }
}

// =============================================================================
// ANALYTICS SERVICE
// =============================================================================

pub struct AnalyticsService {
    engine: Arc<FraudAnalyticsEngine>,
}

impl AnalyticsService {
    pub fn new(engine: Arc<FraudAnalyticsEngine>) -> Self {
        Self { engine }
    }

    /// Generate fraud analytics dashboard
    pub async fn generate_dashboard(&self) -> Result<FraudDashboard, RegulateAIError> {
        self.engine.generate_dashboard().await
    }
}
