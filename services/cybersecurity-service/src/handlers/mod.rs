//! HTTP handlers for the Cybersecurity Service API endpoints

use axum::{
    extract::{Path, Query, State},
    response::Json,
    http::StatusCode,
    Extension,
};
use serde::{Deserialize, Serialize};
use tracing::{info, error};
use uuid::Uuid;
use validator::Validate;

use regulateai_auth::AuthContext;
use regulateai_errors::RegulateAIError;

use crate::{AppState, models::*};

/// Query parameters for pagination
#[derive(Debug, Deserialize)]
pub struct PaginationQuery {
    #[serde(default = "default_page")]
    pub page: u64,
    #[serde(default = "default_per_page")]
    pub per_page: u64,
}

fn default_page() -> u64 { 0 }
fn default_per_page() -> u64 { 20 }

/// Standard API response wrapper
#[derive(Debug, Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub message: Option<String>,
    pub error: Option<String>,
}

impl<T> ApiResponse<T> {
    pub fn success(data: T) -> Self {
        Self {
            success: true,
            data: Some(data),
            message: None,
            error: None,
        }
    }

    pub fn error(message: String) -> Self {
        Self {
            success: false,
            data: None,
            message: None,
            error: Some(message),
        }
    }
}

// =============================================================================
// VULNERABILITY MANAGEMENT HANDLERS
// =============================================================================

/// Create a new vulnerability assessment
pub async fn create_vulnerability_assessment(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateVulnerabilityAssessmentRequest>,
) -> Result<Json<ApiResponse<VulnerabilityAssessment>>, StatusCode> {
    info!("Creating vulnerability assessment: {}", request.title);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.create_vulnerability_assessment(request, auth.user_id).await {
        Ok(assessment) => {
            info!("Vulnerability assessment created successfully: {}", assessment.id);
            Ok(Json(ApiResponse::success(assessment)))
        },
        Err(e) => {
            error!("Failed to create vulnerability assessment: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create vulnerability assessment".to_string())))
        }
    }
}

/// Get vulnerability assessment by ID
pub async fn get_vulnerability_assessment(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<VulnerabilityAssessment>>, StatusCode> {
    info!("Getting vulnerability assessment: {}", id);

    match state.cybersecurity_service.get_vulnerability_assessment(id).await {
        Ok(Some(assessment)) => {
            info!("Vulnerability assessment found: {}", id);
            Ok(Json(ApiResponse::success(assessment)))
        },
        Ok(None) => {
            warn!("Vulnerability assessment not found: {}", id);
            Ok(Json(ApiResponse::error("Vulnerability assessment not found".to_string())))
        },
        Err(e) => {
            error!("Failed to get vulnerability assessment: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get vulnerability assessment".to_string())))
        }
    }
}

/// List vulnerability assessments with pagination
pub async fn list_vulnerability_assessments(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(params): Query<PaginationQuery>,
) -> Result<Json<ApiResponse<Vec<VulnerabilityAssessment>>>, StatusCode> {
    info!("Listing vulnerability assessments - page: {}, per_page: {}", params.page, params.per_page);

    match state.cybersecurity_service.list_vulnerability_assessments(params.page, params.per_page).await {
        Ok(assessments) => {
            info!("Found {} vulnerability assessments", assessments.len());
            Ok(Json(ApiResponse::success(assessments)))
        },
        Err(e) => {
            error!("Failed to list vulnerability assessments: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to list vulnerability assessments".to_string())))
        }
    }
}

// =============================================================================
// INCIDENT RESPONSE HANDLERS
// =============================================================================

/// Create a new security incident
pub async fn create_security_incident(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateSecurityIncidentRequest>,
) -> Result<Json<ApiResponse<SecurityIncident>>, StatusCode> {
    info!("Creating security incident: {}", request.title);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.create_security_incident(request, auth.user_id).await {
        Ok(incident) => {
            info!("Security incident created successfully: {}", incident.id);
            Ok(Json(ApiResponse::success(incident)))
        },
        Err(e) => {
            error!("Failed to create security incident: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create security incident".to_string())))
        }
    }
}

/// Get security incident by ID
pub async fn get_security_incident(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<SecurityIncident>>, StatusCode> {
    info!("Getting security incident: {}", id);

    match state.cybersecurity_service.get_security_incident(id).await {
        Ok(Some(incident)) => {
            info!("Security incident found: {}", id);
            Ok(Json(ApiResponse::success(incident)))
        },
        Ok(None) => {
            warn!("Security incident not found: {}", id);
            Ok(Json(ApiResponse::error("Security incident not found".to_string())))
        },
        Err(e) => {
            error!("Failed to get security incident: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get security incident".to_string())))
        }
    }
}

/// Update security incident status
pub async fn update_incident_status(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
    Json(request): Json<UpdateIncidentStatusRequest>,
) -> Result<Json<ApiResponse<SecurityIncident>>, StatusCode> {
    info!("Updating security incident status: {} to {}", id, request.status);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.update_incident_status(id, request, auth.user_id).await {
        Ok(incident) => {
            info!("Security incident status updated successfully: {}", id);
            Ok(Json(ApiResponse::success(incident)))
        },
        Err(e) => {
            error!("Failed to update security incident status: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to update security incident status".to_string())))
        }
    }
}

// =============================================================================
// GDPR COMPLIANCE HANDLERS
// =============================================================================

/// Create a new data processing record
pub async fn create_data_processing_record(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateDataProcessingRecordRequest>,
) -> Result<Json<ApiResponse<DataProcessingRecord>>, StatusCode> {
    info!("Creating data processing record: {}", request.processing_purpose);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.create_data_processing_record(request, auth.user_id).await {
        Ok(record) => {
            info!("Data processing record created successfully: {}", record.id);
            Ok(Json(ApiResponse::success(record)))
        },
        Err(e) => {
            error!("Failed to create data processing record: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create data processing record".to_string())))
        }
    }
}

/// Process data subject request
pub async fn process_data_subject_request(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<DataSubjectRequest>,
) -> Result<Json<ApiResponse<DataSubjectRequestResponse>>, StatusCode> {
    info!("Processing data subject request: {}", request.request_type);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.process_data_subject_request(request, auth.user_id).await {
        Ok(response) => {
            info!("Data subject request processed successfully: {}", response.request_id);
            Ok(Json(ApiResponse::success(response)))
        },
        Err(e) => {
            error!("Failed to process data subject request: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to process data subject request".to_string())))
        }
    }
}

// =============================================================================
// IAM HANDLERS
// =============================================================================

/// Create access control policy
pub async fn create_access_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateAccessPolicyRequest>,
) -> Result<Json<ApiResponse<AccessPolicy>>, StatusCode> {
    info!("Creating access policy: {}", request.policy_name);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.create_access_policy(request, auth.user_id).await {
        Ok(policy) => {
            info!("Access policy created successfully: {}", policy.id);
            Ok(Json(ApiResponse::success(policy)))
        },
        Err(e) => {
            error!("Failed to create access policy: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create access policy".to_string())))
        }
    }
}

/// Evaluate access request
pub async fn evaluate_access_request(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<AccessEvaluationRequest>,
) -> Result<Json<ApiResponse<AccessEvaluationResult>>, StatusCode> {
    info!("Evaluating access request for user: {}", request.user_id);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.cybersecurity_service.evaluate_access_request(request).await {
        Ok(result) => {
            info!("Access request evaluated: {} - Decision: {}", result.request_id, result.decision);
            Ok(Json(ApiResponse::success(result)))
        },
        Err(e) => {
            error!("Failed to evaluate access request: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to evaluate access request".to_string())))
        }
    }
}
