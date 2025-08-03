//! Cache Serialization
//!
//! Provides comprehensive serialization support for cache entries with multiple formats,
//! performance optimization, and detailed statistics tracking.

use crate::{config::SerializationConfig, errors::{CacheError, CacheResult}};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Instant;

/// Cache serializer with advanced features
pub struct CacheSerializer {
    config: SerializationConfig,
    stats: SerializationStats,
    format_cache: HashMap<String, SerializationFormat>,
}

/// Serialization format
pub use crate::config::SerializationFormat;

/// Serialization statistics
#[derive(Debug, Clone, Default)]
pub struct SerializationStats {
    pub total_serializations: u64,
    pub total_deserializations: u64,
    pub bytes_serialized: u64,
    pub bytes_deserialized: u64,
    pub average_serialization_time_ms: f64,
    pub average_deserialization_time_ms: f64,
    pub format_usage: HashMap<SerializationFormat, u64>,
    pub serialization_errors: u64,
    pub deserialization_errors: u64,
}

/// Serialization performance metrics
#[derive(Debug, Clone)]
pub struct SerializationPerformance {
    pub format: SerializationFormat,
    pub serialization_time_ms: f64,
    pub deserialization_time_ms: f64,
    pub serialized_size: usize,
    pub compression_ratio: f64,
    pub throughput_mb_per_sec: f64,
}

/// Serialization benchmark result
#[derive(Debug, Clone)]
pub struct SerializationBenchmark {
    pub format: SerializationFormat,
    pub avg_serialization_time_ms: f64,
    pub avg_deserialization_time_ms: f64,
    pub avg_size_bytes: usize,
    pub throughput_ops_per_sec: f64,
    pub error_rate: f64,
}

impl CacheSerializer {
    /// Create a new cache serializer
    pub fn new(config: SerializationConfig) -> Self {
        Self {
            config,
            stats: SerializationStats::default(),
            format_cache: HashMap::new(),
        }
    }

    /// Serialize value with performance tracking
    pub fn serialize<T>(&mut self, value: &T) -> CacheResult<Vec<u8>>
    where
        T: Serialize,
    {
        let start_time = Instant::now();

        let result = match self.config.format {
            SerializationFormat::Json => self.serialize_json(value),
            SerializationFormat::Bincode => self.serialize_bincode(value),
            SerializationFormat::MessagePack => self.serialize_messagepack(value),
        };

        let serialization_time = start_time.elapsed().as_millis() as f64;

        match &result {
            Ok(data) => {
                self.update_serialization_stats(data.len(), serialization_time, false);
            }
            Err(_) => {
                self.update_serialization_stats(0, serialization_time, true);
            }
        }

        result
    }

    /// Deserialize value with performance tracking
    pub fn deserialize<T>(&mut self, data: &[u8]) -> CacheResult<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        let start_time = Instant::now();

        let result = match self.config.format {
            SerializationFormat::Json => self.deserialize_json(data),
            SerializationFormat::Bincode => self.deserialize_bincode(data),
            SerializationFormat::MessagePack => self.deserialize_messagepack(data),
        };

        let deserialization_time = start_time.elapsed().as_millis() as f64;

        match &result {
            Ok(_) => {
                self.update_deserialization_stats(data.len(), deserialization_time, false);
            }
            Err(_) => {
                self.update_deserialization_stats(data.len(), deserialization_time, true);
            }
        }

        result
    }

    /// Serialize using JSON format
    fn serialize_json<T>(&self, value: &T) -> CacheResult<Vec<u8>>
    where
        T: Serialize,
    {
        if self.config.pretty_json {
            serde_json::to_vec_pretty(value)
                .map_err(|e| CacheError::Serialization(format!("JSON serialization failed: {}", e)))
        } else {
            serde_json::to_vec(value)
                .map_err(|e| CacheError::Serialization(format!("JSON serialization failed: {}", e)))
        }
    }

    /// Deserialize using JSON format
    fn deserialize_json<T>(&self, data: &[u8]) -> CacheResult<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        serde_json::from_slice(data)
            .map_err(|e| CacheError::Serialization(format!("JSON deserialization failed: {}", e)))
    }

    /// Serialize using Bincode format
    fn serialize_bincode<T>(&self, value: &T) -> CacheResult<Vec<u8>>
    where
        T: Serialize,
    {
        let config = bincode::config::standard()
            .with_big_endian()
            .with_fixed_int_encoding();

        bincode::encode_to_vec(value, config)
            .map_err(|e| CacheError::Serialization(format!("Bincode serialization failed: {}", e)))
    }

    /// Deserialize using Bincode format
    fn deserialize_bincode<T>(&self, data: &[u8]) -> CacheResult<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        let config = bincode::config::standard()
            .with_big_endian()
            .with_fixed_int_encoding();

        let (result, _) = bincode::decode_from_slice(data, config)
            .map_err(|e| CacheError::Serialization(format!("Bincode deserialization failed: {}", e)))?;

        Ok(result)
    }

    /// Serialize using MessagePack format
    fn serialize_messagepack<T>(&self, value: &T) -> CacheResult<Vec<u8>>
    where
        T: Serialize,
    {
        rmp_serde::to_vec_named(value)
            .map_err(|e| CacheError::Serialization(format!("MessagePack serialization failed: {}", e)))
    }

    /// Deserialize using MessagePack format
    fn deserialize_messagepack<T>(&self, data: &[u8]) -> CacheResult<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        rmp_serde::from_slice(data)
            .map_err(|e| CacheError::Serialization(format!("MessagePack deserialization failed: {}", e)))
    }

    /// Auto-detect best serialization format for given data
    pub fn auto_detect_format<T>(&mut self, value: &T) -> CacheResult<SerializationFormat>
    where
        T: Serialize + Clone,
    {
        let formats = vec![
            SerializationFormat::Bincode,
            SerializationFormat::MessagePack,
            SerializationFormat::Json,
        ];

        let mut best_format = SerializationFormat::Json;
        let mut best_score = f64::MAX;

        for format in formats {
            let original_format = self.config.format.clone();
            self.config.format = format.clone();

            if let Ok(serialized) = self.serialize(value) {
                let size_score = serialized.len() as f64;
                let time_score = self.stats.average_serialization_time_ms;

                // Combined score: size (70%) + time (30%)
                let combined_score = size_score * 0.7 + time_score * 0.3;

                if combined_score < best_score {
                    best_score = combined_score;
                    best_format = format;
                }
            }

            self.config.format = original_format;
        }

        Ok(best_format)
    }

    /// Benchmark all serialization formats
    pub fn benchmark_formats<T>(&mut self, value: &T, iterations: usize) -> CacheResult<Vec<SerializationBenchmark>>
    where
        T: Serialize + for<'de> Deserialize<'de> + Clone,
    {
        let formats = vec![
            SerializationFormat::Json,
            SerializationFormat::Bincode,
            SerializationFormat::MessagePack,
        ];

        let mut benchmarks = Vec::new();
        let original_format = self.config.format.clone();

        for format in formats {
            self.config.format = format.clone();

            let mut total_ser_time = 0.0;
            let mut total_deser_time = 0.0;
            let mut total_size = 0;
            let mut errors = 0;

            for _ in 0..iterations {
                // Benchmark serialization
                let ser_start = Instant::now();
                match self.serialize(value) {
                    Ok(data) => {
                        total_ser_time += ser_start.elapsed().as_millis() as f64;
                        total_size += data.len();

                        // Benchmark deserialization
                        let deser_start = Instant::now();
                        match self.deserialize::<T>(&data) {
                            Ok(_) => {
                                total_deser_time += deser_start.elapsed().as_millis() as f64;
                            }
                            Err(_) => errors += 1,
                        }
                    }
                    Err(_) => errors += 1,
                }
            }

            let avg_ser_time = total_ser_time / iterations as f64;
            let avg_deser_time = total_deser_time / iterations as f64;
            let avg_size = total_size / iterations;
            let throughput = if avg_ser_time + avg_deser_time > 0.0 {
                1000.0 / (avg_ser_time + avg_deser_time)
            } else {
                0.0
            };
            let error_rate = errors as f64 / iterations as f64;

            benchmarks.push(SerializationBenchmark {
                format: format.clone(),
                avg_serialization_time_ms: avg_ser_time,
                avg_deserialization_time_ms: avg_deser_time,
                avg_size_bytes: avg_size,
                throughput_ops_per_sec: throughput,
                error_rate,
            });
        }

        self.config.format = original_format;
        Ok(benchmarks)
    }

    /// Update serialization statistics
    fn update_serialization_stats(&mut self, size: usize, time_ms: f64, error: bool) {
        if error {
            self.stats.serialization_errors += 1;
            return;
        }

        self.stats.total_serializations += 1;
        self.stats.bytes_serialized += size as u64;

        // Update average serialization time
        let total = self.stats.total_serializations as f64;
        self.stats.average_serialization_time_ms =
            (self.stats.average_serialization_time_ms * (total - 1.0) + time_ms) / total;

        // Update format usage
        *self.stats.format_usage.entry(self.config.format.clone()).or_insert(0) += 1;
    }

    /// Update deserialization statistics
    fn update_deserialization_stats(&mut self, size: usize, time_ms: f64, error: bool) {
        if error {
            self.stats.deserialization_errors += 1;
            return;
        }

        self.stats.total_deserializations += 1;
        self.stats.bytes_deserialized += size as u64;

        // Update average deserialization time
        let total = self.stats.total_deserializations as f64;
        self.stats.average_deserialization_time_ms =
            (self.stats.average_deserialization_time_ms * (total - 1.0) + time_ms) / total;
    }

    /// Get serialization statistics
    pub fn get_stats(&self) -> &SerializationStats {
        &self.stats
    }

    /// Reset serialization statistics
    pub fn reset_stats(&mut self) {
        self.stats = SerializationStats::default();
    }

    /// Get current configuration
    pub fn get_config(&self) -> &SerializationConfig {
        &self.config
    }

    /// Update configuration
    pub fn update_config(&mut self, config: SerializationConfig) {
        self.config = config;
    }

    /// Calculate serialization efficiency
    pub fn calculate_efficiency<T>(&mut self, value: &T) -> CacheResult<SerializationPerformance>
    where
        T: Serialize + for<'de> Deserialize<'de> + Clone,
    {
        let ser_start = Instant::now();
        let serialized = self.serialize(value)?;
        let serialization_time = ser_start.elapsed().as_millis() as f64;

        let deser_start = Instant::now();
        let _: T = self.deserialize(&serialized)?;
        let deserialization_time = deser_start.elapsed().as_millis() as f64;

        let total_time = serialization_time + deserialization_time;
        let throughput = if total_time > 0.0 {
            (serialized.len() as f64 / 1024.0 / 1024.0) / (total_time / 1000.0)
        } else {
            0.0
        };

        Ok(SerializationPerformance {
            format: self.config.format.clone(),
            serialization_time_ms: serialization_time,
            deserialization_time_ms: deserialization_time,
            serialized_size: serialized.len(),
            compression_ratio: 1.0, // Would be calculated with original size
            throughput_mb_per_sec: throughput,
        })
    }
}
