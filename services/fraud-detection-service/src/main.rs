//! RegulateAI Fraud Detection & Prevention Service
//! 
//! This service provides comprehensive fraud detection capabilities including:
//! - Real-time transaction fraud detection with advanced ML models
//! - Identity fraud detection including synthetic ID and document forgery
//! - Application fraud detection for falsified documents and credit mule patterns
//! - First-party fraud detection for intentional defaults and loan stacking
//! - Internal/insider fraud monitoring with employee behavior analysis
//! - Graph-based anomaly detection for complex fraud networks
//! - Device fingerprinting and behavioral analytics
//! - Machine learning model integration for pattern recognition

mod handlers;
mod models;
mod repositories;
mod services;
mod ml;
mod graph;
mod analytics;

use axum::{
    extract::State,
    http::StatusCode,
    middleware,
    response::Json,
    routing::{get, post, put},
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

use regulateai_config::{AppSettings, FraudDetectionServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::services::FraudDetectionService;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub fraud_service: Arc<FraudDetectionService>,
    pub auth_state: AuthState,
    pub config: FraudDetectionServiceConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI Fraud Detection Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let fraud_config = settings.services.fraud_detection.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize fraud detection service
    let fraud_service = Arc::new(
        FraudDetectionService::new(
            db_connection,
            settings.external_services.clone(),
            fraud_config.clone(),
        ).await?
    );

    // Create application state
    let app_state = AppState {
        fraud_service,
        auth_state,
        config: fraud_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", fraud_config.port);
    info!("Fraud Detection Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Real-time fraud detection endpoints
        .route("/api/v1/detect/transaction", post(handlers::detect_transaction_fraud))
        .route("/api/v1/detect/identity", post(handlers::detect_identity_fraud))
        .route("/api/v1/detect/application", post(handlers::detect_application_fraud))
        .route("/api/v1/detect/first-party", post(handlers::detect_first_party_fraud))
        .route("/api/v1/detect/insider", post(handlers::detect_insider_fraud))
        
        // Fraud case management endpoints
        .route("/api/v1/cases", get(handlers::list_fraud_cases))
        .route("/api/v1/cases", post(handlers::create_fraud_case))
        .route("/api/v1/cases/:id", get(handlers::get_fraud_case))
        .route("/api/v1/cases/:id", put(handlers::update_fraud_case))
        .route("/api/v1/cases/:id/investigate", post(handlers::investigate_fraud_case))
        .route("/api/v1/cases/:id/close", post(handlers::close_fraud_case))
        
        // Alert management endpoints
        .route("/api/v1/alerts", get(handlers::list_fraud_alerts))
        .route("/api/v1/alerts/:id", get(handlers::get_fraud_alert))
        .route("/api/v1/alerts/:id/acknowledge", post(handlers::acknowledge_alert))
        .route("/api/v1/alerts/:id/escalate", post(handlers::escalate_alert))
        
        // Rule management endpoints
        .route("/api/v1/rules", get(handlers::list_fraud_rules))
        .route("/api/v1/rules", post(handlers::create_fraud_rule))
        .route("/api/v1/rules/:id", get(handlers::get_fraud_rule))
        .route("/api/v1/rules/:id", put(handlers::update_fraud_rule))
        .route("/api/v1/rules/:id/test", post(handlers::test_fraud_rule))
        
        // Model management endpoints
        .route("/api/v1/models", get(handlers::list_fraud_models))
        .route("/api/v1/models", post(handlers::create_fraud_model))
        .route("/api/v1/models/:id", get(handlers::get_fraud_model))
        .route("/api/v1/models/:id/train", post(handlers::train_fraud_model))
        .route("/api/v1/models/:id/evaluate", post(handlers::evaluate_fraud_model))
        .route("/api/v1/models/:id/deploy", post(handlers::deploy_fraud_model))
        
        // Device fingerprinting endpoints
        .route("/api/v1/devices", get(handlers::list_devices))
        .route("/api/v1/devices/:id", get(handlers::get_device))
        .route("/api/v1/devices/:id/risk-score", get(handlers::get_device_risk_score))
        .route("/api/v1/devices/fingerprint", post(handlers::create_device_fingerprint))
        
        // Behavioral analytics endpoints
        .route("/api/v1/behavior/profile", post(handlers::create_behavior_profile))
        .route("/api/v1/behavior/analyze", post(handlers::analyze_behavior))
        .route("/api/v1/behavior/anomalies", get(handlers::get_behavior_anomalies))
        
        // Graph analytics endpoints
        .route("/api/v1/graph/networks", get(handlers::get_fraud_networks))
        .route("/api/v1/graph/analyze", post(handlers::analyze_fraud_network))
        .route("/api/v1/graph/connections", get(handlers::get_entity_connections))
        
        // Reporting endpoints
        .route("/api/v1/reports/fraud-dashboard", get(handlers::get_fraud_dashboard))
        .route("/api/v1/reports/fraud-trends", get(handlers::get_fraud_trends))
        .route("/api/v1/reports/model-performance", get(handlers::get_model_performance_report))
        .route("/api/v1/reports/false-positive-analysis", get(handlers::get_false_positive_analysis))
        
        // Configuration endpoints
        .route("/api/v1/config/thresholds", get(handlers::get_fraud_thresholds))
        .route("/api/v1/config/thresholds", put(handlers::update_fraud_thresholds))
        .route("/api/v1/config/whitelist", get(handlers::get_whitelist))
        .route("/api/v1/config/whitelist", post(handlers::add_to_whitelist))
        .route("/api/v1/config/blacklist", get(handlers::get_blacklist))
        .route("/api/v1/config/blacklist", post(handlers::add_to_blacklist))
        
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
        "service": "fraud-detection",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "capabilities": {
            "transaction_fraud_detection": true,
            "identity_fraud_detection": true,
            "application_fraud_detection": true,
            "first_party_fraud_detection": true,
            "insider_fraud_monitoring": true,
            "graph_based_analytics": true,
            "device_fingerprinting": true,
            "behavioral_analytics": true,
            "machine_learning_models": true,
            "real_time_scoring": true,
            "fraud_case_management": true,
            "alert_management": true,
            "rule_engine": true,
            "reporting_analytics": true
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
        let fraud_config = settings.services.fraud_detection.clone();

        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let fraud_service = Arc::new(
            FraudDetectionService::new(
                db_connection,
                settings.external_services.clone(),
                fraud_config.clone(),
            ).await.unwrap()
        );

        let app_state = AppState {
            fraud_service,
            auth_state,
            config: fraud_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "fraud-detection");
        assert_eq!(health_data["status"], "healthy");
        assert!(health_data["capabilities"]["transaction_fraud_detection"].as_bool().unwrap());
        assert!(health_data["capabilities"]["machine_learning_models"].as_bool().unwrap());
        assert!(health_data["capabilities"]["graph_based_analytics"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_service_initialization() {
        let _server = create_test_app().await;
        // If we get here without panicking, the service initialized successfully
    }
}
