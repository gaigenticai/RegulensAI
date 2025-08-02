//! Data models for the Compliance Service

use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

/// Policy management models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreatePolicyRequest {
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub policy_type: PolicyType,
    
    #[validate(length(min = 1))]
    pub content: String,
    
    pub effective_date: NaiveDate,
    pub review_date: NaiveDate,
    pub tags: Vec<String>,
    pub owner_id: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PolicyType {
    Security,
    Privacy,
    Operational,
    Financial,
    Regulatory,
    HR,
    IT,
    Risk,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PolicyStatus {
    Draft,
    UnderReview,
    Approved,
    Active,
    Retired,
    Superseded,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyApprovalRequest {
    pub approved_by: Uuid,
    pub approval_notes: Option<String>,
    pub conditions: Option<Vec<String>>,
}

/// Control framework models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateControlRequest {
    #[validate(length(min = 1, max = 100))]
    pub control_id: String,
    
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub control_type: ControlType,
    pub frequency: ControlFrequency,
    pub owner_id: Uuid,
    pub policy_id: Option<Uuid>,
    pub evidence_requirements: Vec<String>,
    pub testing_procedures: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ControlType {
    Preventive,
    Detective,
    Corrective,
    Compensating,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ControlFrequency {
    Continuous,
    Daily,
    Weekly,
    Monthly,
    Quarterly,
    SemiAnnually,
    Annually,
    AdHoc,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ControlStatus {
    NotImplemented,
    InProgress,
    Implemented,
    Operating,
    Deficient,
    Ineffective,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ControlEffectiveness {
    NotTested,
    Effective,
    PartiallyEffective,
    Ineffective,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ControlTestRequest {
    pub test_date: NaiveDate,
    pub tester_id: Uuid,
    pub test_method: String,
    pub sample_size: Option<i32>,
    pub test_procedures: Vec<String>,
    pub expected_results: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlTestResult {
    pub test_id: Uuid,
    pub control_id: Uuid,
    pub test_date: NaiveDate,
    pub tester_id: Uuid,
    pub effectiveness_rating: ControlEffectiveness,
    pub results: String,
    pub deficiencies: Vec<String>,
    pub recommendations: Vec<String>,
    pub evidence_collected: Vec<String>,
    pub next_test_date: Option<NaiveDate>,
}

/// Audit management models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateAuditRequest {
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub audit_type: AuditType,
    pub scope: Vec<String>,
    pub start_date: NaiveDate,
    pub end_date: NaiveDate,
    pub lead_auditor_id: Uuid,
    pub audit_team: Vec<Uuid>,
    pub framework: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuditType {
    Internal,
    External,
    Regulatory,
    Certification,
    Vendor,
    IT,
    Financial,
    Operational,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuditStatus {
    Planning,
    InProgress,
    FieldworkComplete,
    Reporting,
    Complete,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateAuditFindingRequest {
    pub audit_id: Uuid,
    
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1))]
    pub description: String,
    
    pub severity: FindingSeverity,
    pub category: String,
    pub control_id: Option<Uuid>,
    pub recommendation: String,
    pub management_response: Option<String>,
    pub target_resolution_date: Option<NaiveDate>,
    pub responsible_party: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FindingSeverity {
    Critical,
    High,
    Medium,
    Low,
    Informational,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FindingStatus {
    Open,
    InProgress,
    Resolved,
    Closed,
    Accepted,
}

/// Third-party risk management models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateVendorRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    
    #[validate(length(min = 1, max = 255))]
    pub legal_name: String,
    
    pub vendor_type: VendorType,
    pub criticality: VendorCriticality,
    pub services_provided: Vec<String>,
    pub contact_info: VendorContactInfo,
    pub address: AddressInfo,
    pub contract_start_date: Option<NaiveDate>,
    pub contract_end_date: Option<NaiveDate>,
    pub data_access_level: DataAccessLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VendorType {
    Technology,
    Professional,
    Outsourcing,
    Cloud,
    Financial,
    Legal,
    Consulting,
    Other,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VendorCriticality {
    Critical,
    High,
    Medium,
    Low,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DataAccessLevel {
    None,
    Public,
    Internal,
    Confidential,
    Restricted,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VendorContactInfo {
    pub primary_contact: String,
    pub email: String,
    pub phone: String,
    pub security_contact: Option<String>,
    pub security_email: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressInfo {
    pub street_address: String,
    pub city: String,
    pub state_province: Option<String>,
    pub postal_code: Option<String>,
    pub country: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct VendorRiskAssessmentRequest {
    pub vendor_id: Uuid,
    pub assessor_id: Uuid,
    pub assessment_date: NaiveDate,
    pub assessment_type: AssessmentType,
    pub questionnaire_responses: serde_json::Value,
    pub security_controls: Vec<String>,
    pub compliance_certifications: Vec<String>,
    pub identified_risks: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AssessmentType {
    Initial,
    Annual,
    Triggered,
    Contract,
    Incident,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VendorRiskScore {
    pub overall_score: f64,
    pub security_score: f64,
    pub operational_score: f64,
    pub financial_score: f64,
    pub compliance_score: f64,
    pub risk_level: VendorRiskLevel,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VendorRiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// Regulatory mapping models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegulationInfo {
    pub id: Uuid,
    pub name: String,
    pub jurisdiction: String,
    pub category: String,
    pub effective_date: NaiveDate,
    pub last_updated: NaiveDate,
    pub requirements_count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegulationRequirement {
    pub id: Uuid,
    pub regulation_id: Uuid,
    pub requirement_id: String,
    pub title: String,
    pub description: String,
    pub category: String,
    pub mandatory: bool,
    pub controls: Vec<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateRegulationMappingRequest {
    pub regulation_id: Uuid,
    pub requirement_id: Uuid,
    pub control_id: Uuid,
    pub mapping_type: MappingType,
    pub coverage_level: CoverageLevel,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MappingType {
    Direct,
    Indirect,
    Partial,
    Compensating,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CoverageLevel {
    Full,
    Partial,
    Minimal,
    None,
}

/// Compliance reporting models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceDashboard {
    pub overall_compliance_score: f64,
    pub policy_compliance: PolicyComplianceMetrics,
    pub control_effectiveness: ControlEffectivenessMetrics,
    pub audit_status: AuditStatusMetrics,
    pub vendor_risk: VendorRiskMetrics,
    pub recent_activities: Vec<ComplianceActivity>,
    pub upcoming_deadlines: Vec<ComplianceDeadline>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyComplianceMetrics {
    pub total_policies: i32,
    pub active_policies: i32,
    pub policies_due_for_review: i32,
    pub policies_under_review: i32,
    pub compliance_percentage: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlEffectivenessMetrics {
    pub total_controls: i32,
    pub effective_controls: i32,
    pub partially_effective_controls: i32,
    pub ineffective_controls: i32,
    pub controls_due_for_testing: i32,
    pub effectiveness_percentage: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditStatusMetrics {
    pub total_audits: i32,
    pub completed_audits: i32,
    pub in_progress_audits: i32,
    pub planned_audits: i32,
    pub open_findings: i32,
    pub critical_findings: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VendorRiskMetrics {
    pub total_vendors: i32,
    pub critical_vendors: i32,
    pub high_risk_vendors: i32,
    pub assessments_due: i32,
    pub contracts_expiring: i32,
    pub average_risk_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceActivity {
    pub activity_type: String,
    pub description: String,
    pub timestamp: DateTime<Utc>,
    pub user_id: Uuid,
    pub entity_id: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceDeadline {
    pub deadline_type: String,
    pub title: String,
    pub due_date: NaiveDate,
    pub priority: String,
    pub responsible_party: Option<Uuid>,
    pub entity_id: Option<Uuid>,
}

/// Workflow models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowDefinition {
    pub id: Uuid,
    pub name: String,
    pub description: String,
    pub workflow_type: WorkflowType,
    pub trigger_conditions: serde_json::Value,
    pub steps: Vec<WorkflowStep>,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkflowType {
    PolicyApproval,
    ControlTesting,
    AuditManagement,
    VendorOnboarding,
    IncidentResponse,
    ComplianceReview,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStep {
    pub step_id: String,
    pub step_type: WorkflowStepType,
    pub name: String,
    pub description: String,
    pub assignee: Option<Uuid>,
    pub due_date_offset: Option<i32>,
    pub conditions: serde_json::Value,
    pub actions: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkflowStepType {
    Manual,
    Automated,
    Approval,
    Notification,
    Integration,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowExecution {
    pub id: Uuid,
    pub workflow_id: Uuid,
    pub entity_id: Uuid,
    pub entity_type: String,
    pub status: WorkflowStatus,
    pub current_step: Option<String>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub step_history: Vec<WorkflowStepExecution>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkflowStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStepExecution {
    pub step_id: String,
    pub status: WorkflowStepStatus,
    pub assignee: Option<Uuid>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub notes: Option<String>,
    pub output: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkflowStepStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
    Skipped,
}
