//! Validation error handling utilities

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use validator::ValidationErrors;

use crate::types::RegulateAIError;

/// Convert validator::ValidationErrors to RegulateAIError
impl From<ValidationErrors> for RegulateAIError {
    fn from(errors: ValidationErrors) -> Self {
        let mut error_messages = Vec::new();
        let mut field_errors = HashMap::new();

        for (field, field_errors_vec) in errors.field_errors() {
            let field_messages: Vec<String> = field_errors_vec
                .iter()
                .map(|error| {
                    error
                        .message
                        .as_ref()
                        .map(|msg| msg.to_string())
                        .unwrap_or_else(|| format!("Invalid value for field '{}'", field))
                })
                .collect();

            field_errors.insert(field.to_string(), field_messages.clone());
            error_messages.extend(field_messages);
        }

        RegulateAIError::Validation {
            message: if error_messages.len() == 1 {
                error_messages[0].clone()
            } else {
                format!("Multiple validation errors: {}", error_messages.join(", "))
            },
            field: if field_errors.len() == 1 {
                field_errors.keys().next().cloned()
            } else {
                None
            },
            code: "VALIDATION_ERROR".to_string(),
        }
    }
}

/// Detailed validation error with field-specific information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetailedValidationError {
    pub message: String,
    pub field_errors: HashMap<String, Vec<String>>,
    pub code: String,
}

impl From<ValidationErrors> for DetailedValidationError {
    fn from(errors: ValidationErrors) -> Self {
        let mut field_errors = HashMap::new();
        let mut all_messages = Vec::new();

        for (field, field_errors_vec) in errors.field_errors() {
            let field_messages: Vec<String> = field_errors_vec
                .iter()
                .map(|error| {
                    error
                        .message
                        .as_ref()
                        .map(|msg| msg.to_string())
                        .unwrap_or_else(|| format!("Invalid value for field '{}'", field))
                })
                .collect();

            field_errors.insert(field.to_string(), field_messages.clone());
            all_messages.extend(field_messages);
        }

        Self {
            message: if all_messages.len() == 1 {
                all_messages[0].clone()
            } else {
                format!("Validation failed for {} field(s)", field_errors.len())
            },
            field_errors,
            code: "DETAILED_VALIDATION_ERROR".to_string(),
        }
    }
}

/// Validation error builder for custom validation logic
pub struct ValidationErrorBuilder {
    field_errors: HashMap<String, Vec<String>>,
}

impl ValidationErrorBuilder {
    pub fn new() -> Self {
        Self {
            field_errors: HashMap::new(),
        }
    }

    pub fn add_field_error(&mut self, field: &str, message: &str) -> &mut Self {
        self.field_errors
            .entry(field.to_string())
            .or_insert_with(Vec::new)
            .push(message.to_string());
        self
    }

    pub fn add_field_errors(&mut self, field: &str, messages: Vec<String>) -> &mut Self {
        self.field_errors
            .entry(field.to_string())
            .or_insert_with(Vec::new)
            .extend(messages);
        self
    }

    pub fn has_errors(&self) -> bool {
        !self.field_errors.is_empty()
    }

    pub fn build(self) -> Result<(), RegulateAIError> {
        if self.field_errors.is_empty() {
            Ok(())
        } else {
            let all_messages: Vec<String> = self
                .field_errors
                .values()
                .flat_map(|messages| messages.iter())
                .cloned()
                .collect();

            Err(RegulateAIError::Validation {
                message: if all_messages.len() == 1 {
                    all_messages[0].clone()
                } else {
                    format!("Multiple validation errors: {}", all_messages.join(", "))
                },
                field: if self.field_errors.len() == 1 {
                    self.field_errors.keys().next().cloned()
                } else {
                    None
                },
                code: "VALIDATION_ERROR".to_string(),
            })
        }
    }

    pub fn build_detailed(self) -> Result<(), DetailedValidationError> {
        if self.field_errors.is_empty() {
            Ok(())
        } else {
            Err(DetailedValidationError {
                message: format!("Validation failed for {} field(s)", self.field_errors.len()),
                field_errors: self.field_errors,
                code: "DETAILED_VALIDATION_ERROR".to_string(),
            })
        }
    }
}

impl Default for ValidationErrorBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Utility functions for common validation scenarios
pub mod validators {
    use super::*;

    /// Validate that a string is not empty or whitespace-only
    pub fn validate_not_empty(value: &str, field_name: &str) -> Result<(), RegulateAIError> {
        if value.trim().is_empty() {
            Err(RegulateAIError::Validation {
                message: format!("{} cannot be empty", field_name),
                field: Some(field_name.to_string()),
                code: "FIELD_REQUIRED".to_string(),
            })
        } else {
            Ok(())
        }
    }

    /// Validate string length
    pub fn validate_length(
        value: &str,
        field_name: &str,
        min: Option<usize>,
        max: Option<usize>,
    ) -> Result<(), RegulateAIError> {
        let len = value.len();
        
        if let Some(min_len) = min {
            if len < min_len {
                return Err(RegulateAIError::Validation {
                    message: format!("{} must be at least {} characters long", field_name, min_len),
                    field: Some(field_name.to_string()),
                    code: "FIELD_TOO_SHORT".to_string(),
                });
            }
        }

        if let Some(max_len) = max {
            if len > max_len {
                return Err(RegulateAIError::Validation {
                    message: format!("{} must not exceed {} characters", field_name, max_len),
                    field: Some(field_name.to_string()),
                    code: "FIELD_TOO_LONG".to_string(),
                });
            }
        }

        Ok(())
    }

    /// Validate numeric range
    pub fn validate_range<T>(
        value: T,
        field_name: &str,
        min: Option<T>,
        max: Option<T>,
    ) -> Result<(), RegulateAIError>
    where
        T: PartialOrd + std::fmt::Display + Copy,
    {
        if let Some(min_val) = min {
            if value < min_val {
                return Err(RegulateAIError::Validation {
                    message: format!("{} must be at least {}", field_name, min_val),
                    field: Some(field_name.to_string()),
                    code: "VALUE_TOO_LOW".to_string(),
                });
            }
        }

        if let Some(max_val) = max {
            if value > max_val {
                return Err(RegulateAIError::Validation {
                    message: format!("{} must not exceed {}", field_name, max_val),
                    field: Some(field_name.to_string()),
                    code: "VALUE_TOO_HIGH".to_string(),
                });
            }
        }

        Ok(())
    }

    /// Validate that a value is in a list of allowed values
    pub fn validate_in_list<T>(
        value: &T,
        field_name: &str,
        allowed_values: &[T],
    ) -> Result<(), RegulateAIError>
    where
        T: PartialEq + std::fmt::Display,
    {
        if allowed_values.contains(value) {
            Ok(())
        } else {
            Err(RegulateAIError::Validation {
                message: format!("{} must be one of the allowed values", field_name),
                field: Some(field_name.to_string()),
                code: "INVALID_VALUE".to_string(),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use validator::{Validate, ValidationError};

    #[derive(Debug, Validate)]
    struct TestStruct {
        #[validate(length(min = 3, max = 10))]
        name: String,
        #[validate(email)]
        email: String,
        #[validate(range(min = 18, max = 120))]
        age: u32,
    }

    #[test]
    fn test_validation_errors_conversion() {
        let test_data = TestStruct {
            name: "ab".to_string(), // Too short
            email: "invalid-email".to_string(), // Invalid format
            age: 15, // Too young
        };

        let validation_result = test_data.validate();
        assert!(validation_result.is_err());

        let validation_errors = validation_result.unwrap_err();
        let regulateai_error: RegulateAIError = validation_errors.into();

        match regulateai_error {
            RegulateAIError::Validation { message, field, code } => {
                assert!(message.contains("validation"));
                assert_eq!(code, "VALIDATION_ERROR");
                // Field should be None for multiple errors
                assert!(field.is_none());
            }
            _ => panic!("Expected validation error"),
        }
    }

    #[test]
    fn test_validation_error_builder() {
        let mut builder = ValidationErrorBuilder::new();
        builder
            .add_field_error("name", "Name is required")
            .add_field_error("email", "Invalid email format");

        assert!(builder.has_errors());

        let result = builder.build();
        assert!(result.is_err());

        match result.unwrap_err() {
            RegulateAIError::Validation { message, field, code } => {
                assert!(message.contains("Multiple validation errors"));
                assert!(field.is_none());
                assert_eq!(code, "VALIDATION_ERROR");
            }
            _ => panic!("Expected validation error"),
        }
    }

    #[test]
    fn test_validate_not_empty() {
        assert!(validators::validate_not_empty("test", "name").is_ok());
        assert!(validators::validate_not_empty("", "name").is_err());
        assert!(validators::validate_not_empty("   ", "name").is_err());
    }

    #[test]
    fn test_validate_length() {
        assert!(validators::validate_length("test", "name", Some(3), Some(10)).is_ok());
        assert!(validators::validate_length("ab", "name", Some(3), Some(10)).is_err());
        assert!(validators::validate_length("this is too long", "name", Some(3), Some(10)).is_err());
    }

    #[test]
    fn test_validate_range() {
        assert!(validators::validate_range(25, "age", Some(18), Some(65)).is_ok());
        assert!(validators::validate_range(15, "age", Some(18), Some(65)).is_err());
        assert!(validators::validate_range(70, "age", Some(18), Some(65)).is_err());
    }
}
