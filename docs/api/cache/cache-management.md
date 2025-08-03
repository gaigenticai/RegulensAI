# Cache Management API

## Overview
The Cache Management API provides endpoints for managing the multi-level caching system, including L1 (memory), L2 (Redis), and L3 (database) cache layers.

## Base URL
```
https://api.regulateai.com/v1/cache
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### 1. Get Cache Status

**GET** `/status`

Returns the current status and statistics of all cache levels.

#### Request
```http
GET /v1/cache/status
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "status": "healthy",
  "levels": [
    {
      "level": "L1_MEMORY",
      "enabled": true,
      "status": "healthy",
      "size": 85632,
      "entries": 1247,
      "hit_ratio": 0.892,
      "evictions": 45,
      "memory_usage_mb": 67.5,
      "max_capacity": 10000,
      "max_size_mb": 100
    },
    {
      "level": "L2_REDIS",
      "enabled": true,
      "status": "healthy",
      "size": 2456789,
      "entries": 15623,
      "hit_ratio": 0.756,
      "memory_usage_mb": 245.7,
      "connection_pool_size": 20,
      "active_connections": 8
    },
    {
      "level": "L3_DATABASE",
      "enabled": false,
      "status": "disabled",
      "size": 0,
      "entries": 0,
      "hit_ratio": 0.0
    }
  ],
  "overall_stats": {
    "total_entries": 16870,
    "total_size_mb": 313.2,
    "overall_hit_ratio": 0.834,
    "cache_promotion_count": 1250,
    "cache_demotion_count": 89
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Cache status retrieved successfully
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 2. Get Cache Entry

**GET** `/entries/{key}`

Retrieves a specific cache entry by key.

#### Request
```http
GET /v1/cache/entries/customer:12345
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | string | Yes | Cache key to retrieve |

#### Response
```json
{
  "found": true,
  "key": "customer:12345",
  "value": {
    "id": 12345,
    "name": "John Doe",
    "email": "john.doe@example.com",
    "status": "ACTIVE"
  },
  "metadata": {
    "level": "L1_MEMORY",
    "created_at": "2024-01-15T09:30:00Z",
    "last_accessed": "2024-01-15T10:25:00Z",
    "access_count": 15,
    "ttl_seconds": 3600,
    "expires_at": "2024-01-15T11:30:00Z",
    "size_bytes": 256,
    "compressed": false,
    "serialization_format": "bincode"
  }
}
```

#### Status Codes
- `200 OK` - Cache entry retrieved successfully
- `404 Not Found` - Cache entry not found
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 3. Set Cache Entry

**PUT** `/entries/{key}`

Sets or updates a cache entry.

#### Request
```http
PUT /v1/cache/entries/customer:12345
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "value": {
    "id": 12345,
    "name": "John Doe",
    "email": "john.doe@example.com",
    "status": "ACTIVE",
    "last_login": "2024-01-15T10:00:00Z"
  },
  "ttl_seconds": 3600,
  "tags": ["customer", "active"],
  "compression_enabled": true,
  "cache_levels": ["L1_MEMORY", "L2_REDIS"]
}
```

#### Request Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | object | Yes | Data to cache |
| `ttl_seconds` | integer | No | Time to live in seconds (default: 3600) |
| `tags` | array | No | Tags for cache entry |
| `compression_enabled` | boolean | No | Enable compression (default: true) |
| `cache_levels` | array | No | Specific cache levels to use |

#### Response
```json
{
  "success": true,
  "message": "Cache entry set successfully",
  "key": "customer:12345",
  "metadata": {
    "levels_stored": ["L1_MEMORY", "L2_REDIS"],
    "size_bytes": 312,
    "compressed": true,
    "compression_ratio": 0.78,
    "serialization_format": "bincode",
    "expires_at": "2024-01-15T11:30:00Z",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### Status Codes
- `200 OK` - Cache entry updated successfully
- `201 Created` - Cache entry created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `413 Payload Too Large` - Cache entry exceeds size limit
- `500 Internal Server Error` - Server error

### 4. Delete Cache Entry

**DELETE** `/entries/{key}`

Deletes a cache entry from all levels.

#### Request
```http
DELETE /v1/cache/entries/customer:12345
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "success": true,
  "message": "Cache entry deleted successfully",
  "key": "customer:12345",
  "deleted_from_levels": ["L1_MEMORY", "L2_REDIS"],
  "deleted_at": "2024-01-15T10:35:00Z"
}
```

#### Status Codes
- `200 OK` - Cache entry deleted successfully
- `404 Not Found` - Cache entry not found
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 5. Invalidate Cache Pattern

**POST** `/invalidate`

Invalidates multiple cache entries matching a pattern.

#### Request
```http
POST /v1/cache/invalidate
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "pattern": "customer:*",
  "levels": ["L1_MEMORY", "L2_REDIS"],
  "reason": "Customer data update batch"
}
```

#### Request Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | string | Yes | Pattern to match (supports wildcards) |
| `levels` | array | No | Specific cache levels (default: all) |
| `reason` | string | No | Reason for invalidation |

#### Response
```json
{
  "success": true,
  "message": "Cache entries invalidated successfully",
  "pattern": "customer:*",
  "invalidated_count": 1247,
  "levels_affected": ["L1_MEMORY", "L2_REDIS"],
  "invalidated_at": "2024-01-15T10:40:00Z",
  "reason": "Customer data update batch"
}
```

#### Status Codes
- `200 OK` - Cache entries invalidated successfully
- `400 Bad Request` - Invalid pattern or parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 6. Warm Cache

**POST** `/warm`

Pre-loads cache with specified keys or patterns.

#### Request
```http
POST /v1/cache/warm
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "keys": [
    "customer:12345",
    "customer:12346",
    "customer:12347"
  ],
  "patterns": [
    "transaction:2024-01-*"
  ],
  "strategy": "EAGER",
  "batch_size": 50,
  "max_concurrent": 10
}
```

#### Request Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `keys` | array | No | Specific keys to warm |
| `patterns` | array | No | Patterns to warm |
| `strategy` | string | No | Warming strategy: EAGER, LAZY, SCHEDULED |
| `batch_size` | integer | No | Batch size for warming (default: 50) |
| `max_concurrent` | integer | No | Max concurrent operations (default: 10) |

#### Response
```json
{
  "success": true,
  "message": "Cache warming initiated successfully",
  "warming_job_id": "warm_job_12345",
  "estimated_keys": 1500,
  "strategy": "EAGER",
  "batch_size": 50,
  "max_concurrent": 10,
  "started_at": "2024-01-15T10:45:00Z",
  "estimated_completion": "2024-01-15T10:50:00Z"
}
```

#### Status Codes
- `202 Accepted` - Cache warming initiated successfully
- `400 Bad Request` - Invalid warming parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 7. Get Cache Configuration

**GET** `/config`

Retrieves the current cache configuration.

#### Request
```http
GET /v1/cache/config
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response
```json
{
  "l1_config": {
    "enabled": true,
    "max_capacity": 10000,
    "max_size_mb": 100,
    "ttl_minutes": 60,
    "idle_timeout_minutes": 30,
    "eviction_policy": "LRU"
  },
  "l2_config": {
    "enabled": true,
    "redis_url": "redis://localhost:6379/2",
    "max_connections": 20,
    "connection_timeout_seconds": 5,
    "key_prefix": "regulateai:cache:",
    "compression_enabled": true
  },
  "l3_config": {
    "enabled": false,
    "database_url": "postgresql://localhost:5432/cache",
    "table_name": "cache_entries",
    "max_connections": 5,
    "cleanup_interval_hours": 1
  },
  "compression": {
    "algorithm": "lz4",
    "level": 1,
    "threshold_bytes": 1024
  },
  "serialization": {
    "format": "bincode"
  },
  "max_entry_size_mb": 10
}
```

#### Status Codes
- `200 OK` - Configuration retrieved successfully
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

### 8. Update Cache Configuration

**PUT** `/config`

Updates the cache configuration.

#### Request
```http
PUT /v1/cache/config
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "l1_config": {
    "max_capacity": 15000,
    "max_size_mb": 150,
    "ttl_minutes": 90
  },
  "compression": {
    "algorithm": "zstd",
    "level": 3
  }
}
```

#### Response
```json
{
  "success": true,
  "message": "Cache configuration updated successfully",
  "updated_fields": [
    "l1_config.max_capacity",
    "l1_config.max_size_mb",
    "l1_config.ttl_minutes",
    "compression.algorithm",
    "compression.level"
  ],
  "updated_at": "2024-01-15T10:50:00Z",
  "restart_required": false
}
```

#### Status Codes
- `200 OK` - Configuration updated successfully
- `400 Bad Request` - Invalid configuration parameters
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - Insufficient permissions
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

## Error Responses

```json
{
  "error": {
    "code": "CACHE_KEY_NOT_FOUND",
    "message": "The specified cache key was not found",
    "details": {
      "key": "customer:99999",
      "searched_levels": ["L1_MEMORY", "L2_REDIS", "L3_DATABASE"]
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_cache_12345"
  }
}
```

## Rate Limits

- **Read operations**: 5000 requests per minute per API key
- **Write operations**: 1000 requests per minute per API key
- **Configuration operations**: 10 requests per minute per API key
- **Bulk operations**: 100 requests per minute per API key

## Examples

### Check Cache Status
```bash
curl -X GET "https://api.regulateai.com/v1/cache/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Cache Customer Data
```bash
curl -X PUT "https://api.regulateai.com/v1/cache/entries/customer:12345" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": {
      "id": 12345,
      "name": "John Doe",
      "email": "john.doe@example.com"
    },
    "ttl_seconds": 3600,
    "tags": ["customer", "active"]
  }'
```

### Invalidate Customer Cache
```bash
curl -X POST "https://api.regulateai.com/v1/cache/invalidate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "customer:*",
    "reason": "Customer data update"
  }'
```
