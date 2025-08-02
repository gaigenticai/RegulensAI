//! RegulateAI Cybersecurity & InfoSec Compliance Service
//! 
//! This service provides comprehensive cybersecurity compliance capabilities including:
//! - Vulnerability management with continuous scanning and CVE correlation
//! - Security awareness training with behavioral analysis and targeted delivery
//! - Access control and Identity & Access Management (IAM) with RBAC implementation
//! - Security incident response with automated playbooks for various threat scenarios
//! - Regulatory reporting for GDPR breach notifications and DPIAs
//! - Policy enforcement with automated security baseline checks
//! - Security monitoring and threat detection
//! - Compliance reporting and dashboards

mod handlers;
mod models;
mod repositories;
mod services;
mod scanners;
mod incident;
mod compliance;

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

use regulateai_config::{AppSettings, CybersecurityServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::services::CybersecurityService;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub cybersecurity_service: Arc<CybersecurityService>,
    pub auth_state: AuthState,
    pub config: CybersecurityServiceConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI Cybersecurity Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let cybersecurity_config = settings.services.cybersecurity.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize cybersecurity service
    let cybersecurity_service = Arc::new(
        CybersecurityService::new(
            db_connection,
            settings.external_services.clone(),
            cybersecurity_config.clone(),
        ).await?
    );

    // Create application state
    let app_state = AppState {
        cybersecurity_service,
        auth_state,
        config: cybersecurity_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", cybersecurity_config.port);
    info!("Cybersecurity Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Vulnerability management endpoints
        .route("/api/v1/vulnerabilities", get(handlers::list_vulnerabilities))
        .route("/api/v1/vulnerabilities/:id", get(handlers::get_vulnerability))
        .route("/api/v1/vulnerabilities/:id", put(handlers::update_vulnerability))
        .route("/api/v1/vulnerabilities/scan", post(handlers::initiate_vulnerability_scan))
        .route("/api/v1/vulnerabilities/import", post(handlers::import_vulnerability_data))
        
        // Asset management endpoints
        .route("/api/v1/assets", get(handlers::list_assets))
        .route("/api/v1/assets", post(handlers::create_asset))
        .route("/api/v1/assets/:id", get(handlers::get_asset))
        .route("/api/v1/assets/:id", put(handlers::update_asset))
        .route("/api/v1/assets/:id/scan", post(handlers::scan_asset))
        
        // Security incident management endpoints
        .route("/api/v1/incidents", get(handlers::list_incidents))
        .route("/api/v1/incidents", post(handlers::create_incident))
        .route("/api/v1/incidents/:id", get(handlers::get_incident))
        .route("/api/v1/incidents/:id", put(handlers::update_incident))
        .route("/api/v1/incidents/:id/respond", post(handlers::respond_to_incident))
        .route("/api/v1/incidents/:id/escalate", post(handlers::escalate_incident))
        .route("/api/v1/incidents/:id/close", post(handlers::close_incident))
        
        // Security awareness training endpoints
        .route("/api/v1/training/programs", get(handlers::list_training_programs))
        .route("/api/v1/training/programs", post(handlers::create_training_program))
        .route("/api/v1/training/programs/:id", get(handlers::get_training_program))
        .route("/api/v1/training/assignments", get(handlers::list_training_assignments))
        .route("/api/v1/training/assignments", post(handlers::assign_training))
        .route("/api/v1/training/progress", get(handlers::get_training_progress))
        .route("/api/v1/training/phishing", post(handlers::create_phishing_simulation))
        
        // Access control and IAM endpoints
        .route("/api/v1/access/users", get(handlers::list_users))
        .route("/api/v1/access/users", post(handlers::create_user))
        .route("/api/v1/access/users/:id", get(handlers::get_user))
        .route("/api/v1/access/users/:id", put(handlers::update_user))
        .route("/api/v1/access/users/:id/permissions", get(handlers::get_user_permissions))
        .route("/api/v1/access/users/:id/permissions", put(handlers::update_user_permissions))
        .route("/api/v1/access/roles", get(handlers::list_roles))
        .route("/api/v1/access/roles", post(handlers::create_role))
        .route("/api/v1/access/access-reviews", get(handlers::list_access_reviews))
        .route("/api/v1/access/access-reviews", post(handlers::initiate_access_review))
        
        // Policy management endpoints
        .route("/api/v1/policies", get(handlers::list_security_policies))
        .route("/api/v1/policies", post(handlers::create_security_policy))
        .route("/api/v1/policies/:id", get(handlers::get_security_policy))
        .route("/api/v1/policies/:id", put(handlers::update_security_policy))
        .route("/api/v1/policies/:id/enforce", post(handlers::enforce_policy))
        .route("/api/v1/policies/compliance-check", post(handlers::check_policy_compliance))
        
        // GDPR compliance endpoints
        .route("/api/v1/gdpr/data-subjects", get(handlers::list_data_subjects))
        .route("/api/v1/gdpr/data-subjects/:id", get(handlers::get_data_subject))
        .route("/api/v1/gdpr/requests", get(handlers::list_gdpr_requests))
        .route("/api/v1/gdpr/requests", post(handlers::create_gdpr_request))
        .route("/api/v1/gdpr/requests/:id", get(handlers::get_gdpr_request))
        .route("/api/v1/gdpr/requests/:id/process", post(handlers::process_gdpr_request))
        .route("/api/v1/gdpr/breach-notifications", get(handlers::list_breach_notifications))
        .route("/api/v1/gdpr/breach-notifications", post(handlers::create_breach_notification))
        .route("/api/v1/gdpr/dpia", get(handlers::list_dpias))
        .route("/api/v1/gdpr/dpia", post(handlers::create_dpia))
        
        // Security monitoring endpoints
        .route("/api/v1/monitoring/alerts", get(handlers::list_security_alerts))
        .route("/api/v1/monitoring/alerts/:id", get(handlers::get_security_alert))
        .route("/api/v1/monitoring/alerts/:id/acknowledge", post(handlers::acknowledge_alert))
        .route("/api/v1/monitoring/events", get(handlers::list_security_events))
        .route("/api/v1/monitoring/events", post(handlers::create_security_event))
        .route("/api/v1/monitoring/threats", get(handlers::list_threat_indicators))
        .route("/api/v1/monitoring/threats", post(handlers::create_threat_indicator))
        
        // Compliance reporting endpoints
        .route("/api/v1/reports/security-dashboard", get(handlers::get_security_dashboard))
        .route("/api/v1/reports/vulnerability-report", get(handlers::get_vulnerability_report))
        .route("/api/v1/reports/incident-summary", get(handlers::get_incident_summary))
        .route("/api/v1/reports/compliance-status", get(handlers::get_compliance_status))
        .route("/api/v1/reports/risk-assessment", get(handlers::get_risk_assessment_report))
        .route("/api/v1/reports/audit-log", get(handlers::get_audit_log))
        
        // Configuration endpoints
        .route("/api/v1/config/security-baselines", get(handlers::get_security_baselines))
        .route("/api/v1/config/security-baselines", put(handlers::update_security_baselines))
        .route("/api/v1/config/threat-intelligence", get(handlers::get_threat_intelligence_config))
        .route("/api/v1/config/threat-intelligence", put(handlers::update_threat_intelligence_config))
        
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
        "service": "cybersecurity",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "capabilities": {
            "vulnerability_management": true,
            "security_incident_response": true,
            "security_awareness_training": true,
            "identity_access_management": true,
            "policy_enforcement": true,
            "gdpr_compliance": true,
            "security_monitoring": true,
            "threat_detection": true,
            "compliance_reporting": true,
            "audit_logging": true,
            "risk_assessment": true,
            "security_baselines": true
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
        let cybersecurity_config = settings.services.cybersecurity.clone();

        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let cybersecurity_service = Arc::new(
            CybersecurityService::new(
                db_connection,
                settings.external_services.clone(),
                cybersecurity_config.clone(),
            ).await.unwrap()
        );

        let app_state = AppState {
            cybersecurity_service,
            auth_state,
            config: cybersecurity_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "cybersecurity");
        assert_eq!(health_data["status"], "healthy");
        assert!(health_data["capabilities"]["vulnerability_management"].as_bool().unwrap());
        assert!(health_data["capabilities"]["gdpr_compliance"].as_bool().unwrap());
        assert!(health_data["capabilities"]["security_incident_response"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_service_initialization() {
        let _server = create_test_app().await;
        // If we get here without panicking, the service initialized successfully
    }
}
