//! Data access layer for the Fraud Detection Service

use chrono::{DateTime, Utc};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder,
    QuerySelect, Set, ActiveValue, PaginatorTrait, DbErr,
};
use tracing::{info, error, warn};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use crate::models::*;

// =============================================================================
// FRAUD ALERT REPOSITORY
// =============================================================================

pub struct FraudAlertRepository {
    db: DatabaseConnection,
}

impl FraudAlertRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new fraud alert
    pub async fn create(&self, alert: CreateFraudAlertRequest, created_by: Uuid) -> Result<FraudAlert, RegulateAIError> {
        info!("Creating fraud alert in database: {}", alert.alert_type);

        let active_model = fraud_alerts::ActiveModel {
            id: Set(Uuid::new_v4()),
            alert_type: Set(alert.alert_type),
            customer_id: Set(alert.customer_id),
            transaction_id: Set(alert.transaction_id),
            rule_id: Set(alert.rule_id),
            risk_score: Set(alert.risk_score),
            severity: Set(alert.severity),
            status: Set("OPEN".to_string()),
            description: Set(alert.description),
            triggered_at: Set(Utc::now()),
            assigned_to: Set(None),
            resolved_at: Set(None),
            resolution_notes: Set(None),
            false_positive: Set(false),
            escalated_at: Set(None),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
            metadata: Set(alert.metadata.unwrap_or_default()),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Fraud alert created successfully: {}", model.id);
                Ok(FraudAlert::from(model))
            },
            Err(e) => {
                error!("Failed to create fraud alert: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get fraud alert by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<FraudAlert>, RegulateAIError> {
        info!("Getting fraud alert by ID: {}", id);

        match fraud_alerts::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Fraud alert found: {}", id);
                Ok(Some(FraudAlert::from(model)))
            },
            Ok(None) => {
                warn!("Fraud alert not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get fraud alert: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// List fraud alerts with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<FraudAlert>, RegulateAIError> {
        info!("Listing fraud alerts - page: {}, per_page: {}", page, per_page);

        match fraud_alerts::Entity::find()
            .order_by_desc(fraud_alerts::Column::TriggeredAt)
            .paginate(&self.db, per_page)
            .fetch_page(page)
            .await
        {
            Ok(models) => {
                info!("Found {} fraud alerts", models.len());
                Ok(models.into_iter().map(FraudAlert::from).collect())
            },
            Err(e) => {
                error!("Failed to list fraud alerts: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Update fraud alert status
    pub async fn update_status(&self, id: Uuid, status: String, updated_by: Uuid) -> Result<FraudAlert, RegulateAIError> {
        info!("Updating fraud alert status: {} to {}", id, status);

        match fraud_alerts::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                let mut active_model: fraud_alerts::ActiveModel = model.into();
                
                active_model.status = Set(status.clone());
                active_model.updated_at = Set(Utc::now());
                active_model.updated_by = Set(Some(updated_by));
                active_model.version = Set(active_model.version.unwrap() + 1);

                if status == "RESOLVED" {
                    active_model.resolved_at = Set(Some(Utc::now()));
                }

                match active_model.update(&self.db).await {
                    Ok(updated_model) => {
                        info!("Fraud alert status updated successfully: {}", id);
                        Ok(FraudAlert::from(updated_model))
                    },
                    Err(e) => {
                        error!("Failed to update fraud alert status: {:?}", e);
                        Err(RegulateAIError::DatabaseError(e.to_string()))
                    }
                }
            },
            Ok(None) => {
                warn!("Fraud alert not found for status update: {}", id);
                Err(RegulateAIError::NotFound("Fraud alert not found".to_string()))
            },
            Err(e) => {
                error!("Failed to find fraud alert for status update: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// FRAUD RULES REPOSITORY
// =============================================================================

pub struct FraudRuleRepository {
    db: DatabaseConnection,
}

impl FraudRuleRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new fraud rule
    pub async fn create(&self, rule: CreateFraudRuleRequest, created_by: Uuid) -> Result<FraudRule, RegulateAIError> {
        info!("Creating fraud rule in database: {}", rule.rule_name);

        let active_model = fraud_rules::ActiveModel {
            id: Set(Uuid::new_v4()),
            rule_name: Set(rule.rule_name),
            description: Set(rule.description),
            rule_type: Set(rule.rule_type),
            conditions: Set(rule.conditions),
            actions: Set(rule.actions),
            severity: Set(rule.severity),
            is_active: Set(true),
            priority: Set(rule.priority),
            false_positive_rate: Set(0.0),
            detection_rate: Set(0.0),
            last_triggered: Set(None),
            trigger_count: Set(0),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Fraud rule created successfully: {}", model.id);
                Ok(FraudRule::from(model))
            },
            Err(e) => {
                error!("Failed to create fraud rule: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get fraud rule by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<FraudRule>, RegulateAIError> {
        info!("Getting fraud rule by ID: {}", id);

        match fraud_rules::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Fraud rule found: {}", id);
                Ok(Some(FraudRule::from(model)))
            },
            Ok(None) => {
                warn!("Fraud rule not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get fraud rule: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// List fraud rules with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<FraudRule>, RegulateAIError> {
        info!("Listing fraud rules - page: {}, per_page: {}", page, per_page);

        match fraud_rules::Entity::find()
            .filter(fraud_rules::Column::IsActive.eq(true))
            .order_by_desc(fraud_rules::Column::CreatedAt)
            .paginate(&self.db, per_page)
            .fetch_page(page)
            .await
        {
            Ok(models) => {
                info!("Found {} fraud rules", models.len());
                Ok(models.into_iter().map(FraudRule::from).collect())
            },
            Err(e) => {
                error!("Failed to list fraud rules: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Update fraud rule
    pub async fn update(&self, id: Uuid, rule: UpdateFraudRuleRequest, updated_by: Uuid) -> Result<FraudRule, RegulateAIError> {
        info!("Updating fraud rule: {}", id);

        match fraud_rules::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                let mut active_model: fraud_rules::ActiveModel = model.into();
                
                if let Some(rule_name) = rule.rule_name {
                    active_model.rule_name = Set(rule_name);
                }
                if let Some(description) = rule.description {
                    active_model.description = Set(description);
                }
                if let Some(conditions) = rule.conditions {
                    active_model.conditions = Set(conditions);
                }
                if let Some(actions) = rule.actions {
                    active_model.actions = Set(actions);
                }
                if let Some(severity) = rule.severity {
                    active_model.severity = Set(severity);
                }
                if let Some(is_active) = rule.is_active {
                    active_model.is_active = Set(is_active);
                }
                if let Some(priority) = rule.priority {
                    active_model.priority = Set(priority);
                }
                
                active_model.updated_at = Set(Utc::now());
                active_model.updated_by = Set(Some(updated_by));
                active_model.version = Set(active_model.version.unwrap() + 1);

                match active_model.update(&self.db).await {
                    Ok(updated_model) => {
                        info!("Fraud rule updated successfully: {}", id);
                        Ok(FraudRule::from(updated_model))
                    },
                    Err(e) => {
                        error!("Failed to update fraud rule: {:?}", e);
                        Err(RegulateAIError::DatabaseError(e.to_string()))
                    }
                }
            },
            Ok(None) => {
                warn!("Fraud rule not found for update: {}", id);
                Err(RegulateAIError::NotFound("Fraud rule not found".to_string()))
            },
            Err(e) => {
                error!("Failed to find fraud rule for update: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Delete fraud rule
    pub async fn delete(&self, id: Uuid) -> Result<(), RegulateAIError> {
        info!("Deleting fraud rule: {}", id);

        match fraud_rules::Entity::delete_by_id(id).exec(&self.db).await {
            Ok(result) => {
                if result.rows_affected > 0 {
                    info!("Fraud rule deleted successfully: {}", id);
                    Ok(())
                } else {
                    warn!("Fraud rule not found for deletion: {}", id);
                    Err(RegulateAIError::NotFound("Fraud rule not found".to_string()))
                }
            },
            Err(e) => {
                error!("Failed to delete fraud rule: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get active fraud rules for evaluation
    pub async fn get_active_rules(&self) -> Result<Vec<FraudRule>, RegulateAIError> {
        info!("Getting active fraud rules for evaluation");

        match fraud_rules::Entity::find()
            .filter(fraud_rules::Column::IsActive.eq(true))
            .order_by_asc(fraud_rules::Column::Priority)
            .all(&self.db)
            .await
        {
            Ok(models) => {
                info!("Found {} active fraud rules", models.len());
                Ok(models.into_iter().map(FraudRule::from).collect())
            },
            Err(e) => {
                error!("Failed to get active fraud rules: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// ML MODELS REPOSITORY
// =============================================================================

pub struct MlModelRepository {
    db: DatabaseConnection,
}

impl MlModelRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Get ML model by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<MlModel>, RegulateAIError> {
        info!("Getting ML model by ID: {}", id);

        match ml_models::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("ML model found: {}", id);
                Ok(Some(MlModel::from(model)))
            },
            Ok(None) => {
                warn!("ML model not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get ML model: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Update model performance metrics
    pub async fn update_metrics(&self, id: Uuid, metrics: ModelMetrics) -> Result<(), RegulateAIError> {
        info!("Updating ML model metrics: {}", id);

        match ml_models::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                let mut active_model: ml_models::ActiveModel = model.into();
                
                active_model.accuracy = Set(Some(metrics.accuracy));
                active_model.precision_score = Set(Some(metrics.precision));
                active_model.recall = Set(Some(metrics.recall));
                active_model.f1_score = Set(Some(metrics.f1_score));
                active_model.auc_score = Set(Some(metrics.auc_score));
                active_model.updated_at = Set(Utc::now());

                match active_model.update(&self.db).await {
                    Ok(_) => {
                        info!("ML model metrics updated successfully: {}", id);
                        Ok(())
                    },
                    Err(e) => {
                        error!("Failed to update ML model metrics: {:?}", e);
                        Err(RegulateAIError::DatabaseError(e.to_string()))
                    }
                }
            },
            Ok(None) => {
                warn!("ML model not found for metrics update: {}", id);
                Err(RegulateAIError::NotFound("ML model not found".to_string()))
            },
            Err(e) => {
                error!("Failed to find ML model for metrics update: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}
