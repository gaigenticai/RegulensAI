//! Metrics Collectors

use crate::errors::MetricsResult;

/// Metrics collector trait
pub trait MetricsCollector {
    async fn start(&self) -> MetricsResult<()>;
    async fn stop(&self) -> MetricsResult<()>;
    async fn collect(&self) -> MetricsResult<()>;
}
