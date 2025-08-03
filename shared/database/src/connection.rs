//! Database connection management

use sea_orm::{Database, DatabaseConnection, DbErr};
use sqlx::{Pool, Postgres};
use std::time::Duration;
use tracing::{info, warn};

use regulateai_config::DatabaseConfig;
use regulateai_errors::RegulateAIError;

/// Database connection manager
pub struct DatabaseManager {
    config: DatabaseConfig,
    connection: Option<DatabaseConnection>,
    pool: Option<Pool<Postgres>>,
}

impl DatabaseManager {
    /// Create a new database manager
    pub fn new(config: DatabaseConfig) -> Self {
        Self {
            config,
            connection: None,
            pool: None,
        }
    }

    /// Establish database connection
    pub async fn connect(&mut self) -> Result<(), RegulateAIError> {
        info!("Connecting to database: {}", self.config.masked_url());

        // Validate configuration
        self.config.validate_config()
            .map_err(|e| RegulateAIError::Configuration {
                message: e,
                key: Some("database".to_string()),
                code: "DATABASE_CONFIG_INVALID".to_string(),
            })?;

        // Create SeaORM connection
        let mut opt = sea_orm::ConnectOptions::new(&self.config.url);
        opt.max_connections(self.config.max_connections)
            .min_connections(self.config.min_connections)
            .acquire_timeout(self.config.acquire_timeout_duration())
            .idle_timeout(self.config.idle_timeout_duration())
            .sqlx_logging(self.config.log_queries);

        if let Some(max_lifetime) = self.config.max_lifetime_duration() {
            opt.max_lifetime(max_lifetime);
        }

        let connection = Database::connect(opt).await?;
        
        // Test the connection
        self.test_connection(&connection).await?;
        
        self.connection = Some(connection);
        
        info!("Database connection established successfully");
        Ok(())
    }

    /// Get the database connection
    pub fn connection(&self) -> Result<&DatabaseConnection, RegulateAIError> {
        self.connection.as_ref().ok_or_else(|| RegulateAIError::Database {
            message: "Database connection not established".to_string(),
            operation: "get_connection".to_string(),
            code: "DATABASE_NOT_CONNECTED".to_string(),
        })
    }

    /// Test database connection
    async fn test_connection(&self, conn: &DatabaseConnection) -> Result<(), RegulateAIError> {
        use sea_orm::Statement;
        
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            "SELECT 1".to_string(),
        )).await;

        match result {
            Ok(_) => {
                info!("Database connection test successful");
                Ok(())
            }
            Err(e) => {
                warn!("Database connection test failed: {}", e);
                Err(RegulateAIError::Database {
                    message: format!("Connection test failed: {}", e),
                    operation: "connection_test".to_string(),
                    code: "DATABASE_CONNECTION_TEST_FAILED".to_string(),
                })
            }
        }
    }

    /// Check database health
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        let conn = self.connection()?;
        self.test_connection(conn).await.map(|_| true)
    }

    /// Close database connection
    pub async fn close(&mut self) -> Result<(), RegulateAIError> {
        if let Some(connection) = self.connection.take() {
            connection.close().await?;
            info!("Database connection closed");
        }
        Ok(())
    }

    /// Run database migrations
    pub async fn migrate(&self) -> Result<(), RegulateAIError> {
        let conn = self.connection()?;
        
        info!("Running database migrations");

        // Integrate with SeaORM migrations system
        use sea_orm::{Statement, DbErr};

        // Create migrations table if it doesn't exist
        let create_migrations_table = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            r#"
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            "#.to_string(),
        )).await;

        match create_migrations_table {
            Ok(_) => info!("Migrations table ready"),
            Err(e) => {
                error!("Failed to create migrations table: {}", e);
                return Err(RegulateAIError::DatabaseError {
                    message: format!("Failed to create migrations table: {}", e),
                    source: Some(Box::new(e)),
                });
            }
        }

        // Check which migrations have been applied
        let applied_migrations = conn.query_all(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            "SELECT version FROM schema_migrations ORDER BY version".to_string(),
        )).await.map_err(|e| RegulateAIError::DatabaseError {
            message: format!("Failed to query applied migrations: {}", e),
            source: Some(Box::new(e)),
        })?;

        let applied_versions: std::collections::HashSet<String> = applied_migrations
            .into_iter()
            .map(|row| row.try_get("", "version").unwrap_or_default())
            .collect();

        // List of available migrations (in production, this would be read from files)
        let available_migrations = vec![
            "001_initial_schema",
            "002_risk_fraud_cyber_ai_schema",
        ];

        // Apply pending migrations
        for migration in available_migrations {
            if !applied_versions.contains(migration) {
                info!("Applying migration: {}", migration);

                // Read migration file and execute
                let migration_path = format!("migrations/{}.sql", migration);
                if let Ok(migration_sql) = std::fs::read_to_string(&migration_path) {
                    match conn.execute(Statement::from_string(
                        sea_orm::DatabaseBackend::Postgres,
                        migration_sql,
                    )).await {
                        Ok(_) => {
                            // Record successful migration
                            conn.execute(Statement::from_string(
                                sea_orm::DatabaseBackend::Postgres,
                                format!("INSERT INTO schema_migrations (version) VALUES ('{}')", migration),
                            )).await.map_err(|e| RegulateAIError::DatabaseError {
                                message: format!("Failed to record migration: {}", e),
                                source: Some(Box::new(e)),
                            })?;
                            info!("Migration {} applied successfully", migration);
                        },
                        Err(e) => {
                            error!("Failed to apply migration {}: {}", migration, e);
                            return Err(RegulateAIError::DatabaseError {
                                message: format!("Failed to apply migration {}: {}", migration, e),
                                source: Some(Box::new(e)),
                            });
                        }
                    }
                } else {
                    warn!("Migration file not found: {}", migration_path);
                }
            }
        }

        if check_migrations.is_err() {
            info!("Creating schema_migrations table");
            conn.execute(Statement::from_string(
                sea_orm::DatabaseBackend::Postgres,
                "CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW())".to_string(),
            )).await?;
        }

        info!("Database migrations completed successfully");
        Ok(())
    }

    /// Get database statistics
    pub async fn get_stats(&self) -> Result<DatabaseStats, RegulateAIError> {
        let conn = self.connection()?;
        
        use sea_orm::{FromQueryResult, Statement};
        
        #[derive(FromQueryResult)]
        struct StatsResult {
            active_connections: i64,
            total_connections: i64,
            database_size: i64,
        }

        let stats = StatsResult::find_by_statement(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            r#"
            SELECT 
                (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                (SELECT count(*) FROM pg_stat_activity) as total_connections,
                (SELECT pg_database_size(current_database())) as database_size
            "#.to_string(),
        ))
        .one(conn)
        .await?
        .ok_or_else(|| RegulateAIError::Database {
            message: "Failed to retrieve database statistics".to_string(),
            operation: "get_stats".to_string(),
            code: "DATABASE_STATS_FAILED".to_string(),
        })?;

        Ok(DatabaseStats {
            active_connections: stats.active_connections as u32,
            total_connections: stats.total_connections as u32,
            database_size_bytes: stats.database_size as u64,
            pool_size: self.config.max_connections,
            pool_available: self.config.max_connections - stats.active_connections as u32,
        })
    }
}

/// Database statistics
#[derive(Debug, Clone)]
pub struct DatabaseStats {
    pub active_connections: u32,
    pub total_connections: u32,
    pub database_size_bytes: u64,
    pub pool_size: u32,
    pub pool_available: u32,
}

impl DatabaseStats {
    /// Get database size in MB
    pub fn database_size_mb(&self) -> f64 {
        self.database_size_bytes as f64 / (1024.0 * 1024.0)
    }

    /// Get connection pool utilization percentage
    pub fn pool_utilization_percent(&self) -> f64 {
        if self.pool_size == 0 {
            0.0
        } else {
            (self.active_connections as f64 / self.pool_size as f64) * 100.0
        }
    }
}

/// Create a database connection with the given configuration
pub async fn create_connection(config: &DatabaseConfig) -> Result<DatabaseConnection, RegulateAIError> {
    let mut manager = DatabaseManager::new(config.clone());
    manager.connect().await?;
    Ok(manager.connection()?.clone())
}

/// Create a test database connection
pub async fn create_test_connection() -> Result<DatabaseConnection, RegulateAIError> {
    let config = DatabaseConfig::test_config();
    create_connection(&config).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_database_manager_creation() {
        let config = DatabaseConfig::test_config();
        let manager = DatabaseManager::new(config);
        
        // Should not be connected initially
        assert!(manager.connection().is_err());
    }

    #[test]
    fn test_database_stats() {
        let stats = DatabaseStats {
            active_connections: 5,
            total_connections: 10,
            database_size_bytes: 1024 * 1024 * 100, // 100 MB
            pool_size: 20,
            pool_available: 15,
        };

        assert_eq!(stats.database_size_mb(), 100.0);
        assert_eq!(stats.pool_utilization_percent(), 25.0);
    }
}
