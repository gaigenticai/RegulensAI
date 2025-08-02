//! Document Templates Module
//! 
//! This module provides comprehensive document template management including:
//! - Template creation and management
//! - Variable substitution and processing
//! - Template rendering with different output formats
//! - Template validation and error handling
//! - Template inheritance and composition

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use regex::Regex;
use tracing::{info, warn, error, debug};

use regulateai_errors::RegulateAIError;
use crate::models::{
    DocumentTemplate, TemplateVariable, VariableType, VariableValidation,
    TemplateMetadata, ComplexityLevel, DocumentType,
};

/// Template engine for processing document templates
pub struct TemplateEngine {
    /// Template registry
    templates: HashMap<Uuid, DocumentTemplate>,
    
    /// Template processing configuration
    config: TemplateEngineConfig,
    
    /// Variable processors
    processors: HashMap<VariableType, Box<dyn VariableProcessor>>,
}

/// Template engine configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateEngineConfig {
    /// Variable delimiter start
    pub variable_start: String,
    
    /// Variable delimiter end
    pub variable_end: String,
    
    /// Enable template inheritance
    pub enable_inheritance: bool,
    
    /// Maximum template nesting depth
    pub max_nesting_depth: usize,
    
    /// Template cache size
    pub cache_size: usize,
    
    /// Enable template validation
    pub enable_validation: bool,
}

/// Template processing context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateContext {
    /// Variable values
    pub variables: HashMap<String, serde_json::Value>,
    
    /// User context
    pub user_id: Option<Uuid>,
    
    /// Organization context
    pub organization_id: Option<Uuid>,
    
    /// Processing timestamp
    pub timestamp: DateTime<Utc>,
    
    /// Additional context data
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Template processing result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateResult {
    /// Processed content
    pub content: String,
    
    /// Template ID used
    pub template_id: Uuid,
    
    /// Variables used in processing
    pub variables_used: Vec<String>,
    
    /// Processing warnings
    pub warnings: Vec<String>,
    
    /// Processing timestamp
    pub processed_at: DateTime<Utc>,
    
    /// Processing duration in milliseconds
    pub processing_time_ms: u64,
}

/// Variable processor trait
pub trait VariableProcessor: Send + Sync {
    /// Process a variable value
    fn process(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<String, RegulateAIError>;
    
    /// Validate a variable value
    fn validate(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<(), RegulateAIError>;
}

/// Text variable processor
pub struct TextProcessor;

/// Number variable processor
pub struct NumberProcessor;

/// Date variable processor
pub struct DateProcessor;

/// Boolean variable processor
pub struct BooleanProcessor;

/// Select variable processor
pub struct SelectProcessor;

/// Rich text variable processor
pub struct RichTextProcessor;

impl TemplateEngine {
    /// Create a new template engine
    pub fn new(config: TemplateEngineConfig) -> Self {
        let mut processors: HashMap<VariableType, Box<dyn VariableProcessor>> = HashMap::new();
        processors.insert(VariableType::Text, Box::new(TextProcessor));
        processors.insert(VariableType::Number, Box::new(NumberProcessor));
        processors.insert(VariableType::Date, Box::new(DateProcessor));
        processors.insert(VariableType::Boolean, Box::new(BooleanProcessor));
        processors.insert(VariableType::Select, Box::new(SelectProcessor));
        processors.insert(VariableType::RichText, Box::new(RichTextProcessor));
        
        Self {
            templates: HashMap::new(),
            config,
            processors,
        }
    }
    
    /// Register a template
    pub fn register_template(&mut self, template: DocumentTemplate) -> Result<(), RegulateAIError> {
        info!("Registering template: {} ({})", template.name, template.id);
        
        // Validate template
        self.validate_template(&template)?;
        
        // Store template
        self.templates.insert(template.id, template);
        
        Ok(())
    }
    
    /// Process a template with given context
    pub async fn process_template(
        &self,
        template_id: Uuid,
        context: TemplateContext,
    ) -> Result<TemplateResult, RegulateAIError> {
        let start_time = std::time::Instant::now();
        
        info!("Processing template: {}", template_id);
        
        // Get template
        let template = self.templates.get(&template_id)
            .ok_or_else(|| RegulateAIError::NotFound(format!("Template not found: {}", template_id)))?;
        
        // Validate context variables
        self.validate_context(template, &context)?;
        
        // Process template content
        let mut content = template.content.clone();
        let mut variables_used = Vec::new();
        let mut warnings = Vec::new();
        
        // Replace variables in content
        for variable in &template.variables {
            let variable_pattern = format!("{}{}{}", 
                self.config.variable_start, 
                variable.name, 
                self.config.variable_end
            );
            
            if content.contains(&variable_pattern) {
                let processed_value = self.process_variable(variable, &context, &mut warnings)?;
                content = content.replace(&variable_pattern, &processed_value);
                variables_used.push(variable.name.clone());
            }
        }
        
        // Check for unprocessed variables
        self.check_unprocessed_variables(&content, &mut warnings)?;
        
        let processing_time = start_time.elapsed().as_millis() as u64;
        
        Ok(TemplateResult {
            content,
            template_id,
            variables_used,
            warnings,
            processed_at: Utc::now(),
            processing_time_ms: processing_time,
        })
    }
    
    /// Create a new template
    pub async fn create_template(
        &mut self,
        name: String,
        description: String,
        content: String,
        template_type: DocumentType,
        variables: Vec<TemplateVariable>,
        metadata: TemplateMetadata,
        created_by: Uuid,
    ) -> Result<DocumentTemplate, RegulateAIError> {
        let template = DocumentTemplate {
            id: Uuid::new_v4(),
            name,
            description,
            content,
            template_type,
            variables,
            metadata,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by,
            updated_by: created_by,
        };
        
        // Validate template
        self.validate_template(&template)?;
        
        // Register template
        self.register_template(template.clone())?;
        
        info!("Created new template: {} ({})", template.name, template.id);
        Ok(template)
    }
    
    /// Update an existing template
    pub async fn update_template(
        &mut self,
        template_id: Uuid,
        updates: TemplateUpdate,
        updated_by: Uuid,
    ) -> Result<DocumentTemplate, RegulateAIError> {
        let mut template = self.templates.get(&template_id)
            .ok_or_else(|| RegulateAIError::NotFound(format!("Template not found: {}", template_id)))?
            .clone();
        
        // Apply updates
        if let Some(name) = updates.name {
            template.name = name;
        }
        if let Some(description) = updates.description {
            template.description = description;
        }
        if let Some(content) = updates.content {
            template.content = content;
        }
        if let Some(variables) = updates.variables {
            template.variables = variables;
        }
        if let Some(metadata) = updates.metadata {
            template.metadata = metadata;
        }
        
        template.updated_at = Utc::now();
        template.updated_by = updated_by;
        
        // Validate updated template
        self.validate_template(&template)?;
        
        // Update in registry
        self.templates.insert(template_id, template.clone());
        
        info!("Updated template: {} ({})", template.name, template.id);
        Ok(template)
    }
    
    /// Delete a template
    pub async fn delete_template(&mut self, template_id: Uuid) -> Result<(), RegulateAIError> {
        if self.templates.remove(&template_id).is_some() {
            info!("Deleted template: {}", template_id);
            Ok(())
        } else {
            Err(RegulateAIError::NotFound(format!("Template not found: {}", template_id)))
        }
    }
    
    /// List templates with filtering
    pub async fn list_templates(&self, filter: TemplateFilter) -> Result<Vec<DocumentTemplate>, RegulateAIError> {
        let mut templates: Vec<_> = self.templates.values().cloned().collect();
        
        // Apply filters
        if let Some(template_type) = filter.template_type {
            templates.retain(|t| t.template_type == template_type);
        }
        
        if let Some(category) = filter.category {
            templates.retain(|t| t.metadata.category == category);
        }
        
        if let Some(tags) = filter.tags {
            templates.retain(|t| tags.iter().any(|tag| t.metadata.tags.contains(tag)));
        }
        
        if let Some(complexity) = filter.complexity_level {
            templates.retain(|t| t.metadata.complexity_level == complexity);
        }
        
        // Sort templates
        templates.sort_by(|a, b| a.name.cmp(&b.name));
        
        Ok(templates)
    }
    
    /// Validate template structure and variables
    fn validate_template(&self, template: &DocumentTemplate) -> Result<(), RegulateAIError> {
        if !self.config.enable_validation {
            return Ok(());
        }
        
        // Validate template name
        if template.name.trim().is_empty() {
            return Err(RegulateAIError::BadRequest("Template name cannot be empty".to_string()));
        }
        
        // Validate template content
        if template.content.trim().is_empty() {
            return Err(RegulateAIError::BadRequest("Template content cannot be empty".to_string()));
        }
        
        // Validate variables
        for variable in &template.variables {
            self.validate_template_variable(variable)?;
        }
        
        // Check for variable references in content
        self.validate_variable_references(template)?;
        
        Ok(())
    }
    
    /// Validate a template variable definition
    fn validate_template_variable(&self, variable: &TemplateVariable) -> Result<(), RegulateAIError> {
        // Validate variable name
        if variable.name.trim().is_empty() {
            return Err(RegulateAIError::BadRequest("Variable name cannot be empty".to_string()));
        }
        
        // Validate variable name format (alphanumeric and underscores only)
        let name_regex = Regex::new(r"^[a-zA-Z_][a-zA-Z0-9_]*$").unwrap();
        if !name_regex.is_match(&variable.name) {
            return Err(RegulateAIError::BadRequest(
                format!("Invalid variable name format: {}", variable.name)
            ));
        }
        
        // Validate default value if provided
        if let Some(default_value) = &variable.default_value {
            let json_value = serde_json::Value::String(default_value.clone());
            if let Some(processor) = self.processors.get(&variable.variable_type) {
                processor.validate(&json_value, variable.validation.as_ref())?;
            }
        }
        
        Ok(())
    }
    
    /// Validate variable references in template content
    fn validate_variable_references(&self, template: &DocumentTemplate) -> Result<(), RegulateAIError> {
        let variable_names: std::collections::HashSet<_> = template.variables.iter()
            .map(|v| &v.name)
            .collect();
        
        // Find all variable references in content
        let variable_pattern = format!(r"{}\s*(\w+)\s*{}", 
            regex::escape(&self.config.variable_start),
            regex::escape(&self.config.variable_end)
        );
        let regex = Regex::new(&variable_pattern).unwrap();
        
        for captures in regex.captures_iter(&template.content) {
            if let Some(var_name) = captures.get(1) {
                let var_name_str = var_name.as_str();
                if !variable_names.contains(var_name_str) {
                    return Err(RegulateAIError::BadRequest(
                        format!("Undefined variable reference: {}", var_name_str)
                    ));
                }
            }
        }
        
        Ok(())
    }
    
    /// Validate template context variables
    fn validate_context(&self, template: &DocumentTemplate, context: &TemplateContext) -> Result<(), RegulateAIError> {
        for variable in &template.variables {
            if variable.required {
                if !context.variables.contains_key(&variable.name) {
                    return Err(RegulateAIError::BadRequest(
                        format!("Required variable missing: {}", variable.name)
                    ));
                }
            }
            
            if let Some(value) = context.variables.get(&variable.name) {
                if let Some(processor) = self.processors.get(&variable.variable_type) {
                    processor.validate(value, variable.validation.as_ref())?;
                }
            }
        }
        
        Ok(())
    }
    
    /// Process a single variable
    fn process_variable(
        &self,
        variable: &TemplateVariable,
        context: &TemplateContext,
        warnings: &mut Vec<String>,
    ) -> Result<String, RegulateAIError> {
        let value = context.variables.get(&variable.name)
            .or_else(|| variable.default_value.as_ref().map(|v| &serde_json::Value::String(v.clone())));
        
        match value {
            Some(val) => {
                if let Some(processor) = self.processors.get(&variable.variable_type) {
                    processor.process(val, variable.validation.as_ref())
                } else {
                    warnings.push(format!("No processor found for variable type: {:?}", variable.variable_type));
                    Ok(val.to_string())
                }
            }
            None => {
                if variable.required {
                    Err(RegulateAIError::BadRequest(
                        format!("Required variable not provided: {}", variable.name)
                    ))
                } else {
                    warnings.push(format!("Optional variable not provided: {}", variable.name));
                    Ok(String::new())
                }
            }
        }
    }
    
    /// Check for unprocessed variables in content
    fn check_unprocessed_variables(&self, content: &str, warnings: &mut Vec<String>) -> Result<(), RegulateAIError> {
        let variable_pattern = format!(r"{}\s*(\w+)\s*{}", 
            regex::escape(&self.config.variable_start),
            regex::escape(&self.config.variable_end)
        );
        let regex = Regex::new(&variable_pattern).unwrap();
        
        for captures in regex.captures_iter(content) {
            if let Some(var_name) = captures.get(1) {
                warnings.push(format!("Unprocessed variable found: {}", var_name.as_str()));
            }
        }
        
        Ok(())
    }
}

/// Template update structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateUpdate {
    pub name: Option<String>,
    pub description: Option<String>,
    pub content: Option<String>,
    pub variables: Option<Vec<TemplateVariable>>,
    pub metadata: Option<TemplateMetadata>,
}

/// Template filter for listing
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateFilter {
    pub template_type: Option<DocumentType>,
    pub category: Option<String>,
    pub tags: Option<Vec<String>>,
    pub complexity_level: Option<ComplexityLevel>,
}

// Variable processor implementations
impl VariableProcessor for TextProcessor {
    fn process(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<String, RegulateAIError> {
        let text = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected string value".to_string()))?;
        
        self.validate(value, validation)?;
        Ok(text.to_string())
    }
    
    fn validate(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<(), RegulateAIError> {
        let text = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected string value".to_string()))?;
        
        if let Some(val) = validation {
            if let Some(min_len) = val.min_length {
                if text.len() < min_len {
                    return Err(RegulateAIError::BadRequest(
                        format!("Text too short: {} < {}", text.len(), min_len)
                    ));
                }
            }
            
            if let Some(max_len) = val.max_length {
                if text.len() > max_len {
                    return Err(RegulateAIError::BadRequest(
                        format!("Text too long: {} > {}", text.len(), max_len)
                    ));
                }
            }
            
            if let Some(pattern) = &val.pattern {
                let regex = Regex::new(pattern)
                    .map_err(|e| RegulateAIError::BadRequest(format!("Invalid regex pattern: {}", e)))?;
                if !regex.is_match(text) {
                    return Err(RegulateAIError::BadRequest(
                        format!("Text does not match pattern: {}", pattern)
                    ));
                }
            }
        }
        
        Ok(())
    }
}

impl VariableProcessor for NumberProcessor {
    fn process(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<String, RegulateAIError> {
        let number = value.as_f64()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected number value".to_string()))?;
        
        self.validate(value, validation)?;
        Ok(number.to_string())
    }
    
    fn validate(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<(), RegulateAIError> {
        let number = value.as_f64()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected number value".to_string()))?;
        
        if let Some(val) = validation {
            if let Some(min_val) = val.min_value {
                if number < min_val {
                    return Err(RegulateAIError::BadRequest(
                        format!("Number too small: {} < {}", number, min_val)
                    ));
                }
            }
            
            if let Some(max_val) = val.max_value {
                if number > max_val {
                    return Err(RegulateAIError::BadRequest(
                        format!("Number too large: {} > {}", number, max_val)
                    ));
                }
            }
        }
        
        Ok(())
    }
}

impl VariableProcessor for DateProcessor {
    fn process(&self, value: &serde_json::Value, _validation: Option<&VariableValidation>) -> Result<String, RegulateAIError> {
        let date_str = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected date string".to_string()))?;
        
        // Parse and format date
        let parsed_date = chrono::DateTime::parse_from_rfc3339(date_str)
            .map_err(|e| RegulateAIError::BadRequest(format!("Invalid date format: {}", e)))?;
        
        Ok(parsed_date.format("%Y-%m-%d").to_string())
    }
    
    fn validate(&self, value: &serde_json::Value, _validation: Option<&VariableValidation>) -> Result<(), RegulateAIError> {
        let date_str = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected date string".to_string()))?;
        
        chrono::DateTime::parse_from_rfc3339(date_str)
            .map_err(|e| RegulateAIError::BadRequest(format!("Invalid date format: {}", e)))?;
        
        Ok(())
    }
}

impl VariableProcessor for BooleanProcessor {
    fn process(&self, value: &serde_json::Value, _validation: Option<&VariableValidation>) -> Result<String, RegulateAIError> {
        let boolean = value.as_bool()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected boolean value".to_string()))?;
        
        Ok(if boolean { "Yes" } else { "No" }.to_string())
    }
    
    fn validate(&self, value: &serde_json::Value, _validation: Option<&VariableValidation>) -> Result<(), RegulateAIError> {
        value.as_bool()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected boolean value".to_string()))?;
        
        Ok(())
    }
}

impl VariableProcessor for SelectProcessor {
    fn process(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<String, RegulateAIError> {
        let selected = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected string value".to_string()))?;
        
        self.validate(value, validation)?;
        Ok(selected.to_string())
    }
    
    fn validate(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<(), RegulateAIError> {
        let selected = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected string value".to_string()))?;
        
        if let Some(val) = validation {
            if let Some(allowed_values) = &val.allowed_values {
                if !allowed_values.contains(&selected.to_string()) {
                    return Err(RegulateAIError::BadRequest(
                        format!("Invalid selection: {} not in {:?}", selected, allowed_values)
                    ));
                }
            }
        }
        
        Ok(())
    }
}

impl VariableProcessor for RichTextProcessor {
    fn process(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<String, RegulateAIError> {
        let text = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected string value".to_string()))?;
        
        self.validate(value, validation)?;
        
        // Process rich text (could include markdown to HTML conversion, etc.)
        Ok(text.to_string())
    }
    
    fn validate(&self, value: &serde_json::Value, validation: Option<&VariableValidation>) -> Result<(), RegulateAIError> {
        let text = value.as_str()
            .ok_or_else(|| RegulateAIError::BadRequest("Expected string value".to_string()))?;
        
        if let Some(val) = validation {
            if let Some(max_len) = val.max_length {
                if text.len() > max_len {
                    return Err(RegulateAIError::BadRequest(
                        format!("Rich text too long: {} > {}", text.len(), max_len)
                    ));
                }
            }
        }
        
        Ok(())
    }
}

impl Default for TemplateEngineConfig {
    fn default() -> Self {
        Self {
            variable_start: "{{".to_string(),
            variable_end: "}}".to_string(),
            enable_inheritance: true,
            max_nesting_depth: 10,
            cache_size: 100,
            enable_validation: true,
        }
    }
}

impl Default for TemplateContext {
    fn default() -> Self {
        Self {
            variables: HashMap::new(),
            user_id: None,
            organization_id: None,
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        }
    }
}

// =============================================================================
// TESTING TEMPLATE RENDERING FUNCTIONS
// =============================================================================

/// Render testing dashboard template
pub fn render_testing_dashboard(data: &crate::handlers::TestingDashboardData) -> Result<String, RegulateAIError> {
    // In a real implementation, this would use a template engine like Tera or Handlebars
    // For now, we'll read the HTML template and perform basic substitutions

    let template_path = "services/documentation-service/templates/testing_dashboard.html";
    let template_content = std::fs::read_to_string(template_path)
        .map_err(|e| RegulateAIError::InternalError(format!("Failed to read template: {}", e)))?;

    // Basic template variable substitution
    let mut rendered = template_content;

    // Replace user information
    rendered = rendered.replace("{{ user.username }}", &data.user.username);

    // Replace counts
    rendered = rendered.replace("{{ active_runs | length }}", &data.active_runs.len().to_string());
    rendered = rendered.replace("{{ recent_tests | length }}", &data.recent_tests.len().to_string());

    // In a real implementation, this would properly render the loops and conditionals
    // For demonstration purposes, we'll return the basic template

    Ok(rendered)
}

/// Render test configuration form template
pub fn render_test_configuration_form(data: &crate::handlers::TestConfigurationData) -> Result<String, RegulateAIError> {
    let template_path = "services/documentation-service/templates/test_config_form.html";
    let template_content = std::fs::read_to_string(template_path)
        .unwrap_or_else(|_| {
            // Fallback inline template
            r#"
            <div class="container">
                <h2>Test Configuration</h2>
                <form id="testConfigForm">
                    <div class="mb-3">
                        <label class="form-label">Test Name</label>
                        <input type="text" class="form-control" name="name" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Services</label>
                        <div class="form-check-group">
                            <!-- Services would be dynamically rendered here -->
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Start Tests</button>
                </form>
            </div>
            "#.to_string()
        });

    let mut rendered = template_content;
    rendered = rendered.replace("{{ user.username }}", &data.user.username);

    Ok(rendered)
}

/// Render advanced analytics template
pub fn render_advanced_analytics(data: &crate::handlers::AdvancedAnalyticsData) -> Result<String, RegulateAIError> {
    let template_content = r#"
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RegulateAI - Advanced Test Analytics</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/css/testing.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/testing">
                    <i class="fas fa-shield-alt me-2"></i>RegulateAI Advanced Analytics
                </a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/testing">
                        <i class="fas fa-arrow-left me-1"></i>Back to Dashboard
                    </a>
                </div>
            </div>
        </nav>

        <div class="container-fluid mt-4">
            <div class="row">
                <!-- Coverage Analytics -->
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-chart-pie me-2"></i>Coverage Analytics</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="coverageChart"></canvas>
                            <div class="mt-3">
                                <div class="row text-center">
                                    <div class="col-3">
                                        <div class="stat-number text-success">85.2%</div>
                                        <div class="stat-label">Line Coverage</div>
                                    </div>
                                    <div class="col-3">
                                        <div class="stat-number text-info">78.9%</div>
                                        <div class="stat-label">Branch Coverage</div>
                                    </div>
                                    <div class="col-3">
                                        <div class="stat-number text-warning">92.1%</div>
                                        <div class="stat-label">Function Coverage</div>
                                    </div>
                                    <div class="col-3">
                                        <div class="stat-number text-primary">83.7%</div>
                                        <div class="stat-label">Statement Coverage</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Performance Metrics -->
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-tachometer-alt me-2"></i>Performance Metrics</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="performanceChart"></canvas>
                            <div class="mt-3">
                                <div class="row text-center">
                                    <div class="col-4">
                                        <div class="stat-number text-success">2.3s</div>
                                        <div class="stat-label">Avg Test Time</div>
                                    </div>
                                    <div class="col-4">
                                        <div class="stat-number text-info">15.7</div>
                                        <div class="stat-label">Tests/Second</div>
                                    </div>
                                    <div class="col-4">
                                        <div class="stat-number text-warning">256MB</div>
                                        <div class="stat-label">Memory Usage</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Chaos Testing Controls -->
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-bolt me-2"></i>Chaos Testing</h5>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">Chaos Experiment Type</label>
                                <select class="form-select" id="chaosType">
                                    <option value="ProcessKill">Process Kill</option>
                                    <option value="NetworkLatency">Network Latency</option>
                                    <option value="NetworkPartition">Network Partition</option>
                                    <option value="CpuStress">CPU Stress</option>
                                    <option value="MemoryStress">Memory Stress</option>
                                    <option value="DatabaseFailure">Database Failure</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Target Services</label>
                                <div class="form-check-group">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" value="aml" id="chaos_aml">
                                        <label class="form-check-label" for="chaos_aml">AML Service</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" value="compliance" id="chaos_compliance">
                                        <label class="form-check-label" for="chaos_compliance">Compliance Service</label>
                                    </div>
                                </div>
                            </div>
                            <button class="btn btn-warning" onclick="startChaosTest()">
                                <i class="fas fa-bolt me-2"></i>Start Chaos Test
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Fault Injection Controls -->
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-bug me-2"></i>Fault Injection</h5>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">Fault Type</label>
                                <select class="form-select" id="faultType">
                                    <option value="Exception">Exception</option>
                                    <option value="Timeout">Timeout</option>
                                    <option value="ResourceExhaustion">Resource Exhaustion</option>
                                    <option value="NetworkFault">Network Fault</option>
                                    <option value="AuthFailure">Auth Failure</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Injection Rate (%)</label>
                                <input type="range" class="form-range" id="injectionRate" min="1" max="100" value="10">
                                <div class="text-center"><span id="injectionRateValue">10</span>%</div>
                            </div>
                            <button class="btn btn-danger" onclick="startFaultInjection()">
                                <i class="fas fa-bug me-2"></i>Start Fault Injection
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Flaky Test Detection -->
                <div class="col-12 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-exclamation-triangle me-2"></i>Flaky Test Detection</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-hover" id="flakyTestsTable">
                                    <thead>
                                        <tr>
                                            <th>Test Name</th>
                                            <th>Success Rate</th>
                                            <th>Total Runs</th>
                                            <th>Failed Runs</th>
                                            <th>Flakiness Score</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <!-- Flaky tests will be loaded dynamically -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="/static/js/advanced-analytics.js"></script>
    </body>
    </html>
    "#;

    let mut rendered = template_content.to_string();
    rendered = rendered.replace("{{ user.username }}", &data.user.username);

    Ok(rendered)
}
