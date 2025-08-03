//! HTTP handlers for the Compliance Service API endpoints

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

    pub fn success_with_message(data: T, message: String) -> Self {
        Self {
            success: true,
            data: Some(data),
            message: Some(message),
            error: None,
        }
    }
}

impl ApiResponse<()> {
    pub fn error(error: String) -> Self {
        Self {
            success: false,
            data: None,
            message: None,
            error: Some(error),
        }
    }
}

// Policy Management Handlers

/// List policies with pagination and filtering
pub async fn list_policies(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(pagination): Query<PaginationQuery>,
    Query(filters): Query<HashMap<String, String>>,
) -> Result<Json<ApiResponse<serde_json::Value>>, StatusCode> {
    info!("Listing policies for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    let filter_json = if filters.is_empty() {
        None
    } else {
        Some(serde_json::to_value(filters).unwrap())
    };

    match state.compliance_service.policy_service.list_policies(
        pagination.page,
        pagination.per_page,
        filter_json,
    ).await {
        Ok((policies, total_pages)) => {
            let response_data = serde_json::json!({
                "policies": policies,
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": total_pages
                }
            });
            Ok(Json(ApiResponse::success(response_data)))
        }
        Err(e) => {
            error!("Failed to list policies: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Create a new policy
pub async fn create_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreatePolicyRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::policies::Model>>, StatusCode> {
    info!("Creating policy: {} by user: {}", request.title, auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Policy creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    match state.compliance_service.policy_service.create_policy(request, auth.user_id).await {
        Ok(policy) => {
            info!("Policy created successfully: {}", policy.id);
            Ok(Json(ApiResponse::success_with_message(
                policy,
                "Policy created successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to create policy: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get policy by ID
pub async fn get_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(policy_id): Path<Uuid>,
) -> Result<Json<ApiResponse<regulateai_database::entities::policies::Model>>, StatusCode> {
    info!("Getting policy: {} for user: {}", policy_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.policy_service.get_policy(policy_id).await {
        Ok(policy) => Ok(Json(ApiResponse::success(policy))),
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get policy: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Update policy
pub async fn update_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(policy_id): Path<Uuid>,
    Json(request): Json<CreatePolicyRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::policies::Model>>, StatusCode> {
    info!("Updating policy: {} by user: {}", policy_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:update") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Update the policy using the repository
    match state.policy_repository.update_policy(policy_id, request, auth.user_id).await {
        Ok(updated_policy) => Ok(Json(ApiResponse::success(updated_policy))),
        Err(RegulateAIError::NotFound(_)) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to update policy: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Delete policy
pub async fn delete_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(policy_id): Path<Uuid>,
) -> Result<Json<ApiResponse<()>>, StatusCode> {
    info!("Deleting policy: {} by user: {}", policy_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:delete") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    // In a full implementation, this would soft-delete the policy
    Err(StatusCode::NOT_IMPLEMENTED)
}

/// Approve policy
pub async fn approve_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(policy_id): Path<Uuid>,
    Json(request): Json<PolicyApprovalRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::policies::Model>>, StatusCode> {
    info!("Approving policy: {} by user: {}", policy_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:approve") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.policy_service.approve_policy(policy_id, request).await {
        Ok(policy) => {
            info!("Policy approved successfully: {}", policy_id);
            Ok(Json(ApiResponse::success_with_message(
                policy,
                "Policy approved successfully".to_string(),
            )))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to approve policy: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Review policy
pub async fn review_policy(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(policy_id): Path<Uuid>,
) -> Result<Json<ApiResponse<()>>, StatusCode> {
    info!("Reviewing policy: {} by user: {}", policy_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("policies:review") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    // In a full implementation, this would initiate policy review workflow
    Err(StatusCode::NOT_IMPLEMENTED)
}

// Control Framework Handlers

/// List controls
pub async fn list_controls(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(pagination): Query<PaginationQuery>,
    Query(filters): Query<HashMap<String, String>>,
) -> Result<Json<ApiResponse<serde_json::Value>>, StatusCode> {
    info!("Listing controls for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("controls:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    let filter_json = if filters.is_empty() {
        None
    } else {
        Some(serde_json::to_value(filters).unwrap())
    };

    match state.compliance_service.control_service.list_controls(
        pagination.page,
        pagination.per_page,
        filter_json,
    ).await {
        Ok((controls, total_pages)) => {
            let response_data = serde_json::json!({
                "controls": controls,
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": total_pages
                }
            });
            Ok(Json(ApiResponse::success(response_data)))
        }
        Err(e) => {
            error!("Failed to list controls: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Create control
pub async fn create_control(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateControlRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::controls::Model>>, StatusCode> {
    info!("Creating control: {} by user: {}", request.title, auth.user_id);

    // Check permissions
    if !auth.has_permission("controls:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Control creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    match state.compliance_service.control_service.create_control(request, auth.user_id).await {
        Ok(control) => {
            info!("Control created successfully: {}", control.id);
            Ok(Json(ApiResponse::success_with_message(
                control,
                "Control created successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to create control: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get control by ID
pub async fn get_control(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(control_id): Path<Uuid>,
) -> Result<Json<ApiResponse<regulateai_database::entities::controls::Model>>, StatusCode> {
    info!("Getting control: {} for user: {}", control_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("controls:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.control_service.get_control(control_id).await {
        Ok(control) => Ok(Json(ApiResponse::success(control))),
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get control: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Update control
pub async fn update_control(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(control_id): Path<Uuid>,
    Json(request): Json<CreateControlRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::controls::Model>>, StatusCode> {
    info!("Updating control: {} by user: {}", control_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("controls:update") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    Err(StatusCode::NOT_IMPLEMENTED)
}

/// Test control
pub async fn test_control(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(control_id): Path<Uuid>,
    Json(request): Json<ControlTestRequest>,
) -> Result<Json<ApiResponse<ControlTestResult>>, StatusCode> {
    info!("Testing control: {} by user: {}", control_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("controls:test") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Control test validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    match state.compliance_service.control_service.test_control(control_id, request).await {
        Ok(test_result) => {
            info!("Control test completed: {}", test_result.test_id);
            Ok(Json(ApiResponse::success_with_message(
                test_result,
                "Control test completed successfully".to_string(),
            )))
        }
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to test control: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Upload control evidence
pub async fn upload_control_evidence(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(control_id): Path<Uuid>,
) -> Result<Json<ApiResponse<()>>, StatusCode> {
    info!("Uploading evidence for control: {} by user: {}", control_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("controls:evidence") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    // In a full implementation, this would handle file uploads
    Err(StatusCode::NOT_IMPLEMENTED)
}

// Audit Management Handlers

/// List audits
pub async fn list_audits(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(pagination): Query<PaginationQuery>,
    Query(filters): Query<HashMap<String, String>>,
) -> Result<Json<ApiResponse<serde_json::Value>>, StatusCode> {
    info!("Listing audits for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("audits:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    let filter_json = if filters.is_empty() {
        None
    } else {
        Some(serde_json::to_value(filters).unwrap())
    };

    match state.compliance_service.audit_service.list_audits(
        pagination.page,
        pagination.per_page,
        filter_json,
    ).await {
        Ok((audits, total_pages)) => {
            let response_data = serde_json::json!({
                "audits": audits,
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": total_pages
                }
            });
            Ok(Json(ApiResponse::success(response_data)))
        }
        Err(e) => {
            error!("Failed to list audits: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Create audit
pub async fn create_audit(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateAuditRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::audits::Model>>, StatusCode> {
    info!("Creating audit: {} by user: {}", request.title, auth.user_id);

    // Check permissions
    if !auth.has_permission("audits:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Audit creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    match state.compliance_service.audit_service.create_audit(request, auth.user_id).await {
        Ok(audit) => {
            info!("Audit created successfully: {}", audit.id);
            Ok(Json(ApiResponse::success_with_message(
                audit,
                "Audit created successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to create audit: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get audit by ID
pub async fn get_audit(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(audit_id): Path<Uuid>,
) -> Result<Json<ApiResponse<regulateai_database::entities::audits::Model>>, StatusCode> {
    info!("Getting audit: {} for user: {}", audit_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("audits:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.audit_service.get_audit(audit_id).await {
        Ok(audit) => Ok(Json(ApiResponse::success(audit))),
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get audit: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get audit findings
pub async fn get_audit_findings(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(audit_id): Path<Uuid>,
) -> Result<Json<ApiResponse<Vec<regulateai_database::entities::audit_findings::Model>>>, StatusCode> {
    info!("Getting findings for audit: {} by user: {}", audit_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("audits:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Fetch findings from the repository
    match state.audit_repository.get_audit_findings(audit_id).await {
        Ok(findings) => Ok(Json(ApiResponse::success(findings))),
        Err(RegulateAIError::NotFound(_)) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get audit findings: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Create audit finding
pub async fn create_audit_finding(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(audit_id): Path<Uuid>,
    Json(mut request): Json<CreateAuditFindingRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::audit_findings::Model>>, StatusCode> {
    info!("Creating finding for audit: {} by user: {}", audit_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("audits:create_finding") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Audit finding creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Ensure audit_id matches path parameter
    request.audit_id = audit_id;

    match state.compliance_service.audit_service.create_audit_finding(request, auth.user_id).await {
        Ok(finding) => {
            info!("Audit finding created successfully: {}", finding.id);
            Ok(Json(ApiResponse::success_with_message(
                finding,
                "Audit finding created successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to create audit finding: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Complete audit
pub async fn complete_audit(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(audit_id): Path<Uuid>,
) -> Result<Json<ApiResponse<()>>, StatusCode> {
    info!("Completing audit: {} by user: {}", audit_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("audits:complete") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    // In a full implementation, this would mark the audit as complete
    Err(StatusCode::NOT_IMPLEMENTED)
}

// Vendor Management Handlers

/// List vendors
pub async fn list_vendors(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Query(pagination): Query<PaginationQuery>,
    Query(filters): Query<HashMap<String, String>>,
) -> Result<Json<ApiResponse<serde_json::Value>>, StatusCode> {
    info!("Listing vendors for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("vendors:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    let filter_json = if filters.is_empty() {
        None
    } else {
        Some(serde_json::to_value(filters).unwrap())
    };

    match state.compliance_service.vendor_service.list_vendors(
        pagination.page,
        pagination.per_page,
        filter_json,
    ).await {
        Ok((vendors, total_pages)) => {
            let response_data = serde_json::json!({
                "vendors": vendors,
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total_pages": total_pages
                }
            });
            Ok(Json(ApiResponse::success(response_data)))
        }
        Err(e) => {
            error!("Failed to list vendors: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Create vendor
pub async fn create_vendor(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Json(request): Json<CreateVendorRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::vendors::Model>>, StatusCode> {
    info!("Creating vendor: {} by user: {}", request.name, auth.user_id);

    // Check permissions
    if !auth.has_permission("vendors:create") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Vendor creation validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    match state.compliance_service.vendor_service.create_vendor(request, auth.user_id).await {
        Ok(vendor) => {
            info!("Vendor created successfully: {}", vendor.id);
            Ok(Json(ApiResponse::success_with_message(
                vendor,
                "Vendor created successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to create vendor: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get vendor by ID
pub async fn get_vendor(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(vendor_id): Path<Uuid>,
) -> Result<Json<ApiResponse<regulateai_database::entities::vendors::Model>>, StatusCode> {
    info!("Getting vendor: {} for user: {}", vendor_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("vendors:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.vendor_service.get_vendor(vendor_id).await {
        Ok(vendor) => Ok(Json(ApiResponse::success(vendor))),
        Err(RegulateAIError::NotFound { .. }) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            error!("Failed to get vendor: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Assess vendor risk
pub async fn assess_vendor_risk(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(vendor_id): Path<Uuid>,
    Json(mut request): Json<VendorRiskAssessmentRequest>,
) -> Result<Json<ApiResponse<VendorRiskScore>>, StatusCode> {
    info!("Assessing risk for vendor: {} by user: {}", vendor_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("vendors:assess") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Vendor risk assessment validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Ensure vendor_id matches path parameter
    request.vendor_id = vendor_id;

    match state.compliance_service.vendor_service.assess_vendor_risk(request).await {
        Ok(risk_score) => {
            info!("Vendor risk assessment completed for vendor: {}", vendor_id);
            Ok(Json(ApiResponse::success_with_message(
                risk_score,
                "Vendor risk assessment completed successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to assess vendor risk: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get vendor contracts
pub async fn get_vendor_contracts(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(vendor_id): Path<Uuid>,
) -> Result<Json<ApiResponse<Vec<serde_json::Value>>>, StatusCode> {
    info!("Getting contracts for vendor: {} by user: {}", vendor_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("vendors:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return empty contracts
    // In a full implementation, this would fetch contracts from the repository
    Ok(Json(ApiResponse::success(vec![])))
}

// Regulatory Mapping Handlers

/// List regulations
pub async fn list_regulations(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<ApiResponse<Vec<RegulationInfo>>>, StatusCode> {
    info!("Listing regulations for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("regulations:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.regulatory_service.list_regulations().await {
        Ok(regulations) => Ok(Json(ApiResponse::success(regulations))),
        Err(e) => {
            error!("Failed to list regulations: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get regulation requirements
pub async fn get_regulation_requirements(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(regulation_id): Path<Uuid>,
) -> Result<Json<ApiResponse<Vec<RegulationRequirement>>>, StatusCode> {
    info!("Getting requirements for regulation: {} by user: {}", regulation_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("regulations:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.regulatory_service.get_regulation_requirements(regulation_id).await {
        Ok(requirements) => Ok(Json(ApiResponse::success(requirements))),
        Err(e) => {
            error!("Failed to get regulation requirements: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get regulation mapping
pub async fn get_regulation_mapping(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(regulation_id): Path<Uuid>,
) -> Result<Json<ApiResponse<Vec<serde_json::Value>>>, StatusCode> {
    info!("Getting mapping for regulation: {} by user: {}", regulation_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("regulations:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return empty mapping
    // In a full implementation, this would fetch mappings from the repository
    Ok(Json(ApiResponse::success(vec![])))
}

/// Create regulation mapping
pub async fn create_regulation_mapping(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(regulation_id): Path<Uuid>,
    Json(mut request): Json<CreateRegulationMappingRequest>,
) -> Result<Json<ApiResponse<regulateai_database::entities::regulation_mappings::Model>>, StatusCode> {
    info!("Creating mapping for regulation: {} by user: {}", regulation_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("regulations:map") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Validate request
    if let Err(validation_errors) = request.validate() {
        error!("Regulation mapping validation failed: {:?}", validation_errors);
        return Err(StatusCode::BAD_REQUEST);
    }

    // Ensure regulation_id matches path parameter
    request.regulation_id = regulation_id;

    match state.compliance_service.regulatory_service.create_regulation_mapping(request, auth.user_id).await {
        Ok(mapping) => {
            info!("Regulation mapping created successfully: {}", mapping.id);
            Ok(Json(ApiResponse::success_with_message(
                mapping,
                "Regulation mapping created successfully".to_string(),
            )))
        }
        Err(e) => {
            error!("Failed to create regulation mapping: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// Reporting Handlers

/// Get compliance dashboard
pub async fn get_compliance_dashboard(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<ApiResponse<ComplianceDashboard>>, StatusCode> {
    info!("Getting compliance dashboard for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    match state.compliance_service.get_compliance_dashboard().await {
        Ok(dashboard) => Ok(Json(ApiResponse::success(dashboard))),
        Err(e) => {
            error!("Failed to get compliance dashboard: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Get control effectiveness report
pub async fn get_control_effectiveness_report(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<ApiResponse<ControlEffectivenessMetrics>>, StatusCode> {
    info!("Getting control effectiveness report for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return sample metrics
    // In a full implementation, this would generate the actual report
    let metrics = ControlEffectivenessMetrics {
        total_controls: 0,
        effective_controls: 0,
        partially_effective_controls: 0,
        ineffective_controls: 0,
        controls_due_for_testing: 0,
        effectiveness_percentage: 0.0,
    };

    Ok(Json(ApiResponse::success(metrics)))
}

/// Get audit summary report
pub async fn get_audit_summary_report(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<ApiResponse<AuditStatusMetrics>>, StatusCode> {
    info!("Getting audit summary report for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Generate actual audit summary report from database
    let metrics = match state.audit_repository.get_audit_status_metrics().await {
        Ok(metrics) => metrics,
        Err(e) => {
            error!("Failed to get audit status metrics: {}", e);
            // Return default metrics if database query fails
            AuditStatusMetrics {
                total_audits: 0,
                completed_audits: 0,
                in_progress_audits: 0,
                planned_audits: 0,
                open_findings: 0,
                critical_findings: 0,
            }
        }
    };

    Ok(Json(ApiResponse::success(metrics)))
}

/// Get vendor risk report
pub async fn get_vendor_risk_report(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<ApiResponse<VendorRiskMetrics>>, StatusCode> {
    info!("Getting vendor risk report for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("reports:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return sample metrics
    // In a full implementation, this would generate the actual report
    let metrics = VendorRiskMetrics {
        total_vendors: 0,
        critical_vendors: 0,
        high_risk_vendors: 0,
        assessments_due: 0,
        contracts_expiring: 0,
        average_risk_score: 0.0,
    };

    Ok(Json(ApiResponse::success(metrics)))
}

// Workflow Handlers

/// List workflows
pub async fn list_workflows(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<ApiResponse<Vec<WorkflowDefinition>>>, StatusCode> {
    info!("Listing workflows for user: {}", auth.user_id);

    // Check permissions
    if !auth.has_permission("workflows:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // Fetch workflows from the repository
    match state.workflow_repository.list_workflows().await {
        Ok(workflows) => Ok(Json(ApiResponse::success(workflows))),
        Err(e) => {
            error!("Failed to list workflows: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

/// Execute workflow
pub async fn execute_workflow(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(workflow_id): Path<Uuid>,
) -> Result<Json<ApiResponse<WorkflowExecution>>, StatusCode> {
    info!("Executing workflow: {} by user: {}", workflow_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("workflows:execute") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    // In a full implementation, this would execute the workflow
    Err(StatusCode::NOT_IMPLEMENTED)
}

/// Get workflow status
pub async fn get_workflow_status(
    State(state): State<AppState>,
    Extension(auth): Extension<AuthContext>,
    Path(workflow_id): Path<Uuid>,
) -> Result<Json<ApiResponse<WorkflowExecution>>, StatusCode> {
    info!("Getting workflow status: {} for user: {}", workflow_id, auth.user_id);

    // Check permissions
    if !auth.has_permission("workflows:read") {
        return Err(StatusCode::FORBIDDEN);
    }

    // For now, return not implemented
    // In a full implementation, this would get workflow execution status
    Err(StatusCode::NOT_IMPLEMENTED)
}
