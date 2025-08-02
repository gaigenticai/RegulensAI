//! Utility functions used across RegulateAI services

use chrono::{DateTime, Utc};
use regex::Regex;
use std::collections::HashMap;
use uuid::Uuid;

/// Generate a new UUID v4
pub fn generate_id() -> Uuid {
    Uuid::new_v4()
}

/// Generate a correlation ID for request tracing
pub fn generate_correlation_id() -> String {
    format!("req_{}", Uuid::new_v4().simple())
}

/// Get current UTC timestamp
pub fn now_utc() -> DateTime<Utc> {
    Utc::now()
}

/// Format timestamp as ISO 8601 string
pub fn format_timestamp(timestamp: DateTime<Utc>) -> String {
    timestamp.to_rfc3339()
}

/// Parse ISO 8601 timestamp string
pub fn parse_timestamp(timestamp_str: &str) -> Result<DateTime<Utc>, chrono::ParseError> {
    DateTime::parse_from_rfc3339(timestamp_str)
        .map(|dt| dt.with_timezone(&Utc))
}

/// Validate email address format
pub fn is_valid_email(email: &str) -> bool {
    lazy_static::lazy_static! {
        static ref EMAIL_REGEX: Regex = Regex::new(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        ).unwrap();
    }
    EMAIL_REGEX.is_match(email)
}

/// Validate phone number format (international)
pub fn is_valid_phone(phone: &str) -> bool {
    lazy_static::lazy_static! {
        static ref PHONE_REGEX: Regex = Regex::new(
            r"^\+?[1-9]\d{1,14}$"
        ).unwrap();
    }
    PHONE_REGEX.is_match(phone)
}

/// Validate URL format
pub fn is_valid_url(url_str: &str) -> bool {
    url::Url::parse(url_str).is_ok()
}

/// Sanitize string input by removing potentially harmful characters
pub fn sanitize_string(input: &str) -> String {
    input
        .chars()
        .filter(|c| c.is_alphanumeric() || c.is_whitespace() || ".,!?-_@#$%^&*()[]{}".contains(*c))
        .collect()
}

/// Truncate string to specified length with ellipsis
pub fn truncate_string(input: &str, max_length: usize) -> String {
    if input.len() <= max_length {
        input.to_string()
    } else {
        format!("{}...", &input[..max_length.saturating_sub(3)])
    }
}

/// Convert string to slug format (lowercase, hyphens instead of spaces)
pub fn to_slug(input: &str) -> String {
    lazy_static::lazy_static! {
        static ref SLUG_REGEX: Regex = Regex::new(r"[^a-zA-Z0-9\s-]").unwrap();
        static ref WHITESPACE_REGEX: Regex = Regex::new(r"\s+").unwrap();
    }
    
    let cleaned = SLUG_REGEX.replace_all(input, "");
    let with_hyphens = WHITESPACE_REGEX.replace_all(&cleaned, "-");
    with_hyphens.to_lowercase()
}

/// Calculate percentage with precision
pub fn calculate_percentage(part: f64, total: f64, precision: usize) -> f64 {
    if total == 0.0 {
        0.0
    } else {
        let percentage = (part / total) * 100.0;
        let multiplier = 10_f64.powi(precision as i32);
        (percentage * multiplier).round() / multiplier
    }
}

/// Hash map utility functions
pub mod hash_map {
    use std::collections::HashMap;
    use std::hash::Hash;

    /// Merge two hash maps, with values from the second map taking precedence
    pub fn merge<K, V>(mut map1: HashMap<K, V>, map2: HashMap<K, V>) -> HashMap<K, V>
    where
        K: Eq + Hash,
    {
        for (key, value) in map2 {
            map1.insert(key, value);
        }
        map1
    }

    /// Filter hash map by predicate
    pub fn filter<K, V, F>(map: HashMap<K, V>, predicate: F) -> HashMap<K, V>
    where
        K: Eq + Hash,
        F: Fn(&K, &V) -> bool,
    {
        map.into_iter()
            .filter(|(k, v)| predicate(k, v))
            .collect()
    }
}

/// String utility functions
pub mod string {
    /// Check if string is empty or contains only whitespace
    pub fn is_blank(s: &str) -> bool {
        s.trim().is_empty()
    }

    /// Capitalize first letter of string
    pub fn capitalize(s: &str) -> String {
        let mut chars = s.chars();
        match chars.next() {
            None => String::new(),
            Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        }
    }

    /// Convert camelCase to snake_case
    pub fn camel_to_snake(s: &str) -> String {
        let mut result = String::new();
        for (i, c) in s.chars().enumerate() {
            if c.is_uppercase() && i > 0 {
                result.push('_');
            }
            result.push(c.to_lowercase().next().unwrap_or(c));
        }
        result
    }

    /// Convert snake_case to camelCase
    pub fn snake_to_camel(s: &str) -> String {
        let mut result = String::new();
        let mut capitalize_next = false;
        
        for c in s.chars() {
            if c == '_' {
                capitalize_next = true;
            } else if capitalize_next {
                result.push(c.to_uppercase().next().unwrap_or(c));
                capitalize_next = false;
            } else {
                result.push(c);
            }
        }
        result
    }
}

/// Numeric utility functions
pub mod numeric {
    /// Round float to specified decimal places
    pub fn round_to_decimal_places(value: f64, places: u32) -> f64 {
        let multiplier = 10_f64.powi(places as i32);
        (value * multiplier).round() / multiplier
    }

    /// Check if float is approximately equal to another float
    pub fn approx_equal(a: f64, b: f64, epsilon: f64) -> bool {
        (a - b).abs() < epsilon
    }

    /// Clamp value between min and max
    pub fn clamp<T: PartialOrd>(value: T, min: T, max: T) -> T {
        if value < min {
            min
        } else if value > max {
            max
        } else {
            value
        }
    }
}

/// Collection utility functions
pub mod collections {
    /// Chunk vector into smaller vectors of specified size
    pub fn chunk<T>(vec: Vec<T>, chunk_size: usize) -> Vec<Vec<T>> {
        vec.chunks(chunk_size)
            .map(|chunk| chunk.to_vec())
            .collect()
    }

    /// Remove duplicates from vector while preserving order
    pub fn dedup_preserve_order<T: PartialEq + Clone>(vec: Vec<T>) -> Vec<T> {
        let mut result = Vec::new();
        for item in vec {
            if !result.contains(&item) {
                result.push(item);
            }
        }
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_valid_email() {
        assert!(is_valid_email("test@example.com"));
        assert!(is_valid_email("user.name+tag@domain.co.uk"));
        assert!(!is_valid_email("invalid-email"));
        assert!(!is_valid_email("@domain.com"));
    }

    #[test]
    fn test_to_slug() {
        assert_eq!(to_slug("Hello World!"), "hello-world");
        assert_eq!(to_slug("Test@123 & More"), "test123--more");
    }

    #[test]
    fn test_calculate_percentage() {
        assert_eq!(calculate_percentage(25.0, 100.0, 2), 25.0);
        assert_eq!(calculate_percentage(1.0, 3.0, 2), 33.33);
        assert_eq!(calculate_percentage(10.0, 0.0, 2), 0.0);
    }
}
