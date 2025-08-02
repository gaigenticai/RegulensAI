//! Database configuration management

use serde::{Deserialize, Serialize};
use std::time::Duration;
use url::Url;
use validator::Validate;

/// Database configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct DatabaseConfig {
    /// Database connection URL
    #[validate(length(min = 1))]
    pub url: String,
    
    /// Maximum number of connections in the pool
    #[validate(range(min = 1, max = 1000))]
    pub max_connections: u32,
    
    /// Minimum number of connections in the pool
    #[validate(range(min = 1, max = 100))]
    pub min_connections: u32,
    
    /// Connection acquire timeout in seconds
    #[validate(range(min = 1, max = 300))]
    pub acquire_timeout: u64,
    
    /// Connection idle timeout in seconds
    #[validate(range(min = 1, max = 3600))]
    pub idle_timeout: u64,
    
    /// Connection maximum lifetime in seconds
    pub max_lifetime: Option<u64>,
    
    /// Enable automatic migrations
    pub auto_migrate: bool,
    
    /// Enable SQL query logging
    pub log_queries: bool,
    
    /// Slow query threshold in milliseconds
    pub slow_query_threshold: Option<u64>,
    
    /// Connection pool name for metrics
    pub pool_name: Option<String>,
    
    /// SSL/TLS configuration
    pub ssl: Option<DatabaseSslConfig>,
}

/// Database SSL/TLS configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct DatabaseSslConfig {
    /// Enable SSL/TLS
    pub enabled: bool,
    
    /// SSL mode (require, prefer, allow, disable)
    #[validate(length(min = 1))]
    pub mode: String,
    
    /// Path to CA certificate file
    pub ca_cert_path: Option<String>,
    
    /// Path to client certificate file
    pub client_cert_path: Option<String>,
    
    /// Path to client private key file
    pub client_key_path: Option<String>,
    
    /// Verify server certificate
    pub verify_server_cert: bool,
}

impl DatabaseConfig {
    /// Parse the database URL and extract components
    pub fn parse_url(&self) -> Result<DatabaseUrlComponents, url::ParseError> {
        let url = Url::parse(&self.url)?;
        
        Ok(DatabaseUrlComponents {
            scheme: url.scheme().to_string(),
            username: url.username().to_string(),
            password: url.password().map(|p| p.to_string()),
            host: url.host_str().unwrap_or("localhost").to_string(),
            port: url.port().unwrap_or(5432),
            database: url.path().trim_start_matches('/').to_string(),
            query_params: url.query_pairs().into_owned().collect(),
        })
    }

    /// Get connection acquire timeout as Duration
    pub fn acquire_timeout_duration(&self) -> Duration {
        Duration::from_secs(self.acquire_timeout)
    }

    /// Get connection idle timeout as Duration
    pub fn idle_timeout_duration(&self) -> Duration {
        Duration::from_secs(self.idle_timeout)
    }

    /// Get connection maximum lifetime as Duration
    pub fn max_lifetime_duration(&self) -> Option<Duration> {
        self.max_lifetime.map(Duration::from_secs)
    }

    /// Get slow query threshold as Duration
    pub fn slow_query_threshold_duration(&self) -> Option<Duration> {
        self.slow_query_threshold.map(Duration::from_millis)
    }

    /// Check if SSL is enabled
    pub fn is_ssl_enabled(&self) -> bool {
        self.ssl.as_ref().map_or(false, |ssl| ssl.enabled)
    }

    /// Get SSL mode
    pub fn ssl_mode(&self) -> Option<&str> {
        self.ssl.as_ref().map(|ssl| ssl.mode.as_str())
    }

    /// Validate database configuration
    pub fn validate_config(&self) -> Result<(), String> {
        // Validate URL format
        if let Err(e) = self.parse_url() {
            return Err(format!("Invalid database URL: {}", e));
        }

        // Validate connection pool settings
        if self.min_connections > self.max_connections {
            return Err("min_connections cannot be greater than max_connections".to_string());
        }

        // Validate SSL configuration
        if let Some(ssl) = &self.ssl {
            if ssl.enabled && ssl.mode.is_empty() {
                return Err("SSL mode must be specified when SSL is enabled".to_string());
            }

            let valid_modes = ["require", "prefer", "allow", "disable"];
            if ssl.enabled && !valid_modes.contains(&ssl.mode.as_str()) {
                return Err(format!("Invalid SSL mode: {}. Valid modes are: {:?}", ssl.mode, valid_modes));
            }
        }

        Ok(())
    }

    /// Create a database URL with masked password for logging
    pub fn masked_url(&self) -> String {
        if let Ok(components) = self.parse_url() {
            if components.password.is_some() {
                format!("{}://{}:***@{}:{}/{}", 
                    components.scheme,
                    components.username,
                    components.host,
                    components.port,
                    components.database
                )
            } else {
                self.url.clone()
            }
        } else {
            "invalid_url".to_string()
        }
    }
}

/// Parsed database URL components
#[derive(Debug, Clone)]
pub struct DatabaseUrlComponents {
    pub scheme: String,
    pub username: String,
    pub password: Option<String>,
    pub host: String,
    pub port: u16,
    pub database: String,
    pub query_params: Vec<(String, String)>,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            url: "postgresql://regulateai:password@localhost:5432/regulateai".to_string(),
            max_connections: 20,
            min_connections: 5,
            acquire_timeout: 30,
            idle_timeout: 600,
            max_lifetime: Some(1800),
            auto_migrate: true,
            log_queries: false,
            slow_query_threshold: Some(1000), // 1 second
            pool_name: Some("regulateai_pool".to_string()),
            ssl: Some(DatabaseSslConfig {
                enabled: false,
                mode: "prefer".to_string(),
                ca_cert_path: None,
                client_cert_path: None,
                client_key_path: None,
                verify_server_cert: true,
            }),
        }
    }
}

/// Test database configuration for integration tests
impl DatabaseConfig {
    pub fn test_config() -> Self {
        Self {
            url: "postgresql://regulateai_test:password@localhost:5432/regulateai_test".to_string(),
            max_connections: 5,
            min_connections: 1,
            acquire_timeout: 10,
            idle_timeout: 60,
            max_lifetime: Some(300),
            auto_migrate: true,
            log_queries: true,
            slow_query_threshold: Some(100), // 100ms for tests
            pool_name: Some("test_pool".to_string()),
            ssl: Some(DatabaseSslConfig {
                enabled: false,
                mode: "disable".to_string(),
                ca_cert_path: None,
                client_cert_path: None,
                client_key_path: None,
                verify_server_cert: false,
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_database_config() {
        let config = DatabaseConfig::default();
        assert_eq!(config.max_connections, 20);
        assert_eq!(config.min_connections, 5);
        assert_eq!(config.acquire_timeout, 30);
        assert!(config.auto_migrate);
    }

    #[test]
    fn test_parse_database_url() {
        let config = DatabaseConfig::default();
        let components = config.parse_url().unwrap();
        
        assert_eq!(components.scheme, "postgresql");
        assert_eq!(components.username, "regulateai");
        assert_eq!(components.password, Some("password".to_string()));
        assert_eq!(components.host, "localhost");
        assert_eq!(components.port, 5432);
        assert_eq!(components.database, "regulateai");
    }

    #[test]
    fn test_masked_url() {
        let config = DatabaseConfig::default();
        let masked = config.masked_url();
        assert!(masked.contains("***"));
        assert!(!masked.contains("password"));
    }

    #[test]
    fn test_validate_config() {
        let mut config = DatabaseConfig::default();
        assert!(config.validate_config().is_ok());

        // Test invalid min/max connections
        config.min_connections = 30;
        config.max_connections = 20;
        assert!(config.validate_config().is_err());

        // Reset and test invalid URL
        config = DatabaseConfig::default();
        config.url = "invalid-url".to_string();
        assert!(config.validate_config().is_err());
    }

    #[test]
    fn test_duration_conversions() {
        let config = DatabaseConfig::default();
        
        assert_eq!(config.acquire_timeout_duration(), Duration::from_secs(30));
        assert_eq!(config.idle_timeout_duration(), Duration::from_secs(600));
        assert_eq!(config.max_lifetime_duration(), Some(Duration::from_secs(1800)));
        assert_eq!(config.slow_query_threshold_duration(), Some(Duration::from_millis(1000)));
    }

    #[test]
    fn test_ssl_configuration() {
        let config = DatabaseConfig::default();
        assert!(!config.is_ssl_enabled());
        assert_eq!(config.ssl_mode(), Some("prefer"));
    }

    #[test]
    fn test_test_config() {
        let config = DatabaseConfig::test_config();
        assert!(config.url.contains("test"));
        assert_eq!(config.max_connections, 5);
        assert!(config.log_queries);
    }
}
