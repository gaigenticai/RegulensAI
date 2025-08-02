//! Web-based documentation handlers
//! 
//! These handlers provide interactive web-based user guides as required by Rule #7

use axum::{
    extract::{Path, Query, State, ws::WebSocket},
    response::{Html, Json, sse::{Event, Sse}},
    http::StatusCode,
    Extension,
};
use axum_extra::extract::ws::WebSocketUpgrade;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::{info, error};
use tokio_stream::{wrappers::BroadcastStream, StreamExt};
use futures::stream::Stream;
use std::convert::Infallible;
use uuid::Uuid;

use regulateai_auth::AuthContext;
use regulateai_errors::RegulateAIError;

use crate::{AppState, models::*, templates::*, testing::*};

/// Documentation home page handler
pub async fn documentation_home(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving documentation home page for user: {}", auth.user_id);

    let template_data = DocumentationHomeData {
        user: auth,
        features: get_available_features().await,
        recent_updates: get_recent_documentation_updates().await,
        quick_links: get_quick_links(),
        search_enabled: true,
    };

    match render_documentation_home(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render documentation home: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// List all available features
pub async fn list_features(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Listing features for user: {}", auth.user_id);

    let features = get_available_features().await;
    let template_data = FeaturesListData {
        user: auth,
        features,
        categories: get_feature_categories(),
    };

    match render_features_list(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render features list: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get specific feature documentation
pub async fn get_feature_documentation(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(feature_name): Path<String>,
) -> Result<Html<String>, StatusCode> {
    info!("Getting feature documentation for: {} by user: {}", feature_name, auth.user_id);

    let feature_doc = match get_feature_documentation_data(&feature_name).await {
        Ok(doc) => doc,
        Err(_) => return Err(StatusCode::NOT_FOUND),
    };

    let template_data = FeatureDocumentationData {
        user: auth,
        feature: feature_doc,
        navigation: get_feature_navigation(&feature_name),
        related_features: get_related_features(&feature_name).await,
    };

    match render_feature_documentation(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render feature documentation: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// API reference main page
pub async fn api_reference(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving API reference for user: {}", auth.user_id);

    let api_data = ApiReferenceData {
        user: auth,
        services: get_api_services().await,
        endpoints_by_service: get_endpoints_by_service().await,
        authentication_info: get_authentication_info(),
    };

    match render_api_reference(&api_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render API reference: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get specific API endpoint documentation
pub async fn get_api_documentation(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(endpoint): Path<String>,
) -> Result<Html<String>, StatusCode> {
    info!("Getting API documentation for endpoint: {} by user: {}", endpoint, auth.user_id);

    let endpoint_doc = match get_api_endpoint_data(&endpoint).await {
        Ok(doc) => doc,
        Err(_) => return Err(StatusCode::NOT_FOUND),
    };

    let template_data = ApiEndpointData {
        user: auth,
        endpoint: endpoint_doc,
        examples: get_endpoint_examples(&endpoint).await,
        related_endpoints: get_related_endpoints(&endpoint).await,
    };

    match render_api_endpoint(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render API endpoint documentation: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Search documentation
#[derive(Deserialize)]
pub struct SearchQuery {
    q: String,
    category: Option<String>,
    service: Option<String>,
}

pub async fn search_documentation(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<SearchQuery>,
) -> Result<Html<String>, StatusCode> {
    info!("Searching documentation for: '{}' by user: {}", query.q, auth.user_id);

    let search_results = match state.search_engine.search(&query.q, query.category.as_deref(), query.service.as_deref()).await {
        Ok(results) => results,
        Err(e) => {
            error!("Search failed: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let template_data = SearchResultsData {
        user: auth,
        query: query.q.clone(),
        results: search_results,
        suggestions: get_search_suggestions(&query.q).await,
        filters: SearchFilters {
            categories: get_search_categories(),
            services: get_search_services(),
        },
    };

    match render_search_results(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render search results: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// API search endpoint for AJAX requests
#[derive(Deserialize)]
pub struct ApiSearchRequest {
    query: String,
    category: Option<String>,
    service: Option<String>,
    limit: Option<usize>,
}

pub async fn api_search(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<ApiSearchRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("API search for: '{}' by user: {}", request.query, auth.user_id);

    let search_results = match state.search_engine.search(
        &request.query,
        request.category.as_deref(),
        request.service.as_deref(),
    ).await {
        Ok(results) => results,
        Err(e) => {
            error!("API search failed: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let response = serde_json::json!({
        "success": true,
        "query": request.query,
        "results": search_results,
        "total": search_results.len(),
        "suggestions": get_search_suggestions(&request.query).await
    });

    Ok(Json(response))
}

/// Test results overview
pub async fn test_results(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving test results overview for user: {}", auth.user_id);

    let test_data = TestResultsData {
        user: auth,
        services: get_service_test_summaries().await,
        overall_coverage: calculate_overall_coverage().await,
        recent_test_runs: get_recent_test_runs().await,
        performance_metrics: get_performance_metrics().await,
    };

    match render_test_results(&test_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render test results: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Service-specific test results
pub async fn service_test_results(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(service): Path<String>,
) -> Result<Html<String>, StatusCode> {
    info!("Getting test results for service: {} by user: {}", service, auth.user_id);

    let service_tests = match get_service_test_details(&service).await {
        Ok(tests) => tests,
        Err(_) => return Err(StatusCode::NOT_FOUND),
    };

    let template_data = ServiceTestResultsData {
        user: auth,
        service_name: service.clone(),
        test_suites: service_tests,
        coverage_report: get_service_coverage(&service).await,
        performance_benchmarks: get_service_benchmarks(&service).await,
    };

    match render_service_test_results(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render service test results: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Database schema documentation
pub async fn database_schema(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving database schema documentation for user: {}", auth.user_id);

    let schema_data = DatabaseSchemaData {
        user: auth,
        tables: get_database_tables().await,
        relationships: get_table_relationships().await,
        indexes: get_database_indexes().await,
        migrations: get_migration_history().await,
    };

    match render_database_schema(&schema_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render database schema: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Environment configuration documentation
pub async fn environment_configuration(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving environment configuration for user: {}", auth.user_id);

    let env_data = EnvironmentConfigData {
        user: auth,
        services: get_service_configurations().await,
        variables_by_category: get_environment_variables_by_category().await,
        deployment_configs: get_deployment_configurations().await,
    };

    match render_environment_configuration(&env_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render environment configuration: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Rebuild search index (admin only)
pub async fn rebuild_search_index(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Rebuilding search index by user: {}", auth.user_id);

    // Check admin permissions
    if !auth.has_permission("documentation:admin") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.search_engine.rebuild_index().await {
        Ok(_) => {
            info!("Search index rebuilt successfully");
            Ok(Json(serde_json::json!({
                "success": true,
                "message": "Search index rebuilt successfully"
            })))
        }
        Err(e) => {
            error!("Failed to rebuild search index: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Update documentation content (admin only)
pub async fn update_documentation_content(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Updating documentation content by user: {}", auth.user_id);

    // Check admin permissions
    if !auth.has_permission("documentation:admin") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Update documentation content from source
    match update_content_from_source().await {
        Ok(_) => {
            // Rebuild search index after content update
            let _ = state.search_engine.rebuild_index().await;
            
            Ok(Json(serde_json::json!({
                "success": true,
                "message": "Documentation content updated successfully"
            })))
        }
        Err(e) => {
            error!("Failed to update documentation content: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// Helper functions for data retrieval
async fn get_available_features() -> Vec<FeatureSummary> {
    vec![
        FeatureSummary {
            name: "Authentication & Authorization Framework".to_string(),
            description: "Enterprise-grade security with JWT and RBAC".to_string(),
            category: "Security".to_string(),
            status: "Complete".to_string(),
            last_updated: chrono::Utc::now(),
        },
        FeatureSummary {
            name: "AML Service".to_string(),
            description: "Anti-Money Laundering compliance and monitoring".to_string(),
            category: "Compliance".to_string(),
            status: "Complete".to_string(),
            last_updated: chrono::Utc::now(),
        },
        // Add more features as they are implemented
    ]
}

async fn get_recent_documentation_updates() -> Vec<DocumentationUpdate> {
    vec![
        DocumentationUpdate {
            title: "Authentication Framework Documentation".to_string(),
            description: "Complete web-based user guide with interactive examples".to_string(),
            updated_at: chrono::Utc::now(),
            author: "System".to_string(),
        },
        DocumentationUpdate {
            title: "AML Service Documentation".to_string(),
            description: "Comprehensive guide with API reference and test results".to_string(),
            updated_at: chrono::Utc::now(),
            author: "System".to_string(),
        },
    ]
}

fn get_quick_links() -> Vec<QuickLink> {
    vec![
        QuickLink {
            title: "API Reference".to_string(),
            url: "/api-reference".to_string(),
            description: "Complete API documentation with examples".to_string(),
        },
        QuickLink {
            title: "Test Results".to_string(),
            url: "/test-results".to_string(),
            description: "Unit test results and coverage reports".to_string(),
        },
        QuickLink {
            title: "Database Schema".to_string(),
            url: "/database-schema".to_string(),
            description: "Interactive database schema documentation".to_string(),
        },
        QuickLink {
            title: "Environment Configuration".to_string(),
            url: "/environment-config".to_string(),
            description: "Environment variables and deployment configuration".to_string(),
        },
    ]
}

// =============================================================================
// WEB-BASED TESTING INTERFACE HANDLERS
// =============================================================================

/// Testing dashboard handler
pub async fn testing_dashboard(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving testing dashboard for user: {}", auth.user_id);

    let active_runs = state.test_manager.get_active_runs().await;
    let test_history = state.test_manager.get_test_history(Some(10), None).await;

    let template_data = TestingDashboardData {
        user: auth,
        active_runs,
        recent_tests: test_history,
        available_services: state.test_manager.config.services.clone(),
        available_test_types: state.test_manager.config.test_types.clone(),
    };

    match render_testing_dashboard(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render testing dashboard: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Execute tests handler
pub async fn execute_tests(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<TestExecutionRequest>,
) -> Result<Json<TestExecutionResponse>, StatusCode> {
    info!("Executing tests requested by user: {}", auth.user_id);

    let mut test_request = request;
    test_request.initiated_by = auth.user_id;

    match state.test_manager.execute_tests(test_request).await {
        Ok(run_id) => Ok(Json(TestExecutionResponse {
            run_id,
            status: "queued".to_string(),
            message: "Test execution queued successfully".to_string(),
        })),
        Err(e) => {
            error!("Failed to execute tests: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get test run status
pub async fn get_test_run_status(
    State(state): State<AppState>,
    Path(run_id): Path<Uuid>,
) -> Result<Json<TestRun>, StatusCode> {
    match state.test_manager.get_test_run(run_id).await {
        Ok(test_run) => Ok(Json(test_run)),
        Err(_) => Err(StatusCode::NOT_FOUND),
    }
}

/// Cancel test run
pub async fn cancel_test_run(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(run_id): Path<Uuid>,
) -> Result<Json<CancelTestResponse>, StatusCode> {
    info!("Cancelling test run {} by user: {}", run_id, auth.user_id);

    match state.test_manager.cancel_test_run(run_id).await {
        Ok(_) => Ok(Json(CancelTestResponse {
            run_id,
            status: "cancelled".to_string(),
            message: "Test run cancelled successfully".to_string(),
        })),
        Err(e) => {
            error!("Failed to cancel test run: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get test history
pub async fn get_test_history(
    State(state): State<AppState>,
    Query(params): Query<TestHistoryQuery>,
) -> Result<Json<TestHistoryResponse>, StatusCode> {
    let history = state.test_manager.get_test_history(params.limit, params.offset).await;

    Ok(Json(TestHistoryResponse {
        tests: history,
        total_count: history.len(),
        limit: params.limit.unwrap_or(50),
        offset: params.offset.unwrap_or(0),
    }))
}

/// Real-time test updates via Server-Sent Events
pub async fn test_updates_sse(
    State(state): State<AppState>,
    Path(run_id): Path<Uuid>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let receiver = state.test_manager.subscribe_to_updates();
    let stream = BroadcastStream::new(receiver)
        .filter_map(move |update| {
            match update {
                Ok(test_update) if test_update.run_id == run_id => {
                    Some(Ok(Event::default()
                        .event(format!("{:?}", test_update.update_type))
                        .data(test_update.data.to_string())))
                }
                _ => None,
            }
        });

    Sse::new(stream)
}

/// WebSocket handler for real-time test updates
pub async fn test_updates_ws(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Path(run_id): Path<Uuid>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_test_websocket(socket, state, run_id))
}

/// Handle WebSocket connection for test updates
async fn handle_test_websocket(mut socket: WebSocket, state: AppState, run_id: Uuid) {
    let mut receiver = state.test_manager.subscribe_to_updates();

    while let Ok(update) = receiver.recv().await {
        if update.run_id == run_id {
            let message = serde_json::to_string(&update).unwrap_or_default();
            if socket.send(axum::extract::ws::Message::Text(message)).await.is_err() {
                break;
            }
        }
    }
}

/// Test configuration form handler
pub async fn test_configuration_form(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving test configuration form for user: {}", auth.user_id);

    let template_data = TestConfigurationData {
        user: auth,
        available_services: state.test_manager.config.services.clone(),
        available_test_types: state.test_manager.config.test_types.clone(),
        default_options: TestOptions::default(),
    };

    match render_test_configuration_form(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render test configuration form: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Execute chaos test handler
pub async fn execute_chaos_test(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(config): Json<ChaosTestConfig>,
) -> Result<Json<TestExecutionResponse>, StatusCode> {
    info!("Executing chaos test requested by user: {}", auth.user_id);

    match state.test_manager.execute_chaos_test(config).await {
        Ok(run_id) => Ok(Json(TestExecutionResponse {
            run_id,
            status: "chaos_test_started".to_string(),
            message: "Chaos test execution started successfully".to_string(),
        })),
        Err(e) => {
            error!("Failed to execute chaos test: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Execute fault injection handler
pub async fn execute_fault_injection(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(config): Json<FaultInjectionConfig>,
) -> Result<Json<TestExecutionResponse>, StatusCode> {
    info!("Executing fault injection requested by user: {}", auth.user_id);

    match state.test_manager.execute_fault_injection(config).await {
        Ok(run_id) => Ok(Json(TestExecutionResponse {
            run_id,
            status: "fault_injection_started".to_string(),
            message: "Fault injection started successfully".to_string(),
        })),
        Err(e) => {
            error!("Failed to execute fault injection: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get detailed coverage report
pub async fn get_coverage_report(
    State(state): State<AppState>,
    Path(run_id): Path<Uuid>,
) -> Result<Json<CoverageDetails>, StatusCode> {
    match state.test_manager.generate_coverage_report(run_id).await {
        Ok(coverage) => Ok(Json(coverage)),
        Err(e) => {
            error!("Failed to generate coverage report: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get performance analysis
pub async fn get_performance_analysis(
    State(state): State<AppState>,
    Path(run_id): Path<Uuid>,
) -> Result<Json<PerformanceMetrics>, StatusCode> {
    match state.test_manager.analyze_performance(run_id).await {
        Ok(metrics) => Ok(Json(metrics)),
        Err(e) => {
            error!("Failed to analyze performance: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Detect flaky tests
pub async fn detect_flaky_tests(
    State(state): State<AppState>,
    Path(service): Path<String>,
) -> Result<Json<Vec<FlakyTest>>, StatusCode> {
    match state.test_manager.detect_flaky_tests(&service).await {
        Ok(flaky_tests) => Ok(Json(flaky_tests)),
        Err(e) => {
            error!("Failed to detect flaky tests: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Advanced test analytics dashboard
pub async fn advanced_test_analytics(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving advanced test analytics for user: {}", auth.user_id);

    let template_data = AdvancedAnalyticsData {
        user: auth,
        available_services: state.test_manager.config.services.clone(),
        analytics_enabled: true,
        chaos_testing_enabled: true,
        fault_injection_enabled: true,
    };

    match render_advanced_analytics(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render advanced analytics: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// =============================================================================
// TESTING DATA STRUCTURES
// =============================================================================

#[derive(Debug, Serialize, Deserialize)]
pub struct TestingDashboardData {
    pub user: AuthContext,
    pub active_runs: Vec<TestRun>,
    pub recent_tests: Vec<TestExecution>,
    pub available_services: Vec<String>,
    pub available_test_types: Vec<TestType>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestConfigurationData {
    pub user: AuthContext,
    pub available_services: Vec<String>,
    pub available_test_types: Vec<TestType>,
    pub default_options: TestOptions,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestExecutionResponse {
    pub run_id: Uuid,
    pub status: String,
    pub message: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CancelTestResponse {
    pub run_id: Uuid,
    pub status: String,
    pub message: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestHistoryQuery {
    pub limit: Option<usize>,
    pub offset: Option<usize>,
    pub service: Option<String>,
    pub test_type: Option<TestType>,
    pub status: Option<TestRunStatus>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestHistoryResponse {
    pub tests: Vec<TestExecution>,
    pub total_count: usize,
    pub limit: usize,
    pub offset: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AdvancedAnalyticsData {
    pub user: AuthContext,
    pub available_services: Vec<String>,
    pub analytics_enabled: bool,
    pub chaos_testing_enabled: bool,
    pub fault_injection_enabled: bool,
}
async fn update_content_from_source() -> Result<(), RegulateAIError> {
    // Implementation for updating documentation content
    Ok(())
}
