# RegulensAI API Examples

This document provides comprehensive examples for using the RegulensAI API.

## Table of Contents

- [Authentication](#authentication)
- [User Management](#user-management)
- [Compliance Management](#compliance-management)
- [Training Portal](#training-portal)
- [Dashboard & Analytics](#dashboard--analytics)
- [Error Handling](#error-handling)

## Authentication

### Login

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@regulens.ai",
    "password": "admin123",
    "remember_me": false
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "admin@regulens.ai",
    "full_name": "System Administrator",
    "role": "admin"
  }
}
```

### Get Current User Profile

```bash
# Get current user information
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Refresh Token

```bash
# Refresh access token
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## User Management

### Get Users List

```bash
# Get paginated list of users
curl -X GET "http://localhost:8000/api/v1/users?page=1&size=20&role=analyst" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id"
```

### Create New User

```bash
# Create a new user
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@company.com",
    "full_name": "John Doe",
    "role": "analyst",
    "department": "Compliance",
    "password": "SecurePassword123!",
    "permissions": ["compliance.read", "reports.read"]
  }'
```

### Update User

```bash
# Update user information
curl -X PUT "http://localhost:8000/api/v1/users/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Smith",
    "department": "Risk Management",
    "is_active": true
  }'
```

## Compliance Management

### Get Compliance Tasks

```bash
# Get compliance tasks with filtering
curl -X GET "http://localhost:8000/api/v1/compliance/tasks?status=pending&priority=high" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id"
```

### Create Compliance Task

```bash
# Create a new compliance task
curl -X POST "http://localhost:8000/api/v1/compliance/tasks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q3 AML Review",
    "description": "Quarterly Anti-Money Laundering compliance review",
    "priority": "high",
    "due_date": "2024-09-30",
    "assigned_to": "123e4567-e89b-12d3-a456-426614174000",
    "category": "AML",
    "tags": ["quarterly", "review", "aml"]
  }'
```

### Generate Compliance Report

```bash
# Generate a compliance report
curl -X POST "http://localhost:8000/api/v1/compliance/reports" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "comprehensive",
    "date_from": "2024-01-01",
    "date_to": "2024-06-30",
    "format": "pdf",
    "filters": {
      "departments": ["Compliance", "Risk Management"],
      "risk_levels": ["medium", "high"]
    }
  }'
```

## Training Portal

### Get Training Modules

```bash
# Get available training modules
curl -X GET "http://localhost:8000/api/v1/training/modules?category=AML&difficulty_level=intermediate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id"
```

### Create Training Module

```bash
# Create a new training module
curl -X POST "http://localhost:8000/api/v1/training/modules" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "module_code": "AML-ADV-001",
    "title": "Advanced AML Techniques",
    "description": "Advanced anti-money laundering detection and prevention techniques",
    "category": "AML",
    "difficulty_level": "advanced",
    "estimated_duration_minutes": 120,
    "prerequisites": ["AML-BAS-001", "AML-INT-001"],
    "learning_objectives": [
      "Understand complex AML patterns",
      "Implement advanced detection algorithms",
      "Analyze suspicious transaction networks"
    ],
    "content_type": "interactive"
  }'
```

### Get Training Progress

```bash
# Get user's training progress
curl -X GET "http://localhost:8000/api/v1/training/progress" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id"
```

## Dashboard & Analytics

### Get Dashboard Metrics

```bash
# Get dashboard KPIs and metrics
curl -X GET "http://localhost:8000/api/v1/dashboard/metrics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id"
```

**Response:**
```json
{
  "compliance_score": 94.2,
  "active_alerts": 12,
  "completed_training": 87.5,
  "system_health": 99.1,
  "total_users": 156,
  "pending_tasks": 23,
  "recent_reports": 8,
  "risk_score": 15.3
}
```

### Get Recent Alerts

```bash
# Get recent system alerts
curl -X GET "http://localhost:8000/api/v1/dashboard/alerts?limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id"
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "type": "https://regulens.ai/errors/bad-request",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid input parameters: email format is invalid",
  "instance": "/api/v1/users",
  "timestamp": "2024-01-29T10:30:00Z",
  "trace_id": "abc123def456"
}
```

#### 401 Unauthorized
```json
{
  "type": "https://regulens.ai/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Invalid or expired authentication token",
  "instance": "/api/v1/users",
  "timestamp": "2024-01-29T10:30:00Z",
  "trace_id": "abc123def456"
}
```

#### 404 Not Found
```json
{
  "type": "https://regulens.ai/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "User with ID '123' not found",
  "instance": "/api/v1/users/123",
  "timestamp": "2024-01-29T10:30:00Z",
  "trace_id": "abc123def456"
}
```

#### 429 Rate Limited
```json
{
  "type": "https://regulens.ai/errors/rate-limited",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Rate limit of 1000 requests per minute exceeded",
  "instance": "/api/v1/users",
  "timestamp": "2024-01-29T10:30:00Z",
  "trace_id": "abc123def456"
}
```

## JavaScript/TypeScript Examples

### Authentication Service

```typescript
class RegulensAPIClient {
  private baseURL = 'http://localhost:8000/api/v1';
  private accessToken: string | null = null;
  private tenantId: string;

  constructor(tenantId: string) {
    this.tenantId = tenantId;
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    this.accessToken = data.access_token;
    return data;
  }

  async getUsers(page = 1, size = 20): Promise<UserListResponse> {
    const response = await fetch(`${this.baseURL}/users?page=${page}&size=${size}`, {
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'X-Tenant-ID': this.tenantId,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch users');
    }

    return response.json();
  }

  async createComplianceTask(task: ComplianceTaskCreate): Promise<ComplianceTaskResponse> {
    const response = await fetch(`${this.baseURL}/compliance/tasks`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'X-Tenant-ID': this.tenantId,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(task),
    });

    if (!response.ok) {
      throw new Error('Failed to create compliance task');
    }

    return response.json();
  }
}
```

### Usage Example

```typescript
const client = new RegulensAPIClient('your-tenant-id');

// Login
await client.login('admin@regulens.ai', 'admin123');

// Get users
const users = await client.getUsers(1, 20);

// Create compliance task
const task = await client.createComplianceTask({
  title: 'Monthly Risk Assessment',
  description: 'Conduct monthly risk assessment review',
  priority: 'medium',
  due_date: '2024-08-31',
  category: 'Risk Management'
});
```
