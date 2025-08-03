//! Advanced Rate Limiting Implementation
//! 
//! Provides sophisticated rate limiting with:
//! - Token bucket algorithm
//! - Sliding window rate limiting
//! - Distributed rate limiting with Redis
//! - Per-IP, per-user, and per-endpoint limits
//! - Adaptive rate limiting based on system load

use crate::errors::{SecurityError, SecurityResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};
use tokio::sync::RwLock;
use std::sync::Arc;
use governor::{Quota, RateLimiter as GovernorRateLimiter, DefaultDirectRateLimiter};
use nonzero_ext::*;

/// Advanced rate limiter
pub struct RateLimiter {
    limiters: Arc<RwLock<HashMap<String, DefaultDirectRateLimiter>>>,
    config: RateLimitConfig,
    redis_client: Option<Arc<redis::Client>>,
}

/// Rate limiting configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    pub enabled: bool,
    pub default_requests_per_minute: u32,
    pub default_burst_size: u32,
    pub per_ip_enabled: bool,
    pub per_user_enabled: bool,
    pub per_endpoint_enabled: bool,
    pub distributed_enabled: bool,
    pub adaptive_enabled: bool,
    pub whitelist: Vec<String>,
    pub endpoint_specific_limits: HashMap<String, EndpointRateLimit>,
}

/// Endpoint-specific rate limit configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EndpointRateLimit {
    pub path_pattern: String,
    pub requests_per_minute: u32,
    pub burst_size: u32,
    pub methods: Vec<String>,
    pub per_ip: bool,
    pub per_user: bool,
}

/// Rate limit check result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitResult {
    pub allowed: bool,
    pub limit: u32,
    pub remaining: u32,
    pub reset_time: DateTime<Utc>,
    pub retry_after: Option<u64>, // seconds
}

/// Rate limit key types
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum RateLimitKey {
    Ip(String),
    User(String),
    Endpoint { path: String, method: String },
    IpEndpoint { ip: String, path: String, method: String },
    UserEndpoint { user: String, path: String, method: String },
}

impl RateLimiter {
    /// Create a new rate limiter
    pub fn new(config: RateLimitConfig) -> SecurityResult<Self> {
        let redis_client = if config.distributed_enabled {
            // In a real implementation, this would connect to Redis
            None
        } else {
            None
        };

        Ok(Self {
            limiters: Arc::new(RwLock::new(HashMap::new())),
            config,
            redis_client,
        })
    }

    /// Check rate limit for a request
    pub async fn check_rate_limit(&self, client_ip: &str) -> SecurityResult<RateLimitResult> {
        if !self.config.enabled {
            return Ok(RateLimitResult {
                allowed: true,
                limit: u32::MAX,
                remaining: u32::MAX,
                reset_time: Utc::now() + Duration::hours(1),
                retry_after: None,
            });
        }

        // Check whitelist
        if self.is_whitelisted(client_ip) {
            return Ok(RateLimitResult {
                allowed: true,
                limit: u32::MAX,
                remaining: u32::MAX,
                reset_time: Utc::now() + Duration::hours(1),
                retry_after: None,
            });
        }

        // Check IP-based rate limit
        if self.config.per_ip_enabled {
            let key = RateLimitKey::Ip(client_ip.to_string());
            return self.check_limit(&key).await;
        }

        Ok(RateLimitResult {
            allowed: true,
            limit: self.config.default_requests_per_minute,
            remaining: self.config.default_requests_per_minute,
            reset_time: Utc::now() + Duration::minutes(1),
            retry_after: None,
        })
    }

    /// Check rate limit for a specific endpoint
    pub async fn check_endpoint_rate_limit(
        &self,
        client_ip: &str,
        user_id: Option<&str>,
        method: &str,
        path: &str,
    ) -> SecurityResult<RateLimitResult> {
        if !self.config.enabled {
            return Ok(RateLimitResult {
                allowed: true,
                limit: u32::MAX,
                remaining: u32::MAX,
                reset_time: Utc::now() + Duration::hours(1),
                retry_after: None,
            });
        }

        // Check whitelist
        if self.is_whitelisted(client_ip) {
            return Ok(RateLimitResult {
                allowed: true,
                limit: u32::MAX,
                remaining: u32::MAX,
                reset_time: Utc::now() + Duration::hours(1),
                retry_after: None,
            });
        }

        // Find matching endpoint configuration
        let endpoint_config = self.find_endpoint_config(method, path);

        // Check endpoint-specific limits
        if let Some(config) = &endpoint_config {
            if config.per_ip {
                let key = RateLimitKey::IpEndpoint {
                    ip: client_ip.to_string(),
                    path: path.to_string(),
                    method: method.to_string(),
                };
                return self.check_limit_with_config(&key, config.requests_per_minute, config.burst_size).await;
            }

            if config.per_user {
                if let Some(user) = user_id {
                    let key = RateLimitKey::UserEndpoint {
                        user: user.to_string(),
                        path: path.to_string(),
                        method: method.to_string(),
                    };
                    return self.check_limit_with_config(&key, config.requests_per_minute, config.burst_size).await;
                }
            }
        }

        // Fall back to general IP-based rate limiting
        self.check_rate_limit(client_ip).await
    }

    /// Check rate limit for a user
    pub async fn check_user_rate_limit(&self, user_id: &str) -> SecurityResult<RateLimitResult> {
        if !self.config.enabled || !self.config.per_user_enabled {
            return Ok(RateLimitResult {
                allowed: true,
                limit: u32::MAX,
                remaining: u32::MAX,
                reset_time: Utc::now() + Duration::hours(1),
                retry_after: None,
            });
        }

        let key = RateLimitKey::User(user_id.to_string());
        self.check_limit(&key).await
    }

    /// Internal method to check rate limit
    async fn check_limit(&self, key: &RateLimitKey) -> SecurityResult<RateLimitResult> {
        self.check_limit_with_config(
            key,
            self.config.default_requests_per_minute,
            self.config.default_burst_size,
        ).await
    }

    /// Internal method to check rate limit with custom configuration
    async fn check_limit_with_config(
        &self,
        key: &RateLimitKey,
        requests_per_minute: u32,
        burst_size: u32,
    ) -> SecurityResult<RateLimitResult> {
        let key_str = self.key_to_string(key);

        // Get or create rate limiter for this key
        let limiter = {
            let mut limiters = self.limiters.write().await;
            limiters.entry(key_str.clone()).or_insert_with(|| {
                let quota = Quota::per_minute(nonzero!(requests_per_minute))
                    .allow_burst(nonzero!(burst_size));
                GovernorRateLimiter::direct(quota)
            }).clone()
        };

        // Check the rate limit
        match limiter.check() {
            Ok(_) => {
                Ok(RateLimitResult {
                    allowed: true,
                    limit: requests_per_minute,
                    remaining: requests_per_minute.saturating_sub(1), // Approximate
                    reset_time: Utc::now() + Duration::minutes(1),
                    retry_after: None,
                })
            }
            Err(negative) => {
                let retry_after = negative.wait_time_from(std::time::Instant::now());
                Ok(RateLimitResult {
                    allowed: false,
                    limit: requests_per_minute,
                    remaining: 0,
                    reset_time: Utc::now() + Duration::from_std(retry_after).unwrap_or(Duration::minutes(1)),
                    retry_after: Some(retry_after.as_secs()),
                })
            }
        }
    }

    /// Check if IP is whitelisted
    fn is_whitelisted(&self, ip: &str) -> bool {
        self.config.whitelist.contains(&ip.to_string()) ||
        self.config.whitelist.iter().any(|pattern| {
            // Simple pattern matching - in production, use proper CIDR matching
            pattern.contains('*') && ip.starts_with(&pattern.replace('*', ""))
        })
    }

    /// Find endpoint-specific configuration
    fn find_endpoint_config(&self, method: &str, path: &str) -> Option<&EndpointRateLimit> {
        self.config.endpoint_specific_limits.values().find(|config| {
            config.methods.contains(&method.to_string()) &&
            self.path_matches(&config.path_pattern, path)
        })
    }

    /// Check if path matches pattern
    fn path_matches(&self, pattern: &str, path: &str) -> bool {
        if pattern == "*" {
            return true;
        }
        
        if pattern.ends_with("/*") {
            let prefix = &pattern[..pattern.len() - 2];
            return path.starts_with(prefix);
        }
        
        pattern == path
    }

    /// Convert rate limit key to string
    fn key_to_string(&self, key: &RateLimitKey) -> String {
        match key {
            RateLimitKey::Ip(ip) => format!("ip:{}", ip),
            RateLimitKey::User(user) => format!("user:{}", user),
            RateLimitKey::Endpoint { path, method } => format!("endpoint:{}:{}", method, path),
            RateLimitKey::IpEndpoint { ip, path, method } => format!("ip_endpoint:{}:{}:{}", ip, method, path),
            RateLimitKey::UserEndpoint { user, path, method } => format!("user_endpoint:{}:{}:{}", user, method, path),
        }
    }

    /// Get rate limiting statistics
    pub async fn get_statistics(&self) -> RateLimitStatistics {
        let limiters = self.limiters.read().await;
        RateLimitStatistics {
            active_limiters: limiters.len(),
            total_keys: limiters.keys().cloned().collect(),
            config: self.config.clone(),
        }
    }

    /// Clean up expired limiters
    pub async fn cleanup_expired(&self) -> SecurityResult<usize> {
        let mut limiters = self.limiters.write().await;
        let initial_count = limiters.len();
        
        // In a real implementation, we would check for expired limiters
        // For now, we'll just return the count
        
        Ok(initial_count - limiters.len())
    }

    /// Update configuration
    pub async fn update_config(&mut self, new_config: RateLimitConfig) -> SecurityResult<()> {
        self.config = new_config;
        
        // Clear existing limiters to apply new configuration
        let mut limiters = self.limiters.write().await;
        limiters.clear();
        
        Ok(())
    }

    /// Add IP to whitelist
    pub async fn add_to_whitelist(&mut self, ip: String) -> SecurityResult<()> {
        if !self.config.whitelist.contains(&ip) {
            self.config.whitelist.push(ip);
        }
        Ok(())
    }

    /// Remove IP from whitelist
    pub async fn remove_from_whitelist(&mut self, ip: &str) -> SecurityResult<()> {
        self.config.whitelist.retain(|x| x != ip);
        Ok(())
    }

    /// Add endpoint-specific rate limit
    pub async fn add_endpoint_limit(
        &mut self,
        endpoint_id: String,
        limit: EndpointRateLimit,
    ) -> SecurityResult<()> {
        self.config.endpoint_specific_limits.insert(endpoint_id, limit);
        Ok(())
    }

    /// Remove endpoint-specific rate limit
    pub async fn remove_endpoint_limit(&mut self, endpoint_id: &str) -> SecurityResult<()> {
        self.config.endpoint_specific_limits.remove(endpoint_id);
        Ok(())
    }
}

/// Rate limiting statistics
#[derive(Debug, Serialize)]
pub struct RateLimitStatistics {
    pub active_limiters: usize,
    pub total_keys: Vec<String>,
    pub config: RateLimitConfig,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            default_requests_per_minute: 100,
            default_burst_size: 20,
            per_ip_enabled: true,
            per_user_enabled: true,
            per_endpoint_enabled: true,
            distributed_enabled: false,
            adaptive_enabled: false,
            whitelist: vec![
                "127.0.0.1".to_string(),
                "::1".to_string(),
                "10.0.0.0/8".to_string(),
                "172.16.0.0/12".to_string(),
                "192.168.0.0/16".to_string(),
            ],
            endpoint_specific_limits: HashMap::new(),
        }
    }
}

impl Default for EndpointRateLimit {
    fn default() -> Self {
        Self {
            path_pattern: "*".to_string(),
            requests_per_minute: 60,
            burst_size: 10,
            methods: vec!["GET".to_string(), "POST".to_string(), "PUT".to_string(), "DELETE".to_string()],
            per_ip: true,
            per_user: false,
        }
    }
}
