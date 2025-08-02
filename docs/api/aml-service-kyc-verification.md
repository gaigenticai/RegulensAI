# AML Service - KYC Verification API

## Endpoint Information

**URL**: `/api/v1/aml/kyc/verify`  
**Method**: `POST`  
**Service**: AML Service  
**Port**: 8080  

## Description

Initiates Know Your Customer (KYC) verification process for a customer. This endpoint performs identity verification, document validation, sanctions screening, and risk assessment as part of the customer onboarding process.

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
```

### Request Body
```json
{
  "customer_id": "uuid",
  "verification_type": "string",
  "documents": [
    {
      "document_type": "string",
      "document_number": "string",
      "issuing_country": "string",
      "expiry_date": "string (ISO 8601)",
      "document_image_url": "string"
    }
  ],
  "personal_information": {
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "string (ISO 8601)",
    "nationality": "string",
    "address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "postal_code": "string",
      "country": "string"
    }
  },
  "verification_level": "string"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_id` | UUID | Yes | Unique identifier for the customer |
| `verification_type` | String | Yes | Type of verification: "INDIVIDUAL", "CORPORATE", "TRUST" |
| `documents` | Array | Yes | Array of identity documents for verification |
| `documents[].document_type` | String | Yes | Type: "PASSPORT", "DRIVERS_LICENSE", "NATIONAL_ID", "UTILITY_BILL" |
| `documents[].document_number` | String | Yes | Document identification number |
| `documents[].issuing_country` | String | Yes | ISO 3166-1 alpha-2 country code |
| `documents[].expiry_date` | String | No | Document expiry date in ISO 8601 format |
| `documents[].document_image_url` | String | Yes | URL to document image for OCR processing |
| `personal_information` | Object | Yes | Customer's personal information |
| `personal_information.first_name` | String | Yes | Customer's first name |
| `personal_information.last_name` | String | Yes | Customer's last name |
| `personal_information.date_of_birth` | String | Yes | Date of birth in ISO 8601 format |
| `personal_information.nationality` | String | Yes | ISO 3166-1 alpha-2 country code |
| `personal_information.address` | Object | Yes | Customer's residential address |
| `verification_level` | String | Yes | Required verification level: "BASIC", "ENHANCED", "SIMPLIFIED" |

## Response Schema

### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "verification_id": "uuid",
    "customer_id": "uuid",
    "status": "string",
    "verification_level": "string",
    "results": {
      "identity_verification": {
        "status": "string",
        "confidence_score": "number",
        "verified_fields": ["string"],
        "failed_fields": ["string"]
      },
      "document_verification": {
        "status": "string",
        "documents_verified": "number",
        "documents_failed": "number",
        "ocr_results": [
          {
            "document_type": "string",
            "extracted_data": "object",
            "confidence_score": "number"
          }
        ]
      },
      "sanctions_screening": {
        "status": "string",
        "matches_found": "number",
        "screening_lists": ["string"],
        "match_details": [
          {
            "list_name": "string",
            "match_score": "number",
            "matched_name": "string"
          }
        ]
      },
      "risk_assessment": {
        "risk_score": "number",
        "risk_level": "string",
        "risk_factors": ["string"]
      }
    },
    "compliance_status": "string",
    "next_review_date": "string (ISO 8601)",
    "created_at": "string (ISO 8601)",
    "completed_at": "string (ISO 8601)"
  },
  "message": "KYC verification completed successfully"
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "Invalid request data",
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

### Error Response (401 Unauthorized)
```json
{
  "success": false,
  "error": "Authentication required"
}
```

### Error Response (403 Forbidden)
```json
{
  "success": false,
  "error": "Insufficient permissions for KYC verification"
}
```

### Error Response (500 Internal Server Error)
```json
{
  "success": false,
  "error": "Internal server error during KYC verification"
}
```

## Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `verification_id` | UUID | Unique identifier for this verification process |
| `status` | String | Verification status: "PENDING", "COMPLETED", "FAILED", "REQUIRES_MANUAL_REVIEW" |
| `results.identity_verification.status` | String | Identity check result: "VERIFIED", "FAILED", "PARTIAL" |
| `results.identity_verification.confidence_score` | Number | Confidence score (0.0-1.0) for identity verification |
| `results.sanctions_screening.status` | String | Screening result: "CLEAR", "MATCH_FOUND", "ERROR" |
| `results.risk_assessment.risk_score` | Number | Calculated risk score (0-100) |
| `results.risk_assessment.risk_level` | String | Risk classification: "LOW", "MEDIUM", "HIGH", "VERY_HIGH" |
| `compliance_status` | String | Overall compliance status: "COMPLIANT", "NON_COMPLIANT", "REQUIRES_REVIEW" |

## Example Usage

### cURL Example
```bash
curl -X POST "https://api.regulateai.com/api/v1/aml/kyc/verify" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Request-ID: req_123456789" \
  -d '{
    "customer_id": "550e8400-e29b-41d4-a716-446655440000",
    "verification_type": "INDIVIDUAL",
    "documents": [
      {
        "document_type": "PASSPORT",
        "document_number": "A12345678",
        "issuing_country": "US",
        "expiry_date": "2030-12-31T00:00:00Z",
        "document_image_url": "https://storage.example.com/docs/passport_123.jpg"
      }
    ],
    "personal_information": {
      "first_name": "John",
      "last_name": "Doe",
      "date_of_birth": "1985-06-15T00:00:00Z",
      "nationality": "US",
      "address": {
        "street": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "US"
      }
    },
    "verification_level": "ENHANCED"
  }'
```

### JavaScript Example
```javascript
const response = await fetch('https://api.regulateai.com/api/v1/aml/kyc/verify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token,
    'X-Request-ID': 'req_' + Date.now()
  },
  body: JSON.stringify({
    customer_id: '550e8400-e29b-41d4-a716-446655440000',
    verification_type: 'INDIVIDUAL',
    documents: [{
      document_type: 'PASSPORT',
      document_number: 'A12345678',
      issuing_country: 'US',
      expiry_date: '2030-12-31T00:00:00Z',
      document_image_url: 'https://storage.example.com/docs/passport_123.jpg'
    }],
    personal_information: {
      first_name: 'John',
      last_name: 'Doe',
      date_of_birth: '1985-06-15T00:00:00Z',
      nationality: 'US',
      address: {
        street: '123 Main Street',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'US'
      }
    },
    verification_level: 'ENHANCED'
  })
});

const result = await response.json();
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per API key
- **Burst Limit**: 10 requests per second
- **Headers**: 
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when rate limit resets (Unix timestamp)

## Error Handling

The API uses standard HTTP status codes and provides detailed error messages:

- **400**: Bad Request - Invalid input data or missing required fields
- **401**: Unauthorized - Invalid or missing authentication token
- **403**: Forbidden - Insufficient permissions
- **429**: Too Many Requests - Rate limit exceeded
- **500**: Internal Server Error - Server-side processing error

## Security Considerations

1. **Data Encryption**: All document images and personal data are encrypted in transit and at rest
2. **Data Retention**: Personal data is retained according to regulatory requirements and purged automatically
3. **Audit Logging**: All KYC verification requests are logged for compliance and audit purposes
4. **Access Control**: Role-based access control ensures only authorized personnel can access KYC data

## Compliance Notes

This endpoint complies with:
- **KYC/AML Regulations**: Meets regulatory requirements for customer identification
- **GDPR**: Implements data protection and privacy requirements
- **SOC 2**: Follows security and availability standards
- **PCI DSS**: Maintains payment card industry security standards

## Related Endpoints

- `GET /api/v1/aml/kyc/verification/{verification_id}` - Get verification status
- `POST /api/v1/aml/kyc/update` - Update customer information
- `GET /api/v1/aml/kyc/customer/{customer_id}` - Get customer KYC status
