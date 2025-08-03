//! Security Types and Data Structures
//! 
//! This module defines all the core types used throughout the security system,
//! including request/response structures, security decisions, and threat assessments.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::IpAddr;
use chrono::{DateTime, Utc};
use uuid::Uuid;

/// Security request containing all information needed for security analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityRequest {
    /// Unique identifier for this request
    pub id: Uuid,
    /// HTTP method (GET, POST, PUT, DELETE, etc.)
    pub method: String,
    /// Request path/URI
    pub path: String,
    /// Query parameters
    pub query_params: HashMap<String, String>,
    /// HTTP headers
    pub headers: HashMap<String, String>,
    /// Request body (if present)
    pub body: Option<String>,
    /// Client IP address
    pub client_ip: IpAddr,
    /// User agent string
    pub user_agent: Option<String>,
    /// Referer header
    pub referer: Option<String>,
    /// Request timestamp
    pub timestamp: DateTime<Utc>,
    /// Request size in bytes
    pub size_bytes: usize,
    /// Authentication information (if available)
    pub auth_info: Option<AuthInfo>,
    /// Session information (if available)
    pub session_info: Option<SessionInfo>,
    /// Additional metadata
    pub metadata: HashMap<String, String>,
}

/// Authentication information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthInfo {
    /// User ID (if authenticated)
    pub user_id: Option<String>,
    /// Authentication method used
    pub auth_method: AuthMethod,
    /// JWT token claims (if JWT auth)
    pub jwt_claims: Option<HashMap<String, serde_json::Value>>,
    /// API key information (if API key auth)
    pub api_key_info: Option<ApiKeyInfo>,
    /// Authentication timestamp
    pub authenticated_at: DateTime<Utc>,
}

/// Authentication methods
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuthMethod {
    None,
    Bearer,
    Basic,
    ApiKey,
    OAuth2,
    Custom(String),
}

/// API key information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKeyInfo {
    pub key_id: String,
    pub permissions: Vec<String>,
    pub rate_limit: Option<u32>,
    pub expires_at: Option<DateTime<Utc>>,
}

/// Session information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionInfo {
    pub session_id: String,
    pub created_at: DateTime<Utc>,
    pub last_activity: DateTime<Utc>,
    pub user_id: Option<String>,
    pub session_data: HashMap<String, serde_json::Value>,
}

/// Security response indicating the decision made
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityResponse {
    /// Unique identifier for this response
    pub id: Uuid,
    /// Request ID this response corresponds to
    pub request_id: Uuid,
    /// Security decision made
    pub decision: SecurityDecision,
    /// Reason for the decision
    pub reason: String,
    /// Security score (0.0 = safe, 1.0 = maximum threat)
    pub threat_score: f64,
    /// Rules that were triggered
    pub triggered_rules: Vec<TriggeredRule>,
    /// Actions taken
    pub actions_taken: Vec<SecurityAction>,
    /// Processing time in milliseconds
    pub processing_time_ms: u64,
    /// Response timestamp
    pub timestamp: DateTime<Utc>,
    /// Additional metadata
    pub metadata: HashMap<String, String>,
}

/// Security decision enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SecurityDecision {
    /// Allow the request to proceed
    Allow,
    /// Block the request
    Block,
    /// Allow but monitor closely
    Monitor,
    /// Challenge the user (CAPTCHA, MFA, etc.)
    Challenge,
    /// Rate limit the request
    RateLimit,
    /// Require additional authentication
    RequireAuth,
}

/// Information about a triggered security rule
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggeredRule {
    /// Rule identifier
    pub rule_id: String,
    /// Rule name
    pub rule_name: String,
    /// Rule category
    pub category: RuleCategory,
    /// Severity level
    pub severity: SeverityLevel,
    /// Confidence score (0.0-1.0)
    pub confidence: f64,
    /// Matched pattern or condition
    pub matched_pattern: String,
    /// Location where the rule matched
    pub match_location: MatchLocation,
    /// Additional rule-specific data
    pub rule_data: HashMap<String, serde_json::Value>,
}

/// Security rule categories
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RuleCategory {
    SqlInjection,
    XssAttack,
    PathTraversal,
    CommandInjection,
    FileInclusion,
    AuthenticationBypass,
    SessionFixation,
    CsrfAttack,
    DdosAttack,
    BruteForce,
    Reconnaissance,
    MaliciousBot,
    SuspiciousUserAgent,
    GeoLocationViolation,
    RateLimitViolation,
    Custom(String),
}

/// Severity levels for security violations
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum SeverityLevel {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

/// Location where a security rule matched
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MatchLocation {
    Path,
    QueryParameter(String),
    Header(String),
    Body,
    UserAgent,
    Referer,
    Cookie(String),
    IpAddress,
    Multiple(Vec<String>),
}

/// Security actions that can be taken
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SecurityAction {
    /// Log the security event
    Log {
        level: LogLevel,
        message: String,
    },
    /// Block the request
    Block {
        reason: String,
        duration: Option<chrono::Duration>,
    },
    /// Add IP to blocklist
    BlockIp {
        ip: IpAddr,
        duration: chrono::Duration,
        reason: String,
    },
    /// Rate limit the client
    RateLimit {
        limit: u32,
        window: chrono::Duration,
    },
    /// Send alert notification
    Alert {
        severity: SeverityLevel,
        message: String,
        recipients: Vec<String>,
    },
    /// Trigger CAPTCHA challenge
    Challenge {
        challenge_type: ChallengeType,
    },
    /// Require additional authentication
    RequireAuth {
        auth_methods: Vec<AuthMethod>,
    },
    /// Custom action
    Custom {
        action_type: String,
        parameters: HashMap<String, serde_json::Value>,
    },
}

/// Log levels for security events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
    Critical,
}

/// Challenge types for user verification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ChallengeType {
    Captcha,
    Recaptcha,
    MultiFactorAuth,
    EmailVerification,
    SmsVerification,
    Custom(String),
}

/// Threat assessment result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreatAssessment {
    /// Overall threat score (0.0-1.0)
    pub threat_score: f64,
    /// Risk level classification
    pub risk_level: RiskLevel,
    /// Individual threat indicators
    pub indicators: Vec<ThreatIndicator>,
    /// Confidence in the assessment
    pub confidence: f64,
    /// Assessment timestamp
    pub assessed_at: DateTime<Utc>,
    /// Model version used for assessment
    pub model_version: String,
    /// Additional assessment metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Risk level classifications
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum RiskLevel {
    VeryLow,
    Low,
    Medium,
    High,
    Critical,
}

/// Individual threat indicators
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreatIndicator {
    /// Indicator type
    pub indicator_type: IndicatorType,
    /// Indicator value/score
    pub value: f64,
    /// Confidence in this indicator
    pub confidence: f64,
    /// Description of what was detected
    pub description: String,
    /// Evidence supporting this indicator
    pub evidence: Vec<String>,
}

/// Types of threat indicators
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IndicatorType {
    AnomalousPattern,
    SuspiciousPayload,
    MaliciousIp,
    BotBehavior,
    RateLimitViolation,
    GeolocationAnomaly,
    UserAgentAnomaly,
    SessionAnomaly,
    AuthenticationAnomaly,
    Custom(String),
}

/// Security configuration for requests
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    /// Enable WAF protection
    pub waf_enabled: bool,
    /// Enable threat detection
    pub threat_detection_enabled: bool,
    /// Enable rate limiting
    pub rate_limiting_enabled: bool,
    /// Enable IP filtering
    pub ip_filtering_enabled: bool,
    /// Threat score threshold for blocking
    pub threat_threshold: f64,
    /// Maximum request size in bytes
    pub max_request_size: usize,
    /// Request timeout in seconds
    pub request_timeout: u64,
    /// Enable detailed logging
    pub detailed_logging: bool,
}

impl Default for SecurityRequest {
    fn default() -> Self {
        Self {
            id: Uuid::new_v4(),
            method: "GET".to_string(),
            path: "/".to_string(),
            query_params: HashMap::new(),
            headers: HashMap::new(),
            body: None,
            client_ip: "127.0.0.1".parse().unwrap(),
            user_agent: None,
            referer: None,
            timestamp: Utc::now(),
            size_bytes: 0,
            auth_info: None,
            session_info: None,
            metadata: HashMap::new(),
        }
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            waf_enabled: true,
            threat_detection_enabled: true,
            rate_limiting_enabled: true,
            ip_filtering_enabled: true,
            threat_threshold: 0.7,
            max_request_size: 10 * 1024 * 1024, // 10MB
            request_timeout: 30,
            detailed_logging: true,
        }
    }
}

impl SecurityRequest {
    /// Create a new security request from HTTP components
    pub fn new(
        method: String,
        path: String,
        headers: HashMap<String, String>,
        body: Option<String>,
        client_ip: IpAddr,
    ) -> Self {
        let size_bytes = body.as_ref().map(|b| b.len()).unwrap_or(0) + 
                        headers.iter().map(|(k, v)| k.len() + v.len()).sum::<usize>();

        Self {
            id: Uuid::new_v4(),
            method,
            path,
            query_params: HashMap::new(),
            headers,
            body,
            client_ip,
            user_agent: None,
            referer: None,
            timestamp: Utc::now(),
            size_bytes,
            auth_info: None,
            session_info: None,
            metadata: HashMap::new(),
        }
    }

    /// Extract query parameters from the path
    pub fn extract_query_params(&mut self) {
        if let Some(query_start) = self.path.find('?') {
            let query_string = &self.path[query_start + 1..];
            self.path = self.path[..query_start].to_string();
            
            for param in query_string.split('&') {
                if let Some(eq_pos) = param.find('=') {
                    let key = param[..eq_pos].to_string();
                    let value = param[eq_pos + 1..].to_string();
                    self.query_params.insert(key, value);
                }
            }
        }
    }

    /// Get user agent from headers
    pub fn get_user_agent(&self) -> Option<&String> {
        self.headers.get("user-agent")
            .or_else(|| self.headers.get("User-Agent"))
    }

    /// Get referer from headers
    pub fn get_referer(&self) -> Option<&String> {
        self.headers.get("referer")
            .or_else(|| self.headers.get("Referer"))
    }

    /// Check if request is from a mobile device
    pub fn is_mobile(&self) -> bool {
        if let Some(ua) = self.get_user_agent() {
            let ua_lower = ua.to_lowercase();
            ua_lower.contains("mobile") || 
            ua_lower.contains("android") || 
            ua_lower.contains("iphone") || 
            ua_lower.contains("ipad")
        } else {
            false
        }
    }

    /// Get content type from headers
    pub fn get_content_type(&self) -> Option<&String> {
        self.headers.get("content-type")
            .or_else(|| self.headers.get("Content-Type"))
    }

    /// Check if request contains JSON data
    pub fn is_json(&self) -> bool {
        self.get_content_type()
            .map(|ct| ct.contains("application/json"))
            .unwrap_or(false)
    }
}
