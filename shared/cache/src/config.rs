//! Cache Configuration

use crate::{
    l1_memory::MemoryCacheConfig,
    l2_redis::RedisCacheConfig,
    l3_database::DatabaseCacheConfig,
};
use serde::{Deserialize, Serialize};

/// Main cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub l1_enabled: bool,
    pub l2_enabled: bool,
    pub l3_enabled: bool,
    pub compression_enabled: bool,
    pub metrics_enabled: bool,
    pub max_entry_size: usize,
    pub l1_config: MemoryCacheConfig,
    pub l2_config: RedisCacheConfig,
    pub l3_config: DatabaseCacheConfig,
    pub serialization: SerializationConfig,
    pub compression: CompressionConfig,
    pub invalidation: InvalidationConfig,
    pub warming: WarmingConfig,
}

/// Serialization configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerializationConfig {
    pub format: SerializationFormat,
    pub compression_threshold: usize,
    pub pretty_json: bool,
    pub auto_detect_format: bool,
    pub benchmark_on_startup: bool,
}

/// Serialization formats
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SerializationFormat {
    Json,
    Bincode,
    MessagePack,
}

/// Compression configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressionConfig {
    pub algorithm: CompressionAlgorithm,
    pub level: u32,
    pub threshold_bytes: usize,
}

/// Compression algorithms
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CompressionAlgorithm {
    None,
    Lz4,
    Zstd,
    Gzip,
}

/// Invalidation configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvalidationConfig {
    pub enabled: bool,
    pub strategy: InvalidationStrategyType,
    pub batch_size: usize,
    pub max_queue_size: usize,
}

/// Invalidation strategy types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InvalidationStrategyType {
    Immediate,
    Batched,
    Lazy,
}

/// Cache warming configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WarmingConfig {
    pub enabled: bool,
    pub strategy: WarmingStrategy,
    pub batch_size: usize,
    pub max_concurrent: usize,
}

/// Warming strategies
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WarmingStrategy {
    Eager,
    Lazy,
    Scheduled,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            l1_enabled: true,
            l2_enabled: true,
            l3_enabled: false,
            compression_enabled: true,
            metrics_enabled: true,
            max_entry_size: 1024 * 1024, // 1MB
            l1_config: MemoryCacheConfig::default(),
            l2_config: RedisCacheConfig::default(),
            l3_config: DatabaseCacheConfig::default(),
            serialization: SerializationConfig::default(),
            compression: CompressionConfig::default(),
            invalidation: InvalidationConfig::default(),
            warming: WarmingConfig::default(),
        }
    }
}

impl Default for SerializationConfig {
    fn default() -> Self {
        Self {
            format: SerializationFormat::Bincode,
            compression_threshold: 1024, // 1KB
            pretty_json: false,
            auto_detect_format: false,
            benchmark_on_startup: false,
        }
    }
}

impl Default for CompressionConfig {
    fn default() -> Self {
        Self {
            algorithm: CompressionAlgorithm::Lz4,
            level: 1,
            threshold_bytes: 1024, // 1KB
        }
    }
}

impl Default for InvalidationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            strategy: InvalidationStrategyType::Immediate,
            batch_size: 100,
            max_queue_size: 10000,
        }
    }
}

impl Default for WarmingConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            strategy: WarmingStrategy::Lazy,
            batch_size: 50,
            max_concurrent: 10,
        }
    }
}
