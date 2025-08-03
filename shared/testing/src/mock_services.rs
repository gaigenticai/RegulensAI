//! Mock Services for Testing

use crate::{TestResult, MockServiceConfig};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Mock service builder
pub struct MockServiceBuilder {
    config: MockServiceConfig,
}

/// Mock response definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MockResponse {
    pub status: u16,
    pub headers: HashMap<String, String>,
    pub body: Option<String>,
    pub delay_ms: Option<u64>,
}

impl MockServiceBuilder {
    pub fn new(config: MockServiceConfig) -> Self {
        Self { config }
    }

    pub async fn cleanup(&self) -> TestResult<()> {
        Ok(())
    }
}
