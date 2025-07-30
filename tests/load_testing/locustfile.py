"""
RegulensAI Load Testing Suite
Comprehensive load testing scenarios for API endpoints, database operations, and system performance.
"""

import json
import random
import time
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import structlog

# Configure logging
logger = structlog.get_logger(__name__)


class RegulensAIUser(FastHttpUser):
    """
    Base user class for RegulensAI load testing.
    Simulates realistic user behavior patterns.
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Initialize user session."""
        self.auth_token = None
        self.user_id = f"load_test_user_{random.randint(1000, 9999)}"
        self.authenticate()
    
    def authenticate(self):
        """Authenticate user and get JWT token."""
        login_data = {
            "username": f"test_user_{random.randint(1, 100)}",
            "password": "test_password_123"
        }
        
        with self.client.post("/api/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                logger.info("User authenticated", user_id=self.user_id)
            else:
                logger.warning("Authentication failed", status=response.status_code)
    
    def get_headers(self):
        """Get headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers


class APILoadTestUser(RegulensAIUser):
    """
    Load testing for core API endpoints.
    Tests authentication, CRUD operations, and data retrieval.
    """
    
    @task(3)
    def get_dashboard_data(self):
        """Test dashboard data retrieval."""
        with self.client.get(
            "/api/dashboard/overview",
            headers=self.get_headers(),
            name="Dashboard Overview"
        ) as response:
            if response.status_code != 200:
                logger.error("Dashboard request failed", status=response.status_code)
    
    @task(2)
    def get_operations_status(self):
        """Test operations status endpoint."""
        with self.client.get(
            "/api/operations/status",
            headers=self.get_headers(),
            name="Operations Status"
        ) as response:
            if response.status_code != 200:
                logger.error("Operations status failed", status=response.status_code)
    
    @task(2)
    def validate_configuration(self):
        """Test configuration validation."""
        config_data = {
            "environment": "production",
            "database_config": {
                "host": "localhost",
                "port": 5432,
                "database": "regulens_test"
            },
            "api_config": {
                "rate_limit": 100,
                "timeout": 30
            }
        }
        
        with self.client.post(
            "/api/operations/validate-config",
            json=config_data,
            headers=self.get_headers(),
            name="Configuration Validation"
        ) as response:
            if response.status_code not in [200, 202]:
                logger.error("Config validation failed", status=response.status_code)
    
    @task(1)
    def get_monitoring_metrics(self):
        """Test monitoring metrics endpoint."""
        with self.client.get(
            "/api/monitoring/metrics",
            headers=self.get_headers(),
            name="Monitoring Metrics"
        ) as response:
            if response.status_code != 200:
                logger.error("Metrics request failed", status=response.status_code)
    
    @task(1)
    def create_backup_request(self):
        """Test backup creation endpoint."""
        backup_data = {
            "environment": "staging",
            "backup_type": "full",
            "compression": True
        }
        
        with self.client.post(
            "/api/operations/backup",
            json=backup_data,
            headers=self.get_headers(),
            name="Create Backup"
        ) as response:
            if response.status_code not in [200, 202]:
                logger.error("Backup request failed", status=response.status_code)


class DatabaseLoadTestUser(RegulensAIUser):
    """
    Load testing for database-intensive operations.
    Tests data queries, aggregations, and complex operations.
    """
    
    @task(3)
    def query_training_data(self):
        """Test training data queries."""
        params = {
            "limit": random.randint(10, 100),
            "offset": random.randint(0, 1000),
            "filter": random.choice(["active", "completed", "pending"])
        }
        
        with self.client.get(
            "/api/training/data",
            params=params,
            headers=self.get_headers(),
            name="Query Training Data"
        ) as response:
            if response.status_code != 200:
                logger.error("Training data query failed", status=response.status_code)
    
    @task(2)
    def get_compliance_reports(self):
        """Test compliance report generation."""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "report_type": random.choice(["summary", "detailed", "audit"])
        }
        
        with self.client.get(
            "/api/compliance/reports",
            params=params,
            headers=self.get_headers(),
            name="Compliance Reports"
        ) as response:
            if response.status_code != 200:
                logger.error("Compliance report failed", status=response.status_code)
    
    @task(2)
    def search_regulations(self):
        """Test regulation search functionality."""
        search_terms = [
            "Basel III", "GDPR", "SOX", "MiFID II", "CCAR", 
            "stress testing", "capital requirements", "risk management"
        ]
        
        search_data = {
            "query": random.choice(search_terms),
            "filters": {
                "jurisdiction": random.choice(["US", "EU", "UK", "GLOBAL"]),
                "category": random.choice(["banking", "securities", "insurance"])
            },
            "limit": random.randint(10, 50)
        }
        
        with self.client.post(
            "/api/regulations/search",
            json=search_data,
            headers=self.get_headers(),
            name="Search Regulations"
        ) as response:
            if response.status_code != 200:
                logger.error("Regulation search failed", status=response.status_code)


class MonitoringLoadTestUser(RegulensAIUser):
    """
    Load testing for monitoring and alerting systems.
    Tests metrics collection, alert processing, and real-time data.
    """
    
    @task(4)
    def get_system_metrics(self):
        """Test system metrics retrieval."""
        metrics = [
            "cpu_usage", "memory_usage", "disk_usage", 
            "network_io", "database_connections", "api_response_time"
        ]
        
        metric_name = random.choice(metrics)
        params = {
            "metric": metric_name,
            "timeframe": random.choice(["1h", "6h", "24h", "7d"]),
            "aggregation": random.choice(["avg", "max", "min", "sum"])
        }
        
        with self.client.get(
            "/api/monitoring/metrics/system",
            params=params,
            headers=self.get_headers(),
            name="System Metrics"
        ) as response:
            if response.status_code != 200:
                logger.error("System metrics failed", status=response.status_code)
    
    @task(2)
    def get_alert_status(self):
        """Test alert status endpoint."""
        with self.client.get(
            "/api/monitoring/alerts",
            headers=self.get_headers(),
            name="Alert Status"
        ) as response:
            if response.status_code != 200:
                logger.error("Alert status failed", status=response.status_code)
    
    @task(1)
    def create_custom_alert(self):
        """Test custom alert creation."""
        alert_data = {
            "name": f"Load Test Alert {random.randint(1000, 9999)}",
            "metric": random.choice(["cpu_usage", "memory_usage", "error_rate"]),
            "threshold": random.uniform(70.0, 95.0),
            "operator": random.choice(["gt", "lt", "eq"]),
            "duration": random.choice(["5m", "10m", "15m"]),
            "severity": random.choice(["warning", "critical"])
        }
        
        with self.client.post(
            "/api/monitoring/alerts",
            json=alert_data,
            headers=self.get_headers(),
            name="Create Alert"
        ) as response:
            if response.status_code not in [200, 201]:
                logger.error("Alert creation failed", status=response.status_code)


class HighVolumeUser(RegulensAIUser):
    """
    High-volume user simulation for stress testing.
    Simulates peak load conditions and concurrent operations.
    """
    
    wait_time = between(0.1, 1)  # Faster requests for stress testing
    
    @task(5)
    def rapid_api_calls(self):
        """Rapid succession of API calls."""
        endpoints = [
            "/api/health",
            "/api/status",
            "/api/version",
            "/api/dashboard/summary"
        ]
        
        endpoint = random.choice(endpoints)
        with self.client.get(
            endpoint,
            headers=self.get_headers(),
            name="Rapid API Calls"
        ) as response:
            if response.status_code != 200:
                logger.error("Rapid API call failed", endpoint=endpoint, status=response.status_code)
    
    @task(3)
    def concurrent_data_operations(self):
        """Concurrent data operations."""
        operations = [
            ("GET", "/api/training/models", {}),
            ("GET", "/api/compliance/rules", {}),
            ("GET", "/api/monitoring/logs", {"limit": 100}),
        ]
        
        method, endpoint, params = random.choice(operations)
        
        if method == "GET":
            with self.client.get(
                endpoint,
                params=params,
                headers=self.get_headers(),
                name="Concurrent Operations"
            ) as response:
                if response.status_code != 200:
                    logger.error("Concurrent operation failed", endpoint=endpoint)


# Load testing event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Handle test start event."""
    logger.info("RegulensAI load test started", 
               users=environment.parsed_options.num_users,
               spawn_rate=environment.parsed_options.spawn_rate)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Handle test stop event."""
    logger.info("RegulensAI load test completed")

@events.request_failure.add_listener
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Handle request failures."""
    logger.error("Request failed",
                request_type=request_type,
                name=name,
                response_time=response_time,
                exception=str(exception))

@events.request_success.add_listener
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Handle successful requests."""
    if response_time > 5000:  # Log slow requests (>5s)
        logger.warning("Slow request detected",
                      request_type=request_type,
                      name=name,
                      response_time=response_time)


# Custom load testing scenarios
class PeakLoadScenario(RegulensAIUser):
    """
    Peak load scenario simulating maximum expected traffic.
    """
    
    weight = 1
    wait_time = between(0.5, 2)
    
    tasks = {
        APILoadTestUser.get_dashboard_data: 30,
        APILoadTestUser.get_operations_status: 20,
        DatabaseLoadTestUser.query_training_data: 25,
        MonitoringLoadTestUser.get_system_metrics: 15,
        APILoadTestUser.validate_configuration: 10
    }


class SteadyStateScenario(RegulensAIUser):
    """
    Steady state scenario simulating normal operational load.
    """
    
    weight = 3
    wait_time = between(2, 8)
    
    tasks = {
        APILoadTestUser.get_dashboard_data: 40,
        DatabaseLoadTestUser.query_training_data: 30,
        MonitoringLoadTestUser.get_system_metrics: 20,
        APILoadTestUser.get_operations_status: 10
    }


if __name__ == "__main__":
    # This allows running the locustfile directly for testing
    import subprocess
    import sys

    print("RegulensAI Load Testing Suite")
    print("Usage: locust -f locustfile.py --host=http://localhost:8000")
    print("Available user classes:")
    print("  - APILoadTestUser: Core API testing")
    print("  - DatabaseLoadTestUser: Database-intensive operations")
    print("  - MonitoringLoadTestUser: Monitoring system testing")
    print("  - HighVolumeUser: Stress testing")
    print("  - PeakLoadScenario: Peak load simulation")
    print("  - SteadyStateScenario: Normal load simulation")
    print("\nExample commands:")
    print("  locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5")
    print("  locust -f locustfile.py --host=http://localhost:8000 --headless --users=100 --spawn-rate=10 --run-time=300s")
