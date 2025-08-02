//! Data models for the Risk Management Service

use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;
use rust_decimal::Decimal;

/// Risk assessment models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateRiskRequest {
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub risk_category: RiskCategory,
    pub risk_type: RiskType,
    pub business_unit: String,
    pub owner_id: Uuid,
    pub inherent_likelihood: LikelihoodRating,
    pub inherent_impact: ImpactRating,
    pub current_controls: Vec<String>,
    pub residual_likelihood: Option<LikelihoodRating>,
    pub residual_impact: Option<ImpactRating>,
    pub risk_appetite_threshold: Option<Decimal>,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskCategory {
    Operational,
    Financial,
    Strategic,
    Compliance,
    Reputational,
    Technology,
    Market,
    Credit,
    Liquidity,
    Environmental,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskType {
    ProcessRisk,
    SystemsRisk,
    PeopleRisk,
    ExternalRisk,
    ModelRisk,
    DataRisk,
    CyberRisk,
    RegulatoryRisk,
    ConcentrationRisk,
    CounterpartyRisk,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LikelihoodRating {
    VeryLow = 1,
    Low = 2,
    Medium = 3,
    High = 4,
    VeryHigh = 5,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ImpactRating {
    Negligible = 1,
    Minor = 2,
    Moderate = 3,
    Major = 4,
    Severe = 5,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskStatus {
    Identified,
    Assessed,
    Mitigated,
    Monitored,
    Closed,
    Escalated,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RiskAssessmentRequest {
    pub assessment_date: NaiveDate,
    pub assessor_id: Uuid,
    pub methodology: String,
    pub inherent_likelihood: LikelihoodRating,
    pub inherent_impact: ImpactRating,
    pub control_effectiveness: ControlEffectiveness,
    pub residual_likelihood: LikelihoodRating,
    pub residual_impact: ImpactRating,
    pub quantitative_impact: Option<Decimal>,
    pub assessment_notes: Option<String>,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ControlEffectiveness {
    NotEffective = 0,
    PartiallyEffective = 25,
    LargelyEffective = 75,
    FullyEffective = 100,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskScore {
    pub inherent_score: f64,
    pub residual_score: f64,
    pub risk_level: RiskLevel,
    pub quantitative_impact: Option<Decimal>,
    pub confidence_interval: Option<(f64, f64)>,
    pub calculation_method: String,
    pub calculated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// Key Risk Indicators (KRIs) models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateKRIRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub risk_id: Option<Uuid>,
    pub kri_type: KRIType,
    pub measurement_unit: String,
    pub frequency: MeasurementFrequency,
    pub data_source: String,
    pub calculation_method: String,
    pub green_threshold: Decimal,
    pub amber_threshold: Decimal,
    pub red_threshold: Decimal,
    pub owner_id: Uuid,
    pub automated_collection: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KRIType {
    Leading,
    Lagging,
    Concurrent,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MeasurementFrequency {
    Daily,
    Weekly,
    Monthly,
    Quarterly,
    Annually,
    RealTime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KRIValue {
    pub kri_id: Uuid,
    pub measurement_date: NaiveDate,
    pub value: Decimal,
    pub status: KRIStatus,
    pub trend: TrendDirection,
    pub variance_from_target: Option<Decimal>,
    pub notes: Option<String>,
    pub data_quality_score: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KRIStatus {
    Green,
    Amber,
    Red,
    DataUnavailable,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrendDirection {
    Improving,
    Stable,
    Deteriorating,
    Volatile,
}

/// Stress testing models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateStressTestRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub test_type: StressTestType,
    pub methodology: String,
    pub scenarios: Vec<StressScenario>,
    pub portfolios: Vec<String>,
    pub risk_factors: Vec<String>,
    pub time_horizon: i32, // days
    pub confidence_level: f64,
    pub owner_id: Uuid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StressTestType {
    Sensitivity,
    Scenario,
    ReverseStress,
    BreakEven,
    Extreme,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StressScenario {
    pub name: String,
    pub description: String,
    pub probability: f64,
    pub severity: StressSeverity,
    pub risk_factor_shocks: Vec<RiskFactorShock>,
    pub duration_days: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StressSeverity {
    Mild,
    Moderate,
    Severe,
    Extreme,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactorShock {
    pub factor_name: String,
    pub shock_type: ShockType,
    pub shock_magnitude: Decimal,
    pub correlation_adjustments: Vec<CorrelationAdjustment>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ShockType {
    Absolute,
    Relative,
    Percentile,
    StandardDeviation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorrelationAdjustment {
    pub factor_pair: (String, String),
    pub adjusted_correlation: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StressTestResult {
    pub test_id: Uuid,
    pub scenario_name: String,
    pub portfolio_impact: Decimal,
    pub capital_impact: Decimal,
    pub liquidity_impact: Option<Decimal>,
    pub key_metrics: serde_json::Value,
    pub risk_factor_contributions: Vec<RiskFactorContribution>,
    pub confidence_intervals: serde_json::Value,
    pub execution_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactorContribution {
    pub factor_name: String,
    pub contribution_amount: Decimal,
    pub contribution_percentage: f64,
}

/// Monte Carlo simulation models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateSimulationRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub simulation_type: SimulationType,
    pub num_simulations: u32,
    pub time_horizon: i32, // days
    pub random_seed: Option<u64>,
    pub risk_factors: Vec<RiskFactorDistribution>,
    pub correlations: Vec<CorrelationMatrix>,
    pub portfolios: Vec<String>,
    pub output_metrics: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SimulationType {
    VaR,
    ExpectedShortfall,
    StressTest,
    ScenarioAnalysis,
    CapitalAllocation,
    LiquidityRisk,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskFactorDistribution {
    pub factor_name: String,
    pub distribution_type: DistributionType,
    pub parameters: serde_json::Value,
    pub historical_data: Option<Vec<f64>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DistributionType {
    Normal,
    LogNormal,
    StudentT,
    Exponential,
    Uniform,
    Beta,
    Gamma,
    Historical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorrelationMatrix {
    pub factor_names: Vec<String>,
    pub correlation_values: Vec<Vec<f64>>,
    pub estimation_method: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationResult {
    pub simulation_id: Uuid,
    pub num_paths: u32,
    pub convergence_achieved: bool,
    pub var_95: Decimal,
    pub var_99: Decimal,
    pub expected_shortfall_95: Decimal,
    pub expected_shortfall_99: Decimal,
    pub maximum_loss: Decimal,
    pub expected_return: Decimal,
    pub volatility: Decimal,
    pub percentiles: serde_json::Value,
    pub path_statistics: PathStatistics,
    pub execution_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathStatistics {
    pub mean: f64,
    pub median: f64,
    pub standard_deviation: f64,
    pub skewness: f64,
    pub kurtosis: f64,
    pub minimum: f64,
    pub maximum: f64,
}

/// Model validation models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateModelRequest {
    #[validate(length(min = 1, max = 255))]
    pub name: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub model_type: ModelType,
    pub model_category: ModelCategory,
    pub methodology: String,
    pub input_variables: Vec<String>,
    pub output_variables: Vec<String>,
    pub validation_frequency: ValidationFrequency,
    pub owner_id: Uuid,
    pub business_use: String,
    pub regulatory_classification: RegulatoryClassification,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ModelType {
    Statistical,
    MachineLearning,
    Econometric,
    Simulation,
    RulesBased,
    Hybrid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ModelCategory {
    CreditRisk,
    MarketRisk,
    OperationalRisk,
    LiquidityRisk,
    Pricing,
    Valuation,
    Stress,
    Capital,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationFrequency {
    Monthly,
    Quarterly,
    SemiAnnually,
    Annually,
    AdHoc,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RegulatoryClassification {
    HighImpact,
    ModerateImpact,
    LowImpact,
    NotClassified,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelValidationResult {
    pub model_id: Uuid,
    pub validation_date: NaiveDate,
    pub validator_id: Uuid,
    pub validation_type: ValidationType,
    pub performance_metrics: ModelPerformanceMetrics,
    pub stability_tests: StabilityTestResults,
    pub backtesting_results: BacktestingResults,
    pub limitations: Vec<String>,
    pub recommendations: Vec<String>,
    pub overall_rating: ValidationRating,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationType {
    Initial,
    Periodic,
    Triggered,
    Regulatory,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPerformanceMetrics {
    pub accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1_score: f64,
    pub auc_roc: f64,
    pub gini_coefficient: f64,
    pub ks_statistic: f64,
    pub r_squared: f64,
    pub rmse: f64,
    pub mae: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StabilityTestResults {
    pub population_stability_index: f64,
    pub characteristic_stability_index: f64,
    pub drift_detection: bool,
    pub stability_rating: StabilityRating,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StabilityRating {
    Stable,
    Marginal,
    Unstable,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BacktestingResults {
    pub test_period_start: NaiveDate,
    pub test_period_end: NaiveDate,
    pub number_of_observations: u32,
    pub hit_rate: f64,
    pub coverage_ratio: f64,
    pub independence_test_p_value: f64,
    pub conditional_coverage_test_p_value: f64,
    pub backtesting_exceptions: u32,
    pub traffic_light_status: TrafficLightStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrafficLightStatus {
    Green,
    Yellow,
    Red,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationRating {
    Satisfactory,
    NeedsImprovement,
    Unsatisfactory,
}

/// Operational loss models
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreateOperationalLossRequest {
    #[validate(length(min = 1, max = 255))]
    pub title: String,
    
    #[validate(length(min = 1, max = 1000))]
    pub description: String,
    
    pub loss_date: NaiveDate,
    pub discovery_date: NaiveDate,
    pub business_unit: String,
    pub loss_category: OperationalLossCategory,
    pub loss_type: OperationalLossType,
    pub gross_loss_amount: Decimal,
    pub recovery_amount: Option<Decimal>,
    pub net_loss_amount: Decimal,
    pub currency: String,
    pub root_cause: String,
    pub contributing_factors: Vec<String>,
    pub reporter_id: Uuid,
    pub status: LossStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OperationalLossCategory {
    InternalFraud,
    ExternalFraud,
    EmploymentPractices,
    ClientsProductsBusinessPractices,
    DamageToPhysicalAssets,
    BusinessDisruptionSystemFailures,
    ExecutionDeliveryProcessManagement,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OperationalLossType {
    ProcessError,
    SystemFailure,
    HumanError,
    ExternalEvent,
    FraudulentActivity,
    RegulatoryBreach,
    DataBreach,
    ModelError,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LossStatus {
    Reported,
    UnderInvestigation,
    Validated,
    Closed,
    Disputed,
}

/// Risk appetite models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAppetiteFramework {
    pub overall_risk_appetite: RiskAppetiteStatement,
    pub risk_limits: Vec<RiskLimit>,
    pub risk_tolerances: Vec<RiskTolerance>,
    pub escalation_thresholds: Vec<EscalationThreshold>,
    pub monitoring_frequency: MeasurementFrequency,
    pub last_updated: DateTime<Utc>,
    pub approved_by: Uuid,
    pub next_review_date: NaiveDate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAppetiteStatement {
    pub statement: String,
    pub quantitative_measures: Vec<QuantitativeMeasure>,
    pub qualitative_measures: Vec<QualitativeMeasure>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskLimit {
    pub risk_type: String,
    pub limit_type: LimitType,
    pub limit_value: Decimal,
    pub currency: Option<String>,
    pub measurement_unit: String,
    pub monitoring_frequency: MeasurementFrequency,
    pub breach_tolerance: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LimitType {
    Hard,
    Soft,
    Trigger,
    Target,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskTolerance {
    pub risk_category: String,
    pub tolerance_level: ToleranceLevel,
    pub description: String,
    pub measurement_criteria: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ToleranceLevel {
    Low,
    Moderate,
    High,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscalationThreshold {
    pub threshold_name: String,
    pub threshold_value: Decimal,
    pub escalation_level: EscalationLevel,
    pub notification_recipients: Vec<Uuid>,
    pub required_actions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EscalationLevel {
    Management,
    Executive,
    Board,
    Regulatory,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuantitativeMeasure {
    pub measure_name: String,
    pub target_value: Decimal,
    pub tolerance_range: (Decimal, Decimal),
    pub current_value: Option<Decimal>,
    pub measurement_unit: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualitativeMeasure {
    pub measure_name: String,
    pub target_description: String,
    pub current_assessment: Option<String>,
    pub assessment_criteria: Vec<String>,
}

/// Reporting models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskDashboard {
    pub overall_risk_score: f64,
    pub risk_distribution: RiskDistribution,
    pub top_risks: Vec<TopRisk>,
    pub kri_summary: KRISummary,
    pub recent_losses: Vec<RecentLoss>,
    pub risk_appetite_status: RiskAppetiteStatus,
    pub stress_test_summary: StressTestSummary,
    pub model_validation_status: ModelValidationStatus,
    pub generated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskDistribution {
    pub by_category: serde_json::Value,
    pub by_business_unit: serde_json::Value,
    pub by_risk_level: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopRisk {
    pub risk_id: Uuid,
    pub title: String,
    pub category: String,
    pub current_score: f64,
    pub trend: TrendDirection,
    pub last_assessed: NaiveDate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KRISummary {
    pub total_kris: i32,
    pub green_kris: i32,
    pub amber_kris: i32,
    pub red_kris: i32,
    pub data_unavailable: i32,
    pub trending_worse: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecentLoss {
    pub loss_id: Uuid,
    pub title: String,
    pub loss_date: NaiveDate,
    pub net_amount: Decimal,
    pub category: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAppetiteStatus {
    pub within_appetite: bool,
    pub breached_limits: i32,
    pub approaching_limits: i32,
    pub last_review_date: NaiveDate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StressTestSummary {
    pub last_test_date: Option<NaiveDate>,
    pub worst_case_impact: Option<Decimal>,
    pub tests_passed: i32,
    pub tests_failed: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelValidationStatus {
    pub models_validated: i32,
    pub models_due_validation: i32,
    pub models_with_issues: i32,
    pub average_performance_score: f64,
}
