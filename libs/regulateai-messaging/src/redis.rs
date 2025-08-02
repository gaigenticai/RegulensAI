//! Redis Message Broker Implementation
//! 
//! This module provides Redis-based message broker implementation using Redis Streams
//! for reliable message delivery and Redis Pub/Sub for real-time messaging.

use std::collections::HashMap;
use std::sync::Arc;
use async_trait::async_trait;
use redis::{Client, Connection, AsyncCommands, RedisResult, streams::StreamReadOptions};
use serde_json;
use tokio::sync::RwLock;
use tokio::time::{sleep, Duration};
use tracing::{info, error, warn, debug};
use uuid::Uuid;
use chrono::Utc;

use crate::{MessageBroker, MessageHandler, Message, BrokerHealth, BrokerStats};
use regulateai_errors::RegulateAIError;

/// Redis message broker implementation
pub struct RedisBroker {
    /// Redis client
    client: Client,
    
    /// Active subscriptions
    subscriptions: Arc<RwLock<HashMap<String, SubscriptionInfo>>>,
    
    /// Broker configuration
    config: RedisBrokerConfig,
    
    /// Connection pool
    connection_pool: Arc<RwLock<Vec<redis::aio::Connection>>>,
    
    /// Broker statistics
    stats: Arc<RwLock<BrokerStats>>,
}

/// Redis broker configuration
#[derive(Debug, Clone)]
pub struct RedisBrokerConfig {
    /// Redis connection URL
    pub redis_url: String,
    
    /// Maximum connections in pool
    pub max_connections: usize,
    
    /// Connection timeout in milliseconds
    pub connection_timeout_ms: u64,
    
    /// Use Redis Streams for reliable messaging
    pub use_streams: bool,
    
    /// Stream consumer group name
    pub consumer_group: String,
    
    /// Consumer name
    pub consumer_name: String,
    
    /// Maximum messages to read per batch
    pub max_batch_size: usize,
    
    /// Message acknowledgment timeout in milliseconds
    pub ack_timeout_ms: u64,
    
    /// Enable message persistence
    pub enable_persistence: bool,
    
    /// Message TTL in seconds
    pub message_ttl_seconds: u64,
}

/// Subscription information
#[derive(Debug)]
struct SubscriptionInfo {
    /// Topic name
    topic: String,
    
    /// Message handler
    handler: Arc<dyn MessageHandler>,
    
    /// Subscription active flag
    active: bool,
    
    /// Consumer task handle
    task_handle: Option<tokio::task::JoinHandle<()>>,
}

impl RedisBroker {
    /// Create a new Redis broker
    pub async fn new(config: RedisBrokerConfig) -> Result<Self, RegulateAIError> {
        info!("Initializing Redis message broker");
        
        // Create Redis client
        let client = Client::open(config.redis_url.clone())
            .map_err(|e| RegulateAIError::ConnectionError(format!("Redis client error: {}", e)))?;
        
        // Test connection
        let mut conn = client.get_async_connection().await
            .map_err(|e| RegulateAIError::ConnectionError(format!("Redis connection error: {}", e)))?;
        
        // Ping Redis to verify connection
        let _: String = conn.ping().await
            .map_err(|e| RegulateAIError::ConnectionError(format!("Redis ping failed: {}", e)))?;
        
        info!("Redis connection established successfully");
        
        // Initialize connection pool
        let mut pool = Vec::new();
        for _ in 0..config.max_connections {
            let conn = client.get_async_connection().await
                .map_err(|e| RegulateAIError::ConnectionError(format!("Pool connection error: {}", e)))?;
            pool.push(conn);
        }
        
        let broker = Self {
            client,
            subscriptions: Arc::new(RwLock::new(HashMap::new())),
            config,
            connection_pool: Arc::new(RwLock::new(pool)),
            stats: Arc::new(RwLock::new(BrokerStats {
                messages_published: 0,
                messages_consumed: 0,
                messages_pending: 0,
                active_connections: 0,
                active_subscriptions: 0,
                uptime_seconds: 0,
                memory_usage_bytes: 0,
                additional_stats: HashMap::new(),
            })),
        };
        
        Ok(broker)
    }
    
    /// Get a connection from the pool
    async fn get_connection(&self) -> Result<redis::aio::Connection, RegulateAIError> {
        let mut pool = self.connection_pool.write().await;
        
        if let Some(conn) = pool.pop() {
            Ok(conn)
        } else {
            // Create new connection if pool is empty
            self.client.get_async_connection().await
                .map_err(|e| RegulateAIError::ConnectionError(format!("Connection error: {}", e)))
        }
    }
    
    /// Return connection to pool
    async fn return_connection(&self, conn: redis::aio::Connection) {
        let mut pool = self.connection_pool.write().await;
        if pool.len() < self.config.max_connections {
            pool.push(conn);
        }
    }
    
    /// Publish message using Redis Streams
    async fn publish_stream(&self, topic: &str, message: &Message) -> Result<(), RegulateAIError> {
        let mut conn = self.get_connection().await?;
        
        // Serialize message
        let message_data = serde_json::to_string(message)
            .map_err(|e| RegulateAIError::SerializationError(e.to_string()))?;
        
        // Create stream entry
        let stream_key = format!("stream:{}", topic);
        let entry_id: String = conn.xadd(&stream_key, "*", &[("data", message_data)]).await
            .map_err(|e| RegulateAIError::PublishError(format!("Stream publish error: {}", e)))?;
        
        debug!("Published message {} to stream {} with ID: {}", message.id, stream_key, entry_id);
        
        // Set TTL if configured
        if self.config.message_ttl_seconds > 0 {
            let _: () = conn.expire(&stream_key, self.config.message_ttl_seconds as usize).await
                .map_err(|e| RegulateAIError::PublishError(format!("TTL set error: {}", e)))?;
        }
        
        self.return_connection(conn).await;
        
        // Update statistics
        {
            let mut stats = self.stats.write().await;
            stats.messages_published += 1;
        }
        
        Ok(())
    }
    
    /// Publish message using Redis Pub/Sub
    async fn publish_pubsub(&self, topic: &str, message: &Message) -> Result<(), RegulateAIError> {
        let mut conn = self.get_connection().await?;
        
        // Serialize message
        let message_data = serde_json::to_string(message)
            .map_err(|e| RegulateAIError::SerializationError(e.to_string()))?;
        
        // Publish to channel
        let channel = format!("channel:{}", topic);
        let subscribers: i32 = conn.publish(&channel, message_data).await
            .map_err(|e| RegulateAIError::PublishError(format!("Pub/Sub publish error: {}", e)))?;
        
        debug!("Published message {} to channel {} with {} subscribers", message.id, channel, subscribers);
        
        self.return_connection(conn).await;
        
        // Update statistics
        {
            let mut stats = self.stats.write().await;
            stats.messages_published += 1;
        }
        
        Ok(())
    }
    
    /// Subscribe using Redis Streams
    async fn subscribe_stream<H>(&self, topic: &str, handler: H) -> Result<(), RegulateAIError>
    where
        H: MessageHandler + Send + Sync + 'static,
    {
        let stream_key = format!("stream:{}", topic);
        let group_name = self.config.consumer_group.clone();
        let consumer_name = format!("{}:{}", self.config.consumer_name, Uuid::new_v4());
        
        // Create consumer group if it doesn't exist
        let mut conn = self.get_connection().await?;
        let _: RedisResult<()> = conn.xgroup_create_mkstream(&stream_key, &group_name, "0").await;
        self.return_connection(conn).await;
        
        let handler = Arc::new(handler);
        let client = self.client.clone();
        let config = self.config.clone();
        let stats = self.stats.clone();
        
        // Start consumer task
        let task_handle = tokio::spawn(async move {
            info!("Starting stream consumer for topic: {}", topic);
            
            loop {
                match client.get_async_connection().await {
                    Ok(mut conn) => {
                        // Read messages from stream
                        let opts = StreamReadOptions::default()
                            .group(&group_name, &consumer_name)
                            .count(config.max_batch_size)
                            .block(1000); // Block for 1 second
                        
                        match conn.xread_options(&[&stream_key], &[">"], &opts).await {
                            Ok(streams) => {
                                for stream in streams {
                                    for entry in stream.entries {
                                        // Process message
                                        if let Some(data) = entry.fields.get("data") {
                                            match serde_json::from_str::<Message>(data) {
                                                Ok(message) => {
                                                    debug!("Processing message {} from stream", message.id);
                                                    
                                                    // Handle message
                                                    if let Err(e) = handler.handle(&message).await {
                                                        error!("Handler failed for message {}: {}", message.id, e);
                                                    } else {
                                                        // Acknowledge message
                                                        let _: RedisResult<i32> = conn.xack(&stream_key, &group_name, &[&entry.id]).await;
                                                        
                                                        // Update statistics
                                                        {
                                                            let mut stats = stats.write().await;
                                                            stats.messages_consumed += 1;
                                                        }
                                                    }
                                                }
                                                Err(e) => {
                                                    error!("Failed to deserialize message: {}", e);
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            Err(e) => {
                                error!("Stream read error: {}", e);
                                sleep(Duration::from_secs(1)).await;
                            }
                        }
                    }
                    Err(e) => {
                        error!("Connection error in stream consumer: {}", e);
                        sleep(Duration::from_secs(5)).await;
                    }
                }
            }
        });
        
        // Store subscription info
        {
            let mut subscriptions = self.subscriptions.write().await;
            subscriptions.insert(topic.to_string(), SubscriptionInfo {
                topic: topic.to_string(),
                handler,
                active: true,
                task_handle: Some(task_handle),
            });
        }
        
        // Update statistics
        {
            let mut stats = self.stats.write().await;
            stats.active_subscriptions += 1;
        }
        
        Ok(())
    }
    
    /// Subscribe using Redis Pub/Sub
    async fn subscribe_pubsub<H>(&self, topic: &str, handler: H) -> Result<(), RegulateAIError>
    where
        H: MessageHandler + Send + Sync + 'static,
    {
        let channel = format!("channel:{}", topic);
        let handler = Arc::new(handler);
        let client = self.client.clone();
        let stats = self.stats.clone();
        
        // Start subscriber task
        let task_handle = tokio::spawn(async move {
            info!("Starting pub/sub subscriber for topic: {}", topic);
            
            loop {
                match client.get_async_connection().await {
                    Ok(mut conn) => {
                        match conn.subscribe(&channel).await {
                            Ok(mut pubsub) => {
                                loop {
                                    match pubsub.on_message().next().await {
                                        Some(msg) => {
                                            let payload: String = match msg.get_payload() {
                                                Ok(p) => p,
                                                Err(e) => {
                                                    error!("Failed to get message payload: {}", e);
                                                    continue;
                                                }
                                            };
                                            
                                            match serde_json::from_str::<Message>(&payload) {
                                                Ok(message) => {
                                                    debug!("Processing message {} from pub/sub", message.id);
                                                    
                                                    // Handle message
                                                    if let Err(e) = handler.handle(&message).await {
                                                        error!("Handler failed for message {}: {}", message.id, e);
                                                    } else {
                                                        // Update statistics
                                                        {
                                                            let mut stats = stats.write().await;
                                                            stats.messages_consumed += 1;
                                                        }
                                                    }
                                                }
                                                Err(e) => {
                                                    error!("Failed to deserialize message: {}", e);
                                                }
                                            }
                                        }
                                        None => {
                                            warn!("Pub/sub connection closed, reconnecting...");
                                            break;
                                        }
                                    }
                                }
                            }
                            Err(e) => {
                                error!("Pub/sub subscribe error: {}", e);
                                sleep(Duration::from_secs(5)).await;
                            }
                        }
                    }
                    Err(e) => {
                        error!("Connection error in pub/sub subscriber: {}", e);
                        sleep(Duration::from_secs(5)).await;
                    }
                }
            }
        });
        
        // Store subscription info
        {
            let mut subscriptions = self.subscriptions.write().await;
            subscriptions.insert(topic.to_string(), SubscriptionInfo {
                topic: topic.to_string(),
                handler,
                active: true,
                task_handle: Some(task_handle),
            });
        }
        
        // Update statistics
        {
            let mut stats = self.stats.write().await;
            stats.active_subscriptions += 1;
        }
        
        Ok(())
    }
}

#[async_trait]
impl MessageBroker for RedisBroker {
    async fn publish(&self, topic: &str, message: &Message) -> Result<(), RegulateAIError> {
        info!("Publishing message {} to Redis topic: {}", message.id, topic);
        
        if self.config.use_streams {
            self.publish_stream(topic, message).await
        } else {
            self.publish_pubsub(topic, message).await
        }
    }
    
    async fn subscribe<H>(&self, topic: &str, handler: H) -> Result<(), RegulateAIError>
    where
        H: MessageHandler + Send + Sync + 'static,
    {
        info!("Subscribing to Redis topic: {} with handler: {}", topic, handler.name());
        
        if self.config.use_streams {
            self.subscribe_stream(topic, handler).await
        } else {
            self.subscribe_pubsub(topic, handler).await
        }
    }
    
    async fn unsubscribe(&self, topic: &str) -> Result<(), RegulateAIError> {
        info!("Unsubscribing from Redis topic: {}", topic);
        
        let mut subscriptions = self.subscriptions.write().await;
        
        if let Some(mut subscription) = subscriptions.remove(topic) {
            subscription.active = false;
            
            if let Some(handle) = subscription.task_handle.take() {
                handle.abort();
            }
            
            // Update statistics
            {
                let mut stats = self.stats.write().await;
                stats.active_subscriptions = stats.active_subscriptions.saturating_sub(1);
            }
            
            info!("Unsubscribed from topic: {}", topic);
        }
        
        Ok(())
    }
    
    async fn health_check(&self) -> Result<BrokerHealth, RegulateAIError> {
        let mut conn = self.get_connection().await?;
        
        let start_time = std::time::Instant::now();
        let ping_result: RedisResult<String> = conn.ping().await;
        let response_time = start_time.elapsed();
        
        let (healthy, status) = match ping_result {
            Ok(_) => (true, "Redis broker is healthy".to_string()),
            Err(e) => (false, format!("Redis broker unhealthy: {}", e)),
        };
        
        self.return_connection(conn).await;
        
        let mut details = HashMap::new();
        details.insert("response_time_ms".to_string(), 
            serde_json::Value::Number(response_time.as_millis().into()));
        details.insert("use_streams".to_string(), 
            serde_json::Value::Bool(self.config.use_streams));
        
        Ok(BrokerHealth {
            healthy,
            status,
            connected: ping_result.is_ok(),
            last_check: Utc::now(),
            details,
        })
    }
    
    async fn get_stats(&self) -> Result<BrokerStats, RegulateAIError> {
        let stats = self.stats.read().await.clone();
        Ok(stats)
    }
}

impl Default for RedisBrokerConfig {
    fn default() -> Self {
        Self {
            redis_url: "redis://localhost:6379".to_string(),
            max_connections: 10,
            connection_timeout_ms: 5000,
            use_streams: true,
            consumer_group: "regulateai".to_string(),
            consumer_name: "consumer".to_string(),
            max_batch_size: 10,
            ack_timeout_ms: 30000,
            enable_persistence: true,
            message_ttl_seconds: 3600,
        }
    }
}
