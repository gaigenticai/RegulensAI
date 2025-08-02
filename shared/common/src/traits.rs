//! Common traits used across RegulateAI services

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fmt::Debug;
use uuid::Uuid;

use crate::types::{AuditInfo, PaginatedResponse, PaginationParams};

/// Trait for entities that can be audited
pub trait Auditable {
    fn audit_info(&self) -> &AuditInfo;
    fn audit_info_mut(&mut self) -> &mut AuditInfo;
    
    fn created_at(&self) -> DateTime<Utc> {
        self.audit_info().created_at
    }
    
    fn created_by(&self) -> Uuid {
        self.audit_info().created_by
    }
    
    fn updated_at(&self) -> Option<DateTime<Utc>> {
        self.audit_info().updated_at
    }
    
    fn updated_by(&self) -> Option<Uuid> {
        self.audit_info().updated_by
    }
    
    fn version(&self) -> u32 {
        self.audit_info().version
    }
    
    fn mark_updated(&mut self, user_id: Uuid) {
        self.audit_info_mut().update(user_id);
    }
}

/// Trait for entities that have a unique identifier
pub trait Identifiable {
    fn id(&self) -> Uuid;
}

/// Trait for entities that can be validated
pub trait Validatable {
    type Error;
    
    fn validate(&self) -> Result<(), Self::Error>;
}

/// Trait for entities that can be serialized to/from JSON
pub trait JsonSerializable: Serialize + for<'de> Deserialize<'de> {}
impl<T> JsonSerializable for T where T: Serialize + for<'de> Deserialize<'de> {}

/// Repository trait for CRUD operations
#[async_trait]
pub trait Repository<T, ID = Uuid>
where
    T: Send + Sync,
    ID: Send + Sync,
{
    type Error: Send + Sync + Debug;

    /// Create a new entity
    async fn create(&self, entity: T) -> Result<T, Self::Error>;

    /// Find entity by ID
    async fn find_by_id(&self, id: ID) -> Result<Option<T>, Self::Error>;

    /// Update an existing entity
    async fn update(&self, entity: T) -> Result<T, Self::Error>;

    /// Delete entity by ID
    async fn delete(&self, id: ID) -> Result<bool, Self::Error>;

    /// Find all entities with pagination
    async fn find_all(&self, params: PaginationParams) -> Result<PaginatedResponse<T>, Self::Error>;

    /// Count total entities
    async fn count(&self) -> Result<u64, Self::Error>;
}

/// Service trait for business logic operations
#[async_trait]
pub trait Service<T, ID = Uuid>
where
    T: Send + Sync,
    ID: Send + Sync,
{
    type Error: Send + Sync + Debug;
    type CreateRequest: Send + Sync;
    type UpdateRequest: Send + Sync;

    /// Create a new entity
    async fn create(&self, request: Self::CreateRequest) -> Result<T, Self::Error>;

    /// Get entity by ID
    async fn get_by_id(&self, id: ID) -> Result<T, Self::Error>;

    /// Update an existing entity
    async fn update(&self, id: ID, request: Self::UpdateRequest) -> Result<T, Self::Error>;

    /// Delete entity by ID
    async fn delete(&self, id: ID) -> Result<(), Self::Error>;

    /// List entities with pagination
    async fn list(&self, params: PaginationParams) -> Result<PaginatedResponse<T>, Self::Error>;
}

/// Event handler trait for processing domain events
#[async_trait]
pub trait EventHandler<E>
where
    E: Send + Sync,
{
    type Error: Send + Sync + Debug;

    /// Handle a domain event
    async fn handle(&self, event: E) -> Result<(), Self::Error>;
}

/// Cache trait for caching operations
#[async_trait]
pub trait Cache<K, V>
where
    K: Send + Sync,
    V: Send + Sync,
{
    type Error: Send + Sync + Debug;

    /// Get value by key
    async fn get(&self, key: &K) -> Result<Option<V>, Self::Error>;

    /// Set key-value pair with optional TTL
    async fn set(&self, key: K, value: V, ttl: Option<u64>) -> Result<(), Self::Error>;

    /// Delete key
    async fn delete(&self, key: &K) -> Result<bool, Self::Error>;

    /// Check if key exists
    async fn exists(&self, key: &K) -> Result<bool, Self::Error>;

    /// Clear all cached data
    async fn clear(&self) -> Result<(), Self::Error>;
}

/// Health check trait for services
#[async_trait]
pub trait HealthCheck {
    type Error: Send + Sync + Debug;

    /// Check if the service is healthy
    async fn health_check(&self) -> Result<bool, Self::Error>;

    /// Get detailed health status
    async fn detailed_health(&self) -> Result<crate::types::HealthStatus, Self::Error>;
}

/// Configuration trait for services
pub trait Configurable {
    type Config;

    /// Get the current configuration
    fn config(&self) -> &Self::Config;

    /// Update configuration
    fn update_config(&mut self, config: Self::Config);
}

/// Metrics collection trait
pub trait MetricsCollector {
    /// Increment a counter metric
    fn increment_counter(&self, name: &str, labels: &[(&str, &str)]);

    /// Record a histogram value
    fn record_histogram(&self, name: &str, value: f64, labels: &[(&str, &str)]);

    /// Set a gauge value
    fn set_gauge(&self, name: &str, value: f64, labels: &[(&str, &str)]);
}

/// Logging trait for structured logging
pub trait Logger {
    /// Log an info message
    fn info(&self, message: &str, fields: &[(&str, &dyn std::fmt::Display)]);

    /// Log a warning message
    fn warn(&self, message: &str, fields: &[(&str, &dyn std::fmt::Display)]);

    /// Log an error message
    fn error(&self, message: &str, fields: &[(&str, &dyn std::fmt::Display)]);

    /// Log a debug message
    fn debug(&self, message: &str, fields: &[(&str, &dyn std::fmt::Display)]);
}
