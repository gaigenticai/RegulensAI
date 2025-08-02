//! Password hashing and validation utilities

use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use rand::Rng;
use regex::Regex;
use std::collections::HashSet;

use regulateai_config::PasswordPolicyConfig;
use regulateai_errors::RegulateAIError;

/// Password hasher using Argon2
pub struct PasswordHasher {
    argon2: Argon2<'static>,
    policy: PasswordPolicyConfig,
}

impl PasswordHasher {
    /// Create a new password hasher with the given policy
    pub fn new(policy: PasswordPolicyConfig) -> Self {
        Self {
            argon2: Argon2::default(),
            policy,
        }
    }

    /// Hash a password using Argon2
    pub fn hash_password(&self, password: &str) -> Result<String, RegulateAIError> {
        // Validate password against policy first
        self.validate_password(password)?;

        let salt = SaltString::generate(&mut OsRng);
        
        self.argon2
            .hash_password(password.as_bytes(), &salt)
            .map(|hash| hash.to_string())
            .map_err(|e| RegulateAIError::Cryptographic {
                message: format!("Password hashing failed: {}", e),
                operation: "hash_password".to_string(),
                code: "PASSWORD_HASH_FAILED".to_string(),
            })
    }

    /// Verify a password against its hash
    pub fn verify_password(&self, password: &str, hash: &str) -> Result<bool, RegulateAIError> {
        let parsed_hash = PasswordHash::new(hash)
            .map_err(|e| RegulateAIError::Cryptographic {
                message: format!("Invalid password hash format: {}", e),
                operation: "parse_hash".to_string(),
                code: "INVALID_PASSWORD_HASH".to_string(),
            })?;

        match self.argon2.verify_password(password.as_bytes(), &parsed_hash) {
            Ok(()) => Ok(true),
            Err(argon2::password_hash::Error::Password) => Ok(false),
            Err(e) => Err(RegulateAIError::Cryptographic {
                message: format!("Password verification failed: {}", e),
                operation: "verify_password".to_string(),
                code: "PASSWORD_VERIFY_FAILED".to_string(),
            }),
        }
    }

    /// Validate password against policy
    pub fn validate_password(&self, password: &str) -> Result<(), RegulateAIError> {
        let mut errors = Vec::new();

        // Check length
        if password.len() < self.policy.min_length {
            errors.push(format!("Password must be at least {} characters long", self.policy.min_length));
        }

        if password.len() > self.policy.max_length {
            errors.push(format!("Password must not exceed {} characters", self.policy.max_length));
        }

        // Check character requirements
        if self.policy.require_uppercase && !password.chars().any(|c| c.is_uppercase()) {
            errors.push("Password must contain at least one uppercase letter".to_string());
        }

        if self.policy.require_lowercase && !password.chars().any(|c| c.is_lowercase()) {
            errors.push("Password must contain at least one lowercase letter".to_string());
        }

        if self.policy.require_digits && !password.chars().any(|c| c.is_ascii_digit()) {
            errors.push("Password must contain at least one digit".to_string());
        }

        if self.policy.require_special_chars {
            let has_special = password.chars().any(|c| self.policy.allowed_special_chars.contains(c));
            if !has_special {
                errors.push(format!(
                    "Password must contain at least one special character from: {}",
                    self.policy.allowed_special_chars
                ));
            }
        }

        // Check for common weak patterns
        if let Err(weakness_errors) = self.check_password_weakness(password) {
            errors.extend(weakness_errors);
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(RegulateAIError::Validation {
                message: errors.join(", "),
                field: Some("password".to_string()),
                code: "PASSWORD_POLICY_VIOLATION".to_string(),
            })
        }
    }

    /// Check for common password weaknesses
    fn check_password_weakness(&self, password: &str) -> Result<(), Vec<String>> {
        let mut errors = Vec::new();

        // Check for common patterns
        if self.is_common_pattern(password) {
            errors.push("Password contains common patterns that are easily guessed".to_string());
        }

        // Check for repeated characters
        if self.has_excessive_repetition(password) {
            errors.push("Password contains too many repeated characters".to_string());
        }

        // Check for sequential characters
        if self.has_sequential_characters(password) {
            errors.push("Password contains sequential characters (e.g., 123, abc)".to_string());
        }

        // Check against common passwords (simplified check)
        if self.is_common_password(password) {
            errors.push("Password is too common and easily guessed".to_string());
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }

    /// Check if password contains common patterns
    fn is_common_pattern(&self, password: &str) -> bool {
        let common_patterns = [
            r"^password\d*$",
            r"^123+",
            r"^qwerty",
            r"^admin\d*$",
            r"^user\d*$",
            r"^test\d*$",
        ];

        let lower_password = password.to_lowercase();
        
        for pattern in &common_patterns {
            if let Ok(regex) = Regex::new(pattern) {
                if regex.is_match(&lower_password) {
                    return true;
                }
            }
        }

        false
    }

    /// Check for excessive character repetition
    fn has_excessive_repetition(&self, password: &str) -> bool {
        let mut char_counts = std::collections::HashMap::new();
        
        for c in password.chars() {
            *char_counts.entry(c).or_insert(0) += 1;
        }

        // If any character appears more than 1/3 of the password length, it's excessive
        let max_allowed = (password.len() / 3).max(1);
        char_counts.values().any(|&count| count > max_allowed)
    }

    /// Check for sequential characters
    fn has_sequential_characters(&self, password: &str) -> bool {
        let chars: Vec<char> = password.chars().collect();
        
        for window in chars.windows(3) {
            if let [a, b, c] = window {
                // Check for ascending sequence
                if (*b as u8) == (*a as u8) + 1 && (*c as u8) == (*b as u8) + 1 {
                    return true;
                }
                // Check for descending sequence
                if (*b as u8) == (*a as u8) - 1 && (*c as u8) == (*b as u8) - 1 {
                    return true;
                }
            }
        }

        false
    }

    /// Check if password is in common passwords list (simplified)
    fn is_common_password(&self, password: &str) -> bool {
        let common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "master",
            "shadow", "123456789", "football", "baseball", "superman",
        ];

        let lower_password = password.to_lowercase();
        common_passwords.contains(&lower_password.as_str())
    }

    /// Generate a secure random password
    pub fn generate_secure_password(&self, length: usize) -> String {
        let mut rng = rand::thread_rng();
        
        let uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        let lowercase = "abcdefghijklmnopqrstuvwxyz";
        let digits = "0123456789";
        let special_chars = &self.policy.allowed_special_chars;
        
        let mut password = String::new();
        let mut char_sets = Vec::new();
        
        // Ensure at least one character from each required set
        if self.policy.require_uppercase {
            char_sets.push(uppercase);
            password.push(uppercase.chars().nth(rng.gen_range(0..uppercase.len())).unwrap());
        }
        
        if self.policy.require_lowercase {
            char_sets.push(lowercase);
            password.push(lowercase.chars().nth(rng.gen_range(0..lowercase.len())).unwrap());
        }
        
        if self.policy.require_digits {
            char_sets.push(digits);
            password.push(digits.chars().nth(rng.gen_range(0..digits.len())).unwrap());
        }
        
        if self.policy.require_special_chars {
            char_sets.push(special_chars);
            password.push(special_chars.chars().nth(rng.gen_range(0..special_chars.len())).unwrap());
        }
        
        // Fill the rest with random characters from all allowed sets
        let all_chars: String = char_sets.join("");
        let all_chars_vec: Vec<char> = all_chars.chars().collect();
        
        while password.len() < length {
            let random_char = all_chars_vec[rng.gen_range(0..all_chars_vec.len())];
            password.push(random_char);
        }
        
        // Shuffle the password to avoid predictable patterns
        let mut password_chars: Vec<char> = password.chars().collect();
        for i in (1..password_chars.len()).rev() {
            let j = rng.gen_range(0..=i);
            password_chars.swap(i, j);
        }
        
        password_chars.into_iter().collect()
    }

    /// Check password strength and return a score (0-100)
    pub fn calculate_password_strength(&self, password: &str) -> u8 {
        let mut score = 0u8;
        
        // Length scoring
        match password.len() {
            0..=7 => score += 10,
            8..=11 => score += 20,
            12..=15 => score += 30,
            _ => score += 40,
        }
        
        // Character variety scoring
        let mut char_types = 0;
        if password.chars().any(|c| c.is_lowercase()) { char_types += 1; }
        if password.chars().any(|c| c.is_uppercase()) { char_types += 1; }
        if password.chars().any(|c| c.is_ascii_digit()) { char_types += 1; }
        if password.chars().any(|c| self.policy.allowed_special_chars.contains(c)) { char_types += 1; }
        
        score += char_types * 10;
        
        // Uniqueness scoring
        let unique_chars: HashSet<char> = password.chars().collect();
        let uniqueness_ratio = unique_chars.len() as f32 / password.len() as f32;
        score += (uniqueness_ratio * 20.0) as u8;
        
        // Penalty for common patterns
        if self.is_common_pattern(password) { score = score.saturating_sub(20); }
        if self.has_excessive_repetition(password) { score = score.saturating_sub(15); }
        if self.has_sequential_characters(password) { score = score.saturating_sub(15); }
        if self.is_common_password(password) { score = score.saturating_sub(30); }
        
        score.min(100)
    }

    /// Check if password has been compromised (placeholder for breach database integration)
    pub async fn is_password_compromised(&self, _password: &str) -> Result<bool, RegulateAIError> {
        // In a real implementation, this would check against databases like HaveIBeenPwned
        // For now, return false as a placeholder
        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use regulateai_config::PasswordPolicyConfig;

    fn create_test_policy() -> PasswordPolicyConfig {
        PasswordPolicyConfig {
            min_length: 8,
            max_length: 128,
            require_uppercase: true,
            require_lowercase: true,
            require_digits: true,
            require_special_chars: true,
            allowed_special_chars: "!@#$%^&*()_+-=[]{}|;:,.<>?".to_string(),
            max_login_attempts: 5,
            lockout_duration: 900,
            password_expiry_days: 90,
            password_history_count: 5,
        }
    }

    #[test]
    fn test_password_hashing_and_verification() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        let password = "SecureP@ssw0rd123";
        let hash = hasher.hash_password(password).unwrap();
        
        assert!(hasher.verify_password(password, &hash).unwrap());
        assert!(!hasher.verify_password("WrongPassword", &hash).unwrap());
    }

    #[test]
    fn test_password_validation() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        // Valid password
        assert!(hasher.validate_password("SecureP@ssw0rd123").is_ok());
        
        // Too short
        assert!(hasher.validate_password("Short1!").is_err());
        
        // Missing uppercase
        assert!(hasher.validate_password("lowercase123!").is_err());
        
        // Missing lowercase
        assert!(hasher.validate_password("UPPERCASE123!").is_err());
        
        // Missing digits
        assert!(hasher.validate_password("NoDigitsHere!").is_err());
        
        // Missing special characters
        assert!(hasher.validate_password("NoSpecialChars123").is_err());
    }

    #[test]
    fn test_common_pattern_detection() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        assert!(hasher.is_common_pattern("password123"));
        assert!(hasher.is_common_pattern("123456789"));
        assert!(hasher.is_common_pattern("qwerty123"));
        assert!(!hasher.is_common_pattern("SecureP@ssw0rd123"));
    }

    #[test]
    fn test_repetition_detection() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        assert!(hasher.has_excessive_repetition("aaaaaaa1!"));
        assert!(hasher.has_excessive_repetition("1111111a!"));
        assert!(!hasher.has_excessive_repetition("SecureP@ssw0rd123"));
    }

    #[test]
    fn test_sequential_character_detection() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        assert!(hasher.has_sequential_characters("abc123!"));
        assert!(hasher.has_sequential_characters("123abc!"));
        assert!(hasher.has_sequential_characters("cba321!"));
        assert!(!hasher.has_sequential_characters("SecureP@ssw0rd"));
    }

    #[test]
    fn test_password_strength_calculation() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        let weak_password = "password";
        let medium_password = "Password123";
        let strong_password = "SecureP@ssw0rd123!";
        
        let weak_score = hasher.calculate_password_strength(weak_password);
        let medium_score = hasher.calculate_password_strength(medium_password);
        let strong_score = hasher.calculate_password_strength(strong_password);
        
        assert!(weak_score < medium_score);
        assert!(medium_score < strong_score);
        assert!(strong_score >= 70); // Strong password should score high
    }

    #[test]
    fn test_secure_password_generation() {
        let policy = create_test_policy();
        let hasher = PasswordHasher::new(policy);
        
        let password = hasher.generate_secure_password(12);
        
        assert_eq!(password.len(), 12);
        assert!(hasher.validate_password(&password).is_ok());
        
        // Generate multiple passwords to ensure they're different
        let password1 = hasher.generate_secure_password(16);
        let password2 = hasher.generate_secure_password(16);
        assert_ne!(password1, password2);
    }
}
