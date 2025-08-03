//! Test Data Generation

use serde::{Deserialize, Serialize};

/// Test data generator
pub struct TestDataGenerator {
    config: RandomDataConfig,
}

/// Random data configuration
#[derive(Debug, Clone)]
pub struct RandomDataConfig {
    pub seed: Option<u64>,
}

impl TestDataGenerator {
    pub fn new(config: RandomDataConfig) -> Self {
        Self { config }
    }
}

impl Default for RandomDataConfig {
    fn default() -> Self {
        Self { seed: None }
    }
}
