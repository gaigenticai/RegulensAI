# Compliance Service - Policy Management API

## Endpoint Information

**URL**: `/api/v1/compliance/policies`  
**Method**: `POST`  
**Service**: Compliance Service  
**Port**: 8081  

## Description

Creates and manages compliance policies within the regulatory framework. This endpoint provides comprehensive policy lifecycle management including creation, versioning, approval workflows, and automated compliance monitoring.

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
  "title": "string",
  "description": "string",
  "policy_type": "string",
  "category": "string",
  "content": "string",
  "effective_date": "string (ISO 8601)",
  "review_date": "string (ISO 8601)",
  "owner": "string",
  "stakeholders": ["string"],
  "regulatory_references": [
    {
      "regulation_id": "string",
      "section": "string",
      "requirement": "string"
    }
  ],
  "controls": ["string"],
  "approval_workflow": {
    "required_approvers": ["string"],
    "approval_sequence": "string"
  },
  "metadata": "object (optional)"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | String | Yes | Policy title (max 255 characters) |
| `description` | String | Yes | Detailed policy description |
| `policy_type` | String | Yes | Type: "PROCEDURE", "STANDARD", "GUIDELINE", "FRAMEWORK" |
| `category` | String | Yes | Category: "RISK", "COMPLIANCE", "SECURITY", "OPERATIONAL" |
| `content` | String | Yes | Full policy content in markdown format |
| `effective_date` | String | Yes | When policy becomes effective (ISO 8601) |
| `review_date` | String | Yes | Next scheduled review date (ISO 8601) |
| `owner` | String | Yes | Policy owner user ID |
| `stakeholders` | Array | No | List of stakeholder user IDs |
| `regulatory_references` | Array | No | Related regulatory requirements |
| `controls` | Array | No | Associated control IDs |
| `approval_workflow` | Object | No | Approval process configuration |

## Response Schema

### Success Response (201 Created)
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "string",
    "description": "string",
    "policy_type": "string",
    "category": "string",
    "status": "string",
    "version": "string",
    "effective_date": "string (ISO 8601)",
    "review_date": "string (ISO 8601)",
    "owner": "string",
    "stakeholders": ["string"],
    "regulatory_references": [
      {
        "regulation_id": "string",
        "section": "string",
        "requirement": "string"
      }
    ],
    "controls": ["string"],
    "approval_status": {
      "status": "string",
      "pending_approvers": ["string"],
      "approved_by": ["string"],
      "approval_date": "string (ISO 8601)"
    },
    "compliance_metrics": {
      "adherence_score": "number",
      "last_assessment": "string (ISO 8601)",
      "violations": "number"
    },
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)",
    "created_by": "uuid",
    "updated_by": "uuid"
  },
  "message": "Policy created successfully"
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "Invalid policy data",
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
| `id` | UUID | Unique policy identifier |
| `status` | String | Policy status: "DRAFT", "PENDING_APPROVAL", "APPROVED", "ACTIVE", "EXPIRED" |
| `version` | String | Policy version (semantic versioning) |
| `approval_status` | Object | Current approval workflow status |
| `compliance_metrics` | Object | Policy compliance performance metrics |
| `adherence_score` | Number | Compliance adherence score (0-100) |

## Example Usage

### cURL Example
```bash
curl -X POST "https://api.regulateai.com/api/v1/compliance/policies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Request-ID: req_policy_123456" \
  -d '{
    "title": "Data Privacy Protection Policy",
    "description": "Comprehensive policy for protecting customer data privacy",
    "policy_type": "STANDARD",
    "category": "COMPLIANCE",
    "content": "# Data Privacy Protection Policy\n\n## Purpose\nThis policy establishes requirements for protecting customer data...",
    "effective_date": "2024-09-01T00:00:00Z",
    "review_date": "2025-09-01T00:00:00Z",
    "owner": "compliance-officer-001",
    "stakeholders": ["legal-team", "it-security", "data-protection-officer"],
    "regulatory_references": [
      {
        "regulation_id": "GDPR",
        "section": "Article 32",
        "requirement": "Security of processing"
      }
    ],
    "controls": ["CTRL_DATA_001", "CTRL_ACCESS_002"],
    "approval_workflow": {
      "required_approvers": ["chief-compliance-officer", "legal-counsel"],
      "approval_sequence": "sequential"
    }
  }'
```

### JavaScript Example
```javascript
const response = await fetch('https://api.regulateai.com/api/v1/compliance/policies', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token,
    'X-Request-ID': 'req_policy_js_001'
  },
  body: JSON.stringify({
    title: 'Information Security Policy',
    description: 'Enterprise information security standards and procedures',
    policy_type: 'FRAMEWORK',
    category: 'SECURITY',
    content: '# Information Security Policy\n\n## Scope\nThis policy applies to all employees...',
    effective_date: '2024-08-15T00:00:00Z',
    review_date: '2025-08-15T00:00:00Z',
    owner: 'ciso-001',
    stakeholders: ['security-team', 'it-operations'],
    regulatory_references: [
      {
        regulation_id: 'SOX',
        section: '404',
        requirement: 'Internal controls over financial reporting'
      }
    ],
    controls: ['CTRL_SEC_001', 'CTRL_SEC_002', 'CTRL_SEC_003']
  })
});

const result = await response.json();
console.log('Policy created:', result.data.id);
```

## Policy Lifecycle Management

### Policy States
1. **DRAFT**: Initial creation, editable by owner
2. **PENDING_APPROVAL**: Submitted for approval workflow
3. **APPROVED**: Approved but not yet effective
4. **ACTIVE**: Currently in effect
5. **EXPIRED**: Past review date, requires update
6. **ARCHIVED**: No longer in use

### Approval Workflows
- **Sequential**: Approvers must approve in specified order
- **Parallel**: All approvers can approve simultaneously
- **Majority**: Requires majority approval from approver group
- **Unanimous**: Requires all approvers to approve

### Version Control
- Semantic versioning (MAJOR.MINOR.PATCH)
- Automatic version increment on changes
- Complete audit trail of all versions
- Ability to rollback to previous versions

## Compliance Monitoring

### Automated Assessments
- **Adherence Tracking**: Monitor policy compliance across organization
- **Violation Detection**: Identify policy violations and exceptions
- **Risk Scoring**: Calculate risk scores based on compliance gaps
- **Trend Analysis**: Track compliance trends over time

### Reporting Features
- **Compliance Dashboard**: Real-time compliance status
- **Exception Reports**: Detailed violation and exception reports
- **Audit Reports**: Comprehensive audit trail documentation
- **Executive Summaries**: High-level compliance status for leadership

## Integration Points

### External Systems
- **Document Management**: Integration with SharePoint, Confluence
- **HR Systems**: Employee policy acknowledgment tracking
- **Training Platforms**: Automatic training assignment based on policies
- **Audit Tools**: Export data for external audit requirements

### Internal Services
- **Risk Management**: Policy risk assessment integration
- **Control Management**: Automatic control mapping and updates
- **Incident Management**: Policy violation incident creation
- **Workflow Engine**: Custom approval and review workflows

## Rate Limiting

- **Rate Limit**: 50 requests per minute per API key
- **Burst Limit**: 10 requests per second
- **Large Policies**: Policies >1MB may have additional processing time

## Security Features

1. **Access Control**: Role-based permissions for policy management
2. **Data Encryption**: All policy content encrypted at rest and in transit
3. **Audit Logging**: Complete audit trail of all policy changes
4. **Digital Signatures**: Optional digital signing for approved policies
5. **Version Control**: Immutable version history with change tracking

## Compliance Standards

This endpoint supports compliance with:
- **ISO 27001**: Information security management
- **SOC 2**: Security, availability, and confidentiality
- **GDPR**: Data protection and privacy requirements
- **SOX**: Financial reporting controls
- **NIST**: Cybersecurity framework alignment

## Related Endpoints

- `GET /api/v1/compliance/policies/{id}` - Get policy details
- `PUT /api/v1/compliance/policies/{id}` - Update policy
- `POST /api/v1/compliance/policies/{id}/approve` - Approve policy
- `GET /api/v1/compliance/policies/{id}/compliance` - Get compliance metrics
- `POST /api/v1/compliance/policies/{id}/assessment` - Trigger compliance assessment
