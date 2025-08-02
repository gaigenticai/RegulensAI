//! Document Indexing and Search Module
//! 
//! This module provides comprehensive document indexing and search capabilities including:
//! - Full-text search indexing with advanced text processing
//! - Semantic search with vector embeddings
//! - Faceted search with filters and aggregations
//! - Real-time index updates and maintenance
//! - Search analytics and query optimization

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use tracing::{info, warn, error, debug};

use regulateai_errors::RegulateAIError;
use crate::models::{
    Document, SearchIndex, SearchQuery, SearchResult, DocumentType, 
    VisibilityLevel, SortBy, DateRange,
};

/// Search index manager
pub struct IndexManager {
    /// Document indexes
    indexes: HashMap<Uuid, SearchIndex>,
    
    /// Inverted index for full-text search
    inverted_index: HashMap<String, Vec<Uuid>>,
    
    /// Index configuration
    config: IndexConfig,
    
    /// Text processor for content analysis
    text_processor: TextProcessor,
    
    /// Search analytics
    analytics: SearchAnalytics,
}

/// Index configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexConfig {
    /// Enable full-text search
    pub enable_fulltext: bool,
    
    /// Enable semantic search
    pub enable_semantic: bool,
    
    /// Minimum word length for indexing
    pub min_word_length: usize,
    
    /// Maximum word length for indexing
    pub max_word_length: usize,
    
    /// Stop words to exclude from indexing
    pub stop_words: Vec<String>,
    
    /// Enable stemming
    pub enable_stemming: bool,
    
    /// Index update batch size
    pub batch_size: usize,
    
    /// Search result limit
    pub max_results: usize,
}

/// Text processor for content analysis
pub struct TextProcessor {
    /// Processing configuration
    config: TextProcessingConfig,
    
    /// Stop words set
    stop_words: std::collections::HashSet<String>,
}

/// Text processing configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextProcessingConfig {
    /// Enable tokenization
    pub enable_tokenization: bool,
    
    /// Enable normalization
    pub enable_normalization: bool,
    
    /// Enable stop word removal
    pub enable_stop_word_removal: bool,
    
    /// Enable stemming
    pub enable_stemming: bool,
    
    /// Language for processing
    pub language: String,
}

/// Search analytics tracker
#[derive(Debug, Clone)]
pub struct SearchAnalytics {
    /// Query statistics
    query_stats: HashMap<String, QueryStats>,
    
    /// Popular search terms
    popular_terms: HashMap<String, u64>,
    
    /// Search performance metrics
    performance_metrics: PerformanceMetrics,
}

/// Query statistics
#[derive(Debug, Clone)]
pub struct QueryStats {
    /// Query count
    pub count: u64,
    
    /// Average response time
    pub avg_response_time_ms: f64,
    
    /// Average result count
    pub avg_result_count: f64,
    
    /// Last executed timestamp
    pub last_executed: DateTime<Utc>,
}

/// Performance metrics
#[derive(Debug, Clone)]
pub struct PerformanceMetrics {
    /// Total queries executed
    pub total_queries: u64,
    
    /// Average query time
    pub avg_query_time_ms: f64,
    
    /// Index size in bytes
    pub index_size_bytes: u64,
    
    /// Last updated timestamp
    pub last_updated: DateTime<Utc>,
}

/// Search execution context
#[derive(Debug, Clone)]
pub struct SearchContext {
    /// User ID performing search
    pub user_id: Option<Uuid>,
    
    /// User roles for permission filtering
    pub user_roles: Vec<String>,
    
    /// Search timestamp
    pub timestamp: DateTime<Utc>,
    
    /// Search session ID
    pub session_id: Option<String>,
}

/// Advanced search options
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchOptions {
    /// Enable fuzzy matching
    pub fuzzy_matching: bool,
    
    /// Fuzzy matching distance
    pub fuzzy_distance: usize,
    
    /// Enable phrase matching
    pub phrase_matching: bool,
    
    /// Enable wildcard matching
    pub wildcard_matching: bool,
    
    /// Boost factors for different fields
    pub field_boosts: HashMap<String, f64>,
    
    /// Enable highlighting
    pub enable_highlighting: bool,
    
    /// Highlight fragment size
    pub highlight_fragment_size: usize,
}

impl IndexManager {
    /// Create a new index manager
    pub fn new(config: IndexConfig) -> Self {
        let text_processor = TextProcessor::new(TextProcessingConfig::default());
        
        Self {
            indexes: HashMap::new(),
            inverted_index: HashMap::new(),
            config,
            text_processor,
            analytics: SearchAnalytics::new(),
        }
    }
    
    /// Index a document
    pub async fn index_document(&mut self, document: &Document) -> Result<(), RegulateAIError> {
        info!("Indexing document: {} ({})", document.title, document.id);
        
        // Process document content
        let processed_content = self.text_processor.process(&document.content)?;
        let keywords = self.text_processor.extract_keywords(&document.content)?;
        let summary = self.text_processor.generate_summary(&document.content, 200)?;
        
        // Create search index entry
        let search_index = SearchIndex {
            id: Uuid::new_v4(),
            document_id: document.id,
            indexed_content: processed_content.clone(),
            keywords: keywords.clone(),
            title: document.title.clone(),
            summary,
            document_type: document.document_type.clone(),
            category: document.category.clone(),
            tags: document.tags.clone(),
            visibility: document.visibility.clone(),
            indexed_at: Utc::now(),
            updated_at: Utc::now(),
        };
        
        // Update inverted index
        self.update_inverted_index(&search_index, &keywords)?;
        
        // Store index
        self.indexes.insert(document.id, search_index);
        
        info!("Document indexed successfully: {}", document.id);
        Ok(())
    }
    
    /// Update document index
    pub async fn update_document_index(&mut self, document: &Document) -> Result<(), RegulateAIError> {
        info!("Updating index for document: {}", document.id);
        
        // Remove old index
        if let Some(old_index) = self.indexes.get(&document.id) {
            self.remove_from_inverted_index(old_index)?;
        }
        
        // Re-index document
        self.index_document(document).await?;
        
        Ok(())
    }
    
    /// Remove document from index
    pub async fn remove_document_index(&mut self, document_id: Uuid) -> Result<(), RegulateAIError> {
        info!("Removing document from index: {}", document_id);
        
        if let Some(index) = self.indexes.remove(&document_id) {
            self.remove_from_inverted_index(&index)?;
            info!("Document removed from index: {}", document_id);
        }
        
        Ok(())
    }
    
    /// Search documents
    pub async fn search(
        &mut self,
        query: SearchQuery,
        context: SearchContext,
        options: SearchOptions,
    ) -> Result<SearchResults, RegulateAIError> {
        let start_time = std::time::Instant::now();
        
        info!("Executing search query: '{}'", query.query);
        
        // Process search query
        let processed_query = self.text_processor.process(&query.query)?;
        let query_terms = self.text_processor.tokenize(&processed_query)?;
        
        // Find matching documents
        let mut candidate_documents = self.find_candidate_documents(&query_terms, &options)?;
        
        // Apply filters
        candidate_documents = self.apply_filters(candidate_documents, &query, &context)?;
        
        // Score and rank results
        let mut scored_results = self.score_results(candidate_documents, &query_terms, &options)?;
        
        // Sort results
        self.sort_results(&mut scored_results, query.sort_by.as_ref())?;
        
        // Apply pagination
        let total_results = scored_results.len();
        let offset = query.offset.unwrap_or(0);
        let limit = query.limit.unwrap_or(self.config.max_results).min(self.config.max_results);
        
        let paginated_results: Vec<SearchResult> = scored_results
            .into_iter()
            .skip(offset)
            .take(limit)
            .collect();
        
        let search_time = start_time.elapsed().as_millis() as u64;
        
        // Update analytics
        self.analytics.record_query(&query.query, search_time, total_results);
        
        let results = SearchResults {
            results: paginated_results,
            total_results,
            query: query.query.clone(),
            search_time_ms: search_time,
            offset,
            limit,
            facets: self.compute_facets(&query)?,
        };
        
        info!("Search completed: {} results in {}ms", total_results, search_time);
        Ok(results)
    }
    
    /// Get search suggestions
    pub async fn get_suggestions(&self, partial_query: &str, limit: usize) -> Result<Vec<String>, RegulateAIError> {
        let suggestions = self.analytics.get_popular_terms()
            .into_iter()
            .filter(|(term, _)| term.starts_with(&partial_query.to_lowercase()))
            .take(limit)
            .map(|(term, _)| term)
            .collect();
        
        Ok(suggestions)
    }
    
    /// Get search analytics
    pub async fn get_analytics(&self) -> SearchAnalyticsReport {
        SearchAnalyticsReport {
            total_queries: self.analytics.performance_metrics.total_queries,
            avg_query_time_ms: self.analytics.performance_metrics.avg_query_time_ms,
            popular_terms: self.analytics.get_popular_terms(),
            index_size_bytes: self.analytics.performance_metrics.index_size_bytes,
            last_updated: self.analytics.performance_metrics.last_updated,
        }
    }
    
    /// Rebuild entire search index
    pub async fn rebuild_index(&mut self, documents: Vec<Document>) -> Result<(), RegulateAIError> {
        info!("Rebuilding search index for {} documents", documents.len());
        
        // Clear existing indexes
        self.indexes.clear();
        self.inverted_index.clear();
        
        // Re-index all documents
        for document in documents {
            self.index_document(&document).await?;
        }
        
        info!("Search index rebuilt successfully");
        Ok(())
    }
    
    // Helper methods
    
    /// Update inverted index with document keywords
    fn update_inverted_index(&mut self, index: &SearchIndex, keywords: &[String]) -> Result<(), RegulateAIError> {
        for keyword in keywords {
            self.inverted_index
                .entry(keyword.clone())
                .or_insert_with(Vec::new)
                .push(index.document_id);
        }
        Ok(())
    }
    
    /// Remove document from inverted index
    fn remove_from_inverted_index(&mut self, index: &SearchIndex) -> Result<(), RegulateAIError> {
        for keyword in &index.keywords {
            if let Some(doc_list) = self.inverted_index.get_mut(keyword) {
                doc_list.retain(|&id| id != index.document_id);
                if doc_list.is_empty() {
                    self.inverted_index.remove(keyword);
                }
            }
        }
        Ok(())
    }
    
    /// Find candidate documents based on query terms
    fn find_candidate_documents(&self, query_terms: &[String], options: &SearchOptions) -> Result<Vec<Uuid>, RegulateAIError> {
        let mut candidates = std::collections::HashSet::new();
        
        for term in query_terms {
            // Exact matches
            if let Some(doc_ids) = self.inverted_index.get(term) {
                candidates.extend(doc_ids);
            }
            
            // Fuzzy matches if enabled
            if options.fuzzy_matching {
                for (indexed_term, doc_ids) in &self.inverted_index {
                    if self.is_fuzzy_match(term, indexed_term, options.fuzzy_distance) {
                        candidates.extend(doc_ids);
                    }
                }
            }
        }
        
        Ok(candidates.into_iter().collect())
    }
    
    /// Apply search filters
    fn apply_filters(
        &self,
        candidates: Vec<Uuid>,
        query: &SearchQuery,
        context: &SearchContext,
    ) -> Result<Vec<Uuid>, RegulateAIError> {
        let mut filtered = candidates;
        
        // Filter by document type
        if let Some(doc_types) = &query.document_types {
            filtered.retain(|&doc_id| {
                if let Some(index) = self.indexes.get(&doc_id) {
                    doc_types.contains(&index.document_type)
                } else {
                    false
                }
            });
        }
        
        // Filter by category
        if let Some(categories) = &query.categories {
            filtered.retain(|&doc_id| {
                if let Some(index) = self.indexes.get(&doc_id) {
                    categories.contains(&index.category)
                } else {
                    false
                }
            });
        }
        
        // Filter by tags
        if let Some(tags) = &query.tags {
            filtered.retain(|&doc_id| {
                if let Some(index) = self.indexes.get(&doc_id) {
                    tags.iter().any(|tag| index.tags.contains(tag))
                } else {
                    false
                }
            });
        }
        
        // Filter by visibility (based on user permissions)
        filtered.retain(|&doc_id| {
            if let Some(index) = self.indexes.get(&doc_id) {
                self.check_visibility_permission(&index.visibility, context)
            } else {
                false
            }
        });
        
        Ok(filtered)
    }
    
    /// Score and rank search results
    fn score_results(
        &self,
        candidates: Vec<Uuid>,
        query_terms: &[String],
        options: &SearchOptions,
    ) -> Result<Vec<SearchResult>, RegulateAIError> {
        let mut results = Vec::new();
        
        for doc_id in candidates {
            if let Some(index) = self.indexes.get(&doc_id) {
                let relevance_score = self.calculate_relevance_score(index, query_terms, options);
                let highlights = if options.enable_highlighting {
                    self.generate_highlights(&index.indexed_content, query_terms, options.highlight_fragment_size)
                } else {
                    Vec::new()
                };
                
                results.push(SearchResult {
                    document_id: doc_id,
                    title: index.title.clone(),
                    summary: index.summary.clone(),
                    document_type: index.document_type.clone(),
                    category: index.category.clone(),
                    tags: index.tags.clone(),
                    relevance_score,
                    highlights,
                    url: format!("/documents/{}", doc_id),
                    updated_at: index.updated_at,
                });
            }
        }
        
        Ok(results)
    }
    
    /// Calculate relevance score for a document
    fn calculate_relevance_score(&self, index: &SearchIndex, query_terms: &[String], options: &SearchOptions) -> f64 {
        let mut score = 0.0;
        
        // Term frequency scoring
        for term in query_terms {
            let tf = self.calculate_term_frequency(&index.indexed_content, term);
            score += tf;
            
            // Title boost
            if index.title.to_lowercase().contains(&term.to_lowercase()) {
                score += options.field_boosts.get("title").unwrap_or(&2.0);
            }
            
            // Keywords boost
            if index.keywords.iter().any(|k| k.to_lowercase().contains(&term.to_lowercase())) {
                score += options.field_boosts.get("keywords").unwrap_or(&1.5);
            }
        }
        
        // Document type boost
        score *= options.field_boosts.get(&format!("{:?}", index.document_type)).unwrap_or(&1.0);
        
        score
    }
    
    /// Calculate term frequency in content
    fn calculate_term_frequency(&self, content: &str, term: &str) -> f64 {
        let content_lower = content.to_lowercase();
        let term_lower = term.to_lowercase();
        let matches = content_lower.matches(&term_lower).count();
        let total_words = content_lower.split_whitespace().count();
        
        if total_words > 0 {
            matches as f64 / total_words as f64
        } else {
            0.0
        }
    }
    
    /// Generate highlighted text snippets
    fn generate_highlights(&self, content: &str, query_terms: &[String], fragment_size: usize) -> Vec<String> {
        let mut highlights = Vec::new();
        
        for term in query_terms {
            if let Some(pos) = content.to_lowercase().find(&term.to_lowercase()) {
                let start = pos.saturating_sub(fragment_size / 2);
                let end = (pos + term.len() + fragment_size / 2).min(content.len());
                let fragment = &content[start..end];
                
                // Highlight the term
                let highlighted = fragment.replace(term, &format!("<mark>{}</mark>", term));
                highlights.push(format!("...{}...", highlighted));
            }
        }
        
        highlights
    }
    
    /// Sort search results
    fn sort_results(&self, results: &mut [SearchResult], sort_by: Option<&SortBy>) -> Result<(), RegulateAIError> {
        match sort_by.unwrap_or(&SortBy::Relevance) {
            SortBy::Relevance => {
                results.sort_by(|a, b| b.relevance_score.partial_cmp(&a.relevance_score).unwrap());
            }
            SortBy::CreatedDate | SortBy::UpdatedDate => {
                results.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
            }
            SortBy::Title => {
                results.sort_by(|a, b| a.title.cmp(&b.title));
            }
            SortBy::Category => {
                results.sort_by(|a, b| a.category.cmp(&b.category));
            }
        }
        
        Ok(())
    }
    
    /// Compute search facets
    fn compute_facets(&self, query: &SearchQuery) -> Result<HashMap<String, Vec<FacetValue>>, RegulateAIError> {
        let mut facets = HashMap::new();
        
        // Document type facets
        let mut doc_type_counts = HashMap::new();
        for index in self.indexes.values() {
            *doc_type_counts.entry(format!("{:?}", index.document_type)).or_insert(0) += 1;
        }
        
        let doc_type_facets: Vec<FacetValue> = doc_type_counts.into_iter()
            .map(|(value, count)| FacetValue { value, count })
            .collect();
        facets.insert("document_type".to_string(), doc_type_facets);
        
        // Category facets
        let mut category_counts = HashMap::new();
        for index in self.indexes.values() {
            *category_counts.entry(index.category.clone()).or_insert(0) += 1;
        }
        
        let category_facets: Vec<FacetValue> = category_counts.into_iter()
            .map(|(value, count)| FacetValue { value, count })
            .collect();
        facets.insert("category".to_string(), category_facets);
        
        Ok(facets)
    }
    
    /// Check if user has permission to view document with given visibility
    fn check_visibility_permission(&self, visibility: &VisibilityLevel, context: &SearchContext) -> bool {
        match visibility {
            VisibilityLevel::Public => true,
            VisibilityLevel::Internal => context.user_id.is_some(),
            VisibilityLevel::Restricted => context.user_roles.contains(&"restricted_access".to_string()),
            VisibilityLevel::Confidential => context.user_roles.contains(&"confidential_access".to_string()),
        }
    }
    
    /// Check if two terms are fuzzy matches
    fn is_fuzzy_match(&self, term1: &str, term2: &str, max_distance: usize) -> bool {
        self.levenshtein_distance(term1, term2) <= max_distance
    }
    
    /// Calculate Levenshtein distance between two strings
    fn levenshtein_distance(&self, s1: &str, s2: &str) -> usize {
        let len1 = s1.len();
        let len2 = s2.len();
        let mut matrix = vec![vec![0; len2 + 1]; len1 + 1];
        
        for i in 0..=len1 {
            matrix[i][0] = i;
        }
        for j in 0..=len2 {
            matrix[0][j] = j;
        }
        
        for (i, c1) in s1.chars().enumerate() {
            for (j, c2) in s2.chars().enumerate() {
                let cost = if c1 == c2 { 0 } else { 1 };
                matrix[i + 1][j + 1] = std::cmp::min(
                    std::cmp::min(matrix[i][j + 1] + 1, matrix[i + 1][j] + 1),
                    matrix[i][j] + cost,
                );
            }
        }
        
        matrix[len1][len2]
    }
}

impl TextProcessor {
    /// Create a new text processor
    pub fn new(config: TextProcessingConfig) -> Self {
        let stop_words = Self::load_stop_words(&config.language);
        
        Self {
            config,
            stop_words,
        }
    }
    
    /// Process text content for indexing
    pub fn process(&self, content: &str) -> Result<String, RegulateAIError> {
        let mut processed = content.to_lowercase();
        
        if self.config.enable_normalization {
            processed = self.normalize(&processed);
        }
        
        Ok(processed)
    }
    
    /// Extract keywords from content
    pub fn extract_keywords(&self, content: &str) -> Result<Vec<String>, RegulateAIError> {
        let tokens = self.tokenize(content)?;
        let mut keywords = Vec::new();
        
        for token in tokens {
            if token.len() >= 3 && !self.stop_words.contains(&token) {
                keywords.push(token);
            }
        }
        
        // Remove duplicates
        keywords.sort();
        keywords.dedup();
        
        Ok(keywords)
    }
    
    /// Generate summary from content
    pub fn generate_summary(&self, content: &str, max_length: usize) -> Result<String, RegulateAIError> {
        if content.len() <= max_length {
            return Ok(content.to_string());
        }
        
        // Simple extractive summarization - take first sentences up to max_length
        let sentences: Vec<&str> = content.split('.').collect();
        let mut summary = String::new();
        
        for sentence in sentences {
            if summary.len() + sentence.len() + 1 <= max_length {
                if !summary.is_empty() {
                    summary.push('.');
                }
                summary.push_str(sentence.trim());
            } else {
                break;
            }
        }
        
        if summary.len() < content.len() {
            summary.push_str("...");
        }
        
        Ok(summary)
    }
    
    /// Tokenize text into words
    pub fn tokenize(&self, text: &str) -> Result<Vec<String>, RegulateAIError> {
        let tokens: Vec<String> = text
            .split_whitespace()
            .map(|word| word.trim_matches(|c: char| !c.is_alphanumeric()).to_lowercase())
            .filter(|word| !word.is_empty())
            .collect();
        
        Ok(tokens)
    }
    
    /// Normalize text
    fn normalize(&self, text: &str) -> String {
        // Remove extra whitespace and normalize
        text.split_whitespace().collect::<Vec<_>>().join(" ")
    }
    
    /// Load stop words for language
    fn load_stop_words(language: &str) -> std::collections::HashSet<String> {
        // English stop words
        let stop_words = vec![
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "will", "with", "the", "this", "but", "they", "have",
            "had", "what", "said", "each", "which", "she", "do", "how", "their",
        ];
        
        stop_words.into_iter().map(|s| s.to_string()).collect()
    }
}

impl SearchAnalytics {
    /// Create new search analytics
    pub fn new() -> Self {
        Self {
            query_stats: HashMap::new(),
            popular_terms: HashMap::new(),
            performance_metrics: PerformanceMetrics {
                total_queries: 0,
                avg_query_time_ms: 0.0,
                index_size_bytes: 0,
                last_updated: Utc::now(),
            },
        }
    }
    
    /// Record a search query
    pub fn record_query(&mut self, query: &str, response_time_ms: u64, result_count: usize) {
        // Update query stats
        let stats = self.query_stats.entry(query.to_string()).or_insert(QueryStats {
            count: 0,
            avg_response_time_ms: 0.0,
            avg_result_count: 0.0,
            last_executed: Utc::now(),
        });
        
        stats.count += 1;
        stats.avg_response_time_ms = (stats.avg_response_time_ms * (stats.count - 1) as f64 + response_time_ms as f64) / stats.count as f64;
        stats.avg_result_count = (stats.avg_result_count * (stats.count - 1) as f64 + result_count as f64) / stats.count as f64;
        stats.last_executed = Utc::now();
        
        // Update popular terms
        for term in query.split_whitespace() {
            *self.popular_terms.entry(term.to_lowercase()).or_insert(0) += 1;
        }
        
        // Update performance metrics
        self.performance_metrics.total_queries += 1;
        self.performance_metrics.avg_query_time_ms = 
            (self.performance_metrics.avg_query_time_ms * (self.performance_metrics.total_queries - 1) as f64 + response_time_ms as f64) 
            / self.performance_metrics.total_queries as f64;
        self.performance_metrics.last_updated = Utc::now();
    }
    
    /// Get popular search terms
    pub fn get_popular_terms(&self) -> Vec<(String, u64)> {
        let mut terms: Vec<_> = self.popular_terms.iter()
            .map(|(term, count)| (term.clone(), *count))
            .collect();
        terms.sort_by(|a, b| b.1.cmp(&a.1));
        terms.truncate(20); // Top 20 terms
        terms
    }
}

/// Search results container
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResults {
    pub results: Vec<SearchResult>,
    pub total_results: usize,
    pub query: String,
    pub search_time_ms: u64,
    pub offset: usize,
    pub limit: usize,
    pub facets: HashMap<String, Vec<FacetValue>>,
}

/// Facet value with count
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FacetValue {
    pub value: String,
    pub count: u64,
}

/// Search analytics report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchAnalyticsReport {
    pub total_queries: u64,
    pub avg_query_time_ms: f64,
    pub popular_terms: Vec<(String, u64)>,
    pub index_size_bytes: u64,
    pub last_updated: DateTime<Utc>,
}

impl Default for IndexConfig {
    fn default() -> Self {
        Self {
            enable_fulltext: true,
            enable_semantic: false,
            min_word_length: 2,
            max_word_length: 50,
            stop_words: Vec::new(),
            enable_stemming: false,
            batch_size: 100,
            max_results: 100,
        }
    }
}

impl Default for TextProcessingConfig {
    fn default() -> Self {
        Self {
            enable_tokenization: true,
            enable_normalization: true,
            enable_stop_word_removal: true,
            enable_stemming: false,
            language: "en".to_string(),
        }
    }
}

impl Default for SearchOptions {
    fn default() -> Self {
        let mut field_boosts = HashMap::new();
        field_boosts.insert("title".to_string(), 2.0);
        field_boosts.insert("keywords".to_string(), 1.5);
        
        Self {
            fuzzy_matching: false,
            fuzzy_distance: 2,
            phrase_matching: false,
            wildcard_matching: false,
            field_boosts,
            enable_highlighting: true,
            highlight_fragment_size: 200,
        }
    }
}
