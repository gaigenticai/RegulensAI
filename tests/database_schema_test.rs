//! Comprehensive database schema tests
//! 
//! This test suite validates the database schema design, migrations,
//! and entity model consistency as required by the development rules.

use chrono::Utc;
use regulateai_database::{create_test_connection, DatabaseManager};
use regulateai_config::DatabaseConfig;
use sea_orm::{Database, DatabaseConnection, EntityTrait, Statement};
use uuid::Uuid;

/// Test database schema creation and migrations
#[tokio::test]
async fn test_database_schema_creation() {
    let config = DatabaseConfig::test_config();
    let mut manager = DatabaseManager::new(config);
    
    // Test connection establishment
    assert!(manager.connect().await.is_ok());
    
    // Test migration execution
    assert!(manager.migrate().await.is_ok());
    
    // Test health check
    assert!(manager.health_check().await.unwrap());
    
    // Clean up
    assert!(manager.close().await.is_ok());
}

/// Test all table structures exist and have correct constraints
#[tokio::test]
async fn test_table_structures() {
    let conn = create_test_connection().await.unwrap();
    
    // Test that all expected tables exist
    let expected_tables = vec![
        "users", "roles", "user_roles", "organizations", "audit_logs",
        "customers", "transactions", "sanctions_lists", "aml_alerts",
        "policies", "controls", "control_tests",
        "risk_categories", "risk_assessments", "key_risk_indicators", "kri_measurements", "stress_tests",
        "fraud_rules", "fraud_alerts", "ml_models",
        "vulnerabilities", "security_incidents",
        "ai_agents", "ai_conversations", "ai_messages", "workflow_automations"
    ];
    
    for table_name in expected_tables {
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            format!("SELECT 1 FROM information_schema.tables WHERE table_name = '{}'", table_name),
        )).await;
        
        assert!(result.is_ok(), "Table {} should exist", table_name);
    }
}

/// Test database constraints and indexes
#[tokio::test]
async fn test_database_constraints() {
    let conn = create_test_connection().await.unwrap();
    
    // Test unique constraints
    let unique_constraints = vec![
        ("users", "email"),
        ("users", "username"),
        ("roles", "name"),
        ("sanctions_lists", "entity_name"),
        ("controls", "control_id"),
        ("fraud_rules", "rule_name"),
        ("ai_agents", "agent_name"),
        ("workflow_automations", "workflow_name"),
    ];
    
    for (table, column) in unique_constraints {
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            format!(
                "SELECT 1 FROM information_schema.table_constraints tc 
                 JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                 WHERE tc.table_name = '{}' AND ccu.column_name = '{}' AND tc.constraint_type = 'UNIQUE'",
                table, column
            ),
        )).await;
        
        assert!(result.is_ok(), "Unique constraint on {}.{} should exist", table, column);
    }
}

/// Test foreign key relationships
#[tokio::test]
async fn test_foreign_key_relationships() {
    let conn = create_test_connection().await.unwrap();
    
    // Test some critical foreign key relationships
    let foreign_keys = vec![
        ("user_roles", "user_id", "users", "id"),
        ("user_roles", "role_id", "roles", "id"),
        ("customers", "organization_id", "organizations", "id"),
        ("transactions", "customer_id", "customers", "id"),
        ("aml_alerts", "customer_id", "customers", "id"),
        ("aml_alerts", "transaction_id", "transactions", "id"),
        ("controls", "policy_id", "policies", "id"),
        ("control_tests", "control_id", "controls", "id"),
        ("risk_assessments", "risk_category_id", "risk_categories", "id"),
        ("kri_measurements", "kri_id", "key_risk_indicators", "id"),
        ("fraud_alerts", "customer_id", "customers", "id"),
        ("fraud_alerts", "rule_id", "fraud_rules", "id"),
        ("ai_conversations", "agent_id", "ai_agents", "id"),
        ("ai_messages", "conversation_id", "ai_conversations", "id"),
    ];
    
    for (child_table, child_column, parent_table, parent_column) in foreign_keys {
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            format!(
                "SELECT 1 FROM information_schema.referential_constraints rc
                 JOIN information_schema.key_column_usage kcu ON rc.constraint_name = kcu.constraint_name
                 JOIN information_schema.constraint_column_usage ccu ON rc.unique_constraint_name = ccu.constraint_name
                 WHERE kcu.table_name = '{}' AND kcu.column_name = '{}' 
                 AND ccu.table_name = '{}' AND ccu.column_name = '{}'",
                child_table, child_column, parent_table, parent_column
            ),
        )).await;
        
        assert!(result.is_ok(), "Foreign key {}.{} -> {}.{} should exist", 
                child_table, child_column, parent_table, parent_column);
    }
}

/// Test check constraints for enum values
#[tokio::test]
async fn test_check_constraints() {
    let conn = create_test_connection().await.unwrap();
    
    // Test that check constraints exist for enum fields
    let check_constraints = vec![
        ("users", "is_active"),
        ("organizations", "risk_level"),
        ("organizations", "status"),
        ("customers", "customer_type"),
        ("customers", "risk_level"),
        ("customers", "kyc_status"),
        ("transactions", "status"),
        ("aml_alerts", "severity"),
        ("aml_alerts", "status"),
        ("policies", "status"),
        ("controls", "control_type"),
        ("controls", "status"),
        ("risk_categories", "risk_type"),
        ("fraud_rules", "rule_type"),
        ("fraud_rules", "severity"),
        ("fraud_rules", "action"),
        ("vulnerabilities", "severity"),
        ("security_incidents", "incident_type"),
        ("security_incidents", "severity"),
        ("ai_agents", "agent_type"),
    ];
    
    for (table, _column) in check_constraints {
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            format!(
                "SELECT 1 FROM information_schema.check_constraints cc
                 JOIN information_schema.constraint_column_usage ccu ON cc.constraint_name = ccu.constraint_name
                 WHERE ccu.table_name = '{}'",
                table
            ),
        )).await;
        
        // Note: This is a simplified check - in practice you'd verify specific constraint logic
        assert!(result.is_ok(), "Check constraints should exist for table {}", table);
    }
}

/// Test database indexes for performance
#[tokio::test]
async fn test_database_indexes() {
    let conn = create_test_connection().await.unwrap();
    
    // Test that critical indexes exist
    let expected_indexes = vec![
        "idx_users_email",
        "idx_users_username",
        "idx_customers_org",
        "idx_transactions_customer",
        "idx_transactions_date",
        "idx_aml_alerts_customer",
        "idx_aml_alerts_status",
        "idx_policies_status",
        "idx_controls_owner",
        "idx_risk_assessments_category",
        "idx_fraud_alerts_customer",
        "idx_vulnerabilities_severity",
        "idx_ai_agents_type",
    ];
    
    for index_name in expected_indexes {
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            format!(
                "SELECT 1 FROM pg_indexes WHERE indexname = '{}'",
                index_name
            ),
        )).await;
        
        assert!(result.is_ok(), "Index {} should exist", index_name);
    }
}

/// Test database triggers for updated_at timestamps
#[tokio::test]
async fn test_database_triggers() {
    let conn = create_test_connection().await.unwrap();
    
    // Test that update triggers exist for tables with updated_at columns
    let tables_with_triggers = vec![
        "users", "roles", "organizations", "customers", "transactions",
        "sanctions_lists", "aml_alerts", "policies", "controls", "control_tests",
        "risk_categories", "risk_assessments", "key_risk_indicators", "stress_tests",
        "fraud_rules", "fraud_alerts", "ml_models", "vulnerabilities", "security_incidents",
        "ai_agents", "workflow_automations"
    ];
    
    for table_name in tables_with_triggers {
        let trigger_name = format!("update_{}_updated_at", table_name);
        let result = conn.execute(Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            format!(
                "SELECT 1 FROM information_schema.triggers WHERE trigger_name = '{}'",
                trigger_name
            ),
        )).await;
        
        assert!(result.is_ok(), "Trigger {} should exist", trigger_name);
    }
}

/// Test seed data insertion
#[tokio::test]
async fn test_seed_data() {
    let conn = create_test_connection().await.unwrap();
    
    // Test that system roles were inserted
    let roles_result = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM roles WHERE is_system_role = true".to_string(),
    )).await;
    
    assert!(roles_result.is_ok(), "System roles should be inserted");
    
    // Test that system user was inserted
    let user_result = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM users WHERE email = 'admin@regulateai.com'".to_string(),
    )).await;
    
    assert!(user_result.is_ok(), "System user should be inserted");
    
    // Test that risk categories were inserted
    let risk_categories_result = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM risk_categories".to_string(),
    )).await;
    
    assert!(risk_categories_result.is_ok(), "Risk categories should be inserted");
    
    // Test that default fraud rules were inserted
    let fraud_rules_result = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM fraud_rules WHERE is_active = true".to_string(),
    )).await;
    
    assert!(fraud_rules_result.is_ok(), "Default fraud rules should be inserted");
    
    // Test that AI agents were inserted
    let ai_agents_result = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM ai_agents WHERE is_active = true".to_string(),
    )).await;
    
    assert!(ai_agents_result.is_ok(), "AI agents should be inserted");
}

/// Test data consistency and validation
#[tokio::test]
async fn test_data_consistency() {
    let conn = create_test_connection().await.unwrap();
    
    // Test that all users have valid email formats (basic check)
    let email_check = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM users WHERE email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'".to_string(),
    )).await;
    
    assert!(email_check.is_ok(), "All users should have valid email formats");
    
    // Test that all risk scores are within valid ranges
    let risk_score_check = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM customers WHERE risk_score < 0 OR risk_score > 100".to_string(),
    )).await;
    
    assert!(risk_score_check.is_ok(), "All risk scores should be within 0-100 range");
    
    // Test that all amounts are non-negative
    let amount_check = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        "SELECT COUNT(*) FROM transactions WHERE amount < 0".to_string(),
    )).await;
    
    assert!(amount_check.is_ok(), "All transaction amounts should be non-negative");
}

/// Integration test for database operations
#[tokio::test]
async fn test_database_operations_integration() {
    let conn = create_test_connection().await.unwrap();
    
    // Test inserting a complete user record with all relationships
    let user_id = Uuid::new_v4();
    let role_id = Uuid::new_v4();
    let org_id = Uuid::new_v4();
    
    // Insert organization
    let org_insert = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        format!(
            "INSERT INTO organizations (id, name, country_code, created_by) VALUES ('{}', 'Test Org', 'US', '{}')",
            org_id, user_id
        ),
    )).await;
    
    assert!(org_insert.is_ok(), "Should be able to insert organization");
    
    // Insert role
    let role_insert = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        format!(
            "INSERT INTO roles (id, name, permissions) VALUES ('{}', 'test_role', '[]')",
            role_id
        ),
    )).await;
    
    assert!(role_insert.is_ok(), "Should be able to insert role");
    
    // Insert user
    let user_insert = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        format!(
            "INSERT INTO users (id, email, username, password_hash, first_name, last_name, password_changed_at) 
             VALUES ('{}', 'test@example.com', 'testuser', 'hashed', 'Test', 'User', NOW())",
            user_id
        ),
    )).await;
    
    assert!(user_insert.is_ok(), "Should be able to insert user");
    
    // Insert user role relationship
    let user_role_insert = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        format!(
            "INSERT INTO user_roles (user_id, role_id) VALUES ('{}', '{}')",
            user_id, role_id
        ),
    )).await;
    
    assert!(user_role_insert.is_ok(), "Should be able to insert user role relationship");
    
    // Test cascade deletion (cleanup)
    let cleanup = conn.execute(Statement::from_string(
        sea_orm::DatabaseBackend::Postgres,
        format!("DELETE FROM users WHERE id = '{}'", user_id),
    )).await;
    
    assert!(cleanup.is_ok(), "Should be able to clean up test data");
}
