//! RegulateAI Error Handling Library
//! 
//! This library provides comprehensive error handling for all RegulateAI services.
//! It includes custom error types, HTTP error responses, and error conversion utilities.

pub mod types;
pub mod http;
pub mod validation;
pub mod database;
pub mod external;

// Re-export commonly used types
pub use types::*;
pub use http::*;
pub use validation::*;
pub use database::*;
pub use external::*;

// Re-export external dependencies
pub use anyhow::{anyhow, Context, Result as AnyhowResult};
pub use thiserror::Error;
