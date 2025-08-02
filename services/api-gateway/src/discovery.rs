//! Service Discovery Module
//! 
//! This module handles service registration, health checking, and discovery
//! for the RegulateAI microservices ecosystem.

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{interval, Duration};
use tracing::{info, error, warn, debug};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use reqwest::Client;

use regulateai_config::APIGatewayConfig;
use regulateai_errors::RegulateAIError;

/// Service discovery manager
pub struct ServiceDiscovery {
    /// Registered service instances
    services: Arc<RwLock<HashMap<String, Vec<ServiceInstance>>>>,
    
    /// HTTP client for health checks
    http_client: Client,
    
    /// Configuration
    config: APIGatewayConfig,
    
    /// Health check statistics
    health_stats: Arc<RwLock<HashMap<String, HealthStats>>>,
}

/// Service instance information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceInstance {
    /// Unique instance ID
    pub id: Uuid,
    
    /// Service name
    pub service_name: String,
    
    /// Host address
    pub host: String,
    
    /// Port number
    pub port: u16,
    
    /// Service version
    pub version: String,
    
    /// Health status
    pub health_status: HealthStatus,
    
    /// Last health check timestamp
    pub last_health_check: DateTime<Utc>,
    
    /// Service metadata
    pub metadata: HashMap<String, String>,
    
    /// Registration timestamp
    pub registered_at: DateTime<Utc>,
    
    /// Health check endpoint
    pub health_endpoint: String,
    
    /// Service weight for load balancing
    pub weight: u32,
    
    /// Service tags
    pub tags: Vec<String>,
}

/// Health status enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum HealthStatus {
    Healthy,
    Unhealthy,
    Unknown,
    Degraded,
}

/// Health check statistics
#[derive(Debug, Clone)]
pub struct HealthStats {
    /// Total health checks performed
    pub total_checks: u64,
    
    /// Successful health checks
    pub successful_checks: u64,
    
    /// Failed health checks
    pub failed_checks: u64,
    
    /// Average response time in milliseconds
    pub avg_response_time_ms: f64,
    
    /// Last check timestamp
    pub last_check: DateTime<Utc>,
    
    /// Consecutive failures
    pub consecutive_failures: u32,
}

impl ServiceDiscovery {
    /// Create a new service discovery instance
    pub async fn new(config: APIGatewayConfig) -> Result<Self, RegulateAIError> {
        info!("Initializing service discovery");
        
        let http_client = Client::builder()
            .timeout(Duration::from_millis(config.health_check_timeout_ms))
            .build()
            .map_err(|e| RegulateAIError::ConfigurationError(format!("HTTP client error: {}", e)))?;
        
        let discovery = Self {
            services: Arc::new(RwLock::new(HashMap::new())),
            http_client,
            config,
            health_stats: Arc::new(RwLock::new(HashMap::new())),
        };
        
        // Register default services
        discovery.register_default_services().await?;
        
        // Start health check background task
        discovery.start_health_check_task().await;
        
        Ok(discovery)
    }
    
    /// Register a service instance
    pub async fn register_service(&self, instance: ServiceInstance) -> Result<(), RegulateAIError> {
        info!("Registering service instance: {} ({}:{})", 
              instance.service_name, instance.host, instance.port);
        
        let mut services = self.services.write().await;
        services.entry(instance.service_name.clone())
            .or_insert_with(Vec::new)
            .push(instance.clone());
        
        // Initialize health stats
        let mut health_stats = self.health_stats.write().await;
        health_stats.insert(instance.id.to_string(), HealthStats {
            total_checks: 0,
            successful_checks: 0,
            failed_checks: 0,
            avg_response_time_ms: 0.0,
            last_check: Utc::now(),
            consecutive_failures: 0,
        });
        
        info!("Service instance registered successfully: {}", instance.id);
        Ok(())
    }
    
    /// Deregister a service instance
    pub async fn deregister_service(&self, service_name: &str, instance_id: Uuid) -> Result<(), RegulateAIError> {
        info!("Deregistering service instance: {} ({})", service_name, instance_id);
        
        let mut services = self.services.write().await;
        if let Some(instances) = services.get_mut(service_name) {
            instances.retain(|instance| instance.id != instance_id);
            
            if instances.is_empty() {
                services.remove(service_name);
            }
        }
        
        // Remove health stats
        let mut health_stats = self.health_stats.write().await;
        health_stats.remove(&instance_id.to_string());
        
        info!("Service instance deregistered: {}", instance_id);
        Ok(())
    }
    
    /// Get all service instances for a service
    pub async fn get_service_instances(&self, service_name: &str) -> Result<Vec<ServiceInstance>, RegulateAIError> {
        let services = self.services.read().await;
        
        match services.get(service_name) {
            Some(instances) => Ok(instances.clone()),
            None => Err(RegulateAIError::NotFound(format!("Service not found: {}", service_name))),
        }
    }
    
    /// Get healthy service instances for a service
    pub async fn get_healthy_service_instances(&self, service_name: &str) -> Result<Vec<ServiceInstance>, RegulateAIError> {
        let instances = self.get_service_instances(service_name).await?;
        let healthy_instances: Vec<ServiceInstance> = instances.into_iter()
            .filter(|instance| instance.health_status == HealthStatus::Healthy)
            .collect();
        
        if healthy_instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable(
                format!("No healthy instances found for service: {}", service_name)
            ));
        }
        
        Ok(healthy_instances)
    }
    
    /// Get all healthy services
    pub async fn get_healthy_services(&self) -> Vec<String> {
        let services = self.services.read().await;
        let mut healthy_services = Vec::new();
        
        for (service_name, instances) in services.iter() {
            if instances.iter().any(|instance| instance.health_status == HealthStatus::Healthy) {
                healthy_services.push(service_name.clone());
            }
        }
        
        healthy_services
    }
    
    /// Get all registered services
    pub async fn get_all_services(&self) -> HashMap<String, Vec<ServiceInstance>> {
        self.services.read().await.clone()
    }
    
    /// Perform health check on a service instance
    async fn health_check_instance(&self, instance: &mut ServiceInstance) -> bool {
        let start_time = std::time::Instant::now();
        let health_url = format!("http://{}:{}{}", instance.host, instance.port, instance.health_endpoint);
        
        debug!("Health checking instance: {} at {}", instance.id, health_url);
        
        match self.http_client.get(&health_url).send().await {
            Ok(response) => {
                let response_time = start_time.elapsed().as_millis() as f64;
                let is_healthy = response.status().is_success();
                
                instance.health_status = if is_healthy {
                    HealthStatus::Healthy
                } else {
                    HealthStatus::Unhealthy
                };
                
                instance.last_health_check = Utc::now();
                
                // Update health stats
                self.update_health_stats(&instance.id.to_string(), response_time, is_healthy).await;
                
                debug!("Health check completed for {}: {} ({}ms)", 
                       instance.id, instance.health_status, response_time);
                
                is_healthy
            }
            Err(e) => {
                warn!("Health check failed for instance {}: {}", instance.id, e);
                
                instance.health_status = HealthStatus::Unhealthy;
                instance.last_health_check = Utc::now();
                
                // Update health stats
                self.update_health_stats(&instance.id.to_string(), 0.0, false).await;
                
                false
            }
        }
    }
    
    /// Update health statistics for an instance
    async fn update_health_stats(&self, instance_id: &str, response_time: f64, success: bool) {
        let mut health_stats = self.health_stats.write().await;
        
        if let Some(stats) = health_stats.get_mut(instance_id) {
            stats.total_checks += 1;
            
            if success {
                stats.successful_checks += 1;
                stats.consecutive_failures = 0;
                
                // Update average response time
                stats.avg_response_time_ms = (stats.avg_response_time_ms * (stats.total_checks - 1) as f64 + response_time) / stats.total_checks as f64;
            } else {
                stats.failed_checks += 1;
                stats.consecutive_failures += 1;
            }
            
            stats.last_check = Utc::now();
        }
    }
    
    /// Start background health check task
    async fn start_health_check_task(&self) {
        let services = self.services.clone();
        let http_client = self.http_client.clone();
        let health_stats = self.health_stats.clone();
        let check_interval = self.config.health_check_interval_ms;
        
        tokio::spawn(async move {
            let mut interval = interval(Duration::from_millis(check_interval));
            
            loop {
                interval.tick().await;
                
                let mut services_guard = services.write().await;
                
                for instances in services_guard.values_mut() {
                    for instance in instances.iter_mut() {
                        // Perform health check
                        let start_time = std::time::Instant::now();
                        let health_url = format!("http://{}:{}{}", 
                                                instance.host, instance.port, instance.health_endpoint);
                        
                        match http_client.get(&health_url).send().await {
                            Ok(response) => {
                                let response_time = start_time.elapsed().as_millis() as f64;
                                let is_healthy = response.status().is_success();
                                
                                instance.health_status = if is_healthy {
                                    HealthStatus::Healthy
                                } else {
                                    HealthStatus::Unhealthy
                                };
                                
                                instance.last_health_check = Utc::now();
                                
                                // Update health stats
                                let mut stats_guard = health_stats.write().await;
                                if let Some(stats) = stats_guard.get_mut(&instance.id.to_string()) {
                                    stats.total_checks += 1;
                                    
                                    if is_healthy {
                                        stats.successful_checks += 1;
                                        stats.consecutive_failures = 0;
                                        stats.avg_response_time_ms = (stats.avg_response_time_ms * (stats.total_checks - 1) as f64 + response_time) / stats.total_checks as f64;
                                    } else {
                                        stats.failed_checks += 1;
                                        stats.consecutive_failures += 1;
                                    }
                                    
                                    stats.last_check = Utc::now();
                                }
                            }
                            Err(_) => {
                                instance.health_status = HealthStatus::Unhealthy;
                                instance.last_health_check = Utc::now();
                                
                                // Update health stats
                                let mut stats_guard = health_stats.write().await;
                                if let Some(stats) = stats_guard.get_mut(&instance.id.to_string()) {
                                    stats.total_checks += 1;
                                    stats.failed_checks += 1;
                                    stats.consecutive_failures += 1;
                                    stats.last_check = Utc::now();
                                }
                            }
                        }
                    }
                }
            }
        });
        
        info!("Health check background task started with interval: {}ms", check_interval);
    }
    
    /// Register default services based on configuration
    async fn register_default_services(&self) -> Result<(), RegulateAIError> {
        info!("Registering default services");
        
        let default_services = vec![
            ("aml-service", 8080),
            ("compliance-service", 8081),
            ("risk-management-service", 8082),
            ("fraud-detection-service", 8083),
            ("cybersecurity-service", 8084),
            ("ai-orchestration-service", 8085),
            ("documentation-service", 8086),
        ];
        
        for (service_name, port) in default_services {
            let instance = ServiceInstance {
                id: Uuid::new_v4(),
                service_name: service_name.to_string(),
                host: "localhost".to_string(),
                port,
                version: "1.0.0".to_string(),
                health_status: HealthStatus::Unknown,
                last_health_check: Utc::now(),
                metadata: HashMap::new(),
                registered_at: Utc::now(),
                health_endpoint: "/health".to_string(),
                weight: 100,
                tags: vec!["default".to_string()],
            };
            
            self.register_service(instance).await?;
        }
        
        info!("Default services registered successfully");
        Ok(())
    }
    
    /// Get health statistics for all instances
    pub async fn get_health_stats(&self) -> HashMap<String, HealthStats> {
        self.health_stats.read().await.clone()
    }
}
