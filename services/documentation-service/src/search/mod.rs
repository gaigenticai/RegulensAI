//! Search engine for interactive documentation
//! 
//! Provides full-text search capabilities across all documentation content

use std::path::Path;
use tantivy::{
    collector::TopDocs,
    query::QueryParser,
    schema::{Field, Schema, STORED, TEXT},
    Index, IndexReader, IndexWriter, ReloadPolicy,
};
use tracing::{info, error, warn};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use regulateai_errors::RegulateAIError;

/// Search result item
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub title: String,
    pub content: String,
    pub url: String,
    pub category: String,
    pub service: String,
    pub score: f32,
    pub last_updated: DateTime<Utc>,
}

/// Search engine for documentation content
pub struct SearchEngine {
    index: Index,
    reader: IndexReader,
    title_field: Field,
    content_field: Field,
    url_field: Field,
    category_field: Field,
    service_field: Field,
    timestamp_field: Field,
}

impl SearchEngine {
    /// Create a new search engine instance
    pub async fn new(index_path: &str) -> Result<Self, RegulateAIError> {
        info!("Initializing search engine at: {}", index_path);

        // Create schema
        let mut schema_builder = Schema::builder();
        let title_field = schema_builder.add_text_field("title", TEXT | STORED);
        let content_field = schema_builder.add_text_field("content", TEXT | STORED);
        let url_field = schema_builder.add_text_field("url", STORED);
        let category_field = schema_builder.add_text_field("category", TEXT | STORED);
        let service_field = schema_builder.add_text_field("service", TEXT | STORED);
        let timestamp_field = schema_builder.add_text_field("timestamp", STORED);
        let schema = schema_builder.build();

        // Create or open index
        let index = if Path::new(index_path).exists() {
            Index::open_in_dir(index_path)
                .map_err(|e| RegulateAIError::SearchError {
                    message: format!("Failed to open search index: {}", e),
                    query: None,
                })?
        } else {
            std::fs::create_dir_all(index_path)
                .map_err(|e| RegulateAIError::SearchError {
                    message: format!("Failed to create index directory: {}", e),
                    query: None,
                })?;
            
            Index::create_in_dir(index_path, schema.clone())
                .map_err(|e| RegulateAIError::SearchError {
                    message: format!("Failed to create search index: {}", e),
                    query: None,
                })?
        };

        // Create reader
        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::OnCommit)
            .try_into()
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Failed to create index reader: {}", e),
                query: None,
            })?;

        info!("Search engine initialized successfully");

        Ok(Self {
            index,
            reader,
            title_field,
            content_field,
            url_field,
            category_field,
            service_field,
            timestamp_field,
        })
    }

    /// Search documentation content
    pub async fn search(
        &self,
        query: &str,
        category_filter: Option<&str>,
        service_filter: Option<&str>,
    ) -> Result<Vec<SearchResult>, RegulateAIError> {
        info!("Searching for: '{}' with filters - category: {:?}, service: {:?}", 
              query, category_filter, service_filter);

        let searcher = self.reader.searcher();
        
        // Build query
        let query_parser = QueryParser::for_index(&self.index, vec![self.title_field, self.content_field]);
        let parsed_query = query_parser
            .parse_query(query)
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Failed to parse search query: {}", e),
                query: Some(query.to_string()),
            })?;

        // Execute search
        let top_docs = searcher
            .search(&parsed_query, &TopDocs::with_limit(50))
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Search execution failed: {}", e),
                query: Some(query.to_string()),
            })?;

        let mut results = Vec::new();

        for (score, doc_address) in top_docs {
            let retrieved_doc = searcher
                .doc(doc_address)
                .map_err(|e| RegulateAIError::SearchError {
                    message: format!("Failed to retrieve document: {}", e),
                    query: Some(query.to_string()),
                })?;

            let title = retrieved_doc
                .get_first(self.title_field)
                .and_then(|v| v.as_text())
                .unwrap_or("Untitled")
                .to_string();

            let content = retrieved_doc
                .get_first(self.content_field)
                .and_then(|v| v.as_text())
                .unwrap_or("")
                .to_string();

            let url = retrieved_doc
                .get_first(self.url_field)
                .and_then(|v| v.as_text())
                .unwrap_or("")
                .to_string();

            let category = retrieved_doc
                .get_first(self.category_field)
                .and_then(|v| v.as_text())
                .unwrap_or("General")
                .to_string();

            let service = retrieved_doc
                .get_first(self.service_field)
                .and_then(|v| v.as_text())
                .unwrap_or("Core")
                .to_string();

            let timestamp_str = retrieved_doc
                .get_first(self.timestamp_field)
                .and_then(|v| v.as_text())
                .unwrap_or("");

            let last_updated = timestamp_str
                .parse::<DateTime<Utc>>()
                .unwrap_or_else(|_| Utc::now());

            // Apply filters
            if let Some(cat_filter) = category_filter {
                if !category.to_lowercase().contains(&cat_filter.to_lowercase()) {
                    continue;
                }
            }

            if let Some(svc_filter) = service_filter {
                if !service.to_lowercase().contains(&svc_filter.to_lowercase()) {
                    continue;
                }
            }

            results.push(SearchResult {
                title,
                content: truncate_content(&content, 200),
                url,
                category,
                service,
                score,
                last_updated,
            });
        }

        info!("Found {} search results", results.len());
        Ok(results)
    }

    /// Index all documentation content
    pub async fn index_documentation(&self) -> Result<(), RegulateAIError> {
        info!("Starting documentation indexing");

        let mut index_writer = self.index
            .writer(50_000_000)
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Failed to create index writer: {}", e),
                query: None,
            })?;

        // Clear existing index
        index_writer.delete_all_documents()
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Failed to clear index: {}", e),
                query: None,
            })?;

        // Index authentication framework documentation
        self.index_feature_documentation(
            &mut index_writer,
            "Authentication & Authorization Framework",
            &self.get_auth_framework_content(),
            "/features/authentication-authorization-framework",
            "Security",
            "Authentication",
        )?;

        // Index AML service documentation
        self.index_feature_documentation(
            &mut index_writer,
            "AML Service",
            &self.get_aml_service_content(),
            "/features/aml-service",
            "Compliance",
            "AML",
        )?;

        // Index API documentation
        self.index_api_documentation(&mut index_writer)?;

        // Index test results
        self.index_test_results(&mut index_writer)?;

        // Index database schema
        self.index_database_schema(&mut index_writer)?;

        // Index environment configuration
        self.index_environment_config(&mut index_writer)?;

        // Commit changes
        index_writer.commit()
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Failed to commit index changes: {}", e),
                query: None,
            })?;

        info!("Documentation indexing completed successfully");
        Ok(())
    }

    /// Rebuild the entire search index
    pub async fn rebuild_index(&self) -> Result<(), RegulateAIError> {
        info!("Rebuilding search index");
        self.index_documentation().await
    }

    /// Index feature documentation
    fn index_feature_documentation(
        &self,
        writer: &mut IndexWriter,
        title: &str,
        content: &str,
        url: &str,
        category: &str,
        service: &str,
    ) -> Result<(), RegulateAIError> {
        let mut doc = tantivy::Document::default();
        doc.add_text(self.title_field, title);
        doc.add_text(self.content_field, content);
        doc.add_text(self.url_field, url);
        doc.add_text(self.category_field, category);
        doc.add_text(self.service_field, service);
        doc.add_text(self.timestamp_field, &Utc::now().to_rfc3339());

        writer.add_document(doc)
            .map_err(|e| RegulateAIError::SearchError {
                message: format!("Failed to add document to index: {}", e),
                query: None,
            })?;

        Ok(())
    }

    /// Index API documentation
    fn index_api_documentation(&self, writer: &mut IndexWriter) -> Result<(), RegulateAIError> {
        // Index AML API endpoints
        let aml_endpoints = vec![
            ("Customer Onboarding API", "POST /api/v1/customers/onboard", "/api-reference/aml-customer-onboarding"),
            ("Transaction Monitoring API", "POST /api/v1/transactions/{id}/monitor", "/api-reference/aml-transaction-monitoring"),
            ("Sanctions Screening API", "POST /api/v1/sanctions/screen", "/api-reference/aml-sanctions-screening"),
        ];

        for (title, description, url) in aml_endpoints {
            self.index_feature_documentation(
                writer,
                title,
                &format!("{} - Complete API documentation with request/response schemas, authentication requirements, and examples", description),
                url,
                "API Reference",
                "AML",
            )?;
        }

        // Index Authentication API endpoints
        let auth_endpoints = vec![
            ("Login API", "POST /auth/login", "/api-reference/auth-login"),
            ("Token Refresh API", "POST /auth/refresh", "/api-reference/auth-refresh"),
            ("User Profile API", "GET /auth/me", "/api-reference/auth-profile"),
        ];

        for (title, description, url) in auth_endpoints {
            self.index_feature_documentation(
                writer,
                title,
                &format!("{} - Authentication endpoint with JWT token management", description),
                url,
                "API Reference",
                "Authentication",
            )?;
        }

        Ok(())
    }

    /// Index test results
    fn index_test_results(&self, writer: &mut IndexWriter) -> Result<(), RegulateAIError> {
        self.index_feature_documentation(
            writer,
            "Authentication Framework Test Results",
            "Complete test suite with 47 test cases, 95.2% line coverage. Includes JWT token management, password security, RBAC system, and session management tests.",
            "/test-results/authentication",
            "Test Results",
            "Authentication",
        )?;

        self.index_feature_documentation(
            writer,
            "AML Service Test Results",
            "Comprehensive test suite with 89 test cases, 92.8% line coverage. Covers customer onboarding, transaction monitoring, sanctions screening, and alert management.",
            "/test-results/aml",
            "Test Results",
            "AML",
        )?;

        Ok(())
    }

    /// Index database schema
    fn index_database_schema(&self, writer: &mut IndexWriter) -> Result<(), RegulateAIError> {
        self.index_feature_documentation(
            writer,
            "Database Schema Documentation",
            "Complete PostgreSQL schema with 25+ tables covering users, roles, customers, transactions, alerts, sanctions, policies, controls, and audit logs. Includes table relationships and field descriptions.",
            "/database-schema",
            "Database",
            "Core",
        )?;

        Ok(())
    }

    /// Index environment configuration
    fn index_environment_config(&self, writer: &mut IndexWriter) -> Result<(), RegulateAIError> {
        self.index_feature_documentation(
            writer,
            "Environment Configuration",
            "Comprehensive environment variable documentation covering application configuration, database settings, authentication, external services, AI/ML configuration, and service-specific settings.",
            "/environment-config",
            "Configuration",
            "Core",
        )?;

        Ok(())
    }

    /// Get authentication framework content for indexing
    fn get_auth_framework_content(&self) -> String {
        r#"
        Authentication & Authorization Framework provides enterprise-grade security for RegulateAI platform.
        Features include JWT token management, Argon2 password hashing, Role-Based Access Control (RBAC),
        session management with rotation, multi-factor authentication support, and comprehensive audit logging.
        
        Database tables: users, roles, user_roles, sessions, audit_logs
        Environment variables: JWT_SECRET, JWT_EXPIRATION, APP_SECRET_KEY, SESSION_TIMEOUT
        API endpoints: /auth/login, /auth/logout, /auth/refresh, /auth/register, /auth/me
        
        Security features include brute force protection, secure token generation, password complexity policies,
        session security with rotation, granular permissions, role hierarchy, and complete audit trails.
        "#.to_string()
    }

    /// Get AML service content for indexing
    fn get_aml_service_content(&self) -> String {
        r#"
        AML Service provides comprehensive anti-money laundering capabilities including customer due diligence,
        transaction monitoring, sanctions screening, and suspicious activity reporting.
        
        Features: Customer onboarding with KYC verification, real-time transaction monitoring using 7 rule engines,
        multi-strategy sanctions screening, dynamic risk assessment, alert management, SAR generation,
        and behavioral analytics for pattern detection.
        
        Database tables: customers, transactions, aml_alerts, sanctions_lists
        Environment variables: AML_TRANSACTION_THRESHOLD, AML_RISK_SCORE_THRESHOLD, OFAC_API_KEY
        API endpoints: /api/v1/customers/onboard, /api/v1/transactions/monitor, /api/v1/sanctions/screen
        
        Monitoring rules include high value transactions, velocity patterns, round amounts, geographic anomalies,
        time-based patterns, counterparty risk, and behavioral deviations.
        "#.to_string()
    }
}

/// Truncate content to specified length with ellipsis
fn truncate_content(content: &str, max_length: usize) -> String {
    if content.len() <= max_length {
        content.to_string()
    } else {
        format!("{}...", &content[..max_length])
    }
}
