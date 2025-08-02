//! Database entity models for RegulateAI
//! 
//! This module contains all the database entity models that correspond to the PostgreSQL schema.
//! Each entity implements the necessary traits for SeaORM and includes proper validation.

pub mod user;
pub mod role;
pub mod organization;
pub mod audit_log;
pub mod customer;
pub mod transaction;
pub mod sanctions_list;
pub mod aml_alert;
pub mod policy;
pub mod control;
pub mod control_test;
pub mod risk_category;
pub mod risk_assessment;
pub mod key_risk_indicator;
pub mod kri_measurement;
pub mod stress_test;
pub mod fraud_rule;
pub mod fraud_alert;
pub mod ml_model;
pub mod vulnerability;
pub mod security_incident;
pub mod ai_agent;
pub mod ai_conversation;
pub mod ai_message;
pub mod workflow_automation;

// Re-export all entities
pub use user::*;
pub use role::*;
pub use organization::*;
pub use audit_log::*;
pub use customer::*;
pub use transaction::*;
pub use sanctions_list::*;
pub use aml_alert::*;
pub use policy::*;
pub use control::*;
pub use control_test::*;
pub use risk_category::*;
pub use risk_assessment::*;
pub use key_risk_indicator::*;
pub use kri_measurement::*;
pub use stress_test::*;
pub use fraud_rule::*;
pub use fraud_alert::*;
pub use ml_model::*;
pub use vulnerability::*;
pub use security_incident::*;
pub use ai_agent::*;
pub use ai_conversation::*;
pub use ai_message::*;
pub use workflow_automation::*;
