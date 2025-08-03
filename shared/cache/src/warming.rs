//! Cache Warming

use crate::{
    config::WarmingConfig,
    errors::CacheResult,
    multi_level::MultiLevelCache,
};

/// Cache warmer
pub struct CacheWarmer {
    config: WarmingConfig,
}

/// Warming strategy
pub use crate::config::WarmingStrategy;

impl CacheWarmer {
    pub fn new(config: WarmingConfig) -> Self {
        Self { config }
    }

    pub async fn warm_cache(&self, _cache: &MultiLevelCache, _keys: Vec<String>) -> CacheResult<u64> {
        // Implementation would warm cache based on strategy
        Ok(0)
    }
}
