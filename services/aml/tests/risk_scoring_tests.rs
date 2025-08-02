//! Risk Scoring Module Tests
//! 
//! Comprehensive test suite for the AML risk scoring engine including:
//! - Customer risk assessment tests
//! - Transaction risk assessment tests
//! - Risk calculation algorithm tests
//! - Geographic and industry risk tests
//! - Behavioral pattern analysis tests

use std::collections::HashMap;
use tokio;
use uuid::Uuid;
use chrono::{Utc, Duration};
use serde_json::json;

use regulateai_errors::RegulateAIError;
use crate::risk_scoring::{
    RiskScoringEngine, RiskScoringConfig, RiskCalculationMethod, RiskThresholds,
    BehavioralAnalysisConfig, RiskLevel, RiskFactorType, CustomerRiskAssessment,
    TransactionRiskAssessment,
};
use crate::models::{Customer, Transaction, RiskFactor};

// =============================================================================
// UNIT TESTS
// =============================================================================

#[cfg(test)]
mod unit_tests {
    use super::*;

    #[tokio::test]
    async fn test_customer_risk_assessment_low_risk() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let customer = create_test_customer("INDIVIDUAL", Some("US".to_string()), Some("TECHNOLOGY".to_string()));
        let transactions = create_test_transactions(5, 1000.0, "USD");
        
        let result = engine.assess_customer_risk(&customer, &transactions).await;
        assert!(result.is_ok(), "Customer risk assessment should succeed");
        
        let assessment = result.unwrap();
        assert_eq!(assessment.customer_id, customer.id);
        assert!(assessment.assessment.overall_score >= 0.0 && assessment.assessment.overall_score <= 100.0);
        assert_eq!(assessment.assessment.risk_level, RiskLevel::Low);
        assert!(!assessment.assessment.risk_factors.is_empty());
        assert!(!assessment.mitigation_measures.is_empty());
    }

    #[tokio::test]
    async fn test_customer_risk_assessment_high_risk() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let customer = create_test_customer("PEP", Some("AF".to_string()), Some("CRYPTO".to_string()));
        let transactions = create_test_transactions(50, 50000.0, "USD");
        
        let result = engine.assess_customer_risk(&customer, &transactions).await;
        assert!(result.is_ok(), "High-risk customer assessment should succeed");
        
        let assessment = result.unwrap();
        assert!(assessment.assessment.overall_score > 70.0);
        assert!(matches!(assessment.assessment.risk_level, RiskLevel::High | RiskLevel::VeryHigh));
        
        // Verify risk factors include high-risk elements
        let risk_factors: Vec<_> = assessment.assessment.risk_factors.iter()
            .map(|f| &f.factor_type)
            .collect();
        assert!(risk_factors.contains(&&RiskFactorType::Geographic));
        assert!(risk_factors.contains(&&RiskFactorType::CustomerType));
        assert!(risk_factors.contains(&&RiskFactorType::Industry));
    }

    #[tokio::test]
    async fn test_transaction_risk_assessment_normal() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let customer = create_test_customer("INDIVIDUAL", Some("US".to_string()), Some("TECHNOLOGY".to_string()));
        let transaction = create_single_transaction(5000.0, "USD", Some("US".to_string()));
        
        let result = engine.assess_transaction_risk(&transaction, &customer).await;
        assert!(result.is_ok(), "Transaction risk assessment should succeed");
        
        let assessment = result.unwrap();
        assert_eq!(assessment.transaction_id, transaction.id);
        assert!(assessment.assessment.overall_score >= 0.0 && assessment.assessment.overall_score <= 100.0);
        assert!(!assessment.requires_review);
        assert!(assessment.suspicious_indicators.is_empty());
    }

    #[tokio::test]
    async fn test_transaction_risk_assessment_high_amount() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let customer = create_test_customer("INDIVIDUAL", Some("US".to_string()), Some("TECHNOLOGY".to_string()));
        let transaction = create_single_transaction(150000.0, "USD", Some("AF".to_string()));
        
        let result = engine.assess_transaction_risk(&transaction, &customer).await;
        assert!(result.is_ok(), "High-amount transaction assessment should succeed");
        
        let assessment = result.unwrap();
        assert!(assessment.assessment.overall_score > 50.0);
        assert!(assessment.requires_review);
        assert!(!assessment.suspicious_indicators.is_empty());
        
        // Should have suspicious indicator for high-risk jurisdiction
        let has_jurisdiction_indicator = assessment.suspicious_indicators.iter()
            .any(|indicator| indicator.contains("high-risk jurisdiction"));
        assert!(has_jurisdiction_indicator, "Should flag high-risk jurisdiction");
    }

    #[tokio::test]
    async fn test_risk_calculation_methods() {
        let mut config = create_test_config();
        let risk_factors = create_test_risk_factors();
        
        // Test weighted average method
        config.calculation_method = RiskCalculationMethod::WeightedAverage;
        let engine = RiskScoringEngine::new(config.clone());
        let weighted_result = engine.calculate_risk_score(&risk_factors);
        assert!(weighted_result.is_ok());
        
        // Test maximum risk method
        config.calculation_method = RiskCalculationMethod::MaximumRisk;
        let engine = RiskScoringEngine::new(config.clone());
        let max_result = engine.calculate_risk_score(&risk_factors);
        assert!(max_result.is_ok());
        
        // Test Bayesian inference method
        config.calculation_method = RiskCalculationMethod::BayesianInference;
        let engine = RiskScoringEngine::new(config);
        let bayesian_result = engine.calculate_risk_score(&risk_factors);
        assert!(bayesian_result.is_ok());
        
        // Verify different methods produce different scores
        let weighted_score = weighted_result.unwrap().overall_score;
        let max_score = max_result.unwrap().overall_score;
        let bayesian_score = bayesian_result.unwrap().overall_score;
        
        // Maximum risk should be highest
        assert!(max_score >= weighted_score);
        assert!(max_score >= bayesian_score);
    }

    #[tokio::test]
    async fn test_geographic_risk_assessment() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        // Test low-risk country
        let low_risk_result = engine.assess_geographic_risk("US");
        assert!(low_risk_result.is_ok());
        let low_risk_factor = low_risk_result.unwrap();
        assert!(low_risk_factor.score < 50.0);
        
        // Test high-risk country
        let high_risk_result = engine.assess_geographic_risk("AF");
        assert!(high_risk_result.is_ok());
        let high_risk_factor = high_risk_result.unwrap();
        assert!(high_risk_factor.score > 80.0);
        
        // Test unknown country (should default to medium risk)
        let unknown_result = engine.assess_geographic_risk("XX");
        assert!(unknown_result.is_ok());
        let unknown_factor = unknown_result.unwrap();
        assert_eq!(unknown_factor.score, 50.0);
    }

    #[tokio::test]
    async fn test_industry_risk_assessment() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        // Test low-risk industry
        let low_risk_result = engine.assess_industry_risk("TECHNOLOGY");
        assert!(low_risk_result.is_ok());
        let low_risk_factor = low_risk_result.unwrap();
        assert!(low_risk_factor.score < 50.0);
        
        // Test high-risk industry
        let high_risk_result = engine.assess_industry_risk("CRYPTO");
        assert!(high_risk_result.is_ok());
        let high_risk_factor = high_risk_result.unwrap();
        assert!(high_risk_factor.score > 80.0);
    }

    #[tokio::test]
    async fn test_customer_type_risk_assessment() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        // Test different customer types
        let individual = create_test_customer("INDIVIDUAL", None, None);
        let individual_risk = engine.assess_customer_type_risk(&individual);
        assert!(individual_risk.is_ok());
        assert!(individual_risk.unwrap().score < 50.0);
        
        let corporate = create_test_customer("CORPORATE", None, None);
        let corporate_risk = engine.assess_customer_type_risk(&corporate);
        assert!(corporate_risk.is_ok());
        assert_eq!(corporate_risk.unwrap().score, 50.0);
        
        let pep = create_test_customer("PEP", None, None);
        let pep_risk = engine.assess_customer_type_risk(&pep);
        assert!(pep_risk.is_ok());
        assert!(pep_risk.unwrap().score > 80.0);
    }

    #[tokio::test]
    async fn test_transaction_pattern_analysis() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        // Test normal transaction patterns
        let normal_transactions = create_test_transactions(10, 5000.0, "USD");
        let normal_result = engine.assess_transaction_patterns(&normal_transactions).await;
        assert!(normal_result.is_ok());
        let normal_factors = normal_result.unwrap();
        assert!(!normal_factors.is_empty());
        
        // Test high-volume patterns
        let high_volume_transactions = create_test_transactions(5, 200000.0, "USD");
        let high_volume_result = engine.assess_transaction_patterns(&high_volume_transactions).await;
        assert!(high_volume_result.is_ok());
        let high_volume_factors = high_volume_result.unwrap();
        
        // High volume should have higher risk scores
        let normal_volume_score = normal_factors.iter()
            .find(|f| f.factor_type == RiskFactorType::Volume)
            .map(|f| f.score)
            .unwrap_or(0.0);
        let high_volume_score = high_volume_factors.iter()
            .find(|f| f.factor_type == RiskFactorType::Volume)
            .map(|f| f.score)
            .unwrap_or(0.0);
        
        assert!(high_volume_score > normal_volume_score);
    }

    #[tokio::test]
    async fn test_risk_level_determination() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        // Test risk level thresholds
        assert_eq!(engine.determine_risk_level(10.0), RiskLevel::Low);
        assert_eq!(engine.determine_risk_level(40.0), RiskLevel::Medium);
        assert_eq!(engine.determine_risk_level(60.0), RiskLevel::High);
        assert_eq!(engine.determine_risk_level(95.0), RiskLevel::VeryHigh);
    }

    #[tokio::test]
    async fn test_next_review_date_calculation() {
        let config = create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let base_date = Utc::now();
        
        // Test different risk levels
        let low_review = engine.calculate_next_review_date(&RiskLevel::Low);
        let medium_review = engine.calculate_next_review_date(&RiskLevel::Medium);
        let high_review = engine.calculate_next_review_date(&RiskLevel::High);
        let very_high_review = engine.calculate_next_review_date(&RiskLevel::VeryHigh);
        
        // Higher risk should have shorter review periods
        assert!(very_high_review < high_review);
        assert!(high_review < medium_review);
        assert!(medium_review < low_review);
        
        // Very high risk should be within 30 days
        assert!(very_high_review <= base_date + Duration::days(30));
    }

    #[tokio::test]
    async fn test_behavioral_analysis_configuration() {
        let mut config = create_test_config();
        config.behavioral_analysis.enabled = true;
        config.behavioral_analysis.min_transactions = 5;
        
        let engine = RiskScoringEngine::new(config);
        let customer = create_test_customer("INDIVIDUAL", Some("US".to_string()), Some("TECHNOLOGY".to_string()));
        
        // Test with sufficient transactions for behavioral analysis
        let sufficient_transactions = create_test_transactions(10, 5000.0, "USD");
        let result = engine.assess_customer_risk(&customer, &sufficient_transactions).await;
        assert!(result.is_ok());
        
        // Test with insufficient transactions
        let insufficient_transactions = create_test_transactions(3, 5000.0, "USD");
        let result2 = engine.assess_customer_risk(&customer, &insufficient_transactions).await;
        assert!(result2.is_ok());
        
        // Both should succeed, but behavioral analysis should only run with sufficient data
        let assessment1 = result.unwrap();
        let assessment2 = result2.unwrap();
        
        // First assessment might have behavioral factors, second should not
        let has_behavioral1 = assessment1.assessment.risk_factors.iter()
            .any(|f| f.factor_type == RiskFactorType::Behavioral);
        let has_behavioral2 = assessment2.assessment.risk_factors.iter()
            .any(|f| f.factor_type == RiskFactorType::Behavioral);
        
        // With sufficient transactions, behavioral analysis should be included
        assert!(has_behavioral1 || assessment1.assessment.risk_factors.len() > assessment2.assessment.risk_factors.len());
    }

    // Helper functions for testing
    fn create_test_config() -> RiskScoringConfig {
        RiskScoringConfig {
            dynamic_scoring_enabled: true,
            calculation_method: RiskCalculationMethod::WeightedAverage,
            risk_thresholds: RiskThresholds {
                low_threshold: 30.0,
                medium_threshold: 50.0,
                high_threshold: 70.0,
                very_high_threshold: 90.0,
            },
            factor_weights: HashMap::new(),
            geographic_multipliers: HashMap::new(),
            industry_multipliers: HashMap::new(),
            behavioral_analysis: BehavioralAnalysisConfig {
                enabled: true,
                velocity_window_days: 30,
                pattern_sensitivity: 0.8,
                min_transactions: 10,
            },
        }
    }
    
    fn create_test_customer(customer_type: &str, country: Option<String>, industry: Option<String>) -> Customer {
        Customer {
            id: Uuid::new_v4(),
            customer_type: customer_type.to_string(),
            first_name: Some("John".to_string()),
            last_name: Some("Doe".to_string()),
            company_name: None,
            date_of_birth: Some(chrono::NaiveDate::from_ymd_opt(1980, 1, 15).unwrap()),
            incorporation_date: None,
            nationality: country.clone(),
            jurisdiction: country,
            risk_rating: "MEDIUM".to_string(),
            kyc_status: "COMPLETED".to_string(),
            kyc_completion_date: Some(Utc::now()),
            next_review_date: Some(Utc::now() + Duration::days(365)),
            pep_status: customer_type == "PEP",
            sanctions_status: "CLEAR".to_string(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: Some(Uuid::new_v4()),
            updated_by: Some(Uuid::new_v4()),
            version: 1,
            metadata: json!({"industry": industry}),
            country_code: country,
            industry_code: industry,
        }
    }
    
    fn create_test_transactions(count: usize, amount: f64, currency: &str) -> Vec<Transaction> {
        (0..count).map(|i| {
            Transaction {
                id: Uuid::new_v4(),
                transaction_reference: format!("TXN_{:06}", i),
                customer_id: Uuid::new_v4(),
                transaction_type: "WIRE_TRANSFER".to_string(),
                amount,
                currency: currency.to_string(),
                transaction_date: Utc::now() - Duration::days(i as i64),
                value_date: Utc::now() - Duration::days(i as i64),
                originator_name: Some("John Doe".to_string()),
                originator_account: Some("1234567890".to_string()),
                beneficiary_name: Some("Jane Smith".to_string()),
                beneficiary_account: Some("0987654321".to_string()),
                originating_country: Some("US".to_string()),
                destination_country: Some("GB".to_string()),
                purpose_code: Some("BUSINESS".to_string()),
                description: Some("Business payment".to_string()),
                channel: "ONLINE".to_string(),
                risk_score: Some(25.0),
                monitoring_status: "COMPLETED".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                version: 1,
                metadata: json!({}),
            }
        }).collect()
    }
    
    fn create_single_transaction(amount: f64, currency: &str, destination_country: Option<String>) -> Transaction {
        Transaction {
            id: Uuid::new_v4(),
            transaction_reference: "TXN_SINGLE".to_string(),
            customer_id: Uuid::new_v4(),
            transaction_type: "WIRE_TRANSFER".to_string(),
            amount,
            currency: currency.to_string(),
            transaction_date: Utc::now(),
            value_date: Utc::now(),
            originator_name: Some("John Doe".to_string()),
            originator_account: Some("1234567890".to_string()),
            beneficiary_name: Some("Jane Smith".to_string()),
            beneficiary_account: Some("0987654321".to_string()),
            originating_country: Some("US".to_string()),
            destination_country,
            purpose_code: Some("BUSINESS".to_string()),
            description: Some("Business payment".to_string()),
            channel: "ONLINE".to_string(),
            risk_score: None,
            monitoring_status: "PENDING".to_string(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            version: 1,
            metadata: json!({}),
        }
    }
    
    fn create_test_risk_factors() -> Vec<RiskFactor> {
        vec![
            RiskFactor {
                factor_type: RiskFactorType::Geographic,
                score: 30.0,
                description: "Geographic risk factor".to_string(),
                weight: 1.0,
                confidence: 0.9,
            },
            RiskFactor {
                factor_type: RiskFactorType::Industry,
                score: 40.0,
                description: "Industry risk factor".to_string(),
                weight: 1.0,
                confidence: 0.8,
            },
            RiskFactor {
                factor_type: RiskFactorType::CustomerType,
                score: 50.0,
                description: "Customer type risk factor".to_string(),
                weight: 1.2,
                confidence: 0.95,
            },
            RiskFactor {
                factor_type: RiskFactorType::Volume,
                score: 60.0,
                description: "Volume risk factor".to_string(),
                weight: 1.0,
                confidence: 0.85,
            },
        ]
    }
}

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_end_to_end_risk_assessment_workflow() {
        // Test complete risk assessment workflow from customer onboarding to ongoing monitoring
        
        let config = unit_tests::create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        // 1. Initial customer risk assessment (onboarding)
        let new_customer = unit_tests::create_test_customer("INDIVIDUAL", Some("US".to_string()), Some("TECHNOLOGY".to_string()));
        let initial_transactions = Vec::new(); // No transaction history yet
        
        let initial_assessment = engine.assess_customer_risk(&new_customer, &initial_transactions).await;
        assert!(initial_assessment.is_ok(), "Initial assessment should succeed");
        
        let initial_result = initial_assessment.unwrap();
        assert_eq!(initial_result.assessment.risk_level, RiskLevel::Low);
        
        // 2. Periodic review with transaction history
        let transactions_6_months = unit_tests::create_test_transactions(50, 10000.0, "USD");
        let periodic_assessment = engine.assess_customer_risk(&new_customer, &transactions_6_months).await;
        assert!(periodic_assessment.is_ok(), "Periodic assessment should succeed");
        
        let periodic_result = periodic_assessment.unwrap();
        // Risk might increase due to transaction patterns
        assert!(periodic_result.assessment.overall_score >= initial_result.assessment.overall_score);
        
        // 3. Event-driven assessment (high-value transaction)
        let high_value_transaction = unit_tests::create_single_transaction(500000.0, "USD", Some("CH".to_string()));
        let transaction_assessment = engine.assess_transaction_risk(&high_value_transaction, &new_customer).await;
        assert!(transaction_assessment.is_ok(), "Transaction assessment should succeed");
        
        let transaction_result = transaction_assessment.unwrap();
        assert!(transaction_result.assessment.overall_score > 70.0);
        assert!(transaction_result.requires_review);
        
        println!("✅ End-to-end risk assessment workflow completed successfully");
    }

    #[tokio::test]
    async fn test_multi_jurisdiction_risk_assessment() {
        // Test risk assessment across multiple jurisdictions
        
        let config = unit_tests::create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let jurisdictions = vec![
            ("US", "TECHNOLOGY", RiskLevel::Low),
            ("GB", "BANKING", RiskLevel::Medium),
            ("AF", "CRYPTO", RiskLevel::VeryHigh),
            ("CH", "REAL_ESTATE", RiskLevel::Medium),
        ];
        
        for (country, industry, expected_min_level) in jurisdictions {
            let customer = unit_tests::create_test_customer("CORPORATE", Some(country.to_string()), Some(industry.to_string()));
            let transactions = unit_tests::create_test_transactions(20, 25000.0, "USD");
            
            let assessment = engine.assess_customer_risk(&customer, &transactions).await;
            assert!(assessment.is_ok(), "Assessment should succeed for {}", country);
            
            let result = assessment.unwrap();
            
            // Verify minimum risk level expectations
            match expected_min_level {
                RiskLevel::VeryHigh => assert!(matches!(result.assessment.risk_level, RiskLevel::VeryHigh)),
                RiskLevel::High => assert!(matches!(result.assessment.risk_level, RiskLevel::High | RiskLevel::VeryHigh)),
                RiskLevel::Medium => assert!(matches!(result.assessment.risk_level, RiskLevel::Medium | RiskLevel::High | RiskLevel::VeryHigh)),
                RiskLevel::Low => {}, // Any level is acceptable for low-risk baseline
            }
            
            println!("✅ Risk assessment completed for {} ({}): {:?}", country, industry, result.assessment.risk_level);
        }
    }

    #[tokio::test]
    async fn test_risk_scoring_performance() {
        // Test performance with large datasets
        
        let config = unit_tests::create_test_config();
        let engine = RiskScoringEngine::new(config);
        
        let start_time = std::time::Instant::now();
        let mut assessments = Vec::new();
        
        // Assess 100 customers with varying profiles
        for i in 0..100 {
            let customer_type = if i % 4 == 0 { "PEP" } else { "INDIVIDUAL" };
            let country = match i % 5 {
                0 => "US",
                1 => "GB", 
                2 => "DE",
                3 => "AF",
                _ => "CH",
            };
            let industry = match i % 3 {
                0 => "TECHNOLOGY",
                1 => "BANKING",
                _ => "CRYPTO",
            };
            
            let customer = unit_tests::create_test_customer(customer_type, Some(country.to_string()), Some(industry.to_string()));
            let transactions = unit_tests::create_test_transactions(i % 50 + 1, (i as f64 + 1.0) * 1000.0, "USD");
            
            let assessment = engine.assess_customer_risk(&customer, &transactions).await;
            assert!(assessment.is_ok(), "Assessment {} should succeed", i);
            assessments.push(assessment.unwrap());
        }
        
        let duration = start_time.elapsed();
        println!("✅ Performance test: 100 risk assessments completed in {:?}", duration);
        
        // Performance should be reasonable (less than 10 seconds for 100 assessments)
        assert!(duration.as_secs() < 10, "Risk assessment should be performant");
        
        // Verify all assessments completed
        assert_eq!(assessments.len(), 100);
        
        // Verify risk distribution makes sense
        let risk_distribution: HashMap<RiskLevel, usize> = assessments.iter()
            .fold(HashMap::new(), |mut acc, assessment| {
                *acc.entry(assessment.assessment.risk_level.clone()).or_insert(0) += 1;
                acc
            });
        
        println!("Risk distribution: {:?}", risk_distribution);
        
        // Should have some variety in risk levels
        assert!(risk_distribution.len() > 1, "Should have variety in risk levels");
    }
}

// =============================================================================
// PERFORMANCE TESTS
// =============================================================================

#[cfg(test)]
mod performance_tests {
    use super::*;
    use std::time::Instant;

    #[tokio::test]
    async fn test_risk_calculation_algorithms_performance() {
        let methods = vec![
            RiskCalculationMethod::WeightedAverage,
            RiskCalculationMethod::MaximumRisk,
            RiskCalculationMethod::BayesianInference,
        ];
        
        let risk_factors = unit_tests::create_test_risk_factors();
        
        for method in methods {
            let mut config = unit_tests::create_test_config();
            config.calculation_method = method.clone();
            let engine = RiskScoringEngine::new(config);
            
            let start = Instant::now();
            
            // Perform 1000 risk calculations
            for _ in 0..1000 {
                let result = engine.calculate_risk_score(&risk_factors);
                assert!(result.is_ok());
            }
            
            let duration = start.elapsed();
            println!("✅ {:?} method: 1,000 calculations in {:?}", method, duration);
            
            // Each method should complete 1000 calculations in under 1 second
            assert!(duration.as_millis() < 1000, "{:?} method should be fast", method);
        }
    }

    #[tokio::test]
    async fn test_concurrent_risk_assessments() {
        let config = unit_tests::create_test_config();
        let engine = std::sync::Arc::new(RiskScoringEngine::new(config));
        
        let start = Instant::now();
        let mut handles = Vec::new();
        
        // Run 50 concurrent risk assessments
        for i in 0..50 {
            let engine_clone = engine.clone();
            let handle = tokio::spawn(async move {
                let customer = unit_tests::create_test_customer("INDIVIDUAL", Some("US".to_string()), Some("TECHNOLOGY".to_string()));
                let transactions = unit_tests::create_test_transactions(10, (i as f64 + 1.0) * 1000.0, "USD");
                
                engine_clone.assess_customer_risk(&customer, &transactions).await
            });
            handles.push(handle);
        }
        
        // Wait for all assessments to complete
        let mut successful_assessments = 0;
        for handle in handles {
            match handle.await {
                Ok(Ok(_)) => successful_assessments += 1,
                Ok(Err(e)) => panic!("Assessment failed: {}", e),
                Err(e) => panic!("Task failed: {}", e),
            }
        }
        
        let duration = start.elapsed();
        println!("✅ Concurrent performance: {} assessments in {:?}", successful_assessments, duration);
        
        assert_eq!(successful_assessments, 50);
        assert!(duration.as_secs() < 5, "Concurrent assessments should complete quickly");
    }
}
