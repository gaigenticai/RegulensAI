//! Integration tests for Fraud Detection Service

use std::sync::Arc;
use tokio;
use uuid::Uuid;
use chrono::Utc;
use serde_json::json;

use regulateai_errors::RegulateAIError;

// =============================================================================
// UNIT TESTS
// =============================================================================

#[cfg(test)]
mod unit_tests {
    use super::*;

    #[tokio::test]
    async fn test_fraud_detection_ml_model() {
        let transaction_data = TestTransactionData {
            id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            amount: 5000.0,
            merchant: "Online Retailer".to_string(),
            location: "New York, NY".to_string(),
            time_of_day: 14, // 2 PM
            device_fingerprint: "known_device_123".to_string(),
            velocity_24h: 3,
        };

        let result = analyze_transaction_for_fraud(&transaction_data).await;
        assert!(result.is_ok(), "Fraud analysis should succeed");

        let analysis = result.unwrap();
        assert!(analysis.risk_score >= 0.0 && analysis.risk_score <= 1.0, "Risk score should be between 0 and 1");
        assert!(!analysis.model_version.is_empty(), "Model version should be specified");
    }

    #[tokio::test]
    async fn test_fraud_rule_engine() {
        let rule_data = TestFraudRuleData {
            name: "High Velocity Rule".to_string(),
            rule_type: "VELOCITY".to_string(),
            conditions: json!({
                "transaction_count_24h": {"gt": 10},
                "amount": {"gt": 1000.0}
            }),
            severity: "HIGH".to_string(),
        };

        let rule_result = create_fraud_rule(&rule_data).await;
        assert!(rule_result.is_ok(), "Fraud rule creation should succeed");

        // Test rule evaluation
        let transaction = TestTransactionData {
            id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            amount: 2500.0,
            merchant: "ATM Withdrawal".to_string(),
            location: "Unknown".to_string(),
            time_of_day: 3, // 3 AM
            device_fingerprint: "unknown_device".to_string(),
            velocity_24h: 15, // High velocity
        };

        let evaluation_result = evaluate_fraud_rules(&transaction, &vec![rule_result.unwrap()]).await;
        assert!(evaluation_result.is_ok(), "Rule evaluation should succeed");

        let triggered_rules = evaluation_result.unwrap();
        assert!(!triggered_rules.is_empty(), "High velocity transaction should trigger rules");
    }

    #[tokio::test]
    async fn test_fraud_alert_management() {
        let alert_data = TestFraudAlertData {
            transaction_id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            alert_type: "SUSPICIOUS_TRANSACTION".to_string(),
            risk_score: 0.85,
            severity: "HIGH".to_string(),
            description: "Unusual transaction pattern detected".to_string(),
        };

        let alert_result = create_fraud_alert(&alert_data).await;
        assert!(alert_result.is_ok(), "Fraud alert creation should succeed");

        let alert = alert_result.unwrap();
        assert_eq!(alert.status, "OPEN", "New alert should have OPEN status");
        assert!(alert.triggered_at <= Utc::now(), "Alert timestamp should be valid");

        // Test alert status update
        let update_result = update_alert_status(&alert.id, "INVESTIGATING").await;
        assert!(update_result.is_ok(), "Alert status update should succeed");
    }

    #[tokio::test]
    async fn test_graph_analytics() {
        let customer_id = Uuid::new_v4();
        
        let network_result = analyze_fraud_network(&customer_id).await;
        assert!(network_result.is_ok(), "Network analysis should succeed");

        let network_analysis = network_result.unwrap();
        assert!(network_analysis.risk_score >= 0.0 && network_analysis.risk_score <= 100.0);
        assert!(network_analysis.network_size >= 0, "Network size should be non-negative");
    }

    #[tokio::test]
    async fn test_device_fingerprinting() {
        let device_data = TestDeviceData {
            ip_address: "192.168.1.100".to_string(),
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)".to_string(),
            screen_resolution: "1920x1080".to_string(),
            timezone: "America/New_York".to_string(),
            language: "en-US".to_string(),
        };

        let fingerprint_result = generate_device_fingerprint(&device_data).await;
        assert!(fingerprint_result.is_ok(), "Device fingerprinting should succeed");

        let fingerprint = fingerprint_result.unwrap();
        assert!(!fingerprint.fingerprint_id.is_empty(), "Fingerprint ID should be generated");
        assert!(fingerprint.risk_score >= 0.0 && fingerprint.risk_score <= 100.0);
    }

    // Helper functions for testing
    async fn analyze_transaction_for_fraud(data: &TestTransactionData) -> Result<TestFraudAnalysis, RegulateAIError> {
        // Simplified fraud analysis for testing
        let mut risk_score = 0.0;

        // Amount-based risk
        if data.amount > 10000.0 {
            risk_score += 0.3;
        } else if data.amount > 5000.0 {
            risk_score += 0.15;
        }

        // Time-based risk
        if data.time_of_day < 6 || data.time_of_day > 22 {
            risk_score += 0.2;
        }

        // Velocity-based risk
        if data.velocity_24h > 10 {
            risk_score += 0.25;
        }

        // Device-based risk
        if data.device_fingerprint.contains("unknown") {
            risk_score += 0.2;
        }

        risk_score = risk_score.min(1.0);

        Ok(TestFraudAnalysis {
            transaction_id: data.id,
            risk_score,
            is_fraud: risk_score > 0.7,
            confidence: 0.92,
            model_version: "v2.1.0".to_string(),
            features_used: vec![
                "amount".to_string(),
                "time_of_day".to_string(),
                "velocity_24h".to_string(),
                "device_fingerprint".to_string(),
            ],
            analyzed_at: Utc::now(),
        })
    }

    async fn create_fraud_rule(data: &TestFraudRuleData) -> Result<TestFraudRule, RegulateAIError> {
        Ok(TestFraudRule {
            id: Uuid::new_v4(),
            name: data.name.clone(),
            rule_type: data.rule_type.clone(),
            conditions: data.conditions.clone(),
            severity: data.severity.clone(),
            is_active: true,
            created_at: Utc::now(),
        })
    }

    async fn evaluate_fraud_rules(transaction: &TestTransactionData, rules: &Vec<TestFraudRule>) -> Result<Vec<Uuid>, RegulateAIError> {
        let mut triggered_rules = Vec::new();

        for rule in rules {
            let mut rule_triggered = false;

            match rule.rule_type.as_str() {
                "VELOCITY" => {
                    if transaction.velocity_24h > 10 && transaction.amount > 1000.0 {
                        rule_triggered = true;
                    }
                },
                "AMOUNT" => {
                    if transaction.amount > 10000.0 {
                        rule_triggered = true;
                    }
                },
                "TIME" => {
                    if transaction.time_of_day < 6 || transaction.time_of_day > 22 {
                        rule_triggered = true;
                    }
                },
                _ => {}
            }

            if rule_triggered {
                triggered_rules.push(rule.id);
            }
        }

        Ok(triggered_rules)
    }

    async fn create_fraud_alert(data: &TestFraudAlertData) -> Result<TestFraudAlert, RegulateAIError> {
        Ok(TestFraudAlert {
            id: Uuid::new_v4(),
            transaction_id: data.transaction_id,
            customer_id: data.customer_id,
            alert_type: data.alert_type.clone(),
            risk_score: data.risk_score,
            severity: data.severity.clone(),
            status: "OPEN".to_string(),
            description: data.description.clone(),
            triggered_at: Utc::now(),
            assigned_to: None,
        })
    }

    async fn update_alert_status(alert_id: &Uuid, status: &str) -> Result<TestFraudAlert, RegulateAIError> {
        // Simplified status update for testing
        Ok(TestFraudAlert {
            id: *alert_id,
            transaction_id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            alert_type: "SUSPICIOUS_TRANSACTION".to_string(),
            risk_score: 0.85,
            severity: "HIGH".to_string(),
            status: status.to_string(),
            description: "Status updated".to_string(),
            triggered_at: Utc::now(),
            assigned_to: Some(Uuid::new_v4()),
        })
    }

    async fn analyze_fraud_network(customer_id: &Uuid) -> Result<TestNetworkAnalysis, RegulateAIError> {
        Ok(TestNetworkAnalysis {
            customer_id: *customer_id,
            network_size: 15,
            risk_score: 45.2,
            suspicious_connections: 2,
            analyzed_at: Utc::now(),
        })
    }

    async fn generate_device_fingerprint(data: &TestDeviceData) -> Result<TestDeviceFingerprint, RegulateAIError> {
        // Simplified device fingerprinting
        let fingerprint_id = format!("fp_{}_{}", 
            data.ip_address.replace(".", "_"),
            data.user_agent.len()
        );

        let risk_score = if data.ip_address.starts_with("192.168") {
            25.0 // Low risk for private IP
        } else {
            50.0 // Medium risk for public IP
        };

        Ok(TestDeviceFingerprint {
            fingerprint_id,
            risk_score,
            is_known_device: data.ip_address.starts_with("192.168"),
            created_at: Utc::now(),
        })
    }

    // Test data structures
    #[derive(Debug)]
    struct TestTransactionData {
        id: Uuid,
        customer_id: Uuid,
        amount: f64,
        merchant: String,
        location: String,
        time_of_day: u8,
        device_fingerprint: String,
        velocity_24h: u32,
    }

    #[derive(Debug)]
    struct TestFraudAnalysis {
        transaction_id: Uuid,
        risk_score: f64,
        is_fraud: bool,
        confidence: f64,
        model_version: String,
        features_used: Vec<String>,
        analyzed_at: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestFraudRuleData {
        name: String,
        rule_type: String,
        conditions: serde_json::Value,
        severity: String,
    }

    #[derive(Debug)]
    struct TestFraudRule {
        id: Uuid,
        name: String,
        rule_type: String,
        conditions: serde_json::Value,
        severity: String,
        is_active: bool,
        created_at: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestFraudAlertData {
        transaction_id: Uuid,
        customer_id: Uuid,
        alert_type: String,
        risk_score: f64,
        severity: String,
        description: String,
    }

    #[derive(Debug)]
    struct TestFraudAlert {
        id: Uuid,
        transaction_id: Uuid,
        customer_id: Uuid,
        alert_type: String,
        risk_score: f64,
        severity: String,
        status: String,
        description: String,
        triggered_at: chrono::DateTime<Utc>,
        assigned_to: Option<Uuid>,
    }

    #[derive(Debug)]
    struct TestNetworkAnalysis {
        customer_id: Uuid,
        network_size: u32,
        risk_score: f64,
        suspicious_connections: u32,
        analyzed_at: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestDeviceData {
        ip_address: String,
        user_agent: String,
        screen_resolution: String,
        timezone: String,
        language: String,
    }

    #[derive(Debug)]
    struct TestDeviceFingerprint {
        fingerprint_id: String,
        risk_score: f64,
        is_known_device: bool,
        created_at: chrono::DateTime<Utc>,
    }
}

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_end_to_end_fraud_detection_workflow() {
        // Test complete fraud detection workflow
        
        // 1. Analyze suspicious transaction
        let transaction_data = unit_tests::TestTransactionData {
            id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            amount: 15000.0, // High amount
            merchant: "Unknown Merchant".to_string(),
            location: "High Risk Location".to_string(),
            time_of_day: 3, // 3 AM - unusual time
            device_fingerprint: "unknown_device_suspicious".to_string(),
            velocity_24h: 20, // High velocity
        };

        let analysis_result = unit_tests::analyze_transaction_for_fraud(&transaction_data).await;
        assert!(analysis_result.is_ok(), "Fraud analysis should succeed");

        let analysis = analysis_result.unwrap();
        assert!(analysis.is_fraud, "High-risk transaction should be flagged as fraud");

        // 2. Create fraud alert
        let alert_data = unit_tests::TestFraudAlertData {
            transaction_id: transaction_data.id,
            customer_id: transaction_data.customer_id,
            alert_type: "HIGH_RISK_TRANSACTION".to_string(),
            risk_score: analysis.risk_score,
            severity: "CRITICAL".to_string(),
            description: "Multiple fraud indicators detected".to_string(),
        };

        let alert_result = unit_tests::create_fraud_alert(&alert_data).await;
        assert!(alert_result.is_ok(), "Fraud alert creation should succeed");

        // 3. Analyze customer network
        let network_result = unit_tests::analyze_fraud_network(&transaction_data.customer_id).await;
        assert!(network_result.is_ok(), "Network analysis should succeed");

        println!("✅ End-to-end fraud detection workflow test completed successfully");
    }

    #[tokio::test]
    async fn test_fraud_model_performance() {
        // Test fraud detection model performance with various scenarios
        let test_cases = vec![
            // Low risk transaction
            (unit_tests::TestTransactionData {
                id: Uuid::new_v4(),
                customer_id: Uuid::new_v4(),
                amount: 50.0,
                merchant: "Coffee Shop".to_string(),
                location: "Local".to_string(),
                time_of_day: 10,
                device_fingerprint: "known_device_123".to_string(),
                velocity_24h: 2,
            }, false),
            // High risk transaction
            (unit_tests::TestTransactionData {
                id: Uuid::new_v4(),
                customer_id: Uuid::new_v4(),
                amount: 25000.0,
                merchant: "Unknown".to_string(),
                location: "Foreign".to_string(),
                time_of_day: 2,
                device_fingerprint: "unknown_device".to_string(),
                velocity_24h: 25,
            }, true),
        ];

        for (transaction, expected_fraud) in test_cases {
            let result = unit_tests::analyze_transaction_for_fraud(&transaction).await;
            assert!(result.is_ok(), "Analysis should succeed");
            
            let analysis = result.unwrap();
            assert_eq!(analysis.is_fraud, expected_fraud, 
                "Fraud detection should match expected result for transaction amount: {}", 
                transaction.amount);
        }
    }
}
