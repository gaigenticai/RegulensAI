//! External service error handling utilities

use crate::types::RegulateAIError;

/// Convert reqwest errors to RegulateAIError
impl From<reqwest::Error> for RegulateAIError {
    fn from(error: reqwest::Error) -> Self {
        if error.is_timeout() {
            RegulateAIError::Timeout {
                operation: "http_request".to_string(),
                timeout_seconds: 30,
                code: "HTTP_REQUEST_TIMEOUT".to_string(),
            }
        } else if error.is_connect() {
            RegulateAIError::Network {
                message: format!("Connection error: {}", error),
                endpoint: error.url().map(|u| u.to_string()),
                code: "HTTP_CONNECTION_ERROR".to_string(),
            }
        } else if error.is_request() {
            RegulateAIError::Validation {
                message: format!("Invalid request: {}", error),
                field: None,
                code: "HTTP_REQUEST_ERROR".to_string(),
            }
        } else if let Some(status) = error.status() {
            let status_code = status.as_u16();
            match status_code {
                400..=499 => RegulateAIError::ExternalService {
                    service: "external_api".to_string(),
                    message: format!("Client error: {}", error),
                    status_code: Some(status_code),
                    code: "EXTERNAL_CLIENT_ERROR".to_string(),
                },
                500..=599 => RegulateAIError::ExternalService {
                    service: "external_api".to_string(),
                    message: format!("Server error: {}", error),
                    status_code: Some(status_code),
                    code: "EXTERNAL_SERVER_ERROR".to_string(),
                },
                _ => RegulateAIError::ExternalService {
                    service: "external_api".to_string(),
                    message: format!("HTTP error: {}", error),
                    status_code: Some(status_code),
                    code: "EXTERNAL_HTTP_ERROR".to_string(),
                },
            }
        } else {
            RegulateAIError::ExternalService {
                service: "external_api".to_string(),
                message: error.to_string(),
                status_code: None,
                code: "EXTERNAL_UNKNOWN_ERROR".to_string(),
            }
        }
    }
}

/// Convert serde_json errors to RegulateAIError
impl From<serde_json::Error> for RegulateAIError {
    fn from(error: serde_json::Error) -> Self {
        RegulateAIError::Serialization {
            message: format!("JSON serialization error: {}", error),
            format: "json".to_string(),
            code: "JSON_SERIALIZATION_ERROR".to_string(),
        }
    }
}

/// Convert URL parse errors to RegulateAIError
impl From<url::ParseError> for RegulateAIError {
    fn from(error: url::ParseError) -> Self {
        RegulateAIError::Validation {
            message: format!("Invalid URL format: {}", error),
            field: Some("url".to_string()),
            code: "INVALID_URL_FORMAT".to_string(),
        }
    }
}

/// Convert Redis errors to RegulateAIError
impl From<redis::RedisError> for RegulateAIError {
    fn from(error: redis::RedisError) -> Self {
        match error.kind() {
            redis::ErrorKind::AuthenticationFailed => RegulateAIError::Authentication {
                message: "Redis authentication failed".to_string(),
                code: "REDIS_AUTH_FAILED".to_string(),
            },
            redis::ErrorKind::TypeError => RegulateAIError::Serialization {
                message: format!("Redis type error: {}", error),
                format: "redis".to_string(),
                code: "REDIS_TYPE_ERROR".to_string(),
            },
            redis::ErrorKind::ExecAbortError => RegulateAIError::Database {
                message: "Redis transaction aborted".to_string(),
                operation: "redis_transaction".to_string(),
                code: "REDIS_TRANSACTION_ABORTED".to_string(),
            },
            redis::ErrorKind::BusyLoadingError => RegulateAIError::ServiceUnavailable {
                service: "redis".to_string(),
                message: "Redis is loading dataset".to_string(),
                retry_after: Some(5),
                code: "REDIS_LOADING".to_string(),
            },
            redis::ErrorKind::NoScriptError => RegulateAIError::Configuration {
                message: "Redis script not found".to_string(),
                key: Some("redis_script".to_string()),
                code: "REDIS_SCRIPT_NOT_FOUND".to_string(),
            },
            redis::ErrorKind::InvalidClientConfig => RegulateAIError::Configuration {
                message: format!("Invalid Redis client configuration: {}", error),
                key: Some("redis_config".to_string()),
                code: "REDIS_INVALID_CONFIG".to_string(),
            },
            redis::ErrorKind::Moved | redis::ErrorKind::Ask => RegulateAIError::ServiceUnavailable {
                service: "redis".to_string(),
                message: "Redis cluster redirection".to_string(),
                retry_after: Some(1),
                code: "REDIS_CLUSTER_REDIRECT".to_string(),
            },
            redis::ErrorKind::TryAgain => RegulateAIError::ServiceUnavailable {
                service: "redis".to_string(),
                message: "Redis temporary failure".to_string(),
                retry_after: Some(1),
                code: "REDIS_TRY_AGAIN".to_string(),
            },
            redis::ErrorKind::ClusterDown => RegulateAIError::ServiceUnavailable {
                service: "redis".to_string(),
                message: "Redis cluster is down".to_string(),
                retry_after: Some(10),
                code: "REDIS_CLUSTER_DOWN".to_string(),
            },
            redis::ErrorKind::CrossSlot => RegulateAIError::Database {
                message: "Redis cross-slot operation".to_string(),
                operation: "redis_multi_key".to_string(),
                code: "REDIS_CROSS_SLOT".to_string(),
            },
            redis::ErrorKind::MasterDown => RegulateAIError::ServiceUnavailable {
                service: "redis".to_string(),
                message: "Redis master is down".to_string(),
                retry_after: Some(5),
                code: "REDIS_MASTER_DOWN".to_string(),
            },
            redis::ErrorKind::IoError => RegulateAIError::Network {
                message: format!("Redis I/O error: {}", error),
                endpoint: None,
                code: "REDIS_IO_ERROR".to_string(),
            },
            _ => RegulateAIError::ExternalService {
                service: "redis".to_string(),
                message: error.to_string(),
                status_code: None,
                code: "REDIS_ERROR".to_string(),
            },
        }
    }
}

/// External service context for better error reporting
pub struct ExternalServiceContext {
    pub service_name: String,
    pub operation: String,
    pub endpoint: Option<String>,
    pub timeout_seconds: Option<u32>,
}

impl ExternalServiceContext {
    pub fn new(service_name: &str, operation: &str) -> Self {
        Self {
            service_name: service_name.to_string(),
            operation: operation.to_string(),
            endpoint: None,
            timeout_seconds: None,
        }
    }

    pub fn with_endpoint(mut self, endpoint: &str) -> Self {
        self.endpoint = Some(endpoint.to_string());
        self
    }

    pub fn with_timeout(mut self, timeout_seconds: u32) -> Self {
        self.timeout_seconds = Some(timeout_seconds);
        self
    }

    pub fn enhance_error(&self, error: RegulateAIError) -> RegulateAIError {
        match error {
            RegulateAIError::ExternalService { service: _, message, status_code, code } => {
                RegulateAIError::ExternalService {
                    service: self.service_name.clone(),
                    message: format!("{} (operation: {})", message, self.operation),
                    status_code,
                    code,
                }
            }
            RegulateAIError::Timeout { operation: _, timeout_seconds: _, code } => {
                RegulateAIError::Timeout {
                    operation: format!("{}_{}", self.service_name, self.operation),
                    timeout_seconds: self.timeout_seconds.unwrap_or(30),
                    code,
                }
            }
            RegulateAIError::Network { message, endpoint: _, code } => {
                RegulateAIError::Network {
                    message: format!("{} (service: {})", message, self.service_name),
                    endpoint: self.endpoint.clone(),
                    code,
                }
            }
            _ => error,
        }
    }
}

/// Utility functions for external service error handling
pub mod utils {
    use super::*;

    /// Check if an error is from an external service
    pub fn is_external_service_error(error: &RegulateAIError) -> bool {
        matches!(error, RegulateAIError::ExternalService { .. })
    }

    /// Check if an external service error is retryable
    pub fn is_retryable_external_error(error: &RegulateAIError) -> bool {
        match error {
            RegulateAIError::ExternalService { status_code: Some(status), .. } => {
                // Retry on 5xx errors and specific 4xx errors
                *status >= 500 || *status == 408 || *status == 429
            }
            RegulateAIError::Timeout { .. } |
            RegulateAIError::Network { .. } |
            RegulateAIError::ServiceUnavailable { .. } => true,
            _ => false,
        }
    }

    /// Get retry delay for external service errors
    pub fn get_retry_delay(error: &RegulateAIError, attempt: u32) -> Option<u32> {
        match error {
            RegulateAIError::RateLimit { retry_after: Some(delay), .. } => Some(*delay),
            RegulateAIError::ServiceUnavailable { retry_after: Some(delay), .. } => Some(*delay),
            _ if is_retryable_external_error(error) => {
                // Exponential backoff: 2^attempt seconds, max 60 seconds
                Some(std::cmp::min(2_u32.pow(attempt), 60))
            }
            _ => None,
        }
    }

    /// Extract service name from external service error
    pub fn extract_service_name(error: &RegulateAIError) -> Option<String> {
        match error {
            RegulateAIError::ExternalService { service, .. } => Some(service.clone()),
            RegulateAIError::ServiceUnavailable { service, .. } => Some(service.clone()),
            _ => None,
        }
    }

    /// Check if error indicates service is temporarily unavailable
    pub fn is_service_unavailable(error: &RegulateAIError) -> bool {
        matches!(
            error,
            RegulateAIError::ServiceUnavailable { .. } |
            RegulateAIError::Timeout { .. } |
            RegulateAIError::ExternalService { status_code: Some(503), .. }
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_external_service_context_enhance_error() {
        let context = ExternalServiceContext::new("payment_api", "process_payment")
            .with_endpoint("https://api.payment.com/v1/payments")
            .with_timeout(30);

        let original_error = RegulateAIError::ExternalService {
            service: "unknown".to_string(),
            message: "Request failed".to_string(),
            status_code: Some(500),
            code: "EXTERNAL_SERVER_ERROR".to_string(),
        };

        let enhanced_error = context.enhance_error(original_error);

        match enhanced_error {
            RegulateAIError::ExternalService { service, message, status_code, .. } => {
                assert_eq!(service, "payment_api");
                assert!(message.contains("process_payment"));
                assert_eq!(status_code, Some(500));
            }
            _ => panic!("Expected external service error"),
        }
    }

    #[test]
    fn test_is_retryable_external_error() {
        let server_error = RegulateAIError::ExternalService {
            service: "api".to_string(),
            message: "Server error".to_string(),
            status_code: Some(500),
            code: "EXTERNAL_SERVER_ERROR".to_string(),
        };
        assert!(utils::is_retryable_external_error(&server_error));

        let client_error = RegulateAIError::ExternalService {
            service: "api".to_string(),
            message: "Bad request".to_string(),
            status_code: Some(400),
            code: "EXTERNAL_CLIENT_ERROR".to_string(),
        };
        assert!(!utils::is_retryable_external_error(&client_error));

        let timeout_error = RegulateAIError::Timeout {
            operation: "api_call".to_string(),
            timeout_seconds: 30,
            code: "TIMEOUT".to_string(),
        };
        assert!(utils::is_retryable_external_error(&timeout_error));
    }

    #[test]
    fn test_get_retry_delay() {
        let rate_limit_error = RegulateAIError::RateLimit {
            message: "Rate limit exceeded".to_string(),
            limit: 100,
            window_seconds: 60,
            retry_after: Some(30),
            code: "RATE_LIMIT_EXCEEDED".to_string(),
        };
        assert_eq!(utils::get_retry_delay(&rate_limit_error, 1), Some(30));

        let server_error = RegulateAIError::ExternalService {
            service: "api".to_string(),
            message: "Server error".to_string(),
            status_code: Some(500),
            code: "EXTERNAL_SERVER_ERROR".to_string(),
        };
        assert_eq!(utils::get_retry_delay(&server_error, 1), Some(2));
        assert_eq!(utils::get_retry_delay(&server_error, 5), Some(32));
        assert_eq!(utils::get_retry_delay(&server_error, 10), Some(60)); // Max 60 seconds
    }
}
