//! RegulateAI Testing Framework
//! 
//! Comprehensive testing utilities including:
//! - Property-based testing with proptest
//! - Contract testing between services
//! - Test data generation and factories
//! - Integration testing utilities
//! - Performance testing helpers

pub mod property_testing;
pub mod contract_testing;
pub mod test_factories;
pub mod integration_testing;
pub mod performance_testing;
pub mod mock_services;
pub mod test_data;
pub mod assertions;
pub mod fixtures;

pub use property_testing::{PropertyTestRunner, PropertyTestConfig, TestStrategy};
pub use contract_testing::{ContractTester, ContractTestConfig, ServiceContract};
pub use test_factories::{TestDataFactory, EntityFactory};
pub use integration_testing::{IntegrationTestHarness, TestEnvironment};
pub use performance_testing::{PerformanceTestRunner, BenchmarkConfig};
pub use mock_services::{MockServiceBuilder, MockResponse};
pub use test_data::{TestDataGenerator, RandomDataConfig};
pub use assertions::{CustomAssertions, BusinessRuleAssertions};
pub use fixtures::{TestFixtures, DatabaseFixtures};

/// Re-export commonly used testing macros and types
pub use proptest::prelude::*;
pub use quickcheck::{quickcheck, TestResult};
pub use rstest::*;
pub use test_case::test_case;
pub use tokio_test;
pub use fake::*;

/// Common test result type
pub type TestResult<T> = Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Test configuration for the entire testing framework
#[derive(Debug, Clone)]
pub struct TestFrameworkConfig {
    pub property_testing: PropertyTestConfig,
    pub contract_testing: ContractTestConfig,
    pub performance_testing: BenchmarkConfig,
    pub integration_testing: IntegrationTestConfig,
    pub mock_services: MockServiceConfig,
}

/// Integration test configuration
#[derive(Debug, Clone)]
pub struct IntegrationTestConfig {
    pub database_url: String,
    pub redis_url: String,
    pub test_timeout_seconds: u64,
    pub parallel_execution: bool,
    pub cleanup_after_tests: bool,
    pub seed_test_data: bool,
}

/// Mock service configuration
#[derive(Debug, Clone)]
pub struct MockServiceConfig {
    pub enabled: bool,
    pub port_range_start: u16,
    pub port_range_end: u16,
    pub default_timeout_ms: u64,
    pub record_interactions: bool,
}

impl Default for TestFrameworkConfig {
    fn default() -> Self {
        Self {
            property_testing: PropertyTestConfig::default(),
            contract_testing: ContractTestConfig::default(),
            performance_testing: BenchmarkConfig::default(),
            integration_testing: IntegrationTestConfig::default(),
            mock_services: MockServiceConfig::default(),
        }
    }
}

impl Default for IntegrationTestConfig {
    fn default() -> Self {
        Self {
            database_url: "postgresql://test:test@localhost:5432/regulateai_test".to_string(),
            redis_url: "redis://localhost:6379/1".to_string(),
            test_timeout_seconds: 300,
            parallel_execution: true,
            cleanup_after_tests: true,
            seed_test_data: true,
        }
    }
}

impl Default for MockServiceConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            port_range_start: 8900,
            port_range_end: 8999,
            default_timeout_ms: 5000,
            record_interactions: true,
        }
    }
}

/// Initialize the testing framework
pub async fn init_test_framework(config: TestFrameworkConfig) -> TestResult<TestFramework> {
    TestFramework::new(config).await
}

/// Main testing framework coordinator
pub struct TestFramework {
    config: TestFrameworkConfig,
    property_runner: PropertyTestRunner,
    contract_tester: ContractTester,
    performance_runner: PerformanceTestRunner,
    integration_harness: IntegrationTestHarness,
    mock_services: MockServiceBuilder,
}

impl TestFramework {
    /// Create a new testing framework instance
    pub async fn new(config: TestFrameworkConfig) -> TestResult<Self> {
        let property_runner = PropertyTestRunner::new(config.property_testing.clone());
        let contract_tester = ContractTester::new(config.contract_testing.clone()).await?;
        let performance_runner = PerformanceTestRunner::new(config.performance_testing.clone());
        let integration_harness = IntegrationTestHarness::new(config.integration_testing.clone()).await?;
        let mock_services = MockServiceBuilder::new(config.mock_services.clone());

        Ok(Self {
            config,
            property_runner,
            contract_tester,
            performance_runner,
            integration_harness,
            mock_services,
        })
    }

    /// Get property test runner
    pub fn property_tests(&self) -> &PropertyTestRunner {
        &self.property_runner
    }

    /// Get contract tester
    pub fn contract_tests(&self) -> &ContractTester {
        &self.contract_tester
    }

    /// Get performance test runner
    pub fn performance_tests(&self) -> &PerformanceTestRunner {
        &self.performance_runner
    }

    /// Get integration test harness
    pub fn integration_tests(&self) -> &IntegrationTestHarness {
        &self.integration_harness
    }

    /// Get mock service builder
    pub fn mock_services(&self) -> &MockServiceBuilder {
        &self.mock_services
    }

    /// Run all test suites
    pub async fn run_all_tests(&self) -> TestResult<TestSuiteResults> {
        let mut results = TestSuiteResults::new();

        // Run property tests
        tracing::info!("Running property-based tests...");
        let property_results = self.property_runner.run_all_tests().await?;
        results.property_test_results = Some(property_results);

        // Run contract tests
        tracing::info!("Running contract tests...");
        let contract_results = self.contract_tester.run_all_tests().await?;
        results.contract_test_results = Some(contract_results);

        // Run performance tests
        tracing::info!("Running performance tests...");
        let performance_results = self.performance_runner.run_benchmarks().await?;
        results.performance_test_results = Some(performance_results);

        // Run integration tests
        tracing::info!("Running integration tests...");
        let integration_results = self.integration_harness.run_all_tests().await?;
        results.integration_test_results = Some(integration_results);

        Ok(results)
    }

    /// Clean up test resources
    pub async fn cleanup(&self) -> TestResult<()> {
        self.integration_harness.cleanup().await?;
        self.mock_services.cleanup().await?;
        Ok(())
    }
}

/// Results from running all test suites
#[derive(Debug, Default)]
pub struct TestSuiteResults {
    pub property_test_results: Option<property_testing::PropertyTestResults>,
    pub contract_test_results: Option<contract_testing::ContractTestResults>,
    pub performance_test_results: Option<performance_testing::PerformanceTestResults>,
    pub integration_test_results: Option<integration_testing::IntegrationTestResults>,
}

impl TestSuiteResults {
    pub fn new() -> Self {
        Self::default()
    }

    /// Check if all tests passed
    pub fn all_passed(&self) -> bool {
        let property_passed = self.property_test_results
            .as_ref()
            .map(|r| r.all_passed())
            .unwrap_or(true);

        let contract_passed = self.contract_test_results
            .as_ref()
            .map(|r| r.all_passed())
            .unwrap_or(true);

        let performance_passed = self.performance_test_results
            .as_ref()
            .map(|r| r.all_passed())
            .unwrap_or(true);

        let integration_passed = self.integration_test_results
            .as_ref()
            .map(|r| r.all_passed())
            .unwrap_or(true);

        property_passed && contract_passed && performance_passed && integration_passed
    }

    /// Get summary statistics
    pub fn get_summary(&self) -> TestSummary {
        TestSummary {
            total_tests: self.count_total_tests(),
            passed_tests: self.count_passed_tests(),
            failed_tests: self.count_failed_tests(),
            skipped_tests: self.count_skipped_tests(),
            execution_time_ms: self.total_execution_time(),
        }
    }

    fn count_total_tests(&self) -> usize {
        let mut total = 0;
        
        if let Some(ref results) = self.property_test_results {
            total += results.total_tests();
        }
        
        if let Some(ref results) = self.contract_test_results {
            total += results.total_tests();
        }
        
        if let Some(ref results) = self.performance_test_results {
            total += results.total_tests();
        }
        
        if let Some(ref results) = self.integration_test_results {
            total += results.total_tests();
        }
        
        total
    }

    fn count_passed_tests(&self) -> usize {
        let mut passed = 0;
        
        if let Some(ref results) = self.property_test_results {
            passed += results.passed_tests();
        }
        
        if let Some(ref results) = self.contract_test_results {
            passed += results.passed_tests();
        }
        
        if let Some(ref results) = self.performance_test_results {
            passed += results.passed_tests();
        }
        
        if let Some(ref results) = self.integration_test_results {
            passed += results.passed_tests();
        }
        
        passed
    }

    fn count_failed_tests(&self) -> usize {
        let mut failed = 0;
        
        if let Some(ref results) = self.property_test_results {
            failed += results.failed_tests();
        }
        
        if let Some(ref results) = self.contract_test_results {
            failed += results.failed_tests();
        }
        
        if let Some(ref results) = self.performance_test_results {
            failed += results.failed_tests();
        }
        
        if let Some(ref results) = self.integration_test_results {
            failed += results.failed_tests();
        }
        
        failed
    }

    fn count_skipped_tests(&self) -> usize {
        // Implementation would count skipped tests from all suites
        0
    }

    fn total_execution_time(&self) -> u64 {
        let mut total_time = 0;
        
        if let Some(ref results) = self.property_test_results {
            total_time += results.execution_time_ms();
        }
        
        if let Some(ref results) = self.contract_test_results {
            total_time += results.execution_time_ms();
        }
        
        if let Some(ref results) = self.performance_test_results {
            total_time += results.execution_time_ms();
        }
        
        if let Some(ref results) = self.integration_test_results {
            total_time += results.execution_time_ms();
        }
        
        total_time
    }
}

/// Test execution summary
#[derive(Debug, Clone, serde::Serialize)]
pub struct TestSummary {
    pub total_tests: usize,
    pub passed_tests: usize,
    pub failed_tests: usize,
    pub skipped_tests: usize,
    pub execution_time_ms: u64,
}

impl TestSummary {
    /// Calculate success rate as percentage
    pub fn success_rate(&self) -> f64 {
        if self.total_tests == 0 {
            return 100.0;
        }
        (self.passed_tests as f64 / self.total_tests as f64) * 100.0
    }

    /// Check if all tests passed
    pub fn all_passed(&self) -> bool {
        self.failed_tests == 0 && self.total_tests > 0
    }
}
