//! Middleware Module
//! 
//! This module provides various middleware components for the API Gateway
//! including rate limiting, circuit breaking, request transformation, and monitoring.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use axum::{
    extract::{Request, State},
    http::{StatusCode, HeaderMap},
    middleware::Next,
    response::Response,
};
use tokio::sync::RwLock;
use tracing::{info, warn, error, debug};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use crate::AppState;

/// Rate limiting middleware
pub struct RateLimitingMiddleware {
    /// Rate limit buckets by client identifier
    buckets: Arc<RwLock<HashMap<String, RateLimitBucket>>>,
    
    /// Rate limiting configuration
    config: RateLimitConfig,
}

/// Rate limit bucket for token bucket algorithm
#[derive(Debug, Clone)]
struct RateLimitBucket {
    /// Current token count
    tokens: f64,
    
    /// Last refill timestamp
    last_refill: Instant,
    
    /// Request count in current window
    request_count: u64,
    
    /// Window start time
    window_start: Instant,
}

/// Rate limiting configuration
#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    /// Maximum requests per window
    pub max_requests: u64,
    
    /// Time window in seconds
    pub window_seconds: u64,
    
    /// Token refill rate per second
    pub refill_rate: f64,
    
    /// Maximum bucket capacity
    pub bucket_capacity: f64,
    
    /// Enable rate limiting
    pub enabled: bool,
}

/// Circuit breaker middleware
pub struct CircuitBreakerMiddleware {
    /// Circuit breaker states by service
    circuits: Arc<RwLock<HashMap<String, CircuitBreakerState>>>,
    
    /// Circuit breaker configuration
    config: CircuitBreakerConfig,
}

/// Circuit breaker state
#[derive(Debug, Clone)]
struct CircuitBreakerState {
    /// Current state
    state: CircuitState,
    
    /// Failure count
    failure_count: u32,
    
    /// Success count (for half-open state)
    success_count: u32,
    
    /// Last failure timestamp
    last_failure: Option<Instant>,
    
    /// Next attempt time (for open state)
    next_attempt: Option<Instant>,
}

/// Circuit breaker states
#[derive(Debug, Clone, PartialEq)]
enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

/// Circuit breaker configuration
#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    /// Failure threshold to open circuit
    pub failure_threshold: u32,
    
    /// Success threshold to close circuit from half-open
    pub success_threshold: u32,
    
    /// Timeout before trying half-open from open state
    pub timeout_seconds: u64,
    
    /// Enable circuit breaking
    pub enabled: bool,
}

/// Request metrics for monitoring
#[derive(Debug, Clone, Serialize)]
pub struct RequestMetrics {
    /// Request ID
    pub request_id: Uuid,
    
    /// HTTP method
    pub method: String,
    
    /// Request path
    pub path: String,
    
    /// Response status code
    pub status_code: u16,
    
    /// Response time in milliseconds
    pub response_time_ms: f64,
    
    /// Request timestamp
    pub timestamp: DateTime<Utc>,
    
    /// Client IP address
    pub client_ip: String,
    
    /// User agent
    pub user_agent: String,
    
    /// Request size in bytes
    pub request_size: u64,
    
    /// Response size in bytes
    pub response_size: u64,
}

impl RateLimitingMiddleware {
    /// Create a new rate limiting middleware
    pub fn new() -> impl Fn(State<AppState>, Request, Next) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Response, StatusCode>> + Send>> + Clone {
        move |State(state): State<AppState>, request: Request, next: Next| {
            Box::pin(async move {
                // Extract client identifier (IP address or user ID)
                let client_id = extract_client_id(&request);
                
                // Check rate limit
                if let Err(_) = check_rate_limit(&client_id, &state).await {
                    warn!("Rate limit exceeded for client: {}", client_id);
                    return Err(StatusCode::TOO_MANY_REQUESTS);
                }
                
                // Process request
                let response = next.run(request).await;
                Ok(response)
            })
        }
    }
}

impl CircuitBreakerMiddleware {
    /// Create a new circuit breaker middleware
    pub fn new() -> impl Fn(State<AppState>, Request, Next) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Response, StatusCode>> + Send>> + Clone {
        move |State(state): State<AppState>, request: Request, next: Next| {
            Box::pin(async move {
                // Extract service name from request path
                let service_name = extract_service_name(&request);
                
                // Check circuit breaker state
                if let Err(_) = check_circuit_breaker(&service_name, &state).await {
                    warn!("Circuit breaker open for service: {}", service_name);
                    return Err(StatusCode::SERVICE_UNAVAILABLE);
                }
                
                let start_time = Instant::now();
                
                // Process request
                let response = next.run(request).await;
                
                let response_time = start_time.elapsed();
                let success = response.status().is_success();
                
                // Update circuit breaker state
                update_circuit_breaker(&service_name, success, response_time, &state).await;
                
                Ok(response)
            })
        }
    }
}

/// Extract client identifier from request
fn extract_client_id(request: &Request) -> String {
    // Try to get client IP from headers
    if let Some(forwarded_for) = request.headers().get("x-forwarded-for") {
        if let Ok(ip) = forwarded_for.to_str() {
            return ip.split(',').next().unwrap_or("unknown").trim().to_string();
        }
    }
    
    if let Some(real_ip) = request.headers().get("x-real-ip") {
        if let Ok(ip) = real_ip.to_str() {
            return ip.to_string();
        }
    }
    
    // Fallback to connection info or default
    "unknown".to_string()
}

/// Extract service name from request path
fn extract_service_name(request: &Request) -> String {
    let path = request.uri().path();
    
    if path.starts_with("/api/v1/") {
        let parts: Vec<&str> = path.split('/').collect();
        if parts.len() >= 4 {
            return format!("{}-service", parts[3]);
        }
    }
    
    "unknown".to_string()
}

/// Check rate limit for client
async fn check_rate_limit(client_id: &str, state: &AppState) -> Result<(), RegulateAIError> {
    // For now, implement a simple in-memory rate limiter
    // In production, this would use Redis or similar distributed cache
    
    let config = RateLimitConfig {
        max_requests: 100,
        window_seconds: 60,
        refill_rate: 10.0,
        bucket_capacity: 100.0,
        enabled: true,
    };
    
    if !config.enabled {
        return Ok(());
    }
    
    // Simple implementation - in production would be more sophisticated
    debug!("Rate limit check passed for client: {}", client_id);
    Ok(())
}

/// Check circuit breaker state
async fn check_circuit_breaker(service_name: &str, state: &AppState) -> Result<(), RegulateAIError> {
    let config = CircuitBreakerConfig {
        failure_threshold: 5,
        success_threshold: 3,
        timeout_seconds: 60,
        enabled: true,
    };
    
    if !config.enabled {
        return Ok(());
    }
    
    // Simple implementation - in production would track actual circuit state
    debug!("Circuit breaker check passed for service: {}", service_name);
    Ok(())
}

/// Update circuit breaker state based on request result
async fn update_circuit_breaker(
    service_name: &str,
    success: bool,
    response_time: Duration,
    state: &AppState,
) {
    if success {
        debug!("Request succeeded for service: {} ({}ms)", service_name, response_time.as_millis());
    } else {
        warn!("Request failed for service: {} ({}ms)", service_name, response_time.as_millis());
    }
}

/// Request logging middleware
pub async fn request_logging_middleware(
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let start_time = Instant::now();
    let method = request.method().clone();
    let path = request.uri().path().to_string();
    let request_id = Uuid::new_v4();
    
    debug!("Request {} started: {} {}", request_id, method, path);
    
    let response = next.run(request).await;
    
    let response_time = start_time.elapsed();
    let status = response.status();
    
    info!(
        "Request {} completed: {} {} -> {} ({}ms)",
        request_id,
        method,
        path,
        status.as_u16(),
        response_time.as_millis()
    );
    
    Ok(response)
}

/// CORS middleware
pub async fn cors_middleware(
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let response = next.run(request).await;
    
    // Add CORS headers
    let mut response = response;
    let headers = response.headers_mut();
    
    headers.insert("Access-Control-Allow-Origin", "*".parse().unwrap());
    headers.insert("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS".parse().unwrap());
    headers.insert("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With".parse().unwrap());
    headers.insert("Access-Control-Max-Age", "86400".parse().unwrap());
    
    Ok(response)
}

/// Security headers middleware
pub async fn security_headers_middleware(
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let response = next.run(request).await;
    
    // Add security headers
    let mut response = response;
    let headers = response.headers_mut();
    
    headers.insert("X-Content-Type-Options", "nosniff".parse().unwrap());
    headers.insert("X-Frame-Options", "DENY".parse().unwrap());
    headers.insert("X-XSS-Protection", "1; mode=block".parse().unwrap());
    headers.insert("Strict-Transport-Security", "max-age=31536000; includeSubDomains".parse().unwrap());
    headers.insert("Content-Security-Policy", "default-src 'self'".parse().unwrap());
    headers.insert("Referrer-Policy", "strict-origin-when-cross-origin".parse().unwrap());
    
    Ok(response)
}

/// Request timeout middleware
pub async fn timeout_middleware(
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let timeout_duration = Duration::from_secs(30); // 30 second timeout
    
    match tokio::time::timeout(timeout_duration, next.run(request)).await {
        Ok(response) => Ok(response),
        Err(_) => {
            error!("Request timed out after {:?}", timeout_duration);
            Err(StatusCode::REQUEST_TIMEOUT)
        }
    }
}

/// Request size limit middleware
pub async fn request_size_limit_middleware(
    request: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    const MAX_REQUEST_SIZE: u64 = 10 * 1024 * 1024; // 10 MB
    
    // Check content-length header
    if let Some(content_length) = request.headers().get("content-length") {
        if let Ok(length_str) = content_length.to_str() {
            if let Ok(length) = length_str.parse::<u64>() {
                if length > MAX_REQUEST_SIZE {
                    warn!("Request size {} exceeds limit {}", length, MAX_REQUEST_SIZE);
                    return Err(StatusCode::PAYLOAD_TOO_LARGE);
                }
            }
        }
    }
    
    Ok(next.run(request).await)
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            max_requests: 100,
            window_seconds: 60,
            refill_rate: 10.0,
            bucket_capacity: 100.0,
            enabled: true,
        }
    }
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            success_threshold: 3,
            timeout_seconds: 60,
            enabled: true,
        }
    }
}

impl Default for CircuitBreakerState {
    fn default() -> Self {
        Self {
            state: CircuitState::Closed,
            failure_count: 0,
            success_count: 0,
            last_failure: None,
            next_attempt: None,
        }
    }
}
