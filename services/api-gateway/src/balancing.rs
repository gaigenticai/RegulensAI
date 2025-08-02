//! Load Balancing Module
//! 
//! This module provides various load balancing algorithms for distributing
//! requests across healthy service instances.

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, warn};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};

use regulateai_config::LoadBalancerConfig;
use regulateai_errors::RegulateAIError;
use crate::discovery::ServiceInstance;

/// Load balancer for service instance selection
pub struct LoadBalancer {
    /// Load balancing algorithm
    algorithm: LoadBalancingAlgorithm,
    
    /// Round-robin state
    round_robin_state: Arc<RwLock<HashMap<String, usize>>>,
    
    /// Weighted round-robin state
    weighted_state: Arc<RwLock<HashMap<String, WeightedState>>>,
    
    /// Least connections state
    connections_state: Arc<RwLock<HashMap<Uuid, u32>>>,
    
    /// Configuration
    config: LoadBalancerConfig,
}

/// Load balancing algorithms
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LoadBalancingAlgorithm {
    RoundRobin,
    WeightedRoundRobin,
    LeastConnections,
    Random,
    IpHash,
    HealthAware,
}

/// Weighted round-robin state
#[derive(Debug, Clone)]
struct WeightedState {
    /// Current weights for each instance
    current_weights: HashMap<Uuid, i32>,
    
    /// Total weight
    total_weight: i32,
}

/// Connection tracking for least connections algorithm
#[derive(Debug, Clone)]
struct ConnectionInfo {
    /// Instance ID
    instance_id: Uuid,
    
    /// Current connection count
    connection_count: u32,
    
    /// Last updated timestamp
    last_updated: DateTime<Utc>,
}

impl LoadBalancer {
    /// Create a new load balancer
    pub fn new(config: LoadBalancerConfig) -> Self {
        Self {
            algorithm: config.algorithm.clone(),
            round_robin_state: Arc::new(RwLock::new(HashMap::new())),
            weighted_state: Arc::new(RwLock::new(HashMap::new())),
            connections_state: Arc::new(RwLock::new(HashMap::new())),
            config,
        }
    }
    
    /// Select a service instance using the configured algorithm
    pub async fn select_instance(&self, instances: &[ServiceInstance]) -> Result<ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        // Filter healthy instances
        let healthy_instances: Vec<&ServiceInstance> = instances.iter()
            .filter(|instance| matches!(instance.health_status, crate::discovery::HealthStatus::Healthy))
            .collect();
        
        if healthy_instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No healthy instances available".to_string()));
        }
        
        let selected = match self.algorithm {
            LoadBalancingAlgorithm::RoundRobin => {
                self.round_robin_select(&healthy_instances).await
            }
            LoadBalancingAlgorithm::WeightedRoundRobin => {
                self.weighted_round_robin_select(&healthy_instances).await
            }
            LoadBalancingAlgorithm::LeastConnections => {
                self.least_connections_select(&healthy_instances).await
            }
            LoadBalancingAlgorithm::Random => {
                self.random_select(&healthy_instances).await
            }
            LoadBalancingAlgorithm::IpHash => {
                self.ip_hash_select(&healthy_instances, "default").await
            }
            LoadBalancingAlgorithm::HealthAware => {
                self.health_aware_select(&healthy_instances).await
            }
        }?;
        
        debug!("Selected instance {} for service {} using {:?}", 
               selected.id, selected.service_name, self.algorithm);
        
        Ok(selected.clone())
    }
    
    /// Round-robin selection
    async fn round_robin_select(&self, instances: &[&ServiceInstance]) -> Result<&ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        let service_name = &instances[0].service_name;
        let mut state = self.round_robin_state.write().await;
        
        let current_index = state.entry(service_name.clone()).or_insert(0);
        let selected_instance = instances[*current_index % instances.len()];
        
        *current_index = (*current_index + 1) % instances.len();
        
        Ok(selected_instance)
    }
    
    /// Weighted round-robin selection
    async fn weighted_round_robin_select(&self, instances: &[&ServiceInstance]) -> Result<&ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        let service_name = &instances[0].service_name;
        let mut state = self.weighted_state.write().await;
        
        // Initialize weighted state if not exists
        if !state.contains_key(service_name) {
            let mut current_weights = HashMap::new();
            let mut total_weight = 0;
            
            for instance in instances {
                current_weights.insert(instance.id, instance.weight as i32);
                total_weight += instance.weight as i32;
            }
            
            state.insert(service_name.clone(), WeightedState {
                current_weights,
                total_weight,
            });
        }
        
        let weighted_state = state.get_mut(service_name).unwrap();
        
        // Find instance with highest current weight
        let mut selected_instance = instances[0];
        let mut max_weight = i32::MIN;
        
        for instance in instances {
            if let Some(&current_weight) = weighted_state.current_weights.get(&instance.id) {
                if current_weight > max_weight {
                    max_weight = current_weight;
                    selected_instance = instance;
                }
            }
        }
        
        // Update weights
        if let Some(current_weight) = weighted_state.current_weights.get_mut(&selected_instance.id) {
            *current_weight -= weighted_state.total_weight;
        }
        
        for instance in instances {
            if let Some(current_weight) = weighted_state.current_weights.get_mut(&instance.id) {
                *current_weight += instance.weight as i32;
            }
        }
        
        Ok(selected_instance)
    }
    
    /// Least connections selection
    async fn least_connections_select(&self, instances: &[&ServiceInstance]) -> Result<&ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        let connections = self.connections_state.read().await;
        
        let mut selected_instance = instances[0];
        let mut min_connections = u32::MAX;
        
        for instance in instances {
            let connection_count = connections.get(&instance.id).copied().unwrap_or(0);
            if connection_count < min_connections {
                min_connections = connection_count;
                selected_instance = instance;
            }
        }
        
        Ok(selected_instance)
    }
    
    /// Random selection
    async fn random_select(&self, instances: &[&ServiceInstance]) -> Result<&ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let index = rng.gen_range(0..instances.len());
        
        Ok(instances[index])
    }
    
    /// IP hash selection (consistent hashing)
    async fn ip_hash_select(&self, instances: &[&ServiceInstance], client_ip: &str) -> Result<&ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        client_ip.hash(&mut hasher);
        let hash = hasher.finish();
        
        let index = (hash as usize) % instances.len();
        Ok(instances[index])
    }
    
    /// Health-aware selection (prefers healthier instances)
    async fn health_aware_select(&self, instances: &[&ServiceInstance]) -> Result<&ServiceInstance, RegulateAIError> {
        if instances.is_empty() {
            return Err(RegulateAIError::ServiceUnavailable("No instances available".to_string()));
        }
        
        // For now, just use round-robin among healthy instances
        // In a real implementation, this would consider health scores, response times, etc.
        self.round_robin_select(instances).await
    }
    
    /// Increment connection count for an instance
    pub async fn increment_connections(&self, instance_id: Uuid) {
        let mut connections = self.connections_state.write().await;
        *connections.entry(instance_id).or_insert(0) += 1;
    }
    
    /// Decrement connection count for an instance
    pub async fn decrement_connections(&self, instance_id: Uuid) {
        let mut connections = self.connections_state.write().await;
        if let Some(count) = connections.get_mut(&instance_id) {
            *count = count.saturating_sub(1);
        }
    }
    
    /// Get current connection counts
    pub async fn get_connection_counts(&self) -> HashMap<Uuid, u32> {
        self.connections_state.read().await.clone()
    }
    
    /// Reset load balancer state
    pub async fn reset_state(&self) {
        let mut round_robin = self.round_robin_state.write().await;
        let mut weighted = self.weighted_state.write().await;
        let mut connections = self.connections_state.write().await;
        
        round_robin.clear();
        weighted.clear();
        connections.clear();
    }
    
    /// Get load balancer statistics
    pub async fn get_stats(&self) -> LoadBalancerStats {
        let connections = self.connections_state.read().await;
        let total_connections: u32 = connections.values().sum();
        let active_instances = connections.len() as u32;
        
        LoadBalancerStats {
            algorithm: self.algorithm.clone(),
            total_connections,
            active_instances,
            average_connections_per_instance: if active_instances > 0 {
                total_connections as f64 / active_instances as f64
            } else {
                0.0
            },
            last_updated: chrono::Utc::now(),
        }
    }
}

/// Load balancer statistics
#[derive(Debug, Clone, Serialize)]
pub struct LoadBalancerStats {
    /// Current algorithm
    pub algorithm: LoadBalancingAlgorithm,
    
    /// Total active connections
    pub total_connections: u32,
    
    /// Number of active instances
    pub active_instances: u32,
    
    /// Average connections per instance
    pub average_connections_per_instance: f64,
    
    /// Last updated timestamp
    pub last_updated: DateTime<Utc>,
}

impl Default for LoadBalancingAlgorithm {
    fn default() -> Self {
        LoadBalancingAlgorithm::RoundRobin
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::discovery::{ServiceInstance, HealthStatus};
    use uuid::Uuid;
    use chrono::Utc;
    use std::collections::HashMap;
    
    fn create_test_instance(id: Uuid, service_name: &str, weight: u32) -> ServiceInstance {
        ServiceInstance {
            id,
            service_name: service_name.to_string(),
            host: "localhost".to_string(),
            port: 8080,
            version: "1.0.0".to_string(),
            health_status: HealthStatus::Healthy,
            last_health_check: Utc::now(),
            metadata: HashMap::new(),
            registered_at: Utc::now(),
            health_endpoint: "/health".to_string(),
            weight,
            tags: vec![],
        }
    }
    
    #[tokio::test]
    async fn test_round_robin_selection() {
        let config = LoadBalancerConfig {
            algorithm: LoadBalancingAlgorithm::RoundRobin,
            health_check_enabled: true,
            connection_timeout_ms: 5000,
        };
        
        let balancer = LoadBalancer::new(config);
        
        let instances = vec![
            create_test_instance(Uuid::new_v4(), "test-service", 100),
            create_test_instance(Uuid::new_v4(), "test-service", 100),
            create_test_instance(Uuid::new_v4(), "test-service", 100),
        ];
        
        // Test round-robin behavior
        let selected1 = balancer.select_instance(&instances).await.unwrap();
        let selected2 = balancer.select_instance(&instances).await.unwrap();
        let selected3 = balancer.select_instance(&instances).await.unwrap();
        let selected4 = balancer.select_instance(&instances).await.unwrap();
        
        // Should cycle through instances
        assert_eq!(selected1.id, instances[0].id);
        assert_eq!(selected2.id, instances[1].id);
        assert_eq!(selected3.id, instances[2].id);
        assert_eq!(selected4.id, instances[0].id); // Back to first
    }
    
    #[tokio::test]
    async fn test_weighted_round_robin_selection() {
        let config = LoadBalancerConfig {
            algorithm: LoadBalancingAlgorithm::WeightedRoundRobin,
            health_check_enabled: true,
            connection_timeout_ms: 5000,
        };
        
        let balancer = LoadBalancer::new(config);
        
        let instances = vec![
            create_test_instance(Uuid::new_v4(), "test-service", 300), // Higher weight
            create_test_instance(Uuid::new_v4(), "test-service", 100),
            create_test_instance(Uuid::new_v4(), "test-service", 100),
        ];
        
        // Test that higher weight instance is selected more often
        let mut selections = HashMap::new();
        for _ in 0..10 {
            let selected = balancer.select_instance(&instances).await.unwrap();
            *selections.entry(selected.id).or_insert(0) += 1;
        }
        
        // First instance should be selected more often due to higher weight
        let first_instance_selections = selections.get(&instances[0].id).unwrap_or(&0);
        assert!(*first_instance_selections > 3); // Should get more than 30% of selections
    }
    
    #[tokio::test]
    async fn test_connection_tracking() {
        let config = LoadBalancerConfig {
            algorithm: LoadBalancingAlgorithm::LeastConnections,
            health_check_enabled: true,
            connection_timeout_ms: 5000,
        };
        
        let balancer = LoadBalancer::new(config);
        let instance_id = Uuid::new_v4();
        
        // Test connection increment/decrement
        balancer.increment_connections(instance_id).await;
        balancer.increment_connections(instance_id).await;
        
        let counts = balancer.get_connection_counts().await;
        assert_eq!(counts.get(&instance_id), Some(&2));
        
        balancer.decrement_connections(instance_id).await;
        let counts = balancer.get_connection_counts().await;
        assert_eq!(counts.get(&instance_id), Some(&1));
    }
    
    #[tokio::test]
    async fn test_load_balancer_stats() {
        let config = LoadBalancerConfig {
            algorithm: LoadBalancingAlgorithm::RoundRobin,
            health_check_enabled: true,
            connection_timeout_ms: 5000,
        };

        let balancer = LoadBalancer::new(config);
        let instance_id = Uuid::new_v4();

        balancer.increment_connections(instance_id).await;
        balancer.increment_connections(instance_id).await;

        let stats = balancer.get_stats().await;
        assert_eq!(stats.total_connections, 2);
        assert_eq!(stats.active_instances, 1);
        assert_eq!(stats.average_connections_per_instance, 2.0);
    }
}
