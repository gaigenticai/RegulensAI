//! Security Configuration Management

use serde::{Deserialize, Serialize};
use crate::{
    waf::WafConfig,
    owasp::OwaspScannerConfig,
    threat_detection::ThreatDetectionConfig,
    rate_limiting::RateLimitConfig,
    ip_filtering::IpFilterConfig,
    security_headers::SecurityHeadersConfig,
    vulnerability_scanner::VulnerabilityScannerConfig,
};

/// Main security configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub enabled: bool,
    pub waf: WafConfig,
    pub owasp_scanner: OwaspScannerConfig,
    pub threat_detection: ThreatDetectionConfig,
    pub rate_limiting: RateLimitConfig,
    pub ip_filtering: IpFilterConfig,
    pub security_headers: SecurityHeadersConfig,
    pub vulnerability_scanner: VulnerabilityScannerConfig,
    pub logging: SecurityLoggingConfig,
    pub monitoring: SecurityMonitoringConfig,
}

/// Security logging configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityLoggingConfig {
    pub enabled: bool,
    pub log_level: String,
    pub log_all_requests: bool,
    pub log_blocked_requests: bool,
    pub log_vulnerabilities: bool,
    pub log_threats: bool,
    pub log_auth_events: bool,
    pub structured_logging: bool,
    pub include_request_body: bool,
    pub include_response_body: bool,
    pub max_log_size_mb: usize,
}

/// Security monitoring configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityMonitoringConfig {
    pub enabled: bool,
    pub metrics_enabled: bool,
    pub alerting_enabled: bool,
    pub dashboard_enabled: bool,
    pub real_time_monitoring: bool,
    pub alert_thresholds: AlertThresholds,
    pub notification_channels: Vec<NotificationChannel>,
}

/// Alert thresholds configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertThresholds {
    pub blocked_requests_per_minute: u64,
    pub vulnerabilities_per_hour: u64,
    pub threats_per_hour: u64,
    pub auth_failures_per_minute: u64,
    pub rate_limit_violations_per_minute: u64,
}

/// Notification channel configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationChannel {
    pub name: String,
    pub channel_type: NotificationChannelType,
    pub enabled: bool,
    pub config: serde_json::Value,
}

/// Notification channel types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NotificationChannelType {
    Email,
    Slack,
    Discord,
    Teams,
    Webhook,
    Sms,
    PagerDuty,
}

impl SecurityConfig {
    /// Load security configuration from environment variables
    pub fn from_env() -> Result<Self, config::ConfigError> {
        let mut settings = config::Config::builder();
        
        // Add default configuration
        settings = settings.add_source(config::File::with_name("config/security"));
        
        // Add environment variables
        settings = settings.add_source(
            config::Environment::with_prefix("SECURITY")
                .prefix_separator("_")
                .separator("__")
        );
        
        let config = settings.build()?;
        config.try_deserialize()
    }

    /// Validate security configuration
    pub fn validate(&self) -> Result<(), String> {
        if !self.enabled {
            return Ok(());
        }

        // Validate WAF configuration
        if self.waf.enabled && self.waf.paranoia_level > 4 {
            return Err("WAF paranoia level must be between 1 and 4".to_string());
        }

        // Validate rate limiting configuration
        if self.rate_limiting.enabled {
            if self.rate_limiting.default_requests_per_minute == 0 {
                return Err("Rate limiting requests per minute must be greater than 0".to_string());
            }
            if self.rate_limiting.default_burst_size == 0 {
                return Err("Rate limiting burst size must be greater than 0".to_string());
            }
        }

        // Validate threat detection configuration
        if self.threat_detection.enabled {
            if self.threat_detection.detection_threshold < 0.0 || self.threat_detection.detection_threshold > 1.0 {
                return Err("Threat detection threshold must be between 0.0 and 1.0".to_string());
            }
        }

        // Validate OWASP scanner configuration
        if self.owasp_scanner.enabled {
            if self.owasp_scanner.confidence_threshold < 0.0 || self.owasp_scanner.confidence_threshold > 1.0 {
                return Err("OWASP scanner confidence threshold must be between 0.0 and 1.0".to_string());
            }
        }

        // Validate monitoring configuration
        if self.monitoring.enabled && self.monitoring.alerting_enabled {
            if self.monitoring.notification_channels.is_empty() {
                return Err("At least one notification channel must be configured when alerting is enabled".to_string());
            }
        }

        Ok(())
    }

    /// Get security configuration summary
    pub fn get_summary(&self) -> SecurityConfigSummary {
        SecurityConfigSummary {
            enabled: self.enabled,
            waf_enabled: self.waf.enabled,
            owasp_scanner_enabled: self.owasp_scanner.enabled,
            threat_detection_enabled: self.threat_detection.enabled,
            rate_limiting_enabled: self.rate_limiting.enabled,
            ip_filtering_enabled: self.ip_filtering.enabled,
            security_headers_enabled: self.security_headers.enabled,
            vulnerability_scanner_enabled: self.vulnerability_scanner.enabled,
            logging_enabled: self.logging.enabled,
            monitoring_enabled: self.monitoring.enabled,
            alerting_enabled: self.monitoring.alerting_enabled,
            notification_channels: self.monitoring.notification_channels.len(),
        }
    }
}

/// Security configuration summary
#[derive(Debug, Serialize)]
pub struct SecurityConfigSummary {
    pub enabled: bool,
    pub waf_enabled: bool,
    pub owasp_scanner_enabled: bool,
    pub threat_detection_enabled: bool,
    pub rate_limiting_enabled: bool,
    pub ip_filtering_enabled: bool,
    pub security_headers_enabled: bool,
    pub vulnerability_scanner_enabled: bool,
    pub logging_enabled: bool,
    pub monitoring_enabled: bool,
    pub alerting_enabled: bool,
    pub notification_channels: usize,
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            waf: WafConfig::default(),
            owasp_scanner: OwaspScannerConfig::default(),
            threat_detection: ThreatDetectionConfig::default(),
            rate_limiting: RateLimitConfig::default(),
            ip_filtering: IpFilterConfig::default(),
            security_headers: SecurityHeadersConfig::default(),
            vulnerability_scanner: VulnerabilityScannerConfig::default(),
            logging: SecurityLoggingConfig::default(),
            monitoring: SecurityMonitoringConfig::default(),
        }
    }
}

impl Default for SecurityLoggingConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            log_level: "INFO".to_string(),
            log_all_requests: false,
            log_blocked_requests: true,
            log_vulnerabilities: true,
            log_threats: true,
            log_auth_events: true,
            structured_logging: true,
            include_request_body: false,
            include_response_body: false,
            max_log_size_mb: 100,
        }
    }
}

impl Default for SecurityMonitoringConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            metrics_enabled: true,
            alerting_enabled: true,
            dashboard_enabled: true,
            real_time_monitoring: true,
            alert_thresholds: AlertThresholds::default(),
            notification_channels: vec![],
        }
    }
}

impl Default for AlertThresholds {
    fn default() -> Self {
        Self {
            blocked_requests_per_minute: 100,
            vulnerabilities_per_hour: 10,
            threats_per_hour: 5,
            auth_failures_per_minute: 20,
            rate_limit_violations_per_minute: 50,
        }
    }
}
