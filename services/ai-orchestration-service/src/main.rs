//! RegulateAI AI Agent Orchestration Service
//! 
//! This service provides comprehensive AI integration capabilities including:
//! - Regulatory Q&A agents with natural language processing capabilities
//! - Automated regulatory requirement to control mapping agents
//! - Self-healing control agents for automated remediation
//! - Next best action recommendation agents
//! - Dynamic workflow agents that adapt to regulatory changes
//! - Context-aware search agents for historical compliance data retrieval
//! - Multi-model AI orchestration and management
//! - Intelligent prompt engineering and optimization

mod handlers;
mod models;
mod repositories;
mod services;
mod agents;
mod nlp;
mod orchestration;

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

use regulateai_config::{AppSettings, AIOrchestrationServiceConfig};
use regulateai_database::{DatabaseManager, create_connection};
use regulateai_auth::{AuthState, JwtManager, RbacManager, auth_middleware};
use regulateai_errors::RegulateAIError;

use crate::services::AIOrchestrationService;

/// Application state shared across handlers
#[derive(Clone)]
pub struct AppState {
    pub ai_service: Arc<AIOrchestrationService>,
    pub auth_state: AuthState,
    pub config: AIOrchestrationServiceConfig,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .compact()
        .init();

    info!("Starting RegulateAI AI Orchestration Service");

    // Load configuration
    let settings = AppSettings::load()?;
    let ai_config = settings.services.ai_orchestration.clone();

    // Initialize database connection
    let mut db_manager = DatabaseManager::new(settings.database.clone());
    db_manager.connect().await?;
    let db_connection = db_manager.connection()?.clone();

    // Initialize authentication
    let jwt_manager = JwtManager::new(settings.security.clone())?;
    let mut rbac_manager = RbacManager::new();
    rbac_manager.create_default_roles()?;
    let auth_state = AuthState::new(jwt_manager, rbac_manager);

    // Initialize AI orchestration service
    let ai_service = Arc::new(
        AIOrchestrationService::new(
            db_connection,
            settings.external_services.clone(),
            ai_config.clone(),
        ).await?
    );

    // Create application state
    let app_state = AppState {
        ai_service,
        auth_state,
        config: ai_config.clone(),
    };

    // Build the application router
    let app = create_router(app_state);

    // Start the server
    let bind_address = format!("0.0.0.0:{}", ai_config.port);
    info!("AI Orchestration Service listening on {}", bind_address);

    let listener = TcpListener::bind(&bind_address).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Create the application router with all routes and middleware
fn create_router(state: AppState) -> Router {
    Router::new()
        // Health check endpoint
        .route("/health", get(health_check))
        
        // Regulatory Q&A agent endpoints
        .route("/api/v1/agents/qa/ask", post(handlers::ask_regulatory_question))
        .route("/api/v1/agents/qa/context", post(handlers::add_qa_context))
        .route("/api/v1/agents/qa/history", get(handlers::get_qa_history))
        .route("/api/v1/agents/qa/feedback", post(handlers::provide_qa_feedback))
        
        // Regulatory mapping agent endpoints
        .route("/api/v1/agents/mapping/analyze", post(handlers::analyze_regulatory_requirement))
        .route("/api/v1/agents/mapping/suggest", post(handlers::suggest_control_mapping))
        .route("/api/v1/agents/mapping/validate", post(handlers::validate_mapping))
        .route("/api/v1/agents/mapping/auto-map", post(handlers::auto_map_requirements))
        
        // Self-healing control agent endpoints
        .route("/api/v1/agents/healing/detect", post(handlers::detect_control_issues))
        .route("/api/v1/agents/healing/remediate", post(handlers::remediate_control_issue))
        .route("/api/v1/agents/healing/monitor", get(handlers::monitor_healing_actions))
        .route("/api/v1/agents/healing/rollback", post(handlers::rollback_healing_action))
        
        // Recommendation agent endpoints
        .route("/api/v1/agents/recommendations/next-action", post(handlers::get_next_best_action))
        .route("/api/v1/agents/recommendations/risk-mitigation", post(handlers::recommend_risk_mitigation))
        .route("/api/v1/agents/recommendations/compliance-improvement", post(handlers::recommend_compliance_improvement))
        .route("/api/v1/agents/recommendations/process-optimization", post(handlers::recommend_process_optimization))
        
        // Dynamic workflow agent endpoints
        .route("/api/v1/agents/workflow/adapt", post(handlers::adapt_workflow_to_changes))
        .route("/api/v1/agents/workflow/optimize", post(handlers::optimize_workflow))
        .route("/api/v1/agents/workflow/predict", post(handlers::predict_workflow_outcomes))
        .route("/api/v1/agents/workflow/generate", post(handlers::generate_workflow))
        
        // Context-aware search agent endpoints
        .route("/api/v1/agents/search/semantic", post(handlers::semantic_search))
        .route("/api/v1/agents/search/contextual", post(handlers::contextual_search))
        .route("/api/v1/agents/search/similar", post(handlers::find_similar_cases))
        .route("/api/v1/agents/search/trends", post(handlers::analyze_search_trends))
        
        // AI model management endpoints
        .route("/api/v1/models", get(handlers::list_ai_models))
        .route("/api/v1/models", post(handlers::register_ai_model))
        .route("/api/v1/models/:id", get(handlers::get_ai_model))
        .route("/api/v1/models/:id", put(handlers::update_ai_model))
        .route("/api/v1/models/:id/deploy", post(handlers::deploy_ai_model))
        .route("/api/v1/models/:id/test", post(handlers::test_ai_model))
        .route("/api/v1/models/:id/metrics", get(handlers::get_model_metrics))
        
        // Prompt management endpoints
        .route("/api/v1/prompts", get(handlers::list_prompts))
        .route("/api/v1/prompts", post(handlers::create_prompt))
        .route("/api/v1/prompts/:id", get(handlers::get_prompt))
        .route("/api/v1/prompts/:id", put(handlers::update_prompt))
        .route("/api/v1/prompts/:id/test", post(handlers::test_prompt))
        .route("/api/v1/prompts/:id/optimize", post(handlers::optimize_prompt))
        
        // Knowledge base management endpoints
        .route("/api/v1/knowledge", get(handlers::list_knowledge_items))
        .route("/api/v1/knowledge", post(handlers::add_knowledge_item))
        .route("/api/v1/knowledge/:id", get(handlers::get_knowledge_item))
        .route("/api/v1/knowledge/:id", put(handlers::update_knowledge_item))
        .route("/api/v1/knowledge/embed", post(handlers::embed_knowledge))
        .route("/api/v1/knowledge/search", post(handlers::search_knowledge))
        
        // Agent orchestration endpoints
        .route("/api/v1/orchestration/agents", get(handlers::list_active_agents))
        .route("/api/v1/orchestration/agents/:id/start", post(handlers::start_agent))
        .route("/api/v1/orchestration/agents/:id/stop", post(handlers::stop_agent))
        .route("/api/v1/orchestration/agents/:id/status", get(handlers::get_agent_status))
        .route("/api/v1/orchestration/pipeline", post(handlers::create_agent_pipeline))
        .route("/api/v1/orchestration/pipeline/:id/execute", post(handlers::execute_pipeline))
        
        // AI analytics endpoints
        .route("/api/v1/analytics/usage", get(handlers::get_ai_usage_analytics))
        .route("/api/v1/analytics/performance", get(handlers::get_ai_performance_metrics))
        .route("/api/v1/analytics/costs", get(handlers::get_ai_cost_analysis))
        .route("/api/v1/analytics/insights", get(handlers::get_ai_insights))
        
        // Configuration endpoints
        .route("/api/v1/config/providers", get(handlers::list_ai_providers))
        .route("/api/v1/config/providers", post(handlers::add_ai_provider))
        .route("/api/v1/config/providers/:id", put(handlers::update_ai_provider))
        .route("/api/v1/config/rate-limits", get(handlers::get_rate_limits))
        .route("/api/v1/config/rate-limits", put(handlers::update_rate_limits))
        
        // Reporting endpoints
        .route("/api/v1/reports/ai-dashboard", get(handlers::get_ai_dashboard))
        .route("/api/v1/reports/agent-performance", get(handlers::get_agent_performance_report))
        .route("/api/v1/reports/model-comparison", get(handlers::get_model_comparison_report))
        .route("/api/v1/reports/roi-analysis", get(handlers::get_ai_roi_analysis))
        
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
        "service": "ai-orchestration",
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": chrono::Utc::now(),
        "capabilities": {
            "regulatory_qa_agents": true,
            "automated_regulatory_mapping": true,
            "self_healing_controls": true,
            "next_best_action_recommendations": true,
            "dynamic_workflow_adaptation": true,
            "context_aware_search": true,
            "multi_model_orchestration": true,
            "natural_language_processing": true,
            "semantic_search": true,
            "knowledge_management": true,
            "prompt_optimization": true,
            "agent_pipeline_execution": true,
            "ai_analytics": true,
            "cost_optimization": true
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
        let ai_config = settings.services.ai_orchestration.clone();

        let db_connection = regulateai_database::create_test_connection().await.unwrap();

        let jwt_manager = JwtManager::new(settings.security.clone()).unwrap();
        let mut rbac_manager = RbacManager::new();
        rbac_manager.create_default_roles().unwrap();
        let auth_state = AuthState::new(jwt_manager, rbac_manager);

        let ai_service = Arc::new(
            AIOrchestrationService::new(
                db_connection,
                settings.external_services.clone(),
                ai_config.clone(),
            ).await.unwrap()
        );

        let app_state = AppState {
            ai_service,
            auth_state,
            config: ai_config,
        };

        TestServer::new(create_router(app_state)).unwrap()
    }

    #[tokio::test]
    async fn test_health_check() {
        let server = create_test_app().await;
        
        let response = server.get("/health").await;
        assert_eq!(response.status_code(), StatusCode::OK);
        
        let health_data: serde_json::Value = response.json();
        assert_eq!(health_data["service"], "ai-orchestration");
        assert_eq!(health_data["status"], "healthy");
        assert!(health_data["capabilities"]["regulatory_qa_agents"].as_bool().unwrap());
        assert!(health_data["capabilities"]["automated_regulatory_mapping"].as_bool().unwrap());
        assert!(health_data["capabilities"]["self_healing_controls"].as_bool().unwrap());
        assert!(health_data["capabilities"]["context_aware_search"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_service_initialization() {
        let _server = create_test_app().await;
        // If we get here without panicking, the service initialized successfully
    }
}
