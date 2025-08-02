//! RegulateAI Messaging Library
//! 
//! This library provides event-driven messaging capabilities for the RegulateAI platform,
//! supporting both Redis and RabbitMQ as message brokers for asynchronous communication
//! between microservices.

use std::collections::HashMap;
use std::sync::Arc;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{info, error, warn};
use uuid::Uuid;
use chrono::{DateTime, Utc};

pub mod redis;
pub mod rabbitmq;
pub mod events;
pub mod handlers;

use regulateai_errors::RegulateAIError;

/// Message broker trait for abstracting different messaging implementations
#[async_trait]
pub trait MessageBroker: Send + Sync {
    /// Publish a message to a topic/queue
    async fn publish(&self, topic: &str, message: &Message) -> Result<(), RegulateAIError>;
    
    /// Subscribe to a topic/queue with a message handler
    async fn subscribe<H>(&self, topic: &str, handler: H) -> Result<(), RegulateAIError>
    where
        H: MessageHandler + Send + Sync + 'static;
    
    /// Unsubscribe from a topic/queue
    async fn unsubscribe(&self, topic: &str) -> Result<(), RegulateAIError>;
    
    /// Check broker health
    async fn health_check(&self) -> Result<BrokerHealth, RegulateAIError>;
    
    /// Get broker statistics
    async fn get_stats(&self) -> Result<BrokerStats, RegulateAIError>;
}

/// Message handler trait for processing incoming messages
#[async_trait]
pub trait MessageHandler: Send + Sync {
    /// Handle an incoming message
    async fn handle(&self, message: &Message) -> Result<(), RegulateAIError>;
    
    /// Get handler name for logging and metrics
    fn name(&self) -> &str;
}

/// Core message structure for inter-service communication
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    /// Unique message identifier
    pub id: Uuid,
    
    /// Message type/event name
    pub message_type: String,
    
    /// Source service that published the message
    pub source_service: String,
    
    /// Target service (optional, for direct messaging)
    pub target_service: Option<String>,
    
    /// Message payload
    pub payload: serde_json::Value,
    
    /// Message metadata
    pub metadata: MessageMetadata,
    
    /// Message timestamp
    pub timestamp: DateTime<Utc>,
    
    /// Message expiration time (optional)
    pub expires_at: Option<DateTime<Utc>>,
    
    /// Correlation ID for request/response patterns
    pub correlation_id: Option<Uuid>,
    
    /// Reply-to topic for response messages
    pub reply_to: Option<String>,
}

/// Message metadata for additional context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageMetadata {
    /// Message priority (0-9, higher is more important)
    pub priority: u8,
    
    /// Number of delivery attempts
    pub delivery_count: u32,
    
    /// Maximum delivery attempts before dead letter
    pub max_delivery_attempts: u32,
    
    /// Message routing key
    pub routing_key: Option<String>,
    
    /// Custom headers
    pub headers: HashMap<String, String>,
    
    /// Message tracing information
    pub trace_id: Option<String>,
    
    /// Message span ID for distributed tracing
    pub span_id: Option<String>,
}

/// Broker health information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrokerHealth {
    /// Whether broker is healthy
    pub healthy: bool,
    
    /// Broker status message
    pub status: String,
    
    /// Connection status
    pub connected: bool,
    
    /// Last health check timestamp
    pub last_check: DateTime<Utc>,
    
    /// Additional health details
    pub details: HashMap<String, serde_json::Value>,
}

/// Broker statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrokerStats {
    /// Total messages published
    pub messages_published: u64,
    
    /// Total messages consumed
    pub messages_consumed: u64,
    
    /// Messages currently in queues
    pub messages_pending: u64,
    
    /// Number of active connections
    pub active_connections: u32,
    
    /// Number of active subscriptions
    pub active_subscriptions: u32,
    
    /// Broker uptime in seconds
    pub uptime_seconds: u64,
    
    /// Memory usage in bytes
    pub memory_usage_bytes: u64,
    
    /// Additional broker-specific stats
    pub additional_stats: HashMap<String, serde_json::Value>,
}

/// Message bus for managing multiple brokers and routing
pub struct MessageBus {
    /// Primary message broker
    primary_broker: Arc<dyn MessageBroker>,
    
    /// Fallback message broker (optional)
    fallback_broker: Option<Arc<dyn MessageBroker>>,
    
    /// Message handlers by topic
    handlers: Arc<RwLock<HashMap<String, Vec<Arc<dyn MessageHandler>>>>>,
    
    /// Message routing rules
    routing_rules: Arc<RwLock<HashMap<String, RoutingRule>>>,
    
    /// Bus configuration
    config: MessageBusConfig,
}

/// Message bus configuration
#[derive(Debug, Clone)]
pub struct MessageBusConfig {
    /// Default message TTL in seconds
    pub default_ttl_seconds: u64,
    
    /// Maximum message size in bytes
    pub max_message_size_bytes: usize,
    
    /// Enable message persistence
    pub enable_persistence: bool,
    
    /// Enable message deduplication
    pub enable_deduplication: bool,
    
    /// Dead letter queue configuration
    pub dead_letter_config: DeadLetterConfig,
    
    /// Retry configuration
    pub retry_config: RetryConfig,
}

/// Dead letter queue configuration
#[derive(Debug, Clone)]
pub struct DeadLetterConfig {
    /// Enable dead letter queue
    pub enabled: bool,
    
    /// Dead letter queue name
    pub queue_name: String,
    
    /// Maximum message age before dead letter
    pub max_age_seconds: u64,
}

/// Retry configuration
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Enable automatic retries
    pub enabled: bool,
    
    /// Maximum retry attempts
    pub max_attempts: u32,
    
    /// Initial retry delay in milliseconds
    pub initial_delay_ms: u64,
    
    /// Maximum retry delay in milliseconds
    pub max_delay_ms: u64,
    
    /// Backoff multiplier
    pub backoff_multiplier: f64,
}

/// Message routing rule
#[derive(Debug, Clone)]
pub struct RoutingRule {
    /// Rule name
    pub name: String,
    
    /// Source service pattern
    pub source_pattern: String,
    
    /// Target broker
    pub target_broker: BrokerType,
    
    /// Routing conditions
    pub conditions: Vec<RoutingCondition>,
}

/// Routing condition
#[derive(Debug, Clone)]
pub struct RoutingCondition {
    /// Field to check
    pub field: String,
    
    /// Condition operator
    pub operator: ConditionOperator,
    
    /// Expected value
    pub value: serde_json::Value,
}

/// Condition operators
#[derive(Debug, Clone)]
pub enum ConditionOperator {
    Equals,
    NotEquals,
    Contains,
    StartsWith,
    EndsWith,
    GreaterThan,
    LessThan,
    In,
    NotIn,
}

/// Broker type enumeration
#[derive(Debug, Clone)]
pub enum BrokerType {
    Primary,
    Fallback,
    Redis,
    RabbitMQ,
}

impl MessageBus {
    /// Create a new message bus with primary broker
    pub fn new(primary_broker: Arc<dyn MessageBroker>, config: MessageBusConfig) -> Self {
        Self {
            primary_broker,
            fallback_broker: None,
            handlers: Arc::new(RwLock::new(HashMap::new())),
            routing_rules: Arc::new(RwLock::new(HashMap::new())),
            config,
        }
    }
    
    /// Set fallback broker
    pub fn with_fallback_broker(mut self, fallback_broker: Arc<dyn MessageBroker>) -> Self {
        self.fallback_broker = Some(fallback_broker);
        self
    }
    
    /// Publish a message
    pub async fn publish(&self, topic: &str, message: &Message) -> Result<(), RegulateAIError> {
        info!("Publishing message {} to topic: {}", message.id, topic);
        
        // Validate message
        self.validate_message(message)?;
        
        // Apply routing rules
        let broker = self.select_broker(topic, message).await?;
        
        // Publish message
        match broker.publish(topic, message).await {
            Ok(()) => {
                info!("Message {} published successfully", message.id);
                Ok(())
            }
            Err(e) => {
                error!("Failed to publish message {}: {}", message.id, e);
                
                // Try fallback broker if available
                if let Some(fallback) = &self.fallback_broker {
                    warn!("Trying fallback broker for message {}", message.id);
                    fallback.publish(topic, message).await
                } else {
                    Err(e)
                }
            }
        }
    }
    
    /// Subscribe to a topic with a handler
    pub async fn subscribe<H>(&self, topic: &str, handler: H) -> Result<(), RegulateAIError>
    where
        H: MessageHandler + Send + Sync + 'static,
    {
        info!("Subscribing to topic: {} with handler: {}", topic, handler.name());
        
        // Add handler to registry
        {
            let mut handlers = self.handlers.write().await;
            handlers.entry(topic.to_string())
                .or_insert_with(Vec::new)
                .push(Arc::new(handler));
        }
        
        // Subscribe with primary broker
        self.primary_broker.subscribe(topic, CompositeHandler::new(
            topic.to_string(),
            self.handlers.clone(),
        )).await
    }
    
    /// Get message bus health
    pub async fn health(&self) -> Result<MessageBusHealth, RegulateAIError> {
        let primary_health = self.primary_broker.health_check().await?;
        
        let fallback_health = if let Some(fallback) = &self.fallback_broker {
            Some(fallback.health_check().await?)
        } else {
            None
        };
        
        Ok(MessageBusHealth {
            primary_broker: primary_health,
            fallback_broker: fallback_health,
            handlers_count: self.handlers.read().await.len() as u32,
            routing_rules_count: self.routing_rules.read().await.len() as u32,
        })
    }
    
    /// Get message bus statistics
    pub async fn stats(&self) -> Result<MessageBusStats, RegulateAIError> {
        let primary_stats = self.primary_broker.get_stats().await?;
        
        let fallback_stats = if let Some(fallback) = &self.fallback_broker {
            Some(fallback.get_stats().await?)
        } else {
            None
        };
        
        Ok(MessageBusStats {
            primary_broker: primary_stats,
            fallback_broker: fallback_stats,
        })
    }
    
    // Helper methods
    async fn validate_message(&self, message: &Message) -> Result<(), RegulateAIError> {
        // Check message size
        let message_size = serde_json::to_vec(message)
            .map_err(|e| RegulateAIError::SerializationError(e.to_string()))?
            .len();
        
        if message_size > self.config.max_message_size_bytes {
            return Err(RegulateAIError::BadRequest(
                format!("Message size {} exceeds maximum {}", 
                    message_size, self.config.max_message_size_bytes)
            ));
        }
        
        // Check message expiration
        if let Some(expires_at) = message.expires_at {
            if expires_at <= Utc::now() {
                return Err(RegulateAIError::BadRequest(
                    "Message has already expired".to_string()
                ));
            }
        }
        
        Ok(())
    }
    
    async fn select_broker(&self, topic: &str, message: &Message) -> Result<&Arc<dyn MessageBroker>, RegulateAIError> {
        // Apply routing rules
        let routing_rules = self.routing_rules.read().await;
        
        for rule in routing_rules.values() {
            if self.matches_routing_rule(rule, topic, message) {
                return match rule.target_broker {
                    BrokerType::Primary => Ok(&self.primary_broker),
                    BrokerType::Fallback => {
                        if let Some(fallback) = &self.fallback_broker {
                            Ok(fallback)
                        } else {
                            Ok(&self.primary_broker)
                        }
                    }
                    _ => Ok(&self.primary_broker),
                };
            }
        }
        
        // Default to primary broker
        Ok(&self.primary_broker)
    }
    
    fn matches_routing_rule(&self, rule: &RoutingRule, topic: &str, message: &Message) -> bool {
        // Check source pattern
        if !self.matches_pattern(&rule.source_pattern, &message.source_service) {
            return false;
        }
        
        // Check conditions
        for condition in &rule.conditions {
            if !self.matches_condition(condition, message) {
                return false;
            }
        }
        
        true
    }
    
    fn matches_pattern(&self, pattern: &str, value: &str) -> bool {
        // Simple pattern matching (could be enhanced with regex)
        pattern == "*" || pattern == value
    }
    
    fn matches_condition(&self, condition: &RoutingCondition, message: &Message) -> bool {
        // Extract field value from message
        let field_value = match condition.field.as_str() {
            "message_type" => serde_json::Value::String(message.message_type.clone()),
            "source_service" => serde_json::Value::String(message.source_service.clone()),
            "priority" => serde_json::Value::Number(message.metadata.priority.into()),
            _ => return false,
        };
        
        // Apply condition operator
        match condition.operator {
            ConditionOperator::Equals => field_value == condition.value,
            ConditionOperator::NotEquals => field_value != condition.value,
            // Add more operators as needed
            _ => false,
        }
    }
}

/// Composite handler that delegates to multiple handlers
pub struct CompositeHandler {
    topic: String,
    handlers: Arc<RwLock<HashMap<String, Vec<Arc<dyn MessageHandler>>>>>,
}

impl CompositeHandler {
    pub fn new(topic: String, handlers: Arc<RwLock<HashMap<String, Vec<Arc<dyn MessageHandler>>>>>) -> Self {
        Self { topic, handlers }
    }
}

#[async_trait]
impl MessageHandler for CompositeHandler {
    async fn handle(&self, message: &Message) -> Result<(), RegulateAIError> {
        let handlers = self.handlers.read().await;
        
        if let Some(topic_handlers) = handlers.get(&self.topic) {
            for handler in topic_handlers {
                if let Err(e) = handler.handle(message).await {
                    error!("Handler {} failed to process message {}: {}", 
                        handler.name(), message.id, e);
                }
            }
        }
        
        Ok(())
    }
    
    fn name(&self) -> &str {
        "CompositeHandler"
    }
}

/// Message bus health information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageBusHealth {
    pub primary_broker: BrokerHealth,
    pub fallback_broker: Option<BrokerHealth>,
    pub handlers_count: u32,
    pub routing_rules_count: u32,
}

/// Message bus statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageBusStats {
    pub primary_broker: BrokerStats,
    pub fallback_broker: Option<BrokerStats>,
}

impl Default for MessageBusConfig {
    fn default() -> Self {
        Self {
            default_ttl_seconds: 3600, // 1 hour
            max_message_size_bytes: 1024 * 1024, // 1 MB
            enable_persistence: true,
            enable_deduplication: true,
            dead_letter_config: DeadLetterConfig {
                enabled: true,
                queue_name: "dead_letter".to_string(),
                max_age_seconds: 86400, // 24 hours
            },
            retry_config: RetryConfig {
                enabled: true,
                max_attempts: 3,
                initial_delay_ms: 1000,
                max_delay_ms: 30000,
                backoff_multiplier: 2.0,
            },
        }
    }
}

impl Message {
    /// Create a new message
    pub fn new(message_type: String, source_service: String, payload: serde_json::Value) -> Self {
        Self {
            id: Uuid::new_v4(),
            message_type,
            source_service,
            target_service: None,
            payload,
            metadata: MessageMetadata::default(),
            timestamp: Utc::now(),
            expires_at: None,
            correlation_id: None,
            reply_to: None,
        }
    }
    
    /// Set target service
    pub fn with_target_service(mut self, target_service: String) -> Self {
        self.target_service = Some(target_service);
        self
    }
    
    /// Set correlation ID
    pub fn with_correlation_id(mut self, correlation_id: Uuid) -> Self {
        self.correlation_id = Some(correlation_id);
        self
    }
    
    /// Set reply-to topic
    pub fn with_reply_to(mut self, reply_to: String) -> Self {
        self.reply_to = Some(reply_to);
        self
    }
    
    /// Set message expiration
    pub fn with_expiration(mut self, expires_at: DateTime<Utc>) -> Self {
        self.expires_at = Some(expires_at);
        self
    }
    
    /// Set message priority
    pub fn with_priority(mut self, priority: u8) -> Self {
        self.metadata.priority = priority;
        self
    }
}

impl Default for MessageMetadata {
    fn default() -> Self {
        Self {
            priority: 5, // Medium priority
            delivery_count: 0,
            max_delivery_attempts: 3,
            routing_key: None,
            headers: HashMap::new(),
            trace_id: None,
            span_id: None,
        }
    }
}
