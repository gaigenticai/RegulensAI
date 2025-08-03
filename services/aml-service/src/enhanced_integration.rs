//! Enhanced Integration Example for AML Service
//! 
//! This module demonstrates how the new security, caching, testing, and metrics
//! modules integrate with the existing AML service to provide enhanced functionality.

use regulateai_security::{
    waf::WebApplicationFirewall,
    threat_detection::ThreatDetector,
    rate_limiting::RateLimiter,
    SecurityRequest, SecurityResponse,
};
use regulateai_cache::{
    multi_level::MultiLevelCache,
    config::CacheConfig,
    Duration,
};
use regulateai_metrics::{
    business_metrics::BusinessMetricsCollector,
    compliance_metrics::ComplianceMetricsCollector,
    risk_metrics::RiskMetricsCollector,
    MetricsRegistry,
};
use axum::{
    extract::{Path, State, Request},
    http::StatusCode,
    middleware::Next,
    response::{Json, Response},
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use uuid::Uuid;

/// Enhanced AML service with integrated security, caching, and metrics
pub struct EnhancedAmlService {
    // Existing AML service components
    aml_processor: Arc<AmlProcessor>,
    
    // New enhanced components
    waf: Arc<WebApplicationFirewall>,
    threat_detector: Arc<ThreatDetector>,
    rate_limiter: Arc<RateLimiter>,
    cache: Arc<MultiLevelCache>,
    metrics: Arc<MetricsRegistry>,
}

/// AML check request with enhanced validation
#[derive(Debug, Deserialize)]
pub struct EnhancedAmlCheckRequest {
    pub customer_id: Uuid,
    pub transaction_id: Option<Uuid>,
    pub amount: f64,
    pub currency: String,
    pub counterparty: String,
    pub transaction_type: String,
    pub metadata: serde_json::Value,
}

/// AML check response with enhanced data
#[derive(Debug, Serialize)]
pub struct EnhancedAmlCheckResponse {
    pub check_id: Uuid,
    pub customer_id: Uuid,
    pub risk_score: f64,
    pub risk_level: String,
    pub compliance_status: String,
    pub recommendations: Vec<String>,
    pub processing_time_ms: u64,
    pub cached: bool,
    pub security_validated: bool,
    pub threat_score: f64,
}

/// Placeholder for existing AML processor
pub struct AmlProcessor;

impl AmlProcessor {
    pub async fn process_aml_check(&self, request: &EnhancedAmlCheckRequest) -> Result<AmlCheckResult, AmlError> {
        // Existing AML processing logic would go here
        Ok(AmlCheckResult {
            risk_score: 25.5,
            risk_level: "MEDIUM".to_string(),
            compliance_status: "COMPLIANT".to_string(),
            recommendations: vec!["Monitor future transactions".to_string()],
        })
    }
}

#[derive(Debug)]
pub struct AmlCheckResult {
    pub risk_score: f64,
    pub risk_level: String,
    pub compliance_status: String,
    pub recommendations: Vec<String>,
}

#[derive(Debug, thiserror::Error)]
pub enum AmlError {
    #[error("Processing error: {0}")]
    Processing(String),
}

impl EnhancedAmlService {
    /// Create a new enhanced AML service with all integrations
    pub async fn new() -> Result<Self, Box<dyn std::error::Error>> {
        // Initialize existing AML processor
        let aml_processor = Arc::new(AmlProcessor);

        // Initialize security components
        let waf_config = regulateai_security::waf::WafConfig::default();
        let waf = Arc::new(WebApplicationFirewall::new(waf_config).await?);

        let threat_config = regulateai_security::threat_detection::ThreatDetectionConfig::default();
        let threat_detector = Arc::new(ThreatDetector::new(threat_config).await?);

        let rate_limit_config = regulateai_security::rate_limiting::RateLimitConfig::default();
        let rate_limiter = Arc::new(RateLimiter::new(rate_limit_config).await?);

        // Initialize caching
        let cache_config = CacheConfig::default();
        let cache = Arc::new(MultiLevelCache::new(cache_config).await?);

        // Initialize metrics
        let metrics_config = regulateai_metrics::config::MetricsConfig::default();
        let metrics = Arc::new(MetricsRegistry::new(metrics_config).await?);

        Ok(Self {
            aml_processor,
            waf,
            threat_detector,
            rate_limiter,
            cache,
            metrics,
        })
    }

    /// Enhanced AML check with full security, caching, and metrics integration
    pub async fn enhanced_aml_check(
        &self,
        request: EnhancedAmlCheckRequest,
        security_request: SecurityRequest,
    ) -> Result<EnhancedAmlCheckResponse, Box<dyn std::error::Error>> {
        let start_time = std::time::Instant::now();
        let check_id = Uuid::new_v4();

        // 1. SECURITY VALIDATION
        // WAF protection
        let waf_response = self.waf.process_request(&security_request).await?;
        match waf_response {
            SecurityResponse::Blocked { reason, rule_id } => {
                // Record security block in metrics
                self.metrics.business().record_aml_check(
                    &request.customer_id.to_string(),
                    "BLOCKED_BY_WAF",
                    start_time.elapsed().as_millis() as f64,
                ).await?;

                return Err(format!("Request blocked by WAF: {} (Rule: {})", reason, rule_id).into());
            }
            SecurityResponse::Allowed => {}
        }

        // Rate limiting check
        let rate_allowed = self.rate_limiter.check_rate_limit(
            &security_request.client_ip,
            "aml_check"
        ).await?;

        if !rate_allowed {
            return Err("Rate limit exceeded".into());
        }

        // Threat detection
        let threat_score = self.threat_detector.analyze_request(&security_request).await?;
        if threat_score > 0.8 {
            return Err("High threat score detected".into());
        }

        // 2. CACHE CHECK
        let cache_key = format!("aml:{}:{}:{}", 
            request.customer_id, 
            request.amount, 
            blake3::hash(request.counterparty.as_bytes()).to_hex()
        );

        let mut cached = false;
        if let Some(cached_result) = self.cache.get::<EnhancedAmlCheckResponse>(&cache_key).await? {
            // Update cache hit metrics
            self.metrics.business().record_aml_check(
                &request.customer_id.to_string(),
                "CACHE_HIT",
                start_time.elapsed().as_millis() as f64,
            ).await?;

            return Ok(cached_result);
        }

        // 3. AML PROCESSING
        let aml_result = self.aml_processor.process_aml_check(&request).await?;

        // 4. METRICS RECORDING
        // Record business metrics
        self.metrics.business().record_aml_check(
            &request.customer_id.to_string(),
            &aml_result.compliance_status,
            start_time.elapsed().as_millis() as f64,
        ).await?;

        // Record compliance metrics
        self.metrics.compliance().record_compliance_check(
            "AML",
            &aml_result.compliance_status,
            aml_result.risk_score,
        ).await?;

        // Record risk metrics
        self.metrics.risk().record_risk_assessment(
            "CUSTOMER",
            &request.customer_id.to_string(),
            aml_result.risk_score,
            &aml_result.risk_level,
        ).await?;

        // 5. PREPARE RESPONSE
        let response = EnhancedAmlCheckResponse {
            check_id,
            customer_id: request.customer_id,
            risk_score: aml_result.risk_score,
            risk_level: aml_result.risk_level,
            compliance_status: aml_result.compliance_status,
            recommendations: aml_result.recommendations,
            processing_time_ms: start_time.elapsed().as_millis() as u64,
            cached,
            security_validated: true,
            threat_score,
        };

        // 6. CACHE RESULT
        let cache_ttl = if response.risk_level == "LOW" {
            Duration::hours(24) // Cache low-risk results longer
        } else if response.risk_level == "MEDIUM" {
            Duration::hours(6)
        } else {
            Duration::hours(1) // Cache high-risk results for shorter time
        };

        self.cache.set(&cache_key, &response, cache_ttl).await?;

        Ok(response)
    }

    /// Enhanced middleware for AML service endpoints
    pub async fn security_middleware(
        State(service): State<Arc<EnhancedAmlService>>,
        request: Request,
        next: Next,
    ) -> Result<Response, StatusCode> {
        let start_time = std::time::Instant::now();
        
        // Extract security information from request
        let security_request = SecurityRequest {
            method: request.method().to_string(),
            path: request.uri().path().to_string(),
            headers: request.headers().iter()
                .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
                .collect(),
            body: None, // Would extract body if needed
            client_ip: "127.0.0.1".parse().unwrap(), // Would extract real IP
            user_agent: request.headers()
                .get("user-agent")
                .and_then(|v| v.to_str().ok())
                .map(|s| s.to_string()),
        };

        // Security validation
        match service.waf.process_request(&security_request).await {
            Ok(SecurityResponse::Blocked { reason, .. }) => {
                tracing::warn!("Request blocked by WAF: {}", reason);
                return Err(StatusCode::FORBIDDEN);
            }
            Ok(SecurityResponse::Allowed) => {}
            Err(e) => {
                tracing::error!("WAF processing error: {}", e);
                return Err(StatusCode::INTERNAL_SERVER_ERROR);
            }
        }

        // Rate limiting
        match service.rate_limiter.check_rate_limit(&security_request.client_ip, "aml_service").await {
            Ok(true) => {}
            Ok(false) => {
                tracing::warn!("Rate limit exceeded for IP: {}", security_request.client_ip);
                return Err(StatusCode::TOO_MANY_REQUESTS);
            }
            Err(e) => {
                tracing::error!("Rate limiting error: {}", e);
                return Err(StatusCode::INTERNAL_SERVER_ERROR);
            }
        }

        // Process request
        let response = next.run(request).await;

        // Record operational metrics
        let duration = start_time.elapsed();
        service.metrics.operational().record_http_request(
            &security_request.method,
            &security_request.path,
            response.status().as_u16(),
            duration.as_millis() as f64,
        ).await;

        Ok(response)
    }

    /// Health check endpoint with enhanced monitoring
    pub async fn health_check(&self) -> Result<Json<HealthCheckResponse>, StatusCode> {
        let mut health = HealthCheckResponse {
            status: "healthy".to_string(),
            timestamp: chrono::Utc::now(),
            components: std::collections::HashMap::new(),
            metrics_summary: None,
        };

        // Check cache health
        match self.cache.get_cache_info().await {
            Ok(cache_info) => {
                health.components.insert("cache".to_string(), ComponentHealth {
                    status: "healthy".to_string(),
                    details: serde_json::json!({
                        "total_entries": cache_info.total_entries,
                        "hit_ratio": cache_info.hit_ratio
                    }),
                });
            }
            Err(e) => {
                health.status = "degraded".to_string();
                health.components.insert("cache".to_string(), ComponentHealth {
                    status: "unhealthy".to_string(),
                    details: serde_json::json!({ "error": e.to_string() }),
                });
            }
        }

        // Get metrics summary
        match self.metrics.get_metrics_summary().await {
            Ok(summary) => {
                health.metrics_summary = Some(summary);
            }
            Err(e) => {
                tracing::warn!("Failed to get metrics summary: {}", e);
            }
        }

        Ok(Json(health))
    }
}

/// Health check response structure
#[derive(Debug, Serialize)]
pub struct HealthCheckResponse {
    pub status: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub components: std::collections::HashMap<String, ComponentHealth>,
    pub metrics_summary: Option<regulateai_metrics::MetricsSummary>,
}

/// Component health information
#[derive(Debug, Serialize)]
pub struct ComponentHealth {
    pub status: String,
    pub details: serde_json::Value,
}

/// Example usage and integration tests
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_enhanced_aml_integration() {
        // This test demonstrates the full integration
        let service = EnhancedAmlService::new().await.expect("Failed to create service");

        let request = EnhancedAmlCheckRequest {
            customer_id: Uuid::new_v4(),
            transaction_id: Some(Uuid::new_v4()),
            amount: 10000.0,
            currency: "USD".to_string(),
            counterparty: "Test Counterparty".to_string(),
            transaction_type: "WIRE_TRANSFER".to_string(),
            metadata: serde_json::json!({"source": "test"}),
        };

        let security_request = SecurityRequest {
            method: "POST".to_string(),
            path: "/api/v1/aml/check".to_string(),
            headers: std::collections::HashMap::new(),
            body: None,
            client_ip: "192.168.1.100".parse().unwrap(),
            user_agent: Some("TestAgent/1.0".to_string()),
        };

        let result = service.enhanced_aml_check(request, security_request).await;
        assert!(result.is_ok(), "Enhanced AML check should succeed");

        let response = result.unwrap();
        assert!(response.security_validated, "Security should be validated");
        assert!(response.processing_time_ms > 0, "Processing time should be recorded");
    }

    #[tokio::test]
    async fn test_cache_integration() {
        let service = EnhancedAmlService::new().await.expect("Failed to create service");

        // Test cache functionality
        let test_key = "test:cache:key";
        let test_value = "test_value";
        
        service.cache.set(test_key, &test_value, Duration::minutes(5)).await
            .expect("Cache set should succeed");

        let cached_value: Option<String> = service.cache.get(test_key).await
            .expect("Cache get should succeed");

        assert_eq!(cached_value, Some(test_value.to_string()));
    }

    #[tokio::test]
    async fn test_metrics_integration() {
        let service = EnhancedAmlService::new().await.expect("Failed to create service");

        // Test metrics recording
        service.metrics.business().record_aml_check(
            "test_customer",
            "COMPLIANT",
            150.0,
        ).await.expect("Metrics recording should succeed");

        let summary = service.metrics.get_metrics_summary().await
            .expect("Metrics summary should be available");

        assert!(!summary.business_kpis.is_empty(), "Business KPIs should be recorded");
    }
}
