//! IP Filtering and Geolocation-based Security

use crate::errors::{SecurityError, SecurityResult};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::net::IpAddr;
use ipnet::IpNet;
use chrono::{DateTime, Utc};

/// IP filtering system
pub struct IpFilter {
    rules: Vec<IpFilterRule>,
    blocked_ips: HashSet<IpAddr>,
    allowed_ips: HashSet<IpAddr>,
    blocked_networks: Vec<IpNet>,
    allowed_networks: Vec<IpNet>,
    country_rules: HashMap<String, IpFilterAction>,
    config: IpFilterConfig,
}

/// IP filter rule
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IpFilterRule {
    pub id: String,
    pub name: String,
    pub rule_type: IpFilterRuleType,
    pub action: IpFilterAction,
    pub priority: u32,
    pub enabled: bool,
    pub created_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
}

/// IP filter rule types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IpFilterRuleType {
    SingleIp(IpAddr),
    IpRange { start: IpAddr, end: IpAddr },
    Network(IpNet),
    Country(String),
    Asn(u32),
    Custom(String),
}

/// IP filter actions
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum IpFilterAction {
    Allow,
    Block,
    Challenge,
    RateLimit { requests_per_minute: u32 },
    Log,
}

/// IP filter configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IpFilterConfig {
    pub enabled: bool,
    pub default_action: IpFilterAction,
    pub enable_geolocation: bool,
    pub enable_asn_filtering: bool,
    pub blocked_countries: Vec<String>,
    pub allowed_countries: Vec<String>,
    pub blocked_asns: Vec<u32>,
    pub max_rules: usize,
}

impl IpFilter {
    /// Create a new IP filter
    pub fn new(config: IpFilterConfig) -> Self {
        Self {
            rules: Vec::new(),
            blocked_ips: HashSet::new(),
            allowed_ips: HashSet::new(),
            blocked_networks: Vec::new(),
            allowed_networks: Vec::new(),
            country_rules: HashMap::new(),
            config,
        }
    }

    /// Check if an IP address should be allowed
    pub async fn check_ip(&self, ip_str: &str) -> SecurityResult<()> {
        if !self.config.enabled {
            return Ok(());
        }

        let ip: IpAddr = ip_str.parse()
            .map_err(|_| SecurityError::ValidationError {
                field: "ip_address".to_string(),
                message: "Invalid IP address format".to_string(),
            })?;

        // Check explicit allow list first
        if self.allowed_ips.contains(&ip) {
            return Ok(());
        }

        // Check explicit block list
        if self.blocked_ips.contains(&ip) {
            return Err(SecurityError::IpBlocked {
                ip: ip_str.to_string(),
                until: Utc::now() + chrono::Duration::hours(24),
            });
        }

        // Check network rules
        for network in &self.blocked_networks {
            if network.contains(&ip) {
                return Err(SecurityError::IpBlocked {
                    ip: ip_str.to_string(),
                    until: Utc::now() + chrono::Duration::hours(24),
                });
            }
        }

        for network in &self.allowed_networks {
            if network.contains(&ip) {
                return Ok(());
            }
        }

        // Check rules in priority order
        let mut applicable_rules: Vec<_> = self.rules.iter()
            .filter(|rule| rule.enabled && !self.is_rule_expired(rule))
            .collect();
        applicable_rules.sort_by_key(|rule| rule.priority);

        for rule in applicable_rules {
            if self.rule_matches(rule, &ip).await? {
                match rule.action {
                    IpFilterAction::Allow => return Ok(()),
                    IpFilterAction::Block => {
                        return Err(SecurityError::IpBlocked {
                            ip: ip_str.to_string(),
                            until: rule.expires_at.unwrap_or_else(|| Utc::now() + chrono::Duration::hours(24)),
                        });
                    }
                    IpFilterAction::Challenge => {
                        // For now, treat as block
                        return Err(SecurityError::IpBlocked {
                            ip: ip_str.to_string(),
                            until: Utc::now() + chrono::Duration::minutes(15),
                        });
                    }
                    IpFilterAction::RateLimit { .. } => {
                        // Rate limiting would be handled by the rate limiter
                        continue;
                    }
                    IpFilterAction::Log => {
                        tracing::info!(ip = %ip, rule_id = %rule.id, "IP filter rule matched");
                        continue;
                    }
                }
            }
        }

        // Apply default action
        match self.config.default_action {
            IpFilterAction::Allow => Ok(()),
            IpFilterAction::Block => Err(SecurityError::IpBlocked {
                ip: ip_str.to_string(),
                until: Utc::now() + chrono::Duration::hours(1),
            }),
            _ => Ok(()), // Other actions default to allow
        }
    }

    /// Check if a rule matches an IP
    async fn rule_matches(&self, rule: &IpFilterRule, ip: &IpAddr) -> SecurityResult<bool> {
        match &rule.rule_type {
            IpFilterRuleType::SingleIp(rule_ip) => Ok(rule_ip == ip),
            IpFilterRuleType::IpRange { start, end } => {
                Ok(ip >= start && ip <= end)
            }
            IpFilterRuleType::Network(network) => Ok(network.contains(ip)),
            IpFilterRuleType::Country(country) => {
                if self.config.enable_geolocation {
                    self.check_ip_country(ip, country).await
                } else {
                    Ok(false)
                }
            }
            IpFilterRuleType::Asn(asn) => {
                if self.config.enable_asn_filtering {
                    self.check_ip_asn(ip, *asn).await
                } else {
                    Ok(false)
                }
            }
            IpFilterRuleType::Custom(_) => {
                // Custom rules would be implemented based on specific requirements
                Ok(false)
            }
        }
    }

    /// Check IP country (would integrate with GeoIP database)
    async fn check_ip_country(&self, _ip: &IpAddr, _country: &str) -> SecurityResult<bool> {
        // In a real implementation, this would query a GeoIP database
        // For now, return false
        Ok(false)
    }

    /// Check IP ASN (would integrate with ASN database)
    async fn check_ip_asn(&self, _ip: &IpAddr, _asn: u32) -> SecurityResult<bool> {
        // In a real implementation, this would query an ASN database
        // For now, return false
        Ok(false)
    }

    /// Check if a rule has expired
    fn is_rule_expired(&self, rule: &IpFilterRule) -> bool {
        if let Some(expires_at) = rule.expires_at {
            Utc::now() > expires_at
        } else {
            false
        }
    }

    /// Add a new IP filter rule
    pub async fn add_rule(&mut self, rule: IpFilterRule) -> SecurityResult<()> {
        if self.rules.len() >= self.config.max_rules {
            return Err(SecurityError::ResourceExhaustion {
                resource: "IP filter rules".to_string(),
            });
        }

        self.rules.push(rule);
        self.rules.sort_by_key(|r| r.priority);
        Ok(())
    }

    /// Remove an IP filter rule
    pub async fn remove_rule(&mut self, rule_id: &str) -> SecurityResult<()> {
        self.rules.retain(|rule| rule.id != rule_id);
        Ok(())
    }

    /// Block an IP address temporarily
    pub async fn block_ip_temporarily(
        &mut self,
        ip_str: &str,
        duration_minutes: u64,
        reason: &str,
    ) -> SecurityResult<()> {
        let ip: IpAddr = ip_str.parse()
            .map_err(|_| SecurityError::ValidationError {
                field: "ip_address".to_string(),
                message: "Invalid IP address format".to_string(),
            })?;

        let rule = IpFilterRule {
            id: uuid::Uuid::new_v4().to_string(),
            name: format!("Temporary block: {}", reason),
            rule_type: IpFilterRuleType::SingleIp(ip),
            action: IpFilterAction::Block,
            priority: 1, // High priority
            enabled: true,
            created_at: Utc::now(),
            expires_at: Some(Utc::now() + chrono::Duration::minutes(duration_minutes as i64)),
        };

        self.add_rule(rule).await?;
        Ok(())
    }

    /// Block an IP address permanently
    pub async fn block_ip_permanently(&mut self, ip_str: &str, reason: &str) -> SecurityResult<()> {
        let ip: IpAddr = ip_str.parse()
            .map_err(|_| SecurityError::ValidationError {
                field: "ip_address".to_string(),
                message: "Invalid IP address format".to_string(),
            })?;

        self.blocked_ips.insert(ip);

        let rule = IpFilterRule {
            id: uuid::Uuid::new_v4().to_string(),
            name: format!("Permanent block: {}", reason),
            rule_type: IpFilterRuleType::SingleIp(ip),
            action: IpFilterAction::Block,
            priority: 1,
            enabled: true,
            created_at: Utc::now(),
            expires_at: None,
        };

        self.add_rule(rule).await?;
        Ok(())
    }

    /// Allow an IP address
    pub async fn allow_ip(&mut self, ip_str: &str) -> SecurityResult<()> {
        let ip: IpAddr = ip_str.parse()
            .map_err(|_| SecurityError::ValidationError {
                field: "ip_address".to_string(),
                message: "Invalid IP address format".to_string(),
            })?;

        self.allowed_ips.insert(ip);
        self.blocked_ips.remove(&ip);

        // Remove any blocking rules for this IP
        self.rules.retain(|rule| {
            if let IpFilterRuleType::SingleIp(rule_ip) = &rule.rule_type {
                if rule_ip == &ip && rule.action == IpFilterAction::Block {
                    return false;
                }
            }
            true
        });

        Ok(())
    }

    /// Block a network range
    pub async fn block_network(&mut self, network_str: &str, reason: &str) -> SecurityResult<()> {
        let network: IpNet = network_str.parse()
            .map_err(|_| SecurityError::ValidationError {
                field: "network".to_string(),
                message: "Invalid network format".to_string(),
            })?;

        self.blocked_networks.push(network);

        let rule = IpFilterRule {
            id: uuid::Uuid::new_v4().to_string(),
            name: format!("Network block: {}", reason),
            rule_type: IpFilterRuleType::Network(network),
            action: IpFilterAction::Block,
            priority: 10,
            enabled: true,
            created_at: Utc::now(),
            expires_at: None,
        };

        self.add_rule(rule).await?;
        Ok(())
    }

    /// Block a country
    pub async fn block_country(&mut self, country_code: &str, reason: &str) -> SecurityResult<()> {
        if !self.config.enable_geolocation {
            return Err(SecurityError::Configuration(
                "Geolocation filtering is not enabled".to_string()
            ));
        }

        let rule = IpFilterRule {
            id: uuid::Uuid::new_v4().to_string(),
            name: format!("Country block: {}", reason),
            rule_type: IpFilterRuleType::Country(country_code.to_string()),
            action: IpFilterAction::Block,
            priority: 20,
            enabled: true,
            created_at: Utc::now(),
            expires_at: None,
        };

        self.add_rule(rule).await?;
        Ok(())
    }

    /// Get IP filter statistics
    pub async fn get_statistics(&self) -> IpFilterStatistics {
        let now = Utc::now();
        let active_rules = self.rules.iter()
            .filter(|rule| rule.enabled && !self.is_rule_expired(rule))
            .count();

        let expired_rules = self.rules.iter()
            .filter(|rule| self.is_rule_expired(rule))
            .count();

        IpFilterStatistics {
            total_rules: self.rules.len(),
            active_rules,
            expired_rules,
            blocked_ips: self.blocked_ips.len(),
            allowed_ips: self.allowed_ips.len(),
            blocked_networks: self.blocked_networks.len(),
            allowed_networks: self.allowed_networks.len(),
            rules_by_action: self.rules.iter()
                .fold(HashMap::new(), |mut acc, rule| {
                    *acc.entry(rule.action.clone()).or_insert(0) += 1;
                    acc
                }),
        }
    }

    /// Clean up expired rules
    pub async fn cleanup_expired_rules(&mut self) -> SecurityResult<usize> {
        let initial_count = self.rules.len();
        self.rules.retain(|rule| !self.is_rule_expired(rule));
        Ok(initial_count - self.rules.len())
    }

    /// Update configuration
    pub async fn update_config(&mut self, new_config: IpFilterConfig) -> SecurityResult<()> {
        self.config = new_config;
        Ok(())
    }
}

/// IP filter statistics
#[derive(Debug, Serialize)]
pub struct IpFilterStatistics {
    pub total_rules: usize,
    pub active_rules: usize,
    pub expired_rules: usize,
    pub blocked_ips: usize,
    pub allowed_ips: usize,
    pub blocked_networks: usize,
    pub allowed_networks: usize,
    pub rules_by_action: HashMap<IpFilterAction, usize>,
}

impl Default for IpFilterConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            default_action: IpFilterAction::Allow,
            enable_geolocation: false,
            enable_asn_filtering: false,
            blocked_countries: vec![],
            allowed_countries: vec![],
            blocked_asns: vec![],
            max_rules: 10000,
        }
    }
}
