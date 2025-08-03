# Testing Framework API

## Overview
The Testing Framework API provides endpoints for managing and executing property-based tests, contract tests, integration tests, and performance benchmarks.

## Base URL
```
https://api.regulateai.com/v1/testing
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### 1. Execute Property-Based Tests

**POST** `/property-tests/execute`

Executes property-based tests with configurable parameters.

#### Request
```http
POST /v1/testing/property-tests/execute
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "test_suite": "aml_validation",
  "max_test_cases": 1000,
  "max_shrink_iterations": 100,
  "timeout_seconds": 300,
  "properties": [
    {
      "name": "customer_id_validation",
      "description": "Customer ID must be valid UUID",
      "generator": "uuid_generator",
      "property_function": "validate_customer_id"
    },
    {
      "name": "transaction_amount_validation", 
      "description": "Transaction amount must be positive",
      "generator": "amount_generator",
      "property_function": "validate_positive_amount"
    }
  ]
}
```

#### Response
```json
{
  "execution_id": "prop_test_12345",
  "status": "completed",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "results": {
    "total_properties": 2,
    "passed_properties": 2,
    "failed_properties": 0,
    "total_test_cases": 2000,
    "passed_test_cases": 2000,
    "failed_test_cases": 0,
    "shrink_attempts": 0,
    "execution_time_ms": 300000
  },
  "property_results": [
    {
      "property_name": "customer_id_validation",
      "passed": true,
      "test_cases_run": 1000,
      "failures": 0,
      "counterexamples": [],
      "execution_time_ms": 150000
    },
    {
      "property_name": "transaction_amount_validation",
      "passed": true,
      "test_cases_run": 1000,
      "failures": 0,
      "counterexamples": [],
      "execution_time_ms": 150000
    }
  ]
}
```

### 2. Execute Contract Tests

**POST** `/contract-tests/execute`

Executes consumer-driven contract tests against service providers.

#### Request
```http
POST /v1/testing/contract-tests/execute
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "consumer": "aml-frontend",
  "provider": "aml-service",
  "contract_version": "1.0.0",
  "pact_broker_url": "http://localhost:9292",
  "verification_timeout_seconds": 120,
  "interactions": [
    {
      "description": "AML check request",
      "provider_state": "customer exists",
      "request": {
        "method": "POST",
        "path": "/api/v1/aml/check",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "customer_id": "12345",
          "transaction_amount": 10000.0
        }
      },
      "response": {
        "status": 200,
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "risk_score": 25.5,
          "risk_level": "MEDIUM"
        }
      }
    }
  ]
}
```

#### Response
```json
{
  "verification_id": "contract_verify_67890",
  "consumer": "aml-frontend",
  "provider": "aml-service",
  "contract_version": "1.0.0",
  "status": "passed",
  "started_at": "2024-01-15T10:40:00Z",
  "completed_at": "2024-01-15T10:42:00Z",
  "results": {
    "total_interactions": 1,
    "passed_interactions": 1,
    "failed_interactions": 0,
    "execution_time_ms": 120000
  },
  "interaction_results": [
    {
      "description": "AML check request",
      "passed": true,
      "request_matched": true,
      "response_matched": true,
      "execution_time_ms": 120000,
      "errors": []
    }
  ],
  "pact_published": true,
  "pact_url": "http://localhost:9292/pacts/provider/aml-service/consumer/aml-frontend/version/1.0.0"
}
```

### 3. Execute Performance Benchmarks

**POST** `/performance-tests/execute`

Executes performance benchmarks and load tests.

#### Request
```http
POST /v1/testing/performance-tests/execute
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "benchmark_suite": "aml_service_performance",
  "warmup_iterations": 100,
  "measurement_iterations": 1000,
  "concurrent_users": 50,
  "test_duration_seconds": 300,
  "benchmarks": [
    {
      "name": "aml_check_benchmark",
      "endpoint": "/api/v1/aml/check",
      "method": "POST",
      "payload_template": {
        "customer_id": "{{uuid}}",
        "transaction_amount": "{{random_amount}}"
      }
    }
  ],
  "performance_thresholds": {
    "max_response_time_ms": 500,
    "min_throughput_rps": 100,
    "max_error_rate_percent": 1.0
  }
}
```

#### Response
```json
{
  "execution_id": "perf_test_11111",
  "status": "completed",
  "started_at": "2024-01-15T11:00:00Z",
  "completed_at": "2024-01-15T11:05:00Z",
  "results": {
    "total_benchmarks": 1,
    "passed_benchmarks": 1,
    "failed_benchmarks": 0,
    "total_execution_time_ms": 300000
  },
  "benchmark_results": [
    {
      "benchmark_name": "aml_check_benchmark",
      "passed": true,
      "mean_response_time_ms": 125.5,
      "p95_response_time_ms": 320.0,
      "p99_response_time_ms": 450.0,
      "throughput_rps": 156.8,
      "error_rate_percent": 0.2,
      "total_requests": 47040,
      "successful_requests": 46946,
      "failed_requests": 94
    }
  ],
  "load_test_results": [
    {
      "test_name": "aml_service_load_test",
      "concurrent_users": 50,
      "total_requests": 47040,
      "average_response_time_ms": 125.5,
      "throughput_rps": 156.8,
      "error_rate_percent": 0.2,
      "passed": true
    }
  ],
  "system_metrics": {
    "cpu_usage_percent": 45.2,
    "memory_usage_mb": 512,
    "disk_io_mb_per_sec": 25.6,
    "network_io_mb_per_sec": 12.3
  }
}
```

### 4. Get Test Execution Status

**GET** `/executions/{execution_id}/status`

Retrieves the status of a running or completed test execution.

#### Request
```http
GET /v1/testing/executions/prop_test_12345/status
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "execution_id": "prop_test_12345",
  "test_type": "property_based",
  "status": "running",
  "progress_percent": 65.5,
  "started_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "current_phase": "executing_properties",
  "completed_test_cases": 1310,
  "total_test_cases": 2000,
  "failures_so_far": 0
}
```

### 5. Generate Test Data

**POST** `/test-data/generate`

Generates realistic test data using the test factories.

#### Request
```http
POST /v1/testing/test-data/generate
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "data_type": "customer",
  "count": 100,
  "options": {
    "include_high_risk": true,
    "geographic_distribution": ["US", "UK", "DE"],
    "risk_levels": ["LOW", "MEDIUM", "HIGH"]
  }
}
```

#### Response
```json
{
  "generation_id": "gen_22222",
  "data_type": "customer",
  "count": 100,
  "generated_at": "2024-01-15T11:10:00Z",
  "data": [
    {
      "customer_id": "cust_001",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "country": "US",
      "risk_level": "MEDIUM",
      "created_at": "2024-01-10T08:00:00Z"
    }
  ],
  "download_url": "/v1/testing/test-data/download/gen_22222",
  "expires_at": "2024-01-16T11:10:00Z"
}
```

### 6. Get Test Reports

**GET** `/reports`

Retrieves comprehensive test execution reports.

#### Request
```http
GET /v1/testing/reports?start_date=2024-01-14&end_date=2024-01-15&test_type=all
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "report_period": {
    "start_date": "2024-01-14T00:00:00Z",
    "end_date": "2024-01-15T23:59:59Z"
  },
  "summary": {
    "total_executions": 25,
    "passed_executions": 23,
    "failed_executions": 2,
    "success_rate_percent": 92.0,
    "total_test_cases": 50000,
    "total_execution_time_hours": 12.5
  },
  "test_type_breakdown": {
    "property_based": {
      "executions": 10,
      "success_rate": 100.0,
      "avg_execution_time_minutes": 5.2
    },
    "contract_tests": {
      "executions": 8,
      "success_rate": 87.5,
      "avg_execution_time_minutes": 2.1
    },
    "performance_tests": {
      "executions": 7,
      "success_rate": 85.7,
      "avg_execution_time_minutes": 45.3
    }
  },
  "trend_analysis": {
    "success_rate_trend": "stable",
    "execution_time_trend": "improving",
    "test_coverage_trend": "increasing"
  }
}
```

## Error Responses

All endpoints may return the following error format:

```json
{
  "error": {
    "code": "TEST_EXECUTION_FAILED",
    "message": "Property-based test execution failed",
    "details": {
      "property": "customer_id_validation",
      "counterexample": "invalid-uuid-format",
      "shrink_steps": 15
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "execution_id": "prop_test_12345"
  }
}
```

## Rate Limits

- **Test execution endpoints**: 10 requests per minute per API key
- **Status check endpoints**: 100 requests per minute per API key
- **Report endpoints**: 50 requests per minute per API key
- **Test data generation**: 20 requests per minute per API key

## Examples

### Execute Property Tests
```bash
curl -X POST "https://api.regulateai.com/v1/testing/property-tests/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_suite": "aml_validation",
    "max_test_cases": 1000,
    "properties": [
      {
        "name": "customer_id_validation",
        "generator": "uuid_generator",
        "property_function": "validate_customer_id"
      }
    ]
  }'
```

### Check Test Status
```bash
curl -X GET "https://api.regulateai.com/v1/testing/executions/prop_test_12345/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Generate Test Data
```bash
curl -X POST "https://api.regulateai.com/v1/testing/test-data/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data_type": "customer",
    "count": 100,
    "options": {
      "include_high_risk": true
    }
  }'
```
