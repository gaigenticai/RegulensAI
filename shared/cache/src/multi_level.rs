//! Multi-Level Cache Implementation
//! 
//! Coordinates between L1 (memory), L2 (Redis), and L3 (database) cache layers
//! with intelligent cache promotion, demotion, and coherence management.

use crate::{
    l1_memory::MemoryCache,
    l2_redis::RedisCache,
    l3_database::DatabaseCache,
    serialization::CacheSerializer,
    compression::CacheCompressor,
    invalidation::{InvalidationStrategy, InvalidationEvent},
    warming::CacheWarmer,
    metrics::CacheMetrics,
    config::CacheConfig,
    errors::{CacheError, CacheResult},
    CacheLevel, CacheStats, Duration, DateTime,
};
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Multi-level cache coordinator
pub struct MultiLevelCache {
    config: CacheConfig,
    l1_cache: Option<Arc<MemoryCache>>,
    l2_cache: Option<Arc<RedisCache>>,
    l3_cache: Option<Arc<DatabaseCache>>,
    serializer: Arc<CacheSerializer>,
    compressor: Arc<CacheCompressor>,
    invalidation: Arc<InvalidationStrategy>,
    warmer: Arc<CacheWarmer>,
    metrics: Arc<CacheMetrics>,
    stats: Arc<RwLock<CacheStats>>,
}

/// Cache entry with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheEntry<T> {
    pub value: T,
    pub metadata: CacheMetadata,
}

/// Cache entry metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheMetadata {
    pub key: String,
    pub created_at: DateTime,
    pub last_accessed: DateTime,
    pub access_count: u64,
    pub ttl: Duration,
    pub size_bytes: usize,
    pub level: CacheLevel,
    pub version: u32,
    pub tags: Vec<String>,
}

/// Cache key type
pub type CacheKey = String;

/// Cache value type
pub type CacheValue = Vec<u8>;

/// Cache operation result
#[derive(Debug, Clone)]
pub struct CacheOperationResult {
    pub hit: bool,
    pub level: Option<CacheLevel>,
    pub latency_ms: u64,
    pub size_bytes: usize,
}

impl MultiLevelCache {
    /// Create a new multi-level cache
    pub async fn new(config: CacheConfig) -> CacheResult<Self> {
        let serializer = Arc::new(CacheSerializer::new(config.serialization.clone()));
        let compressor = Arc::new(CacheCompressor::new(config.compression.clone()));
        let metrics = Arc::new(CacheMetrics::new());

        // Initialize cache levels
        let l1_cache = if config.l1_enabled {
            Some(Arc::new(MemoryCache::new(config.l1_config.clone()).await?))
        } else {
            None
        };

        let l2_cache = if config.l2_enabled {
            Some(Arc::new(RedisCache::new(config.l2_config.clone()).await?))
        } else {
            None
        };

        let l3_cache = if config.l3_enabled {
            Some(Arc::new(DatabaseCache::new(config.l3_config.clone()).await?))
        } else {
            None
        };

        let invalidation = Arc::new(InvalidationStrategy::new(config.invalidation.clone()));
        let warmer = Arc::new(CacheWarmer::new(config.warming.clone()));

        Ok(Self {
            config,
            l1_cache,
            l2_cache,
            l3_cache,
            serializer,
            compressor,
            invalidation,
            warmer,
            metrics,
            stats: Arc::new(RwLock::new(CacheStats::new())),
        })
    }

    /// Get value from cache with automatic promotion
    pub async fn get<T>(&self, key: &str) -> CacheResult<Option<T>>
    where
        T: serde::de::DeserializeOwned + serde::Serialize + Clone + Send + Sync,
    {
        let start_time = std::time::Instant::now();
        let mut result = CacheOperationResult {
            hit: false,
            level: None,
            latency_ms: 0,
            size_bytes: 0,
        };

        // Try L1 cache first (fastest)
        if let Some(ref l1) = self.l1_cache {
            if let Ok(Some(entry)) = l1.get_with_metadata::<T>(key).await {
                result.hit = true;
                result.level = Some(CacheLevel::L1Memory);
                result.size_bytes = entry.metadata.size_bytes;
                
                // Update access metadata
                self.update_access_metadata(key, CacheLevel::L1Memory).await?;
                
                self.record_cache_hit(CacheLevel::L1Memory, start_time, &result).await;
                return Ok(Some(entry.value));
            }
        }

        // Try L2 cache (Redis)
        if let Some(ref l2) = self.l2_cache {
            if let Ok(Some(entry)) = l2.get_with_metadata::<T>(key).await {
                result.hit = true;
                result.level = Some(CacheLevel::L2Redis);
                result.size_bytes = entry.metadata.size_bytes;
                
                // Promote to L1 if enabled
                if let Some(ref l1) = self.l1_cache {
                    if let Err(e) = l1.set_with_metadata(key, &entry.value, &entry.metadata).await {
                        tracing::warn!("Failed to promote cache entry to L1: {}", e);
                    }
                }
                
                self.update_access_metadata(key, CacheLevel::L2Redis).await?;
                self.record_cache_hit(CacheLevel::L2Redis, start_time, &result).await;
                return Ok(Some(entry.value));
            }
        }

        // Try L3 cache (Database)
        if let Some(ref l3) = self.l3_cache {
            if let Ok(Some(entry)) = l3.get_with_metadata::<T>(key).await {
                result.hit = true;
                result.level = Some(CacheLevel::L3Database);
                result.size_bytes = entry.metadata.size_bytes;
                
                // Promote to higher levels
                if let Some(ref l2) = self.l2_cache {
                    if let Err(e) = l2.set_with_metadata(key, &entry.value, &entry.metadata).await {
                        tracing::warn!("Failed to promote cache entry to L2: {}", e);
                    }
                }
                
                if let Some(ref l1) = self.l1_cache {
                    if let Err(e) = l1.set_with_metadata(key, &entry.value, &entry.metadata).await {
                        tracing::warn!("Failed to promote cache entry to L1: {}", e);
                    }
                }
                
                self.update_access_metadata(key, CacheLevel::L3Database).await?;
                self.record_cache_hit(CacheLevel::L3Database, start_time, &result).await;
                return Ok(Some(entry.value));
            }
        }

        // Cache miss
        self.record_cache_miss(start_time).await;
        Ok(None)
    }

    /// Set value in cache with write-through to all levels
    pub async fn set<T>(&self, key: &str, value: &T, ttl: Duration) -> CacheResult<()>
    where
        T: serde::Serialize + Clone + Send + Sync,
    {
        let start_time = std::time::Instant::now();
        
        // Create cache metadata
        let metadata = CacheMetadata {
            key: key.to_string(),
            created_at: chrono::Utc::now(),
            last_accessed: chrono::Utc::now(),
            access_count: 0,
            ttl,
            size_bytes: self.calculate_size(value)?,
            level: CacheLevel::L1Memory, // Will be updated per level
            version: 1,
            tags: Vec::new(),
        };

        // Check if value should be cached based on size
        if metadata.size_bytes > self.config.max_entry_size {
            return Err(CacheError::EntryTooLarge {
                size: metadata.size_bytes,
                max_size: self.config.max_entry_size,
            });
        }

        let mut errors = Vec::new();

        // Set in L1 cache
        if let Some(ref l1) = self.l1_cache {
            let mut l1_metadata = metadata.clone();
            l1_metadata.level = CacheLevel::L1Memory;
            
            if let Err(e) = l1.set_with_metadata(key, value, &l1_metadata).await {
                errors.push(format!("L1: {}", e));
            }
        }

        // Set in L2 cache
        if let Some(ref l2) = self.l2_cache {
            let mut l2_metadata = metadata.clone();
            l2_metadata.level = CacheLevel::L2Redis;
            
            if let Err(e) = l2.set_with_metadata(key, value, &l2_metadata).await {
                errors.push(format!("L2: {}", e));
            }
        }

        // Set in L3 cache
        if let Some(ref l3) = self.l3_cache {
            let mut l3_metadata = metadata.clone();
            l3_metadata.level = CacheLevel::L3Database;
            
            if let Err(e) = l3.set_with_metadata(key, value, &l3_metadata).await {
                errors.push(format!("L3: {}", e));
            }
        }

        // Record metrics
        self.record_cache_set(start_time, metadata.size_bytes).await;

        // Trigger invalidation events if needed
        let invalidation_event = InvalidationEvent {
            key: key.to_string(),
            operation: crate::CacheOperation::Set,
            timestamp: chrono::Utc::now(),
            metadata: Some(metadata),
        };
        
        if let Err(e) = self.invalidation.handle_event(invalidation_event).await {
            tracing::warn!("Failed to handle invalidation event: {}", e);
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(CacheError::MultipleErrors(errors))
        }
    }

    /// Delete value from all cache levels
    pub async fn delete(&self, key: &str) -> CacheResult<bool> {
        let start_time = std::time::Instant::now();
        let mut deleted = false;

        // Delete from all levels
        if let Some(ref l1) = self.l1_cache {
            if l1.delete(key).await.unwrap_or(false) {
                deleted = true;
            }
        }

        if let Some(ref l2) = self.l2_cache {
            if l2.delete(key).await.unwrap_or(false) {
                deleted = true;
            }
        }

        if let Some(ref l3) = self.l3_cache {
            if l3.delete(key).await.unwrap_or(false) {
                deleted = true;
            }
        }

        // Record metrics
        if deleted {
            self.record_cache_delete(start_time).await;
        }

        // Trigger invalidation event
        let invalidation_event = InvalidationEvent {
            key: key.to_string(),
            operation: crate::CacheOperation::Delete,
            timestamp: chrono::Utc::now(),
            metadata: None,
        };
        
        if let Err(e) = self.invalidation.handle_event(invalidation_event).await {
            tracing::warn!("Failed to handle invalidation event: {}", e);
        }

        Ok(deleted)
    }

    /// Invalidate cache entries by pattern
    pub async fn invalidate_pattern(&self, pattern: &str) -> CacheResult<u64> {
        let mut total_invalidated = 0;

        if let Some(ref l1) = self.l1_cache {
            total_invalidated += l1.invalidate_pattern(pattern).await.unwrap_or(0);
        }

        if let Some(ref l2) = self.l2_cache {
            total_invalidated += l2.invalidate_pattern(pattern).await.unwrap_or(0);
        }

        if let Some(ref l3) = self.l3_cache {
            total_invalidated += l3.invalidate_pattern(pattern).await.unwrap_or(0);
        }

        Ok(total_invalidated)
    }

    /// Warm cache with preloaded data
    pub async fn warm_cache(&self, keys: Vec<String>) -> CacheResult<u64> {
        self.warmer.warm_cache(self, keys).await
    }

    /// Get cache statistics
    pub async fn get_stats(&self) -> CacheStats {
        let mut stats = self.stats.read().await.clone();
        stats.calculate_hit_ratio();
        stats
    }

    /// Get detailed cache information
    pub async fn get_cache_info(&self) -> CacheResult<CacheInfo> {
        let mut info = CacheInfo {
            levels: Vec::new(),
            total_size: 0,
            total_entries: 0,
            hit_ratio: 0.0,
        };

        if let Some(ref l1) = self.l1_cache {
            let l1_info = l1.get_info().await?;
            info.levels.push(CacheLevelInfo {
                level: CacheLevel::L1Memory,
                size: l1_info.size,
                entries: l1_info.entries,
                hit_ratio: l1_info.hit_ratio,
                enabled: true,
            });
            info.total_size += l1_info.size;
            info.total_entries += l1_info.entries;
        }

        if let Some(ref l2) = self.l2_cache {
            let l2_info = l2.get_info().await?;
            info.levels.push(CacheLevelInfo {
                level: CacheLevel::L2Redis,
                size: l2_info.size,
                entries: l2_info.entries,
                hit_ratio: l2_info.hit_ratio,
                enabled: true,
            });
            info.total_size += l2_info.size;
            info.total_entries += l2_info.entries;
        }

        if let Some(ref l3) = self.l3_cache {
            let l3_info = l3.get_info().await?;
            info.levels.push(CacheLevelInfo {
                level: CacheLevel::L3Database,
                size: l3_info.size,
                entries: l3_info.entries,
                hit_ratio: l3_info.hit_ratio,
                enabled: true,
            });
            info.total_size += l3_info.size;
            info.total_entries += l3_info.entries;
        }

        let stats = self.get_stats().await;
        info.hit_ratio = stats.hit_ratio;

        Ok(info)
    }

    /// Clear all cache levels
    pub async fn clear(&self) -> CacheResult<()> {
        let mut errors = Vec::new();

        if let Some(ref l1) = self.l1_cache {
            if let Err(e) = l1.clear().await {
                errors.push(format!("L1: {}", e));
            }
        }

        if let Some(ref l2) = self.l2_cache {
            if let Err(e) = l2.clear().await {
                errors.push(format!("L2: {}", e));
            }
        }

        if let Some(ref l3) = self.l3_cache {
            if let Err(e) = l3.clear().await {
                errors.push(format!("L3: {}", e));
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(CacheError::MultipleErrors(errors))
        }
    }

    // Private helper methods

    async fn update_access_metadata(&self, key: &str, level: CacheLevel) -> CacheResult<()> {
        // Update access count and last accessed time
        // This would be implemented based on the specific cache level
        Ok(())
    }

    async fn record_cache_hit(&self, level: CacheLevel, start_time: std::time::Instant, result: &CacheOperationResult) {
        let latency = start_time.elapsed().as_millis() as u64;
        
        let mut stats = self.stats.write().await;
        stats.hits += 1;
        
        self.metrics.record_cache_hit(level, latency, result.size_bytes).await;
    }

    async fn record_cache_miss(&self, start_time: std::time::Instant) {
        let latency = start_time.elapsed().as_millis() as u64;
        
        let mut stats = self.stats.write().await;
        stats.misses += 1;
        
        self.metrics.record_cache_miss(latency).await;
    }

    async fn record_cache_set(&self, start_time: std::time::Instant, size_bytes: usize) {
        let latency = start_time.elapsed().as_millis() as u64;
        
        let mut stats = self.stats.write().await;
        stats.sets += 1;
        
        self.metrics.record_cache_set(latency, size_bytes).await;
    }

    async fn record_cache_delete(&self, start_time: std::time::Instant) {
        let latency = start_time.elapsed().as_millis() as u64;
        
        let mut stats = self.stats.write().await;
        stats.deletes += 1;
        
        self.metrics.record_cache_delete(latency).await;
    }

    fn calculate_size<T>(&self, value: &T) -> CacheResult<usize>
    where
        T: serde::Serialize,
    {
        bincode::serialized_size(value)
            .map(|size| size as usize)
            .map_err(|e| CacheError::Serialization(e.to_string()))
    }
}

/// Cache information structure
#[derive(Debug, Clone, Serialize)]
pub struct CacheInfo {
    pub levels: Vec<CacheLevelInfo>,
    pub total_size: usize,
    pub total_entries: usize,
    pub hit_ratio: f64,
}

/// Cache level information
#[derive(Debug, Clone, Serialize)]
pub struct CacheLevelInfo {
    pub level: CacheLevel,
    pub size: usize,
    pub entries: usize,
    pub hit_ratio: f64,
    pub enabled: bool,
}

impl<T> CacheEntry<T> {
    pub fn new(value: T, key: String, ttl: Duration) -> Self {
        Self {
            value,
            metadata: CacheMetadata {
                key,
                created_at: chrono::Utc::now(),
                last_accessed: chrono::Utc::now(),
                access_count: 0,
                ttl,
                size_bytes: 0, // Will be calculated
                level: CacheLevel::L1Memory,
                version: 1,
                tags: Vec::new(),
            },
        }
    }

    pub fn is_expired(&self) -> bool {
        let now = chrono::Utc::now();
        let expires_at = self.metadata.created_at + self.metadata.ttl;
        now > expires_at
    }

    pub fn update_access(&mut self) {
        self.metadata.last_accessed = chrono::Utc::now();
        self.metadata.access_count += 1;
    }
}
