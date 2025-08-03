//! Fraud Detection Metrics
//!
//! Comprehensive fraud detection metrics collection and analysis system
//! with real-time monitoring, ML model performance tracking, and alerting.

use crate::{errors::{MetricsError, MetricsResult}, FraudDetectionStats};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};
use tokio::sync::RwLock;
use std::sync::Arc;

/// Fraud metrics collector with comprehensive tracking
pub struct FraudMetricsCollector {
    config: FraudMetricsConfig,
    detection_history: Arc<RwLock<Vec<FraudDetectionEvent>>>,
    model_performance: Arc<RwLock<ModelPerformanceMetrics>>,
    alert_history: Arc<RwLock<Vec<FraudAlert>>>,
    transaction_stats: Arc<RwLock<TransactionStats>>,
}

/// Fraud metrics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudMetricsConfig {
    pub enabled: bool,
    pub collection_interval_seconds: u64,
    pub retention_days: u32,
    pub alert_threshold: f64,
    pub model_accuracy_threshold: f64,
    pub false_positive_threshold: f64,
}

/// Individual fraud detection event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudDetectionEvent {
    pub event_id: String,
    pub timestamp: DateTime<Utc>,
    pub transaction_id: String,
    pub customer_id: String,
    pub fraud_score: f64,
    pub model_prediction: bool,
    pub actual_fraud: Option<bool>, // Set after investigation
    pub blocked: bool,
    pub amount: f64,
    pub model_version: String,
    pub detection_rules: Vec<String>,
}

/// Model performance metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPerformanceMetrics {
    pub model_version: String,
    pub total_predictions: u64,
    pub true_positives: u64,
    pub false_positives: u64,
    pub true_negatives: u64,
    pub false_negatives: u64,
    pub last_updated: DateTime<Utc>,
    pub training_date: DateTime<Utc>,
    pub feature_importance: HashMap<String, f64>,
}

/// Fraud alert information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudAlert {
    pub alert_id: String,
    pub timestamp: DateTime<Utc>,
    pub severity: AlertSeverity,
    pub alert_type: FraudAlertType,
    pub description: String,
    pub affected_transactions: Vec<String>,
    pub recommended_actions: Vec<String>,
    pub resolved: bool,
    pub resolved_at: Option<DateTime<Utc>>,
}

/// Alert severity levels
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertSeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// Types of fraud alerts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FraudAlertType {
    HighFraudScore,
    ModelDrift,
    UnusualPattern,
    SystemAnomaly,
    PerformanceDegradation,
}

/// Transaction statistics for fraud analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionStats {
    pub total_transactions: u64,
    pub total_amount: f64,
    pub blocked_transactions: u64,
    pub blocked_amount: f64,
    pub average_fraud_score: f64,
    pub last_updated: DateTime<Utc>,
}

/// Fraud KPI with trend analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FraudKPI {
    pub name: String,
    pub current_value: f64,
    pub previous_value: f64,
    pub benchmark: f64,
    pub trend: TrendDirection,
    pub last_updated: DateTime<Utc>,
}

/// Trend direction for KPIs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrendDirection {
    Improving,
    Declining,
    Stable,
    Volatile,
}

impl FraudMetricsCollector {
    /// Create a new fraud metrics collector
    pub async fn new(config: FraudMetricsConfig) -> MetricsResult<Self> {
        Ok(Self {
            config,
            detection_history: Arc::new(RwLock::new(Vec::new())),
            model_performance: Arc::new(RwLock::new(ModelPerformanceMetrics::default())),
            alert_history: Arc::new(RwLock::new(Vec::new())),
            transaction_stats: Arc::new(RwLock::new(TransactionStats::default())),
        })
    }

    /// Start the fraud metrics collection
    pub async fn start(&self) -> MetricsResult<()> {
        if !self.config.enabled {
            return Ok(());
        }

        // Initialize background tasks for metrics collection
        self.start_metrics_collection().await?;
        self.start_performance_monitoring().await?;
        self.start_alert_monitoring().await?;

        Ok(())
    }

    /// Stop the fraud metrics collection
    pub async fn stop(&self) -> MetricsResult<()> {
        // Cleanup and save final metrics
        self.cleanup_old_data().await?;
        Ok(())
    }

    /// Record a fraud detection event
    pub async fn record_detection_event(&self, event: FraudDetectionEvent) -> MetricsResult<()> {
        let mut history = self.detection_history.write().await;
        history.push(event.clone());

        // Update transaction stats
        let mut stats = self.transaction_stats.write().await;
        stats.total_transactions += 1;
        stats.total_amount += event.amount;

        if event.blocked {
            stats.blocked_transactions += 1;
            stats.blocked_amount += event.amount;
        }

        // Update average fraud score
        let total_score: f64 = history.iter().map(|e| e.fraud_score).sum();
        stats.average_fraud_score = total_score / history.len() as f64;
        stats.last_updated = Utc::now();

        // Update model performance if we have ground truth
        if let Some(actual_fraud) = event.actual_fraud {
            self.update_model_performance(&event, actual_fraud).await?;
        }

        // Check for alerts
        self.check_for_alerts(&event).await?;

        Ok(())
    }

    /// Get comprehensive fraud detection statistics
    pub async fn get_detection_stats(&self) -> MetricsResult<FraudDetectionStats> {
        let history = self.detection_history.read().await;
        let performance = self.model_performance.read().await;
        let stats = self.transaction_stats.read().await;
        let alerts = self.alert_history.read().await;

        if history.is_empty() {
            return Ok(FraudDetectionStats::default());
        }

        // Calculate detection rate
        let detection_rate = self.calculate_detection_rate(&performance).await?;

        // Calculate false positive rate
        let false_positive_rate = self.calculate_false_positive_rate(&performance).await?;

        // Calculate model accuracy
        let model_accuracy = self.calculate_model_accuracy(&performance).await?;

        // Calculate prevented loss
        let prevented_loss = stats.blocked_amount;

        Ok(FraudDetectionStats {
            detection_rate,
            false_positive_rate,
            blocked_transactions: stats.blocked_transactions,
            prevented_loss_amount: prevented_loss,
            model_accuracy,
            alerts_generated: alerts.len() as u64,
        })
    }

    /// Get fraud KPIs with trend analysis
    pub async fn get_fraud_kpis(&self) -> MetricsResult<Vec<FraudKPI>> {
        let stats = self.get_detection_stats().await?;
        let mut kpis = Vec::new();

        // Detection Rate KPI
        kpis.push(FraudKPI {
            name: "Fraud Detection Rate".to_string(),
            current_value: stats.detection_rate,
            previous_value: self.get_previous_detection_rate().await?,
            benchmark: 95.0, // Industry benchmark
            trend: self.calculate_trend(stats.detection_rate, self.get_previous_detection_rate().await?),
            last_updated: Utc::now(),
        });

        // False Positive Rate KPI
        kpis.push(FraudKPI {
            name: "False Positive Rate".to_string(),
            current_value: stats.false_positive_rate,
            previous_value: self.get_previous_false_positive_rate().await?,
            benchmark: 5.0, // Target: less than 5%
            trend: self.calculate_trend(stats.false_positive_rate, self.get_previous_false_positive_rate().await?),
            last_updated: Utc::now(),
        });

        // Model Accuracy KPI
        kpis.push(FraudKPI {
            name: "Model Accuracy".to_string(),
            current_value: stats.model_accuracy,
            previous_value: self.get_previous_model_accuracy().await?,
            benchmark: 98.0, // Target: 98%+ accuracy
            trend: self.calculate_trend(stats.model_accuracy, self.get_previous_model_accuracy().await?),
            last_updated: Utc::now(),
        });

        Ok(kpis)
    }

    /// Calculate detection rate based on model performance
    async fn calculate_detection_rate(&self, performance: &ModelPerformanceMetrics) -> MetricsResult<f64> {
        if performance.total_predictions == 0 {
            return Ok(0.0);
        }

        let true_positives = performance.true_positives as f64;
        let false_negatives = performance.false_negatives as f64;

        if true_positives + false_negatives == 0.0 {
            return Ok(0.0);
        }

        Ok((true_positives / (true_positives + false_negatives)) * 100.0)
    }

    /// Calculate false positive rate
    async fn calculate_false_positive_rate(&self, performance: &ModelPerformanceMetrics) -> MetricsResult<f64> {
        if performance.total_predictions == 0 {
            return Ok(0.0);
        }

        let false_positives = performance.false_positives as f64;
        let true_negatives = performance.true_negatives as f64;

        if false_positives + true_negatives == 0.0 {
            return Ok(0.0);
        }

        Ok((false_positives / (false_positives + true_negatives)) * 100.0)
    }

    /// Calculate model accuracy
    async fn calculate_model_accuracy(&self, performance: &ModelPerformanceMetrics) -> MetricsResult<f64> {
        if performance.total_predictions == 0 {
            return Ok(0.0);
        }

        let correct_predictions = (performance.true_positives + performance.true_negatives) as f64;
        let total_predictions = performance.total_predictions as f64;

        Ok((correct_predictions / total_predictions) * 100.0)
    }

    /// Update model performance metrics
    async fn update_model_performance(&self, event: &FraudDetectionEvent, actual_fraud: bool) -> MetricsResult<()> {
        let mut performance = self.model_performance.write().await;

        performance.total_predictions += 1;

        match (event.model_prediction, actual_fraud) {
            (true, true) => performance.true_positives += 1,
            (true, false) => performance.false_positives += 1,
            (false, true) => performance.false_negatives += 1,
            (false, false) => performance.true_negatives += 1,
        }

        performance.last_updated = Utc::now();
        Ok(())
    }

    /// Check for fraud alerts based on current metrics
    async fn check_for_alerts(&self, event: &FraudDetectionEvent) -> MetricsResult<()> {
        let mut alerts = self.alert_history.write().await;

        // High fraud score alert
        if event.fraud_score > self.config.alert_threshold {
            alerts.push(FraudAlert {
                alert_id: format!("alert_{}", uuid::Uuid::new_v4()),
                timestamp: Utc::now(),
                severity: if event.fraud_score > 0.9 { AlertSeverity::Critical } else { AlertSeverity::High },
                alert_type: FraudAlertType::HighFraudScore,
                description: format!("High fraud score detected: {:.2}", event.fraud_score),
                affected_transactions: vec![event.transaction_id.clone()],
                recommended_actions: vec![
                    "Review transaction details".to_string(),
                    "Contact customer for verification".to_string(),
                    "Consider blocking transaction".to_string(),
                ],
                resolved: false,
                resolved_at: None,
            });
        }

        Ok(())
    }

    /// Start background metrics collection
    async fn start_metrics_collection(&self) -> MetricsResult<()> {
        // This would start background tasks for continuous metrics collection
        // In a real implementation, this would spawn tokio tasks
        Ok(())
    }

    /// Start performance monitoring
    async fn start_performance_monitoring(&self) -> MetricsResult<()> {
        // Monitor model performance and detect drift
        Ok(())
    }

    /// Start alert monitoring
    async fn start_alert_monitoring(&self) -> MetricsResult<()> {
        // Monitor for alert conditions and send notifications
        Ok(())
    }

    /// Cleanup old data based on retention policy
    async fn cleanup_old_data(&self) -> MetricsResult<()> {
        let cutoff_date = Utc::now() - Duration::days(self.config.retention_days as i64);

        let mut history = self.detection_history.write().await;
        history.retain(|event| event.timestamp > cutoff_date);

        let mut alerts = self.alert_history.write().await;
        alerts.retain(|alert| alert.timestamp > cutoff_date);

        Ok(())
    }

    /// Calculate trend direction
    fn calculate_trend(&self, current: f64, previous: f64) -> TrendDirection {
        let change_percent = if previous != 0.0 {
            ((current - previous) / previous) * 100.0
        } else {
            0.0
        };

        match change_percent {
            x if x > 5.0 => TrendDirection::Improving,
            x if x < -5.0 => TrendDirection::Declining,
            x if x.abs() > 15.0 => TrendDirection::Volatile,
            _ => TrendDirection::Stable,
        }
    }

    /// Get previous period detection rate for trend analysis
    async fn get_previous_detection_rate(&self) -> MetricsResult<f64> {
        // This would calculate the detection rate from the previous period
        // For now, return a calculated value based on historical data
        let history = self.detection_history.read().await;
        if history.len() < 2 {
            return Ok(0.0);
        }

        // Calculate from first half of data as "previous"
        let mid_point = history.len() / 2;
        let previous_events = &history[0..mid_point];

        let fraud_events = previous_events.iter()
            .filter(|e| e.actual_fraud.unwrap_or(false))
            .count();

        if previous_events.is_empty() {
            Ok(0.0)
        } else {
            Ok((fraud_events as f64 / previous_events.len() as f64) * 100.0)
        }
    }

    /// Get previous period false positive rate
    async fn get_previous_false_positive_rate(&self) -> MetricsResult<f64> {
        // Similar calculation for false positive rate
        Ok(2.5) // Placeholder - would be calculated from historical data
    }

    /// Get previous period model accuracy
    async fn get_previous_model_accuracy(&self) -> MetricsResult<f64> {
        // Similar calculation for model accuracy
        Ok(96.2) // Placeholder - would be calculated from historical data
    }
}

impl Default for FraudMetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            collection_interval_seconds: 60,
            retention_days: 90,
            alert_threshold: 0.8,
            model_accuracy_threshold: 95.0,
            false_positive_threshold: 5.0,
        }
    }
}

impl Default for ModelPerformanceMetrics {
    fn default() -> Self {
        Self {
            model_version: "1.0.0".to_string(),
            total_predictions: 0,
            true_positives: 0,
            false_positives: 0,
            true_negatives: 0,
            false_negatives: 0,
            last_updated: Utc::now(),
            training_date: Utc::now(),
            feature_importance: HashMap::new(),
        }
    }
}

impl Default for TransactionStats {
    fn default() -> Self {
        Self {
            total_transactions: 0,
            total_amount: 0.0,
            blocked_transactions: 0,
            blocked_amount: 0.0,
            average_fraud_score: 0.0,
            last_updated: Utc::now(),
        }
    }
}
