//! Core error types for RegulateAI services

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use uuid::Uuid;

/// Main error type for RegulateAI services
#[derive(Error, Debug, Clone, Serialize, Deserialize)]
pub enum RegulateAIError {
    /// Validation errors
    #[error("Validation failed: {message}")]
    Validation {
        message: String,
        field: Option<String>,
        code: String,
    },

    /// Authentication errors
    #[error("Authentication failed: {message}")]
    Authentication {
        message: String,
        code: String,
    },

    /// Authorization errors
    #[error("Authorization failed: {message}")]
    Authorization {
        message: String,
        required_permission: Option<String>,
        code: String,
    },

    /// Resource not found errors
    #[error("Resource not found: {resource_type} with ID {resource_id}")]
    NotFound {
        resource_type: String,
        resource_id: String,
        code: String,
    },

    /// Resource already exists errors
    #[error("Resource already exists: {resource_type} with identifier {identifier}")]
    AlreadyExists {
        resource_type: String,
        identifier: String,
        code: String,
    },

    /// Business logic errors
    #[error("Business rule violation: {message}")]
    BusinessRule {
        message: String,
        rule: String,
        code: String,
    },

    /// Database errors
    #[error("Database error: {message}")]
    Database {
        message: String,
        operation: String,
        code: String,
    },

    /// External service errors
    #[error("External service error: {service} - {message}")]
    ExternalService {
        service: String,
        message: String,
        status_code: Option<u16>,
        code: String,
    },

    /// Configuration errors
    #[error("Configuration error: {message}")]
    Configuration {
        message: String,
        key: Option<String>,
        code: String,
    },

    /// Rate limiting errors
    #[error("Rate limit exceeded: {message}")]
    RateLimit {
        message: String,
        limit: u32,
        window_seconds: u32,
        retry_after: Option<u32>,
        code: String,
    },

    /// Timeout errors
    #[error("Operation timed out: {operation}")]
    Timeout {
        operation: String,
        timeout_seconds: u32,
        code: String,
    },

    /// Internal server errors
    #[error("Internal server error: {message}")]
    Internal {
        message: String,
        source: Option<String>,
        code: String,
    },

    /// Service unavailable errors
    #[error("Service unavailable: {service}")]
    ServiceUnavailable {
        service: String,
        message: String,
        retry_after: Option<u32>,
        code: String,
    },

    /// Data integrity errors
    #[error("Data integrity violation: {message}")]
    DataIntegrity {
        message: String,
        constraint: Option<String>,
        code: String,
    },

    /// Serialization/Deserialization errors
    #[error("Serialization error: {message}")]
    Serialization {
        message: String,
        format: String,
        code: String,
    },

    /// File system errors
    #[error("File system error: {message}")]
    FileSystem {
        message: String,
        path: Option<String>,
        operation: String,
        code: String,
    },

    /// Network errors
    #[error("Network error: {message}")]
    Network {
        message: String,
        endpoint: Option<String>,
        code: String,
    },

    /// Cryptographic errors
    #[error("Cryptographic error: {message}")]
    Cryptographic {
        message: String,
        operation: String,
        code: String,
    },
}

impl RegulateAIError {
    /// Get the error code
    pub fn code(&self) -> &str {
        match self {
            Self::Validation { code, .. } => code,
            Self::Authentication { code, .. } => code,
            Self::Authorization { code, .. } => code,
            Self::NotFound { code, .. } => code,
            Self::AlreadyExists { code, .. } => code,
            Self::BusinessRule { code, .. } => code,
            Self::Database { code, .. } => code,
            Self::ExternalService { code, .. } => code,
            Self::Configuration { code, .. } => code,
            Self::RateLimit { code, .. } => code,
            Self::Timeout { code, .. } => code,
            Self::Internal { code, .. } => code,
            Self::ServiceUnavailable { code, .. } => code,
            Self::DataIntegrity { code, .. } => code,
            Self::Serialization { code, .. } => code,
            Self::FileSystem { code, .. } => code,
            Self::Network { code, .. } => code,
            Self::Cryptographic { code, .. } => code,
        }
    }

    /// Check if the error is retryable
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::Timeout { .. }
                | Self::ServiceUnavailable { .. }
                | Self::Network { .. }
                | Self::ExternalService { status_code: Some(status), .. } if *status >= 500
        )
    }

    /// Check if the error is a client error (4xx)
    pub fn is_client_error(&self) -> bool {
        matches!(
            self,
            Self::Validation { .. }
                | Self::Authentication { .. }
                | Self::Authorization { .. }
                | Self::NotFound { .. }
                | Self::AlreadyExists { .. }
                | Self::BusinessRule { .. }
                | Self::RateLimit { .. }
        )
    }

    /// Check if the error is a server error (5xx)
    pub fn is_server_error(&self) -> bool {
        matches!(
            self,
            Self::Internal { .. }
                | Self::ServiceUnavailable { .. }
                | Self::Database { .. }
                | Self::Configuration { .. }
                | Self::Timeout { .. }
        )
    }
}

/// Error context for additional debugging information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorContext {
    pub request_id: Uuid,
    pub correlation_id: Option<String>,
    pub user_id: Option<Uuid>,
    pub service: String,
    pub operation: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ErrorContext {
    pub fn new(service: &str, operation: &str) -> Self {
        Self {
            request_id: Uuid::new_v4(),
            correlation_id: None,
            user_id: None,
            service: service.to_string(),
            operation: operation.to_string(),
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        }
    }

    pub fn with_correlation_id(mut self, correlation_id: String) -> Self {
        self.correlation_id = Some(correlation_id);
        self
    }

    pub fn with_user_id(mut self, user_id: Uuid) -> Self {
        self.user_id = Some(user_id);
        self
    }

    pub fn with_metadata(mut self, key: &str, value: serde_json::Value) -> Self {
        self.metadata.insert(key.to_string(), value);
        self
    }
}

/// Detailed error response with context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorResponse {
    pub error: RegulateAIError,
    pub context: ErrorContext,
    pub trace_id: Option<String>,
}

impl ErrorResponse {
    pub fn new(error: RegulateAIError, context: ErrorContext) -> Self {
        Self {
            error,
            context,
            trace_id: None,
        }
    }

    pub fn with_trace_id(mut self, trace_id: String) -> Self {
        self.trace_id = Some(trace_id);
        self
    }
}

/// Result type alias for RegulateAI operations
pub type Result<T> = std::result::Result<T, RegulateAIError>;

/// Convenience macros for creating errors
#[macro_export]
macro_rules! validation_error {
    ($message:expr) => {
        RegulateAIError::Validation {
            message: $message.to_string(),
            field: None,
            code: "VALIDATION_ERROR".to_string(),
        }
    };
    ($message:expr, $field:expr) => {
        RegulateAIError::Validation {
            message: $message.to_string(),
            field: Some($field.to_string()),
            code: "VALIDATION_ERROR".to_string(),
        }
    };
    ($message:expr, $field:expr, $code:expr) => {
        RegulateAIError::Validation {
            message: $message.to_string(),
            field: Some($field.to_string()),
            code: $code.to_string(),
        }
    };
}

#[macro_export]
macro_rules! not_found_error {
    ($resource_type:expr, $resource_id:expr) => {
        RegulateAIError::NotFound {
            resource_type: $resource_type.to_string(),
            resource_id: $resource_id.to_string(),
            code: "RESOURCE_NOT_FOUND".to_string(),
        }
    };
}

#[macro_export]
macro_rules! internal_error {
    ($message:expr) => {
        RegulateAIError::Internal {
            message: $message.to_string(),
            source: None,
            code: "INTERNAL_ERROR".to_string(),
        }
    };
    ($message:expr, $source:expr) => {
        RegulateAIError::Internal {
            message: $message.to_string(),
            source: Some($source.to_string()),
            code: "INTERNAL_ERROR".to_string(),
        }
    };
}
