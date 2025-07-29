"""
Regulens AI - Advanced Testing Portal
Enterprise-grade testing interface with API testing, performance monitoring, and automated test execution.
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.api.auth import get_current_user
from core_infra.performance.caching import cache_manager
from core_infra.monitoring.observability import observability_manager
from core_infra.exceptions import BusinessLogicException, DataValidationException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class TestType(Enum):
    """Test type enumeration."""
    API_ENDPOINT = "api_endpoint"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"

class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"

@dataclass
class TestExecution:
    """Test execution data structure."""
    id: str
    session_id: str
    tenant_id: str
    test_type: TestType
    service_name: str
    endpoint_path: str
    http_method: str
    request_data: Dict[str, Any]
    response_status_code: Optional[int]
    response_data: Optional[Dict[str, Any]]
    response_time_ms: Optional[int]
    success: bool
    error_message: Optional[str]
    executed_at: datetime

@dataclass
class TestSuite:
    """Test suite configuration."""
    id: str
    name: str
    description: str
    tests: List[Dict[str, Any]]
    tenant_id: str
    created_by: str
    created_at: datetime

class APITestExecutor:
    """Advanced API testing with comprehensive validation."""
    
    def __init__(self):
        self.timeout = 30  # seconds
        self.max_concurrent_tests = 10
        
    async def execute_api_test(self, session_id: str, tenant_id: str,
                             endpoint_path: str, http_method: str,
                             request_data: Dict[str, Any],
                             headers: Optional[Dict[str, str]] = None,
                             validation_rules: Optional[Dict[str, Any]] = None) -> TestExecution:
        """Execute a single API test with comprehensive validation."""
        try:
            start_time = time.time()
            test_id = str(uuid.uuid4())
            
            # Prepare request
            url = f"{settings.api_base_url}{endpoint_path}"
            test_headers = {
                'Content-Type': 'application/json',
                'X-Tenant-ID': tenant_id,
                **(headers or {})
            }
            
            # Execute request
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                try:
                    async with session.request(
                        method=http_method.upper(),
                        url=url,
                        json=request_data if http_method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                        params=request_data if http_method.upper() == 'GET' else None,
                        headers=test_headers
                    ) as response:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        
                        # Validate response
                        success = await self._validate_response(
                            response.status, response_data, validation_rules
                        )
                        
                        test_execution = TestExecution(
                            id=test_id,
                            session_id=session_id,
                            tenant_id=tenant_id,
                            test_type=TestType.API_ENDPOINT,
                            service_name=self._extract_service_name(endpoint_path),
                            endpoint_path=endpoint_path,
                            http_method=http_method.upper(),
                            request_data=request_data,
                            response_status_code=response.status,
                            response_data=response_data if isinstance(response_data, dict) else {'text': response_data},
                            response_time_ms=response_time_ms,
                            success=success,
                            error_message=None,
                            executed_at=datetime.utcnow()
                        )
                        
                except asyncio.TimeoutError:
                    test_execution = TestExecution(
                        id=test_id,
                        session_id=session_id,
                        tenant_id=tenant_id,
                        test_type=TestType.API_ENDPOINT,
                        service_name=self._extract_service_name(endpoint_path),
                        endpoint_path=endpoint_path,
                        http_method=http_method.upper(),
                        request_data=request_data,
                        response_status_code=None,
                        response_data=None,
                        response_time_ms=int((time.time() - start_time) * 1000),
                        success=False,
                        error_message="Request timeout",
                        executed_at=datetime.utcnow()
                    )
                    
                except Exception as e:
                    test_execution = TestExecution(
                        id=test_id,
                        session_id=session_id,
                        tenant_id=tenant_id,
                        test_type=TestType.API_ENDPOINT,
                        service_name=self._extract_service_name(endpoint_path),
                        endpoint_path=endpoint_path,
                        http_method=http_method.upper(),
                        request_data=request_data,
                        response_status_code=None,
                        response_data=None,
                        response_time_ms=int((time.time() - start_time) * 1000),
                        success=False,
                        error_message=str(e),
                        executed_at=datetime.utcnow()
                    )
            
            # Store test execution
            await self._store_test_execution(test_execution)
            
            # Record metrics
            await observability_manager.metrics_collector.record_timer(
                'api_test.execution_time', test_execution.response_time_ms or 0,
                tags={
                    'endpoint': endpoint_path,
                    'method': http_method,
                    'success': str(test_execution.success)
                }
            )
            
            logger.info(f"API test executed: {endpoint_path} - Success: {test_execution.success}")
            return test_execution
            
        except Exception as e:
            logger.error(f"API test execution failed: {e}")
            raise BusinessLogicException(f"Test execution failed: {e}")
    
    async def _validate_response(self, status_code: int, response_data: Any,
                               validation_rules: Optional[Dict[str, Any]]) -> bool:
        """Validate API response against rules."""
        try:
            if not validation_rules:
                # Default validation - 2xx status codes are success
                return 200 <= status_code < 300
            
            # Status code validation
            expected_status = validation_rules.get('expected_status_code')
            if expected_status and status_code != expected_status:
                return False
            
            # Response structure validation
            required_fields = validation_rules.get('required_fields', [])
            if isinstance(response_data, dict):
                for field in required_fields:
                    if field not in response_data:
                        return False
            
            # Response value validation
            field_validations = validation_rules.get('field_validations', {})
            if isinstance(response_data, dict):
                for field, expected_value in field_validations.items():
                    if response_data.get(field) != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Response validation error: {e}")
            return False
    
    def _extract_service_name(self, endpoint_path: str) -> str:
        """Extract service name from endpoint path."""
        parts = endpoint_path.strip('/').split('/')
        if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'v1':
            return parts[2]
        return 'unknown'
    
    async def _store_test_execution(self, test_execution: TestExecution):
        """Store test execution in database."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO ui_test_executions (
                        id, session_id, tenant_id, test_type, service_name,
                        endpoint_path, http_method, request_data, response_status_code,
                        response_data, response_time_ms, success, error_message, executed_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """,
                    uuid.UUID(test_execution.id),
                    uuid.UUID(test_execution.session_id),
                    uuid.UUID(test_execution.tenant_id),
                    test_execution.test_type.value,
                    test_execution.service_name,
                    test_execution.endpoint_path,
                    test_execution.http_method,
                    test_execution.request_data,
                    test_execution.response_status_code,
                    test_execution.response_data,
                    test_execution.response_time_ms,
                    test_execution.success,
                    test_execution.error_message,
                    test_execution.executed_at
                )
        except Exception as e:
            logger.error(f"Failed to store test execution: {e}")

class TestSuiteManager:
    """Advanced test suite management and execution."""
    
    async def create_test_suite(self, name: str, description: str,
                              tests: List[Dict[str, Any]], tenant_id: str,
                              created_by: str) -> TestSuite:
        """Create a new test suite."""
        try:
            suite_id = str(uuid.uuid4())
            
            test_suite = TestSuite(
                id=suite_id,
                name=name,
                description=description,
                tests=tests,
                tenant_id=tenant_id,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            # Store in database
            await self._store_test_suite(test_suite)

            # Also cache it for quick access
            await cache_manager.set_cached_data('test_suites', suite_id, asdict(test_suite))
            
            logger.info(f"Test suite created: {name} with {len(tests)} tests")
            return test_suite
            
        except Exception as e:
            logger.error(f"Failed to create test suite: {e}")
            raise BusinessLogicException(f"Test suite creation failed: {e}")
    
    async def execute_test_suite(self, suite_id: str, session_id: str,
                               tenant_id: str) -> Dict[str, Any]:
        """Execute all tests in a test suite."""
        try:
            # Get test suite
            suite_data = await cache_manager.get_cached_data('test_suites', suite_id)
            if not suite_data:
                # Try to get from database
                suite_data = await self._get_test_suite_from_db(suite_id, tenant_id)
                if not suite_data:
                    raise BusinessLogicException("Test suite not found")
            
            test_suite = TestSuite(**suite_data)
            
            # Execute tests
            api_executor = APITestExecutor()
            results = []
            
            for test_config in test_suite.tests:
                try:
                    result = await api_executor.execute_api_test(
                        session_id=session_id,
                        tenant_id=tenant_id,
                        endpoint_path=test_config['endpoint_path'],
                        http_method=test_config['http_method'],
                        request_data=test_config.get('request_data', {}),
                        headers=test_config.get('headers'),
                        validation_rules=test_config.get('validation_rules')
                    )
                    results.append(asdict(result))
                except Exception as e:
                    logger.error(f"Test execution failed: {e}")
                    results.append({
                        'test_name': test_config.get('name', 'Unknown'),
                        'success': False,
                        'error_message': str(e)
                    })
            
            # Calculate summary
            total_tests = len(results)
            passed_tests = sum(1 for r in results if r.get('success', False))
            failed_tests = total_tests - passed_tests
            
            summary = {
                'suite_id': suite_id,
                'suite_name': test_suite.name,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'executed_at': datetime.utcnow().isoformat(),
                'results': results
            }
            
            logger.info(f"Test suite executed: {test_suite.name} - {passed_tests}/{total_tests} passed")
            return summary
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            raise BusinessLogicException(f"Test suite execution failed: {e}")

    async def _store_test_suite(self, test_suite: TestSuite):
        """Store test suite in database."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO ui_test_suites (
                        id, name, description, tenant_id, created_by, tests, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    uuid.UUID(test_suite.id),
                    test_suite.name,
                    test_suite.description,
                    uuid.UUID(test_suite.tenant_id),
                    uuid.UUID(test_suite.created_by),
                    test_suite.tests,
                    test_suite.created_at,
                    test_suite.created_at
                )
        except Exception as e:
            logger.error(f"Failed to store test suite: {e}")
            raise

    async def _get_test_suite_from_db(self, suite_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get test suite from database."""
        try:
            async with get_database() as db:
                row = await db.fetchrow(
                    """
                    SELECT * FROM ui_test_suites
                    WHERE id = $1 AND tenant_id = $2 AND is_active = true
                    """,
                    uuid.UUID(suite_id),
                    uuid.UUID(tenant_id)
                )

                if row:
                    return {
                        'id': str(row['id']),
                        'name': row['name'],
                        'description': row['description'],
                        'tests': row['tests'],
                        'tenant_id': str(row['tenant_id']),
                        'created_by': str(row['created_by']),
                        'created_at': row['created_at']
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get test suite from database: {e}")
            return None

class PerformanceTestManager:
    """Performance testing and load testing capabilities."""
    
    async def execute_load_test(self, endpoint_path: str, http_method: str,
                              request_data: Dict[str, Any], concurrent_users: int,
                              duration_seconds: int, session_id: str,
                              tenant_id: str) -> Dict[str, Any]:
        """Execute load test with multiple concurrent requests."""
        try:
            start_time = time.time()
            results = []
            
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(concurrent_users)
            
            async def execute_single_request():
                async with semaphore:
                    api_executor = APITestExecutor()
                    return await api_executor.execute_api_test(
                        session_id=session_id,
                        tenant_id=tenant_id,
                        endpoint_path=endpoint_path,
                        http_method=http_method,
                        request_data=request_data
                    )
            
            # Execute requests for specified duration
            tasks = []
            while time.time() - start_time < duration_seconds:
                task = asyncio.create_task(execute_single_request())
                tasks.append(task)
                await asyncio.sleep(0.1)  # Small delay between request starts
            
            # Wait for all tasks to complete
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_requests = 0
            failed_requests = 0
            response_times = []
            
            for result in completed_results:
                if isinstance(result, TestExecution):
                    results.append(asdict(result))
                    if result.success:
                        successful_requests += 1
                        if result.response_time_ms:
                            response_times.append(result.response_time_ms)
                    else:
                        failed_requests += 1
                else:
                    failed_requests += 1
            
            # Calculate statistics
            total_requests = len(results)
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            requests_per_second = total_requests / duration_seconds if duration_seconds > 0 else 0
            
            summary = {
                'endpoint_path': endpoint_path,
                'http_method': http_method,
                'concurrent_users': concurrent_users,
                'duration_seconds': duration_seconds,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                'requests_per_second': round(requests_per_second, 2),
                'avg_response_time_ms': round(avg_response_time, 2),
                'min_response_time_ms': min_response_time,
                'max_response_time_ms': max_response_time,
                'executed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Load test completed: {endpoint_path} - {successful_requests}/{total_requests} successful")
            return summary
            
        except Exception as e:
            logger.error(f"Load test execution failed: {e}")
            raise BusinessLogicException(f"Load test execution failed: {e}")

class TestReportGenerator:
    """Generate comprehensive test reports and analytics."""
    
    async def generate_test_report(self, tenant_id: str, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive test execution report."""
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=7)
            if not end_date:
                end_date = datetime.utcnow()
            
            async with get_database() as db:
                # Get test execution statistics
                stats_query = """
                    SELECT 
                        test_type,
                        service_name,
                        COUNT(*) as total_tests,
                        COUNT(*) FILTER (WHERE success = true) as passed_tests,
                        COUNT(*) FILTER (WHERE success = false) as failed_tests,
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time
                    FROM ui_test_executions
                    WHERE tenant_id = $1 AND executed_at >= $2 AND executed_at <= $3
                    GROUP BY test_type, service_name
                    ORDER BY total_tests DESC
                """
                
                stats_results = await db.fetch(stats_query, uuid.UUID(tenant_id), start_date, end_date)
                
                # Get trending data
                trend_query = """
                    SELECT 
                        DATE_TRUNC('day', executed_at) as test_date,
                        COUNT(*) as total_tests,
                        COUNT(*) FILTER (WHERE success = true) as passed_tests,
                        AVG(response_time_ms) as avg_response_time
                    FROM ui_test_executions
                    WHERE tenant_id = $1 AND executed_at >= $2 AND executed_at <= $3
                    GROUP BY test_date
                    ORDER BY test_date
                """
                
                trend_results = await db.fetch(trend_query, uuid.UUID(tenant_id), start_date, end_date)
                
                # Calculate overall metrics
                total_tests = sum(row['total_tests'] for row in stats_results)
                total_passed = sum(row['passed_tests'] for row in stats_results)
                total_failed = sum(row['failed_tests'] for row in stats_results)
                overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
                
                return {
                    'report_period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'summary': {
                        'total_tests': total_tests,
                        'passed_tests': total_passed,
                        'failed_tests': total_failed,
                        'success_rate': round(overall_success_rate, 2)
                    },
                    'by_service': [dict(row) for row in stats_results],
                    'trends': [dict(row) for row in trend_results],
                    'generated_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")
            raise BusinessLogicException(f"Test report generation failed: {e}")

# Global testing managers
api_test_executor = APITestExecutor()
test_suite_manager = TestSuiteManager()
performance_test_manager = PerformanceTestManager()
test_report_generator = TestReportGenerator()

# Convenience functions
async def execute_api_test(session_id: str, tenant_id: str, endpoint_path: str,
                         http_method: str, request_data: Dict[str, Any],
                         headers: Optional[Dict[str, str]] = None,
                         validation_rules: Optional[Dict[str, Any]] = None) -> TestExecution:
    """Convenience function for API testing."""
    return await api_test_executor.execute_api_test(
        session_id, tenant_id, endpoint_path, http_method, request_data, headers, validation_rules
    )

async def execute_test_suite(suite_id: str, session_id: str, tenant_id: str) -> Dict[str, Any]:
    """Convenience function for test suite execution."""
    return await test_suite_manager.execute_test_suite(suite_id, session_id, tenant_id)

async def execute_load_test(endpoint_path: str, http_method: str, request_data: Dict[str, Any],
                          concurrent_users: int, duration_seconds: int,
                          session_id: str, tenant_id: str) -> Dict[str, Any]:
    """Convenience function for load testing."""
    return await performance_test_manager.execute_load_test(
        endpoint_path, http_method, request_data, concurrent_users, duration_seconds, session_id, tenant_id
    )

async def generate_test_report(tenant_id: str, start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Convenience function for test report generation."""
    return await test_report_generator.generate_test_report(tenant_id, start_date, end_date)
