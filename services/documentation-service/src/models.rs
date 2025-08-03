//! Documentation Service Data Models
//! 
//! This module defines the core data structures for the documentation service including:
//! - Document models with metadata and versioning
//! - Content types and formatting structures
//! - Search and indexing models
//! - User permissions and access control models

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

/// Document model representing a single document in the system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    /// Unique document identifier
    pub id: Uuid,
    
    /// Document title
    pub title: String,
    
    /// Document slug for URL-friendly access
    pub slug: String,
    
    /// Document content in markdown format
    pub content: String,
    
    /// Document type classification
    pub document_type: DocumentType,
    
    /// Document category for organization
    pub category: String,
    
    /// Document tags for classification
    pub tags: Vec<String>,
    
    /// Document status
    pub status: DocumentStatus,
    
    /// Document visibility level
    pub visibility: VisibilityLevel,
    
    /// Document metadata
    pub metadata: DocumentMetadata,
    
    /// Current version number
    pub version: i32,
    
    /// Parent document ID (for hierarchical documents)
    pub parent_id: Option<Uuid>,
    
    /// Document order within parent (for sorting)
    pub sort_order: i32,
    
    /// Document language code
    pub language: String,
    
    /// Document creation timestamp
    pub created_at: DateTime<Utc>,
    
    /// Document last update timestamp
    pub updated_at: DateTime<Utc>,
    
    /// Document publication timestamp
    pub published_at: Option<DateTime<Utc>>,
    
    /// User who created the document
    pub created_by: Uuid,
    
    /// User who last updated the document
    pub updated_by: Uuid,
    
    /// Document approval information
    pub approval: Option<DocumentApproval>,
}

/// Document type enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DocumentType {
    /// Policy documents
    Policy,
    
    /// Procedure documents
    Procedure,
    
    /// Regulatory guidance
    Regulation,
    
    /// Training materials
    Training,
    
    /// API documentation
    ApiDocumentation,
    
    /// User guides
    UserGuide,
    
    /// Technical specifications
    TechnicalSpec,
    
    /// Compliance templates
    Template,
    
    /// Knowledge base articles
    KnowledgeBase,
    
    /// FAQ documents
    FAQ,
}

/// Document status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DocumentStatus {
    /// Document is in draft state
    Draft,
    
    /// Document is under review
    UnderReview,
    
    /// Document is approved for publication
    Approved,
    
    /// Document is published and active
    Published,
    
    /// Document is archived
    Archived,
    
    /// Document is deprecated
    Deprecated,
}

/// Document visibility levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum VisibilityLevel {
    /// Public - visible to all users
    Public,
    
    /// Internal - visible to organization members
    Internal,
    
    /// Restricted - visible to specific roles/users
    Restricted,
    
    /// Confidential - visible to authorized users only
    Confidential,
}

/// Document metadata structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentMetadata {
    /// Document description/summary
    pub description: Option<String>,
    
    /// Document keywords for search
    pub keywords: Vec<String>,
    
    /// Document author information
    pub author: Option<String>,
    
    /// Document reviewer information
    pub reviewer: Option<String>,
    
    /// Document effective date
    pub effective_date: Option<DateTime<Utc>>,
    
    /// Document expiration date
    pub expiration_date: Option<DateTime<Utc>>,
    
    /// Document review frequency in days
    pub review_frequency_days: Option<i32>,
    
    /// Next review due date
    pub next_review_date: Option<DateTime<Utc>>,
    
    /// Document compliance requirements
    pub compliance_requirements: Vec<String>,
    
    /// Related document IDs
    pub related_documents: Vec<Uuid>,
    
    /// External references and links
    pub external_references: Vec<ExternalReference>,
    
    /// Custom metadata fields
    pub custom_fields: HashMap<String, serde_json::Value>,
}

/// Document approval information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentApproval {
    /// Approval status
    pub status: ApprovalStatus,
    
    /// User who approved the document
    pub approved_by: Option<Uuid>,
    
    /// Approval timestamp
    pub approved_at: Option<DateTime<Utc>>,
    
    /// Approval comments
    pub comments: Option<String>,
    
    /// Required approvers
    pub required_approvers: Vec<Uuid>,
    
    /// Completed approvals
    pub completed_approvals: Vec<CompletedApproval>,
}

/// Approval status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ApprovalStatus {
    /// Pending approval
    Pending,
    
    /// Approved
    Approved,
    
    /// Rejected
    Rejected,
    
    /// Approval not required
    NotRequired,
}

/// Completed approval record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompletedApproval {
    /// User who provided approval
    pub approver_id: Uuid,
    
    /// Approval decision
    pub decision: ApprovalDecision,
    
    /// Approval timestamp
    pub approved_at: DateTime<Utc>,
    
    /// Approval comments
    pub comments: Option<String>,
}

/// Approval decision enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ApprovalDecision {
    Approve,
    Reject,
    RequestChanges,
}

/// External reference structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalReference {
    /// Reference title
    pub title: String,
    
    /// Reference URL
    pub url: String,
    
    /// Reference type
    pub reference_type: ReferenceType,
    
    /// Reference description
    pub description: Option<String>,
}

/// Reference type enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ReferenceType {
    /// Regulatory document
    Regulation,
    
    /// Industry standard
    Standard,
    
    /// External policy
    Policy,
    
    /// Research paper
    Research,
    
    /// Best practice guide
    BestPractice,
    
    /// Tool or system
    Tool,
    
    /// Other reference
    Other,
}

/// Document version model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentVersion {
    /// Version ID
    pub id: Uuid,
    
    /// Document ID this version belongs to
    pub document_id: Uuid,
    
    /// Version number
    pub version: i32,
    
    /// Version content
    pub content: String,
    
    /// Version metadata
    pub metadata: DocumentMetadata,
    
    /// Version change summary
    pub change_summary: String,
    
    /// Version creation timestamp
    pub created_at: DateTime<Utc>,
    
    /// User who created this version
    pub created_by: Uuid,
    
    /// Whether this is the current version
    pub is_current: bool,
}

/// Document template model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentTemplate {
    /// Template ID
    pub id: Uuid,
    
    /// Template name
    pub name: String,
    
    /// Template description
    pub description: String,
    
    /// Template content with placeholders
    pub content: String,
    
    /// Template type
    pub template_type: DocumentType,
    
    /// Template variables/placeholders
    pub variables: Vec<TemplateVariable>,
    
    /// Template metadata
    pub metadata: TemplateMetadata,
    
    /// Template creation timestamp
    pub created_at: DateTime<Utc>,
    
    /// Template last update timestamp
    pub updated_at: DateTime<Utc>,
    
    /// User who created the template
    pub created_by: Uuid,
    
    /// User who last updated the template
    pub updated_by: Uuid,
}

/// Template variable definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateVariable {
    /// Variable name
    pub name: String,
    
    /// Variable description
    pub description: String,
    
    /// Variable type
    pub variable_type: VariableType,
    
    /// Whether variable is required
    pub required: bool,
    
    /// Default value
    pub default_value: Option<String>,
    
    /// Validation rules
    pub validation: Option<VariableValidation>,
}

/// Template variable types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum VariableType {
    Text,
    Number,
    Date,
    Boolean,
    Select,
    MultiSelect,
    RichText,
}

/// Variable validation rules
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariableValidation {
    /// Minimum length (for text)
    pub min_length: Option<usize>,
    
    /// Maximum length (for text)
    pub max_length: Option<usize>,
    
    /// Pattern validation (regex)
    pub pattern: Option<String>,
    
    /// Allowed values (for select)
    pub allowed_values: Option<Vec<String>>,
    
    /// Minimum value (for numbers)
    pub min_value: Option<f64>,
    
    /// Maximum value (for numbers)
    pub max_value: Option<f64>,
}

/// Template metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateMetadata {
    /// Template category
    pub category: String,
    
    /// Template tags
    pub tags: Vec<String>,
    
    /// Template usage instructions
    pub usage_instructions: Option<String>,
    
    /// Template preview image
    pub preview_image: Option<String>,
    
    /// Template complexity level
    pub complexity_level: ComplexityLevel,
}

/// Template complexity levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ComplexityLevel {
    Simple,
    Intermediate,
    Advanced,
    Expert,
}

/// Search index model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchIndex {
    /// Index ID
    pub id: Uuid,
    
    /// Document ID being indexed
    pub document_id: Uuid,
    
    /// Indexed content (processed for search)
    pub indexed_content: String,
    
    /// Search keywords extracted from content
    pub keywords: Vec<String>,
    
    /// Document title for search results
    pub title: String,
    
    /// Document summary for search results
    pub summary: String,
    
    /// Document type for filtering
    pub document_type: DocumentType,
    
    /// Document category for filtering
    pub category: String,
    
    /// Document tags for filtering
    pub tags: Vec<String>,
    
    /// Document visibility level
    pub visibility: VisibilityLevel,
    
    /// Index creation timestamp
    pub indexed_at: DateTime<Utc>,
    
    /// Index last update timestamp
    pub updated_at: DateTime<Utc>,
}

/// Search query model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchQuery {
    /// Search query text
    pub query: String,
    
    /// Document type filters
    pub document_types: Option<Vec<DocumentType>>,
    
    /// Category filters
    pub categories: Option<Vec<String>>,
    
    /// Tag filters
    pub tags: Option<Vec<String>>,
    
    /// Date range filter
    pub date_range: Option<DateRange>,
    
    /// Visibility level filter
    pub visibility_levels: Option<Vec<VisibilityLevel>>,
    
    /// Search result limit
    pub limit: Option<usize>,
    
    /// Search result offset
    pub offset: Option<usize>,
    
    /// Sort order
    pub sort_by: Option<SortBy>,
}

/// Date range filter
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DateRange {
    /// Start date
    pub start_date: DateTime<Utc>,
    
    /// End date
    pub end_date: DateTime<Utc>,
}

/// Sort options for search results
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SortBy {
    Relevance,
    CreatedDate,
    UpdatedDate,
    Title,
    Category,
}

/// Search result model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    /// Document ID
    pub document_id: Uuid,
    
    /// Document title
    pub title: String,
    
    /// Document summary/excerpt
    pub summary: String,
    
    /// Document type
    pub document_type: DocumentType,
    
    /// Document category
    pub category: String,
    
    /// Document tags
    pub tags: Vec<String>,
    
    /// Search relevance score
    pub relevance_score: f64,
    
    /// Highlighted text snippets
    pub highlights: Vec<String>,
    
    /// Document URL/path
    pub url: String,
    
    /// Document last update timestamp
    pub updated_at: DateTime<Utc>,
}

/// User permission model for document access
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentPermission {
    /// Permission ID
    pub id: Uuid,
    
    /// Document ID
    pub document_id: Uuid,
    
    /// User ID (optional, for user-specific permissions)
    pub user_id: Option<Uuid>,
    
    /// Role ID (optional, for role-based permissions)
    pub role_id: Option<Uuid>,
    
    /// Permission type
    pub permission_type: PermissionType,
    
    /// Permission granted timestamp
    pub granted_at: DateTime<Utc>,
    
    /// Permission granted by user
    pub granted_by: Uuid,
    
    /// Permission expiration (optional)
    pub expires_at: Option<DateTime<Utc>>,
}

/// Permission types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PermissionType {
    /// Can view the document
    Read,
    
    /// Can edit the document
    Write,
    
    /// Can delete the document
    Delete,
    
    /// Can approve the document
    Approve,
    
    /// Can manage document permissions
    Admin,
}

/// Document analytics model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentAnalytics {
    /// Analytics ID
    pub id: Uuid,
    
    /// Document ID
    pub document_id: Uuid,
    
    /// View count
    pub view_count: i64,
    
    /// Download count
    pub download_count: i64,
    
    /// Share count
    pub share_count: i64,
    
    /// Average rating
    pub average_rating: Option<f64>,
    
    /// Rating count
    pub rating_count: i64,
    
    /// Last viewed timestamp
    pub last_viewed_at: Option<DateTime<Utc>>,
    
    /// Analytics last update timestamp
    pub updated_at: DateTime<Utc>,
}

impl Default for DocumentMetadata {
    fn default() -> Self {
        Self {
            description: None,
            keywords: Vec::new(),
            author: None,
            reviewer: None,
            effective_date: None,
            expiration_date: None,
            review_frequency_days: None,
            next_review_date: None,
            compliance_requirements: Vec::new(),
            related_documents: Vec::new(),
            external_references: Vec::new(),
            custom_fields: HashMap::new(),
        }
    }
}

impl Default for DocumentApproval {
    fn default() -> Self {
        Self {
            status: ApprovalStatus::NotRequired,
            approved_by: None,
            approved_at: None,
            comments: None,
            required_approvers: Vec::new(),
            completed_approvals: Vec::new(),
        }
    }
}

/// User guide home page data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserGuideHomeData {
    /// Current user context
    pub user: regulateai_auth::AuthContext,

    /// Available modules
    pub modules: Vec<ModuleInfo>,

    /// Quick start guides
    pub quick_start_guides: Vec<QuickStartGuide>,

    /// Search functionality enabled
    pub search_enabled: bool,

    /// Recent guide updates
    pub recent_updates: Vec<GuideUpdate>,
}

/// User guide module-specific data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserGuideModuleData {
    /// Current user context
    pub user: regulateai_auth::AuthContext,

    /// Module information
    pub module: ModuleGuideData,

    /// Module workflows
    pub workflows: Vec<WorkflowGuide>,

    /// Field references
    pub field_references: Vec<FieldReference>,

    /// Usage examples
    pub examples: Vec<UsageExample>,

    /// Troubleshooting guides
    pub troubleshooting: Vec<TroubleshootingItem>,
}

/// Module information structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleInfo {
    /// Module identifier
    pub id: String,

    /// Module display name
    pub name: String,

    /// Module description
    pub description: String,

    /// Module icon class
    pub icon: String,

    /// Module URL path
    pub url: String,

    /// Module status
    pub status: String,

    /// User roles that can access this module
    pub required_roles: Vec<String>,
}

/// Quick start guide structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuickStartGuide {
    /// Guide identifier
    pub id: String,

    /// Guide title
    pub title: String,

    /// Guide description
    pub description: String,

    /// Estimated completion time in minutes
    pub estimated_time: u32,

    /// Guide steps
    pub steps: Vec<GuideStep>,

    /// Required user role
    pub required_role: String,
}

/// Guide update information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuideUpdate {
    /// Update title
    pub title: String,

    /// Update description
    pub description: String,

    /// Update timestamp
    pub updated_at: DateTime<Utc>,

    /// Module affected
    pub module: String,

    /// Update type
    pub update_type: String,
}

/// Module guide data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleGuideData {
    /// Module identifier
    pub id: String,

    /// Module name
    pub name: String,

    /// Module description
    pub description: String,

    /// Module overview content
    pub overview: String,

    /// Getting started content
    pub getting_started: String,

    /// Key features
    pub key_features: Vec<String>,

    /// Prerequisites
    pub prerequisites: Vec<String>,
}

/// Workflow guide structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowGuide {
    /// Workflow identifier
    pub id: String,

    /// Workflow title
    pub title: String,

    /// Workflow description
    pub description: String,

    /// Workflow steps
    pub steps: Vec<WorkflowStep>,

    /// Estimated completion time
    pub estimated_time: u32,

    /// Required permissions
    pub required_permissions: Vec<String>,
}

/// Workflow step structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStep {
    /// Step number
    pub step_number: u32,

    /// Step title
    pub title: String,

    /// Step description
    pub description: String,

    /// Step instructions
    pub instructions: String,

    /// Screenshot or image URL
    pub screenshot_url: Option<String>,

    /// Tips and warnings
    pub tips: Vec<String>,

    /// Expected outcome
    pub expected_outcome: String,
}

/// Guide step structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuideStep {
    /// Step number
    pub step_number: u32,

    /// Step title
    pub title: String,

    /// Step content
    pub content: String,

    /// Code examples
    pub code_examples: Vec<CodeExample>,

    /// Related links
    pub related_links: Vec<String>,
}

/// Field reference structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldReference {
    /// Field name
    pub field_name: String,

    /// Field type
    pub field_type: String,

    /// Field description
    pub description: String,

    /// Whether field is required
    pub required: bool,

    /// Validation rules
    pub validation_rules: Vec<String>,

    /// Example values
    pub example_values: Vec<String>,

    /// Related fields
    pub related_fields: Vec<String>,
}

/// Usage example structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageExample {
    /// Example title
    pub title: String,

    /// Example description
    pub description: String,

    /// Example code or configuration
    pub code: String,

    /// Programming language or format
    pub language: String,

    /// Expected output
    pub expected_output: Option<String>,

    /// Notes and explanations
    pub notes: Vec<String>,
}

/// Code example structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeExample {
    /// Example title
    pub title: String,

    /// Code content
    pub code: String,

    /// Programming language
    pub language: String,

    /// Example description
    pub description: Option<String>,
}

/// Troubleshooting item structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TroubleshootingItem {
    /// Issue title
    pub title: String,

    /// Issue description
    pub description: String,

    /// Possible causes
    pub causes: Vec<String>,

    /// Solution steps
    pub solutions: Vec<String>,

    /// Related documentation links
    pub related_links: Vec<String>,

    /// Issue severity
    pub severity: String,
}
