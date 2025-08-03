//! Security Headers Management

use axum::http::HeaderMap;
use serde::{Deserialize, Serialize};

/// Security headers configuration and management
pub struct SecurityHeaders {
    config: SecurityHeadersConfig,
}

/// Security headers configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityHeadersConfig {
    pub enabled: bool,
    pub strict_transport_security: Option<String>,
    pub content_security_policy: Option<String>,
    pub x_frame_options: Option<String>,
    pub x_content_type_options: Option<String>,
    pub x_xss_protection: Option<String>,
    pub referrer_policy: Option<String>,
    pub permissions_policy: Option<String>,
    pub cross_origin_embedder_policy: Option<String>,
    pub cross_origin_opener_policy: Option<String>,
    pub cross_origin_resource_policy: Option<String>,
}

impl SecurityHeaders {
    /// Create new security headers manager
    pub fn new(config: SecurityHeadersConfig) -> Self {
        Self { config }
    }

    /// Apply security headers to response
    pub fn apply_headers(&self, headers: &mut HeaderMap) {
        if !self.config.enabled {
            return;
        }

        if let Some(ref hsts) = self.config.strict_transport_security {
            headers.insert("Strict-Transport-Security", hsts.parse().unwrap());
        }

        if let Some(ref csp) = self.config.content_security_policy {
            headers.insert("Content-Security-Policy", csp.parse().unwrap());
        }

        if let Some(ref xfo) = self.config.x_frame_options {
            headers.insert("X-Frame-Options", xfo.parse().unwrap());
        }

        if let Some(ref xcto) = self.config.x_content_type_options {
            headers.insert("X-Content-Type-Options", xcto.parse().unwrap());
        }

        if let Some(ref xxp) = self.config.x_xss_protection {
            headers.insert("X-XSS-Protection", xxp.parse().unwrap());
        }

        if let Some(ref rp) = self.config.referrer_policy {
            headers.insert("Referrer-Policy", rp.parse().unwrap());
        }

        if let Some(ref pp) = self.config.permissions_policy {
            headers.insert("Permissions-Policy", pp.parse().unwrap());
        }

        if let Some(ref coep) = self.config.cross_origin_embedder_policy {
            headers.insert("Cross-Origin-Embedder-Policy", coep.parse().unwrap());
        }

        if let Some(ref coop) = self.config.cross_origin_opener_policy {
            headers.insert("Cross-Origin-Opener-Policy", coop.parse().unwrap());
        }

        if let Some(ref corp) = self.config.cross_origin_resource_policy {
            headers.insert("Cross-Origin-Resource-Policy", corp.parse().unwrap());
        }
    }
}

impl Default for SecurityHeadersConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            strict_transport_security: Some("max-age=31536000; includeSubDomains; preload".to_string()),
            content_security_policy: Some("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; child-src 'self'; frame-src 'self'; worker-src 'self'; frame-ancestors 'self'; form-action 'self'; base-uri 'self'".to_string()),
            x_frame_options: Some("DENY".to_string()),
            x_content_type_options: Some("nosniff".to_string()),
            x_xss_protection: Some("1; mode=block".to_string()),
            referrer_policy: Some("strict-origin-when-cross-origin".to_string()),
            permissions_policy: Some("geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=()".to_string()),
            cross_origin_embedder_policy: Some("require-corp".to_string()),
            cross_origin_opener_policy: Some("same-origin".to_string()),
            cross_origin_resource_policy: Some("same-origin".to_string()),
        }
    }
}
