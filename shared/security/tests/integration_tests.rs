//! Integration tests for the security module

use regulateai_security::{
    waf::{WebApplicationFirewall, WafConfig, WafRule, WafAction},
    threat_detection::{ThreatDetector, ThreatDetectionConfig},
    rate_limiting::{RateLimiter, RateLimitConfig},
    ip_filtering::{IpFilter, IpFilterConfig},
    SecurityRequest, SecurityResponse, SecurityResult,
};
use std::net::IpAddr;
use tokio_test;

#[tokio::test]
async fn test_waf_basic_functionality() -> SecurityResult<()> {
    let config = WafConfig::default();
    let waf = WebApplicationFirewall::new(config).await?;

    // Test SQL injection detection
    let request = SecurityRequest {
        method: "POST".to_string(),
        path: "/api/login".to_string(),
        headers: std::collections::HashMap::new(),
        body: Some("username=admin' OR '1'='1&password=test".to_string()),
        client_ip: "192.168.1.100".parse().unwrap(),
        user_agent: Some("TestAgent/1.0".to_string()),
    };

    let response = waf.process_request(&request).await?;
    
    match response {
        SecurityResponse::Blocked { reason, rule_id } => {
            assert!(reason.contains("SQL injection"));
            assert!(!rule_id.is_empty());
            println!("✅ WAF correctly blocked SQL injection attempt");
        }
        SecurityResponse::Allowed => {
            panic!("WAF should have blocked SQL injection attempt");
        }
    }

    Ok(())
}

#[tokio::test]
async fn test_waf_xss_detection() -> SecurityResult<()> {
    let config = WafConfig::default();
    let waf = WebApplicationFirewall::new(config).await?;

    let request = SecurityRequest {
        method: "POST".to_string(),
        path: "/api/comment".to_string(),
        headers: std::collections::HashMap::new(),
        body: Some("comment=<script>alert('xss')</script>".to_string()),
        client_ip: "192.168.1.101".parse().unwrap(),
        user_agent: Some("TestAgent/1.0".to_string()),
    };

    let response = waf.process_request(&request).await?;
    
    match response {
        SecurityResponse::Blocked { reason, rule_id } => {
            assert!(reason.contains("XSS") || reason.contains("script"));
            println!("✅ WAF correctly blocked XSS attempt");
        }
        SecurityResponse::Allowed => {
            panic!("WAF should have blocked XSS attempt");
        }
    }

    Ok(())
}

#[tokio::test]
async fn test_rate_limiting() -> SecurityResult<()> {
    let mut config = RateLimitConfig::default();
    config.default_requests_per_minute = 5;
    config.default_burst_size = 2;
    
    let rate_limiter = RateLimiter::new(config).await?;
    let client_ip: IpAddr = "192.168.1.102".parse().unwrap();

    // First few requests should be allowed
    for i in 1..=3 {
        let allowed = rate_limiter.check_rate_limit(&client_ip, "test_endpoint").await?;
        assert!(allowed, "Request {} should be allowed", i);
    }

    // Rapid subsequent requests should be rate limited
    let mut blocked_count = 0;
    for i in 4..=10 {
        let allowed = rate_limiter.check_rate_limit(&client_ip, "test_endpoint").await?;
        if !allowed {
            blocked_count += 1;
        }
    }

    assert!(blocked_count > 0, "Some requests should have been rate limited");
    println!("✅ Rate limiting working correctly, blocked {} requests", blocked_count);

    Ok(())
}

#[tokio::test]
async fn test_ip_filtering() -> SecurityResult<()> {
    let config = IpFilterConfig::default();
    let mut ip_filter = IpFilter::new(config).await?;

    // Add a blocked IP
    let blocked_ip: IpAddr = "10.0.0.1".parse().unwrap();
    ip_filter.add_blocked_ip(blocked_ip, "Test block".to_string()).await?;

    // Test that blocked IP is rejected
    let is_allowed = ip_filter.is_ip_allowed(&blocked_ip).await?;
    assert!(!is_allowed, "Blocked IP should not be allowed");

    // Test that other IPs are allowed
    let allowed_ip: IpAddr = "192.168.1.103".parse().unwrap();
    let is_allowed = ip_filter.is_ip_allowed(&allowed_ip).await?;
    assert!(is_allowed, "Non-blocked IP should be allowed");

    println!("✅ IP filtering working correctly");

    Ok(())
}

#[tokio::test]
async fn test_threat_detection() -> SecurityResult<()> {
    let config = ThreatDetectionConfig::default();
    let threat_detector = ThreatDetector::new(config).await?;

    // Test suspicious request pattern
    let request = SecurityRequest {
        method: "GET".to_string(),
        path: "/admin/../../../etc/passwd".to_string(),
        headers: std::collections::HashMap::new(),
        body: None,
        client_ip: "192.168.1.104".parse().unwrap(),
        user_agent: Some("curl/7.68.0".to_string()),
    };

    let threat_score = threat_detector.analyze_request(&request).await?;
    assert!(threat_score > 0.5, "Path traversal attempt should have high threat score");

    println!("✅ Threat detection working correctly, threat score: {:.2}", threat_score);

    Ok(())
}

#[tokio::test]
async fn test_security_headers() -> SecurityResult<()> {
    use regulateai_security::security_headers::{SecurityHeaders, SecurityHeadersConfig};

    let config = SecurityHeadersConfig::default();
    let security_headers = SecurityHeaders::new(config);

    let mut headers = std::collections::HashMap::new();
    security_headers.apply_headers(&mut headers);

    // Check that security headers are applied
    assert!(headers.contains_key("X-Content-Type-Options"));
    assert!(headers.contains_key("X-Frame-Options"));
    assert!(headers.contains_key("X-XSS-Protection"));
    assert!(headers.contains_key("Strict-Transport-Security"));

    println!("✅ Security headers applied correctly: {} headers", headers.len());

    Ok(())
}

#[tokio::test]
async fn test_comprehensive_security_pipeline() -> SecurityResult<()> {
    // Test the complete security pipeline
    let waf_config = WafConfig::default();
    let waf = WebApplicationFirewall::new(waf_config).await?;

    let rate_limit_config = RateLimitConfig::default();
    let rate_limiter = RateLimiter::new(rate_limit_config).await?;

    let ip_filter_config = IpFilterConfig::default();
    let ip_filter = IpFilter::new(ip_filter_config).await?;

    let threat_config = ThreatDetectionConfig::default();
    let threat_detector = ThreatDetector::new(threat_config).await?;

    // Test a legitimate request
    let legitimate_request = SecurityRequest {
        method: "GET".to_string(),
        path: "/api/users".to_string(),
        headers: std::collections::HashMap::new(),
        body: None,
        client_ip: "192.168.1.105".parse().unwrap(),
        user_agent: Some("Mozilla/5.0".to_string()),
    };

    // Should pass all security checks
    let ip_allowed = ip_filter.is_ip_allowed(&legitimate_request.client_ip).await?;
    assert!(ip_allowed);

    let rate_allowed = rate_limiter.check_rate_limit(&legitimate_request.client_ip, &legitimate_request.path).await?;
    assert!(rate_allowed);

    let waf_response = waf.process_request(&legitimate_request).await?;
    assert!(matches!(waf_response, SecurityResponse::Allowed));

    let threat_score = threat_detector.analyze_request(&legitimate_request).await?;
    assert!(threat_score < 0.3); // Low threat score for legitimate request

    println!("✅ Comprehensive security pipeline working correctly");

    Ok(())
}

#[tokio::test]
async fn test_security_metrics() -> SecurityResult<()> {
    use regulateai_security::metrics::SecurityMetrics;

    let metrics = SecurityMetrics;

    // Test metrics recording
    metrics.record_waf_request().await;
    metrics.record_waf_block("SQL_INJECTION", "Detected SQL injection attempt").await;
    metrics.record_rate_limit_exceeded("192.168.1.106").await;
    metrics.record_threat_detected("PATH_TRAVERSAL", "HIGH", "192.168.1.107").await;

    let summary = metrics.get_metrics_summary();
    
    assert!(summary.total_waf_requests > 0);
    assert!(summary.total_blocked_requests > 0);
    assert!(summary.total_rate_limit_violations > 0);
    assert!(summary.total_threats_detected > 0);

    println!("✅ Security metrics recording correctly");
    println!("   WAF Requests: {}", summary.total_waf_requests);
    println!("   Blocked Requests: {}", summary.total_blocked_requests);
    println!("   Rate Limit Violations: {}", summary.total_rate_limit_violations);
    println!("   Threats Detected: {}", summary.total_threats_detected);

    Ok(())
}

// Edge case and error condition tests

#[tokio::test]
async fn test_waf_with_empty_request() -> SecurityResult<()> {
    let config = WafConfig::default();
    let waf = WebApplicationFirewall::new(config).await?;

    let empty_request = SecurityRequest {
        method: "".to_string(),
        path: "".to_string(),
        headers: std::collections::HashMap::new(),
        body: None,
        client_ip: "127.0.0.1".parse().unwrap(),
        user_agent: None,
    };

    // Should handle empty request gracefully
    let response = waf.process_request(&empty_request).await?;
    // Empty requests should typically be allowed (not malicious)
    assert!(matches!(response, SecurityResponse::Allowed));

    println!("✅ WAF handles empty requests correctly");

    Ok(())
}

#[tokio::test]
async fn test_rate_limiter_edge_cases() -> SecurityResult<()> {
    let mut config = RateLimitConfig::default();
    config.default_requests_per_minute = 1;
    config.default_burst_size = 1;
    
    let rate_limiter = RateLimiter::new(config).await?;
    let client_ip: IpAddr = "192.168.1.200".parse().unwrap();

    // Test with zero requests per minute (should block all)
    let mut zero_config = RateLimitConfig::default();
    zero_config.default_requests_per_minute = 0;
    let zero_limiter = RateLimiter::new(zero_config).await?;
    
    let allowed = zero_limiter.check_rate_limit(&client_ip, "test").await?;
    assert!(!allowed, "Zero rate limit should block all requests");

    println!("✅ Rate limiter edge cases handled correctly");

    Ok(())
}
