//! RegulateAI Regulatory Compliance Service
//! 
//! This service provides comprehensive regulatory compliance capabilities including:
//! - Policy management and lifecycle
//! - Regulatory mapping and tracking
//! - Control framework implementation
//! - Audit management and evidence collection
//! - Third-party risk management (TPRM)
//! - Compliance reporting and dashboards

mod handlers;
mod models;
mod repositories;
mod services;
mod workflows;

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

use regulateai_config::{AppSettings, ComplianceServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::services::ComplianceService;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub compliance_service: Arc<ComplianceService>,
    pub auth_state: AuthState,
    pub config: ComplianceServiceConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI Compliance Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let compliance_config = settings.services.compliance.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize compliance service
    let compliance_service = Arc::new(
        ComplianceService::new(
            db_connection,
            settings.external_services.clone(),
            compliance_config.clone(),
        ).await?
    );

    // Create application state
    let app_state = AppState {
        compliance_service,
        auth_state,
        config: compliance_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", compliance_config.port);
    info!("Compliance Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Policy management endpoints
        .route("/api/v1/policies", get(handlers::list_policies))
        .route("/api/v1/policies", post(handlers::create_policy))
        .route("/api/v1/policies/:id", get(handlers::get_policy))
        .route("/api/v1/policies/:id", put(handlers::update_policy))
        .route("/api/v1/policies/:id", delete(handlers::delete_policy))
        .route("/api/v1/policies/:id/approve", post(handlers::approve_policy))
        .route("/api/v1/policies/:id/review", post(handlers::review_policy))
        
        // Control framework endpoints
        .route("/api/v1/controls", get(handlers::list_controls))
        .route("/api/v1/controls", post(handlers::create_control))
        .route("/api/v1/controls/:id", get(handlers::get_control))
        .route("/api/v1/controls/:id", put(handlers::update_control))
        .route("/api/v1/controls/:id/test", post(handlers::test_control))
        .route("/api/v1/controls/:id/evidence", post(handlers::upload_control_evidence))
        
        // Audit management endpoints
        .route("/api/v1/audits", get(handlers::list_audits))
        .route("/api/v1/audits", post(handlers::create_audit))
        .route("/api/v1/audits/:id", get(handlers::get_audit))
        .route("/api/v1/audits/:id/findings", get(handlers::get_audit_findings))
        .route("/api/v1/audits/:id/findings", post(handlers::create_audit_finding))
        .route("/api/v1/audits/:id/complete", post(handlers::complete_audit))
        
        // Third-party risk management endpoints
        .route("/api/v1/vendors", get(handlers::list_vendors))
        .route("/api/v1/vendors", post(handlers::create_vendor))
        .route("/api/v1/vendors/:id", get(handlers::get_vendor))
        .route("/api/v1/vendors/:id/assess", post(handlers::assess_vendor_risk))
        .route("/api/v1/vendors/:id/contracts", get(handlers::get_vendor_contracts))
        
        // Regulatory mapping endpoints
        .route("/api/v1/regulations", get(handlers::list_regulations))
        .route("/api/v1/regulations/:id/requirements", get(handlers::get_regulation_requirements))
        .route("/api/v1/regulations/:id/mapping", get(handlers::get_regulation_mapping))
        .route("/api/v1/regulations/:id/mapping", post(handlers::create_regulation_mapping))
        
        // Compliance reporting endpoints
        .route("/api/v1/reports/compliance-dashboard", get(handlers::get_compliance_dashboard))
        .route("/api/v1/reports/control-effectiveness", get(handlers::get_control_effectiveness_report))
        .route("/api/v1/reports/audit-summary", get(handlers::get_audit_summary_report))
        .route("/api/v1/reports/vendor-risk", get(handlers::get_vendor_risk_report))
        
        // Workflow endpoints
        .route("/api/v1/workflows", get(handlers::list_workflows))
        .route("/api/v1/workflows/:id/execute", post(handlers::execute_workflow))
        .route("/api/v1/workflows/:id/status", get(handlers::get_workflow_status))
        
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
        "service": "compliance",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "capabilities": {
            "policy_management": true,
            "control_framework": true,
            "audit_management": true,
            "vendor_risk_management": true,
            "regulatory_mapping": true,
            "compliance_reporting": true,
            "workflow_automation": true
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
        let compliance_config = settings.services.compliance.clone();

        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let compliance_service = Arc::new(
            ComplianceService::new(
                db_connection,
                settings.external_services.clone(),
                compliance_config.clone(),
            ).await.unwrap()
        );

        let app_state = AppState {
            compliance_service,
            auth_state,
            config: compliance_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "compliance");
        assert_eq!(health_data["status"], "healthy");
        assert!(health_data["capabilities"]["policy_management"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_service_initialization() {
        let _server = create_test_app().await;
        // If we get here without panicking, the service initialized successfully
    }
}
