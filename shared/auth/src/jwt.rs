//! JWT token management and validation

use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use uuid::Uuid;

use regulateai_config::SecurityConfig;
use regulateai_errors::RegulateAIError;

/// JWT claims structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    /// Subject (user ID)
    pub sub: String,
    
    /// Issued at timestamp
    pub iat: i64,
    
    /// Expiration timestamp
    pub exp: i64,
    
    /// Not before timestamp
    pub nbf: i64,
    
    /// Issuer
    pub iss: String,
    
    /// Audience
    pub aud: String,
    
    /// JWT ID
    pub jti: String,
    
    /// User email
    pub email: String,
    
    /// User roles
    pub roles: Vec<String>,
    
    /// User permissions
    pub permissions: Vec<String>,
    
    /// Session ID
    pub session_id: String,
    
    /// Token type (access or refresh)
    pub token_type: TokenType,
    
    /// Organization ID (optional)
    pub org_id: Option<String>,
}

/// Token type enumeration
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum TokenType {
    Access,
    Refresh,
}

/// JWT token manager
pub struct JwtManager {
    encoding_key: EncodingKey,
    decoding_key: DecodingKey,
    validation: Validation,
    config: SecurityConfig,
}

impl JwtManager {
    /// Create a new JWT manager
    pub fn new(config: SecurityConfig) -> Result<Self, RegulateAIError> {
        let encoding_key = EncodingKey::from_secret(config.jwt.secret.as_bytes());
        let decoding_key = DecodingKey::from_secret(config.jwt.secret.as_bytes());
        
        let mut validation = Validation::new(Algorithm::HS256);
        validation.set_issuer(&[&config.jwt.issuer]);
        validation.set_audience(&[&config.jwt.audience]);
        validation.leeway = config.jwt.leeway;
        
        Ok(Self {
            encoding_key,
            decoding_key,
            validation,
            config,
        })
    }

    /// Generate an access token
    pub fn generate_access_token(
        &self,
        user_id: Uuid,
        email: &str,
        roles: Vec<String>,
        permissions: Vec<String>,
        session_id: Uuid,
        org_id: Option<Uuid>,
    ) -> Result<String, RegulateAIError> {
        let now = Utc::now();
        let exp = now + Duration::seconds(self.config.jwt.expiration as i64);
        
        let claims = Claims {
            sub: user_id.to_string(),
            iat: now.timestamp(),
            exp: exp.timestamp(),
            nbf: now.timestamp(),
            iss: self.config.jwt.issuer.clone(),
            aud: self.config.jwt.audience.clone(),
            jti: Uuid::new_v4().to_string(),
            email: email.to_string(),
            roles,
            permissions,
            session_id: session_id.to_string(),
            token_type: TokenType::Access,
            org_id: org_id.map(|id| id.to_string()),
        };

        encode(&Header::default(), &claims, &self.encoding_key)
            .map_err(|e| RegulateAIError::Authentication {
                message: format!("Failed to generate access token: {}", e),
                code: "JWT_GENERATION_FAILED".to_string(),
            })
    }

    /// Generate a refresh token
    pub fn generate_refresh_token(
        &self,
        user_id: Uuid,
        session_id: Uuid,
    ) -> Result<String, RegulateAIError> {
        let now = Utc::now();
        let exp = now + Duration::seconds(self.config.jwt.refresh_expiration as i64);
        
        let claims = Claims {
            sub: user_id.to_string(),
            iat: now.timestamp(),
            exp: exp.timestamp(),
            nbf: now.timestamp(),
            iss: self.config.jwt.issuer.clone(),
            aud: self.config.jwt.audience.clone(),
            jti: Uuid::new_v4().to_string(),
            email: String::new(), // Not needed for refresh tokens
            roles: vec![],
            permissions: vec![],
            session_id: session_id.to_string(),
            token_type: TokenType::Refresh,
            org_id: None,
        };

        encode(&Header::default(), &claims, &self.encoding_key)
            .map_err(|e| RegulateAIError::Authentication {
                message: format!("Failed to generate refresh token: {}", e),
                code: "JWT_GENERATION_FAILED".to_string(),
            })
    }

    /// Validate and decode a token
    pub fn validate_token(&self, token: &str) -> Result<Claims, RegulateAIError> {
        decode::<Claims>(token, &self.decoding_key, &self.validation)
            .map(|token_data| token_data.claims)
            .map_err(|e| match e.kind() {
                jsonwebtoken::errors::ErrorKind::ExpiredSignature => {
                    RegulateAIError::Authentication {
                        message: "Token has expired".to_string(),
                        code: "JWT_EXPIRED".to_string(),
                    }
                }
                jsonwebtoken::errors::ErrorKind::InvalidToken => {
                    RegulateAIError::Authentication {
                        message: "Invalid token format".to_string(),
                        code: "JWT_INVALID".to_string(),
                    }
                }
                jsonwebtoken::errors::ErrorKind::InvalidSignature => {
                    RegulateAIError::Authentication {
                        message: "Invalid token signature".to_string(),
                        code: "JWT_INVALID_SIGNATURE".to_string(),
                    }
                }
                jsonwebtoken::errors::ErrorKind::InvalidIssuer => {
                    RegulateAIError::Authentication {
                        message: "Invalid token issuer".to_string(),
                        code: "JWT_INVALID_ISSUER".to_string(),
                    }
                }
                jsonwebtoken::errors::ErrorKind::InvalidAudience => {
                    RegulateAIError::Authentication {
                        message: "Invalid token audience".to_string(),
                        code: "JWT_INVALID_AUDIENCE".to_string(),
                    }
                }
                _ => RegulateAIError::Authentication {
                    message: format!("Token validation failed: {}", e),
                    code: "JWT_VALIDATION_FAILED".to_string(),
                }
            })
    }

    /// Extract user ID from token
    pub fn extract_user_id(&self, token: &str) -> Result<Uuid, RegulateAIError> {
        let claims = self.validate_token(token)?;
        Uuid::parse_str(&claims.sub).map_err(|_| RegulateAIError::Authentication {
            message: "Invalid user ID in token".to_string(),
            code: "JWT_INVALID_USER_ID".to_string(),
        })
    }

    /// Extract session ID from token
    pub fn extract_session_id(&self, token: &str) -> Result<Uuid, RegulateAIError> {
        let claims = self.validate_token(token)?;
        Uuid::parse_str(&claims.session_id).map_err(|_| RegulateAIError::Authentication {
            message: "Invalid session ID in token".to_string(),
            code: "JWT_INVALID_SESSION_ID".to_string(),
        })
    }

    /// Check if token has specific permission
    pub fn has_permission(&self, token: &str, permission: &str) -> Result<bool, RegulateAIError> {
        let claims = self.validate_token(token)?;
        Ok(claims.permissions.contains(&permission.to_string()) || 
           claims.permissions.contains(&"*".to_string()))
    }

    /// Check if token has specific role
    pub fn has_role(&self, token: &str, role: &str) -> Result<bool, RegulateAIError> {
        let claims = self.validate_token(token)?;
        Ok(claims.roles.contains(&role.to_string()))
    }

    /// Check if token has any of the specified roles
    pub fn has_any_role(&self, token: &str, roles: &[&str]) -> Result<bool, RegulateAIError> {
        let claims = self.validate_token(token)?;
        let user_roles: HashSet<String> = claims.roles.into_iter().collect();
        let required_roles: HashSet<String> = roles.iter().map(|r| r.to_string()).collect();
        
        Ok(!user_roles.is_disjoint(&required_roles))
    }

    /// Check if token is of specific type
    pub fn is_token_type(&self, token: &str, token_type: TokenType) -> Result<bool, RegulateAIError> {
        let claims = self.validate_token(token)?;
        Ok(claims.token_type == token_type)
    }

    /// Get token expiration time
    pub fn get_token_expiration(&self, token: &str) -> Result<chrono::DateTime<Utc>, RegulateAIError> {
        let claims = self.validate_token(token)?;
        Ok(chrono::DateTime::from_timestamp(claims.exp, 0)
            .ok_or_else(|| RegulateAIError::Authentication {
                message: "Invalid expiration timestamp in token".to_string(),
                code: "JWT_INVALID_EXPIRATION".to_string(),
            })?)
    }

    /// Check if token is about to expire (within specified minutes)
    pub fn is_token_expiring_soon(&self, token: &str, minutes: i64) -> Result<bool, RegulateAIError> {
        let exp_time = self.get_token_expiration(token)?;
        let threshold = Utc::now() + Duration::minutes(minutes);
        Ok(exp_time <= threshold)
    }
}

/// Token pair containing access and refresh tokens
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenPair {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: i64,
    pub refresh_expires_in: i64,
}

impl TokenPair {
    pub fn new(
        access_token: String,
        refresh_token: String,
        access_expires_in: i64,
        refresh_expires_in: i64,
    ) -> Self {
        Self {
            access_token,
            refresh_token,
            token_type: "Bearer".to_string(),
            expires_in: access_expires_in,
            refresh_expires_in,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use regulateai_config::SecurityConfig;

    fn create_test_jwt_manager() -> JwtManager {
        let config = SecurityConfig::default();
        JwtManager::new(config).unwrap()
    }

    #[test]
    fn test_generate_and_validate_access_token() {
        let jwt_manager = create_test_jwt_manager();
        let user_id = Uuid::new_v4();
        let session_id = Uuid::new_v4();
        
        let token = jwt_manager.generate_access_token(
            user_id,
            "test@example.com",
            vec!["user".to_string()],
            vec!["read".to_string()],
            session_id,
            None,
        ).unwrap();
        
        let claims = jwt_manager.validate_token(&token).unwrap();
        assert_eq!(claims.sub, user_id.to_string());
        assert_eq!(claims.email, "test@example.com");
        assert_eq!(claims.token_type, TokenType::Access);
    }

    #[test]
    fn test_generate_and_validate_refresh_token() {
        let jwt_manager = create_test_jwt_manager();
        let user_id = Uuid::new_v4();
        let session_id = Uuid::new_v4();
        
        let token = jwt_manager.generate_refresh_token(user_id, session_id).unwrap();
        
        let claims = jwt_manager.validate_token(&token).unwrap();
        assert_eq!(claims.sub, user_id.to_string());
        assert_eq!(claims.token_type, TokenType::Refresh);
    }

    #[test]
    fn test_extract_user_id() {
        let jwt_manager = create_test_jwt_manager();
        let user_id = Uuid::new_v4();
        let session_id = Uuid::new_v4();
        
        let token = jwt_manager.generate_access_token(
            user_id,
            "test@example.com",
            vec![],
            vec![],
            session_id,
            None,
        ).unwrap();
        
        let extracted_id = jwt_manager.extract_user_id(&token).unwrap();
        assert_eq!(extracted_id, user_id);
    }

    #[test]
    fn test_permission_check() {
        let jwt_manager = create_test_jwt_manager();
        let user_id = Uuid::new_v4();
        let session_id = Uuid::new_v4();
        
        let token = jwt_manager.generate_access_token(
            user_id,
            "test@example.com",
            vec![],
            vec!["read".to_string(), "write".to_string()],
            session_id,
            None,
        ).unwrap();
        
        assert!(jwt_manager.has_permission(&token, "read").unwrap());
        assert!(jwt_manager.has_permission(&token, "write").unwrap());
        assert!(!jwt_manager.has_permission(&token, "admin").unwrap());
    }

    #[test]
    fn test_role_check() {
        let jwt_manager = create_test_jwt_manager();
        let user_id = Uuid::new_v4();
        let session_id = Uuid::new_v4();
        
        let token = jwt_manager.generate_access_token(
            user_id,
            "test@example.com",
            vec!["user".to_string(), "analyst".to_string()],
            vec![],
            session_id,
            None,
        ).unwrap();
        
        assert!(jwt_manager.has_role(&token, "user").unwrap());
        assert!(jwt_manager.has_role(&token, "analyst").unwrap());
        assert!(!jwt_manager.has_role(&token, "admin").unwrap());
        
        assert!(jwt_manager.has_any_role(&token, &["user", "admin"]).unwrap());
        assert!(!jwt_manager.has_any_role(&token, &["admin", "super_admin"]).unwrap());
    }

    #[test]
    fn test_invalid_token() {
        let jwt_manager = create_test_jwt_manager();
        
        let result = jwt_manager.validate_token("invalid.token.here");
        assert!(result.is_err());
    }
}
