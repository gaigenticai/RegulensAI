# API Gateway - Service Discovery Endpoints

## Overview
The API Gateway Service Discovery endpoints provide functionality for service registration, health monitoring, and service instance management within the RegulateAI microservices ecosystem.

## Base URL
```
http://localhost:8079/gateway
```

## Authentication
All endpoints require JWT authentication via the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Register Service Instance

**Endpoint:** `POST /gateway/services/register`

**Description:** Register a new service instance with the gateway for load balancing and health monitoring.

**Request Headers:**
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "service_name": "aml-service",
  "host": "localhost",
  "port": 8080,
  "version": "1.0.0",
  "health_endpoint": "/health",
  "weight": 100,
  "tags": ["production", "primary"],
  "metadata": {
    "region": "us-east-1",
    "datacenter": "dc1"
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "instance_id": "550e8400-e29b-41d4-a716-446655440000",
    "service_name": "aml-service",
    "host": "localhost",
    "port": 8080,
    "version": "1.0.0",
    "health_status": "Unknown",
    "registered_at": "2025-08-02T10:30:00Z",
    "health_endpoint": "/health",
    "weight": 100,
    "tags": ["production", "primary"],
    "metadata": {
      "region": "us-east-1",
      "datacenter": "dc1"
    }
  },
  "message": "Service instance registered successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `409 Conflict`: Service instance already registered
- `500 Internal Server Error`: Registration failed

### 2. Deregister Service Instance

**Endpoint:** `DELETE /gateway/services/{service_name}/instances/{instance_id}`

**Description:** Remove a service instance from the gateway registry.

**Path Parameters:**
- `service_name` (string): Name of the service
- `instance_id` (UUID): Unique identifier of the service instance

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Service instance deregistered successfully"
}
```

**Error Responses:**
- `404 Not Found`: Service instance not found
- `401 Unauthorized`: Missing or invalid authentication
- `500 Internal Server Error`: Deregistration failed

### 3. Get Service Instances

**Endpoint:** `GET /gateway/services/{service_name}/instances`

**Description:** Retrieve all registered instances for a specific service.

**Path Parameters:**
- `service_name` (string): Name of the service

**Query Parameters:**
- `health_status` (optional): Filter by health status (healthy, unhealthy, unknown, degraded)
- `tags` (optional): Comma-separated list of tags to filter by

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "service_name": "aml-service",
    "total_instances": 3,
    "healthy_instances": 2,
    "instances": [
      {
        "instance_id": "550e8400-e29b-41d4-a716-446655440000",
        "host": "localhost",
        "port": 8080,
        "version": "1.0.0",
        "health_status": "Healthy",
        "last_health_check": "2025-08-02T10:35:00Z",
        "weight": 100,
        "tags": ["production", "primary"],
        "metadata": {
          "region": "us-east-1",
          "datacenter": "dc1"
        }
      },
      {
        "instance_id": "550e8400-e29b-41d4-a716-446655440001",
        "host": "localhost",
        "port": 8081,
        "version": "1.0.0",
        "health_status": "Healthy",
        "last_health_check": "2025-08-02T10:35:00Z",
        "weight": 150,
        "tags": ["production", "secondary"],
        "metadata": {
          "region": "us-east-1",
          "datacenter": "dc2"
        }
      },
      {
        "instance_id": "550e8400-e29b-41d4-a716-446655440002",
        "host": "localhost",
        "port": 8082,
        "version": "1.0.0",
        "health_status": "Unhealthy",
        "last_health_check": "2025-08-02T10:35:00Z",
        "weight": 100,
        "tags": ["production", "backup"],
        "metadata": {
          "region": "us-west-1",
          "datacenter": "dc3"
        }
      }
    ]
  }
}
```

### 4. Get All Services

**Endpoint:** `GET /gateway/services`

**Description:** Retrieve all registered services and their instances.

**Query Parameters:**
- `include_unhealthy` (optional, boolean): Include unhealthy instances (default: false)
- `tags` (optional): Comma-separated list of tags to filter by

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_services": 6,
    "services": {
      "aml-service": {
        "total_instances": 3,
        "healthy_instances": 2,
        "load_balancer_algorithm": "WeightedRoundRobin",
        "instances": [...]
      },
      "compliance-service": {
        "total_instances": 2,
        "healthy_instances": 2,
        "load_balancer_algorithm": "RoundRobin",
        "instances": [...]
      },
      "risk-management-service": {
        "total_instances": 4,
        "healthy_instances": 3,
        "load_balancer_algorithm": "LeastConnections",
        "instances": [...]
      }
    }
  }
}
```

### 5. Get Service Health Status

**Endpoint:** `GET /gateway/services/{service_name}/health`

**Description:** Get detailed health information for a service and its instances.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "service_name": "aml-service",
    "overall_health": "Degraded",
    "total_instances": 3,
    "healthy_instances": 2,
    "unhealthy_instances": 1,
    "health_check_interval_ms": 30000,
    "last_health_check": "2025-08-02T10:35:00Z",
    "instances": [
      {
        "instance_id": "550e8400-e29b-41d4-a716-446655440000",
        "health_status": "Healthy",
        "response_time_ms": 15.2,
        "consecutive_failures": 0,
        "total_checks": 1440,
        "successful_checks": 1438,
        "last_check": "2025-08-02T10:35:00Z"
      },
      {
        "instance_id": "550e8400-e29b-41d4-a716-446655440001",
        "health_status": "Healthy",
        "response_time_ms": 22.1,
        "consecutive_failures": 0,
        "total_checks": 1440,
        "successful_checks": 1440,
        "last_check": "2025-08-02T10:35:00Z"
      },
      {
        "instance_id": "550e8400-e29b-41d4-a716-446655440002",
        "health_status": "Unhealthy",
        "response_time_ms": 0,
        "consecutive_failures": 5,
        "total_checks": 1440,
        "successful_checks": 1200,
        "last_check": "2025-08-02T10:35:00Z"
      }
    ]
  }
}
```

### 6. Update Service Instance

**Endpoint:** `PUT /gateway/services/{service_name}/instances/{instance_id}`

**Description:** Update configuration for a registered service instance.

**Request Body:**
```json
{
  "weight": 200,
  "tags": ["production", "primary", "high-capacity"],
  "metadata": {
    "region": "us-east-1",
    "datacenter": "dc1",
    "capacity": "high"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "instance_id": "550e8400-e29b-41d4-a716-446655440000",
    "service_name": "aml-service",
    "weight": 200,
    "tags": ["production", "primary", "high-capacity"],
    "metadata": {
      "region": "us-east-1",
      "datacenter": "dc1",
      "capacity": "high"
    },
    "updated_at": "2025-08-02T10:40:00Z"
  },
  "message": "Service instance updated successfully"
}
```

### 7. Force Health Check

**Endpoint:** `POST /gateway/services/{service_name}/instances/{instance_id}/health-check`

**Description:** Trigger an immediate health check for a specific service instance.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "instance_id": "550e8400-e29b-41d4-a716-446655440000",
    "health_status": "Healthy",
    "response_time_ms": 18.5,
    "check_timestamp": "2025-08-02T10:45:00Z",
    "health_endpoint": "/health",
    "status_code": 200,
    "response_body": {
      "status": "healthy",
      "version": "1.0.0",
      "uptime_seconds": 86400
    }
  }
}
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_NOT_FOUND",
    "message": "Service 'unknown-service' not found",
    "details": {
      "service_name": "unknown-service",
      "available_services": ["aml-service", "compliance-service", "risk-management-service"]
    }
  },
  "timestamp": "2025-08-02T10:30:00Z",
  "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
}
```

## Rate Limiting

Service Discovery endpoints are rate limited to:
- 100 requests per minute for read operations (GET)
- 20 requests per minute for write operations (POST, PUT, DELETE)

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1659441600
```

## WebSocket Support

Real-time service health updates are available via WebSocket:

**Endpoint:** `ws://localhost:8079/gateway/services/events`

**Authentication:** JWT token via query parameter or header

**Event Types:**
- `service_registered`: New service instance registered
- `service_deregistered`: Service instance removed
- `health_status_changed`: Instance health status changed
- `service_unavailable`: All instances for a service are unhealthy

**Example Event:**
```json
{
  "event_type": "health_status_changed",
  "timestamp": "2025-08-02T10:35:00Z",
  "data": {
    "service_name": "aml-service",
    "instance_id": "550e8400-e29b-41d4-a716-446655440000",
    "old_status": "Healthy",
    "new_status": "Unhealthy",
    "response_time_ms": 0,
    "error_message": "Connection timeout"
  }
}
```

## SDK Examples

### JavaScript/Node.js
```javascript
const axios = require('axios');

const gatewayClient = axios.create({
  baseURL: 'http://localhost:8079/gateway',
  headers: {
    'Authorization': 'Bearer your-jwt-token',
    'Content-Type': 'application/json'
  }
});

// Register service instance
async function registerService() {
  try {
    const response = await gatewayClient.post('/services/register', {
      service_name: 'my-service',
      host: 'localhost',
      port: 8080,
      version: '1.0.0',
      health_endpoint: '/health',
      weight: 100,
      tags: ['production']
    });
    console.log('Service registered:', response.data);
  } catch (error) {
    console.error('Registration failed:', error.response.data);
  }
}

// Get service instances
async function getServiceInstances(serviceName) {
  try {
    const response = await gatewayClient.get(`/services/${serviceName}/instances`);
    return response.data.data.instances;
  } catch (error) {
    console.error('Failed to get instances:', error.response.data);
    return [];
  }
}
```

### Python
```python
import requests
import json

class GatewayClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def register_service(self, service_config):
        response = requests.post(
            f'{self.base_url}/services/register',
            headers=self.headers,
            json=service_config
        )
        return response.json()
    
    def get_service_instances(self, service_name, health_status=None):
        params = {}
        if health_status:
            params['health_status'] = health_status
        
        response = requests.get(
            f'{self.base_url}/services/{service_name}/instances',
            headers=self.headers,
            params=params
        )
        return response.json()

# Usage
client = GatewayClient('http://localhost:8079/gateway', 'your-jwt-token')

# Register service
service_config = {
    'service_name': 'my-service',
    'host': 'localhost',
    'port': 8080,
    'version': '1.0.0',
    'health_endpoint': '/health',
    'weight': 100,
    'tags': ['production']
}

result = client.register_service(service_config)
print(f"Registration result: {result}")
```
