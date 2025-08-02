//! RegulateAI Common Library
//! 
//! This library provides common types, utilities, and traits used across all RegulateAI services.
//! It includes fundamental data structures, validation helpers, and shared business logic.

pub mod types;
pub mod traits;
pub mod utils;
pub mod constants;
pub mod validation;

// Re-export commonly used types
pub use types::*;
pub use traits::*;
pub use utils::*;
pub use constants::*;
pub use validation::*;

// Re-export external dependencies for consistency
pub use chrono::{DateTime, Utc};
pub use serde::{Deserialize, Serialize};
pub use uuid::Uuid;
pub use validator::Validate;
