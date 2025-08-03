//! Integration tests for the cache module

use regulateai_cache::{
    multi_level::MultiLevelCache,
    l1_memory::{MemoryCache, MemoryCacheConfig},
    l2_redis::{RedisCache, RedisCacheConfig},
    l3_database::{DatabaseCache, DatabaseCacheConfig},
    config::CacheConfig,
    compression::{CacheCompressor, CompressionAlgorithm},
    serialization::{CacheSerializer, SerializationFormat},
    CacheLevel, Duration,
};
use serde::{Deserialize, Serialize};
use tokio_test;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct TestData {
    id: u64,
    name: String,
    value: f64,
    tags: Vec<String>,
}

impl TestData {
    fn new(id: u64, name: &str, value: f64) -> Self {
        Self {
            id,
            name: name.to_string(),
            value,
            tags: vec!["test".to_string(), "cache".to_string()],
        }
    }
}

#[tokio::test]
async fn test_memory_cache_basic_operations() {
    let config = MemoryCacheConfig::default();
    let cache = MemoryCache::new(config).await.expect("Failed to create memory cache");

    let test_data = TestData::new(1, "test_item", 42.0);
    let key = "test_key_1";
    let ttl = Duration::minutes(5);

    // Test set operation
    cache.set(key, &test_data, ttl).await.expect("Failed to set cache entry");
    println!("✅ Memory cache set operation successful");

    // Test get operation
    let retrieved: Option<TestData> = cache.get(key).await.expect("Failed to get cache entry");
    assert!(retrieved.is_some(), "Cache entry should exist");
    assert_eq!(retrieved.unwrap(), test_data, "Retrieved data should match original");
    println!("✅ Memory cache get operation successful");

    // Test exists operation
    let exists = cache.exists(key).await.expect("Failed to check cache existence");
    assert!(exists, "Cache entry should exist");
    println!("✅ Memory cache exists operation successful");

    // Test delete operation
    let deleted = cache.delete(key).await.expect("Failed to delete cache entry");
    assert!(deleted, "Delete operation should return true");
    
    let retrieved_after_delete: Option<TestData> = cache.get(key).await.expect("Failed to get cache entry after delete");
    assert!(retrieved_after_delete.is_none(), "Cache entry should not exist after delete");
    println!("✅ Memory cache delete operation successful");
}

#[tokio::test]
async fn test_memory_cache_expiration() {
    let config = MemoryCacheConfig::default();
    let cache = MemoryCache::new(config).await.expect("Failed to create memory cache");

    let test_data = TestData::new(2, "expiring_item", 100.0);
    let key = "expiring_key";
    let short_ttl = Duration::milliseconds(100);

    // Set with short TTL
    cache.set(key, &test_data, short_ttl).await.expect("Failed to set cache entry");
    
    // Should exist immediately
    let exists_immediately = cache.exists(key).await.expect("Failed to check cache existence");
    assert!(exists_immediately, "Cache entry should exist immediately");

    // Wait for expiration
    tokio::time::sleep(std::time::Duration::from_millis(150)).await;

    // Should not exist after expiration
    let retrieved_after_expiry: Option<TestData> = cache.get(key).await.expect("Failed to get cache entry");
    assert!(retrieved_after_expiry.is_none(), "Cache entry should be expired");
    println!("✅ Memory cache expiration working correctly");
}

#[tokio::test]
async fn test_compression_algorithms() {
    use regulateai_cache::config::{CompressionConfig, CompressionAlgorithm};

    let test_data = "This is a test string that should compress well when using compression algorithms. ".repeat(100);
    let test_bytes = test_data.as_bytes();

    // Test LZ4 compression
    let lz4_config = CompressionConfig {
        algorithm: CompressionAlgorithm::Lz4,
        level: 1,
        threshold_bytes: 10,
    };
    let mut lz4_compressor = CacheCompressor::new(lz4_config);
    
    let compressed_lz4 = lz4_compressor.compress(test_bytes).expect("LZ4 compression failed");
    let decompressed_lz4 = lz4_compressor.decompress(&compressed_lz4).expect("LZ4 decompression failed");
    
    assert_eq!(test_bytes, decompressed_lz4.as_slice(), "LZ4 round-trip should preserve data");
    assert!(compressed_lz4.len() < test_bytes.len(), "LZ4 should compress data");
    println!("✅ LZ4 compression working correctly: {} -> {} bytes", test_bytes.len(), compressed_lz4.len());

    // Test Zstd compression
    let zstd_config = CompressionConfig {
        algorithm: CompressionAlgorithm::Zstd,
        level: 3,
        threshold_bytes: 10,
    };
    let mut zstd_compressor = CacheCompressor::new(zstd_config);
    
    let compressed_zstd = zstd_compressor.compress(test_bytes).expect("Zstd compression failed");
    let decompressed_zstd = zstd_compressor.decompress(&compressed_zstd).expect("Zstd decompression failed");
    
    assert_eq!(test_bytes, decompressed_zstd.as_slice(), "Zstd round-trip should preserve data");
    assert!(compressed_zstd.len() < test_bytes.len(), "Zstd should compress data");
    println!("✅ Zstd compression working correctly: {} -> {} bytes", test_bytes.len(), compressed_zstd.len());

    // Test Gzip compression
    let gzip_config = CompressionConfig {
        algorithm: CompressionAlgorithm::Gzip,
        level: 6,
        threshold_bytes: 10,
    };
    let mut gzip_compressor = CacheCompressor::new(gzip_config);
    
    let compressed_gzip = gzip_compressor.compress(test_bytes).expect("Gzip compression failed");
    let decompressed_gzip = gzip_compressor.decompress(&compressed_gzip).expect("Gzip decompression failed");
    
    assert_eq!(test_bytes, decompressed_gzip.as_slice(), "Gzip round-trip should preserve data");
    assert!(compressed_gzip.len() < test_bytes.len(), "Gzip should compress data");
    println!("✅ Gzip compression working correctly: {} -> {} bytes", test_bytes.len(), compressed_gzip.len());
}

#[tokio::test]
async fn test_serialization_formats() {
    use regulateai_cache::config::SerializationConfig;

    let test_data = TestData::new(3, "serialization_test", 123.456);

    // Test JSON serialization
    let json_config = SerializationConfig {
        format: SerializationFormat::Json,
        compression_threshold: 1024,
    };
    let json_serializer = CacheSerializer::new(json_config);
    
    let json_bytes = json_serializer.serialize(&test_data).expect("JSON serialization failed");
    let json_deserialized: TestData = json_serializer.deserialize(&json_bytes).expect("JSON deserialization failed");
    
    assert_eq!(test_data, json_deserialized, "JSON round-trip should preserve data");
    println!("✅ JSON serialization working correctly: {} bytes", json_bytes.len());

    // Test Bincode serialization
    let bincode_config = SerializationConfig {
        format: SerializationFormat::Bincode,
        compression_threshold: 1024,
    };
    let bincode_serializer = CacheSerializer::new(bincode_config);
    
    let bincode_bytes = bincode_serializer.serialize(&test_data).expect("Bincode serialization failed");
    let bincode_deserialized: TestData = bincode_serializer.deserialize(&bincode_bytes).expect("Bincode deserialization failed");
    
    assert_eq!(test_data, bincode_deserialized, "Bincode round-trip should preserve data");
    println!("✅ Bincode serialization working correctly: {} bytes", bincode_bytes.len());

    // Test MessagePack serialization
    let msgpack_config = SerializationConfig {
        format: SerializationFormat::MessagePack,
        compression_threshold: 1024,
    };
    let msgpack_serializer = CacheSerializer::new(msgpack_config);
    
    let msgpack_bytes = msgpack_serializer.serialize(&test_data).expect("MessagePack serialization failed");
    let msgpack_deserialized: TestData = msgpack_serializer.deserialize(&msgpack_bytes).expect("MessagePack deserialization failed");
    
    assert_eq!(test_data, msgpack_deserialized, "MessagePack round-trip should preserve data");
    println!("✅ MessagePack serialization working correctly: {} bytes", msgpack_bytes.len());
}

#[tokio::test]
async fn test_cache_performance() {
    let config = MemoryCacheConfig {
        max_capacity: 10000,
        max_size_bytes: 10 * 1024 * 1024, // 10MB
        time_to_live: Some(Duration::hours(1)),
        time_to_idle: Some(Duration::minutes(30)),
        eviction_policy: regulateai_cache::l1_memory::EvictionPolicy::Lru,
        initial_capacity: Some(1000),
        num_segments: None,
        weigher_enabled: true,
    };
    
    let cache = MemoryCache::new(config).await.expect("Failed to create memory cache");
    
    let start_time = std::time::Instant::now();
    let num_operations = 1000;
    
    // Perform bulk set operations
    for i in 0..num_operations {
        let test_data = TestData::new(i, &format!("item_{}", i), i as f64);
        let key = format!("perf_key_{}", i);
        cache.set(&key, &test_data, Duration::minutes(10)).await.expect("Failed to set cache entry");
    }
    
    let set_duration = start_time.elapsed();
    println!("✅ Bulk set performance: {} operations in {:?} ({:.2} ops/sec)", 
             num_operations, set_duration, num_operations as f64 / set_duration.as_secs_f64());
    
    // Perform bulk get operations
    let get_start = std::time::Instant::now();
    let mut successful_gets = 0;
    
    for i in 0..num_operations {
        let key = format!("perf_key_{}", i);
        let retrieved: Option<TestData> = cache.get(&key).await.expect("Failed to get cache entry");
        if retrieved.is_some() {
            successful_gets += 1;
        }
    }
    
    let get_duration = get_start.elapsed();
    println!("✅ Bulk get performance: {} operations in {:?} ({:.2} ops/sec), {} successful", 
             num_operations, get_duration, num_operations as f64 / get_duration.as_secs_f64(), successful_gets);
    
    assert_eq!(successful_gets, num_operations, "All get operations should succeed");
}

#[tokio::test]
async fn test_cache_eviction() {
    let config = MemoryCacheConfig {
        max_capacity: 5, // Small capacity to force eviction
        max_size_bytes: 1024,
        time_to_live: Some(Duration::hours(1)),
        time_to_idle: Some(Duration::minutes(30)),
        eviction_policy: regulateai_cache::l1_memory::EvictionPolicy::Lru,
        initial_capacity: Some(5),
        num_segments: None,
        weigher_enabled: false,
    };
    
    let cache = MemoryCache::new(config).await.expect("Failed to create memory cache");
    
    // Fill cache beyond capacity
    for i in 0..10 {
        let test_data = TestData::new(i, &format!("eviction_item_{}", i), i as f64);
        let key = format!("eviction_key_{}", i);
        cache.set(&key, &test_data, Duration::minutes(10)).await.expect("Failed to set cache entry");
    }
    
    // Check that some early entries were evicted
    let early_key_exists = cache.exists("eviction_key_0").await.expect("Failed to check cache existence");
    let late_key_exists = cache.exists("eviction_key_9").await.expect("Failed to check cache existence");
    
    // Due to LRU eviction, early keys should be evicted, late keys should remain
    assert!(!early_key_exists, "Early cache entries should be evicted");
    assert!(late_key_exists, "Recent cache entries should remain");
    
    println!("✅ Cache eviction working correctly");
}

// Edge case tests

#[tokio::test]
async fn test_cache_with_large_data() {
    let config = MemoryCacheConfig::default();
    let cache = MemoryCache::new(config).await.expect("Failed to create memory cache");
    
    // Create large test data
    let large_data = TestData {
        id: 999,
        name: "large_item".to_string(),
        value: 999.999,
        tags: (0..1000).map(|i| format!("tag_{}", i)).collect(),
    };
    
    let key = "large_key";
    let ttl = Duration::minutes(5);
    
    // Should handle large data
    cache.set(key, &large_data, ttl).await.expect("Failed to set large cache entry");
    
    let retrieved: Option<TestData> = cache.get(key).await.expect("Failed to get large cache entry");
    assert!(retrieved.is_some(), "Large cache entry should exist");
    assert_eq!(retrieved.unwrap().tags.len(), 1000, "Large data should be preserved");
    
    println!("✅ Cache handles large data correctly");
}

#[tokio::test]
async fn test_cache_with_empty_data() {
    let config = MemoryCacheConfig::default();
    let cache = MemoryCache::new(config).await.expect("Failed to create memory cache");
    
    let empty_data = TestData {
        id: 0,
        name: String::new(),
        value: 0.0,
        tags: Vec::new(),
    };
    
    let key = "empty_key";
    let ttl = Duration::minutes(5);
    
    // Should handle empty data
    cache.set(key, &empty_data, ttl).await.expect("Failed to set empty cache entry");
    
    let retrieved: Option<TestData> = cache.get(key).await.expect("Failed to get empty cache entry");
    assert!(retrieved.is_some(), "Empty cache entry should exist");
    assert_eq!(retrieved.unwrap().name, "", "Empty data should be preserved");
    
    println!("✅ Cache handles empty data correctly");
}

#[tokio::test]
async fn test_cache_concurrent_access() {
    use std::sync::Arc;
    
    let config = MemoryCacheConfig::default();
    let cache = Arc::new(MemoryCache::new(config).await.expect("Failed to create memory cache"));
    
    let mut handles = Vec::new();
    let num_tasks = 10;
    let operations_per_task = 100;
    
    // Spawn concurrent tasks
    for task_id in 0..num_tasks {
        let cache_clone = Arc::clone(&cache);
        let handle = tokio::spawn(async move {
            for i in 0..operations_per_task {
                let test_data = TestData::new(
                    (task_id * operations_per_task + i) as u64,
                    &format!("concurrent_item_{}_{}", task_id, i),
                    (task_id * operations_per_task + i) as f64,
                );
                let key = format!("concurrent_key_{}_{}", task_id, i);
                
                // Set and immediately get
                cache_clone.set(&key, &test_data, Duration::minutes(5)).await.expect("Failed to set in concurrent task");
                let retrieved: Option<TestData> = cache_clone.get(&key).await.expect("Failed to get in concurrent task");
                assert!(retrieved.is_some(), "Concurrent cache entry should exist");
            }
        });
        handles.push(handle);
    }
    
    // Wait for all tasks to complete
    for handle in handles {
        handle.await.expect("Concurrent task failed");
    }
    
    println!("✅ Cache handles concurrent access correctly: {} tasks × {} operations", num_tasks, operations_per_task);
}

#[tokio::test]
async fn test_compression_efficiency() {
    use regulateai_cache::config::CompressionConfig;
    
    // Test compression efficiency with different data types
    let repetitive_data = "AAAAAAAAAA".repeat(1000);
    let random_data = (0..10000).map(|i| (i % 256) as u8).collect::<Vec<u8>>();
    
    let config = CompressionConfig {
        algorithm: CompressionAlgorithm::Lz4,
        level: 1,
        threshold_bytes: 100,
    };
    
    let mut compressor = CacheCompressor::new(config);
    
    // Test repetitive data (should compress well)
    let repetitive_efficiency = compressor.calculate_efficiency(repetitive_data.as_bytes())
        .expect("Failed to calculate compression efficiency");
    
    assert!(repetitive_efficiency.space_saved_percentage > 50.0, 
            "Repetitive data should compress well");
    
    println!("✅ Compression efficiency test:");
    println!("   Repetitive data: {:.1}% space saved", repetitive_efficiency.space_saved_percentage);
    
    // Test random data (should compress poorly)
    let random_efficiency = compressor.calculate_efficiency(&random_data)
        .expect("Failed to calculate compression efficiency");
    
    println!("   Random data: {:.1}% space saved", random_efficiency.space_saved_percentage);
    
    // Get compression statistics
    let stats = compressor.get_stats();
    println!("   Total compressions: {}", stats.total_compressions);
    println!("   Average compression ratio: {:.3}", stats.compression_ratio);
}
