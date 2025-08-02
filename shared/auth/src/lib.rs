//! RegulateAI Authentication and Authorization Library
//! 
//! This library provides comprehensive authentication and authorization features
//! including JWT tokens, password hashing, RBAC, and session management.

pub mod jwt;
pub mod password;
pub mod rbac;
pub mod session;
pub mod middleware;
pub mod types;

// Re-export commonly used types
pub use jwt::*;
pub use password::*;
pub use rbac::*;
pub use session::*;
pub use middleware::*;
pub use types::*;

// Re-export external dependencies
pub use jsonwebtoken::{Algorithm, DecodingKey, EncodingKey, Header, Validation};
pub use uuid::Uuid;
