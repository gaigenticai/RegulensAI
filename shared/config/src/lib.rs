//! RegulateAI Configuration Management Library
//! 
//! This library provides comprehensive configuration management for all RegulateAI services.
//! It supports environment variables, YAML files, TOML files, and runtime configuration updates.

pub mod settings;
pub mod database;
pub mod redis;
pub mod security;
pub mod external;
pub mod monitoring;
pub mod service;

// Re-export commonly used types
pub use settings::*;
pub use database::*;
pub use redis::*;
pub use security::*;
pub use external::*;
pub use monitoring::*;
pub use service::*;

// Re-export external dependencies
pub use config::{Config, ConfigError, Environment, File, FileFormat};
pub use dotenvy::dotenv;
