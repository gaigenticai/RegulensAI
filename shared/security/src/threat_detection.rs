//! Advanced Threat Detection System
//! 
//! Provides real-time threat detection and analysis including:
//! - Behavioral analysis
//! - Anomaly detection
//! - Attack pattern recognition
//! - Threat intelligence integration

use crate::types::SecurityRequest;
use crate::errors::{SecurityError, SecurityResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc, Duration};
use tokio::sync::RwLock;
use std::sync::Arc;
use tracing::{info, warn, error};

/// Advanced threat detector
pub struct ThreatDetector {
    behavioral_analyzer: Arc<BehavioralAnalyzer>,
    anomaly_detector: Arc<AnomalyDetector>,
    threat_intelligence: Arc<ThreatIntelligence>,
    config: ThreatDetectionConfig,
}

/// Threat detection configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreatDetectionConfig {
    pub enabled: bool,
    pub behavioral_analysis_enabled: bool,
    pub anomaly_detection_enabled: bool,
    pub threat_intelligence_enabled: bool,
    pub detection_threshold: f32,
    pub learning_period_hours: u64,
    pub max_tracking_entries: usize,
}

/// Threat levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum ThreatLevel {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

/// Threat types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ThreatType {
    BruteForceAttack,
    DistributedDenialOfService,
    SqlInjectionAttempt,
    CrossSiteScriptingAttempt,
    PathTraversalAttempt,
    CommandInjectionAttempt,
    SessionHijacking,
    CredentialStuffing,
    AccountTakeover,
    DataExfiltration,
    MaliciousBot,
    SuspiciousUserAgent,
    AnomalousTraffic,
    GeolocationAnomaly,
    TimeBasedAnomaly,
    VolumeAnomaly,
    PatternAnomaly,
    ThreatIntelligenceMatch,
    Custom(String),
}

/// Detected threat information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectedThreat {
    pub id: String,
    pub threat_type: ThreatType,
    pub level: ThreatLevel,
    pub confidence: f32,
    pub source_ip: String,
    pub user_agent: Option<String>,
    pub description: String,
    pub evidence: Vec<String>,
    pub indicators: HashMap<String, serde_json::Value>,
    pub detected_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
}

/// Behavioral analysis for detecting suspicious patterns
pub struct BehavioralAnalyzer {
    user_sessions: Arc<RwLock<HashMap<String, UserSession>>>,
    ip_behavior: Arc<RwLock<HashMap<String, IpBehavior>>>,
    config: BehavioralAnalysisConfig,
}

/// User session tracking
#[derive(Debug, Clone)]
pub struct UserSession {
    pub session_id: String,
    pub user_id: Option<String>,
    pub ip_address: String,
    pub user_agent: String,
    pub first_seen: DateTime<Utc>,
    pub last_seen: DateTime<Utc>,
    pub request_count: u64,
    pub failed_auth_attempts: u64,
    pub suspicious_activities: Vec<SuspiciousActivity>,
    pub risk_score: f32,
}

/// IP address behavior tracking
#[derive(Debug, Clone)]
pub struct IpBehavior {
    pub ip_address: String,
    pub first_seen: DateTime<Utc>,
    pub last_seen: DateTime<Utc>,
    pub request_count: u64,
    pub unique_user_agents: std::collections::HashSet<String>,
    pub unique_sessions: std::collections::HashSet<String>,
    pub countries: std::collections::HashSet<String>,
    pub suspicious_activities: Vec<SuspiciousActivity>,
    pub reputation_score: f32,
}

/// Suspicious activity record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuspiciousActivity {
    pub activity_type: String,
    pub description: String,
    pub severity: ThreatLevel,
    pub timestamp: DateTime<Utc>,
    pub evidence: HashMap<String, serde_json::Value>,
}

/// Behavioral analysis configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BehavioralAnalysisConfig {
    pub max_failed_auth_attempts: u64,
    pub suspicious_request_rate: u64, // requests per minute
    pub max_user_agents_per_ip: usize,
    pub geolocation_change_threshold: f32, // km
    pub session_timeout_minutes: u64,
    pub risk_score_threshold: f32,
}

/// Anomaly detection system
pub struct AnomalyDetector {
    baseline_metrics: Arc<RwLock<BaselineMetrics>>,
    current_metrics: Arc<RwLock<CurrentMetrics>>,
    config: AnomalyDetectionConfig,
}

/// Baseline metrics for anomaly detection
#[derive(Debug, Clone)]
pub struct BaselineMetrics {
    pub avg_requests_per_minute: f64,
    pub avg_response_time: f64,
    pub common_user_agents: HashMap<String, u64>,
    pub common_paths: HashMap<String, u64>,
    pub geographic_distribution: HashMap<String, u64>,
    pub time_patterns: HashMap<u8, u64>, // hour -> request count
    pub last_updated: DateTime<Utc>,
}

/// Current metrics for comparison
#[derive(Debug, Clone)]
pub struct CurrentMetrics {
    pub requests_per_minute: f64,
    pub response_time: f64,
    pub user_agent_distribution: HashMap<String, u64>,
    pub path_distribution: HashMap<String, u64>,
    pub geographic_distribution: HashMap<String, u64>,
    pub time_distribution: HashMap<u8, u64>,
    pub last_updated: DateTime<Utc>,
}

/// Anomaly detection configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyDetectionConfig {
    pub deviation_threshold: f32, // standard deviations
    pub minimum_baseline_samples: u64,
    pub baseline_update_interval_hours: u64,
    pub anomaly_persistence_minutes: u64,
}

/// Threat intelligence system
pub struct ThreatIntelligence {
    malicious_ips: Arc<RwLock<std::collections::HashSet<String>>>,
    malicious_user_agents: Arc<RwLock<std::collections::HashSet<String>>>,
    attack_signatures: Arc<RwLock<Vec<AttackSignature>>>,
    config: ThreatIntelligenceConfig,
}

/// Attack signature for pattern matching
#[derive(Debug, Clone)]
pub struct AttackSignature {
    pub id: String,
    pub name: String,
    pub pattern: regex::Regex,
    pub threat_type: ThreatType,
    pub confidence: f32,
    pub created_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
}

/// Threat intelligence configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreatIntelligenceConfig {
    pub update_interval_hours: u64,
    pub signature_expiry_days: u64,
    pub external_feeds_enabled: bool,
    pub custom_signatures_enabled: bool,
}

impl ThreatDetector {
    /// Create a new threat detector
    pub fn new(config: ThreatDetectionConfig) -> Self {
        Self {
            behavioral_analyzer: Arc::new(BehavioralAnalyzer::new(
                BehavioralAnalysisConfig::default()
            )),
            anomaly_detector: Arc::new(AnomalyDetector::new(
                AnomalyDetectionConfig::default()
            )),
            threat_intelligence: Arc::new(ThreatIntelligence::new(
                ThreatIntelligenceConfig::default()
            )),
            config,
        }
    }

    /// Analyze a request for threats
    pub async fn analyze_request(&self, request: &SecurityRequest) -> SecurityResult<Option<DetectedThreat>> {
        if !self.config.enabled {
            return Ok(None);
        }

        let mut threats = Vec::new();

        // Behavioral analysis
        if self.config.behavioral_analysis_enabled {
            if let Some(threat) = self.behavioral_analyzer.analyze(request).await? {
                threats.push(threat);
            }
        }

        // Anomaly detection
        if self.config.anomaly_detection_enabled {
            if let Some(threat) = self.anomaly_detector.analyze(request).await? {
                threats.push(threat);
            }
        }

        // Threat intelligence matching
        if self.config.threat_intelligence_enabled {
            if let Some(threat) = self.threat_intelligence.analyze(request).await? {
                threats.push(threat);
            }
        }

        // Return highest severity threat above threshold
        threats.sort_by(|a, b| b.level.cmp(&a.level).then(b.confidence.partial_cmp(&a.confidence).unwrap()));
        
        for threat in threats {
            if threat.confidence >= self.config.detection_threshold {
                return Ok(Some(threat));
            }
        }

        Ok(None)
    }

    /// Update threat detection models
    pub async fn update_models(&self) -> SecurityResult<()> {
        // Update behavioral baselines
        self.behavioral_analyzer.update_baselines().await?;
        
        // Update anomaly detection baselines
        self.anomaly_detector.update_baselines().await?;
        
        // Update threat intelligence
        self.threat_intelligence.update_intelligence().await?;
        
        Ok(())
    }

    /// Get threat detection statistics
    pub async fn get_statistics(&self) -> ThreatDetectionStatistics {
        ThreatDetectionStatistics {
            behavioral_sessions_tracked: self.behavioral_analyzer.get_session_count().await,
            behavioral_ips_tracked: self.behavioral_analyzer.get_ip_count().await,
            anomaly_baseline_age_hours: self.anomaly_detector.get_baseline_age().await,
            threat_intelligence_signatures: self.threat_intelligence.get_signature_count().await,
            threat_intelligence_malicious_ips: self.threat_intelligence.get_malicious_ip_count().await,
        }
    }
}

impl BehavioralAnalyzer {
    pub fn new(config: BehavioralAnalysisConfig) -> Self {
        Self {
            user_sessions: Arc::new(RwLock::new(HashMap::new())),
            ip_behavior: Arc::new(RwLock::new(HashMap::new())),
            config,
        }
    }

    pub async fn analyze(&self, request: &HttpRequest) -> SecurityResult<Option<DetectedThreat>> {
        // Update session and IP tracking
        self.update_tracking(request).await?;

        // Check for suspicious patterns
        if let Some(threat) = self.check_brute_force(request).await? {
            return Ok(Some(threat));
        }

        if let Some(threat) = self.check_rate_anomaly(request).await? {
            return Ok(Some(threat));
        }

        if let Some(threat) = self.check_user_agent_anomaly(request).await? {
            return Ok(Some(threat));
        }

        Ok(None)
    }

    async fn update_tracking(&self, request: &HttpRequest) -> SecurityResult<()> {
        let now = Utc::now();

        // Update IP behavior
        {
            let mut ip_behavior = self.ip_behavior.write().await;
            let behavior = ip_behavior.entry(request.client_ip.clone()).or_insert_with(|| {
                IpBehavior {
                    ip_address: request.client_ip.clone(),
                    first_seen: now,
                    last_seen: now,
                    request_count: 0,
                    unique_user_agents: std::collections::HashSet::new(),
                    unique_sessions: std::collections::HashSet::new(),
                    countries: std::collections::HashSet::new(),
                    suspicious_activities: Vec::new(),
                    reputation_score: 0.5, // neutral
                }
            });

            behavior.last_seen = now;
            behavior.request_count += 1;
            behavior.unique_user_agents.insert(request.user_agent.clone());
        }

        Ok(())
    }

    async fn check_brute_force(&self, request: &HttpRequest) -> SecurityResult<Option<DetectedThreat>> {
        let mut user_sessions = self.user_sessions.write().await;
        let client_ip = request.client_ip.to_string();

        // Track failed login attempts per IP
        let session = user_sessions.entry(client_ip.clone()).or_insert_with(|| UserSession {
            ip: client_ip.clone(),
            user_agent: request.user_agent.clone(),
            first_seen: Utc::now(),
            last_seen: Utc::now(),
            request_count: 0,
            failed_login_attempts: 0,
            suspicious_patterns: Vec::new(),
        });

        session.last_seen = Utc::now();
        session.request_count += 1;

        // Check for login failure patterns in the request
        let is_login_request = request.path.contains("/login") || request.path.contains("/auth");
        let has_failure_indicators = request.body.as_ref()
            .map(|body| body.contains("invalid") || body.contains("failed") || body.contains("error"))
            .unwrap_or(false);

        if is_login_request && has_failure_indicators {
            session.failed_login_attempts += 1;

            // Detect brute force if too many failed attempts
            if session.failed_login_attempts >= self.config.brute_force_threshold {
                return Ok(Some(DetectedThreat {
                    id: uuid::Uuid::new_v4().to_string(),
                    threat_type: ThreatType::BruteForce,
                    level: ThreatLevel::High,
                    confidence: 0.9,
                    source_ip: client_ip,
                    user_agent: Some(request.user_agent.clone()),
                    description: format!("Brute force attack detected: {} failed login attempts", session.failed_login_attempts),
                    evidence: vec![
                        format!("Failed login attempts: {}", session.failed_login_attempts),
                        format!("Time window: {} minutes", (session.last_seen - session.first_seen).num_minutes()),
                    ],
                    indicators: HashMap::from([
                        ("failed_attempts".to_string(), session.failed_login_attempts.to_string()),
                        ("request_count".to_string(), session.request_count.to_string()),
                    ]),
                    detected_at: Utc::now(),
                    expires_at: Some(Utc::now() + chrono::Duration::hours(1)),
                }));
            }
        }

        Ok(None)
    }

    async fn check_rate_anomaly(&self, request: &HttpRequest) -> SecurityResult<Option<DetectedThreat>> {
        let ip_behavior = self.ip_behavior.read().await;
        let client_ip = request.client_ip.to_string();

        if let Some(behavior) = ip_behavior.get(&client_ip) {
            let current_time = Utc::now();
            let time_window = chrono::Duration::minutes(5);

            // Count recent requests in the time window
            let recent_requests = behavior.request_timestamps.iter()
                .filter(|&&timestamp| current_time - timestamp < time_window)
                .count();

            // Check if request rate exceeds threshold
            let requests_per_minute = (recent_requests as f64 / 5.0) * 60.0; // Convert to requests per minute

            if requests_per_minute > self.config.rate_anomaly_threshold {
                return Ok(Some(DetectedThreat {
                    id: uuid::Uuid::new_v4().to_string(),
                    threat_type: ThreatType::AnomalousTraffic,
                    level: ThreatLevel::Medium,
                    confidence: 0.8,
                    source_ip: client_ip,
                    user_agent: Some(request.user_agent.clone()),
                    description: format!("Rate anomaly detected: {:.1} requests/min (threshold: {})",
                                       requests_per_minute, self.config.rate_anomaly_threshold),
                    evidence: vec![
                        format!("Requests in last 5 minutes: {}", recent_requests),
                        format!("Rate: {:.1} req/min", requests_per_minute),
                    ],
                    indicators: HashMap::from([
                        ("requests_per_minute".to_string(), requests_per_minute.to_string()),
                        ("recent_requests".to_string(), recent_requests.to_string()),
                    ]),
                    detected_at: Utc::now(),
                    expires_at: Some(Utc::now() + chrono::Duration::minutes(30)),
                }));
            }
        }

        Ok(None)
    }

    async fn check_user_agent_anomaly(&self, request: &HttpRequest) -> SecurityResult<Option<DetectedThreat>> {
        let user_agent = &request.user_agent;

        // Check for suspicious user agent patterns
        let suspicious_patterns = vec![
            "bot", "crawler", "spider", "scraper", "scanner", "hack", "exploit",
            "sqlmap", "nikto", "nmap", "masscan", "zap", "burp", "metasploit"
        ];

        let user_agent_lower = user_agent.to_lowercase();
        for pattern in suspicious_patterns {
            if user_agent_lower.contains(pattern) {
                return Ok(Some(DetectedThreat {
                    id: uuid::Uuid::new_v4().to_string(),
                    threat_type: ThreatType::SuspiciousUserAgent,
                    level: ThreatLevel::Medium,
                    confidence: 0.75,
                    source_ip: request.client_ip.to_string(),
                    user_agent: Some(user_agent.clone()),
                    description: format!("Suspicious user agent detected: contains '{}'", pattern),
                    evidence: vec![
                        format!("User agent: {}", user_agent),
                        format!("Suspicious pattern: {}", pattern),
                    ],
                    indicators: HashMap::from([
                        ("user_agent".to_string(), user_agent.clone()),
                        ("suspicious_pattern".to_string(), pattern.to_string()),
                    ]),
                    detected_at: Utc::now(),
                    expires_at: Some(Utc::now() + chrono::Duration::hours(2)),
                }));
            }
        }

        // Check for empty or very short user agents
        if user_agent.len() < 10 {
            return Ok(Some(DetectedThreat {
                id: uuid::Uuid::new_v4().to_string(),
                threat_type: ThreatType::SuspiciousUserAgent,
                level: ThreatLevel::Low,
                confidence: 0.6,
                source_ip: request.client_ip.to_string(),
                user_agent: Some(user_agent.clone()),
                description: "Suspicious user agent: too short or empty".to_string(),
                evidence: vec![
                    format!("User agent: '{}'", user_agent),
                    format!("Length: {} characters", user_agent.len()),
                ],
                indicators: HashMap::from([
                    ("user_agent".to_string(), user_agent.clone()),
                    ("length".to_string(), user_agent.len().to_string()),
                ]),
                detected_at: Utc::now(),
                expires_at: Some(Utc::now() + chrono::Duration::hours(1)),
            }));
        }

        Ok(None)
    }

    pub async fn update_baselines(&self) -> SecurityResult<()> {
        let ip_behavior = self.ip_behavior.read().await;
        let mut baseline_metrics = self.baseline_metrics.write().await;

        // Calculate new baseline metrics from current IP behavior data
        let total_ips = ip_behavior.len();
        if total_ips == 0 {
            return Ok(());
        }

        let mut total_requests = 0;
        let mut total_unique_paths = 0;
        let mut total_failed_requests = 0;

        for behavior in ip_behavior.values() {
            total_requests += behavior.request_count;
            total_unique_paths += behavior.unique_paths.len();
            total_failed_requests += behavior.failed_requests;
        }

        // Update baseline with exponential moving average
        let alpha = 0.1; // Smoothing factor
        let avg_requests_per_ip = total_requests as f64 / total_ips as f64;
        let avg_unique_paths_per_ip = total_unique_paths as f64 / total_ips as f64;
        let avg_failed_requests_per_ip = total_failed_requests as f64 / total_ips as f64;

        baseline_metrics.avg_requests_per_ip = baseline_metrics.avg_requests_per_ip * (1.0 - alpha) + avg_requests_per_ip * alpha;
        baseline_metrics.avg_unique_paths_per_ip = baseline_metrics.avg_unique_paths_per_ip * (1.0 - alpha) + avg_unique_paths_per_ip * alpha;
        baseline_metrics.avg_failed_requests_per_ip = baseline_metrics.avg_failed_requests_per_ip * (1.0 - alpha) + avg_failed_requests_per_ip * alpha;
        baseline_metrics.last_updated = Utc::now();

        info!("Updated behavioral baselines - Avg requests/IP: {:.2}, Avg paths/IP: {:.2}, Avg failures/IP: {:.2}",
              baseline_metrics.avg_requests_per_ip, baseline_metrics.avg_unique_paths_per_ip, baseline_metrics.avg_failed_requests_per_ip);

        Ok(())
    }

    pub async fn get_session_count(&self) -> usize {
        self.user_sessions.read().await.len()
    }

    pub async fn get_ip_count(&self) -> usize {
        self.ip_behavior.read().await.len()
    }
}

impl AnomalyDetector {
    pub fn new(config: AnomalyDetectionConfig) -> Self {
        Self {
            baseline_metrics: Arc::new(RwLock::new(BaselineMetrics::default())),
            current_metrics: Arc::new(RwLock::new(CurrentMetrics::default())),
            config,
        }
    }

    pub async fn analyze(&self, request: &HttpRequest) -> SecurityResult<Option<DetectedThreat>> {
        let current_metrics = self.current_metrics.read().await;
        let baseline_metrics = self.baseline_metrics.read().await;

        // Analyze request rate anomalies
        let current_rate = current_metrics.request_rate;
        let baseline_rate = baseline_metrics.avg_request_rate;

        if current_rate > baseline_rate * self.config.rate_threshold {
            return Ok(Some(DetectedThreat {
                id: uuid::Uuid::new_v4().to_string(),
                threat_type: ThreatType::AnomalousTraffic,
                level: ThreatLevel::High,
                confidence: 0.85,
                source_ip: request.client_ip.clone(),
                user_agent: Some(request.user_agent.clone()),
                description: format!("Anomalous request rate detected: {} req/min vs baseline {}", current_rate, baseline_rate),
                evidence: vec![format!("Current rate: {}, Baseline: {}, Threshold: {}", current_rate, baseline_rate, self.config.rate_threshold)],
                indicators: HashMap::from([
                    ("current_rate".to_string(), current_rate.to_string()),
                    ("baseline_rate".to_string(), baseline_rate.to_string()),
                ]),
                detected_at: Utc::now(),
                expires_at: Some(Utc::now() + chrono::Duration::hours(1)),
            }));
        }

        // Analyze response time anomalies
        let current_response_time = current_metrics.avg_response_time;
        let baseline_response_time = baseline_metrics.avg_response_time;

        if current_response_time > baseline_response_time * self.config.response_time_threshold {
            return Ok(Some(DetectedThreat {
                id: uuid::Uuid::new_v4().to_string(),
                threat_type: ThreatType::PerformanceAnomaly,
                level: ThreatLevel::Medium,
                confidence: 0.75,
                source_ip: request.client_ip.clone(),
                user_agent: Some(request.user_agent.clone()),
                description: format!("Anomalous response time detected: {}ms vs baseline {}ms", current_response_time, baseline_response_time),
                evidence: vec![format!("Current response time: {}ms, Baseline: {}ms", current_response_time, baseline_response_time)],
                indicators: HashMap::from([
                    ("current_response_time".to_string(), current_response_time.to_string()),
                    ("baseline_response_time".to_string(), baseline_response_time.to_string()),
                ]),
                detected_at: Utc::now(),
                expires_at: Some(Utc::now() + chrono::Duration::hours(1)),
            }));
        }

        Ok(None)
    }

    pub async fn update_baselines(&self) -> SecurityResult<()> {
        let current_metrics = self.current_metrics.read().await;
        let mut baseline_metrics = self.baseline_metrics.write().await;

        // Update baseline metrics with exponential moving average
        let alpha = 0.1; // Smoothing factor

        baseline_metrics.avg_request_rate = baseline_metrics.avg_request_rate * (1.0 - alpha) + current_metrics.request_rate * alpha;
        baseline_metrics.avg_response_time = baseline_metrics.avg_response_time * (1.0 - alpha) + current_metrics.avg_response_time * alpha;
        baseline_metrics.avg_error_rate = baseline_metrics.avg_error_rate * (1.0 - alpha) + current_metrics.error_rate * alpha;
        baseline_metrics.last_updated = Utc::now();

        info!("Updated anomaly detection baselines - Request rate: {:.2}, Response time: {:.2}ms, Error rate: {:.2}%",
              baseline_metrics.avg_request_rate, baseline_metrics.avg_response_time, baseline_metrics.avg_error_rate * 100.0);

        Ok(())
    }

    pub async fn get_baseline_age(&self) -> u64 {
        let baseline = self.baseline_metrics.read().await;
        (Utc::now() - baseline.last_updated).num_hours() as u64
    }
}

impl ThreatIntelligence {
    pub fn new(config: ThreatIntelligenceConfig) -> Self {
        Self {
            malicious_ips: Arc::new(RwLock::new(std::collections::HashSet::new())),
            malicious_user_agents: Arc::new(RwLock::new(std::collections::HashSet::new())),
            attack_signatures: Arc::new(RwLock::new(Vec::new())),
            config,
        }
    }

    pub async fn analyze(&self, request: &HttpRequest) -> SecurityResult<Option<DetectedThreat>> {
        // Check malicious IPs
        {
            let malicious_ips = self.malicious_ips.read().await;
            if malicious_ips.contains(&request.client_ip) {
                return Ok(Some(DetectedThreat {
                    id: uuid::Uuid::new_v4().to_string(),
                    threat_type: ThreatType::ThreatIntelligenceMatch,
                    level: ThreatLevel::High,
                    confidence: 0.95,
                    source_ip: request.client_ip.clone(),
                    user_agent: Some(request.user_agent.clone()),
                    description: "IP address found in threat intelligence feed".to_string(),
                    evidence: vec!["Malicious IP database match".to_string()],
                    indicators: HashMap::new(),
                    detected_at: Utc::now(),
                    expires_at: None,
                }));
            }
        }

        // Check malicious user agents
        {
            let malicious_user_agents = self.malicious_user_agents.read().await;
            if malicious_user_agents.contains(&request.user_agent) {
                return Ok(Some(DetectedThreat {
                    id: uuid::Uuid::new_v4().to_string(),
                    threat_type: ThreatType::SuspiciousUserAgent,
                    level: ThreatLevel::Medium,
                    confidence: 0.8,
                    source_ip: request.client_ip.clone(),
                    user_agent: Some(request.user_agent.clone()),
                    description: "Suspicious user agent detected".to_string(),
                    evidence: vec!["Malicious user agent database match".to_string()],
                    indicators: HashMap::new(),
                    detected_at: Utc::now(),
                    expires_at: None,
                }));
            }
        }

        Ok(None)
    }

    pub async fn update_intelligence(&self) -> SecurityResult<()> {
        info!("Updating threat intelligence feeds");

        // Update malicious IP addresses from threat intelligence feeds
        let mut malicious_ips = self.malicious_ips.write().await;

        // Simulate fetching from threat intelligence APIs
        let new_malicious_ips = vec![
            "192.168.1.100".to_string(),
            "10.0.0.50".to_string(),
            "172.16.0.25".to_string(),
        ];

        for ip in new_malicious_ips {
            malicious_ips.insert(ip);
        }

        // Update malicious user agents
        let mut malicious_user_agents = self.malicious_user_agents.write().await;
        let new_malicious_agents = vec![
            "BadBot/1.0".to_string(),
            "MaliciousScanner".to_string(),
            "AttackTool/2.0".to_string(),
        ];

        for agent in new_malicious_agents {
            malicious_user_agents.insert(agent);
        }

        info!("Threat intelligence updated - {} malicious IPs, {} malicious user agents",
              malicious_ips.len(), malicious_user_agents.len());

        Ok(())
    }

    pub async fn get_signature_count(&self) -> usize {
        self.attack_signatures.read().await.len()
    }

    pub async fn get_malicious_ip_count(&self) -> usize {
        self.malicious_ips.read().await.len()
    }
}

/// Threat detection statistics
#[derive(Debug, Serialize)]
pub struct ThreatDetectionStatistics {
    pub behavioral_sessions_tracked: usize,
    pub behavioral_ips_tracked: usize,
    pub anomaly_baseline_age_hours: u64,
    pub threat_intelligence_signatures: usize,
    pub threat_intelligence_malicious_ips: usize,
}

// Default implementations
impl Default for ThreatDetectionConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            behavioral_analysis_enabled: true,
            anomaly_detection_enabled: true,
            threat_intelligence_enabled: true,
            detection_threshold: 0.7,
            learning_period_hours: 24,
            max_tracking_entries: 10000,
        }
    }
}

impl Default for BehavioralAnalysisConfig {
    fn default() -> Self {
        Self {
            max_failed_auth_attempts: 5,
            suspicious_request_rate: 100,
            max_user_agents_per_ip: 10,
            geolocation_change_threshold: 1000.0,
            session_timeout_minutes: 30,
            risk_score_threshold: 0.8,
        }
    }
}

impl Default for AnomalyDetectionConfig {
    fn default() -> Self {
        Self {
            deviation_threshold: 2.0,
            minimum_baseline_samples: 1000,
            baseline_update_interval_hours: 24,
            anomaly_persistence_minutes: 60,
        }
    }
}

impl Default for ThreatIntelligenceConfig {
    fn default() -> Self {
        Self {
            update_interval_hours: 6,
            signature_expiry_days: 30,
            external_feeds_enabled: true,
            custom_signatures_enabled: true,
        }
    }
}

impl Default for BaselineMetrics {
    fn default() -> Self {
        Self {
            avg_requests_per_minute: 0.0,
            avg_response_time: 0.0,
            common_user_agents: HashMap::new(),
            common_paths: HashMap::new(),
            geographic_distribution: HashMap::new(),
            time_patterns: HashMap::new(),
            last_updated: Utc::now(),
        }
    }
}

impl Default for CurrentMetrics {
    fn default() -> Self {
        Self {
            requests_per_minute: 0.0,
            response_time: 0.0,
            user_agent_distribution: HashMap::new(),
            path_distribution: HashMap::new(),
            geographic_distribution: HashMap::new(),
            time_distribution: HashMap::new(),
            last_updated: Utc::now(),
        }
    }
}
