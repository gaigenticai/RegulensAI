//! Constants used across RegulateAI services

/// Application constants
pub mod app {
    pub const NAME: &str = "RegulateAI";
    pub const VERSION: &str = env!("CARGO_PKG_VERSION");
    pub const DESCRIPTION: &str = "Enterprise Regulatory Compliance & Risk Management System";
}

/// HTTP constants
pub mod http {
    pub const DEFAULT_TIMEOUT_SECONDS: u64 = 30;
    pub const MAX_REQUEST_SIZE_BYTES: usize = 10 * 1024 * 1024; // 10MB
    pub const MAX_RESPONSE_SIZE_BYTES: usize = 50 * 1024 * 1024; // 50MB
    
    /// HTTP headers
    pub mod headers {
        pub const CORRELATION_ID: &str = "X-Correlation-ID";
        pub const REQUEST_ID: &str = "X-Request-ID";
        pub const USER_ID: &str = "X-User-ID";
        pub const TENANT_ID: &str = "X-Tenant-ID";
        pub const API_VERSION: &str = "X-API-Version";
        pub const RATE_LIMIT_REMAINING: &str = "X-RateLimit-Remaining";
        pub const RATE_LIMIT_RESET: &str = "X-RateLimit-Reset";
    }
}

/// Database constants
pub mod database {
    pub const DEFAULT_PAGE_SIZE: u32 = 50;
    pub const MAX_PAGE_SIZE: u32 = 1000;
    pub const DEFAULT_CONNECTION_TIMEOUT_SECONDS: u64 = 30;
    pub const DEFAULT_QUERY_TIMEOUT_SECONDS: u64 = 60;
    pub const MAX_CONNECTIONS: u32 = 100;
    pub const MIN_CONNECTIONS: u32 = 5;
}

/// Cache constants
pub mod cache {
    pub const DEFAULT_TTL_SECONDS: u64 = 3600; // 1 hour
    pub const SESSION_TTL_SECONDS: u64 = 86400; // 24 hours
    pub const SHORT_TTL_SECONDS: u64 = 300; // 5 minutes
    pub const LONG_TTL_SECONDS: u64 = 604800; // 1 week
    
    /// Cache key prefixes
    pub mod keys {
        pub const USER_SESSION: &str = "user:session:";
        pub const USER_PROFILE: &str = "user:profile:";
        pub const API_RATE_LIMIT: &str = "rate_limit:";
        pub const SANCTIONS_LIST: &str = "sanctions:list:";
        pub const RISK_SCORE: &str = "risk:score:";
        pub const FRAUD_MODEL: &str = "fraud:model:";
    }
}

/// Authentication and authorization constants
pub mod auth {
    pub const JWT_DEFAULT_EXPIRY_SECONDS: u64 = 3600; // 1 hour
    pub const JWT_REFRESH_EXPIRY_SECONDS: u64 = 604800; // 1 week
    pub const PASSWORD_MIN_LENGTH: usize = 8;
    pub const PASSWORD_MAX_LENGTH: usize = 128;
    pub const MAX_LOGIN_ATTEMPTS: u32 = 5;
    pub const LOCKOUT_DURATION_SECONDS: u64 = 900; // 15 minutes
    
    /// JWT claims
    pub mod claims {
        pub const ISSUER: &str = "regulateai";
        pub const AUDIENCE: &str = "regulateai-services";
        pub const SUBJECT: &str = "user";
    }
    
    /// RBAC roles
    pub mod roles {
        pub const SUPER_ADMIN: &str = "super_admin";
        pub const ADMIN: &str = "admin";
        pub const COMPLIANCE_OFFICER: &str = "compliance_officer";
        pub const RISK_MANAGER: &str = "risk_manager";
        pub const ANALYST: &str = "analyst";
        pub const AUDITOR: &str = "auditor";
        pub const USER: &str = "user";
        pub const READONLY: &str = "readonly";
    }
    
    /// Permissions
    pub mod permissions {
        pub const READ: &str = "read";
        pub const WRITE: &str = "write";
        pub const DELETE: &str = "delete";
        pub const ADMIN: &str = "admin";
        pub const APPROVE: &str = "approve";
        pub const AUDIT: &str = "audit";
    }
}

/// AML (Anti-Money Laundering) constants
pub mod aml {
    pub const DEFAULT_TRANSACTION_THRESHOLD: f64 = 10000.0;
    pub const HIGH_RISK_THRESHOLD: f64 = 75.0;
    pub const MEDIUM_RISK_THRESHOLD: f64 = 50.0;
    pub const LOW_RISK_THRESHOLD: f64 = 25.0;
    pub const SANCTIONS_UPDATE_INTERVAL_SECONDS: u64 = 3600; // 1 hour
    pub const KYC_DOCUMENT_RETENTION_DAYS: u32 = 2555; // 7 years
    
    /// Transaction types
    pub mod transaction_types {
        pub const DEPOSIT: &str = "deposit";
        pub const WITHDRAWAL: &str = "withdrawal";
        pub const TRANSFER: &str = "transfer";
        pub const PAYMENT: &str = "payment";
        pub const EXCHANGE: &str = "exchange";
    }
    
    /// Risk factors
    pub mod risk_factors {
        pub const HIGH_RISK_COUNTRIES: &[&str] = &[
            "AF", "BY", "MM", "CF", "CU", "CD", "ER", "GN", "HT", "IR", "IQ", "LB", "LY", "ML", "NI", "KP", "SO", "SS", "SD", "SY", "UA", "VE", "YE", "ZW"
        ];
        pub const PEP_RISK_MULTIPLIER: f64 = 2.0;
        pub const SANCTIONS_RISK_MULTIPLIER: f64 = 5.0;
    }
}

/// Fraud detection constants
pub mod fraud {
    pub const DEFAULT_DETECTION_THRESHOLD: f64 = 0.8;
    pub const MODEL_UPDATE_INTERVAL_SECONDS: u64 = 86400; // 24 hours
    pub const VELOCITY_CHECK_WINDOW_SECONDS: u64 = 3600; // 1 hour
    pub const MAX_DAILY_TRANSACTIONS: u32 = 100;
    pub const MAX_TRANSACTION_AMOUNT: f64 = 100000.0;
    
    /// Fraud types
    pub mod types {
        pub const IDENTITY_FRAUD: &str = "identity_fraud";
        pub const TRANSACTION_FRAUD: &str = "transaction_fraud";
        pub const APPLICATION_FRAUD: &str = "application_fraud";
        pub const ACCOUNT_TAKEOVER: &str = "account_takeover";
        pub const SYNTHETIC_IDENTITY: &str = "synthetic_identity";
    }
}

/// Risk management constants
pub mod risk {
    pub const MONTE_CARLO_DEFAULT_ITERATIONS: u32 = 10000;
    pub const STRESS_TEST_SCENARIOS: u32 = 5;
    pub const RISK_ASSESSMENT_INTERVAL_SECONDS: u64 = 86400; // 24 hours
    pub const VaR_CONFIDENCE_LEVEL: f64 = 0.95; // 95%
    pub const EXPECTED_SHORTFALL_CONFIDENCE: f64 = 0.975; // 97.5%
    
    /// Risk categories
    pub mod categories {
        pub const CREDIT_RISK: &str = "credit_risk";
        pub const MARKET_RISK: &str = "market_risk";
        pub const OPERATIONAL_RISK: &str = "operational_risk";
        pub const LIQUIDITY_RISK: &str = "liquidity_risk";
        pub const REGULATORY_RISK: &str = "regulatory_risk";
        pub const REPUTATIONAL_RISK: &str = "reputational_risk";
    }
}

/// Compliance constants
pub mod compliance {
    pub const AUDIT_RETENTION_DAYS: u32 = 2555; // 7 years
    pub const POLICY_REVIEW_INTERVAL_DAYS: u32 = 365; // 1 year
    pub const ATTESTATION_REMINDER_DAYS: u32 = 30;
    pub const CONTROL_TESTING_FREQUENCY_DAYS: u32 = 90; // Quarterly
    
    /// Compliance frameworks
    pub mod frameworks {
        pub const SOC2: &str = "SOC2";
        pub const ISO27001: &str = "ISO27001";
        pub const PCI_DSS: &str = "PCI_DSS";
        pub const GDPR: &str = "GDPR";
        pub const CCPA: &str = "CCPA";
        pub const HIPAA: &str = "HIPAA";
        pub const SOX: &str = "SOX";
    }
}

/// Cybersecurity constants
pub mod cybersecurity {
    pub const VULNERABILITY_SCAN_INTERVAL_SECONDS: u64 = 86400; // 24 hours
    pub const INCIDENT_RESPONSE_SLA_MINUTES: u32 = 60; // 1 hour
    pub const PASSWORD_EXPIRY_DAYS: u32 = 90;
    pub const SESSION_TIMEOUT_MINUTES: u32 = 30;
    pub const MAX_FAILED_LOGIN_ATTEMPTS: u32 = 3;
    
    /// Severity levels
    pub mod severity {
        pub const CRITICAL: &str = "critical";
        pub const HIGH: &str = "high";
        pub const MEDIUM: &str = "medium";
        pub const LOW: &str = "low";
        pub const INFO: &str = "info";
    }
    
    /// Incident types
    pub mod incident_types {
        pub const DATA_BREACH: &str = "data_breach";
        pub const MALWARE: &str = "malware";
        pub const PHISHING: &str = "phishing";
        pub const UNAUTHORIZED_ACCESS: &str = "unauthorized_access";
        pub const DENIAL_OF_SERVICE: &str = "denial_of_service";
        pub const INSIDER_THREAT: &str = "insider_threat";
    }
}

/// AI and ML constants
pub mod ai {
    pub const DEFAULT_CONTEXT_WINDOW: usize = 4096;
    pub const MAX_TOKENS: usize = 8192;
    pub const DEFAULT_TEMPERATURE: f32 = 0.1;
    pub const AGENT_TIMEOUT_SECONDS: u64 = 300; // 5 minutes
    pub const MODEL_CACHE_TTL_SECONDS: u64 = 3600; // 1 hour
    
    /// Model types
    pub mod models {
        pub const GPT4: &str = "gpt-4";
        pub const GPT35_TURBO: &str = "gpt-3.5-turbo";
        pub const CLAUDE: &str = "claude-3";
        pub const LLAMA: &str = "llama-2";
    }
}

/// File and document constants
pub mod files {
    pub const MAX_FILE_SIZE_BYTES: usize = 100 * 1024 * 1024; // 100MB
    pub const ALLOWED_DOCUMENT_TYPES: &[&str] = &[
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv"
    ];
    pub const ALLOWED_IMAGE_TYPES: &[&str] = &[
        "jpg", "jpeg", "png", "gif", "bmp", "webp"
    ];
    pub const DOCUMENT_RETENTION_DAYS: u32 = 2555; // 7 years
}

/// Notification constants
pub mod notifications {
    pub const EMAIL_RETRY_ATTEMPTS: u32 = 3;
    pub const SMS_RETRY_ATTEMPTS: u32 = 2;
    pub const WEBHOOK_TIMEOUT_SECONDS: u64 = 30;
    pub const NOTIFICATION_BATCH_SIZE: usize = 100;
    
    /// Notification types
    pub mod types {
        pub const ALERT: &str = "alert";
        pub const WARNING: &str = "warning";
        pub const INFO: &str = "info";
        pub const REMINDER: &str = "reminder";
        pub const APPROVAL_REQUEST: &str = "approval_request";
    }
}

/// Monitoring and observability constants
pub mod monitoring {
    pub const METRICS_COLLECTION_INTERVAL_SECONDS: u64 = 60;
    pub const HEALTH_CHECK_INTERVAL_SECONDS: u64 = 30;
    pub const LOG_RETENTION_DAYS: u32 = 90;
    pub const TRACE_SAMPLE_RATE: f64 = 0.1; // 10%
    
    /// Metric names
    pub mod metrics {
        pub const REQUEST_DURATION: &str = "http_request_duration_seconds";
        pub const REQUEST_COUNT: &str = "http_requests_total";
        pub const ERROR_COUNT: &str = "errors_total";
        pub const DATABASE_CONNECTIONS: &str = "database_connections_active";
        pub const CACHE_HIT_RATE: &str = "cache_hit_rate";
    }
}
