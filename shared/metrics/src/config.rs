//! Metrics Configuration

use crate::{
    business_metrics::BusinessMetricsConfig,
    compliance_metrics::ComplianceMetricsConfig,
    risk_metrics::RiskMetricsConfig,
    fraud_metrics::FraudMetricsConfig,
    customer_metrics::CustomerMetricsConfig,
    transaction_metrics::TransactionMetricsConfig,
    operational_metrics::OperationalMetricsConfig,
    sla_metrics::SlaMetricsConfig,
    custom_metrics::CustomMetricsConfig,
};
use serde::{Deserialize, Serialize};

/// Main metrics configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    pub enabled: bool,
    pub export_interval_seconds: u64,
    pub retention_days: u32,
    pub business: BusinessMetricsConfig,
    pub compliance: ComplianceMetricsConfig,
    pub risk: RiskMetricsConfig,
    pub fraud: FraudMetricsConfig,
    pub customer: CustomerMetricsConfig,
    pub transaction: TransactionMetricsConfig,
    pub operational: OperationalMetricsConfig,
    pub sla: SlaMetricsConfig,
    pub custom: CustomMetricsConfig,
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            export_interval_seconds: 60,
            retention_days: 90,
            business: BusinessMetricsConfig::default(),
            compliance: ComplianceMetricsConfig::default(),
            risk: RiskMetricsConfig::default(),
            fraud: FraudMetricsConfig::default(),
            customer: CustomerMetricsConfig::default(),
            transaction: TransactionMetricsConfig::default(),
            operational: OperationalMetricsConfig::default(),
            sla: SlaMetricsConfig::default(),
            custom: CustomMetricsConfig::default(),
        }
    }
}
