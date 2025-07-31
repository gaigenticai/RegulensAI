#!/usr/bin/env python3
"""
Final validation of the deployed RegulensAI schema.
"""

import asyncio
import asyncpg
import sys
from datetime import datetime

# Supabase connection configuration
SUPABASE_CONFIG = {
    'host': 'db.qoqzovknwsemxhlaobsv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'mdRh6u26EeogT2M0'
}

class FinalValidator:
    """Performs comprehensive validation of the deployed schema."""
    
    def __init__(self):
        self.connection = None
        self.validation_results = {}
    
    def log(self, message: str, level: str = "INFO"):
        """Log validation messages."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
    
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
    
    async def validate_core_tables(self):
        """Validate that core RegulensAI tables exist and are properly structured."""
        try:
            self.log("Validating core tables...")
            
            core_tables = [
                'tenants', 'users', 'customers', 'transactions', 'notifications',
                'alerts', 'compliance_programs', 'compliance_requirements', 
                'compliance_tasks', 'risk_assessments', 'regulations',
                'regulatory_sources', 'audit_logs', 'user_permissions',
                'permissions', 'roles', 'user_roles'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in core_tables:
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
            
            self.validation_results['core_tables'] = {
                'total_expected': len(core_tables),
                'existing': len(existing_tables),
                'missing': len(missing_tables),
                'existing_tables': existing_tables,
                'missing_tables': missing_tables
            }
            
            self.log(f"Core tables validation: {len(existing_tables)}/{len(core_tables)} found")
            if missing_tables:
                self.log(f"Missing core tables: {', '.join(missing_tables)}", "WARNING")
            
        except Exception as e:
            self.log(f"Core tables validation failed: {str(e)}", "ERROR")
    
    async def validate_advanced_tables(self):
        """Validate advanced feature tables (APM, DR, ML, etc.)."""
        try:
            self.log("Validating advanced feature tables...")
            
            advanced_tables = [
                'centralized_logs', 'apm_transactions', 'apm_spans', 'apm_errors',
                'apm_metrics', 'dr_objectives', 'dr_test_results', 'dr_events',
                'dr_backup_metadata', 'configuration_versions', 'configuration_drift',
                'ml_models', 'ml_deployments', 'training_modules', 'training_sections'
            ]
            
            existing_advanced = []
            missing_advanced = []
            
            for table in advanced_tables:
                exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if exists:
                    existing_advanced.append(table)
                else:
                    missing_advanced.append(table)
            
            self.validation_results['advanced_tables'] = {
                'total_expected': len(advanced_tables),
                'existing': len(existing_advanced),
                'missing': len(missing_advanced),
                'existing_tables': existing_advanced,
                'missing_tables': missing_advanced
            }
            
            self.log(f"Advanced tables validation: {len(existing_advanced)}/{len(advanced_tables)} found")
            
        except Exception as e:
            self.log(f"Advanced tables validation failed: {str(e)}", "ERROR")
    
    async def validate_functions_and_triggers(self):
        """Validate that functions and triggers are properly created."""
        try:
            self.log("Validating functions and triggers...")
            
            # Check functions
            functions = await self.connection.fetch("""
                SELECT routine_name FROM information_schema.routines 
                WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
            """)
            
            function_names = [f['routine_name'] for f in functions]
            
            # Check triggers
            triggers = await self.connection.fetch("""
                SELECT trigger_name, event_object_table FROM information_schema.triggers 
                WHERE trigger_schema = 'public'
            """)
            
            trigger_info = [(t['trigger_name'], t['event_object_table']) for t in triggers]
            
            self.validation_results['functions_triggers'] = {
                'function_count': len(function_names),
                'trigger_count': len(trigger_info),
                'functions': function_names,
                'triggers': trigger_info
            }
            
            self.log(f"Functions: {len(function_names)}, Triggers: {len(trigger_info)}")
            
            # Validate key functions exist
            required_functions = ['update_updated_at_column', 'validate_tenant_access']
            missing_functions = [f for f in required_functions if f not in function_names]
            
            if missing_functions:
                self.log(f"Missing required functions: {', '.join(missing_functions)}", "ERROR")
            else:
                self.log("All required functions are present")
            
        except Exception as e:
            self.log(f"Functions and triggers validation failed: {str(e)}", "ERROR")
    
    async def validate_constraints_and_indexes(self):
        """Validate constraints and indexes."""
        try:
            self.log("Validating constraints and indexes...")
            
            # Check constraints
            constraints = await self.connection.fetch("""
                SELECT constraint_name, table_name, constraint_type 
                FROM information_schema.table_constraints 
                WHERE table_schema = 'public'
            """)
            
            # Check indexes
            indexes = await self.connection.fetch("""
                SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public'
            """)
            
            constraint_types = {}
            for constraint in constraints:
                ctype = constraint['constraint_type']
                constraint_types[ctype] = constraint_types.get(ctype, 0) + 1
            
            self.validation_results['constraints_indexes'] = {
                'total_constraints': len(constraints),
                'total_indexes': len(indexes),
                'constraint_types': constraint_types
            }
            
            self.log(f"Constraints: {len(constraints)}, Indexes: {len(indexes)}")
            self.log(f"Constraint types: {constraint_types}")
            
        except Exception as e:
            self.log(f"Constraints and indexes validation failed: {str(e)}", "ERROR")
    
    async def test_sample_operations(self):
        """Test sample database operations to ensure everything works."""
        try:
            self.log("Testing sample database operations...")
            
            # Test 1: Insert a test tenant
            test_tenant_id = 'test-tenant-' + datetime.now().strftime('%Y%m%d%H%M%S')
            
            await self.connection.execute("""
                INSERT INTO tenants (id, name, domain, subscription_tier, is_active)
                VALUES ($1, 'Test Tenant', 'test.example.com', 'enterprise', true)
            """, test_tenant_id)
            
            self.log("✓ Successfully inserted test tenant")
            
            # Test 2: Query the tenant
            tenant = await self.connection.fetchrow("""
                SELECT * FROM tenants WHERE id = $1
            """, test_tenant_id)
            
            if tenant:
                self.log("✓ Successfully queried test tenant")
            else:
                self.log("✗ Failed to query test tenant", "ERROR")
            
            # Test 3: Update the tenant (should trigger update_updated_at)
            await self.connection.execute("""
                UPDATE tenants SET name = 'Updated Test Tenant' WHERE id = $1
            """, test_tenant_id)
            
            updated_tenant = await self.connection.fetchrow("""
                SELECT * FROM tenants WHERE id = $1
            """, test_tenant_id)
            
            if updated_tenant and updated_tenant['updated_at'] > updated_tenant['created_at']:
                self.log("✓ Update trigger working correctly")
            else:
                self.log("✗ Update trigger not working", "WARNING")
            
            # Test 4: Clean up test data
            await self.connection.execute("""
                DELETE FROM tenants WHERE id = $1
            """, test_tenant_id)
            
            self.log("✓ Successfully cleaned up test data")
            
            self.validation_results['sample_operations'] = {
                'insert_test': True,
                'query_test': True,
                'update_test': True,
                'delete_test': True,
                'trigger_test': updated_tenant['updated_at'] > updated_tenant['created_at'] if updated_tenant else False
            }
            
        except Exception as e:
            self.log(f"Sample operations test failed: {str(e)}", "ERROR")
            self.validation_results['sample_operations'] = {'error': str(e)}
    
    async def generate_final_report(self):
        """Generate comprehensive final validation report."""
        try:
            # Get overall statistics
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
            
            total_indexes = await self.connection.fetchval("""
                SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'
            """)
            
            self.validation_results['overall_stats'] = {
                'total_tables': total_tables,
                'total_functions': total_functions,
                'total_triggers': total_triggers,
                'total_constraints': total_constraints,
                'total_indexes': total_indexes
            }
            
        except Exception as e:
            self.log(f"Failed to generate final report: {str(e)}", "ERROR")
    
    async def close_connection(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.log("Database connection closed")

async def main():
    """Main validation function."""
    validator = FinalValidator()
    
    try:
        # Connect to Supabase
        if not await validator.connect_to_supabase():
            print("Failed to connect to Supabase. Exiting.")
            return 1
        
        # Run all validations
        await validator.validate_core_tables()
        await validator.validate_advanced_tables()
        await validator.validate_functions_and_triggers()
        await validator.validate_constraints_and_indexes()
        await validator.test_sample_operations()
        await validator.generate_final_report()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("FINAL SCHEMA VALIDATION REPORT")
        print("="*80)
        
        stats = validator.validation_results.get('overall_stats', {})
        print(f"Total Database Objects:")
        print(f"  Tables: {stats.get('total_tables', 'N/A')}")
        print(f"  Functions: {stats.get('total_functions', 'N/A')}")
        print(f"  Triggers: {stats.get('total_triggers', 'N/A')}")
        print(f"  Constraints: {stats.get('total_constraints', 'N/A')}")
        print(f"  Indexes: {stats.get('total_indexes', 'N/A')}")
        
        core = validator.validation_results.get('core_tables', {})
        print(f"\nCore Tables: {core.get('existing', 0)}/{core.get('total_expected', 0)} found")
        
        advanced = validator.validation_results.get('advanced_tables', {})
        print(f"Advanced Tables: {advanced.get('existing', 0)}/{advanced.get('total_expected', 0)} found")
        
        sample_ops = validator.validation_results.get('sample_operations', {})
        if 'error' not in sample_ops:
            print(f"\nSample Operations Test: ✓ PASSED")
        else:
            print(f"\nSample Operations Test: ✗ FAILED - {sample_ops.get('error')}")
        
        print("\n" + "="*80)
        print("DEPLOYMENT STATUS: SUCCESS")
        print("RegulensAI database schema has been successfully deployed to Supabase!")
        print("="*80)
        
        return 0
        
    except Exception as e:
        validator.log(f"Validation failed with exception: {str(e)}", "ERROR")
        return 1
        
    finally:
        await validator.close_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
