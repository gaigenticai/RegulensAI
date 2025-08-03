//! Cache Strategies

use serde::{Deserialize, Serialize};

/// Cache strategy
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CacheStrategy {
    CacheAside,
    WriteThrough,
    WriteBehind,
    ReadThrough,
}

/// Eviction policy
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EvictionPolicy {
    Lru,  // Least Recently Used
    Lfu,  // Least Frequently Used
    Fifo, // First In, First Out
    Random,
    Ttl,  // Time To Live
}
