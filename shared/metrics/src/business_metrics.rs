//! Business Metrics Collection
//! 
//! Tracks key business performance indicators and operational metrics
//! for RegulateAI platform including revenue, customer growth, and efficiency.

use crate::{errors::{MetricsError, MetricsResult}, DataPoint, MetricValue};
use prometheus::{Counter, Gauge, Histogram, IntCounter, IntGauge, register_counter, register_gauge, register_histogram, register_int_counter, register_int_gauge};
use lazy_static::lazy_static;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};

lazy_static! {
    // Revenue metrics
    static ref TOTAL_REVENUE: Gauge = register_gauge!(
        "business_total_revenue",
        "Total revenue generated"
    ).unwrap();

    static ref MONTHLY_RECURRING_REVENUE: Gauge = register_gauge!(
        "business_monthly_recurring_revenue",
        "Monthly recurring revenue (MRR)"
    ).unwrap();

    static ref AVERAGE_REVENUE_PER_USER: Gauge = register_gauge!(
        "business_average_revenue_per_user",
        "Average revenue per user (ARPU)"
    ).unwrap();

    // Customer metrics
    static ref TOTAL_CUSTOMERS: IntGauge = register_int_gauge!(
        "business_total_customers",
        "Total number of customers"
    ).unwrap();

    static ref NEW_CUSTOMERS: IntCounter = register_int_counter!(
        "business_new_customers_total",
        "Total number of new customers acquired"
    ).unwrap();

    static ref CUSTOMER_CHURN_RATE: Gauge = register_gauge!(
        "business_customer_churn_rate",
        "Customer churn rate percentage"
    ).unwrap();

    // Transaction metrics
    static ref TRANSACTION_VOLUME: Counter = register_counter!(
        "business_transaction_volume_total",
        "Total transaction volume processed"
    ).unwrap();

    static ref TRANSACTION_COUNT: IntCounter = register_int_counter!(
        "business_transaction_count_total",
        "Total number of transactions processed"
    ).unwrap();

    static ref AVERAGE_TRANSACTION_SIZE: Gauge = register_gauge!(
        "business_average_transaction_size",
        "Average transaction size"
    ).unwrap();

    // Compliance metrics
    static ref COMPLIANCE_SCORE: Gauge = register_gauge!(
        "business_compliance_score",
        "Overall compliance score"
    ).unwrap();

    static ref AML_CHECKS_COMPLETED: IntCounter = register_int_counter!(
        "business_aml_checks_completed_total",
        "Total AML checks completed"
    ).unwrap();

    static ref KYC_VERIFICATIONS: IntCounter = register_int_counter!(
        "business_kyc_verifications_total",
        "Total KYC verifications completed"
    ).unwrap();

    // Operational efficiency
    static ref PROCESSING_TIME: Histogram = register_histogram!(
        "business_processing_time_seconds",
        "Time taken to process business operations"
    ).unwrap();

    static ref AUTOMATION_RATE: Gauge = register_gauge!(
        "business_automation_rate",
        "Percentage of automated processes"
    ).unwrap();

    static ref COST_PER_TRANSACTION: Gauge = register_gauge!(
        "business_cost_per_transaction",
        "Average cost per transaction"
    ).unwrap();
}

/// Business metrics collector
pub struct BusinessMetricsCollector {
    config: BusinessMetricsConfig,
    kpis: Vec<BusinessKPI>,
    data_points: Vec<DataPoint>,
}

/// Business metrics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BusinessMetricsConfig {
    pub enabled: bool,
    pub collection_interval_seconds: u64,
    pub retention_days: u32,
    pub revenue_tracking_enabled: bool,
    pub customer_analytics_enabled: bool,
    pub transaction_analytics_enabled: bool,
    pub compliance_tracking_enabled: bool,
    pub efficiency_tracking_enabled: bool,
}

/// Business Key Performance Indicator
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BusinessKPI {
    pub name: String,
    pub value: f64,
    pub unit: String,
    pub target: Option<f64>,
    pub trend: KPITrend,
    pub category: KPICategory,
    pub last_updated: DateTime<Utc>,
    pub description: String,
}

/// KPI trend direction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KPITrend {
    Up,
    Down,
    Stable,
    Unknown,
}

/// KPI categories
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KPICategory {
    Revenue,
    Customer,
    Transaction,
    Compliance,
    Efficiency,
    Risk,
    Custom(String),
}

impl BusinessMetricsCollector {
    /// Create a new business metrics collector
    pub async fn new(config: BusinessMetricsConfig) -> MetricsResult<Self> {
        Ok(Self {
            config,
            kpis: Vec::new(),
            data_points: Vec::new(),
        })
    }

    /// Start metrics collection
    pub async fn start(&self) -> MetricsResult<()> {
        if !self.config.enabled {
            return Ok(());
        }

        // Start background collection task
        let collection_interval = self.config.collection_interval_seconds;
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(
                std::time::Duration::from_secs(collection_interval)
            );

            loop {
                interval.tick().await;
                
                // Collect business metrics
                if let Err(e) = Self::collect_business_metrics().await {
                    tracing::error!("Failed to collect business metrics: {}", e);
                }
            }
        });

        tracing::info!("Business metrics collection started");
        Ok(())
    }

    /// Stop metrics collection
    pub async fn stop(&self) -> MetricsResult<()> {
        tracing::info!("Business metrics collection stopped");
        Ok(())
    }

    /// Record revenue
    pub async fn record_revenue(&self, amount: f64, currency: &str) -> MetricsResult<()> {
        if !self.config.revenue_tracking_enabled {
            return Ok(());
        }

        TOTAL_REVENUE.add(amount);
        
        tracing::debug!("Recorded revenue: {} {}", amount, currency);
        Ok(())
    }

    /// Record new customer
    pub async fn record_new_customer(&self, customer_id: &str, acquisition_cost: f64) -> MetricsResult<()> {
        if !self.config.customer_analytics_enabled {
            return Ok(());
        }

        NEW_CUSTOMERS.inc();
        TOTAL_CUSTOMERS.inc();
        
        tracing::debug!("Recorded new customer: {} (acquisition cost: {})", customer_id, acquisition_cost);
        Ok(())
    }

    /// Record customer churn
    pub async fn record_customer_churn(&self, customer_id: &str, reason: &str) -> MetricsResult<()> {
        if !self.config.customer_analytics_enabled {
            return Ok(());
        }

        TOTAL_CUSTOMERS.dec();
        
        // Calculate and update churn rate
        let total_customers = TOTAL_CUSTOMERS.get() as f64;
        if total_customers > 0.0 {
            // This is a simplified calculation - in practice, you'd track churn over time periods
            let churn_rate = 1.0 / total_customers * 100.0;
            CUSTOMER_CHURN_RATE.set(churn_rate);
        }
        
        tracing::debug!("Recorded customer churn: {} (reason: {})", customer_id, reason);
        Ok(())
    }

    /// Record transaction
    pub async fn record_transaction(&self, amount: f64, transaction_type: &str, processing_time_ms: f64) -> MetricsResult<()> {
        if !self.config.transaction_analytics_enabled {
            return Ok(());
        }

        TRANSACTION_VOLUME.inc_by(amount);
        TRANSACTION_COUNT.inc();
        PROCESSING_TIME.observe(processing_time_ms / 1000.0);
        
        // Update average transaction size
        let total_volume = TRANSACTION_VOLUME.get();
        let total_count = TRANSACTION_COUNT.get() as f64;
        if total_count > 0.0 {
            AVERAGE_TRANSACTION_SIZE.set(total_volume / total_count);
        }
        
        tracing::debug!("Recorded transaction: {} {} (type: {}, processing time: {}ms)", 
                       amount, "USD", transaction_type, processing_time_ms);
        Ok(())
    }

    /// Record AML check
    pub async fn record_aml_check(&self, customer_id: &str, result: &str, processing_time_ms: f64) -> MetricsResult<()> {
        if !self.config.compliance_tracking_enabled {
            return Ok(());
        }

        AML_CHECKS_COMPLETED.inc();
        PROCESSING_TIME.observe(processing_time_ms / 1000.0);
        
        tracing::debug!("Recorded AML check: {} (result: {}, processing time: {}ms)", 
                       customer_id, result, processing_time_ms);
        Ok(())
    }

    /// Record KYC verification
    pub async fn record_kyc_verification(&self, customer_id: &str, status: &str, processing_time_ms: f64) -> MetricsResult<()> {
        if !self.config.compliance_tracking_enabled {
            return Ok(());
        }

        KYC_VERIFICATIONS.inc();
        PROCESSING_TIME.observe(processing_time_ms / 1000.0);
        
        tracing::debug!("Recorded KYC verification: {} (status: {}, processing time: {}ms)", 
                       customer_id, status, processing_time_ms);
        Ok(())
    }

    /// Update compliance score
    pub async fn update_compliance_score(&self, score: f64) -> MetricsResult<()> {
        if !self.config.compliance_tracking_enabled {
            return Ok(());
        }

        COMPLIANCE_SCORE.set(score);
        
        tracing::debug!("Updated compliance score: {}", score);
        Ok(())
    }

    /// Update automation rate
    pub async fn update_automation_rate(&self, rate: f64) -> MetricsResult<()> {
        if !self.config.efficiency_tracking_enabled {
            return Ok(());
        }

        AUTOMATION_RATE.set(rate);
        
        tracing::debug!("Updated automation rate: {}%", rate);
        Ok(())
    }

    /// Get current KPIs
    pub async fn get_current_kpis(&self) -> MetricsResult<Vec<BusinessKPI>> {
        let mut kpis = Vec::new();

        // Revenue KPIs
        if self.config.revenue_tracking_enabled {
            kpis.push(BusinessKPI {
                name: "Total Revenue".to_string(),
                value: TOTAL_REVENUE.get(),
                unit: "USD".to_string(),
                target: Some(1_000_000.0),
                trend: KPITrend::Up,
                category: KPICategory::Revenue,
                last_updated: Utc::now(),
                description: "Total revenue generated across all services".to_string(),
            });

            kpis.push(BusinessKPI {
                name: "Average Revenue Per User".to_string(),
                value: AVERAGE_REVENUE_PER_USER.get(),
                unit: "USD".to_string(),
                target: Some(500.0),
                trend: KPITrend::Stable,
                category: KPICategory::Revenue,
                last_updated: Utc::now(),
                description: "Average revenue generated per user".to_string(),
            });
        }

        // Customer KPIs
        if self.config.customer_analytics_enabled {
            kpis.push(BusinessKPI {
                name: "Total Customers".to_string(),
                value: TOTAL_CUSTOMERS.get() as f64,
                unit: "count".to_string(),
                target: Some(10_000.0),
                trend: KPITrend::Up,
                category: KPICategory::Customer,
                last_updated: Utc::now(),
                description: "Total number of active customers".to_string(),
            });

            kpis.push(BusinessKPI {
                name: "Customer Churn Rate".to_string(),
                value: CUSTOMER_CHURN_RATE.get(),
                unit: "percentage".to_string(),
                target: Some(5.0),
                trend: KPITrend::Down,
                category: KPICategory::Customer,
                last_updated: Utc::now(),
                description: "Percentage of customers who churned".to_string(),
            });
        }

        // Transaction KPIs
        if self.config.transaction_analytics_enabled {
            kpis.push(BusinessKPI {
                name: "Transaction Volume".to_string(),
                value: TRANSACTION_VOLUME.get(),
                unit: "USD".to_string(),
                target: Some(10_000_000.0),
                trend: KPITrend::Up,
                category: KPICategory::Transaction,
                last_updated: Utc::now(),
                description: "Total volume of transactions processed".to_string(),
            });

            kpis.push(BusinessKPI {
                name: "Average Transaction Size".to_string(),
                value: AVERAGE_TRANSACTION_SIZE.get(),
                unit: "USD".to_string(),
                target: Some(1_000.0),
                trend: KPITrend::Stable,
                category: KPICategory::Transaction,
                last_updated: Utc::now(),
                description: "Average size of transactions".to_string(),
            });
        }

        // Compliance KPIs
        if self.config.compliance_tracking_enabled {
            kpis.push(BusinessKPI {
                name: "Compliance Score".to_string(),
                value: COMPLIANCE_SCORE.get(),
                unit: "percentage".to_string(),
                target: Some(95.0),
                trend: KPITrend::Up,
                category: KPICategory::Compliance,
                last_updated: Utc::now(),
                description: "Overall compliance score across all regulations".to_string(),
            });
        }

        // Efficiency KPIs
        if self.config.efficiency_tracking_enabled {
            kpis.push(BusinessKPI {
                name: "Automation Rate".to_string(),
                value: AUTOMATION_RATE.get(),
                unit: "percentage".to_string(),
                target: Some(80.0),
                trend: KPITrend::Up,
                category: KPICategory::Efficiency,
                last_updated: Utc::now(),
                description: "Percentage of processes that are automated".to_string(),
            });
        }

        Ok(kpis)
    }

    /// Collect business metrics (internal method)
    async fn collect_business_metrics() -> MetricsResult<()> {
        // This would typically query databases, APIs, etc. to collect current metrics
        // For now, we'll just update some sample metrics
        
        // Update MRR based on current revenue (simplified calculation)
        let total_revenue = TOTAL_REVENUE.get();
        let estimated_mrr = total_revenue * 0.1; // Assume 10% of total revenue is monthly
        MONTHLY_RECURRING_REVENUE.set(estimated_mrr);
        
        // Update ARPU
        let total_customers = TOTAL_CUSTOMERS.get() as f64;
        if total_customers > 0.0 {
            let arpu = total_revenue / total_customers;
            AVERAGE_REVENUE_PER_USER.set(arpu);
        }
        
        // Update cost per transaction
        let total_transactions = TRANSACTION_COUNT.get() as f64;
        if total_transactions > 0.0 {
            let estimated_cost_per_transaction = 2.50; // Example fixed cost
            COST_PER_TRANSACTION.set(estimated_cost_per_transaction);
        }
        
        Ok(())
    }
}

impl Default for BusinessMetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            collection_interval_seconds: 60,
            retention_days: 90,
            revenue_tracking_enabled: true,
            customer_analytics_enabled: true,
            transaction_analytics_enabled: true,
            compliance_tracking_enabled: true,
            efficiency_tracking_enabled: true,
        }
    }
}
