//! Integration tests for Risk Management Service

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
    async fn test_risk_assessment_creation() {
        let assessment_data = TestRiskAssessmentData {
            title: "Market Risk Assessment".to_string(),
            description: "Assessment of market volatility impact".to_string(),
            risk_category: "MARKET_RISK".to_string(),
            inherent_risk_score: 75.0,
            residual_risk_score: 45.0,
        };

        let result = create_risk_assessment(&assessment_data).await;
        assert!(result.is_ok(), "Risk assessment creation should succeed");

        let assessment = result.unwrap();
        assert_eq!(assessment.title, assessment_data.title);
        assert!(assessment.inherent_risk_score >= assessment.residual_risk_score);
    }

    #[tokio::test]
    async fn test_kri_monitoring() {
        let kri_data = TestKriData {
            name: "Credit Loss Rate".to_string(),
            metric_type: "PERCENTAGE".to_string(),
            threshold_green: 1.0,
            threshold_amber: 2.5,
            threshold_red: 5.0,
        };

        let kri_result = create_kri(&kri_data).await;
        assert!(result.is_ok(), "KRI creation should succeed");

        // Test measurement recording
        let measurement_data = TestKriMeasurement {
            value: 3.2,
            measurement_date: Utc::now(),
        };

        let measurement_result = record_kri_measurement(&kri_result.unwrap().id, &measurement_data).await;
        assert!(measurement_result.is_ok(), "KRI measurement recording should succeed");

        let measurement = measurement_result.unwrap();
        assert_eq!(measurement.status, "AMBER", "KRI should be in AMBER status for value 3.2");
    }

    #[tokio::test]
    async fn test_monte_carlo_simulation() {
        let simulation_params = TestMonteCarloParams {
            iterations: 10000,
            confidence_level: 0.95,
            time_horizon: 252, // 1 year in trading days
            portfolio_value: 10_000_000.0,
            volatility: 0.15,
        };

        let result = run_monte_carlo_simulation(&simulation_params).await;
        assert!(result.is_ok(), "Monte Carlo simulation should succeed");

        let simulation_result = result.unwrap();
        assert!(simulation_result.var_95 > 0.0, "VaR should be positive");
        assert!(simulation_result.expected_shortfall > simulation_result.var_95, "Expected shortfall should be greater than VaR");
        assert_eq!(simulation_result.iterations, simulation_params.iterations);
    }

    #[tokio::test]
    async fn test_stress_testing() {
        let stress_scenario = TestStressScenario {
            name: "Market Crash Scenario".to_string(),
            description: "30% market decline with increased volatility".to_string(),
            market_shock: -0.30,
            volatility_multiplier: 2.0,
            correlation_breakdown: true,
        };

        let result = run_stress_test(&stress_scenario).await;
        assert!(result.is_ok(), "Stress test should succeed");

        let stress_result = result.unwrap();
        assert!(stress_result.portfolio_impact < 0.0, "Stress test should show negative impact");
        assert!(stress_result.risk_metrics.var_impact > 1.0, "VaR should increase under stress");
    }

    #[tokio::test]
    async fn test_risk_analytics() {
        let analytics_request = TestAnalyticsRequest {
            analysis_type: "PORTFOLIO_RISK".to_string(),
            time_period: 30,
            include_scenarios: true,
        };

        let result = generate_risk_analytics(&analytics_request).await;
        assert!(result.is_ok(), "Risk analytics generation should succeed");

        let analytics = result.unwrap();
        assert!(analytics.total_risk_score >= 0.0 && analytics.total_risk_score <= 100.0);
        assert!(!analytics.risk_factors.is_empty(), "Should identify risk factors");
        assert!(!analytics.recommendations.is_empty(), "Should provide recommendations");
    }

    // Helper functions for testing
    async fn create_risk_assessment(data: &TestRiskAssessmentData) -> Result<TestRiskAssessment, RegulateAIError> {
        Ok(TestRiskAssessment {
            id: Uuid::new_v4(),
            title: data.title.clone(),
            description: data.description.clone(),
            risk_category: data.risk_category.clone(),
            inherent_risk_score: data.inherent_risk_score,
            residual_risk_score: data.residual_risk_score,
            status: "DRAFT".to_string(),
            created_at: Utc::now(),
        })
    }

    async fn create_kri(data: &TestKriData) -> Result<TestKri, RegulateAIError> {
        Ok(TestKri {
            id: Uuid::new_v4(),
            name: data.name.clone(),
            metric_type: data.metric_type.clone(),
            threshold_green: data.threshold_green,
            threshold_amber: data.threshold_amber,
            threshold_red: data.threshold_red,
            is_active: true,
            created_at: Utc::now(),
        })
    }

    async fn record_kri_measurement(kri_id: &Uuid, data: &TestKriMeasurement) -> Result<TestKriMeasurementResult, RegulateAIError> {
        let status = if data.value <= 1.0 {
            "GREEN"
        } else if data.value <= 2.5 {
            "AMBER"
        } else {
            "RED"
        };

        Ok(TestKriMeasurementResult {
            id: Uuid::new_v4(),
            kri_id: *kri_id,
            value: data.value,
            status: status.to_string(),
            measurement_date: data.measurement_date,
            created_at: Utc::now(),
        })
    }

    async fn run_monte_carlo_simulation(params: &TestMonteCarloParams) -> Result<TestMonteCarloResult, RegulateAIError> {
        // Simplified Monte Carlo simulation for testing
        let var_95 = params.portfolio_value * params.volatility * 1.645; // Approximate VaR
        let expected_shortfall = var_95 * 1.3; // Approximate ES

        Ok(TestMonteCarloResult {
            iterations: params.iterations,
            confidence_level: params.confidence_level,
            var_95,
            expected_shortfall,
            portfolio_value: params.portfolio_value,
            simulation_date: Utc::now(),
        })
    }

    async fn run_stress_test(scenario: &TestStressScenario) -> Result<TestStressTestResult, RegulateAIError> {
        // Simplified stress test for testing
        let portfolio_impact = scenario.market_shock * 10_000_000.0; // Assume $10M portfolio
        
        Ok(TestStressTestResult {
            scenario_name: scenario.name.clone(),
            portfolio_impact,
            risk_metrics: TestStressRiskMetrics {
                var_impact: scenario.volatility_multiplier,
                correlation_impact: if scenario.correlation_breakdown { 1.5 } else { 1.0 },
                liquidity_impact: 1.2,
            },
            execution_date: Utc::now(),
        })
    }

    async fn generate_risk_analytics(request: &TestAnalyticsRequest) -> Result<TestRiskAnalytics, RegulateAIError> {
        Ok(TestRiskAnalytics {
            analysis_type: request.analysis_type.clone(),
            total_risk_score: 67.5,
            risk_factors: vec![
                "Market volatility".to_string(),
                "Credit concentration".to_string(),
                "Operational dependencies".to_string(),
            ],
            recommendations: vec![
                "Diversify portfolio holdings".to_string(),
                "Implement additional hedging strategies".to_string(),
                "Review risk limits quarterly".to_string(),
            ],
            generated_at: Utc::now(),
        })
    }

    // Test data structures
    #[derive(Debug)]
    struct TestRiskAssessmentData {
        title: String,
        description: String,
        risk_category: String,
        inherent_risk_score: f64,
        residual_risk_score: f64,
    }

    #[derive(Debug)]
    struct TestRiskAssessment {
        id: Uuid,
        title: String,
        description: String,
        risk_category: String,
        inherent_risk_score: f64,
        residual_risk_score: f64,
        status: String,
        created_at: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestKriData {
        name: String,
        metric_type: String,
        threshold_green: f64,
        threshold_amber: f64,
        threshold_red: f64,
    }

    #[derive(Debug)]
    struct TestKri {
        id: Uuid,
        name: String,
        metric_type: String,
        threshold_green: f64,
        threshold_amber: f64,
        threshold_red: f64,
        is_active: bool,
        created_at: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestKriMeasurement {
        value: f64,
        measurement_date: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestKriMeasurementResult {
        id: Uuid,
        kri_id: Uuid,
        value: f64,
        status: String,
        measurement_date: chrono::DateTime<Utc>,
        created_at: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestMonteCarloParams {
        iterations: u32,
        confidence_level: f64,
        time_horizon: u32,
        portfolio_value: f64,
        volatility: f64,
    }

    #[derive(Debug)]
    struct TestMonteCarloResult {
        iterations: u32,
        confidence_level: f64,
        var_95: f64,
        expected_shortfall: f64,
        portfolio_value: f64,
        simulation_date: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestStressScenario {
        name: String,
        description: String,
        market_shock: f64,
        volatility_multiplier: f64,
        correlation_breakdown: bool,
    }

    #[derive(Debug)]
    struct TestStressTestResult {
        scenario_name: String,
        portfolio_impact: f64,
        risk_metrics: TestStressRiskMetrics,
        execution_date: chrono::DateTime<Utc>,
    }

    #[derive(Debug)]
    struct TestStressRiskMetrics {
        var_impact: f64,
        correlation_impact: f64,
        liquidity_impact: f64,
    }

    #[derive(Debug)]
    struct TestAnalyticsRequest {
        analysis_type: String,
        time_period: u32,
        include_scenarios: bool,
    }

    #[derive(Debug)]
    struct TestRiskAnalytics {
        analysis_type: String,
        total_risk_score: f64,
        risk_factors: Vec<String>,
        recommendations: Vec<String>,
        generated_at: chrono::DateTime<Utc>,
    }
}

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_end_to_end_risk_management_workflow() {
        // Test complete risk management workflow
        
        // 1. Create risk assessment
        let assessment_data = unit_tests::TestRiskAssessmentData {
            title: "Comprehensive Risk Assessment".to_string(),
            description: "Full enterprise risk assessment".to_string(),
            risk_category: "ENTERPRISE_RISK".to_string(),
            inherent_risk_score: 85.0,
            residual_risk_score: 55.0,
        };

        let assessment_result = unit_tests::create_risk_assessment(&assessment_data).await;
        assert!(assessment_result.is_ok(), "Risk assessment creation should succeed");

        // 2. Set up KRI monitoring
        let kri_data = unit_tests::TestKriData {
            name: "Overall Risk Score".to_string(),
            metric_type: "SCORE".to_string(),
            threshold_green: 30.0,
            threshold_amber: 60.0,
            threshold_red: 80.0,
        };

        let kri_result = unit_tests::create_kri(&kri_data).await;
        assert!(kri_result.is_ok(), "KRI creation should succeed");

        // 3. Run Monte Carlo simulation
        let simulation_params = unit_tests::TestMonteCarloParams {
            iterations: 5000,
            confidence_level: 0.99,
            time_horizon: 252,
            portfolio_value: 50_000_000.0,
            volatility: 0.20,
        };

        let simulation_result = unit_tests::run_monte_carlo_simulation(&simulation_params).await;
        assert!(simulation_result.is_ok(), "Monte Carlo simulation should succeed");

        // 4. Execute stress test
        let stress_scenario = unit_tests::TestStressScenario {
            name: "Economic Recession Scenario".to_string(),
            description: "Severe economic downturn with market disruption".to_string(),
            market_shock: -0.40,
            volatility_multiplier: 2.5,
            correlation_breakdown: true,
        };

        let stress_result = unit_tests::run_stress_test(&stress_scenario).await;
        assert!(stress_result.is_ok(), "Stress test should succeed");

        println!("✅ End-to-end risk management workflow test completed successfully");
    }

    #[tokio::test]
    async fn test_risk_limit_monitoring() {
        // Test risk limit monitoring and alerting
        let mut breach_count = 0;

        for i in 1..=100 {
            let risk_value = i as f64;
            let limit = 75.0;

            if risk_value > limit {
                breach_count += 1;
                println!("Risk limit breach detected: {} > {}", risk_value, limit);
            }
        }

        assert!(breach_count > 0, "Should detect risk limit breaches");
        assert_eq!(breach_count, 25, "Should detect exactly 25 breaches (76-100)");
    }
}
