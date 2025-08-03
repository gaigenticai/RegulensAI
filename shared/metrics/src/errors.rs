//! Metrics Error Types

use thiserror::Error;

/// Metrics error types
#[derive(Error, Debug)]
pub enum MetricsError {
    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Collection error: {0}")]
    Collection(String),

    #[error("Export error: {0}")]
    Export(String),

    #[error("Database error: {0}")]
    Database(String),

    #[error("Network error: {0}")]
    Network(String),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Unknown error: {0}")]
    Unknown(String),
}

/// Metrics result type
pub type MetricsResult<T> = Result<T, MetricsError>;
