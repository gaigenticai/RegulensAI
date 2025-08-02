//! Documentation Service Integration Tests
//! 
//! Comprehensive test suite for the documentation service including:
//! - Document management operations
//! - Template processing and rendering
//! - Version control and history management
//! - Search and indexing functionality
//! - User permissions and access control

use std::collections::HashMap;
use tokio;
use uuid::Uuid;
use chrono::{Utc, Duration};
use serde_json::json;

use regulateai_errors::RegulateAIError;
use crate::models::{
    Document, DocumentType, DocumentStatus, VisibilityLevel, DocumentMetadata,
    DocumentTemplate, TemplateVariable, VariableType, TemplateMetadata, ComplexityLevel,
    SearchQuery, SortBy,
};
use crate::templates::{TemplateEngine, TemplateEngineConfig, TemplateContext};
use crate::versioning::{VersionManager, VersionConfig};
use crate::indexing::{IndexManager, IndexConfig, SearchContext, SearchOptions};

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_complete_document_lifecycle() {
        // Test complete document lifecycle from creation to archival
        
        let mut version_manager = VersionManager::new(VersionConfig::default());
        let mut index_manager = IndexManager::new(IndexConfig::default());
        
        // 1. Create initial document
        let document = create_test_document("Test Policy", DocumentType::Policy);
        
        // 2. Index the document
        let index_result = index_manager.index_document(&document).await;
        assert!(index_result.is_ok(), "Document indexing should succeed");
        
        // 3. Create initial version
        let version_result = version_manager.create_version(
            &document,
            "Initial version".to_string(),
            Uuid::new_v4(),
        ).await;
        assert!(version_result.is_ok(), "Version creation should succeed");
        let initial_version = version_result.unwrap();
        assert_eq!(initial_version.version, 1);
        assert!(initial_version.is_current);
        
        // 4. Update document content
        let mut updated_document = document.clone();
        updated_document.content = "Updated policy content with new requirements.".to_string();
        updated_document.updated_at = Utc::now();
        
        // 5. Update index
        let update_index_result = index_manager.update_document_index(&updated_document).await;
        assert!(update_index_result.is_ok(), "Index update should succeed");
        
        // 6. Create new version
        let new_version_result = version_manager.create_version(
            &updated_document,
            "Added new requirements".to_string(),
            Uuid::new_v4(),
        ).await;
        assert!(new_version_result.is_ok(), "New version creation should succeed");
        let new_version = new_version_result.unwrap();
        assert_eq!(new_version.version, 2);
        assert!(new_version.is_current);
        
        // 7. Verify version history
        let history_result = version_manager.get_version_history(document.id).await;
        assert!(history_result.is_ok(), "Version history retrieval should succeed");
        let history = history_result.unwrap();
        assert_eq!(history.len(), 2);
        assert_eq!(history[0].version_number, 2); // Newest first
        assert_eq!(history[1].version_number, 1);
        
        // 8. Compare versions
        let diff_result = version_manager.compare_versions(document.id, 1, 2).await;
        assert!(diff_result.is_ok(), "Version comparison should succeed");
        let diff = diff_result.unwrap();
        assert!(!diff.changes.is_empty(), "Should have detected changes");
        assert!(diff.summary.total_changes > 0);
        
        // 9. Search for document
        let search_query = SearchQuery {
            query: "policy requirements".to_string(),
            document_types: Some(vec![DocumentType::Policy]),
            categories: None,
            tags: None,
            date_range: None,
            visibility_levels: None,
            limit: Some(10),
            offset: Some(0),
            sort_by: Some(SortBy::Relevance),
        };
        
        let search_context = SearchContext {
            user_id: Some(Uuid::new_v4()),
            user_roles: vec!["user".to_string()],
            timestamp: Utc::now(),
            session_id: Some("test_session".to_string()),
        };
        
        let search_result = index_manager.search(
            search_query,
            search_context,
            SearchOptions::default(),
        ).await;
        assert!(search_result.is_ok(), "Search should succeed");
        let results = search_result.unwrap();
        assert!(!results.results.is_empty(), "Should find the document");
        assert_eq!(results.results[0].document_id, document.id);
        
        // 10. Rollback to previous version
        let rollback_result = version_manager.rollback_to_version(
            document.id,
            1,
            Uuid::new_v4(),
        ).await;
        assert!(rollback_result.is_ok(), "Rollback should succeed");
        let rollback_version = rollback_result.unwrap();
        assert_eq!(rollback_version.version, 3);
        assert_eq!(rollback_version.content, initial_version.content);
        
        println!("✅ Complete document lifecycle test passed");
    }

    #[tokio::test]
    async fn test_template_processing_workflow() {
        // Test complete template processing workflow
        
        let mut template_engine = TemplateEngine::new(TemplateEngineConfig::default());
        
        // 1. Create template with variables
        let variables = vec![
            TemplateVariable {
                name: "company_name".to_string(),
                description: "Company name".to_string(),
                variable_type: VariableType::Text,
                required: true,
                default_value: None,
                validation: None,
            },
            TemplateVariable {
                name: "effective_date".to_string(),
                description: "Policy effective date".to_string(),
                variable_type: VariableType::Date,
                required: true,
                default_value: None,
                validation: None,
            },
            TemplateVariable {
                name: "review_frequency".to_string(),
                description: "Review frequency in months".to_string(),
                variable_type: VariableType::Number,
                required: false,
                default_value: Some("12".to_string()),
                validation: None,
            },
        ];
        
        let template_content = r#"
# {{company_name}} Data Protection Policy

**Effective Date:** {{effective_date}}
**Review Frequency:** {{review_frequency}} months

This policy establishes data protection requirements for {{company_name}}.

## 1. Purpose
This policy ensures {{company_name}} complies with applicable data protection regulations.

## 2. Scope
This policy applies to all employees of {{company_name}}.
"#.to_string();
        
        let template_result = template_engine.create_template(
            "Data Protection Policy Template".to_string(),
            "Template for creating data protection policies".to_string(),
            template_content,
            DocumentType::Policy,
            variables,
            TemplateMetadata {
                category: "Data Protection".to_string(),
                tags: vec!["GDPR".to_string(), "Privacy".to_string()],
                usage_instructions: Some("Fill in company details and dates".to_string()),
                preview_image: None,
                complexity_level: ComplexityLevel::Simple,
            },
            Uuid::new_v4(),
        ).await;
        
        assert!(template_result.is_ok(), "Template creation should succeed");
        let template = template_result.unwrap();
        
        // 2. Process template with context
        let mut context = TemplateContext::default();
        context.variables.insert("company_name".to_string(), json!("RegulateAI Corp"));
        context.variables.insert("effective_date".to_string(), json!("2025-01-01"));
        context.variables.insert("review_frequency".to_string(), json!(6));
        
        let process_result = template_engine.process_template(template.id, context).await;
        assert!(process_result.is_ok(), "Template processing should succeed");
        let result = process_result.unwrap();
        
        // 3. Verify processed content
        assert!(result.content.contains("RegulateAI Corp"));
        assert!(result.content.contains("2025-01-01"));
        assert!(result.content.contains("6 months"));
        assert_eq!(result.variables_used.len(), 3);
        assert!(result.warnings.is_empty());
        
        // 4. Test template with missing required variable
        let mut incomplete_context = TemplateContext::default();
        incomplete_context.variables.insert("effective_date".to_string(), json!("2025-01-01"));
        // Missing required company_name
        
        let incomplete_result = template_engine.process_template(template.id, incomplete_context).await;
        assert!(incomplete_result.is_err(), "Should fail with missing required variable");
        
        // 5. Test template listing and filtering
        let filter = crate::templates::TemplateFilter {
            template_type: Some(DocumentType::Policy),
            category: Some("Data Protection".to_string()),
            tags: Some(vec!["GDPR".to_string()]),
            complexity_level: Some(ComplexityLevel::Simple),
        };
        
        let list_result = template_engine.list_templates(filter).await;
        assert!(list_result.is_ok(), "Template listing should succeed");
        let templates = list_result.unwrap();
        assert_eq!(templates.len(), 1);
        assert_eq!(templates[0].id, template.id);
        
        println!("✅ Template processing workflow test passed");
    }

    #[tokio::test]
    async fn test_advanced_search_functionality() {
        // Test advanced search features including facets, filters, and analytics
        
        let mut index_manager = IndexManager::new(IndexConfig::default());
        
        // 1. Create and index multiple documents
        let documents = vec![
            create_test_document("GDPR Compliance Policy", DocumentType::Policy),
            create_test_document("Security Incident Response", DocumentType::Procedure),
            create_test_document("Data Protection Training", DocumentType::Training),
            create_test_document("Privacy Impact Assessment", DocumentType::Template),
            create_test_document("GDPR Article 30 Records", DocumentType::KnowledgeBase),
        ];
        
        for document in &documents {
            let index_result = index_manager.index_document(document).await;
            assert!(index_result.is_ok(), "Document indexing should succeed");
        }
        
        // 2. Test basic search
        let basic_search = SearchQuery {
            query: "GDPR".to_string(),
            document_types: None,
            categories: None,
            tags: None,
            date_range: None,
            visibility_levels: None,
            limit: Some(10),
            offset: Some(0),
            sort_by: Some(SortBy::Relevance),
        };
        
        let search_context = SearchContext {
            user_id: Some(Uuid::new_v4()),
            user_roles: vec!["user".to_string()],
            timestamp: Utc::now(),
            session_id: Some("test_session".to_string()),
        };
        
        let basic_result = index_manager.search(
            basic_search,
            search_context.clone(),
            SearchOptions::default(),
        ).await;
        assert!(basic_result.is_ok(), "Basic search should succeed");
        let basic_results = basic_result.unwrap();
        assert!(basic_results.results.len() >= 2, "Should find GDPR-related documents");
        
        // 3. Test filtered search
        let filtered_search = SearchQuery {
            query: "data".to_string(),
            document_types: Some(vec![DocumentType::Policy, DocumentType::Training]),
            categories: None,
            tags: None,
            date_range: None,
            visibility_levels: None,
            limit: Some(10),
            offset: Some(0),
            sort_by: Some(SortBy::Title),
        };
        
        let filtered_result = index_manager.search(
            filtered_search,
            search_context.clone(),
            SearchOptions::default(),
        ).await;
        assert!(filtered_result.is_ok(), "Filtered search should succeed");
        let filtered_results = filtered_result.unwrap();
        
        // Verify only Policy and Training documents are returned
        for result in &filtered_results.results {
            assert!(matches!(result.document_type, DocumentType::Policy | DocumentType::Training));
        }
        
        // 4. Test fuzzy search
        let mut fuzzy_options = SearchOptions::default();
        fuzzy_options.fuzzy_matching = true;
        fuzzy_options.fuzzy_distance = 2;
        
        let fuzzy_search = SearchQuery {
            query: "complience".to_string(), // Misspelled "compliance"
            document_types: None,
            categories: None,
            tags: None,
            date_range: None,
            visibility_levels: None,
            limit: Some(10),
            offset: Some(0),
            sort_by: Some(SortBy::Relevance),
        };
        
        let fuzzy_result = index_manager.search(
            fuzzy_search,
            search_context.clone(),
            fuzzy_options,
        ).await;
        assert!(fuzzy_result.is_ok(), "Fuzzy search should succeed");
        let fuzzy_results = fuzzy_result.unwrap();
        assert!(!fuzzy_results.results.is_empty(), "Should find documents despite misspelling");
        
        // 5. Test search suggestions
        let suggestions_result = index_manager.get_suggestions("comp", 5).await;
        assert!(suggestions_result.is_ok(), "Suggestions should succeed");
        let suggestions = suggestions_result.unwrap();
        assert!(!suggestions.is_empty(), "Should provide suggestions");
        
        // 6. Test search analytics
        let analytics = index_manager.get_analytics().await;
        assert!(analytics.total_queries > 0, "Should have recorded queries");
        assert!(!analytics.popular_terms.is_empty(), "Should have popular terms");
        
        println!("✅ Advanced search functionality test passed");
    }

    #[tokio::test]
    async fn test_version_control_branching() {
        // Test advanced version control features including branching and merging
        
        let mut version_manager = VersionManager::new(VersionConfig {
            enable_branching: true,
            ..VersionConfig::default()
        });
        
        let document = create_test_document("Branching Test Policy", DocumentType::Policy);
        let user_id = Uuid::new_v4();
        
        // 1. Create initial version
        let initial_version = version_manager.create_version(
            &document,
            "Initial version".to_string(),
            user_id,
        ).await.unwrap();
        
        // 2. Create a branch from initial version
        let branch_result = version_manager.create_branch(
            document.id,
            "feature-branch".to_string(),
            initial_version.version,
            user_id,
        ).await;
        assert!(branch_result.is_ok(), "Branch creation should succeed");
        let branch = branch_result.unwrap();
        assert_eq!(branch.name, "feature-branch");
        assert_eq!(branch.branch_point_version_id, initial_version.id);
        
        // 3. Create another version on main branch
        let mut updated_document = document.clone();
        updated_document.content = "Main branch update".to_string();
        
        let main_version = version_manager.create_version(
            &updated_document,
            "Main branch update".to_string(),
            user_id,
        ).await.unwrap();
        assert_eq!(main_version.version, 2);
        
        // 4. Test merge operation
        let target_branch_id = Uuid::new_v4(); // Simulated target branch
        let merge_result = version_manager.merge_branches(
            branch.id,
            target_branch_id,
            user_id,
        ).await;
        assert!(merge_result.is_ok(), "Merge should succeed");
        let merge = merge_result.unwrap();
        assert_eq!(merge.source_branch_id, branch.id);
        assert_eq!(merge.target_branch_id, target_branch_id);
        
        // 5. Test version history after branching
        let history = version_manager.get_version_history(document.id).await.unwrap();
        assert_eq!(history.len(), 2); // Initial + main branch update
        
        println!("✅ Version control branching test passed");
    }

    #[tokio::test]
    async fn test_document_permissions_and_visibility() {
        // Test document visibility and permission controls
        
        let mut index_manager = IndexManager::new(IndexConfig::default());
        
        // 1. Create documents with different visibility levels
        let public_doc = create_document_with_visibility("Public Document", VisibilityLevel::Public);
        let internal_doc = create_document_with_visibility("Internal Document", VisibilityLevel::Internal);
        let restricted_doc = create_document_with_visibility("Restricted Document", VisibilityLevel::Restricted);
        let confidential_doc = create_document_with_visibility("Confidential Document", VisibilityLevel::Confidential);
        
        // Index all documents
        for doc in &[&public_doc, &internal_doc, &restricted_doc, &confidential_doc] {
            index_manager.index_document(doc).await.unwrap();
        }
        
        // 2. Test search as anonymous user (no user_id)
        let anonymous_context = SearchContext {
            user_id: None,
            user_roles: vec![],
            timestamp: Utc::now(),
            session_id: Some("anonymous_session".to_string()),
        };
        
        let anonymous_search = SearchQuery {
            query: "document".to_string(),
            document_types: None,
            categories: None,
            tags: None,
            date_range: None,
            visibility_levels: None,
            limit: Some(10),
            offset: Some(0),
            sort_by: Some(SortBy::Title),
        };
        
        let anonymous_results = index_manager.search(
            anonymous_search,
            anonymous_context,
            SearchOptions::default(),
        ).await.unwrap();
        
        // Should only see public documents
        assert_eq!(anonymous_results.results.len(), 1);
        assert_eq!(anonymous_results.results[0].document_id, public_doc.id);
        
        // 3. Test search as regular user
        let user_context = SearchContext {
            user_id: Some(Uuid::new_v4()),
            user_roles: vec!["user".to_string()],
            timestamp: Utc::now(),
            session_id: Some("user_session".to_string()),
        };
        
        let user_results = index_manager.search(
            SearchQuery {
                query: "document".to_string(),
                document_types: None,
                categories: None,
                tags: None,
                date_range: None,
                visibility_levels: None,
                limit: Some(10),
                offset: Some(0),
                sort_by: Some(SortBy::Title),
            },
            user_context,
            SearchOptions::default(),
        ).await.unwrap();
        
        // Should see public and internal documents
        assert_eq!(user_results.results.len(), 2);
        let visible_ids: Vec<_> = user_results.results.iter().map(|r| r.document_id).collect();
        assert!(visible_ids.contains(&public_doc.id));
        assert!(visible_ids.contains(&internal_doc.id));
        
        // 4. Test search as privileged user
        let privileged_context = SearchContext {
            user_id: Some(Uuid::new_v4()),
            user_roles: vec!["user".to_string(), "restricted_access".to_string(), "confidential_access".to_string()],
            timestamp: Utc::now(),
            session_id: Some("privileged_session".to_string()),
        };
        
        let privileged_results = index_manager.search(
            SearchQuery {
                query: "document".to_string(),
                document_types: None,
                categories: None,
                tags: None,
                date_range: None,
                visibility_levels: None,
                limit: Some(10),
                offset: Some(0),
                sort_by: Some(SortBy::Title),
            },
            privileged_context,
            SearchOptions::default(),
        ).await.unwrap();
        
        // Should see all documents
        assert_eq!(privileged_results.results.len(), 4);
        
        println!("✅ Document permissions and visibility test passed");
    }

    #[tokio::test]
    async fn test_performance_and_scalability() {
        // Test performance with larger datasets
        
        let mut index_manager = IndexManager::new(IndexConfig::default());
        let mut version_manager = VersionManager::new(VersionConfig::default());
        
        let start_time = std::time::Instant::now();
        
        // 1. Create and index 100 documents
        let mut documents = Vec::new();
        for i in 0..100 {
            let doc = create_test_document(
                &format!("Performance Test Document {}", i),
                if i % 3 == 0 { DocumentType::Policy } else if i % 3 == 1 { DocumentType::Procedure } else { DocumentType::Training }
            );
            documents.push(doc);
        }
        
        // Index all documents
        for doc in &documents {
            index_manager.index_document(doc).await.unwrap();
        }
        
        let indexing_time = start_time.elapsed();
        println!("Indexed 100 documents in {:?}", indexing_time);
        assert!(indexing_time.as_secs() < 5, "Indexing should be fast");
        
        // 2. Create versions for documents
        let versioning_start = std::time::Instant::now();
        for doc in documents.iter().take(20) { // Version first 20 documents
            version_manager.create_version(
                doc,
                "Performance test version".to_string(),
                Uuid::new_v4(),
            ).await.unwrap();
        }
        
        let versioning_time = versioning_start.elapsed();
        println!("Created 20 versions in {:?}", versioning_time);
        assert!(versioning_time.as_secs() < 2, "Versioning should be fast");
        
        // 3. Perform multiple searches
        let search_start = std::time::Instant::now();
        let search_context = SearchContext {
            user_id: Some(Uuid::new_v4()),
            user_roles: vec!["user".to_string()],
            timestamp: Utc::now(),
            session_id: Some("perf_session".to_string()),
        };
        
        for i in 0..50 {
            let search_query = SearchQuery {
                query: format!("test document {}", i % 10),
                document_types: None,
                categories: None,
                tags: None,
                date_range: None,
                visibility_levels: None,
                limit: Some(10),
                offset: Some(0),
                sort_by: Some(SortBy::Relevance),
            };
            
            let result = index_manager.search(
                search_query,
                search_context.clone(),
                SearchOptions::default(),
            ).await;
            assert!(result.is_ok(), "Search {} should succeed", i);
        }
        
        let search_time = search_start.elapsed();
        println!("Performed 50 searches in {:?}", search_time);
        assert!(search_time.as_secs() < 3, "Searches should be fast");
        
        // 4. Test analytics performance
        let analytics = index_manager.get_analytics().await;
        assert_eq!(analytics.total_queries, 50);
        assert!(analytics.avg_query_time_ms < 100.0, "Average query time should be reasonable");
        
        println!("✅ Performance and scalability test passed");
    }

    // Helper functions
    fn create_test_document(title: &str, doc_type: DocumentType) -> Document {
        Document {
            id: Uuid::new_v4(),
            title: title.to_string(),
            slug: title.to_lowercase().replace(" ", "-"),
            content: format!("This is the content for {}. It contains important information about compliance and regulatory requirements.", title),
            document_type: doc_type,
            category: "Compliance".to_string(),
            tags: vec!["test".to_string(), "compliance".to_string()],
            status: DocumentStatus::Published,
            visibility: VisibilityLevel::Internal,
            metadata: DocumentMetadata::default(),
            version: 1,
            parent_id: None,
            sort_order: 0,
            language: "en".to_string(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            published_at: Some(Utc::now()),
            created_by: Uuid::new_v4(),
            updated_by: Uuid::new_v4(),
            approval: None,
        }
    }
    
    fn create_document_with_visibility(title: &str, visibility: VisibilityLevel) -> Document {
        let mut doc = create_test_document(title, DocumentType::Policy);
        doc.visibility = visibility;
        doc
    }
}

// =============================================================================
// UNIT TESTS FOR INDIVIDUAL MODULES
// =============================================================================

#[cfg(test)]
mod unit_tests {
    use super::*;

    #[tokio::test]
    async fn test_template_variable_validation() {
        let template_engine = TemplateEngine::new(TemplateEngineConfig::default());
        
        // Test text variable validation
        let text_processor = crate::templates::TextProcessor;
        let valid_text = json!("Valid text content");
        let result = text_processor.process(&valid_text, None);
        assert!(result.is_ok());
        
        // Test number variable validation
        let number_processor = crate::templates::NumberProcessor;
        let valid_number = json!(42.5);
        let result = number_processor.process(&valid_number, None);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "42.5");
        
        // Test invalid number
        let invalid_number = json!("not a number");
        let result = number_processor.process(&invalid_number, None);
        assert!(result.is_err());
        
        println!("✅ Template variable validation test passed");
    }

    #[tokio::test]
    async fn test_version_diff_calculation() {
        let version_manager = VersionManager::new(VersionConfig::default());
        let diff_engine = &version_manager.diff_engine;
        
        // Create two versions with different content
        let version1 = crate::models::DocumentVersion {
            id: Uuid::new_v4(),
            document_id: Uuid::new_v4(),
            version: 1,
            content: "Line 1\nLine 2\nLine 3".to_string(),
            metadata: DocumentMetadata::default(),
            change_summary: "Initial version".to_string(),
            created_at: Utc::now(),
            created_by: Uuid::new_v4(),
            is_current: false,
        };
        
        let version2 = crate::models::DocumentVersion {
            id: Uuid::new_v4(),
            document_id: version1.document_id,
            version: 2,
            content: "Line 1\nModified Line 2\nLine 3\nNew Line 4".to_string(),
            metadata: DocumentMetadata::default(),
            change_summary: "Modified content".to_string(),
            created_at: Utc::now(),
            created_by: Uuid::new_v4(),
            is_current: true,
        };
        
        let diff_result = diff_engine.compare(&version1, &version2).await;
        assert!(diff_result.is_ok());
        
        let diff = diff_result.unwrap();
        assert!(!diff.changes.is_empty());
        assert!(diff.summary.total_changes > 0);
        assert!(diff.summary.lines_added > 0);
        assert!(diff.summary.lines_modified > 0);
        
        println!("✅ Version diff calculation test passed");
    }

    #[tokio::test]
    async fn test_search_index_operations() {
        let mut index_manager = IndexManager::new(IndexConfig::default());
        
        let document = create_test_document("Search Test Document", DocumentType::Policy);
        
        // Test indexing
        let index_result = index_manager.index_document(&document).await;
        assert!(index_result.is_ok());
        
        // Test search
        let search_query = SearchQuery {
            query: "search test".to_string(),
            document_types: None,
            categories: None,
            tags: None,
            date_range: None,
            visibility_levels: None,
            limit: Some(10),
            offset: Some(0),
            sort_by: Some(SortBy::Relevance),
        };
        
        let search_context = SearchContext {
            user_id: Some(Uuid::new_v4()),
            user_roles: vec!["user".to_string()],
            timestamp: Utc::now(),
            session_id: Some("test_session".to_string()),
        };
        
        let search_result = index_manager.search(
            search_query,
            search_context,
            SearchOptions::default(),
        ).await;
        
        assert!(search_result.is_ok());
        let results = search_result.unwrap();
        assert!(!results.results.is_empty());
        assert_eq!(results.results[0].document_id, document.id);
        
        // Test document removal
        let remove_result = index_manager.remove_document_index(document.id).await;
        assert!(remove_result.is_ok());
        
        println!("✅ Search index operations test passed");
    }

    fn create_test_document(title: &str, doc_type: DocumentType) -> Document {
        Document {
            id: Uuid::new_v4(),
            title: title.to_string(),
            slug: title.to_lowercase().replace(" ", "-"),
            content: format!("This is the content for {}. It contains important information.", title),
            document_type: doc_type,
            category: "Test".to_string(),
            tags: vec!["test".to_string()],
            status: DocumentStatus::Published,
            visibility: VisibilityLevel::Internal,
            metadata: DocumentMetadata::default(),
            version: 1,
            parent_id: None,
            sort_order: 0,
            language: "en".to_string(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            published_at: Some(Utc::now()),
            created_by: Uuid::new_v4(),
            updated_by: Uuid::new_v4(),
            approval: None,
        }
    }
}
