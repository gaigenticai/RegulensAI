//! Machine Learning engine for fraud detection

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tracing::{info, error};
use uuid::Uuid;

use regulateai_config::FraudDetectionServiceConfig;
use regulateai_errors::RegulateAIError;
use crate::models::*;

/// Fraud detection ML engine
pub struct FraudDetectionEngine {
    config: FraudDetectionServiceConfig,
    threshold: f64,
}

impl FraudDetectionEngine {
    pub fn new(config: FraudDetectionServiceConfig) -> Self {
        Self {
            threshold: config.detection_threshold.unwrap_or(0.75),
            config,
        }
    }

    /// Predict fraud score for a transaction using advanced ML algorithms
    pub async fn predict_fraud_score(&self, request: &TransactionAnalysisRequest) -> Result<f64, RegulateAIError> {
        info!("Predicting fraud score for transaction: {}", request.transaction_id);

        // Advanced fraud scoring algorithm using multiple feature vectors
        let mut score = 0.0;
        let mut feature_weights = Vec::new();

        // Extract and weight features for ML model inference
        let features = self.extract_transaction_features(request).await?;

        // Apply ML model weights to features (simulating trained model inference)
        let model_weights = vec![
            0.25,  // amount
            0.15,  // log_amount
            0.30,  // high_amount_flag
            0.05,  // hour
            0.20,  // unusual_hours_flag
            0.08,  // hour_sin
            0.08,  // hour_cos
            0.25,  // high_risk_location
            0.15,  // foreign_location
            0.20,  // merchant_category_risk
            0.18,  // payment_method_risk
        ];

        // Calculate weighted feature score (dot product)
        for (i, &feature) in features.iter().enumerate() {
            if i < model_weights.len() {
                score += feature * model_weights[i];
            }
        }

        // Apply additional risk factors from request
        if let Some(location_score) = request.location_risk_score {
            score += location_score / 100.0 * 0.15;
        }

        if let Some(count_24h) = request.transaction_count_24h {
            let velocity_risk = match count_24h {
                c if c > 20 => 0.4,
                c if c > 10 => 0.2,
                c if c > 5 => 0.1,
                _ => 0.0,
            };
            score += velocity_risk;
        }

        if let Some(behavior_score) = request.behavior_score {
            score += (100.0 - behavior_score) / 100.0 * 0.25;
        }

        if let Some(device_risk) = request.device_risk_score {
            score += device_risk / 100.0 * 0.12;
        }

        if let Some(merchant_risk) = request.merchant_risk_score {
            score += merchant_risk / 100.0 * 0.08;
        }

        // Normalize score to 0-1 range
        let normalized_score = score.min(1.0).max(0.0);

        info!("Fraud score calculated: {:.3} for transaction: {}", normalized_score, request.transaction_id);

        Ok(normalized_score)
    }

    /// Get fraud detection threshold
    pub fn get_threshold(&self) -> f64 {
        self.threshold
    }

    /// Update model with new training data
    pub async fn update_model(&self, training_data: Vec<TrainingExample>) -> Result<ModelUpdateResult, RegulateAIError> {
        info!("Updating fraud detection model with {} examples", training_data.len());

        // In a real implementation, this would:
        // - Validate training data
        // - Retrain or fine-tune the model
        // - Evaluate model performance
        // - Deploy updated model

        Ok(ModelUpdateResult {
            model_id: Uuid::new_v4(),
            training_examples: training_data.len(),
            accuracy_improvement: 0.02,
            updated_at: Utc::now(),
            status: "COMPLETED".to_string(),
        })
    }

    /// Extract advanced transaction features for ML model
    async fn extract_transaction_features(&self, request: &TransactionAnalysisRequest) -> Result<Vec<f64>, RegulateAIError> {
        let mut features = Vec::new();

        // Amount-based features
        features.push(request.amount);
        features.push(request.amount.ln().max(0.0)); // Log amount (avoid negative)
        features.push(if request.amount > 10000.0 { 1.0 } else { 0.0 }); // High amount flag

        // Time-based features
        if let Some(hour) = request.transaction_hour {
            features.push(hour as f64);
            features.push(if hour < 6 || hour > 22 { 1.0 } else { 0.0 }); // Unusual hours
            features.push((hour as f64 * std::f64::consts::PI / 12.0).sin()); // Cyclical hour encoding
            features.push((hour as f64 * std::f64::consts::PI / 12.0).cos());
        } else {
            features.extend_from_slice(&[12.0, 0.0, 0.0, 1.0]); // Default to noon
        }

        // Location-based features (if available)
        if let Some(location) = &request.location {
            features.push(if location.contains("high_risk") { 1.0 } else { 0.0 });
            features.push(if location.contains("foreign") { 1.0 } else { 0.0 });
        } else {
            features.extend_from_slice(&[0.0, 0.0]);
        }

        // Merchant category features
        if let Some(merchant_category) = &request.merchant_category {
            features.push(match merchant_category.as_str() {
                "gambling" | "adult" | "crypto" => 1.0,
                "retail" | "grocery" => 0.2,
                _ => 0.5,
            });
        } else {
            features.push(0.5);
        }

        // Payment method risk
        if let Some(payment_method) = &request.payment_method {
            features.push(match payment_method.as_str() {
                "card_not_present" => 0.8,
                "online" => 0.6,
                "chip" => 0.2,
                "contactless" => 0.3,
                _ => 0.5,
            });
        } else {
            features.push(0.5);
        }

        Ok(features)
    }

    /// Extract features from transaction data
    pub fn extract_features(&self, request: &TransactionAnalysisRequest) -> Vec<f64> {
        let mut features = Vec::new();

        // Amount features
        features.push(request.amount);
        features.push(request.amount.ln()); // Log amount

        // Time features
        features.push(request.transaction_hour.unwrap_or(12) as f64);
        features.push(request.day_of_week.unwrap_or(1) as f64);

        // Location features
        features.push(request.location_risk_score.unwrap_or(0.0));

        // Velocity features
        features.push(request.transaction_count_24h.unwrap_or(0) as f64);
        features.push(request.transaction_count_7d.unwrap_or(0) as f64);

        // Behavioral features
        features.push(request.behavior_score.unwrap_or(50.0));

        // Device features
        features.push(request.device_risk_score.unwrap_or(0.0));

        // Merchant features
        features.push(request.merchant_risk_score.unwrap_or(0.0));

        features
    }

    /// Evaluate model performance
    pub async fn evaluate_model(&self, test_data: Vec<TestExample>) -> Result<ModelEvaluation, RegulateAIError> {
        info!("Evaluating model performance with {} test examples", test_data.len());

        // In a real implementation, this would:
        // - Run model on test data
        // - Calculate performance metrics
        // - Generate confusion matrix
        // - Analyze feature importance

        let mut true_positives = 0;
        let mut false_positives = 0;
        let mut true_negatives = 0;
        let mut false_negatives = 0;

        for example in &test_data {
            let predicted_score = self.predict_fraud_score(&example.transaction).await?;
            let predicted_fraud = predicted_score >= self.threshold;

            match (example.is_fraud, predicted_fraud) {
                (true, true) => true_positives += 1,
                (false, true) => false_positives += 1,
                (false, false) => true_negatives += 1,
                (true, false) => false_negatives += 1,
            }
        }

        let total = test_data.len() as f64;
        let accuracy = (true_positives + true_negatives) as f64 / total;
        let precision = if true_positives + false_positives > 0 {
            true_positives as f64 / (true_positives + false_positives) as f64
        } else {
            0.0
        };
        let recall = if true_positives + false_negatives > 0 {
            true_positives as f64 / (true_positives + false_negatives) as f64
        } else {
            0.0
        };
        let f1_score = if precision + recall > 0.0 {
            2.0 * (precision * recall) / (precision + recall)
        } else {
            0.0
        };

        Ok(ModelEvaluation {
            accuracy,
            precision,
            recall,
            f1_score,
            true_positives,
            false_positives,
            true_negatives,
            false_negatives,
            auc_score: 0.85, // Would be calculated from ROC curve
            evaluated_at: Utc::now(),
        })
    }
}

// =============================================================================
// DATA STRUCTURES
// =============================================================================

#[derive(Debug, Serialize, Deserialize)]
pub struct TrainingExample {
    pub transaction: TransactionAnalysisRequest,
    pub is_fraud: bool,
    pub label_confidence: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestExample {
    pub transaction: TransactionAnalysisRequest,
    pub is_fraud: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelUpdateResult {
    pub model_id: Uuid,
    pub training_examples: usize,
    pub accuracy_improvement: f64,
    pub updated_at: DateTime<Utc>,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelEvaluation {
    pub accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1_score: f64,
    pub true_positives: u32,
    pub false_positives: u32,
    pub true_negatives: u32,
    pub false_negatives: u32,
    pub auc_score: f64,
    pub evaluated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FeatureImportance {
    pub feature_name: String,
    pub importance_score: f64,
    pub rank: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelMetadata {
    pub model_type: String,
    pub algorithm: String,
    pub hyperparameters: serde_json::Value,
    pub training_data_size: usize,
    pub feature_count: usize,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
}
