//! Comprehensive AML service tests
//! 
//! This test suite validates the AML service implementation including
//! customer onboarding, transaction monitoring, sanctions screening,
//! and alert management as required by the development rules.

use chrono::{NaiveDate, Utc};
use regulateai_aml_service::{
    models::*,
    services::AmlService,
    screening::SanctionsScreener,
    monitoring::TransactionMonitor,
    repositories::*,
};
use regulateai_config::{AppSettings, AmlServiceConfig, ExternalServicesConfig};
use regulateai_database::{create_test_connection, entities::*};
use uuid::Uuid;

/// Test AML service initialization
#[tokio::test]
async fn test_aml_service_initialization() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db,
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();
    
    // Test health check
    assert!(aml_service.health_check().await.unwrap());
}

/// Test customer onboarding flow
#[tokio::test]
async fn test_customer_onboarding_flow() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db,
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // Create customer onboarding request
    let onboarding_request = CustomerOnboardingRequest {
        customer_type: CustomerType::Individual,
        first_name: "John".to_string(),
        last_name: "Doe".to_string(),
        date_of_birth: Some(NaiveDate::from_ymd_opt(1990, 1, 1).unwrap()),
        nationality: Some("US".to_string()),
        email: "john.doe@example.com".to_string(),
        identification_documents: vec![
            IdentificationDocument {
                document_type: "PASSPORT".to_string(),
                document_number: "P123456789".to_string(),
                issuing_country: "US".to_string(),
                issue_date: Some(NaiveDate::from_ymd_opt(2020, 1, 1).unwrap()),
                expiry_date: Some(NaiveDate::from_ymd_opt(2030, 1, 1).unwrap()),
                document_image_url: None,
            }
        ],
        address: AddressInfo {
            street_address: "123 Main St".to_string(),
            city: "New York".to_string(),
            state_province: Some("NY".to_string()),
            postal_code: Some("10001".to_string()),
            country: "US".to_string(),
        },
        contact_info: ContactInfo {
            email: "john.doe@example.com".to_string(),
            phone: Some("+1234567890".to_string()),
            mobile: None,
        },
        organization_id: None,
    };

    // Test customer onboarding
    let onboarding_result = aml_service.onboard_customer(onboarding_request).await.unwrap();
    
    assert_ne!(onboarding_result.customer_id, Uuid::nil());
    assert!(matches!(onboarding_result.status, OnboardingStatus::Approved | OnboardingStatus::PendingReview));
    assert_ne!(onboarding_result.risk_level, RiskLevel::Critical); // Should not be critical for clean customer
    assert_eq!(onboarding_result.sanctions_status, SanctionsStatus::Clear);
}

/// Test transaction monitoring
#[tokio::test]
async fn test_transaction_monitoring() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db.clone(),
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // First create a customer
    let customer_request = CreateCustomerRequest {
        customer_type: CustomerType::Individual,
        first_name: "Jane".to_string(),
        last_name: "Smith".to_string(),
        date_of_birth: Some(NaiveDate::from_ymd_opt(1985, 5, 15).unwrap()),
        nationality: Some("US".to_string()),
        identification_documents: vec![],
        address: AddressInfo {
            street_address: "456 Oak Ave".to_string(),
            city: "Los Angeles".to_string(),
            state_province: Some("CA".to_string()),
            postal_code: Some("90210".to_string()),
            country: "US".to_string(),
        },
        contact_info: ContactInfo {
            email: "jane.smith@example.com".to_string(),
            phone: Some("+1987654321".to_string()),
            mobile: None,
        },
        organization_id: None,
    };

    let customer_repo = CustomerRepository::new(db.clone());
    let customer = customer_repo.create_customer(customer_request).await.unwrap();

    // Create a high-value transaction
    let transaction_request = CreateTransactionRequest {
        customer_id: customer.id,
        transaction_type: "WIRE_TRANSFER".to_string(),
        amount: 15000.0, // High value to trigger monitoring
        currency: "USD".to_string(),
        description: Some("Large wire transfer".to_string()),
        counterparty_name: Some("Test Counterparty".to_string()),
        counterparty_account: Some("123456789".to_string()),
        counterparty_bank: Some("Test Bank".to_string()),
        counterparty_country: Some("US".to_string()),
        transaction_date: Utc::now(),
        value_date: Some(Utc::now().date_naive()),
        reference_number: Some("REF123456".to_string()),
        channel: Some("ONLINE".to_string()),
    };

    let transaction_repo = TransactionRepository::new(db.clone());
    let transaction = transaction_repo.create_transaction(transaction_request).await.unwrap();

    // Monitor the transaction
    let monitoring_result = aml_service.monitor_transaction(transaction.id).await.unwrap();
    
    assert_eq!(monitoring_result.transaction_id, transaction.id);
    assert!(monitoring_result.risk_score > 0.0);
    // High value transaction should trigger at least one rule
    assert!(!monitoring_result.triggered_rules.is_empty());
    
    // Check if high value rule was triggered
    let high_value_rule_triggered = monitoring_result.triggered_rules
        .iter()
        .any(|rule| rule.rule_name == "High Value Transaction");
    assert!(high_value_rule_triggered);
}

/// Test sanctions screening
#[tokio::test]
async fn test_sanctions_screening() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    // Create sanctions screener
    let sanctions_repo = std::sync::Arc::new(SanctionsRepository::new(db.clone()));
    let screener = SanctionsScreener::new(sanctions_repo.clone(), settings.external_services.ofac);

    // Add a test sanctions entry
    sanctions_repo.upsert_sanctions_entry(
        "TEST_SDN".to_string(),
        "TEST".to_string(),
        "INDIVIDUAL".to_string(),
        "John Doe".to_string(),
        serde_json::json!(["Johnny Doe", "J. Doe"]),
        serde_json::json!([]),
        serde_json::json!([]),
    ).await.unwrap();

    // Test exact match
    let screening_result = screener.screen_name("John Doe").await.unwrap();
    assert!(screening_result.is_match);
    assert_eq!(screening_result.match_score, 100.0);
    assert!(screening_result.matched_lists.contains(&"TEST_SDN".to_string()));

    // Test no match
    let no_match_result = screener.screen_name("Jane Smith").await.unwrap();
    assert!(!no_match_result.is_match);
    assert_eq!(no_match_result.match_score, 0.0);
    assert!(no_match_result.matched_lists.is_empty());

    // Test fuzzy match
    let fuzzy_result = screener.screen_name("Jon Doe").await.unwrap(); // Slight misspelling
    // Should have some match score due to fuzzy matching
    assert!(fuzzy_result.match_score > 0.0);
}

/// Test alert management
#[tokio::test]
async fn test_alert_management() {
    let db = create_test_connection().await.unwrap();
    let alert_repo = AlertRepository::new(db);

    // Create an alert
    let alert_request = CreateAlertRequest {
        alert_type: "HIGH_VALUE_TRANSACTION".to_string(),
        severity: AlertSeverity::High,
        customer_id: Some(Uuid::new_v4()),
        transaction_id: Some(Uuid::new_v4()),
        rule_name: Some("High Value Transaction Rule".to_string()),
        description: "Transaction amount exceeds threshold".to_string(),
        risk_score: Some(85.0),
        metadata: serde_json::json!({
            "threshold": 10000.0,
            "actual_amount": 15000.0
        }),
    };

    let alert = alert_repo.create_alert(alert_request).await.unwrap();
    
    assert_eq!(alert.alert_type, "HIGH_VALUE_TRANSACTION");
    assert_eq!(alert.severity, "HIGH");
    assert_eq!(alert.status, "OPEN");
    assert!(alert.risk_score.is_some());

    // Update alert status
    let updated_alert = alert_repo.update_alert_status(
        alert.id,
        "INVESTIGATING".to_string(),
        Some(Uuid::new_v4()),
        Some("Starting investigation".to_string()),
    ).await.unwrap();

    assert_eq!(updated_alert.status, "INVESTIGATING");
    assert!(updated_alert.assigned_to.is_some());
    assert!(updated_alert.investigation_notes.is_some());

    // Close alert
    let closed_alert = alert_repo.update_alert_status(
        alert.id,
        "CLOSED".to_string(),
        updated_alert.assigned_to,
        Some("Investigation completed - false positive".to_string()),
    ).await.unwrap();

    assert_eq!(closed_alert.status, "CLOSED");
    assert!(closed_alert.closed_at.is_some());
}

/// Test bulk transaction monitoring
#[tokio::test]
async fn test_bulk_transaction_monitoring() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db.clone(),
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // Create test customer
    let customer_repo = CustomerRepository::new(db.clone());
    let customer_request = CreateCustomerRequest {
        customer_type: CustomerType::Individual,
        first_name: "Test".to_string(),
        last_name: "User".to_string(),
        date_of_birth: Some(NaiveDate::from_ymd_opt(1980, 1, 1).unwrap()),
        nationality: Some("US".to_string()),
        identification_documents: vec![],
        address: AddressInfo {
            street_address: "123 Test St".to_string(),
            city: "Test City".to_string(),
            state_province: Some("TS".to_string()),
            postal_code: Some("12345".to_string()),
            country: "US".to_string(),
        },
        contact_info: ContactInfo {
            email: "test@example.com".to_string(),
            phone: None,
            mobile: None,
        },
        organization_id: None,
    };

    let customer = customer_repo.create_customer(customer_request).await.unwrap();

    // Create multiple transactions
    let transaction_repo = TransactionRepository::new(db.clone());
    let mut transaction_ids = Vec::new();

    for i in 0..5 {
        let transaction_request = CreateTransactionRequest {
            customer_id: customer.id,
            transaction_type: "TRANSFER".to_string(),
            amount: (i + 1) as f64 * 1000.0, // Varying amounts
            currency: "USD".to_string(),
            description: Some(format!("Test transaction {}", i + 1)),
            counterparty_name: Some("Test Counterparty".to_string()),
            counterparty_account: None,
            counterparty_bank: None,
            counterparty_country: Some("US".to_string()),
            transaction_date: Utc::now(),
            value_date: None,
            reference_number: Some(format!("REF{}", i + 1)),
            channel: Some("API".to_string()),
        };

        let transaction = transaction_repo.create_transaction(transaction_request).await.unwrap();
        transaction_ids.push(transaction.id);
    }

    // Bulk monitor transactions
    let bulk_result = aml_service.bulk_monitor_transactions(transaction_ids.clone()).await.unwrap();
    
    assert_eq!(bulk_result.total_processed, 5);
    assert_eq!(bulk_result.successful, 5);
    assert_eq!(bulk_result.failed, 0);
    assert_eq!(bulk_result.results.len(), 5);

    // Check that all transactions were processed
    for result in &bulk_result.results {
        assert_eq!(result.status, "completed");
        assert!(transaction_ids.contains(&result.transaction_id));
    }
}

/// Test customer risk assessment
#[tokio::test]
async fn test_customer_risk_assessment() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db.clone(),
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // Create customer
    let customer_repo = CustomerRepository::new(db.clone());
    let customer_request = CreateCustomerRequest {
        customer_type: CustomerType::Individual,
        first_name: "Risk".to_string(),
        last_name: "Assessment".to_string(),
        date_of_birth: Some(NaiveDate::from_ymd_opt(1975, 6, 15).unwrap()),
        nationality: Some("US".to_string()),
        identification_documents: vec![],
        address: AddressInfo {
            street_address: "789 Risk Ave".to_string(),
            city: "Assessment City".to_string(),
            state_province: Some("AC".to_string()),
            postal_code: Some("54321".to_string()),
            country: "US".to_string(),
        },
        contact_info: ContactInfo {
            email: "risk@example.com".to_string(),
            phone: None,
            mobile: None,
        },
        organization_id: None,
    };

    let customer = customer_repo.create_customer(customer_request).await.unwrap();

    // Assess customer risk
    let risk_assessment = aml_service.risk_service.assess_customer_risk(customer.id, None).await.unwrap();
    
    assert_eq!(risk_assessment.customer_id, customer.id);
    assert!(risk_assessment.risk_score >= 0.0 && risk_assessment.risk_score <= 100.0);
    assert!(matches!(risk_assessment.risk_level, RiskLevel::Low | RiskLevel::Medium | RiskLevel::High | RiskLevel::Critical));
    assert!(!risk_assessment.risk_factors.is_empty());
    assert!(risk_assessment.next_review_date > risk_assessment.assessment_timestamp);
}

/// Test SAR generation
#[tokio::test]
async fn test_sar_generation() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db.clone(),
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // Create SAR generation request
    let sar_request = SarGenerationRequest {
        customer_id: Some(Uuid::new_v4()),
        transaction_id: Some(Uuid::new_v4()),
        alert_ids: vec![Uuid::new_v4()],
        suspicious_activity_description: "Multiple high-value transactions in short timeframe".to_string(),
        filing_reason: "Unusual transaction patterns".to_string(),
        reporter_id: Uuid::new_v4(),
    };

    // Generate SAR
    let sar_report = aml_service.generate_sar(sar_request).await.unwrap();
    
    assert!(!sar_report.sar_id.is_empty());
    assert_eq!(sar_report.status, SarStatus::Draft);
    assert!(!sar_report.suspicious_activity_description.is_empty());
    assert!(!sar_report.filing_reason.is_empty());
}

/// Test risk summary report
#[tokio::test]
async fn test_risk_summary_report() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db.clone(),
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // Create risk summary request
    let request = RiskSummaryRequest {
        start_date: Utc::now() - chrono::Duration::days(30),
        end_date: Utc::now(),
        organization_id: None,
        risk_levels: Some(vec![RiskLevel::High, RiskLevel::Critical]),
    };

    // Generate risk summary report
    let report = aml_service.get_risk_summary_report(request).await.unwrap();
    
    assert!(report.report_period.start_date <= report.report_period.end_date);
    assert!(report.total_customers >= 0);
    assert!(report.risk_distribution.low >= 0);
    assert!(report.risk_distribution.medium >= 0);
    assert!(report.risk_distribution.high >= 0);
    assert!(report.risk_distribution.critical >= 0);
    assert!(report.compliance_metrics.kyc_completion_rate >= 0.0);
    assert!(report.compliance_metrics.kyc_completion_rate <= 1.0);
}

/// Integration test for complete AML workflow
#[tokio::test]
async fn test_complete_aml_workflow() {
    let settings = AppSettings::default();
    let db = create_test_connection().await.unwrap();
    
    let aml_service = AmlService::new(
        db.clone(),
        settings.external_services,
        settings.services.aml,
    ).await.unwrap();

    // Step 1: Customer onboarding
    let onboarding_request = CustomerOnboardingRequest {
        customer_type: CustomerType::Individual,
        first_name: "Complete".to_string(),
        last_name: "Workflow".to_string(),
        date_of_birth: Some(NaiveDate::from_ymd_opt(1988, 3, 20).unwrap()),
        nationality: Some("US".to_string()),
        email: "complete.workflow@example.com".to_string(),
        identification_documents: vec![],
        address: AddressInfo {
            street_address: "999 Workflow St".to_string(),
            city: "Integration City".to_string(),
            state_province: Some("IC".to_string()),
            postal_code: Some("99999".to_string()),
            country: "US".to_string(),
        },
        contact_info: ContactInfo {
            email: "complete.workflow@example.com".to_string(),
            phone: Some("+1555123456".to_string()),
            mobile: None,
        },
        organization_id: None,
    };

    let onboarding_result = aml_service.onboard_customer(onboarding_request).await.unwrap();
    assert!(matches!(onboarding_result.status, OnboardingStatus::Approved | OnboardingStatus::PendingReview));

    // Step 2: Create and monitor transaction
    let transaction_request = CreateTransactionRequest {
        customer_id: onboarding_result.customer_id,
        transaction_type: "WIRE_TRANSFER".to_string(),
        amount: 12000.0, // High value
        currency: "USD".to_string(),
        description: Some("Integration test transaction".to_string()),
        counterparty_name: Some("Integration Counterparty".to_string()),
        counterparty_account: Some("987654321".to_string()),
        counterparty_bank: Some("Integration Bank".to_string()),
        counterparty_country: Some("US".to_string()),
        transaction_date: Utc::now(),
        value_date: Some(Utc::now().date_naive()),
        reference_number: Some("INTEG123".to_string()),
        channel: Some("BRANCH".to_string()),
    };

    let transaction_repo = TransactionRepository::new(db.clone());
    let transaction = transaction_repo.create_transaction(transaction_request).await.unwrap();

    // Step 3: Monitor transaction
    let monitoring_result = aml_service.monitor_transaction(transaction.id).await.unwrap();
    assert!(monitoring_result.risk_score > 0.0);

    // Step 4: If alerts were generated, verify they exist
    if monitoring_result.is_suspicious {
        let alert_repo = AlertRepository::new(db.clone());
        let (alerts, _) = alert_repo.list_alerts(0, 10, None, None, Some(onboarding_result.customer_id)).await.unwrap();
        assert!(!alerts.is_empty());
    }

    // Step 5: Generate risk summary
    let risk_summary_request = RiskSummaryRequest {
        start_date: Utc::now() - chrono::Duration::hours(1),
        end_date: Utc::now(),
        organization_id: None,
        risk_levels: None,
    };

    let risk_summary = aml_service.get_risk_summary_report(risk_summary_request).await.unwrap();
    assert!(risk_summary.total_customers >= 1); // At least our test customer

    println!("Complete AML workflow test passed successfully!");
}
