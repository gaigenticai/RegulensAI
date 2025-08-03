# WAF Management API

## Overview
The Web Application Firewall (WAF) Management API provides endpoints for configuring, monitoring, and managing WAF rules and policies.

## Base URL
```
https://api.regulateai.com/v1/security/waf
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### 1. Get WAF Status

**GET** `/status`

Returns the current status and configuration of the WAF.

#### Request
```http
GET /v1/security/waf/status
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "status": "active",
  "enabled": true,
  "block_mode": true,
  "owasp_core_rules_enabled": true,
  "sql_injection_protection": true,
  "xss_protection": true,
  "total_rules": 1247,
  "active_rules": 1198,
  "last_updated": "2024-01-15T10:30:00Z",
  "statistics": {
    "requests_processed": 125000,
    "requests_blocked": 1250,
    "block_rate": 1.0,
    "top_blocked_attacks": [
      {
        "type": "SQL_INJECTION",
        "count": 450,
        "percentage": 36.0
      },
      {
        "type": "XSS",
        "count": 380,
        "percentage": 30.4
      },
      {
        "type": "PATH_TRAVERSAL",
        "count": 220,
        "percentage": 17.6
      }
    ]
  }
}
```

#### Status Codes
- `200 OK` - WAF status retrieved successfully
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 2. Update WAF Configuration

**PUT** `/config`

Updates the WAF configuration settings.

#### Request
```http
PUT /v1/security/waf/config
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "enabled": true,
  "block_mode": true,
  "owasp_core_rules_enabled": true,
  "sql_injection_protection": true,
  "xss_protection": true,
  "custom_rules_enabled": true,
  "log_level": "INFO",
  "rate_limit_enabled": true,
  "rate_limit_threshold": 1000
}
```

#### Request Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | Enable/disable WAF |
| `block_mode` | boolean | Yes | Block malicious requests (true) or log only (false) |
| `owasp_core_rules_enabled` | boolean | Yes | Enable OWASP Core Rule Set |
| `sql_injection_protection` | boolean | Yes | Enable SQL injection protection |
| `xss_protection` | boolean | Yes | Enable XSS protection |
| `custom_rules_enabled` | boolean | No | Enable custom rules |
| `log_level` | string | No | Logging level: DEBUG, INFO, WARN, ERROR |
| `rate_limit_enabled` | boolean | No | Enable rate limiting |
| `rate_limit_threshold` | integer | No | Rate limit threshold per minute |

#### Response
```json
{
  "success": true,
  "message": "WAF configuration updated successfully",
  "config": {
    "enabled": true,
    "block_mode": true,
    "owasp_core_rules_enabled": true,
    "sql_injection_protection": true,
    "xss_protection": true,
    "custom_rules_enabled": true,
    "log_level": "INFO",
    "rate_limit_enabled": true,
    "rate_limit_threshold": 1000,
    "updated_at": "2024-01-15T10:35:00Z"
  }
}
```

#### Status Codes
- `200 OK` - Configuration updated successfully
- `400 Bad Request` - Invalid configuration parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

### 3. Get WAF Rules

**GET** `/rules`

Retrieves the list of active WAF rules.

#### Request
```http
GET /v1/security/waf/rules?page=1&limit=50&category=sql_injection
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `limit` | integer | No | Items per page (default: 50, max: 100) |
| `category` | string | No | Filter by rule category |
| `enabled` | boolean | No | Filter by enabled status |
| `severity` | string | No | Filter by severity: LOW, MEDIUM, HIGH, CRITICAL |

#### Response
```json
{
  "rules": [
    {
      "id": "rule_001",
      "name": "SQL Injection Detection",
      "category": "sql_injection",
      "severity": "HIGH",
      "enabled": true,
      "pattern": "(?i)(union|select|insert|delete|update|drop|create|alter)\\s",
      "action": "BLOCK",
      "description": "Detects common SQL injection patterns",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-10T15:30:00Z",
      "hit_count": 450,
      "last_triggered": "2024-01-15T09:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1247,
    "total_pages": 25
  }
}
```

#### Status Codes
- `200 OK` - Rules retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 4. Create Custom WAF Rule

**POST** `/rules`

Creates a new custom WAF rule.

#### Request
```http
POST /v1/security/waf/rules
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "Custom API Rate Limit",
  "category": "rate_limiting",
  "severity": "MEDIUM",
  "pattern": "^/api/v1/sensitive-endpoint",
  "action": "RATE_LIMIT",
  "description": "Rate limit sensitive API endpoint",
  "enabled": true,
  "rate_limit": {
    "requests_per_minute": 10,
    "burst_size": 2
  }
}
```

#### Request Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Rule name (max 100 chars) |
| `category` | string | Yes | Rule category |
| `severity` | string | Yes | Severity: LOW, MEDIUM, HIGH, CRITICAL |
| `pattern` | string | Yes | Regex pattern to match |
| `action` | string | Yes | Action: BLOCK, LOG, RATE_LIMIT |
| `description` | string | No | Rule description |
| `enabled` | boolean | No | Enable rule (default: true) |
| `rate_limit` | object | No | Rate limit configuration (if action is RATE_LIMIT) |

#### Response
```json
{
  "success": true,
  "message": "WAF rule created successfully",
  "rule": {
    "id": "rule_custom_001",
    "name": "Custom API Rate Limit",
    "category": "rate_limiting",
    "severity": "MEDIUM",
    "pattern": "^/api/v1/sensitive-endpoint",
    "action": "RATE_LIMIT",
    "description": "Rate limit sensitive API endpoint",
    "enabled": true,
    "created_at": "2024-01-15T10:40:00Z",
    "updated_at": "2024-01-15T10:40:00Z",
    "hit_count": 0,
    "rate_limit": {
      "requests_per_minute": 10,
      "burst_size": 2
    }
  }
}
```

#### Status Codes
- `201 Created` - Rule created successfully
- `400 Bad Request` - Invalid rule parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `409 Conflict` - Rule with same name already exists
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

### 5. Get WAF Logs

**GET** `/logs`

Retrieves WAF security logs and blocked requests.

#### Request
```http
GET /v1/security/waf/logs?start_date=2024-01-14&end_date=2024-01-15&action=BLOCK&limit=100
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | No | Start date (YYYY-MM-DD) |
| `end_date` | string | No | End date (YYYY-MM-DD) |
| `action` | string | No | Filter by action: BLOCK, LOG, RATE_LIMIT |
| `ip_address` | string | No | Filter by IP address |
| `rule_id` | string | No | Filter by rule ID |
| `severity` | string | No | Filter by severity |
| `limit` | integer | No | Items per page (default: 50, max: 1000) |
| `offset` | integer | No | Offset for pagination |

#### Response
```json
{
  "logs": [
    {
      "id": "log_001",
      "timestamp": "2024-01-15T10:30:15Z",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "method": "POST",
      "path": "/api/login",
      "rule_id": "rule_001",
      "rule_name": "SQL Injection Detection",
      "action": "BLOCK",
      "severity": "HIGH",
      "threat_score": 0.95,
      "request_body": "username=admin' OR '1'='1&password=test",
      "blocked_reason": "SQL injection pattern detected",
      "geolocation": {
        "country": "US",
        "city": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060
      }
    }
  ],
  "pagination": {
    "limit": 100,
    "offset": 0,
    "total": 1250
  },
  "summary": {
    "total_events": 1250,
    "blocked_requests": 1250,
    "top_attack_types": [
      {
        "type": "SQL_INJECTION",
        "count": 450
      },
      {
        "type": "XSS",
        "count": 380
      }
    ]
  }
}
```

#### Status Codes
- `200 OK` - Logs retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

## Error Responses

All endpoints may return the following error format:

```json
{
  "error": {
    "code": "WAF_CONFIG_ERROR",
    "message": "Invalid WAF configuration parameter",
    "details": {
      "field": "rate_limit_threshold",
      "reason": "Value must be between 1 and 10000"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_12345"
  }
}
```

## Rate Limits

- **Standard endpoints**: 1000 requests per minute per API key
- **Log endpoints**: 100 requests per minute per API key
- **Configuration endpoints**: 10 requests per minute per API key

## Examples

### Enable WAF Protection
```bash
curl -X PUT "https://api.regulateai.com/v1/security/waf/config" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "block_mode": true,
    "owasp_core_rules_enabled": true,
    "sql_injection_protection": true,
    "xss_protection": true
  }'
```

### Get Recent Security Logs
```bash
curl -X GET "https://api.regulateai.com/v1/security/waf/logs?limit=10&action=BLOCK" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Custom Rule
```bash
curl -X POST "https://api.regulateai.com/v1/security/waf/rules" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block Suspicious User Agents",
    "category": "user_agent",
    "severity": "MEDIUM",
    "pattern": "(bot|crawler|scanner)",
    "action": "BLOCK",
    "description": "Block requests from suspicious user agents"
  }'
```
