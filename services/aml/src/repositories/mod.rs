//! Data access repositories for AML service

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, 
    PaginatorTrait, QueryFilter, QueryOrder, Set, DbErr
};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use regulateai_database::entities::{
    Customer, Transaction, AmlAlert, SanctionsList,
    customer, transaction, aml_alert, sanctions_list
};

use crate::models::*;

/// Customer repository
pub struct CustomerRepository {
    db: DatabaseConnection,
}

impl CustomerRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new customer
    pub async fn create_customer(&self, request: CreateCustomerRequest) -> Result<Customer, RegulateAIError> {
        let customer_model = customer::ActiveModel {
            id: Set(Uuid::new_v4()),
            organization_id: Set(request.organization_id),
            customer_type: Set(match request.customer_type {
                CustomerType::Individual => "INDIVIDUAL".to_string(),
                CustomerType::Business => "BUSINESS".to_string(),
            }),
            first_name: Set(Some(request.first_name)),
            last_name: Set(Some(request.last_name)),
            date_of_birth: Set(request.date_of_birth),
            nationality: Set(request.nationality),
            identification_documents: Set(serde_json::to_value(request.identification_documents)?),
            address: Set(serde_json::to_value(request.address)?),
            contact_info: Set(serde_json::to_value(request.contact_info)?),
            risk_score: Set(rust_decimal::Decimal::from(0)),
            risk_level: Set("MEDIUM".to_string()),
            pep_status: Set(false),
            sanctions_status: Set(false),
            kyc_status: Set("PENDING".to_string()),
            kyc_completed_at: Set(None),
            last_reviewed_at: Set(Some(Utc::now())),
            next_review_due: Set(Some(Utc::now() + chrono::Duration::days(365))),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(None),
            updated_by: Set(None),
            version: Set(1),
            metadata: Set(serde_json::json!({})),
        };

        let customer = customer_model.insert(&self.db).await?;
        Ok(customer)
    }

    /// Get customer by ID
    pub async fn get_customer(&self, customer_id: Uuid) -> Result<Customer, RegulateAIError> {
        customer::Entity::find_by_id(customer_id)
            .one(&self.db)
            .await?
            .ok_or_else(|| RegulateAIError::NotFound {
                resource_type: "Customer".to_string(),
                resource_id: customer_id.to_string(),
                code: "CUSTOMER_NOT_FOUND".to_string(),
            })
    }

    /// Update customer risk assessment
    pub async fn update_customer_risk(
        &self,
        customer_id: Uuid,
        risk_score: f64,
        risk_level: RiskLevel,
    ) -> Result<Customer, RegulateAIError> {
        let customer = self.get_customer(customer_id).await?;
        
        let mut customer_model: customer::ActiveModel = customer.into();
        customer_model.risk_score = Set(rust_decimal::Decimal::from_f64_retain(risk_score).unwrap_or_default());
        customer_model.risk_level = Set(match risk_level {
            RiskLevel::Low => "LOW".to_string(),
            RiskLevel::Medium => "MEDIUM".to_string(),
            RiskLevel::High => "HIGH".to_string(),
            RiskLevel::Critical => "CRITICAL".to_string(),
        });
        customer_model.updated_at = Set(Utc::now());

        let updated_customer = customer_model.update(&self.db).await?;
        Ok(updated_customer)
    }

    /// List customers with pagination
    pub async fn list_customers(
        &self,
        page: u64,
        per_page: u64,
        organization_id: Option<Uuid>,
    ) -> Result<(Vec<Customer>, u64), RegulateAIError> {
        let mut query = customer::Entity::find();

        if let Some(org_id) = organization_id {
            query = query.filter(customer::Column::OrganizationId.eq(org_id));
        }

        let paginator = query
            .order_by_desc(customer::Column::CreatedAt)
            .paginate(&self.db, per_page);

        let total_pages = paginator.num_pages().await?;
        let customers = paginator.fetch_page(page).await?;

        Ok((customers, total_pages))
    }

    /// Get high-risk customers
    pub async fn get_high_risk_customers(&self, limit: u64) -> Result<Vec<Customer>, RegulateAIError> {
        let customers = customer::Entity::find()
            .filter(customer::Column::RiskLevel.is_in(["HIGH", "CRITICAL"]))
            .order_by_desc(customer::Column::RiskScore)
            .limit(limit)
            .all(&self.db)
            .await?;

        Ok(customers)
    }
}

/// Transaction repository
pub struct TransactionRepository {
    db: DatabaseConnection,
}

impl TransactionRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new transaction
    pub async fn create_transaction(&self, request: CreateTransactionRequest) -> Result<Transaction, RegulateAIError> {
        let transaction_model = transaction::ActiveModel {
            id: Set(Uuid::new_v4()),
            customer_id: Set(request.customer_id),
            transaction_type: Set(request.transaction_type),
            amount: Set(rust_decimal::Decimal::from_f64_retain(request.amount).unwrap_or_default()),
            currency: Set(request.currency),
            description: Set(request.description),
            counterparty_name: Set(request.counterparty_name),
            counterparty_account: Set(request.counterparty_account),
            counterparty_bank: Set(request.counterparty_bank),
            counterparty_country: Set(request.counterparty_country),
            transaction_date: Set(request.transaction_date),
            value_date: Set(request.value_date),
            reference_number: Set(request.reference_number),
            channel: Set(request.channel),
            risk_score: Set(rust_decimal::Decimal::from(0)),
            risk_factors: Set(serde_json::json!([])),
            is_suspicious: Set(false),
            alert_generated: Set(false),
            status: Set("PENDING".to_string()),
            processed_at: Set(None),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(None),
            updated_by: Set(None),
            version: Set(1),
            metadata: Set(serde_json::json!({})),
        };

        let transaction = transaction_model.insert(&self.db).await?;
        Ok(transaction)
    }

    /// Get transaction by ID
    pub async fn get_transaction(&self, transaction_id: Uuid) -> Result<Transaction, RegulateAIError> {
        transaction::Entity::find_by_id(transaction_id)
            .one(&self.db)
            .await?
            .ok_or_else(|| RegulateAIError::NotFound {
                resource_type: "Transaction".to_string(),
                resource_id: transaction_id.to_string(),
                code: "TRANSACTION_NOT_FOUND".to_string(),
            })
    }

    /// Get customer transactions since a date
    pub async fn get_customer_transactions_since(
        &self,
        customer_id: Uuid,
        since_date: DateTime<Utc>,
    ) -> Result<Vec<Transaction>, RegulateAIError> {
        let transactions = transaction::Entity::find()
            .filter(transaction::Column::CustomerId.eq(customer_id))
            .filter(transaction::Column::TransactionDate.gte(since_date))
            .order_by_desc(transaction::Column::TransactionDate)
            .all(&self.db)
            .await?;

        Ok(transactions)
    }

    /// Update transaction risk assessment
    pub async fn update_transaction_risk(
        &self,
        transaction_id: Uuid,
        risk_score: f64,
        risk_factors: Vec<String>,
        is_suspicious: bool,
    ) -> Result<Transaction, RegulateAIError> {
        let transaction = self.get_transaction(transaction_id).await?;
        
        let mut transaction_model: transaction::ActiveModel = transaction.into();
        transaction_model.risk_score = Set(rust_decimal::Decimal::from_f64_retain(risk_score).unwrap_or_default());
        transaction_model.risk_factors = Set(serde_json::to_value(risk_factors)?);
        transaction_model.is_suspicious = Set(is_suspicious);
        transaction_model.alert_generated = Set(is_suspicious);
        transaction_model.updated_at = Set(Utc::now());

        let updated_transaction = transaction_model.update(&self.db).await?;
        Ok(updated_transaction)
    }

    /// Get suspicious transactions
    pub async fn get_suspicious_transactions(
        &self,
        start_date: DateTime<Utc>,
        end_date: DateTime<Utc>,
        limit: u64,
    ) -> Result<Vec<Transaction>, RegulateAIError> {
        let transactions = transaction::Entity::find()
            .filter(transaction::Column::IsSuspicious.eq(true))
            .filter(transaction::Column::TransactionDate.between(start_date, end_date))
            .order_by_desc(transaction::Column::RiskScore)
            .limit(limit)
            .all(&self.db)
            .await?;

        Ok(transactions)
    }
}

/// Alert repository
pub struct AlertRepository {
    db: DatabaseConnection,
}

impl AlertRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new alert
    pub async fn create_alert(&self, request: CreateAlertRequest) -> Result<AmlAlert, RegulateAIError> {
        let alert_model = aml_alert::ActiveModel {
            id: Set(Uuid::new_v4()),
            alert_type: Set(request.alert_type),
            severity: Set(match request.severity {
                AlertSeverity::Low => "LOW".to_string(),
                AlertSeverity::Medium => "MEDIUM".to_string(),
                AlertSeverity::High => "HIGH".to_string(),
                AlertSeverity::Critical => "CRITICAL".to_string(),
            }),
            customer_id: Set(request.customer_id),
            transaction_id: Set(request.transaction_id),
            rule_name: Set(request.rule_name),
            description: Set(request.description),
            risk_score: Set(request.risk_score.map(|s| rust_decimal::Decimal::from_f64_retain(s).unwrap_or_default())),
            status: Set("OPEN".to_string()),
            assigned_to: Set(None),
            investigation_notes: Set(None),
            resolution: Set(None),
            closed_at: Set(None),
            escalated_at: Set(None),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(None),
            updated_by: Set(None),
            version: Set(1),
            metadata: Set(request.metadata),
        };

        let alert = alert_model.insert(&self.db).await?;
        Ok(alert)
    }

    /// Get alert by ID
    pub async fn get_alert(&self, alert_id: Uuid) -> Result<AmlAlert, RegulateAIError> {
        aml_alert::Entity::find_by_id(alert_id)
            .one(&self.db)
            .await?
            .ok_or_else(|| RegulateAIError::NotFound {
                resource_type: "Alert".to_string(),
                resource_id: alert_id.to_string(),
                code: "ALERT_NOT_FOUND".to_string(),
            })
    }

    /// List alerts with filtering
    pub async fn list_alerts(
        &self,
        page: u64,
        per_page: u64,
        status: Option<String>,
        severity: Option<String>,
        customer_id: Option<Uuid>,
    ) -> Result<(Vec<AmlAlert>, u64), RegulateAIError> {
        let mut query = aml_alert::Entity::find();

        if let Some(status_filter) = status {
            query = query.filter(aml_alert::Column::Status.eq(status_filter));
        }

        if let Some(severity_filter) = severity {
            query = query.filter(aml_alert::Column::Severity.eq(severity_filter));
        }

        if let Some(cust_id) = customer_id {
            query = query.filter(aml_alert::Column::CustomerId.eq(cust_id));
        }

        let paginator = query
            .order_by_desc(aml_alert::Column::CreatedAt)
            .paginate(&self.db, per_page);

        let total_pages = paginator.num_pages().await?;
        let alerts = paginator.fetch_page(page).await?;

        Ok((alerts, total_pages))
    }

    /// Update alert status
    pub async fn update_alert_status(
        &self,
        alert_id: Uuid,
        status: String,
        assigned_to: Option<Uuid>,
        notes: Option<String>,
    ) -> Result<AmlAlert, RegulateAIError> {
        let alert = self.get_alert(alert_id).await?;
        
        let mut alert_model: aml_alert::ActiveModel = alert.into();
        alert_model.status = Set(status.clone());
        alert_model.assigned_to = Set(assigned_to);
        
        if let Some(investigation_notes) = notes {
            alert_model.investigation_notes = Set(Some(investigation_notes));
        }

        if status == "CLOSED" {
            alert_model.closed_at = Set(Some(Utc::now()));
        }

        alert_model.updated_at = Set(Utc::now());

        let updated_alert = alert_model.update(&self.db).await?;
        Ok(updated_alert)
    }
}

/// Sanctions repository
pub struct SanctionsRepository {
    db: DatabaseConnection,
}

impl SanctionsRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Get active sanctions lists
    pub async fn get_active_sanctions(&self) -> Result<Vec<SanctionsList>, RegulateAIError> {
        let sanctions = sanctions_list::Entity::find()
            .filter(sanctions_list::Column::IsActive.eq(true))
            .order_by_asc(sanctions_list::Column::ListName)
            .all(&self.db)
            .await?;

        Ok(sanctions)
    }

    /// Search sanctions by name
    pub async fn search_sanctions_by_name(&self, name: &str) -> Result<Vec<SanctionsList>, RegulateAIError> {
        let sanctions = sanctions_list::Entity::find()
            .filter(sanctions_list::Column::IsActive.eq(true))
            .filter(sanctions_list::Column::EntityName.contains(name))
            .limit(100)
            .all(&self.db)
            .await?;

        Ok(sanctions)
    }

    /// Update sanctions list from external source
    pub async fn upsert_sanctions_entry(
        &self,
        list_name: String,
        source: String,
        entity_type: String,
        entity_name: String,
        aliases: serde_json::Value,
        addresses: serde_json::Value,
        identifiers: serde_json::Value,
    ) -> Result<SanctionsList, RegulateAIError> {
        // Check if entry already exists
        let existing = sanctions_list::Entity::find()
            .filter(sanctions_list::Column::ListName.eq(&list_name))
            .filter(sanctions_list::Column::EntityName.eq(&entity_name))
            .one(&self.db)
            .await?;

        if let Some(existing_entry) = existing {
            // Update existing entry
            let mut sanctions_model: sanctions_list::ActiveModel = existing_entry.into();
            sanctions_model.aliases = Set(aliases);
            sanctions_model.addresses = Set(addresses);
            sanctions_model.identifiers = Set(identifiers);
            sanctions_model.last_updated = Set(Some(Utc::now().date_naive()));
            sanctions_model.updated_at = Set(Utc::now());

            let updated_entry = sanctions_model.update(&self.db).await?;
            Ok(updated_entry)
        } else {
            // Create new entry
            let sanctions_model = sanctions_list::ActiveModel {
                id: Set(Uuid::new_v4()),
                list_name: Set(list_name),
                source: Set(source),
                entity_type: Set(entity_type),
                entity_name: Set(entity_name),
                aliases: Set(aliases),
                addresses: Set(addresses),
                identifiers: Set(identifiers),
                sanctions_type: Set(Some("SANCTIONS".to_string())),
                listing_date: Set(Some(Utc::now().date_naive())),
                last_updated: Set(Some(Utc::now().date_naive())),
                is_active: Set(true),
                created_at: Set(Utc::now()),
                updated_at: Set(Utc::now()),
            };

            let new_entry = sanctions_model.insert(&self.db).await?;
            Ok(new_entry)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use regulateai_database::create_test_connection;

    #[tokio::test]
    async fn test_customer_repository() {
        let db = create_test_connection().await.unwrap();
        let repo = CustomerRepository::new(db);

        let request = CreateCustomerRequest {
            customer_type: CustomerType::Individual,
            first_name: "John".to_string(),
            last_name: "Doe".to_string(),
            date_of_birth: Some(chrono::NaiveDate::from_ymd_opt(1990, 1, 1).unwrap()),
            nationality: Some("US".to_string()),
            identification_documents: vec![],
            address: AddressInfo {
                street_address: "123 Main St".to_string(),
                city: "New York".to_string(),
                state_province: Some("NY".to_string()),
                postal_code: Some("10001".to_string()),
                country: "US".to_string(),
            },
            contact_info: ContactInfo {
                email: "john.doe@example.com".to_string(),
                phone: Some("+1234567890".to_string()),
                mobile: None,
            },
            organization_id: None,
        };

        let customer = repo.create_customer(request).await.unwrap();
        assert_eq!(customer.first_name, Some("John".to_string()));
        assert_eq!(customer.last_name, Some("Doe".to_string()));

        let retrieved = repo.get_customer(customer.id).await.unwrap();
        assert_eq!(retrieved.id, customer.id);
    }

    #[tokio::test]
    async fn test_alert_repository() {
        let db = create_test_connection().await.unwrap();
        let repo = AlertRepository::new(db);

        let request = CreateAlertRequest {
            alert_type: "TEST_ALERT".to_string(),
            severity: AlertSeverity::Medium,
            customer_id: Some(Uuid::new_v4()),
            transaction_id: None,
            rule_name: Some("Test Rule".to_string()),
            description: "Test alert description".to_string(),
            risk_score: Some(75.0),
            metadata: serde_json::json!({"test": "data"}),
        };

        let alert = repo.create_alert(request).await.unwrap();
        assert_eq!(alert.alert_type, "TEST_ALERT");
        assert_eq!(alert.severity, "MEDIUM");

        let retrieved = repo.get_alert(alert.id).await.unwrap();
        assert_eq!(retrieved.id, alert.id);
    }
}
