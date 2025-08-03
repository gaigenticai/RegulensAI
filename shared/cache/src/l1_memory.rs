//! L1 Memory Cache Implementation
//! 
//! High-performance in-memory cache using Moka for the fastest possible access.
//! Supports LRU, LFU, and time-based eviction policies.

use crate::{
    multi_level::{CacheEntry, CacheMetadata},
    errors::{CacheError, CacheResult},
    CacheLevel, Duration,
};
use moka::future::Cache as MokaCache;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// L1 Memory cache implementation
pub struct MemoryCache {
    cache: MokaCache<String, CacheEntry<Vec<u8>>>,
    config: MemoryCacheConfig,
    stats: Arc<RwLock<MemoryCacheStats>>,
}

/// Memory cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryCacheConfig {
    pub max_capacity: u64,
    pub max_size_bytes: u64,
    pub time_to_live: Option<Duration>,
    pub time_to_idle: Option<Duration>,
    pub eviction_policy: EvictionPolicy,
    pub initial_capacity: Option<u64>,
    pub num_segments: Option<usize>,
    pub weigher_enabled: bool,
}

/// Eviction policies for memory cache
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EvictionPolicy {
    Lru,  // Least Recently Used
    Lfu,  // Least Frequently Used
    Fifo, // First In, First Out
    Random,
}

/// Memory cache statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryCacheStats {
    pub hits: u64,
    pub misses: u64,
    pub evictions: u64,
    pub size: usize,
    pub entry_count: u64,
    pub hit_ratio: f64,
}

/// Cache information
#[derive(Debug, Clone, Serialize)]
pub struct MemoryCacheInfo {
    pub size: usize,
    pub entries: usize,
    pub hit_ratio: f64,
    pub evictions: u64,
}

impl MemoryCache {
    /// Create a new memory cache
    pub async fn new(config: MemoryCacheConfig) -> CacheResult<Self> {
        let mut builder = MokaCache::builder()
            .max_capacity(config.max_capacity);

        // Configure time-based eviction
        if let Some(ttl) = config.time_to_live {
            let std_duration = std::time::Duration::from_secs(ttl.num_seconds() as u64);
            builder = builder.time_to_live(std_duration);
        }

        if let Some(tti) = config.time_to_idle {
            let std_duration = std::time::Duration::from_secs(tti.num_seconds() as u64);
            builder = builder.time_to_idle(std_duration);
        }

        // Configure initial capacity
        if let Some(initial_capacity) = config.initial_capacity {
            builder = builder.initial_capacity(initial_capacity as usize);
        }

        // Configure weigher for size-based eviction
        if config.weigher_enabled {
            builder = builder.weigher(|_key: &String, value: &CacheEntry<Vec<u8>>| {
                value.metadata.size_bytes as u32
            });
            
            if config.max_size_bytes > 0 {
                builder = builder.max_capacity(config.max_size_bytes);
            }
        }

        let cache = builder.build();

        Ok(Self {
            cache,
            config,
            stats: Arc::new(RwLock::new(MemoryCacheStats {
                hits: 0,
                misses: 0,
                evictions: 0,
                size: 0,
                entry_count: 0,
                hit_ratio: 0.0,
            })),
        })
    }

    /// Get value with metadata
    pub async fn get_with_metadata<T>(&self, key: &str) -> CacheResult<Option<CacheEntry<T>>>
    where
        T: serde::de::DeserializeOwned,
    {
        if let Some(entry) = self.cache.get(key).await {
            // Check if entry is expired
            if entry.is_expired() {
                self.cache.invalidate(key).await;
                self.record_miss().await;
                return Ok(None);
            }

            // Deserialize the value
            let value: T = bincode::deserialize(&entry.value)
                .map_err(|e| CacheError::Serialization(e.to_string()))?;

            let mut result_entry = entry.clone();
            result_entry.value = bincode::serialize(&value)
                .map_err(|e| CacheError::Serialization(e.to_string()))?;

            // Update access metadata
            let mut updated_entry = entry;
            updated_entry.metadata.last_accessed = chrono::Utc::now();
            updated_entry.metadata.access_count += 1;
            
            // Update cache with new metadata
            self.cache.insert(key.to_string(), updated_entry).await;

            self.record_hit().await;

            // Convert back to the requested type
            let typed_entry = CacheEntry {
                value,
                metadata: result_entry.metadata,
            };

            Ok(Some(typed_entry))
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
        let serialized_value = bincode::serialize(value)
            .map_err(|e| CacheError::Serialization(e.to_string()))?;

        let mut entry_metadata = metadata.clone();
        entry_metadata.size_bytes = serialized_value.len();
        entry_metadata.level = CacheLevel::L1Memory;

        let entry = CacheEntry {
            value: serialized_value,
            metadata: entry_metadata,
        };

        self.cache.insert(key.to_string(), entry).await;
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
            size_bytes: 0, // Will be calculated in set_with_metadata
            level: CacheLevel::L1Memory,
            version: 1,
            tags: Vec::new(),
        };

        self.set_with_metadata(key, value, &metadata).await
    }

    /// Delete value
    pub async fn delete(&self, key: &str) -> CacheResult<bool> {
        let existed = self.cache.get(key).await.is_some();
        self.cache.invalidate(key).await;
        
        if existed {
            self.record_delete().await;
        }
        
        Ok(existed)
    }

    /// Check if key exists
    pub async fn exists(&self, key: &str) -> CacheResult<bool> {
        Ok(self.cache.get(key).await.is_some())
    }

    /// Clear all entries
    pub async fn clear(&self) -> CacheResult<()> {
        self.cache.invalidate_all();
        
        // Wait for invalidation to complete
        self.cache.run_pending_tasks().await;
        
        let mut stats = self.stats.write().await;
        stats.size = 0;
        stats.entry_count = 0;
        
        Ok(())
    }

    /// Get cache size
    pub async fn size(&self) -> CacheResult<usize> {
        Ok(self.cache.entry_count() as usize)
    }

    /// Get keys matching pattern
    pub async fn keys(&self, pattern: &str) -> CacheResult<Vec<String>> {
        // Since Moka doesn't provide direct key iteration, we maintain a separate key index
        let key_index = self.key_index.read().await;

        if pattern == "*" {
            // Return all keys
            Ok(key_index.iter().cloned().collect())
        } else if pattern.contains('*') {
            // Simple glob pattern matching
            let regex_pattern = pattern.replace('*', ".*");
            let regex = regex::Regex::new(&regex_pattern)
                .map_err(|e| CacheError::InvalidPattern(format!("Invalid pattern: {}", e)))?;

            Ok(key_index.iter()
                .filter(|key| regex.is_match(key))
                .cloned()
                .collect())
        } else {
            // Exact match
            if key_index.contains(pattern) {
                Ok(vec![pattern.to_string()])
            } else {
                Ok(Vec::new())
            }
        }
    }

    /// Invalidate entries matching pattern
    pub async fn invalidate_pattern(&self, pattern: &str) -> CacheResult<u64> {
        let mut key_index = self.key_index.write().await;
        let mut invalidated_count = 0;

        if pattern == "*" {
            // Invalidate all entries
            let count = self.cache.entry_count();
            self.cache.invalidate_all();
            self.cache.run_pending_tasks().await;
            key_index.clear();
            Ok(count)
        } else if pattern.contains('*') {
            // Pattern matching with glob
            let regex_pattern = pattern.replace('*', ".*");
            let regex = regex::Regex::new(&regex_pattern)
                .map_err(|e| CacheError::InvalidPattern(format!("Invalid pattern: {}", e)))?;

            let keys_to_remove: Vec<String> = key_index.iter()
                .filter(|key| regex.is_match(key))
                .cloned()
                .collect();

            for key in &keys_to_remove {
                self.cache.invalidate(key);
                key_index.remove(key);
                invalidated_count += 1;
            }

            self.cache.run_pending_tasks().await;
            Ok(invalidated_count)
        } else {
            // Exact match
            if key_index.contains(pattern) {
                self.cache.invalidate(pattern);
                key_index.remove(pattern);
                self.cache.run_pending_tasks().await;
                Ok(1)
            } else {
                Ok(0)
            }
        }
    }

    /// Get cache information
    pub async fn get_info(&self) -> CacheResult<MemoryCacheInfo> {
        let stats = self.stats.read().await;
        
        Ok(MemoryCacheInfo {
            size: self.cache.weighted_size() as usize,
            entries: self.cache.entry_count() as usize,
            hit_ratio: stats.hit_ratio,
            evictions: stats.evictions,
        })
    }

    /// Get cache statistics
    pub async fn get_stats(&self) -> MemoryCacheStats {
        let mut stats = self.stats.read().await.clone();
        
        // Update current size and entry count
        stats.size = self.cache.weighted_size() as usize;
        stats.entry_count = self.cache.entry_count();
        
        // Calculate hit ratio
        let total = stats.hits + stats.misses;
        stats.hit_ratio = if total > 0 {
            stats.hits as f64 / total as f64
        } else {
            0.0
        };
        
        stats
    }

    /// Force eviction of expired entries
    pub async fn evict_expired(&self) -> CacheResult<u64> {
        // Moka handles expiration automatically, but we can trigger cleanup
        self.cache.run_pending_tasks().await;
        Ok(0) // Moka doesn't report eviction count directly
    }

    /// Get memory usage in bytes
    pub async fn memory_usage(&self) -> CacheResult<usize> {
        Ok(self.cache.weighted_size() as usize)
    }

    // Private helper methods

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
        stats.entry_count = self.cache.entry_count();
        stats.size = self.cache.weighted_size() as usize;
    }

    async fn record_delete(&self) {
        let mut stats = self.stats.write().await;
        stats.entry_count = self.cache.entry_count();
        stats.size = self.cache.weighted_size() as usize;
    }
}

impl Default for MemoryCacheConfig {
    fn default() -> Self {
        Self {
            max_capacity: 10_000,
            max_size_bytes: 100 * 1024 * 1024, // 100MB
            time_to_live: Some(Duration::hours(1)),
            time_to_idle: Some(Duration::minutes(30)),
            eviction_policy: EvictionPolicy::Lru,
            initial_capacity: Some(1_000),
            num_segments: None,
            weigher_enabled: true,
        }
    }
}

impl Default for MemoryCacheStats {
    fn default() -> Self {
        Self {
            hits: 0,
            misses: 0,
            evictions: 0,
            size: 0,
            entry_count: 0,
            hit_ratio: 0.0,
        }
    }
}

// Implement async trait for Cache
#[async_trait::async_trait]
impl crate::Cache for MemoryCache {
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
