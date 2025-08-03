//! Security Metrics Collection and Monitoring

use prometheus::{Counter, Histogram, Gauge, register_counter, register_histogram, register_gauge};
use lazy_static::lazy_static;
use std::collections::HashMap;

lazy_static! {
    // WAF metrics
    pub static ref WAF_REQUESTS_TOTAL: Counter = register_counter!(
        "security_waf_requests_total",
        "Total number of requests processed by WAF"
    ).unwrap();

    pub static ref WAF_BLOCKED_REQUESTS: Counter = register_counter!(
        "security_waf_blocked_requests_total",
        "Total number of requests blocked by WAF"
    ).unwrap();

    pub static ref WAF_RULE_VIOLATIONS: Counter = register_counter!(
        "security_waf_rule_violations_total",
        "Total number of WAF rule violations"
    ).unwrap();

    // OWASP scanner metrics
    pub static ref OWASP_VULNERABILITIES_DETECTED: Counter = register_counter!(
        "security_owasp_vulnerabilities_detected_total",
        "Total number of OWASP vulnerabilities detected"
    ).unwrap();

    pub static ref OWASP_SCAN_DURATION: Histogram = register_histogram!(
        "security_owasp_scan_duration_seconds",
        "Time taken to complete OWASP scans"
    ).unwrap();

    // Rate limiting metrics
    pub static ref RATE_LIMIT_EXCEEDED: Counter = register_counter!(
        "security_rate_limit_exceeded_total",
        "Total number of rate limit violations"
    ).unwrap();

    pub static ref RATE_LIMIT_ACTIVE_LIMITERS: Gauge = register_gauge!(
        "security_rate_limit_active_limiters",
        "Number of active rate limiters"
    ).unwrap();

    // IP filtering metrics
    pub static ref IP_FILTER_BLOCKED: Counter = register_counter!(
        "security_ip_filter_blocked_total",
        "Total number of IPs blocked by IP filter"
    ).unwrap();

    pub static ref IP_FILTER_ACTIVE_RULES: Gauge = register_gauge!(
        "security_ip_filter_active_rules",
        "Number of active IP filter rules"
    ).unwrap();

    // Threat detection metrics
    pub static ref THREATS_DETECTED: Counter = register_counter!(
        "security_threats_detected_total",
        "Total number of threats detected"
    ).unwrap();

    pub static ref THREAT_DETECTION_DURATION: Histogram = register_histogram!(
        "security_threat_detection_duration_seconds",
        "Time taken for threat detection analysis"
    ).unwrap();

    // Authentication metrics
    pub static ref AUTH_ATTEMPTS_TOTAL: Counter = register_counter!(
        "security_auth_attempts_total",
        "Total number of authentication attempts"
    ).unwrap();

    pub static ref AUTH_FAILURES_TOTAL: Counter = register_counter!(
        "security_auth_failures_total",
        "Total number of authentication failures"
    ).unwrap();

    pub static ref AUTH_SUCCESSES_TOTAL: Counter = register_counter!(
        "security_auth_successes_total",
        "Total number of successful authentications"
    ).unwrap();

    // Session metrics
    pub static ref ACTIVE_SESSIONS: Gauge = register_gauge!(
        "security_active_sessions",
        "Number of active user sessions"
    ).unwrap();

    pub static ref SESSION_DURATION: Histogram = register_histogram!(
        "security_session_duration_seconds",
        "Duration of user sessions"
    ).unwrap();

    // Security scan metrics
    pub static ref SECURITY_SCANS_TOTAL: Counter = register_counter!(
        "security_scans_total",
        "Total number of security scans performed"
    ).unwrap();

    pub static ref SECURITY_SCAN_DURATION: Histogram = register_histogram!(
        "security_scan_duration_seconds",
        "Time taken to complete security scans"
    ).unwrap();

    // Vulnerability metrics
    pub static ref VULNERABILITIES_FOUND: Counter = register_counter!(
        "security_vulnerabilities_found_total",
        "Total number of vulnerabilities found"
    ).unwrap();

    pub static ref VULNERABILITIES_FIXED: Counter = register_counter!(
        "security_vulnerabilities_fixed_total",
        "Total number of vulnerabilities fixed"
    ).unwrap();
}

/// Security metrics collector
pub struct SecurityMetrics;

impl SecurityMetrics {
    /// Record a WAF request
    pub fn record_waf_request(&self) {
        WAF_REQUESTS_TOTAL.inc();
    }

    /// Record a WAF block
    pub fn record_waf_block(&self, rule_id: &str, reason: &str) {
        WAF_BLOCKED_REQUESTS.inc();
        WAF_RULE_VIOLATIONS.inc();
        
        tracing::info!(
            rule_id = rule_id,
            reason = reason,
            "WAF blocked request"
        );
    }

    /// Record a blocked request by category
    pub fn record_blocked_request(&self, category: &str, client_ip: &str) {
        match category {
            "waf" => WAF_BLOCKED_REQUESTS.inc(),
            "rate_limit" => RATE_LIMIT_EXCEEDED.inc(),
            "ip_filter" => IP_FILTER_BLOCKED.inc(),
            _ => {}
        }
        
        tracing::warn!(
            category = category,
            client_ip = client_ip,
            "Request blocked by security system"
        );
    }

    /// Record rate limit exceeded
    pub fn record_rate_limit_exceeded(&self, client_ip: &str) {
        RATE_LIMIT_EXCEEDED.inc();
        
        tracing::warn!(
            client_ip = client_ip,
            "Rate limit exceeded"
        );
    }

    /// Record vulnerability detected
    pub fn record_vulnerability_detected(&self, category: &str) {
        OWASP_VULNERABILITIES_DETECTED.inc();
        VULNERABILITIES_FOUND.inc();
        
        tracing::warn!(
            category = category,
            "Vulnerability detected"
        );
    }

    /// Record threat detected
    pub fn record_threat_detected(&self, threat_type: &str, severity: &str, client_ip: &str) {
        THREATS_DETECTED.inc();
        
        tracing::warn!(
            threat_type = threat_type,
            severity = severity,
            client_ip = client_ip,
            "Threat detected"
        );
    }

    /// Record authentication attempt
    pub fn record_auth_attempt(&self, success: bool, client_ip: &str, user_id: Option<&str>) {
        AUTH_ATTEMPTS_TOTAL.inc();
        
        if success {
            AUTH_SUCCESSES_TOTAL.inc();
            tracing::info!(
                client_ip = client_ip,
                user_id = user_id,
                "Authentication successful"
            );
        } else {
            AUTH_FAILURES_TOTAL.inc();
            tracing::warn!(
                client_ip = client_ip,
                user_id = user_id,
                "Authentication failed"
            );
        }
    }

    /// Update active sessions count
    pub fn update_active_sessions(&self, count: i64) {
        ACTIVE_SESSIONS.set(count as f64);
    }

    /// Record session duration
    pub fn record_session_duration(&self, duration_seconds: f64) {
        SESSION_DURATION.observe(duration_seconds);
    }

    /// Record security scan
    pub fn record_security_scan(&self, scan_type: &str, duration_seconds: f64, vulnerabilities_found: usize) {
        SECURITY_SCANS_TOTAL.inc();
        SECURITY_SCAN_DURATION.observe(duration_seconds);
        
        if vulnerabilities_found > 0 {
            for _ in 0..vulnerabilities_found {
                VULNERABILITIES_FOUND.inc();
            }
        }
        
        tracing::info!(
            scan_type = scan_type,
            duration_seconds = duration_seconds,
            vulnerabilities_found = vulnerabilities_found,
            "Security scan completed"
        );
    }

    /// Record OWASP scan
    pub fn record_owasp_scan(&self, duration_seconds: f64, vulnerabilities_found: usize) {
        let timer = OWASP_SCAN_DURATION.start_timer();
        
        for _ in 0..vulnerabilities_found {
            OWASP_VULNERABILITIES_DETECTED.inc();
        }
        
        timer.observe_duration();
        
        tracing::info!(
            duration_seconds = duration_seconds,
            vulnerabilities_found = vulnerabilities_found,
            "OWASP scan completed"
        );
    }

    /// Record threat detection analysis
    pub fn record_threat_analysis(&self, duration_seconds: f64, threats_found: usize) {
        THREAT_DETECTION_DURATION.observe(duration_seconds);
        
        for _ in 0..threats_found {
            THREATS_DETECTED.inc();
        }
    }

    /// Update rate limiter statistics
    pub fn update_rate_limiter_stats(&self, active_limiters: usize) {
        RATE_LIMIT_ACTIVE_LIMITERS.set(active_limiters as f64);
    }

    /// Update IP filter statistics
    pub fn update_ip_filter_stats(&self, active_rules: usize) {
        IP_FILTER_ACTIVE_RULES.set(active_rules as f64);
    }

    /// Record vulnerability fixed
    pub fn record_vulnerability_fixed(&self, vulnerability_id: &str, severity: &str) {
        VULNERABILITIES_FIXED.inc();
        
        tracing::info!(
            vulnerability_id = vulnerability_id,
            severity = severity,
            "Vulnerability fixed"
        );
    }

    /// Get security metrics summary
    pub fn get_metrics_summary(&self) -> SecurityMetricsSummary {
        SecurityMetricsSummary {
            total_waf_requests: WAF_REQUESTS_TOTAL.get() as u64,
            total_blocked_requests: WAF_BLOCKED_REQUESTS.get() as u64,
            total_rate_limit_violations: RATE_LIMIT_EXCEEDED.get() as u64,
            total_threats_detected: THREATS_DETECTED.get() as u64,
            total_vulnerabilities_found: VULNERABILITIES_FOUND.get() as u64,
            total_vulnerabilities_fixed: VULNERABILITIES_FIXED.get() as u64,
            total_auth_attempts: AUTH_ATTEMPTS_TOTAL.get() as u64,
            total_auth_failures: AUTH_FAILURES_TOTAL.get() as u64,
            active_sessions: ACTIVE_SESSIONS.get() as u64,
            active_rate_limiters: RATE_LIMIT_ACTIVE_LIMITERS.get() as u64,
            active_ip_filter_rules: IP_FILTER_ACTIVE_RULES.get() as u64,
        }
    }
}

/// Security metrics summary
#[derive(Debug, serde::Serialize)]
pub struct SecurityMetricsSummary {
    pub total_waf_requests: u64,
    pub total_blocked_requests: u64,
    pub total_rate_limit_violations: u64,
    pub total_threats_detected: u64,
    pub total_vulnerabilities_found: u64,
    pub total_vulnerabilities_fixed: u64,
    pub total_auth_attempts: u64,
    pub total_auth_failures: u64,
    pub active_sessions: u64,
    pub active_rate_limiters: u64,
    pub active_ip_filter_rules: u64,
}
