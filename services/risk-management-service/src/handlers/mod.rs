//! HTTP handlers for the Risk Management Service API endpoints

use axum::{
    extract::{Path, Query, State},
    response::Json,
    http::StatusCode,
    Extension,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
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
// RISK ASSESSMENT HANDLERS
// =============================================================================

/// Create a new risk assessment
pub async fn create_risk_assessment(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateRiskAssessmentRequest>,
) -> Result<Json<ApiResponse<RiskAssessment>>, StatusCode> {
    info!("Creating risk assessment: {}", request.title);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.risk_service.create_risk_assessment(request, auth.user_id).await {
        Ok(assessment) => {
            info!("Risk assessment created successfully: {}", assessment.id);
            Ok(Json(ApiResponse::success(assessment)))
        },
        Err(e) => {
            error!("Failed to create risk assessment: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create risk assessment".to_string())))
        }
    }
}

/// Get risk assessment by ID
pub async fn get_risk_assessment(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<RiskAssessment>>, StatusCode> {
    info!("Getting risk assessment: {}", id);

    match state.risk_service.get_risk_assessment(id).await {
        Ok(Some(assessment)) => {
            info!("Risk assessment found: {}", id);
            Ok(Json(ApiResponse::success(assessment)))
        },
        Ok(None) => {
            warn!("Risk assessment not found: {}", id);
            Ok(Json(ApiResponse::error("Risk assessment not found".to_string())))
        },
        Err(e) => {
            error!("Failed to get risk assessment: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get risk assessment".to_string())))
        }
    }
}

/// List risk assessments with pagination
pub async fn list_risk_assessments(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(params): Query<PaginationQuery>,
) -> Result<Json<ApiResponse<Vec<RiskAssessment>>>, StatusCode> {
    info!("Listing risk assessments - page: {}, per_page: {}", params.page, params.per_page);

    match state.risk_service.list_risk_assessments(params.page, params.per_page).await {
        Ok(assessments) => {
            info!("Found {} risk assessments", assessments.len());
            Ok(Json(ApiResponse::success(assessments)))
        },
        Err(e) => {
            error!("Failed to list risk assessments: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to list risk assessments".to_string())))
        }
    }
}

/// Update risk assessment
pub async fn update_risk_assessment(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
    Json(request): Json<UpdateRiskAssessmentRequest>,
) -> Result<Json<ApiResponse<RiskAssessment>>, StatusCode> {
    info!("Updating risk assessment: {}", id);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.risk_service.update_risk_assessment(id, request, auth.user_id).await {
        Ok(assessment) => {
            info!("Risk assessment updated successfully: {}", id);
            Ok(Json(ApiResponse::success(assessment)))
        },
        Err(e) => {
            error!("Failed to update risk assessment: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to update risk assessment".to_string())))
        }
    }
}

/// Delete risk assessment
pub async fn delete_risk_assessment(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<()>>, StatusCode> {
    info!("Deleting risk assessment: {}", id);

    match state.risk_service.delete_risk_assessment(id, auth.user_id).await {
        Ok(_) => {
            info!("Risk assessment deleted successfully: {}", id);
            Ok(Json(ApiResponse::success(())))
        },
        Err(e) => {
            error!("Failed to delete risk assessment: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to delete risk assessment".to_string())))
        }
    }
}

// =============================================================================
// KEY RISK INDICATORS (KRI) HANDLERS
// =============================================================================

/// Create a new KRI
pub async fn create_kri(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateKriRequest>,
) -> Result<Json<ApiResponse<KeyRiskIndicator>>, StatusCode> {
    info!("Creating KRI: {}", request.name);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.risk_service.create_kri(request, auth.user_id).await {
        Ok(kri) => {
            info!("KRI created successfully: {}", kri.id);
            Ok(Json(ApiResponse::success(kri)))
        },
        Err(e) => {
            error!("Failed to create KRI: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create KRI".to_string())))
        }
    }
}

/// Get KRI by ID
pub async fn get_kri(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<KeyRiskIndicator>>, StatusCode> {
    info!("Getting KRI: {}", id);

    match state.risk_service.get_kri(id).await {
        Ok(Some(kri)) => {
            info!("KRI found: {}", id);
            Ok(Json(ApiResponse::success(kri)))
        },
        Ok(None) => {
            warn!("KRI not found: {}", id);
            Ok(Json(ApiResponse::error("KRI not found".to_string())))
        },
        Err(e) => {
            error!("Failed to get KRI: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get KRI".to_string())))
        }
    }
}

/// List KRIs with pagination
pub async fn list_kris(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(params): Query<PaginationQuery>,
) -> Result<Json<ApiResponse<Vec<KeyRiskIndicator>>>, StatusCode> {
    info!("Listing KRIs - page: {}, per_page: {}", params.page, params.per_page);

    match state.risk_service.list_kris(params.page, params.per_page).await {
        Ok(kris) => {
            info!("Found {} KRIs", kris.len());
            Ok(Json(ApiResponse::success(kris)))
        },
        Err(e) => {
            error!("Failed to list KRIs: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to list KRIs".to_string())))
        }
    }
}

/// Record KRI measurement
pub async fn record_kri_measurement(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(kri_id): Path<Uuid>,
    Json(request): Json<RecordKriMeasurementRequest>,
) -> Result<Json<ApiResponse<KriMeasurement>>, StatusCode> {
    info!("Recording KRI measurement for KRI: {}", kri_id);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.risk_service.record_kri_measurement(kri_id, request, auth.user_id).await {
        Ok(measurement) => {
            info!("KRI measurement recorded successfully: {}", measurement.id);
            Ok(Json(ApiResponse::success(measurement)))
        },
        Err(e) => {
            error!("Failed to record KRI measurement: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to record KRI measurement".to_string())))
        }
    }
}
