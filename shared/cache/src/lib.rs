//! RegulateAI Multi-Level Caching System
//! 
//! Provides a sophisticated caching architecture with:
//! - L1 Cache: In-memory caching with Moka (fastest access)
//! - L2 Cache: Redis distributed caching (shared across instances)
//! - L3 Cache: Database-backed persistent caching (slowest but most reliable)
//! 
//! Features:
//! - Automatic cache warming and preloading
//! - Intelligent cache invalidation
//! - Cache coherence across distributed systems
//! - Compression and serialization optimization
//! - Comprehensive metrics and monitoring
//! - Cache-aside, write-through, and write-behind patterns

pub mod multi_level;
pub mod l1_memory;
pub mod l2_redis;
pub mod l3_database;
pub mod serialization;
pub mod compression;
pub mod invalidation;
pub mod warming;
pub mod metrics;
pub mod config;
pub mod errors;
pub mod strategies;
pub mod coherence;

pub use multi_level::{MultiLevelCache, CacheEntry, CacheKey, CacheValue};
pub use l1_memory::{MemoryCache, MemoryCacheConfig};
pub use l2_redis::{RedisCache, RedisCacheConfig};
pub use l3_database::{DatabaseCache, DatabaseCacheConfig};
pub use serialization::{CacheSerializer, SerializationFormat};
pub use compression::{CacheCompressor, CompressionAlgorithm};
pub use invalidation::{InvalidationStrategy, InvalidationEvent};
pub use warming::{CacheWarmer, WarmingStrategy};
pub use metrics::CacheMetrics;
pub use config::CacheConfig;
pub use errors::{CacheError, CacheResult};
pub use strategies::{CacheStrategy, EvictionPolicy};
pub use coherence::{CacheCoherence, CoherenceProtocol};

/// Cache operation types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CacheOperation {
    Get,
    Set,
    Delete,
    Invalidate,
    Warm,
    Evict,
}

/// Cache level enumeration
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CacheLevel {
    L1Memory,
    L2Redis,
    L3Database,
}

/// Cache statistics
#[derive(Debug, Clone, serde::Serialize)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub sets: u64,
    pub deletes: u64,
    pub evictions: u64,
    pub size: usize,
    pub hit_ratio: f64,
}

impl CacheStats {
    pub fn new() -> Self {
        Self {
            hits: 0,
            misses: 0,
            sets: 0,
            deletes: 0,
            evictions: 0,
            size: 0,
            hit_ratio: 0.0,
        }
    }

    pub fn calculate_hit_ratio(&mut self) {
        let total = self.hits + self.misses;
        self.hit_ratio = if total > 0 {
            self.hits as f64 / total as f64
        } else {
            0.0
        };
    }
}

/// Cache configuration builder
pub struct CacheConfigBuilder {
    config: CacheConfig,
}

impl CacheConfigBuilder {
    pub fn new() -> Self {
        Self {
            config: CacheConfig::default(),
        }
    }

    pub fn with_l1_enabled(mut self, enabled: bool) -> Self {
        self.config.l1_enabled = enabled;
        self
    }

    pub fn with_l2_enabled(mut self, enabled: bool) -> Self {
        self.config.l2_enabled = enabled;
        self
    }

    pub fn with_l3_enabled(mut self, enabled: bool) -> Self {
        self.config.l3_enabled = enabled;
        self
    }

    pub fn with_compression(mut self, enabled: bool) -> Self {
        self.config.compression_enabled = enabled;
        self
    }

    pub fn with_metrics(mut self, enabled: bool) -> Self {
        self.config.metrics_enabled = enabled;
        self
    }

    pub fn build(self) -> CacheConfig {
        self.config
    }
}

impl Default for CacheConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Cache factory for creating cache instances
pub struct CacheFactory;

impl CacheFactory {
    /// Create a new multi-level cache instance
    pub async fn create_multi_level_cache(config: CacheConfig) -> CacheResult<MultiLevelCache> {
        MultiLevelCache::new(config).await
    }

    /// Create a memory-only cache
    pub async fn create_memory_cache(config: MemoryCacheConfig) -> CacheResult<MemoryCache> {
        MemoryCache::new(config).await
    }

    /// Create a Redis-only cache
    pub async fn create_redis_cache(config: RedisCacheConfig) -> CacheResult<RedisCache> {
        RedisCache::new(config).await
    }

    /// Create a database-only cache
    pub async fn create_database_cache(config: DatabaseCacheConfig) -> CacheResult<DatabaseCache> {
        DatabaseCache::new(config).await
    }
}

/// Cache utilities
pub mod utils {
    use super::*;
    use blake3::Hasher;

    /// Generate a cache key hash
    pub fn hash_key(key: &str) -> String {
        let mut hasher = Hasher::new();
        hasher.update(key.as_bytes());
        hex::encode(hasher.finalize().as_bytes())
    }

    /// Calculate cache entry size
    pub fn calculate_entry_size<T>(value: &T) -> usize 
    where
        T: serde::Serialize,
    {
        bincode::serialized_size(value).unwrap_or(0) as usize
    }

    /// Check if a value should be cached based on size
    pub fn should_cache_by_size(size: usize, max_size: usize) -> bool {
        size <= max_size
    }

    /// Generate cache key with namespace
    pub fn namespaced_key(namespace: &str, key: &str) -> String {
        format!("{}:{}", namespace, key)
    }

    /// Parse namespaced key
    pub fn parse_namespaced_key(key: &str) -> Option<(&str, &str)> {
        key.split_once(':')
    }

    /// Calculate TTL based on access patterns
    pub fn calculate_adaptive_ttl(
        access_count: u64,
        last_access: chrono::DateTime<chrono::Utc>,
        base_ttl: chrono::Duration,
    ) -> chrono::Duration {
        let now = chrono::Utc::now();
        let time_since_access = now - last_access;
        
        // Increase TTL for frequently accessed items
        let frequency_multiplier = if access_count > 100 {
            2.0
        } else if access_count > 10 {
            1.5
        } else {
            1.0
        };
        
        // Decrease TTL for items not accessed recently
        let recency_multiplier = if time_since_access > chrono::Duration::hours(24) {
            0.5
        } else if time_since_access > chrono::Duration::hours(1) {
            0.8
        } else {
            1.0
        };
        
        let multiplier = frequency_multiplier * recency_multiplier;
        let new_ttl_secs = (base_ttl.num_seconds() as f64 * multiplier) as i64;
        
        chrono::Duration::seconds(new_ttl_secs.max(60)) // Minimum 1 minute TTL
    }
}

/// Cache middleware for HTTP requests
pub mod middleware {
    use super::*;
    use axum::{
        extract::{Request, State},
        http::{HeaderMap, StatusCode},
        middleware::Next,
        response::Response,
    };
    use std::sync::Arc;

    /// HTTP cache middleware
    pub async fn cache_middleware(
        State(cache): State<Arc<MultiLevelCache>>,
        request: Request,
        next: Next,
    ) -> Result<Response, StatusCode> {
        let method = request.method().clone();
        let uri = request.uri().clone();
        
        // Only cache GET requests
        if method != axum::http::Method::GET {
            return Ok(next.run(request).await);
        }
        
        let cache_key = format!("http:{}:{}", method, uri);
        
        // Try to get from cache
        if let Ok(Some(cached_response)) = cache.get::<CachedHttpResponse>(&cache_key).await {
            if !cached_response.is_expired() {
                return Ok(cached_response.into_response());
            }
        }
        
        // Execute request
        let response = next.run(request).await;
        
        // Cache successful responses
        if response.status().is_success() {
            let cached_response = CachedHttpResponse::from_response(&response);
            let ttl = chrono::Duration::minutes(5); // Default 5 minute cache
            
            if let Err(e) = cache.set(&cache_key, &cached_response, ttl).await {
                tracing::warn!("Failed to cache HTTP response: {}", e);
            }
        }
        
        Ok(response)
    }

    /// Cached HTTP response
    #[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
    pub struct CachedHttpResponse {
        pub status: u16,
        pub headers: std::collections::HashMap<String, String>,
        pub body: Vec<u8>,
        pub cached_at: chrono::DateTime<chrono::Utc>,
        pub ttl_seconds: i64,
    }

    impl CachedHttpResponse {
        pub fn from_response(response: &Response) -> Self {
            // This is a simplified implementation
            // In practice, you'd need to handle the response body properly
            Self {
                status: response.status().as_u16(),
                headers: std::collections::HashMap::new(),
                body: Vec::new(),
                cached_at: chrono::Utc::now(),
                ttl_seconds: 300, // 5 minutes
            }
        }

        pub fn is_expired(&self) -> bool {
            let now = chrono::Utc::now();
            let expires_at = self.cached_at + chrono::Duration::seconds(self.ttl_seconds);
            now > expires_at
        }

        pub fn into_response(self) -> Response {
            // This is a simplified implementation
            // In practice, you'd reconstruct the full response
            Response::builder()
                .status(self.status)
                .body(axum::body::Body::from(self.body))
                .unwrap()
        }
    }
}

/// Re-export commonly used types
pub type Duration = chrono::Duration;
pub type DateTime = chrono::DateTime<chrono::Utc>;

/// Cache trait for implementing custom cache backends
#[async_trait::async_trait]
pub trait Cache: Send + Sync {
    type Error: std::error::Error + Send + Sync + 'static;

    async fn get<T>(&self, key: &str) -> Result<Option<T>, Self::Error>
    where
        T: serde::de::DeserializeOwned + Send;

    async fn set<T>(&self, key: &str, value: &T, ttl: Duration) -> Result<(), Self::Error>
    where
        T: serde::Serialize + Send + Sync;

    async fn delete(&self, key: &str) -> Result<bool, Self::Error>;

    async fn exists(&self, key: &str) -> Result<bool, Self::Error>;

    async fn clear(&self) -> Result<(), Self::Error>;

    async fn size(&self) -> Result<usize, Self::Error>;

    async fn keys(&self, pattern: &str) -> Result<Vec<String>, Self::Error>;
}

/// Initialize the cache system
pub async fn init_cache_system(config: CacheConfig) -> CacheResult<MultiLevelCache> {
    tracing::info!("Initializing RegulateAI cache system");
    
    let cache = MultiLevelCache::new(config).await?;
    
    tracing::info!("Cache system initialized successfully");
    Ok(cache)
}
