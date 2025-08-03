//! Cache Metrics

use crate::CacheLevel;
use prometheus::{Counter, Histogram, Gauge, register_counter, register_histogram, register_gauge};
use lazy_static::lazy_static;

lazy_static! {
    static ref CACHE_HITS: Counter = register_counter!(
        "cache_hits_total",
        "Total number of cache hits"
    ).unwrap();

    static ref CACHE_MISSES: Counter = register_counter!(
        "cache_misses_total", 
        "Total number of cache misses"
    ).unwrap();

    static ref CACHE_SETS: Counter = register_counter!(
        "cache_sets_total",
        "Total number of cache sets"
    ).unwrap();

    static ref CACHE_DELETES: Counter = register_counter!(
        "cache_deletes_total",
        "Total number of cache deletes"
    ).unwrap();

    static ref CACHE_LATENCY: Histogram = register_histogram!(
        "cache_operation_duration_seconds",
        "Cache operation latency"
    ).unwrap();

    static ref CACHE_SIZE: Gauge = register_gauge!(
        "cache_size_bytes",
        "Current cache size in bytes"
    ).unwrap();
}

/// Cache metrics collector
pub struct CacheMetrics;

impl CacheMetrics {
    pub fn new() -> Self {
        Self
    }

    pub async fn record_cache_hit(&self, _level: CacheLevel, latency_ms: u64, _size_bytes: usize) {
        CACHE_HITS.inc();
        CACHE_LATENCY.observe(latency_ms as f64 / 1000.0);
    }

    pub async fn record_cache_miss(&self, latency_ms: u64) {
        CACHE_MISSES.inc();
        CACHE_LATENCY.observe(latency_ms as f64 / 1000.0);
    }

    pub async fn record_cache_set(&self, latency_ms: u64, size_bytes: usize) {
        CACHE_SETS.inc();
        CACHE_LATENCY.observe(latency_ms as f64 / 1000.0);
        CACHE_SIZE.add(size_bytes as f64);
    }

    pub async fn record_cache_delete(&self, latency_ms: u64) {
        CACHE_DELETES.inc();
        CACHE_LATENCY.observe(latency_ms as f64 / 1000.0);
    }
}
