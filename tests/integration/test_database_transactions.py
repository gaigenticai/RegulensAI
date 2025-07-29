"""
Regulens AI - Database Transaction Integration Tests
Comprehensive testing of database transactions, consistency, and performance.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
import structlog

from core_infra.database.connection import get_database
from core_infra.database.operations import db_operations
from tests.integration.fixtures import (
    test_tenant, test_user, test_customer, cleanup_test_data,
    setup_test_environment, db_helper
)

# Initialize logging
logger = structlog.get_logger(__name__)

class TestDatabaseTransactions:
    """Test database transaction integrity and consistency."""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, test_tenant, test_user):
        """Test that database transactions rollback properly on errors."""
        
        async with get_database() as db:
            # Start transaction
            async with db.transaction():
                try:
                    # Create a compliance program
                    program_id = uuid.uuid4()
                    await db.execute(
                        """
                        INSERT INTO compliance_programs (
                            id, tenant_id, name, description, framework, jurisdiction,
                            effective_date, review_frequency, owner_id, is_active,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        """,
                        program_id,
                        uuid.UUID(test_tenant["id"]),
                        "Test Program",
                        "Test Description",
                        "SOX",
                        "US",
                        datetime.utcnow().date(),
                        365,
                        uuid.UUID(test_user["id"]),
                        True,
                        datetime.utcnow(),
                        datetime.utcnow()
                    )
                    
                    # Verify program was created
                    program = await db.fetchrow(
                        "SELECT * FROM compliance_programs WHERE id = $1",
                        program_id
                    )
                    assert program is not None
                    
                    # Now cause an error (invalid foreign key)
                    await db.execute(
                        """
                        INSERT INTO compliance_requirements (
                            id, program_id, title, description, requirement_type,
                            priority, status, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        uuid.uuid4(),
                        uuid.uuid4(),  # Invalid program_id
                        "Test Requirement",
                        "Test Description",
                        "assessment",
                        "high",
                        "pending",
                        datetime.utcnow(),
                        datetime.utcnow()
                    )
                    
                except Exception as e:
                    logger.info(f"Expected error occurred: {e}")
                    raise  # Re-raise to trigger rollback
            
            # Verify that the program was rolled back
            program = await db.fetchrow(
                "SELECT * FROM compliance_programs WHERE id = $1",
                program_id
            )
            assert program is None, "Transaction should have been rolled back"
    
    @pytest.mark.asyncio
    async def test_concurrent_transaction_handling(self, test_tenant, test_user):
        """Test handling of concurrent database transactions."""
        
        async def create_compliance_program(name_suffix: str):
            """Create a compliance program in a separate transaction."""
            async with get_database() as db:
                program_id = uuid.uuid4()
                await db.execute(
                    """
                    INSERT INTO compliance_programs (
                        id, tenant_id, name, description, framework, jurisdiction,
                        effective_date, review_frequency, owner_id, is_active,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    program_id,
                    uuid.UUID(test_tenant["id"]),
                    f"Concurrent Program {name_suffix}",
                    "Test Description",
                    "SOX",
                    "US",
                    datetime.utcnow().date(),
                    365,
                    uuid.UUID(test_user["id"]),
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
                return str(program_id)
        
        # Create multiple programs concurrently
        tasks = [create_compliance_program(str(i)) for i in range(10)]
        program_ids = await asyncio.gather(*tasks)
        
        # Verify all programs were created
        async with get_database() as db:
            for program_id in program_ids:
                program = await db.fetchrow(
                    "SELECT * FROM compliance_programs WHERE id = $1",
                    uuid.UUID(program_id)
                )
                assert program is not None
                assert "Concurrent Program" in program["name"]
        
        # Cleanup
        async with get_database() as db:
            for program_id in program_ids:
                await db.execute(
                    "DELETE FROM compliance_programs WHERE id = $1",
                    uuid.UUID(program_id)
                )
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, test_tenant, test_user):
        """Test foreign key constraint enforcement."""
        
        async with get_database() as db:
            # Try to create a compliance requirement with invalid program_id
            with pytest.raises(Exception):  # Should raise foreign key constraint error
                await db.execute(
                    """
                    INSERT INTO compliance_requirements (
                        id, program_id, title, description, requirement_type,
                        priority, status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    uuid.uuid4(),
                    uuid.uuid4(),  # Invalid program_id
                    "Test Requirement",
                    "Test Description",
                    "assessment",
                    "high",
                    "pending",
                    datetime.utcnow(),
                    datetime.utcnow()
                )
    
    @pytest.mark.asyncio
    async def test_cascade_deletes(self, test_tenant, test_user):
        """Test cascade delete behavior."""
        
        async with get_database() as db:
            # Create compliance program
            program_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO compliance_programs (
                    id, tenant_id, name, description, framework, jurisdiction,
                    effective_date, review_frequency, owner_id, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                program_id,
                uuid.UUID(test_tenant["id"]),
                "Cascade Test Program",
                "Test Description",
                "SOX",
                "US",
                datetime.utcnow().date(),
                365,
                uuid.UUID(test_user["id"]),
                True,
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Create compliance requirement
            requirement_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO compliance_requirements (
                    id, program_id, title, description, requirement_type,
                    priority, status, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                requirement_id,
                program_id,
                "Test Requirement",
                "Test Description",
                "assessment",
                "high",
                "pending",
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Verify both records exist
            program = await db.fetchrow(
                "SELECT * FROM compliance_programs WHERE id = $1",
                program_id
            )
            requirement = await db.fetchrow(
                "SELECT * FROM compliance_requirements WHERE id = $1",
                requirement_id
            )
            assert program is not None
            assert requirement is not None
            
            # Delete the program (should cascade to requirement)
            await db.execute(
                "DELETE FROM compliance_programs WHERE id = $1",
                program_id
            )
            
            # Verify requirement was also deleted
            requirement = await db.fetchrow(
                "SELECT * FROM compliance_requirements WHERE id = $1",
                requirement_id
            )
            assert requirement is None, "Requirement should have been cascade deleted"

class TestDatabasePerformance:
    """Test database performance and optimization."""
    
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, test_tenant):
        """Test bulk insert performance."""
        
        start_time = datetime.utcnow()
        
        # Create 1000 test records
        async with get_database() as db:
            values = []
            for i in range(1000):
                values.append((
                    uuid.uuid4(),
                    uuid.UUID(test_tenant["id"]),
                    f"performance.test.{i}",
                    f"Performance Test {i}",
                    "count",
                    {},
                    datetime.utcnow()
                ))
            
            await db.executemany(
                """
                INSERT INTO performance_metrics (
                    id, tenant_id, metric_name, metric_value, metric_unit, tags, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                values
            )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Bulk insert of 1000 records took {duration:.3f} seconds")
        assert duration < 5.0, "Bulk insert should complete within 5 seconds"
        
        # Cleanup
        async with get_database() as db:
            await db.execute(
                "DELETE FROM performance_metrics WHERE metric_name LIKE 'performance.test.%'"
            )
    
    @pytest.mark.asyncio
    async def test_complex_query_performance(self, test_tenant, test_user):
        """Test performance of complex queries."""
        
        # Create test data
        async with get_database() as db:
            # Create multiple compliance programs
            program_ids = []
            for i in range(10):
                program_id = uuid.uuid4()
                program_ids.append(program_id)
                await db.execute(
                    """
                    INSERT INTO compliance_programs (
                        id, tenant_id, name, description, framework, jurisdiction,
                        effective_date, review_frequency, owner_id, is_active,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    program_id,
                    uuid.UUID(test_tenant["id"]),
                    f"Performance Test Program {i}",
                    "Test Description",
                    "SOX",
                    "US",
                    datetime.utcnow().date(),
                    365,
                    uuid.UUID(test_user["id"]),
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
                
                # Create requirements for each program
                for j in range(5):
                    await db.execute(
                        """
                        INSERT INTO compliance_requirements (
                            id, program_id, title, description, requirement_type,
                            priority, status, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        uuid.uuid4(),
                        program_id,
                        f"Requirement {j} for Program {i}",
                        "Test Description",
                        "assessment",
                        "high",
                        "pending",
                        datetime.utcnow(),
                        datetime.utcnow()
                    )
            
            # Execute complex query
            start_time = datetime.utcnow()
            
            results = await db.fetch(
                """
                SELECT 
                    p.id,
                    p.name,
                    p.framework,
                    COUNT(r.id) as requirement_count,
                    COUNT(r.id) FILTER (WHERE r.status = 'completed') as completed_count,
                    ROUND(
                        COUNT(r.id) FILTER (WHERE r.status = 'completed') * 100.0 / 
                        NULLIF(COUNT(r.id), 0), 2
                    ) as completion_percentage
                FROM compliance_programs p
                LEFT JOIN compliance_requirements r ON p.id = r.program_id
                WHERE p.tenant_id = $1 AND p.name LIKE 'Performance Test Program%'
                GROUP BY p.id, p.name, p.framework
                ORDER BY p.name
                """,
                uuid.UUID(test_tenant["id"])
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Complex query took {duration:.3f} seconds, returned {len(results)} results")
            assert duration < 1.0, "Complex query should complete within 1 second"
            assert len(results) == 10, "Should return 10 programs"
            
            # Cleanup
            for program_id in program_ids:
                await db.execute(
                    "DELETE FROM compliance_programs WHERE id = $1",
                    program_id
                )
    
    @pytest.mark.asyncio
    async def test_index_effectiveness(self, test_tenant):
        """Test that database indexes are effective."""
        
        async with get_database() as db:
            # Test tenant_id index effectiveness
            start_time = datetime.utcnow()
            
            # Query that should use tenant_id index
            result = await db.fetchval(
                "SELECT COUNT(*) FROM users WHERE tenant_id = $1",
                uuid.UUID(test_tenant["id"])
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Indexed query took {duration:.3f} seconds")
            assert duration < 0.1, "Indexed query should be very fast"

class TestDatabaseOperations:
    """Test database operations framework."""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test database health check functionality."""
        
        health_status = await db_operations.perform_health_check()
        
        assert health_status["overall_status"] in ["healthy", "degraded"]
        assert "checks" in health_status
        assert "connection" in health_status["checks"]
        assert "connection_pool" in health_status["checks"]
        assert "database_size" in health_status["checks"]
        
        # Connection check should be healthy
        assert health_status["checks"]["connection"]["status"] == "healthy"
        assert "response_time_ms" in health_status["checks"]["connection"]
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test database performance metrics collection."""
        
        metrics = await db_operations.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        if "error" not in metrics:
            assert "connections" in metrics
            assert "database_size" in metrics
            
            # Verify connection metrics structure
            conn_metrics = metrics["connections"]
            assert "total_connections" in conn_metrics
            assert "active_connections" in conn_metrics
            assert "idle_connections" in conn_metrics
    
    @pytest.mark.asyncio
    async def test_database_optimization(self):
        """Test database optimization operations."""
        
        optimization_results = await db_operations.optimize_database()
        
        assert "timestamp" in optimization_results
        assert "operations" in optimization_results
        
        # Check that optimization operations were attempted
        operations = optimization_results["operations"]
        expected_operations = ["analyze_tables", "vacuum", "index_maintenance", "update_statistics"]
        
        for operation in expected_operations:
            assert operation in operations
            assert "status" in operations[operation]
    
    @pytest.mark.asyncio
    async def test_data_cleanup(self, test_tenant):
        """Test data cleanup functionality."""
        
        # Create some old test data
        async with get_database() as db:
            old_date = datetime.utcnow() - timedelta(days=100)
            
            # Create old audit log entry
            await db.execute(
                """
                INSERT INTO audit_logs (
                    id, tenant_id, action, resource_type, created_at
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                uuid.uuid4(),
                uuid.UUID(test_tenant["id"]),
                "test_action",
                "test_resource",
                old_date
            )
            
            # Create old performance metric
            await db.execute(
                """
                INSERT INTO performance_metrics (
                    id, tenant_id, metric_name, metric_value, metric_unit, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid.uuid4(),
                uuid.UUID(test_tenant["id"]),
                "test.metric",
                1.0,
                "count",
                old_date
            )
        
        # Run cleanup with 90-day retention
        cleanup_results = await db_operations.cleanup_old_data(retention_days=90)
        
        assert "timestamp" in cleanup_results
        assert "operations" in cleanup_results
        assert cleanup_results["retention_days"] == 90
        
        # Verify old data was cleaned up
        operations = cleanup_results["operations"]
        if "audit_logs" in operations:
            assert operations["audit_logs"]["deleted_rows"] >= 0
        if "performance_metrics" in operations:
            assert operations["performance_metrics"]["deleted_rows"] >= 0

# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    # Run database integration tests
    pytest.main([__file__, "-v", "--tb=short"])
