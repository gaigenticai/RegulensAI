//! Service Routing Module
//! 
//! This module handles intelligent request routing to backend services based on
//! URL patterns, service health, and load balancing algorithms.

use std::collections::HashMap;
use std::sync::Arc;
use axum::{
    extract::Request,
    response::Response,
    http::{Method, Uri, HeaderMap, HeaderName, HeaderValue},
};
use hyper::body::Body;
use reqwest::Client;
use tokio::sync::RwLock;
use tracing::{info, error, warn, debug};
use uuid::Uuid;
use chrono::{DateTime, Utc};

use regulateai_config::APIGatewayConfig;
use regulateai_errors::RegulateAIError;
use crate::discovery::{ServiceDiscovery, ServiceInstance};
use crate::balancing::LoadBalancer;

/// Service router for handling request routing and proxying
pub struct ServiceRouter {
    /// Service discovery client
    service_discovery: Arc<ServiceDiscovery>,
    
    /// Load balancer for service instances
    load_balancer: Arc<LoadBalancer>,
    
    /// HTTP client for proxying requests
    http_client: Client,
    
    /// Routing rules configuration
    routing_rules: Arc<RwLock<HashMap<String, RoutingRule>>>,
    
    /// Gateway configuration
    config: APIGatewayConfig,
    
    /// Request statistics
    stats: Arc<RwLock<RoutingStats>>,
}

/// Routing rule for service mapping
#[derive(Debug, Clone)]
pub struct RoutingRule {
    /// Rule name
    pub name: String,
    
    /// URL path pattern to match
    pub path_pattern: String,
    
    /// Target service name
    pub target_service: String,
    
    /// Path rewrite rule (optional)
    pub path_rewrite: Option<String>,
    
    /// Required HTTP methods
    pub methods: Vec<Method>,
    
    /// Request timeout in milliseconds
    pub timeout_ms: u64,
    
    /// Retry configuration
    pub retry_config: RetryConfig,
    
    /// Circuit breaker configuration
    pub circuit_breaker_config: CircuitBreakerConfig,
}

/// Retry configuration for failed requests
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Maximum retry attempts
    pub max_attempts: u32,
    
    /// Initial delay between retries in milliseconds
    pub initial_delay_ms: u64,
    
    /// Maximum delay between retries in milliseconds
    pub max_delay_ms: u64,
    
    /// Backoff multiplier
    pub backoff_multiplier: f64,
    
    /// HTTP status codes that trigger retries
    pub retry_status_codes: Vec<u16>,
}

/// Circuit breaker configuration
#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    /// Failure threshold to open circuit
    pub failure_threshold: u32,
    
    /// Success threshold to close circuit
    pub success_threshold: u32,
    
    /// Timeout in milliseconds before trying to close circuit
    pub timeout_ms: u64,
}

/// Routing statistics
#[derive(Debug, Default)]
pub struct RoutingStats {
    /// Total requests routed
    pub total_requests: u64,
    
    /// Successful requests
    pub successful_requests: u64,
    
    /// Failed requests
    pub failed_requests: u64,
    
    /// Average response time in milliseconds
    pub avg_response_time_ms: f64,
    
    /// Requests by service
    pub requests_by_service: HashMap<String, u64>,
    
    /// Last updated timestamp
    pub last_updated: DateTime<Utc>,
}

impl ServiceRouter {
    /// Create a new service router
    pub async fn new(
        service_discovery: Arc<ServiceDiscovery>,
        config: APIGatewayConfig,
    ) -> Result<Self, RegulateAIError> {
        info!("Initializing service router");
        
        let load_balancer = Arc::new(LoadBalancer::new(config.load_balancer.clone()));
        let http_client = Client::builder()
            .timeout(std::time::Duration::from_millis(config.default_timeout_ms))
            .build()
            .map_err(|e| RegulateAIError::ConfigurationError(format!("HTTP client error: {}", e)))?;
        
        let routing_rules = Arc::new(RwLock::new(HashMap::new()));
        let stats = Arc::new(RwLock::new(RoutingStats::default()));
        
        let router = Self {
            service_discovery,
            load_balancer,
            http_client,
            routing_rules,
            config,
            stats,
        };
        
        // Initialize default routing rules
        router.initialize_default_rules().await?;
        
        Ok(router)
    }
    
    /// Route an incoming request to the appropriate backend service
    pub async fn route_request(&self, request: Request) -> Result<Response, RegulateAIError> {
        let start_time = std::time::Instant::now();
        let request_id = Uuid::new_v4();
        
        debug!("Routing request {} to path: {}", request_id, request.uri().path());
        
        // Find matching routing rule
        let routing_rule = self.find_routing_rule(request.uri(), request.method()).await?;
        
        // Get healthy service instance
        let service_instance = self.select_service_instance(&routing_rule.target_service).await?;
        
        // Transform request for backend service
        let backend_request = self.transform_request(request, &routing_rule, &service_instance).await?;
        
        // Execute request with retries
        let response = self.execute_with_retries(backend_request, &routing_rule).await?;
        
        // Update statistics
        let response_time = start_time.elapsed().as_millis() as f64;
        self.update_stats(&routing_rule.target_service, response_time, response.status().is_success()).await;
        
        debug!("Request {} completed in {:.2}ms", request_id, response_time);
        
        Ok(response)
    }
    
    /// Find the appropriate routing rule for a request
    async fn find_routing_rule(&self, uri: &Uri, method: &Method) -> Result<RoutingRule, RegulateAIError> {
        let routing_rules = self.routing_rules.read().await;
        let path = uri.path();
        
        // Check for exact matches first
        for rule in routing_rules.values() {
            if self.matches_pattern(&rule.path_pattern, path) && rule.methods.contains(method) {
                return Ok(rule.clone());
            }
        }
        
        // If no specific rule found, try to infer from path
        if let Some(service_name) = self.infer_service_from_path(path) {
            return Ok(self.create_default_rule(service_name, path.to_string()));
        }
        
        Err(RegulateAIError::NotFound(format!("No routing rule found for {} {}", method, path)))
    }
    
    /// Select a healthy service instance using load balancing
    async fn select_service_instance(&self, service_name: &str) -> Result<ServiceInstance, RegulateAIError> {
        let instances = self.service_discovery.get_service_instances(service_name).await?;
        
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable(
                format!("No healthy instances found for service: {}", service_name)
            ));
        }
        
        self.load_balancer.select_instance(&instances).await
    }
    
    /// Transform the incoming request for the backend service
    async fn transform_request(
        &self,
        mut request: Request,
        rule: &RoutingRule,
        instance: &ServiceInstance,
    ) -> Result<reqwest::Request, RegulateAIError> {
        let uri = request.uri();
        let method = request.method().clone();
        let headers = request.headers().clone();
        
        // Build target URL
        let target_path = if let Some(rewrite) = &rule.path_rewrite {
            rewrite.clone()
        } else {
            uri.path().to_string()
        };
        
        let target_url = format!("http://{}:{}{}", instance.host, instance.port, target_path);
        
        // Add query parameters if present
        let final_url = if let Some(query) = uri.query() {
            format!("{}?{}", target_url, query)
        } else {
            target_url
        };
        
        // Build reqwest request
        let mut req_builder = self.http_client.request(method, &final_url);
        
        // Copy headers (excluding hop-by-hop headers)
        for (name, value) in headers.iter() {
            if !self.is_hop_by_hop_header(name) {
                req_builder = req_builder.header(name, value);
            }
        }
        
        // Add gateway headers
        req_builder = req_builder
            .header("X-Forwarded-For", "gateway")
            .header("X-Request-ID", Uuid::new_v4().to_string())
            .header("X-Gateway-Version", env!("CARGO_PKG_VERSION"));
        
        // Add body if present
        let body = axum::body::to_bytes(request.into_body(), usize::MAX).await
            .map_err(|e| RegulateAIError::BadRequest(format!("Body read error: {}", e)))?;
        
        if !body.is_empty() {
            req_builder = req_builder.body(body);
        }
        
        req_builder.build()
            .map_err(|e| RegulateAIError::BadRequest(format!("Request build error: {}", e)))
    }
    
    /// Execute request with retry logic
    async fn execute_with_retries(
        &self,
        request: reqwest::Request,
        rule: &RoutingRule,
    ) -> Result<Response, RegulateAIError> {
        let mut attempts = 0;
        let mut delay = rule.retry_config.initial_delay_ms;
        
        loop {
            attempts += 1;
            
            // Clone request for retry attempts
            let req = request.try_clone()
                .ok_or_else(|| RegulateAIError::InternalError("Cannot clone request for retry".to_string()))?;
            
            match self.http_client.execute(req).await {
                Ok(response) => {
                    let status = response.status();
                    
                    // Check if we should retry based on status code
                    if attempts < rule.retry_config.max_attempts && 
                       rule.retry_config.retry_status_codes.contains(&status.as_u16()) {
                        warn!("Request failed with status {}, retrying attempt {}/{}", 
                              status, attempts, rule.retry_config.max_attempts);
                        
                        tokio::time::sleep(std::time::Duration::from_millis(delay)).await;
                        delay = (delay as f64 * rule.retry_config.backoff_multiplier) as u64;
                        delay = delay.min(rule.retry_config.max_delay_ms);
                        continue;
                    }
                    
                    // Convert reqwest::Response to axum::Response
                    return self.convert_response(response).await;
                }
                Err(e) => {
                    if attempts >= rule.retry_config.max_attempts {
                        return Err(RegulateAIError::ServiceUnavailable(
                            format!("Request failed after {} attempts: {}", attempts, e)
                        ));
                    }
                    
                    warn!("Request failed: {}, retrying attempt {}/{}", e, attempts, rule.retry_config.max_attempts);
                    tokio::time::sleep(std::time::Duration::from_millis(delay)).await;
                    delay = (delay as f64 * rule.retry_config.backoff_multiplier) as u64;
                    delay = delay.min(rule.retry_config.max_delay_ms);
                }
            }
        }
    }
    
    /// Convert reqwest::Response to axum::Response
    async fn convert_response(&self, response: reqwest::Response) -> Result<Response, RegulateAIError> {
        let status = response.status();
        let headers = response.headers().clone();
        let body = response.bytes().await
            .map_err(|e| RegulateAIError::InternalError(format!("Response body error: {}", e)))?;
        
        let mut builder = Response::builder().status(status);
        
        // Copy response headers (excluding hop-by-hop headers)
        for (name, value) in headers.iter() {
            if !self.is_hop_by_hop_header(name) {
                builder = builder.header(name, value);
            }
        }
        
        builder.body(Body::from(body))
            .map_err(|e| RegulateAIError::InternalError(format!("Response build error: {}", e)))
    }
    
    /// Initialize default routing rules for known services
    async fn initialize_default_rules(&self) -> Result<(), RegulateAIError> {
        let mut rules = self.routing_rules.write().await;
        
        // AML Service routes
        rules.insert("aml".to_string(), RoutingRule {
            name: "AML Service".to_string(),
            path_pattern: "/api/v1/aml/*".to_string(),
            target_service: "aml-service".to_string(),
            path_rewrite: None,
            methods: vec![Method::GET, Method::POST, Method::PUT, Method::DELETE],
            timeout_ms: 30000,
            retry_config: RetryConfig::default(),
            circuit_breaker_config: CircuitBreakerConfig::default(),
        });
        
        // Compliance Service routes
        rules.insert("compliance".to_string(), RoutingRule {
            name: "Compliance Service".to_string(),
            path_pattern: "/api/v1/compliance/*".to_string(),
            target_service: "compliance-service".to_string(),
            path_rewrite: None,
            methods: vec![Method::GET, Method::POST, Method::PUT, Method::DELETE],
            timeout_ms: 30000,
            retry_config: RetryConfig::default(),
            circuit_breaker_config: CircuitBreakerConfig::default(),
        });
        
        // Risk Management Service routes
        rules.insert("risk".to_string(), RoutingRule {
            name: "Risk Management Service".to_string(),
            path_pattern: "/api/v1/risk/*".to_string(),
            target_service: "risk-management-service".to_string(),
            path_rewrite: None,
            methods: vec![Method::GET, Method::POST, Method::PUT, Method::DELETE],
            timeout_ms: 30000,
            retry_config: RetryConfig::default(),
            circuit_breaker_config: CircuitBreakerConfig::default(),
        });
        
        // Add more service routes...
        
        info!("Initialized {} default routing rules", rules.len());
        Ok(())
    }
    
    // Helper methods
    fn matches_pattern(&self, pattern: &str, path: &str) -> bool {
        if pattern.ends_with("/*") {
            let prefix = &pattern[..pattern.len() - 2];
            path.starts_with(prefix)
        } else {
            pattern == path
        }
    }
    
    fn infer_service_from_path(&self, path: &str) -> Option<String> {
        if path.starts_with("/api/v1/") {
            let parts: Vec<&str> = path.split('/').collect();
            if parts.len() >= 4 {
                return Some(format!("{}-service", parts[3]));
            }
        }
        None
    }
    
    fn create_default_rule(&self, service_name: String, path: String) -> RoutingRule {
        RoutingRule {
            name: format!("Default rule for {}", service_name),
            path_pattern: path,
            target_service: service_name,
            path_rewrite: None,
            methods: vec![Method::GET, Method::POST, Method::PUT, Method::DELETE],
            timeout_ms: self.config.default_timeout_ms,
            retry_config: RetryConfig::default(),
            circuit_breaker_config: CircuitBreakerConfig::default(),
        }
    }
    
    fn is_hop_by_hop_header(&self, name: &HeaderName) -> bool {
        matches!(name.as_str().to_lowercase().as_str(),
            "connection" | "keep-alive" | "proxy-authenticate" | 
            "proxy-authorization" | "te" | "trailers" | "transfer-encoding" | "upgrade"
        )
    }
    
    async fn update_stats(&self, service_name: &str, response_time: f64, success: bool) {
        let mut stats = self.stats.write().await;
        stats.total_requests += 1;
        
        if success {
            stats.successful_requests += 1;
        } else {
            stats.failed_requests += 1;
        }
        
        // Update average response time
        stats.avg_response_time_ms = (stats.avg_response_time_ms * (stats.total_requests - 1) as f64 + response_time) / stats.total_requests as f64;
        
        // Update service-specific stats
        *stats.requests_by_service.entry(service_name.to_string()).or_insert(0) += 1;
        
        stats.last_updated = Utc::now();
    }
    
    /// Get routing statistics
    pub async fn get_stats(&self) -> RoutingStats {
        self.stats.read().await.clone()
    }
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay_ms: 1000,
            max_delay_ms: 10000,
            backoff_multiplier: 2.0,
            retry_status_codes: vec![502, 503, 504],
        }
    }
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            success_threshold: 3,
            timeout_ms: 60000,
        }
    }
}

impl Clone for RoutingStats {
    fn clone(&self) -> Self {
        Self {
            total_requests: self.total_requests,
            successful_requests: self.successful_requests,
            failed_requests: self.failed_requests,
            avg_response_time_ms: self.avg_response_time_ms,
            requests_by_service: self.requests_by_service.clone(),
            last_updated: self.last_updated,
        }
    }
}
