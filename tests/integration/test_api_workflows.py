"""
Regulens AI - Integration Testing Framework
Comprehensive end-to-end API workflow testing for financial compliance platform.
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from tests.integration.fixtures import (
    test_client, test_tenant, test_user, test_customer,
    cleanup_test_data, setup_test_environment
)

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class TestAuthenticationWorkflow:
    """Test complete authentication and authorization workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_auth_workflow(self, test_client, test_tenant, test_user):
        """Test complete authentication workflow from login to protected resource access."""
        
        # Step 1: User login
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "test_password"
        })
        
        assert login_response.status_code == 200
        auth_data = login_response.json()
        assert "access_token" in auth_data
        assert "refresh_token" in auth_data
        assert auth_data["user"]["id"] == test_user["id"]
        
        access_token = auth_data["access_token"]
        refresh_token = auth_data["refresh_token"]
        
        # Step 2: Access protected resource
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": test_tenant["id"]
        }
        
        profile_response = await test_client.get("/api/v1/users/profile", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["id"] == test_user["id"]
        
        # Step 3: Token refresh
        refresh_response = await test_client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert refresh_response.status_code == 200
        new_auth_data = refresh_response.json()
        assert "access_token" in new_auth_data
        assert new_auth_data["access_token"] != access_token
        
        # Step 4: Use new token
        new_headers = {
            "Authorization": f"Bearer {new_auth_data['access_token']}",
            "X-Tenant-ID": test_tenant["id"]
        }
        
        new_profile_response = await test_client.get("/api/v1/users/profile", headers=new_headers)
        assert new_profile_response.status_code == 200
        
        # Step 5: Logout
        logout_response = await test_client.post("/api/v1/auth/logout", headers=new_headers)
        assert logout_response.status_code == 200
        
        # Step 6: Verify token is invalidated
        invalid_response = await test_client.get("/api/v1/users/profile", headers=new_headers)
        assert invalid_response.status_code == 401

class TestComplianceWorkflow:
    """Test complete compliance management workflows."""
    
    @pytest.mark.asyncio
    async def test_compliance_program_lifecycle(self, test_client, test_tenant, test_user):
        """Test complete compliance program lifecycle."""
        
        headers = await self._get_auth_headers(test_client, test_user, test_tenant)
        
        # Step 1: Create compliance program
        program_data = {
            "name": "SOX Compliance Program",
            "description": "Sarbanes-Oxley compliance framework",
            "framework": "SOX",
            "jurisdiction": "US",
            "effective_date": "2024-01-01",
            "review_frequency": 365
        }
        
        create_response = await test_client.post(
            "/api/v1/compliance/programs", 
            json=program_data, 
            headers=headers
        )
        
        assert create_response.status_code == 201
        program = create_response.json()
        program_id = program["id"]
        
        # Step 2: Add compliance requirements
        requirement_data = {
            "title": "Internal Controls Assessment",
            "description": "Quarterly assessment of internal controls",
            "requirement_type": "assessment",
            "priority": "high",
            "due_date": "2024-03-31"
        }
        
        req_response = await test_client.post(
            f"/api/v1/compliance/programs/{program_id}/requirements",
            json=requirement_data,
            headers=headers
        )
        
        assert req_response.status_code == 201
        requirement = req_response.json()
        requirement_id = requirement["id"]
        
        # Step 3: Create compliance task
        task_data = {
            "title": "Review Financial Controls",
            "description": "Review and document financial controls",
            "task_type": "compliance",
            "priority": "high",
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        task_response = await test_client.post(
            "/api/v1/tasks", 
            json=task_data, 
            headers=headers
        )
        
        assert task_response.status_code == 201
        task = task_response.json()
        task_id = task["id"]
        
        # Step 4: Complete task
        complete_response = await test_client.put(
            f"/api/v1/tasks/{task_id}/complete",
            json={"completion_notes": "Controls reviewed and documented"},
            headers=headers
        )
        
        assert complete_response.status_code == 200
        
        # Step 5: Mark requirement as complete
        req_complete_response = await test_client.put(
            f"/api/v1/compliance/requirements/{requirement_id}/complete",
            json={"completion_notes": "Assessment completed successfully"},
            headers=headers
        )
        
        assert req_complete_response.status_code == 200
        
        # Step 6: Generate compliance report
        report_data = {
            "report_type": "compliance_summary",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "format": "json",
            "filters": {"program_id": program_id}
        }
        
        report_response = await test_client.post(
            "/api/v1/reports/generate",
            json=report_data,
            headers=headers
        )
        
        assert report_response.status_code == 202
        report = report_response.json()
        assert "report_id" in report
    
    async def _get_auth_headers(self, test_client, test_user, test_tenant) -> Dict[str, str]:
        """Helper to get authentication headers."""
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "test_password"
        })
        
        auth_data = login_response.json()
        return {
            "Authorization": f"Bearer {auth_data['access_token']}",
            "X-Tenant-ID": test_tenant["id"]
        }

class TestAMLWorkflow:
    """Test complete AML/KYC workflows."""
    
    @pytest.mark.asyncio
    async def test_customer_onboarding_and_screening(self, test_client, test_tenant, test_user, test_customer):
        """Test complete customer onboarding and AML screening workflow."""
        
        headers = await self._get_auth_headers(test_client, test_user, test_tenant)
        
        # Step 1: Create customer
        customer_data = {
            "customer_type": "individual",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "date_of_birth": "1985-06-15",
            "country": "US",
            "address": "123 Main St, City, State 12345"
        }
        
        customer_response = await test_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=headers
        )
        
        assert customer_response.status_code == 201
        customer = customer_response.json()
        customer_id = customer["id"]
        
        # Step 2: Perform KYC screening
        screening_data = {
            "customer_id": customer_id,
            "screening_types": ["sanctions", "pep", "adverse_media"]
        }
        
        screening_response = await test_client.post(
            "/api/v1/aml/screen-customer",
            json=screening_data,
            headers=headers
        )
        
        assert screening_response.status_code == 202
        screening = screening_response.json()
        assert "screening_id" in screening
        
        # Step 3: Get AI risk assessment
        risk_response = await test_client.get(
            f"/api/v1/customers/{customer_id}/risk-assessment",
            headers=headers
        )
        
        assert risk_response.status_code == 200
        risk_data = risk_response.json()
        assert "risk_score" in risk_data
        assert "risk_category" in risk_data
        
        # Step 4: Create transaction
        transaction_data = {
            "customer_id": customer_id,
            "transaction_type": "wire_transfer",
            "amount": 50000.00,
            "currency": "USD",
            "source_country": "US",
            "destination_country": "US",
            "description": "Business payment"
        }
        
        transaction_response = await test_client.post(
            "/api/v1/transactions",
            json=transaction_data,
            headers=headers
        )
        
        assert transaction_response.status_code == 201
        transaction = transaction_response.json()
        transaction_id = transaction["id"]
        
        # Step 5: Monitor transaction
        monitor_response = await test_client.get(
            f"/api/v1/aml/transactions/{transaction_id}/monitor",
            headers=headers
        )
        
        assert monitor_response.status_code == 200
        monitor_data = monitor_response.json()
        assert "monitoring_status" in monitor_data
        
        # Step 6: If flagged, create SAR (Suspicious Activity Report)
        if monitor_data.get("requires_sar"):
            sar_data = {
                "customer_id": customer_id,
                "transaction_ids": [transaction_id],
                "suspicious_activity_type": "unusual_transaction_pattern",
                "description": "Large transaction from new customer",
                "supporting_documentation": []
            }
            
            sar_response = await test_client.post(
                "/api/v1/aml/sar",
                json=sar_data,
                headers=headers
            )
            
            assert sar_response.status_code == 201
    
    async def _get_auth_headers(self, test_client, test_user, test_tenant) -> Dict[str, str]:
        """Helper to get authentication headers."""
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "test_password"
        })
        
        auth_data = login_response.json()
        return {
            "Authorization": f"Bearer {auth_data['access_token']}",
            "X-Tenant-ID": test_tenant["id"]
        }

class TestUIPortalWorkflow:
    """Test complete UI portal workflows."""
    
    @pytest.mark.asyncio
    async def test_documentation_portal_workflow(self, test_client, test_tenant, test_user):
        """Test complete documentation portal workflow."""
        
        headers = await self._get_auth_headers(test_client, test_user, test_tenant)
        
        # Step 1: Create documentation portal session
        session_data = {
            "portal_type": "documentation",
            "user_agent": "Test Browser 1.0"
        }
        
        session_response = await test_client.post(
            "/api/v1/ui/sessions",
            json=session_data,
            headers=headers
        )
        
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["session_id"]
        
        # Step 2: Perform documentation search
        search_data = {
            "query": "authentication API",
            "search_type": "api",
            "filters": {"category": "security"}
        }
        
        search_response = await test_client.post(
            f"/api/v1/ui/documentation/search?session_id={session_id}",
            json=search_data,
            headers=headers
        )
        
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert "results" in search_results
        assert "execution_time_ms" in search_results
        
        # Step 3: Update session activity
        activity_data = {"last_page": "/docs/authentication"}
        
        activity_response = await test_client.put(
            f"/api/v1/ui/sessions/{session_id}/activity",
            json=activity_data,
            headers=headers
        )
        
        assert activity_response.status_code == 200
        
        # Step 4: End session
        end_response = await test_client.delete(
            f"/api/v1/ui/sessions/{session_id}",
            headers=headers
        )
        
        assert end_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_testing_portal_workflow(self, test_client, test_tenant, test_user):
        """Test complete testing portal workflow."""
        
        headers = await self._get_auth_headers(test_client, test_user, test_tenant)
        
        # Step 1: Create testing portal session
        session_data = {
            "portal_type": "testing",
            "user_agent": "Test Browser 1.0"
        }
        
        session_response = await test_client.post(
            "/api/v1/ui/sessions",
            json=session_data,
            headers=headers
        )
        
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["session_id"]
        
        # Step 2: Execute API test
        test_data = {
            "endpoint_path": "/api/v1/health",
            "http_method": "GET",
            "request_data": {},
            "validation_rules": {
                "expected_status_code": 200,
                "required_fields": ["status"]
            }
        }
        
        test_response = await test_client.post(
            f"/api/v1/ui/testing/api-test?session_id={session_id}",
            json=test_data,
            headers=headers
        )
        
        assert test_response.status_code == 200
        test_result = test_response.json()
        assert "success" in test_result
        assert "response_time_ms" in test_result
        
        # Step 3: Create test suite
        suite_data = {
            "name": "Health Check Suite",
            "description": "Basic health check tests",
            "tests": [
                {
                    "name": "API Health Check",
                    "endpoint_path": "/api/v1/health",
                    "http_method": "GET",
                    "request_data": {}
                }
            ]
        }
        
        suite_response = await test_client.post(
            "/api/v1/ui/testing/test-suite",
            json=suite_data,
            headers=headers
        )
        
        assert suite_response.status_code == 200
        suite = suite_response.json()
        suite_id = suite["suite_id"]
        
        # Step 4: Execute test suite
        execute_response = await test_client.post(
            f"/api/v1/ui/testing/test-suite/{suite_id}/execute?session_id={session_id}",
            headers=headers
        )
        
        assert execute_response.status_code == 200
        execution_result = execute_response.json()
        assert "total_tests" in execution_result
        assert "passed_tests" in execution_result
    
    async def _get_auth_headers(self, test_client, test_user, test_tenant) -> Dict[str, str]:
        """Helper to get authentication headers."""
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "test_password"
        })
        
        auth_data = login_response.json()
        return {
            "Authorization": f"Bearer {auth_data['access_token']}",
            "X-Tenant-ID": test_tenant["id"]
        }

class TestPerformanceBenchmarks:
    """Test performance benchmarks and load testing."""
    
    @pytest.mark.asyncio
    async def test_api_performance_benchmarks(self, test_client, test_tenant, test_user):
        """Test API performance under load."""
        
        headers = await self._get_auth_headers(test_client, test_user, test_tenant)
        
        # Test concurrent requests to health endpoint
        async def make_request():
            response = await test_client.get("/api/v1/health", headers=headers)
            return response.status_code, response.elapsed.total_seconds()
        
        # Execute 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        status_codes = [result[0] for result in results]
        response_times = [result[1] for result in results]
        
        # Performance assertions
        assert all(code == 200 for code in status_codes), "All requests should succeed"
        assert max(response_times) < 5.0, "Max response time should be under 5 seconds"
        assert sum(response_times) / len(response_times) < 1.0, "Average response time should be under 1 second"
        
        logger.info(f"Performance test results: {len(results)} requests, "
                   f"avg: {sum(response_times)/len(response_times):.3f}s, "
                   f"max: {max(response_times):.3f}s")
    
    async def _get_auth_headers(self, test_client, test_user, test_tenant) -> Dict[str, str]:
        """Helper to get authentication headers."""
        login_response = await test_client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "test_password"
        })
        
        auth_data = login_response.json()
        return {
            "Authorization": f"Bearer {auth_data['access_token']}",
            "X-Tenant-ID": test_tenant["id"]
        }

# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
