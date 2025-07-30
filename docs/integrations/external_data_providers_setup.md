# External Data Providers Integration Setup Guide

This guide provides step-by-step instructions for setting up external data provider integrations in RegulensAI.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [OFAC Sanctions Lists](#ofac-sanctions-lists)
3. [EU Sanctions Lists](#eu-sanctions-lists)
4. [UN Sanctions Lists](#un-sanctions-lists)
5. [Refinitiv Market Data](#refinitiv-market-data)
6. [Experian Credit Services](#experian-credit-services)
7. [Configuration Validation](#configuration-validation)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before setting up external data provider integrations, ensure you have:

- RegulensAI platform deployed and running
- Administrative access to the platform
- Valid credentials for commercial data providers
- Network connectivity to external services
- Proper firewall configurations

### Required Environment Variables

```bash
# Core configuration
TENANT_ID=your-tenant-uuid
ENVIRONMENT=production  # or staging, development

# Database configuration
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Security configuration
ENCRYPTION_KEY=your-32-character-encryption-key
JWT_SECRET=your-jwt-secret-key
```

## OFAC Sanctions Lists

The Office of Foreign Assets Control (OFAC) provides publicly available sanctions lists.

### Setup Steps

1. **Configure OFAC Provider**
   ```bash
   # Add to .env file
   OFAC_CACHE_HOURS=12
   OFAC_AUTO_UPDATE=true
   OFAC_UPDATE_INTERVAL_HOURS=4
   OFAC_BASE_URL=https://www.treasury.gov/ofac/downloads
   ```

2. **Initialize OFAC Data Source**
   ```python
   from core_infra.services.integrations.external_data_integration import ExternalDataIntegrationService
   
   # Initialize service
   service = ExternalDataIntegrationService(supabase_client)
   
   # Configure OFAC provider
   await service.configure_provider('ofac', {
       'base_url': 'https://www.treasury.gov/ofac/downloads',
       'cache_hours': 12,
       'auto_update': True,
       'data_sources': ['sdn.xml', 'consolidated.xml', 'ssi.xml']
   })
   ```

3. **Test OFAC Integration**
   ```bash
   # Run integration test
   python scripts/test_ofac_integration.py
   ```

### OFAC Data Sources

- **SDN List**: Specially Designated Nationals and Blocked Persons
- **Consolidated List**: Comprehensive sanctions list
- **SSI List**: Sectoral Sanctions Identifications

### Update Schedule

- **Automatic Updates**: Every 4 hours (configurable)
- **Manual Updates**: Available via API or admin interface
- **Cache Duration**: 12 hours (configurable)

## EU Sanctions Lists

European Union sanctions data is available from the European Commission.

### Setup Steps

1. **Configure EU Sanctions Provider**
   ```bash
   # Add to .env file
   EU_SANCTIONS_CACHE_HOURS=24
   EU_SANCTIONS_AUTO_UPDATE=true
   EU_SANCTIONS_UPDATE_INTERVAL_HOURS=6
   ```

2. **Initialize EU Sanctions Data Source**
   ```python
   await service.configure_provider('eu_sanctions', {
       'consolidated_url': 'https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content',
       'financial_url': 'https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList/content',
       'cache_hours': 24,
       'auto_update': True
   })
   ```

3. **Test EU Sanctions Integration**
   ```bash
   python scripts/test_eu_sanctions_integration.py
   ```

### EU Data Sources

- **Consolidated Sanctions List**: Complete EU sanctions database
- **Financial Sanctions**: Financial restrictions and asset freezes

## UN Sanctions Lists

United Nations sanctions data from the UN Security Council.

### Setup Steps

1. **Configure UN Sanctions Provider**
   ```bash
   # Add to .env file
   UN_SANCTIONS_CACHE_HOURS=24
   UN_SANCTIONS_AUTO_UPDATE=true
   UN_SANCTIONS_UPDATE_INTERVAL_HOURS=6
   ```

2. **Initialize UN Sanctions Data Source**
   ```python
   await service.configure_provider('un_sanctions', {
       'consolidated_url': 'https://scsanctions.un.org/resources/xml/en/consolidated.xml',
       'cache_hours': 24,
       'auto_update': True
   })
   ```

## Refinitiv Market Data

Refinitiv provides comprehensive market data and financial information.

### Prerequisites

- Refinitiv account with API access
- Valid API credentials
- Appropriate data subscriptions

### Setup Steps

1. **Obtain Refinitiv Credentials**
   - Contact Refinitiv to set up API access
   - Obtain API key, username, and password
   - Note your application ID

2. **Configure Refinitiv Provider**
   ```bash
   # Add to .env file
   REFINITIV_API_KEY=your-refinitiv-api-key
   REFINITIV_USERNAME=your-refinitiv-username
   REFINITIV_PASSWORD=your-refinitiv-password
   REFINITIV_APP_ID=RegulensAI
   REFINITIV_BASE_URL=https://api.refinitiv.com
   REFINITIV_RATE_LIMIT_PER_MINUTE=1000
   REFINITIV_TIMEOUT_SECONDS=30
   ```

3. **Initialize Refinitiv Integration**
   ```python
   await service.configure_provider('refinitiv', {
       'api_key': os.getenv('REFINITIV_API_KEY'),
       'username': os.getenv('REFINITIV_USERNAME'),
       'password': os.getenv('REFINITIV_PASSWORD'),
       'app_id': os.getenv('REFINITIV_APP_ID'),
       'base_url': os.getenv('REFINITIV_BASE_URL'),
       'rate_limit_per_minute': 1000,
       'timeout_seconds': 30
   })
   ```

4. **Test Refinitiv Integration**
   ```bash
   python scripts/test_refinitiv_integration.py
   ```

### Refinitiv Services

- **Market Data**: Real-time and historical market data
- **News & Sentiment**: Financial news and sentiment analysis
- **ESG Data**: Environmental, Social, and Governance data
- **Fundamentals**: Company financial fundamentals

### Rate Limiting

- **Default Limit**: 1000 requests per minute
- **Burst Handling**: Automatic retry with exponential backoff
- **Monitoring**: Rate limit usage tracked and logged

## Experian Credit Services

Experian provides credit information and business intelligence.

### Prerequisites

- Experian account with API access
- Valid client credentials
- Appropriate service subscriptions

### Setup Steps

1. **Obtain Experian Credentials**
   - Contact Experian for API access
   - Obtain client ID and client secret
   - Get subscriber and sub codes

2. **Configure Experian Provider**
   ```bash
   # Add to .env file
   EXPERIAN_CLIENT_ID=your-experian-client-id
   EXPERIAN_CLIENT_SECRET=your-experian-client-secret
   EXPERIAN_SUBSCRIBER_CODE=your-subscriber-code
   EXPERIAN_SUB_CODE=your-sub-code
   EXPERIAN_USE_SANDBOX=false
   EXPERIAN_BASE_URL_PRODUCTION=https://api.experian.com
   EXPERIAN_BASE_URL_SANDBOX=https://sandbox-api.experian.com
   ```

3. **Initialize Experian Integration**
   ```python
   await service.configure_provider('experian', {
       'client_id': os.getenv('EXPERIAN_CLIENT_ID'),
       'client_secret': os.getenv('EXPERIAN_CLIENT_SECRET'),
       'subscriber_code': os.getenv('EXPERIAN_SUBSCRIBER_CODE'),
       'sub_code': os.getenv('EXPERIAN_SUB_CODE'),
       'use_sandbox': os.getenv('EXPERIAN_USE_SANDBOX', 'false').lower() == 'true',
       'base_url': os.getenv('EXPERIAN_BASE_URL_PRODUCTION')
   })
   ```

4. **Test Experian Integration**
   ```bash
   python scripts/test_experian_integration.py
   ```

### Experian Services

- **Business Credit Reports**: Comprehensive business credit information
- **Identity Verification**: Identity validation services
- **Fraud Detection**: Fraud risk assessment
- **Compliance Screening**: AML and sanctions screening

## Configuration Validation

### Automated Setup Script

Use the provided setup script for automated configuration:

```bash
# Run interactive setup
python scripts/setup_production_integrations.py

# Follow prompts to configure each provider
# Script will validate configurations and test connections
```

### Manual Validation

1. **Test All Providers**
   ```python
   from core_infra.services.integrations.external_data_integration import ExternalDataIntegrationService
   
   service = ExternalDataIntegrationService(supabase_client)
   
   # Test entity screening across all providers
   result = await service.screen_entity(
       tenant_id="your-tenant-id",
       entity_data={
           "name": "Test Entity",
           "entity_type": "corporation"
       },
       screening_type="comprehensive"
   )
   
   print(f"Screening result: {result}")
   ```

2. **Validate Data Updates**
   ```python
   # Test data source updates
   update_result = await service.update_all_data_sources("your-tenant-id")
   print(f"Update result: {update_result}")
   ```

### Health Checks

Monitor provider health using built-in health checks:

```bash
# Check provider status
curl -H "Authorization: Bearer $API_TOKEN" \
     https://api.regulensai.com/v1/external-data/health

# Expected response:
{
  "status": "healthy",
  "providers": {
    "ofac": {"status": "healthy", "last_update": "2024-01-29T10:00:00Z"},
    "eu_sanctions": {"status": "healthy", "last_update": "2024-01-29T09:00:00Z"},
    "un_sanctions": {"status": "healthy", "last_update": "2024-01-29T09:00:00Z"},
    "refinitiv": {"status": "healthy", "last_request": "2024-01-29T10:30:00Z"},
    "experian": {"status": "healthy", "last_request": "2024-01-29T10:25:00Z"}
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

**Symptoms**: HTTP 401 errors, "Invalid credentials" messages

**Solutions**:
- Verify API credentials are correct
- Check credential expiration dates
- Ensure proper environment variable configuration
- Test credentials using provider's test endpoints

#### 2. Rate Limiting

**Symptoms**: HTTP 429 errors, "Rate limit exceeded" messages

**Solutions**:
- Implement exponential backoff retry logic
- Reduce request frequency
- Contact provider to increase rate limits
- Use caching to reduce API calls

#### 3. Data Update Failures

**Symptoms**: Stale data, update errors in logs

**Solutions**:
- Check network connectivity to provider endpoints
- Verify data source URLs are current
- Review provider maintenance schedules
- Check disk space for data storage

#### 4. Slow Response Times

**Symptoms**: Timeouts, slow screening responses

**Solutions**:
- Increase timeout values
- Implement request caching
- Use asynchronous processing
- Consider data pre-loading

### Logging and Monitoring

Enable detailed logging for troubleshooting:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable provider-specific logging
logger = logging.getLogger('external_data_integration')
logger.setLevel(logging.DEBUG)
```

### Support Contacts

- **OFAC Support**: Contact US Treasury OFAC office
- **EU Sanctions**: Contact European Commission
- **UN Sanctions**: Contact UN Security Council
- **Refinitiv Support**: Contact Refinitiv customer support
- **Experian Support**: Contact Experian API support
- **RegulensAI Support**: support@regulensai.com

### Performance Optimization

1. **Caching Strategy**
   - Enable provider-level caching
   - Set appropriate cache TTL values
   - Use Redis for distributed caching

2. **Batch Processing**
   - Process multiple entities in batches
   - Use bulk screening APIs where available
   - Implement queue-based processing

3. **Connection Pooling**
   - Configure HTTP connection pools
   - Reuse connections across requests
   - Set appropriate pool sizes

4. **Monitoring**
   - Set up provider performance monitoring
   - Track response times and error rates
   - Configure alerting for failures

For additional support, consult the [API documentation](../api/openapi_spec.yaml) or contact RegulensAI support.
