# AI Orchestration Service - Regulatory Q&A API

## Endpoint Information

**URL**: `/api/v1/ai/regulatory/qa`  
**Method**: `POST`  
**Service**: AI Orchestration Service  
**Port**: 8085  

## Description

Processes regulatory questions using specialized AI agents with natural language processing capabilities. This endpoint provides intelligent answers to compliance and regulatory questions, leveraging a knowledge base of regulatory content and domain-specific AI models.

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
  "question": "string",
  "context": "string (optional)",
  "regulation_domain": "string (optional)",
  "jurisdiction": "string (optional)"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | String | Yes | The regulatory question to be answered |
| `context` | String | No | Additional context to help with answer generation |
| `regulation_domain` | String | No | Specific regulatory domain: "banking", "securities", "insurance", "healthcare" |
| `jurisdiction` | String | No | Jurisdiction code: "US", "EU", "UK", "CA", "AU" |

## Response Schema

### Success Response (200 OK)
```json
{
  "answer": "string",
  "confidence": "number",
  "sources": ["string"],
  "related_regulations": ["string"],
  "follow_up_questions": ["string"]
}
```

### Error Response (400 Bad Request)
```json
{
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

## Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `answer` | String | Comprehensive answer to the regulatory question |
| `confidence` | Number | Confidence score (0.0-1.0) for the answer accuracy |
| `sources` | Array | List of regulatory sources used to generate the answer |
| `related_regulations` | Array | Related regulations that may be relevant |
| `follow_up_questions` | Array | Suggested follow-up questions for deeper understanding |

## Example Usage

### cURL Example
```bash
curl -X POST "https://api.regulateai.com/api/v1/ai/regulatory/qa" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Request-ID: req_qa_123456" \
  -d '{
    "question": "What are the capital adequacy requirements for banks under Basel III?",
    "context": "We are a mid-size commercial bank looking to understand minimum capital requirements",
    "regulation_domain": "banking",
    "jurisdiction": "US"
  }'
```

### Python Example
```python
import requests

url = "https://api.regulateai.com/api/v1/ai/regulatory/qa"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + token,
    "X-Request-ID": "req_qa_python_001"
}

payload = {
    "question": "What are the data retention requirements under GDPR?",
    "context": "European fintech company processing customer data",
    "regulation_domain": "data_protection",
    "jurisdiction": "EU"
}

response = requests.post(url, headers=headers, json=payload)
result = response.json()

print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
print(f"Sources: {', '.join(result['sources'])}")
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per API key
- **Burst Limit**: 10 requests per second
- **Complex Questions**: May have lower limits due to processing requirements

## AI Model Information

### Regulatory Q&A Models
- **Primary Model**: GPT-4 fine-tuned on regulatory content
- **Domain Models**: Specialized models for banking, securities, insurance
- **Knowledge Base**: 50,000+ regulatory documents and guidelines
- **Update Frequency**: Weekly updates with latest regulatory changes

### Supported Domains
- **Banking**: Basel III, Dodd-Frank, CRA, BSA/AML
- **Securities**: SEC regulations, MiFID II, FINRA rules
- **Insurance**: Solvency II, NAIC guidelines, state regulations
- **Data Protection**: GDPR, CCPA, PIPEDA, data privacy laws
- **Healthcare**: HIPAA, FDA regulations, clinical trial requirements

### Supported Jurisdictions
- **United States**: Federal and state regulations
- **European Union**: EU-wide directives and regulations
- **United Kingdom**: Post-Brexit regulatory framework
- **Canada**: Federal and provincial regulations
- **Australia**: APRA, ASIC, and other regulatory bodies

## Performance Metrics

- **Response Time**: < 2 seconds for 95% of requests
- **Accuracy**: 94% accuracy on regulatory Q&A benchmarks
- **Coverage**: 98% of common regulatory questions answered
- **Availability**: 99.9% uptime SLA

## Use Cases

1. **Compliance Training**: Generate training content and Q&A materials
2. **Regulatory Research**: Quick answers to complex regulatory questions
3. **Policy Development**: Understand regulatory requirements for policy creation
4. **Audit Preparation**: Get clarification on regulatory expectations
5. **Risk Assessment**: Understand regulatory implications of business decisions

## Error Handling

The API uses standard HTTP status codes:

- **200**: Success - Question answered successfully
- **400**: Bad Request - Invalid question format or missing required fields
- **401**: Unauthorized - Invalid or missing authentication token
- **403**: Forbidden - Insufficient permissions for regulatory Q&A
- **429**: Too Many Requests - Rate limit exceeded
- **500**: Internal Server Error - AI processing error

## Security Considerations

1. **Data Privacy**: Questions and answers are encrypted and not stored permanently
2. **Access Control**: Role-based access to different regulatory domains
3. **Audit Logging**: All Q&A interactions are logged for compliance
4. **Content Filtering**: Inappropriate or irrelevant questions are filtered out

## Related Endpoints

- `POST /api/v1/ai/mapping/requirements` - Map regulatory requirements to controls
- `GET /api/v1/ai/search/context-aware` - Search regulatory knowledge base
- `POST /api/v1/ai/recommendations/next-action` - Get recommended actions
- `GET /api/v1/ai/agents/status` - Check AI agent status
