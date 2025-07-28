"""
Regulens AI Documentation Portal
Comprehensive user guide and documentation system with advanced search capabilities
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import requests
import yaml

# Optional imports with fallbacks
try:
    from streamlit_searchbox import st_searchbox
except ImportError:
    st_searchbox = None

try:
    from streamlit_ace import st_ace
except ImportError:
    st_ace = None

try:
    from markdown import markdown
except ImportError:
    def markdown(text):
        return text  # Fallback to plain text

# Configuration
st.set_page_config(
    page_title="Regulens AI Documentation Portal",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2c5aa0 0%, #1e3f73 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .feature-card {
        background: #f8f9fa;
        border-left: 4px solid #2c5aa0;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .search-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .guide-section {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .api-endpoint {
        background: #f1f3f4;
        padding: 1rem;
        border-radius: 5px;
        border-left: 3px solid #2c5aa0;
        margin: 0.5rem 0;
        font-family: monospace;
    }
    .env-variable {
        background: #e8f5e8;
        padding: 0.5rem;
        border-radius: 3px;
        margin: 0.2rem 0;
        font-family: monospace;
        border-left: 3px solid #28a745;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .code-block {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        font-family: monospace;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

class DocumentationPortal:
    def __init__(self):
        self.documentation_data = self.load_documentation_data()
        self.api_endpoints = self.load_api_endpoints()
        self.service_guides = self.load_service_guides()
        self.field_guides = self.load_field_level_guides()
        
        # API integration
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_version = "v1"
        
        # Log search queries to database
        self.log_search_queries = True
        
    def load_documentation_data(self) -> Dict[str, Any]:
        """Load comprehensive documentation data structure"""
        return {
            "platform_overview": {
                "title": "Platform Overview",
                "description": "Regulens AI is an enterprise-grade financial compliance platform designed for banks, financial institutions, and fintech companies.",
                "key_features": [
                    "Real-time regulatory change monitoring",
                    "AI-powered regulatory interpretation",
                    "Automated AML/KYC compliance",
                    "Risk scoring and assessment",
                    "Compliance workflow automation",
                    "Audit-ready reporting",
                    "Enterprise system integration"
                ],
                "architecture": {
                    "microservices": "API-driven microservices architecture",
                    "database": "Supabase PostgreSQL with multi-tenant isolation",
                    "ai_ml": "OpenAI GPT-4, Claude, custom ML models",
                    "storage": "Supabase Storage for documents",
                    "monitoring": "Jaeger distributed tracing, Prometheus metrics",
                    "deployment": "Docker containerization with docker-compose"
                }
            },
            "services": {
                "regulatory_monitor": {
                    "title": "Regulatory Monitoring Service",
                    "description": "Real-time monitoring of global regulatory changes",
                    "endpoints": ["/v1/regulatory/monitor", "/v1/regulatory/sources", "/v1/regulatory/changes"],
                    "features": ["SEC, FCA, ECB integration", "Change impact assessment", "Alert notifications"],
                    "configuration": {
                        "REGULATORY_MONITOR_ENABLED": "Enable/disable monitoring",
                        "REGULATORY_MONITOR_INTERVAL_MINUTES": "Monitoring frequency",
                        "SEC_API_KEY": "SEC API access key",
                        "FCA_API_KEY": "FCA API access key"
                    }
                },
                "aml_kyc": {
                    "title": "AML/KYC Compliance Service",
                    "description": "Automated anti-money laundering and customer verification",
                    "endpoints": ["/v1/aml/customers", "/v1/aml/transactions", "/v1/aml/screening"],
                    "features": ["Customer risk scoring", "Transaction monitoring", "Sanctions screening", "PEP detection"],
                    "configuration": {
                        "AML_MONITORING_ENABLED": "Enable AML monitoring",
                        "AML_THRESHOLD_AMOUNT": "Transaction threshold for monitoring",
                        "SANCTIONS_LIST_UPDATE_INTERVAL_HOURS": "Sanctions list update frequency"
                    }
                },
                "ai_insights": {
                    "title": "AI Regulatory Insights",
                    "description": "Natural language processing for regulatory interpretation",
                    "endpoints": ["/v1/ai/analyze", "/v1/ai/interpret", "/v1/ai/qa"],
                    "features": ["Document analysis", "Regulatory Q&A", "Policy interpretation", "Risk assessment"],
                    "configuration": {
                        "OPENAI_API_KEY": "OpenAI API key for GPT models",
                        "CLAUDE_API_KEY": "Anthropic Claude API key",
                        "LANGCHAIN_TRACING_V2": "Enable LangSmith tracing"
                    }
                },
                "compliance_workflows": {
                    "title": "Compliance Workflow Engine",
                    "description": "Automated task management and compliance workflows",
                    "endpoints": ["/v1/workflows", "/v1/tasks", "/v1/compliance/programs"],
                    "features": ["Task automation", "Escalation management", "Compliance tracking", "Audit trails"],
                    "configuration": {
                        "TASK_ASSIGNMENT_AUTO": "Automatic task assignment",
                        "ESCALATION_ENABLED": "Enable escalation workflows",
                        "ESCALATION_THRESHOLD_HOURS": "Hours before escalation"
                    }
                },
                "integrations": {
                    "title": "Enterprise Integrations",
                    "description": "Integration with external enterprise systems",
                    "endpoints": ["/v1/integrations", "/v1/integrations/grc", "/v1/integrations/banking"],
                    "features": ["GRC system integration", "Core banking connectivity", "Document management", "External data sources"],
                    "configuration": {
                        "integration system specific": "Various integration-specific configurations"
                    }
                },
                "analytics": {
                    "title": "Analytics & Reporting",
                    "description": "Advanced analytics and compliance reporting",
                    "endpoints": ["/v1/analytics", "/v1/reports", "/v1/metrics"],
                    "features": ["Risk analytics", "Compliance metrics", "Performance benchmarking", "Predictive insights"],
                    "configuration": {
                        "METRICS_ENABLED": "Enable metrics collection",
                        "PROMETHEUS_PORT": "Prometheus metrics port"
                    }
                }
            },
            "deployment": {
                "prerequisites": [
                    "Docker and Docker Compose installed",
                    "Supabase account and project setup",
                    "OpenAI API key (optional for AI features)",
                    "Claude API key (optional for AI features)",
                    "Minimum 4GB RAM, 2 CPU cores",
                    "20GB available disk space"
                ],
                "setup_steps": [
                    "Clone the repository",
                    "Configure environment variables in .env file",
                    "Run one-click installer: ./oneclickinstall.sh",
                    "Verify services are running",
                    "Access documentation at http://localhost:8501",
                    "Access API documentation at http://localhost:8000/docs"
                ],
                "production_considerations": [
                    "Use production-grade Supabase instance",
                    "Configure SSL certificates",
                    "Set up proper monitoring and alerting",
                    "Implement backup strategies",
                    "Configure rate limiting and security headers",
                    "Set up log aggregation"
                ]
            }
        }
    
    def load_api_endpoints(self) -> Dict[str, Any]:
        """Load API endpoint documentation"""
        return {
            "authentication": {
                "POST /v1/auth/login": {
                    "description": "Authenticate user and obtain JWT token",
                    "parameters": {"username": "string", "password": "string"},
                    "response": {"access_token": "string", "token_type": "bearer", "expires_in": "int"}
                },
                "POST /v1/auth/refresh": {
                    "description": "Refresh access token",
                    "parameters": {"refresh_token": "string"},
                    "response": {"access_token": "string", "expires_in": "int"}
                }
            },
            "regulatory": {
                "GET /v1/regulatory/sources": {
                    "description": "List configured regulatory sources",
                    "parameters": {"jurisdiction": "string (optional)", "active": "boolean (optional)"},
                    "response": {"sources": "array of source objects"}
                },
                "POST /v1/regulatory/monitor": {
                    "description": "Start regulatory monitoring for specific sources",
                    "parameters": {"source_ids": "array", "monitoring_config": "object"},
                    "response": {"monitoring_session_id": "string", "status": "string"}
                },
                "GET /v1/regulatory/changes": {
                    "description": "Retrieve regulatory changes",
                    "parameters": {"date_from": "datetime", "date_to": "datetime", "jurisdiction": "string", "impact_level": "string"},
                    "response": {"changes": "array of change objects", "total": "int", "page": "int"}
                }
            },
            "aml": {
                "POST /v1/aml/customers/screen": {
                    "description": "Screen customer against sanctions and PEP lists",
                    "parameters": {"customer_data": "object", "screening_options": "object"},
                    "response": {"screening_result": "object", "risk_score": "float", "matches": "array"}
                },
                "POST /v1/aml/transactions/monitor": {
                    "description": "Monitor transaction for AML compliance",
                    "parameters": {"transaction_data": "object", "monitoring_rules": "object"},
                    "response": {"compliance_result": "object", "risk_score": "float", "alerts": "array"}
                }
            },
            "ai": {
                "POST /v1/ai/analyze": {
                    "description": "Analyze document or text with AI",
                    "parameters": {"content": "string", "analysis_type": "string", "model": "string"},
                    "response": {"analysis_result": "object", "confidence": "float", "insights": "array"}
                },
                "POST /v1/ai/qa": {
                    "description": "Ask questions about regulatory content",
                    "parameters": {"question": "string", "context": "string", "model": "string"},
                    "response": {"answer": "string", "confidence": "float", "sources": "array"}
                }
            }
        }
    
    def load_field_level_guides(self) -> Dict[str, Any]:
        """Load comprehensive field-level documentation for all features"""
        return {
            "authentication_fields": {
                "title": "Authentication & Security Fields",
                "fields": {
                    "JWT_SECRET_KEY": {
                        "description": "Secret key used for signing JWT tokens",
                        "type": "string",
                        "required": True,
                        "example": "your-super-secure-jwt-secret-key-change-in-production",
                        "validation": "Minimum 32 characters, alphanumeric with special characters",
                        "security_note": "CRITICAL: Change this in production! Use a cryptographically secure random string"
                    },
                    "JWT_ALGORITHM": {
                        "description": "Algorithm used for JWT token signing",
                        "type": "string",
                        "required": True,
                        "example": "HS256",
                        "validation": "Must be one of: HS256, HS384, HS512, RS256, RS384, RS512",
                        "default": "HS256"
                    },
                    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": {
                        "description": "Access token expiration time in minutes",
                        "type": "integer",
                        "required": True,
                        "example": 60,
                        "validation": "Range: 5-1440 minutes (5 minutes to 24 hours)",
                        "security_note": "Shorter expiration is more secure but requires more frequent re-authentication"
                    },
                    "BCRYPT_ROUNDS": {
                        "description": "Number of rounds for BCrypt password hashing",
                        "type": "integer",
                        "required": True,
                        "example": 12,
                        "validation": "Range: 4-15 (higher is more secure but slower)",
                        "performance_note": "Each increment doubles the computation time"
                    }
                }
            },
            "database_fields": {
                "title": "Database Configuration Fields",
                "fields": {
                    "SUPABASE_URL": {
                        "description": "Supabase project URL for database connection",
                        "type": "string",
                        "required": True,
                        "example": "https://your-project.supabase.co",
                        "validation": "Must be a valid HTTPS URL from Supabase",
                        "where_to_find": "Supabase Dashboard > Settings > API > Project URL"
                    },
                    "SUPABASE_SERVICE_ROLE_KEY": {
                        "description": "Service role key with admin privileges",
                        "type": "string",
                        "required": True,
                        "example": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "validation": "Must be a valid JWT token",
                        "where_to_find": "Supabase Dashboard > Settings > API > service_role key",
                        "security_note": "Keep this secret! Has admin access to your database"
                    },
                    "DATABASE_POOL_SIZE": {
                        "description": "Maximum number of database connections in the pool",
                        "type": "integer",
                        "required": False,
                        "example": 20,
                        "validation": "Range: 5-100",
                        "default": 20,
                        "performance_note": "Higher values allow more concurrent users but use more resources"
                    }
                }
            },
            "aml_kyc_fields": {
                "title": "AML/KYC Configuration Fields",
                "fields": {
                    "AML_THRESHOLD_AMOUNT": {
                        "description": "Transaction amount threshold for AML monitoring",
                        "type": "decimal",
                        "required": True,
                        "example": 10000.00,
                        "validation": "Must be positive number",
                        "compliance_note": "Set according to your jurisdiction's requirements (e.g., $10,000 in US)"
                    },
                    "AML_HIGH_RISK_COUNTRIES": {
                        "description": "Comma-separated list of high-risk country codes",
                        "type": "string",
                        "required": False,
                        "example": "IR,KP,SY,AF,MM",
                        "validation": "ISO 3166-1 alpha-2 country codes",
                        "compliance_note": "Based on FATF high-risk jurisdictions list"
                    },
                    "SANCTIONS_LIST_UPDATE_INTERVAL_HOURS": {
                        "description": "How often to update sanctions lists (in hours)",
                        "type": "integer",
                        "required": False,
                        "example": 24,
                        "validation": "Range: 1-168 hours (1 hour to 1 week)",
                        "default": 24,
                        "compliance_note": "Daily updates recommended for compliance"
                    },
                    "PEP_SCREENING_ENABLED": {
                        "description": "Enable Politically Exposed Person screening",
                        "type": "boolean",
                        "required": False,
                        "example": True,
                        "validation": "true or false",
                        "default": True,
                        "compliance_note": "Required for most financial institutions"
                    }
                }
            },
            "ai_ml_fields": {
                "title": "AI/ML Service Fields",
                "fields": {
                    "OPENAI_API_KEY": {
                        "description": "OpenAI API key for GPT models",
                        "type": "string",
                        "required": False,
                        "example": "sk-proj-...",
                        "validation": "Must start with 'sk-proj-' for new keys",
                        "where_to_find": "OpenAI Platform > API Keys",
                        "cost_note": "Monitor usage to control costs"
                    },
                    "OPENAI_MODEL": {
                        "description": "Default OpenAI model to use",
                        "type": "string",
                        "required": False,
                        "example": "gpt-4",
                        "validation": "Must be available model: gpt-4, gpt-4-turbo, gpt-3.5-turbo",
                        "default": "gpt-4",
                        "cost_note": "GPT-4 is more expensive but more accurate than GPT-3.5-turbo"
                    },
                    "OPENAI_MAX_TOKENS": {
                        "description": "Maximum tokens per API call",
                        "type": "integer",
                        "required": False,
                        "example": 4000,
                        "validation": "Range: 1-128000 (depending on model)",
                        "default": 4000,
                        "cost_note": "Higher values increase cost per request"
                    },
                    "CLAUDE_API_KEY": {
                        "description": "Anthropic Claude API key",
                        "type": "string",
                        "required": False,
                        "example": "sk-ant-...",
                        "validation": "Must start with 'sk-ant-'",
                        "where_to_find": "Anthropic Console > API Keys"
                    }
                }
            },
            "regulatory_fields": {
                "title": "Regulatory Monitoring Fields",
                "fields": {
                    "REGULATORY_MONITOR_ENABLED": {
                        "description": "Enable regulatory change monitoring",
                        "type": "boolean",
                        "required": False,
                        "example": True,
                        "validation": "true or false",
                        "default": True,
                        "business_note": "Core feature for compliance automation"
                    },
                    "REGULATORY_MONITOR_INTERVAL_MINUTES": {
                        "description": "How often to check for regulatory changes (in minutes)",
                        "type": "integer",
                        "required": False,
                        "example": 60,
                        "validation": "Range: 15-1440 minutes (15 minutes to 24 hours)",
                        "default": 60,
                        "performance_note": "More frequent checks increase API usage"
                    },
                    "SEC_API_KEY": {
                        "description": "Securities and Exchange Commission API key",
                        "type": "string",
                        "required": False,
                        "example": "your-sec-api-key",
                        "where_to_find": "SEC.gov > Data > APIs",
                        "jurisdiction": "United States"
                    },
                    "FCA_API_KEY": {
                        "description": "Financial Conduct Authority API key",
                        "type": "string",
                        "required": False,
                        "example": "your-fca-api-key",
                        "where_to_find": "FCA.org.uk > Developer Portal",
                        "jurisdiction": "United Kingdom"
                    }
                }
            },
            "monitoring_fields": {
                "title": "Monitoring & Observability Fields",
                "fields": {
                    "JAEGER_ENABLED": {
                        "description": "Enable Jaeger distributed tracing",
                        "type": "boolean",
                        "required": False,
                        "example": True,
                        "validation": "true or false",
                        "default": True,
                        "performance_note": "Minimal overhead, recommended for production"
                    },
                    "JAEGER_SERVICE_NAME": {
                        "description": "Service name for Jaeger tracing",
                        "type": "string",
                        "required": False,
                        "example": "regulens-ai-compliance",
                        "validation": "Alphanumeric with hyphens only",
                        "default": "regulens-ai-compliance"
                    },
                    "LOG_LEVEL": {
                        "description": "Application logging level",
                        "type": "string",
                        "required": False,
                        "example": "INFO",
                        "validation": "Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
                        "default": "INFO",
                        "performance_note": "DEBUG level increases log volume significantly"
                    },
                    "METRICS_ENABLED": {
                        "description": "Enable Prometheus metrics collection",
                        "type": "boolean",
                        "required": False,
                        "example": True,
                        "validation": "true or false",
                        "default": True,
                        "monitoring_note": "Required for production monitoring dashboards"
                    }
                }
            }
        }
    
    def load_service_guides(self) -> Dict[str, Any]:
        """Load detailed service configuration guides"""
        return {
            "database_setup": {
                "title": "Database Setup Guide",
                "steps": [
                    "Create Supabase account at https://supabase.com",
                    "Create new project in Supabase dashboard",
                    "Navigate to Settings > API to get your keys",
                    "Copy Project URL and API keys to .env file",
                    "Run database schema: Execute core_infra/database/schema.sql",
                    "Verify tables are created in Supabase dashboard"
                ],
                "troubleshooting": [
                    "If connection fails, check SUPABASE_URL format",
                    "Ensure SERVICE_ROLE_KEY has proper permissions",
                    "Verify database schema was applied successfully"
                ]
            },
            "ai_configuration": {
                "title": "AI Services Configuration",
                "steps": [
                    "Obtain OpenAI API key from https://platform.openai.com",
                    "Get Claude API key from https://console.anthropic.com",
                    "Configure keys in .env file",
                    "Set appropriate model parameters (temperature, max_tokens)",
                    "Enable LangSmith tracing for monitoring (optional)",
                    "Test AI services with sample requests"
                ],
                "best_practices": [
                    "Use different API keys for development and production",
                    "Monitor token usage and set up billing alerts",
                    "Implement proper error handling for API failures"
                ]
            },
            "monitoring_setup": {
                "title": "Monitoring and Observability",
                "steps": [
                    "Enable Jaeger tracing in docker-compose.yml",
                    "Configure Prometheus metrics collection",
                    "Set up log aggregation with appropriate log levels",
                    "Configure health check endpoints",
                    "Set up alerting for critical failures"
                ],
                "endpoints": [
                    "Jaeger UI: http://localhost:16686",
                    "Prometheus: http://localhost:9090",
                    "Health Check: http://localhost:8000/v1/health",
                    "Metrics: http://localhost:8000/v1/metrics"
                ]
            }
        }

    def render_search_interface(self):
        """Render the search interface"""
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        st.subheader("🔍 Search Documentation")
        
        search_query = st.text_input(
            "Search for features, APIs, configuration, or deployment guides:",
            placeholder="e.g., AML monitoring, JWT authentication, Docker setup..."
        )
        
        if search_query:
            results = self.search_documentation(search_query)
            if results:
                st.write(f"Found {len(results)} results:")
                for result in results:
                    with st.expander(f"📄 {result['title']} - {result['category']}"):
                        st.markdown(result['content'])
                        if result.get('related_config'):
                            st.subheader("Related Configuration:")
                            for key, desc in result['related_config'].items():
                                st.markdown(f'<div class="env-variable">{key}: {desc}</div>', unsafe_allow_html=True)
            else:
                st.warning("No results found. Try different keywords.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def log_search_query(self, query: str, results_count: int, execution_time: float):
        """Log search query to database via API"""
        if not self.log_search_queries:
            return
            
        try:
            import requests
            
            log_data = {
                "search_query": query,
                "search_type": "documentation_search",
                "results_count": results_count,
                "execution_time_ms": int(execution_time * 1000),
                "tenant_id": "ui-portal-tenant"
            }
            
            # Make API call to log search
            requests.post(
                f"{self.base_url}/{self.api_version}/analytics/log-search",
                json=log_data,
                timeout=5
            )
        except Exception as e:
            print(f"Failed to log search query: {str(e)}")
    
    def search_documentation(self, query: str) -> List[Dict[str, Any]]:
        """Search through documentation content"""
        start_time = datetime.now()
        results = []
        query_lower = query.lower()
        
        # Search through services
        for service_key, service_data in self.documentation_data["services"].items():
            if (query_lower in service_data["title"].lower() or 
                query_lower in service_data["description"].lower() or
                any(query_lower in feature.lower() for feature in service_data["features"])):
                results.append({
                    "title": service_data["title"],
                    "category": "Service",
                    "content": f"**Description:** {service_data['description']}\n\n**Features:**\n" + 
                              "\n".join([f"• {feature}" for feature in service_data["features"]]),
                    "related_config": service_data.get("configuration", {})
                })
        
        # Search through API endpoints
        for category, endpoints in self.api_endpoints.items():
            for endpoint, details in endpoints.items():
                if (query_lower in endpoint.lower() or 
                    query_lower in details["description"].lower()):
                    results.append({
                        "title": f"{endpoint}",
                        "category": f"API - {category.title()}",
                        "content": f"**Description:** {details['description']}\n\n**Parameters:** {details['parameters']}\n\n**Response:** {details['response']}"
                    })
        
        # Search through field guides
        for category_key, category_data in self.field_guides.items():
            for field_name, field_info in category_data["fields"].items():
                if (query_lower in field_name.lower() or 
                    query_lower in field_info.get("description", "").lower()):
                    results.append({
                        "title": f"{field_name}",
                        "category": f"Field - {category_data['title']}",
                        "content": f"**Description:** {field_info['description']}\n\n**Type:** {field_info['type']}\n\n**Example:** {field_info['example']}"
                    })
        
        # Log search query
        execution_time = (datetime.now() - start_time).total_seconds()
        self.log_search_query(query, len(results), execution_time)
        
        return results

    def render_main_interface(self):
        """Render the main documentation interface"""
        # Header
        st.markdown("""
        <div class="main-header">
            <h1>📚 Regulens AI Documentation Portal</h1>
            <p>Comprehensive guides, API documentation, and deployment instructions</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Search interface
        self.render_search_interface()
        
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "🏠 Platform Overview", 
            "🛠️ Services Guide", 
            "🔌 API Reference", 
            "📝 Field Guide",
            "🚀 Deployment", 
            "🔧 Configuration",
            "📋 Complete Feature List",
            "🏗️ Software Architecture"
        ])
        
        with tab1:
            self.render_platform_overview()
        
        with tab2:
            self.render_services_guide()
        
        with tab3:
            self.render_api_reference()
        
        with tab4:
            self.render_field_level_guide()
        
        with tab5:
            self.render_deployment_guide()
        
        with tab6:
            self.render_configuration_guide()
            
        with tab7:
            self.render_complete_feature_list()
            
        with tab8:
            self.render_software_architecture()

    def render_platform_overview(self):
        """Render platform overview section"""
        overview = self.documentation_data["platform_overview"]
        
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.header("Platform Overview")
        st.write(overview["description"])
        
        st.subheader("🚀 Key Features")
        for feature in overview["key_features"]:
            st.markdown(f'<div class="feature-card">✅ {feature}</div>', unsafe_allow_html=True)
        
        st.subheader("🏗️ Architecture")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Core Components:**")
            for key, value in overview["architecture"].items():
                st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
        
        with col2:
            st.write("**Technology Stack:**")
            tech_stack = [
                "FastAPI + Python for APIs",
                "Supabase PostgreSQL for data",
                "Docker for containerization",
                "Streamlit for UI portals",
                "OpenAI/Claude for AI features",
                "Jaeger for distributed tracing"
            ]
            for tech in tech_stack:
                st.markdown(f"• {tech}")
        
        st.markdown('</div>', unsafe_allow_html=True)

    def render_services_guide(self):
        """Render detailed services guide"""
        st.header("🛠️ Services Guide")
        
        service_options = list(self.documentation_data["services"].keys())
        selected_service = st.selectbox(
            "Select a service to view detailed documentation:",
            options=service_options,
            format_func=lambda x: self.documentation_data["services"][x]["title"]
        )
        
        if selected_service:
            service_data = self.documentation_data["services"][selected_service]
            
            st.markdown('<div class="guide-section">', unsafe_allow_html=True)
            st.subheader(f"📋 {service_data['title']}")
            st.write(service_data["description"])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🎯 Features:**")
                for feature in service_data["features"]:
                    st.markdown(f"• {feature}")
                
                st.write("**🔌 API Endpoints:**")
                for endpoint in service_data["endpoints"]:
                    st.markdown(f'<div class="api-endpoint">{endpoint}</div>', unsafe_allow_html=True)
            
            with col2:
                st.write("**⚙️ Configuration Variables:**")
                for var, desc in service_data["configuration"].items():
                    st.markdown(f'<div class="env-variable">{var}</div>', unsafe_allow_html=True)
                    st.caption(desc)
            
            # Add testing section
            st.subheader("🧪 Testing This Service")
            st.info("Use the Testing Portal to interactively test this service's endpoints and functionality.")
            
            if st.button(f"Open {service_data['title']} in Testing Portal", key=f"test_{selected_service}"):
                st.markdown(f'<a href="http://localhost:8502?service={selected_service}" target="_blank">Open Testing Portal</a>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    def render_api_reference(self):
        """Render API reference documentation"""
        st.header("🔌 API Reference")
        
        # Quick links to Swagger
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="success-box">
                <h4>📖 Interactive API Docs</h4>
                <p>Complete Swagger documentation with live testing</p>
                <a href="http://localhost:8000/docs" target="_blank">Open Swagger UI →</a>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="success-box">
                <h4>📚 ReDoc Documentation</h4>
                <p>Alternative API documentation format</p>
                <a href="http://localhost:8000/redoc" target="_blank">Open ReDoc →</a>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="success-box">
                <h4>🧪 Testing Portal</h4>
                <p>Interactive service testing interface</p>
                <a href="http://localhost:8502" target="_blank">Open Testing Portal →</a>
            </div>
            """, unsafe_allow_html=True)
        
        # API categories
        for category, endpoints in self.api_endpoints.items():
            with st.expander(f"📁 {category.title()} APIs"):
                for endpoint, details in endpoints.items():
                    st.markdown(f'<div class="api-endpoint">{endpoint}</div>', unsafe_allow_html=True)
                    st.write(f"**Description:** {details['description']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Parameters:**")
                        st.json(details["parameters"])
                    with col2:
                        st.write("**Response:**")
                        st.json(details["response"])
                    st.divider()

    def render_deployment_guide(self):
        """Render comprehensive deployment guide"""
        st.header("🚀 Deployment Guide")
        
        deployment_data = self.documentation_data["deployment"]
        
        # Prerequisites
        st.subheader("📋 Prerequisites")
        for prereq in deployment_data["prerequisites"]:
            st.markdown(f"• {prereq}")
        
        # Quick Start
        st.subheader("⚡ Quick Start")
        st.markdown("""
        <div class="code-block">
        # 1. Clone the repository
        git clone <repository-url>
        cd regulens-ai

        # 2. Configure environment
        cp .env.example .env
        # Edit .env with your configuration

        # 3. One-click installation
        chmod +x oneclickinstall.sh
        ./oneclickinstall.sh

        # 4. Verify installation
        curl http://localhost:8000/v1/health
        </div>
        """, unsafe_allow_html=True)
        
        # Detailed Setup Steps
        st.subheader("📖 Detailed Setup Steps")
        for i, step in enumerate(deployment_data["setup_steps"], 1):
            with st.expander(f"Step {i}: {step}"):
                if "Configure environment" in step:
                    st.write("Key environment variables to configure:")
                    env_vars = [
                        ("SUPABASE_URL", "Your Supabase project URL"),
                        ("SUPABASE_SERVICE_ROLE_KEY", "Service role key from Supabase"),
                        ("OPENAI_API_KEY", "OpenAI API key (optional for AI features)"),
                        ("JWT_SECRET_KEY", "Secure random string for JWT tokens")
                    ]
                    for var, desc in env_vars:
                        st.markdown(f'<div class="env-variable">{var}</div>', unsafe_allow_html=True)
                        st.caption(desc)
                
                elif "one-click installer" in step.lower():
                    st.code("""
                    # The installer will:
                    # 1. Pull required Docker images
                    # 2. Set up network configuration
                    # 3. Initialize database schema
                    # 4. Start all services
                    # 5. Verify health checks
                    
                    ./oneclickinstall.sh
                    """)
                
                elif "Verify services" in step:
                    st.write("Check that all services are running:")
                    st.code("""
                    # Check main API
                    curl http://localhost:8000/v1/health
                    
                    # Check documentation portal
                    curl http://localhost:8501
                    
                    # Check testing portal
                    curl http://localhost:8502
                    
                    # View running containers
                    docker ps
                    """)
        
        # Production Considerations
        st.subheader("🏭 Production Deployment")
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.write("**Important production considerations:**")
        for consideration in deployment_data["production_considerations"]:
            st.markdown(f"⚠️ {consideration}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Troubleshooting
        st.subheader("🔧 Troubleshooting")
        troubleshooting_guide = {
            "Database Connection Issues": [
                "Verify Supabase URL and keys in .env",
                "Check network connectivity to Supabase",
                "Ensure database schema was applied"
            ],
            "Docker Issues": [
                "Ensure Docker daemon is running",
                "Check port availability (8000, 8501, 8502)",
                "Verify Docker Compose version compatibility"
            ],
            "API Authentication Errors": [
                "Verify JWT_SECRET_KEY is set",
                "Check token expiration settings",
                "Ensure proper CORS configuration"
            ]
        }
        
        for issue, solutions in troubleshooting_guide.items():
            with st.expander(f"❓ {issue}"):
                for solution in solutions:
                    st.markdown(f"• {solution}")

    def render_field_level_guide(self):
        """Render comprehensive field-level documentation"""
        st.header("📝 Field-Level Configuration Guide")
        st.info("Detailed explanation of every configuration field with validation rules, examples, and best practices")
        
        # Field category selector
        field_categories = list(self.field_guides.keys())
        selected_category = st.selectbox(
            "Select field category:",
            options=field_categories,
            format_func=lambda x: self.field_guides[x]["title"]
        )
        
        if selected_category:
            category_data = self.field_guides[selected_category]
            
            st.markdown('<div class="guide-section">', unsafe_allow_html=True)
            st.subheader(f"📋 {category_data['title']}")
            
            # Search within fields
            search_term = st.text_input(
                f"Search within {category_data['title']}:",
                placeholder="e.g., JWT, API key, port..."
            )
            
            fields = category_data["fields"]
            
            # Filter fields based on search
            if search_term:
                filtered_fields = {
                    k: v for k, v in fields.items() 
                    if search_term.lower() in k.lower() or 
                    search_term.lower() in v.get("description", "").lower()
                }
            else:
                filtered_fields = fields
            
            if not filtered_fields:
                st.warning("No fields found matching your search term.")
            else:
                st.write(f"**Found {len(filtered_fields)} field(s):**")
                
                for field_name, field_info in filtered_fields.items():
                    with st.expander(f"🔧 {field_name}", expanded=False):
                        
                        # Basic info
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Description:** {field_info['description']}")
                            st.markdown(f"**Type:** `{field_info['type']}`")
                            
                            if field_info.get('required'):
                                st.markdown("**Required:** ✅ Yes")
                            else:
                                st.markdown("**Required:** ⚪ No")
                        
                        with col2:
                            st.markdown("**Example:**")
                            st.code(f"{field_name}={field_info['example']}")
                            
                            if field_info.get('default'):
                                st.markdown(f"**Default:** `{field_info['default']}`")
                        
                        # Validation rules
                        if field_info.get('validation'):
                            st.markdown(f"**Validation:** {field_info['validation']}")
                        
                        # Where to find
                        if field_info.get('where_to_find'):
                            st.info(f"📍 **Where to find:** {field_info['where_to_find']}")
                        
                        # Security note
                        if field_info.get('security_note'):
                            st.error(f"🔒 **Security:** {field_info['security_note']}")
                        
                        # Performance note
                        if field_info.get('performance_note'):
                            st.warning(f"⚡ **Performance:** {field_info['performance_note']}")
                        
                        # Compliance note
                        if field_info.get('compliance_note'):
                            st.info(f"📋 **Compliance:** {field_info['compliance_note']}")
                        
                        # Cost note
                        if field_info.get('cost_note'):
                            st.warning(f"💰 **Cost:** {field_info['cost_note']}")
                        
                        # Business note
                        if field_info.get('business_note'):
                            st.info(f"💼 **Business:** {field_info['business_note']}")
                        
                        # Jurisdiction
                        if field_info.get('jurisdiction'):
                            st.info(f"🌍 **Jurisdiction:** {field_info['jurisdiction']}")
                        
                        # Monitoring note
                        if field_info.get('monitoring_note'):
                            st.info(f"📊 **Monitoring:** {field_info['monitoring_note']}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Configuration validation section
            st.subheader("✅ Configuration Validation")
            
            if st.button(f"Validate {category_data['title']} Configuration", key=f"validate_{selected_category}"):
                st.info("Configuration validation would check:")
                validation_items = []
                
                for field_name, field_info in fields.items():
                    if field_info.get('required'):
                        validation_items.append(f"• {field_name}: Required field presence")
                    
                    if field_info.get('validation'):
                        validation_items.append(f"• {field_name}: {field_info['validation']}")
                
                for item in validation_items[:5]:  # Show first 5
                    st.markdown(item)
                
                if len(validation_items) > 5:
                    st.markdown(f"... and {len(validation_items) - 5} more checks")

    def render_configuration_guide(self):
        """Render configuration guide with all environment variables"""
        st.header("🔧 Configuration Guide")
        
        st.info("All configuration is managed through environment variables in the .env file")
        
        # Configuration categories
        config_categories = {
            "Application": {
                "APP_NAME": "Application name for branding",
                "APP_VERSION": "Current application version",
                "APP_ENVIRONMENT": "Deployment environment (development/staging/production)",
                "DEBUG": "Enable debug mode and detailed error messages",
                "API_VERSION": "API version prefix (e.g., v1)",
                "API_PORT": "Port for the main API service",
                "API_HOST": "Host binding for the API service"
            },
            "Security": {
                "JWT_SECRET_KEY": "Secret key for JWT token signing (change in production!)",
                "JWT_ALGORITHM": "Algorithm for JWT token signing",
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "Access token expiration time",
                "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "Refresh token expiration time",
                "ENCRYPTION_KEY": "Key for encrypting sensitive data",
                "BCRYPT_ROUNDS": "BCrypt hashing rounds for password security"
            },
            "Database": {
                "SUPABASE_URL": "Supabase project URL",
                "SUPABASE_ANON_KEY": "Anonymous key from Supabase",
                "SUPABASE_SERVICE_ROLE_KEY": "Service role key with admin privileges",
                "DATABASE_URL": "PostgreSQL connection string",
                "DATABASE_POOL_SIZE": "Connection pool size",
                "DATABASE_POOL_TIMEOUT": "Connection timeout in seconds"
            },
            "AI/ML Services": {
                "OPENAI_API_KEY": "OpenAI API key for GPT models",
                "OPENAI_MODEL": "Default OpenAI model (gpt-4, gpt-3.5-turbo)",
                "OPENAI_MAX_TOKENS": "Maximum tokens per API call",
                "CLAUDE_API_KEY": "Anthropic Claude API key",
                "LANGCHAIN_TRACING_V2": "Enable LangSmith tracing",
                "LANGCHAIN_API_KEY": "LangSmith API key for tracing"
            },
            "Regulatory Data": {
                "REGULATORY_MONITOR_ENABLED": "Enable regulatory change monitoring",
                "REGULATORY_MONITOR_INTERVAL_MINUTES": "Monitoring check frequency",
                "SEC_API_KEY": "Securities and Exchange Commission API key",
                "FCA_API_KEY": "Financial Conduct Authority API key",
                "ECB_API_KEY": "European Central Bank API key"
            },
            "AML/KYC": {
                "AML_MONITORING_ENABLED": "Enable AML transaction monitoring",
                "AML_THRESHOLD_AMOUNT": "Transaction amount threshold for monitoring",
                "AML_HIGH_RISK_COUNTRIES": "Comma-separated list of high-risk country codes",
                "SANCTIONS_LIST_UPDATE_INTERVAL_HOURS": "How often to update sanctions lists",
                "PEP_SCREENING_ENABLED": "Enable Politically Exposed Person screening"
            },
            "Monitoring": {
                "JAEGER_ENABLED": "Enable Jaeger distributed tracing",
                "JAEGER_AGENT_HOST": "Jaeger agent hostname",
                "JAEGER_AGENT_PORT": "Jaeger agent port",
                "JAEGER_SERVICE_NAME": "Service name for tracing",
                "METRICS_ENABLED": "Enable Prometheus metrics collection",
                "LOG_LEVEL": "Logging level (DEBUG, INFO, WARNING, ERROR)"
            }
        }
        
        for category, variables in config_categories.items():
            with st.expander(f"⚙️ {category} Configuration"):
                for var, description in variables.items():
                    st.markdown(f'<div class="env-variable">{var}</div>', unsafe_allow_html=True)
                    st.caption(description)
                    if "KEY" in var and "SECRET" in var:
                        st.markdown('<div class="warning-box">🔐 Security: Generate a secure random value for production!</div>', unsafe_allow_html=True)
        
        # Configuration validation
        st.subheader("✅ Configuration Validation")
        if st.button("Validate Current Configuration"):
            st.info("Configuration validation would check:")
            validation_checks = [
                "Database connectivity",
                "Required API keys presence",
                "Security settings strength",
                "Service dependencies",
                "Port availability"
            ]
            for check in validation_checks:
                st.markdown(f"• {check}")

    def render_complete_feature_list(self):
        """Render comprehensive feature list for the entire platform"""
        st.header("📋 Complete Feature List")
        st.markdown("""
        <div class="success-box">
        <h4>🎯 Regulens AI Financial Compliance Platform</h4>
        <p>Complete catalog of all features across 6 implementation phases</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Phase-based feature organization
        phases = {
            "Phase 1: Foundation Infrastructure": {
                "icon": "🏗️",
                "status": "✅ Completed",
                "features": [
                    "Multi-Tenant Architecture with strict tenant isolation",
                    "User Authentication & Role-Based Access Control (RBAC)",
                    "Comprehensive Database Schema (25+ tables)",
                    "RESTful API Infrastructure with FastAPI",
                    "Docker Containerization with docker-compose",
                    "Distributed Tracing with Jaeger integration",
                    "Prometheus Metrics Collection",
                    "Audit Logging & Compliance Trails",
                    "Security Framework (HTTPS, JWT, API Keys)",
                    "Health Check & Monitoring Endpoints"
                ]
            },
            "Phase 2: Regulatory Engine": {
                "icon": "📋",
                "status": "✅ Completed", 
                "features": [
                    "Real-time Regulatory Change Monitoring",
                    "Multi-Source Data Ingestion (SEC, FCA, ECB, FINCEN)",
                    "RSS Feed Monitoring & Content Analysis",
                    "AI-Powered Document Analysis with GPT-4/Claude",
                    "Vector Database for Semantic Search (Qdrant)",
                    "Document Embedding & Similarity Detection",
                    "Automated Change Impact Assessment",
                    "Intelligent Alert System with Priority Scoring",
                    "Task Scheduler for Background Processing",
                    "Document Deduplication & Fingerprinting"
                ]
            },
            "Phase 3: Compliance Workflows": {
                "icon": "🔄",
                "status": "✅ Completed",
                "features": [
                    "Automated Workflow Orchestration Engine",
                    "Dynamic Task Management & Assignment",
                    "Business Impact Assessment Automation",
                    "Multi-trigger Workflow Execution (Events, Schedule, Manual)",
                    "Task Evidence Collection & Validation",
                    "Escalation Management with SLA Monitoring",
                    "Deadline Tracking & Alert System",
                    "Compliance Program Template Library",
                    "Workflow Performance Analytics",
                    "Audit Trail for All Workflow Activities"
                ]
            },
            "Phase 4: Advanced Analytics & Intelligence": {
                "icon": "📊",
                "status": "✅ Completed",
                "features": [
                    "AI-Powered Risk Scoring Models",
                    "Customer Risk Assessment & Grading",
                    "Transaction Risk Analysis with ML",
                    "Predictive Compliance Analytics",
                    "Real-time Compliance Metrics Dashboard",
                    "Performance Benchmarking Against Industry Standards",
                    "Regulatory Intelligence Generation",
                    "Anomaly Detection in Compliance Data",
                    "Time Series Forecasting for Compliance Trends",
                    "Interactive Analytics Dashboards"
                ]
            },
            "Phase 5: Enterprise Integrations": {
                "icon": "🔗",
                "status": "✅ Completed",
                "features": [
                    "GRC System Integration (Archer, ServiceNow, MetricStream)",
                    "Core Banking System Connectivity (Temenos, Finacle, Flexcube)",
                    "External Data Source Integration (OFAC, EU Sanctions, UN)",
                    "PEP (Politically Exposed Persons) Screening",
                    "Credit Bureau Integration (Experian, Equifax, TransUnion)",
                    "Document Management System Integration (SharePoint, Box, Google Drive)",
                    "Market Data Integration (Refinitiv, Bloomberg)",
                    "Real-time Sanctions Screening",
                    "Automated Data Synchronization",
                    "API Rate Limiting & Circuit Breaker Patterns"
                ]
            },
            "Phase 6: Advanced AI & Automation": {
                "icon": "🤖",
                "status": "✅ Completed",
                "features": [
                    "Natural Language Processing Suite (Multi-provider)",
                    "Financial Document Entity Extraction",
                    "Sentiment Analysis for Regulatory Content",
                    "Intelligent Chatbot for Compliance Q&A",
                    "Computer Vision for Document Classification",
                    "KYC Document Verification with OCR",
                    "Intelligent Automation Execution Engine",
                    "RPA Integration (UiPath, Blue Prism, Automation Anywhere)",
                    "Deep Learning Model Training & Deployment",
                    "AutoML Pipeline for Custom Model Creation"
                ]
            }
        }
        
        # Feature statistics
        total_features = sum(len(phase["features"]) for phase in phases.values())
        completed_phases = sum(1 for phase in phases.values() if "Completed" in phase["status"])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Features", total_features)
        with col2:
            st.metric("Completed Phases", f"{completed_phases}/6")
        with col3:
            st.metric("API Endpoints", "50+")
        with col4:
            st.metric("Database Tables", "25+")
        
        st.divider()
        
        # Render each phase
        for phase_name, phase_data in phases.items():
            with st.expander(f"{phase_data['icon']} {phase_name} ({phase_data['status']})", expanded=False):
                st.markdown(f"**Status:** {phase_data['status']}")
                st.markdown(f"**Features:** {len(phase_data['features'])} implemented")
                
                # Two-column layout for features
                col1, col2 = st.columns(2)
                features = phase_data["features"]
                mid_point = len(features) // 2
                
                with col1:
                    for feature in features[:mid_point]:
                        st.markdown(f"✅ {feature}")
                        
                with col2:
                    for feature in features[mid_point:]:
                        st.markdown(f"✅ {feature}")
        
        # Core Capabilities Summary
        st.divider()
        st.subheader("🎯 Core Platform Capabilities")
        
        capability_categories = {
            "🛡️ Compliance & Risk Management": [
                "Real-time regulatory change monitoring",
                "Automated AML/KYC compliance",
                "Risk scoring and assessment",
                "Sanctions and PEP screening",
                "Transaction monitoring"
            ],
            "🤖 AI & Machine Learning": [
                "Multi-provider AI integration (OpenAI, Claude, HuggingFace)",
                "Natural language processing",
                "Computer vision for document analysis",
                "Predictive analytics and forecasting",
                "Custom ML model training"
            ],
            "🔄 Workflow & Automation": [
                "Automated compliance workflows",
                "Task management and assignment",
                "RPA tool integration",
                "Intelligent document processing",
                "Business process automation"
            ],
            "📊 Analytics & Reporting": [
                "Real-time compliance dashboards",
                "Performance benchmarking",
                "Regulatory intelligence",
                "Audit-ready reporting",
                "Advanced analytics"
            ],
            "🔗 Enterprise Integration": [
                "Core banking system connectivity",
                "GRC platform integration",
                "Document management systems",
                "External data source integration",
                "API-first architecture"
            ],
            "🏗️ Infrastructure & Security": [
                "Multi-tenant architecture",
                "Enterprise-grade security",
                "Docker containerization",
                "Distributed tracing",
                "Comprehensive audit trails"
            ]
        }
        
        for category, capabilities in capability_categories.items():
            with st.expander(f"{category}", expanded=False):
                for capability in capabilities:
                    st.markdown(f"• {capability}")
        
        # Technology Integrations
        st.divider()
        st.subheader("🔌 Supported Integrations")
        
        integration_cols = st.columns(3)
        
        with integration_cols[0]:
            st.markdown("**🏦 Core Banking Systems**")
            banking_systems = ["Temenos T24", "Infosys Finacle", "Oracle Flexcube", "Custom REST APIs"]
            for system in banking_systems:
                st.markdown(f"• {system}")
                
            st.markdown("**🛡️ GRC Platforms**")
            grc_systems = ["RSA Archer", "ServiceNow GRC", "MetricStream", "Custom integrations"]
            for system in grc_systems:
                st.markdown(f"• {system}")
        
        with integration_cols[1]:
            st.markdown("**🤖 RPA Tools**")
            rpa_tools = ["UiPath", "Blue Prism", "Automation Anywhere", "Microsoft Power Automate"]
            for tool in rpa_tools:
                st.markdown(f"• {tool}")
                
            st.markdown("**🧠 AI Providers**")
            ai_providers = ["OpenAI GPT-4", "Anthropic Claude", "HuggingFace", "Azure Cognitive Services", "AWS Textract"]
            for provider in ai_providers:
                st.markdown(f"• {provider}")
        
        with integration_cols[2]:
            st.markdown("**📊 Data Sources**")
            data_sources = ["OFAC Sanctions", "EU Consolidated List", "UN Sanctions", "PEP Databases", "Market Data"]
            for source in data_sources:
                st.markdown(f"• {source}")
                
            st.markdown("**📁 Document Systems**")
            doc_systems = ["Microsoft SharePoint", "Box", "Google Drive", "AWS S3", "Local File Systems"]
            for system in doc_systems:
                st.markdown(f"• {system}")

    def render_software_architecture(self):
        """Render comprehensive software architecture documentation"""
        st.header("🏗️ Software Architecture & Technology Stack")
        st.markdown("""
        <div class="success-box">
        <h4>🎯 Enterprise-Grade Financial Compliance Platform</h4>
        <p>Comprehensive overview of all software components, their usage, and system architecture</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Architecture diagram using Mermaid
        st.subheader("📐 System Architecture Diagram")
        
        # Create the Mermaid diagram
        architecture_diagram = """
        graph TB
            %% External Systems
            subgraph "External Systems"
                SEC[SEC API]
                FCA[FCA API]
                ECB[ECB API]
                OFAC[OFAC API]
                OpenAI[OpenAI GPT-4]
                Claude[Anthropic Claude]
                Supabase[Supabase Cloud]
            end
            
            %% Load Balancer & API Gateway
            LB[Load Balancer<br/>nginx]
            
            %% Core Services Layer
            subgraph "Core Services Layer"
                API[FastAPI Application<br/>Python 3.9+]
                Auth[Authentication Service<br/>JWT + RBAC]
                RegMon[Regulatory Monitor<br/>Real-time scanning]
                Workflow[Workflow Engine<br/>Task orchestration]
                Analytics[Analytics Engine<br/>ML + Predictive models]
                NLP[NLP Service<br/>Multi-provider AI]
                CV[Computer Vision<br/>Document processing]
                Automation[Automation Engine<br/>RPA integration]
            end
            
            %% Data & Storage Layer
            subgraph "Data & Storage Layer"
                DB[(Supabase PostgreSQL<br/>Multi-tenant)]
                Vector[(Qdrant Vector DB<br/>Semantic search)]
                Storage[Supabase Storage<br/>Document files]
                Redis[Redis Cache<br/>Session + performance]
            end
            
            %% Monitoring & Observability
            subgraph "Monitoring & Observability"
                Jaeger[Jaeger Tracing<br/>Distributed tracing]
                Prometheus[Prometheus<br/>Metrics collection]
                Grafana[Grafana<br/>Dashboards]
                Logs[Structured Logging<br/>JSON logs]
            end
            
            %% User Interfaces
            subgraph "User Interfaces"
                DocPortal[Documentation Portal<br/>Streamlit]
                TestPortal[Testing Portal<br/>Streamlit]
                Swagger[API Documentation<br/>Swagger UI]
            end
            
            %% Connections
            SEC --> API
            FCA --> API
            ECB --> API
            OFAC --> API
            OpenAI --> NLP
            Claude --> NLP
            
            LB --> API
            
            API --> Auth
            API --> RegMon
            API --> Workflow
            API --> Analytics
            API --> NLP
            API --> CV
            API --> Automation
            
            RegMon --> DB
            RegMon --> Vector
            RegMon --> Storage
            
            Workflow --> DB
            Analytics --> DB
            NLP --> DB
            CV --> DB
            Automation --> DB
            
            API --> Redis
            
            API --> Jaeger
            API --> Prometheus
            RegMon --> Jaeger
            Workflow --> Jaeger
            
            DocPortal --> API
            TestPortal --> API
            
            Supabase -.-> DB
            Supabase -.-> Storage
            
            %% Styling
            classDef external fill:#e1f5fe,stroke:#01579b,stroke-width:2px
            classDef core fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
            classDef data fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
            classDef monitor fill:#fff3e0,stroke:#e65100,stroke-width:2px
            classDef ui fill:#fce4ec,stroke:#880e4f,stroke-width:2px
            
            class SEC,FCA,ECB,OFAC,OpenAI,Claude,Supabase external
            class API,Auth,RegMon,Workflow,Analytics,NLP,CV,Automation core
            class DB,Vector,Storage,Redis data
            class Jaeger,Prometheus,Grafana,Logs monitor
            class DocPortal,TestPortal,Swagger ui
        """
        
        # Display the architecture diagram
        st.markdown("""
        <div class="success-box">
        <h4>📐 Professional System Architecture</h4>
        <p>The diagram below shows the complete system architecture with all components and their relationships.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display the Mermaid diagram code for reference
        with st.expander("📋 View Architecture Diagram Source (Mermaid)", expanded=False):
            st.code(architecture_diagram, language="mermaid")
            st.info("💡 Copy this code to Mermaid Live Editor (https://mermaid.live) for interactive viewing")
        
        # Alternative architecture representation
        st.markdown("### 🔄 Data Flow Architecture")
        
        flow_cols = st.columns(4)
        with flow_cols[0]:
            st.markdown("""
            **📥 Input Layer**
            - External APIs
            - User Requests  
            - File Uploads
            - Scheduled Tasks
            """)
        
        with flow_cols[1]:
            st.markdown("""
            **⚙️ Processing Layer**
            - FastAPI Router
            - Service Handlers
            - AI Processing
            - Background Jobs
            """)
        
        with flow_cols[2]:
            st.markdown("""
            **💾 Storage Layer**
            - PostgreSQL DB
            - Vector Database
            - File Storage
            - Cache Layer
            """)
        
        with flow_cols[3]:
            st.markdown("""
            **📊 Output Layer**
            - API Responses
            - Real-time Alerts
            - Reports & Analytics
            - UI Portals
            """)
        
        st.divider()
        
        # Technology Stack Overview
        st.subheader("💻 Complete Technology Stack")
        
        tech_categories = {
            "🐍 Backend & API": {
                "FastAPI": {
                    "version": "0.104+",
                    "usage": "Core REST API framework with automatic OpenAPI documentation",
                    "features": "Async support, dependency injection, automatic validation"
                },
                "Python": {
                    "version": "3.9+",
                    "usage": "Primary backend programming language",
                    "features": "Type hints, async/await, comprehensive stdlib"
                },
                "Pydantic": {
                    "version": "2.0+",
                    "usage": "Data validation and settings management",
                    "features": "Type validation, JSON schema generation, configuration"
                },
                "Uvicorn": {
                    "version": "Latest",
                    "usage": "ASGI server for FastAPI application",
                    "features": "High performance, WebSocket support, auto-reload"
                }
            },
            "🗄️ Database & Storage": {
                "Supabase PostgreSQL": {
                    "version": "15+",
                    "usage": "Primary database with multi-tenant architecture",
                    "features": "JSONB support, full-text search, RLS, real-time subscriptions"
                },
                "Qdrant": {
                    "version": "1.7+",
                    "usage": "Vector database for semantic search and embeddings",
                    "features": "Fast similarity search, filtering, clustering"
                },
                "Redis": {
                    "version": "7.0+",
                    "usage": "Caching, session storage, and background job queue",
                    "features": "In-memory performance, persistence, pub/sub"
                },
                "Supabase Storage": {
                    "version": "Latest",
                    "usage": "File storage for documents and media",
                    "features": "CDN integration, access control, image transformations"
                }
            },
            "🤖 AI & Machine Learning": {
                "OpenAI GPT-4": {
                    "version": "Latest API",
                    "usage": "Advanced language understanding and generation",
                    "features": "Function calling, JSON mode, vision capabilities"
                },
                "Anthropic Claude": {
                    "version": "3.5 Sonnet",
                    "usage": "Alternative LLM with strong reasoning capabilities",
                    "features": "Large context window, safety features, structured output"
                },
                "HuggingFace Transformers": {
                    "version": "4.35+",
                    "usage": "Open-source models for NLP tasks",
                    "features": "Pre-trained models, fine-tuning, tokenization"
                },
                "FastEmbed": {
                    "version": "Latest",
                    "usage": "Fast text embeddings for vector database",
                    "features": "Multiple model support, optimized inference"
                },
                "spaCy": {
                    "version": "3.7+",
                    "usage": "Industrial-strength NLP library",
                    "features": "Named entity recognition, POS tagging, dependency parsing"
                }
            },
            "👁️ Computer Vision": {
                "AWS Textract": {
                    "version": "Latest API",
                    "usage": "Document OCR and form recognition",
                    "features": "Table extraction, form data, handwriting recognition"
                },
                "Azure Form Recognizer": {
                    "version": "Latest API",
                    "usage": "Intelligent document processing",
                    "features": "Custom models, receipt processing, ID document analysis"
                },
                "Tesseract OCR": {
                    "version": "5.0+",
                    "usage": "Open-source OCR engine",
                    "features": "Multi-language support, configurable output"
                },
                "OpenCV": {
                    "version": "4.8+",
                    "usage": "Image preprocessing and analysis",
                    "features": "Image enhancement, contour detection, morphological operations"
                },
                "Pillow (PIL)": {
                    "version": "10.0+",
                    "usage": "Image manipulation and format conversion",
                    "features": "Multiple formats, transformations, metadata extraction"
                }
            },
            "🔄 Integration & Automation": {
                "aiohttp": {
                    "version": "3.9+",
                    "usage": "Async HTTP client for external API integration",
                    "features": "Connection pooling, timeout handling, SSL support"
                },
                "Celery": {
                    "version": "5.3+",
                    "usage": "Distributed task queue for background processing",
                    "features": "Scheduling, retry logic, monitoring"
                },
                "APScheduler": {
                    "version": "3.10+",
                    "usage": "Advanced Python scheduler for recurring tasks",
                    "features": "Cron-like scheduling, job persistence, clustering"
                },
                "Requests": {
                    "version": "2.31+",
                    "usage": "HTTP library for synchronous API calls",
                    "features": "Session management, authentication, proxies"
                }
            },
            "📊 Monitoring & Observability": {
                "Jaeger": {
                    "version": "1.50+",
                    "usage": "Distributed tracing for microservices",
                    "features": "Request tracing, performance analysis, dependency mapping"
                },
                "OpenTelemetry": {
                    "version": "1.20+",
                    "usage": "Observability framework for traces and metrics",
                    "features": "Vendor-neutral, auto-instrumentation, custom metrics"
                },
                "Prometheus": {
                    "version": "2.47+",
                    "usage": "Metrics collection and alerting",
                    "features": "Time series database, PromQL, alert manager"
                },
                "Grafana": {
                    "version": "10.0+",
                    "usage": "Metrics visualization and dashboards",
                    "features": "Multiple data sources, alerting, custom dashboards"
                },
                "Structlog": {
                    "version": "23.1+",
                    "usage": "Structured logging with JSON output",
                    "features": "Context preservation, log enrichment, formatting"
                }
            },
            "🐳 Containerization & Deployment": {
                "Docker": {
                    "version": "24.0+",
                    "usage": "Application containerization",
                    "features": "Multi-stage builds, layer caching, security scanning"
                },
                "Docker Compose": {
                    "version": "2.21+",
                    "usage": "Multi-container application orchestration",
                    "features": "Service dependencies, network isolation, volume management"
                },
                "nginx": {
                    "version": "1.25+",
                    "usage": "Reverse proxy and load balancer",
                    "features": "SSL termination, static file serving, request routing"
                }
            },
            "🖥️ User Interface": {
                "Streamlit": {
                    "version": "1.28+",
                    "usage": "Web interface for documentation and testing portals",
                    "features": "Reactive UI, built-in components, easy deployment"
                },
                "Swagger UI": {
                    "version": "Latest",
                    "usage": "Interactive API documentation",
                    "features": "API testing, schema validation, code generation"
                },
                "ReDoc": {
                    "version": "Latest",
                    "usage": "Alternative API documentation interface",
                    "features": "Clean design, search functionality, mobile responsive"
                }
            },
            "🔐 Security & Authentication": {
                "PyJWT": {
                    "version": "2.8+",
                    "usage": "JSON Web Token implementation",
                    "features": "Token generation/validation, algorithm support, expiration"
                },
                "Passlib": {
                    "version": "1.7+",
                    "usage": "Password hashing and verification",
                    "features": "Multiple hash algorithms, bcrypt support, migration"
                },
                "python-multipart": {
                    "version": "0.0.6+",
                    "usage": "Multipart form data parsing",
                    "features": "File upload handling, form parsing, streaming"
                }
            },
            "📊 Data Processing": {
                "Pandas": {
                    "version": "2.1+",
                    "usage": "Data manipulation and analysis",
                    "features": "DataFrame operations, CSV/Excel handling, aggregations"
                },
                "NumPy": {
                    "version": "1.25+",
                    "usage": "Numerical computing and array operations",
                    "features": "Mathematical functions, array operations, linear algebra"
                },
                "python-dateutil": {
                    "version": "2.8+",
                    "usage": "Advanced date/time parsing and manipulation",
                    "features": "Timezone handling, relative deltas, parsing"
                }
            }
        }
        
        # Render technology categories
        for category, technologies in tech_categories.items():
            with st.expander(f"{category}", expanded=False):
                for tech_name, tech_info in technologies.items():
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.markdown(f"**{tech_name}**")
                        st.caption(f"Version: {tech_info['version']}")
                    
                    with col2:
                        st.markdown(f"**Usage:** {tech_info['usage']}")
                        st.markdown(f"**Key Features:** {tech_info['features']}")
                    
                    st.divider()
        
        # Deployment Architecture
        st.divider()
        st.subheader("🚀 Deployment Architecture")
        
        deployment_info = {
            "🐳 Container Strategy": [
                "Multi-container Docker Compose setup",
                "Service-specific containers with health checks",
                "Shared networks and volume mounts",
                "Environment-based configuration",
                "Automatic restart policies"
            ],
            "🔗 Service Communication": [
                "HTTP/HTTPS for API communication",
                "PostgreSQL connections via connection pooling",
                "Redis for caching and session management",
                "Message queues for async processing",
                "gRPC for high-performance internal services"
            ],
            "📊 Data Flow": [
                "External APIs → Regulatory Monitor → Database",
                "User Requests → FastAPI → Services → Database",
                "Background Tasks → Celery → Redis Queue",
                "Documents → Storage → Vector Database",
                "Metrics → Prometheus → Grafana"
            ],
            "🛡️ Security Layers": [
                "TLS encryption for all external communications",
                "JWT-based authentication with RBAC",
                "Database-level row-level security (RLS)",
                "API rate limiting and request validation",
                "Docker container security best practices"
            ]
        }
        
        for section, items in deployment_info.items():
            with st.expander(f"{section}", expanded=False):
                for item in items:
                    st.markdown(f"• {item}")
        
        # Performance Specifications
        st.divider()
        st.subheader("⚡ Performance & Scalability")
        
        perf_cols = st.columns(2)
        
        with perf_cols[0]:
            st.markdown("**📈 Performance Metrics**")
            metrics = [
                "API Response Time: < 200ms (95th percentile)",
                "Database Queries: < 50ms average",
                "Document Processing: < 5s per document",
                "Vector Search: < 100ms for similarity queries",
                "Concurrent Users: 1000+ supported",
                "Throughput: 10,000+ requests/minute"
            ]
            for metric in metrics:
                st.markdown(f"• {metric}")
        
        with perf_cols[1]:
            st.markdown("**🔄 Scalability Features**")
            scalability = [
                "Horizontal scaling via load balancing",
                "Database connection pooling",
                "Redis clustering support",
                "Microservices architecture",
                "Async processing for heavy workloads",
                "Auto-scaling container orchestration"
            ]
            for feature in scalability:
                st.markdown(f"• {feature}")
        
        # System Requirements
        st.divider()
        st.subheader("💾 System Requirements")
        
        req_cols = st.columns(3)
        
        with req_cols[0]:
            st.markdown("**🖥️ Minimum Requirements**")
            st.markdown("""
            • **CPU:** 4 cores
            • **RAM:** 8 GB
            • **Storage:** 50 GB SSD
            • **Network:** 10 Mbps
            • **OS:** Linux/macOS/Windows
            • **Docker:** 24.0+
            """)
        
        with req_cols[1]:
            st.markdown("**🚀 Recommended Specs**")
            st.markdown("""
            • **CPU:** 8+ cores
            • **RAM:** 16+ GB
            • **Storage:** 200+ GB SSD
            • **Network:** 100+ Mbps
            • **Load Balancer:** nginx/HAProxy
            • **Monitoring:** Dedicated instance
            """)
        
        with req_cols[2]:
            st.markdown("**🏢 Enterprise Setup**")
            st.markdown("""
            • **CPU:** 16+ cores
            • **RAM:** 32+ GB
            • **Storage:** 1+ TB NVMe
            • **Network:** 1+ Gbps
            • **High Availability:** Multi-zone
            • **Backup:** Automated daily
            """)

def main():
    """Main application entry point"""
    portal = DocumentationPortal()
    portal.render_main_interface()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>📚 Regulens AI Documentation Portal | 
        <a href="http://localhost:8000/docs" target="_blank">API Docs</a> | 
        <a href="http://localhost:8502" target="_blank">Testing Portal</a> | 
        <a href="http://localhost:8000/v1/health" target="_blank">System Health</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 