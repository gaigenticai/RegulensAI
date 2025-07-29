"""
Regulens AI - Integration Test Fixtures
Comprehensive test fixtures for end-to-end integration testing.
"""

import pytest
import asyncio
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, AsyncGenerator
import httpx
from fastapi.testclient import TestClient
import structlog

from core_infra.api.main import app
from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.api.auth import create_access_token, hash_password

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

@pytest.fixture(scope="session")
async def setup_test_environment():
    """Setup test environment and cleanup after tests."""
    logger.info("Setting up integration test environment")
    
    # Initialize application components
    try:
        # Initialize database connections
        async with get_database() as db:
            await db.fetchval("SELECT 1")
        
        # Initialize other components as needed
        logger.info("Test environment setup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Test environment setup failed: {e}")
        raise
    finally:
        logger.info("Cleaning up test environment")
        await cleanup_test_data()

@pytest.fixture(scope="session")
def test_client():
    """Create test client for API testing."""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
async def test_tenant() -> Dict[str, Any]:
    """Create test tenant for integration tests."""
    tenant_id = str(uuid.uuid4())
    tenant_data = {
        "id": tenant_id,
        "name": "Integration Test Tenant",
        "domain": "test.regulens.ai",
        "subscription_tier": "enterprise",
        "is_active": True,
        "settings": {
            "compliance_frameworks": ["SOX", "GDPR"],
            "risk_tolerance": "medium",
            "notification_preferences": {
                "email": True,
                "sms": False
            }
        }
    }
    
    try:
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO tenants (
                    id, name, domain, subscription_tier, is_active, 
                    settings, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                uuid.UUID(tenant_id),
                tenant_data["name"],
                tenant_data["domain"],
                tenant_data["subscription_tier"],
                tenant_data["is_active"],
                tenant_data["settings"],
                datetime.utcnow(),
                datetime.utcnow()
            )
        
        logger.info(f"Created test tenant: {tenant_id}")
        return tenant_data
        
    except Exception as e:
        logger.error(f"Failed to create test tenant: {e}")
        raise

@pytest.fixture(scope="session")
async def test_user(test_tenant) -> Dict[str, Any]:
    """Create test user for integration tests."""
    user_id = str(uuid.uuid4())
    password = "test_password"
    password_hash = hash_password(password)
    
    user_data = {
        "id": user_id,
        "tenant_id": test_tenant["id"],
        "email": "test.user@regulens.ai",
        "full_name": "Test User",
        "role": "admin",
        "department": "compliance",
        "is_active": True,
        "password": password  # Store plain password for testing
    }
    
    try:
        async with get_database() as db:
            # Create user
            await db.execute(
                """
                INSERT INTO users (
                    id, tenant_id, email, full_name, role, department,
                    is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                uuid.UUID(user_id),
                uuid.UUID(test_tenant["id"]),
                user_data["email"],
                user_data["full_name"],
                user_data["role"],
                user_data["department"],
                user_data["is_active"],
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Create user credentials
            await db.execute(
                """
                INSERT INTO user_credentials (
                    id, user_id, password_hash, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                uuid.uuid4(),
                uuid.UUID(user_id),
                password_hash,
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Grant admin permissions
            admin_permissions = [
                "auth.login", "users.read", "users.create", "users.update",
                "tenants.read", "tenants.update", "compliance.programs.read",
                "compliance.programs.create", "compliance.programs.update",
                "aml.customers.read", "aml.customers.screen", "reports.read",
                "reports.create", "ai.analysis.trigger", "system.admin"
            ]
            
            for permission_name in admin_permissions:
                # Get or create permission
                permission = await db.fetchrow(
                    "SELECT id FROM permissions WHERE name = $1",
                    permission_name
                )
                
                if permission:
                    # Grant permission to user
                    await db.execute(
                        """
                        INSERT INTO user_permissions (
                            id, user_id, permission_id, granted_at
                        ) VALUES ($1, $2, $3, $4)
                        ON CONFLICT (user_id, permission_id) DO NOTHING
                        """,
                        uuid.uuid4(),
                        uuid.UUID(user_id),
                        permission["id"],
                        datetime.utcnow()
                    )
        
        logger.info(f"Created test user: {user_id}")
        return user_data
        
    except Exception as e:
        logger.error(f"Failed to create test user: {e}")
        raise

@pytest.fixture(scope="session")
async def test_customer(test_tenant) -> Dict[str, Any]:
    """Create test customer for integration tests."""
    customer_id = str(uuid.uuid4())
    customer_data = {
        "id": customer_id,
        "tenant_id": test_tenant["id"],
        "customer_type": "individual",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "date_of_birth": "1985-06-15",
        "country": "US",
        "address": "123 Main St, City, State 12345",
        "risk_score": 25,
        "risk_category": "low",
        "kyc_status": "compliant",
        "status": "active"
    }
    
    try:
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO customers (
                    id, tenant_id, customer_type, first_name, last_name,
                    email, phone, date_of_birth, country, address,
                    risk_score, risk_category, kyc_status, status,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """,
                uuid.UUID(customer_id),
                uuid.UUID(test_tenant["id"]),
                customer_data["customer_type"],
                customer_data["first_name"],
                customer_data["last_name"],
                customer_data["email"],
                customer_data["phone"],
                datetime.strptime(customer_data["date_of_birth"], "%Y-%m-%d").date(),
                customer_data["country"],
                customer_data["address"],
                customer_data["risk_score"],
                customer_data["risk_category"],
                customer_data["kyc_status"],
                customer_data["status"],
                datetime.utcnow(),
                datetime.utcnow()
            )
        
        logger.info(f"Created test customer: {customer_id}")
        return customer_data
        
    except Exception as e:
        logger.error(f"Failed to create test customer: {e}")
        raise

@pytest.fixture(scope="function")
async def test_transaction(test_tenant, test_customer) -> Dict[str, Any]:
    """Create test transaction for integration tests."""
    transaction_id = str(uuid.uuid4())
    transaction_data = {
        "id": transaction_id,
        "tenant_id": test_tenant["id"],
        "customer_id": test_customer["id"],
        "transaction_type": "wire_transfer",
        "amount": 10000.00,
        "currency": "USD",
        "source_country": "US",
        "destination_country": "US",
        "description": "Test transaction",
        "monitoring_status": "pending",
        "risk_score": 15
    }
    
    try:
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO transactions (
                    id, tenant_id, customer_id, transaction_type, amount,
                    currency, source_country, destination_country, description,
                    monitoring_status, risk_score, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                uuid.UUID(transaction_id),
                uuid.UUID(test_tenant["id"]),
                uuid.UUID(test_customer["id"]),
                transaction_data["transaction_type"],
                transaction_data["amount"],
                transaction_data["currency"],
                transaction_data["source_country"],
                transaction_data["destination_country"],
                transaction_data["description"],
                transaction_data["monitoring_status"],
                transaction_data["risk_score"],
                datetime.utcnow(),
                datetime.utcnow()
            )
        
        logger.info(f"Created test transaction: {transaction_id}")
        yield transaction_data
        
        # Cleanup after test
        await db.execute(
            "DELETE FROM transactions WHERE id = $1",
            uuid.UUID(transaction_id)
        )
        
    except Exception as e:
        logger.error(f"Failed to create test transaction: {e}")
        raise

@pytest.fixture(scope="function")
async def test_compliance_program(test_tenant, test_user) -> Dict[str, Any]:
    """Create test compliance program for integration tests."""
    program_id = str(uuid.uuid4())
    program_data = {
        "id": program_id,
        "tenant_id": test_tenant["id"],
        "name": "Test Compliance Program",
        "description": "Test compliance program for integration testing",
        "framework": "SOX",
        "jurisdiction": "US",
        "effective_date": "2024-01-01",
        "review_frequency": 365,
        "owner_id": test_user["id"],
        "is_active": True
    }
    
    try:
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO compliance_programs (
                    id, tenant_id, name, description, framework, jurisdiction,
                    effective_date, review_frequency, owner_id, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                uuid.UUID(program_id),
                uuid.UUID(test_tenant["id"]),
                program_data["name"],
                program_data["description"],
                program_data["framework"],
                program_data["jurisdiction"],
                datetime.strptime(program_data["effective_date"], "%Y-%m-%d").date(),
                program_data["review_frequency"],
                uuid.UUID(test_user["id"]),
                program_data["is_active"],
                datetime.utcnow(),
                datetime.utcnow()
            )
        
        logger.info(f"Created test compliance program: {program_id}")
        yield program_data
        
        # Cleanup after test
        await db.execute(
            "DELETE FROM compliance_programs WHERE id = $1",
            uuid.UUID(program_id)
        )
        
    except Exception as e:
        logger.error(f"Failed to create test compliance program: {e}")
        raise

async def cleanup_test_data():
    """Clean up test data after integration tests."""
    try:
        async with get_database() as db:
            # Clean up in reverse dependency order
            cleanup_tables = [
                "user_permissions",
                "user_credentials", 
                "user_sessions",
                "transactions",
                "customers",
                "compliance_requirements",
                "compliance_programs",
                "tasks",
                "screening_results",
                "screening_tasks",
                "enhanced_monitoring",
                "ai_analysis_results",
                "report_generations",
                "audit_logs",
                "security_events",
                "file_uploads",
                "performance_metrics",
                "system_health_checks",
                "backup_logs",
                "notifications",
                "notification_deliveries",
                "alerts",
                "alert_history",
                "ui_portal_sessions",
                "ui_search_logs",
                "ui_test_executions",
                "ui_portal_analytics",
                "ui_test_suites",
                "users",
                "tenants"
            ]
            
            for table in cleanup_tables:
                try:
                    # Only delete test data (identified by specific patterns)
                    if table == "tenants":
                        await db.execute(
                            "DELETE FROM tenants WHERE domain LIKE '%test.regulens.ai%'"
                        )
                    elif table == "users":
                        await db.execute(
                            "DELETE FROM users WHERE email LIKE '%@regulens.ai' AND email LIKE 'test.%'"
                        )
                    else:
                        # For other tables, we rely on CASCADE deletes from tenant/user cleanup
                        pass
                        
                except Exception as e:
                    logger.warning(f"Failed to cleanup table {table}: {e}")
        
        logger.info("Test data cleanup completed")
        
    except Exception as e:
        logger.error(f"Test data cleanup failed: {e}")

@pytest.fixture(scope="function")
async def auth_headers(test_client, test_user, test_tenant) -> Dict[str, str]:
    """Get authentication headers for API requests."""
    login_response = test_client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    
    if login_response.status_code != 200:
        raise Exception(f"Login failed: {login_response.text}")
    
    auth_data = login_response.json()
    return {
        "Authorization": f"Bearer {auth_data['access_token']}",
        "X-Tenant-ID": test_tenant["id"],
        "Content-Type": "application/json"
    }

class DatabaseTestHelper:
    """Helper class for database operations in tests."""
    
    @staticmethod
    async def create_test_record(table: str, data: Dict[str, Any]) -> str:
        """Create a test record in the specified table."""
        record_id = str(uuid.uuid4())
        data["id"] = uuid.UUID(record_id)
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        async with get_database() as db:
            await db.execute(query, *values)
        
        return record_id
    
    @staticmethod
    async def delete_test_record(table: str, record_id: str):
        """Delete a test record from the specified table."""
        async with get_database() as db:
            await db.execute(
                f"DELETE FROM {table} WHERE id = $1",
                uuid.UUID(record_id)
            )
    
    @staticmethod
    async def get_record_count(table: str, where_clause: str = "", params: list = None) -> int:
        """Get the count of records in a table."""
        query = f"SELECT COUNT(*) FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        async with get_database() as db:
            result = await db.fetchval(query, *(params or []))
            return result

# Export helper for use in tests
db_helper = DatabaseTestHelper()
