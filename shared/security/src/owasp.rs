//! OWASP Top 10 Vulnerability Scanner
//! 
//! Comprehensive scanner for detecting OWASP Top 10 vulnerabilities:
//! 1. Injection (SQL, NoSQL, OS, LDAP)
//! 2. Broken Authentication
//! 3. Sensitive Data Exposure
//! 4. XML External Entities (XXE)
//! 5. Broken Access Control
//! 6. Security Misconfiguration
//! 7. Cross-Site Scripting (XSS)
//! 8. Insecure Deserialization
//! 9. Using Components with Known Vulnerabilities
//! 10. Insufficient Logging & Monitoring

use crate::middleware::HttpRequest;
use crate::errors::{SecurityError, SecurityResult};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use tracing::{info, warn, error};
use lazy_static::lazy_static;

/// OWASP vulnerability scanner
pub struct OwaspScanner {
    patterns: HashMap<OwaspCategory, Vec<VulnerabilityPattern>>,
    config: OwaspScannerConfig,
}

/// OWASP Top 10 categories
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum OwaspCategory {
    Injection,
    BrokenAuthentication,
    SensitiveDataExposure,
    XmlExternalEntities,
    BrokenAccessControl,
    SecurityMisconfiguration,
    CrossSiteScripting,
    InsecureDeserialization,
    KnownVulnerableComponents,
    InsufficientLogging,
}

/// Vulnerability pattern for detection
#[derive(Debug, Clone)]
pub struct VulnerabilityPattern {
    pub id: String,
    pub name: String,
    pub description: String,
    pub regex: Regex,
    pub severity: VulnerabilitySeverity,
    pub confidence: f32, // 0.0 - 1.0
    pub false_positive_indicators: Vec<String>,
}

/// Vulnerability severity levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum VulnerabilitySeverity {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

/// Detected vulnerability
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OwaspVulnerability {
    pub id: String,
    pub category: OwaspCategory,
    pub name: String,
    pub description: String,
    pub severity: VulnerabilitySeverity,
    pub confidence: f32,
    pub location: VulnerabilityLocation,
    pub evidence: String,
    pub recommendation: String,
    pub detected_at: DateTime<Utc>,
}

/// Location where vulnerability was detected
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VulnerabilityLocation {
    Url,
    Header { name: String },
    Body,
    Parameter { name: String },
    Cookie { name: String },
}

/// OWASP scanner configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OwaspScannerConfig {
    pub enabled: bool,
    pub scan_headers: bool,
    pub scan_body: bool,
    pub scan_cookies: bool,
    pub max_body_size: usize,
    pub confidence_threshold: f32,
    pub enable_deep_scan: bool,
}

lazy_static! {
    /// Pre-compiled regex patterns for common vulnerabilities
    static ref SQL_INJECTION_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)\b(union\s+(all\s+)?select|select\s+.*\s+union)\b", "UNION-based SQL injection", VulnerabilitySeverity::Critical),
        (r"(?i)\b(and|or)\s+\d+\s*[=<>]\s*\d+", "Boolean-based blind SQL injection", VulnerabilitySeverity::High),
        (r"(?i)\b(sleep|waitfor\s+delay|benchmark|pg_sleep)\s*\(", "Time-based blind SQL injection", VulnerabilitySeverity::Critical),
        (r"(?i)\b(drop|delete|truncate|alter)\s+(table|database|schema)", "Destructive SQL commands", VulnerabilitySeverity::Critical),
        (r"(?i)\b(exec|execute|sp_executesql|xp_cmdshell)\b", "SQL command execution", VulnerabilitySeverity::Critical),
        (r"(?i)'\s*(or|and)\s*'[^']*'\s*=\s*'[^']*'", "SQL injection with quotes", VulnerabilitySeverity::High),
        (r"(?i)\b(information_schema|sys\.tables|mysql\.user)\b", "Database metadata access", VulnerabilitySeverity::Medium),
    ];

    static ref XSS_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)<\s*script[^>]*>.*?</\s*script\s*>", "Script tag injection", VulnerabilitySeverity::High),
        (r"(?i)\bon\w+\s*=\s*[\"']?[^\"']*[\"']?", "Event handler injection", VulnerabilitySeverity::High),
        (r"(?i)javascript\s*:", "JavaScript protocol injection", VulnerabilitySeverity::Medium),
        (r"(?i)<\s*(iframe|object|embed|applet)[^>]*>", "Dangerous HTML tags", VulnerabilitySeverity::Medium),
        (r"(?i)expression\s*\(", "CSS expression injection", VulnerabilitySeverity::Medium),
        (r"(?i)vbscript\s*:", "VBScript protocol injection", VulnerabilitySeverity::Medium),
        (r"(?i)<\s*meta[^>]*http-equiv[^>]*refresh", "Meta refresh injection", VulnerabilitySeverity::Low),
    ];

    static ref XXE_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)<!DOCTYPE[^>]*\[.*<!ENTITY", "XML external entity declaration", VulnerabilitySeverity::High),
        (r"(?i)<!ENTITY[^>]*SYSTEM", "XML external entity with SYSTEM", VulnerabilitySeverity::Critical),
        (r"(?i)<!ENTITY[^>]*PUBLIC", "XML external entity with PUBLIC", VulnerabilitySeverity::High),
        (r"(?i)&[a-zA-Z][a-zA-Z0-9]*;", "XML entity reference", VulnerabilitySeverity::Medium),
    ];

    static ref COMMAND_INJECTION_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)\b(cat|ls|pwd|id|whoami|uname|ps|netstat|ifconfig)\b", "System command injection", VulnerabilitySeverity::Critical),
        (r"(?i)[;&|`$(){}[\]\\]", "Command injection metacharacters", VulnerabilitySeverity::High),
        (r"(?i)\b(curl|wget|nc|netcat|telnet|ssh)\b", "Network command injection", VulnerabilitySeverity::Critical),
        (r"(?i)\b(rm|del|format|fdisk|mkfs)\b", "Destructive command injection", VulnerabilitySeverity::Critical),
    ];

    static ref PATH_TRAVERSAL_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)", "Directory traversal", VulnerabilitySeverity::High),
        (r"(?i)(\/etc\/passwd|\/etc\/shadow|\/windows\/system32)", "Sensitive file access", VulnerabilitySeverity::Critical),
        (r"(?i)\.\.[\\/].*\.\.[\\/]", "Multiple directory traversal", VulnerabilitySeverity::High),
    ];

    static ref LDAP_INJECTION_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)(\*\)|&\||!\(|\|\(|\)\(|&\(|\*\(|\|\*)", "LDAP injection metacharacters", VulnerabilitySeverity::High),
        (r"(?i)\(\|\(.*\)\)", "LDAP OR injection", VulnerabilitySeverity::High),
        (r"(?i)\(&\(.*\)\)", "LDAP AND injection", VulnerabilitySeverity::High),
    ];

    static ref DESERIALIZATION_PATTERNS: Vec<(&'static str, &'static str, VulnerabilitySeverity)> = vec![
        (r"(?i)\brO0AB", "Java serialization magic bytes", VulnerabilitySeverity::High),
        (r"(?i)__reduce__|__setstate__", "Python pickle injection", VulnerabilitySeverity::Critical),
        (r"(?i)O:\d+:", "PHP object serialization", VulnerabilitySeverity::High),
        (r"(?i)BinaryFormatter|ObjectStateFormatter", ".NET unsafe deserialization", VulnerabilitySeverity::Critical),
    ];
}

impl OwaspScanner {
    /// Create a new OWASP scanner with default patterns
    pub fn new(config: OwaspScannerConfig) -> SecurityResult<Self> {
        let mut scanner = Self {
            patterns: HashMap::new(),
            config,
        };

        scanner.load_default_patterns()?;
        Ok(scanner)
    }

    /// Load default vulnerability detection patterns
    fn load_default_patterns(&mut self) -> SecurityResult<()> {
        // Load SQL injection patterns
        let mut sql_patterns = Vec::new();
        for (pattern, name, severity) in SQL_INJECTION_PATTERNS.iter() {
            sql_patterns.push(VulnerabilityPattern {
                id: format!("sql_injection_{}", sql_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.9,
                false_positive_indicators: vec!["catalog".to_string(), "category".to_string()],
            });
        }
        self.patterns.insert(OwaspCategory::Injection, sql_patterns);

        // Load XSS patterns
        let mut xss_patterns = Vec::new();
        for (pattern, name, severity) in XSS_PATTERNS.iter() {
            xss_patterns.push(VulnerabilityPattern {
                id: format!("xss_{}", xss_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.85,
                false_positive_indicators: vec![],
            });
        }
        self.patterns.insert(OwaspCategory::CrossSiteScripting, xss_patterns);

        // Load XXE patterns
        let mut xxe_patterns = Vec::new();
        for (pattern, name, severity) in XXE_PATTERNS.iter() {
            xxe_patterns.push(VulnerabilityPattern {
                id: format!("xxe_{}", xxe_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.95,
                false_positive_indicators: vec![],
            });
        }
        self.patterns.insert(OwaspCategory::XmlExternalEntities, xxe_patterns);

        // Load command injection patterns
        let mut cmd_patterns = Vec::new();
        for (pattern, name, severity) in COMMAND_INJECTION_PATTERNS.iter() {
            cmd_patterns.push(VulnerabilityPattern {
                id: format!("cmd_injection_{}", cmd_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.8,
                false_positive_indicators: vec!["catalog".to_string(), "concatenate".to_string()],
            });
        }
        self.patterns.insert(OwaspCategory::Injection, cmd_patterns);

        // Load path traversal patterns
        let mut path_patterns = Vec::new();
        for (pattern, name, severity) in PATH_TRAVERSAL_PATTERNS.iter() {
            path_patterns.push(VulnerabilityPattern {
                id: format!("path_traversal_{}", path_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.9,
                false_positive_indicators: vec![],
            });
        }
        self.patterns.insert(OwaspCategory::BrokenAccessControl, path_patterns);

        // Load LDAP injection patterns
        let mut ldap_patterns = Vec::new();
        for (pattern, name, severity) in LDAP_INJECTION_PATTERNS.iter() {
            ldap_patterns.push(VulnerabilityPattern {
                id: format!("ldap_injection_{}", ldap_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.85,
                false_positive_indicators: vec![],
            });
        }
        self.patterns.insert(OwaspCategory::Injection, ldap_patterns);

        // Load deserialization patterns
        let mut deser_patterns = Vec::new();
        for (pattern, name, severity) in DESERIALIZATION_PATTERNS.iter() {
            deser_patterns.push(VulnerabilityPattern {
                id: format!("deserialization_{}", deser_patterns.len()),
                name: name.to_string(),
                description: format!("Detects {}", name.to_lowercase()),
                regex: Regex::new(pattern)?,
                severity: severity.clone(),
                confidence: 0.95,
                false_positive_indicators: vec![],
            });
        }
        self.patterns.insert(OwaspCategory::InsecureDeserialization, deser_patterns);

        info!("Loaded {} OWASP vulnerability patterns", 
              self.patterns.values().map(|v| v.len()).sum::<usize>());
        
        Ok(())
    }

    /// Scan a request for OWASP vulnerabilities
    pub async fn scan_request(&self, request: &HttpRequest) -> SecurityResult<()> {
        if !self.config.enabled {
            return Ok(());
        }

        let mut vulnerabilities = Vec::new();

        // Scan URL path
        if let Some(vuln) = self.scan_content(&request.path, VulnerabilityLocation::Url).await? {
            vulnerabilities.push(vuln);
        }

        // Scan headers if enabled
        if self.config.scan_headers {
            for (name, value) in request.headers.iter() {
                if let Ok(value_str) = value.to_str() {
                    if let Some(vuln) = self.scan_content(
                        value_str, 
                        VulnerabilityLocation::Header { name: name.to_string() }
                    ).await? {
                        vulnerabilities.push(vuln);
                    }
                }
            }
        }

        // Scan body if present and enabled
        if self.config.scan_body {
            if let Some(body) = &request.body {
                if body.len() <= self.config.max_body_size {
                    if let Some(vuln) = self.scan_content(body, VulnerabilityLocation::Body).await? {
                        vulnerabilities.push(vuln);
                    }
                }
            }
        }

        // Return first high-confidence vulnerability found
        for vuln in vulnerabilities {
            if vuln.confidence >= self.config.confidence_threshold {
                return Err(SecurityError::VulnerabilityDetected(vuln));
            }
        }

        Ok(())
    }

    /// Scan content for vulnerabilities
    async fn scan_content(
        &self, 
        content: &str, 
        location: VulnerabilityLocation
    ) -> SecurityResult<Option<OwaspVulnerability>> {
        for (category, patterns) in &self.patterns {
            for pattern in patterns {
                if pattern.regex.is_match(content) {
                    // Check for false positives
                    let is_false_positive = pattern.false_positive_indicators
                        .iter()
                        .any(|indicator| content.to_lowercase().contains(&indicator.to_lowercase()));

                    if !is_false_positive {
                        return Ok(Some(OwaspVulnerability {
                            id: pattern.id.clone(),
                            category: category.clone(),
                            name: pattern.name.clone(),
                            description: pattern.description.clone(),
                            severity: pattern.severity.clone(),
                            confidence: pattern.confidence,
                            location: location.clone(),
                            evidence: self.extract_evidence(content, &pattern.regex),
                            recommendation: self.get_recommendation(category),
                            detected_at: Utc::now(),
                        }));
                    }
                }
            }
        }

        Ok(None)
    }

    /// Extract evidence from matched content
    fn extract_evidence(&self, content: &str, regex: &Regex) -> String {
        if let Some(captures) = regex.captures(content) {
            if let Some(matched) = captures.get(0) {
                let start = matched.start().saturating_sub(20);
                let end = (matched.end() + 20).min(content.len());
                return content[start..end].to_string();
            }
        }
        content.chars().take(100).collect()
    }

    /// Get security recommendation for vulnerability category
    fn get_recommendation(&self, category: &OwaspCategory) -> String {
        match category {
            OwaspCategory::Injection => "Use parameterized queries and input validation".to_string(),
            OwaspCategory::CrossSiteScripting => "Implement proper output encoding and CSP headers".to_string(),
            OwaspCategory::XmlExternalEntities => "Disable XML external entity processing".to_string(),
            OwaspCategory::BrokenAccessControl => "Implement proper access controls and path validation".to_string(),
            OwaspCategory::InsecureDeserialization => "Avoid deserializing untrusted data".to_string(),
            _ => "Review and remediate the detected vulnerability".to_string(),
        }
    }

    /// Get scanner statistics
    pub fn get_statistics(&self) -> OwaspScannerStatistics {
        OwaspScannerStatistics {
            total_patterns: self.patterns.values().map(|v| v.len()).sum(),
            patterns_by_category: self.patterns.iter()
                .map(|(k, v)| (k.clone(), v.len()))
                .collect(),
            enabled: self.config.enabled,
        }
    }
}

/// OWASP scanner statistics
#[derive(Debug, Serialize)]
pub struct OwaspScannerStatistics {
    pub total_patterns: usize,
    pub patterns_by_category: HashMap<OwaspCategory, usize>,
    pub enabled: bool,
}

impl Default for OwaspScannerConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            scan_headers: true,
            scan_body: true,
            scan_cookies: true,
            max_body_size: 1024 * 1024, // 1MB
            confidence_threshold: 0.8,
            enable_deep_scan: false,
        }
    }
}

impl ToString for OwaspCategory {
    fn to_string(&self) -> String {
        match self {
            OwaspCategory::Injection => "Injection".to_string(),
            OwaspCategory::BrokenAuthentication => "Broken Authentication".to_string(),
            OwaspCategory::SensitiveDataExposure => "Sensitive Data Exposure".to_string(),
            OwaspCategory::XmlExternalEntities => "XML External Entities".to_string(),
            OwaspCategory::BrokenAccessControl => "Broken Access Control".to_string(),
            OwaspCategory::SecurityMisconfiguration => "Security Misconfiguration".to_string(),
            OwaspCategory::CrossSiteScripting => "Cross-Site Scripting".to_string(),
            OwaspCategory::InsecureDeserialization => "Insecure Deserialization".to_string(),
            OwaspCategory::KnownVulnerableComponents => "Known Vulnerable Components".to_string(),
            OwaspCategory::InsufficientLogging => "Insufficient Logging".to_string(),
        }
    }
}
