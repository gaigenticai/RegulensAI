//! HTTP handlers for AML service endpoints

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
    Extension,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::{info, error};
use uuid::Uuid;
use validator::Validate;

use regulateai_auth::{AuthContext, require_auth_context};
use regulateai_errors::RegulateAIError;

use crate::{AppState, models::*};

/// Customer creation handler
pub async fn create_customer(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateCustomerRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Creating customer for user: {}", auth.user_id);

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Customer creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Check permissions
    if !auth.has_permission("customers:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.customer_service.create_customer(request).await {
        Ok(customer) => {
            info!("Customer created successfully: {}", customer.id);
            Ok(Json(serde_json::json!({
                "success": true,
                "data": customer,
                "message": "Customer created successfully"
            })))
        }
        Err(e) => {
            error!("Failed to create customer: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get customer handler
pub async fn get_customer(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(customer_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting customer: {} for user: {}", customer_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("customers:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.customer_service.get_customer(customer_id).await {
        Ok(customer) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": customer
            })))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get customer: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Update customer handler
pub async fn update_customer(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(customer_id): Path<Uuid>,
    Json(request): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Updating customer: {} for user: {}", customer_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("customers:update") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    // In a full implementation, this would handle customer updates
    Ok(Json(serde_json::json!({
        "success": true,
        "message": "Customer update functionality not yet implemented"
    })))
}

/// List customers handler
#[derive(Debug, Deserialize)]
pub struct ListCustomersQuery {
    page: Option<u64>,
    per_page: Option<u64>,
    organization_id: Option<Uuid>,
}

pub async fn list_customers(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<ListCustomersQuery>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Listing customers for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("customers:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    let page = query.page.unwrap_or(0);
    let per_page = query.per_page.unwrap_or(20).min(100); // Cap at 100

    match state.aml_service.customer_service.list_customers(page, per_page, query.organization_id).await {
        Ok((customers, total_pages)) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": customers,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages
                }
            })))
        }
        Err(e) => {
            error!("Failed to list customers: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Customer risk assessment handler
pub async fn assess_customer_risk(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(customer_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Assessing risk for customer: {} by user: {}", customer_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("risk:assess") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.risk_service.assess_customer_risk(customer_id, None).await {
        Ok(risk_assessment) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": risk_assessment
            })))
        }
        Err(e) => {
            error!("Failed to assess customer risk: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// KYC verification handler
pub async fn perform_kyc(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(customer_id): Path<Uuid>,
    Json(documents): Json<Vec<IdentificationDocument>>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Performing KYC for customer: {} by user: {}", customer_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("kyc:verify") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Get customer
    let customer = match state.aml_service.customer_service.get_customer(customer_id).await {
        Ok(customer) => customer,
        Err(RegulateAIError::NotFound { .. }) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get customer for KYC: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    match state.aml_service.kyc_service.verify_customer(&customer, &documents).await {
        Ok(kyc_result) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": kyc_result
            })))
        }
        Err(e) => {
            error!("Failed to perform KYC: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Sanctions check handler
pub async fn check_sanctions(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(customer_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Checking sanctions for customer: {} by user: {}", customer_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("sanctions:check") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Get customer
    let customer = match state.aml_service.customer_service.get_customer(customer_id).await {
        Ok(customer) => customer,
        Err(RegulateAIError::NotFound { .. }) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get customer for sanctions check: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    match state.aml_service.sanctions_screener.screen_customer(&customer).await {
        Ok(screening_result) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": screening_result
            })))
        }
        Err(e) => {
            error!("Failed to check sanctions: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Transaction creation handler
pub async fn create_transaction(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateTransactionRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Creating transaction for user: {}", auth.user_id);

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Transaction creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Check permissions
    if !auth.has_permission("transactions:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.transaction_service.create_transaction(request).await {
        Ok(transaction) => {
            info!("Transaction created successfully: {}", transaction.id);
            Ok(Json(serde_json::json!({
                "success": true,
                "data": transaction,
                "message": "Transaction created successfully"
            })))
        }
        Err(e) => {
            error!("Failed to create transaction: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get transaction handler
pub async fn get_transaction(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(transaction_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting transaction: {} for user: {}", transaction_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("transactions:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.transaction_service.get_transaction(transaction_id).await {
        Ok(transaction) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": transaction
            })))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get transaction: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// List transactions handler
#[derive(Debug, Deserialize)]
pub struct ListTransactionsQuery {
    page: Option<u64>,
    per_page: Option<u64>,
    customer_id: Option<Uuid>,
    suspicious_only: Option<bool>,
}

pub async fn list_transactions(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<ListTransactionsQuery>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Listing transactions for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("transactions:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    // In a full implementation, this would handle transaction listing with filters
    Ok(Json(serde_json::json!({
        "success": true,
        "data": [],
        "message": "Transaction listing functionality not yet implemented"
    })))
}

/// Monitor transaction handler
pub async fn monitor_transaction(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(transaction_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Monitoring transaction: {} by user: {}", transaction_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("transactions:monitor") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.monitor_transaction(transaction_id).await {
        Ok(monitoring_result) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": monitoring_result
            })))
        }
        Err(e) => {
            error!("Failed to monitor transaction: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Bulk monitor transactions handler
#[derive(Debug, Deserialize, Validate)]
pub struct BulkMonitorRequest {
    #[validate(length(min = 1, max = 100))]
    pub transaction_ids: Vec<Uuid>,
}

pub async fn bulk_monitor_transactions(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<BulkMonitorRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Bulk monitoring {} transactions by user: {}", request.transaction_ids.len(), auth.user_id);

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Bulk monitor validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Check permissions
    if !auth.has_permission("transactions:monitor") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.bulk_monitor_transactions(request.transaction_ids).await {
        Ok(bulk_result) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": bulk_result
            })))
        }
        Err(e) => {
            error!("Failed to bulk monitor transactions: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// List alerts handler
#[derive(Debug, Deserialize)]
pub struct ListAlertsQuery {
    page: Option<u64>,
    per_page: Option<u64>,
    status: Option<String>,
    severity: Option<String>,
    customer_id: Option<Uuid>,
}

pub async fn list_alerts(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<ListAlertsQuery>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Listing alerts for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("alerts:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    let page = query.page.unwrap_or(0);
    let per_page = query.per_page.unwrap_or(20).min(100);

    match state.aml_service.alert_service.list_alerts(
        page,
        per_page,
        query.status,
        query.severity,
        query.customer_id,
    ).await {
        Ok((alerts, total_pages)) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": alerts,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages
                }
            })))
        }
        Err(e) => {
            error!("Failed to list alerts: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get alert handler
pub async fn get_alert(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(alert_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting alert: {} for user: {}", alert_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("alerts:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.alert_service.get_alert(alert_id).await {
        Ok(alert) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": alert
            })))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get alert: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Update alert handler
#[derive(Debug, Deserialize, Validate)]
pub struct UpdateAlertRequest {
    pub status: Option<String>,
    pub assigned_to: Option<Uuid>,
    pub investigation_notes: Option<String>,
}

pub async fn update_alert(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(alert_id): Path<Uuid>,
    Json(request): Json<UpdateAlertRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Updating alert: {} by user: {}", alert_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("alerts:update") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.alert_service.update_alert_status(
        alert_id,
        request.status.unwrap_or_else(|| "OPEN".to_string()),
        request.assigned_to,
        request.investigation_notes,
    ).await {
        Ok(alert) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": alert,
                "message": "Alert updated successfully"
            })))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to update alert: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Investigate alert handler
pub async fn investigate_alert(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(alert_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Starting investigation for alert: {} by user: {}", alert_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("alerts:investigate") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Update alert status to investigating and assign to current user
    match state.aml_service.alert_service.update_alert_status(
        alert_id,
        "INVESTIGATING".to_string(),
        Some(auth.user_id),
        Some(format!("Investigation started by {}", auth.email)),
    ).await {
        Ok(alert) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": alert,
                "message": "Alert investigation started"
            })))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to start alert investigation: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Close alert handler
#[derive(Debug, Deserialize, Validate)]
pub struct CloseAlertRequest {
    #[validate(length(min = 1))]
    pub resolution: String,
    pub resolution_notes: Option<String>,
}

pub async fn close_alert(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(alert_id): Path<Uuid>,
    Json(request): Json<CloseAlertRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Closing alert: {} by user: {}", alert_id, auth.user_id);

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Close alert validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Check permissions
    if !auth.has_permission("alerts:close") {
        return Err(StatusCode::FORBIDDEN);
    }

    let notes = format!(
        "Resolution: {}\nNotes: {}",
        request.resolution,
        request.resolution_notes.unwrap_or_else(|| "None".to_string())
    );

    match state.aml_service.alert_service.update_alert_status(
        alert_id,
        "CLOSED".to_string(),
        Some(auth.user_id),
        Some(notes),
    ).await {
        Ok(alert) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": alert,
                "message": "Alert closed successfully"
            })))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to close alert: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Screen against sanctions handler
#[derive(Debug, Deserialize, Validate)]
pub struct SanctionsScreenRequest {
    #[validate(length(min = 1))]
    pub name: String,
}

pub async fn screen_against_sanctions(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<SanctionsScreenRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Screening name '{}' against sanctions by user: {}", request.name, auth.user_id);

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Sanctions screen validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Check permissions
    if !auth.has_permission("sanctions:screen") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.sanctions_screener.screen_name(&request.name).await {
        Ok(screening_result) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": screening_result
            })))
        }
        Err(e) => {
            error!("Failed to screen against sanctions: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// List sanctions lists handler
pub async fn list_sanctions_lists(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Listing sanctions lists for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("sanctions:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.sanctions_service.get_active_sanctions().await {
        Ok(sanctions_lists) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": sanctions_lists
            })))
        }
        Err(e) => {
            error!("Failed to list sanctions lists: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Update sanctions lists handler
pub async fn update_sanctions_lists(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Updating sanctions lists by user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("sanctions:update") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.update_sanctions_lists().await {
        Ok(update_result) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": update_result,
                "message": "Sanctions lists updated successfully"
            })))
        }
        Err(e) => {
            error!("Failed to update sanctions lists: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Generate SAR handler
pub async fn generate_sar(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<SarGenerationRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Generating SAR by user: {}", auth.user_id);

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("SAR generation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Check permissions
    if !auth.has_permission("reports:sar") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.aml_service.generate_sar(request).await {
        Ok(sar_report) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": sar_report,
                "message": "SAR generated successfully"
            })))
        }
        Err(e) => {
            error!("Failed to generate SAR: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get suspicious activity report handler
pub async fn get_suspicious_activity_report(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting suspicious activity report for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Generate comprehensive suspicious activity report
    let report_period = query.get("period").unwrap_or(&"30".to_string()).parse::<i64>().unwrap_or(30);
    let start_date = Utc::now() - chrono::Duration::days(report_period);

    // Query suspicious activities from database
    let suspicious_activities = state.aml_repository
        .get_suspicious_activities_by_date_range(start_date, Utc::now())
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Calculate report metrics
    let total_activities = suspicious_activities.len();
    let high_risk_count = suspicious_activities.iter()
        .filter(|activity| activity.risk_score > 80.0)
        .count();
    let medium_risk_count = suspicious_activities.iter()
        .filter(|activity| activity.risk_score > 50.0 && activity.risk_score <= 80.0)
        .count();

    // Group by activity type
    let mut activity_types = std::collections::HashMap::new();
    for activity in &suspicious_activities {
        *activity_types.entry(activity.activity_type.clone()).or_insert(0) += 1;
    }

    Ok(Json(serde_json::json!({
        "success": true,
        "data": {
            "report_type": "suspicious_activity",
            "generated_at": chrono::Utc::now(),
            "period_days": report_period,
            "summary": {
                "total_activities": total_activities,
                "high_risk_activities": high_risk_count,
                "medium_risk_activities": medium_risk_count,
                "low_risk_activities": total_activities - high_risk_count - medium_risk_count,
                "activity_types": activity_types
            },
            "activities": suspicious_activities.into_iter().take(100).collect::<Vec<_>>() // Limit to 100 for response size
        }
    })))
}

/// Get risk summary report handler
pub async fn get_risk_summary_report(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting risk summary report for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Parse query parameters for date range
    let start_date = query.get("start_date")
        .and_then(|d| chrono::DateTime::parse_from_rfc3339(d).ok())
        .map(|d| d.with_timezone(&chrono::Utc))
        .unwrap_or_else(|| chrono::Utc::now() - chrono::Duration::days(30));

    let end_date = query.get("end_date")
        .and_then(|d| chrono::DateTime::parse_from_rfc3339(d).ok())
        .map(|d| d.with_timezone(&chrono::Utc))
        .unwrap_or_else(|| chrono::Utc::now());

    let request = RiskSummaryRequest {
        start_date,
        end_date,
        organization_id: auth.organization_id,
        risk_levels: None,
    };

    match state.aml_service.get_risk_summary_report(request).await {
        Ok(report) => {
            Ok(Json(serde_json::json!({
                "success": true,
                "data": report
            })))
        }
        Err(e) => {
            error!("Failed to get risk summary report: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get compliance report handler
pub async fn get_compliance_report(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<HashMap<String, String>>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting compliance report for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    Ok(Json(serde_json::json!({
        "success": true,
        "data": {
            "report_type": "compliance",
            "generated_at": chrono::Utc::now(),
            "summary": "Compliance report functionality not yet implemented"
        }
    })))
}

/// Get monitoring rules handler
pub async fn get_monitoring_rules(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Getting monitoring rules for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("config:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    Ok(Json(serde_json::json!({
        "success": true,
        "data": [],
        "message": "Monitoring rules configuration not yet implemented"
    })))
}

/// Create monitoring rule handler
pub async fn create_monitoring_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Creating monitoring rule for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("config:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    Ok(Json(serde_json::json!({
        "success": true,
        "message": "Monitoring rule creation not yet implemented"
    })))
}

/// Update monitoring rule handler
pub async fn update_monitoring_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(rule_id): Path<Uuid>,
    Json(request): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Updating monitoring rule: {} for user: {}", rule_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("config:update") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    Ok(Json(serde_json::json!({
        "success": true,
        "message": "Monitoring rule update not yet implemented"
    })))
}

/// Delete monitoring rule handler
pub async fn delete_monitoring_rule(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(rule_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("Deleting monitoring rule: {} for user: {}", rule_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("config:delete") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return a placeholder response
    Ok(Json(serde_json::json!({
        "success": true,
        "message": "Monitoring rule deletion not yet implemented"
    })))
}
