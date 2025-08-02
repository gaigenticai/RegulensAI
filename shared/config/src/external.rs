//! External services configuration

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;
use validator::Validate;

/// External services configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ExternalServicesConfig {
    /// OFAC/Sanctions screening configuration
    pub ofac: OfacConfig,
    
    /// KYC provider configuration
    pub kyc: KycConfig,
    
    /// Credit bureau configuration
    pub credit_bureau: CreditBureauConfig,
    
    /// Regulatory data feeds configuration
    pub regulatory_feeds: RegulatoryFeedsConfig,
    
    /// AI/ML services configuration
    pub ai_services: AiServicesConfig,
    
    /// Email service configuration
    pub email: EmailConfig,
    
    /// SMS service configuration
    pub sms: SmsConfig,
    
    /// Webhook configuration
    pub webhooks: WebhookConfig,
}

/// OFAC/Sanctions screening configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct OfacConfig {
    #[validate(url)]
    pub api_url: String,
    
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 0, max = 10))]
    pub retry_attempts: u32,
    
    #[validate(range(min = 100, max = 60000))]
    pub retry_delay_ms: u64,
    
    #[validate(range(min = 300, max = 86400))]
    pub update_interval_seconds: u64,
    
    pub enable_fuzzy_matching: bool,
    
    #[validate(range(min = 0.0, max = 1.0))]
    pub fuzzy_match_threshold: f64,
}

/// KYC provider configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct KycConfig {
    #[validate(url)]
    pub api_url: String,
    
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 0, max = 10))]
    pub retry_attempts: u32,
    
    pub enable_document_verification: bool,
    pub enable_biometric_verification: bool,
    pub enable_address_verification: bool,
    
    pub supported_document_types: Vec<String>,
    pub supported_countries: Vec<String>,
}

/// Credit bureau configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CreditBureauConfig {
    #[validate(url)]
    pub api_url: String,
    
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    pub enable_credit_score: bool,
    pub enable_credit_report: bool,
    pub enable_identity_verification: bool,
    
    pub supported_bureaus: Vec<String>,
}

/// Regulatory data feeds configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RegulatoryFeedsConfig {
    #[validate(url)]
    pub api_url: String,
    
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 3600, max = 86400))]
    pub update_interval_seconds: u64,
    
    pub enabled_feeds: Vec<String>,
    pub supported_jurisdictions: Vec<String>,
}

/// AI/ML services configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct AiServicesConfig {
    /// OpenAI configuration
    pub openai: OpenAiConfig,
    
    /// Hugging Face configuration
    pub huggingface: HuggingFaceConfig,
    
    /// Local model configuration
    pub local_models: LocalModelsConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct OpenAiConfig {
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(length(min = 1))]
    pub model: String,
    
    #[validate(range(min = 1, max = 32768))]
    pub max_tokens: u32,
    
    #[validate(range(min = 0.0, max = 2.0))]
    pub temperature: f32,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 0, max = 10))]
    pub retry_attempts: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct HuggingFaceConfig {
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(length(min = 1))]
    pub model_cache_dir: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    pub enabled_models: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct LocalModelsConfig {
    #[validate(length(min = 1))]
    pub model_path: String,
    
    #[validate(range(min = 3600, max = 604800))]
    pub update_interval_seconds: u64,
    
    pub enabled_models: HashMap<String, String>,
}

/// Email service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct EmailConfig {
    pub provider: EmailProvider,
    
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(email)]
    pub from_address: String,
    
    #[validate(length(min = 1))]
    pub from_name: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 0, max = 5))]
    pub retry_attempts: u32,
    
    pub enable_tracking: bool,
    pub enable_templates: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EmailProvider {
    SendGrid,
    Mailgun,
    Ses,
    Smtp,
}

/// SMS service configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct SmsConfig {
    pub provider: SmsProvider,
    
    #[validate(length(min = 1))]
    pub api_key: String,
    
    #[validate(length(min = 1))]
    pub from_number: String,
    
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 0, max = 3))]
    pub retry_attempts: u32,
    
    pub enable_delivery_reports: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SmsProvider {
    Twilio,
    Sns,
    Nexmo,
}

/// Webhook configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct WebhookConfig {
    #[validate(range(min = 1, max = 300))]
    pub timeout_seconds: u64,
    
    #[validate(range(min = 0, max = 5))]
    pub retry_attempts: u32,
    
    #[validate(range(min = 1000, max = 300000))]
    pub retry_delay_ms: u64,
    
    pub verify_ssl: bool,
    pub enable_signature_verification: bool,
    
    #[validate(length(min = 1))]
    pub signature_secret: String,
    
    pub endpoints: Vec<WebhookEndpoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct WebhookEndpoint {
    #[validate(length(min = 1))]
    pub name: String,
    
    #[validate(url)]
    pub url: String,
    
    pub events: Vec<String>,
    pub enabled: bool,
    pub headers: HashMap<String, String>,
}

impl Default for ExternalServicesConfig {
    fn default() -> Self {
        Self {
            ofac: OfacConfig {
                api_url: "https://api.treasury.gov/v1/sanctions".to_string(),
                api_key: "your-ofac-api-key".to_string(),
                timeout_seconds: 30,
                retry_attempts: 3,
                retry_delay_ms: 1000,
                update_interval_seconds: 3600,
                enable_fuzzy_matching: true,
                fuzzy_match_threshold: 0.8,
            },
            kyc: KycConfig {
                api_url: "https://api.kyc-provider.com/v1".to_string(),
                api_key: "your-kyc-api-key".to_string(),
                timeout_seconds: 60,
                retry_attempts: 3,
                enable_document_verification: true,
                enable_biometric_verification: true,
                enable_address_verification: true,
                supported_document_types: vec!["passport".to_string(), "drivers_license".to_string(), "national_id".to_string()],
                supported_countries: vec!["US".to_string(), "CA".to_string(), "GB".to_string(), "DE".to_string()],
            },
            credit_bureau: CreditBureauConfig {
                api_url: "https://api.creditbureau.com/v1".to_string(),
                api_key: "your-credit-bureau-key".to_string(),
                timeout_seconds: 30,
                enable_credit_score: true,
                enable_credit_report: true,
                enable_identity_verification: true,
                supported_bureaus: vec!["experian".to_string(), "equifax".to_string(), "transunion".to_string()],
            },
            regulatory_feeds: RegulatoryFeedsConfig {
                api_url: "https://api.regulatory-feed.com/v1".to_string(),
                api_key: "your-regulatory-feed-key".to_string(),
                timeout_seconds: 60,
                update_interval_seconds: 86400,
                enabled_feeds: vec!["sec".to_string(), "finra".to_string(), "cftc".to_string()],
                supported_jurisdictions: vec!["US".to_string(), "EU".to_string(), "UK".to_string()],
            },
            ai_services: AiServicesConfig {
                openai: OpenAiConfig {
                    api_key: "your-openai-api-key".to_string(),
                    model: "gpt-4".to_string(),
                    max_tokens: 4096,
                    temperature: 0.1,
                    timeout_seconds: 60,
                    retry_attempts: 3,
                },
                huggingface: HuggingFaceConfig {
                    api_key: "your-huggingface-key".to_string(),
                    model_cache_dir: "./models".to_string(),
                    timeout_seconds: 120,
                    enabled_models: vec!["bert-base-uncased".to_string(), "distilbert-base-uncased".to_string()],
                },
                local_models: LocalModelsConfig {
                    model_path: "./models".to_string(),
                    update_interval_seconds: 86400,
                    enabled_models: HashMap::new(),
                },
            },
            email: EmailConfig {
                provider: EmailProvider::SendGrid,
                api_key: "your-email-api-key".to_string(),
                from_address: "noreply@regulateai.com".to_string(),
                from_name: "RegulateAI".to_string(),
                timeout_seconds: 30,
                retry_attempts: 3,
                enable_tracking: true,
                enable_templates: true,
            },
            sms: SmsConfig {
                provider: SmsProvider::Twilio,
                api_key: "your-sms-api-key".to_string(),
                from_number: "+1234567890".to_string(),
                timeout_seconds: 30,
                retry_attempts: 2,
                enable_delivery_reports: true,
            },
            webhooks: WebhookConfig {
                timeout_seconds: 30,
                retry_attempts: 3,
                retry_delay_ms: 5000,
                verify_ssl: true,
                enable_signature_verification: true,
                signature_secret: "your-webhook-signature-secret".to_string(),
                endpoints: vec![],
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_external_services_config() {
        let config = ExternalServicesConfig::default();
        assert_eq!(config.ofac.timeout_seconds, 30);
        assert_eq!(config.kyc.retry_attempts, 3);
        assert!(config.kyc.enable_document_verification);
        assert_eq!(config.ai_services.openai.model, "gpt-4");
    }
}
