//! Transaction monitoring and suspicious activity detection

use async_trait::async_trait;
use chrono::{DateTime, Utc, Duration};
use sea_orm::DatabaseConnection;
use std::collections::HashMap;
use std::sync::Arc;
use tracing::{info, warn, debug};
use uuid::Uuid;

use regulateai_config::AmlServiceConfig;
use regulateai_errors::RegulateAIError;
use regulateai_database::entities::{Customer, Transaction};

use crate::models::{TransactionMonitoringResult, TriggeredRule, AlertSeverity};
use crate::repositories::{TransactionRepository, AlertRepository};

/// Transaction monitoring engine
pub struct TransactionMonitor {
    transaction_repo: Arc<TransactionRepository>,
    alert_repo: Arc<AlertRepository>,
    config: AmlServiceConfig,
    monitoring_rules: Vec<Box<dyn MonitoringRule + Send + Sync>>,
}

impl TransactionMonitor {
    /// Create a new transaction monitor
    pub fn new(
        transaction_repo: Arc<TransactionRepository>,
        alert_repo: Arc<AlertRepository>,
        config: AmlServiceConfig,
    ) -> Self {
        let mut monitor = Self {
            transaction_repo,
            alert_repo,
            config: config.clone(),
            monitoring_rules: Vec::new(),
        };

        // Initialize default monitoring rules
        monitor.initialize_default_rules();
        monitor
    }

    /// Monitor a single transaction for suspicious activity
    pub async fn monitor_transaction(
        &self,
        transaction: &Transaction,
        customer: &Customer,
    ) -> Result<TransactionMonitoringResult, RegulateAIError> {
        debug!("Monitoring transaction: {} for customer: {}", transaction.id, customer.id);

        let mut triggered_rules = Vec::new();
        let mut risk_factors = Vec::new();
        let mut total_risk_score = 0.0;

        // Create monitoring context
        let context = MonitoringContext {
            transaction: transaction.clone(),
            customer: customer.clone(),
            transaction_history: self.get_customer_transaction_history(customer.id, 90).await?,
            customer_profile: self.build_customer_profile(customer.id).await?,
        };

        // Run all monitoring rules
        for rule in &self.monitoring_rules {
            match rule.evaluate(&context).await {
                Ok(Some(result)) => {
                    info!("Rule '{}' triggered for transaction: {}", result.rule_name, transaction.id);
                    
                    total_risk_score += result.risk_score;
                    risk_factors.push(result.description.clone());
                    triggered_rules.push(result);
                }
                Ok(None) => {
                    // Rule did not trigger
                    debug!("Rule '{}' did not trigger", rule.name());
                }
                Err(e) => {
                    warn!("Error evaluating rule '{}': {}", rule.name(), e);
                }
            }
        }

        // Normalize risk score (0-100 scale)
        let normalized_risk_score = (total_risk_score / self.monitoring_rules.len() as f64).min(100.0);
        
        // Determine if transaction is suspicious
        let is_suspicious = normalized_risk_score >= self.config.risk_score_threshold || 
                           triggered_rules.iter().any(|r| matches!(r.severity, AlertSeverity::High | AlertSeverity::Critical));

        Ok(TransactionMonitoringResult {
            transaction_id: transaction.id,
            is_suspicious,
            risk_score: normalized_risk_score,
            risk_factors,
            triggered_rules,
            monitoring_timestamp: Utc::now(),
        })
    }

    /// Initialize default monitoring rules
    fn initialize_default_rules(&mut self) {
        // High value transaction rule
        self.monitoring_rules.push(Box::new(HighValueTransactionRule {
            threshold: self.config.transaction_threshold,
        }));

        // Velocity rule - multiple transactions in short time
        self.monitoring_rules.push(Box::new(VelocityRule {
            max_transactions: 10,
            time_window_hours: 1,
        }));

        // Round amount rule - structuring detection
        self.monitoring_rules.push(Box::new(RoundAmountRule {
            threshold: 9999.99, // Just under reporting threshold
        }));

        // Geographic anomaly rule
        self.monitoring_rules.push(Box::new(GeographicAnomalyRule));

        // Time-based anomaly rule
        self.monitoring_rules.push(Box::new(TimeAnomalyRule));

        // Counterparty risk rule
        self.monitoring_rules.push(Box::new(CounterpartyRiskRule));

        // Behavioral pattern rule
        self.monitoring_rules.push(Box::new(BehavioralPatternRule));

        info!("Initialized {} monitoring rules", self.monitoring_rules.len());
    }

    /// Get customer transaction history
    async fn get_customer_transaction_history(
        &self,
        customer_id: Uuid,
        days: i64,
    ) -> Result<Vec<Transaction>, RegulateAIError> {
        let since_date = Utc::now() - Duration::days(days);
        self.transaction_repo.get_customer_transactions_since(customer_id, since_date).await
    }

    /// Build customer behavioral profile
    async fn build_customer_profile(&self, customer_id: Uuid) -> Result<CustomerProfile, RegulateAIError> {
        let transactions = self.get_customer_transaction_history(customer_id, 365).await?;
        
        if transactions.is_empty() {
            return Ok(CustomerProfile::default());
        }

        let total_amount: f64 = transactions.iter().map(|t| t.amount.to_f64().unwrap_or(0.0)).sum();
        let avg_amount = total_amount / transactions.len() as f64;
        
        let mut country_frequency = HashMap::new();
        let mut time_patterns = Vec::new();
        let mut amount_patterns = Vec::new();

        for transaction in &transactions {
            // Track country patterns
            if let Some(country) = &transaction.counterparty_country {
                *country_frequency.entry(country.clone()).or_insert(0) += 1;
            }

            // Track time patterns
            time_patterns.push(transaction.transaction_date.hour());
            
            // Track amount patterns
            amount_patterns.push(transaction.amount.to_f64().unwrap_or(0.0));
        }

        Ok(CustomerProfile {
            total_transactions: transactions.len(),
            average_amount: avg_amount,
            total_volume: total_amount,
            common_countries: country_frequency,
            typical_hours: time_patterns,
            amount_variance: calculate_variance(&amount_patterns),
        })
    }
}

/// Monitoring context provided to rules
#[derive(Debug, Clone)]
pub struct MonitoringContext {
    pub transaction: Transaction,
    pub customer: Customer,
    pub transaction_history: Vec<Transaction>,
    pub customer_profile: CustomerProfile,
}

/// Customer behavioral profile
#[derive(Debug, Clone, Default)]
pub struct CustomerProfile {
    pub total_transactions: usize,
    pub average_amount: f64,
    pub total_volume: f64,
    pub common_countries: HashMap<String, usize>,
    pub typical_hours: Vec<u32>,
    pub amount_variance: f64,
}

/// Trait for monitoring rules
#[async_trait]
pub trait MonitoringRule {
    /// Rule name
    fn name(&self) -> &str;
    
    /// Evaluate the rule against a transaction
    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError>;
}

/// High value transaction rule
pub struct HighValueTransactionRule {
    threshold: f64,
}

#[async_trait]
impl MonitoringRule for HighValueTransactionRule {
    fn name(&self) -> &str {
        "High Value Transaction"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        let amount = context.transaction.amount.to_f64().unwrap_or(0.0);
        
        if amount >= self.threshold {
            Ok(Some(TriggeredRule {
                rule_id: "HVT001".to_string(),
                rule_name: self.name().to_string(),
                rule_type: "AMOUNT".to_string(),
                severity: if amount >= self.threshold * 5.0 { AlertSeverity::Critical } else { AlertSeverity::High },
                description: format!("High value transaction: ${:.2}", amount),
                risk_score: ((amount / self.threshold) * 25.0).min(100.0),
                threshold_value: Some(self.threshold),
                actual_value: Some(amount),
            }))
        } else {
            Ok(None)
        }
    }
}

/// Velocity rule - detects rapid succession of transactions
pub struct VelocityRule {
    max_transactions: usize,
    time_window_hours: i64,
}

#[async_trait]
impl MonitoringRule for VelocityRule {
    fn name(&self) -> &str {
        "Transaction Velocity"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        let cutoff_time = context.transaction.transaction_date - Duration::hours(self.time_window_hours);
        
        let recent_transactions = context.transaction_history
            .iter()
            .filter(|t| t.transaction_date >= cutoff_time)
            .count();

        if recent_transactions > self.max_transactions {
            Ok(Some(TriggeredRule {
                rule_id: "VEL001".to_string(),
                rule_name: self.name().to_string(),
                rule_type: "VELOCITY".to_string(),
                severity: AlertSeverity::Medium,
                description: format!("{} transactions in {} hours", recent_transactions, self.time_window_hours),
                risk_score: ((recent_transactions as f64 / self.max_transactions as f64) * 30.0).min(100.0),
                threshold_value: Some(self.max_transactions as f64),
                actual_value: Some(recent_transactions as f64),
            }))
        } else {
            Ok(None)
        }
    }
}

/// Round amount rule - detects potential structuring
pub struct RoundAmountRule {
    threshold: f64,
}

#[async_trait]
impl MonitoringRule for RoundAmountRule {
    fn name(&self) -> &str {
        "Round Amount Pattern"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        let amount = context.transaction.amount.to_f64().unwrap_or(0.0);
        
        // Check if amount is suspiciously close to reporting thresholds
        let is_suspicious_round = amount > self.threshold * 0.95 && amount < self.threshold;
        let is_exact_round = amount % 1000.0 == 0.0 && amount >= 5000.0;
        
        if is_suspicious_round || is_exact_round {
            let severity = if is_suspicious_round { AlertSeverity::High } else { AlertSeverity::Medium };
            let description = if is_suspicious_round {
                format!("Amount ${:.2} just under reporting threshold", amount)
            } else {
                format!("Exact round amount: ${:.2}", amount)
            };

            Ok(Some(TriggeredRule {
                rule_id: "RND001".to_string(),
                rule_name: self.name().to_string(),
                rule_type: "PATTERN".to_string(),
                severity,
                description,
                risk_score: if is_suspicious_round { 40.0 } else { 20.0 },
                threshold_value: Some(self.threshold),
                actual_value: Some(amount),
            }))
        } else {
            Ok(None)
        }
    }
}

/// Geographic anomaly rule
pub struct GeographicAnomalyRule;

#[async_trait]
impl MonitoringRule for GeographicAnomalyRule {
    fn name(&self) -> &str {
        "Geographic Anomaly"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        if let Some(country) = &context.transaction.counterparty_country {
            // Check if this is a high-risk country
            let high_risk_countries = vec!["AF", "IR", "KP", "SY"]; // Example high-risk countries
            
            if high_risk_countries.contains(&country.as_str()) {
                return Ok(Some(TriggeredRule {
                    rule_id: "GEO001".to_string(),
                    rule_name: self.name().to_string(),
                    rule_type: "LOCATION".to_string(),
                    severity: AlertSeverity::High,
                    description: format!("Transaction to high-risk country: {}", country),
                    risk_score: 50.0,
                    threshold_value: None,
                    actual_value: None,
                }));
            }

            // Check if this country is unusual for this customer
            let country_frequency = context.customer_profile.common_countries.get(country).unwrap_or(&0);
            let total_transactions = context.customer_profile.total_transactions;
            
            if total_transactions > 10 && *country_frequency == 0 {
                return Ok(Some(TriggeredRule {
                    rule_id: "GEO002".to_string(),
                    rule_name: self.name().to_string(),
                    rule_type: "LOCATION".to_string(),
                    severity: AlertSeverity::Medium,
                    description: format!("First transaction to country: {}", country),
                    risk_score: 25.0,
                    threshold_value: None,
                    actual_value: None,
                }));
            }
        }

        Ok(None)
    }
}

/// Time-based anomaly rule
pub struct TimeAnomalyRule;

#[async_trait]
impl MonitoringRule for TimeAnomalyRule {
    fn name(&self) -> &str {
        "Time Anomaly"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        let transaction_hour = context.transaction.transaction_date.hour();
        
        // Flag transactions during unusual hours (late night/early morning)
        if transaction_hour >= 23 || transaction_hour <= 5 {
            // Check if this is unusual for the customer
            let night_transactions = context.customer_profile.typical_hours
                .iter()
                .filter(|&&h| h >= 23 || h <= 5)
                .count();
            
            let total_transactions = context.customer_profile.total_transactions;
            let night_ratio = if total_transactions > 0 {
                night_transactions as f64 / total_transactions as f64
            } else {
                0.0
            };

            // If customer rarely transacts at night, flag it
            if total_transactions > 10 && night_ratio < 0.1 {
                return Ok(Some(TriggeredRule {
                    rule_id: "TIME001".to_string(),
                    rule_name: self.name().to_string(),
                    rule_type: "BEHAVIORAL".to_string(),
                    severity: AlertSeverity::Low,
                    description: format!("Unusual transaction time: {}:00", transaction_hour),
                    risk_score: 15.0,
                    threshold_value: Some(0.1),
                    actual_value: Some(night_ratio),
                }));
            }
        }

        Ok(None)
    }
}

/// Counterparty risk rule
pub struct CounterpartyRiskRule;

#[async_trait]
impl MonitoringRule for CounterpartyRiskRule {
    fn name(&self) -> &str {
        "Counterparty Risk"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        // This would integrate with external counterparty risk databases
        // For now, implement basic checks
        
        if let Some(counterparty) = &context.transaction.counterparty_name {
            // Check for suspicious patterns in counterparty names
            let suspicious_keywords = vec!["cash", "bearer", "anonymous", "shell"];
            let counterparty_lower = counterparty.to_lowercase();
            
            for keyword in suspicious_keywords {
                if counterparty_lower.contains(keyword) {
                    return Ok(Some(TriggeredRule {
                        rule_id: "CP001".to_string(),
                        rule_name: self.name().to_string(),
                        rule_type: "COUNTERPARTY".to_string(),
                        severity: AlertSeverity::Medium,
                        description: format!("Suspicious counterparty name: {}", counterparty),
                        risk_score: 30.0,
                        threshold_value: None,
                        actual_value: None,
                    }));
                }
            }
        }

        Ok(None)
    }
}

/// Behavioral pattern rule
pub struct BehavioralPatternRule;

#[async_trait]
impl MonitoringRule for BehavioralPatternRule {
    fn name(&self) -> &str {
        "Behavioral Pattern"
    }

    async fn evaluate(&self, context: &MonitoringContext) -> Result<Option<TriggeredRule>, RegulateAIError> {
        let amount = context.transaction.amount.to_f64().unwrap_or(0.0);
        let avg_amount = context.customer_profile.average_amount;
        
        // Check for significant deviation from normal behavior
        if avg_amount > 0.0 && context.customer_profile.total_transactions > 5 {
            let deviation_ratio = (amount - avg_amount).abs() / avg_amount;
            
            if deviation_ratio > 5.0 { // Transaction is 5x larger/smaller than average
                return Ok(Some(TriggeredRule {
                    rule_id: "BEH001".to_string(),
                    rule_name: self.name().to_string(),
                    rule_type: "BEHAVIORAL".to_string(),
                    severity: AlertSeverity::Medium,
                    description: format!("Amount ${:.2} deviates significantly from average ${:.2}", amount, avg_amount),
                    risk_score: (deviation_ratio * 5.0).min(50.0),
                    threshold_value: Some(avg_amount * 5.0),
                    actual_value: Some(amount),
                }));
            }
        }

        Ok(None)
    }
}

/// Calculate variance of a numeric vector
fn calculate_variance(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }

    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let variance = values.iter()
        .map(|x| (x - mean).powi(2))
        .sum::<f64>() / (values.len() - 1) as f64;
    
    variance
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use regulateai_database::entities::{Customer, Transaction};
    use rust_decimal::Decimal;

    fn create_test_customer() -> Customer {
        Customer {
            id: Uuid::new_v4(),
            organization_id: None,
            customer_type: "INDIVIDUAL".to_string(),
            first_name: Some("John".to_string()),
            last_name: Some("Doe".to_string()),
            date_of_birth: Some(NaiveDate::from_ymd_opt(1990, 1, 1).unwrap()),
            nationality: Some("US".to_string()),
            identification_documents: serde_json::json!([]),
            address: serde_json::json!({}),
            contact_info: serde_json::json!({}),
            risk_score: Decimal::from(50),
            risk_level: "MEDIUM".to_string(),
            pep_status: false,
            sanctions_status: false,
            kyc_status: "APPROVED".to_string(),
            kyc_completed_at: Some(Utc::now()),
            last_reviewed_at: Some(Utc::now()),
            next_review_due: Some(Utc::now() + Duration::days(365)),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: None,
            updated_by: None,
            version: 1,
            metadata: serde_json::json!({}),
        }
    }

    fn create_test_transaction(amount: f64) -> Transaction {
        Transaction {
            id: Uuid::new_v4(),
            customer_id: Uuid::new_v4(),
            transaction_type: "TRANSFER".to_string(),
            amount: Decimal::from_f64_retain(amount).unwrap(),
            currency: "USD".to_string(),
            description: Some("Test transaction".to_string()),
            counterparty_name: Some("Test Counterparty".to_string()),
            counterparty_account: Some("123456789".to_string()),
            counterparty_bank: Some("Test Bank".to_string()),
            counterparty_country: Some("US".to_string()),
            transaction_date: Utc::now(),
            value_date: Some(Utc::now().date_naive()),
            reference_number: Some("REF123".to_string()),
            channel: Some("ONLINE".to_string()),
            risk_score: Decimal::from(0),
            risk_factors: serde_json::json!([]),
            is_suspicious: false,
            alert_generated: false,
            status: "PENDING".to_string(),
            processed_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: None,
            updated_by: None,
            version: 1,
            metadata: serde_json::json!({}),
        }
    }

    #[tokio::test]
    async fn test_high_value_transaction_rule() {
        let rule = HighValueTransactionRule { threshold: 10000.0 };
        let customer = create_test_customer();
        let transaction = create_test_transaction(15000.0);
        
        let context = MonitoringContext {
            transaction,
            customer,
            transaction_history: vec![],
            customer_profile: CustomerProfile::default(),
        };

        let result = rule.evaluate(&context).await.unwrap();
        assert!(result.is_some());
        
        let triggered_rule = result.unwrap();
        assert_eq!(triggered_rule.rule_name, "High Value Transaction");
        assert!(triggered_rule.risk_score > 0.0);
    }

    #[tokio::test]
    async fn test_round_amount_rule() {
        let rule = RoundAmountRule { threshold: 10000.0 };
        let customer = create_test_customer();
        let transaction = create_test_transaction(9999.99); // Just under threshold
        
        let context = MonitoringContext {
            transaction,
            customer,
            transaction_history: vec![],
            customer_profile: CustomerProfile::default(),
        };

        let result = rule.evaluate(&context).await.unwrap();
        assert!(result.is_some());
        
        let triggered_rule = result.unwrap();
        assert_eq!(triggered_rule.rule_name, "Round Amount Pattern");
        assert_eq!(triggered_rule.severity, AlertSeverity::High);
    }

    #[test]
    fn test_calculate_variance() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let variance = calculate_variance(&values);
        assert!(variance > 0.0);
        
        let uniform_values = vec![5.0, 5.0, 5.0, 5.0];
        let uniform_variance = calculate_variance(&uniform_values);
        assert_eq!(uniform_variance, 0.0);
    }
}
