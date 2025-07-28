"""
Regulens AI Testing Portal
Interactive service testing interface for validating all core services
"""

import os
import json
import asyncio
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import traceback

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_ace import st_ace
import yaml

# Configuration
st.set_page_config(
    page_title="Regulens AI Testing Portal",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .test-header {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .service-card {
        background: #f8f9fa;
        border-left: 4px solid #28a745;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .test-result-success {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .test-result-error {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .test-result-warning {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .endpoint-box {
        background: #f1f3f4;
        padding: 1rem;
        border-radius: 5px;
        border-left: 3px solid #28a745;
        margin: 0.5rem 0;
        font-family: monospace;
    }
    .response-json {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        font-family: monospace;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

class TestingPortal:
    def __init__(self):
        # Get API base URL from environment or default
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_version = "v1"
        self.test_results = {}
        self.auth_token = None
        
        # Initialize session state
        if 'test_history' not in st.session_state:
            st.session_state.test_history = []
        if 'auth_token' not in st.session_state:
            st.session_state.auth_token = None
        
        # Log database test executions
        self.log_test_execution = True
    
    def get_service_definitions(self) -> Dict[str, Any]:
        """Define all testable services and their endpoints"""
        return {
            "health": {
                "title": "System Health",
                "description": "Test system health and status endpoints",
                "endpoints": {
                    "health_check": {
                        "method": "GET",
                        "url": f"/{self.api_version}/health",
                        "description": "Check overall system health",
                        "requires_auth": False,
                        "test_data": {}
                    },
                    "system_info": {
                        "method": "GET", 
                        "url": f"/{self.api_version}/info",
                        "description": "Get platform information",
                        "requires_auth": False,
                        "test_data": {}
                    },
                    "metrics": {
                        "method": "GET",
                        "url": f"/{self.api_version}/metrics",
                        "description": "Get system metrics",
                        "requires_auth": True,
                        "test_data": {}
                    }
                }
            },
            "authentication": {
                "title": "Authentication Service",
                "description": "Test user authentication and token management",
                "endpoints": {
                    "create_test_user": {
                        "method": "POST",
                        "url": f"/{self.api_version}/auth/register",
                        "description": "Create test user account",
                        "requires_auth": False,
                        "test_data": {
                            "username": "test_user",
                            "email": "test@regulens-ai.com", 
                            "password": "TestPass123!",
                            "tenant_id": "test-tenant"
                        }
                    },
                    "login": {
                        "method": "POST",
                        "url": f"/{self.api_version}/auth/login",
                        "description": "Login and obtain JWT token",
                        "requires_auth": False,
                        "test_data": {
                            "username": "test_user",
                            "password": "TestPass123!"
                        }
                    },
                    "verify_token": {
                        "method": "GET",
                        "url": f"/{self.api_version}/auth/verify",
                        "description": "Verify JWT token validity",
                        "requires_auth": True,
                        "test_data": {}
                    }
                }
            },
            "regulatory": {
                "title": "Regulatory Monitoring",
                "description": "Test regulatory data sources and monitoring",
                "endpoints": {
                    "list_sources": {
                        "method": "GET",
                        "url": f"/{self.api_version}/regulatory/sources",
                        "description": "List available regulatory sources",
                        "requires_auth": True,
                        "test_data": {}
                    },
                    "create_source": {
                        "method": "POST",
                        "url": f"/{self.api_version}/regulatory/sources",
                        "description": "Create new regulatory source",
                        "requires_auth": True,
                        "test_data": {
                            "name": "Test SEC Source",
                            "jurisdiction": "US",
                            "authority": "SEC",
                            "source_type": "api",
                            "base_url": "https://api.sec.gov",
                            "update_frequency": "daily"
                        }
                    },
                    "get_changes": {
                        "method": "GET",
                        "url": f"/{self.api_version}/regulatory/changes",
                        "description": "Get recent regulatory changes",
                        "requires_auth": True,
                        "test_data": {
                            "date_from": "2024-01-01",
                            "jurisdiction": "US"
                        }
                    }
                }
            },
            "aml": {
                "title": "AML/KYC Service",
                "description": "Test anti-money laundering and KYC features",
                "endpoints": {
                    "create_customer": {
                        "method": "POST",
                        "url": f"/{self.api_version}/aml/customers",
                        "description": "Create customer profile for testing",
                        "requires_auth": True,
                        "test_data": {
                            "customer_id": "TEST_CUST_001",
                            "first_name": "John",
                            "last_name": "Doe",
                            "date_of_birth": "1985-05-15",
                            "nationality": "US",
                            "address": {
                                "street": "123 Test St",
                                "city": "Test City",
                                "country": "US",
                                "postal_code": "12345"
                            }
                        }
                    },
                    "screen_customer": {
                        "method": "POST",
                        "url": f"/{self.api_version}/aml/customers/screen",
                        "description": "Screen customer against sanctions",
                        "requires_auth": True,
                        "test_data": {
                            "customer_id": "TEST_CUST_001",
                            "screening_type": "sanctions",
                            "include_pep": True
                        }
                    },
                    "monitor_transaction": {
                        "method": "POST",
                        "url": f"/{self.api_version}/aml/transactions/monitor",
                        "description": "Monitor transaction for AML compliance",
                        "requires_auth": True,
                        "test_data": {
                            "transaction_id": "TXN_001",
                            "customer_id": "TEST_CUST_001",
                            "amount": 25000.00,
                            "currency": "USD",
                            "transaction_type": "wire_transfer",
                            "counterparty": {
                                "name": "Test Company Ltd",
                                "country": "GB"
                            }
                        }
                    }
                }
            },
            "ai": {
                "title": "AI Services",
                "description": "Test AI-powered regulatory insights",
                "endpoints": {
                    "analyze_document": {
                        "method": "POST",
                        "url": f"/{self.api_version}/ai/analyze",
                        "description": "Analyze regulatory document with AI",
                        "requires_auth": True,
                        "test_data": {
                            "content": "The Federal Reserve announces new capital requirements for banks effective January 2024. All banks must maintain a minimum tier 1 capital ratio of 8.5%.",
                            "analysis_type": "regulatory_impact",
                            "model": "gpt-4"
                        }
                    },
                    "regulatory_qa": {
                        "method": "POST",
                        "url": f"/{self.api_version}/ai/qa",
                        "description": "Ask questions about regulations",
                        "requires_auth": True,
                        "test_data": {
                            "question": "What are the current capital requirements for banks in the US?",
                            "context": "banking_regulations",
                            "model": "gpt-4"
                        }
                    },
                    "extract_entities": {
                        "method": "POST",
                        "url": f"/{self.api_version}/ai/extract",
                        "description": "Extract entities from regulatory text",
                        "requires_auth": True,
                        "test_data": {
                            "text": "Bank of America must comply with Basel III requirements by December 31, 2024",
                            "entity_types": ["organizations", "dates", "regulations"]
                        }
                    }
                }
            },
            "compliance": {
                "title": "Compliance Workflows",
                "description": "Test compliance task and workflow management",
                "endpoints": {
                    "create_task": {
                        "method": "POST",
                        "url": f"/{self.api_version}/tasks",
                        "description": "Create compliance task",
                        "requires_auth": True,
                        "test_data": {
                            "title": "Review New Banking Regulation",
                            "description": "Analyze impact of new Fed capital requirements",
                            "priority": "high",
                            "due_date": "2024-02-15",
                            "assigned_to": "compliance_team",
                            "task_type": "regulatory_review"
                        }
                    },
                    "list_tasks": {
                        "method": "GET",
                        "url": f"/{self.api_version}/tasks",
                        "description": "List compliance tasks",
                        "requires_auth": True,
                        "test_data": {}
                    },
                    "create_workflow": {
                        "method": "POST",
                        "url": f"/{self.api_version}/workflows",
                        "description": "Create compliance workflow",
                        "requires_auth": True,
                        "test_data": {
                            "name": "Regulatory Change Review",
                            "description": "Standard workflow for reviewing regulatory changes",
                            "steps": [
                                {"name": "Initial Assessment", "assignee": "analyst"},
                                {"name": "Legal Review", "assignee": "legal_team"},
                                {"name": "Implementation Plan", "assignee": "compliance_manager"}
                            ]
                        }
                    }
                }
            },
            "analytics": {
                "title": "Analytics & Reporting",
                "description": "Test analytics and reporting capabilities",
                "endpoints": {
                    "compliance_metrics": {
                        "method": "GET",
                        "url": f"/{self.api_version}/analytics/compliance-metrics",
                        "description": "Get compliance performance metrics",
                        "requires_auth": True,
                        "test_data": {
                            "date_from": "2024-01-01",
                            "date_to": "2024-01-31",
                            "metric_types": ["task_completion", "risk_scores"]
                        }
                    },
                    "risk_analysis": {
                        "method": "POST",
                        "url": f"/{self.api_version}/analytics/risk-analysis",
                        "description": "Perform risk analysis",
                        "requires_auth": True,
                        "test_data": {
                            "analysis_type": "customer_risk",
                            "customer_ids": ["TEST_CUST_001"],
                            "risk_factors": ["transaction_volume", "geography", "sanctions"]
                        }
                    },
                    "generate_report": {
                        "method": "POST",
                        "url": f"/{self.api_version}/reports/generate",
                        "description": "Generate compliance report",
                        "requires_auth": True,
                        "test_data": {
                            "report_type": "monthly_compliance",
                            "date_range": {
                                "start": "2024-01-01",
                                "end": "2024-01-31"
                            },
                            "format": "pdf"
                        }
                    }
                }
            }
        }

    def make_api_request(self, method: str, url: str, data: Dict = None, 
                        requires_auth: bool = False) -> Dict[str, Any]:
        """Make API request to the service"""
        try:
            full_url = f"{self.base_url}{url}"
            headers = {"Content-Type": "application/json"}
            
            # Add authentication if required
            if requires_auth and st.session_state.auth_token:
                headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
            elif requires_auth:
                return {
                    "success": False,
                    "error": "Authentication required. Please login first.",
                    "status_code": 401
                }
            
            # Make request
            if method.upper() == "GET":
                response = requests.get(full_url, headers=headers, params=data, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(full_url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(full_url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(full_url, headers=headers, timeout=30)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            # Process response
            result = {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "response_time": response.elapsed.total_seconds()
            }
            
            try:
                result["data"] = response.json()
            except:
                result["data"] = response.text
            
            if not result["success"]:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"
            
            return result
            
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed. Is the API server running on localhost:8000?",
                "status_code": 0
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out after 30 seconds",
                "status_code": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "status_code": 0
            }

    def render_main_interface(self):
        """Render the main testing interface"""
        # Header
        st.markdown("""
        <div class="test-header">
            <h1>🧪 Regulens AI Testing Portal</h1>
            <p>Interactive testing interface for all core services</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Service connection test
        self.render_connection_test()
        
        # Authentication section
        self.render_authentication_section()
        
        # Main testing interface
        col1, col2 = st.columns([1, 2])
        
        with col1:
            self.render_service_selector()
        
        with col2:
            self.render_test_interface()
        
        # Test history
        self.render_test_history()

    def render_connection_test(self):
        """Test basic connection to the API"""
        st.subheader("🔗 Connection Test")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Test API Connection"):
                result = self.make_api_request("GET", f"/{self.api_version}/health")
                if result["success"]:
                    st.markdown('<div class="test-result-success">✅ API is running and healthy</div>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="test-result-error">❌ Connection failed: {result.get("error", "Unknown error")}</div>', 
                               unsafe_allow_html=True)
        
        with col2:
            if st.button("Test Documentation"):
                try:
                    response = requests.get("http://localhost:8501", timeout=5)
                    if response.status_code == 200:
                        st.markdown('<div class="test-result-success">✅ Documentation Portal is running</div>', 
                                   unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="test-result-error">❌ Documentation Portal not accessible</div>', 
                                   unsafe_allow_html=True)
                except:
                    st.markdown('<div class="test-result-error">❌ Documentation Portal not running</div>', 
                               unsafe_allow_html=True)
        
        with col3:
            if st.button("Test Swagger Docs"):
                try:
                    response = requests.get("http://localhost:8000/docs", timeout=5)
                    if response.status_code == 200:
                        st.markdown('<div class="test-result-success">✅ Swagger UI is accessible</div>', 
                                   unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="test-result-error">❌ Swagger UI not accessible</div>', 
                                   unsafe_allow_html=True)
                except:
                    st.markdown('<div class="test-result-error">❌ Swagger UI not running</div>', 
                               unsafe_allow_html=True)

    def render_authentication_section(self):
        """Render authentication controls"""
        st.subheader("🔐 Authentication")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Quick Login (Test User)"):
                login_data = {
                    "username": "test_user",
                    "password": "TestPass123!"
                }
                result = self.make_api_request("POST", f"/{self.api_version}/auth/login", login_data)
                
                if result["success"] and "access_token" in result.get("data", {}):
                    st.session_state.auth_token = result["data"]["access_token"]
                    st.markdown('<div class="test-result-success">✅ Successfully authenticated</div>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="test-result-error">❌ Login failed: {result.get("error", "Unknown error")}</div>', 
                               unsafe_allow_html=True)
        
        with col2:
            if st.session_state.auth_token:
                if st.button("Verify Token"):
                    result = self.make_api_request("GET", f"/{self.api_version}/auth/verify", 
                                                 requires_auth=True)
                    if result["success"]:
                        st.markdown('<div class="test-result-success">✅ Token is valid</div>', 
                                   unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="test-result-error">❌ Token is invalid</div>', 
                                   unsafe_allow_html=True)
                        st.session_state.auth_token = None
        
        with col3:
            if st.session_state.auth_token:
                if st.button("Logout"):
                    st.session_state.auth_token = None
                    st.markdown('<div class="test-result-success">✅ Logged out</div>', 
                               unsafe_allow_html=True)
        
        # Display current auth status
        if st.session_state.auth_token:
            st.info(f"🟢 Authenticated - Token: {st.session_state.auth_token[:20]}...")
        else:
            st.warning("🔴 Not authenticated - Some tests require authentication")

    def render_service_selector(self):
        """Render service selection interface"""
        st.subheader("🛠️ Select Service")
        
        services = self.get_service_definitions()
        
        selected_service = st.selectbox(
            "Choose a service to test:",
            options=list(services.keys()),
            format_func=lambda x: services[x]["title"]
        )
        
        if selected_service:
            service_data = services[selected_service]
            
            # Service info
            st.markdown(f'<div class="service-card">', unsafe_allow_html=True)
            st.write(f"**{service_data['title']}**")
            st.write(service_data["description"])
            st.write(f"**Endpoints:** {len(service_data['endpoints'])}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Endpoint selector
            st.subheader("📡 Select Endpoint")
            endpoints = service_data["endpoints"]
            
            selected_endpoint = st.selectbox(
                "Choose an endpoint:",
                options=list(endpoints.keys()),
                format_func=lambda x: f"{endpoints[x]['method']} {endpoints[x]['description']}"
            )
            
            if selected_endpoint:
                st.session_state.selected_service = selected_service
                st.session_state.selected_endpoint = selected_endpoint
        
        # Quick test all endpoints
        if st.button("🚀 Test All Endpoints", type="primary"):
            self.run_comprehensive_test(services)

    def render_test_interface(self):
        """Render the main testing interface"""
        if not hasattr(st.session_state, 'selected_service'):
            st.info("👈 Select a service and endpoint to start testing")
            return
        
        services = self.get_service_definitions()
        service = services[st.session_state.selected_service]
        endpoint = service["endpoints"][st.session_state.selected_endpoint]
        
        st.subheader(f"🧪 Test: {endpoint['description']}")
        
        # Display endpoint info
        st.markdown(f'<div class="endpoint-box">{endpoint["method"]} {endpoint["url"]}</div>', 
                   unsafe_allow_html=True)
        
        if endpoint["requires_auth"]:
            st.warning("🔐 This endpoint requires authentication")
        
        # Test data editor
        st.subheader("📝 Request Data")
        
        # Load default test data
        default_data = endpoint.get("test_data", {})
        
        if default_data:
            # JSON editor for test data
            edited_data = st_ace(
                value=json.dumps(default_data, indent=2),
                language='json',
                theme='github',
                height=200,
                key=f"editor_{st.session_state.selected_service}_{st.session_state.selected_endpoint}"
            )
            
            try:
                test_data = json.loads(edited_data) if edited_data else {}
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON format")
                test_data = default_data
        else:
            st.info("No request data required for this endpoint")
            test_data = {}
        
        # Execute test
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 Execute Test", type="primary", key="execute_test"):
                self.execute_single_test(endpoint, test_data)
        
        with col2:
            if st.button("📋 Copy cURL Command"):
                curl_command = self.generate_curl_command(endpoint, test_data)
                st.code(curl_command, language="bash")

    def log_test_to_database(self, test_record: Dict, endpoint: Dict, test_data: Dict, result: Dict):
        """Log test execution to database via API"""
        if not self.log_test_execution:
            return
        
        try:
            # Prepare log data for API
            log_data = {
                "test_type": "ui_portal_test",
                "service_name": test_record["service"],
                "endpoint_path": endpoint["url"],
                "http_method": endpoint["method"],
                "request_data": test_data,
                "response_status_code": result.get("status_code"),
                "response_data": result.get("data", {}),
                "response_time_ms": int(result.get("response_time", 0) * 1000),
                "success": result["success"],
                "error_message": result.get("error"),
                "tenant_id": "ui-portal-tenant"  # Default for UI testing
            }
            
            # Make API call to log test execution
            log_result = self.make_api_request(
                "POST",
                f"/{self.api_version}/analytics/log-test-execution",
                log_data,
                requires_auth=False  # Logging endpoint doesn't require auth
            )
            
            if not log_result.get("success"):
                print(f"Failed to log test execution: {log_result.get('error')}")
                
        except Exception as e:
            print(f"Error logging test execution: {str(e)}")
    
    def execute_single_test(self, endpoint: Dict, test_data: Dict):
        """Execute a single test and display results"""
        st.subheader("📊 Test Results")
        
        with st.spinner("Executing test..."):
            start_time = datetime.now()
            result = self.make_api_request(
                endpoint["method"],
                endpoint["url"],
                test_data,
                endpoint["requires_auth"]
            )
            end_time = datetime.now()
        
        # Add to test history
        test_record = {
            "timestamp": start_time.isoformat(),
            "service": st.session_state.selected_service,
            "endpoint": st.session_state.selected_endpoint,
            "method": endpoint["method"],
            "url": endpoint["url"],
            "success": result["success"],
            "status_code": result.get("status_code", 0),
            "response_time": result.get("response_time", 0),
            "error": result.get("error")
        }
        st.session_state.test_history.append(test_record)
        
        # Log to database via API
        self.log_test_to_database(test_record, endpoint, test_data, result)
        
        # Display results
        if result["success"]:
            st.markdown('<div class="test-result-success">✅ Test Passed</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="test-result-error">❌ Test Failed: {result.get("error", "Unknown error")}</div>', 
                       unsafe_allow_html=True)
        
        # Response details
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Response Details:**")
            st.write(f"Status Code: {result.get('status_code', 'N/A')}")
            st.write(f"Response Time: {result.get('response_time', 'N/A'):.3f}s")
        
        with col2:
            st.write("**Headers:**")
            headers = result.get("headers", {})
            for key, value in list(headers.items())[:5]:  # Show first 5 headers
                st.write(f"{key}: {value}")
        
        # Response data
        st.subheader("📄 Response Data")
        if result.get("data"):
            st.markdown('<div class="response-json">', unsafe_allow_html=True)
            st.json(result["data"])
            st.markdown('</div>', unsafe_allow_html=True)

    def generate_curl_command(self, endpoint: Dict, test_data: Dict) -> str:
        """Generate cURL command for the test"""
        curl_cmd = f"curl -X {endpoint['method']} \\\n"
        curl_cmd += f"  '{self.base_url}{endpoint['url']}' \\\n"
        curl_cmd += "  -H 'Content-Type: application/json' \\\n"
        
        if endpoint["requires_auth"] and st.session_state.auth_token:
            curl_cmd += f"  -H 'Authorization: Bearer {st.session_state.auth_token}' \\\n"
        
        if test_data and endpoint["method"] in ["POST", "PUT"]:
            curl_cmd += f"  -d '{json.dumps(test_data)}'"
        
        return curl_cmd

    def run_comprehensive_test(self, services: Dict):
        """Run comprehensive test across all endpoints"""
        st.subheader("🔄 Comprehensive Test Results")
        
        progress_bar = st.progress(0)
        results_container = st.empty()
        
        all_results = []
        total_endpoints = sum(len(service["endpoints"]) for service in services.values())
        current_test = 0
        
        for service_key, service in services.items():
            for endpoint_key, endpoint in service["endpoints"].items():
                current_test += 1
                progress_bar.progress(current_test / total_endpoints)
                
                # Execute test
                result = self.make_api_request(
                    endpoint["method"],
                    endpoint["url"],
                    endpoint.get("test_data", {}),
                    endpoint["requires_auth"]
                )
                
                all_results.append({
                    "Service": service["title"],
                    "Endpoint": endpoint["description"],
                    "Method": endpoint["method"],
                    "Status": "✅ Pass" if result["success"] else "❌ Fail",
                    "Status Code": result.get("status_code", "N/A"),
                    "Response Time": f"{result.get('response_time', 0):.3f}s",
                    "Error": result.get("error", "")
                })
        
        # Display results table
        df = pd.DataFrame(all_results)
        st.dataframe(df, use_container_width=True)
        
        # Summary statistics
        total_tests = len(all_results)
        passed_tests = len([r for r in all_results if "Pass" in r["Status"]])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tests", total_tests)
        with col2:
            st.metric("Passed", passed_tests)
        with col3:
            st.metric("Success Rate", f"{(passed_tests/total_tests)*100:.1f}%")

    def render_test_history(self):
        """Render test execution history"""
        if not st.session_state.test_history:
            return
        
        st.subheader("📈 Test History")
        
        # Convert to DataFrame
        df = pd.DataFrame(st.session_state.test_history)
        
        # Summary charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Success rate over time
            fig = px.line(df, x="timestamp", y="success", 
                         title="Test Success Rate Over Time")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Response times
            fig = px.scatter(df, x="timestamp", y="response_time", 
                           color="success", title="Response Times")
            st.plotly_chart(fig, use_container_width=True)
        
        # History table
        if st.checkbox("Show Detailed History"):
            st.dataframe(df, use_container_width=True)
        
        # Clear history
        if st.button("Clear History"):
            st.session_state.test_history = []
            st.rerun()

def main():
    """Main application entry point"""
    portal = TestingPortal()
    portal.render_main_interface()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>🧪 Regulens AI Testing Portal | 
        <a href="http://localhost:8000/docs" target="_blank">Swagger UI</a> | 
        <a href="http://localhost:8501" target="_blank">Documentation</a> | 
        <a href="http://localhost:8000/v1/health" target="_blank">API Health</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 