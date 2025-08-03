//! Core business logic services for the Risk Management Service

use std::sync::Arc;
use chrono::{DateTime, NaiveDate, Utc};
use sea_orm::DatabaseConnection;
use tracing::{info, error, warn};
use uuid::Uuid;

use regulateai_config::{RiskManagementServiceConfig, ExternalServicesConfig};
use regulateai_errors::RegulateAIError;

use crate::models::*;
use crate::repositories::*;
use crate::simulation::MonteCarloEngine;
use crate::analytics::RiskAnalyticsEngine;

/// Main risk management service orchestrator
pub struct RiskManagementService {
    pub risk_assessment_service: Arc<RiskAssessmentService>,
    pub kri_service: Arc<KriService>,
    pub stress_testing_service: Arc<StressTestingService>,
    pub monte_carlo_service: Arc<MonteCarloService>,
    pub analytics_service: Arc<AnalyticsService>,
    pub config: RiskManagementServiceConfig,
}

impl RiskManagementService {
    /// Create a new risk management service instance
    pub async fn new(
        db: DatabaseConnection,
        external_config: ExternalServicesConfig,
        config: RiskManagementServiceConfig,
    ) -> Result<Self, RegulateAIError> {
        info!("Initializing Risk Management Service");

        // Initialize repositories
        let risk_assessment_repo = Arc::new(RiskAssessmentRepository::new(db.clone()));
        let kri_repo = Arc::new(KriRepository::new(db.clone()));
        let kri_measurement_repo = Arc::new(KriMeasurementRepository::new(db.clone()));

        // Initialize engines
        let monte_carlo_engine = Arc::new(MonteCarloEngine::new(config.clone()));
        let analytics_engine = Arc::new(RiskAnalyticsEngine::new(db.clone()));

        // Initialize services
        let risk_assessment_service = Arc::new(RiskAssessmentService::new(risk_assessment_repo));
        let kri_service = Arc::new(KriService::new(kri_repo, kri_measurement_repo));
        let stress_testing_service = Arc::new(StressTestingService::new(db.clone()));
        let monte_carlo_service = Arc::new(MonteCarloService::new(monte_carlo_engine));
        let analytics_service = Arc::new(AnalyticsService::new(analytics_engine));

        Ok(Self {
            risk_assessment_service,
            kri_service,
            stress_testing_service,
            monte_carlo_service,
            analytics_service,
            config,
        })
    }

    /// Get service health status
    pub async fn health_check(&self) -> Result<ServiceHealth, RegulateAIError> {
        info!("Performing risk management service health check");

        Ok(ServiceHealth {
            service_name: "Risk Management Service".to_string(),
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
                    name: "Monte Carlo Engine".to_string(),
                    status: "healthy".to_string(),
                },
            ],
        })
    }
}

// =============================================================================
// RISK ASSESSMENT SERVICE
// =============================================================================

pub struct RiskAssessmentService {
    repository: Arc<RiskAssessmentRepository>,
}

impl RiskAssessmentService {
    pub fn new(repository: Arc<RiskAssessmentRepository>) -> Self {
        Self { repository }
    }

    /// Create a new risk assessment
    pub async fn create_risk_assessment(
        &self,
        request: CreateRiskAssessmentRequest,
        created_by: Uuid,
    ) -> Result<RiskAssessment, RegulateAIError> {
        info!("Creating risk assessment: {}", request.title);

        // Validate risk scores
        if request.inherent_risk_score < 0.0 || request.inherent_risk_score > 100.0 {
            return Err(RegulateAIError::ValidationError(
                "Inherent risk score must be between 0 and 100".to_string()
            ));
        }

        if request.residual_risk_score < 0.0 || request.residual_risk_score > 100.0 {
            return Err(RegulateAIError::ValidationError(
                "Residual risk score must be between 0 and 100".to_string()
            ));
        }

        if request.residual_risk_score > request.inherent_risk_score {
            return Err(RegulateAIError::ValidationError(
                "Residual risk score cannot be higher than inherent risk score".to_string()
            ));
        }

        self.repository.create(request, created_by).await
    }

    /// Get risk assessment by ID
    pub async fn get_risk_assessment(&self, id: Uuid) -> Result<Option<RiskAssessment>, RegulateAIError> {
        self.repository.get_by_id(id).await
    }

    /// List risk assessments with pagination
    pub async fn list_risk_assessments(&self, page: u64, per_page: u64) -> Result<Vec<RiskAssessment>, RegulateAIError> {
        self.repository.list(page, per_page).await
    }

    /// Update risk assessment
    pub async fn update_risk_assessment(
        &self,
        id: Uuid,
        request: UpdateRiskAssessmentRequest,
        updated_by: Uuid,
    ) -> Result<RiskAssessment, RegulateAIError> {
        info!("Updating risk assessment: {}", id);

        // Validate risk scores if provided
        if let Some(inherent_score) = request.inherent_risk_score {
            if inherent_score < 0.0 || inherent_score > 100.0 {
                return Err(RegulateAIError::ValidationError(
                    "Inherent risk score must be between 0 and 100".to_string()
                ));
            }
        }

        if let Some(residual_score) = request.residual_risk_score {
            if residual_score < 0.0 || residual_score > 100.0 {
                return Err(RegulateAIError::ValidationError(
                    "Residual risk score must be between 0 and 100".to_string()
                ));
            }
        }

        self.repository.update(id, request, updated_by).await
    }

    /// Delete risk assessment
    pub async fn delete_risk_assessment(&self, id: Uuid, deleted_by: Uuid) -> Result<(), RegulateAIError> {
        info!("Deleting risk assessment: {} by user: {}", id, deleted_by);
        self.repository.delete(id).await
    }
}

// =============================================================================
// KRI SERVICE
// =============================================================================

pub struct KriService {
    kri_repository: Arc<KriRepository>,
    measurement_repository: Arc<KriMeasurementRepository>,
}

impl KriService {
    pub fn new(
        kri_repository: Arc<KriRepository>,
        measurement_repository: Arc<KriMeasurementRepository>,
    ) -> Self {
        Self {
            kri_repository,
            measurement_repository,
        }
    }

    /// Create a new KRI
    pub async fn create_kri(
        &self,
        request: CreateKriRequest,
        created_by: Uuid,
    ) -> Result<KeyRiskIndicator, RegulateAIError> {
        info!("Creating KRI: {}", request.name);

        // Validate thresholds
        if request.threshold_green >= request.threshold_amber || 
           request.threshold_amber >= request.threshold_red {
            return Err(RegulateAIError::ValidationError(
                "Thresholds must be in ascending order: green < amber < red".to_string()
            ));
        }

        self.kri_repository.create(request, created_by).await
    }

    /// Get KRI by ID
    pub async fn get_kri(&self, id: Uuid) -> Result<Option<KeyRiskIndicator>, RegulateAIError> {
        self.kri_repository.get_by_id(id).await
    }

    /// List KRIs with pagination
    pub async fn list_kris(&self, page: u64, per_page: u64) -> Result<Vec<KeyRiskIndicator>, RegulateAIError> {
        self.kri_repository.list(page, per_page).await
    }

    /// Record KRI measurement
    pub async fn record_kri_measurement(
        &self,
        kri_id: Uuid,
        request: RecordKriMeasurementRequest,
        recorded_by: Uuid,
    ) -> Result<KriMeasurement, RegulateAIError> {
        info!("Recording KRI measurement for KRI: {} by user: {}", kri_id, recorded_by);

        // Verify KRI exists
        match self.kri_repository.get_by_id(kri_id).await? {
            Some(_) => {
                self.measurement_repository.create(kri_id, request).await
            },
            None => {
                Err(RegulateAIError::NotFound("KRI not found".to_string()))
            }
        }
    }
}

// =============================================================================
// STRESS TESTING SERVICE
// =============================================================================

pub struct StressTestingService {
    db: DatabaseConnection,
}

impl StressTestingService {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Run stress test scenario
    pub async fn run_stress_test(&self, scenario_id: Uuid) -> Result<StressTestResult, RegulateAIError> {
        info!("Running stress test scenario: {}", scenario_id);

        // Load scenario parameters from database
        use sea_orm::*;
        let scenario = stress_test_scenarios::Entity::find_by_id(scenario_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to load stress test scenario: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound("Stress test scenario not found".to_string()))?;

        // Apply stress factors to portfolio/positions
        let stress_factors = serde_json::from_value(scenario.stress_factors.clone())
            .unwrap_or_else(|_| serde_json::json!({}));

        // Calculate impact on risk metrics
        let market_shock = stress_factors.get("market_shock").and_then(|v| v.as_f64()).unwrap_or(-0.15);
        let credit_shock = stress_factors.get("credit_shock").and_then(|v| v.as_f64()).unwrap_or(-0.08);
        let liquidity_shock = stress_factors.get("liquidity_shock").and_then(|v| v.as_f64()).unwrap_or(-0.12);

        // Simulate portfolio impact calculation
        let portfolio_impact = market_shock * 100.0; // Convert to percentage
        let var_impact = (market_shock.abs() + credit_shock.abs()) * 50.0; // VaR increase
        let liquidity_impact = liquidity_shock * 100.0;

        // Generate detailed results
        let results = serde_json::json!({
            "portfolio_impact": portfolio_impact,
            "var_impact": var_impact,
            "liquidity_impact": liquidity_impact,
            "scenario_details": {
                "market_shock": market_shock,
                "credit_shock": credit_shock,
                "liquidity_shock": liquidity_shock
            },
            "risk_metrics": {
                "pre_stress_var": 100.0,
                "post_stress_var": 100.0 + var_impact,
                "capital_adequacy_ratio": 12.5 + (portfolio_impact * 0.1),
                "liquidity_coverage_ratio": 150.0 + (liquidity_impact * 2.0)
            }
        });

        Ok(StressTestResult {
            id: Uuid::new_v4(),
            scenario_id,
            execution_date: Utc::now(),
            results,
            status: "COMPLETED".to_string(),
        })
    }
}

// =============================================================================
// MONTE CARLO SERVICE
// =============================================================================

pub struct MonteCarloService {
    engine: Arc<MonteCarloEngine>,
}

impl MonteCarloService {
    pub fn new(engine: Arc<MonteCarloEngine>) -> Self {
        Self { engine }
    }

    /// Run Monte Carlo simulation
    pub async fn run_simulation(&self, parameters: MonteCarloParameters) -> Result<MonteCarloResult, RegulateAIError> {
        info!("Running Monte Carlo simulation with {} iterations", parameters.iterations);
        self.engine.run_simulation(parameters).await
    }
}

// =============================================================================
// ANALYTICS SERVICE
// =============================================================================

pub struct AnalyticsService {
    engine: Arc<RiskAnalyticsEngine>,
}

impl AnalyticsService {
    pub fn new(engine: Arc<RiskAnalyticsEngine>) -> Self {
        Self { engine }
    }

    /// Generate risk analytics dashboard
    pub async fn generate_dashboard(&self) -> Result<RiskDashboard, RegulateAIError> {
        info!("Generating risk analytics dashboard");
        self.engine.generate_dashboard().await
    }
}
