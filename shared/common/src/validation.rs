//! Validation utilities and custom validators for RegulateAI services

use regex::Regex;
use std::collections::HashSet;
use validator::{ValidationError, ValidationErrors};

/// Custom validation result type
pub type ValidationResult<T> = Result<T, ValidationErrors>;

/// Validate email address format
pub fn validate_email(email: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref EMAIL_REGEX: Regex = Regex::new(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        ).unwrap();
    }
    
    if EMAIL_REGEX.is_match(email) {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_email_format"))
    }
}

/// Validate phone number format (international)
pub fn validate_phone(phone: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref PHONE_REGEX: Regex = Regex::new(
            r"^\+?[1-9]\d{1,14}$"
        ).unwrap();
    }
    
    if PHONE_REGEX.is_match(phone) {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_phone_format"))
    }
}

/// Validate URL format
pub fn validate_url(url: &str) -> Result<(), ValidationError> {
    match url::Url::parse(url) {
        Ok(_) => Ok(()),
        Err(_) => Err(ValidationError::new("invalid_url_format")),
    }
}

/// Validate password strength
pub fn validate_password(password: &str) -> Result<(), ValidationError> {
    let mut errors = Vec::new();
    
    // Minimum length
    if password.len() < 8 {
        errors.push("Password must be at least 8 characters long");
    }
    
    // Maximum length
    if password.len() > 128 {
        errors.push("Password must not exceed 128 characters");
    }
    
    // Must contain lowercase letter
    if !password.chars().any(|c| c.is_lowercase()) {
        errors.push("Password must contain at least one lowercase letter");
    }
    
    // Must contain uppercase letter
    if !password.chars().any(|c| c.is_uppercase()) {
        errors.push("Password must contain at least one uppercase letter");
    }
    
    // Must contain digit
    if !password.chars().any(|c| c.is_ascii_digit()) {
        errors.push("Password must contain at least one digit");
    }
    
    // Must contain special character
    if !password.chars().any(|c| "!@#$%^&*()_+-=[]{}|;:,.<>?".contains(c)) {
        errors.push("Password must contain at least one special character");
    }
    
    if errors.is_empty() {
        Ok(())
    } else {
        let mut error = ValidationError::new("weak_password");
        error.message = Some(errors.join(", ").into());
        Err(error)
    }
}

/// Validate country code (ISO 3166-1 alpha-2)
pub fn validate_country_code(code: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref COUNTRY_CODES: HashSet<&'static str> = {
            let mut set = HashSet::new();
            // Add common country codes (this is a subset - in production, use a complete list)
            set.insert("US"); set.insert("CA"); set.insert("GB"); set.insert("DE");
            set.insert("FR"); set.insert("IT"); set.insert("ES"); set.insert("NL");
            set.insert("BE"); set.insert("CH"); set.insert("AT"); set.insert("SE");
            set.insert("NO"); set.insert("DK"); set.insert("FI"); set.insert("IE");
            set.insert("PT"); set.insert("GR"); set.insert("PL"); set.insert("CZ");
            set.insert("HU"); set.insert("SK"); set.insert("SI"); set.insert("HR");
            set.insert("BG"); set.insert("RO"); set.insert("LT"); set.insert("LV");
            set.insert("EE"); set.insert("MT"); set.insert("CY"); set.insert("LU");
            set.insert("JP"); set.insert("KR"); set.insert("CN"); set.insert("IN");
            set.insert("AU"); set.insert("NZ"); set.insert("SG"); set.insert("HK");
            set.insert("BR"); set.insert("MX"); set.insert("AR"); set.insert("CL");
            set.insert("CO"); set.insert("PE"); set.insert("VE"); set.insert("UY");
            set.insert("ZA"); set.insert("EG"); set.insert("NG"); set.insert("KE");
            set.insert("MA"); set.insert("TN"); set.insert("GH"); set.insert("ET");
            set.insert("RU"); set.insert("TR"); set.insert("SA"); set.insert("AE");
            set.insert("IL"); set.insert("JO"); set.insert("LB"); set.insert("KW");
            set.insert("QA"); set.insert("BH"); set.insert("OM"); set.insert("PK");
            set.insert("BD"); set.insert("LK"); set.insert("TH"); set.insert("VN");
            set.insert("MY"); set.insert("ID"); set.insert("PH"); set.insert("TW");
            set
        };
    }
    
    if COUNTRY_CODES.contains(code) {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_country_code"))
    }
}

/// Validate currency code (ISO 4217)
pub fn validate_currency_code(code: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref CURRENCY_CODES: HashSet<&'static str> = {
            let mut set = HashSet::new();
            // Add common currency codes
            set.insert("USD"); set.insert("EUR"); set.insert("GBP"); set.insert("JPY");
            set.insert("CHF"); set.insert("CAD"); set.insert("AUD"); set.insert("NZD");
            set.insert("SEK"); set.insert("NOK"); set.insert("DKK"); set.insert("PLN");
            set.insert("CZK"); set.insert("HUF"); set.insert("BGN"); set.insert("RON");
            set.insert("HRK"); set.insert("RUB"); set.insert("TRY"); set.insert("CNY");
            set.insert("INR"); set.insert("KRW"); set.insert("SGD"); set.insert("HKD");
            set.insert("THB"); set.insert("MYR"); set.insert("IDR"); set.insert("PHP");
            set.insert("VND"); set.insert("BRL"); set.insert("MXN"); set.insert("ARS");
            set.insert("CLP"); set.insert("COP"); set.insert("PEN"); set.insert("UYU");
            set.insert("ZAR"); set.insert("EGP"); set.insert("NGN"); set.insert("KES");
            set.insert("MAD"); set.insert("TND"); set.insert("GHS"); set.insert("ETB");
            set.insert("SAR"); set.insert("AED"); set.insert("ILS"); set.insert("JOD");
            set.insert("LBP"); set.insert("KWD"); set.insert("QAR"); set.insert("BHD");
            set.insert("OMR"); set.insert("PKR"); set.insert("BDT"); set.insert("LKR");
            set
        };
    }
    
    if CURRENCY_CODES.contains(code) {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_currency_code"))
    }
}

/// Validate IBAN (International Bank Account Number)
pub fn validate_iban(iban: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref IBAN_REGEX: Regex = Regex::new(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$").unwrap();
    }
    
    let iban = iban.replace(' ', "").to_uppercase();
    
    if !IBAN_REGEX.is_match(&iban) {
        return Err(ValidationError::new("invalid_iban_format"));
    }
    
    // IBAN checksum validation (simplified)
    let (country_code, check_digits, bban) = (&iban[0..2], &iban[2..4], &iban[4..]);
    let rearranged = format!("{}{}{}", bban, country_code, check_digits);
    
    // Convert letters to numbers (A=10, B=11, ..., Z=35)
    let mut numeric_string = String::new();
    for c in rearranged.chars() {
        if c.is_ascii_digit() {
            numeric_string.push(c);
        } else {
            numeric_string.push_str(&((c as u8 - b'A' + 10).to_string()));
        }
    }
    
    // Calculate mod 97
    let mut remainder = 0u64;
    for chunk in numeric_string.chars().collect::<Vec<_>>().chunks(9) {
        let chunk_str: String = chunk.iter().collect();
        let chunk_num: u64 = format!("{}{}", remainder, chunk_str).parse().unwrap_or(0);
        remainder = chunk_num % 97;
    }
    
    if remainder == 1 {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_iban_checksum"))
    }
}

/// Validate credit card number using Luhn algorithm
pub fn validate_credit_card(number: &str) -> Result<(), ValidationError> {
    let number = number.replace(' ', "").replace('-', "");
    
    if !number.chars().all(|c| c.is_ascii_digit()) {
        return Err(ValidationError::new("invalid_credit_card_format"));
    }
    
    if number.len() < 13 || number.len() > 19 {
        return Err(ValidationError::new("invalid_credit_card_length"));
    }
    
    // Luhn algorithm
    let mut sum = 0;
    let mut alternate = false;
    
    for c in number.chars().rev() {
        let mut digit = c.to_digit(10).unwrap() as u32;
        
        if alternate {
            digit *= 2;
            if digit > 9 {
                digit = (digit % 10) + 1;
            }
        }
        
        sum += digit;
        alternate = !alternate;
    }
    
    if sum % 10 == 0 {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_credit_card_checksum"))
    }
}

/// Validate tax identification number (simplified - US SSN format)
pub fn validate_tax_id(tax_id: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref SSN_REGEX: Regex = Regex::new(r"^\d{3}-?\d{2}-?\d{4}$").unwrap();
    }
    
    if SSN_REGEX.is_match(tax_id) {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_tax_id_format"))
    }
}

/// Validate business identifier (simplified - US EIN format)
pub fn validate_business_id(business_id: &str) -> Result<(), ValidationError> {
    lazy_static::lazy_static! {
        static ref EIN_REGEX: Regex = Regex::new(r"^\d{2}-?\d{7}$").unwrap();
    }
    
    if EIN_REGEX.is_match(business_id) {
        Ok(())
    } else {
        Err(ValidationError::new("invalid_business_id_format"))
    }
}

/// Validate amount is positive and within reasonable bounds
pub fn validate_amount(amount: f64) -> Result<(), ValidationError> {
    if amount < 0.0 {
        return Err(ValidationError::new("amount_must_be_positive"));
    }
    
    if amount > 1_000_000_000.0 {
        return Err(ValidationError::new("amount_exceeds_maximum"));
    }
    
    // Check for reasonable decimal precision (max 2 decimal places for currency)
    let rounded = (amount * 100.0).round() / 100.0;
    if (amount - rounded).abs() > f64::EPSILON {
        return Err(ValidationError::new("amount_too_many_decimal_places"));
    }
    
    Ok(())
}

/// Validate risk score is between 0 and 100
pub fn validate_risk_score(score: f64) -> Result<(), ValidationError> {
    if score < 0.0 || score > 100.0 {
        Err(ValidationError::new("risk_score_out_of_range"))
    } else {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_email() {
        assert!(validate_email("test@example.com").is_ok());
        assert!(validate_email("user.name+tag@domain.co.uk").is_ok());
        assert!(validate_email("invalid-email").is_err());
        assert!(validate_email("@domain.com").is_err());
    }

    #[test]
    fn test_validate_password() {
        assert!(validate_password("StrongP@ss123").is_ok());
        assert!(validate_password("weak").is_err());
        assert!(validate_password("NoSpecialChar123").is_err());
        assert!(validate_password("nouppercasechar@123").is_err());
    }

    #[test]
    fn test_validate_credit_card() {
        // Valid test card numbers
        assert!(validate_credit_card("4111111111111111").is_ok()); // Visa
        assert!(validate_credit_card("5555555555554444").is_ok()); // Mastercard
        assert!(validate_credit_card("invalid").is_err());
        assert!(validate_credit_card("1234567890123456").is_err());
    }

    #[test]
    fn test_validate_risk_score() {
        assert!(validate_risk_score(50.0).is_ok());
        assert!(validate_risk_score(0.0).is_ok());
        assert!(validate_risk_score(100.0).is_ok());
        assert!(validate_risk_score(-1.0).is_err());
        assert!(validate_risk_score(101.0).is_err());
    }
}
