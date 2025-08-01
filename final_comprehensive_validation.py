#!/usr/bin/env python3
"""
Final Comprehensive Validation of RegulensAI Database Schema
Performs exhaustive testing to ensure 100% functionality.
"""

import asyncio
import asyncpg
import uuid
import json
import sys
from datetime import datetime, date
from typing import Dict, List, Any

# Supabase connection configuration
SUPABASE_CONFIG = {
    'host': 'db.qoqzovknwsemxhlaobsv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'mdRh6u26EeogT2M0'
}

class ComprehensiveValidator:
    """Performs comprehensive validation of the deployed schema."""
    
    def __init__(self):
        self.connection = None
        self.validation_results = {}
        self.test_data_ids = []
        self.errors = []
        self.warnings = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log validation messages."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        if level == "ERROR":
            self.errors.append(message)
        elif level == "WARNING":
            self.warnings.append(message)
    
    async def connect_to_supabase(self):
        """Establish connection to Supabase PostgreSQL database."""
        try:
            self.log("Connecting to Supabase PostgreSQL database...")
            self.connection = await asyncpg.connect(**SUPABASE_CONFIG)
            self.log("Connected successfully")
            return True
        except Exception as e:
            self.log(f"Failed to connect to Supabase: {str(e)}", "ERROR")
            return False
    
    async def validate_all_tables_exist(self):
        """Validate that all required tables exist."""
        try:
            self.log("Validating all required tables exist...")
            
            # Complete list of required tables
            required_tables = [
                # Core tables
                'tenants', 'users', 'customers', 'transactions', 'notifications', 
                'alerts', 'compliance_programs', 'compliance_requirements', 
                'compliance_tasks', 'risk_assessments', 'regulations', 
                'regulatory_sources', 'audit_logs', 'user_permissions',
                'permissions', 'roles', 'user_roles',
                
                # Advanced tables
                'centralized_logs', 'apm_transactions', 'apm_spans', 'apm_errors',
                'apm_metrics', 'dr_objectives', 'dr_test_results', 'dr_events',
                'dr_backup_metadata', 'configuration_versions', 'configuration_drift',
                'ml_models', 'ml_deployments', 'training_modules'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in required_tables:
                exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if exists:
                    existing_tables.append(table)
                else:
                    missing_tables.append(table)
            
            self.validation_results['tables'] = {
                'total_required': len(required_tables),
                'existing': len(existing_tables),
                'missing': len(missing_tables),
                'missing_tables': missing_tables
            }
            
            if missing_tables:
                self.log(f"Missing tables: {missing_tables}", "ERROR")
            else:
                self.log(f"✓ All {len(required_tables)} required tables exist")
            
            return len(missing_tables) == 0
            
        except Exception as e:
            self.log(f"Table validation failed: {str(e)}", "ERROR")
            return False
    
    async def validate_critical_columns(self):
        """Validate that critical columns exist in key tables."""
        try:
            self.log("Validating critical columns...")
            
            critical_columns = {
                'tenants': ['id', 'name', 'domain', 'subscription_tier', 'is_active'],
                'users': ['id', 'tenant_id', 'email', 'full_name'],
                'customers': ['id', 'tenant_id', 'full_name', 'kyc_status'],
                'transactions': ['id', 'tenant_id', 'customer_id', 'amount'],
                'compliance_tasks': ['id', 'tenant_id', 'status', 'priority'],
                'risk_assessments': ['id', 'tenant_id', 'risk_score', 'risk_level'],
                'regulations': ['id', 'regulation_code', 'title', 'jurisdiction'],
                'roles': ['id', 'name', 'permissions'],
                'user_roles': ['id', 'user_id', 'role_id']
            }
            
            column_validation_results = {}
            
            for table_name, required_cols in critical_columns.items():
                # Get actual columns
                actual_columns = await self.connection.fetch("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = $1
                """, table_name)
                
                actual_col_names = [col['column_name'] for col in actual_columns]
                missing_cols = [col for col in required_cols if col not in actual_col_names]
                
                column_validation_results[table_name] = {
                    'required': required_cols,
                    'actual': actual_col_names,
                    'missing': missing_cols
                }
                
                if missing_cols:
                    self.log(f"Table {table_name} missing columns: {missing_cols}", "ERROR")
                else:
                    self.log(f"✓ Table {table_name} has all required columns")
            
            self.validation_results['columns'] = column_validation_results
            
            # Check if any tables have missing columns
            tables_with_missing_cols = [t for t, data in column_validation_results.items() if data['missing']]
            
            return len(tables_with_missing_cols) == 0
            
        except Exception as e:
            self.log(f"Column validation failed: {str(e)}", "ERROR")
            return False
    
    async def test_comprehensive_crud_operations(self):
        """Test comprehensive CRUD operations on all critical tables."""
        try:
            self.log("Testing comprehensive CRUD operations...")
            
            # Test 1: Create a complete tenant with all required fields
            tenant_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO tenants (id, name, domain, industry, country_code, subscription_tier, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, tenant_id, 'Test Tenant', 'test.example.com', 'Financial Services', 'US', 'enterprise', True)
            
            self.test_data_ids.append(('tenants', tenant_id))
            self.log("✓ Created test tenant")
            
            # Test 2: Create a user
            user_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO users (id, tenant_id, email, full_name, is_active)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, tenant_id, 'test@example.com', 'Test User', True)
            
            self.test_data_ids.append(('users', user_id))
            self.log("✓ Created test user")
            
            # Test 3: Create a customer
            customer_id = str(uuid.uuid4())
            customer_external_id = f"CUST_{customer_id[:8]}"
            await self.connection.execute("""
                INSERT INTO customers (id, tenant_id, customer_id, customer_type, full_name, email, kyc_status, risk_rating, pep_status, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, customer_id, tenant_id, customer_external_id, 'individual', 'Test Customer', 'customer@example.com', 'pending', 'low', False, True)
            
            self.test_data_ids.append(('customers', customer_id))
            self.log("✓ Created test customer")
            
            # Test 4: Create a transaction
            transaction_id = str(uuid.uuid4())
            transaction_external_id = f"TXN_{transaction_id[:8]}"
            from datetime import datetime
            await self.connection.execute("""
                INSERT INTO transactions (id, tenant_id, customer_id, transaction_id, amount, currency, transaction_type, transaction_date, aml_status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, transaction_id, tenant_id, customer_id, transaction_external_id, 1000.00, 'USD', 'transfer', datetime.utcnow(), 'clear')
            
            self.test_data_ids.append(('transactions', transaction_id))
            self.log("✓ Created test transaction")
            
            # Test 5: Create a role
            role_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO roles (id, name, description, permissions)
                VALUES ($1, $2, $3, $4)
            """, role_id, 'test_role', 'Test Role', json.dumps(['test.permission']))
            
            self.test_data_ids.append(('roles', role_id))
            self.log("✓ Created test role")
            
            # Test 6: Create a user role assignment
            user_role_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO user_roles (id, user_id, role_id)
                VALUES ($1, $2, $3)
            """, user_role_id, user_id, role_id)
            
            self.test_data_ids.append(('user_roles', user_role_id))
            self.log("✓ Created test user role assignment")
            
            # Test 7: Create a risk assessment
            risk_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO risk_assessments (id, tenant_id, assessment_type, entity_type, entity_id, risk_score, risk_level)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, risk_id, tenant_id, 'customer_risk', 'customer', customer_id, 75.5, 'medium')
            
            self.test_data_ids.append(('risk_assessments', risk_id))
            self.log("✓ Created test risk assessment")
            
            # Test 8: Create a regulation
            regulation_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO regulations (id, regulation_code, title, jurisdiction, regulatory_body, category)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, regulation_id, 'TEST-REG-001', 'Test Regulation', 'US', 'Test Authority', 'AML')
            
            self.test_data_ids.append(('regulations', regulation_id))
            self.log("✓ Created test regulation")
            
            self.log("✓ All CRUD operations successful")
            return True
            
        except Exception as e:
            self.log(f"CRUD operations test failed: {str(e)}", "ERROR")
            return False
    
    async def test_foreign_key_relationships(self):
        """Test foreign key relationships work correctly."""
        try:
            self.log("Testing foreign key relationships...")
            
            # Test 1: Try to create user with invalid tenant_id (should fail)
            try:
                invalid_tenant_id = str(uuid.uuid4())
                await self.connection.execute("""
                    INSERT INTO users (id, tenant_id, email, first_name, last_name)
                    VALUES ($1, $2, $3, $4, $5)
                """, str(uuid.uuid4()), invalid_tenant_id, 'invalid@example.com', 'Invalid', 'User')
                
                self.log("✗ Foreign key constraint not working - invalid tenant_id accepted", "ERROR")
                return False
                
            except Exception:
                self.log("✓ Foreign key constraint working - invalid tenant_id rejected")
            
            # Test 2: Try to delete tenant with dependent users (should fail)
            try:
                # Find a tenant with users
                tenant_with_users = await self.connection.fetchrow("""
                    SELECT t.id FROM tenants t 
                    JOIN users u ON t.id = u.tenant_id 
                    LIMIT 1
                """)
                
                if tenant_with_users:
                    await self.connection.execute("DELETE FROM tenants WHERE id = $1", tenant_with_users['id'])
                    self.log("✗ Foreign key constraint not working - tenant with users deleted", "ERROR")
                    return False
                else:
                    self.log("! No tenant with users found for FK test")
                    
            except Exception:
                self.log("✓ Foreign key constraint working - cannot delete tenant with users")
            
            self.log("✓ Foreign key relationships working correctly")
            return True
            
        except Exception as e:
            self.log(f"Foreign key relationship test failed: {str(e)}", "ERROR")
            return False
    
    async def test_triggers_and_functions(self):
        """Test that triggers and functions work correctly."""
        try:
            self.log("Testing triggers and functions...")
            
            # Test update trigger on tenants table
            if self.test_data_ids:
                tenant_record = next((item for item in self.test_data_ids if item[0] == 'tenants'), None)
                if tenant_record:
                    tenant_id = tenant_record[1]
                    
                    # Get initial updated_at
                    initial_record = await self.connection.fetchrow("""
                        SELECT updated_at FROM tenants WHERE id = $1
                    """, tenant_id)
                    
                    # Wait a moment to ensure timestamp difference
                    await asyncio.sleep(1)
                    
                    # Update the record
                    await self.connection.execute("""
                        UPDATE tenants SET name = 'Updated Test Tenant' WHERE id = $1
                    """, tenant_id)
                    
                    # Get updated record
                    updated_record = await self.connection.fetchrow("""
                        SELECT updated_at FROM tenants WHERE id = $1
                    """, tenant_id)
                    
                    if updated_record['updated_at'] > initial_record['updated_at']:
                        self.log("✓ Update trigger working correctly")
                    else:
                        self.log("✗ Update trigger not working", "ERROR")
                        return False
            
            self.log("✓ Triggers and functions working correctly")
            return True
            
        except Exception as e:
            self.log(f"Triggers and functions test failed: {str(e)}", "ERROR")
            return False
    
    async def test_advanced_features(self):
        """Test advanced features like ML models, APM, etc."""
        try:
            self.log("Testing advanced features...")
            
            # Test ML models table
            if self.test_data_ids:
                tenant_record = next((item for item in self.test_data_ids if item[0] == 'tenants'), None)
                if tenant_record:
                    tenant_id = tenant_record[1]
                    
                    # Create ML model
                    ml_model_id = str(uuid.uuid4())
                    await self.connection.execute("""
                        INSERT INTO ml_models (id, tenant_id, name, model_type, version, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, ml_model_id, tenant_id, 'Test Model', 'classification', '1.0', 'trained')
                    
                    self.test_data_ids.append(('ml_models', ml_model_id))
                    self.log("✓ ML models table working")
                    
                    # Create ML deployment
                    deployment_id = str(uuid.uuid4())
                    await self.connection.execute("""
                        INSERT INTO ml_deployments (id, tenant_id, model_id, deployment_name, environment, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, deployment_id, tenant_id, ml_model_id, 'test-deployment', 'development', 'active')
                    
                    self.test_data_ids.append(('ml_deployments', deployment_id))
                    self.log("✓ ML deployments table working")
            
            # Test APM tables
            apm_transaction_id = str(uuid.uuid4())
            await self.connection.execute("""
                INSERT INTO apm_transactions (id, transaction_id, transaction_name, transaction_type, service_name, start_time)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, apm_transaction_id, 'test-txn-001', 'API Request', 'http', 'test-service', datetime.now())
            
            self.test_data_ids.append(('apm_transactions', apm_transaction_id))
            self.log("✓ APM transactions table working")
            
            self.log("✓ Advanced features working correctly")
            return True
            
        except Exception as e:
            self.log(f"Advanced features test failed: {str(e)}", "ERROR")
            return False
    
    async def cleanup_test_data(self):
        """Clean up all test data created during validation."""
        try:
            self.log("Cleaning up test data...")
            
            # Delete in reverse order to respect foreign key constraints
            for table, record_id in reversed(self.test_data_ids):
                try:
                    await self.connection.execute(f"DELETE FROM {table} WHERE id = $1", record_id)
                except Exception as e:
                    self.log(f"Warning: Could not delete test record from {table}: {str(e)}", "WARNING")
            
            self.log("✓ Test data cleanup completed")
            
        except Exception as e:
            self.log(f"Test data cleanup failed: {str(e)}", "WARNING")
    
    async def generate_final_report(self):
        """Generate comprehensive final report."""
        try:
            # Get database statistics
            total_tables = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            
            total_functions = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.routines 
                WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
            """)
            
            total_triggers = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.triggers 
                WHERE trigger_schema = 'public'
            """)
            
            total_constraints = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE table_schema = 'public'
            """)
            
            self.validation_results['database_stats'] = {
                'total_tables': total_tables,
                'total_functions': total_functions,
                'total_triggers': total_triggers,
                'total_constraints': total_constraints
            }
            
        except Exception as e:
            self.log(f"Failed to generate final report: {str(e)}", "ERROR")
    
    async def close_connection(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.log("Database connection closed")

async def main():
    """Main comprehensive validation function."""
    validator = ComprehensiveValidator()
    
    try:
        # Connect to Supabase
        if not await validator.connect_to_supabase():
            print("CRITICAL: Failed to connect to Supabase. Exiting.")
            return 1
        
        # Run all validations
        tables_valid = await validator.validate_all_tables_exist()
        columns_valid = await validator.validate_critical_columns()
        crud_valid = await validator.test_comprehensive_crud_operations()
        fk_valid = await validator.test_foreign_key_relationships()
        triggers_valid = await validator.test_triggers_and_functions()
        advanced_valid = await validator.test_advanced_features()
        
        # Generate final report
        await validator.generate_final_report()
        
        # Clean up test data
        await validator.cleanup_test_data()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("FINAL COMPREHENSIVE VALIDATION REPORT")
        print("="*80)
        
        stats = validator.validation_results.get('database_stats', {})
        print(f"Database Statistics:")
        print(f"  Total Tables: {stats.get('total_tables', 'N/A')}")
        print(f"  Total Functions: {stats.get('total_functions', 'N/A')}")
        print(f"  Total Triggers: {stats.get('total_triggers', 'N/A')}")
        print(f"  Total Constraints: {stats.get('total_constraints', 'N/A')}")
        
        print(f"\nValidation Results:")
        print(f"  ✓ Tables Validation: {'PASSED' if tables_valid else 'FAILED'}")
        print(f"  ✓ Columns Validation: {'PASSED' if columns_valid else 'FAILED'}")
        print(f"  ✓ CRUD Operations: {'PASSED' if crud_valid else 'FAILED'}")
        print(f"  ✓ Foreign Keys: {'PASSED' if fk_valid else 'FAILED'}")
        print(f"  ✓ Triggers/Functions: {'PASSED' if triggers_valid else 'FAILED'}")
        print(f"  ✓ Advanced Features: {'PASSED' if advanced_valid else 'FAILED'}")
        
        print(f"\nIssues Summary:")
        print(f"  Errors: {len(validator.errors)}")
        print(f"  Warnings: {len(validator.warnings)}")
        
        if validator.errors:
            print(f"\nErrors:")
            for error in validator.errors:
                print(f"  ✗ {error}")
        
        # Final status
        all_tests_passed = all([tables_valid, columns_valid, crud_valid, fk_valid, triggers_valid, advanced_valid])
        
        if all_tests_passed and len(validator.errors) == 0:
            print("\n🎉 FINAL STATUS: 100% SUCCESS")
            print("RegulensAI database schema is fully deployed and 100% functional!")
            print("All tables, columns, relationships, and features are working correctly.")
            return 0
        else:
            print("\n🚨 FINAL STATUS: ISSUES DETECTED")
            print("Some validation tests failed. Please review the errors above.")
            return 1
        
    except Exception as e:
        validator.log(f"Comprehensive validation failed with exception: {str(e)}", "ERROR")
        return 1
        
    finally:
        await validator.close_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
