# AML Service - Transaction Monitoring API

## Endpoint Information

**URL**: `/api/v1/aml/monitoring/transactions`  
**Method**: `POST`  
**Service**: AML Service  
**Port**: 8080  

## Description

Monitors financial transactions in real-time for suspicious activity patterns, money laundering indicators, and regulatory compliance violations. This endpoint provides comprehensive transaction analysis using advanced pattern recognition, behavioral analytics, and regulatory rule engines.

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
X-Real-Time-Processing: <true|false>
```

### Request Body
```json
{
  "transaction_id": "string",
  "customer_id": "string",
  "transaction_details": {
    "amount": "number",
    "currency": "string",
    "transaction_type": "string",
    "transaction_date": "string (ISO 8601)",
    "value_date": "string (ISO 8601)",
    "description": "string",
    "reference_number": "string"
  },
  "parties": {
    "originator": {
      "name": "string",
      "account_number": "string",
      "bank_code": "string",
      "address": "object",
      "identification": "object"
    },
    "beneficiary": {
      "name": "string",
      "account_number": "string",
      "bank_code": "string",
      "address": "object",
      "identification": "object"
    },
    "intermediary_banks": ["object"]
  },
  "geographic_data": {
    "originating_country": "string",
    "destination_country": "string",
    "high_risk_jurisdictions": ["string"],
    "sanctions_jurisdictions": ["string"]
  },
  "channel_information": {
    "channel_type": "string",
    "device_id": "string",
    "ip_address": "string",
    "location": "object",
    "authentication_method": "string"
  },
  "monitoring_parameters": {
    "rule_sets": ["string"],
    "sensitivity_level": "string",
    "bypass_rules": ["string"],
    "custom_thresholds": "object"
  },
  "context_data": {
    "business_relationship": "string",
    "expected_activity": "object",
    "customer_risk_rating": "string",
    "previous_alerts": "number"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_id` | String | Yes | Unique transaction identifier |
| `customer_id` | String | Yes | Customer identifier for relationship analysis |
| `transaction_details.amount` | Number | Yes | Transaction amount in base currency units |
| `transaction_details.currency` | String | Yes | ISO 4217 currency code |
| `transaction_details.transaction_type` | String | Yes | Type: "WIRE", "ACH", "CASH", "CHECK", "CARD", "CRYPTO" |
| `parties.originator` | Object | Yes | Transaction originator information |
| `parties.beneficiary` | Object | Yes | Transaction beneficiary information |
| `geographic_data.originating_country` | String | Yes | ISO 3166-1 alpha-2 country code |
| `geographic_data.destination_country` | String | Yes | ISO 3166-1 alpha-2 country code |
| `monitoring_parameters.rule_sets` | Array | No | Specific rule sets to apply |
| `monitoring_parameters.sensitivity_level` | String | No | Level: "LOW", "MEDIUM", "HIGH", "MAXIMUM" |

## Response Schema

### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "monitoring_id": "uuid",
    "transaction_id": "string",
    "monitoring_status": "string",
    "risk_assessment": {
      "overall_risk_score": "number",
      "risk_level": "string",
      "risk_factors": [
        {
          "factor": "string",
          "score": "number",
          "weight": "number",
          "description": "string"
        }
      ]
    },
    "alerts_generated": [
      {
        "alert_id": "uuid",
        "alert_type": "string",
        "severity": "string",
        "rule_triggered": "string",
        "description": "string",
        "threshold_exceeded": "object"
      }
    ],
    "pattern_analysis": {
      "velocity_analysis": {
        "transactions_24h": "number",
        "amount_24h": "number",
        "velocity_score": "number"
      },
      "behavioral_analysis": {
        "deviation_from_normal": "number",
        "pattern_type": "string",
        "confidence": "number"
      },
      "network_analysis": {
        "connection_strength": "number",
        "suspicious_connections": "number",
        "network_risk_score": "number"
      }
    },
    "regulatory_checks": {
      "sanctions_screening": {
        "status": "string",
        "matches_found": "number",
        "screening_lists": ["string"]
      },
      "pep_screening": {
        "status": "string",
        "matches_found": "number",
        "risk_level": "string"
      },
      "adverse_media": {
        "status": "string",
        "matches_found": "number",
        "severity": "string"
      }
    },
    "compliance_status": {
      "ctr_required": "boolean",
      "sar_required": "boolean",
      "regulatory_reporting": ["string"],
      "hold_required": "boolean"
    },
    "recommendations": [
      {
        "action": "string",
        "priority": "string",
        "description": "string",
        "deadline": "string (ISO 8601)"
      }
    ],
    "processing_metadata": {
      "processing_time_ms": "number",
      "rules_evaluated": "number",
      "data_sources_checked": "number",
      "confidence_level": "number"
    },
    "created_at": "string (ISO 8601)",
    "expires_at": "string (ISO 8601)"
  },
  "message": "Transaction monitoring completed successfully"
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
| `monitoring_id` | UUID | Unique identifier for this monitoring session |
| `monitoring_status` | String | Status: "COMPLETED", "PENDING", "ESCALATED", "CLEARED" |
| `overall_risk_score` | Number | Composite risk score (0-100) |
| `risk_level` | String | Risk classification: "LOW", "MEDIUM", "HIGH", "CRITICAL" |
| `alerts_generated` | Array | List of alerts triggered by this transaction |
| `ctr_required` | Boolean | Whether Currency Transaction Report is required |
| `sar_required` | Boolean | Whether Suspicious Activity Report is required |
| `processing_time_ms` | Number | Processing time in milliseconds |

## Example Usage

### cURL Example
```bash
curl -X POST "https://api.regulateai.com/api/v1/aml/monitoring/transactions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Request-ID: req_aml_monitor_123456" \
  -H "X-Real-Time-Processing: true" \
  -d '{
    "transaction_id": "TXN_2024_08_001234567",
    "customer_id": "CUST_550e8400-e29b-41d4-a716-446655440000",
    "transaction_details": {
      "amount": 25000.00,
      "currency": "USD",
      "transaction_type": "WIRE",
      "transaction_date": "2024-08-01T14:30:00Z",
      "value_date": "2024-08-01T14:30:00Z",
      "description": "Business payment for consulting services",
      "reference_number": "REF_2024_08_001"
    },
    "parties": {
      "originator": {
        "name": "ABC Corporation",
        "account_number": "1234567890",
        "bank_code": "ABCBUS33",
        "address": {
          "street": "123 Business Ave",
          "city": "New York",
          "state": "NY",
          "postal_code": "10001",
          "country": "US"
        }
      },
      "beneficiary": {
        "name": "XYZ Consulting Ltd",
        "account_number": "9876543210",
        "bank_code": "XYZGB2L",
        "address": {
          "street": "456 Consulting St",
          "city": "London",
          "postal_code": "EC1A 1BB",
          "country": "GB"
        }
      }
    },
    "geographic_data": {
      "originating_country": "US",
      "destination_country": "GB",
      "high_risk_jurisdictions": [],
      "sanctions_jurisdictions": []
    },
    "channel_information": {
      "channel_type": "ONLINE_BANKING",
      "device_id": "DEV_ABC123",
      "ip_address": "192.168.1.100",
      "authentication_method": "MFA"
    },
    "monitoring_parameters": {
      "rule_sets": ["STANDARD_AML", "WIRE_TRANSFER", "HIGH_VALUE"],
      "sensitivity_level": "HIGH"
    },
    "context_data": {
      "business_relationship": "EXISTING_CLIENT",
      "customer_risk_rating": "MEDIUM",
      "previous_alerts": 0
    }
  }'
```

### Java Example
```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import com.fasterxml.jackson.databind.ObjectMapper;

public class AMLMonitoring {
    private static final String API_URL = "https://api.regulateai.com/api/v1/aml/monitoring/transactions";
    private static final String TOKEN = "your_jwt_token_here";
    
    public void monitorTransaction() throws Exception {
        HttpClient client = HttpClient.newHttpClient();
        ObjectMapper mapper = new ObjectMapper();
        
        // Create transaction monitoring request
        TransactionMonitoringRequest request = new TransactionMonitoringRequest();
        request.setTransactionId("TXN_JAVA_001");
        request.setCustomerId("CUST_JAVA_001");
        
        TransactionDetails details = new TransactionDetails();
        details.setAmount(15000.00);
        details.setCurrency("EUR");
        details.setTransactionType("SEPA");
        request.setTransactionDetails(details);
        
        String requestBody = mapper.writeValueAsString(request);
        
        HttpRequest httpRequest = HttpRequest.newBuilder()
            .uri(URI.create(API_URL))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer " + TOKEN)
            .header("X-Request-ID", "req_java_aml_001")
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();
            
        HttpResponse<String> response = client.send(httpRequest, 
            HttpResponse.BodyHandlers.ofString());
            
        if (response.statusCode() == 200) {
            TransactionMonitoringResponse result = mapper.readValue(
                response.body(), TransactionMonitoringResponse.class);
            System.out.println("Monitoring ID: " + result.getData().getMonitoringId());
            System.out.println("Risk Level: " + result.getData().getRiskAssessment().getRiskLevel());
        }
    }
}
```

## AML Rule Categories

### Velocity Rules
- **Transaction Frequency**: Unusual number of transactions in time period
- **Amount Velocity**: Rapid accumulation of transaction amounts
- **Cross-Border Velocity**: High frequency of international transfers
- **Account Velocity**: Multiple accounts used in short timeframe

### Pattern Recognition Rules
- **Structuring Detection**: Transactions just below reporting thresholds
- **Round Dollar Amounts**: Suspicious use of round numbers
- **Rapid Movement**: Quick movement of funds through multiple accounts
- **Circular Transfers**: Funds returning to originator through complex paths

### Geographic Risk Rules
- **High-Risk Jurisdictions**: Transactions involving sanctioned countries
- **Tax Haven Routing**: Transactions routed through tax havens
- **Border Proximity**: Transactions near high-risk borders
- **Jurisdiction Hopping**: Multiple jurisdictions in transaction chain

### Behavioral Analysis Rules
- **Deviation from Profile**: Transactions inconsistent with customer profile
- **Time-of-Day Patterns**: Unusual transaction timing
- **Channel Switching**: Rapid changes in transaction channels
- **Dormant Account Activity**: Sudden activity in inactive accounts

## Regulatory Compliance

### BSA/AML (United States)
- **Currency Transaction Reports (CTR)**: Transactions ≥ $10,000
- **Suspicious Activity Reports (SAR)**: Suspicious patterns detected
- **Customer Due Diligence (CDD)**: Enhanced due diligence triggers
- **Beneficial Ownership**: Ultimate beneficial owner identification

### EU Anti-Money Laundering Directives
- **4th AML Directive (4AMLD)**: Risk-based approach requirements
- **5th AML Directive (5AMLD)**: Enhanced transparency measures
- **6th AML Directive (6AMLD)**: Criminal liability provisions
- **Transfer of Funds Regulation**: Wire transfer information requirements

### FATF Recommendations
- **Risk Assessment**: Customer and transaction risk assessment
- **Enhanced Due Diligence**: High-risk customer requirements
- **Suspicious Transaction Reporting**: STR filing requirements
- **Record Keeping**: Transaction record retention requirements

## Performance Specifications

- **Real-Time Processing**: < 500ms for standard transactions
- **Batch Processing**: 100,000+ transactions per hour
- **Rule Evaluation**: 200+ rules evaluated per transaction
- **Accuracy**: 95%+ true positive rate for suspicious activity
- **Availability**: 99.9% uptime with failover capabilities

## Machine Learning Integration

### Behavioral Models
- **Customer Profiling**: Dynamic customer behavior modeling
- **Anomaly Detection**: Unsupervised learning for pattern detection
- **Network Analysis**: Graph-based relationship analysis
- **Predictive Scoring**: Risk prediction based on historical patterns

### Model Performance
- **Training Data**: 10M+ historical transactions
- **Model Accuracy**: 94% precision, 91% recall
- **False Positive Rate**: < 5% for high-confidence alerts
- **Model Updates**: Weekly retraining with new data

## Integration Capabilities

### Core Banking Systems
- **Real-Time Integration**: Direct API integration with core banking
- **Batch Processing**: Scheduled batch transaction processing
- **Event-Driven**: Real-time event processing for immediate alerts
- **Data Synchronization**: Automatic customer and account data sync

### Regulatory Reporting
- **Automated Filing**: Direct submission to regulatory authorities
- **Report Generation**: Standardized regulatory report formats
- **Audit Trail**: Complete audit trail for regulatory examinations
- **Compliance Dashboard**: Real-time compliance status monitoring

## Related Endpoints

- `GET /api/v1/aml/monitoring/transactions/{id}` - Get monitoring results
- `POST /api/v1/aml/monitoring/batch` - Batch transaction monitoring
- `GET /api/v1/aml/alerts` - List generated alerts
- `POST /api/v1/aml/alerts/{id}/investigate` - Start alert investigation
- `GET /api/v1/aml/reports/sar` - Generate SAR reports
- `GET /api/v1/aml/customers/{id}/risk-profile` - Get customer risk profile
