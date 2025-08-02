//! HTTP error handling and response utilities

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::error;
use uuid::Uuid;

use crate::types::{ErrorContext, ErrorResponse, RegulateAIError};

/// HTTP error response structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HttpErrorResponse {
    pub success: bool,
    pub error: HttpError,
    pub request_id: Uuid,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub path: Option<String>,
}

/// HTTP error details
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HttpError {
    pub code: String,
    pub message: String,
    pub details: Option<HashMap<String, serde_json::Value>>,
    pub retry_after: Option<u32>,
}

impl IntoResponse for RegulateAIError {
    fn into_response(self) -> Response {
        let (status_code, http_error) = match &self {
            RegulateAIError::Validation { message, field, code } => {
                let mut details = HashMap::new();
                if let Some(field) = field {
                    details.insert("field".to_string(), serde_json::Value::String(field.clone()));
                }
                (
                    StatusCode::BAD_REQUEST,
                    HttpError {
                        code: code.clone(),
                        message: message.clone(),
                        details: if details.is_empty() { None } else { Some(details) },
                        retry_after: None,
                    },
                )
            }
            RegulateAIError::Authentication { message, code } => (
                StatusCode::UNAUTHORIZED,
                HttpError {
                    code: code.clone(),
                    message: message.clone(),
                    details: None,
                    retry_after: None,
                },
            ),
            RegulateAIError::Authorization { message, required_permission, code } => {
                let mut details = HashMap::new();
                if let Some(permission) = required_permission {
                    details.insert("required_permission".to_string(), serde_json::Value::String(permission.clone()));
                }
                (
                    StatusCode::FORBIDDEN,
                    HttpError {
                        code: code.clone(),
                        message: message.clone(),
                        details: if details.is_empty() { None } else { Some(details) },
                        retry_after: None,
                    },
                )
            }
            RegulateAIError::NotFound { resource_type, resource_id, code } => {
                let mut details = HashMap::new();
                details.insert("resource_type".to_string(), serde_json::Value::String(resource_type.clone()));
                details.insert("resource_id".to_string(), serde_json::Value::String(resource_id.clone()));
                (
                    StatusCode::NOT_FOUND,
                    HttpError {
                        code: code.clone(),
                        message: format!("{} not found", resource_type),
                        details: Some(details),
                        retry_after: None,
                    },
                )
            }
            RegulateAIError::AlreadyExists { resource_type, identifier, code } => {
                let mut details = HashMap::new();
                details.insert("resource_type".to_string(), serde_json::Value::String(resource_type.clone()));
                details.insert("identifier".to_string(), serde_json::Value::String(identifier.clone()));
                (
                    StatusCode::CONFLICT,
                    HttpError {
                        code: code.clone(),
                        message: format!("{} already exists", resource_type),
                        details: Some(details),
                        retry_after: None,
                    },
                )
            }
            RegulateAIError::BusinessRule { message, rule, code } => {
                let mut details = HashMap::new();
                details.insert("rule".to_string(), serde_json::Value::String(rule.clone()));
                (
                    StatusCode::UNPROCESSABLE_ENTITY,
                    HttpError {
                        code: code.clone(),
                        message: message.clone(),
                        details: Some(details),
                        retry_after: None,
                    },
                )
            }
            RegulateAIError::RateLimit { message, limit, window_seconds, retry_after, code } => {
                let mut details = HashMap::new();
                details.insert("limit".to_string(), serde_json::Value::Number((*limit).into()));
                details.insert("window_seconds".to_string(), serde_json::Value::Number((*window_seconds).into()));
                (
                    StatusCode::TOO_MANY_REQUESTS,
                    HttpError {
                        code: code.clone(),
                        message: message.clone(),
                        details: Some(details),
                        retry_after: *retry_after,
                    },
                )
            }
            RegulateAIError::Timeout { operation, timeout_seconds, code } => {
                let mut details = HashMap::new();
                details.insert("operation".to_string(), serde_json::Value::String(operation.clone()));
                details.insert("timeout_seconds".to_string(), serde_json::Value::Number((*timeout_seconds).into()));
                (
                    StatusCode::REQUEST_TIMEOUT,
                    HttpError {
                        code: code.clone(),
                        message: format!("Operation '{}' timed out", operation),
                        details: Some(details),
                        retry_after: None,
                    },
                )
            }
            RegulateAIError::ServiceUnavailable { service, message, retry_after, code } => {
                let mut details = HashMap::new();
                details.insert("service".to_string(), serde_json::Value::String(service.clone()));
                (
                    StatusCode::SERVICE_UNAVAILABLE,
                    HttpError {
                        code: code.clone(),
                        message: message.clone(),
                        details: Some(details),
                        retry_after: *retry_after,
                    },
                )
            }
            RegulateAIError::ExternalService { service, message, status_code, code } => {
                let mut details = HashMap::new();
                details.insert("service".to_string(), serde_json::Value::String(service.clone()));
                if let Some(status) = status_code {
                    details.insert("external_status_code".to_string(), serde_json::Value::Number((*status).into()));
                }
                (
                    StatusCode::BAD_GATEWAY,
                    HttpError {
                        code: code.clone(),
                        message: format!("External service '{}' error: {}", service, message),
                        details: Some(details),
                        retry_after: None,
                    },
                )
            }
            _ => (
                StatusCode::INTERNAL_SERVER_ERROR,
                HttpError {
                    code: self.code().to_string(),
                    message: "Internal server error".to_string(),
                    details: None,
                    retry_after: None,
                },
            ),
        };

        let response = HttpErrorResponse {
            success: false,
            error: http_error,
            request_id: Uuid::new_v4(),
            timestamp: chrono::Utc::now(),
            path: None,
        };

        // Log the error
        error!(
            error = %self,
            status_code = %status_code,
            request_id = %response.request_id,
            "HTTP error response"
        );

        (status_code, Json(response)).into_response()
    }
}

impl IntoResponse for ErrorResponse {
    fn into_response(self) -> Response {
        let mut regulateai_error_response: Response = self.error.into_response();
        
        // Add trace ID header if available
        if let Some(trace_id) = &self.trace_id {
            regulateai_error_response.headers_mut().insert(
                "X-Trace-ID",
                trace_id.parse().unwrap_or_else(|_| "invalid".parse().unwrap()),
            );
        }

        // Add correlation ID header if available
        if let Some(correlation_id) = &self.context.correlation_id {
            regulateai_error_response.headers_mut().insert(
                "X-Correlation-ID",
                correlation_id.parse().unwrap_or_else(|_| "invalid".parse().unwrap()),
            );
        }

        regulateai_error_response
    }
}

/// Utility function to create a validation error response
pub fn validation_error_response(message: &str, field: Option<&str>) -> RegulateAIError {
    RegulateAIError::Validation {
        message: message.to_string(),
        field: field.map(|f| f.to_string()),
        code: "VALIDATION_ERROR".to_string(),
    }
}

/// Utility function to create a not found error response
pub fn not_found_error_response(resource_type: &str, resource_id: &str) -> RegulateAIError {
    RegulateAIError::NotFound {
        resource_type: resource_type.to_string(),
        resource_id: resource_id.to_string(),
        code: "RESOURCE_NOT_FOUND".to_string(),
    }
}

/// Utility function to create an internal error response
pub fn internal_error_response(message: &str) -> RegulateAIError {
    RegulateAIError::Internal {
        message: message.to_string(),
        source: None,
        code: "INTERNAL_ERROR".to_string(),
    }
}

/// Utility function to create an authentication error response
pub fn auth_error_response(message: &str) -> RegulateAIError {
    RegulateAIError::Authentication {
        message: message.to_string(),
        code: "AUTHENTICATION_FAILED".to_string(),
    }
}

/// Utility function to create an authorization error response
pub fn authz_error_response(message: &str, required_permission: Option<&str>) -> RegulateAIError {
    RegulateAIError::Authorization {
        message: message.to_string(),
        required_permission: required_permission.map(|p| p.to_string()),
        code: "AUTHORIZATION_FAILED".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;

    #[test]
    fn test_validation_error_response() {
        let error = validation_error_response("Invalid email format", Some("email"));
        match error {
            RegulateAIError::Validation { message, field, code } => {
                assert_eq!(message, "Invalid email format");
                assert_eq!(field, Some("email".to_string()));
                assert_eq!(code, "VALIDATION_ERROR");
            }
            _ => panic!("Expected validation error"),
        }
    }

    #[test]
    fn test_not_found_error_response() {
        let error = not_found_error_response("User", "123");
        match error {
            RegulateAIError::NotFound { resource_type, resource_id, code } => {
                assert_eq!(resource_type, "User");
                assert_eq!(resource_id, "123");
                assert_eq!(code, "RESOURCE_NOT_FOUND");
            }
            _ => panic!("Expected not found error"),
        }
    }

    #[test]
    fn test_error_is_retryable() {
        let timeout_error = RegulateAIError::Timeout {
            operation: "database_query".to_string(),
            timeout_seconds: 30,
            code: "TIMEOUT".to_string(),
        };
        assert!(timeout_error.is_retryable());

        let validation_error = RegulateAIError::Validation {
            message: "Invalid input".to_string(),
            field: None,
            code: "VALIDATION_ERROR".to_string(),
        };
        assert!(!validation_error.is_retryable());
    }
}
