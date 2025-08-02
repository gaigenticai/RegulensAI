//! Data Models for AI Orchestration Service
//! 
//! This module contains all data structures and models used by the AI orchestration service,
//! including database entities, request/response types, and domain models.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// =============================================================================
// DATABASE ENTITIES
// =============================================================================

/// AI Agent database entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AIAgent {
    pub id: Uuid,
    pub agent_type: String,
    pub name: String,
    pub description: Option<String>,
    pub configuration: serde_json::Value,
    pub status: String,
    pub capabilities: Vec<String>,
    pub performance_metrics: serde_json::Value,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Option<Uuid>,
    pub updated_by: Option<Uuid>,
    pub version: i32,
}

/// Workflow Template database entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowTemplate {
    pub id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub template_type: String,
    pub template_definition: serde_json::Value,
    pub trigger_conditions: serde_json::Value,
    pub default_parameters: serde_json::Value,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Option<Uuid>,
    pub updated_by: Option<Uuid>,
    pub version: i32,
}

/// Workflow Instance database entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowInstance {
    pub id: Uuid,
    pub template_id: Option<Uuid>,
    pub name: String,
    pub description: Option<String>,
    pub workflow_definition: serde_json::Value,
    pub input_parameters: serde_json::Value,
    pub status: String,
    pub current_step: Option<String>,
    pub execution_context: serde_json::Value,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Option<Uuid>,
    pub updated_by: Option<Uuid>,
    pub version: i32,
}

/// Agent Interaction database entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentInteraction {
    pub id: Uuid,
    pub agent_id: Uuid,
    pub interaction_type: String,
    pub request_data: serde_json::Value,
    pub response_data: Option<serde_json::Value>,
    pub status: String,
    pub processing_time_ms: Option<i32>,
    pub error_message: Option<String>,
    pub workflow_instance_id: Option<Uuid>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Option<Uuid>,
    pub version: i32,
}

/// Knowledge Base Entry database entity
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KnowledgeBaseEntry {
    pub id: Uuid,
    pub title: String,
    pub content: String,
    pub content_type: String,
    pub category: String,
    pub tags: Vec<String>,
    pub metadata: serde_json::Value,
    pub embedding_vector: Option<Vec<f32>>,
    pub source_url: Option<String>,
    pub source_type: String,
    pub confidence_score: Option<f64>,
    pub is_verified: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub created_by: Option<Uuid>,
    pub updated_by: Option<Uuid>,
    pub version: i32,
}

// =============================================================================
// REQUEST/RESPONSE TYPES
// =============================================================================

/// Create AI Agent request
#[derive(Debug, Deserialize)]
pub struct CreateAIAgentRequest {
    pub agent_type: String,
    pub name: String,
    pub description: Option<String>,
    pub configuration: serde_json::Value,
    pub capabilities: Vec<String>,
}

/// Update AI Agent request
#[derive(Debug, Deserialize)]
pub struct UpdateAIAgentRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub configuration: Option<serde_json::Value>,
    pub capabilities: Option<Vec<String>>,
    pub status: Option<String>,
}

/// AI Agent response
#[derive(Debug, Serialize)]
pub struct AIAgentResponse {
    pub id: Uuid,
    pub agent_type: String,
    pub name: String,
    pub description: Option<String>,
    pub status: String,
    pub capabilities: Vec<String>,
    pub performance_metrics: serde_json::Value,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Create Workflow Template request
#[derive(Debug, Deserialize)]
pub struct CreateWorkflowTemplateRequest {
    pub name: String,
    pub description: Option<String>,
    pub template_type: String,
    pub template_definition: serde_json::Value,
    pub trigger_conditions: serde_json::Value,
    pub default_parameters: Option<serde_json::Value>,
}

/// Workflow Template response
#[derive(Debug, Serialize)]
pub struct WorkflowTemplateResponse {
    pub id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub template_type: String,
    pub template_definition: serde_json::Value,
    pub trigger_conditions: serde_json::Value,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Create Workflow Instance request
#[derive(Debug, Deserialize)]
pub struct CreateWorkflowInstanceRequest {
    pub template_id: Option<Uuid>,
    pub name: String,
    pub description: Option<String>,
    pub workflow_definition: Option<serde_json::Value>,
    pub input_parameters: serde_json::Value,
}

/// Workflow Instance response
#[derive(Debug, Serialize)]
pub struct WorkflowInstanceResponse {
    pub id: Uuid,
    pub template_id: Option<Uuid>,
    pub name: String,
    pub description: Option<String>,
    pub status: String,
    pub current_step: Option<String>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Agent Interaction request
#[derive(Debug, Deserialize)]
pub struct CreateAgentInteractionRequest {
    pub agent_id: Uuid,
    pub interaction_type: String,
    pub request_data: serde_json::Value,
    pub workflow_instance_id: Option<Uuid>,
}

/// Agent Interaction response
#[derive(Debug, Serialize)]
pub struct AgentInteractionResponse {
    pub id: Uuid,
    pub agent_id: Uuid,
    pub interaction_type: String,
    pub status: String,
    pub processing_time_ms: Option<i32>,
    pub response_data: Option<serde_json::Value>,
    pub error_message: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// Knowledge Base Entry request
#[derive(Debug, Deserialize)]
pub struct CreateKnowledgeBaseEntryRequest {
    pub title: String,
    pub content: String,
    pub content_type: String,
    pub category: String,
    pub tags: Vec<String>,
    pub metadata: Option<serde_json::Value>,
    pub source_url: Option<String>,
    pub source_type: String,
}

/// Knowledge Base Entry response
#[derive(Debug, Serialize)]
pub struct KnowledgeBaseEntryResponse {
    pub id: Uuid,
    pub title: String,
    pub content: String,
    pub content_type: String,
    pub category: String,
    pub tags: Vec<String>,
    pub metadata: serde_json::Value,
    pub source_type: String,
    pub confidence_score: Option<f64>,
    pub is_verified: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// =============================================================================
// DOMAIN MODELS
// =============================================================================

/// Agent capability definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentCapability {
    pub name: String,
    pub description: String,
    pub input_schema: serde_json::Value,
    pub output_schema: serde_json::Value,
    pub parameters: Vec<CapabilityParameter>,
}

/// Capability parameter
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityParameter {
    pub name: String,
    pub parameter_type: String,
    pub required: bool,
    pub default_value: Option<serde_json::Value>,
    pub description: String,
}

/// Workflow step definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStepDefinition {
    pub id: String,
    pub name: String,
    pub step_type: String,
    pub agent_type: Option<String>,
    pub input_mapping: serde_json::Value,
    pub output_mapping: serde_json::Value,
    pub conditions: Option<serde_json::Value>,
    pub timeout_seconds: Option<i32>,
    pub retry_policy: Option<RetryPolicy>,
}

/// Retry policy for workflow steps
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryPolicy {
    pub max_attempts: i32,
    pub backoff_strategy: String,
    pub initial_delay_ms: i32,
    pub max_delay_ms: i32,
    pub retry_conditions: Vec<String>,
}

/// Execution context for workflows
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionContext {
    pub variables: serde_json::Value,
    pub step_outputs: std::collections::HashMap<String, serde_json::Value>,
    pub execution_metadata: serde_json::Value,
    pub error_history: Vec<ExecutionError>,
}

/// Execution error information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionError {
    pub step_id: String,
    pub error_type: String,
    pub error_message: String,
    pub occurred_at: DateTime<Utc>,
    pub retry_attempt: i32,
}

/// Performance metrics for agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentPerformanceMetrics {
    pub total_interactions: u64,
    pub successful_interactions: u64,
    pub failed_interactions: u64,
    pub average_response_time_ms: f64,
    pub median_response_time_ms: f64,
    pub p95_response_time_ms: f64,
    pub error_rate: f64,
    pub uptime_percentage: f64,
    pub last_updated: DateTime<Utc>,
}

/// Search query with context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextualSearchQuery {
    pub query: String,
    pub context: Option<String>,
    pub filters: std::collections::HashMap<String, serde_json::Value>,
    pub limit: Option<u32>,
    pub offset: Option<u32>,
    pub include_embeddings: bool,
}

/// Search result with relevance scoring
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResultWithScore {
    pub entry: KnowledgeBaseEntry,
    pub relevance_score: f64,
    pub match_highlights: Vec<String>,
    pub context_relevance: f64,
}

// =============================================================================
// ENUMS
// =============================================================================

/// Agent status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AgentStatus {
    Active,
    Inactive,
    Maintenance,
    Error,
    Initializing,
}

/// Workflow status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum WorkflowStatus {
    Created,
    Running,
    Paused,
    Completed,
    Failed,
    Cancelled,
}

/// Interaction status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum InteractionStatus {
    Pending,
    Processing,
    Completed,
    Failed,
    Timeout,
}

/// Content type enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ContentType {
    Regulation,
    Policy,
    Procedure,
    Guideline,
    FAQ,
    Documentation,
    Template,
    Example,
}

impl std::fmt::Display for AgentStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AgentStatus::Active => write!(f, "active"),
            AgentStatus::Inactive => write!(f, "inactive"),
            AgentStatus::Maintenance => write!(f, "maintenance"),
            AgentStatus::Error => write!(f, "error"),
            AgentStatus::Initializing => write!(f, "initializing"),
        }
    }
}

impl std::fmt::Display for WorkflowStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WorkflowStatus::Created => write!(f, "created"),
            WorkflowStatus::Running => write!(f, "running"),
            WorkflowStatus::Paused => write!(f, "paused"),
            WorkflowStatus::Completed => write!(f, "completed"),
            WorkflowStatus::Failed => write!(f, "failed"),
            WorkflowStatus::Cancelled => write!(f, "cancelled"),
        }
    }
}

impl std::fmt::Display for InteractionStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            InteractionStatus::Pending => write!(f, "pending"),
            InteractionStatus::Processing => write!(f, "processing"),
            InteractionStatus::Completed => write!(f, "completed"),
            InteractionStatus::Failed => write!(f, "failed"),
            InteractionStatus::Timeout => write!(f, "timeout"),
        }
    }
}
