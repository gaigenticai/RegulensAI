//! RegulateAI Database Library
//! 
//! This library provides database connection management, ORM utilities,
//! and migration support for all RegulateAI services.

pub mod connection;
pub mod migration;
pub mod repository;
pub mod transaction;
pub mod health;

// Re-export commonly used types
pub use connection::*;
pub use migration::*;
pub use repository::*;
pub use transaction::*;
pub use health::*;

// Re-export external dependencies
pub use sea_orm::{
    ActiveModelTrait, ActiveValue, ColumnTrait, DatabaseConnection, DatabaseTransaction,
    EntityTrait, ModelTrait, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect,
    Set, Unset, DbErr, TransactionTrait,
};
pub use sqlx::{Pool, Postgres, Row};
pub use uuid::Uuid;
