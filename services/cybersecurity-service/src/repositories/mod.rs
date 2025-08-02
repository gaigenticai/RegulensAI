//! Data access layer for the Cybersecurity Service

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
// VULNERABILITY ASSESSMENT REPOSITORY
// =============================================================================

pub struct VulnerabilityAssessmentRepository {
    db: DatabaseConnection,
}

impl VulnerabilityAssessmentRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new vulnerability assessment
    pub async fn create(&self, assessment: CreateVulnerabilityAssessmentRequest, created_by: Uuid) -> Result<VulnerabilityAssessment, RegulateAIError> {
        info!("Creating vulnerability assessment in database: {}", assessment.title);

        let active_model = vulnerability_assessments::ActiveModel {
            id: Set(Uuid::new_v4()),
            title: Set(assessment.title),
            description: Set(assessment.description),
            assessment_type: Set(assessment.assessment_type),
            scope: Set(assessment.scope),
            methodology: Set(assessment.methodology),
            status: Set("PLANNED".to_string()),
            severity: Set(assessment.severity),
            cvss_score: Set(assessment.cvss_score),
            affected_systems: Set(assessment.affected_systems),
            remediation_plan: Set(assessment.remediation_plan),
            scheduled_date: Set(assessment.scheduled_date),
            completed_date: Set(None),
            next_assessment_date: Set(assessment.next_assessment_date),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
            metadata: Set(assessment.metadata.unwrap_or_default()),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Vulnerability assessment created successfully: {}", model.id);
                Ok(VulnerabilityAssessment::from(model))
            },
            Err(e) => {
                error!("Failed to create vulnerability assessment: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get vulnerability assessment by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<VulnerabilityAssessment>, RegulateAIError> {
        info!("Getting vulnerability assessment by ID: {}", id);

        match vulnerability_assessments::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Vulnerability assessment found: {}", id);
                Ok(Some(VulnerabilityAssessment::from(model)))
            },
            Ok(None) => {
                warn!("Vulnerability assessment not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get vulnerability assessment: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// List vulnerability assessments with pagination
    pub async fn list(&self, page: u64, per_page: u64) -> Result<Vec<VulnerabilityAssessment>, RegulateAIError> {
        info!("Listing vulnerability assessments - page: {}, per_page: {}", page, per_page);

        match vulnerability_assessments::Entity::find()
            .order_by_desc(vulnerability_assessments::Column::CreatedAt)
            .paginate(&self.db, per_page)
            .fetch_page(page)
            .await
        {
            Ok(models) => {
                info!("Found {} vulnerability assessments", models.len());
                Ok(models.into_iter().map(VulnerabilityAssessment::from).collect())
            },
            Err(e) => {
                error!("Failed to list vulnerability assessments: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// SECURITY INCIDENT REPOSITORY
// =============================================================================

pub struct SecurityIncidentRepository {
    db: DatabaseConnection,
}

impl SecurityIncidentRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new security incident
    pub async fn create(&self, incident: CreateSecurityIncidentRequest, created_by: Uuid) -> Result<SecurityIncident, RegulateAIError> {
        info!("Creating security incident in database: {}", incident.title);

        let active_model = security_incidents::ActiveModel {
            id: Set(Uuid::new_v4()),
            title: Set(incident.title),
            description: Set(incident.description),
            incident_type: Set(incident.incident_type),
            severity: Set(incident.severity),
            status: Set("OPEN".to_string()),
            source: Set(incident.source),
            affected_systems: Set(incident.affected_systems),
            impact_assessment: Set(incident.impact_assessment),
            containment_actions: Set(incident.containment_actions),
            eradication_actions: Set(incident.eradication_actions),
            recovery_actions: Set(incident.recovery_actions),
            lessons_learned: Set(incident.lessons_learned),
            detected_at: Set(incident.detected_at),
            reported_at: Set(Utc::now()),
            resolved_at: Set(None),
            assigned_to: Set(None),
            escalated_at: Set(None),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
            metadata: Set(incident.metadata.unwrap_or_default()),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Security incident created successfully: {}", model.id);
                Ok(SecurityIncident::from(model))
            },
            Err(e) => {
                error!("Failed to create security incident: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get security incident by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<SecurityIncident>, RegulateAIError> {
        info!("Getting security incident by ID: {}", id);

        match security_incidents::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Security incident found: {}", id);
                Ok(Some(SecurityIncident::from(model)))
            },
            Ok(None) => {
                warn!("Security incident not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get security incident: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Update security incident status
    pub async fn update_status(&self, id: Uuid, status: String, updated_by: Uuid) -> Result<SecurityIncident, RegulateAIError> {
        info!("Updating security incident status: {} to {}", id, status);

        match security_incidents::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                let mut active_model: security_incidents::ActiveModel = model.into();
                
                active_model.status = Set(status.clone());
                active_model.updated_at = Set(Utc::now());
                active_model.updated_by = Set(Some(updated_by));
                active_model.version = Set(active_model.version.unwrap() + 1);

                if status == "RESOLVED" {
                    active_model.resolved_at = Set(Some(Utc::now()));
                }

                match active_model.update(&self.db).await {
                    Ok(updated_model) => {
                        info!("Security incident status updated successfully: {}", id);
                        Ok(SecurityIncident::from(updated_model))
                    },
                    Err(e) => {
                        error!("Failed to update security incident status: {:?}", e);
                        Err(RegulateAIError::DatabaseError(e.to_string()))
                    }
                }
            },
            Ok(None) => {
                warn!("Security incident not found for status update: {}", id);
                Err(RegulateAIError::NotFound("Security incident not found".to_string()))
            },
            Err(e) => {
                error!("Failed to find security incident for status update: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// DATA PROCESSING RECORD REPOSITORY
// =============================================================================

pub struct DataProcessingRecordRepository {
    db: DatabaseConnection,
}

impl DataProcessingRecordRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new data processing record
    pub async fn create(&self, record: CreateDataProcessingRecordRequest, created_by: Uuid) -> Result<DataProcessingRecord, RegulateAIError> {
        info!("Creating data processing record in database: {}", record.processing_purpose);

        let active_model = data_processing_records::ActiveModel {
            id: Set(Uuid::new_v4()),
            processing_purpose: Set(record.processing_purpose),
            legal_basis: Set(record.legal_basis),
            data_categories: Set(record.data_categories),
            data_subjects: Set(record.data_subjects),
            recipients: Set(record.recipients),
            retention_period: Set(record.retention_period),
            security_measures: Set(record.security_measures),
            international_transfers: Set(record.international_transfers),
            dpia_required: Set(record.dpia_required),
            dpia_completed: Set(false),
            consent_mechanism: Set(record.consent_mechanism),
            withdrawal_mechanism: Set(record.withdrawal_mechanism),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Data processing record created successfully: {}", model.id);
                Ok(DataProcessingRecord::from(model))
            },
            Err(e) => {
                error!("Failed to create data processing record: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get data processing record by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<DataProcessingRecord>, RegulateAIError> {
        info!("Getting data processing record by ID: {}", id);

        match data_processing_records::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Data processing record found: {}", id);
                Ok(Some(DataProcessingRecord::from(model)))
            },
            Ok(None) => {
                warn!("Data processing record not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get data processing record: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}

// =============================================================================
// ACCESS POLICY REPOSITORY
// =============================================================================

pub struct AccessPolicyRepository {
    db: DatabaseConnection,
}

impl AccessPolicyRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new access policy
    pub async fn create(&self, policy: CreateAccessPolicyRequest, created_by: Uuid) -> Result<AccessPolicy, RegulateAIError> {
        info!("Creating access policy in database: {}", policy.policy_name);

        let active_model = access_policies::ActiveModel {
            id: Set(Uuid::new_v4()),
            policy_name: Set(policy.policy_name),
            description: Set(policy.description),
            policy_type: Set(policy.policy_type),
            rules: Set(policy.rules),
            conditions: Set(policy.conditions),
            actions: Set(policy.actions),
            priority: Set(policy.priority),
            is_active: Set(true),
            effective_date: Set(policy.effective_date),
            expiry_date: Set(policy.expiry_date),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(Some(created_by)),
            updated_by: Set(Some(created_by)),
            version: Set(1),
        };

        match active_model.insert(&self.db).await {
            Ok(model) => {
                info!("Access policy created successfully: {}", model.id);
                Ok(AccessPolicy::from(model))
            },
            Err(e) => {
                error!("Failed to create access policy: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get access policy by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<AccessPolicy>, RegulateAIError> {
        info!("Getting access policy by ID: {}", id);

        match access_policies::Entity::find_by_id(id).one(&self.db).await {
            Ok(Some(model)) => {
                info!("Access policy found: {}", id);
                Ok(Some(AccessPolicy::from(model)))
            },
            Ok(None) => {
                warn!("Access policy not found: {}", id);
                Ok(None)
            },
            Err(e) => {
                error!("Failed to get access policy: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }

    /// Get active access policies
    pub async fn get_active_policies(&self) -> Result<Vec<AccessPolicy>, RegulateAIError> {
        info!("Getting active access policies");

        match access_policies::Entity::find()
            .filter(access_policies::Column::IsActive.eq(true))
            .order_by_asc(access_policies::Column::Priority)
            .all(&self.db)
            .await
        {
            Ok(models) => {
                info!("Found {} active access policies", models.len());
                Ok(models.into_iter().map(AccessPolicy::from).collect())
            },
            Err(e) => {
                error!("Failed to get active access policies: {:?}", e);
                Err(RegulateAIError::DatabaseError(e.to_string()))
            }
        }
    }
}
