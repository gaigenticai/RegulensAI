//! Monitoring and observability configuration

use serde::{Deserialize, Serialize};
use validator::Validate;

/// Monitoring configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct MonitoringConfig {
    /// Metrics configuration
    pub metrics: MetricsConfig,
    
    /// Tracing configuration
    pub tracing: TracingConfig,
    
    /// Health check configuration
    pub health_check: HealthCheckConfig,
    
    /// Logging configuration
    pub logging: LoggingConfig,
}

/// Metrics configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct MetricsConfig {
    /// Enable metrics collection
    pub enabled: bool,
    
    /// Metrics server port
    #[validate(range(min = 1024, max = 65535))]
    pub port: u16,
    
    /// Metrics endpoint path
    #[validate(length(min = 1))]
    pub path: String,
    
    /// Collection interval in seconds
    #[validate(range(min = 1, max = 300))]
    pub collection_interval: u64,
    
    /// Prometheus configuration
    pub prometheus: PrometheusConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct PrometheusConfig {
    /// Enable Prometheus metrics
    pub enabled: bool,
    
    /// Metrics namespace
    #[validate(length(min = 1))]
    pub namespace: String,
    
    /// Default labels to add to all metrics
    pub default_labels: std::collections::HashMap<String, String>,
    
    /// Histogram buckets for request duration
    pub request_duration_buckets: Vec<f64>,
}

/// Tracing configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct TracingConfig {
    /// Enable distributed tracing
    pub enabled: bool,
    
    /// Service name for tracing
    #[validate(length(min = 1))]
    pub service_name: String,
    
    /// Jaeger configuration
    pub jaeger: JaegerConfig,
    
    /// Sampling configuration
    pub sampling: SamplingConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct JaegerConfig {
    /// Enable Jaeger tracing
    pub enabled: bool,
    
    /// Jaeger endpoint URL
    #[validate(url)]
    pub endpoint: String,
    
    /// Jaeger agent host
    pub agent_host: Option<String>,
    
    /// Jaeger agent port
    pub agent_port: Option<u16>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct SamplingConfig {
    /// Sampling rate (0.0 to 1.0)
    #[validate(range(min = 0.0, max = 1.0))]
    pub rate: f64,
    
    /// Sampling strategy
    pub strategy: SamplingStrategy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SamplingStrategy {
    /// Always sample
    Always,
    /// Never sample
    Never,
    /// Probabilistic sampling
    Probabilistic,
    /// Rate limiting sampling
    RateLimiting,
}

/// Health check configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct HealthCheckConfig {
    /// Enable health checks
    pub enabled: bool,
    
    /// Health check endpoint path
    #[validate(length(min = 1))]
    pub path: String,
    
    /// Health check interval in seconds
    #[validate(range(min = 1, max = 300))]
    pub interval: u64,
    
    /// Health check timeout in seconds
    #[validate(range(min = 1, max = 60))]
    pub timeout: u64,
    
    /// Dependencies to check
    pub dependencies: Vec<DependencyCheck>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct DependencyCheck {
    /// Dependency name
    #[validate(length(min = 1))]
    pub name: String,
    
    /// Dependency type
    pub check_type: DependencyType,
    
    /// Connection string or URL
    #[validate(length(min = 1))]
    pub connection: String,
    
    /// Check timeout in seconds
    #[validate(range(min = 1, max = 30))]
    pub timeout: u64,
    
    /// Critical dependency (affects overall health)
    pub critical: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DependencyType {
    Database,
    Redis,
    Http,
    Tcp,
    Custom,
}

/// Logging configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct LoggingConfig {
    /// Log level
    pub level: LogLevel,
    
    /// Log format
    pub format: LogFormat,
    
    /// Include source location in logs
    pub include_location: bool,
    
    /// Include thread ID in logs
    pub include_thread_id: bool,
    
    /// Log file configuration
    pub file: Option<LogFileConfig>,
    
    /// Structured logging fields
    pub structured_fields: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogLevel {
    Trace,
    Debug,
    Info,
    Warn,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogFormat {
    Json,
    Pretty,
    Compact,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct LogFileConfig {
    /// Log file path
    #[validate(length(min = 1))]
    pub path: String,
    
    /// Maximum file size in MB
    #[validate(range(min = 1, max = 1000))]
    pub max_size_mb: u64,
    
    /// Maximum number of log files to keep
    #[validate(range(min = 1, max = 100))]
    pub max_files: u32,
    
    /// Log rotation strategy
    pub rotation: LogRotation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LogRotation {
    Daily,
    Hourly,
    Size,
    Never,
}

impl Default for MonitoringConfig {
    fn default() -> Self {
        Self {
            metrics: MetricsConfig {
                enabled: true,
                port: 9090,
                path: "/metrics".to_string(),
                collection_interval: 60,
                prometheus: PrometheusConfig {
                    enabled: true,
                    namespace: "regulateai".to_string(),
                    default_labels: std::collections::HashMap::new(),
                    request_duration_buckets: vec![0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                },
            },
            tracing: TracingConfig {
                enabled: true,
                service_name: "regulateai".to_string(),
                jaeger: JaegerConfig {
                    enabled: true,
                    endpoint: "http://localhost:14268/api/traces".to_string(),
                    agent_host: Some("localhost".to_string()),
                    agent_port: Some(6831),
                },
                sampling: SamplingConfig {
                    rate: 0.1,
                    strategy: SamplingStrategy::Probabilistic,
                },
            },
            health_check: HealthCheckConfig {
                enabled: true,
                path: "/health".to_string(),
                interval: 30,
                timeout: 10,
                dependencies: vec![],
            },
            logging: LoggingConfig {
                level: LogLevel::Info,
                format: LogFormat::Json,
                include_location: true,
                include_thread_id: true,
                file: None,
                structured_fields: vec!["request_id".to_string(), "user_id".to_string(), "correlation_id".to_string()],
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_monitoring_config() {
        let config = MonitoringConfig::default();
        assert!(config.metrics.enabled);
        assert_eq!(config.metrics.port, 9090);
        assert!(config.tracing.enabled);
        assert_eq!(config.tracing.service_name, "regulateai");
        assert!(config.health_check.enabled);
    }
}
