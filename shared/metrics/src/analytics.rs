//! Metrics Analytics

use crate::errors::{MetricsError, MetricsResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};

/// Metrics analyzer for statistical analysis and trend detection
pub struct MetricsAnalyzer {
    window_size: usize,
    trend_threshold: f64,
}

/// Analytics engine for complex business intelligence
pub struct AnalyticsEngine {
    analyzers: Vec<MetricsAnalyzer>,
    correlation_threshold: f64,
}

/// Analysis result containing insights and recommendations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisResult {
    pub metric_name: String,
    pub trend: TrendDirection,
    pub anomalies: Vec<Anomaly>,
    pub correlations: Vec<Correlation>,
    pub recommendations: Vec<String>,
    pub confidence_score: f64,
    pub analyzed_at: DateTime<Utc>,
}

/// Trend direction enumeration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrendDirection {
    Increasing,
    Decreasing,
    Stable,
    Volatile,
}

/// Anomaly detection result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Anomaly {
    pub timestamp: DateTime<Utc>,
    pub value: f64,
    pub expected_value: f64,
    pub deviation_score: f64,
    pub severity: AnomalySeverity,
}

/// Anomaly severity levels
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AnomalySeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// Correlation between metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Correlation {
    pub metric_a: String,
    pub metric_b: String,
    pub correlation_coefficient: f64,
    pub significance: f64,
}

impl MetricsAnalyzer {
    pub fn new(window_size: usize, trend_threshold: f64) -> Self {
        Self {
            window_size,
            trend_threshold,
        }
    }

    /// Analyze metric data for trends and anomalies
    pub async fn analyze(&self, metric_name: &str, data_points: &[(DateTime<Utc>, f64)]) -> MetricsResult<AnalysisResult> {
        if data_points.is_empty() {
            return Err(MetricsError::Collection("No data points provided for analysis".to_string()));
        }

        let trend = self.detect_trend(data_points)?;
        let anomalies = self.detect_anomalies(data_points)?;
        let recommendations = self.generate_recommendations(&trend, &anomalies);
        let confidence_score = self.calculate_confidence_score(data_points.len(), &anomalies);

        Ok(AnalysisResult {
            metric_name: metric_name.to_string(),
            trend,
            anomalies,
            correlations: Vec::new(), // Will be populated by AnalyticsEngine
            recommendations,
            confidence_score,
            analyzed_at: Utc::now(),
        })
    }

    /// Detect trend direction using linear regression
    fn detect_trend(&self, data_points: &[(DateTime<Utc>, f64)]) -> MetricsResult<TrendDirection> {
        if data_points.len() < 2 {
            return Ok(TrendDirection::Stable);
        }

        // Convert timestamps to numeric values for regression
        let base_time = data_points[0].0.timestamp() as f64;
        let points: Vec<(f64, f64)> = data_points
            .iter()
            .map(|(timestamp, value)| {
                ((timestamp.timestamp() as f64 - base_time) / 3600.0, *value) // Hours since start
            })
            .collect();

        let slope = self.calculate_linear_regression_slope(&points)?;
        let volatility = self.calculate_volatility(data_points);

        if volatility > self.trend_threshold * 2.0 {
            Ok(TrendDirection::Volatile)
        } else if slope > self.trend_threshold {
            Ok(TrendDirection::Increasing)
        } else if slope < -self.trend_threshold {
            Ok(TrendDirection::Decreasing)
        } else {
            Ok(TrendDirection::Stable)
        }
    }

    /// Calculate linear regression slope
    fn calculate_linear_regression_slope(&self, points: &[(f64, f64)]) -> MetricsResult<f64> {
        let n = points.len() as f64;
        if n < 2.0 {
            return Ok(0.0);
        }

        let sum_x: f64 = points.iter().map(|(x, _)| x).sum();
        let sum_y: f64 = points.iter().map(|(_, y)| y).sum();
        let sum_xy: f64 = points.iter().map(|(x, y)| x * y).sum();
        let sum_x_squared: f64 = points.iter().map(|(x, _)| x * x).sum();

        let denominator = n * sum_x_squared - sum_x * sum_x;
        if denominator.abs() < f64::EPSILON {
            return Ok(0.0);
        }

        let slope = (n * sum_xy - sum_x * sum_y) / denominator;
        Ok(slope)
    }

    /// Calculate volatility (standard deviation of values)
    fn calculate_volatility(&self, data_points: &[(DateTime<Utc>, f64)]) -> f64 {
        if data_points.len() < 2 {
            return 0.0;
        }

        let values: Vec<f64> = data_points.iter().map(|(_, v)| *v).collect();
        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let variance = values
            .iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f64>() / values.len() as f64;

        variance.sqrt()
    }

    /// Detect anomalies using statistical methods
    fn detect_anomalies(&self, data_points: &[(DateTime<Utc>, f64)]) -> MetricsResult<Vec<Anomaly>> {
        if data_points.len() < self.window_size {
            return Ok(Vec::new());
        }

        let mut anomalies = Vec::new();
        let values: Vec<f64> = data_points.iter().map(|(_, v)| *v).collect();

        for i in self.window_size..values.len() {
            let window = &values[i - self.window_size..i];
            let mean = window.iter().sum::<f64>() / window.len() as f64;
            let std_dev = self.calculate_standard_deviation(window);

            let current_value = values[i];
            let expected_value = mean;
            let deviation_score = if std_dev > 0.0 {
                (current_value - expected_value).abs() / std_dev
            } else {
                0.0
            };

            if deviation_score > 3.0 {
                let severity = if deviation_score > 5.0 {
                    AnomalySeverity::Critical
                } else if deviation_score > 4.0 {
                    AnomalySeverity::High
                } else {
                    AnomalySeverity::Medium
                };

                anomalies.push(Anomaly {
                    timestamp: data_points[i].0,
                    value: current_value,
                    expected_value,
                    deviation_score,
                    severity,
                });
            }
        }

        Ok(anomalies)
    }

    /// Calculate standard deviation
    fn calculate_standard_deviation(&self, values: &[f64]) -> f64 {
        if values.len() < 2 {
            return 0.0;
        }

        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let variance = values
            .iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f64>() / values.len() as f64;

        variance.sqrt()
    }

    /// Generate recommendations based on analysis
    fn generate_recommendations(&self, trend: &TrendDirection, anomalies: &[Anomaly]) -> Vec<String> {
        let mut recommendations = Vec::new();

        match trend {
            TrendDirection::Increasing => {
                recommendations.push("Positive trend detected. Consider scaling resources to handle increased load.".to_string());
            }
            TrendDirection::Decreasing => {
                recommendations.push("Declining trend detected. Investigate potential issues or optimization opportunities.".to_string());
            }
            TrendDirection::Volatile => {
                recommendations.push("High volatility detected. Consider implementing smoothing mechanisms or investigating root causes.".to_string());
            }
            TrendDirection::Stable => {
                recommendations.push("Stable performance. Monitor for any changes in patterns.".to_string());
            }
        }

        let critical_anomalies = anomalies.iter().filter(|a| matches!(a.severity, AnomalySeverity::Critical)).count();
        if critical_anomalies > 0 {
            recommendations.push(format!("Critical anomalies detected ({}). Immediate investigation required.", critical_anomalies));
        }

        let high_anomalies = anomalies.iter().filter(|a| matches!(a.severity, AnomalySeverity::High)).count();
        if high_anomalies > 2 {
            recommendations.push("Multiple high-severity anomalies detected. Review system health and alert thresholds.".to_string());
        }

        recommendations
    }

    /// Calculate confidence score based on data quality
    fn calculate_confidence_score(&self, data_points_count: usize, anomalies: &[Anomaly]) -> f64 {
        let base_confidence = if data_points_count >= 100 {
            0.9
        } else if data_points_count >= 50 {
            0.8
        } else if data_points_count >= 20 {
            0.7
        } else {
            0.5
        };

        let anomaly_penalty = (anomalies.len() as f64 * 0.05).min(0.3);
        (base_confidence - anomaly_penalty).max(0.1)
    }
}

impl AnalyticsEngine {
    pub fn new(correlation_threshold: f64) -> Self {
        Self {
            analyzers: vec![
                MetricsAnalyzer::new(10, 0.1),  // Short-term analyzer
                MetricsAnalyzer::new(50, 0.05), // Medium-term analyzer
                MetricsAnalyzer::new(100, 0.02), // Long-term analyzer
            ],
            correlation_threshold,
        }
    }

    /// Run comprehensive analysis across multiple metrics
    pub async fn run_analysis(&self, metrics_data: HashMap<String, Vec<(DateTime<Utc>, f64)>>) -> MetricsResult<Vec<AnalysisResult>> {
        let mut results = Vec::new();

        // Analyze each metric individually
        for (metric_name, data_points) in &metrics_data {
            for analyzer in &self.analyzers {
                let mut result = analyzer.analyze(metric_name, data_points).await?;

                // Add correlations
                result.correlations = self.calculate_correlations(metric_name, &metrics_data)?;

                results.push(result);
            }
        }

        Ok(results)
    }

    /// Calculate correlations between metrics
    fn calculate_correlations(&self, target_metric: &str, metrics_data: &HashMap<String, Vec<(DateTime<Utc>, f64)>>) -> MetricsResult<Vec<Correlation>> {
        let mut correlations = Vec::new();

        let target_data = match metrics_data.get(target_metric) {
            Some(data) => data,
            None => return Ok(correlations),
        };

        for (other_metric, other_data) in metrics_data {
            if other_metric == target_metric {
                continue;
            }

            let correlation_coefficient = self.calculate_pearson_correlation(target_data, other_data)?;

            if correlation_coefficient.abs() >= self.correlation_threshold {
                correlations.push(Correlation {
                    metric_a: target_metric.to_string(),
                    metric_b: other_metric.clone(),
                    correlation_coefficient,
                    significance: correlation_coefficient.abs(),
                });
            }
        }

        Ok(correlations)
    }

    /// Calculate Pearson correlation coefficient
    fn calculate_pearson_correlation(&self, data_a: &[(DateTime<Utc>, f64)], data_b: &[(DateTime<Utc>, f64)]) -> MetricsResult<f64> {
        // Align data points by timestamp
        let mut aligned_pairs = Vec::new();

        for (timestamp_a, value_a) in data_a {
            if let Some((_, value_b)) = data_b.iter().find(|(timestamp_b, _)| timestamp_b == timestamp_a) {
                aligned_pairs.push((*value_a, *value_b));
            }
        }

        if aligned_pairs.len() < 2 {
            return Ok(0.0);
        }

        let n = aligned_pairs.len() as f64;
        let sum_a: f64 = aligned_pairs.iter().map(|(a, _)| a).sum();
        let sum_b: f64 = aligned_pairs.iter().map(|(_, b)| b).sum();
        let sum_a_squared: f64 = aligned_pairs.iter().map(|(a, _)| a * a).sum();
        let sum_b_squared: f64 = aligned_pairs.iter().map(|(_, b)| b * b).sum();
        let sum_ab: f64 = aligned_pairs.iter().map(|(a, b)| a * b).sum();

        let numerator = n * sum_ab - sum_a * sum_b;
        let denominator = ((n * sum_a_squared - sum_a * sum_a) * (n * sum_b_squared - sum_b * sum_b)).sqrt();

        if denominator.abs() < f64::EPSILON {
            Ok(0.0)
        } else {
            Ok(numerator / denominator)
        }
    }
}
