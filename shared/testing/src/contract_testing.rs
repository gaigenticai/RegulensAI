//! Contract Testing Framework
//! 
//! Implements consumer-driven contract testing to ensure API compatibility
//! between services in the RegulateAI microservices architecture.

use pact_consumer::prelude::*;
use pact_mock_server::mock_server::MockServer;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use uuid::Uuid;

/// Contract tester for managing service contracts
pub struct ContractTester {
    config: ContractTestConfig,
    contracts: HashMap<String, ServiceContract>,
    mock_servers: HashMap<String, MockServer>,
    http_client: Client,
}

/// Contract testing configuration
#[derive(Debug, Clone)]
pub struct ContractTestConfig {
    pub enabled: bool,
    pub pact_broker_url: Option<String>,
    pub pact_broker_token: Option<String>,
    pub consumer_version: String,
    pub provider_verification_enabled: bool,
    pub mock_server_port_range: (u16, u16),
    pub timeout_seconds: u64,
    pub parallel_execution: bool,
}

/// Service contract definition
#[derive(Debug, Clone)]
pub struct ServiceContract {
    pub consumer: String,
    pub provider: String,
    pub interactions: Vec<ContractInteraction>,
    pub metadata: ContractMetadata,
}

/// Contract interaction definition
#[derive(Debug, Clone)]
pub struct ContractInteraction {
    pub description: String,
    pub given: Option<String>,
    pub request: ContractRequest,
    pub response: ContractResponse,
}

/// Contract request specification
#[derive(Debug, Clone)]
pub struct ContractRequest {
    pub method: String,
    pub path: String,
    pub headers: Option<HashMap<String, String>>,
    pub body: Option<Value>,
    pub query: Option<HashMap<String, String>>,
}

/// Contract response specification
#[derive(Debug, Clone)]
pub struct ContractResponse {
    pub status: u16,
    pub headers: Option<HashMap<String, String>>,
    pub body: Option<Value>,
}

/// Contract metadata
#[derive(Debug, Clone)]
pub struct ContractMetadata {
    pub version: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub tags: Vec<String>,
}

/// Contract test results
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContractTestResults {
    pub results: Vec<ContractTestResult>,
    pub total_execution_time_ms: u64,
    pub started_at: DateTime<Utc>,
    pub completed_at: DateTime<Utc>,
}

/// Individual contract test result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContractTestResult {
    pub contract_name: String,
    pub consumer: String,
    pub provider: String,
    pub passed: bool,
    pub interactions_tested: usize,
    pub interactions_passed: usize,
    pub execution_time_ms: u64,
    pub error_message: Option<String>,
    pub failed_interactions: Vec<String>,
}

impl ContractTester {
    /// Create a new contract tester
    pub async fn new(config: ContractTestConfig) -> crate::TestResult<Self> {
        let http_client = Client::builder()
            .timeout(std::time::Duration::from_secs(config.timeout_seconds))
            .build()?;

        let mut tester = Self {
            config,
            contracts: HashMap::new(),
            mock_servers: HashMap::new(),
            http_client,
        };

        // Register default contracts for RegulateAI services
        tester.register_default_contracts().await?;

        Ok(tester)
    }

    /// Register default service contracts
    async fn register_default_contracts(&mut self) -> crate::TestResult<()> {
        // AML Service contracts
        self.register_contract(self.create_aml_customer_contract()).await?;
        self.register_contract(self.create_aml_transaction_contract()).await?;
        
        // Compliance Service contracts
        self.register_contract(self.create_compliance_policy_contract()).await?;
        self.register_contract(self.create_compliance_audit_contract()).await?;
        
        // Risk Management contracts
        self.register_contract(self.create_risk_assessment_contract()).await?;
        
        // Fraud Detection contracts
        self.register_contract(self.create_fraud_analysis_contract()).await?;

        Ok(())
    }

    /// Create AML-Customer service contract
    fn create_aml_customer_contract(&self) -> ServiceContract {
        ServiceContract {
            consumer: "aml-service".to_string(),
            provider: "customer-service".to_string(),
            interactions: vec![
                ContractInteraction {
                    description: "Get customer by ID".to_string(),
                    given: Some("customer exists with ID 12345".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/customers/12345".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: None,
                        query: None,
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "id": "12345",
                            "name": "John Doe",
                            "email": "john@example.com",
                            "kyc_status": "COMPLETED",
                            "risk_level": "LOW",
                            "created_at": "2024-01-01T00:00:00Z"
                        })),
                    },
                },
                ContractInteraction {
                    description: "Create new customer".to_string(),
                    given: Some("valid customer data provided".to_string()),
                    request: ContractRequest {
                        method: "POST".to_string(),
                        path: "/api/v1/customers".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "name": "Jane Doe",
                            "email": "jane@example.com",
                            "date_of_birth": "1990-01-01",
                            "country": "US"
                        })),
                        query: None,
                    },
                    response: ContractResponse {
                        status: 201,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "id": Matcher::regex(r"[0-9a-f-]{36}", "uuid"),
                            "name": "Jane Doe",
                            "email": "jane@example.com",
                            "kyc_status": "PENDING",
                            "risk_level": "MEDIUM",
                            "created_at": Matcher::iso_datetime()
                        })),
                    },
                },
            ],
            metadata: ContractMetadata {
                version: "1.0.0".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                tags: vec!["aml".to_string(), "customer".to_string()],
            },
        }
    }

    /// Create AML-Transaction service contract
    fn create_aml_transaction_contract(&self) -> ServiceContract {
        ServiceContract {
            consumer: "aml-service".to_string(),
            provider: "transaction-service".to_string(),
            interactions: vec![
                ContractInteraction {
                    description: "Get transaction by ID".to_string(),
                    given: Some("transaction exists with ID 67890".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/transactions/67890".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                        ])),
                        body: None,
                        query: None,
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "id": "67890",
                            "customer_id": "12345",
                            "amount": 1000.00,
                            "currency": "USD",
                            "type": "TRANSFER",
                            "status": "COMPLETED",
                            "created_at": "2024-01-01T12:00:00Z"
                        })),
                    },
                },
                ContractInteraction {
                    description: "Get transactions for customer".to_string(),
                    given: Some("customer has transactions".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/transactions".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                        ])),
                        body: None,
                        query: Some(HashMap::from([
                            ("customer_id".to_string(), "12345".to_string()),
                            ("limit".to_string(), "10".to_string()),
                        ])),
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "transactions": Matcher::each_like(json!({
                                "id": Matcher::regex(r"\d+", "transaction_id"),
                                "customer_id": "12345",
                                "amount": Matcher::decimal(),
                                "currency": Matcher::regex(r"[A-Z]{3}", "currency_code"),
                                "type": Matcher::regex(r"TRANSFER|DEPOSIT|WITHDRAWAL", "transaction_type"),
                                "status": Matcher::regex(r"PENDING|COMPLETED|FAILED", "status"),
                                "created_at": Matcher::iso_datetime()
                            }), 1),
                            "total": Matcher::integer(),
                            "page": 1,
                            "limit": 10
                        })),
                    },
                },
            ],
            metadata: ContractMetadata {
                version: "1.0.0".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                tags: vec!["aml".to_string(), "transaction".to_string()],
            },
        }
    }

    /// Create additional service contracts (simplified for brevity)
    fn create_compliance_policy_contract(&self) -> ServiceContract {
        ServiceContract {
            consumer: "compliance-service".to_string(),
            provider: "policy-service".to_string(),
            interactions: vec![
                ContractInteraction {
                    description: "Get compliance policies".to_string(),
                    given: Some("policies exist".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/policies".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                        ])),
                        body: None,
                        query: None,
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "policies": Matcher::each_like(json!({
                                "id": Matcher::uuid(),
                                "name": Matcher::string("Policy Name"),
                                "type": Matcher::regex(r"AML|KYC|GDPR", "policy_type"),
                                "status": "ACTIVE",
                                "created_at": Matcher::iso_datetime()
                            }), 1)
                        })),
                    },
                },
            ],
            metadata: ContractMetadata {
                version: "1.0.0".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                tags: vec!["compliance".to_string(), "policy".to_string()],
            },
        }
    }

    fn create_compliance_audit_contract(&self) -> ServiceContract {
        ServiceContract {
            consumer: "compliance-service".to_string(),
            provider: "audit-service".to_string(),
            interactions: vec![
                ContractInteraction {
                    description: "Create audit log entry".to_string(),
                    given: Some("valid audit data provided".to_string()),
                    request: ContractRequest {
                        method: "POST".to_string(),
                        path: "/api/v1/audit/logs".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "user_id": "user-123",
                            "action": "POLICY_UPDATE",
                            "resource_type": "COMPLIANCE_POLICY",
                            "resource_id": "policy-456",
                            "details": {
                                "old_status": "DRAFT",
                                "new_status": "ACTIVE"
                            },
                            "ip_address": "192.168.1.100"
                        })),
                        query: None,
                    },
                    response: ContractResponse {
                        status: 201,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "id": Matcher::uuid(),
                            "user_id": "user-123",
                            "action": "POLICY_UPDATE",
                            "resource_type": "COMPLIANCE_POLICY",
                            "resource_id": "policy-456",
                            "timestamp": Matcher::iso_datetime(),
                            "status": "LOGGED"
                        })),
                    },
                },
                ContractInteraction {
                    description: "Get audit logs for compliance review".to_string(),
                    given: Some("audit logs exist for the specified period".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/audit/logs".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                        ])),
                        body: None,
                        query: Some(HashMap::from([
                            ("start_date".to_string(), "2024-01-01".to_string()),
                            ("end_date".to_string(), "2024-01-31".to_string()),
                            ("resource_type".to_string(), "COMPLIANCE_POLICY".to_string()),
                            ("limit".to_string(), "50".to_string()),
                        ])),
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "logs": Matcher::each_like(json!({
                                "id": Matcher::uuid(),
                                "user_id": Matcher::string("user_id"),
                                "action": Matcher::regex(r"CREATE|UPDATE|DELETE|VIEW|APPROVE|REJECT", "action"),
                                "resource_type": "COMPLIANCE_POLICY",
                                "resource_id": Matcher::string("resource_id"),
                                "timestamp": Matcher::iso_datetime(),
                                "details": Matcher::object(),
                                "ip_address": Matcher::regex(r"\d+\.\d+\.\d+\.\d+", "ip_address")
                            }), 1),
                            "total": Matcher::integer(),
                            "page": 1,
                            "limit": 50
                        })),
                    },
                },
            ],
            metadata: ContractMetadata {
                version: "1.0.0".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                tags: vec!["compliance".to_string(), "audit".to_string()],
            },
        }
    }

    fn create_risk_assessment_contract(&self) -> ServiceContract {
        ServiceContract {
            consumer: "risk-service".to_string(),
            provider: "assessment-service".to_string(),
            interactions: vec![
                ContractInteraction {
                    description: "Create risk assessment for customer".to_string(),
                    given: Some("customer exists and requires risk assessment".to_string()),
                    request: ContractRequest {
                        method: "POST".to_string(),
                        path: "/api/v1/assessments".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "customer_id": "customer-123",
                            "assessment_type": "ONBOARDING",
                            "factors": {
                                "geographic_risk": 25.0,
                                "transaction_volume": 15000.0,
                                "customer_profile": "BUSINESS",
                                "regulatory_requirements": ["AML", "KYC"]
                            }
                        })),
                        query: None,
                    },
                    response: ContractResponse {
                        status: 201,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "id": Matcher::uuid(),
                            "customer_id": "customer-123",
                            "assessment_type": "ONBOARDING",
                            "risk_score": Matcher::decimal(),
                            "risk_level": Matcher::regex(r"LOW|MEDIUM|HIGH|CRITICAL", "risk_level"),
                            "factors": Matcher::object(),
                            "recommendations": Matcher::each_like(Matcher::string("recommendation"), 1),
                            "assessed_by": Matcher::uuid(),
                            "assessed_at": Matcher::iso_datetime(),
                            "valid_until": Matcher::iso_datetime(),
                            "status": "COMPLETED"
                        })),
                    },
                },
                ContractInteraction {
                    description: "Get risk assessment by ID".to_string(),
                    given: Some("risk assessment exists with specified ID".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/assessments/assessment-456".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                        ])),
                        body: None,
                        query: None,
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "id": "assessment-456",
                            "customer_id": Matcher::string("customer_id"),
                            "assessment_type": Matcher::regex(r"ONBOARDING|PERIODIC|TRANSACTION_BASED|EVENT_DRIVEN", "assessment_type"),
                            "risk_score": Matcher::decimal(),
                            "risk_level": Matcher::regex(r"LOW|MEDIUM|HIGH|CRITICAL", "risk_level"),
                            "factors": Matcher::object(),
                            "recommendations": Matcher::each_like(Matcher::string("recommendation"), 1),
                            "assessed_by": Matcher::uuid(),
                            "assessed_at": Matcher::iso_datetime(),
                            "valid_until": Matcher::iso_datetime(),
                            "status": "COMPLETED"
                        })),
                    },
                },
            ],
            metadata: ContractMetadata {
                version: "1.0.0".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                tags: vec!["risk".to_string(), "assessment".to_string()],
            },
        }
    }

    fn create_fraud_analysis_contract(&self) -> ServiceContract {
        ServiceContract {
            consumer: "fraud-service".to_string(),
            provider: "analysis-service".to_string(),
            interactions: vec![
                ContractInteraction {
                    description: "Analyze transaction for fraud indicators".to_string(),
                    given: Some("transaction data is available for analysis".to_string()),
                    request: ContractRequest {
                        method: "POST".to_string(),
                        path: "/api/v1/fraud/analyze".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "transaction_id": "txn-789",
                            "customer_id": "customer-123",
                            "amount": 5000.00,
                            "currency": "USD",
                            "merchant": "Online Store XYZ",
                            "location": {
                                "country": "US",
                                "city": "New York",
                                "ip_address": "192.168.1.100"
                            },
                            "device_fingerprint": "device-abc123",
                            "timestamp": "2024-01-15T10:30:00Z"
                        })),
                        query: None,
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "analysis_id": Matcher::uuid(),
                            "transaction_id": "txn-789",
                            "fraud_score": Matcher::decimal(),
                            "risk_level": Matcher::regex(r"LOW|MEDIUM|HIGH|CRITICAL", "risk_level"),
                            "indicators": Matcher::each_like(json!({
                                "type": Matcher::string("indicator_type"),
                                "severity": Matcher::regex(r"LOW|MEDIUM|HIGH", "severity"),
                                "description": Matcher::string("description"),
                                "confidence": Matcher::decimal()
                            }), 0),
                            "recommendation": Matcher::regex(r"APPROVE|REVIEW|BLOCK", "recommendation"),
                            "model_version": Matcher::string("model_version"),
                            "analyzed_at": Matcher::iso_datetime()
                        })),
                    },
                },
                ContractInteraction {
                    description: "Get fraud analysis history for customer".to_string(),
                    given: Some("customer has previous fraud analyses".to_string()),
                    request: ContractRequest {
                        method: "GET".to_string(),
                        path: "/api/v1/fraud/history".to_string(),
                        headers: Some(HashMap::from([
                            ("Authorization".to_string(), "Bearer token".to_string()),
                        ])),
                        body: None,
                        query: Some(HashMap::from([
                            ("customer_id".to_string(), "customer-123".to_string()),
                            ("limit".to_string(), "20".to_string()),
                            ("days".to_string(), "30".to_string()),
                        ])),
                    },
                    response: ContractResponse {
                        status: 200,
                        headers: Some(HashMap::from([
                            ("Content-Type".to_string(), "application/json".to_string()),
                        ])),
                        body: Some(json!({
                            "analyses": Matcher::each_like(json!({
                                "analysis_id": Matcher::uuid(),
                                "transaction_id": Matcher::string("transaction_id"),
                                "fraud_score": Matcher::decimal(),
                                "risk_level": Matcher::regex(r"LOW|MEDIUM|HIGH|CRITICAL", "risk_level"),
                                "recommendation": Matcher::regex(r"APPROVE|REVIEW|BLOCK", "recommendation"),
                                "analyzed_at": Matcher::iso_datetime()
                            }), 1),
                            "total": Matcher::integer(),
                            "customer_risk_profile": {
                                "overall_score": Matcher::decimal(),
                                "trend": Matcher::regex(r"IMPROVING|STABLE|DETERIORATING", "trend"),
                                "last_updated": Matcher::iso_datetime()
                            }
                        })),
                    },
                },
            ],
            metadata: ContractMetadata {
                version: "1.0.0".to_string(),
                created_at: Utc::now(),
                updated_at: Utc::now(),
                tags: vec!["fraud".to_string(), "analysis".to_string()],
            },
        }
    }

    /// Register a service contract
    pub async fn register_contract(&mut self, contract: ServiceContract) -> crate::TestResult<()> {
        let contract_name = format!("{}-{}", contract.consumer, contract.provider);
        self.contracts.insert(contract_name, contract);
        Ok(())
    }

    /// Run all contract tests
    pub async fn run_all_tests(&self) -> crate::TestResult<ContractTestResults> {
        let started_at = Utc::now();
        let mut results = Vec::new();
        let mut total_time = 0;

        for (contract_name, contract) in &self.contracts {
            let result = self.run_contract_test(contract_name, contract).await?;
            total_time += result.execution_time_ms;
            results.push(result);
        }

        let completed_at = Utc::now();

        Ok(ContractTestResults {
            results,
            total_execution_time_ms: total_time,
            started_at,
            completed_at,
        })
    }

    /// Run a specific contract test
    async fn run_contract_test(&self, contract_name: &str, contract: &ServiceContract) -> crate::TestResult<ContractTestResult> {
        let start_time = std::time::Instant::now();
        
        // Create Pact builder
        let mut pact_builder = PactBuilder::new(&contract.consumer, &contract.provider);

        // Add interactions to the pact
        for interaction in &contract.interactions {
            pact_builder = pact_builder.interaction(&interaction.description, |mut i| {
                if let Some(ref given) = interaction.given {
                    i = i.given(given);
                }

                // Set up request
                i = match interaction.request.method.as_str() {
                    "GET" => i.request.get(),
                    "POST" => i.request.post(),
                    "PUT" => i.request.put(),
                    "DELETE" => i.request.delete(),
                    _ => i.request.get(),
                };

                i = i.request.path(&interaction.request.path);

                // Add headers
                if let Some(ref headers) = interaction.request.headers {
                    for (key, value) in headers {
                        i = i.request.header(key, value);
                    }
                }

                // Add query parameters
                if let Some(ref query) = interaction.request.query {
                    for (key, value) in query {
                        i = i.request.query_param(key, value);
                    }
                }

                // Add request body
                if let Some(ref body) = interaction.request.body {
                    i = i.request.json_body(body.clone());
                }

                // Set up response
                i = i.response.status(interaction.response.status);

                // Add response headers
                if let Some(ref headers) = interaction.response.headers {
                    for (key, value) in headers {
                        i = i.response.header(key, value);
                    }
                }

                // Add response body
                if let Some(ref body) = interaction.response.body {
                    i = i.response.json_body(body.clone());
                }

                i
            });
        }

        // Start mock server
        let mock_server = pact_builder.start_mock_server(None);
        let base_url = mock_server.url();

        let mut interactions_passed = 0;
        let mut failed_interactions = Vec::new();

        // Test each interaction
        for interaction in &contract.interactions {
            match self.test_interaction(&base_url, interaction).await {
                Ok(_) => interactions_passed += 1,
                Err(e) => {
                    failed_interactions.push(format!("{}: {}", interaction.description, e));
                }
            }
        }

        let execution_time = start_time.elapsed().as_millis() as u64;
        let passed = failed_interactions.is_empty();

        Ok(ContractTestResult {
            contract_name: contract_name.to_string(),
            consumer: contract.consumer.clone(),
            provider: contract.provider.clone(),
            passed,
            interactions_tested: contract.interactions.len(),
            interactions_passed,
            execution_time_ms: execution_time,
            error_message: if !passed {
                Some(failed_interactions.join("; "))
            } else {
                None
            },
            failed_interactions,
        })
    }

    /// Test a specific interaction
    async fn test_interaction(&self, base_url: &str, interaction: &ContractInteraction) -> crate::TestResult<()> {
        let url = format!("{}{}", base_url, interaction.request.path);
        
        let mut request_builder = match interaction.request.method.as_str() {
            "GET" => self.http_client.get(&url),
            "POST" => self.http_client.post(&url),
            "PUT" => self.http_client.put(&url),
            "DELETE" => self.http_client.delete(&url),
            _ => self.http_client.get(&url),
        };

        // Add headers
        if let Some(ref headers) = interaction.request.headers {
            for (key, value) in headers {
                request_builder = request_builder.header(key, value);
            }
        }

        // Add query parameters
        if let Some(ref query) = interaction.request.query {
            request_builder = request_builder.query(query);
        }

        // Add body
        if let Some(ref body) = interaction.request.body {
            request_builder = request_builder.json(body);
        }

        // Execute request
        let response = request_builder.send().await?;

        // Verify response status
        if response.status().as_u16() != interaction.response.status {
            return Err(format!(
                "Expected status {}, got {}",
                interaction.response.status,
                response.status().as_u16()
            ).into());
        }

        // Additional response verification would go here
        // (headers, body structure, etc.)

        Ok(())
    }
}

impl ContractTestResults {
    pub fn all_passed(&self) -> bool {
        self.results.iter().all(|r| r.passed)
    }

    pub fn total_tests(&self) -> usize {
        self.results.len()
    }

    pub fn passed_tests(&self) -> usize {
        self.results.iter().filter(|r| r.passed).count()
    }

    pub fn failed_tests(&self) -> usize {
        self.results.iter().filter(|r| !r.passed).count()
    }

    pub fn execution_time_ms(&self) -> u64 {
        self.total_execution_time_ms
    }
}

impl Default for ContractTestConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            pact_broker_url: None,
            pact_broker_token: None,
            consumer_version: "1.0.0".to_string(),
            provider_verification_enabled: true,
            mock_server_port_range: (9000, 9100),
            timeout_seconds: 30,
            parallel_execution: true,
        }
    }
}
