//! Data access layer for the Risk Management Service

use chrono::{DateTime, NaiveDate, Utc};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder,
    QuerySelect, Set, ActiveValue, PaginatorTrait, DbErr,
};
use tracing::{info, error, warn};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use crate::models::*;

// =============================================================================
// RISK ASSESSMENT REPOSITORY
// =============================================================================

pub struct RiskAssessmentRepository {
    db: DatabaseConnection,
}

impl RiskAssessmentRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new risk assessment
    pub async fn create(&self, assessment: CreateRiskAssessmentRequest, created_by: Uuid) -> Result<RiskAssessment, RegulateAIError> {
        info!("Creating risk assessment in database: {}", assessment.title);

        let active_model = risk_assessments::ActiveModel {
            id: Set(Uuid::new_v4()),
            title: Set(assessment.title),
            description: Set(assessment.description),
            risk_category_id: Set(assessment.risk_category_id),
            organization_id: Set(assessment.organization_id),
            assessment_type: Set(assessment.assessment_type),
            methodology: Set(assessment.methodology),
            scope: Set(assessment.scope),
            inherent_risk_score: Set(assessment.inherent_risk_score),
            residual_risk_score: Set(assessment.residual_risk_score),
            risk_appetite_threshold: Set(assessment.risk_appetite_threshold),
            assessment_date: Set(assessment.assessment_date),
            next_review_date: Set(assessment.next_review_date),
            status: Set("DRAFT".to_string()),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
            metadata: Set(assessment.metadata.unwrap_or_default()),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Risk assessment created successfully: {}", model.id);
                Ok(RiskAssessment::from(model))
            },
            Err(e) => {
                error!("Failed to create risk assessment: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get risk assessment by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<RiskAssessment>, RegulateAIError> {
        info!("Getting risk assessment by ID: {}", id);

        match risk_assessments::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Risk assessment found: {}", id);
                Ok(Some(RiskAssessment::from(model)))
            },
            Ok(None) => {
                warn!("Risk assessment not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get risk assessment: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// List risk assessments with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<RiskAssessment>, RegulateAIError> {
        info!("Listing risk assessments - page: {}, per_page: {}", page, per_page);

        match risk_assessments::Entity::find()
            .order_by_desc(risk_assessments::Column::CreatedAt)
            .paginate(&self.db, per_page)
            .fetch_page(page)
            .await
        {
            Ok(models) => {
                info!("Found {} risk assessments", models.len());
                Ok(models.into_iter().map(RiskAssessment::from).collect())
            },
            Err(e) => {
                error!("Failed to list risk assessments: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Update risk assessment
    pub async fn update(&self, id: Uuid, assessment: UpdateRiskAssessmentRequest, updated_by: Uuid) -> Result<RiskAssessment, RegulateAIError> {
        info!("Updating risk assessment: {}", id);

        match risk_assessments::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                let mut active_model: risk_assessments::ActiveModel = model.into();
                
                if let Some(title) = assessment.title {
                    active_model.title = Set(title);
                }
                if let Some(description) = assessment.description {
                    active_model.description = Set(description);
                }
                if let Some(inherent_risk_score) = assessment.inherent_risk_score {
                    active_model.inherent_risk_score = Set(inherent_risk_score);
                }
                if let Some(residual_risk_score) = assessment.residual_risk_score {
                    active_model.residual_risk_score = Set(residual_risk_score);
                }
                if let Some(status) = assessment.status {
                    active_model.status = Set(status);
                }
                
                active_model.updated_at = Set(Utc::now());
                active_model.updated_by = Set(Some(updated_by));
                active_model.version = Set(active_model.version.unwrap() + 1);

                match active_model.update(&self.db).await {
                    Ok(updated_model) => {
                        info!("Risk assessment updated successfully: {}", id);
                        Ok(RiskAssessment::from(updated_model))
                    },
                    Err(e) => {
                        error!("Failed to update risk assessment: {:?}", e);
                        Err(RegulateAIError::DatabaseError(e.to_string()))
                    }
                }
            },
            Ok(None) => {
                warn!("Risk assessment not found for update: {}", id);
                Err(RegulateAIError::NotFound("Risk assessment not found".to_string()))
            },
            Err(e) => {
                error!("Failed to find risk assessment for update: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Delete risk assessment
    pub async fn delete(&self, id: Uuid) -> Result<(), RegulateAIError> {
        info!("Deleting risk assessment: {}", id);

        match risk_assessments::Entity::delete_by_id(id).exec(&self.db).await {
            Ok(result) => {
                if result.rows_affected > 0 {
                    info!("Risk assessment deleted successfully: {}", id);
                    Ok(())
                } else {
                    warn!("Risk assessment not found for deletion: {}", id);
                    Err(RegulateAIError::NotFound("Risk assessment not found".to_string()))
                }
            },
            Err(e) => {
                error!("Failed to delete risk assessment: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// KEY RISK INDICATORS REPOSITORY
// =============================================================================

pub struct KriRepository {
    db: DatabaseConnection,
}

impl KriRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new KRI
    pub async fn create(&self, kri: CreateKriRequest, created_by: Uuid) -> Result<KeyRiskIndicator, RegulateAIError> {
        info!("Creating KRI in database: {}", kri.name);

        let active_model = key_risk_indicators::ActiveModel {
            id: Set(Uuid::new_v4()),
            name: Set(kri.name),
            description: Set(kri.description),
            risk_category_id: Set(kri.risk_category_id),
            metric_type: Set(kri.metric_type),
            calculation_method: Set(kri.calculation_method),
            data_source: Set(kri.data_source),
            frequency: Set(kri.frequency),
            threshold_green: Set(kri.threshold_green),
            threshold_amber: Set(kri.threshold_amber),
            threshold_red: Set(kri.threshold_red),
            unit_of_measure: Set(kri.unit_of_measure),
            is_active: Set(true),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("KRI created successfully: {}", model.id);
                Ok(KeyRiskIndicator::from(model))
            },
            Err(e) => {
                error!("Failed to create KRI: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get KRI by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<KeyRiskIndicator>, RegulateAIError> {
        info!("Getting KRI by ID: {}", id);

        match key_risk_indicators::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("KRI found: {}", id);
                Ok(Some(KeyRiskIndicator::from(model)))
            },
            Ok(None) => {
                warn!("KRI not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get KRI: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// List KRIs with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<KeyRiskIndicator>, RegulateAIError> {
        info!("Listing KRIs - page: {}, per_page: {}", page, per_page);

        match key_risk_indicators::Entity::find()
            .filter(key_risk_indicators::Column::IsActive.eq(true))
            .order_by_desc(key_risk_indicators::Column::CreatedAt)
            .paginate(&self.db, per_page)
            .fetch_page(page)
            .await
        {
            Ok(models) => {
                info!("Found {} KRIs", models.len());
                Ok(models.into_iter().map(KeyRiskIndicator::from).collect())
            },
            Err(e) => {
                error!("Failed to list KRIs: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// KRI MEASUREMENTS REPOSITORY
// =============================================================================

pub struct KriMeasurementRepository {
    db: DatabaseConnection,
}

impl KriMeasurementRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Record a new KRI measurement
    pub async fn create(&self, kri_id: Uuid, measurement: RecordKriMeasurementRequest) -> Result<KriMeasurement, RegulateAIError> {
        info!("Recording KRI measurement for KRI: {}", kri_id);

        let status = if measurement.value <= measurement.threshold_green {
            "GREEN"
        } else if measurement.value <= measurement.threshold_amber {
            "AMBER"
        } else {
            "RED"
        };

        let active_model = kri_measurements::ActiveModel {
            id: Set(Uuid::new_v4()),
            kri_id: Set(kri_id),
            measurement_date: Set(measurement.measurement_date),
            value: Set(measurement.value),
            status: Set(status.to_string()),
            created_at: Set(Utc::now()),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("KRI measurement recorded successfully: {}", model.id);
                Ok(KriMeasurement::from(model))
            },
            Err(e) => {
                error!("Failed to record KRI measurement: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}
