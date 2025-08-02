//! RegulateAI Web-Based Documentation Service
//! 
//! This service provides interactive web-based user guides as required by Rule #7
//! of the development standards. It includes:
//! - Interactive web interface with search functionality
//! - Feature documentation with database tables, environment variables, and API endpoints
//! - Field-by-field explanations of data structures
//! - Complete unit test results and coverage
//! - Integration with the main application for seamless user experience

mod handlers;
mod models;
mod search;
mod templates;
mod versioning;
mod indexing;
mod testing;

use axum::{
    extract::State,
    http::StatusCode,
    middleware,
    response::{Html, Json},
    routing::{get, post},
    Router,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower::ServiceBuilder;
use tower_http::{
    cors::CorsLayer,
    trace::TraceLayer,
    services::ServeDir,
};
use tracing::{info, error};

use regulateai_config::{AppSettings, DocumentationServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::search::SearchEngine;
use crate::handlers::*;
use crate::testing::{TestExecutionManager, TestConfig};

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub search_engine: Arc<SearchEngine>,
    pub auth_state: AuthState,
    pub config: DocumentationServiceConfig,
    pub db: sea_orm::DatabaseConnection,
    pub test_manager: Arc<TestExecutionManager>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI Documentation Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let doc_config = settings.services.documentation.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize search engine
    let search_engine = Arc::new(SearchEngine::new(&doc_config.search_index_path).await?);

    // Index all documentation content
    search_engine.index_documentation().await?;

    // Initialize test execution manager
    let test_config = TestConfig::default();
    let test_manager = Arc::new(TestExecutionManager::new(test_config));

    // Create application state
    let app_state = AppState {
        search_engine,
        auth_state,
        config: doc_config.clone(),
        db: db_connection,
        test_manager,
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", doc_config.port);
    info!("Documentation Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Main documentation interface
        .route("/", get(documentation_home))
        .route("/features", get(list_features))
        .route("/features/:feature_name", get(get_feature_documentation))
        .route("/api-reference", get(api_reference))
        .route("/api-reference/:endpoint", get(get_api_documentation))
        
        // Search functionality
        .route("/search", get(search_documentation))
        .route("/api/search", post(api_search))
        
        // Interactive features
        .route("/test-results", get(test_results))
        .route("/test-results/:service", get(service_test_results))
        .route("/database-schema", get(database_schema))
        .route("/environment-config", get(environment_configuration))
        
        // Admin endpoints for documentation management
        .route("/admin/rebuild-index", post(rebuild_search_index))
        .route("/admin/update-content", post(update_documentation_content))

        // Web-based testing interface
        .route("/testing", get(testing_dashboard))
        .route("/testing/config", get(test_configuration_form))
        .route("/testing/history", get(get_test_history))

        // Testing API endpoints
        .route("/api/testing/execute", post(execute_tests))
        .route("/api/testing/runs/:run_id", get(get_test_run_status))
        .route("/api/testing/runs/:run_id/cancel", post(cancel_test_run))
        .route("/api/testing/runs/:run_id/sse", get(test_updates_sse))
        .route("/api/testing/runs/:run_id/ws", get(test_updates_ws))
        .route("/api/testing/active-runs", get(|| async { Json(Vec::<String>::new()) }))
        .route("/api/testing/history", get(get_test_history))

        // Enhanced testing endpoints
        .route("/api/testing/chaos", post(execute_chaos_test))
        .route("/api/testing/fault-injection", post(execute_fault_injection))
        .route("/api/testing/coverage/:run_id", get(get_coverage_report))
        .route("/api/testing/performance/:run_id", get(get_performance_analysis))
        .route("/api/testing/flaky-tests/:service", get(detect_flaky_tests))
        .route("/testing/analytics", get(advanced_test_analytics))
        
        // Static file serving for CSS, JS, images
        .nest_service("/static", ServeDir::new("services/documentation-service/static"))
        
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
        "service": "documentation",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "features": {
            "search": true,
            "interactive_guides": true,
            "api_documentation": true,
            "test_results": true
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
        let doc_config = settings.services.documentation.clone();

        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let search_engine = Arc::new(SearchEngine::new("/tmp/test_search_index").await.unwrap());

        let app_state = AppState {
            search_engine,
            auth_state,
            config: doc_config,
            db: db_connection,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "documentation");
        assert_eq!(health_data["status"], "healthy");
    }

    #[tokio::test]
    async fn test_documentation_home() {
        let server = create_test_app().await;
        
        let response = server.get("/").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let content = response.text();
        assert!(content.contains("RegulateAI Documentation"));
    }

    #[tokio::test]
    async fn test_search_functionality() {
        let server = create_test_app().await;
        
        let response = server.get("/search?q=authentication").await;
        assert_eq!(response.status_code(), StatusCode::OK);
    }
}
