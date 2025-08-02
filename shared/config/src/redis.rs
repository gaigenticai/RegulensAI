//! Redis configuration management

use serde::{Deserialize, Serialize};
use std::time::Duration;
use validator::Validate;

/// Redis configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RedisConfig {
    /// Redis connection URL
    #[validate(length(min = 1))]
    pub url: String,
    
    /// Maximum number of connections in the pool
    #[validate(range(min = 1, max = 100))]
    pub max_connections: u32,
    
    /// Minimum number of connections in the pool
    #[validate(range(min = 1, max = 50))]
    pub min_connections: u32,
    
    /// Connection timeout in seconds
    #[validate(range(min = 1, max = 60))]
    pub connection_timeout: u64,
    
    /// Response timeout in seconds
    #[validate(range(min = 1, max = 60))]
    pub response_timeout: u64,
    
    /// Connection retry attempts
    #[validate(range(min = 0, max = 10))]
    pub retry_attempts: u32,
    
    /// Retry delay in milliseconds
    #[validate(range(min = 100, max = 10000))]
    pub retry_delay: u64,
    
    /// Enable cluster mode
    pub cluster_mode: bool,
    
    /// Cluster nodes (only used if cluster_mode is true)
    pub cluster_nodes: Vec<String>,
    
    /// Default TTL for cached items in seconds
    #[validate(range(min = 1))]
    pub default_ttl: u64,
    
    /// Key prefix for this application
    pub key_prefix: Option<String>,
    
    /// Enable Redis AUTH
    pub auth_enabled: bool,
    
    /// Redis password (if auth is enabled)
    pub password: Option<String>,
    
    /// Redis username (for Redis 6+ ACL)
    pub username: Option<String>,
    
    /// Database number (0-15)
    #[validate(range(min = 0, max = 15))]
    pub database: u8,
    
    /// Enable TLS
    pub tls_enabled: bool,
    
    /// TLS certificate verification
    pub tls_verify_cert: bool,
}

impl RedisConfig {
    /// Get connection timeout as Duration
    pub fn connection_timeout_duration(&self) -> Duration {
        Duration::from_secs(self.connection_timeout)
    }

    /// Get response timeout as Duration
    pub fn response_timeout_duration(&self) -> Duration {
        Duration::from_secs(self.response_timeout)
    }

    /// Get retry delay as Duration
    pub fn retry_delay_duration(&self) -> Duration {
        Duration::from_millis(self.retry_delay)
    }

    /// Get default TTL as Duration
    pub fn default_ttl_duration(&self) -> Duration {
        Duration::from_secs(self.default_ttl)
    }

    /// Build a prefixed key
    pub fn build_key(&self, key: &str) -> String {
        if let Some(prefix) = &self.key_prefix {
            format!("{}:{}", prefix, key)
        } else {
            key.to_string()
        }
    }

    /// Get Redis connection URL with masked password for logging
    pub fn masked_url(&self) -> String {
        if self.password.is_some() {
            self.url.replace(&format!(":{}", self.password.as_ref().unwrap()), ":***")
        } else {
            self.url.clone()
        }
    }

    /// Validate Redis configuration
    pub fn validate_config(&self) -> Result<(), String> {
        // Validate URL format
        if !self.url.starts_with("redis://") && !self.url.starts_with("rediss://") {
            return Err("Redis URL must start with redis:// or rediss://".to_string());
        }

        // Validate connection pool settings
        if self.min_connections > self.max_connections {
            return Err("min_connections cannot be greater than max_connections".to_string());
        }

        // Validate cluster configuration
        if self.cluster_mode && self.cluster_nodes.is_empty() {
            return Err("cluster_nodes must be specified when cluster_mode is enabled".to_string());
        }

        // Validate auth configuration
        if self.auth_enabled && self.password.is_none() {
            return Err("password must be specified when auth_enabled is true".to_string());
        }

        Ok(())
    }

    /// Check if running in cluster mode
    pub fn is_cluster_mode(&self) -> bool {
        self.cluster_mode
    }

    /// Get cluster nodes
    pub fn get_cluster_nodes(&self) -> &[String] {
        &self.cluster_nodes
    }
}

impl Default for RedisConfig {
    fn default() -> Self {
        Self {
            url: "redis://localhost:6379".to_string(),
            max_connections: 10,
            min_connections: 2,
            connection_timeout: 5,
            response_timeout: 5,
            retry_attempts: 3,
            retry_delay: 1000,
            cluster_mode: false,
            cluster_nodes: Vec::new(),
            default_ttl: 3600, // 1 hour
            key_prefix: Some("regulateai".to_string()),
            auth_enabled: false,
            password: None,
            username: None,
            database: 0,
            tls_enabled: false,
            tls_verify_cert: true,
        }
    }
}

/// Redis cache configuration for different cache types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    /// Session cache TTL in seconds
    pub session_ttl: u64,
    
    /// User profile cache TTL in seconds
    pub user_profile_ttl: u64,
    
    /// API rate limit cache TTL in seconds
    pub rate_limit_ttl: u64,
    
    /// Sanctions list cache TTL in seconds
    pub sanctions_list_ttl: u64,
    
    /// Risk score cache TTL in seconds
    pub risk_score_ttl: u64,
    
    /// Fraud model cache TTL in seconds
    pub fraud_model_ttl: u64,
    
    /// Enable cache compression
    pub enable_compression: bool,
    
    /// Cache key expiration strategy
    pub expiration_strategy: CacheExpirationStrategy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CacheExpirationStrategy {
    /// Expire keys at exact TTL
    Exact,
    /// Add random jitter to prevent thundering herd
    Jitter,
    /// Sliding window expiration
    Sliding,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            session_ttl: 86400,        // 24 hours
            user_profile_ttl: 3600,    // 1 hour
            rate_limit_ttl: 3600,      // 1 hour
            sanctions_list_ttl: 3600,  // 1 hour
            risk_score_ttl: 1800,      // 30 minutes
            fraud_model_ttl: 86400,    // 24 hours
            enable_compression: true,
            expiration_strategy: CacheExpirationStrategy::Jitter,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_redis_config() {
        let config = RedisConfig::default();
        assert_eq!(config.url, "redis://localhost:6379");
        assert_eq!(config.max_connections, 10);
        assert_eq!(config.min_connections, 2);
        assert!(!config.cluster_mode);
        assert!(!config.auth_enabled);
    }

    #[test]
    fn test_build_key() {
        let config = RedisConfig::default();
        assert_eq!(config.build_key("test"), "regulateai:test");

        let mut config_no_prefix = config.clone();
        config_no_prefix.key_prefix = None;
        assert_eq!(config_no_prefix.build_key("test"), "test");
    }

    #[test]
    fn test_masked_url() {
        let mut config = RedisConfig::default();
        config.url = "redis://:password123@localhost:6379".to_string();
        config.password = Some("password123".to_string());
        
        let masked = config.masked_url();
        assert!(masked.contains("***"));
        assert!(!masked.contains("password123"));
    }

    #[test]
    fn test_validate_config() {
        let mut config = RedisConfig::default();
        assert!(config.validate_config().is_ok());

        // Test invalid URL
        config.url = "invalid-url".to_string();
        assert!(config.validate_config().is_err());

        // Reset and test invalid connection pool
        config = RedisConfig::default();
        config.min_connections = 20;
        config.max_connections = 10;
        assert!(config.validate_config().is_err());

        // Reset and test cluster mode without nodes
        config = RedisConfig::default();
        config.cluster_mode = true;
        assert!(config.validate_config().is_err());

        // Reset and test auth without password
        config = RedisConfig::default();
        config.auth_enabled = true;
        assert!(config.validate_config().is_err());
    }

    #[test]
    fn test_duration_conversions() {
        let config = RedisConfig::default();
        
        assert_eq!(config.connection_timeout_duration(), Duration::from_secs(5));
        assert_eq!(config.response_timeout_duration(), Duration::from_secs(5));
        assert_eq!(config.retry_delay_duration(), Duration::from_millis(1000));
        assert_eq!(config.default_ttl_duration(), Duration::from_secs(3600));
    }

    #[test]
    fn test_cache_config_default() {
        let config = CacheConfig::default();
        assert_eq!(config.session_ttl, 86400);
        assert_eq!(config.user_profile_ttl, 3600);
        assert!(config.enable_compression);
        assert!(matches!(config.expiration_strategy, CacheExpirationStrategy::Jitter));
    }
}
