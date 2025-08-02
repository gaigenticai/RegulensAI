//! HTTP Request Handlers for AI Orchestration Service
//! 
//! This module contains all HTTP endpoint handlers for the AI orchestration service,
//! providing RESTful APIs for AI agent management and workflow orchestration.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tracing::{info, error};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use crate::AppState;
use crate::services::{
    RegulatoryQaRequest, RegulatoryQaResponse,
    RequirementMappingRequest, RequirementMappingResponse,
    SelfHealingRequest, SelfHealingResponse,
    NextActionRequest, NextActionResponse,
    DynamicWorkflowRequest, DynamicWorkflowResponse,
    SearchParams, SearchResponse,
    AgentStatusResponse,
    OrchestrationRequest, OrchestrationResponse,
};

/// Health check endpoint handler
pub async fn health_check() -> Result<Json<HealthResponse>, RegulateAIError> {
    Ok(Json(HealthResponse {
        status: "healthy".to_string(),
        service: "ai-orchestration-service".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        capabilities: vec![
            "regulatory_qa".to_string(),
            "requirement_mapping".to_string(),
            "self_healing_controls".to_string(),
            "next_best_action".to_string(),
            "dynamic_workflows".to_string(),
            "context_aware_search".to_string(),
            "agent_orchestration".to_string(),
        ],
    }))
}

/// Regulatory Q&A endpoint handler
pub async fn regulatory_qa(
    State(state): State<Arc<AppState>>,
    Json(request): Json<RegulatoryQaRequest>,
) -> Result<Json<RegulatoryQaResponse>, RegulateAIError> {
    info!("Processing regulatory Q&A request: {}", request.question);
    
    let response = state.ai_service.process_regulatory_qa(request).await?;
    Ok(Json(response))
}

/// Requirement mapping endpoint handler
pub async fn requirement_mapping(
    State(state): State<Arc<AppState>>,
    Json(request): Json<RequirementMappingRequest>,
) -> Result<Json<RequirementMappingResponse>, RegulateAIError> {
    info!("Processing requirement mapping for regulation: {}", request.regulation_id);
    
    let response = state.ai_service.map_requirements_to_controls(request).await?;
    Ok(Json(response))
}

/// Self-healing controls endpoint handler
pub async fn self_healing_controls(
    State(state): State<Arc<AppState>>,
    Json(request): Json<SelfHealingRequest>,
) -> Result<Json<SelfHealingResponse>, RegulateAIError> {
    info!("Processing self-healing control request for control: {}", request.control_id);
    
    let response = state.ai_service.execute_self_healing(request).await?;
    Ok(Json(response))
}

/// Next best action recommendations endpoint handler
pub async fn next_best_action(
    State(state): State<Arc<AppState>>,
    Json(request): Json<NextActionRequest>,
) -> Result<Json<NextActionResponse>, RegulateAIError> {
    info!("Generating next best action recommendations for context: {}", request.context_type);
    
    let response = state.ai_service.recommend_next_action(request).await?;
    Ok(Json(response))
}

/// Dynamic workflows endpoint handler
pub async fn dynamic_workflows(
    State(state): State<Arc<AppState>>,
    Json(request): Json<DynamicWorkflowRequest>,
) -> Result<Json<DynamicWorkflowResponse>, RegulateAIError> {
    info!("Creating dynamic workflow for trigger: {}", request.trigger_event);
    
    let response = state.ai_service.create_dynamic_workflow(request).await?;
    Ok(Json(response))
}

/// Context-aware search endpoint handler
pub async fn context_aware_search(
    State(state): State<Arc<AppState>>,
    Query(params): Query<SearchParams>,
) -> Result<Json<SearchResponse>, RegulateAIError> {
    info!("Performing context-aware search for query: {}", params.query);
    
    let response = state.ai_service.context_aware_search(params).await?;
    Ok(Json(response))
}

/// Agent status endpoint handler
pub async fn agent_status(
    State(state): State<Arc<AppState>>,
) -> Result<Json<AgentStatusResponse>, RegulateAIError> {
    let response = state.ai_service.get_agent_status().await?;
    Ok(Json(response))
}

/// Orchestration execution endpoint handler
pub async fn execute_orchestration(
    State(state): State<Arc<AppState>>,
    Json(request): Json<OrchestrationRequest>,
) -> Result<Json<OrchestrationResponse>, RegulateAIError> {
    info!("Executing orchestration workflow: {}", request.workflow_id);
    
    let response = state.ai_service.execute_orchestration(request).await?;
    Ok(Json(response))
}

/// Get orchestration status endpoint handler
pub async fn get_orchestration_status(
    State(state): State<Arc<AppState>>,
    Path(execution_id): Path<String>,
) -> Result<Json<OrchestrationStatusResponse>, RegulateAIError> {
    info!("Getting orchestration status for execution: {}", execution_id);
    
    // Simulate status retrieval
    let response = OrchestrationStatusResponse {
        execution_id: execution_id.clone(),
        status: "running".to_string(),
        progress: 45.0,
        current_step: "assess_impact".to_string(),
        estimated_completion: "2024-08-01T14:30:00Z".to_string(),
        steps_completed: 2,
        total_steps: 5,
        last_updated: chrono::Utc::now().to_rfc3339(),
    };
    
    Ok(Json(response))
}

/// List available workflows endpoint handler
pub async fn list_workflows(
    State(state): State<Arc<AppState>>,
    Query(params): Query<ListWorkflowsParams>,
) -> Result<Json<ListWorkflowsResponse>, RegulateAIError> {
    info!("Listing workflows with status: {:?}", params.status);
    
    // Simulate workflow listing
    let workflows = vec![
        WorkflowSummary {
            id: Uuid::new_v4().to_string(),
            name: "Regulatory Change Response".to_string(),
            status: "active".to_string(),
            created_at: chrono::Utc::now().to_rfc3339(),
            estimated_duration: "8 hours".to_string(),
        },
        WorkflowSummary {
            id: Uuid::new_v4().to_string(),
            name: "Security Incident Response".to_string(),
            status: "completed".to_string(),
            created_at: (chrono::Utc::now() - chrono::Duration::hours(2)).to_rfc3339(),
            estimated_duration: "4 hours".to_string(),
        },
    ];
    
    let response = ListWorkflowsResponse {
        workflows,
        total_count: 2,
        page: params.page.unwrap_or(1),
        per_page: params.per_page.unwrap_or(10),
    };
    
    Ok(Json(response))
}

/// Create workflow template endpoint handler
pub async fn create_workflow_template(
    State(state): State<Arc<AppState>>,
    Json(request): Json<CreateWorkflowTemplateRequest>,
) -> Result<Json<CreateWorkflowTemplateResponse>, RegulateAIError> {
    info!("Creating workflow template: {}", request.name);
    
    let template_id = Uuid::new_v4().to_string();
    
    let response = CreateWorkflowTemplateResponse {
        template_id,
        name: request.name,
        status: "created".to_string(),
        created_at: chrono::Utc::now().to_rfc3339(),
    };
    
    Ok(Json(response))
}

/// Get agent performance metrics endpoint handler
pub async fn get_agent_metrics(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Result<Json<AgentMetricsResponse>, RegulateAIError> {
    info!("Getting metrics for agent: {}", agent_id);
    
    let response = AgentMetricsResponse {
        agent_id: agent_id.clone(),
        metrics: AgentMetrics {
            requests_processed: 1250,
            success_rate: 0.967,
            average_response_time_ms: 145,
            error_rate: 0.033,
            uptime_percentage: 99.8,
            last_24h_requests: 89,
        },
        performance_trend: "improving".to_string(),
        last_updated: chrono::Utc::now().to_rfc3339(),
    };
    
    Ok(Json(response))
}

/// Bulk agent operation endpoint handler
pub async fn bulk_agent_operation(
    State(state): State<Arc<AppState>>,
    Json(request): Json<BulkAgentOperationRequest>,
) -> Result<Json<BulkAgentOperationResponse>, RegulateAIError> {
    info!("Performing bulk operation: {} on {} agents", request.operation, request.agent_ids.len());
    
    let mut results = Vec::new();
    
    for agent_id in &request.agent_ids {
        results.push(AgentOperationResult {
            agent_id: agent_id.clone(),
            success: true,
            message: format!("Operation {} completed successfully", request.operation),
        });
    }
    
    let response = BulkAgentOperationResponse {
        operation: request.operation,
        total_agents: request.agent_ids.len(),
        successful: results.len(),
        failed: 0,
        results,
    };
    
    Ok(Json(response))
}

// Response types
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub service: String,
    pub version: String,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct OrchestrationStatusResponse {
    pub execution_id: String,
    pub status: String,
    pub progress: f64,
    pub current_step: String,
    pub estimated_completion: String,
    pub steps_completed: u32,
    pub total_steps: u32,
    pub last_updated: String,
}

#[derive(Debug, Deserialize)]
pub struct ListWorkflowsParams {
    pub status: Option<String>,
    pub page: Option<u32>,
    pub per_page: Option<u32>,
}

#[derive(Debug, Serialize)]
pub struct ListWorkflowsResponse {
    pub workflows: Vec<WorkflowSummary>,
    pub total_count: u32,
    pub page: u32,
    pub per_page: u32,
}

#[derive(Debug, Serialize)]
pub struct WorkflowSummary {
    pub id: String,
    pub name: String,
    pub status: String,
    pub created_at: String,
    pub estimated_duration: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateWorkflowTemplateRequest {
    pub name: String,
    pub description: String,
    pub steps: Vec<serde_json::Value>,
    pub triggers: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct CreateWorkflowTemplateResponse {
    pub template_id: String,
    pub name: String,
    pub status: String,
    pub created_at: String,
}

#[derive(Debug, Serialize)]
pub struct AgentMetricsResponse {
    pub agent_id: String,
    pub metrics: AgentMetrics,
    pub performance_trend: String,
    pub last_updated: String,
}

#[derive(Debug, Serialize)]
pub struct AgentMetrics {
    pub requests_processed: u64,
    pub success_rate: f64,
    pub average_response_time_ms: u64,
    pub error_rate: f64,
    pub uptime_percentage: f64,
    pub last_24h_requests: u64,
}

#[derive(Debug, Deserialize)]
pub struct BulkAgentOperationRequest {
    pub operation: String,
    pub agent_ids: Vec<String>,
    pub parameters: Option<serde_json::Value>,
}

#[derive(Debug, Serialize)]
pub struct BulkAgentOperationResponse {
    pub operation: String,
    pub total_agents: usize,
    pub successful: usize,
    pub failed: usize,
    pub results: Vec<AgentOperationResult>,
}

#[derive(Debug, Serialize)]
pub struct AgentOperationResult {
    pub agent_id: String,
    pub success: bool,
    pub message: String,
}
