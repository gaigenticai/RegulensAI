//! Security configuration management

use serde::{Deserialize, Serialize};
use std::time::Duration;
use validator::Validate;

/// Security configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct SecurityConfig {
    /// JWT configuration
    pub jwt: JwtConfig,
    
    /// CORS configuration
    pub cors: CorsConfig,
    
    /// Rate limiting configuration
    pub rate_limiting: RateLimitConfig,
    
    /// Password policy configuration
    pub password_policy: PasswordPolicyConfig,
    
    /// Session configuration
    pub session: SessionConfig,
    
    /// Encryption configuration
    pub encryption: EncryptionConfig,
}

/// JWT (JSON Web Token) configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct JwtConfig {
    /// JWT secret key for signing tokens
    #[validate(length(min = 32))]
    pub secret: String,
    
    /// Token expiration time in seconds
    #[validate(range(min = 300, max = 86400))] // 5 minutes to 24 hours
    pub expiration: u64,
    
    /// Refresh token expiration time in seconds
    #[validate(range(min = 3600, max = 2592000))] // 1 hour to 30 days
    pub refresh_expiration: u64,
    
    /// JWT issuer
    #[validate(length(min = 1))]
    pub issuer: String,
    
    /// JWT audience
    #[validate(length(min = 1))]
    pub audience: String,
    
    /// Algorithm for signing tokens
    pub algorithm: JwtAlgorithm,
    
    /// Enable token refresh
    pub enable_refresh: bool,
    
    /// Token leeway in seconds (for clock skew)
    pub leeway: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum JwtAlgorithm {
    HS256,
    HS384,
    HS512,
    RS256,
    RS384,
    RS512,
}

/// CORS (Cross-Origin Resource Sharing) configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct CorsConfig {
    /// Allowed origins
    pub allowed_origins: Vec<String>,
    
    /// Allowed methods
    pub allowed_methods: Vec<String>,
    
    /// Allowed headers
    pub allowed_headers: Vec<String>,
    
    /// Exposed headers
    pub exposed_headers: Vec<String>,
    
    /// Allow credentials
    pub allow_credentials: bool,
    
    /// Max age for preflight requests in seconds
    #[validate(range(min = 0, max = 86400))]
    pub max_age: u64,
}

/// Rate limiting configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct RateLimitConfig {
    /// Enable rate limiting
    pub enabled: bool,
    
    /// Requests per minute per IP
    #[validate(range(min = 1, max = 10000))]
    pub requests_per_minute: u32,
    
    /// Burst size (number of requests allowed in a burst)
    #[validate(range(min = 1, max = 1000))]
    pub burst_size: u32,
    
    /// Rate limit window in seconds
    #[validate(range(min = 1, max = 3600))]
    pub window_seconds: u32,
    
    /// Whitelist of IP addresses/ranges exempt from rate limiting
    pub whitelist: Vec<String>,
    
    /// Custom rate limits for specific endpoints
    pub endpoint_limits: Vec<EndpointRateLimit>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct EndpointRateLimit {
    /// Endpoint pattern (e.g., "/api/v1/users/*")
    #[validate(length(min = 1))]
    pub pattern: String,
    
    /// Requests per minute for this endpoint
    #[validate(range(min = 1, max = 10000))]
    pub requests_per_minute: u32,
    
    /// HTTP methods this limit applies to
    pub methods: Vec<String>,
}

/// Password policy configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct PasswordPolicyConfig {
    /// Minimum password length
    #[validate(range(min = 8, max = 128))]
    pub min_length: usize,
    
    /// Maximum password length
    #[validate(range(min = 8, max = 256))]
    pub max_length: usize,
    
    /// Require uppercase letters
    pub require_uppercase: bool,
    
    /// Require lowercase letters
    pub require_lowercase: bool,
    
    /// Require digits
    pub require_digits: bool,
    
    /// Require special characters
    pub require_special_chars: bool,
    
    /// Special characters to allow
    pub allowed_special_chars: String,
    
    /// Maximum login attempts before lockout
    #[validate(range(min = 3, max = 10))]
    pub max_login_attempts: u32,
    
    /// Account lockout duration in seconds
    #[validate(range(min = 300, max = 86400))] // 5 minutes to 24 hours
    pub lockout_duration: u64,
    
    /// Password expiration in days (0 = never expires)
    pub password_expiry_days: u32,
    
    /// Number of previous passwords to remember
    #[validate(range(min = 0, max = 24))]
    pub password_history_count: u32,
}

/// Session configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct SessionConfig {
    /// Session timeout in seconds
    #[validate(range(min = 300, max = 86400))] // 5 minutes to 24 hours
    pub timeout: u64,
    
    /// Session cookie name
    #[validate(length(min = 1))]
    pub cookie_name: String,
    
    /// Session cookie domain
    pub cookie_domain: Option<String>,
    
    /// Session cookie path
    #[validate(length(min = 1))]
    pub cookie_path: String,
    
    /// Session cookie secure flag
    pub cookie_secure: bool,
    
    /// Session cookie HTTP-only flag
    pub cookie_http_only: bool,
    
    /// Session cookie SameSite attribute
    pub cookie_same_site: SameSitePolicy,
    
    /// Enable session rotation
    pub enable_rotation: bool,
    
    /// Session rotation interval in seconds
    pub rotation_interval: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub enum SameSitePolicy {
    Strict,
    Lax,
    None,
}

/// Encryption configuration
#[derive(Debug, Clone, Serialize, Deserialize, Validate)]
pub struct EncryptionConfig {
    /// Application encryption key
    #[validate(length(min = 32))]
    pub app_key: String,
    
    /// Encryption algorithm
    pub algorithm: EncryptionAlgorithm,
    
    /// Key derivation function
    pub kdf: KeyDerivationFunction,
    
    /// Number of iterations for key derivation
    #[validate(range(min = 10000, max = 1000000))]
    pub kdf_iterations: u32,
    
    /// Salt length for key derivation
    #[validate(range(min = 16, max = 64))]
    pub salt_length: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum EncryptionAlgorithm {
    AES256GCM,
    AES256CBC,
    ChaCha20Poly1305,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum KeyDerivationFunction {
    PBKDF2,
    Argon2,
    Scrypt,
}

impl SecurityConfig {
    /// Get JWT expiration as Duration
    pub fn jwt_expiration_duration(&self) -> Duration {
        Duration::from_secs(self.jwt.expiration)
    }

    /// Get JWT refresh expiration as Duration
    pub fn jwt_refresh_expiration_duration(&self) -> Duration {
        Duration::from_secs(self.jwt.refresh_expiration)
    }

    /// Get session timeout as Duration
    pub fn session_timeout_duration(&self) -> Duration {
        Duration::from_secs(self.session.timeout)
    }

    /// Get lockout duration as Duration
    pub fn lockout_duration(&self) -> Duration {
        Duration::from_secs(self.password_policy.lockout_duration)
    }

    /// Check if rate limiting is enabled
    pub fn is_rate_limiting_enabled(&self) -> bool {
        self.rate_limiting.enabled
    }

    /// Get rate limit window as Duration
    pub fn rate_limit_window_duration(&self) -> Duration {
        Duration::from_secs(self.rate_limiting.window_seconds as u64)
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            jwt: JwtConfig {
                secret: "your-jwt-secret-key-must-be-at-least-32-characters-long".to_string(),
                expiration: 3600, // 1 hour
                refresh_expiration: 86400, // 24 hours
                issuer: "regulateai".to_string(),
                audience: "regulateai-services".to_string(),
                algorithm: JwtAlgorithm::HS256,
                enable_refresh: true,
                leeway: 60, // 1 minute
            },
            cors: CorsConfig {
                allowed_origins: vec!["http://localhost:3000".to_string(), "http://localhost:8080".to_string()],
                allowed_methods: vec!["GET".to_string(), "POST".to_string(), "PUT".to_string(), "DELETE".to_string(), "OPTIONS".to_string()],
                allowed_headers: vec!["Content-Type".to_string(), "Authorization".to_string(), "X-Requested-With".to_string()],
                exposed_headers: vec!["X-Request-ID".to_string(), "X-Correlation-ID".to_string()],
                allow_credentials: true,
                max_age: 3600,
            },
            rate_limiting: RateLimitConfig {
                enabled: true,
                requests_per_minute: 100,
                burst_size: 10,
                window_seconds: 60,
                whitelist: vec!["127.0.0.1".to_string(), "::1".to_string()],
                endpoint_limits: vec![],
            },
            password_policy: PasswordPolicyConfig {
                min_length: 8,
                max_length: 128,
                require_uppercase: true,
                require_lowercase: true,
                require_digits: true,
                require_special_chars: true,
                allowed_special_chars: "!@#$%^&*()_+-=[]{}|;:,.<>?".to_string(),
                max_login_attempts: 5,
                lockout_duration: 900, // 15 minutes
                password_expiry_days: 90,
                password_history_count: 5,
            },
            session: SessionConfig {
                timeout: 1800, // 30 minutes
                cookie_name: "regulateai_session".to_string(),
                cookie_domain: None,
                cookie_path: "/".to_string(),
                cookie_secure: true,
                cookie_http_only: true,
                cookie_same_site: SameSitePolicy::Lax,
                enable_rotation: true,
                rotation_interval: 300, // 5 minutes
            },
            encryption: EncryptionConfig {
                app_key: "your-application-encryption-key-must-be-at-least-32-characters-long".to_string(),
                algorithm: EncryptionAlgorithm::AES256GCM,
                kdf: KeyDerivationFunction::Argon2,
                kdf_iterations: 100000,
                salt_length: 32,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_security_config() {
        let config = SecurityConfig::default();
        assert_eq!(config.jwt.expiration, 3600);
        assert_eq!(config.jwt.issuer, "regulateai");
        assert!(config.rate_limiting.enabled);
        assert_eq!(config.password_policy.min_length, 8);
    }

    #[test]
    fn test_duration_conversions() {
        let config = SecurityConfig::default();
        
        assert_eq!(config.jwt_expiration_duration(), Duration::from_secs(3600));
        assert_eq!(config.jwt_refresh_expiration_duration(), Duration::from_secs(86400));
        assert_eq!(config.session_timeout_duration(), Duration::from_secs(1800));
        assert_eq!(config.lockout_duration(), Duration::from_secs(900));
    }

    #[test]
    fn test_rate_limiting_checks() {
        let config = SecurityConfig::default();
        assert!(config.is_rate_limiting_enabled());
        assert_eq!(config.rate_limit_window_duration(), Duration::from_secs(60));
    }
}
