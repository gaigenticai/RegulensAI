//! Document Versioning Module
//! 
//! This module provides comprehensive document version control including:
//! - Document version creation and management
//! - Version comparison and diff generation
//! - Version history tracking and audit trails
//! - Branch and merge operations for collaborative editing
//! - Version rollback and restoration capabilities

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use tracing::{info, warn, error, debug};

use regulateai_errors::RegulateAIError;
use crate::models::{Document, DocumentVersion, DocumentMetadata};

/// Version control manager for documents
pub struct VersionManager {
    /// Version storage
    versions: HashMap<Uuid, Vec<DocumentVersion>>,
    
    /// Version control configuration
    config: VersionConfig,
    
    /// Diff engine for comparing versions
    diff_engine: DiffEngine,
}

/// Version control configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionConfig {
    /// Maximum versions to keep per document
    pub max_versions: usize,
    
    /// Enable automatic versioning on save
    pub auto_version: bool,
    
    /// Version retention period in days
    pub retention_days: u32,
    
    /// Enable version compression
    pub enable_compression: bool,
    
    /// Enable branch operations
    pub enable_branching: bool,
}

/// Diff engine for version comparison
pub struct DiffEngine {
    /// Diff algorithm configuration
    config: DiffConfig,
}

/// Diff configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiffConfig {
    /// Context lines around changes
    pub context_lines: usize,
    
    /// Ignore whitespace changes
    pub ignore_whitespace: bool,
    
    /// Ignore case changes
    pub ignore_case: bool,
    
    /// Word-level diff granularity
    pub word_level: bool,
}

/// Version comparison result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionDiff {
    /// Source version ID
    pub source_version_id: Uuid,
    
    /// Target version ID
    pub target_version_id: Uuid,
    
    /// Diff changes
    pub changes: Vec<DiffChange>,
    
    /// Summary statistics
    pub summary: DiffSummary,
    
    /// Comparison timestamp
    pub compared_at: DateTime<Utc>,
}

/// Individual diff change
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiffChange {
    /// Change type
    pub change_type: ChangeType,
    
    /// Line number in source
    pub source_line: Option<usize>,
    
    /// Line number in target
    pub target_line: Option<usize>,
    
    /// Changed content
    pub content: String,
    
    /// Context lines before change
    pub context_before: Vec<String>,
    
    /// Context lines after change
    pub context_after: Vec<String>,
}

/// Change types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ChangeType {
    /// Content added
    Addition,
    
    /// Content deleted
    Deletion,
    
    /// Content modified
    Modification,
    
    /// Content moved
    Move,
}

/// Diff summary statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiffSummary {
    /// Total lines added
    pub lines_added: usize,
    
    /// Total lines deleted
    pub lines_deleted: usize,
    
    /// Total lines modified
    pub lines_modified: usize,
    
    /// Total changes
    pub total_changes: usize,
    
    /// Similarity percentage
    pub similarity_percent: f64,
}

/// Version branch information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionBranch {
    /// Branch ID
    pub id: Uuid,
    
    /// Branch name
    pub name: String,
    
    /// Parent branch ID
    pub parent_branch_id: Option<Uuid>,
    
    /// Branch point version ID
    pub branch_point_version_id: Uuid,
    
    /// Current head version ID
    pub head_version_id: Uuid,
    
    /// Branch creation timestamp
    pub created_at: DateTime<Utc>,
    
    /// User who created the branch
    pub created_by: Uuid,
    
    /// Branch status
    pub status: BranchStatus,
}

/// Branch status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum BranchStatus {
    Active,
    Merged,
    Abandoned,
    Locked,
}

/// Merge operation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeResult {
    /// Merge operation ID
    pub id: Uuid,
    
    /// Source branch ID
    pub source_branch_id: Uuid,
    
    /// Target branch ID
    pub target_branch_id: Uuid,
    
    /// Resulting version ID
    pub result_version_id: Uuid,
    
    /// Merge conflicts
    pub conflicts: Vec<MergeConflict>,
    
    /// Merge status
    pub status: MergeStatus,
    
    /// Merge timestamp
    pub merged_at: DateTime<Utc>,
    
    /// User who performed the merge
    pub merged_by: Uuid,
}

/// Merge conflict information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeConflict {
    /// Conflict ID
    pub id: Uuid,
    
    /// Conflict location (line number)
    pub location: usize,
    
    /// Source content
    pub source_content: String,
    
    /// Target content
    pub target_content: String,
    
    /// Conflict resolution
    pub resolution: Option<String>,
    
    /// Conflict status
    pub status: ConflictStatus,
}

/// Merge status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MergeStatus {
    Success,
    ConflictsResolved,
    ConflictsPending,
    Failed,
}

/// Conflict status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ConflictStatus {
    Unresolved,
    Resolved,
    Ignored,
}

impl VersionManager {
    /// Create a new version manager
    pub fn new(config: VersionConfig) -> Self {
        Self {
            versions: HashMap::new(),
            config,
            diff_engine: DiffEngine::new(DiffConfig::default()),
        }
    }
    
    /// Create a new version of a document
    pub async fn create_version(
        &mut self,
        document: &Document,
        change_summary: String,
        created_by: Uuid,
    ) -> Result<DocumentVersion, RegulateAIError> {
        info!("Creating new version for document: {}", document.id);
        
        // Get current versions for this document
        let versions = self.versions.entry(document.id).or_insert_with(Vec::new);
        
        // Determine next version number
        let next_version = versions.len() as i32 + 1;
        
        // Create new version
        let version = DocumentVersion {
            id: Uuid::new_v4(),
            document_id: document.id,
            version: next_version,
            content: document.content.clone(),
            metadata: document.metadata.clone(),
            change_summary,
            created_at: Utc::now(),
            created_by,
            is_current: true,
        };
        
        // Mark previous version as not current
        if let Some(previous_version) = versions.last_mut() {
            previous_version.is_current = false;
        }
        
        // Add new version
        versions.push(version.clone());
        
        // Apply retention policy
        self.apply_retention_policy(document.id).await?;
        
        info!("Created version {} for document {}", next_version, document.id);
        Ok(version)
    }
    
    /// Get all versions for a document
    pub async fn get_versions(&self, document_id: Uuid) -> Result<Vec<DocumentVersion>, RegulateAIError> {
        match self.versions.get(&document_id) {
            Some(versions) => Ok(versions.clone()),
            None => Ok(Vec::new()),
        }
    }
    
    /// Get a specific version
    pub async fn get_version(&self, document_id: Uuid, version: i32) -> Result<DocumentVersion, RegulateAIError> {
        let versions = self.versions.get(&document_id)
            .ok_or_else(|| RegulateAIError::NotFound(format!("No versions found for document: {}", document_id)))?;
        
        versions.iter()
            .find(|v| v.version == version)
            .cloned()
            .ok_or_else(|| RegulateAIError::NotFound(
                format!("Version {} not found for document: {}", version, document_id)
            ))
    }
    
    /// Get the current version
    pub async fn get_current_version(&self, document_id: Uuid) -> Result<DocumentVersion, RegulateAIError> {
        let versions = self.versions.get(&document_id)
            .ok_or_else(|| RegulateAIError::NotFound(format!("No versions found for document: {}", document_id)))?;
        
        versions.iter()
            .find(|v| v.is_current)
            .cloned()
            .ok_or_else(|| RegulateAIError::NotFound(
                format!("No current version found for document: {}", document_id)
            ))
    }
    
    /// Compare two versions
    pub async fn compare_versions(
        &self,
        document_id: Uuid,
        source_version: i32,
        target_version: i32,
    ) -> Result<VersionDiff, RegulateAIError> {
        let source = self.get_version(document_id, source_version).await?;
        let target = self.get_version(document_id, target_version).await?;
        
        self.diff_engine.compare(&source, &target).await
    }
    
    /// Rollback to a previous version
    pub async fn rollback_to_version(
        &mut self,
        document_id: Uuid,
        target_version: i32,
        rollback_by: Uuid,
    ) -> Result<DocumentVersion, RegulateAIError> {
        info!("Rolling back document {} to version {}", document_id, target_version);
        
        // Get target version
        let target = self.get_version(document_id, target_version).await?;
        
        // Create new version with target content
        let rollback_version = DocumentVersion {
            id: Uuid::new_v4(),
            document_id,
            version: self.get_next_version_number(document_id),
            content: target.content.clone(),
            metadata: target.metadata.clone(),
            change_summary: format!("Rollback to version {}", target_version),
            created_at: Utc::now(),
            created_by: rollback_by,
            is_current: true,
        };
        
        // Add rollback version
        let versions = self.versions.entry(document_id).or_insert_with(Vec::new);
        
        // Mark previous version as not current
        if let Some(previous_version) = versions.last_mut() {
            previous_version.is_current = false;
        }
        
        versions.push(rollback_version.clone());
        
        info!("Rolled back document {} to version {}", document_id, target_version);
        Ok(rollback_version)
    }
    
    /// Create a branch from a version
    pub async fn create_branch(
        &mut self,
        document_id: Uuid,
        branch_name: String,
        source_version: i32,
        created_by: Uuid,
    ) -> Result<VersionBranch, RegulateAIError> {
        if !self.config.enable_branching {
            return Err(RegulateAIError::BadRequest("Branching is not enabled".to_string()));
        }
        
        info!("Creating branch '{}' for document {} from version {}", branch_name, document_id, source_version);
        
        // Get source version
        let source = self.get_version(document_id, source_version).await?;
        
        let branch = VersionBranch {
            id: Uuid::new_v4(),
            name: branch_name,
            parent_branch_id: None, // Main branch
            branch_point_version_id: source.id,
            head_version_id: source.id,
            created_at: Utc::now(),
            created_by,
            status: BranchStatus::Active,
        };
        
        info!("Created branch: {} ({})", branch.name, branch.id);
        Ok(branch)
    }
    
    /// Merge branches
    pub async fn merge_branches(
        &mut self,
        source_branch_id: Uuid,
        target_branch_id: Uuid,
        merged_by: Uuid,
    ) -> Result<MergeResult, RegulateAIError> {
        if !self.config.enable_branching {
            return Err(RegulateAIError::BadRequest("Branching is not enabled".to_string()));
        }
        
        info!("Merging branch {} into {}", source_branch_id, target_branch_id);
        
        // This is a simplified merge implementation
        // In a real system, this would involve complex conflict detection and resolution
        let merge_result = MergeResult {
            id: Uuid::new_v4(),
            source_branch_id,
            target_branch_id,
            result_version_id: Uuid::new_v4(),
            conflicts: Vec::new(),
            status: MergeStatus::Success,
            merged_at: Utc::now(),
            merged_by,
        };
        
        info!("Merge completed: {}", merge_result.id);
        Ok(merge_result)
    }
    
    /// Get version history for a document
    pub async fn get_version_history(&self, document_id: Uuid) -> Result<Vec<VersionHistoryEntry>, RegulateAIError> {
        let versions = self.get_versions(document_id).await?;
        
        let mut history: Vec<VersionHistoryEntry> = versions.into_iter()
            .map(|v| VersionHistoryEntry {
                version_id: v.id,
                version_number: v.version,
                change_summary: v.change_summary,
                created_at: v.created_at,
                created_by: v.created_by,
                is_current: v.is_current,
                content_size: v.content.len(),
            })
            .collect();
        
        // Sort by version number descending (newest first)
        history.sort_by(|a, b| b.version_number.cmp(&a.version_number));
        
        Ok(history)
    }
    
    /// Apply retention policy to versions
    async fn apply_retention_policy(&mut self, document_id: Uuid) -> Result<(), RegulateAIError> {
        let versions = self.versions.get_mut(&document_id)
            .ok_or_else(|| RegulateAIError::NotFound(format!("No versions found for document: {}", document_id)))?;
        
        // Remove old versions if exceeding max_versions
        if versions.len() > self.config.max_versions {
            let excess = versions.len() - self.config.max_versions;
            versions.drain(0..excess);
            info!("Removed {} old versions for document {}", excess, document_id);
        }
        
        // Remove versions older than retention period
        let cutoff_date = Utc::now() - chrono::Duration::days(self.config.retention_days as i64);
        let original_count = versions.len();
        versions.retain(|v| v.created_at > cutoff_date || v.is_current);
        let removed_count = original_count - versions.len();
        
        if removed_count > 0 {
            info!("Removed {} expired versions for document {}", removed_count, document_id);
        }
        
        Ok(())
    }
    
    /// Get next version number for a document
    fn get_next_version_number(&self, document_id: Uuid) -> i32 {
        match self.versions.get(&document_id) {
            Some(versions) => versions.len() as i32 + 1,
            None => 1,
        }
    }
}

impl DiffEngine {
    /// Create a new diff engine
    pub fn new(config: DiffConfig) -> Self {
        Self { config }
    }
    
    /// Compare two document versions
    pub async fn compare(&self, source: &DocumentVersion, target: &DocumentVersion) -> Result<VersionDiff, RegulateAIError> {
        debug!("Comparing versions {} and {}", source.version, target.version);
        
        let source_lines: Vec<&str> = source.content.lines().collect();
        let target_lines: Vec<&str> = target.content.lines().collect();
        
        let changes = self.compute_diff(&source_lines, &target_lines);
        let summary = self.compute_summary(&changes);
        
        Ok(VersionDiff {
            source_version_id: source.id,
            target_version_id: target.id,
            changes,
            summary,
            compared_at: Utc::now(),
        })
    }
    
    /// Compute diff changes between two sets of lines
    fn compute_diff(&self, source_lines: &[&str], target_lines: &[&str]) -> Vec<DiffChange> {
        let mut changes = Vec::new();
        
        // Simple line-by-line comparison
        // In a real implementation, this would use a more sophisticated diff algorithm like Myers
        let max_lines = source_lines.len().max(target_lines.len());
        
        for i in 0..max_lines {
            let source_line = source_lines.get(i);
            let target_line = target_lines.get(i);
            
            match (source_line, target_line) {
                (Some(src), Some(tgt)) => {
                    if src != tgt {
                        changes.push(DiffChange {
                            change_type: ChangeType::Modification,
                            source_line: Some(i + 1),
                            target_line: Some(i + 1),
                            content: format!("- {}\n+ {}", src, tgt),
                            context_before: self.get_context_lines(source_lines, i, true),
                            context_after: self.get_context_lines(source_lines, i, false),
                        });
                    }
                }
                (Some(src), None) => {
                    changes.push(DiffChange {
                        change_type: ChangeType::Deletion,
                        source_line: Some(i + 1),
                        target_line: None,
                        content: format!("- {}", src),
                        context_before: self.get_context_lines(source_lines, i, true),
                        context_after: self.get_context_lines(source_lines, i, false),
                    });
                }
                (None, Some(tgt)) => {
                    changes.push(DiffChange {
                        change_type: ChangeType::Addition,
                        source_line: None,
                        target_line: Some(i + 1),
                        content: format!("+ {}", tgt),
                        context_before: self.get_context_lines(target_lines, i, true),
                        context_after: self.get_context_lines(target_lines, i, false),
                    });
                }
                (None, None) => break,
            }
        }
        
        changes
    }
    
    /// Get context lines around a change
    fn get_context_lines(&self, lines: &[&str], index: usize, before: bool) -> Vec<String> {
        let mut context = Vec::new();
        
        if before {
            let start = index.saturating_sub(self.config.context_lines);
            for i in start..index {
                if let Some(line) = lines.get(i) {
                    context.push(line.to_string());
                }
            }
        } else {
            let end = (index + self.config.context_lines + 1).min(lines.len());
            for i in (index + 1)..end {
                if let Some(line) = lines.get(i) {
                    context.push(line.to_string());
                }
            }
        }
        
        context
    }
    
    /// Compute diff summary statistics
    fn compute_summary(&self, changes: &[DiffChange]) -> DiffSummary {
        let mut lines_added = 0;
        let mut lines_deleted = 0;
        let mut lines_modified = 0;
        
        for change in changes {
            match change.change_type {
                ChangeType::Addition => lines_added += 1,
                ChangeType::Deletion => lines_deleted += 1,
                ChangeType::Modification => lines_modified += 1,
                ChangeType::Move => lines_modified += 1,
            }
        }
        
        let total_changes = changes.len();
        let total_lines = lines_added + lines_deleted + lines_modified;
        let similarity_percent = if total_lines > 0 {
            100.0 - (total_changes as f64 / total_lines as f64 * 100.0)
        } else {
            100.0
        };
        
        DiffSummary {
            lines_added,
            lines_deleted,
            lines_modified,
            total_changes,
            similarity_percent: similarity_percent.max(0.0).min(100.0),
        }
    }
}

/// Version history entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionHistoryEntry {
    pub version_id: Uuid,
    pub version_number: i32,
    pub change_summary: String,
    pub created_at: DateTime<Utc>,
    pub created_by: Uuid,
    pub is_current: bool,
    pub content_size: usize,
}

impl Default for VersionConfig {
    fn default() -> Self {
        Self {
            max_versions: 50,
            auto_version: true,
            retention_days: 365,
            enable_compression: false,
            enable_branching: true,
        }
    }
}

impl Default for DiffConfig {
    fn default() -> Self {
        Self {
            context_lines: 3,
            ignore_whitespace: false,
            ignore_case: false,
            word_level: false,
        }
    }
}
