"""
Enhanced Swagger Configuration for Regulens AI
Comprehensive API documentation with examples, field descriptions, and usage guides
"""

from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def get_enhanced_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Generate enhanced OpenAPI schema with comprehensive documentation"""
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Regulens AI - Financial Compliance Platform",
        version="1.0.0",
        description=get_comprehensive_description(),
        routes=app.routes,
        servers=[
            {"url": "http://localhost:8000", "description": "Development server"},
            {"url": "https://api.regulens-ai.com", "description": "Production server"}
        ]
    )
    
    # Add comprehensive examples
    openapi_schema = add_comprehensive_examples(openapi_schema)
    
    # Add security schemes
    openapi_schema = add_security_schemes(openapi_schema)
    
    # Add response examples
    openapi_schema = add_response_examples(openapi_schema)
    
    # Add field descriptions
    openapi_schema = add_field_descriptions(openapi_schema)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def get_comprehensive_description() -> str:
    """Get comprehensive API description with usage examples"""
    return """
# Regulens AI Financial Compliance Platform API

**Enterprise-grade financial compliance platform** for banks, financial institutions, and fintech companies.

## 🚀 Quick Start

### Authentication
All endpoints require JWT authentication. First, obtain a token:

```bash
curl -X POST "http://localhost:8000/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "your_username", "password": "your_password"}'
```

Then include the token in subsequent requests:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  "http://localhost:8000/v1/regulatory/sources"
```

### Multi-tenancy
Include your tenant ID in all requests:
```bash
curl -H "X-Tenant-ID: your-tenant-id" \\
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
     "http://localhost:8000/v1/compliance/tasks"
```

## 🏗️ Core Features

### 📊 Regulatory Monitoring
- Real-time monitoring of SEC, FCA, ECB, and other regulatory sources
- Automated change detection and impact assessment
- Customizable alert thresholds and notification workflows

### 🛡️ AML/KYC Compliance
- Customer risk scoring and profiling
- Real-time transaction monitoring
- Sanctions and PEP screening
- Automated suspicious activity reporting

### 🤖 AI-Powered Insights
- Regulatory document analysis with GPT-4/Claude
- Natural language Q&A for compliance questions
- Automated policy interpretation and summarization
- Entity extraction from regulatory texts

### 📋 Workflow Management
- Automated compliance task creation and assignment
- Escalation workflows with SLA monitoring
- Audit trail generation and compliance reporting
- Integration with external GRC systems

### 📈 Analytics & Reporting
- Risk analytics and performance benchmarking
- Compliance metrics and KPI dashboards
- Predictive analytics for regulatory impact
- Audit-ready compliance reports

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Multi-tenant Isolation**: Complete data separation by tenant
- **Rate Limiting**: Configurable request rate limits
- **Audit Logging**: Complete audit trail for all operations
- **Role-based Access Control**: Granular permission management

## 📋 API Conventions

### Response Format
All API responses follow a consistent format:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### Error Handling
Error responses include detailed information:

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Invalid input parameters",
  "details": {
    "field": "customer_id",
    "issue": "Required field missing"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### Pagination
List endpoints support pagination:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

## 📚 Integration Examples

### Python Example
```python
import requests

# Authentication
auth_response = requests.post(
    "http://localhost:8000/v1/auth/login",
    json={"username": "user", "password": "pass"}
)
token = auth_response.json()["data"]["access_token"]

# Make authenticated request
headers = {
    "Authorization": f"Bearer {token}",
    "X-Tenant-ID": "your-tenant-id"
}
response = requests.get(
    "http://localhost:8000/v1/regulatory/sources",
    headers=headers
)
```

### JavaScript Example
```javascript
// Authentication
const authResponse = await fetch('/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'user', password: 'pass' })
});
const { access_token } = await authResponse.json();

// Make authenticated request
const response = await fetch('/v1/regulatory/sources', {
    headers: {
        'Authorization': `Bearer ${access_token}`,
        'X-Tenant-ID': 'your-tenant-id'
    }
});
```

## 🔧 Configuration

The platform is highly configurable through environment variables:

- **Database**: Supabase PostgreSQL with connection pooling
- **AI Models**: OpenAI GPT-4, Anthropic Claude integration
- **Monitoring**: Jaeger tracing, Prometheus metrics
- **Security**: Configurable JWT, rate limiting, CORS

## 📞 Support

- **Documentation Portal**: http://localhost:8501
- **Testing Portal**: http://localhost:8502
- **Health Check**: http://localhost:8000/v1/health
- **System Metrics**: http://localhost:8000/v1/metrics

For technical support, please refer to the comprehensive documentation portal.
"""

def add_comprehensive_examples(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add comprehensive request/response examples to the schema"""
    
    examples = {
        "CustomerScreeningRequest": {
            "summary": "Screen customer against sanctions lists",
            "description": "Complete customer screening with PEP and sanctions checking",
            "value": {
                "customer_id": "CUST_001_2024",
                "customer_data": {
                    "first_name": "John",
                    "last_name": "Smith",
                    "date_of_birth": "1985-03-15",
                    "nationality": "US",
                    "address": {
                        "street": "123 Main Street",
                        "city": "New York",
                        "state": "NY",
                        "country": "US",
                        "postal_code": "10001"
                    },
                    "identification": {
                        "type": "passport",
                        "number": "A12345678",
                        "issuing_country": "US",
                        "expiry_date": "2028-03-15"
                    }
                },
                "screening_options": {
                    "include_sanctions": True,
                    "include_pep": True,
                    "include_adverse_media": True,
                    "confidence_threshold": 0.85
                }
            }
        },
        "TransactionMonitoringRequest": {
            "summary": "Monitor high-value wire transfer",
            "description": "Monitor international wire transfer for AML compliance",
            "value": {
                "transaction_id": "TXN_WR_20240115_001",
                "customer_id": "CUST_001_2024",
                "transaction_data": {
                    "amount": 150000.00,
                    "currency": "USD",
                    "transaction_type": "wire_transfer",
                    "transaction_date": "2024-01-15T14:30:00Z",
                    "originator": {
                        "name": "ABC Corporation",
                        "account": "123456789",
                        "bank": "First National Bank",
                        "country": "US"
                    },
                    "beneficiary": {
                        "name": "XYZ Trading Ltd",
                        "account": "987654321",
                        "bank": "London Commercial Bank",
                        "country": "GB"
                    },
                    "purpose": "Trade settlement for commodity purchase"
                },
                "monitoring_rules": {
                    "check_sanctions": True,
                    "check_threshold": True,
                    "check_geography": True,
                    "check_pattern": True
                }
            }
        },
        "RegulatoryAnalysisRequest": {
            "summary": "Analyze new banking regulation",
            "description": "AI analysis of Federal Reserve regulation changes",
            "value": {
                "content": "The Federal Reserve Board announced final rules implementing revisions to the regulatory capital framework for banking organizations. The rules maintain the current capital requirements for community banking organizations with total consolidated assets of less than $10 billion. For larger banking organizations, the rules implement the final components of the Basel III regulatory capital reforms.",
                "analysis_type": "regulatory_impact",
                "options": {
                    "model": "gpt-4",
                    "include_entities": True,
                    "include_recommendations": True,
                    "confidence_threshold": 0.7
                }
            }
        },
        "ComplianceTaskCreation": {
            "summary": "Create regulatory review task",
            "description": "Create a compliance task for regulatory change review",
            "value": {
                "title": "Review Basel III Capital Requirements Update",
                "description": "Analyze impact of new Basel III requirements on current capital allocation and reporting processes",
                "task_type": "regulatory_review",
                "priority": "high",
                "due_date": "2024-02-15T17:00:00Z",
                "assigned_to_user_id": "user_compliance_manager",
                "regulatory_reference": "Fed_Basel_III_2024_Q1",
                "workflow_id": "wf_regulatory_review_standard",
                "metadata": {
                    "regulation_source": "Federal Reserve",
                    "effective_date": "2024-06-01",
                    "impact_assessment": "high",
                    "business_units": ["risk_management", "capital_planning", "reporting"]
                }
            }
        },
        "RiskAnalysisRequest": {
            "summary": "Comprehensive customer risk analysis",
            "description": "Multi-factor risk analysis for high-value customer",
            "value": {
                "analysis_type": "customer_risk_comprehensive",
                "customer_ids": ["CUST_001_2024", "CUST_002_2024"],
                "risk_factors": {
                    "transaction_volume": True,
                    "geographic_risk": True,
                    "sanctions_exposure": True,
                    "pep_status": True,
                    "adverse_media": True,
                    "business_relationship": True
                },
                "analysis_period": {
                    "start_date": "2023-07-01",
                    "end_date": "2024-01-15"
                },
                "options": {
                    "include_recommendations": True,
                    "generate_report": True,
                    "alert_thresholds": {
                        "high_risk": 0.8,
                        "medium_risk": 0.5
                    }
                }
            }
        }
    }
    
    # Add examples to components
    if "components" not in schema:
        schema["components"] = {}
    if "examples" not in schema["components"]:
        schema["components"]["examples"] = {}
    
    schema["components"]["examples"].update(examples)
    
    return schema

def add_security_schemes(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add comprehensive security scheme definitions"""
    
    security_schemes = {
        "JWTAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication. Obtain token from /v1/auth/login endpoint."
        },
        "TenantHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Tenant-ID",
            "description": "Tenant isolation header. Required for all authenticated requests."
        }
    }
    
    if "components" not in schema:
        schema["components"] = {}
    if "securitySchemes" not in schema["components"]:
        schema["components"]["securitySchemes"] = {}
    
    schema["components"]["securitySchemes"].update(security_schemes)
    
    # Add global security requirement
    schema["security"] = [
        {"JWTAuth": [], "TenantHeader": []}
    ]
    
    return schema

def add_response_examples(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add comprehensive response examples"""
    
    response_examples = {
        "SuccessfulScreeningResponse": {
            "summary": "Successful customer screening result",
            "value": {
                "success": True,
                "data": {
                    "screening_id": "SCR_20240115_001",
                    "customer_id": "CUST_001_2024",
                    "screening_date": "2024-01-15T14:30:00Z",
                    "overall_risk_score": 0.25,
                    "risk_level": "low",
                    "screening_results": {
                        "sanctions": {
                            "matches_found": 0,
                            "confidence": 0.0,
                            "status": "clear"
                        },
                        "pep": {
                            "matches_found": 0,
                            "confidence": 0.0,
                            "status": "clear"
                        },
                        "adverse_media": {
                            "matches_found": 1,
                            "confidence": 0.15,
                            "status": "low_risk",
                            "details": "Minor traffic violation 2019"
                        }
                    },
                    "recommendations": [
                        "Customer cleared for standard service level",
                        "Schedule routine review in 12 months"
                    ]
                },
                "message": "Customer screening completed successfully",
                "timestamp": "2024-01-15T14:30:00Z",
                "request_id": "req_scr_123456"
            }
        },
        "ComplianceMetricsResponse": {
            "summary": "Monthly compliance metrics",
            "value": {
                "success": True,
                "data": {
                    "reporting_period": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31"
                    },
                    "metrics": {
                        "total_tasks": 156,
                        "completed_tasks": 142,
                        "completion_rate": 0.91,
                        "average_completion_time_hours": 18.5,
                        "overdue_tasks": 3,
                        "escalated_tasks": 5
                    },
                    "risk_metrics": {
                        "high_risk_customers": 23,
                        "medium_risk_customers": 145,
                        "suspicious_transactions": 8,
                        "sars_filed": 2
                    },
                    "regulatory_updates": {
                        "total_changes": 12,
                        "high_impact": 2,
                        "medium_impact": 6,
                        "low_impact": 4
                    },
                    "trends": {
                        "month_over_month_completion": 0.05,
                        "risk_score_trend": -0.02,
                        "alert_volume_trend": 0.15
                    }
                },
                "message": "Compliance metrics retrieved successfully",
                "timestamp": "2024-02-01T09:00:00Z"
            }
        },
        "ValidationErrorResponse": {
            "summary": "Validation error example",
            "value": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "field": "customer_data.date_of_birth",
                    "issue": "Date format must be YYYY-MM-DD",
                    "provided_value": "15/03/1985",
                    "expected_format": "1985-03-15"
                },
                "timestamp": "2024-01-15T14:30:00Z",
                "request_id": "req_err_123456"
            }
        },
        "AuthenticationErrorResponse": {
            "summary": "Authentication error example",
            "value": {
                "success": False,
                "error": "AUTHENTICATION_ERROR",
                "message": "Invalid or expired JWT token",
                "details": {
                    "error_code": "TOKEN_EXPIRED",
                    "token_expiry": "2024-01-15T13:00:00Z",
                    "current_time": "2024-01-15T14:30:00Z"
                },
                "timestamp": "2024-01-15T14:30:00Z",
                "request_id": "req_auth_123456"
            }
        }
    }
    
    if "components" not in schema:
        schema["components"] = {}
    if "examples" not in schema["components"]:
        schema["components"]["examples"] = {}
    
    schema["components"]["examples"].update(response_examples)
    
    return schema

def add_field_descriptions(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add detailed field descriptions to schema components"""
    
    field_descriptions = {
        "customer_id": {
            "description": "Unique customer identifier. Must be alphanumeric, 3-50 characters.",
            "example": "CUST_001_2024"
        },
        "transaction_id": {
            "description": "Unique transaction identifier. System generates if not provided.",
            "example": "TXN_WR_20240115_001"
        },
        "risk_score": {
            "description": "Calculated risk score between 0.0 (lowest risk) and 1.0 (highest risk).",
            "example": 0.25
        },
        "confidence": {
            "description": "AI model confidence level for the analysis result (0.0 to 1.0).",
            "example": 0.85
        },
        "tenant_id": {
            "description": "Tenant identifier for multi-tenant data isolation.",
            "example": "tenant_bank_abc"
        },
        "regulatory_reference": {
            "description": "Reference to the specific regulation or regulatory change.",
            "example": "Fed_Basel_III_2024_Q1"
        }
    }
    
    # Apply field descriptions to all schema components
    if "components" in schema and "schemas" in schema["components"]:
        for schema_name, schema_def in schema["components"]["schemas"].items():
            if "properties" in schema_def:
                for field_name, field_def in schema_def["properties"].items():
                    if field_name in field_descriptions:
                        field_def.update(field_descriptions[field_name])
    
    return schema

def get_api_tags_metadata() -> List[Dict[str, Any]]:
    """Get comprehensive API tags metadata for better organization"""
    
    return [
        {
            "name": "System",
            "description": "System health, information, and monitoring endpoints",
            "externalDocs": {
                "description": "System monitoring guide",
                "url": "http://localhost:8501#monitoring"
            }
        },
        {
            "name": "Authentication",
            "description": "User authentication and token management",
            "externalDocs": {
                "description": "Authentication guide",
                "url": "http://localhost:8501#authentication"
            }
        },
        {
            "name": "Tenants",
            "description": "Multi-tenant organization management",
            "externalDocs": {
                "description": "Multi-tenancy documentation",
                "url": "http://localhost:8501#tenants"
            }
        },
        {
            "name": "Users",
            "description": "User management and role-based access control",
            "externalDocs": {
                "description": "User management guide",
                "url": "http://localhost:8501#users"
            }
        },
        {
            "name": "Regulatory",
            "description": "Regulatory monitoring, sources, and change detection",
            "externalDocs": {
                "description": "Regulatory monitoring guide",
                "url": "http://localhost:8501#regulatory"
            }
        },
        {
            "name": "Compliance",
            "description": "Compliance workflows, tasks, and program management",
            "externalDocs": {
                "description": "Compliance workflows guide",
                "url": "http://localhost:8501#compliance"
            }
        },
        {
            "name": "AML/KYC",
            "description": "Anti-money laundering and Know Your Customer compliance",
            "externalDocs": {
                "description": "AML/KYC implementation guide",
                "url": "http://localhost:8501#aml-kyc"
            }
        },
        {
            "name": "Tasks",
            "description": "Task management and workflow automation",
            "externalDocs": {
                "description": "Task management guide",
                "url": "http://localhost:8501#tasks"
            }
        },
        {
            "name": "Reports",
            "description": "Compliance reporting and audit trail generation",
            "externalDocs": {
                "description": "Reporting and analytics guide",
                "url": "http://localhost:8501#reports"
            }
        },
        {
            "name": "AI Insights",
            "description": "AI-powered regulatory analysis and insights",
            "externalDocs": {
                "description": "AI services documentation",
                "url": "http://localhost:8501#ai-insights"
            }
        },
        {
            "name": "Analytics",
            "description": "Advanced analytics and risk scoring",
            "externalDocs": {
                "description": "Analytics and risk scoring guide",
                "url": "http://localhost:8501#analytics"
            }
        },
        {
            "name": "Integrations",
            "description": "Enterprise system integrations (GRC, Core Banking, etc.)",
            "externalDocs": {
                "description": "Integration setup guide",
                "url": "http://localhost:8501#integrations"
            }
        },
        {
            "name": "Advanced AI",
            "description": "Phase 6 advanced AI and automation features",
            "externalDocs": {
                "description": "Advanced AI documentation",
                "url": "http://localhost:8501#advanced-ai"
            }
        }
    ] 