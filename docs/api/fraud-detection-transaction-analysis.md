# Fraud Detection Service - Transaction Analysis API

## Endpoint Information

**URL**: `/api/v1/fraud/analyze/transaction`  
**Method**: `POST`  
**Service**: Fraud Detection Service  
**Port**: 8083  

## Description

Analyzes a transaction in real-time for fraud indicators using machine learning models, rule-based detection, and behavioral analytics. Returns a comprehensive fraud risk assessment with actionable insights.

## Authentication

**Required**: Yes  
**Type**: Bearer Token  
**Header**: `Authorization: Bearer <jwt_token>`

## Request Schema

### Headers
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
X-Request-ID: <unique_request_id>
X-Real-Time: true
```

### Request Body
```json
{
  "transaction_id": "uuid",
  "customer_id": "uuid",
  "transaction_details": {
    "amount": "number",
    "currency": "string",
    "merchant_id": "string",
    "merchant_name": "string",
    "merchant_category": "string",
    "transaction_type": "string",
    "payment_method": "string",
    "card_details": {
      "card_number_hash": "string",
      "card_type": "string",
      "issuing_bank": "string",
      "country_of_issue": "string"
    }
  },
  "location_data": {
    "ip_address": "string",
    "country": "string",
    "city": "string",
    "latitude": "number",
    "longitude": "number",
    "timezone": "string"
  },
  "device_data": {
    "device_fingerprint": "string",
    "user_agent": "string",
    "screen_resolution": "string",
    "browser_language": "string",
    "operating_system": "string"
  },
  "behavioral_data": {
    "session_duration": "number",
    "pages_visited": "number",
    "typing_patterns": "object",
    "mouse_movements": "object"
  },
  "timestamp": "string (ISO 8601)"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_id` | UUID | Yes | Unique identifier for the transaction |
| `customer_id` | UUID | Yes | Unique identifier for the customer |
| `transaction_details.amount` | Number | Yes | Transaction amount in base currency units |
| `transaction_details.currency` | String | Yes | ISO 4217 currency code |
| `transaction_details.merchant_id` | String | Yes | Unique merchant identifier |
| `transaction_details.merchant_name` | String | Yes | Merchant display name |
| `transaction_details.merchant_category` | String | Yes | Merchant category code (MCC) |
| `transaction_details.transaction_type` | String | Yes | Type: "PURCHASE", "WITHDRAWAL", "TRANSFER", "REFUND" |
| `transaction_details.payment_method` | String | Yes | Method: "CARD", "BANK_TRANSFER", "DIGITAL_WALLET", "CRYPTO" |
| `location_data.ip_address` | String | Yes | Client IP address (anonymized) |
| `location_data.country` | String | Yes | ISO 3166-1 alpha-2 country code |
| `device_data.device_fingerprint` | String | Yes | Unique device identifier hash |
| `behavioral_data` | Object | No | Optional behavioral analytics data |
| `timestamp` | String | Yes | Transaction timestamp in ISO 8601 format |

## Response Schema

### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "transaction_id": "uuid",
    "analysis_id": "uuid",
    "fraud_assessment": {
      "overall_risk_score": "number",
      "risk_level": "string",
      "is_fraud": "boolean",
      "confidence": "number",
      "recommendation": "string"
    },
    "ml_analysis": {
      "model_version": "string",
      "fraud_probability": "number",
      "feature_importance": [
        {
          "feature": "string",
          "importance": "number",
          "value": "string"
        }
      ]
    },
    "rule_analysis": {
      "triggered_rules": [
        {
          "rule_id": "uuid",
          "rule_name": "string",
          "severity": "string",
          "description": "string"
        }
      ],
      "rule_score": "number"
    },
    "behavioral_analysis": {
      "velocity_check": {
        "transactions_24h": "number",
        "amount_24h": "number",
        "velocity_score": "number"
      },
      "pattern_analysis": {
        "deviation_score": "number",
        "unusual_patterns": ["string"]
      }
    },
    "network_analysis": {
      "device_risk_score": "number",
      "location_risk_score": "number",
      "network_connections": "number",
      "suspicious_associations": "number"
    },
    "alerts_generated": [
      {
        "alert_id": "uuid",
        "alert_type": "string",
        "severity": "string",
        "message": "string"
      }
    ],
    "processing_time_ms": "number",
    "analyzed_at": "string (ISO 8601)"
  },
  "message": "Transaction analysis completed successfully"
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "Invalid transaction data",
  "details": {
    "field_errors": [
      {
        "field": "string",
        "message": "string"
      }
    ]
  }
}
```

## Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `analysis_id` | UUID | Unique identifier for this analysis |
| `fraud_assessment.overall_risk_score` | Number | Combined risk score (0-100) |
| `fraud_assessment.risk_level` | String | Risk classification: "LOW", "MEDIUM", "HIGH", "CRITICAL" |
| `fraud_assessment.is_fraud` | Boolean | Binary fraud determination |
| `fraud_assessment.confidence` | Number | Model confidence (0.0-1.0) |
| `fraud_assessment.recommendation` | String | Action: "APPROVE", "REVIEW", "DECLINE", "CHALLENGE" |
| `ml_analysis.fraud_probability` | Number | ML model fraud probability (0.0-1.0) |
| `rule_analysis.triggered_rules` | Array | List of triggered fraud rules |
| `behavioral_analysis.velocity_check` | Object | Transaction velocity analysis |
| `network_analysis.device_risk_score` | Number | Device-based risk score (0-100) |
| `processing_time_ms` | Number | Analysis processing time in milliseconds |

## Example Usage

### cURL Example
```bash
curl -X POST "https://api.regulateai.com/api/v1/fraud/analyze/transaction" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Request-ID: req_fraud_123456" \
  -H "X-Real-Time: true" \
  -d '{
    "transaction_id": "txn_550e8400-e29b-41d4-a716-446655440000",
    "customer_id": "cust_660f9511-f3ac-52e5-b827-557766551111",
    "transaction_details": {
      "amount": 2500.00,
      "currency": "USD",
      "merchant_id": "merch_12345",
      "merchant_name": "Online Electronics Store",
      "merchant_category": "5732",
      "transaction_type": "PURCHASE",
      "payment_method": "CARD",
      "card_details": {
        "card_number_hash": "sha256_hash_of_card",
        "card_type": "VISA",
        "issuing_bank": "Chase Bank",
        "country_of_issue": "US"
      }
    },
    "location_data": {
      "ip_address": "192.168.1.100",
      "country": "US",
      "city": "New York",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "timezone": "America/New_York"
    },
    "device_data": {
      "device_fingerprint": "fp_abc123def456",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "screen_resolution": "1920x1080",
      "browser_language": "en-US",
      "operating_system": "Windows 10"
    },
    "timestamp": "2024-01-15T14:30:00Z"
  }'
```

### Python Example
```python
import requests
import json

url = "https://api.regulateai.com/api/v1/fraud/analyze/transaction"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + token,
    "X-Request-ID": "req_fraud_123456",
    "X-Real-Time": "true"
}

payload = {
    "transaction_id": "txn_550e8400-e29b-41d4-a716-446655440000",
    "customer_id": "cust_660f9511-f3ac-52e5-b827-557766551111",
    "transaction_details": {
        "amount": 2500.00,
        "currency": "USD",
        "merchant_id": "merch_12345",
        "merchant_name": "Online Electronics Store",
        "merchant_category": "5732",
        "transaction_type": "PURCHASE",
        "payment_method": "CARD"
    },
    "location_data": {
        "ip_address": "192.168.1.100",
        "country": "US",
        "city": "New York"
    },
    "device_data": {
        "device_fingerprint": "fp_abc123def456",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    },
    "timestamp": "2024-01-15T14:30:00Z"
}

response = requests.post(url, headers=headers, json=payload)
result = response.json()

if result["success"]:
    risk_score = result["data"]["fraud_assessment"]["overall_risk_score"]
    recommendation = result["data"]["fraud_assessment"]["recommendation"]
    print(f"Risk Score: {risk_score}, Recommendation: {recommendation}")
```

## Rate Limiting

- **Rate Limit**: 1000 requests per minute per API key
- **Burst Limit**: 50 requests per second
- **Real-time Priority**: Requests with `X-Real-Time: true` header get priority processing

## Performance SLA

- **Response Time**: < 100ms for 95% of requests
- **Availability**: 99.9% uptime
- **Throughput**: Up to 10,000 transactions per second

## Security Features

1. **Data Privacy**: All sensitive data is hashed or encrypted
2. **Audit Trail**: Complete audit log of all analysis requests
3. **Model Security**: ML models are protected against adversarial attacks
4. **Access Control**: Role-based permissions for fraud analysis

## Machine Learning Models

The service uses multiple ML models:
- **Gradient Boosting**: Primary fraud detection model
- **Neural Networks**: Deep learning for pattern recognition
- **Ensemble Methods**: Combines multiple model predictions
- **Anomaly Detection**: Identifies unusual transaction patterns

## Compliance

- **PCI DSS**: Level 1 compliance for payment card data
- **GDPR**: Privacy-by-design implementation
- **SOX**: Financial reporting compliance
- **Regional Regulations**: Supports local fraud prevention requirements

## Related Endpoints

- `GET /api/v1/fraud/analysis/{analysis_id}` - Get analysis details
- `POST /api/v1/fraud/feedback` - Provide fraud feedback for model training
- `GET /api/v1/fraud/customer/{customer_id}/risk-profile` - Get customer risk profile
- `POST /api/v1/fraud/rules/evaluate` - Test fraud rules against transaction
