//! Security-specific error types and handling

use crate::owasp::OwaspVulnerability;
use thiserror::Error;

/// Security-specific error types
#[derive(Error, Debug)]
pub enum SecurityError {
    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Regex compilation error: {0}")]
    RegexError(#[from] regex::Error),

    #[error("Rate limit exceeded for {client_ip}: {current}/{max} requests")]
    RateLimitExceeded {
        client_ip: String,
        current: u64,
        max: u64,
    },

    #[error("IP address {ip} is blocked until {until}")]
    IpBlocked {
        ip: String,
        until: chrono::DateTime<chrono::Utc>,
    },

    #[error("Vulnerability detected: {0:?}")]
    VulnerabilityDetected(OwaspVulnerability),

    #[error("WAF rule violation: {rule_id} - {reason}")]
    WafViolation {
        rule_id: String,
        reason: String,
    },

    #[error("Threat detected: {threat_type} with level {level:?}")]
    ThreatDetected {
        threat_type: String,
        level: crate::threat_detection::ThreatLevel,
    },

    #[error("Authentication failed: {reason}")]
    AuthenticationFailed {
        reason: String,
    },

    #[error("Authorization denied: {reason}")]
    AuthorizationDenied {
        reason: String,
    },

    #[error("Security policy violation: {policy} - {details}")]
    PolicyViolation {
        policy: String,
        details: String,
    },

    #[error("Cryptographic error: {0}")]
    CryptographicError(String),

    #[error("Network security error: {0}")]
    NetworkError(String),

    #[error("File system security error: {0}")]
    FileSystemError(String),

    #[error("Database security error: {0}")]
    DatabaseError(String),

    #[error("Session security error: {0}")]
    SessionError(String),

    #[error("Input validation error: {field} - {message}")]
    ValidationError {
        field: String,
        message: String,
    },

    #[error("Security scan failed: {0}")]
    ScanError(String),

    #[error("Security metric collection failed: {0}")]
    MetricsError(String),

    #[error("Internal security error: {0}")]
    Internal(String),

    #[error("External service error: {service} - {error}")]
    ExternalServiceError {
        service: String,
        error: String,
    },

    #[error("Timeout error: operation timed out after {seconds} seconds")]
    Timeout {
        seconds: u64,
    },

    #[error("Resource exhaustion: {resource} limit exceeded")]
    ResourceExhaustion {
        resource: String,
    },

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Security result type alias
pub type SecurityResult<T> = Result<T, SecurityError>;

impl SecurityError {
    /// Check if the error is recoverable
    pub fn is_recoverable(&self) -> bool {
        match self {
            SecurityError::Configuration(_) => false,
            SecurityError::RegexError(_) => false,
            SecurityError::RateLimitExceeded { .. } => true,
            SecurityError::IpBlocked { .. } => true,
            SecurityError::VulnerabilityDetected(_) => false,
            SecurityError::WafViolation { .. } => false,
            SecurityError::ThreatDetected { .. } => false,
            SecurityError::AuthenticationFailed { .. } => true,
            SecurityError::AuthorizationDenied { .. } => false,
            SecurityError::PolicyViolation { .. } => false,
            SecurityError::CryptographicError(_) => false,
            SecurityError::NetworkError(_) => true,
            SecurityError::FileSystemError(_) => true,
            SecurityError::DatabaseError(_) => true,
            SecurityError::SessionError(_) => true,
            SecurityError::ValidationError { .. } => true,
            SecurityError::ScanError(_) => true,
            SecurityError::MetricsError(_) => true,
            SecurityError::Internal(_) => false,
            SecurityError::ExternalServiceError { .. } => true,
            SecurityError::Timeout { .. } => true,
            SecurityError::ResourceExhaustion { .. } => true,
            SecurityError::SerializationError(_) => true,
            SecurityError::IoError(_) => true,
        }
    }

    /// Get the severity level of the error
    pub fn severity(&self) -> ErrorSeverity {
        match self {
            SecurityError::Configuration(_) => ErrorSeverity::Critical,
            SecurityError::RegexError(_) => ErrorSeverity::High,
            SecurityError::RateLimitExceeded { .. } => ErrorSeverity::Medium,
            SecurityError::IpBlocked { .. } => ErrorSeverity::Medium,
            SecurityError::VulnerabilityDetected(vuln) => match vuln.severity {
                crate::owasp::VulnerabilitySeverity::Critical => ErrorSeverity::Critical,
                crate::owasp::VulnerabilitySeverity::High => ErrorSeverity::High,
                crate::owasp::VulnerabilitySeverity::Medium => ErrorSeverity::Medium,
                crate::owasp::VulnerabilitySeverity::Low => ErrorSeverity::Low,
                crate::owasp::VulnerabilitySeverity::Info => ErrorSeverity::Info,
            },
            SecurityError::WafViolation { .. } => ErrorSeverity::High,
            SecurityError::ThreatDetected { level, .. } => match level {
                crate::threat_detection::ThreatLevel::Critical => ErrorSeverity::Critical,
                crate::threat_detection::ThreatLevel::High => ErrorSeverity::High,
                crate::threat_detection::ThreatLevel::Medium => ErrorSeverity::Medium,
                crate::threat_detection::ThreatLevel::Low => ErrorSeverity::Low,
                crate::threat_detection::ThreatLevel::Info => ErrorSeverity::Info,
            },
            SecurityError::AuthenticationFailed { .. } => ErrorSeverity::Medium,
            SecurityError::AuthorizationDenied { .. } => ErrorSeverity::Medium,
            SecurityError::PolicyViolation { .. } => ErrorSeverity::High,
            SecurityError::CryptographicError(_) => ErrorSeverity::Critical,
            SecurityError::NetworkError(_) => ErrorSeverity::Medium,
            SecurityError::FileSystemError(_) => ErrorSeverity::Medium,
            SecurityError::DatabaseError(_) => ErrorSeverity::High,
            SecurityError::SessionError(_) => ErrorSeverity::Medium,
            SecurityError::ValidationError { .. } => ErrorSeverity::Low,
            SecurityError::ScanError(_) => ErrorSeverity::Low,
            SecurityError::MetricsError(_) => ErrorSeverity::Low,
            SecurityError::Internal(_) => ErrorSeverity::Critical,
            SecurityError::ExternalServiceError { .. } => ErrorSeverity::Medium,
            SecurityError::Timeout { .. } => ErrorSeverity::Low,
            SecurityError::ResourceExhaustion { .. } => ErrorSeverity::High,
            SecurityError::SerializationError(_) => ErrorSeverity::Low,
            SecurityError::IoError(_) => ErrorSeverity::Medium,
        }
    }

    /// Get error category for metrics and logging
    pub fn category(&self) -> &'static str {
        match self {
            SecurityError::Configuration(_) => "configuration",
            SecurityError::RegexError(_) => "regex",
            SecurityError::RateLimitExceeded { .. } => "rate_limit",
            SecurityError::IpBlocked { .. } => "ip_blocking",
            SecurityError::VulnerabilityDetected(_) => "vulnerability",
            SecurityError::WafViolation { .. } => "waf",
            SecurityError::ThreatDetected { .. } => "threat",
            SecurityError::AuthenticationFailed { .. } => "authentication",
            SecurityError::AuthorizationDenied { .. } => "authorization",
            SecurityError::PolicyViolation { .. } => "policy",
            SecurityError::CryptographicError(_) => "cryptography",
            SecurityError::NetworkError(_) => "network",
            SecurityError::FileSystemError(_) => "filesystem",
            SecurityError::DatabaseError(_) => "database",
            SecurityError::SessionError(_) => "session",
            SecurityError::ValidationError { .. } => "validation",
            SecurityError::ScanError(_) => "scan",
            SecurityError::MetricsError(_) => "metrics",
            SecurityError::Internal(_) => "internal",
            SecurityError::ExternalServiceError { .. } => "external_service",
            SecurityError::Timeout { .. } => "timeout",
            SecurityError::ResourceExhaustion { .. } => "resource_exhaustion",
            SecurityError::SerializationError(_) => "serialization",
            SecurityError::IoError(_) => "io",
        }
    }
}

/// Error severity levels
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum ErrorSeverity {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

impl std::fmt::Display for ErrorSeverity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ErrorSeverity::Info => write!(f, "INFO"),
            ErrorSeverity::Low => write!(f, "LOW"),
            ErrorSeverity::Medium => write!(f, "MEDIUM"),
            ErrorSeverity::High => write!(f, "HIGH"),
            ErrorSeverity::Critical => write!(f, "CRITICAL"),
        }
    }
}

/// Security error context for enhanced debugging
#[derive(Debug, Clone)]
pub struct SecurityErrorContext {
    pub client_ip: Option<String>,
    pub user_agent: Option<String>,
    pub request_id: Option<String>,
    pub session_id: Option<String>,
    pub user_id: Option<String>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub additional_data: std::collections::HashMap<String, serde_json::Value>,
}

impl Default for SecurityErrorContext {
    fn default() -> Self {
        Self {
            client_ip: None,
            user_agent: None,
            request_id: None,
            session_id: None,
            user_id: None,
            timestamp: chrono::Utc::now(),
            additional_data: std::collections::HashMap::new(),
        }
    }
}

/// Enhanced security error with context
#[derive(Debug)]
pub struct ContextualSecurityError {
    pub error: SecurityError,
    pub context: SecurityErrorContext,
}

impl std::fmt::Display for ContextualSecurityError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} (context: {:?})", self.error, self.context)
    }
}

impl std::error::Error for ContextualSecurityError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(&self.error)
    }
}
