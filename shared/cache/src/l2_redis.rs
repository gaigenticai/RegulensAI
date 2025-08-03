//! L2 Redis Cache Implementation

use crate::{
    multi_level::{CacheEntry, CacheMetadata},
    errors::{CacheError, CacheResult},
    CacheLevel, Duration,
};
use redis::{AsyncCommands, Client, Connection};
use deadpool_redis::{Config, Pool, Runtime};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

/// L2 Redis cache implementation
pub struct RedisCache {
    pool: Pool,
    config: RedisCacheConfig,
    stats: Arc<RwLock<RedisCacheStats>>,
}

/// Redis cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisCacheConfig {
    pub url: String,
    pub max_connections: usize,
    pub connection_timeout: Duration,
    pub key_prefix: String,
    pub compression_enabled: bool,
    pub serialization_format: SerializationFormat,
}

/// Serialization formats
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SerializationFormat {
    Json,
    Bincode,
    MessagePack,
}

/// Redis cache statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedisCacheStats {
    pub hits: u64,
    pub misses: u64,
    pub sets: u64,
    pub deletes: u64,
    pub errors: u64,
    pub hit_ratio: f64,
}

/// Redis cache information
#[derive(Debug, Clone, Serialize)]
pub struct RedisCacheInfo {
    pub size: usize,
    pub entries: usize,
    pub hit_ratio: f64,
    pub memory_usage: usize,
}

impl RedisCache {
    /// Create a new Redis cache
    pub async fn new(config: RedisCacheConfig) -> CacheResult<Self> {
        let redis_config = Config::from_url(&config.url);
        let pool = redis_config
            .create_pool(Some(Runtime::Tokio1))
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        // Test connection
        let mut conn = pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;
        
        let _: String = conn
            .ping()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        Ok(Self {
            pool,
            config,
            stats: Arc::new(RwLock::new(RedisCacheStats::default())),
        })
    }

    /// Get value with metadata
    pub async fn get_with_metadata<T>(&self, key: &str) -> CacheResult<Option<CacheEntry<T>>>
    where
        T: serde::de::DeserializeOwned,
    {
        let prefixed_key = self.prefixed_key(key);
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let result: Option<Vec<u8>> = conn
            .get(&prefixed_key)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

        if let Some(data) = result {
            match self.deserialize_entry::<T>(&data) {
                Ok(entry) => {
                    if entry.is_expired() {
                        // Remove expired entry
                        let _: () = conn
                            .del(&prefixed_key)
                            .await
                            .map_err(|e| CacheError::Redis(e.to_string()))?;
                        
                        self.record_miss().await;
                        Ok(None)
                    } else {
                        self.record_hit().await;
                        Ok(Some(entry))
                    }
                }
                Err(e) => {
                    self.record_error().await;
                    Err(e)
                }
            }
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
        let prefixed_key = self.prefixed_key(key);
        
        let mut entry_metadata = metadata.clone();
        entry_metadata.level = CacheLevel::L2Redis;

        let entry = CacheEntry {
            value: value,
            metadata: entry_metadata,
        };

        let serialized_data = self.serialize_entry(&entry)?;
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let ttl_seconds = metadata.ttl.num_seconds() as u64;
        
        let _: () = conn
            .setex(&prefixed_key, ttl_seconds, &serialized_data)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

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
            level: CacheLevel::L2Redis,
            version: 1,
            tags: Vec::new(),
        };

        self.set_with_metadata(key, value, &metadata).await
    }

    /// Delete value
    pub async fn delete(&self, key: &str) -> CacheResult<bool> {
        let prefixed_key = self.prefixed_key(key);
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let deleted: u64 = conn
            .del(&prefixed_key)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

        if deleted > 0 {
            self.record_delete().await;
        }

        Ok(deleted > 0)
    }

    /// Check if key exists
    pub async fn exists(&self, key: &str) -> CacheResult<bool> {
        let prefixed_key = self.prefixed_key(key);
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let exists: bool = conn
            .exists(&prefixed_key)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

        Ok(exists)
    }

    /// Clear all entries with prefix
    pub async fn clear(&self) -> CacheResult<()> {
        let pattern = format!("{}*", self.config.key_prefix);
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let keys: Vec<String> = conn
            .keys(&pattern)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

        if !keys.is_empty() {
            let _: () = conn
                .del(&keys)
                .await
                .map_err(|e| CacheError::Redis(e.to_string()))?;
        }

        Ok(())
    }

    /// Get cache size
    pub async fn size(&self) -> CacheResult<usize> {
        let pattern = format!("{}*", self.config.key_prefix);
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let keys: Vec<String> = conn
            .keys(&pattern)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

        Ok(keys.len())
    }

    /// Get keys matching pattern
    pub async fn keys(&self, pattern: &str) -> CacheResult<Vec<String>> {
        let prefixed_pattern = format!("{}{}", self.config.key_prefix, pattern);
        
        let mut conn = self.pool
            .get()
            .await
            .map_err(|e| CacheError::Connection(e.to_string()))?;

        let keys: Vec<String> = conn
            .keys(&prefixed_pattern)
            .await
            .map_err(|e| CacheError::Redis(e.to_string()))?;

        // Remove prefix from keys
        let unprefixed_keys = keys
            .into_iter()
            .filter_map(|key| key.strip_prefix(&self.config.key_prefix).map(|s| s.to_string()))
            .collect();

        Ok(unprefixed_keys)
    }

    /// Invalidate entries matching pattern
    pub async fn invalidate_pattern(&self, pattern: &str) -> CacheResult<u64> {
        let keys = self.keys(pattern).await?;
        let mut total_deleted = 0;

        if !keys.is_empty() {
            let prefixed_keys: Vec<String> = keys
                .iter()
                .map(|key| self.prefixed_key(key))
                .collect();

            let mut conn = self.pool
                .get()
                .await
                .map_err(|e| CacheError::Connection(e.to_string()))?;

            let deleted: u64 = conn
                .del(&prefixed_keys)
                .await
                .map_err(|e| CacheError::Redis(e.to_string()))?;

            total_deleted = deleted;
        }

        Ok(total_deleted)
    }

    /// Get cache information
    pub async fn get_info(&self) -> CacheResult<RedisCacheInfo> {
        let stats = self.stats.read().await;
        let size = self.size().await?;
        
        Ok(RedisCacheInfo {
            size: 0, // Would need Redis MEMORY USAGE command
            entries: size,
            hit_ratio: stats.hit_ratio,
            memory_usage: 0, // Would need Redis INFO memory
        })
    }

    /// Get cache statistics
    pub async fn get_stats(&self) -> RedisCacheStats {
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

    // Private helper methods

    fn prefixed_key(&self, key: &str) -> String {
        format!("{}{}", self.config.key_prefix, key)
    }

    fn serialize_entry<T>(&self, entry: &CacheEntry<T>) -> CacheResult<Vec<u8>>
    where
        T: serde::Serialize,
    {
        match self.config.serialization_format {
            SerializationFormat::Json => {
                serde_json::to_vec(entry)
                    .map_err(|e| CacheError::Serialization(e.to_string()))
            }
            SerializationFormat::Bincode => {
                bincode::serialize(entry)
                    .map_err(|e| CacheError::Serialization(e.to_string()))
            }
            SerializationFormat::MessagePack => {
                rmp_serde::to_vec(entry)
                    .map_err(|e| CacheError::Serialization(e.to_string()))
            }
        }
    }

    fn deserialize_entry<T>(&self, data: &[u8]) -> CacheResult<CacheEntry<T>>
    where
        T: serde::de::DeserializeOwned,
    {
        match self.config.serialization_format {
            SerializationFormat::Json => {
                serde_json::from_slice(data)
                    .map_err(|e| CacheError::Serialization(e.to_string()))
            }
            SerializationFormat::Bincode => {
                bincode::deserialize(data)
                    .map_err(|e| CacheError::Serialization(e.to_string()))
            }
            SerializationFormat::MessagePack => {
                rmp_serde::from_slice(data)
                    .map_err(|e| CacheError::Serialization(e.to_string()))
            }
        }
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

    async fn record_error(&self) {
        let mut stats = self.stats.write().await;
        stats.errors += 1;
    }
}

impl Default for RedisCacheConfig {
    fn default() -> Self {
        Self {
            url: "redis://localhost:6379".to_string(),
            max_connections: 10,
            connection_timeout: Duration::seconds(5),
            key_prefix: "regulateai:cache:".to_string(),
            compression_enabled: true,
            serialization_format: SerializationFormat::Bincode,
        }
    }
}

impl Default for RedisCacheStats {
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
impl crate::Cache for RedisCache {
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
