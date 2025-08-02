//! Session management for user authentication

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

use regulateai_config::SessionConfig;
use regulateai_errors::RegulateAIError;

/// User session data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    /// Session ID
    pub id: Uuid,
    
    /// User ID
    pub user_id: Uuid,
    
    /// Session creation timestamp
    pub created_at: DateTime<Utc>,
    
    /// Last activity timestamp
    pub last_activity: DateTime<Utc>,
    
    /// Session expiration timestamp
    pub expires_at: DateTime<Utc>,
    
    /// IP address of the session
    pub ip_address: Option<String>,
    
    /// User agent string
    pub user_agent: Option<String>,
    
    /// Session metadata
    pub metadata: HashMap<String, serde_json::Value>,
    
    /// Whether the session is active
    pub is_active: bool,
    
    /// Organization ID (if applicable)
    pub organization_id: Option<Uuid>,
    
    /// Session rotation count
    pub rotation_count: u32,
}

impl Session {
    /// Create a new session
    pub fn new(
        user_id: Uuid,
        timeout_seconds: u64,
        ip_address: Option<String>,
        user_agent: Option<String>,
        organization_id: Option<Uuid>,
    ) -> Self {
        let now = Utc::now();
        let expires_at = now + Duration::seconds(timeout_seconds as i64);

        Self {
            id: Uuid::new_v4(),
            user_id,
            created_at: now,
            last_activity: now,
            expires_at,
            ip_address,
            user_agent,
            metadata: HashMap::new(),
            is_active: true,
            organization_id,
            rotation_count: 0,
        }
    }

    /// Check if the session is expired
    pub fn is_expired(&self) -> bool {
        Utc::now() > self.expires_at
    }

    /// Check if the session is valid (active and not expired)
    pub fn is_valid(&self) -> bool {
        self.is_active && !self.is_expired()
    }

    /// Update the last activity timestamp and extend expiration
    pub fn update_activity(&mut self, timeout_seconds: u64) {
        let now = Utc::now();
        self.last_activity = now;
        self.expires_at = now + Duration::seconds(timeout_seconds as i64);
    }

    /// Invalidate the session
    pub fn invalidate(&mut self) {
        self.is_active = false;
    }

    /// Rotate the session ID
    pub fn rotate_id(&mut self) {
        self.id = Uuid::new_v4();
        self.rotation_count += 1;
        self.last_activity = Utc::now();
    }

    /// Add metadata to the session
    pub fn add_metadata(&mut self, key: String, value: serde_json::Value) {
        self.metadata.insert(key, value);
    }

    /// Get metadata from the session
    pub fn get_metadata(&self, key: &str) -> Option<&serde_json::Value> {
        self.metadata.get(key)
    }

    /// Check if session needs rotation based on time
    pub fn needs_rotation(&self, rotation_interval_seconds: u64) -> bool {
        let rotation_threshold = self.last_activity + Duration::seconds(rotation_interval_seconds as i64);
        Utc::now() > rotation_threshold
    }

    /// Get session duration in seconds
    pub fn duration_seconds(&self) -> i64 {
        (self.last_activity - self.created_at).num_seconds()
    }

    /// Get time until expiration in seconds
    pub fn time_until_expiration_seconds(&self) -> i64 {
        (self.expires_at - Utc::now()).num_seconds().max(0)
    }
}

/// Session manager for handling user sessions
pub struct SessionManager {
    sessions: HashMap<Uuid, Session>,
    user_sessions: HashMap<Uuid, Vec<Uuid>>, // User ID -> Session IDs
    config: SessionConfig,
}

impl SessionManager {
    /// Create a new session manager
    pub fn new(config: SessionConfig) -> Self {
        Self {
            sessions: HashMap::new(),
            user_sessions: HashMap::new(),
            config,
        }
    }

    /// Create a new session for a user
    pub fn create_session(
        &mut self,
        user_id: Uuid,
        ip_address: Option<String>,
        user_agent: Option<String>,
        organization_id: Option<Uuid>,
    ) -> Result<Session, RegulateAIError> {
        let session = Session::new(
            user_id,
            self.config.timeout,
            ip_address,
            user_agent,
            organization_id,
        );

        let session_id = session.id;
        
        // Store the session
        self.sessions.insert(session_id, session.clone());
        
        // Track user sessions
        self.user_sessions
            .entry(user_id)
            .or_insert_with(Vec::new)
            .push(session_id);

        Ok(session)
    }

    /// Get a session by ID
    pub fn get_session(&self, session_id: &Uuid) -> Option<&Session> {
        self.sessions.get(session_id)
    }

    /// Get a mutable session by ID
    pub fn get_session_mut(&mut self, session_id: &Uuid) -> Option<&mut Session> {
        self.sessions.get_mut(session_id)
    }

    /// Validate and update a session
    pub fn validate_session(&mut self, session_id: &Uuid) -> Result<&Session, RegulateAIError> {
        let session = self.sessions.get_mut(session_id)
            .ok_or_else(|| RegulateAIError::Authentication {
                message: "Session not found".to_string(),
                code: "SESSION_NOT_FOUND".to_string(),
            })?;

        if !session.is_valid() {
            return Err(RegulateAIError::Authentication {
                message: "Session is invalid or expired".to_string(),
                code: "SESSION_INVALID".to_string(),
            });
        }

        // Update activity
        session.update_activity(self.config.timeout);

        // Check if rotation is needed
        if self.config.enable_rotation && session.needs_rotation(self.config.rotation_interval) {
            session.rotate_id();
        }

        Ok(session)
    }

    /// Invalidate a session
    pub fn invalidate_session(&mut self, session_id: &Uuid) -> Result<(), RegulateAIError> {
        if let Some(session) = self.sessions.get_mut(session_id) {
            session.invalidate();
            
            // Remove from user sessions tracking
            if let Some(user_sessions) = self.user_sessions.get_mut(&session.user_id) {
                user_sessions.retain(|id| id != session_id);
                if user_sessions.is_empty() {
                    self.user_sessions.remove(&session.user_id);
                }
            }
            
            // Remove the session
            self.sessions.remove(session_id);
        }
        
        Ok(())
    }

    /// Invalidate all sessions for a user
    pub fn invalidate_user_sessions(&mut self, user_id: &Uuid) -> Result<(), RegulateAIError> {
        if let Some(session_ids) = self.user_sessions.remove(user_id) {
            for session_id in session_ids {
                if let Some(session) = self.sessions.get_mut(&session_id) {
                    session.invalidate();
                }
                self.sessions.remove(&session_id);
            }
        }
        
        Ok(())
    }

    /// Get all active sessions for a user
    pub fn get_user_sessions(&self, user_id: &Uuid) -> Vec<&Session> {
        if let Some(session_ids) = self.user_sessions.get(user_id) {
            session_ids
                .iter()
                .filter_map(|id| self.sessions.get(id))
                .filter(|session| session.is_valid())
                .collect()
        } else {
            Vec::new()
        }
    }

    /// Clean up expired sessions
    pub fn cleanup_expired_sessions(&mut self) -> usize {
        let mut expired_sessions = Vec::new();
        
        for (session_id, session) in &self.sessions {
            if !session.is_valid() {
                expired_sessions.push(*session_id);
            }
        }
        
        let count = expired_sessions.len();
        
        for session_id in expired_sessions {
            if let Some(session) = self.sessions.remove(&session_id) {
                // Remove from user sessions tracking
                if let Some(user_sessions) = self.user_sessions.get_mut(&session.user_id) {
                    user_sessions.retain(|id| *id != session_id);
                    if user_sessions.is_empty() {
                        self.user_sessions.remove(&session.user_id);
                    }
                }
            }
        }
        
        count
    }

    /// Get session statistics
    pub fn get_statistics(&self) -> SessionStatistics {
        let total_sessions = self.sessions.len();
        let active_sessions = self.sessions.values().filter(|s| s.is_valid()).count();
        let expired_sessions = total_sessions - active_sessions;
        let unique_users = self.user_sessions.len();
        
        let average_duration = if active_sessions > 0 {
            let total_duration: i64 = self.sessions
                .values()
                .filter(|s| s.is_valid())
                .map(|s| s.duration_seconds())
                .sum();
            total_duration / active_sessions as i64
        } else {
            0
        };

        SessionStatistics {
            total_sessions,
            active_sessions,
            expired_sessions,
            unique_users,
            average_duration_seconds: average_duration,
        }
    }

    /// Extend session timeout
    pub fn extend_session(&mut self, session_id: &Uuid, additional_seconds: u64) -> Result<(), RegulateAIError> {
        let session = self.sessions.get_mut(session_id)
            .ok_or_else(|| RegulateAIError::Authentication {
                message: "Session not found".to_string(),
                code: "SESSION_NOT_FOUND".to_string(),
            })?;

        if !session.is_valid() {
            return Err(RegulateAIError::Authentication {
                message: "Cannot extend invalid session".to_string(),
                code: "SESSION_INVALID".to_string(),
            });
        }

        session.expires_at = session.expires_at + Duration::seconds(additional_seconds as i64);
        Ok(())
    }
}

/// Session statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionStatistics {
    pub total_sessions: usize,
    pub active_sessions: usize,
    pub expired_sessions: usize,
    pub unique_users: usize,
    pub average_duration_seconds: i64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use regulateai_config::SessionConfig;

    fn create_test_config() -> SessionConfig {
        SessionConfig {
            timeout: 1800, // 30 minutes
            cookie_name: "test_session".to_string(),
            cookie_domain: None,
            cookie_path: "/".to_string(),
            cookie_secure: false,
            cookie_http_only: true,
            cookie_same_site: regulateai_config::SameSitePolicy::Lax,
            enable_rotation: true,
            rotation_interval: 300, // 5 minutes
        }
    }

    #[test]
    fn test_session_creation() {
        let user_id = Uuid::new_v4();
        let session = Session::new(
            user_id,
            1800,
            Some("127.0.0.1".to_string()),
            Some("Test Agent".to_string()),
            None,
        );

        assert_eq!(session.user_id, user_id);
        assert!(session.is_valid());
        assert!(!session.is_expired());
    }

    #[test]
    fn test_session_expiration() {
        let user_id = Uuid::new_v4();
        let mut session = Session::new(user_id, 0, None, None, None); // Expires immediately
        
        // Manually set expiration to past
        session.expires_at = Utc::now() - Duration::seconds(1);
        
        assert!(session.is_expired());
        assert!(!session.is_valid());
    }

    #[test]
    fn test_session_manager() {
        let config = create_test_config();
        let mut manager = SessionManager::new(config);
        let user_id = Uuid::new_v4();

        // Create session
        let session = manager.create_session(
            user_id,
            Some("127.0.0.1".to_string()),
            Some("Test Agent".to_string()),
            None,
        ).unwrap();

        let session_id = session.id;

        // Validate session
        let validated_session = manager.validate_session(&session_id).unwrap();
        assert_eq!(validated_session.user_id, user_id);

        // Get user sessions
        let user_sessions = manager.get_user_sessions(&user_id);
        assert_eq!(user_sessions.len(), 1);

        // Invalidate session
        manager.invalidate_session(&session_id).unwrap();
        assert!(manager.get_session(&session_id).is_none());
    }

    #[test]
    fn test_session_rotation() {
        let user_id = Uuid::new_v4();
        let mut session = Session::new(user_id, 1800, None, None, None);
        let original_id = session.id;

        session.rotate_id();
        
        assert_ne!(session.id, original_id);
        assert_eq!(session.rotation_count, 1);
    }

    #[test]
    fn test_session_metadata() {
        let user_id = Uuid::new_v4();
        let mut session = Session::new(user_id, 1800, None, None, None);

        session.add_metadata("test_key".to_string(), serde_json::Value::String("test_value".to_string()));
        
        let value = session.get_metadata("test_key");
        assert!(value.is_some());
        assert_eq!(value.unwrap(), &serde_json::Value::String("test_value".to_string()));
    }

    #[test]
    fn test_cleanup_expired_sessions() {
        let config = create_test_config();
        let mut manager = SessionManager::new(config);
        let user_id = Uuid::new_v4();

        // Create a session
        let session = manager.create_session(user_id, None, None, None).unwrap();
        let session_id = session.id;

        // Manually expire the session
        if let Some(session) = manager.sessions.get_mut(&session_id) {
            session.expires_at = Utc::now() - Duration::seconds(1);
        }

        // Cleanup should remove the expired session
        let cleaned_count = manager.cleanup_expired_sessions();
        assert_eq!(cleaned_count, 1);
        assert!(manager.get_session(&session_id).is_none());
    }
}
