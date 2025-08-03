//! Custom Assertions for Testing

/// Custom assertions for business logic
pub struct CustomAssertions;

/// Business rule assertions
pub struct BusinessRuleAssertions;

impl CustomAssertions {
    pub fn assert_valid_uuid(value: &str) -> Result<(), String> {
        uuid::Uuid::parse_str(value)
            .map(|_| ())
            .map_err(|_| format!("Invalid UUID: {}", value))
    }
}

impl BusinessRuleAssertions {
    pub fn assert_valid_transaction_amount(amount: f64) -> Result<(), String> {
        if amount <= 0.0 {
            Err("Transaction amount must be positive".to_string())
        } else if amount > 1_000_000.0 {
            Err("Transaction amount exceeds maximum limit".to_string())
        } else {
            Ok(())
        }
    }
}
