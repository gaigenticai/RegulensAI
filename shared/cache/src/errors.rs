//! Cache Error Types

use thiserror::Error;

/// Cache error types
#[derive(Error, Debug)]
pub enum CacheError {
    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Compression error: {0}")]
    Compression(String),

    #[error("Connection error: {0}")]
    Connection(String),

    #[error("Redis error: {0}")]
    Redis(String),

    #[error("Database error: {0}")]
    Database(String),

    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Entry too large: {size} bytes, max: {max_size} bytes")]
    EntryTooLarge { size: usize, max_size: usize },

    #[error("Cache level not available: {level:?}")]
    LevelNotAvailable { level: crate::CacheLevel },

    #[error("Multiple errors occurred: {0:?}")]
    MultipleErrors(Vec<String>),

    #[error("Timeout error: {0}")]
    Timeout(String),

    #[error("Invalid key: {0}")]
    InvalidKey(String),

    #[error("Cache is full")]
    CacheFull,

    #[error("Unknown error: {0}")]
    Unknown(String),
}

/// Cache result type
pub type CacheResult<T> = Result<T, CacheError>;

impl From<redis::RedisError> for CacheError {
    fn from(err: redis::RedisError) -> Self {
        CacheError::Redis(err.to_string())
    }
}

impl From<sqlx::Error> for CacheError {
    fn from(err: sqlx::Error) -> Self {
        CacheError::Database(err.to_string())
    }
}

impl From<serde_json::Error> for CacheError {
    fn from(err: serde_json::Error) -> Self {
        CacheError::Serialization(err.to_string())
    }
}

impl From<bincode::Error> for CacheError {
    fn from(err: bincode::Error) -> Self {
        CacheError::Serialization(err.to_string())
    }
}
