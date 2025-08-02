//! Monte Carlo simulation engine for risk analysis
//! 
//! This module provides advanced Monte Carlo simulation capabilities for:
//! - Value at Risk (VaR) calculations
//! - Expected Shortfall (ES) calculations
//! - Stress testing scenarios
//! - Portfolio risk analysis
//! - Capital allocation modeling

use std::collections::HashMap;
use rand::{Rng, SeedableRng};
use rand_distr::{Distribution, Normal, LogNormal, StudentT, Uniform, Beta, Gamma, Exp};
use nalgebra::{DMatrix, DVector};
use statrs::statistics::{Statistics, OrderStatistics};
use tracing::{info, warn, error};
use uuid::Uuid;
use rust_decimal::Decimal;

use regulateai_errors::RegulateAIError;
use crate::models::*;

/// Monte Carlo simulation engine
pub struct MonteCarloEngine {
    rng: rand::rngs::StdRng,
    convergence_threshold: f64,
    max_iterations: u32,
}

impl MonteCarloEngine {
    /// Create a new Monte Carlo engine
    pub fn new(seed: Option<u64>) -> Self {
        let rng = match seed {
            Some(s) => rand::rngs::StdRng::seed_from_u64(s),
            None => rand::rngs::StdRng::from_entropy(),
        };

        Self {
            rng,
            convergence_threshold: 0.001, // 0.1% convergence threshold
            max_iterations: 1_000_000,
        }
    }

    /// Run Monte Carlo simulation
    pub async fn run_simulation(
        &mut self,
        request: &CreateSimulationRequest,
    ) -> Result<SimulationResult, RegulateAIError> {
        info!("Starting Monte Carlo simulation: {}", request.name);

        let start_time = std::time::Instant::now();

        // Validate simulation parameters
        self.validate_simulation_request(request)?;

        // Generate correlated random samples
        let samples = self.generate_correlated_samples(
            &request.risk_factors,
            &request.correlations,
            request.num_simulations,
        )?;

        // Run simulation paths
        let path_results = self.simulate_paths(&samples, request).await?;

        // Calculate statistics
        let statistics = self.calculate_statistics(&path_results)?;

        // Check convergence
        let convergence_achieved = self.check_convergence(&path_results)?;

        let execution_time = start_time.elapsed().as_millis() as u64;

        let result = SimulationResult {
            simulation_id: Uuid::new_v4(),
            num_paths: request.num_simulations,
            convergence_achieved,
            var_95: Decimal::from_f64_retain(statistics.var_95).unwrap_or_default(),
            var_99: Decimal::from_f64_retain(statistics.var_99).unwrap_or_default(),
            expected_shortfall_95: Decimal::from_f64_retain(statistics.es_95).unwrap_or_default(),
            expected_shortfall_99: Decimal::from_f64_retain(statistics.es_99).unwrap_or_default(),
            maximum_loss: Decimal::from_f64_retain(statistics.maximum_loss).unwrap_or_default(),
            expected_return: Decimal::from_f64_retain(statistics.expected_return).unwrap_or_default(),
            volatility: Decimal::from_f64_retain(statistics.volatility).unwrap_or_default(),
            percentiles: serde_json::to_value(&statistics.percentiles)?,
            path_statistics: statistics.path_stats,
            execution_time_ms: execution_time,
        };

        info!("Monte Carlo simulation completed in {}ms", execution_time);
        Ok(result)
    }

    /// Validate simulation request parameters
    fn validate_simulation_request(&self, request: &CreateSimulationRequest) -> Result<(), RegulateAIError> {
        if request.num_simulations == 0 {
            return Err(RegulateAIError::ValidationError {
                field: "num_simulations".to_string(),
                message: "Number of simulations must be greater than 0".to_string(),
            });
        }

        if request.num_simulations > self.max_iterations {
            return Err(RegulateAIError::ValidationError {
                field: "num_simulations".to_string(),
                message: format!("Number of simulations cannot exceed {}", self.max_iterations),
            });
        }

        if request.risk_factors.is_empty() {
            return Err(RegulateAIError::ValidationError {
                field: "risk_factors".to_string(),
                message: "At least one risk factor must be specified".to_string(),
            });
        }

        // Validate correlation matrices
        for correlation in &request.correlations {
            self.validate_correlation_matrix(correlation)?;
        }

        Ok(())
    }

    /// Validate correlation matrix
    fn validate_correlation_matrix(&self, correlation: &CorrelationMatrix) -> Result<(), RegulateAIError> {
        let n = correlation.factor_names.len();
        
        if correlation.correlation_values.len() != n {
            return Err(RegulateAIError::ValidationError {
                field: "correlation_matrix".to_string(),
                message: "Correlation matrix dimensions do not match factor names".to_string(),
            });
        }

        for (i, row) in correlation.correlation_values.iter().enumerate() {
            if row.len() != n {
                return Err(RegulateAIError::ValidationError {
                    field: "correlation_matrix".to_string(),
                    message: format!("Row {} has incorrect length", i),
                });
            }

            // Check diagonal elements are 1.0
            if (row[i] - 1.0).abs() > 1e-6 {
                return Err(RegulateAIError::ValidationError {
                    field: "correlation_matrix".to_string(),
                    message: format!("Diagonal element at ({}, {}) is not 1.0", i, i),
                });
            }

            // Check symmetry and bounds
            for (j, &value) in row.iter().enumerate() {
                if value < -1.0 || value > 1.0 {
                    return Err(RegulateAIError::ValidationError {
                        field: "correlation_matrix".to_string(),
                        message: format!("Correlation value at ({}, {}) is out of bounds [-1, 1]", i, j),
                    });
                }

                if i != j && (value - correlation.correlation_values[j][i]).abs() > 1e-6 {
                    return Err(RegulateAIError::ValidationError {
                        field: "correlation_matrix".to_string(),
                        message: format!("Correlation matrix is not symmetric at ({}, {})", i, j),
                    });
                }
            }
        }

        Ok(())
    }

    /// Generate correlated random samples using Cholesky decomposition
    fn generate_correlated_samples(
        &mut self,
        risk_factors: &[RiskFactorDistribution],
        correlations: &[CorrelationMatrix],
        num_samples: u32,
    ) -> Result<Vec<Vec<f64>>, RegulateAIError> {
        info!("Generating {} correlated samples for {} risk factors", num_samples, risk_factors.len());

        let num_factors = risk_factors.len();
        let mut samples = vec![vec![0.0; num_factors]; num_samples as usize];

        // Generate independent samples first
        let mut independent_samples = vec![vec![0.0; num_factors]; num_samples as usize];
        
        for (factor_idx, factor) in risk_factors.iter().enumerate() {
            let distribution = self.create_distribution(factor)?;
            
            for sample_idx in 0..num_samples as usize {
                independent_samples[sample_idx][factor_idx] = self.sample_from_distribution(&distribution)?;
            }
        }

        // Apply correlation if specified
        if !correlations.is_empty() {
            let correlation_matrix = &correlations[0]; // Use first correlation matrix
            let cholesky = self.cholesky_decomposition(&correlation_matrix.correlation_values)?;
            
            // Apply Cholesky transformation
            for sample_idx in 0..num_samples as usize {
                let independent = DVector::from_vec(independent_samples[sample_idx].clone());
                let correlated = &cholesky * independent;
                samples[sample_idx] = correlated.data.as_vec().clone();
            }
        } else {
            samples = independent_samples;
        }

        info!("Generated correlated samples successfully");
        Ok(samples)
    }

    /// Create distribution from risk factor specification
    fn create_distribution(&self, factor: &RiskFactorDistribution) -> Result<Box<dyn Distribution<f64> + Send + Sync>, RegulateAIError> {
        match factor.distribution_type {
            DistributionType::Normal => {
                let mean = factor.parameters.get("mean")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);
                let std_dev = factor.parameters.get("std_dev")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                
                Ok(Box::new(Normal::new(mean, std_dev).map_err(|e| {
                    RegulateAIError::ValidationError {
                        field: "distribution_parameters".to_string(),
                        message: format!("Invalid normal distribution parameters: {}", e),
                    }
                })?))
            }
            DistributionType::LogNormal => {
                let mean = factor.parameters.get("mean")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);
                let std_dev = factor.parameters.get("std_dev")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                
                Ok(Box::new(LogNormal::new(mean, std_dev).map_err(|e| {
                    RegulateAIError::ValidationError {
                        field: "distribution_parameters".to_string(),
                        message: format!("Invalid log-normal distribution parameters: {}", e),
                    }
                })?))
            }
            DistributionType::StudentT => {
                let degrees_of_freedom = factor.parameters.get("degrees_of_freedom")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(3.0);
                
                Ok(Box::new(StudentT::new(degrees_of_freedom).map_err(|e| {
                    RegulateAIError::ValidationError {
                        field: "distribution_parameters".to_string(),
                        message: format!("Invalid Student-t distribution parameters: {}", e),
                    }
                })?))
            }
            DistributionType::Uniform => {
                let low = factor.parameters.get("low")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);
                let high = factor.parameters.get("high")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                
                Ok(Box::new(Uniform::new(low, high)))
            }
            DistributionType::Beta => {
                let alpha = factor.parameters.get("alpha")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                let beta = factor.parameters.get("beta")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                
                Ok(Box::new(Beta::new(alpha, beta).map_err(|e| {
                    RegulateAIError::ValidationError {
                        field: "distribution_parameters".to_string(),
                        message: format!("Invalid beta distribution parameters: {}", e),
                    }
                })?))
            }
            DistributionType::Gamma => {
                let shape = factor.parameters.get("shape")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                let rate = factor.parameters.get("rate")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                
                Ok(Box::new(Gamma::new(shape, rate).map_err(|e| {
                    RegulateAIError::ValidationError {
                        field: "distribution_parameters".to_string(),
                        message: format!("Invalid gamma distribution parameters: {}", e),
                    }
                })?))
            }
            DistributionType::Exponential => {
                let lambda = factor.parameters.get("lambda")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                
                Ok(Box::new(Exp::new(lambda).map_err(|e| {
                    RegulateAIError::ValidationError {
                        field: "distribution_parameters".to_string(),
                        message: format!("Invalid exponential distribution parameters: {}", e),
                    }
                })?))
            }
            DistributionType::Historical => {
                // For historical distribution, we would sample from historical data
                // For now, return a normal distribution as fallback
                Ok(Box::new(Normal::new(0.0, 1.0).unwrap()))
            }
        }
    }

    /// Sample from a distribution
    fn sample_from_distribution(&mut self, distribution: &dyn Distribution<f64>) -> Result<f64, RegulateAIError> {
        Ok(distribution.sample(&mut self.rng))
    }

    /// Perform Cholesky decomposition
    fn cholesky_decomposition(&self, correlation_matrix: &[Vec<f64>]) -> Result<DMatrix<f64>, RegulateAIError> {
        let n = correlation_matrix.len();
        let mut matrix_data = Vec::with_capacity(n * n);
        
        for row in correlation_matrix {
            matrix_data.extend_from_slice(row);
        }
        
        let matrix = DMatrix::from_vec(n, n, matrix_data);
        
        // Perform Cholesky decomposition
        match matrix.cholesky() {
            Some(cholesky) => Ok(cholesky.l().clone()),
            None => {
                error!("Cholesky decomposition failed - matrix is not positive definite");
                Err(RegulateAIError::ValidationError {
                    field: "correlation_matrix".to_string(),
                    message: "Correlation matrix is not positive definite".to_string(),
                })
            }
        }
    }

    /// Simulate paths using the generated samples
    async fn simulate_paths(
        &self,
        samples: &[Vec<f64>],
        request: &CreateSimulationRequest,
    ) -> Result<Vec<f64>, RegulateAIError> {
        info!("Simulating {} paths", samples.len());

        let mut path_results = Vec::with_capacity(samples.len());

        for sample in samples {
            // For each sample, calculate the portfolio value change
            // This is a simplified calculation - in practice, this would involve
            // complex portfolio valuation models
            let mut portfolio_change = 0.0;
            
            for (i, &factor_value) in sample.iter().enumerate() {
                // Apply factor to portfolio (simplified linear model)
                let factor_weight = 1.0 / sample.len() as f64; // Equal weighting
                portfolio_change += factor_value * factor_weight;
            }
            
            path_results.push(portfolio_change);
        }

        info!("Completed path simulation");
        Ok(path_results)
    }

    /// Calculate simulation statistics
    fn calculate_statistics(&self, path_results: &[f64]) -> Result<SimulationStatistics, RegulateAIError> {
        if path_results.is_empty() {
            return Err(RegulateAIError::ValidationError {
                field: "path_results".to_string(),
                message: "No path results to analyze".to_string(),
            });
        }

        let mut sorted_results = path_results.to_vec();
        sorted_results.sort_by(|a, b| a.partial_cmp(b).unwrap());

        // Calculate basic statistics
        let mean = path_results.mean();
        let std_dev = path_results.std_dev();
        let min_value = sorted_results[0];
        let max_value = sorted_results[sorted_results.len() - 1];
        let median = sorted_results.median();

        // Calculate VaR and Expected Shortfall
        let var_95_idx = ((1.0 - 0.95) * sorted_results.len() as f64) as usize;
        let var_99_idx = ((1.0 - 0.99) * sorted_results.len() as f64) as usize;
        
        let var_95 = sorted_results[var_95_idx.min(sorted_results.len() - 1)];
        let var_99 = sorted_results[var_99_idx.min(sorted_results.len() - 1)];

        // Expected Shortfall (Conditional VaR)
        let es_95 = sorted_results[..=var_95_idx].iter().sum::<f64>() / (var_95_idx + 1) as f64;
        let es_99 = sorted_results[..=var_99_idx].iter().sum::<f64>() / (var_99_idx + 1) as f64;

        // Calculate percentiles
        let percentiles = self.calculate_percentiles(&sorted_results);

        // Calculate higher moments
        let skewness = self.calculate_skewness(path_results, mean, std_dev);
        let kurtosis = self.calculate_kurtosis(path_results, mean, std_dev);

        let path_stats = PathStatistics {
            mean,
            median,
            standard_deviation: std_dev,
            skewness,
            kurtosis,
            minimum: min_value,
            maximum: max_value,
        };

        Ok(SimulationStatistics {
            var_95,
            var_99,
            es_95,
            es_99,
            maximum_loss: min_value, // Most negative value
            expected_return: mean,
            volatility: std_dev,
            percentiles,
            path_stats,
        })
    }

    /// Calculate percentiles
    fn calculate_percentiles(&self, sorted_results: &[f64]) -> serde_json::Value {
        let percentiles = vec![1.0, 5.0, 10.0, 25.0, 50.0, 75.0, 90.0, 95.0, 99.0];
        let mut percentile_map = serde_json::Map::new();

        for p in percentiles {
            let idx = ((p / 100.0) * sorted_results.len() as f64) as usize;
            let value = sorted_results[idx.min(sorted_results.len() - 1)];
            percentile_map.insert(format!("p{}", p as i32), serde_json::Value::from(value));
        }

        serde_json::Value::Object(percentile_map)
    }

    /// Calculate skewness
    fn calculate_skewness(&self, data: &[f64], mean: f64, std_dev: f64) -> f64 {
        if std_dev == 0.0 {
            return 0.0;
        }

        let n = data.len() as f64;
        let sum_cubed_deviations: f64 = data.iter()
            .map(|&x| ((x - mean) / std_dev).powi(3))
            .sum();

        sum_cubed_deviations / n
    }

    /// Calculate kurtosis
    fn calculate_kurtosis(&self, data: &[f64], mean: f64, std_dev: f64) -> f64 {
        if std_dev == 0.0 {
            return 0.0;
        }

        let n = data.len() as f64;
        let sum_fourth_deviations: f64 = data.iter()
            .map(|&x| ((x - mean) / std_dev).powi(4))
            .sum();

        (sum_fourth_deviations / n) - 3.0 // Excess kurtosis
    }

    /// Check convergence of simulation
    fn check_convergence(&self, path_results: &[f64]) -> Result<bool, RegulateAIError> {
        if path_results.len() < 1000 {
            return Ok(false); // Need minimum number of samples
        }

        // Check convergence by comparing statistics of first half vs second half
        let mid_point = path_results.len() / 2;
        let first_half = &path_results[..mid_point];
        let second_half = &path_results[mid_point..];

        let mean1 = first_half.mean();
        let mean2 = second_half.mean();
        let std1 = first_half.std_dev();
        let std2 = second_half.std_dev();

        let mean_diff = (mean1 - mean2).abs() / mean1.abs().max(1e-10);
        let std_diff = (std1 - std2).abs() / std1.abs().max(1e-10);

        let converged = mean_diff < self.convergence_threshold && std_diff < self.convergence_threshold;

        if !converged {
            warn!("Simulation has not converged: mean_diff={:.6}, std_diff={:.6}", mean_diff, std_diff);
        }

        Ok(converged)
    }
}

/// Internal structure for simulation statistics
struct SimulationStatistics {
    pub var_95: f64,
    pub var_99: f64,
    pub es_95: f64,
    pub es_99: f64,
    pub maximum_loss: f64,
    pub expected_return: f64,
    pub volatility: f64,
    pub percentiles: serde_json::Value,
    pub path_stats: PathStatistics,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_monte_carlo_engine_creation() {
        let engine = MonteCarloEngine::new(Some(12345));
        assert_eq!(engine.convergence_threshold, 0.001);
        assert_eq!(engine.max_iterations, 1_000_000);
    }

    #[tokio::test]
    async fn test_normal_distribution_creation() {
        let engine = MonteCarloEngine::new(Some(12345));
        
        let factor = RiskFactorDistribution {
            factor_name: "test_factor".to_string(),
            distribution_type: DistributionType::Normal,
            parameters: serde_json::json!({
                "mean": 0.0,
                "std_dev": 1.0
            }),
            historical_data: None,
        };

        let distribution = engine.create_distribution(&factor).unwrap();
        // Test passes if no error is thrown
    }

    #[tokio::test]
    async fn test_correlation_matrix_validation() {
        let engine = MonteCarloEngine::new(Some(12345));
        
        let valid_correlation = CorrelationMatrix {
            factor_names: vec!["factor1".to_string(), "factor2".to_string()],
            correlation_values: vec![
                vec![1.0, 0.5],
                vec![0.5, 1.0],
            ],
            estimation_method: "historical".to_string(),
        };

        assert!(engine.validate_correlation_matrix(&valid_correlation).is_ok());

        let invalid_correlation = CorrelationMatrix {
            factor_names: vec!["factor1".to_string(), "factor2".to_string()],
            correlation_values: vec![
                vec![1.0, 1.5], // Invalid correlation > 1
                vec![0.5, 1.0],
            ],
            estimation_method: "historical".to_string(),
        };

        assert!(engine.validate_correlation_matrix(&invalid_correlation).is_err());
    }

    #[tokio::test]
    async fn test_percentile_calculation() {
        let engine = MonteCarloEngine::new(Some(12345));
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
        
        let percentiles = engine.calculate_percentiles(&data);
        assert!(percentiles.is_object());
        
        // Check that median (p50) is approximately 5.5
        let p50 = percentiles.get("p50").unwrap().as_f64().unwrap();
        assert!((p50 - 5.0).abs() < 1.0); // Allow some tolerance due to indexing
    }
}
