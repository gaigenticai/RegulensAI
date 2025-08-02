//! AML Reporting Module
//! 
//! This module provides comprehensive regulatory reporting capabilities including:
//! - Suspicious Activity Report (SAR) generation and filing
//! - Currency Transaction Report (CTR) generation
//! - Cross-Border Report (CBR) generation
//! - Threshold Transaction Report (TTR) generation
//! - Automated regulatory filing with authorities
//! - Report status tracking and audit trails

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use tracing::{info, warn, error, debug};

use regulateai_errors::RegulateAIError;
use crate::models::{Customer, Transaction, Alert, Investigation};

/// AML reporting engine for regulatory compliance
pub struct AMLReportingEngine {
    /// Reporting configuration
    config: ReportingConfig,
    
    /// Report templates
    templates: HashMap<ReportType, ReportTemplate>,
    
    /// Filing endpoints for different jurisdictions
    filing_endpoints: HashMap<String, FilingEndpoint>,
}

/// Reporting configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportingConfig {
    /// Enable automated filing
    pub automated_filing_enabled: bool,
    
    /// Default jurisdiction for reporting
    pub default_jurisdiction: String,
    
    /// Report retention period in days
    pub retention_period_days: u32,
    
    /// Filing deadlines by report type
    pub filing_deadlines: HashMap<ReportType, u32>,
    
    /// Regulatory authority endpoints
    pub authority_endpoints: HashMap<String, String>,
    
    /// Digital signature configuration
    pub digital_signature: DigitalSignatureConfig,
}

/// Digital signature configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DigitalSignatureConfig {
    /// Enable digital signatures
    pub enabled: bool,
    
    /// Certificate path
    pub certificate_path: String,
    
    /// Private key path
    pub private_key_path: String,
    
    /// Signature algorithm
    pub algorithm: String,
}

/// Report types
#[derive(Debug, Clone, Hash, Eq, PartialEq, Serialize, Deserialize)]
pub enum ReportType {
    SAR,  // Suspicious Activity Report
    CTR,  // Currency Transaction Report
    CBR,  // Cross-Border Report
    TTR,  // Threshold Transaction Report
    FBAR, // Foreign Bank Account Report
    Form8300, // IRS Form 8300
}

/// Report template
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportTemplate {
    /// Template name
    pub name: String,
    
    /// Template version
    pub version: String,
    
    /// Required fields
    pub required_fields: Vec<String>,
    
    /// Optional fields
    pub optional_fields: Vec<String>,
    
    /// Validation rules
    pub validation_rules: Vec<ValidationRule>,
    
    /// Template content
    pub template_content: String,
}

/// Validation rule
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationRule {
    /// Field name
    pub field: String,
    
    /// Rule type
    pub rule_type: ValidationRuleType,
    
    /// Rule parameters
    pub parameters: HashMap<String, String>,
    
    /// Error message
    pub error_message: String,
}

/// Validation rule types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationRuleType {
    Required,
    MinLength,
    MaxLength,
    Pattern,
    Range,
    Custom,
}

/// Filing endpoint configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilingEndpoint {
    /// Endpoint URL
    pub url: String,
    
    /// Authentication method
    pub auth_method: AuthMethod,
    
    /// API key or credentials
    pub credentials: HashMap<String, String>,
    
    /// Supported report types
    pub supported_reports: Vec<ReportType>,
    
    /// Filing format
    pub format: FilingFormat,
}

/// Authentication methods
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AuthMethod {
    ApiKey,
    OAuth2,
    Certificate,
    BasicAuth,
}

/// Filing formats
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FilingFormat {
    XML,
    JSON,
    PDF,
    CSV,
}

/// Suspicious Activity Report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuspiciousActivityReport {
    /// Report ID
    pub id: Uuid,
    
    /// Report number (sequential)
    pub report_number: String,
    
    /// Filing institution information
    pub filing_institution: InstitutionInfo,
    
    /// Subject information
    pub subject: SubjectInfo,
    
    /// Suspicious activity details
    pub suspicious_activity: SuspiciousActivityDetails,
    
    /// Supporting documentation
    pub supporting_documents: Vec<SupportingDocument>,
    
    /// Report status
    pub status: ReportStatus,
    
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    
    /// Filed timestamp
    pub filed_at: Option<DateTime<Utc>>,
    
    /// Filing reference number
    pub filing_reference: Option<String>,
    
    /// Jurisdiction
    pub jurisdiction: String,
}

/// Institution information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstitutionInfo {
    /// Institution name
    pub name: String,
    
    /// Institution identifier
    pub identifier: String,
    
    /// Address
    pub address: Address,
    
    /// Contact information
    pub contact: ContactInfo,
    
    /// Regulatory identifiers
    pub regulatory_ids: HashMap<String, String>,
}

/// Subject information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubjectInfo {
    /// Subject type (Individual, Entity)
    pub subject_type: String,
    
    /// Name
    pub name: String,
    
    /// Date of birth (for individuals)
    pub date_of_birth: Option<chrono::NaiveDate>,
    
    /// Identification documents
    pub identification: Vec<IdentificationDocument>,
    
    /// Address
    pub address: Address,
    
    /// Account information
    pub accounts: Vec<AccountInfo>,
    
    /// Relationship to institution
    pub relationship: String,
}

/// Suspicious activity details
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuspiciousActivityDetails {
    /// Activity type
    pub activity_type: String,
    
    /// Activity description
    pub description: String,
    
    /// Date range of activity
    pub date_range: DateRange,
    
    /// Total amount involved
    pub total_amount: f64,
    
    /// Currency
    pub currency: String,
    
    /// Transactions involved
    pub transactions: Vec<TransactionSummary>,
    
    /// Suspicious indicators
    pub indicators: Vec<String>,
    
    /// Investigation summary
    pub investigation_summary: String,
    
    /// Law enforcement contacted
    pub law_enforcement_contacted: bool,
}

/// Supporting document
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupportingDocument {
    /// Document type
    pub document_type: String,
    
    /// Document name
    pub name: String,
    
    /// File path or reference
    pub file_reference: String,
    
    /// Document hash for integrity
    pub hash: String,
    
    /// Upload timestamp
    pub uploaded_at: DateTime<Utc>,
}

/// Report status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ReportStatus {
    Draft,
    UnderReview,
    Approved,
    Filed,
    Acknowledged,
    Rejected,
}

/// Address information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Address {
    pub street: String,
    pub city: String,
    pub state: Option<String>,
    pub postal_code: String,
    pub country: String,
}

/// Contact information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContactInfo {
    pub phone: Option<String>,
    pub email: Option<String>,
    pub fax: Option<String>,
}

/// Identification document
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentificationDocument {
    pub document_type: String,
    pub document_number: String,
    pub issuing_authority: String,
    pub issue_date: Option<chrono::NaiveDate>,
    pub expiry_date: Option<chrono::NaiveDate>,
}

/// Account information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountInfo {
    pub account_number: String,
    pub account_type: String,
    pub opening_date: chrono::NaiveDate,
    pub closing_date: Option<chrono::NaiveDate>,
    pub balance: Option<f64>,
}

/// Date range
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DateRange {
    pub start_date: chrono::NaiveDate,
    pub end_date: chrono::NaiveDate,
}

/// Transaction summary
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionSummary {
    pub transaction_id: Uuid,
    pub date: chrono::NaiveDate,
    pub amount: f64,
    pub currency: String,
    pub description: String,
    pub counterparty: Option<String>,
}

/// Currency Transaction Report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CurrencyTransactionReport {
    /// Report ID
    pub id: Uuid,
    
    /// Report number
    pub report_number: String,
    
    /// Filing institution
    pub filing_institution: InstitutionInfo,
    
    /// Transaction details
    pub transaction: CTRTransaction,
    
    /// Person conducting transaction
    pub person: PersonInfo,
    
    /// Report status
    pub status: ReportStatus,
    
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    
    /// Filed timestamp
    pub filed_at: Option<DateTime<Utc>>,
}

/// CTR transaction details
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CTRTransaction {
    pub transaction_date: chrono::NaiveDate,
    pub total_amount: f64,
    pub currency: String,
    pub transaction_type: String,
    pub account_number: String,
    pub multiple_transactions: bool,
}

/// Person information for CTR
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonInfo {
    pub name: String,
    pub date_of_birth: Option<chrono::NaiveDate>,
    pub address: Address,
    pub identification: IdentificationDocument,
    pub occupation: Option<String>,
}

impl AMLReportingEngine {
    /// Create a new AML reporting engine
    pub fn new(config: ReportingConfig) -> Self {
        let templates = Self::initialize_templates();
        let filing_endpoints = Self::initialize_filing_endpoints(&config);
        
        Self {
            config,
            templates,
            filing_endpoints,
        }
    }
    
    /// Generate a Suspicious Activity Report
    pub async fn generate_sar(
        &self,
        customer: &Customer,
        transactions: &[Transaction],
        alert: &Alert,
        investigation: &Investigation,
    ) -> Result<SuspiciousActivityReport, RegulateAIError> {
        info!("Generating SAR for customer: {} and alert: {}", customer.id, alert.id);
        
        // Create institution information
        let filing_institution = self.create_institution_info()?;
        
        // Create subject information from customer
        let subject = self.create_subject_info(customer)?;
        
        // Create suspicious activity details
        let suspicious_activity = self.create_suspicious_activity_details(
            transactions,
            alert,
            investigation,
        )?;
        
        // Generate report number
        let report_number = self.generate_report_number(ReportType::SAR).await?;
        
        let sar = SuspiciousActivityReport {
            id: Uuid::new_v4(),
            report_number,
            filing_institution,
            subject,
            suspicious_activity,
            supporting_documents: Vec::new(),
            status: ReportStatus::Draft,
            created_at: Utc::now(),
            filed_at: None,
            filing_reference: None,
            jurisdiction: self.config.default_jurisdiction.clone(),
        };
        
        // Validate the report
        self.validate_sar(&sar)?;
        
        info!("SAR generated successfully: {}", sar.id);
        Ok(sar)
    }
    
    /// Generate a Currency Transaction Report
    pub async fn generate_ctr(
        &self,
        customer: &Customer,
        transaction: &Transaction,
    ) -> Result<CurrencyTransactionReport, RegulateAIError> {
        info!("Generating CTR for customer: {} and transaction: {}", customer.id, transaction.id);
        
        // Check if transaction meets CTR threshold
        if transaction.amount < 10000.0 {
            return Err(RegulateAIError::BadRequest(
                "Transaction amount does not meet CTR threshold".to_string()
            ));
        }
        
        let filing_institution = self.create_institution_info()?;
        let person = self.create_person_info(customer)?;
        let ctr_transaction = self.create_ctr_transaction(transaction)?;
        let report_number = self.generate_report_number(ReportType::CTR).await?;
        
        let ctr = CurrencyTransactionReport {
            id: Uuid::new_v4(),
            report_number,
            filing_institution,
            transaction: ctr_transaction,
            person,
            status: ReportStatus::Draft,
            created_at: Utc::now(),
            filed_at: None,
        };
        
        // Validate the report
        self.validate_ctr(&ctr)?;
        
        info!("CTR generated successfully: {}", ctr.id);
        Ok(ctr)
    }
    
    /// File a report with regulatory authorities
    pub async fn file_report(
        &self,
        report_type: ReportType,
        report_data: &serde_json::Value,
        jurisdiction: &str,
    ) -> Result<FilingResult, RegulateAIError> {
        info!("Filing {} report for jurisdiction: {}", format!("{:?}", report_type), jurisdiction);
        
        // Get filing endpoint for jurisdiction
        let endpoint = self.filing_endpoints.get(jurisdiction)
            .ok_or_else(|| RegulateAIError::NotFound(
                format!("No filing endpoint configured for jurisdiction: {}", jurisdiction)
            ))?;
        
        // Check if endpoint supports this report type
        if !endpoint.supported_reports.contains(&report_type) {
            return Err(RegulateAIError::BadRequest(
                format!("Report type {:?} not supported for jurisdiction: {}", report_type, jurisdiction)
            ));
        }
        
        // Format report data according to endpoint requirements
        let formatted_data = self.format_report_data(report_data, &endpoint.format)?;
        
        // Sign the report if digital signatures are enabled
        let signed_data = if self.config.digital_signature.enabled {
            self.sign_report_data(&formatted_data)?
        } else {
            formatted_data
        };
        
        // Submit to regulatory authority
        let filing_result = self.submit_to_authority(endpoint, &signed_data).await?;
        
        info!("Report filed successfully: {}", filing_result.reference_number);
        Ok(filing_result)
    }
    
    /// Get report status
    pub async fn get_report_status(&self, report_id: Uuid) -> Result<ReportStatus, RegulateAIError> {
        // This would typically query a database
        // For now, return a placeholder status
        Ok(ReportStatus::Filed)
    }
    
    /// List reports by criteria
    pub async fn list_reports(
        &self,
        criteria: ReportSearchCriteria,
    ) -> Result<Vec<ReportSummary>, RegulateAIError> {
        // This would typically query a database with the given criteria
        // For now, return empty list
        Ok(Vec::new())
    }
    
    // Helper methods
    fn create_institution_info(&self) -> Result<InstitutionInfo, RegulateAIError> {
        Ok(InstitutionInfo {
            name: "RegulateAI Financial Services".to_string(),
            identifier: "REGAI001".to_string(),
            address: Address {
                street: "123 Compliance Street".to_string(),
                city: "Financial District".to_string(),
                state: Some("NY".to_string()),
                postal_code: "10001".to_string(),
                country: "US".to_string(),
            },
            contact: ContactInfo {
                phone: Some("+1-555-0123".to_string()),
                email: Some("compliance@regulateai.com".to_string()),
                fax: None,
            },
            regulatory_ids: {
                let mut ids = HashMap::new();
                ids.insert("FDIC".to_string(), "12345".to_string());
                ids.insert("OCC".to_string(), "67890".to_string());
                ids
            },
        })
    }
    
    fn create_subject_info(&self, customer: &Customer) -> Result<SubjectInfo, RegulateAIError> {
        Ok(SubjectInfo {
            subject_type: customer.customer_type.clone(),
            name: format!("{} {}", 
                customer.first_name.as_deref().unwrap_or(""), 
                customer.last_name.as_deref().unwrap_or("")
            ).trim().to_string(),
            date_of_birth: customer.date_of_birth,
            identification: Vec::new(), // Would be populated from customer data
            address: Address {
                street: "Unknown".to_string(),
                city: "Unknown".to_string(),
                state: None,
                postal_code: "00000".to_string(),
                country: customer.nationality.clone().unwrap_or("US".to_string()),
            },
            accounts: Vec::new(), // Would be populated from customer accounts
            relationship: "Customer".to_string(),
        })
    }
    
    fn create_suspicious_activity_details(
        &self,
        transactions: &[Transaction],
        alert: &Alert,
        investigation: &Investigation,
    ) -> Result<SuspiciousActivityDetails, RegulateAIError> {
        let total_amount: f64 = transactions.iter().map(|t| t.amount).sum();
        
        let transaction_summaries: Vec<TransactionSummary> = transactions.iter()
            .map(|t| TransactionSummary {
                transaction_id: t.id,
                date: t.transaction_date.date_naive(),
                amount: t.amount,
                currency: t.currency.clone(),
                description: t.description.clone().unwrap_or("Unknown".to_string()),
                counterparty: t.beneficiary_name.clone(),
            })
            .collect();
        
        Ok(SuspiciousActivityDetails {
            activity_type: alert.alert_type.clone(),
            description: alert.description.clone(),
            date_range: DateRange {
                start_date: transactions.iter()
                    .map(|t| t.transaction_date.date_naive())
                    .min()
                    .unwrap_or_else(|| chrono::Utc::now().date_naive()),
                end_date: transactions.iter()
                    .map(|t| t.transaction_date.date_naive())
                    .max()
                    .unwrap_or_else(|| chrono::Utc::now().date_naive()),
            },
            total_amount,
            currency: transactions.first().map(|t| t.currency.clone()).unwrap_or("USD".to_string()),
            transactions: transaction_summaries,
            indicators: vec![alert.description.clone()],
            investigation_summary: investigation.summary.clone().unwrap_or("Investigation ongoing".to_string()),
            law_enforcement_contacted: false,
        })
    }
    
    fn create_person_info(&self, customer: &Customer) -> Result<PersonInfo, RegulateAIError> {
        Ok(PersonInfo {
            name: format!("{} {}", 
                customer.first_name.as_deref().unwrap_or(""), 
                customer.last_name.as_deref().unwrap_or("")
            ).trim().to_string(),
            date_of_birth: customer.date_of_birth,
            address: Address {
                street: "Unknown".to_string(),
                city: "Unknown".to_string(),
                state: None,
                postal_code: "00000".to_string(),
                country: customer.nationality.clone().unwrap_or("US".to_string()),
            },
            identification: IdentificationDocument {
                document_type: "Unknown".to_string(),
                document_number: "Unknown".to_string(),
                issuing_authority: "Unknown".to_string(),
                issue_date: None,
                expiry_date: None,
            },
            occupation: None,
        })
    }
    
    fn create_ctr_transaction(&self, transaction: &Transaction) -> Result<CTRTransaction, RegulateAIError> {
        Ok(CTRTransaction {
            transaction_date: transaction.transaction_date.date_naive(),
            total_amount: transaction.amount,
            currency: transaction.currency.clone(),
            transaction_type: transaction.transaction_type.clone(),
            account_number: transaction.originator_account.clone().unwrap_or("Unknown".to_string()),
            multiple_transactions: false,
        })
    }
    
    async fn generate_report_number(&self, report_type: ReportType) -> Result<String, RegulateAIError> {
        // This would typically use a database sequence or counter
        let timestamp = Utc::now().format("%Y%m%d%H%M%S");
        let type_prefix = match report_type {
            ReportType::SAR => "SAR",
            ReportType::CTR => "CTR",
            ReportType::CBR => "CBR",
            ReportType::TTR => "TTR",
            ReportType::FBAR => "FBAR",
            ReportType::Form8300 => "8300",
        };
        
        Ok(format!("{}-{}-{:04}", type_prefix, timestamp, rand::random::<u16>() % 10000))
    }
    
    fn validate_sar(&self, sar: &SuspiciousActivityReport) -> Result<(), RegulateAIError> {
        // Implement SAR validation logic
        if sar.subject.name.is_empty() {
            return Err(RegulateAIError::BadRequest("Subject name is required".to_string()));
        }
        
        if sar.suspicious_activity.description.is_empty() {
            return Err(RegulateAIError::BadRequest("Activity description is required".to_string()));
        }
        
        Ok(())
    }
    
    fn validate_ctr(&self, ctr: &CurrencyTransactionReport) -> Result<(), RegulateAIError> {
        // Implement CTR validation logic
        if ctr.transaction.total_amount < 10000.0 {
            return Err(RegulateAIError::BadRequest("CTR threshold not met".to_string()));
        }
        
        if ctr.person.name.is_empty() {
            return Err(RegulateAIError::BadRequest("Person name is required".to_string()));
        }
        
        Ok(())
    }
    
    fn format_report_data(&self, data: &serde_json::Value, format: &FilingFormat) -> Result<Vec<u8>, RegulateAIError> {
        match format {
            FilingFormat::JSON => {
                serde_json::to_vec_pretty(data)
                    .map_err(|e| RegulateAIError::SerializationError(e.to_string()))
            }
            FilingFormat::XML => {
                // Would implement XML serialization
                Err(RegulateAIError::NotImplemented("XML format not yet implemented".to_string()))
            }
            FilingFormat::PDF => {
                // Would implement PDF generation
                Err(RegulateAIError::NotImplemented("PDF format not yet implemented".to_string()))
            }
            FilingFormat::CSV => {
                // Would implement CSV serialization
                Err(RegulateAIError::NotImplemented("CSV format not yet implemented".to_string()))
            }
        }
    }
    
    fn sign_report_data(&self, data: &[u8]) -> Result<Vec<u8>, RegulateAIError> {
        // Would implement digital signature
        // For now, just return the original data
        Ok(data.to_vec())
    }
    
    async fn submit_to_authority(&self, endpoint: &FilingEndpoint, data: &[u8]) -> Result<FilingResult, RegulateAIError> {
        // Would implement actual HTTP submission to regulatory authority
        // For now, return a mock result
        Ok(FilingResult {
            reference_number: format!("REF-{}", Uuid::new_v4()),
            status: "SUBMITTED".to_string(),
            submitted_at: Utc::now(),
            acknowledgment_expected_at: Some(Utc::now() + chrono::Duration::hours(24)),
        })
    }
    
    fn initialize_templates() -> HashMap<ReportType, ReportTemplate> {
        let mut templates = HashMap::new();
        
        // SAR template
        templates.insert(ReportType::SAR, ReportTemplate {
            name: "Suspicious Activity Report".to_string(),
            version: "1.0".to_string(),
            required_fields: vec![
                "filing_institution".to_string(),
                "subject".to_string(),
                "suspicious_activity".to_string(),
            ],
            optional_fields: vec![
                "supporting_documents".to_string(),
            ],
            validation_rules: Vec::new(),
            template_content: "SAR Template Content".to_string(),
        });
        
        // CTR template
        templates.insert(ReportType::CTR, ReportTemplate {
            name: "Currency Transaction Report".to_string(),
            version: "1.0".to_string(),
            required_fields: vec![
                "filing_institution".to_string(),
                "transaction".to_string(),
                "person".to_string(),
            ],
            optional_fields: Vec::new(),
            validation_rules: Vec::new(),
            template_content: "CTR Template Content".to_string(),
        });
        
        templates
    }
    
    fn initialize_filing_endpoints(config: &ReportingConfig) -> HashMap<String, FilingEndpoint> {
        let mut endpoints = HashMap::new();
        
        // US FinCEN endpoint
        endpoints.insert("US".to_string(), FilingEndpoint {
            url: "https://api.fincen.gov/reports".to_string(),
            auth_method: AuthMethod::Certificate,
            credentials: HashMap::new(),
            supported_reports: vec![ReportType::SAR, ReportType::CTR],
            format: FilingFormat::XML,
        });
        
        endpoints
    }
}

/// Filing result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilingResult {
    pub reference_number: String,
    pub status: String,
    pub submitted_at: DateTime<Utc>,
    pub acknowledgment_expected_at: Option<DateTime<Utc>>,
}

/// Report search criteria
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportSearchCriteria {
    pub report_type: Option<ReportType>,
    pub status: Option<ReportStatus>,
    pub date_range: Option<DateRange>,
    pub customer_id: Option<Uuid>,
    pub jurisdiction: Option<String>,
}

/// Report summary
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportSummary {
    pub id: Uuid,
    pub report_type: ReportType,
    pub report_number: String,
    pub status: ReportStatus,
    pub created_at: DateTime<Utc>,
    pub filed_at: Option<DateTime<Utc>>,
}

impl Default for ReportingConfig {
    fn default() -> Self {
        Self {
            automated_filing_enabled: false,
            default_jurisdiction: "US".to_string(),
            retention_period_days: 2555, // 7 years
            filing_deadlines: {
                let mut deadlines = HashMap::new();
                deadlines.insert(ReportType::SAR, 30); // 30 days
                deadlines.insert(ReportType::CTR, 15); // 15 days
                deadlines
            },
            authority_endpoints: HashMap::new(),
            digital_signature: DigitalSignatureConfig {
                enabled: false,
                certificate_path: "/etc/ssl/certs/regulateai.crt".to_string(),
                private_key_path: "/etc/ssl/private/regulateai.key".to_string(),
                algorithm: "RSA-SHA256".to_string(),
            },
        }
    }
}
