//! Sanctions screening and watchlist checking

use async_trait::async_trait;
use fuzzy_matcher::{FuzzyMatcher, SkimMatcher};
use levenshtein::levenshtein;
use regex::Regex;
use std::collections::HashMap;
use std::sync::Arc;
use tracing::{info, warn, debug};
use uuid::Uuid;

use regulateai_config::OfacConfig;
use regulateai_errors::RegulateAIError;
use regulateai_database::entities::{Customer, SanctionsList};

use crate::models::SanctionsScreeningResult;
use crate::repositories::SanctionsRepository;

/// Sanctions screening engine
pub struct SanctionsScreener {
    sanctions_repo: Arc<SanctionsRepository>,
    ofac_config: OfacConfig,
    matcher: SkimMatcher,
    screening_strategies: Vec<Box<dyn ScreeningStrategy + Send + Sync>>,
}

impl SanctionsScreener {
    /// Create a new sanctions screener
    pub fn new(sanctions_repo: Arc<SanctionsRepository>, ofac_config: OfacConfig) -> Self {
        let matcher = SkimMatcher::default();
        
        let mut screener = Self {
            sanctions_repo,
            ofac_config: ofac_config.clone(),
            matcher,
            screening_strategies: Vec::new(),
        };

        // Initialize screening strategies
        screener.initialize_strategies();
        screener
    }

    /// Screen a customer against sanctions lists
    pub async fn screen_customer(&self, customer: &Customer) -> Result<SanctionsScreeningResult, RegulateAIError> {
        info!("Screening customer: {} against sanctions lists", customer.id);

        // Get active sanctions lists
        let sanctions_lists = self.sanctions_repo.get_active_sanctions().await?;
        
        if sanctions_lists.is_empty() {
            warn!("No active sanctions lists found");
            return Ok(SanctionsScreeningResult {
                is_match: false,
                match_score: 0.0,
                match_details: "No sanctions lists available".to_string(),
                matched_lists: vec![],
                screening_timestamp: chrono::Utc::now(),
            });
        }

        // Extract searchable terms from customer
        let search_terms = self.extract_customer_search_terms(customer);
        
        let mut best_match_score = 0.0;
        let mut match_details = Vec::new();
        let mut matched_lists = Vec::new();

        // Screen against each sanctions list
        for sanctions_entry in &sanctions_lists {
            for strategy in &self.screening_strategies {
                let match_result = strategy.screen(&search_terms, sanctions_entry).await?;
                
                if match_result.score > best_match_score {
                    best_match_score = match_result.score;
                }

                if match_result.is_match {
                    match_details.push(format!(
                        "Match found in {} ({}): {} - Score: {:.2}",
                        sanctions_entry.list_name,
                        strategy.name(),
                        match_result.details,
                        match_result.score
                    ));
                    
                    if !matched_lists.contains(&sanctions_entry.list_name) {
                        matched_lists.push(sanctions_entry.list_name.clone());
                    }
                }
            }
        }

        let is_match = best_match_score >= self.ofac_config.fuzzy_match_threshold;
        
        let result = SanctionsScreeningResult {
            is_match,
            match_score: best_match_score,
            match_details: if match_details.is_empty() {
                "No matches found".to_string()
            } else {
                match_details.join("; ")
            },
            matched_lists,
            screening_timestamp: chrono::Utc::now(),
        };

        if is_match {
            warn!("Sanctions match found for customer {}: {}", customer.id, result.match_details);
        } else {
            debug!("No sanctions matches found for customer {}", customer.id);
        }

        Ok(result)
    }

    /// Screen a name against sanctions lists
    pub async fn screen_name(&self, name: &str) -> Result<SanctionsScreeningResult, RegulateAIError> {
        info!("Screening name: {} against sanctions lists", name);

        let sanctions_lists = self.sanctions_repo.get_active_sanctions().await?;
        let search_terms = vec![name.to_string()];
        
        let mut best_match_score = 0.0;
        let mut match_details = Vec::new();
        let mut matched_lists = Vec::new();

        for sanctions_entry in &sanctions_lists {
            for strategy in &self.screening_strategies {
                let match_result = strategy.screen(&search_terms, sanctions_entry).await?;
                
                if match_result.score > best_match_score {
                    best_match_score = match_result.score;
                }

                if match_result.is_match {
                    match_details.push(format!(
                        "Match in {}: {} - Score: {:.2}",
                        sanctions_entry.list_name,
                        match_result.details,
                        match_result.score
                    ));
                    
                    if !matched_lists.contains(&sanctions_entry.list_name) {
                        matched_lists.push(sanctions_entry.list_name.clone());
                    }
                }
            }
        }

        Ok(SanctionsScreeningResult {
            is_match: best_match_score >= self.ofac_config.fuzzy_match_threshold,
            match_score: best_match_score,
            match_details: if match_details.is_empty() {
                "No matches found".to_string()
            } else {
                match_details.join("; ")
            },
            matched_lists,
            screening_timestamp: chrono::Utc::now(),
        })
    }

    /// Initialize screening strategies
    fn initialize_strategies(&mut self) {
        // Exact match strategy
        self.screening_strategies.push(Box::new(ExactMatchStrategy));
        
        // Fuzzy match strategy
        self.screening_strategies.push(Box::new(FuzzyMatchStrategy {
            threshold: self.ofac_config.fuzzy_match_threshold,
        }));
        
        // Phonetic match strategy
        self.screening_strategies.push(Box::new(PhoneticMatchStrategy));
        
        // Alias match strategy
        self.screening_strategies.push(Box::new(AliasMatchStrategy));
        
        // Partial match strategy
        self.screening_strategies.push(Box::new(PartialMatchStrategy));

        info!("Initialized {} screening strategies", self.screening_strategies.len());
    }

    /// Extract searchable terms from customer data
    fn extract_customer_search_terms(&self, customer: &Customer) -> Vec<String> {
        let mut terms = Vec::new();

        // Add full name
        if let (Some(first_name), Some(last_name)) = (&customer.first_name, &customer.last_name) {
            terms.push(format!("{} {}", first_name, last_name));
            terms.push(format!("{}, {}", last_name, first_name));
            terms.push(first_name.clone());
            terms.push(last_name.clone());
        }

        // Add identification document numbers (if available)
        if let Ok(docs) = serde_json::from_value::<Vec<serde_json::Value>>(customer.identification_documents.clone()) {
            for doc in docs {
                if let Some(doc_number) = doc.get("document_number").and_then(|v| v.as_str()) {
                    terms.push(doc_number.to_string());
                }
            }
        }

        // Remove duplicates and empty strings
        terms.sort();
        terms.dedup();
        terms.retain(|t| !t.trim().is_empty());

        debug!("Extracted {} search terms for customer {}", terms.len(), customer.id);
        terms
    }
}

/// Screening match result
#[derive(Debug, Clone)]
pub struct ScreeningMatchResult {
    pub is_match: bool,
    pub score: f64,
    pub details: String,
}

/// Trait for different screening strategies
#[async_trait]
pub trait ScreeningStrategy {
    /// Strategy name
    fn name(&self) -> &str;
    
    /// Screen search terms against a sanctions entry
    async fn screen(&self, search_terms: &[String], sanctions_entry: &SanctionsList) -> Result<ScreeningMatchResult, RegulateAIError>;
}

/// Exact match screening strategy
pub struct ExactMatchStrategy;

#[async_trait]
impl ScreeningStrategy for ExactMatchStrategy {
    fn name(&self) -> &str {
        "Exact Match"
    }

    async fn screen(&self, search_terms: &[String], sanctions_entry: &SanctionsList) -> Result<ScreeningMatchResult, RegulateAIError> {
        let entity_name = sanctions_entry.entity_name.to_lowercase();
        
        // Check aliases if available
        let mut all_names = vec![entity_name.clone()];
        if let Ok(aliases) = serde_json::from_value::<Vec<String>>(sanctions_entry.aliases.clone()) {
            for alias in aliases {
                all_names.push(alias.to_lowercase());
            }
        }

        for search_term in search_terms {
            let search_term_lower = search_term.to_lowercase();
            
            for name in &all_names {
                if name == &search_term_lower {
                    return Ok(ScreeningMatchResult {
                        is_match: true,
                        score: 100.0,
                        details: format!("Exact match: '{}' matches '{}'", search_term, name),
                    });
                }
            }
        }

        Ok(ScreeningMatchResult {
            is_match: false,
            score: 0.0,
            details: "No exact match found".to_string(),
        })
    }
}

/// Fuzzy match screening strategy
pub struct FuzzyMatchStrategy {
    threshold: f64,
}

#[async_trait]
impl ScreeningStrategy for FuzzyMatchStrategy {
    fn name(&self) -> &str {
        "Fuzzy Match"
    }

    async fn screen(&self, search_terms: &[String], sanctions_entry: &SanctionsList) -> Result<ScreeningMatchResult, RegulateAIError> {
        let matcher = SkimMatcher::default();
        let entity_name = &sanctions_entry.entity_name;
        
        let mut best_score = 0.0;
        let mut best_match = String::new();

        // Check main entity name
        for search_term in search_terms {
            if let Some(score) = matcher.fuzzy_match(entity_name, search_term) {
                let normalized_score = (score as f64 / search_term.len() as f64) * 100.0;
                if normalized_score > best_score {
                    best_score = normalized_score;
                    best_match = format!("'{}' matches '{}'", search_term, entity_name);
                }
            }
        }

        // Check aliases
        if let Ok(aliases) = serde_json::from_value::<Vec<String>>(sanctions_entry.aliases.clone()) {
            for alias in aliases {
                for search_term in search_terms {
                    if let Some(score) = matcher.fuzzy_match(&alias, search_term) {
                        let normalized_score = (score as f64 / search_term.len() as f64) * 100.0;
                        if normalized_score > best_score {
                            best_score = normalized_score;
                            best_match = format!("'{}' matches alias '{}'", search_term, alias);
                        }
                    }
                }
            }
        }

        let is_match = best_score >= self.threshold * 100.0;

        Ok(ScreeningMatchResult {
            is_match,
            score: best_score,
            details: if is_match {
                format!("Fuzzy match: {} (score: {:.2})", best_match, best_score)
            } else {
                "No fuzzy match above threshold".to_string()
            },
        })
    }
}

/// Phonetic match screening strategy
pub struct PhoneticMatchStrategy;

#[async_trait]
impl ScreeningStrategy for PhoneticMatchStrategy {
    fn name(&self) -> &str {
        "Phonetic Match"
    }

    async fn screen(&self, search_terms: &[String], sanctions_entry: &SanctionsList) -> Result<ScreeningMatchResult, RegulateAIError> {
        // Simplified phonetic matching using Levenshtein distance
        let entity_name = &sanctions_entry.entity_name;
        let mut best_score = 0.0;
        let mut best_match = String::new();

        for search_term in search_terms {
            let distance = levenshtein(search_term, entity_name);
            let max_len = search_term.len().max(entity_name.len());
            
            if max_len > 0 {
                let similarity = (1.0 - (distance as f64 / max_len as f64)) * 100.0;
                if similarity > best_score {
                    best_score = similarity;
                    best_match = format!("'{}' phonetically similar to '{}'", search_term, entity_name);
                }
            }
        }

        // Consider it a match if similarity is above 80%
        let is_match = best_score >= 80.0;

        Ok(ScreeningMatchResult {
            is_match,
            score: best_score,
            details: if is_match {
                format!("Phonetic match: {} (score: {:.2})", best_match, best_score)
            } else {
                "No phonetic match found".to_string()
            },
        })
    }
}

/// Alias match screening strategy
pub struct AliasMatchStrategy;

#[async_trait]
impl ScreeningStrategy for AliasMatchStrategy {
    fn name(&self) -> &str {
        "Alias Match"
    }

    async fn screen(&self, search_terms: &[String], sanctions_entry: &SanctionsList) -> Result<ScreeningMatchResult, RegulateAIError> {
        if let Ok(aliases) = serde_json::from_value::<Vec<String>>(sanctions_entry.aliases.clone()) {
            for alias in aliases {
                for search_term in search_terms {
                    // Check for partial matches in aliases
                    if alias.to_lowercase().contains(&search_term.to_lowercase()) ||
                       search_term.to_lowercase().contains(&alias.to_lowercase()) {
                        return Ok(ScreeningMatchResult {
                            is_match: true,
                            score: 75.0,
                            details: format!("Alias match: '{}' contains '{}'", search_term, alias),
                        });
                    }
                }
            }
        }

        Ok(ScreeningMatchResult {
            is_match: false,
            score: 0.0,
            details: "No alias match found".to_string(),
        })
    }
}

/// Partial match screening strategy
pub struct PartialMatchStrategy;

#[async_trait]
impl ScreeningStrategy for PartialMatchStrategy {
    fn name(&self) -> &str {
        "Partial Match"
    }

    async fn screen(&self, search_terms: &[String], sanctions_entry: &SanctionsList) -> Result<ScreeningMatchResult, RegulateAIError> {
        let entity_name = sanctions_entry.entity_name.to_lowercase();
        
        for search_term in search_terms {
            let search_term_lower = search_term.to_lowercase();
            
            // Check if search term is contained in entity name or vice versa
            if entity_name.contains(&search_term_lower) && search_term_lower.len() >= 4 {
                return Ok(ScreeningMatchResult {
                    is_match: true,
                    score: 60.0,
                    details: format!("Partial match: '{}' contains '{}'", entity_name, search_term_lower),
                });
            }
            
            if search_term_lower.contains(&entity_name) && entity_name.len() >= 4 {
                return Ok(ScreeningMatchResult {
                    is_match: true,
                    score: 60.0,
                    details: format!("Partial match: '{}' contains '{}'", search_term_lower, entity_name),
                });
            }
        }

        Ok(ScreeningMatchResult {
            is_match: false,
            score: 0.0,
            details: "No partial match found".to_string(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use regulateai_database::entities::{Customer, SanctionsList};

    fn create_test_customer() -> Customer {
        Customer {
            id: Uuid::new_v4(),
            organization_id: None,
            customer_type: "INDIVIDUAL".to_string(),
            first_name: Some("John".to_string()),
            last_name: Some("Doe".to_string()),
            date_of_birth: Some(NaiveDate::from_ymd_opt(1990, 1, 1).unwrap()),
            nationality: Some("US".to_string()),
            identification_documents: serde_json::json!([]),
            address: serde_json::json!({}),
            contact_info: serde_json::json!({}),
            risk_score: rust_decimal::Decimal::from(50),
            risk_level: "MEDIUM".to_string(),
            pep_status: false,
            sanctions_status: false,
            kyc_status: "APPROVED".to_string(),
            kyc_completed_at: Some(chrono::Utc::now()),
            last_reviewed_at: Some(chrono::Utc::now()),
            next_review_due: Some(chrono::Utc::now() + chrono::Duration::days(365)),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            created_by: None,
            updated_by: None,
            version: 1,
            metadata: serde_json::json!({}),
        }
    }

    fn create_test_sanctions_entry() -> SanctionsList {
        SanctionsList {
            id: Uuid::new_v4(),
            list_name: "OFAC SDN".to_string(),
            source: "OFAC".to_string(),
            entity_type: "INDIVIDUAL".to_string(),
            entity_name: "John Doe".to_string(),
            aliases: serde_json::json!(["Johnny Doe", "J. Doe"]),
            addresses: serde_json::json!([]),
            identifiers: serde_json::json!([]),
            sanctions_type: Some("SANCTIONS".to_string()),
            listing_date: Some(chrono::Utc::now().date_naive()),
            last_updated: Some(chrono::Utc::now().date_naive()),
            is_active: true,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        }
    }

    #[tokio::test]
    async fn test_exact_match_strategy() {
        let strategy = ExactMatchStrategy;
        let search_terms = vec!["John Doe".to_string()];
        let sanctions_entry = create_test_sanctions_entry();

        let result = strategy.screen(&search_terms, &sanctions_entry).await.unwrap();
        assert!(result.is_match);
        assert_eq!(result.score, 100.0);
    }

    #[tokio::test]
    async fn test_fuzzy_match_strategy() {
        let strategy = FuzzyMatchStrategy { threshold: 0.8 };
        let search_terms = vec!["Jon Doe".to_string()]; // Slight misspelling
        let sanctions_entry = create_test_sanctions_entry();

        let result = strategy.screen(&search_terms, &sanctions_entry).await.unwrap();
        // Should match due to fuzzy matching
        assert!(result.score > 0.0);
    }

    #[tokio::test]
    async fn test_phonetic_match_strategy() {
        let strategy = PhoneticMatchStrategy;
        let search_terms = vec!["Jon Do".to_string()]; // Phonetically similar
        let sanctions_entry = create_test_sanctions_entry();

        let result = strategy.screen(&search_terms, &sanctions_entry).await.unwrap();
        assert!(result.score > 0.0);
    }

    #[test]
    fn test_extract_customer_search_terms() {
        let ofac_config = OfacConfig {
            api_url: "test".to_string(),
            api_key: "test".to_string(),
            timeout_seconds: 30,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            update_interval_seconds: 3600,
            enable_fuzzy_matching: true,
            fuzzy_match_threshold: 0.8,
        };
        
        let sanctions_repo = Arc::new(SanctionsRepository::new(
            regulateai_database::create_test_connection().await.unwrap()
        ));
        
        let screener = SanctionsScreener::new(sanctions_repo, ofac_config);
        let customer = create_test_customer();
        
        let terms = screener.extract_customer_search_terms(&customer);
        assert!(!terms.is_empty());
        assert!(terms.contains(&"John Doe".to_string()));
        assert!(terms.contains(&"Doe, John".to_string()));
    }
}
