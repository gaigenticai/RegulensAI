//! L3 Database Cache Implementation

use crate::{
    multi_level::{CacheEntry, CacheMetadata},
    errors::{CacheError, CacheResult},
    CacheLevel, Duration,
};
use sqlx::{PgPool, Row};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

/// L3 Database cache implementation
pub struct DatabaseCache {
    pool: PgPool,
    config: DatabaseCacheConfig,
    stats: Arc<RwLock<DatabaseCacheStats>>,
}

/// Database cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseCacheConfig {
    pub database_url: String,
    pub table_name: String,
    pub max_connections: u32,
    pub cleanup_interval_hours: u64,
    pub max_entry_size_bytes: usize,
}

/// Database cache statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseCacheStats {
    pub hits: u64,
    pub misses: u64,
    pub sets: u64,
    pub deletes: u64,
    pub errors: u64,
    pub hit_ratio: f64,
}

/// Database cache information
#[derive(Debug, Clone, Serialize)]
pub struct DatabaseCacheInfo {
    pub size: usize,
    pub entries: usize,
    pub hit_ratio: f64,
    pub total_size_bytes: usize,
}

impl DatabaseCache {
    /// Create a new database cache
    pub async fn new(config: DatabaseCacheConfig) -> CacheResult<Self> {
        let pool = PgPool::connect(&config.database_url)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        // Start of table structure
        let create_table_sql = format!(
            r#"
            -- L3 Database Cache Table Structure
            -- This table stores cache entries with metadata for the L3 cache layer
            CREATE TABLE IF NOT EXISTS {} (
                -- Primary key for cache entries
                key VARCHAR(255) PRIMARY KEY,
                -- Serialized cache value data (binary format)
                value BYTEA NOT NULL,
                -- Cache metadata in JSON format (TTL, access patterns, etc.)
                metadata JSONB NOT NULL,
                -- Timestamp when the cache entry was created
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Timestamp when the cache entry expires
                expires_at TIMESTAMPTZ NOT NULL,
                -- Timestamp when the cache entry was last accessed
                last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Number of times this cache entry has been accessed
                access_count BIGINT NOT NULL DEFAULT 0,
                -- Size of the cache entry in bytes
                size_bytes INTEGER NOT NULL DEFAULT 0
            );

            -- Index for efficient cleanup of expired entries
            CREATE INDEX IF NOT EXISTS idx_{}_expires_at ON {} (expires_at);
            -- Index for LRU eviction based on last access time
            CREATE INDEX IF NOT EXISTS idx_{}_last_accessed ON {} (last_accessed);
            -- Index for cache size monitoring and management
            CREATE INDEX IF NOT EXISTS idx_{}_size_bytes ON {} (size_bytes);
            -- Composite index for cache statistics queries
            CREATE INDEX IF NOT EXISTS idx_{}_stats ON {} (created_at, expires_at, access_count);
            "#,
            config.table_name,
            config.table_name,
            config.table_name,
            config.table_name,
            config.table_name,
            config.table_name,
            config.table_name,
            config.table_name,
            config.table_name
        );
        // End of table structure

        sqlx::query(&create_table_sql)
            .execute(&pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        let cache = Self {
            pool,
            config,
            stats: Arc::new(RwLock::new(DatabaseCacheStats::default())),
        };

        // Start cleanup task
        cache.start_cleanup_task().await;

        Ok(cache)
    }

    /// Get value with metadata
    pub async fn get_with_metadata<T>(&self, key: &str) -> CacheResult<Option<CacheEntry<T>>>
    where
        T: serde::de::DeserializeOwned,
    {
        let query = format!(
            "SELECT value, metadata FROM {} WHERE key = $1 AND expires_at > NOW()",
            self.config.table_name
        );

        let row = sqlx::query(&query)
            .bind(key)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        if let Some(row) = row {
            let value_bytes: Vec<u8> = row.get("value");
            let metadata_json: serde_json::Value = row.get("metadata");

            let metadata: CacheMetadata = serde_json::from_value(metadata_json)
                .map_err(|e| CacheError::Serialization(e.to_string()))?;

            let value: T = bincode::deserialize(&value_bytes)
                .map_err(|e| CacheError::Serialization(e.to_string()))?;

            // Update access metadata
            self.update_access_metadata(key).await?;

            self.record_hit().await;

            Ok(Some(CacheEntry { value, metadata }))
        } else {
            self.record_miss().await;
            Ok(None)
        }
    }

    /// Set value with metadata
    pub async fn set_with_metadata<T>(&self, key: &str, value: &T, metadata: &CacheMetadata) -> CacheResult<()>
    where
        T: serde::Serialize,
    {
        let value_bytes = bincode::serialize(value)
            .map_err(|e| CacheError::Serialization(e.to_string()))?;

        if value_bytes.len() > self.config.max_entry_size_bytes {
            return Err(CacheError::EntryTooLarge {
                size: value_bytes.len(),
                max_size: self.config.max_entry_size_bytes,
            });
        }

        let mut entry_metadata = metadata.clone();
        entry_metadata.level = CacheLevel::L3Database;
        entry_metadata.size_bytes = value_bytes.len();

        let metadata_json = serde_json::to_value(&entry_metadata)
            .map_err(|e| CacheError::Serialization(e.to_string()))?;

        let expires_at = metadata.created_at + metadata.ttl;

        let query = format!(
            r#"
            INSERT INTO {} (key, value, metadata, expires_at, size_bytes)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                metadata = EXCLUDED.metadata,
                expires_at = EXCLUDED.expires_at,
                size_bytes = EXCLUDED.size_bytes,
                last_accessed = NOW()
            "#,
            self.config.table_name
        );

        sqlx::query(&query)
            .bind(key)
            .bind(&value_bytes)
            .bind(&metadata_json)
            .bind(expires_at)
            .bind(value_bytes.len() as i32)
            .execute(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        self.record_set().await;
        Ok(())
    }

    /// Get value (simplified interface)
    pub async fn get<T>(&self, key: &str) -> CacheResult<Option<T>>
    where
        T: serde::de::DeserializeOwned,
    {
        if let Some(entry) = self.get_with_metadata::<T>(key).await? {
            Ok(Some(entry.value))
        } else {
            Ok(None)
        }
    }

    /// Set value (simplified interface)
    pub async fn set<T>(&self, key: &str, value: &T, ttl: Duration) -> CacheResult<()>
    where
        T: serde::Serialize,
    {
        let metadata = CacheMetadata {
            key: key.to_string(),
            created_at: chrono::Utc::now(),
            last_accessed: chrono::Utc::now(),
            access_count: 0,
            ttl,
            size_bytes: 0,
            level: CacheLevel::L3Database,
            version: 1,
            tags: Vec::new(),
        };

        self.set_with_metadata(key, value, &metadata).await
    }

    /// Delete value
    pub async fn delete(&self, key: &str) -> CacheResult<bool> {
        let query = format!("DELETE FROM {} WHERE key = $1", self.config.table_name);

        let result = sqlx::query(&query)
            .bind(key)
            .execute(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        let deleted = result.rows_affected() > 0;
        
        if deleted {
            self.record_delete().await;
        }

        Ok(deleted)
    }

    /// Check if key exists
    pub async fn exists(&self, key: &str) -> CacheResult<bool> {
        let query = format!(
            "SELECT 1 FROM {} WHERE key = $1 AND expires_at > NOW() LIMIT 1",
            self.config.table_name
        );

        let exists = sqlx::query(&query)
            .bind(key)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?
            .is_some();

        Ok(exists)
    }

    /// Clear all entries
    pub async fn clear(&self) -> CacheResult<()> {
        let query = format!("DELETE FROM {}", self.config.table_name);

        sqlx::query(&query)
            .execute(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        Ok(())
    }

    /// Get cache size
    pub async fn size(&self) -> CacheResult<usize> {
        let query = format!(
            "SELECT COUNT(*) as count FROM {} WHERE expires_at > NOW()",
            self.config.table_name
        );

        let row = sqlx::query(&query)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        let count: i64 = row.get("count");
        Ok(count as usize)
    }

    /// Get keys matching pattern
    pub async fn keys(&self, pattern: &str) -> CacheResult<Vec<String>> {
        let sql_pattern = pattern.replace('*', '%');
        let query = format!(
            "SELECT key FROM {} WHERE key LIKE $1 AND expires_at > NOW()",
            self.config.table_name
        );

        let rows = sqlx::query(&query)
            .bind(&sql_pattern)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        let keys = rows
            .into_iter()
            .map(|row| row.get::<String, _>("key"))
            .collect();

        Ok(keys)
    }

    /// Invalidate entries matching pattern
    pub async fn invalidate_pattern(&self, pattern: &str) -> CacheResult<u64> {
        let sql_pattern = pattern.replace('*', '%');
        let query = format!(
            "DELETE FROM {} WHERE key LIKE $1",
            self.config.table_name
        );

        let result = sqlx::query(&query)
            .bind(&sql_pattern)
            .execute(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        Ok(result.rows_affected())
    }

    /// Get cache information
    pub async fn get_info(&self) -> CacheResult<DatabaseCacheInfo> {
        let stats = self.stats.read().await;
        let size = self.size().await?;
        
        let query = format!(
            "SELECT COALESCE(SUM(size_bytes), 0) as total_size FROM {} WHERE expires_at > NOW()",
            self.config.table_name
        );

        let row = sqlx::query(&query)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        let total_size_bytes: i64 = row.get("total_size");

        Ok(DatabaseCacheInfo {
            size: 0, // Database size would need specific queries
            entries: size,
            hit_ratio: stats.hit_ratio,
            total_size_bytes: total_size_bytes as usize,
        })
    }

    /// Get cache statistics
    pub async fn get_stats(&self) -> DatabaseCacheStats {
        let mut stats = self.stats.read().await.clone();
        
        // Calculate hit ratio
        let total = stats.hits + stats.misses;
        stats.hit_ratio = if total > 0 {
            stats.hits as f64 / total as f64
        } else {
            0.0
        };
        
        stats
    }

    /// Clean up expired entries
    pub async fn cleanup_expired(&self) -> CacheResult<u64> {
        let query = format!("DELETE FROM {} WHERE expires_at <= NOW()", self.config.table_name);

        let result = sqlx::query(&query)
            .execute(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        Ok(result.rows_affected())
    }

    // Private helper methods

    async fn update_access_metadata(&self, key: &str) -> CacheResult<()> {
        let query = format!(
            "UPDATE {} SET last_accessed = NOW(), access_count = access_count + 1 WHERE key = $1",
            self.config.table_name
        );

        sqlx::query(&query)
            .bind(key)
            .execute(&self.pool)
            .await
            .map_err(|e| CacheError::Database(e.to_string()))?;

        Ok(())
    }

    async fn start_cleanup_task(&self) {
        let pool = self.pool.clone();
        let table_name = self.config.table_name.clone();
        let cleanup_interval = self.config.cleanup_interval_hours;

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(
                std::time::Duration::from_secs(cleanup_interval * 3600)
            );

            loop {
                interval.tick().await;
                
                let query = format!("DELETE FROM {} WHERE expires_at <= NOW()", table_name);
                
                if let Err(e) = sqlx::query(&query).execute(&pool).await {
                    tracing::error!("Failed to cleanup expired cache entries: {}", e);
                }
            }
        });
    }

    async fn record_hit(&self) {
        let mut stats = self.stats.write().await;
        stats.hits += 1;
    }

    async fn record_miss(&self) {
        let mut stats = self.stats.write().await;
        stats.misses += 1;
    }

    async fn record_set(&self) {
        let mut stats = self.stats.write().await;
        stats.sets += 1;
    }

    async fn record_delete(&self) {
        let mut stats = self.stats.write().await;
        stats.deletes += 1;
    }
}

impl Default for DatabaseCacheConfig {
    fn default() -> Self {
        Self {
            database_url: "postgresql://localhost:5432/regulateai_cache".to_string(),
            table_name: "cache_entries".to_string(),
            max_connections: 10,
            cleanup_interval_hours: 1,
            max_entry_size_bytes: 1024 * 1024, // 1MB
        }
    }
}

impl Default for DatabaseCacheStats {
    fn default() -> Self {
        Self {
            hits: 0,
            misses: 0,
            sets: 0,
            deletes: 0,
            errors: 0,
            hit_ratio: 0.0,
        }
    }
}

// Implement async trait for Cache
#[async_trait::async_trait]
impl crate::Cache for DatabaseCache {
    type Error = CacheError;

    async fn get<T>(&self, key: &str) -> Result<Option<T>, Self::Error>
    where
        T: serde::de::DeserializeOwned + Send,
    {
        self.get(key).await
    }

    async fn set<T>(&self, key: &str, value: &T, ttl: Duration) -> Result<(), Self::Error>
    where
        T: serde::Serialize + Send + Sync,
    {
        self.set(key, value, ttl).await
    }

    async fn delete(&self, key: &str) -> Result<bool, Self::Error> {
        self.delete(key).await
    }

    async fn exists(&self, key: &str) -> Result<bool, Self::Error> {
        self.exists(key).await
    }

    async fn clear(&self) -> Result<(), Self::Error> {
        self.clear().await
    }

    async fn size(&self) -> Result<usize, Self::Error> {
        self.size().await
    }

    async fn keys(&self, pattern: &str) -> Result<Vec<String>, Self::Error> {
        self.keys(pattern).await
    }
}
