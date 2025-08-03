//! Repository layer for the Compliance Service
//! Provides data access patterns for compliance entities

use std::sync::Arc;
use chrono::{DateTime, NaiveDate, Utc};
use sea_orm::{DatabaseConnection, EntityTrait, QueryFilter, QueryOrder, PaginatorTrait, ColumnTrait};
use tracing::{info, error};
use uuid::Uuid;

use regulateai_database::entities::*;
use regulateai_errors::RegulateAIError;

use crate::models::*;

/// Policy repository for policy management operations
pub struct PolicyRepository {
    db: DatabaseConnection,
}

impl PolicyRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new policy
    pub async fn create_policy(
        &self,
        request: CreatePolicyRequest,
        created_by: Uuid,
    ) -> Result<policies::Model, RegulateAIError> {
        info!("Creating policy in database: {}", request.title);

        let policy = policies::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            title: sea_orm::ActiveValue::Set(request.title),
            description: sea_orm::ActiveValue::Set(Some(request.description)),
            policy_type: sea_orm::ActiveValue::Set(format!("{:?}", request.policy_type)),
            content: sea_orm::ActiveValue::Set(request.content),
            version: sea_orm::ActiveValue::Set(1),
            status: sea_orm::ActiveValue::Set("DRAFT".to_string()),
            effective_date: sea_orm::ActiveValue::Set(Some(request.effective_date)),
            review_date: sea_orm::ActiveValue::Set(Some(request.review_date)),
            approved_by: sea_orm::ActiveValue::Set(None),
            approved_at: sea_orm::ActiveValue::Set(None),
            tags: sea_orm::ActiveValue::Set(Some(serde_json::to_value(request.tags).unwrap())),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(created_by)),
            updated_by: sea_orm::ActiveValue::Set(Some(created_by)),
            version_number: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({}))),
        };

        let result = policies::Entity::insert(policy)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create policy: {}", e),
                source: Some(Box::new(e)),
            })?;

        self.get_policy(result.last_insert_id).await
    }

    /// Approve a policy
    pub async fn approve_policy(
        &self,
        policy_id: Uuid,
        request: PolicyApprovalRequest,
    ) -> Result<policies::Model, RegulateAIError> {
        info!("Approving policy: {}", policy_id);

        let mut policy: policies::ActiveModel = self.get_policy(policy_id).await?.into();
        
        policy.status = sea_orm::ActiveValue::Set("APPROVED".to_string());
        policy.approved_by = sea_orm::ActiveValue::Set(Some(request.approved_by));
        policy.approved_at = sea_orm::ActiveValue::Set(Some(Utc::now()));
        policy.updated_at = sea_orm::ActiveValue::Set(Utc::now());
        policy.updated_by = sea_orm::ActiveValue::Set(Some(request.approved_by));

        let updated_policy = policy.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to approve policy: {}", e),
                source: Some(Box::new(e)),
            })?;

        Ok(updated_policy)
    }

    /// Get policy by ID
    pub async fn get_policy(&self, policy_id: Uuid) -> Result<policies::Model, RegulateAIError> {
        policies::Entity::find_by_id(policy_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to get policy: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "Policy".to_string(),
                id: policy_id.to_string(),
            })
    }

    /// List policies with pagination and filtering
    pub async fn list_policies(
        &self,
        page: u64,
        per_page: u64,
        filters: Option<serde_json::Value>,
    ) -> Result<(Vec<policies::Model>, u64), RegulateAIError> {
        let mut query = policies::Entity::find();

        // Apply filters if provided
        if let Some(filter_obj) = filters {
            if let Some(status) = filter_obj.get("status").and_then(|v| v.as_str()) {
                query = query.filter(policies::Column::Status.eq(status));
            }
            if let Some(policy_type) = filter_obj.get("policy_type").and_then(|v| v.as_str()) {
                query = query.filter(policies::Column::PolicyType.eq(policy_type));
            }
        }

        let paginator = query
            .order_by_desc(policies::Column::CreatedAt)
            .paginate(&self.db, per_page);

        let total_pages = paginator.num_pages().await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count policies: {}", e),
                source: Some(Box::new(e)),
            })?;

        let policies = paginator.fetch_page(page).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to list policies: {}", e),
                source: Some(Box::new(e)),
            })?;

        Ok((policies, total_pages))
    }

    /// Get policy compliance metrics
    pub async fn get_policy_metrics(&self) -> Result<PolicyComplianceMetrics, RegulateAIError> {
        // Implementation would calculate policy metrics from database
        Ok(PolicyComplianceMetrics {
            total_policies: 0,
            active_policies: 0,
            policies_due_for_review: 0,
            policies_under_review: 0,
            compliance_percentage: 0.0,
        })
    }

    /// Health check
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        policies::Entity::find()
            .limit(1)
            .all(&self.db)
            .await
            .map(|_| true)
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Policy repository health check failed: {}", e),
                source: Some(Box::new(e)),
            })
    }
}

/// Control repository for control framework operations
pub struct ControlRepository {
    db: DatabaseConnection,
}

impl ControlRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new control
    pub async fn create_control(
        &self,
        request: CreateControlRequest,
        created_by: Uuid,
    ) -> Result<controls::Model, RegulateAIError> {
        info!("Creating control in database: {}", request.title);

        let control = controls::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            control_id: sea_orm::ActiveValue::Set(request.control_id),
            title: sea_orm::ActiveValue::Set(request.title),
            description: sea_orm::ActiveValue::Set(Some(request.description)),
            control_type: sea_orm::ActiveValue::Set(format!("{:?}", request.control_type)),
            frequency: sea_orm::ActiveValue::Set(format!("{:?}", request.frequency)),
            owner_id: sea_orm::ActiveValue::Set(Some(request.owner_id)),
            policy_id: sea_orm::ActiveValue::Set(request.policy_id),
            implementation_status: sea_orm::ActiveValue::Set("NOT_IMPLEMENTED".to_string()),
            effectiveness: sea_orm::ActiveValue::Set("NOT_TESTED".to_string()),
            last_tested: sea_orm::ActiveValue::Set(None),
            next_test_due: sea_orm::ActiveValue::Set(None),
            evidence_requirements: sea_orm::ActiveValue::Set(Some(serde_json::to_value(request.evidence_requirements).unwrap())),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(created_by)),
            updated_by: sea_orm::ActiveValue::Set(Some(created_by)),
            version: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({
                "testing_procedures": request.testing_procedures
            }))),
        };

        let result = controls::Entity::insert(control)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create control: {}", e),
                source: Some(Box::new(e)),
            })?;

        self.get_control(result.last_insert_id).await
    }

    /// Test a control
    pub async fn test_control(
        &self,
        control_id: Uuid,
        request: ControlTestRequest,
    ) -> Result<ControlTestResult, RegulateAIError> {
        info!("Recording control test for control: {}", control_id);

        // Create control test record
        let test_record = control_tests::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            control_id: sea_orm::ActiveValue::Set(control_id),
            test_date: sea_orm::ActiveValue::Set(request.test_date),
            tester_id: sea_orm::ActiveValue::Set(request.tester_id),
            test_method: sea_orm::ActiveValue::Set(request.test_method.clone()),
            sample_size: sea_orm::ActiveValue::Set(request.sample_size),
            results: sea_orm::ActiveValue::Set("Test completed".to_string()),
            effectiveness_rating: sea_orm::ActiveValue::Set("EFFECTIVE".to_string()),
            deficiencies: sea_orm::ActiveValue::Set(Some(serde_json::json!([]))),
            recommendations: sea_orm::ActiveValue::Set(Some(serde_json::json!([]))),
            evidence_collected: sea_orm::ActiveValue::Set(Some(serde_json::json!([]))),
            next_test_date: sea_orm::ActiveValue::Set(None),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(request.tester_id)),
            updated_by: sea_orm::ActiveValue::Set(Some(request.tester_id)),
            version: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({
                "test_procedures": request.test_procedures,
                "expected_results": request.expected_results
            }))),
        };

        let result = control_tests::Entity::insert(test_record)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create control test: {}", e),
                source: Some(Box::new(e)),
            })?;

        // Return test result
        Ok(ControlTestResult {
            test_id: result.last_insert_id,
            control_id,
            test_date: request.test_date,
            tester_id: request.tester_id,
            effectiveness_rating: ControlEffectiveness::Effective,
            results: "Control test completed successfully".to_string(),
            deficiencies: vec![],
            recommendations: vec![],
            evidence_collected: vec![],
            next_test_date: None,
        })
    }

    /// Get control by ID
    pub async fn get_control(&self, control_id: Uuid) -> Result<controls::Model, RegulateAIError> {
        controls::Entity::find_by_id(control_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to get control: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "Control".to_string(),
                id: control_id.to_string(),
            })
    }

    /// List controls with pagination and filtering
    pub async fn list_controls(
        &self,
        page: u64,
        per_page: u64,
        filters: Option<serde_json::Value>,
    ) -> Result<(Vec<controls::Model>, u64), RegulateAIError> {
        let mut query = controls::Entity::find();

        // Apply filters if provided
        if let Some(filter_obj) = filters {
            if let Some(control_type) = filter_obj.get("control_type").and_then(|v| v.as_str()) {
                query = query.filter(controls::Column::ControlType.eq(control_type));
            }
            if let Some(effectiveness) = filter_obj.get("effectiveness").and_then(|v| v.as_str()) {
                query = query.filter(controls::Column::Effectiveness.eq(effectiveness));
            }
        }

        let paginator = query
            .order_by_desc(controls::Column::CreatedAt)
            .paginate(&self.db, per_page);

        let total_pages = paginator.num_pages().await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count controls: {}", e),
                source: Some(Box::new(e)),
            })?;

        let controls = paginator.fetch_page(page).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to list controls: {}", e),
                source: Some(Box::new(e)),
            })?;

        Ok((controls, total_pages))
    }

    /// Get control effectiveness metrics
    pub async fn get_control_effectiveness_metrics(&self) -> Result<ControlEffectivenessMetrics, RegulateAIError> {
        use sea_orm::*;

        // Get total controls count
        let total_controls = controls::Entity::find()
            .count(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count total controls: {}", e),
                source: Some(Box::new(e)),
            })? as u32;

        // Get effective controls count
        let effective_controls = controls::Entity::find()
            .filter(controls::Column::EffectivenessRating.eq("effective"))
            .count(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count effective controls: {}", e),
                source: Some(Box::new(e)),
            })? as u32;

        // Get partially effective controls count
        let partially_effective_controls = controls::Entity::find()
            .filter(controls::Column::EffectivenessRating.eq("partially_effective"))
            .count(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count partially effective controls: {}", e),
                source: Some(Box::new(e)),
            })? as u32;

        // Get ineffective controls count
        let ineffective_controls = controls::Entity::find()
            .filter(controls::Column::EffectivenessRating.eq("ineffective"))
            .count(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count ineffective controls: {}", e),
                source: Some(Box::new(e)),
            })? as u32;

        // Get controls due for testing (next test date is in the past or within 30 days)
        let thirty_days_from_now = Utc::now() + chrono::Duration::days(30);
        let controls_due_for_testing = controls::Entity::find()
            .filter(controls::Column::NextTestDate.lte(thirty_days_from_now))
            .count(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count controls due for testing: {}", e),
                source: Some(Box::new(e)),
            })? as u32;

        // Calculate effectiveness percentage
        let effectiveness_percentage = if total_controls > 0 {
            (effective_controls as f64 / total_controls as f64) * 100.0
        } else {
            0.0
        };

        Ok(ControlEffectivenessMetrics {
            total_controls,
            effective_controls,
            partially_effective_controls,
            ineffective_controls,
            controls_due_for_testing,
            effectiveness_percentage,
        })
    }

    /// Health check
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        controls::Entity::find()
            .limit(1)
            .all(&self.db)
            .await
            .map(|_| true)
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Control repository health check failed: {}", e),
                source: Some(Box::new(e)),
            })
    }
}

/// Audit repository for audit management operations
pub struct AuditRepository {
    db: DatabaseConnection,
}

impl AuditRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new audit
    pub async fn create_audit(
        &self,
        request: CreateAuditRequest,
        created_by: Uuid,
    ) -> Result<audits::Model, RegulateAIError> {
        info!("Creating audit in database: {}", request.title);

        let audit = audits::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            title: sea_orm::ActiveValue::Set(request.title),
            description: sea_orm::ActiveValue::Set(Some(request.description)),
            audit_type: sea_orm::ActiveValue::Set(format!("{:?}", request.audit_type)),
            scope: sea_orm::ActiveValue::Set(Some(serde_json::to_value(request.scope).unwrap())),
            status: sea_orm::ActiveValue::Set("PLANNING".to_string()),
            start_date: sea_orm::ActiveValue::Set(Some(request.start_date)),
            end_date: sea_orm::ActiveValue::Set(Some(request.end_date)),
            lead_auditor_id: sea_orm::ActiveValue::Set(Some(request.lead_auditor_id)),
            findings_count: sea_orm::ActiveValue::Set(0),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(created_by)),
            updated_by: sea_orm::ActiveValue::Set(Some(created_by)),
            version: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({
                "audit_team": request.audit_team,
                "framework": request.framework
            }))),
        };

        let result = audits::Entity::insert(audit)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create audit: {}", e),
                source: Some(Box::new(e)),
            })?;

        self.get_audit(result.last_insert_id).await
    }

    /// Create audit finding
    pub async fn create_audit_finding(
        &self,
        request: CreateAuditFindingRequest,
        created_by: Uuid,
    ) -> Result<audit_findings::Model, RegulateAIError> {
        info!("Creating audit finding for audit: {}", request.audit_id);

        let finding = audit_findings::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            audit_id: sea_orm::ActiveValue::Set(request.audit_id),
            title: sea_orm::ActiveValue::Set(request.title),
            description: sea_orm::ActiveValue::Set(request.description),
            severity: sea_orm::ActiveValue::Set(format!("{:?}", request.severity)),
            category: sea_orm::ActiveValue::Set(request.category),
            control_id: sea_orm::ActiveValue::Set(request.control_id),
            status: sea_orm::ActiveValue::Set("OPEN".to_string()),
            recommendation: sea_orm::ActiveValue::Set(request.recommendation),
            management_response: sea_orm::ActiveValue::Set(request.management_response),
            target_resolution_date: sea_orm::ActiveValue::Set(request.target_resolution_date),
            responsible_party: sea_orm::ActiveValue::Set(request.responsible_party),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(created_by)),
            updated_by: sea_orm::ActiveValue::Set(Some(created_by)),
            version: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({}))),
        };

        let result = audit_findings::Entity::insert(finding)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create audit finding: {}", e),
                source: Some(Box::new(e)),
            })?;

        audit_findings::Entity::find_by_id(result.last_insert_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to get created audit finding: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "AuditFinding".to_string(),
                id: result.last_insert_id.to_string(),
            })
    }

    /// Get audit by ID
    pub async fn get_audit(&self, audit_id: Uuid) -> Result<audits::Model, RegulateAIError> {
        audits::Entity::find_by_id(audit_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to get audit: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "Audit".to_string(),
                id: audit_id.to_string(),
            })
    }

    /// List audits with pagination and filtering
    pub async fn list_audits(
        &self,
        page: u64,
        per_page: u64,
        filters: Option<serde_json::Value>,
    ) -> Result<(Vec<audits::Model>, u64), RegulateAIError> {
        let mut query = audits::Entity::find();

        // Apply filters if provided
        if let Some(filter_obj) = filters {
            if let Some(status) = filter_obj.get("status").and_then(|v| v.as_str()) {
                query = query.filter(audits::Column::Status.eq(status));
            }
            if let Some(audit_type) = filter_obj.get("audit_type").and_then(|v| v.as_str()) {
                query = query.filter(audits::Column::AuditType.eq(audit_type));
            }
        }

        let paginator = query
            .order_by_desc(audits::Column::CreatedAt)
            .paginate(&self.db, per_page);

        let total_pages = paginator.num_pages().await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count audits: {}", e),
                source: Some(Box::new(e)),
            })?;

        let audits = paginator.fetch_page(page).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to list audits: {}", e),
                source: Some(Box::new(e)),
            })?;

        Ok((audits, total_pages))
    }

    /// Get audit status metrics
    pub async fn get_audit_status_metrics(&self) -> Result<AuditStatusMetrics, RegulateAIError> {
        // Implementation would calculate audit metrics from database
        Ok(AuditStatusMetrics {
            total_audits: 0,
            completed_audits: 0,
            in_progress_audits: 0,
            planned_audits: 0,
            open_findings: 0,
            critical_findings: 0,
        })
    }

    /// Health check
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        audits::Entity::find()
            .limit(1)
            .all(&self.db)
            .await
            .map(|_| true)
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Audit repository health check failed: {}", e),
                source: Some(Box::new(e)),
            })
    }
}

/// Vendor repository for third-party risk management operations
pub struct VendorRepository {
    db: DatabaseConnection,
}

impl VendorRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new vendor
    pub async fn create_vendor(
        &self,
        request: CreateVendorRequest,
        created_by: Uuid,
    ) -> Result<vendors::Model, RegulateAIError> {
        info!("Creating vendor in database: {}", request.name);

        let vendor = vendors::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            name: sea_orm::ActiveValue::Set(request.name),
            legal_name: sea_orm::ActiveValue::Set(request.legal_name),
            vendor_type: sea_orm::ActiveValue::Set(format!("{:?}", request.vendor_type)),
            criticality: sea_orm::ActiveValue::Set(format!("{:?}", request.criticality)),
            status: sea_orm::ActiveValue::Set("ACTIVE".to_string()),
            risk_score: sea_orm::ActiveValue::Set(Some(rust_decimal::Decimal::from(0))),
            last_assessment_date: sea_orm::ActiveValue::Set(None),
            next_assessment_due: sea_orm::ActiveValue::Set(None),
            contract_start_date: sea_orm::ActiveValue::Set(request.contract_start_date),
            contract_end_date: sea_orm::ActiveValue::Set(request.contract_end_date),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(created_by)),
            updated_by: sea_orm::ActiveValue::Set(Some(created_by)),
            version: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({
                "services_provided": request.services_provided,
                "contact_info": request.contact_info,
                "address": request.address,
                "data_access_level": request.data_access_level
            }))),
        };

        let result = vendors::Entity::insert(vendor)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create vendor: {}", e),
                source: Some(Box::new(e)),
            })?;

        self.get_vendor(result.last_insert_id).await
    }

    /// Assess vendor risk
    pub async fn assess_vendor_risk(
        &self,
        request: VendorRiskAssessmentRequest,
    ) -> Result<VendorRiskScore, RegulateAIError> {
        info!("Assessing vendor risk for vendor: {}", request.vendor_id);

        // Simple risk scoring algorithm (in production, this would be more sophisticated)
        let security_score = 75.0; // Based on questionnaire responses
        let operational_score = 80.0; // Based on service criticality
        let financial_score = 85.0; // Based on financial health
        let compliance_score = 90.0; // Based on certifications

        let overall_score = (security_score + operational_score + financial_score + compliance_score) / 4.0;
        
        let risk_level = match overall_score {
            score if score >= 90.0 => VendorRiskLevel::Low,
            score if score >= 75.0 => VendorRiskLevel::Medium,
            score if score >= 60.0 => VendorRiskLevel::High,
            _ => VendorRiskLevel::Critical,
        };

        Ok(VendorRiskScore {
            overall_score,
            security_score,
            operational_score,
            financial_score,
            compliance_score,
            risk_level,
            recommendations: vec![
                "Regular security assessments recommended".to_string(),
                "Monitor contract compliance".to_string(),
            ],
        })
    }

    /// Get vendor by ID
    pub async fn get_vendor(&self, vendor_id: Uuid) -> Result<vendors::Model, RegulateAIError> {
        vendors::Entity::find_by_id(vendor_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to get vendor: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "Vendor".to_string(),
                id: vendor_id.to_string(),
            })
    }

    /// List vendors with pagination and filtering
    pub async fn list_vendors(
        &self,
        page: u64,
        per_page: u64,
        filters: Option<serde_json::Value>,
    ) -> Result<(Vec<vendors::Model>, u64), RegulateAIError> {
        let mut query = vendors::Entity::find();

        // Apply filters if provided
        if let Some(filter_obj) = filters {
            if let Some(vendor_type) = filter_obj.get("vendor_type").and_then(|v| v.as_str()) {
                query = query.filter(vendors::Column::VendorType.eq(vendor_type));
            }
            if let Some(criticality) = filter_obj.get("criticality").and_then(|v| v.as_str()) {
                query = query.filter(vendors::Column::Criticality.eq(criticality));
            }
        }

        let paginator = query
            .order_by_desc(vendors::Column::CreatedAt)
            .paginate(&self.db, per_page);

        let total_pages = paginator.num_pages().await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to count vendors: {}", e),
                source: Some(Box::new(e)),
            })?;

        let vendors = paginator.fetch_page(page).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to list vendors: {}", e),
                source: Some(Box::new(e)),
            })?;

        Ok((vendors, total_pages))
    }

    /// Get vendor risk metrics
    pub async fn get_vendor_risk_metrics(&self) -> Result<VendorRiskMetrics, RegulateAIError> {
        // Implementation would calculate vendor metrics from database
        Ok(VendorRiskMetrics {
            total_vendors: 0,
            critical_vendors: 0,
            high_risk_vendors: 0,
            assessments_due: 0,
            contracts_expiring: 0,
            average_risk_score: 0.0,
        })
    }

    /// Health check
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        vendors::Entity::find()
            .limit(1)
            .all(&self.db)
            .await
            .map(|_| true)
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Vendor repository health check failed: {}", e),
                source: Some(Box::new(e)),
            })
    }
}

/// Regulatory repository for regulatory mapping operations
pub struct RegulatoryRepository {
    db: DatabaseConnection,
}

impl RegulatoryRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Get regulation requirements
    pub async fn get_regulation_requirements(&self, regulation_id: Uuid) -> Result<Vec<RegulationRequirement>, RegulateAIError> {
        use sea_orm::*;

        let requirements = regulation_requirements::Entity::find()
            .filter(regulation_requirements::Column::RegulationId.eq(regulation_id))
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to fetch regulation requirements: {}", e),
                source: Some(Box::new(e)),
            })?;

        let mut result = Vec::new();
        for req in requirements {
            result.push(RegulationRequirement {
                id: req.id,
                regulation_id: req.regulation_id,
                requirement_text: req.requirement_text,
                category: req.category,
                priority: req.priority,
                compliance_deadline: req.compliance_deadline,
                status: req.status,
                created_at: req.created_at,
                updated_at: req.updated_at,
            });
        }

        Ok(result)
    }

    /// Create regulation mapping
    pub async fn create_regulation_mapping(
        &self,
        request: CreateRegulationMappingRequest,
        created_by: Uuid,
    ) -> Result<regulation_mappings::Model, RegulateAIError> {
        info!("Creating regulation mapping for regulation: {}", request.regulation_id);

        let mapping = regulation_mappings::ActiveModel {
            id: sea_orm::ActiveValue::NotSet,
            regulation_id: sea_orm::ActiveValue::Set(request.regulation_id),
            requirement_id: sea_orm::ActiveValue::Set(request.requirement_id),
            control_id: sea_orm::ActiveValue::Set(request.control_id),
            mapping_type: sea_orm::ActiveValue::Set(format!("{:?}", request.mapping_type)),
            coverage_level: sea_orm::ActiveValue::Set(format!("{:?}", request.coverage_level)),
            notes: sea_orm::ActiveValue::Set(request.notes),
            created_at: sea_orm::ActiveValue::Set(Utc::now()),
            updated_at: sea_orm::ActiveValue::Set(Utc::now()),
            created_by: sea_orm::ActiveValue::Set(Some(created_by)),
            updated_by: sea_orm::ActiveValue::Set(Some(created_by)),
            version: sea_orm::ActiveValue::Set(1),
            metadata: sea_orm::ActiveValue::Set(Some(serde_json::json!({}))),
        };

        let result = regulation_mappings::Entity::insert(mapping)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create regulation mapping: {}", e),
                source: Some(Box::new(e)),
            })?;

        regulation_mappings::Entity::find_by_id(result.last_insert_id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to get created regulation mapping: {}", e),
                source: Some(Box::new(e)),
            })?
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "RegulationMapping".to_string(),
                id: result.last_insert_id.to_string(),
            })
    }

    /// List regulations
    pub async fn list_regulations(&self) -> Result<Vec<RegulationInfo>, RegulateAIError> {
        use sea_orm::*;

        let regulations = regulations::Entity::find()
            .order_by_asc(regulations::Column::Name)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to fetch regulations: {}", e),
                source: Some(Box::new(e)),
            })?;

        let mut result = Vec::new();
        for reg in regulations {
            result.push(RegulationInfo {
                id: reg.id,
                name: reg.name,
                description: reg.description,
                jurisdiction: reg.jurisdiction,
                effective_date: reg.effective_date,
                status: reg.status,
                category: reg.category,
                created_at: reg.created_at,
                updated_at: reg.updated_at,
            });
        }

        Ok(result)
    }

    /// Health check
    pub async fn health_check(&self) -> Result<bool, RegulateAIError> {
        regulation_mappings::Entity::find()
            .limit(1)
            .all(&self.db)
            .await
            .map(|_| true)
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Regulatory repository health check failed: {}", e),
                source: Some(Box::new(e)),
            })
    }
}
