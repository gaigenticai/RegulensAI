//! HTTP handlers for the Fraud Detection Service API endpoints

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
// FRAUD DETECTION HANDLERS
// =============================================================================

/// Analyze transaction for fraud
pub async fn analyze_transaction(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<TransactionAnalysisRequest>,
) -> Result<Json<ApiResponse<FraudAnalysisResult>>, StatusCode> {
    info!("Analyzing transaction for fraud: {}", request.transaction_id);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.fraud_service.analyze_transaction(request).await {
        Ok(result) => {
            info!("Transaction analysis completed: {} - Risk Score: {}", 
                  result.transaction_id, result.risk_score);
            Ok(Json(ApiResponse::success(result)))
        },
        Err(e) => {
            error!("Failed to analyze transaction: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to analyze transaction".to_string())))
        }
    }
}

/// Get fraud alert by ID
pub async fn get_fraud_alert(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<FraudAlert>>, StatusCode> {
    info!("Getting fraud alert: {}", id);

    match state.fraud_service.get_fraud_alert(id).await {
        Ok(Some(alert)) => {
            info!("Fraud alert found: {}", id);
            Ok(Json(ApiResponse::success(alert)))
        },
        Ok(None) => {
            warn!("Fraud alert not found: {}", id);
            Ok(Json(ApiResponse::error("Fraud alert not found".to_string())))
        },
        Err(e) => {
            error!("Failed to get fraud alert: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get fraud alert".to_string())))
        }
    }
}

/// List fraud alerts with pagination
pub async fn list_fraud_alerts(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(params): Query<PaginationQuery>,
) -> Result<Json<ApiResponse<Vec<FraudAlert>>>, StatusCode> {
    info!("Listing fraud alerts - page: {}, per_page: {}", params.page, params.per_page);

    match state.fraud_service.list_fraud_alerts(params.page, params.per_page).await {
        Ok(alerts) => {
            info!("Found {} fraud alerts", alerts.len());
            Ok(Json(ApiResponse::success(alerts)))
        },
        Err(e) => {
            error!("Failed to list fraud alerts: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to list fraud alerts".to_string())))
        }
    }
}

/// Update fraud alert status
pub async fn update_fraud_alert_status(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
    Json(request): Json<UpdateAlertStatusRequest>,
) -> Result<Json<ApiResponse<FraudAlert>>, StatusCode> {
    info!("Updating fraud alert status: {} to {}", id, request.status);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.fraud_service.update_alert_status(id, request, auth.user_id).await {
        Ok(alert) => {
            info!("Fraud alert status updated successfully: {}", id);
            Ok(Json(ApiResponse::success(alert)))
        },
        Err(e) => {
            error!("Failed to update fraud alert status: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to update fraud alert status".to_string())))
        }
    }
}

// =============================================================================
// FRAUD RULES HANDLERS
// =============================================================================

/// Create a new fraud rule
pub async fn create_fraud_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateFraudRuleRequest>,
) -> Result<Json<ApiResponse<FraudRule>>, StatusCode> {
    info!("Creating fraud rule: {}", request.rule_name);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.fraud_service.create_fraud_rule(request, auth.user_id).await {
        Ok(rule) => {
            info!("Fraud rule created successfully: {}", rule.id);
            Ok(Json(ApiResponse::success(rule)))
        },
        Err(e) => {
            error!("Failed to create fraud rule: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to create fraud rule".to_string())))
        }
    }
}

/// Get fraud rule by ID
pub async fn get_fraud_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<FraudRule>>, StatusCode> {
    info!("Getting fraud rule: {}", id);

    match state.fraud_service.get_fraud_rule(id).await {
        Ok(Some(rule)) => {
            info!("Fraud rule found: {}", id);
            Ok(Json(ApiResponse::success(rule)))
        },
        Ok(None) => {
            warn!("Fraud rule not found: {}", id);
            Ok(Json(ApiResponse::error("Fraud rule not found".to_string())))
        },
        Err(e) => {
            error!("Failed to get fraud rule: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get fraud rule".to_string())))
        }
    }
}

/// List fraud rules with pagination
pub async fn list_fraud_rules(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(params): Query<PaginationQuery>,
) -> Result<Json<ApiResponse<Vec<FraudRule>>>, StatusCode> {
    info!("Listing fraud rules - page: {}, per_page: {}", params.page, params.per_page);

    match state.fraud_service.list_fraud_rules(params.page, params.per_page).await {
        Ok(rules) => {
            info!("Found {} fraud rules", rules.len());
            Ok(Json(ApiResponse::success(rules)))
        },
        Err(e) => {
            error!("Failed to list fraud rules: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to list fraud rules".to_string())))
        }
    }
}

/// Update fraud rule
pub async fn update_fraud_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
    Json(request): Json<UpdateFraudRuleRequest>,
) -> Result<Json<ApiResponse<FraudRule>>, StatusCode> {
    info!("Updating fraud rule: {}", id);

    match request.validate() {
        Ok(_) => {},
        Err(e) => {
            error!("Validation error: {:?}", e);
            return Ok(Json(ApiResponse::error("Invalid request data".to_string())));
        }
    }

    match state.fraud_service.update_fraud_rule(id, request, auth.user_id).await {
        Ok(rule) => {
            info!("Fraud rule updated successfully: {}", id);
            Ok(Json(ApiResponse::success(rule)))
        },
        Err(e) => {
            error!("Failed to update fraud rule: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to update fraud rule".to_string())))
        }
    }
}

/// Delete fraud rule
pub async fn delete_fraud_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(id): Path<Uuid>,
) -> Result<Json<ApiResponse<()>>, StatusCode> {
    info!("Deleting fraud rule: {}", id);

    match state.fraud_service.delete_fraud_rule(id, auth.user_id).await {
        Ok(_) => {
            info!("Fraud rule deleted successfully: {}", id);
            Ok(Json(ApiResponse::success(())))
        },
        Err(e) => {
            error!("Failed to delete fraud rule: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to delete fraud rule".to_string())))
        }
    }
}

// =============================================================================
// ML MODEL HANDLERS
// =============================================================================

/// Get ML model performance metrics
pub async fn get_model_metrics(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(model_id): Path<Uuid>,
) -> Result<Json<ApiResponse<ModelMetrics>>, StatusCode> {
    info!("Getting ML model metrics: {}", model_id);

    match state.fraud_service.get_model_metrics(model_id).await {
        Ok(metrics) => {
            info!("Model metrics retrieved: {}", model_id);
            Ok(Json(ApiResponse::success(metrics)))
        },
        Err(e) => {
            error!("Failed to get model metrics: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to get model metrics".to_string())))
        }
    }
}

/// Retrain ML model
pub async fn retrain_model(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(model_id): Path<Uuid>,
    Json(request): Json<RetrainModelRequest>,
) -> Result<Json<ApiResponse<ModelRetrainResult>>, StatusCode> {
    info!("Retraining ML model: {}", model_id);

    match state.fraud_service.retrain_model(model_id, request, auth.user_id).await {
        Ok(result) => {
            info!("Model retrain initiated: {}", model_id);
            Ok(Json(ApiResponse::success(result)))
        },
        Err(e) => {
            error!("Failed to retrain model: {:?}", e);
            Ok(Json(ApiResponse::error("Failed to retrain model".to_string())))
        }
    }
}
