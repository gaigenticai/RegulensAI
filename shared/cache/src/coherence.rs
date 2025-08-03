//! Cache Coherence

use serde::{Deserialize, Serialize};

/// Cache coherence manager
pub struct CacheCoherence;

/// Coherence protocol
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CoherenceProtocol {
    None,
    EventBased,
    TimeBasedInvalidation,
    VersionBased,
}

impl CacheCoherence {
    pub fn new() -> Self {
        Self
    }
}
