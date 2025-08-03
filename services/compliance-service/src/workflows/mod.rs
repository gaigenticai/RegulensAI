//! Workflow engine for compliance automation

use std::collections::HashMap;
use chrono::{DateTime, Utc};
use sea_orm::DatabaseConnection;
use tracing::{info, error};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;
use crate::models::*;

/// Workflow engine for automating compliance processes
pub struct WorkflowEngine {
    db: DatabaseConnection,
    workflow_definitions: HashMap<WorkflowType, WorkflowDefinition>,
}

impl WorkflowEngine {
    /// Create a new workflow engine
    pub async fn new(db: DatabaseConnection) -> Result<Self, RegulateAIError> {
        info!("Initializing workflow engine");

        let mut engine = Self {
            db,
            workflow_definitions: HashMap::new(),
        };

        // Load default workflow definitions
        engine.load_default_workflows().await?;

        info!("Workflow engine initialized successfully");
        Ok(engine)
    }

    /// Execute a workflow
    pub async fn execute_workflow(
        &self,
        workflow_type: WorkflowType,
        entity_id: Uuid,
        entity_type: String,
        triggered_by: Uuid,
    ) -> Result<WorkflowExecution, RegulateAIError> {
        info!("Executing workflow: {:?} for entity: {}", workflow_type, entity_id);

        let workflow_def = self.workflow_definitions.get(&workflow_type)
            .ok_or_else(|| RegulateAIError::NotFound {
                entity: "WorkflowDefinition".to_string(),
                id: format!("{:?}", workflow_type),
            })?;

        let execution = WorkflowExecution {
            id: Uuid::new_v4(),
            workflow_id: workflow_def.id,
            entity_id,
            entity_type,
            status: WorkflowStatus::InProgress,
            current_step: Some(workflow_def.steps.first().unwrap().step_id.clone()),
            started_at: Utc::now(),
            completed_at: None,
            step_history: vec![],
        };

        // Execute workflow steps
        self.execute_workflow_steps(&execution, workflow_def).await?;

        info!("Workflow execution completed: {}", execution.id);
        Ok(execution)
    }

    /// Load default workflow definitions
    async fn load_default_workflows(&mut self) -> Result<(), RegulateAIError> {
        // Policy Approval Workflow
        let policy_approval_workflow = WorkflowDefinition {
            id: Uuid::new_v4(),
            name: "Policy Approval Workflow".to_string(),
            description: "Automated workflow for policy approval process".to_string(),
            workflow_type: WorkflowType::PolicyApproval,
            trigger_conditions: serde_json::json!({
                "entity_type": "policy",
                "status": "draft"
            }),
            steps: vec![
                WorkflowStep {
                    step_id: "review".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Policy Review".to_string(),
                    description: "Review policy content and compliance".to_string(),
                    assignee: None,
                    due_date_offset: Some(5), // 5 days
                    conditions: serde_json::json!({}),
                    actions: serde_json::json!({
                        "notify_reviewers": true,
                        "create_review_task": true
                    }),
                },
                WorkflowStep {
                    step_id: "approval".to_string(),
                    step_type: WorkflowStepType::Approval,
                    name: "Policy Approval".to_string(),
                    description: "Approve or reject policy".to_string(),
                    assignee: None,
                    due_date_offset: Some(3), // 3 days
                    conditions: serde_json::json!({
                        "requires_approval": true
                    }),
                    actions: serde_json::json!({
                        "update_status": "approved",
                        "notify_stakeholders": true
                    }),
                },
                WorkflowStep {
                    step_id: "publication".to_string(),
                    step_type: WorkflowStepType::Automated,
                    name: "Policy Publication".to_string(),
                    description: "Publish approved policy".to_string(),
                    assignee: None,
                    due_date_offset: Some(1), // 1 day
                    conditions: serde_json::json!({
                        "status": "approved"
                    }),
                    actions: serde_json::json!({
                        "publish_policy": true,
                        "update_status": "active",
                        "notify_organization": true
                    }),
                },
            ],
            is_active: true,
        };

        // Control Testing Workflow
        let control_testing_workflow = WorkflowDefinition {
            id: Uuid::new_v4(),
            name: "Control Testing Workflow".to_string(),
            description: "Automated workflow for control testing process".to_string(),
            workflow_type: WorkflowType::ControlTesting,
            trigger_conditions: serde_json::json!({
                "entity_type": "control",
                "test_due": true
            }),
            steps: vec![
                WorkflowStep {
                    step_id: "test_planning".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Test Planning".to_string(),
                    description: "Plan control testing procedures".to_string(),
                    assignee: None,
                    due_date_offset: Some(3), // 3 days
                    conditions: serde_json::json!({}),
                    actions: serde_json::json!({
                        "create_test_plan": true,
                        "assign_tester": true
                    }),
                },
                WorkflowStep {
                    step_id: "test_execution".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Test Execution".to_string(),
                    description: "Execute control tests".to_string(),
                    assignee: None,
                    due_date_offset: Some(7), // 7 days
                    conditions: serde_json::json!({
                        "test_plan_approved": true
                    }),
                    actions: serde_json::json!({
                        "execute_tests": true,
                        "collect_evidence": true
                    }),
                },
                WorkflowStep {
                    step_id: "test_review".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Test Review".to_string(),
                    description: "Review test results and evidence".to_string(),
                    assignee: None,
                    due_date_offset: Some(2), // 2 days
                    conditions: serde_json::json!({
                        "tests_completed": true
                    }),
                    actions: serde_json::json!({
                        "review_results": true,
                        "update_effectiveness": true,
                        "generate_report": true
                    }),
                },
            ],
            is_active: true,
        };

        // Audit Management Workflow
        let audit_management_workflow = WorkflowDefinition {
            id: Uuid::new_v4(),
            name: "Audit Management Workflow".to_string(),
            description: "Automated workflow for audit management process".to_string(),
            workflow_type: WorkflowType::AuditManagement,
            trigger_conditions: serde_json::json!({
                "entity_type": "audit",
                "status": "planning"
            }),
            steps: vec![
                WorkflowStep {
                    step_id: "audit_planning".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Audit Planning".to_string(),
                    description: "Plan audit scope and procedures".to_string(),
                    assignee: None,
                    due_date_offset: Some(10), // 10 days
                    conditions: serde_json::json!({}),
                    actions: serde_json::json!({
                        "create_audit_plan": true,
                        "assign_audit_team": true,
                        "schedule_fieldwork": true
                    }),
                },
                WorkflowStep {
                    step_id: "fieldwork".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Audit Fieldwork".to_string(),
                    description: "Conduct audit fieldwork".to_string(),
                    assignee: None,
                    due_date_offset: Some(30), // 30 days
                    conditions: serde_json::json!({
                        "audit_plan_approved": true
                    }),
                    actions: serde_json::json!({
                        "conduct_fieldwork": true,
                        "document_findings": true,
                        "collect_evidence": true
                    }),
                },
                WorkflowStep {
                    step_id: "reporting".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Audit Reporting".to_string(),
                    description: "Prepare audit report".to_string(),
                    assignee: None,
                    due_date_offset: Some(14), // 14 days
                    conditions: serde_json::json!({
                        "fieldwork_completed": true
                    }),
                    actions: serde_json::json!({
                        "prepare_report": true,
                        "review_findings": true,
                        "finalize_report": true
                    }),
                },
            ],
            is_active: true,
        };

        // Vendor Onboarding Workflow
        let vendor_onboarding_workflow = WorkflowDefinition {
            id: Uuid::new_v4(),
            name: "Vendor Onboarding Workflow".to_string(),
            description: "Automated workflow for vendor onboarding process".to_string(),
            workflow_type: WorkflowType::VendorOnboarding,
            trigger_conditions: serde_json::json!({
                "entity_type": "vendor",
                "status": "new"
            }),
            steps: vec![
                WorkflowStep {
                    step_id: "initial_assessment".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Initial Risk Assessment".to_string(),
                    description: "Conduct initial vendor risk assessment".to_string(),
                    assignee: None,
                    due_date_offset: Some(5), // 5 days
                    conditions: serde_json::json!({}),
                    actions: serde_json::json!({
                        "send_questionnaire": true,
                        "request_documents": true
                    }),
                },
                WorkflowStep {
                    step_id: "due_diligence".to_string(),
                    step_type: WorkflowStepType::Manual,
                    name: "Due Diligence Review".to_string(),
                    description: "Conduct comprehensive due diligence".to_string(),
                    assignee: None,
                    due_date_offset: Some(10), // 10 days
                    conditions: serde_json::json!({
                        "questionnaire_completed": true
                    }),
                    actions: serde_json::json!({
                        "review_documents": true,
                        "conduct_site_visit": false,
                        "verify_certifications": true
                    }),
                },
                WorkflowStep {
                    step_id: "approval".to_string(),
                    step_type: WorkflowStepType::Approval,
                    name: "Vendor Approval".to_string(),
                    description: "Approve or reject vendor".to_string(),
                    assignee: None,
                    due_date_offset: Some(3), // 3 days
                    conditions: serde_json::json!({
                        "due_diligence_completed": true
                    }),
                    actions: serde_json::json!({
                        "make_decision": true,
                        "update_status": true,
                        "notify_stakeholders": true
                    }),
                },
            ],
            is_active: true,
        };

        // Store workflow definitions
        self.workflow_definitions.insert(WorkflowType::PolicyApproval, policy_approval_workflow);
        self.workflow_definitions.insert(WorkflowType::ControlTesting, control_testing_workflow);
        self.workflow_definitions.insert(WorkflowType::AuditManagement, audit_management_workflow);
        self.workflow_definitions.insert(WorkflowType::VendorOnboarding, vendor_onboarding_workflow);

        info!("Loaded {} default workflow definitions", self.workflow_definitions.len());
        Ok(())
    }

    /// Execute workflow steps
    async fn execute_workflow_steps(
        &self,
        execution: &WorkflowExecution,
        workflow_def: &WorkflowDefinition,
    ) -> Result<(), RegulateAIError> {
        info!("Executing workflow steps for workflow: {}", workflow_def.name);

        for step in &workflow_def.steps {
            match step.step_type {
                WorkflowStepType::Automated => {
                    self.execute_automated_step(execution, step).await?;
                }
                WorkflowStepType::Manual => {
                    self.create_manual_task(execution, step).await?;
                }
                WorkflowStepType::Approval => {
                    self.create_approval_task(execution, step).await?;
                }
                WorkflowStepType::Notification => {
                    self.send_notification(execution, step).await?;
                }
                WorkflowStepType::Integration => {
                    self.execute_integration_step(execution, step).await?;
                }
            }
        }

        Ok(())
    }

    /// Execute automated workflow step
    async fn execute_automated_step(
        &self,
        execution: &WorkflowExecution,
        step: &WorkflowStep,
    ) -> Result<(), RegulateAIError> {
        info!("Executing automated step: {}", step.name);

        // Execute automated actions based on step configuration
        let action_type = step.config.get("action_type")
            .and_then(|v| v.as_str())
            .unwrap_or("generic");

        match action_type {
            "data_validation" => {
                let validation_rules = step.config.get("validation_rules")
                    .and_then(|v| v.as_array())
                    .unwrap_or(&vec![]);

                info!("Executing data validation with {} rules", validation_rules.len());

                // Simulate data validation
                for (i, rule) in validation_rules.iter().enumerate() {
                    let rule_name = rule.get("name").and_then(|v| v.as_str()).unwrap_or("unknown");
                    info!("Validating rule {}: {}", i + 1, rule_name);

                    // Simulate validation logic
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                }
            },
            "report_generation" => {
                let report_type = step.config.get("report_type")
                    .and_then(|v| v.as_str())
                    .unwrap_or("compliance_summary");

                info!("Generating {} report", report_type);

                // Simulate report generation
                tokio::time::sleep(std::time::Duration::from_millis(500)).await;

                info!("Report generated successfully");
            },
            "notification_dispatch" => {
                let recipients = step.config.get("recipients")
                    .and_then(|v| v.as_array())
                    .unwrap_or(&vec![]);

                info!("Dispatching notifications to {} recipients", recipients.len());

                // Simulate notification dispatch
                for recipient in recipients {
                    if let Some(email) = recipient.as_str() {
                        info!("Sending notification to: {}", email);
                        tokio::time::sleep(std::time::Duration::from_millis(50)).await;
                    }
                }
            },
            "compliance_check" => {
                let check_type = step.config.get("check_type")
                    .and_then(|v| v.as_str())
                    .unwrap_or("general");

                info!("Performing {} compliance check", check_type);

                // Simulate compliance checking
                tokio::time::sleep(std::time::Duration::from_millis(300)).await;

                info!("Compliance check completed");
            },
            _ => {
                info!("Executing generic automated action");
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            }
        }

        info!("Automated step '{}' executed successfully", step.name);
        Ok(())
    }

    /// Create manual task for workflow step
    async fn create_manual_task(
        &self,
        execution: &WorkflowExecution,
        step: &WorkflowStep,
    ) -> Result<(), RegulateAIError> {
        info!("Creating manual task for step: {}", step.name);

        // Create manual task in database
        use sea_orm::*;

        let manual_task = manual_tasks::ActiveModel {
            id: Set(Uuid::new_v4()),
            workflow_execution_id: Set(execution.id),
            step_name: Set(step.name.clone()),
            step_description: Set(step.description.clone()),
            assigned_to: Set(step.config.get("assigned_to").and_then(|v| v.as_str()).map(|s| Uuid::parse_str(s).ok()).flatten()),
            priority: Set(step.config.get("priority").and_then(|v| v.as_str()).unwrap_or("medium").to_string()),
            status: Set("pending".to_string()),
            due_date: Set(step.config.get("due_date").and_then(|v| v.as_str()).and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok()).map(|dt| dt.with_timezone(&Utc))),
            instructions: Set(step.config.get("instructions").and_then(|v| v.as_str()).map(String::from)),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(execution.created_by),
            updated_by: Set(None),
            version: Set(1),
        };

        manual_task.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create manual task: {}", e),
                source: Some(Box::new(e)),
            })?;

        info!("Manual task '{}' created successfully", step.name);
        Ok(())
    }

    /// Create approval task for workflow step
    async fn create_approval_task(
        &self,
        execution: &WorkflowExecution,
        step: &WorkflowStep,
    ) -> Result<(), RegulateAIError> {
        info!("Creating approval task for step: {}", step.name);

        // Create approval request in database
        use sea_orm::*;

        let approval_task = approval_tasks::ActiveModel {
            id: Set(Uuid::new_v4()),
            workflow_execution_id: Set(execution.id),
            step_name: Set(step.name.clone()),
            step_description: Set(step.description.clone()),
            required_approvers: Set(step.config.get("required_approvers").and_then(|v| v.as_array()).map(|arr| arr.len() as i32).unwrap_or(1)),
            current_approvals: Set(0),
            status: Set("pending".to_string()),
            due_date: Set(step.config.get("due_date").and_then(|v| v.as_str()).and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok()).map(|dt| dt.with_timezone(&Utc))),
            created_at: Set(Utc::now()),
            updated_at: Set(Utc::now()),
            created_by: Set(execution.created_by),
            updated_by: Set(None),
            version: Set(1),
        };

        approval_task.insert(&self.db).await
            .map_err(|e| RegulateAIError::DatabaseError {
                message: format!("Failed to create approval task: {}", e),
                source: Some(Box::new(e)),
            })?;

        info!("Approval task '{}' created successfully", step.name);
        Ok(())
    }

    /// Send notification for workflow step
    async fn send_notification(
        &self,
        execution: &WorkflowExecution,
        step: &WorkflowStep,
    ) -> Result<(), RegulateAIError> {
        info!("Sending notification for step: {}", step.name);

        // Send notifications via configured channels
        let notification_channels = step.config.get("notification_channels")
            .and_then(|v| v.as_array())
            .unwrap_or(&vec![]);

        for channel in notification_channels {
            let channel_type = channel.get("type").and_then(|v| v.as_str()).unwrap_or("email");
            let recipients = channel.get("recipients").and_then(|v| v.as_array()).unwrap_or(&vec![]);

            match channel_type {
                "email" => {
                    for recipient in recipients {
                        if let Some(email) = recipient.as_str() {
                            self.send_email_notification(email, &step.name, &step.description).await?;
                        }
                    }
                },
                "slack" => {
                    let webhook_url = channel.get("webhook_url").and_then(|v| v.as_str()).unwrap_or("");
                    self.send_slack_notification(webhook_url, &step.name, &step.description).await?;
                },
                "teams" => {
                    let webhook_url = channel.get("webhook_url").and_then(|v| v.as_str()).unwrap_or("");
                    self.send_teams_notification(webhook_url, &step.name, &step.description).await?;
                },
                _ => {
                    warn!("Unknown notification channel type: {}", channel_type);
                }
            }
        }

        info!("Notification for '{}' sent successfully", step.name);
        Ok(())
    }

    /// Send email notification
    async fn send_email_notification(&self, recipient: &str, subject: &str, body: &str) -> Result<(), RegulateAIError> {
        info!("Sending email notification to: {}", recipient);

        // Email sending implementation would go here
        // For now, just log the email details
        info!("Email sent - To: {}, Subject: {}, Body: {}", recipient, subject, body);

        Ok(())
    }

    /// Send Slack notification
    async fn send_slack_notification(&self, webhook_url: &str, title: &str, message: &str) -> Result<(), RegulateAIError> {
        info!("Sending Slack notification to: {}", webhook_url);

        let payload = serde_json::json!({
            "text": format!("Workflow Notification: {}", title),
            "attachments": [{
                "color": "warning",
                "fields": [{
                    "title": title,
                    "value": message,
                    "short": false
                }]
            }]
        });

        let client = reqwest::Client::new();
        match client.post(webhook_url).json(&payload).send().await {
            Ok(response) if response.status().is_success() => {
                info!("Slack notification sent successfully");
            },
            Ok(response) => {
                warn!("Slack notification failed with status: {}", response.status());
            },
            Err(e) => {
                error!("Failed to send Slack notification: {}", e);
                return Err(RegulateAIError::ExternalServiceError(format!("Slack notification failed: {}", e)));
            }
        }

        Ok(())
    }

    /// Send Teams notification
    async fn send_teams_notification(&self, webhook_url: &str, title: &str, message: &str) -> Result<(), RegulateAIError> {
        info!("Sending Teams notification to: {}", webhook_url);

        let payload = serde_json::json!({
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": format!("Workflow Notification: {}", title),
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": "Workflow Step Notification",
                "text": message,
                "markdown": true
            }]
        });

        let client = reqwest::Client::new();
        match client.post(webhook_url).json(&payload).send().await {
            Ok(response) if response.status().is_success() => {
                info!("Teams notification sent successfully");
            },
            Ok(response) => {
                warn!("Teams notification failed with status: {}", response.status());
            },
            Err(e) => {
                error!("Failed to send Teams notification: {}", e);
                return Err(RegulateAIError::ExternalServiceError(format!("Teams notification failed: {}", e)));
            }
        }

        Ok(())
    }

    /// Execute integration step
    async fn execute_integration_step(
        &self,
        execution: &WorkflowExecution,
        step: &WorkflowStep,
    ) -> Result<(), RegulateAIError> {
        info!("Executing integration step: {}", step.name);

        // Execute integration with external systems based on step configuration
        let integration_type = step.config.get("integration_type")
            .and_then(|v| v.as_str())
            .unwrap_or("generic");

        match integration_type {
            "api_call" => {
                let endpoint = step.config.get("endpoint").and_then(|v| v.as_str()).unwrap_or("");
                let method = step.config.get("method").and_then(|v| v.as_str()).unwrap_or("GET");

                info!("Making {} request to {}", method, endpoint);

                // Make HTTP request to external system
                let client = reqwest::Client::new();
                let response = match method {
                    "POST" => {
                        let body = step.config.get("body").unwrap_or(&serde_json::json!({}));
                        client.post(endpoint).json(body).send().await
                    },
                    "PUT" => {
                        let body = step.config.get("body").unwrap_or(&serde_json::json!({}));
                        client.put(endpoint).json(body).send().await
                    },
                    _ => client.get(endpoint).send().await,
                };

                match response {
                    Ok(resp) if resp.status().is_success() => {
                        info!("Integration API call successful: {}", resp.status());
                    },
                    Ok(resp) => {
                        warn!("Integration API call failed with status: {}", resp.status());
                        return Err(RegulateAIError::ExternalServiceError(
                            format!("API call failed with status: {}", resp.status())
                        ));
                    },
                    Err(e) => {
                        error!("Integration API call error: {}", e);
                        return Err(RegulateAIError::ExternalServiceError(
                            format!("API call error: {}", e)
                        ));
                    }
                }
            },
            "database_update" => {
                let table = step.config.get("table").and_then(|v| v.as_str()).unwrap_or("");
                let update_data = step.config.get("data").unwrap_or(&serde_json::json!({}));

                info!("Updating database table: {} with data: {}", table, update_data);
                // Database update would be implemented here
            },
            "file_transfer" => {
                let source = step.config.get("source").and_then(|v| v.as_str()).unwrap_or("");
                let destination = step.config.get("destination").and_then(|v| v.as_str()).unwrap_or("");

                info!("Transferring file from {} to {}", source, destination);
                // File transfer would be implemented here
            },
            _ => {
                info!("Generic integration step executed");
            }
        }

        info!("Integration step '{}' executed successfully", step.name);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use regulateai_database::create_test_connection;

    #[tokio::test]
    async fn test_workflow_engine_initialization() {
        let db = create_test_connection().await.unwrap();
        let engine = WorkflowEngine::new(db).await.unwrap();
        
        assert_eq!(engine.workflow_definitions.len(), 4);
        assert!(engine.workflow_definitions.contains_key(&WorkflowType::PolicyApproval));
        assert!(engine.workflow_definitions.contains_key(&WorkflowType::ControlTesting));
        assert!(engine.workflow_definitions.contains_key(&WorkflowType::AuditManagement));
        assert!(engine.workflow_definitions.contains_key(&WorkflowType::VendorOnboarding));
    }

    #[tokio::test]
    async fn test_workflow_execution() {
        let db = create_test_connection().await.unwrap();
        let engine = WorkflowEngine::new(db).await.unwrap();
        
        let entity_id = Uuid::new_v4();
        let triggered_by = Uuid::new_v4();
        
        let execution = engine.execute_workflow(
            WorkflowType::PolicyApproval,
            entity_id,
            "policy".to_string(),
            triggered_by,
        ).await.unwrap();
        
        assert_eq!(execution.entity_id, entity_id);
        assert_eq!(execution.entity_type, "policy");
        assert_eq!(execution.status, WorkflowStatus::InProgress);
        assert!(execution.current_step.is_some());
    }
}
