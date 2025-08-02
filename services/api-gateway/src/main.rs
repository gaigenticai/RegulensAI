//! RegulateAI API Gateway
//! 
//! This service provides a unified entry point for all RegulateAI services including:
//! - Request routing and load balancing
//! - Authentication and authorization
//! - Rate limiting and throttling
//! - Request/response transformation
//! - Circuit breaking and fault tolerance
//! - Service discovery integration
//! - Monitoring and observability
//! - CORS and security headers

mod routing;
mod middleware;
mod discovery;
mod balancing;

use axum::{
    extract::State,
    http::StatusCode,
    middleware,
    response::Json,
    routing::{any, get},
    Router,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower::ServiceBuilder;
use tower_http::{
    cors::CorsLayer,
    trace::TraceLayer,
    compression::CompressionLayer,
};
use tracing::{info, error};

use regulateai_config::{AppSettings, APIGatewayConfig};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::routing::ServiceRouter;
use crate::middleware::{RateLimitingMiddleware, CircuitBreakerMiddleware};
use crate::discovery::ServiceDiscovery;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub service_router: Arc<ServiceRouter>,
    pub service_discovery: Arc<ServiceDiscovery>,
    pub auth_state: AuthState,
    pub config: APIGatewayConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI API Gateway");

    // Load configuration
    let settings = AppSettings::load()?;
    let gateway_config = settings.services.api_gateway.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize service discovery
    let service_discovery = Arc::new(ServiceDiscovery::new(gateway_config.clone()).await?);

    // Initialize service router
    let service_router = Arc::new(ServiceRouter::new(
        service_discovery.clone(),
        gateway_config.clone(),
    ).await?);

    // Create application state
    let app_state = AppState {
        service_router,
        service_discovery,
        auth_state,
        config: gateway_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", gateway_config.port);
    info!("API Gateway listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Gateway management endpoints
        .route("/gateway/status", get(gateway_status))
        .route("/gateway/services", get(list_services))
        .route("/gateway/metrics", get(gateway_metrics))
        
        // Catch-all route for service proxying
        .route("/*path", any(proxy_request))
        
        // Apply middleware stack
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(CompressionLayer::new())
                .layer(CorsLayer::permissive())
                .layer(middleware::from_fn_with_state(
                    state.clone(),
                    RateLimitingMiddleware::new(),
                ))
                .layer(middleware::from_fn_with_state(
                    state.clone(),
                    CircuitBreakerMiddleware::new(),
                ))
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
        "service": "api-gateway",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "capabilities": {
            "request_routing": true,
            "load_balancing": true,
            "authentication": true,
            "rate_limiting": true,
            "circuit_breaking": true,
            "service_discovery": true,
            "request_transformation": true,
            "monitoring": true,
            "cors_support": true,
            "compression": true
        }
    });

    Ok(Json(health_status))
}

/// Gateway status handler
async fn gateway_status(State(state): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    let services = state.service_discovery.get_healthy_services().await;
    
    let status = serde_json::json!({
        "gateway_status": "operational",
        "registered_services": services.len(),
        "services": services,
        "load_balancer_status": "active",
        "circuit_breaker_status": "monitoring",
        "rate_limiter_status": "active",
        "timestamp": chrono::Utc::now()
    });

    Ok(Json(status))
}

/// List registered services
async fn list_services(State(state): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    let services = state.service_discovery.get_all_services().await;
    Ok(Json(serde_json::json!({ "services": services })))
}

/// Gateway metrics handler
async fn gateway_metrics(State(state): State<AppState>) -> Result<Json<serde_json::Value>, StatusCode> {
    let metrics = serde_json::json!({
        "requests_total": 0, // Would be populated from actual metrics
        "requests_per_second": 0.0,
        "average_response_time_ms": 0.0,
        "error_rate": 0.0,
        "circuit_breaker_trips": 0,
        "rate_limit_hits": 0,
        "active_connections": 0,
        "timestamp": chrono::Utc::now()
    });

    Ok(Json(metrics))
}

/// Main request proxying handler
async fn proxy_request(
    State(state): State<AppState>,
    request: axum::extract::Request,
) -> Result<axum::response::Response, StatusCode> {
    match state.service_router.route_request(request).await {
        Ok(response) => Ok(response),
        Err(e) => {
            error!("Request routing failed: {}", e);
            Err(StatusCode::BAD_GATEWAY)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;
    use axum_test::TestServer;

    async fn create_test_app() -> TestServer {
        let settings = AppSettings::default();
        let gateway_config = settings.services.api_gateway.clone();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let service_discovery = Arc::new(ServiceDiscovery::new(gateway_config.clone()).await.unwrap());
        let service_router = Arc::new(ServiceRouter::new(
            service_discovery.clone(),
            gateway_config.clone(),
        ).await.unwrap());

        let app_state = AppState {
            service_router,
            service_discovery,
            auth_state,
            config: gateway_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "api-gateway");
        assert_eq!(health_data["status"], "healthy");
        assert!(health_data["capabilities"]["request_routing"].as_bool().unwrap());
        assert!(health_data["capabilities"]["load_balancing"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_gateway_status() {
        let server = create_test_app().await;
        
        let response = server.get("/gateway/status").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let status_data: serde_json::Value = response.json();
        assert_eq!(status_data["gateway_status"], "operational");
        assert!(status_data["registered_services"].is_number());
    }

    #[tokio::test]
    async fn test_service_initialization() {
        let _server = create_test_app().await;
        // If we get here without panicking, the service initialized successfully
    }
}
