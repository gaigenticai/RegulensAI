//! Main application settings and configuration management

use config::{Config, ConfigError, Environment, File, FileFormat};
use serde::{Deserialize, Serialize};
use std::env;
use std::path::Path;
use validator::Validate;

use crate::{DatabaseConfig, RedisConfig, SecurityConfig, ExternalServicesConfig, MonitoringConfig, ServiceConfig};

/// Main application settings structure
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct AppSettings {
    /// Application metadata
    pub application: ApplicationConfig,
    
    /// Server configuration
    pub server: ServerConfig,
    
    /// Database configuration
    pub database: DatabaseConfig,
    
    /// Redis configuration
    pub redis: RedisConfig,
    
    /// Security configuration
    pub security: SecurityConfig,
    
    /// External services configuration
    pub external_services: ExternalServicesConfig,
    
    /// Monitoring configuration
    pub monitoring: MonitoringConfig,
    
    /// Service-specific configurations
    pub services: ServiceConfig,
}

/// Application metadata configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ApplicationConfig {
    #[validate(length(min = 1))]
    pub name: String,
    
    #[validate(length(min = 1))]
    pub version: String,
    
    #[validate(length(min = 1))]
    pub environment: String,
    
    pub description: Option<String>,
}

/// Server configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct ServerConfig {
    #[validate(length(min = 1))]
    pub host: String,
    
    #[validate(range(min = 1, max = 65535))]
    pub port: u16,
    
    #[validate(range(min = 1, max = 1000))]
    pub workers: Option<usize>,
    
    #[validate(range(min = 1))]
    pub keep_alive: Option<u64>,
    
    #[validate(range(min = 1))]
    pub client_timeout: Option<u64>,
    
    #[validate(range(min = 1))]
    pub client_shutdown: Option<u64>,
    
    pub tls: Option<TlsConfig>,
}

/// TLS configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct TlsConfig {
    pub enabled: bool,
    
    #[validate(length(min = 1))]
    pub cert_path: String,
    
    #[validate(length(min = 1))]
    pub key_path: String,
    
    pub ca_cert_path: Option<String>,
}

impl AppSettings {
    /// Load configuration from multiple sources
    pub fn load() -> Result<Self, ConfigError> {
        let mut config = Config::builder();

        // Start with default configuration file
        if Path::new("config/default.yaml").exists() {
            config = config.add_source(File::with_name("config/default").format(FileFormat::Yaml));
        }

        // Add environment-specific configuration
        let env = env::var("RUST_ENV").unwrap_or_else(|_| "development".to_string());
        let env_config_path = format!("config/{}.yaml", env);
        if Path::new(&env_config_path).exists() {
            config = config.add_source(File::with_name(&format!("config/{}", env)).format(FileFormat::Yaml));
        }

        // Add local configuration (not committed to version control)
        if Path::new("config/local.yaml").exists() {
            config = config.add_source(File::with_name("config/local").format(FileFormat::Yaml));
        }

        // Add environment variables (with REGULATEAI_ prefix)
        config = config.add_source(
            Environment::with_prefix("REGULATEAI")
                .separator("_")
                .try_parsing(true)
        );

        // Add environment variables without prefix for common settings
        config = config.add_source(
            Environment::default()
                .try_parsing(true)
        );

        let settings: AppSettings = config.build()?.try_deserialize()?;
        
        // Validate the configuration
        settings.validate().map_err(|e| {
            ConfigError::Message(format!("Configuration validation failed: {:?}", e))
        })?;

        Ok(settings)
    }

    /// Load configuration with custom config directory
    pub fn load_from_dir<P: AsRef<Path>>(config_dir: P) -> Result<Self, ConfigError> {
        let config_dir = config_dir.as_ref();
        let mut config = Config::builder();

        // Default configuration
        let default_path = config_dir.join("default.yaml");
        if default_path.exists() {
            config = config.add_source(File::from(default_path).format(FileFormat::Yaml));
        }

        // Environment-specific configuration
        let env = env::var("RUST_ENV").unwrap_or_else(|_| "development".to_string());
        let env_path = config_dir.join(format!("{}.yaml", env));
        if env_path.exists() {
            config = config.add_source(File::from(env_path).format(FileFormat::Yaml));
        }

        // Local configuration
        let local_path = config_dir.join("local.yaml");
        if local_path.exists() {
            config = config.add_source(File::from(local_path).format(FileFormat::Yaml));
        }

        // Environment variables
        config = config.add_source(
            Environment::with_prefix("REGULATEAI")
                .separator("_")
                .try_parsing(true)
        );

        config = config.add_source(
            Environment::default()
                .try_parsing(true)
        );

        let settings: AppSettings = config.build()?.try_deserialize()?;
        
        settings.validate().map_err(|e| {
            ConfigError::Message(format!("Configuration validation failed: {:?}", e))
        })?;

        Ok(settings)
    }

    /// Get the current environment
    pub fn environment(&self) -> &str {
        &self.application.environment
    }

    /// Check if running in development mode
    pub fn is_development(&self) -> bool {
        self.application.environment == "development"
    }

    /// Check if running in production mode
    pub fn is_production(&self) -> bool {
        self.application.environment == "production"
    }

    /// Check if running in test mode
    pub fn is_test(&self) -> bool {
        self.application.environment == "test"
    }

    /// Get the server bind address
    pub fn bind_address(&self) -> String {
        format!("{}:{}", self.server.host, self.server.port)
    }

    /// Get the number of worker threads
    pub fn workers(&self) -> usize {
        self.server.workers.unwrap_or_else(|| {
            std::thread::available_parallelism()
                .map(|n| n.get())
                .unwrap_or(4)
        })
    }
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            application: ApplicationConfig {
                name: "RegulateAI".to_string(),
                version: env!("CARGO_PKG_VERSION").to_string(),
                environment: "development".to_string(),
                description: Some("Enterprise Regulatory Compliance & Risk Management System".to_string()),
            },
            server: ServerConfig {
                host: "0.0.0.0".to_string(),
                port: 8080,
                workers: None,
                keep_alive: Some(75),
                client_timeout: Some(5000),
                client_shutdown: Some(5000),
                tls: None,
            },
            database: DatabaseConfig::default(),
            redis: RedisConfig::default(),
            security: SecurityConfig::default(),
            external_services: ExternalServicesConfig::default(),
            monitoring: MonitoringConfig::default(),
            services: ServiceConfig::default(),
        }
    }
}

/// Configuration builder for programmatic configuration
pub struct ConfigBuilder {
    config: Config,
}

impl ConfigBuilder {
    pub fn new() -> Self {
        Self {
            config: Config::builder().build().unwrap(),
        }
    }

    pub fn add_file<P: AsRef<Path>>(mut self, path: P, format: FileFormat) -> Self {
        self.config = Config::builder()
            .add_source(self.config)
            .add_source(File::from(path.as_ref()).format(format))
            .build()
            .unwrap();
        self
    }

    pub fn add_env_prefix(mut self, prefix: &str) -> Self {
        self.config = Config::builder()
            .add_source(self.config)
            .add_source(
                Environment::with_prefix(prefix)
                    .separator("_")
                    .try_parsing(true)
            )
            .build()
            .unwrap();
        self
    }

    pub fn set<T>(mut self, key: &str, value: T) -> Self 
    where
        T: Into<config::Value>,
    {
        self.config.set(key, value).unwrap();
        self
    }

    pub fn build(self) -> Result<AppSettings, ConfigError> {
        let settings: AppSettings = self.config.try_deserialize()?;
        
        settings.validate().map_err(|e| {
            ConfigError::Message(format!("Configuration validation failed: {:?}", e))
        })?;

        Ok(settings)
    }
}

impl Default for ConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_default_settings() {
        let settings = AppSettings::default();
        assert_eq!(settings.application.name, "RegulateAI");
        assert_eq!(settings.application.environment, "development");
        assert_eq!(settings.server.host, "0.0.0.0");
        assert_eq!(settings.server.port, 8080);
    }

    #[test]
    fn test_bind_address() {
        let settings = AppSettings::default();
        assert_eq!(settings.bind_address(), "0.0.0.0:8080");
    }

    #[test]
    fn test_environment_checks() {
        let mut settings = AppSettings::default();
        
        settings.application.environment = "development".to_string();
        assert!(settings.is_development());
        assert!(!settings.is_production());
        assert!(!settings.is_test());

        settings.application.environment = "production".to_string();
        assert!(!settings.is_development());
        assert!(settings.is_production());
        assert!(!settings.is_test());

        settings.application.environment = "test".to_string();
        assert!(!settings.is_development());
        assert!(!settings.is_production());
        assert!(settings.is_test());
    }

    #[test]
    fn test_config_builder() {
        let settings = ConfigBuilder::new()
            .set("application.name", "TestApp")
            .set("server.port", 9000)
            .build()
            .unwrap();

        assert_eq!(settings.application.name, "TestApp");
        assert_eq!(settings.server.port, 9000);
    }
}
