# Business Metrics API

## Overview
The Business Metrics API provides endpoints for collecting, analyzing, and reporting business KPIs, compliance metrics, risk assessments, and operational health data.

## Base URL
```
https://api.regulateai.com/v1/metrics
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### 1. Get Business KPIs

**GET** `/business/kpis`

Returns current business key performance indicators.

#### Request
```http
GET /v1/metrics/business/kpis?category=revenue&period=30d
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by KPI category: revenue, customer, transaction, compliance, efficiency |
| `period` | string | No | Time period: 1d, 7d, 30d, 90d, 1y |
| `include_trends` | boolean | No | Include trend analysis (default: true) |

#### Response
```json
{
  "kpis": [
    {
      "name": "Total Revenue",
      "value": 2450000.00,
      "unit": "USD",
      "target": 3000000.00,
      "trend": "UP",
      "category": "REVENUE",
      "last_updated": "2024-01-15T10:30:00Z",
      "description": "Total revenue generated across all services",
      "change_percentage": 12.5,
      "change_period": "30d"
    },
    {
      "name": "Monthly Recurring Revenue",
      "value": 245000.00,
      "unit": "USD",
      "target": 300000.00,
      "trend": "UP",
      "category": "REVENUE",
      "last_updated": "2024-01-15T10:30:00Z",
      "description": "Monthly recurring revenue from subscriptions",
      "change_percentage": 8.3,
      "change_period": "30d"
    },
    {
      "name": "Total Customers",
      "value": 1855.0,
      "unit": "count",
      "target": 2500.0,
      "trend": "UP",
      "category": "CUSTOMER",
      "last_updated": "2024-01-15T10:30:00Z",
      "description": "Total number of active customers",
      "change_percentage": 15.2,
      "change_period": "30d"
    },
    {
      "name": "Customer Churn Rate",
      "value": 3.5,
      "unit": "percentage",
      "target": 5.0,
      "trend": "DOWN",
      "category": "CUSTOMER",
      "last_updated": "2024-01-15T10:30:00Z",
      "description": "Percentage of customers who churned",
      "change_percentage": -12.5,
      "change_period": "30d"
    }
  ],
  "summary": {
    "total_kpis": 15,
    "kpis_on_target": 12,
    "kpis_above_target": 8,
    "kpis_below_target": 4,
    "overall_performance_score": 85.2
  },
  "period": "30d",
  "generated_at": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - KPIs retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 2. Get Compliance Status

**GET** `/compliance/status`

Returns current compliance metrics and status across all regulations.

#### Request
```http
GET /v1/metrics/compliance/status?regulation=AML&include_violations=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `regulation` | string | No | Filter by regulation: AML, KYC, GDPR, SOX, PCI_DSS |
| `include_violations` | boolean | No | Include violation details (default: false) |
| `period` | string | No | Time period for metrics (default: 30d) |

#### Response
```json
{
  "overall_score": 95.2,
  "compliance_metrics": {
    "aml_compliance": 98.1,
    "kyc_compliance": 96.5,
    "gdpr_compliance": 94.2,
    "sox_compliance": 92.8,
    "pci_dss_compliance": 97.3
  },
  "violations": {
    "total_count": 3,
    "critical_count": 0,
    "high_count": 1,
    "medium_count": 2,
    "low_count": 0,
    "recent_violations": [
      {
        "id": "viol_001",
        "regulation": "GDPR",
        "severity": "HIGH",
        "description": "Data retention period exceeded for inactive customer",
        "detected_at": "2024-01-14T15:30:00Z",
        "status": "REMEDIATED",
        "remediated_at": "2024-01-14T16:45:00Z"
      }
    ]
  },
  "pending_reviews": 5,
  "compliance_checks_completed": 15420,
  "compliance_checks_passed": 14687,
  "pass_rate": 95.2,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Compliance status retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 3. Get Risk Levels

**GET** `/risk/levels`

Returns current risk assessment metrics and distribution.

#### Request
```http
GET /v1/metrics/risk/levels?include_distribution=true&period=7d
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "overall_risk_score": 25.8,
  "risk_trend": "STABLE",
  "customer_risk_distribution": {
    "LOW": 1391,
    "MEDIUM": 371,
    "HIGH": 74,
    "CRITICAL": 19
  },
  "transaction_risk_distribution": {
    "LOW": 106250,
    "MEDIUM": 15000,
    "HIGH": 3125,
    "CRITICAL": 625
  },
  "high_risk_alerts": 17,
  "risk_assessments_completed": 2450,
  "risk_assessments_pending": 125,
  "top_risk_factors": [
    {
      "factor": "Geographic Risk",
      "average_score": 35.2,
      "impact": "HIGH"
    },
    {
      "factor": "Transaction Volume",
      "average_score": 28.7,
      "impact": "MEDIUM"
    },
    {
      "factor": "Customer Profile",
      "average_score": 22.1,
      "impact": "MEDIUM"
    }
  ],
  "period": "7d",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Risk levels retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 4. Get Fraud Detection Stats

**GET** `/fraud/stats`

Returns fraud detection performance metrics and statistics.

#### Request
```http
GET /v1/metrics/fraud/stats?period=30d&include_model_performance=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "detection_rate": 98.5,
  "false_positive_rate": 2.1,
  "blocked_transactions": 125,
  "prevented_loss_amount": 250000.00,
  "model_accuracy": 96.8,
  "alerts_generated": 45,
  "model_performance": {
    "precision": 0.968,
    "recall": 0.985,
    "f1_score": 0.976,
    "auc_roc": 0.992,
    "model_version": "v2.1.0",
    "last_trained": "2024-01-10T08:00:00Z"
  },
  "fraud_patterns": [
    {
      "pattern": "Unusual transaction timing",
      "frequency": 35,
      "severity": "MEDIUM"
    },
    {
      "pattern": "Geographic anomaly",
      "frequency": 28,
      "severity": "HIGH"
    },
    {
      "pattern": "Amount pattern deviation",
      "frequency": 22,
      "severity": "MEDIUM"
    }
  ],
  "period": "30d",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Fraud stats retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 5. Get Operational Health

**GET** `/operational/health`

Returns system operational health and performance metrics.

#### Request
```http
GET /v1/metrics/operational/health?include_services=true
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "system_uptime": 99.95,
  "response_time_avg": 125.5,
  "error_rate": 0.05,
  "throughput": 1250.0,
  "resource_utilization": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 35.1,
    "network_usage": 28.5
  },
  "service_health": {
    "aml-service": {
      "status": "HEALTHY",
      "uptime": 99.98,
      "response_time": 98.5,
      "error_rate": 0.02,
      "last_health_check": "2024-01-15T10:29:00Z"
    },
    "compliance-service": {
      "status": "HEALTHY",
      "uptime": 99.95,
      "response_time": 145.2,
      "error_rate": 0.05,
      "last_health_check": "2024-01-15T10:29:00Z"
    },
    "risk-service": {
      "status": "HEALTHY",
      "uptime": 99.92,
      "response_time": 156.8,
      "error_rate": 0.08,
      "last_health_check": "2024-01-15T10:29:00Z"
    }
  },
  "alerts": {
    "active_alerts": 2,
    "critical_alerts": 0,
    "warning_alerts": 2
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Operational health retrieved successfully
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 6. Record Business Event

**POST** `/business/events`

Records a business event for metrics tracking.

#### Request
```http
POST /v1/metrics/business/events
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "event_type": "TRANSACTION_COMPLETED",
  "customer_id": "customer_12345",
  "transaction_id": "txn_67890",
  "amount": 1500.00,
  "currency": "USD",
  "processing_time_ms": 245,
  "metadata": {
    "channel": "API",
    "risk_score": 15.2,
    "compliance_checks_passed": true
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Request Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | Yes | Type of business event |
| `customer_id` | string | No | Associated customer ID |
| `transaction_id` | string | No | Associated transaction ID |
| `amount` | number | No | Monetary amount |
| `currency` | string | No | Currency code |
| `processing_time_ms` | number | No | Processing time in milliseconds |
| `metadata` | object | No | Additional event metadata |
| `timestamp` | string | No | Event timestamp (ISO 8601) |

#### Response
```json
{
  "success": true,
  "message": "Business event recorded successfully",
  "event_id": "event_12345",
  "event_type": "TRANSACTION_COMPLETED",
  "recorded_at": "2024-01-15T10:30:15Z",
  "metrics_updated": [
    "total_transaction_volume",
    "transaction_count",
    "average_processing_time",
    "revenue_metrics"
  ]
}
```

#### Status Codes
- `201 Created` - Event recorded successfully
- `400 Bad Request` - Invalid event data
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

### 7. Get Metrics Summary

**GET** `/summary`

Returns a comprehensive summary of all metrics categories.

#### Request
```http
GET /v1/metrics/summary?period=30d
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "business_kpis": [
    {
      "name": "Total Revenue",
      "value": 2450000.00,
      "unit": "USD",
      "trend": "UP"
    }
  ],
  "compliance_status": {
    "overall_score": 95.2,
    "violations_count": 3,
    "pending_reviews": 5
  },
  "risk_levels": {
    "overall_risk_score": 25.8,
    "high_risk_alerts": 17,
    "risk_trend": "STABLE"
  },
  "fraud_detection_stats": {
    "detection_rate": 98.5,
    "blocked_transactions": 125,
    "prevented_loss_amount": 250000.00
  },
  "operational_health": {
    "system_uptime": 99.95,
    "response_time_avg": 125.5,
    "error_rate": 0.05
  },
  "sla_compliance": {
    "overall_sla_score": 99.2,
    "sla_violations": 2,
    "sla_credits_issued": 150.0
  },
  "period": "30d",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Metrics summary retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

## Error Responses

```json
{
  "error": {
    "code": "METRICS_PERIOD_INVALID",
    "message": "Invalid time period specified",
    "details": {
      "period": "invalid_period",
      "valid_periods": ["1d", "7d", "30d", "90d", "1y"]
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_metrics_12345"
  }
}
```

## Rate Limits

- **Read operations**: 1000 requests per minute per API key
- **Event recording**: 5000 requests per minute per API key
- **Summary endpoints**: 100 requests per minute per API key

## Examples

### Get Revenue KPIs
```bash
curl -X GET "https://api.regulateai.com/v1/metrics/business/kpis?category=revenue&period=30d" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Record Transaction Event
```bash
curl -X POST "https://api.regulateai.com/v1/metrics/business/events" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "TRANSACTION_COMPLETED",
    "customer_id": "customer_12345",
    "amount": 1500.00,
    "currency": "USD",
    "processing_time_ms": 245
  }'
```

### Get Compliance Status
```bash
curl -X GET "https://api.regulateai.com/v1/metrics/compliance/status?include_violations=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```
