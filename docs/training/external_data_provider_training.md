# External Data Provider Integration Training

## Table of Contents

1. [Overview](#overview)
2. [Supported Providers](#supported-providers)
3. [Configuration Management](#configuration-management)
4. [Entity Screening Workflows](#entity-screening-workflows)
5. [Data Management](#data-management)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
7. [Best Practices](#best-practices)
8. [Hands-on Exercises](#hands-on-exercises)

## Overview

RegulensAI integrates with multiple external data providers to enhance compliance and risk management capabilities. This training covers configuration, usage, and management of these integrations.

### Learning Objectives

After completing this training, you will be able to:
- Configure external data provider connections
- Perform entity screening across multiple providers
- Manage data updates and synchronization
- Monitor provider performance and availability
- Troubleshoot common integration issues

### Key Benefits

- **Comprehensive Coverage**: Multiple data sources for thorough screening
- **Real-time Updates**: Automatic data synchronization
- **Performance Optimization**: Caching and rate limiting
- **Reliability**: Failover and retry mechanisms
- **Compliance**: Audit trails and data lineage

## Supported Providers

### Sanctions Lists

#### OFAC (Office of Foreign Assets Control)
- **Type**: Government sanctions list
- **Coverage**: US sanctions and blocked persons
- **Update Frequency**: Multiple times daily
- **Data Format**: XML
- **Cost**: Free

#### EU Sanctions
- **Type**: European Union sanctions
- **Coverage**: EU financial and trade sanctions
- **Update Frequency**: Daily
- **Data Format**: XML
- **Cost**: Free

#### UN Sanctions
- **Type**: United Nations sanctions
- **Coverage**: Global UN sanctions
- **Update Frequency**: Daily
- **Data Format**: XML
- **Cost**: Free

### Commercial Data Providers

#### Refinitiv (formerly Thomson Reuters)
- **Type**: Financial and market data
- **Coverage**: Global companies, individuals, vessels
- **Services**: World-Check, Eikon, News & Analytics
- **Update Frequency**: Real-time
- **Cost**: Subscription-based

#### Experian
- **Type**: Credit and identity verification
- **Coverage**: Business and consumer data
- **Services**: Credit reports, identity verification, fraud detection
- **Update Frequency**: Real-time
- **Cost**: Per-query pricing

## Configuration Management

### Initial Setup

#### Web Interface Configuration

1. **Navigate to Settings**
   - Go to **Settings > Integrations > External Data Providers**

2. **Add New Provider**
   - Click **Add Provider**
   - Select provider type
   - Enter configuration details

3. **Test Connection**
   - Use **Test Connection** button
   - Verify credentials and connectivity

#### API Configuration

```python
import requests

# Configure OFAC provider
ofac_config = {
    "provider": "ofac",
    "config": {
        "base_url": "https://www.treasury.gov/ofac/downloads",
        "cache_hours": 12,
        "auto_update": True,
        "update_interval_hours": 4
    }
}

response = requests.post(
    "https://api.regulensai.com/v1/integrations/external-data/configure",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json=ofac_config
)
```

### Provider-Specific Configuration

#### Refinitiv Configuration

```json
{
  "provider": "refinitiv",
  "config": {
    "api_key": "your-api-key",
    "username": "your-username",
    "password": "your-password",
    "app_id": "RegulensAI",
    "base_url": "https://api.refinitiv.com",
    "rate_limit_per_minute": 1000,
    "timeout_seconds": 30,
    "services": {
      "world_check": {
        "enabled": true,
        "endpoint": "/world-check/v1"
      },
      "news": {
        "enabled": true,
        "endpoint": "/news/v1"
      }
    }
  }
}
```

#### Experian Configuration

```json
{
  "provider": "experian",
  "config": {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "subscriber_code": "your-subscriber-code",
    "sub_code": "your-sub-code",
    "use_sandbox": false,
    "base_url": "https://api.experian.com",
    "services": {
      "business_credit": {
        "enabled": true,
        "product_code": "BCP"
      },
      "identity_verification": {
        "enabled": true,
        "product_code": "IDV"
      }
    }
  }
}
```

### Configuration Validation

#### Automated Validation

The system automatically validates configurations:
- **Credential Testing**: Verifies API credentials
- **Connectivity Checks**: Tests network connectivity
- **Service Availability**: Confirms service endpoints
- **Rate Limit Verification**: Checks rate limit settings

#### Manual Validation

```python
# Test provider configuration
response = requests.post(
    "https://api.regulensai.com/v1/integrations/external-data/test",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"provider": "refinitiv"}
)

if response.status_code == 200:
    print("Configuration valid")
else:
    print(f"Configuration error: {response.json()}")
```

## Entity Screening Workflows

### Basic Entity Screening

#### Single Entity Screening

```python
# Screen a single entity
entity_data = {
    "name": "Acme Corporation Ltd",
    "entity_type": "corporation",
    "address": "123 Business Street, London, UK",
    "business_registration": "UK12345678"
}

screening_request = {
    "entity_data": entity_data,
    "screening_type": "comprehensive",
    "providers": ["ofac", "eu_sanctions", "refinitiv"]
}

response = requests.post(
    "https://api.regulensai.com/v1/external-data/screen-entity",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json=screening_request
)

result = response.json()
```

#### Batch Entity Screening

```python
# Screen multiple entities
entities = [
    {
        "name": "Company A",
        "entity_type": "corporation",
        "country": "US"
    },
    {
        "name": "John Doe",
        "entity_type": "person",
        "date_of_birth": "1980-01-01"
    }
]

batch_request = {
    "entities": entities,
    "screening_type": "basic",
    "providers": ["ofac", "eu_sanctions"]
}

response = requests.post(
    "https://api.regulensai.com/v1/external-data/screen-batch",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json=batch_request
)
```

### Advanced Screening Options

#### Custom Screening Parameters

```python
screening_request = {
    "entity_data": entity_data,
    "screening_type": "custom",
    "providers": ["refinitiv"],
    "screening_options": {
        "include_historical": True,
        "fuzzy_matching": True,
        "match_threshold": 0.8,
        "include_aliases": True,
        "search_depth": "comprehensive"
    }
}
```

#### Scheduled Screening

```python
# Set up scheduled screening
schedule_config = {
    "entity_list_id": "list-uuid",
    "schedule": {
        "frequency": "daily",
        "time": "02:00",
        "timezone": "UTC"
    },
    "providers": ["ofac", "eu_sanctions", "un_sanctions"],
    "notification_settings": {
        "on_matches": True,
        "on_errors": True,
        "recipients": ["compliance@company.com"]
    }
}

response = requests.post(
    "https://api.regulensai.com/v1/external-data/schedule-screening",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json=schedule_config
)
```

### Result Interpretation

#### Screening Result Structure

```json
{
  "status": "success",
  "entity_name": "Acme Corporation Ltd",
  "screening_id": "screening-uuid",
  "screening_date": "2024-01-29T10:30:00Z",
  "total_providers": 3,
  "successful_screenings": 3,
  "failed_screenings": 0,
  "total_matches": 2,
  "overall_risk_score": 0.75,
  "screening_result": "potential_match",
  "provider_results": [
    {
      "provider": "refinitiv",
      "status": "success",
      "matches": [
        {
          "match_id": "match-uuid",
          "match_strength": 0.85,
          "matched_name": "Acme Corp Limited",
          "list_name": "World-Check",
          "match_type": "fuzzy",
          "additional_info": {
            "categories": ["PEP", "Sanctions"],
            "last_updated": "2024-01-28"
          }
        }
      ]
    }
  ]
}
```

#### Risk Assessment

- **Clear**: No matches found across all providers
- **Possible Match**: Low-confidence matches requiring review
- **Potential Match**: Medium-confidence matches requiring investigation
- **Hit**: High-confidence matches requiring immediate action

### Workflow Integration

#### Automated Workflows

```python
# Create automated screening workflow
workflow_config = {
    "name": "Customer Onboarding Screening",
    "trigger": "customer_creation",
    "steps": [
        {
            "type": "screen_entity",
            "providers": ["ofac", "eu_sanctions", "refinitiv"],
            "screening_type": "comprehensive"
        },
        {
            "type": "risk_assessment",
            "rules": [
                {
                    "condition": "overall_risk_score > 0.8",
                    "action": "flag_for_review"
                },
                {
                    "condition": "screening_result == 'hit'",
                    "action": "block_onboarding"
                }
            ]
        },
        {
            "type": "notification",
            "template": "screening_complete",
            "recipients": ["compliance@company.com"]
        }
    ]
}
```

## Data Management

### Data Synchronization

#### Automatic Updates

The system automatically updates data from providers:
- **OFAC**: Every 4 hours
- **EU Sanctions**: Every 6 hours
- **UN Sanctions**: Every 6 hours
- **Refinitiv**: Real-time via API
- **Experian**: Real-time via API

#### Manual Updates

```python
# Trigger manual data update
response = requests.post(
    "https://api.regulensai.com/v1/external-data/update-sources",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "providers": ["ofac", "eu_sanctions"],
        "force_update": True
    }
)
```

### Data Quality Management

#### Data Validation

- **Format Validation**: Ensures data meets expected formats
- **Completeness Checks**: Verifies all required fields are present
- **Consistency Validation**: Checks for data inconsistencies
- **Freshness Monitoring**: Tracks data age and update frequency

#### Data Lineage

Track data sources and transformations:
- **Source Tracking**: Original data provider
- **Update History**: When data was last updated
- **Processing Log**: Data transformation steps
- **Quality Metrics**: Data quality scores

### Caching Strategy

#### Cache Configuration

```python
cache_config = {
    "provider": "refinitiv",
    "cache_settings": {
        "enabled": True,
        "ttl_seconds": 3600,  # 1 hour
        "max_size_mb": 100,
        "eviction_policy": "lru"
    }
}
```

#### Cache Performance

Monitor cache effectiveness:
- **Hit Ratio**: Percentage of cache hits
- **Miss Ratio**: Percentage of cache misses
- **Response Time**: Average response time with/without cache
- **Storage Usage**: Cache storage utilization

## Monitoring and Troubleshooting

### Performance Monitoring

#### Key Metrics

- **Response Time**: Average API response time per provider
- **Success Rate**: Percentage of successful requests
- **Error Rate**: Percentage of failed requests
- **Rate Limit Usage**: Current rate limit utilization
- **Data Freshness**: Age of cached data

#### Monitoring Dashboard

Access real-time metrics at `https://grafana.regulensai.com/external-data`:
- Provider availability status
- Response time trends
- Error rate analysis
- Rate limit monitoring
- Cache performance

### Common Issues and Solutions

#### Authentication Failures

**Symptoms**: HTTP 401 errors, "Invalid credentials" messages

**Solutions**:
1. Verify API credentials are correct
2. Check credential expiration dates
3. Ensure proper environment configuration
4. Test credentials using provider's test endpoints

#### Rate Limiting

**Symptoms**: HTTP 429 errors, "Rate limit exceeded" messages

**Solutions**:
1. Implement exponential backoff retry logic
2. Reduce request frequency
3. Contact provider to increase rate limits
4. Use caching to reduce API calls

#### Data Synchronization Issues

**Symptoms**: Stale data, update errors in logs

**Solutions**:
1. Check network connectivity to provider endpoints
2. Verify data source URLs are current
3. Review provider maintenance schedules
4. Check disk space for data storage

### Troubleshooting Tools

#### Health Check Endpoint

```bash
curl -H "Authorization: Bearer $TOKEN" \
     https://api.regulensai.com/v1/external-data/health
```

#### Provider Status Check

```python
# Check specific provider status
response = requests.get(
    "https://api.regulensai.com/v1/external-data/providers/refinitiv/status",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

status = response.json()
print(f"Status: {status['status']}")
print(f"Last Request: {status['last_request']}")
print(f"Error Rate: {status['error_rate']}")
```

## Best Practices

### Configuration Management

1. **Environment Separation**: Use different credentials for dev/staging/prod
2. **Credential Security**: Store credentials securely using secret management
3. **Regular Testing**: Periodically test provider connections
4. **Documentation**: Maintain configuration documentation
5. **Change Management**: Follow change control processes

### Performance Optimization

1. **Caching Strategy**: Implement appropriate caching for each provider
2. **Batch Processing**: Use batch operations where available
3. **Rate Limit Management**: Respect provider rate limits
4. **Connection Pooling**: Reuse connections for better performance
5. **Monitoring**: Continuously monitor performance metrics

### Data Quality

1. **Validation Rules**: Implement data validation rules
2. **Quality Metrics**: Track data quality over time
3. **Error Handling**: Implement robust error handling
4. **Data Lineage**: Maintain clear data lineage
5. **Regular Audits**: Conduct regular data quality audits

### Security Considerations

1. **Encryption**: Encrypt data in transit and at rest
2. **Access Control**: Implement proper access controls
3. **Audit Logging**: Log all data access and modifications
4. **Compliance**: Follow data protection regulations
5. **Incident Response**: Have incident response procedures

## Hands-on Exercises

### Exercise 1: Provider Configuration

1. Configure OFAC sanctions list integration
2. Test the connection and data retrieval
3. Set up automatic updates
4. Verify data quality and freshness

### Exercise 2: Entity Screening

1. Screen a test entity against multiple providers
2. Analyze the screening results
3. Configure screening thresholds
4. Set up automated screening workflows

### Exercise 3: Performance Monitoring

1. Access the monitoring dashboard
2. Analyze provider performance metrics
3. Set up alerts for performance issues
4. Create a performance report

### Exercise 4: Troubleshooting

1. Simulate a provider connection issue
2. Use troubleshooting tools to diagnose the problem
3. Implement a solution
4. Verify the fix and document the resolution

## Additional Resources

- **API Documentation**: https://docs.regulensai.com/api/external-data
- **Provider Documentation**: Links to individual provider docs
- **Video Tutorials**: https://training.regulensai.com/external-data
- **Support Portal**: https://support.regulensai.com

## Support and Feedback

For questions about external data provider integrations:
- **Email**: integrations@regulensai.com
- **Slack**: #external-data-support
- **Phone**: +1-XXX-XXX-XXXX (business hours)

---

*This training guide is part of the RegulensAI certification program. For updates and additional resources, visit the training portal.*
