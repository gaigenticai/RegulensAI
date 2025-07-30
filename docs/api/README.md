# RegulensAI API Documentation

## 🚀 Overview

**RegulensAI** is an enterprise-grade financial compliance platform providing comprehensive AML/KYC monitoring, regulatory compliance management, and AI-powered risk assessment capabilities.

## 📚 Documentation Resources

### 🌐 Interactive API Documentation
- **[Swagger UI Documentation](./index.html)** - Interactive API explorer with live testing
- **[OpenAPI 3.0 Specification](./openapi_spec.yaml)** - Complete API specification

### 📖 Guides & Examples
- **[API Examples](./examples.md)** - Comprehensive code examples and curl commands
- **[Authentication Guide](#authentication)** - JWT-based authentication flow
- **[Error Handling Guide](#error-handling)** - Structured error responses

## 🎯 Quick Start

### 1. Access Interactive Documentation
Open the [Swagger UI Documentation](./index.html) in your browser for an interactive API explorer.

### 2. Authentication
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@regulens.ai",
    "password": "admin123"
  }'
```

### 3. Use the API
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "X-Tenant-ID: your-tenant-id" \
     "http://localhost:8000/api/v1/dashboard/metrics"
```

## 📋 Table of Contents

- [Core Features](#core-features)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Security](#security)
- [Examples](#examples)

## 🔥 Core Features

- **🔐 Authentication & Authorization**: JWT-based auth with RBAC
- **📊 Compliance Management**: Task tracking and report generation
- **🎓 Training Portal**: Interactive compliance training modules
- **📈 Dashboard & Analytics**: Real-time metrics and KPIs
- **👥 User Management**: Complete user lifecycle management
- **🤖 AI-Powered Insights**: Machine learning-driven analysis
- **🔗 External Integrations**: GRC systems and data providers
- **📱 Multi-channel Notifications**: Email, SMS, and webhook alerts

## Authentication

All API endpoints require authentication using JWT tokens. The platform supports role-based access control (RBAC) with granular permissions.

### Authentication Flow

1. **Login**: POST `/api/v1/auth/login`
2. **Token Refresh**: POST `/api/v1/auth/refresh`
3. **Logout**: POST `/api/v1/auth/logout`

### Headers

```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
X-Tenant-ID: <tenant_uuid>
```

## API Endpoints

### Authentication & User Management

#### POST /api/v1/auth/login
Authenticate user and obtain JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "analyst",
    "permissions": ["compliance.read", "customers.read"]
  }
}
```

#### GET /api/v1/users
List users with filtering and pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50, max: 100)
- `role`: Filter by user role
- `department`: Filter by department
- `is_active`: Filter by active status

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "analyst",
      "department": "compliance",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_login": "2024-01-20T14:15:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3
  }
}
```

### Customer Management

#### GET /api/v1/customers
List customers with advanced filtering.

**Query Parameters:**
- `page`, `limit`: Pagination
- `risk_category`: Filter by risk level (low, medium, high)
- `kyc_status`: Filter by KYC status
- `country`: Filter by country code
- `search`: Search by name or email

#### POST /api/v1/customers
Create a new customer record.

**Request Body:**
```json
{
  "customer_type": "individual",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "date_of_birth": "1985-06-15",
  "country": "US",
  "address": "123 Main St, City, State 12345"
}
```

#### GET /api/v1/customers/{customer_id}/risk-assessment
Get AI-powered risk assessment for a customer.

**Response:**
```json
{
  "customer_id": "uuid",
  "risk_score": 25,
  "risk_category": "low",
  "risk_factors": [
    {
      "factor": "geographic_risk",
      "weight": 0.1,
      "description": "Low-risk jurisdiction"
    }
  ],
  "recommendations": [
    "Standard monitoring procedures",
    "Annual KYC review"
  ],
  "last_updated": "2024-01-20T14:15:00Z"
}
```

### AML/KYC Operations

#### POST /api/v1/aml/screen-customer
Screen customer against sanctions and PEP lists.

**Request Body:**
```json
{
  "customer_id": "uuid",
  "screening_types": ["sanctions", "pep", "adverse_media"]
}
```

#### GET /api/v1/aml/transactions/monitor
Get transaction monitoring results.

**Query Parameters:**
- `start_date`, `end_date`: Date range
- `risk_level`: Filter by risk level
- `status`: Filter by monitoring status

#### POST /api/v1/aml/sar
Create Suspicious Activity Report.

**Request Body:**
```json
{
  "customer_id": "uuid",
  "transaction_ids": ["uuid1", "uuid2"],
  "suspicious_activity_type": "unusual_transaction_pattern",
  "description": "Customer exhibited unusual transaction patterns...",
  "supporting_documentation": ["file_id1", "file_id2"]
}
```

### Compliance Management

#### GET /api/v1/compliance/programs
List compliance programs.

#### POST /api/v1/compliance/programs
Create new compliance program.

#### GET /api/v1/compliance/requirements
List compliance requirements with status tracking.

#### PUT /api/v1/compliance/requirements/{requirement_id}/complete
Mark compliance requirement as complete.

### Reporting & Analytics

#### POST /api/v1/reports/generate
Generate compliance reports.

**Request Body:**
```json
{
  "report_type": "aml_summary",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "format": "pdf",
  "filters": {
    "risk_level": "high",
    "include_charts": true
  }
}
```

#### GET /api/v1/analytics/dashboard
Get dashboard metrics and KPIs.

### AI & Machine Learning

#### POST /api/v1/ai/analyze/risk
Trigger AI risk analysis.

#### GET /api/v1/ai/insights/compliance
Get AI-generated compliance insights.

#### GET /api/v1/ai/predictions/alerts
Get predictive alerts from AI models.

## Data Models

### User Model
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "email": "string",
  "full_name": "string",
  "role": "admin|manager|analyst|viewer",
  "department": "string",
  "permissions": ["string"],
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_login": "datetime"
}
```

### Customer Model
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "customer_type": "individual|corporate",
  "first_name": "string",
  "last_name": "string",
  "email": "string",
  "phone": "string",
  "date_of_birth": "date",
  "country": "string",
  "address": "string",
  "risk_score": "integer",
  "risk_category": "low|medium|high",
  "kyc_status": "pending|compliant|non_compliant",
  "pep_status": "boolean",
  "sanctions_status": "boolean",
  "status": "active|inactive|suspended",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Transaction Model
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "customer_id": "uuid",
  "transaction_type": "wire_transfer|ach|check|cash",
  "amount": "decimal",
  "currency": "string",
  "source_country": "string",
  "destination_country": "string",
  "monitoring_status": "pending|cleared|flagged",
  "risk_score": "integer",
  "suspicious_indicators": ["string"],
  "requires_sar": "boolean",
  "created_at": "datetime"
}
```

## Error Handling

The API uses standard HTTP status codes and returns detailed error information.

### Error Response Format
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid input data",
  "details": {
    "field": "email",
    "value": "invalid-email",
    "validation_rule": "must be valid email format"
  },
  "exception_id": "uuid",
  "timestamp": "2024-01-20T14:15:00Z"
}
```

### Common Error Codes
- `AUTHENTICATION_ERROR`: Invalid credentials or token
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `VALIDATION_ERROR`: Invalid input data
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_SERVER_ERROR`: Server error

## Rate Limiting

API requests are rate limited to ensure fair usage and system stability.

### Default Limits
- **Standard Users**: 100 requests per minute
- **Premium Users**: 500 requests per minute
- **Enterprise Users**: 1000 requests per minute

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642694400
```

## Security

### Data Protection
- All sensitive data is encrypted at rest and in transit
- PII data is automatically encrypted using field-level encryption
- GDPR-compliant data handling and anonymization

### Input Validation
- Comprehensive input validation prevents XSS and SQL injection
- File uploads are scanned for viruses and malicious content
- All user inputs are sanitized and validated

### Audit Logging
- All API calls are logged for audit purposes
- Sensitive operations trigger security alerts
- Comprehensive audit trail for compliance reporting

## Examples

### Complete Customer Onboarding Flow

```python
import requests

# 1. Authenticate
auth_response = requests.post('/api/v1/auth/login', json={
    'email': 'analyst@company.com',
    'password': 'secure_password'
})
token = auth_response.json()['access_token']

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'X-Tenant-ID': 'your-tenant-id'
}

# 2. Create customer
customer_data = {
    'customer_type': 'individual',
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'john.doe@example.com',
    'country': 'US'
}
customer_response = requests.post('/api/v1/customers', 
                                json=customer_data, headers=headers)
customer_id = customer_response.json()['id']

# 3. Screen customer
screening_response = requests.post('/api/v1/aml/screen-customer', 
                                 json={'customer_id': customer_id,
                                      'screening_types': ['sanctions', 'pep']}, 
                                 headers=headers)

# 4. Get risk assessment
risk_response = requests.get(f'/api/v1/customers/{customer_id}/risk-assessment',
                           headers=headers)
```

### Generating Compliance Reports

```python
# Generate monthly AML report
report_request = {
    'report_type': 'aml_summary',
    'start_date': '2024-01-01',
    'end_date': '2024-01-31',
    'format': 'pdf',
    'filters': {
        'include_charts': True,
        'include_details': True
    }
}

report_response = requests.post('/api/v1/reports/generate',
                              json=report_request, headers=headers)
report_id = report_response.json()['report_id']

# Check report status
status_response = requests.get(f'/api/v1/reports/{report_id}/status',
                             headers=headers)
```

## Support

For API support and questions:
- **Documentation**: [https://docs.regulens.ai](https://docs.regulens.ai)
- **Support Email**: support@regulens.ai
- **Developer Portal**: [https://developers.regulens.ai](https://developers.regulens.ai)

## Changelog

### Version 1.0.0 (2024-01-20)
- Initial API release
- Complete authentication and user management
- Customer and transaction management
- AML/KYC screening capabilities
- Compliance program management
- AI-powered risk assessment
- Comprehensive reporting system
