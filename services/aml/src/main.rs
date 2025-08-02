//! RegulateAI AML (Anti-Money Laundering) Service
//! 
//! This service provides comprehensive AML capabilities including:
//! - Customer Due Diligence (CDD) and Enhanced Due Diligence (EDD)
//! - Transaction monitoring and suspicious activity detection
//! - Sanctions screening against global watchlists
//! - Risk scoring and assessment
//! - Suspicious Activity Report (SAR) generation
//! - KYC (Know Your Customer) compliance

mod handlers;
mod services;
mod models;
mod repositories;
mod screening;
mod monitoring;
mod risk_scoring;
mod reporting;

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
    timeout::TimeoutLayer,
};
use tracing::{info, error};

use regulateai_config::{AppSettings, AmlServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::services::AmlService;
use crate::handlers::*;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub aml_service: Arc<AmlService>,
    pub auth_state: AuthState,
    pub config: AmlServiceConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI AML Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let aml_config = settings.services.aml.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Run migrations
    db_manager.migrate().await?;

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize AML service
    let aml_service = Arc::new(AmlService::new(
        db_connection,
        settings.external_services.clone(),
        aml_config.clone(),
    ).await?);

    // Create application state
    let app_state = AppState {
        aml_service,
        auth_state,
        config: aml_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", aml_config.port);
    info!("AML Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Customer endpoints
        .route("/api/v1/customers", post(create_customer))
        .route("/api/v1/customers/:id", get(get_customer))
        .route("/api/v1/customers/:id", put(update_customer))
        .route("/api/v1/customers", get(list_customers))
        .route("/api/v1/customers/:id/risk-assessment", post(assess_customer_risk))
        .route("/api/v1/customers/:id/kyc", post(perform_kyc))
        .route("/api/v1/customers/:id/sanctions-check", post(check_sanctions))
        
        // Transaction endpoints
        .route("/api/v1/transactions", post(create_transaction))
        .route("/api/v1/transactions/:id", get(get_transaction))
        .route("/api/v1/transactions", get(list_transactions))
        .route("/api/v1/transactions/:id/monitor", post(monitor_transaction))
        .route("/api/v1/transactions/bulk-monitor", post(bulk_monitor_transactions))
        
        // Alert endpoints
        .route("/api/v1/alerts", get(list_alerts))
        .route("/api/v1/alerts/:id", get(get_alert))
        .route("/api/v1/alerts/:id", put(update_alert))
        .route("/api/v1/alerts/:id/investigate", post(investigate_alert))
        .route("/api/v1/alerts/:id/close", post(close_alert))
        
        // Sanctions screening endpoints
        .route("/api/v1/sanctions/screen", post(screen_against_sanctions))
        .route("/api/v1/sanctions/lists", get(list_sanctions_lists))
        .route("/api/v1/sanctions/update", post(update_sanctions_lists))
        
        // Reporting endpoints
        .route("/api/v1/reports/sar", post(generate_sar))
        .route("/api/v1/reports/suspicious-activity", get(get_suspicious_activity_report))
        .route("/api/v1/reports/risk-summary", get(get_risk_summary_report))
        .route("/api/v1/reports/compliance", get(get_compliance_report))
        
        // Configuration endpoints
        .route("/api/v1/config/rules", get(get_monitoring_rules))
        .route("/api/v1/config/rules", post(create_monitoring_rule))
        .route("/api/v1/config/rules/:id", put(update_monitoring_rule))
        .route("/api/v1/config/rules/:id", delete(delete_monitoring_rule))
        
        // Metrics endpoint
        .route("/metrics", get(get_metrics))
        
        // Apply middleware
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(TimeoutLayer::new(std::time::Duration::from_secs(30)))
                .layer(CorsLayer::permissive())
                .layer(middleware::from_fn_with_state(
                    state.auth_state.clone(),
                    auth_middleware,
                ))
        )
        .with_state(state)
}

/// Health check handler
async fn health_check(State(state): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    // Check database connectivity
    let db_healthy = state.aml_service.health_check().await.unwrap_or(false);
    
    let health_status = serde_json::json!({
        "status": if db_healthy { "healthy" } else { "unhealthy" },
        "service": "aml",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "checks": {
            "database": db_healthy,
            "sanctions_api": true, // Would check external API
            "kyc_provider": true,  // Would check external API
        }
    });

    if db_healthy {
        Ok(Json(health_status))
    } else {
        Err(StatusCode::SERVICE_UNAVAILABLE)
    }
}

/// Metrics handler for Prometheus
async fn get_metrics() -> Result<String, StatusCode> {
    use prometheus::{Encoder, TextEncoder};
    
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    
    encoder.encode_to_string(&metric_families)
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;
    use axum_test::TestServer;

    async fn create_test_app() -> TestServer {
        // Create test configuration
        let settings = AppSettings::default();
        let aml_config = settings.services.aml.clone();

        // Create test database connection
        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        // Initialize test authentication
        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        // Initialize test AML service
        let aml_service = Arc::new(AmlService::new(
            db_connection,
            settings.external_services.clone(),
            aml_config.clone(),
        ).await.unwrap());

        let app_state = AppState {
            aml_service,
            auth_state,
            config: aml_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "aml");
        assert_eq!(health_data["status"], "healthy");
    }

    #[tokio::test]
    async fn test_metrics_endpoint() {
        let server = create_test_app().await;
        
        let response = server.get("/metrics").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let metrics_text = response.text();
        assert!(metrics_text.contains("# HELP"));
    }
}
