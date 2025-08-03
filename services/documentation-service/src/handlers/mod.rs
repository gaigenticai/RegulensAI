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

/// User guide home page handler
pub async fn user_guide_home(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving user guide home page for user: {}", auth.user_id);

    let template_data = UserGuideHomeData {
        user: auth,
        modules: get_available_modules().await,
        quick_start_guides: get_quick_start_guides().await,
        search_enabled: true,
        recent_updates: get_recent_guide_updates().await,
    };

    match render_user_guide_home(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render user guide home: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// User guide module-specific page handler
pub async fn user_guide_module(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(module): Path<String>,
) -> Result<Html<String>, StatusCode> {
    info!("Serving user guide for module: {} by user: {}", module, auth.user_id);

    let module_data = match get_module_guide_data(&module).await {
        Ok(data) => data,
        Err(_) => return Err(StatusCode::NOT_FOUND),
    };

    let template_data = UserGuideModuleData {
        user: auth,
        module: module_data,
        workflows: get_module_workflows(&module).await,
        field_references: get_module_field_references(&module).await,
        examples: get_module_examples(&module).await,
        troubleshooting: get_module_troubleshooting(&module).await,
    };

    match render_user_guide_module(&template_data) {
        Ok(html) => Ok(Html(html)),
        Err(e) => {
            error!("Failed to render user guide module: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// Helper functions for user guide data

/// Get available modules for user guide
async fn get_available_modules() -> Vec<ModuleInfo> {
    vec![
        ModuleInfo {
            id: "aml-kyc".to_string(),
            name: "AML/KYC Module".to_string(),
            description: "Anti-Money Laundering and Know Your Customer verification workflows".to_string(),
            icon: "fas fa-user-check".to_string(),
            url: "/user-guide/aml-kyc".to_string(),
            status: "Active".to_string(),
            required_roles: vec!["aml_analyst".to_string(), "compliance_officer".to_string()],
        },
        ModuleInfo {
            id: "fraud-detection".to_string(),
            name: "Fraud Detection".to_string(),
            description: "Real-time fraud detection and prevention system".to_string(),
            icon: "fas fa-shield-alt".to_string(),
            url: "/user-guide/fraud-detection".to_string(),
            status: "Active".to_string(),
            required_roles: vec!["fraud_investigator".to_string(), "security_analyst".to_string()],
        },
        ModuleInfo {
            id: "risk-management".to_string(),
            name: "Risk Management".to_string(),
            description: "Comprehensive risk assessment and monitoring tools".to_string(),
            icon: "fas fa-chart-line".to_string(),
            url: "/user-guide/risk-management".to_string(),
            status: "Active".to_string(),
            required_roles: vec!["risk_manager".to_string(), "compliance_officer".to_string()],
        },
        ModuleInfo {
            id: "compliance".to_string(),
            name: "Compliance Management".to_string(),
            description: "Policy management and regulatory compliance tracking".to_string(),
            icon: "fas fa-clipboard-check".to_string(),
            url: "/user-guide/compliance".to_string(),
            status: "Active".to_string(),
            required_roles: vec!["compliance_officer".to_string(), "legal_counsel".to_string()],
        },
        ModuleInfo {
            id: "cybersecurity".to_string(),
            name: "Cybersecurity".to_string(),
            description: "Vulnerability assessment and security monitoring".to_string(),
            icon: "fas fa-lock".to_string(),
            url: "/user-guide/cybersecurity".to_string(),
            status: "Active".to_string(),
            required_roles: vec!["security_analyst".to_string(), "system_admin".to_string()],
        },
        ModuleInfo {
            id: "ai-orchestration".to_string(),
            name: "AI Orchestration".to_string(),
            description: "AI-powered regulatory Q&A and automation".to_string(),
            icon: "fas fa-robot".to_string(),
            url: "/user-guide/ai-orchestration".to_string(),
            status: "Active".to_string(),
            required_roles: vec!["compliance_officer".to_string(), "risk_manager".to_string()],
        },
    ]
}

/// Get quick start guides
async fn get_quick_start_guides() -> Vec<QuickStartGuide> {
    vec![
        QuickStartGuide {
            id: "first-login".to_string(),
            title: "First Time Login".to_string(),
            description: "Complete your first login and setup your profile".to_string(),
            estimated_time: 10,
            steps: vec![
                GuideStep {
                    step_number: 1,
                    title: "Access the Platform".to_string(),
                    content: "Navigate to the RegulateAI platform URL and enter your credentials".to_string(),
                    code_examples: vec![],
                    related_links: vec![],
                },
                GuideStep {
                    step_number: 2,
                    title: "Complete Profile Setup".to_string(),
                    content: "Fill in your profile information and set notification preferences".to_string(),
                    code_examples: vec![],
                    related_links: vec![],
                },
            ],
            required_role: "any".to_string(),
        },
        QuickStartGuide {
            id: "customer-onboarding".to_string(),
            title: "Customer Onboarding".to_string(),
            description: "Learn how to onboard a new customer with KYC verification".to_string(),
            estimated_time: 15,
            steps: vec![
                GuideStep {
                    step_number: 1,
                    title: "Navigate to AML Module".to_string(),
                    content: "Access the AML/KYC module from the main navigation".to_string(),
                    code_examples: vec![],
                    related_links: vec![],
                },
                GuideStep {
                    step_number: 2,
                    title: "Start Customer Verification".to_string(),
                    content: "Click 'New Customer Verification' and select customer type".to_string(),
                    code_examples: vec![],
                    related_links: vec![],
                },
            ],
            required_role: "aml_analyst".to_string(),
        },
    ]
}

/// Get recent guide updates
async fn get_recent_guide_updates() -> Vec<GuideUpdate> {
    vec![
        GuideUpdate {
            title: "Enhanced Fraud Detection Workflows".to_string(),
            description: "Updated fraud detection module with new ML models and investigation workflows".to_string(),
            updated_at: chrono::Utc::now() - chrono::Duration::days(2),
            module: "fraud-detection".to_string(),
            update_type: "Feature Enhancement".to_string(),
        },
        GuideUpdate {
            title: "New Risk Assessment Templates".to_string(),
            description: "Added pre-built risk assessment templates for common scenarios".to_string(),
            updated_at: chrono::Utc::now() - chrono::Duration::days(5),
            module: "risk-management".to_string(),
            update_type: "New Feature".to_string(),
        },
    ]
}

/// Get module guide data
async fn get_module_guide_data(module: &str) -> Result<ModuleGuideData, RegulateAIError> {
    match module {
        "aml-kyc" => Ok(ModuleGuideData {
            id: "aml-kyc".to_string(),
            name: "AML/KYC Module".to_string(),
            description: "Comprehensive Anti-Money Laundering and Know Your Customer verification system".to_string(),
            overview: "The AML/KYC module provides complete customer onboarding workflows, transaction monitoring, sanctions screening, and regulatory reporting capabilities.".to_string(),
            getting_started: "Begin by navigating to the AML module and selecting 'New Customer Verification' to start the onboarding process.".to_string(),
            key_features: vec![
                "Customer identity verification".to_string(),
                "Document verification with OCR".to_string(),
                "Real-time sanctions screening".to_string(),
                "Transaction monitoring and alerts".to_string(),
                "Suspicious activity reporting (SAR)".to_string(),
                "Case management and investigation".to_string(),
            ],
            prerequisites: vec![
                "Valid user account with AML analyst role".to_string(),
                "Access to customer data sources".to_string(),
                "Understanding of AML regulations".to_string(),
            ],
        }),
        "fraud-detection" => Ok(ModuleGuideData {
            id: "fraud-detection".to_string(),
            name: "Fraud Detection Module".to_string(),
            description: "Advanced machine learning-powered fraud detection and prevention system".to_string(),
            overview: "The Fraud Detection module uses advanced ML algorithms to detect fraudulent transactions in real-time, providing investigation tools and case management capabilities.".to_string(),
            getting_started: "Access the fraud detection dashboard to view real-time alerts and begin investigating suspicious transactions.".to_string(),
            key_features: vec![
                "Real-time transaction analysis".to_string(),
                "Machine learning fraud models".to_string(),
                "Behavioral analytics".to_string(),
                "Investigation workflows".to_string(),
                "False positive management".to_string(),
                "Performance analytics".to_string(),
            ],
            prerequisites: vec![
                "Fraud investigator role access".to_string(),
                "Understanding of fraud patterns".to_string(),
                "Transaction data access".to_string(),
            ],
        }),
        "risk-management" => Ok(ModuleGuideData {
            id: "risk-management".to_string(),
            name: "Risk Management Module".to_string(),
            description: "Comprehensive enterprise risk assessment and monitoring platform".to_string(),
            overview: "The Risk Management module provides tools for risk identification, assessment, monitoring, and reporting with advanced analytics and simulation capabilities.".to_string(),
            getting_started: "Create your first risk assessment by navigating to Risk Management and selecting 'New Risk Assessment'.".to_string(),
            key_features: vec![
                "Risk assessment creation".to_string(),
                "Monte Carlo simulations".to_string(),
                "Key Risk Indicator (KRI) monitoring".to_string(),
                "Stress testing scenarios".to_string(),
                "Risk reporting and dashboards".to_string(),
                "Control effectiveness tracking".to_string(),
            ],
            prerequisites: vec![
                "Risk manager role access".to_string(),
                "Understanding of risk management principles".to_string(),
                "Access to relevant business data".to_string(),
            ],
        }),
        "compliance" => Ok(ModuleGuideData {
            id: "compliance".to_string(),
            name: "Compliance Management Module".to_string(),
            description: "Policy management and regulatory compliance tracking system".to_string(),
            overview: "The Compliance module manages organizational policies, tracks regulatory obligations, and provides comprehensive compliance monitoring and reporting.".to_string(),
            getting_started: "Begin by reviewing existing policies or creating new ones using the policy management interface.".to_string(),
            key_features: vec![
                "Policy lifecycle management".to_string(),
                "Regulatory obligation tracking".to_string(),
                "Compliance monitoring".to_string(),
                "Audit trail management".to_string(),
                "Regulatory reporting".to_string(),
                "Third-party risk management".to_string(),
            ],
            prerequisites: vec![
                "Compliance officer role access".to_string(),
                "Knowledge of applicable regulations".to_string(),
                "Understanding of organizational policies".to_string(),
            ],
        }),
        "cybersecurity" => Ok(ModuleGuideData {
            id: "cybersecurity".to_string(),
            name: "Cybersecurity Module".to_string(),
            description: "Comprehensive cybersecurity assessment and monitoring platform".to_string(),
            overview: "The Cybersecurity module provides vulnerability assessment, security monitoring, incident management, and compliance tracking capabilities.".to_string(),
            getting_started: "Start with a vulnerability assessment by navigating to the Cybersecurity module and selecting 'New Assessment'.".to_string(),
            key_features: vec![
                "Vulnerability assessments".to_string(),
                "Security monitoring".to_string(),
                "Incident response management".to_string(),
                "Compliance tracking".to_string(),
                "Threat intelligence integration".to_string(),
                "Security metrics and reporting".to_string(),
            ],
            prerequisites: vec![
                "Security analyst role access".to_string(),
                "Understanding of cybersecurity principles".to_string(),
                "Access to system and network data".to_string(),
            ],
        }),
        "ai-orchestration" => Ok(ModuleGuideData {
            id: "ai-orchestration".to_string(),
            name: "AI Orchestration Module".to_string(),
            description: "AI-powered regulatory assistance and automation platform".to_string(),
            overview: "The AI Orchestration module provides intelligent regulatory Q&A, requirement mapping, and automated compliance assistance using advanced AI models.".to_string(),
            getting_started: "Ask your first regulatory question using the Q&A interface to experience AI-powered compliance assistance.".to_string(),
            key_features: vec![
                "Regulatory Q&A system".to_string(),
                "Requirement-to-control mapping".to_string(),
                "Automated compliance recommendations".to_string(),
                "Context-aware search".to_string(),
                "Multi-jurisdiction support".to_string(),
                "Natural language processing".to_string(),
            ],
            prerequisites: vec![
                "Compliance officer or risk manager role".to_string(),
                "Understanding of regulatory frameworks".to_string(),
                "Basic knowledge of AI capabilities".to_string(),
            ],
        }),
        _ => Err(RegulateAIError::NotFound(format!("Module '{}' not found", module))),
    }
}

/// Get module workflows
async fn get_module_workflows(module: &str) -> Vec<WorkflowGuide> {
    match module {
        "aml-kyc" => vec![
            WorkflowGuide {
                id: "customer-onboarding".to_string(),
                title: "Customer Onboarding Workflow".to_string(),
                description: "Complete workflow for onboarding new customers with KYC verification".to_string(),
                steps: vec![
                    WorkflowStep {
                        step_number: 1,
                        title: "Initiate KYC Process".to_string(),
                        description: "Start the customer verification process".to_string(),
                        instructions: "Navigate to AML Module → Customer Onboarding → New Customer Verification".to_string(),
                        screenshot_url: Some("/static/images/kyc-step1.png".to_string()),
                        tips: vec!["Ensure you have all required customer documents before starting".to_string()],
                        expected_outcome: "KYC verification process initiated with unique case ID".to_string(),
                    },
                    WorkflowStep {
                        step_number: 2,
                        title: "Enter Customer Information".to_string(),
                        description: "Input basic customer details and select verification type".to_string(),
                        instructions: "Fill in customer name, date of birth, nationality, and select Individual/Corporate".to_string(),
                        screenshot_url: Some("/static/images/kyc-step2.png".to_string()),
                        tips: vec![
                            "Use exact names as they appear on government-issued ID".to_string(),
                            "Double-check date format (YYYY-MM-DD)".to_string(),
                        ],
                        expected_outcome: "Customer profile created with basic information".to_string(),
                    },
                    WorkflowStep {
                        step_number: 3,
                        title: "Document Upload and Verification".to_string(),
                        description: "Upload and verify customer identification documents".to_string(),
                        instructions: "Upload government-issued ID, proof of address, and any additional required documents".to_string(),
                        screenshot_url: Some("/static/images/kyc-step3.png".to_string()),
                        tips: vec![
                            "Ensure documents are clear and all corners are visible".to_string(),
                            "Accepted formats: PDF, JPG, PNG (max 10MB)".to_string(),
                        ],
                        expected_outcome: "Documents uploaded and OCR extraction completed".to_string(),
                    },
                ],
                estimated_time: 20,
                required_permissions: vec!["aml_analyst".to_string(), "kyc_verification".to_string()],
            },
        ],
        "fraud-detection" => vec![
            WorkflowGuide {
                id: "fraud-investigation".to_string(),
                title: "Fraud Alert Investigation".to_string(),
                description: "Step-by-step process for investigating fraud alerts".to_string(),
                steps: vec![
                    WorkflowStep {
                        step_number: 1,
                        title: "Review Alert Details".to_string(),
                        description: "Examine the fraud alert and associated transaction data".to_string(),
                        instructions: "Click on the alert from the queue and review risk factors, transaction details, and customer history".to_string(),
                        screenshot_url: Some("/static/images/fraud-step1.png".to_string()),
                        tips: vec!["Pay attention to risk score and triggering rules".to_string()],
                        expected_outcome: "Understanding of alert context and risk factors".to_string(),
                    },
                ],
                estimated_time: 15,
                required_permissions: vec!["fraud_investigator".to_string()],
            },
        ],
        _ => vec![],
    }
}

/// Get module field references
async fn get_module_field_references(module: &str) -> Vec<FieldReference> {
    match module {
        "aml-kyc" => vec![
            FieldReference {
                field_name: "first_name".to_string(),
                field_type: "String".to_string(),
                description: "Customer's legal first name as it appears on government-issued identification".to_string(),
                required: true,
                validation_rules: vec![
                    "Maximum 100 characters".to_string(),
                    "Letters and spaces only".to_string(),
                    "Cannot be empty".to_string(),
                ],
                example_values: vec!["John".to_string(), "Mary Jane".to_string(), "José".to_string()],
                related_fields: vec!["last_name".to_string(), "full_name".to_string()],
            },
            FieldReference {
                field_name: "date_of_birth".to_string(),
                field_type: "Date".to_string(),
                description: "Customer's date of birth used for age verification and risk assessment".to_string(),
                required: true,
                validation_rules: vec![
                    "Format: YYYY-MM-DD".to_string(),
                    "Must be 18+ years ago".to_string(),
                    "Cannot be future date".to_string(),
                ],
                example_values: vec!["1985-03-15".to_string(), "1990-12-01".to_string()],
                related_fields: vec!["age".to_string(), "risk_rating".to_string()],
            },
            FieldReference {
                field_name: "risk_rating".to_string(),
                field_type: "Enum".to_string(),
                description: "Calculated customer risk level based on multiple factors".to_string(),
                required: false,
                validation_rules: vec![
                    "Values: LOW, MEDIUM, HIGH, VERY_HIGH".to_string(),
                    "Auto-calculated by system".to_string(),
                ],
                example_values: vec!["LOW".to_string(), "MEDIUM".to_string(), "HIGH".to_string()],
                related_fields: vec!["kyc_status".to_string(), "enhanced_dd_required".to_string()],
            },
        ],
        _ => vec![],
    }
}

/// Get module examples
async fn get_module_examples(module: &str) -> Vec<UsageExample> {
    match module {
        "aml-kyc" => vec![
            UsageExample {
                title: "Customer Onboarding API Call".to_string(),
                description: "Example API request for initiating customer KYC verification".to_string(),
                code: r#"{
  "customer_type": "INDIVIDUAL",
  "first_name": "John",
  "last_name": "Smith",
  "date_of_birth": "1985-03-15",
  "nationality": "USA",
  "id_document_type": "PASSPORT",
  "id_document_number": "123456789"
}"#.to_string(),
                language: "json".to_string(),
                expected_output: Some(r#"{
  "customer_id": "uuid-here",
  "kyc_status": "PENDING",
  "verification_id": "verification-uuid"
}"#.to_string()),
                notes: vec![
                    "All fields are required for individual customers".to_string(),
                    "Document number must match uploaded document".to_string(),
                ],
            },
        ],
        _ => vec![],
    }
}

/// Get module troubleshooting
async fn get_module_troubleshooting(module: &str) -> Vec<TroubleshootingItem> {
    match module {
        "aml-kyc" => vec![
            TroubleshootingItem {
                title: "KYC Verification Stuck in Pending Status".to_string(),
                description: "Customer verification remains in PENDING status for extended period".to_string(),
                causes: vec![
                    "Missing required documents".to_string(),
                    "Poor document quality preventing OCR".to_string(),
                    "Manual review required due to high risk score".to_string(),
                ],
                solutions: vec![
                    "Check document upload status and quality".to_string(),
                    "Verify all required fields are completed".to_string(),
                    "Contact supervisor for manual review approval".to_string(),
                ],
                related_links: vec![
                    "/user-guide/aml-kyc#document-requirements".to_string(),
                    "/user-guide/aml-kyc#manual-review-process".to_string(),
                ],
                severity: "Medium".to_string(),
            },
        ],
        _ => vec![],
    }
}
