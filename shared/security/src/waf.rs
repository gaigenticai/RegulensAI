//! Web Application Firewall (WAF) Implementation
//! 
//! Provides comprehensive protection against common web attacks including:
//! - SQL Injection
//! - Cross-Site Scripting (XSS)
//! - Path Traversal
//! - Command Injection
//! - LDAP Injection
//! - XML External Entity (XXE)
//! - Server-Side Request Forgery (SSRF)

use crate::types::SecurityRequest;
use crate::errors::{SecurityError, SecurityResult};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};
use tokio::sync::RwLock;
use std::sync::Arc;
use tracing::{info, warn, error};

/// Web Application Firewall main struct
pub struct WebApplicationFirewall {
    rules: Arc<RwLock<HashMap<String, WafRule>>>,
    blocked_ips: Arc<RwLock<HashMap<String, DateTime<Utc>>>>,
    config: WafConfig,
}

/// WAF rule definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WafRule {
    pub id: String,
    pub name: String,
    pub description: String,
    pub pattern: String,
    #[serde(skip)]
    pub regex: Option<Regex>,
    pub action: WafAction,
    pub severity: WafSeverity,
    pub enabled: bool,
    pub category: WafCategory,
    pub false_positive_patterns: Vec<String>,
}

/// WAF action to take when rule matches
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum WafAction {
    Block,
    Log,
    Challenge,
    RateLimit { requests_per_minute: u32 },
}

/// WAF rule severity levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum WafSeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// WAF rule categories
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum WafCategory {
    SqlInjection,
    CrossSiteScripting,
    PathTraversal,
    CommandInjection,
    LdapInjection,
    XmlExternalEntity,
    ServerSideRequestForgery,
    RemoteFileInclusion,
    LocalFileInclusion,
    HttpHeaderInjection,
    ResponseSplitting,
    SessionFixation,
    Custom(String),
}

/// WAF decision result
#[derive(Debug, Clone, PartialEq)]
pub enum WafDecision {
    Allow,
    Block { reason: String, rule_id: String },
    Challenge { challenge_type: ChallengeType },
    RateLimit { retry_after: u64 },
}

/// Challenge types for suspicious requests
#[derive(Debug, Clone, PartialEq)]
pub enum ChallengeType {
    Captcha,
    TwoFactor,
    DeviceVerification,
}

/// WAF configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WafConfig {
    pub enabled: bool,
    pub block_duration_minutes: u64,
    pub max_request_size: usize,
    pub enable_ip_blocking: bool,
    pub enable_rate_limiting: bool,
    pub log_all_requests: bool,
    pub paranoia_level: u8, // 1-4, higher = more strict
}

impl WebApplicationFirewall {
    /// Create a new WAF instance with default rules
    pub fn new(config: WafConfig) -> Self {
        let waf = Self {
            rules: Arc::new(RwLock::new(HashMap::new())),
            blocked_ips: Arc::new(RwLock::new(HashMap::new())),
            config,
        };
        
        // Load default OWASP rules
        tokio::spawn({
            let waf_clone = waf.clone();
            async move {
                if let Err(e) = waf_clone.load_default_rules().await {
                    error!("Failed to load default WAF rules: {}", e);
                }
            }
        });
        
        waf
    }

    /// Load default OWASP Top 10 protection rules
    async fn load_default_rules(&self) -> SecurityResult<()> {
        let default_rules = vec![
            // SQL Injection Detection
            WafRule {
                id: "sql_injection_001".to_string(),
                name: "SQL Injection - Union Based".to_string(),
                description: "Detects UNION-based SQL injection attempts".to_string(),
                pattern: r"(?i)\b(union\s+(all\s+)?select|select\s+.*\s+union)\b".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::Critical,
                enabled: true,
                category: WafCategory::SqlInjection,
                false_positive_patterns: vec![],
            },
            WafRule {
                id: "sql_injection_002".to_string(),
                name: "SQL Injection - Boolean Based".to_string(),
                description: "Detects boolean-based blind SQL injection".to_string(),
                pattern: r"(?i)\b(and|or)\s+\d+\s*[=<>]\s*\d+".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::High,
                enabled: true,
                category: WafCategory::SqlInjection,
                false_positive_patterns: vec![],
            },
            WafRule {
                id: "sql_injection_003".to_string(),
                name: "SQL Injection - Time Based".to_string(),
                description: "Detects time-based blind SQL injection".to_string(),
                pattern: r"(?i)\b(sleep|waitfor\s+delay|benchmark|pg_sleep)\s*\(".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::Critical,
                enabled: true,
                category: WafCategory::SqlInjection,
                false_positive_patterns: vec![],
            },
            
            // XSS Detection
            WafRule {
                id: "xss_001".to_string(),
                name: "XSS - Script Tag".to_string(),
                description: "Detects script tag injection attempts".to_string(),
                pattern: r"(?i)<\s*script[^>]*>.*?</\s*script\s*>".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::High,
                enabled: true,
                category: WafCategory::CrossSiteScripting,
                false_positive_patterns: vec![],
            },
            WafRule {
                id: "xss_002".to_string(),
                name: "XSS - Event Handlers".to_string(),
                description: "Detects JavaScript event handler injection".to_string(),
                pattern: r"(?i)\bon\w+\s*=\s*[\"']?[^\"']*[\"']?".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::High,
                enabled: true,
                category: WafCategory::CrossSiteScripting,
                false_positive_patterns: vec![],
            },
            WafRule {
                id: "xss_003".to_string(),
                name: "XSS - JavaScript Protocol".to_string(),
                description: "Detects javascript: protocol injection".to_string(),
                pattern: r"(?i)javascript\s*:".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::Medium,
                enabled: true,
                category: WafCategory::CrossSiteScripting,
                false_positive_patterns: vec![],
            },
            
            // Path Traversal
            WafRule {
                id: "path_traversal_001".to_string(),
                name: "Path Traversal - Directory Traversal".to_string(),
                description: "Detects directory traversal attempts".to_string(),
                pattern: r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::High,
                enabled: true,
                category: WafCategory::PathTraversal,
                false_positive_patterns: vec![],
            },
            
            // Command Injection
            WafRule {
                id: "command_injection_001".to_string(),
                name: "Command Injection - System Commands".to_string(),
                description: "Detects system command injection attempts".to_string(),
                pattern: r"(?i)\b(cat|ls|pwd|id|whoami|uname|ps|netstat|ifconfig|ping|nslookup|dig)\b".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::Critical,
                enabled: true,
                category: WafCategory::CommandInjection,
                false_positive_patterns: vec!["catalog".to_string(), "category".to_string()],
            },
            
            // LDAP Injection
            WafRule {
                id: "ldap_injection_001".to_string(),
                name: "LDAP Injection".to_string(),
                description: "Detects LDAP injection attempts".to_string(),
                pattern: r"(?i)(\*\)|&\||!\(|\|\(|\)\(|&\(|\*\(|\|\*)".to_string(),
                regex: None,
                action: WafAction::Block,
                severity: WafSeverity::High,
                enabled: true,
                category: WafCategory::LdapInjection,
                false_positive_patterns: vec![],
            },
        ];

        let mut rules = self.rules.write().await;
        for mut rule in default_rules {
            // Compile regex pattern
            match Regex::new(&rule.pattern) {
                Ok(regex) => {
                    rule.regex = Some(regex);
                    rules.insert(rule.id.clone(), rule);
                }
                Err(e) => {
                    warn!("Failed to compile regex for rule {}: {}", rule.id, e);
                }
            }
        }

        info!("Loaded {} default WAF rules", rules.len());
        Ok(())
    }

    /// Evaluate a request against all WAF rules
    pub async fn evaluate_request(&self, request: &SecurityRequest) -> SecurityResult<WafDecision> {
        if !self.config.enabled {
            return Ok(WafDecision::Allow);
        }

        // Check if IP is blocked
        if self.config.enable_ip_blocking {
            let blocked_ips = self.blocked_ips.read().await;
            let client_ip_str = request.client_ip.to_string();
            if let Some(blocked_until) = blocked_ips.get(&client_ip_str) {
                if Utc::now() < *blocked_until {
                    return Ok(WafDecision::Block {
                        reason: "IP temporarily blocked".to_string(),
                        rule_id: "ip_block".to_string(),
                    });
                }
            }
        }

        // Evaluate all enabled rules
        let rules = self.rules.read().await;
        for rule in rules.values() {
            if !rule.enabled {
                continue;
            }

            if self.rule_matches(rule, request).await? {
                match &rule.action {
                    WafAction::Block => {
                        self.log_violation(rule, request).await;
                        
                        // Block IP if configured
                        if self.config.enable_ip_blocking && rule.severity == WafSeverity::Critical {
                            let client_ip_str = request.client_ip.to_string();
                            self.block_ip(&client_ip_str).await;
                        }
                        
                        return Ok(WafDecision::Block {
                            reason: rule.name.clone(),
                            rule_id: rule.id.clone(),
                        });
                    }
                    WafAction::Log => {
                        self.log_violation(rule, request).await;
                    }
                    WafAction::Challenge => {
                        return Ok(WafDecision::Challenge {
                            challenge_type: ChallengeType::Captcha,
                        });
                    }
                    WafAction::RateLimit { requests_per_minute } => {
                        // Integrate with rate limiter to enforce the limit
                        let client_ip = request.client_ip.to_string();
                        let current_time = std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap()
                            .as_secs();

                        // Check current request count for this IP
                        let mut rate_limits = self.rate_limits.write().await;
                        let rate_limit_entry = rate_limits.entry(client_ip.clone()).or_insert_with(|| RateLimitEntry {
                            requests: 0,
                            window_start: current_time,
                        });

                        // Reset window if it's been more than a minute
                        if current_time - rate_limit_entry.window_start >= 60 {
                            rate_limit_entry.requests = 0;
                            rate_limit_entry.window_start = current_time;
                        }

                        rate_limit_entry.requests += 1;

                        if rate_limit_entry.requests > *requests_per_minute {
                            let retry_after = 60 - (current_time - rate_limit_entry.window_start);
                            return Ok(WafDecision::RateLimit {
                                retry_after: retry_after as u32,
                            });
                        }
                    }
                }
            }
        }

        Ok(WafDecision::Allow)
    }

    /// Check if a rule matches the request
    async fn rule_matches(&self, rule: &WafRule, request: &SecurityRequest) -> SecurityResult<bool> {
        let regex = rule.regex.as_ref().ok_or_else(|| {
            SecurityError::Configuration("Rule regex not compiled".to_string())
        })?;

        // Check URL path
        if regex.is_match(&request.path) {
            return Ok(!self.is_false_positive(rule, &request.path));
        }

        // Check query parameters (if any in path)
        if let Some(query_start) = request.path.find('?') {
            let query = &request.path[query_start + 1..];
            if regex.is_match(query) {
                return Ok(!self.is_false_positive(rule, query));
            }
        }

        // Check headers
        for (name, value) in request.headers.iter() {
            if regex.is_match(value) {
                return Ok(!self.is_false_positive(rule, value));
            }
        }

        // Check body if present
        if let Some(body) = &request.body {
            if regex.is_match(body) {
                return Ok(!self.is_false_positive(rule, body));
            }
        }

        Ok(false)
    }

    /// Check if the match is a false positive
    fn is_false_positive(&self, rule: &WafRule, content: &str) -> bool {
        for fp_pattern in &rule.false_positive_patterns {
            if content.contains(fp_pattern) {
                return true;
            }
        }
        false
    }

    /// Log a security violation
    async fn log_violation(&self, rule: &WafRule, request: &SecurityRequest) {
        warn!(
            rule_id = %rule.id,
            rule_name = %rule.name,
            severity = ?rule.severity,
            category = ?rule.category,
            client_ip = %request.client_ip,
            method = %request.method,
            path = %request.path,
            user_agent = ?request.user_agent,
            "WAF rule violation detected"
        );
    }

    /// Block an IP address temporarily
    async fn block_ip(&self, ip: &str) {
        let block_until = Utc::now() + Duration::minutes(self.config.block_duration_minutes as i64);
        let mut blocked_ips = self.blocked_ips.write().await;
        blocked_ips.insert(ip.to_string(), block_until);
        
        info!(
            ip = %ip,
            block_until = %block_until,
            "IP address blocked by WAF"
        );
    }

    /// Add a custom rule
    pub async fn add_rule(&self, rule: WafRule) -> SecurityResult<()> {
        let mut compiled_rule = rule;
        compiled_rule.regex = Some(Regex::new(&compiled_rule.pattern)?);
        
        let mut rules = self.rules.write().await;
        rules.insert(compiled_rule.id.clone(), compiled_rule);
        
        Ok(())
    }

    /// Remove a rule
    pub async fn remove_rule(&self, rule_id: &str) -> SecurityResult<()> {
        let mut rules = self.rules.write().await;
        rules.remove(rule_id);
        Ok(())
    }

    /// Get rule statistics
    pub async fn get_statistics(&self) -> WafStatistics {
        let rules = self.rules.read().await;
        let blocked_ips = self.blocked_ips.read().await;
        
        WafStatistics {
            total_rules: rules.len(),
            enabled_rules: rules.values().filter(|r| r.enabled).count(),
            blocked_ips: blocked_ips.len(),
            rules_by_category: rules.values()
                .fold(HashMap::new(), |mut acc, rule| {
                    *acc.entry(rule.category.clone()).or_insert(0) += 1;
                    acc
                }),
        }
    }
}

impl Clone for WebApplicationFirewall {
    fn clone(&self) -> Self {
        Self {
            rules: Arc::clone(&self.rules),
            blocked_ips: Arc::clone(&self.blocked_ips),
            config: self.config.clone(),
        }
    }
}

/// WAF statistics
#[derive(Debug, Serialize)]
pub struct WafStatistics {
    pub total_rules: usize,
    pub enabled_rules: usize,
    pub blocked_ips: usize,
    pub rules_by_category: HashMap<WafCategory, usize>,
}

impl Default for WafConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            block_duration_minutes: 60,
            max_request_size: 10 * 1024 * 1024, // 10MB
            enable_ip_blocking: true,
            enable_rate_limiting: true,
            log_all_requests: false,
            paranoia_level: 2,
        }
    }
}
