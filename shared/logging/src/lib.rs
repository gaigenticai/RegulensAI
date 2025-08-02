//! RegulateAI Logging and Observability Library
//! 
//! This library provides structured logging, distributed tracing, and observability
//! features for all RegulateAI services.

pub mod logger;
pub mod tracing_setup;
pub mod metrics;
pub mod correlation;

// Re-export commonly used types
pub use logger::*;
pub use tracing_setup::*;
pub use metrics::*;
pub use correlation::*;

// Re-export external dependencies
pub use tracing::{debug, error, info, trace, warn, event, span, Level, Span};
pub use uuid::Uuid;
