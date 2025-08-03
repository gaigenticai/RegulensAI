//! Data Access Layer for AI Orchestration Service
//! 
//! This module provides data access repositories for all AI orchestration entities,
//! implementing CRUD operations and complex queries for agents, workflows, and knowledge base.

use std::sync::Arc;
use chrono::{DateTime, Utc};
use sea_orm::{DatabaseConnection, EntityTrait, QueryFilter, ColumnTrait, QueryOrder, PaginatorTrait};
use tracing::{info, error, warn};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use crate::models::*;

// =============================================================================
// AI AGENT REPOSITORY
// =============================================================================

pub struct AIAgentRepository {
    db: DatabaseConnection,
}

impl AIAgentRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new AI agent
    pub async fn create(&self, request: CreateAIAgentRequest, created_by: Uuid) -> Result<AIAgent, RegulateAIError> {
        info!("Creating AI agent: {}", request.name);
        
        let agent = AIAgent {
            id: Uuid::new_v4(),
            agent_type: request.agent_type,
            name: request.name,
            description: request.description,
            configuration: request.configuration,
            status: "initializing".to_string(),
            capabilities: request.capabilities,
            performance_metrics: serde_json::json!({
                "total_interactions": 0,
                "successful_interactions": 0,
                "failed_interactions": 0,
                "average_response_time_ms": 0.0,
                "error_rate": 0.0,
                "uptime_percentage": 100.0
            }),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: Some(created_by),
            updated_by: Some(created_by),
            version: 1,
        };

        // Insert the agent into the database
        use sea_orm::*;
        let agent_model = crate::entities::ai_agent::ActiveModel {
            id: Set(agent.id),
            name: Set(agent.name.clone()),
            agent_type: Set(agent.agent_type.clone()),
            description: Set(agent.description.clone()),
            configuration: Set(serde_json::to_value(&agent.configuration).unwrap_or_default()),
            status: Set(agent.status.clone()),
            created_at: Set(agent.created_at),
            updated_at: Set(agent.updated_at),
            created_by: Set(agent.created_by),
            updated_by: Set(agent.updated_by),
            version: Set(agent.version as i32),
        };

        let inserted = agent_model.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to insert AI agent: {}", e)))?;

        Ok(agent)
    }

    /// Get AI agent by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<AIAgent>, RegulateAIError> {
        info!("Getting AI agent by ID: {}", id);

        use sea_orm::*;
        let agent = crate::entities::ai_agent::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to query AI agent: {}", e)))?;

        if let Some(model) = agent {
            let ai_agent = AIAgent {
                id: model.id,
                name: model.name,
                agent_type: model.agent_type,
                description: model.description,
                configuration: serde_json::from_value(model.configuration).unwrap_or_default(),
                status: model.status,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            Ok(Some(ai_agent))
        } else {
            Ok(None)
        }
    }

    /// List AI agents with pagination
    pub async fn list(&self, page: u64, per_page: u64, agent_type: Option<String>) -> Result<Vec<AIAgent>, RegulateAIError> {
        info!("Listing AI agents - page: {}, per_page: {}, type: {:?}", page, per_page, agent_type);

        use sea_orm::*;
        let mut query = crate::entities::ai_agent::Entity::find();

        // Apply type filter if provided
        if let Some(agent_type_filter) = agent_type {
            query = query.filter(crate::entities::ai_agent::Column::AgentType.eq(agent_type_filter));
        }

        // Apply pagination
        let offset = page * per_page;
        let agents = query
            .offset(offset)
            .limit(per_page)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to list AI agents: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in agents {
            let ai_agent = AIAgent {
                id: model.id,
                name: model.name,
                agent_type: model.agent_type,
                description: model.description,
                configuration: serde_json::from_value(model.configuration).unwrap_or_default(),
                status: model.status,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(ai_agent);
        }

        Ok(result)
    }

    /// Update AI agent
    pub async fn update(&self, id: Uuid, request: UpdateAIAgentRequest, updated_by: Uuid) -> Result<AIAgent, RegulateAIError> {
        info!("Updating AI agent: {}", id);

        use sea_orm::*;

        // First, find the existing agent
        let existing_agent = crate::entities::ai_agent::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find AI agent: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("AI agent not found".to_string()))?;

        // Update the agent
        let mut agent_model: crate::entities::ai_agent::ActiveModel = existing_agent.into();

        if let Some(name) = request.name {
            agent_model.name = Set(name);
        }
        if let Some(description) = request.description {
            agent_model.description = Set(description);
        }
        if let Some(configuration) = request.configuration {
            agent_model.configuration = Set(serde_json::to_value(configuration).unwrap_or_default());
        }
        if let Some(status) = request.status {
            agent_model.status = Set(status);
        }

        agent_model.updated_at = Set(Utc::now());
        agent_model.updated_by = Set(Some(updated_by));
        agent_model.version = Set(agent_model.version.unwrap() + 1);

        let updated_model = agent_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update AI agent: {}", e)))?;

        // Convert back to domain model
        let updated_agent = AIAgent {
            id: updated_model.id,
            name: updated_model.name,
            agent_type: updated_model.agent_type,
            description: updated_model.description,
            configuration: serde_json::from_value(updated_model.configuration).unwrap_or_default(),
            status: updated_model.status,
            created_at: updated_model.created_at,
            updated_at: updated_model.updated_at,
            created_by: updated_model.created_by,
            updated_by: updated_model.updated_by,
            version: updated_model.version as u32,
        };

        Ok(updated_agent)
    }

    /// Delete AI agent
    pub async fn delete(&self, id: Uuid) -> Result<(), RegulateAIError> {
        info!("Deleting AI agent: {}", id);

        use sea_orm::*;

        let delete_result = crate::entities::ai_agent::Entity::delete_by_id(id)
            .exec(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to delete AI agent: {}", e)))?;

        if delete_result.rows_affected == 0 {
            return Err(RegulateAIError::NotFound("AI agent not found".to_string()));
        }

        Ok(())
    }

    /// Update agent performance metrics
    pub async fn update_performance_metrics(&self, id: Uuid, metrics: AgentPerformanceMetrics) -> Result<(), RegulateAIError> {
        info!("Updating performance metrics for agent: {}", id);

        use sea_orm::*;

        // Find the existing agent
        let existing_agent = crate::entities::ai_agent::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find AI agent: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("AI agent not found".to_string()))?;

        // Update the agent with performance metrics
        let mut agent_model: crate::entities::ai_agent::ActiveModel = existing_agent.into();

        // Store metrics in configuration field as JSON
        let mut config = serde_json::from_value(agent_model.configuration.clone().unwrap())
            .unwrap_or_else(|_| serde_json::json!({}));
        config["performance_metrics"] = serde_json::to_value(&metrics)
            .map_err(|e| RegulateAIError::SerializationError(format!("Failed to serialize metrics: {}", e)))?;

        agent_model.configuration = Set(config);
        agent_model.updated_at = Set(Utc::now());

        agent_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update agent metrics: {}", e)))?;

        Ok(())
    }

    /// Get agents by type
    pub async fn get_by_type(&self, agent_type: &str) -> Result<Vec<AIAgent>, RegulateAIError> {
        info!("Getting agents by type: {}", agent_type);

        use sea_orm::*;
        let agents = crate::entities::ai_agent::Entity::find()
            .filter(crate::entities::ai_agent::Column::AgentType.eq(agent_type))
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to query agents by type: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in agents {
            let ai_agent = AIAgent {
                id: model.id,
                name: model.name,
                agent_type: model.agent_type,
                description: model.description,
                configuration: serde_json::from_value(model.configuration).unwrap_or_default(),
                status: model.status,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(ai_agent);
        }

        Ok(result)
    }
}

// =============================================================================
// WORKFLOW TEMPLATE REPOSITORY
// =============================================================================

pub struct WorkflowTemplateRepository {
    db: DatabaseConnection,
}

impl WorkflowTemplateRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new workflow template
    pub async fn create(&self, request: CreateWorkflowTemplateRequest, created_by: Uuid) -> Result<WorkflowTemplate, RegulateAIError> {
        info!("Creating workflow template: {}", request.name);
        
        let template = WorkflowTemplate {
            id: Uuid::new_v4(),
            name: request.name,
            description: request.description,
            template_type: request.template_type,
            template_definition: request.template_definition,
            trigger_conditions: request.trigger_conditions,
            default_parameters: request.default_parameters.unwrap_or_else(|| serde_json::json!({})),
            is_active: true,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: Some(created_by),
            updated_by: Some(created_by),
            version: 1,
        };

        // Insert the workflow template into the database
        use sea_orm::*;
        let template_model = crate::entities::workflow_template::ActiveModel {
            id: Set(template.id),
            name: Set(template.name.clone()),
            description: Set(template.description.clone()),
            template_type: Set(template.template_type.clone()),
            template_definition: Set(serde_json::to_value(&template.template_definition).unwrap_or_default()),
            trigger_conditions: Set(serde_json::to_value(&template.trigger_conditions).unwrap_or_default()),
            default_parameters: Set(template.default_parameters.clone()),
            is_active: Set(template.is_active),
            created_at: Set(template.created_at),
            updated_at: Set(template.updated_at),
            created_by: Set(template.created_by),
            updated_by: Set(template.updated_by),
            version: Set(template.version as i32),
        };

        let inserted = template_model.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to insert workflow template: {}", e)))?;

        Ok(template)
    }

    /// Get workflow template by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<WorkflowTemplate>, RegulateAIError> {
        info!("Getting workflow template by ID: {}", id);

        use sea_orm::*;
        let template = crate::entities::workflow_template::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to query workflow template: {}", e)))?;

        if let Some(model) = template {
            let workflow_template = WorkflowTemplate {
                id: model.id,
                name: model.name,
                description: model.description,
                template_type: model.template_type,
                template_definition: serde_json::from_value(model.template_definition).unwrap_or_default(),
                trigger_conditions: serde_json::from_value(model.trigger_conditions).unwrap_or_default(),
                default_parameters: model.default_parameters,
                is_active: model.is_active,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            Ok(Some(workflow_template))
        } else {
            Ok(None)
        }
    }

    /// List workflow templates
    pub async fn list(&self, page: u64, per_page: u64, template_type: Option<String>) -> Result<Vec<WorkflowTemplate>, RegulateAIError> {
        info!("Listing workflow templates - page: {}, per_page: {}, type: {:?}", page, per_page, template_type);

        use sea_orm::*;
        let mut query = crate::entities::workflow_template::Entity::find();

        // Apply type filter if provided
        if let Some(template_type_filter) = template_type {
            query = query.filter(crate::entities::workflow_template::Column::TemplateType.eq(template_type_filter));
        }

        // Apply pagination
        let offset = page * per_page;
        let templates = query
            .offset(offset)
            .limit(per_page)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to list workflow templates: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in templates {
            let workflow_template = WorkflowTemplate {
                id: model.id,
                name: model.name,
                description: model.description,
                template_type: model.template_type,
                template_definition: serde_json::from_value(model.template_definition).unwrap_or_default(),
                trigger_conditions: serde_json::from_value(model.trigger_conditions).unwrap_or_default(),
                default_parameters: model.default_parameters,
                is_active: model.is_active,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(workflow_template);
        }

        Ok(result)
    }

    /// Get active templates by trigger
    pub async fn get_by_trigger(&self, trigger: &str) -> Result<Vec<WorkflowTemplate>, RegulateAIError> {
        info!("Getting workflow templates by trigger: {}", trigger);

        use sea_orm::*;
        let templates = crate::entities::workflow_template::Entity::find()
            .filter(crate::entities::workflow_template::Column::IsActive.eq(true))
            .filter(crate::entities::workflow_template::Column::TriggerConditions.contains(trigger))
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to query templates by trigger: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in templates {
            let workflow_template = WorkflowTemplate {
                id: model.id,
                name: model.name,
                description: model.description,
                template_type: model.template_type,
                template_definition: serde_json::from_value(model.template_definition).unwrap_or_default(),
                trigger_conditions: serde_json::from_value(model.trigger_conditions).unwrap_or_default(),
                default_parameters: model.default_parameters,
                is_active: model.is_active,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(workflow_template);
        }

        Ok(result)
    }
}

// =============================================================================
// WORKFLOW INSTANCE REPOSITORY
// =============================================================================

pub struct WorkflowInstanceRepository {
    db: DatabaseConnection,
}

impl WorkflowInstanceRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new workflow instance
    pub async fn create(&self, request: CreateWorkflowInstanceRequest, created_by: Uuid) -> Result<WorkflowInstance, RegulateAIError> {
        info!("Creating workflow instance: {}", request.name);
        
        let instance = WorkflowInstance {
            id: Uuid::new_v4(),
            template_id: request.template_id,
            name: request.name,
            description: request.description,
            workflow_definition: request.workflow_definition.unwrap_or_else(|| serde_json::json!({})),
            input_parameters: request.input_parameters,
            status: "created".to_string(),
            current_step: None,
            execution_context: serde_json::json!({}),
            started_at: None,
            completed_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: Some(created_by),
            updated_by: Some(created_by),
            version: 1,
        };

        // Insert the workflow instance into the database
        use sea_orm::*;
        let instance_model = crate::entities::workflow_instance::ActiveModel {
            id: Set(instance.id),
            template_id: Set(instance.template_id),
            name: Set(instance.name.clone()),
            description: Set(instance.description.clone()),
            workflow_definition: Set(instance.workflow_definition.clone()),
            input_parameters: Set(instance.input_parameters.clone()),
            status: Set(instance.status.clone()),
            current_step: Set(instance.current_step.clone()),
            execution_context: Set(instance.execution_context.clone()),
            started_at: Set(instance.started_at),
            completed_at: Set(instance.completed_at),
            created_at: Set(instance.created_at),
            updated_at: Set(instance.updated_at),
            created_by: Set(instance.created_by),
            updated_by: Set(instance.updated_by),
            version: Set(instance.version as i32),
        };

        let inserted = instance_model.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to insert workflow instance: {}", e)))?;

        Ok(instance)
    }

    /// Get workflow instance by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<WorkflowInstance>, RegulateAIError> {
        info!("Getting workflow instance by ID: {}", id);

        use sea_orm::*;
        let instance = crate::entities::workflow_instance::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to query workflow instance: {}", e)))?;

        if let Some(model) = instance {
            let workflow_instance = WorkflowInstance {
                id: model.id,
                template_id: model.template_id,
                name: model.name,
                description: model.description,
                workflow_definition: model.workflow_definition,
                input_parameters: model.input_parameters,
                status: model.status,
                current_step: model.current_step,
                execution_context: model.execution_context,
                started_at: model.started_at,
                completed_at: model.completed_at,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            Ok(Some(workflow_instance))
        } else {
            Ok(None)
        }
    }

    /// Update workflow instance status
    pub async fn update_status(&self, id: Uuid, status: &str, current_step: Option<String>, updated_by: Uuid) -> Result<WorkflowInstance, RegulateAIError> {
        info!("Updating workflow instance status: {} to {}", id, status);

        use sea_orm::*;

        // Find the existing workflow instance
        let existing_instance = crate::entities::workflow_instance::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find workflow instance: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("Workflow instance not found".to_string()))?;

        // Update the workflow instance
        let mut instance_model: crate::entities::workflow_instance::ActiveModel = existing_instance.into();
        instance_model.status = Set(status.to_string());
        if let Some(step) = current_step {
            instance_model.current_step = Set(Some(step));
        }
        instance_model.updated_at = Set(Utc::now());
        instance_model.updated_by = Set(Some(updated_by));

        // Set completion time if status is completed
        if status == "completed" {
            instance_model.completed_at = Set(Some(Utc::now()));
        }

        let updated_model = instance_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update workflow instance: {}", e)))?;

        // Convert back to domain model
        let updated_instance = WorkflowInstance {
            id: updated_model.id,
            template_id: updated_model.template_id,
            name: updated_model.name,
            description: updated_model.description,
            workflow_definition: updated_model.workflow_definition,
            input_parameters: updated_model.input_parameters,
            status: updated_model.status,
            current_step: updated_model.current_step,
            execution_context: updated_model.execution_context,
            started_at: updated_model.started_at,
            completed_at: updated_model.completed_at,
            created_at: updated_model.created_at,
            updated_at: updated_model.updated_at,
            created_by: updated_model.created_by,
            updated_by: updated_model.updated_by,
            version: updated_model.version as u32,
        };

        Ok(updated_instance)
    }

    /// Update execution context
    pub async fn update_execution_context(&self, id: Uuid, context: serde_json::Value, updated_by: Uuid) -> Result<(), RegulateAIError> {
        info!("Updating execution context for workflow instance: {}", id);

        use sea_orm::*;

        // Find the existing workflow instance
        let existing_instance = crate::entities::workflow_instance::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find workflow instance: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("Workflow instance not found".to_string()))?;

        // Update the execution context
        let mut instance_model: crate::entities::workflow_instance::ActiveModel = existing_instance.into();
        instance_model.execution_context = Set(Some(context));
        instance_model.updated_at = Set(Utc::now());
        instance_model.updated_by = Set(Some(updated_by));

        instance_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update execution context: {}", e)))?;

        Ok(())
    }

    /// List workflow instances
    pub async fn list(&self, page: u64, per_page: u64, status: Option<String>) -> Result<Vec<WorkflowInstance>, RegulateAIError> {
        info!("Listing workflow instances - page: {}, per_page: {}, status: {:?}", page, per_page, status);

        use sea_orm::*;
        let mut query = crate::entities::workflow_instance::Entity::find();

        // Apply status filter if provided
        if let Some(status_filter) = status {
            query = query.filter(crate::entities::workflow_instance::Column::Status.eq(status_filter));
        }

        // Apply pagination
        let offset = page * per_page;
        let instances = query
            .offset(offset)
            .limit(per_page)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to list workflow instances: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in instances {
            let workflow_instance = WorkflowInstance {
                id: model.id,
                template_id: model.template_id,
                name: model.name,
                description: model.description,
                workflow_definition: model.workflow_definition,
                input_parameters: model.input_parameters,
                status: model.status,
                current_step: model.current_step,
                execution_context: model.execution_context,
                started_at: model.started_at,
                completed_at: model.completed_at,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(workflow_instance);
        }

        Ok(result)
    }

    /// Get active workflow instances
    pub async fn get_active_instances(&self) -> Result<Vec<WorkflowInstance>, RegulateAIError> {
        info!("Getting active workflow instances");

        use sea_orm::*;
        let instances = crate::entities::workflow_instance::Entity::find()
            .filter(crate::entities::workflow_instance::Column::Status.is_in(vec!["running", "pending", "paused"]))
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to get active workflow instances: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in instances {
            let workflow_instance = WorkflowInstance {
                id: model.id,
                template_id: model.template_id,
                name: model.name,
                description: model.description,
                workflow_definition: model.workflow_definition,
                input_parameters: model.input_parameters,
                status: model.status,
                current_step: model.current_step,
                execution_context: model.execution_context,
                started_at: model.started_at,
                completed_at: model.completed_at,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(workflow_instance);
        }

        Ok(result)
    }
}

// =============================================================================
// AGENT INTERACTION REPOSITORY
// =============================================================================

pub struct AgentInteractionRepository {
    db: DatabaseConnection,
}

impl AgentInteractionRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new agent interaction
    pub async fn create(&self, request: CreateAgentInteractionRequest, created_by: Uuid) -> Result<AgentInteraction, RegulateAIError> {
        info!("Creating agent interaction for agent: {}", request.agent_id);
        
        let interaction = AgentInteraction {
            id: Uuid::new_v4(),
            agent_id: request.agent_id,
            interaction_type: request.interaction_type,
            request_data: request.request_data,
            response_data: None,
            status: "pending".to_string(),
            processing_time_ms: None,
            error_message: None,
            workflow_instance_id: request.workflow_instance_id,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: Some(created_by),
            version: 1,
        };

        // Insert the agent interaction into the database
        use sea_orm::*;
        let interaction_model = crate::entities::agent_interaction::ActiveModel {
            id: Set(interaction.id),
            agent_id: Set(interaction.agent_id),
            interaction_type: Set(interaction.interaction_type.clone()),
            request_data: Set(interaction.request_data.clone()),
            response_data: Set(interaction.response_data.clone()),
            status: Set(interaction.status.clone()),
            processing_time_ms: Set(interaction.processing_time_ms),
            error_message: Set(interaction.error_message.clone()),
            workflow_instance_id: Set(interaction.workflow_instance_id),
            created_at: Set(interaction.created_at),
            updated_at: Set(interaction.updated_at),
            created_by: Set(interaction.created_by),
            version: Set(interaction.version as i32),
        };

        let inserted = interaction_model.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to insert agent interaction: {}", e)))?;

        Ok(interaction)
    }

    /// Update interaction with response
    pub async fn update_response(&self, id: Uuid, response_data: serde_json::Value, processing_time_ms: i32) -> Result<AgentInteraction, RegulateAIError> {
        info!("Updating agent interaction response: {}", id);

        use sea_orm::*;

        // Find the existing interaction
        let existing_interaction = crate::entities::agent_interaction::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find agent interaction: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("Agent interaction not found".to_string()))?;

        // Update the interaction with response
        let mut interaction_model: crate::entities::agent_interaction::ActiveModel = existing_interaction.into();
        interaction_model.response_data = Set(Some(response_data.clone()));
        interaction_model.processing_time_ms = Set(Some(processing_time_ms));
        interaction_model.status = Set("completed".to_string());
        interaction_model.updated_at = Set(Utc::now());

        let updated_model = interaction_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update agent interaction: {}", e)))?;

        // Convert back to domain model
        let updated_interaction = AgentInteraction {
            id: updated_model.id,
            agent_id: updated_model.agent_id,
            interaction_type: updated_model.interaction_type,
            request_data: updated_model.request_data,
            response_data: updated_model.response_data,
            status: updated_model.status,
            processing_time_ms: updated_model.processing_time_ms,
            error_message: updated_model.error_message,
            workflow_instance_id: updated_model.workflow_instance_id,
            created_at: updated_model.created_at,
            updated_at: updated_model.updated_at,
            created_by: updated_model.created_by,
            version: updated_model.version as u32,
        };

        Ok(updated_interaction)
    }

    /// Update interaction with error
    pub async fn update_error(&self, id: Uuid, error_message: String) -> Result<AgentInteraction, RegulateAIError> {
        info!("Updating agent interaction error: {}", id);

        use sea_orm::*;

        // Find the existing interaction
        let existing_interaction = crate::entities::agent_interaction::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find agent interaction: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("Agent interaction not found".to_string()))?;

        // Update the interaction with error
        let mut interaction_model: crate::entities::agent_interaction::ActiveModel = existing_interaction.into();
        interaction_model.status = Set("error".to_string());
        interaction_model.error_message = Set(Some(error_message.clone()));
        interaction_model.updated_at = Set(Utc::now());

        let updated_model = interaction_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update agent interaction: {}", e)))?;

        // Convert back to domain model
        let updated_interaction = AgentInteraction {
            id: updated_model.id,
            agent_id: updated_model.agent_id,
            interaction_type: updated_model.interaction_type,
            request_data: updated_model.request_data,
            response_data: updated_model.response_data,
            status: updated_model.status,
            processing_time_ms: updated_model.processing_time_ms,
            error_message: updated_model.error_message,
            workflow_instance_id: updated_model.workflow_instance_id,
            created_at: updated_model.created_at,
            updated_at: updated_model.updated_at,
            created_by: updated_model.created_by,
            version: updated_model.version as u32,
        };

        Ok(updated_interaction)
    }

    /// Get interactions by agent
    pub async fn get_by_agent(&self, agent_id: Uuid, page: u64, per_page: u64) -> Result<Vec<AgentInteraction>, RegulateAIError> {
        info!("Getting interactions for agent: {}", agent_id);

        use sea_orm::*;

        // Apply pagination
        let offset = page * per_page;
        let interactions = crate::entities::agent_interaction::Entity::find()
            .filter(crate::entities::agent_interaction::Column::AgentId.eq(agent_id))
            .offset(offset)
            .limit(per_page)
            .order_by_desc(crate::entities::agent_interaction::Column::CreatedAt)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to get interactions by agent: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in interactions {
            let agent_interaction = AgentInteraction {
                id: model.id,
                agent_id: model.agent_id,
                interaction_type: model.interaction_type,
                request_data: model.request_data,
                response_data: model.response_data,
                status: model.status,
                processing_time_ms: model.processing_time_ms,
                error_message: model.error_message,
                workflow_instance_id: model.workflow_instance_id,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                version: model.version as u32,
            };
            result.push(agent_interaction);
        }

        Ok(result)
    }

    /// Get interactions by workflow
    pub async fn get_by_workflow(&self, workflow_id: Uuid) -> Result<Vec<AgentInteraction>, RegulateAIError> {
        info!("Getting interactions for workflow: {}", workflow_id);

        use sea_orm::*;
        let interactions = crate::entities::agent_interaction::Entity::find()
            .filter(crate::entities::agent_interaction::Column::WorkflowInstanceId.eq(Some(workflow_id)))
            .order_by_desc(crate::entities::agent_interaction::Column::CreatedAt)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to get interactions by workflow: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in interactions {
            let agent_interaction = AgentInteraction {
                id: model.id,
                agent_id: model.agent_id,
                interaction_type: model.interaction_type,
                request_data: model.request_data,
                response_data: model.response_data,
                status: model.status,
                processing_time_ms: model.processing_time_ms,
                error_message: model.error_message,
                workflow_instance_id: model.workflow_instance_id,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                version: model.version as u32,
            };
            result.push(agent_interaction);
        }

        Ok(result)
    }
}

// =============================================================================
// KNOWLEDGE BASE REPOSITORY
// =============================================================================

pub struct KnowledgeBaseRepository {
    db: DatabaseConnection,
}

impl KnowledgeBaseRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }

    /// Create a new knowledge base entry
    pub async fn create(&self, request: CreateKnowledgeBaseEntryRequest, created_by: Uuid) -> Result<KnowledgeBaseEntry, RegulateAIError> {
        info!("Creating knowledge base entry: {}", request.title);
        
        let entry = KnowledgeBaseEntry {
            id: Uuid::new_v4(),
            title: request.title,
            content: request.content,
            content_type: request.content_type,
            category: request.category,
            tags: request.tags,
            metadata: request.metadata.unwrap_or_else(|| serde_json::json!({})),
            embedding_vector: None, // Would be generated by ML service
            source_url: request.source_url,
            source_type: request.source_type,
            confidence_score: None,
            is_verified: false,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            created_by: Some(created_by),
            updated_by: Some(created_by),
            version: 1,
        };

        // Insert the knowledge base entry into the database
        use sea_orm::*;
        let entry_model = crate::entities::knowledge_base_entry::ActiveModel {
            id: Set(entry.id),
            title: Set(entry.title.clone()),
            content: Set(entry.content.clone()),
            content_type: Set(entry.content_type.clone()),
            category: Set(entry.category.clone()),
            tags: Set(serde_json::to_value(&entry.tags).unwrap_or_default()),
            metadata: Set(entry.metadata.clone()),
            embedding_vector: Set(entry.embedding_vector.clone()),
            source_url: Set(entry.source_url.clone()),
            source_type: Set(entry.source_type.clone()),
            confidence_score: Set(entry.confidence_score),
            is_verified: Set(entry.is_verified),
            created_at: Set(entry.created_at),
            updated_at: Set(entry.updated_at),
            created_by: Set(entry.created_by),
            updated_by: Set(entry.updated_by),
            version: Set(entry.version as i32),
        };

        let inserted = entry_model.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to insert knowledge base entry: {}", e)))?;

        Ok(entry)
    }

    /// Search knowledge base entries
    pub async fn search(&self, query: ContextualSearchQuery) -> Result<Vec<SearchResultWithScore>, RegulateAIError> {
        info!("Searching knowledge base with query: {}", query.query);

        use sea_orm::*;

        // Perform text-based search first
        let mut db_query = crate::entities::knowledge_base_entry::Entity::find();

        // Apply text search filters
        if !query.query.is_empty() {
            db_query = db_query.filter(
                Condition::any()
                    .add(crate::entities::knowledge_base_entry::Column::Title.contains(&query.query))
                    .add(crate::entities::knowledge_base_entry::Column::Content.contains(&query.query))
                    .add(crate::entities::knowledge_base_entry::Column::Tags.contains(&query.query))
            );
        }

        // Apply category filter
        if let Some(category) = &query.category {
            db_query = db_query.filter(crate::entities::knowledge_base_entry::Column::Category.eq(category));
        }

        // Apply content type filter
        if let Some(content_type) = &query.content_type {
            db_query = db_query.filter(crate::entities::knowledge_base_entry::Column::ContentType.eq(content_type));
        }

        // Apply pagination
        let entries = db_query
            .limit(query.limit.unwrap_or(10))
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to search knowledge base: {}", e)))?;

        // Convert to search results with scores
        let mut results = Vec::new();
        for entry in entries {
            // Calculate relevance score based on text matching
            let score = calculate_relevance_score(&query.query, &entry.title, &entry.content);

            let search_result = SearchResultWithScore {
                entry: KnowledgeBaseEntry {
                    id: entry.id,
                    title: entry.title,
                    content: entry.content,
                    content_type: entry.content_type,
                    category: entry.category,
                    tags: serde_json::from_value(entry.tags).unwrap_or_default(),
                    metadata: entry.metadata,
                    embedding_vector: entry.embedding_vector,
                    source_url: entry.source_url,
                    source_type: entry.source_type,
                    confidence_score: entry.confidence_score,
                    is_verified: entry.is_verified,
                    created_at: entry.created_at,
                    updated_at: entry.updated_at,
                    created_by: entry.created_by,
                    updated_by: entry.updated_by,
                    version: entry.version as u32,
                },
                relevance_score: score,
            };
            results.push(search_result);
        }

        // Sort by relevance score
        results.sort_by(|a, b| b.relevance_score.partial_cmp(&a.relevance_score).unwrap_or(std::cmp::Ordering::Equal));

        Ok(results)
    }

    /// Get knowledge base entry by ID
    pub async fn get_by_id(&self, id: Uuid) -> Result<Option<KnowledgeBaseEntry>, RegulateAIError> {
        info!("Getting knowledge base entry by ID: {}", id);

        use sea_orm::*;
        let entry = crate::entities::knowledge_base_entry::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to query knowledge base entry: {}", e)))?;

        if let Some(model) = entry {
            let knowledge_entry = KnowledgeBaseEntry {
                id: model.id,
                title: model.title,
                content: model.content,
                content_type: model.content_type,
                category: model.category,
                tags: serde_json::from_value(model.tags).unwrap_or_default(),
                metadata: model.metadata,
                embedding_vector: model.embedding_vector,
                source_url: model.source_url,
                source_type: model.source_type,
                confidence_score: model.confidence_score,
                is_verified: model.is_verified,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            Ok(Some(knowledge_entry))
        } else {
            Ok(None)
        }
    }

    /// List knowledge base entries
    pub async fn list(&self, page: u64, per_page: u64, category: Option<String>) -> Result<Vec<KnowledgeBaseEntry>, RegulateAIError> {
        info!("Listing knowledge base entries - page: {}, per_page: {}, category: {:?}", page, per_page, category);

        use sea_orm::*;
        let mut query = crate::entities::knowledge_base_entry::Entity::find();

        // Apply category filter if provided
        if let Some(category_filter) = category {
            query = query.filter(crate::entities::knowledge_base_entry::Column::Category.eq(category_filter));
        }

        // Apply pagination
        let offset = page * per_page;
        let entries = query
            .offset(offset)
            .limit(per_page)
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to list knowledge base entries: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in entries {
            let knowledge_entry = KnowledgeBaseEntry {
                id: model.id,
                title: model.title,
                content: model.content,
                content_type: model.content_type,
                category: model.category,
                tags: serde_json::from_value(model.tags).unwrap_or_default(),
                metadata: model.metadata,
                embedding_vector: model.embedding_vector,
                source_url: model.source_url,
                source_type: model.source_type,
                confidence_score: model.confidence_score,
                is_verified: model.is_verified,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(knowledge_entry);
        }

        Ok(result)
    }

    /// Update embedding vector
    pub async fn update_embedding(&self, id: Uuid, embedding: Vec<f32>) -> Result<(), RegulateAIError> {
        info!("Updating embedding for knowledge base entry: {}", id);

        use sea_orm::*;

        // Find the existing entry
        let existing_entry = crate::entities::knowledge_base_entry::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to find knowledge base entry: {}", e)))?
            .ok_or_else(|| RegulateAIError::NotFound("Knowledge base entry not found".to_string()))?;

        // Update the embedding vector
        let mut entry_model: crate::entities::knowledge_base_entry::ActiveModel = existing_entry.into();
        entry_model.embedding_vector = Set(Some(embedding));
        entry_model.updated_at = Set(Utc::now());

        entry_model.update(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to update embedding: {}", e)))?;

        Ok(())
    }

    /// Get entries by category
    pub async fn get_by_category(&self, category: &str, limit: Option<u64>) -> Result<Vec<KnowledgeBaseEntry>, RegulateAIError> {
        info!("Getting knowledge base entries by category: {}", category);

        use sea_orm::*;
        let mut query = crate::entities::knowledge_base_entry::Entity::find()
            .filter(crate::entities::knowledge_base_entry::Column::Category.eq(category));

        if let Some(limit_val) = limit {
            query = query.limit(limit_val);
        }

        let entries = query
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to get entries by category: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in entries {
            let knowledge_entry = KnowledgeBaseEntry {
                id: model.id,
                title: model.title,
                content: model.content,
                content_type: model.content_type,
                category: model.category,
                tags: serde_json::from_value(model.tags).unwrap_or_default(),
                metadata: model.metadata,
                embedding_vector: model.embedding_vector,
                source_url: model.source_url,
                source_type: model.source_type,
                confidence_score: model.confidence_score,
                is_verified: model.is_verified,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(knowledge_entry);
        }

        Ok(result)
    }

    /// Get entries by tags
    pub async fn get_by_tags(&self, tags: &[String], limit: Option<u64>) -> Result<Vec<KnowledgeBaseEntry>, RegulateAIError> {
        info!("Getting knowledge base entries by tags: {:?}", tags);

        use sea_orm::*;
        let mut query = crate::entities::knowledge_base_entry::Entity::find();

        // Filter by tags (check if any of the provided tags match)
        for tag in tags {
            query = query.filter(crate::entities::knowledge_base_entry::Column::Tags.contains(tag));
        }

        if let Some(limit_val) = limit {
            query = query.limit(limit_val);
        }

        let entries = query
            .all(&self.db)
            .await
            .map_err(|e| RegulateAIError::DatabaseError(format!("Failed to get entries by tags: {}", e)))?;

        // Convert to domain models
        let mut result = Vec::new();
        for model in entries {
            let knowledge_entry = KnowledgeBaseEntry {
                id: model.id,
                title: model.title,
                content: model.content,
                content_type: model.content_type,
                category: model.category,
                tags: serde_json::from_value(model.tags).unwrap_or_default(),
                metadata: model.metadata,
                embedding_vector: model.embedding_vector,
                source_url: model.source_url,
                source_type: model.source_type,
                confidence_score: model.confidence_score,
                is_verified: model.is_verified,
                created_at: model.created_at,
                updated_at: model.updated_at,
                created_by: model.created_by,
                updated_by: model.updated_by,
                version: model.version as u32,
            };
            result.push(knowledge_entry);
        }

        Ok(result)
    }
}

/// Calculate relevance score for search results
fn calculate_relevance_score(query: &str, title: &str, content: &str) -> f32 {
    let query_lower = query.to_lowercase();
    let title_lower = title.to_lowercase();
    let content_lower = content.to_lowercase();

    let mut score = 0.0;

    // Title matches are weighted higher
    if title_lower.contains(&query_lower) {
        score += 10.0;
    }

    // Content matches
    if content_lower.contains(&query_lower) {
        score += 5.0;
    }

    // Word-level matching
    let query_words: Vec<&str> = query_lower.split_whitespace().collect();
    for word in query_words {
        if title_lower.contains(word) {
            score += 3.0;
        }
        if content_lower.contains(word) {
            score += 1.0;
        }
    }

    // Normalize score
    score / (query.len() as f32).max(1.0)
}
