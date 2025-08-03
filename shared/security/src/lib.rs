//! RegulateAI Security Module
//! 
//! Comprehensive security framework providing:
//! - Web Application Firewall (WAF) protection
//! - OWASP Top 10 vulnerability detection
//! - Advanced threat protection
//! - Rate limiting and DDoS protection
//! - Security monitoring and alerting

pub mod types;
pub mod waf;
pub mod owasp;
pub mod threat_detection;
pub mod rate_limiting;
pub mod ip_filtering;
pub mod security_headers;
pub mod vulnerability_scanner;
pub mod metrics;
pub mod config;
pub mod errors;

pub use types::*;
pub use waf::{WebApplicationFirewall, WafRule, WafAction, WafDecision};
pub use owasp::{OwaspScanner, OwaspVulnerability, OwaspCategory};
pub use threat_detection::{ThreatDetector, ThreatLevel, ThreatType};
pub use rate_limiting::{RateLimiter, RateLimitConfig, RateLimitResult};
pub use ip_filtering::{IpFilter, IpFilterRule, IpFilterAction};
pub use security_headers::SecurityHeaders;
pub use vulnerability_scanner::{VulnerabilityScanner, SecurityScanResult};
pub use metrics::SecurityMetrics;
pub use config::SecurityConfig;
pub use errors::{SecurityError, SecurityResult};

/// Security middleware for Axum applications
pub mod middleware {
    use super::*;
    use axum::{
        extract::{Request, State},
        http::StatusCode,
        middleware::Next,
        response::Response,
    };
    use std::sync::Arc;

    /// Main security middleware that applies all security checks
    pub async fn security_middleware(
        State(security_state): State<Arc<SecurityState>>,
        request: Request,
        next: Next,
    ) -> Result<Response, StatusCode> {
        // Extract client information
        let client_ip = extract_client_ip(&request);
        let user_agent = extract_user_agent(&request);
        let request_path = request.uri().path();
        let request_method = request.method().as_str();

        // 1. IP filtering check
        if let Err(_) = security_state.ip_filter.check_ip(&client_ip).await {
            security_state.metrics.record_blocked_request("ip_filter", &client_ip);
            return Err(StatusCode::FORBIDDEN);
        }

        // 2. Rate limiting check
        match security_state.rate_limiter.check_rate_limit(&client_ip).await {
            Ok(result) if !result.allowed => {
                security_state.metrics.record_rate_limit_exceeded(&client_ip);
                return Err(StatusCode::TOO_MANY_REQUESTS);
            }
            Err(_) => return Err(StatusCode::INTERNAL_SERVER_ERROR),
            _ => {}
        }

        // 3. WAF evaluation
        let http_request = HttpRequest {
            method: request_method.to_string(),
            path: request_path.to_string(),
            headers: request.headers().clone(),
            client_ip: client_ip.clone(),
            user_agent: user_agent.clone(),
            body: None, // Will be populated if needed
        };

        match security_state.waf.evaluate_request(&http_request).await {
            Ok(WafDecision::Block { reason, rule_id }) => {
                security_state.metrics.record_waf_block(&rule_id, &reason);
                tracing::warn!(
                    client_ip = %client_ip,
                    rule_id = %rule_id,
                    reason = %reason,
                    "WAF blocked request"
                );
                return Err(StatusCode::FORBIDDEN);
            }
            Ok(WafDecision::Challenge { .. }) => {
                // For now, treat challenges as blocks
                // In production, this would redirect to a challenge page
                return Err(StatusCode::FORBIDDEN);
            }
            Ok(WafDecision::Allow) => {}
            Err(_) => return Err(StatusCode::INTERNAL_SERVER_ERROR),
        }

        // 4. OWASP vulnerability scanning
        if let Err(vulnerability) = security_state.owasp_scanner.scan_request(&http_request).await {
            security_state.metrics.record_vulnerability_detected(&vulnerability.category.to_string());
            tracing::warn!(
                client_ip = %client_ip,
                vulnerability = ?vulnerability,
                "OWASP vulnerability detected"
            );
            return Err(StatusCode::BAD_REQUEST);
        }

        // Process the request
        let mut response = next.run(request).await;

        // 5. Add security headers to response
        security_state.security_headers.apply_headers(response.headers_mut());

        Ok(response)
    }

    /// Security state shared across middleware
    pub struct SecurityState {
        pub waf: Arc<WebApplicationFirewall>,
        pub owasp_scanner: Arc<OwaspScanner>,
        pub threat_detector: Arc<ThreatDetector>,
        pub rate_limiter: Arc<RateLimiter>,
        pub ip_filter: Arc<IpFilter>,
        pub security_headers: Arc<SecurityHeaders>,
        pub metrics: Arc<SecurityMetrics>,
    }

    /// HTTP request representation for security analysis
    #[derive(Debug, Clone)]
    pub struct HttpRequest {
        pub method: String,
        pub path: String,
        pub headers: axum::http::HeaderMap,
        pub client_ip: String,
        pub user_agent: String,
        pub body: Option<String>,
    }

    fn extract_client_ip(request: &Request) -> String {
        // Try X-Forwarded-For first, then X-Real-IP, then connection info
        request
            .headers()
            .get("x-forwarded-for")
            .and_then(|hv| hv.to_str().ok())
            .and_then(|s| s.split(',').next())
            .map(|s| s.trim().to_string())
            .or_else(|| {
                request
                    .headers()
                    .get("x-real-ip")
                    .and_then(|hv| hv.to_str().ok())
                    .map(|s| s.to_string())
            })
            .unwrap_or_else(|| "unknown".to_string())
    }

    fn extract_user_agent(request: &Request) -> String {
        request
            .headers()
            .get("user-agent")
            .and_then(|hv| hv.to_str().ok())
            .unwrap_or("unknown")
            .to_string()
    }
}
