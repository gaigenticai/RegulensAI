//! Data models for the Fraud Detection Service

use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;
use rust_decimal::Decimal;
use std::collections::HashMap;

/// Transaction fraud detection models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct TransactionFraudRequest {
    pub transaction_id: Uuid,
    pub customer_id: Uuid,
    pub account_id: Uuid,
    pub amount: Decimal,
    pub currency: String,
    pub transaction_type: TransactionType,
    pub merchant_id: Option<String>,
    pub merchant_category: Option<String>,
    pub location: Option<TransactionLocation>,
    pub device_info: Option<DeviceInfo>,
    pub timestamp: DateTime<Utc>,
    pub channel: TransactionChannel,
    pub payment_method: PaymentMethod,
    pub additional_data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TransactionType {
    Purchase,
    Withdrawal,
    Transfer,
    Deposit,
    Payment,
    Refund,
    Reversal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TransactionChannel {
    Online,
    Mobile,
    ATM,
    Branch,
    Phone,
    Mail,
    PointOfSale,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PaymentMethod {
    CreditCard,
    DebitCard,
    BankTransfer,
    DigitalWallet,
    Cryptocurrency,
    Check,
    Cash,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionLocation {
    pub latitude: f64,
    pub longitude: f64,
    pub country: String,
    pub city: Option<String>,
    pub ip_address: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub device_id: String,
    pub device_type: DeviceType,
    pub operating_system: Option<String>,
    pub browser: Option<String>,
    pub user_agent: Option<String>,
    pub screen_resolution: Option<String>,
    pub timezone: Option<String>,
    pub language: Option<String>,
    pub fingerprint_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DeviceType {
    Desktop,
    Mobile,
    Tablet,
    ATM,
    POS,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudDetectionResult {
    pub transaction_id: Uuid,
    pub fraud_score: f64,
    pub risk_level: RiskLevel,
    pub decision: FraudDecision,
    pub triggered_rules: Vec<TriggeredRule>,
    pub model_scores: Vec<ModelScore>,
    pub risk_factors: Vec<RiskFactor>,
    pub recommended_action: RecommendedAction,
    pub confidence_score: f64,
    pub processing_time_ms: u64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FraudDecision {
    Approve,
    Review,
    Decline,
    Block,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggeredRule {
    pub rule_id: Uuid,
    pub rule_name: String,
    pub rule_type: RuleType,
    pub score_contribution: f64,
    pub threshold_exceeded: bool,
    pub details: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RuleType {
    Velocity,
    Amount,
    Location,
    Device,
    Behavioral,
    Network,
    Blacklist,
    Whitelist,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelScore {
    pub model_id: Uuid,
    pub model_name: String,
    pub model_type: ModelType,
    pub score: f64,
    pub confidence: f64,
    pub features_used: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ModelType {
    LogisticRegression,
    RandomForest,
    GradientBoosting,
    NeuralNetwork,
    SVM,
    Ensemble,
    DeepLearning,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactor {
    pub factor_name: String,
    pub factor_type: RiskFactorType,
    pub impact_score: f64,
    pub description: String,
    pub evidence: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskFactorType {
    Velocity,
    Amount,
    Location,
    Time,
    Device,
    Behavioral,
    Historical,
    Network,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RecommendedAction {
    Approve,
    RequestAdditionalAuth,
    ManualReview,
    Decline,
    BlockCard,
    ContactCustomer,
    EscalateToInvestigator,
}

/// Identity fraud detection models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct IdentityFraudRequest {
    pub application_id: Uuid,
    pub customer_id: Option<Uuid>,
    pub personal_info: PersonalInfo,
    pub documents: Vec<DocumentInfo>,
    pub biometric_data: Option<BiometricData>,
    pub device_info: Option<DeviceInfo>,
    pub application_source: ApplicationSource,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonalInfo {
    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: NaiveDate,
    pub ssn: Option<String>,
    pub phone_number: String,
    pub email: String,
    pub address: AddressInfo,
    pub employment_info: Option<EmploymentInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressInfo {
    pub street_address: String,
    pub city: String,
    pub state: String,
    pub postal_code: String,
    pub country: String,
    pub address_type: AddressType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AddressType {
    Residential,
    Business,
    MailingOnly,
    Temporary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmploymentInfo {
    pub employer_name: String,
    pub job_title: String,
    pub employment_status: EmploymentStatus,
    pub annual_income: Option<Decimal>,
    pub employment_duration_months: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EmploymentStatus {
    Employed,
    SelfEmployed,
    Unemployed,
    Retired,
    Student,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentInfo {
    pub document_type: DocumentType,
    pub document_number: String,
    pub issuing_authority: String,
    pub issue_date: Option<NaiveDate>,
    pub expiry_date: Option<NaiveDate>,
    pub document_image_hash: Option<String>,
    pub verification_status: DocumentVerificationStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DocumentType {
    DriversLicense,
    Passport,
    NationalID,
    SocialSecurityCard,
    BirthCertificate,
    UtilityBill,
    BankStatement,
    PayStub,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DocumentVerificationStatus {
    NotVerified,
    Verified,
    Failed,
    Suspicious,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BiometricData {
    pub fingerprint_hash: Option<String>,
    pub facial_recognition_hash: Option<String>,
    pub voice_print_hash: Option<String>,
    pub behavioral_biometrics: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ApplicationSource {
    Online,
    Mobile,
    Branch,
    Phone,
    Mail,
    Agent,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityFraudResult {
    pub application_id: Uuid,
    pub identity_fraud_score: f64,
    pub synthetic_id_score: f64,
    pub document_fraud_score: f64,
    pub overall_risk_level: RiskLevel,
    pub decision: IdentityDecision,
    pub fraud_indicators: Vec<FraudIndicator>,
    pub verification_results: Vec<VerificationResult>,
    pub recommended_actions: Vec<RecommendedAction>,
    pub confidence_score: f64,
    pub processing_time_ms: u64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IdentityDecision {
    Accept,
    Review,
    Reject,
    RequestAdditionalDocuments,
    RequireInPersonVerification,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudIndicator {
    pub indicator_type: FraudIndicatorType,
    pub severity: IndicatorSeverity,
    pub description: String,
    pub evidence: serde_json::Value,
    pub score_impact: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FraudIndicatorType {
    SyntheticIdentity,
    DocumentForgery,
    IdentityTheft,
    AddressFraud,
    PhoneFraud,
    EmailFraud,
    EmploymentFraud,
    BiometricMismatch,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IndicatorSeverity {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    pub verification_type: VerificationType,
    pub status: VerificationStatus,
    pub confidence: f64,
    pub details: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerificationType {
    SSNVerification,
    AddressVerification,
    PhoneVerification,
    EmailVerification,
    DocumentVerification,
    BiometricVerification,
    EmploymentVerification,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VerificationStatus {
    Verified,
    Failed,
    Partial,
    Unavailable,
}

/// Fraud case management models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateFraudCaseRequest {
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub case_type: FraudCaseType,
    pub priority: CasePriority,
    pub customer_id: Option<Uuid>,
    pub transaction_ids: Vec<Uuid>,
    pub suspected_fraud_amount: Option<Decimal>,
    pub currency: Option<String>,
    pub assigned_investigator: Option<Uuid>,
    pub source: CaseSource,
    pub additional_data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FraudCaseType {
    TransactionFraud,
    IdentityFraud,
    ApplicationFraud,
    FirstPartyFraud,
    InsiderFraud,
    AccountTakeover,
    SyntheticIdentity,
    DocumentFraud,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CasePriority {
    Low,
    Medium,
    High,
    Critical,
    Emergency,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CaseSource {
    AutomaticDetection,
    CustomerReport,
    InternalAudit,
    ExternalTip,
    RegulatoryNotification,
    PartnerAlert,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CaseStatus {
    Open,
    InProgress,
    UnderReview,
    Closed,
    Escalated,
    OnHold,
}

/// Fraud rule models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateFraudRuleRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub rule_type: RuleType,
    pub conditions: Vec<RuleCondition>,
    pub actions: Vec<RuleAction>,
    pub threshold: Option<f64>,
    pub weight: f64,
    pub is_active: bool,
    pub applies_to: Vec<String>,
    pub priority: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleCondition {
    pub field: String,
    pub operator: ConditionOperator,
    pub value: serde_json::Value,
    pub data_type: DataType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConditionOperator {
    Equals,
    NotEquals,
    GreaterThan,
    LessThan,
    GreaterThanOrEqual,
    LessThanOrEqual,
    Contains,
    NotContains,
    StartsWith,
    EndsWith,
    In,
    NotIn,
    Between,
    IsNull,
    IsNotNull,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DataType {
    String,
    Number,
    Boolean,
    Date,
    Array,
    Object,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleAction {
    pub action_type: ActionType,
    pub parameters: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActionType {
    AddScore,
    SetDecision,
    CreateAlert,
    BlockTransaction,
    RequireAuth,
    LogEvent,
    SendNotification,
    EscalateCase,
}

/// Behavioral analytics models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehaviorProfile {
    pub customer_id: Uuid,
    pub profile_type: ProfileType,
    pub behavioral_patterns: Vec<BehavioralPattern>,
    pub baseline_metrics: BaselineMetrics,
    pub anomaly_thresholds: AnomalyThresholds,
    pub last_updated: DateTime<Utc>,
    pub confidence_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProfileType {
    Transaction,
    Login,
    Navigation,
    Communication,
    Application,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehavioralPattern {
    pub pattern_name: String,
    pub pattern_type: PatternType,
    pub frequency: f64,
    pub typical_values: Vec<f64>,
    pub variance: f64,
    pub seasonality: Option<SeasonalityInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PatternType {
    Temporal,
    Amount,
    Location,
    Device,
    Channel,
    Frequency,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaselineMetrics {
    pub average_transaction_amount: Decimal,
    pub transaction_frequency: f64,
    pub preferred_channels: Vec<String>,
    pub typical_locations: Vec<String>,
    pub common_merchants: Vec<String>,
    pub usual_transaction_times: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyThresholds {
    pub amount_deviation_threshold: f64,
    pub frequency_deviation_threshold: f64,
    pub location_deviation_threshold: f64,
    pub time_deviation_threshold: f64,
    pub overall_anomaly_threshold: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeasonalityInfo {
    pub seasonal_type: SeasonalType,
    pub period: i32,
    pub amplitude: f64,
    pub phase: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SeasonalType {
    Daily,
    Weekly,
    Monthly,
    Quarterly,
    Yearly,
}

/// Graph analytics models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudNetwork {
    pub network_id: Uuid,
    pub network_type: NetworkType,
    pub entities: Vec<NetworkEntity>,
    pub relationships: Vec<NetworkRelationship>,
    pub risk_score: f64,
    pub suspicious_patterns: Vec<SuspiciousPattern>,
    pub created_at: DateTime<Utc>,
    pub last_analyzed: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NetworkType {
    TransactionNetwork,
    IdentityNetwork,
    DeviceNetwork,
    LocationNetwork,
    MerchantNetwork,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkEntity {
    pub entity_id: String,
    pub entity_type: EntityType,
    pub attributes: HashMap<String, serde_json::Value>,
    pub risk_score: f64,
    pub centrality_measures: CentralityMeasures,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EntityType {
    Customer,
    Account,
    Device,
    Location,
    Merchant,
    Transaction,
    PhoneNumber,
    EmailAddress,
    IPAddress,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CentralityMeasures {
    pub degree_centrality: f64,
    pub betweenness_centrality: f64,
    pub closeness_centrality: f64,
    pub eigenvector_centrality: f64,
    pub pagerank: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkRelationship {
    pub source_entity: String,
    pub target_entity: String,
    pub relationship_type: RelationshipType,
    pub strength: f64,
    pub attributes: HashMap<String, serde_json::Value>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RelationshipType {
    Transaction,
    SharedDevice,
    SharedLocation,
    SharedContact,
    SharedAddress,
    SharedPaymentMethod,
    SimilarBehavior,
    TemporalProximity,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuspiciousPattern {
    pub pattern_name: String,
    pub pattern_type: SuspiciousPatternType,
    pub description: String,
    pub entities_involved: Vec<String>,
    pub risk_score: f64,
    pub evidence: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SuspiciousPatternType {
    CircularTransactions,
    RapidFireTransactions,
    UnusualConnections,
    HighRiskClusters,
    AnomalousPathways,
    SuspiciousHubs,
}

/// Reporting models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudDashboard {
    pub total_transactions_analyzed: u64,
    pub fraud_detection_rate: f64,
    pub false_positive_rate: f64,
    pub total_fraud_prevented: Decimal,
    pub active_cases: u32,
    pub high_risk_alerts: u32,
    pub model_performance: Vec<ModelPerformanceMetric>,
    pub fraud_trends: FraudTrends,
    pub top_fraud_types: Vec<FraudTypeStatistic>,
    pub geographic_distribution: serde_json::Value,
    pub generated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPerformanceMetric {
    pub model_id: Uuid,
    pub model_name: String,
    pub accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1_score: f64,
    pub auc_roc: f64,
    pub false_positive_rate: f64,
    pub last_evaluated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudTrends {
    pub daily_fraud_attempts: Vec<DailyFraudStat>,
    pub fraud_by_channel: HashMap<String, u32>,
    pub fraud_by_amount_range: HashMap<String, u32>,
    pub seasonal_patterns: Vec<SeasonalPattern>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyFraudStat {
    pub date: NaiveDate,
    pub fraud_attempts: u32,
    pub fraud_prevented: u32,
    pub total_amount: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudTypeStatistic {
    pub fraud_type: String,
    pub count: u32,
    pub percentage: f64,
    pub total_amount: Decimal,
    pub trend: TrendDirection,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrendDirection {
    Increasing,
    Decreasing,
    Stable,
    Volatile,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeasonalPattern {
    pub pattern_name: String,
    pub period: String,
    pub peak_times: Vec<String>,
    pub impact_factor: f64,
}
