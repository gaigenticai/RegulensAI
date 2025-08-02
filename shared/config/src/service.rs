//! Service-specific configuration

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use validator::Validate;

/// Service-specific configurations
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ServiceConfig {
    /// AML service configuration
    pub aml: AmlServiceConfig,
    
    /// Compliance service configuration
    pub compliance: ComplianceServiceConfig,
    
    /// Risk management service configuration
    pub risk_management: RiskManagementServiceConfig,
    
    /// Fraud detection service configuration
    pub fraud_detection: FraudDetectionServiceConfig,
    
    /// Cybersecurity service configuration
    pub cybersecurity: CybersecurityServiceConfig,
    
    /// AI orchestration service configuration
    pub ai_orchestration: AiOrchestrationServiceConfig,
}

/// AML service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct AmlServiceConfig {
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1024, max = 65535))]
    pub metrics_port: u16,
    
    #[validate(range(min = 0.0))]
    pub transaction_threshold: f64,
    
    #[validate(range(min = 0.0, max = 100.0))]
    pub risk_score_threshold: f64,
    
    #[validate(range(min = 300, max = 86400))]
    pub sanctions_update_interval: u64,
    
    #[validate(range(min = 0.0, max = 1.0))]
    pub fuzzy_match_threshold: f64,
    
    pub enable_real_time_monitoring: bool,
    pub enable_behavioral_analysis: bool,
    pub enable_sanctions_screening: bool,
    
    pub supported_currencies: Vec<String>,
    pub high_risk_countries: Vec<String>,
    
    pub kyc_document_retention_days: u32,
    pub sar_filing_threshold: f64,
}

/// Compliance service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ComplianceServiceConfig {
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1024, max = 65535))]
    pub metrics_port: u16,
    
    #[validate(range(min = 1, max = 10000))]
    pub audit_retention_days: u32,
    
    #[validate(range(min = 86400, max = 31536000))]
    pub policy_review_interval: u64,
    
    #[validate(range(min = 1, max = 365))]
    pub attestation_reminder_days: u32,
    
    #[validate(range(min = 1, max = 365))]
    pub control_testing_frequency_days: u32,
    
    pub enable_automated_controls: bool,
    pub enable_policy_versioning: bool,
    pub enable_workflow_automation: bool,
    
    pub supported_frameworks: Vec<String>,
    pub default_approval_workflow: String,
}

/// Risk management service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RiskManagementServiceConfig {
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1024, max = 65535))]
    pub metrics_port: u16,
    
    #[validate(range(min = 3600, max = 604800))]
    pub assessment_interval: u64,
    
    #[validate(range(min = 1000, max = 1000000))]
    pub monte_carlo_iterations: u32,
    
    #[validate(range(min = 0.0, max = 1.0))]
    pub var_confidence_level: f64,
    
    #[validate(range(min = 0.0, max = 1.0))]
    pub expected_shortfall_confidence: f64,
    
    pub enable_stress_testing: bool,
    pub enable_scenario_analysis: bool,
    pub enable_model_validation: bool,
    
    pub risk_categories: Vec<String>,
    pub stress_test_scenarios: HashMap<String, f64>,
}

/// Fraud detection service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct FraudDetectionServiceConfig {
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1024, max = 65535))]
    pub metrics_port: u16,
    
    #[validate(range(min = 0.0, max = 1.0))]
    pub detection_threshold: f64,
    
    #[validate(range(min = 3600, max = 604800))]
    pub model_update_interval: u64,
    
    #[validate(range(min = 300, max = 86400))]
    pub velocity_check_window: u64,
    
    #[validate(range(min = 1, max = 10000))]
    pub max_daily_transactions: u32,
    
    #[validate(range(min = 0.0))]
    pub max_transaction_amount: f64,
    
    pub enable_graph_analysis: bool,
    pub enable_ml_models: bool,
    pub enable_real_time_scoring: bool,
    
    pub fraud_types: Vec<String>,
    pub ml_model_endpoints: HashMap<String, String>,
}

/// Cybersecurity service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CybersecurityServiceConfig {
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1024, max = 65535))]
    pub metrics_port: u16,
    
    #[validate(range(min = 3600, max = 604800))]
    pub vuln_scan_interval: u64,
    
    #[validate(range(min = 60, max = 86400))]
    pub incident_response_sla_minutes: u32,
    
    #[validate(range(min = 1, max = 365))]
    pub password_expiry_days: u32,
    
    #[validate(range(min = 1, max = 1440))]
    pub session_timeout_minutes: u32,
    
    #[validate(range(min = 1, max = 10))]
    pub max_failed_login_attempts: u32,
    
    pub enable_vulnerability_scanning: bool,
    pub enable_incident_response: bool,
    pub enable_security_monitoring: bool,
    
    pub security_frameworks: Vec<String>,
    pub incident_types: Vec<String>,
    pub vulnerability_sources: Vec<String>,
}

/// AI orchestration service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct AiOrchestrationServiceConfig {
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1024, max = 65535))]
    pub metrics_port: u16,
    
    #[validate(range(min = 30, max = 3600))]
    pub agent_timeout: u64,
    
    #[validate(range(min = 512, max = 32768))]
    pub context_window_size: u32,
    
    #[validate(range(min = 300, max = 86400))]
    pub response_cache_ttl: u64,
    
    #[validate(range(min = 0.0, max = 2.0))]
    pub default_temperature: f32,
    
    #[validate(range(min = 1, max = 16384))]
    pub max_tokens: u32,
    
    pub enable_regulatory_qa: bool,
    pub enable_automated_mapping: bool,
    pub enable_self_healing: bool,
    pub enable_recommendations: bool,
    
    pub supported_models: Vec<String>,
    pub agent_types: Vec<String>,
    pub workflow_templates: HashMap<String, String>,
}

impl Default for ServiceConfig {
    fn default() -> Self {
        Self {
            aml: AmlServiceConfig {
                port: 8081,
                metrics_port: 9091,
                transaction_threshold: 10000.0,
                risk_score_threshold: 75.0,
                sanctions_update_interval: 3600,
                fuzzy_match_threshold: 0.8,
                enable_real_time_monitoring: true,
                enable_behavioral_analysis: true,
                enable_sanctions_screening: true,
                supported_currencies: vec!["USD".to_string(), "EUR".to_string(), "GBP".to_string()],
                high_risk_countries: vec!["AF".to_string(), "IR".to_string(), "KP".to_string()],
                kyc_document_retention_days: 2555,
                sar_filing_threshold: 5000.0,
            },
            compliance: ComplianceServiceConfig {
                port: 8082,
                metrics_port: 9092,
                audit_retention_days: 2555,
                policy_review_interval: 31536000, // 1 year
                attestation_reminder_days: 30,
                control_testing_frequency_days: 90,
                enable_automated_controls: true,
                enable_policy_versioning: true,
                enable_workflow_automation: true,
                supported_frameworks: vec!["SOC2".to_string(), "ISO27001".to_string(), "PCI_DSS".to_string()],
                default_approval_workflow: "standard_approval".to_string(),
            },
            risk_management: RiskManagementServiceConfig {
                port: 8083,
                metrics_port: 9093,
                assessment_interval: 86400,
                monte_carlo_iterations: 10000,
                var_confidence_level: 0.95,
                expected_shortfall_confidence: 0.975,
                enable_stress_testing: true,
                enable_scenario_analysis: true,
                enable_model_validation: true,
                risk_categories: vec!["credit".to_string(), "market".to_string(), "operational".to_string()],
                stress_test_scenarios: HashMap::new(),
            },
            fraud_detection: FraudDetectionServiceConfig {
                port: 8084,
                metrics_port: 9094,
                detection_threshold: 0.8,
                model_update_interval: 86400,
                velocity_check_window: 3600,
                max_daily_transactions: 100,
                max_transaction_amount: 100000.0,
                enable_graph_analysis: true,
                enable_ml_models: true,
                enable_real_time_scoring: true,
                fraud_types: vec!["identity".to_string(), "transaction".to_string(), "application".to_string()],
                ml_model_endpoints: HashMap::new(),
            },
            cybersecurity: CybersecurityServiceConfig {
                port: 8085,
                metrics_port: 9095,
                vuln_scan_interval: 86400,
                incident_response_sla_minutes: 60,
                password_expiry_days: 90,
                session_timeout_minutes: 30,
                max_failed_login_attempts: 3,
                enable_vulnerability_scanning: true,
                enable_incident_response: true,
                enable_security_monitoring: true,
                security_frameworks: vec!["NIST".to_string(), "ISO27001".to_string()],
                incident_types: vec!["data_breach".to_string(), "malware".to_string(), "phishing".to_string()],
                vulnerability_sources: vec!["nessus".to_string(), "openvas".to_string()],
            },
            ai_orchestration: AiOrchestrationServiceConfig {
                port: 8086,
                metrics_port: 9096,
                agent_timeout: 300,
                context_window_size: 4096,
                response_cache_ttl: 3600,
                default_temperature: 0.1,
                max_tokens: 4096,
                enable_regulatory_qa: true,
                enable_automated_mapping: true,
                enable_self_healing: true,
                enable_recommendations: true,
                supported_models: vec!["gpt-4".to_string(), "claude-3".to_string()],
                agent_types: vec!["qa".to_string(), "mapping".to_string(), "healing".to_string()],
                workflow_templates: HashMap::new(),
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_service_config() {
        let config = ServiceConfig::default();
        assert_eq!(config.aml.port, 8081);
        assert_eq!(config.compliance.port, 8082);
        assert_eq!(config.risk_management.port, 8083);
        assert_eq!(config.fraud_detection.port, 8084);
        assert_eq!(config.cybersecurity.port, 8085);
        assert_eq!(config.ai_orchestration.port, 8086);
    }
}
