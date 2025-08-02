//! Database error handling utilities

use crate::types::RegulateAIError;

/// Convert SQLx errors to RegulateAIError
impl From<sqlx::Error> for RegulateAIError {
    fn from(error: sqlx::Error) -> Self {
        match error {
            sqlx::Error::RowNotFound => RegulateAIError::NotFound {
                resource_type: "Record".to_string(),
                resource_id: "unknown".to_string(),
                code: "DATABASE_RECORD_NOT_FOUND".to_string(),
            },
            sqlx::Error::Database(db_error) => {
                // Handle specific database constraint violations
                if let Some(constraint) = db_error.constraint() {
                    match constraint {
                        name if name.contains("unique") || name.contains("pk") => {
                            RegulateAIError::AlreadyExists {
                                resource_type: "Record".to_string(),
                                identifier: constraint.to_string(),
                                code: "DATABASE_UNIQUE_VIOLATION".to_string(),
                            }
                        }
                        name if name.contains("fk") || name.contains("foreign") => {
                            RegulateAIError::DataIntegrity {
                                message: "Foreign key constraint violation".to_string(),
                                constraint: Some(constraint.to_string()),
                                code: "DATABASE_FOREIGN_KEY_VIOLATION".to_string(),
                            }
                        }
                        name if name.contains("check") => {
                            RegulateAIError::DataIntegrity {
                                message: "Check constraint violation".to_string(),
                                constraint: Some(constraint.to_string()),
                                code: "DATABASE_CHECK_VIOLATION".to_string(),
                            }
                        }
                        _ => RegulateAIError::DataIntegrity {
                            message: db_error.message().to_string(),
                            constraint: Some(constraint.to_string()),
                            code: "DATABASE_CONSTRAINT_VIOLATION".to_string(),
                        },
                    }
                } else {
                    RegulateAIError::Database {
                        message: db_error.message().to_string(),
                        operation: "database_operation".to_string(),
                        code: "DATABASE_ERROR".to_string(),
                    }
                }
            }
            sqlx::Error::PoolTimedOut => RegulateAIError::Timeout {
                operation: "database_connection".to_string(),
                timeout_seconds: 30,
                code: "DATABASE_POOL_TIMEOUT".to_string(),
            },
            sqlx::Error::PoolClosed => RegulateAIError::ServiceUnavailable {
                service: "database".to_string(),
                message: "Database connection pool is closed".to_string(),
                retry_after: Some(60),
                code: "DATABASE_POOL_CLOSED".to_string(),
            },
            sqlx::Error::Io(io_error) => RegulateAIError::Network {
                message: format!("Database I/O error: {}", io_error),
                endpoint: None,
                code: "DATABASE_IO_ERROR".to_string(),
            },
            sqlx::Error::Tls(tls_error) => RegulateAIError::Network {
                message: format!("Database TLS error: {}", tls_error),
                endpoint: None,
                code: "DATABASE_TLS_ERROR".to_string(),
            },
            sqlx::Error::Protocol(protocol_error) => RegulateAIError::Database {
                message: format!("Database protocol error: {}", protocol_error),
                operation: "database_communication".to_string(),
                code: "DATABASE_PROTOCOL_ERROR".to_string(),
            },
            sqlx::Error::TypeNotFound { type_name } => RegulateAIError::Configuration {
                message: format!("Database type not found: {}", type_name),
                key: Some("database_type".to_string()),
                code: "DATABASE_TYPE_NOT_FOUND".to_string(),
            },
            sqlx::Error::ColumnNotFound(column_name) => RegulateAIError::Configuration {
                message: format!("Database column not found: {}", column_name),
                key: Some("database_column".to_string()),
                code: "DATABASE_COLUMN_NOT_FOUND".to_string(),
            },
            sqlx::Error::ColumnIndexOutOfBounds { index, len } => RegulateAIError::Internal {
                message: format!("Column index {} out of bounds (length: {})", index, len),
                source: Some("database_query".to_string()),
                code: "DATABASE_COLUMN_INDEX_ERROR".to_string(),
            },
            sqlx::Error::Decode(decode_error) => RegulateAIError::Serialization {
                message: format!("Database decode error: {}", decode_error),
                format: "database".to_string(),
                code: "DATABASE_DECODE_ERROR".to_string(),
            },
            sqlx::Error::Migrate(migrate_error) => RegulateAIError::Database {
                message: format!("Database migration error: {}", migrate_error),
                operation: "database_migration".to_string(),
                code: "DATABASE_MIGRATION_ERROR".to_string(),
            },
            _ => RegulateAIError::Database {
                message: error.to_string(),
                operation: "unknown_database_operation".to_string(),
                code: "DATABASE_UNKNOWN_ERROR".to_string(),
            },
        }
    }
}

/// Convert SeaORM errors to RegulateAIError
impl From<sea_orm::DbErr> for RegulateAIError {
    fn from(error: sea_orm::DbErr) -> Self {
        match error {
            sea_orm::DbErr::RecordNotFound(message) => RegulateAIError::NotFound {
                resource_type: "Record".to_string(),
                resource_id: message,
                code: "ORM_RECORD_NOT_FOUND".to_string(),
            },
            sea_orm::DbErr::Custom(message) => RegulateAIError::Database {
                message,
                operation: "orm_operation".to_string(),
                code: "ORM_CUSTOM_ERROR".to_string(),
            },
            sea_orm::DbErr::Type(message) => RegulateAIError::Serialization {
                message,
                format: "orm".to_string(),
                code: "ORM_TYPE_ERROR".to_string(),
            },
            sea_orm::DbErr::Json(message) => RegulateAIError::Serialization {
                message,
                format: "json".to_string(),
                code: "ORM_JSON_ERROR".to_string(),
            },
            sea_orm::DbErr::Migration(message) => RegulateAIError::Database {
                message,
                operation: "orm_migration".to_string(),
                code: "ORM_MIGRATION_ERROR".to_string(),
            },
            sea_orm::DbErr::Conn(conn_error) => RegulateAIError::Database {
                message: conn_error.to_string(),
                operation: "orm_connection".to_string(),
                code: "ORM_CONNECTION_ERROR".to_string(),
            },
            sea_orm::DbErr::Exec(exec_error) => RegulateAIError::Database {
                message: exec_error.to_string(),
                operation: "orm_execution".to_string(),
                code: "ORM_EXECUTION_ERROR".to_string(),
            },
            sea_orm::DbErr::Query(query_error) => RegulateAIError::Database {
                message: query_error.to_string(),
                operation: "orm_query".to_string(),
                code: "ORM_QUERY_ERROR".to_string(),
            },
            sea_orm::DbErr::ConvertFromU64(message) => RegulateAIError::Serialization {
                message,
                format: "u64_conversion".to_string(),
                code: "ORM_U64_CONVERSION_ERROR".to_string(),
            },
            sea_orm::DbErr::UnpackInsertId => RegulateAIError::Database {
                message: "Failed to unpack insert ID".to_string(),
                operation: "orm_insert".to_string(),
                code: "ORM_INSERT_ID_ERROR".to_string(),
            },
            sea_orm::DbErr::UpdateGetPrimaryKey => RegulateAIError::Database {
                message: "Failed to get primary key for update".to_string(),
                operation: "orm_update".to_string(),
                code: "ORM_UPDATE_PRIMARY_KEY_ERROR".to_string(),
            },
            sea_orm::DbErr::RecordNotUpdated => RegulateAIError::NotFound {
                resource_type: "Record".to_string(),
                resource_id: "update_target".to_string(),
                code: "ORM_RECORD_NOT_UPDATED".to_string(),
            },
            sea_orm::DbErr::RecordNotInserted => RegulateAIError::Database {
                message: "Record was not inserted".to_string(),
                operation: "orm_insert".to_string(),
                code: "ORM_RECORD_NOT_INSERTED".to_string(),
            },
            sea_orm::DbErr::TryIntoErr { from, into, source } => RegulateAIError::Serialization {
                message: format!("Type conversion error from {} to {}: {}", from, into, source),
                format: "type_conversion".to_string(),
                code: "ORM_TYPE_CONVERSION_ERROR".to_string(),
            },
        }
    }
}

/// Database operation context for better error reporting
pub struct DatabaseContext {
    pub table: String,
    pub operation: String,
    pub entity_id: Option<String>,
}

impl DatabaseContext {
    pub fn new(table: &str, operation: &str) -> Self {
        Self {
            table: table.to_string(),
            operation: operation.to_string(),
            entity_id: None,
        }
    }

    pub fn with_entity_id(mut self, entity_id: &str) -> Self {
        self.entity_id = Some(entity_id.to_string());
        self
    }

    pub fn enhance_error(&self, error: RegulateAIError) -> RegulateAIError {
        match error {
            RegulateAIError::NotFound { resource_type: _, resource_id, code } => {
                RegulateAIError::NotFound {
                    resource_type: self.table.clone(),
                    resource_id: self.entity_id.clone().unwrap_or(resource_id),
                    code,
                }
            }
            RegulateAIError::Database { message, operation: _, code } => {
                RegulateAIError::Database {
                    message: format!("{} (table: {}, operation: {})", message, self.table, self.operation),
                    operation: format!("{}_{}", self.table, self.operation),
                    code,
                }
            }
            _ => error,
        }
    }
}

/// Utility functions for database error handling
pub mod utils {
    use super::*;

    /// Check if an error is a unique constraint violation
    pub fn is_unique_violation(error: &RegulateAIError) -> bool {
        matches!(
            error,
            RegulateAIError::AlreadyExists { .. } |
            RegulateAIError::DataIntegrity { code, .. } if code.contains("UNIQUE")
        )
    }

    /// Check if an error is a foreign key constraint violation
    pub fn is_foreign_key_violation(error: &RegulateAIError) -> bool {
        matches!(
            error,
            RegulateAIError::DataIntegrity { code, .. } if code.contains("FOREIGN_KEY")
        )
    }

    /// Check if an error is retryable (connection issues, timeouts, etc.)
    pub fn is_retryable_db_error(error: &RegulateAIError) -> bool {
        matches!(
            error,
            RegulateAIError::Timeout { .. } |
            RegulateAIError::ServiceUnavailable { .. } |
            RegulateAIError::Network { .. } |
            RegulateAIError::Database { code, .. } if code.contains("POOL") || code.contains("CONNECTION")
        )
    }

    /// Extract table name from database error context
    pub fn extract_table_name(error: &RegulateAIError) -> Option<String> {
        match error {
            RegulateAIError::Database { operation, .. } => {
                operation.split('_').next().map(|s| s.to_string())
            }
            RegulateAIError::NotFound { resource_type, .. } => Some(resource_type.clone()),
            RegulateAIError::AlreadyExists { resource_type, .. } => Some(resource_type.clone()),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_database_context_enhance_error() {
        let context = DatabaseContext::new("users", "select").with_entity_id("123");
        
        let original_error = RegulateAIError::NotFound {
            resource_type: "Record".to_string(),
            resource_id: "unknown".to_string(),
            code: "DATABASE_RECORD_NOT_FOUND".to_string(),
        };

        let enhanced_error = context.enhance_error(original_error);

        match enhanced_error {
            RegulateAIError::NotFound { resource_type, resource_id, .. } => {
                assert_eq!(resource_type, "users");
                assert_eq!(resource_id, "123");
            }
            _ => panic!("Expected not found error"),
        }
    }

    #[test]
    fn test_is_unique_violation() {
        let unique_error = RegulateAIError::AlreadyExists {
            resource_type: "User".to_string(),
            identifier: "email".to_string(),
            code: "DATABASE_UNIQUE_VIOLATION".to_string(),
        };
        assert!(utils::is_unique_violation(&unique_error));

        let other_error = RegulateAIError::NotFound {
            resource_type: "User".to_string(),
            resource_id: "123".to_string(),
            code: "NOT_FOUND".to_string(),
        };
        assert!(!utils::is_unique_violation(&other_error));
    }

    #[test]
    fn test_is_retryable_db_error() {
        let timeout_error = RegulateAIError::Timeout {
            operation: "database_query".to_string(),
            timeout_seconds: 30,
            code: "DATABASE_POOL_TIMEOUT".to_string(),
        };
        assert!(utils::is_retryable_db_error(&timeout_error));

        let validation_error = RegulateAIError::Validation {
            message: "Invalid input".to_string(),
            field: None,
            code: "VALIDATION_ERROR".to_string(),
        };
        assert!(!utils::is_retryable_db_error(&validation_error));
    }
}
