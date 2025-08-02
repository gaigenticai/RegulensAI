//! RegulateAI Enterprise Risk Management Service
//! 
//! This service provides comprehensive enterprise risk management capabilities including:
//! - Risk assessment and scoring with advanced algorithms
//! - Key Risk Indicators (KRIs) monitoring and alerting
//! - Stress testing and scenario analysis with Monte Carlo simulation
//! - Model validation framework for risk models
//! - Operational loss tracking and analysis
//! - Risk appetite framework and monitoring
//! - Advanced analytics and reporting

mod handlers;
mod models;
mod repositories;
mod services;
mod analytics;
mod simulation;

use axum::{
    extract::State,
    http::StatusCode,
    middleware,
    response::Json,
    routing::{get, post, put, delete},
    Router,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower::ServiceBuilder;
use tower_http::{
    cors::CorsLayer,
    trace::TraceLayer,
};
use tracing::{info, error};

use regulateai_config::{AppSettings, RiskManagementServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::services::RiskManagementService;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub risk_service: Arc<RiskManagementService>,
    pub auth_state: AuthState,
    pub config: RiskManagementServiceConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI Risk Management Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let risk_config = settings.services.risk_management.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize risk management service
    let risk_service = Arc::new(
        RiskManagementService::new(
            db_connection,
            settings.external_services.clone(),
            risk_config.clone(),
        ).await?
    );

    // Create application state
    let app_state = AppState {
        risk_service,
        auth_state,
        config: risk_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", risk_config.port);
    info!("Risk Management Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Risk assessment endpoints
        .route("/api/v1/risks", get(handlers::list_risks))
        .route("/api/v1/risks", post(handlers::create_risk))
        .route("/api/v1/risks/:id", get(handlers::get_risk))
        .route("/api/v1/risks/:id", put(handlers::update_risk))
        .route("/api/v1/risks/:id/assess", post(handlers::assess_risk))
        .route("/api/v1/risks/:id/mitigate", post(handlers::mitigate_risk))
        
        // Key Risk Indicators (KRIs) endpoints
        .route("/api/v1/kris", get(handlers::list_kris))
        .route("/api/v1/kris", post(handlers::create_kri))
        .route("/api/v1/kris/:id", get(handlers::get_kri))
        .route("/api/v1/kris/:id", put(handlers::update_kri))
        .route("/api/v1/kris/:id/values", get(handlers::get_kri_values))
        .route("/api/v1/kris/:id/values", post(handlers::record_kri_value))
        .route("/api/v1/kris/:id/alerts", get(handlers::get_kri_alerts))
        
        // Stress testing endpoints
        .route("/api/v1/stress-tests", get(handlers::list_stress_tests))
        .route("/api/v1/stress-tests", post(handlers::create_stress_test))
        .route("/api/v1/stress-tests/:id", get(handlers::get_stress_test))
        .route("/api/v1/stress-tests/:id/execute", post(handlers::execute_stress_test))
        .route("/api/v1/stress-tests/:id/results", get(handlers::get_stress_test_results))
        
        // Scenario analysis endpoints
        .route("/api/v1/scenarios", get(handlers::list_scenarios))
        .route("/api/v1/scenarios", post(handlers::create_scenario))
        .route("/api/v1/scenarios/:id", get(handlers::get_scenario))
        .route("/api/v1/scenarios/:id/analyze", post(handlers::analyze_scenario))
        
        // Monte Carlo simulation endpoints
        .route("/api/v1/simulations", get(handlers::list_simulations))
        .route("/api/v1/simulations", post(handlers::create_simulation))
        .route("/api/v1/simulations/:id", get(handlers::get_simulation))
        .route("/api/v1/simulations/:id/run", post(handlers::run_simulation))
        .route("/api/v1/simulations/:id/results", get(handlers::get_simulation_results))
        
        // Model validation endpoints
        .route("/api/v1/models", get(handlers::list_models))
        .route("/api/v1/models", post(handlers::create_model))
        .route("/api/v1/models/:id", get(handlers::get_model))
        .route("/api/v1/models/:id/validate", post(handlers::validate_model))
        .route("/api/v1/models/:id/backtest", post(handlers::backtest_model))
        
        // Operational loss endpoints
        .route("/api/v1/operational-losses", get(handlers::list_operational_losses))
        .route("/api/v1/operational-losses", post(handlers::create_operational_loss))
        .route("/api/v1/operational-losses/:id", get(handlers::get_operational_loss))
        .route("/api/v1/operational-losses/:id", put(handlers::update_operational_loss))
        
        // Risk appetite endpoints
        .route("/api/v1/risk-appetite", get(handlers::get_risk_appetite))
        .route("/api/v1/risk-appetite", put(handlers::update_risk_appetite))
        .route("/api/v1/risk-appetite/monitoring", get(handlers::get_risk_appetite_monitoring))
        
        // Risk reporting endpoints
        .route("/api/v1/reports/risk-dashboard", get(handlers::get_risk_dashboard))
        .route("/api/v1/reports/risk-register", get(handlers::get_risk_register_report))
        .route("/api/v1/reports/kri-summary", get(handlers::get_kri_summary_report))
        .route("/api/v1/reports/stress-test-summary", get(handlers::get_stress_test_summary))
        .route("/api/v1/reports/operational-loss-summary", get(handlers::get_operational_loss_summary))
        
        // Analytics endpoints
        .route("/api/v1/analytics/risk-trends", get(handlers::get_risk_trends))
        .route("/api/v1/analytics/correlation-analysis", get(handlers::get_correlation_analysis))
        .route("/api/v1/analytics/var-calculation", post(handlers::calculate_var))
        .route("/api/v1/analytics/expected-shortfall", post(handlers::calculate_expected_shortfall))
        
        // Apply middleware
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(CorsLayer::permissive())
                .layer(middleware::from_fn_with_state(
                    state.auth_state.clone(),
                    auth_middleware,
                ))
        )
        .with_state(state)
}

/// Health check handler
async fn health_check() -> Result<Json<serde_json::Value>, StatusCode> {
    let health_status = serde_json::json!({
        "status": "healthy",
        "service": "risk-management",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "capabilities": {
            "risk_assessment": true,
            "key_risk_indicators": true,
            "stress_testing": true,
            "scenario_analysis": true,
            "monte_carlo_simulation": true,
            "model_validation": true,
            "operational_loss_tracking": true,
            "risk_appetite_monitoring": true,
            "advanced_analytics": true,
            "risk_reporting": true
        }
    });

    Ok(Json(health_status))
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;
    use axum_test::TestServer;

    async fn create_test_app() -> TestServer {
        let settings = AppSettings::default();
        let risk_config = settings.services.risk_management.clone();

        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let risk_service = Arc::new(
            RiskManagementService::new(
                db_connection,
                settings.external_services.clone(),
                risk_config.clone(),
            ).await.unwrap()
        );

        let app_state = AppState {
            risk_service,
            auth_state,
            config: risk_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "risk-management");
        assert_eq!(health_data["status"], "healthy");
        assert!(health_data["capabilities"]["risk_assessment"].as_bool().unwrap());
        assert!(health_data["capabilities"]["monte_carlo_simulation"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_service_initialization() {
        let _server = create_test_app().await;
        // If we get here without panicking, the service initialized successfully
    }
}
