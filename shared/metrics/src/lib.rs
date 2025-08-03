//! RegulateAI Business Metrics System
//! 
//! Comprehensive business metrics and analytics framework providing:
//! - Real-time business KPIs and operational metrics
//! - Compliance and regulatory reporting metrics
//! - Customer behavior and transaction analytics
//! - Risk assessment and fraud detection metrics
//! - Performance and SLA monitoring
//! - Custom dashboards and alerting
//! - Time-series data collection and analysis

pub mod business_metrics;
pub mod compliance_metrics;
pub mod risk_metrics;
pub mod fraud_metrics;
pub mod customer_metrics;
pub mod transaction_metrics;
pub mod operational_metrics;
pub mod sla_metrics;
pub mod custom_metrics;
pub mod collectors;
pub mod exporters;
pub mod dashboards;
pub mod alerts;
pub mod analytics;
pub mod config;
pub mod errors;

pub use business_metrics::{BusinessMetricsCollector, BusinessKPI};
pub use compliance_metrics::{ComplianceMetricsCollector, ComplianceKPI};
pub use risk_metrics::{RiskMetricsCollector, RiskKPI};
pub use fraud_metrics::{FraudMetricsCollector, FraudKPI};
pub use customer_metrics::{CustomerMetricsCollector, CustomerKPI};
pub use transaction_metrics::{TransactionMetricsCollector, TransactionKPI};
pub use operational_metrics::{OperationalMetricsCollector, OperationalKPI};
pub use sla_metrics::{SlaMetricsCollector, SlaKPI};
pub use custom_metrics::{CustomMetricsCollector, CustomMetric};
pub use collectors::MetricsCollector;
pub use exporters::{MetricsExporter, ExportFormat};
pub use dashboards::{DashboardManager, Dashboard};
pub use alerts::{AlertManager, Alert, AlertRule};
pub use analytics::{MetricsAnalyzer, AnalyticsEngine};
pub use config::MetricsConfig;
pub use errors::{MetricsError, MetricsResult};

/// Re-export Prometheus types
pub use prometheus::{Counter, Gauge, Histogram, IntCounter, IntGauge};

/// Metric types
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum MetricType {
    Counter,
    Gauge,
    Histogram,
    Summary,
    Custom(String),
}

/// Metric value
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum MetricValue {
    Counter(u64),
    Gauge(f64),
    Histogram(Vec<f64>),
    Summary { sum: f64, count: u64, quantiles: Vec<(f64, f64)> },
    Custom(serde_json::Value),
}

/// Time series data point
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DataPoint {
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub value: MetricValue,
    pub labels: std::collections::HashMap<String, String>,
}

/// Metrics registry for managing all metrics
pub struct MetricsRegistry {
    business_metrics: BusinessMetricsCollector,
    compliance_metrics: ComplianceMetricsCollector,
    risk_metrics: RiskMetricsCollector,
    fraud_metrics: FraudMetricsCollector,
    customer_metrics: CustomerMetricsCollector,
    transaction_metrics: TransactionMetricsCollector,
    operational_metrics: OperationalMetricsCollector,
    sla_metrics: SlaMetricsCollector,
    custom_metrics: CustomMetricsCollector,
    config: MetricsConfig,
}

impl MetricsRegistry {
    /// Create a new metrics registry
    pub async fn new(config: MetricsConfig) -> MetricsResult<Self> {
        Ok(Self {
            business_metrics: BusinessMetricsCollector::new(config.business.clone()).await?,
            compliance_metrics: ComplianceMetricsCollector::new(config.compliance.clone()).await?,
            risk_metrics: RiskMetricsCollector::new(config.risk.clone()).await?,
            fraud_metrics: FraudMetricsCollector::new(config.fraud.clone()).await?,
            customer_metrics: CustomerMetricsCollector::new(config.customer.clone()).await?,
            transaction_metrics: TransactionMetricsCollector::new(config.transaction.clone()).await?,
            operational_metrics: OperationalMetricsCollector::new(config.operational.clone()).await?,
            sla_metrics: SlaMetricsCollector::new(config.sla.clone()).await?,
            custom_metrics: CustomMetricsCollector::new(config.custom.clone()).await?,
            config,
        })
    }

    /// Get business metrics collector
    pub fn business(&self) -> &BusinessMetricsCollector {
        &self.business_metrics
    }

    /// Get compliance metrics collector
    pub fn compliance(&self) -> &ComplianceMetricsCollector {
        &self.compliance_metrics
    }

    /// Get risk metrics collector
    pub fn risk(&self) -> &RiskMetricsCollector {
        &self.risk_metrics
    }

    /// Get fraud metrics collector
    pub fn fraud(&self) -> &FraudMetricsCollector {
        &self.fraud_metrics
    }

    /// Get customer metrics collector
    pub fn customer(&self) -> &CustomerMetricsCollector {
        &self.customer_metrics
    }

    /// Get transaction metrics collector
    pub fn transaction(&self) -> &TransactionMetricsCollector {
        &self.transaction_metrics
    }

    /// Get operational metrics collector
    pub fn operational(&self) -> &OperationalMetricsCollector {
        &self.operational_metrics
    }

    /// Get SLA metrics collector
    pub fn sla(&self) -> &SlaMetricsCollector {
        &self.sla_metrics
    }

    /// Get custom metrics collector
    pub fn custom(&self) -> &CustomMetricsCollector {
        &self.custom_metrics
    }

    /// Start metrics collection
    pub async fn start_collection(&self) -> MetricsResult<()> {
        // Start all metric collectors
        self.business_metrics.start().await?;
        self.compliance_metrics.start().await?;
        self.risk_metrics.start().await?;
        self.fraud_metrics.start().await?;
        self.customer_metrics.start().await?;
        self.transaction_metrics.start().await?;
        self.operational_metrics.start().await?;
        self.sla_metrics.start().await?;
        self.custom_metrics.start().await?;

        tracing::info!("Metrics collection started");
        Ok(())
    }

    /// Stop metrics collection
    pub async fn stop_collection(&self) -> MetricsResult<()> {
        // Stop all metric collectors
        self.business_metrics.stop().await?;
        self.compliance_metrics.stop().await?;
        self.risk_metrics.stop().await?;
        self.fraud_metrics.stop().await?;
        self.customer_metrics.stop().await?;
        self.transaction_metrics.stop().await?;
        self.operational_metrics.stop().await?;
        self.sla_metrics.stop().await?;
        self.custom_metrics.stop().await?;

        tracing::info!("Metrics collection stopped");
        Ok(())
    }

    /// Get all metrics summary
    pub async fn get_metrics_summary(&self) -> MetricsResult<MetricsSummary> {
        Ok(MetricsSummary {
            business_kpis: self.business_metrics.get_current_kpis().await?,
            compliance_status: self.compliance_metrics.get_compliance_status().await?,
            risk_levels: self.risk_metrics.get_current_risk_levels().await?,
            fraud_detection_stats: self.fraud_metrics.get_detection_stats().await?,
            customer_analytics: self.customer_metrics.get_analytics_summary().await?,
            transaction_analytics: self.transaction_metrics.get_analytics_summary().await?,
            operational_health: self.operational_metrics.get_health_status().await?,
            sla_compliance: self.sla_metrics.get_sla_status().await?,
            custom_metrics_count: self.custom_metrics.get_metrics_count().await?,
            last_updated: chrono::Utc::now(),
        })
    }

    /// Export metrics in various formats
    pub async fn export_metrics(&self, format: ExportFormat) -> MetricsResult<String> {
        let exporter = MetricsExporter::new(format);
        let summary = self.get_metrics_summary().await?;
        exporter.export(&summary).await
    }
}

/// Comprehensive metrics summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MetricsSummary {
    pub business_kpis: Vec<BusinessKPI>,
    pub compliance_status: ComplianceStatus,
    pub risk_levels: RiskLevels,
    pub fraud_detection_stats: FraudDetectionStats,
    pub customer_analytics: CustomerAnalytics,
    pub transaction_analytics: TransactionAnalytics,
    pub operational_health: OperationalHealth,
    pub sla_compliance: SlaCompliance,
    pub custom_metrics_count: usize,
    pub last_updated: chrono::DateTime<chrono::Utc>,
}

/// Compliance status summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ComplianceStatus {
    pub overall_score: f64,
    pub aml_compliance: f64,
    pub kyc_compliance: f64,
    pub gdpr_compliance: f64,
    pub sox_compliance: f64,
    pub violations_count: u64,
    pub pending_reviews: u64,
}

/// Risk levels summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RiskLevels {
    pub overall_risk_score: f64,
    pub customer_risk_distribution: std::collections::HashMap<String, u64>,
    pub transaction_risk_distribution: std::collections::HashMap<String, u64>,
    pub high_risk_alerts: u64,
    pub risk_trend: String,
}

/// Fraud detection statistics
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FraudDetectionStats {
    pub detection_rate: f64,
    pub false_positive_rate: f64,
    pub blocked_transactions: u64,
    pub prevented_loss_amount: f64,
    pub model_accuracy: f64,
    pub alerts_generated: u64,
}

/// Customer analytics summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CustomerAnalytics {
    pub total_customers: u64,
    pub new_customers_today: u64,
    pub active_customers: u64,
    pub customer_satisfaction_score: f64,
    pub churn_rate: f64,
    pub average_customer_value: f64,
}

/// Transaction analytics summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TransactionAnalytics {
    pub total_transactions: u64,
    pub transactions_today: u64,
    pub total_volume: f64,
    pub average_transaction_size: f64,
    pub success_rate: f64,
    pub processing_time_avg: f64,
}

/// Operational health summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct OperationalHealth {
    pub system_uptime: f64,
    pub response_time_avg: f64,
    pub error_rate: f64,
    pub throughput: f64,
    pub resource_utilization: ResourceUtilization,
    pub service_health: std::collections::HashMap<String, String>,
}

/// Resource utilization metrics
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ResourceUtilization {
    pub cpu_usage: f64,
    pub memory_usage: f64,
    pub disk_usage: f64,
    pub network_usage: f64,
}

/// SLA compliance summary
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SlaCompliance {
    pub overall_sla_score: f64,
    pub availability_sla: f64,
    pub response_time_sla: f64,
    pub throughput_sla: f64,
    pub sla_violations: u64,
    pub sla_credits_issued: f64,
}

/// Initialize the metrics system
pub async fn init_metrics_system(config: MetricsConfig) -> MetricsResult<MetricsRegistry> {
    tracing::info!("Initializing RegulateAI metrics system");
    
    let registry = MetricsRegistry::new(config).await?;
    registry.start_collection().await?;
    
    tracing::info!("Metrics system initialized successfully");
    Ok(registry)
}

/// Metrics middleware for HTTP requests
pub mod middleware {
    use super::*;
    use axum::{
        extract::{Request, State},
        http::StatusCode,
        middleware::Next,
        response::Response,
    };
    use std::sync::Arc;
    use std::time::Instant;

    /// HTTP metrics middleware
    pub async fn metrics_middleware(
        State(metrics): State<Arc<MetricsRegistry>>,
        request: Request,
        next: Next,
    ) -> Result<Response, StatusCode> {
        let start_time = Instant::now();
        let method = request.method().clone();
        let uri = request.uri().clone();
        
        // Execute request
        let response = next.run(request).await;
        
        // Record metrics
        let duration = start_time.elapsed();
        let status = response.status();
        
        // Record HTTP request metrics
        metrics.operational().record_http_request(
            method.as_str(),
            uri.path(),
            status.as_u16(),
            duration.as_millis() as f64,
        ).await;
        
        Ok(response)
    }
}

/// Utility functions for metrics
pub mod utils {
    use super::*;

    /// Calculate percentile from a vector of values
    pub fn calculate_percentile(values: &[f64], percentile: f64) -> f64 {
        if values.is_empty() {
            return 0.0;
        }
        
        let mut sorted_values = values.to_vec();
        sorted_values.sort_by(|a, b| a.partial_cmp(b).unwrap());
        
        let index = (percentile / 100.0 * (sorted_values.len() - 1) as f64).round() as usize;
        sorted_values[index.min(sorted_values.len() - 1)]
    }

    /// Calculate moving average
    pub fn calculate_moving_average(values: &[f64], window_size: usize) -> Vec<f64> {
        if values.len() < window_size {
            return vec![values.iter().sum::<f64>() / values.len() as f64];
        }
        
        values
            .windows(window_size)
            .map(|window| window.iter().sum::<f64>() / window_size as f64)
            .collect()
    }

    /// Calculate standard deviation
    pub fn calculate_standard_deviation(values: &[f64]) -> f64 {
        if values.is_empty() {
            return 0.0;
        }
        
        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let variance = values
            .iter()
            .map(|value| (value - mean).powi(2))
            .sum::<f64>() / values.len() as f64;
        
        variance.sqrt()
    }

    /// Format metric value for display
    pub fn format_metric_value(value: f64, unit: &str) -> String {
        match unit {
            "bytes" => format_bytes(value),
            "percentage" => format!("{:.2}%", value),
            "currency" => format!("${:.2}", value),
            "duration_ms" => format!("{:.2}ms", value),
            "duration_s" => format!("{:.2}s", value),
            _ => format!("{:.2}", value),
        }
    }

    fn format_bytes(bytes: f64) -> String {
        const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
        let mut size = bytes;
        let mut unit_index = 0;
        
        while size >= 1024.0 && unit_index < UNITS.len() - 1 {
            size /= 1024.0;
            unit_index += 1;
        }
        
        format!("{:.2} {}", size, UNITS[unit_index])
    }
}
