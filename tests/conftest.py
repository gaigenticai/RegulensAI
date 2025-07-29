"""
Pytest configuration and fixtures for Regulens AI test suite.
"""

import asyncio
import pytest
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
from fastapi.testclient import TestClient
from httpx import AsyncClient

from core_infra.api.main import app
from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.api.auth import create_access_token, get_password_hash

# Test configuration
settings = get_settings()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def db_connection():
    """Create a database connection for testing."""
    async with get_database() as db:
        yield db

@pytest.fixture
async def test_tenant(db_connection) -> Dict[str, Any]:
    """Create a test tenant."""
    tenant_id = uuid.uuid4()
    tenant_data = {
        'id': tenant_id,
        'name': 'Test Organization',
        'domain': 'test.example.com',
        'industry': 'financial_services',
        'country': 'US',
        'timezone': 'UTC',
        'settings': {},
        'is_active': True
    }
    
    await db_connection.execute(
        """
        INSERT INTO tenants (id, name, domain, industry, country, timezone, settings, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        tenant_data['id'],
        tenant_data['name'],
        tenant_data['domain'],
        tenant_data['industry'],
        tenant_data['country'],
        tenant_data['timezone'],
        tenant_data['settings'],
        tenant_data['is_active']
    )
    
    yield tenant_data
    
    # Cleanup
    await db_connection.execute("DELETE FROM tenants WHERE id = $1", tenant_id)

@pytest.fixture
async def test_user(db_connection, test_tenant) -> Dict[str, Any]:
    """Create a test user."""
    user_id = uuid.uuid4()
    user_data = {
        'id': user_id,
        'tenant_id': test_tenant['id'],
        'email': 'test@example.com',
        'full_name': 'Test User',
        'role': 'admin',
        'department': 'compliance',
        'is_active': True
    }
    
    # Create user
    await db_connection.execute(
        """
        INSERT INTO users (id, tenant_id, email, full_name, role, department, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        user_data['id'],
        user_data['tenant_id'],
        user_data['email'],
        user_data['full_name'],
        user_data['role'],
        user_data['department'],
        user_data['is_active']
    )
    
    # Create user credentials
    password_hash = get_password_hash('testpassword123')
    await db_connection.execute(
        """
        INSERT INTO user_credentials (user_id, password_hash)
        VALUES ($1, $2)
        """,
        user_data['id'],
        password_hash
    )
    
    yield user_data
    
    # Cleanup
    await db_connection.execute("DELETE FROM user_credentials WHERE user_id = $1", user_id)
    await db_connection.execute("DELETE FROM users WHERE id = $1", user_id)

@pytest.fixture
async def auth_headers(test_user) -> Dict[str, str]:
    """Create authentication headers for test requests."""
    token_data = {
        "user_id": str(test_user['id']),
        "tenant_id": str(test_user['tenant_id']),
        "email": test_user['email'],
        "role": test_user['role'],
        "permissions": ["auth.login", "users.read", "compliance.programs.read"]
    }
    
    access_token = create_access_token(token_data)
    
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture
async def test_customer(db_connection, test_tenant) -> Dict[str, Any]:
    """Create a test customer."""
    customer_id = uuid.uuid4()
    customer_data = {
        'id': customer_id,
        'tenant_id': test_tenant['id'],
        'customer_type': 'individual',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'phone': '+1234567890',
        'country': 'US',
        'risk_score': 25,
        'risk_category': 'low',
        'kyc_status': 'compliant',
        'pep_status': False,
        'sanctions_status': False,
        'status': 'active'
    }
    
    await db_connection.execute(
        """
        INSERT INTO customers (
            id, tenant_id, customer_type, first_name, last_name, email, phone,
            country, risk_score, risk_category, kyc_status, pep_status,
            sanctions_status, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
        customer_data['id'],
        customer_data['tenant_id'],
        customer_data['customer_type'],
        customer_data['first_name'],
        customer_data['last_name'],
        customer_data['email'],
        customer_data['phone'],
        customer_data['country'],
        customer_data['risk_score'],
        customer_data['risk_category'],
        customer_data['kyc_status'],
        customer_data['pep_status'],
        customer_data['sanctions_status'],
        customer_data['status']
    )
    
    yield customer_data
    
    # Cleanup
    await db_connection.execute("DELETE FROM customers WHERE id = $1", customer_id)

@pytest.fixture
async def test_transaction(db_connection, test_customer) -> Dict[str, Any]:
    """Create a test transaction."""
    transaction_id = uuid.uuid4()
    transaction_data = {
        'id': transaction_id,
        'tenant_id': test_customer['tenant_id'],
        'customer_id': test_customer['id'],
        'transaction_type': 'wire_transfer',
        'amount': 5000.00,
        'currency': 'USD',
        'source_country': 'US',
        'destination_country': 'CA',
        'monitoring_status': 'pending',
        'risk_score': 15,
        'suspicious_indicators': [],
        'requires_sar': False
    }
    
    await db_connection.execute(
        """
        INSERT INTO transactions (
            id, tenant_id, customer_id, transaction_type, amount, currency,
            source_country, destination_country, monitoring_status, risk_score,
            suspicious_indicators, requires_sar
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """,
        transaction_data['id'],
        transaction_data['tenant_id'],
        transaction_data['customer_id'],
        transaction_data['transaction_type'],
        transaction_data['amount'],
        transaction_data['currency'],
        transaction_data['source_country'],
        transaction_data['destination_country'],
        transaction_data['monitoring_status'],
        transaction_data['risk_score'],
        transaction_data['suspicious_indicators'],
        transaction_data['requires_sar']
    )
    
    yield transaction_data
    
    # Cleanup
    await db_connection.execute("DELETE FROM transactions WHERE id = $1", transaction_id)

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return {
        'jwt_secret_key': 'test-secret-key',
        'jwt_algorithm': 'HS256',
        'jwt_access_token_expire_minutes': 30,
        'jwt_refresh_token_expire_days': 7
    }

# Test utilities
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user_data(tenant_id: uuid.UUID, **overrides) -> Dict[str, Any]:
        """Create user test data."""
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'role': 'analyst',
            'department': 'compliance',
            'password': 'testpassword123',
            'permissions': ['users.read', 'compliance.programs.read'],
            'is_active': True
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_customer_data(tenant_id: uuid.UUID, **overrides) -> Dict[str, Any]:
        """Create customer test data."""
        data = {
            'customer_type': 'individual',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'customer@example.com',
            'phone': '+1234567890',
            'country': 'US',
            'risk_score': 25,
            'kyc_status': 'pending'
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_transaction_data(customer_id: uuid.UUID, **overrides) -> Dict[str, Any]:
        """Create transaction test data."""
        data = {
            'transaction_type': 'wire_transfer',
            'amount': 1000.00,
            'currency': 'USD',
            'source_country': 'US',
            'destination_country': 'CA'
        }
        data.update(overrides)
        return data

@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory
