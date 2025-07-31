#!/usr/bin/env python3
"""
Fix identified schema deployment issues and complete the deployment.
"""

import asyncio
import asyncpg
import os
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

class SchemaFixer:
    """Fixes the identified schema deployment issues."""
    
    def __init__(self):
        self.connection = None
        self.fixes_applied = []
        self.errors = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log fix messages."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        if level == "ERROR":
            self.errors.append(message)
    
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
    
    async def create_missing_functions(self):
        """Create the missing functions that are needed for triggers."""
        try:
            self.log("Creating missing functions...")
            
            # Create update_updated_at_column function
            update_function_sql = """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            """
            
            await self.connection.execute(update_function_sql)
            self.log("Created update_updated_at_column function")
            self.fixes_applied.append("update_updated_at_column function")
            
            # Create validate_tenant_access function
            tenant_function_sql = """
            CREATE OR REPLACE FUNCTION validate_tenant_access()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Skip validation if no tenant context is set
                IF current_setting('app.current_tenant_id', true) IS NULL THEN
                    RETURN NEW;
                END IF;
                
                -- Validate tenant access
                IF NEW.tenant_id != (current_setting('app.current_tenant_id', true))::uuid THEN
                    RAISE EXCEPTION 'Access denied: Invalid tenant ID';
                END IF;
                
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            """
            
            await self.connection.execute(tenant_function_sql)
            self.log("Created validate_tenant_access function")
            self.fixes_applied.append("validate_tenant_access function")
            
        except Exception as e:
            self.log(f"Failed to create functions: {str(e)}", "ERROR")
    
    async def create_missing_triggers(self):
        """Create the missing triggers that depend on the functions."""
        try:
            self.log("Creating missing triggers...")
            
            # List of tables that need update triggers
            tables_for_update_triggers = [
                'tenants', 'users', 'user_credentials', 'user_sessions', 'customers',
                'transactions', 'notifications', 'alerts', 'compliance_programs',
                'compliance_requirements', 'tasks', 'screening_tasks', 'enhanced_monitoring',
                'training_modules', 'training_sections', 'training_assessments', 'training_discussions'
            ]
            
            for table in tables_for_update_triggers:
                # Check if table exists
                table_exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if table_exists:
                    trigger_sql = f"""
                    CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON public.{table}
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    """
                    
                    try:
                        await self.connection.execute(trigger_sql)
                        self.log(f"Created update trigger for {table}")
                        self.fixes_applied.append(f"update trigger for {table}")
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            self.log(f"Failed to create trigger for {table}: {str(e)}", "ERROR")
                else:
                    self.log(f"Table {table} does not exist, skipping trigger creation")
            
            # Create tenant validation triggers for key tables
            tenant_tables = ['users', 'customers', 'transactions']
            
            for table in tenant_tables:
                table_exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if table_exists:
                    trigger_sql = f"""
                    CREATE TRIGGER validate_tenant_access_{table}
                    BEFORE INSERT OR UPDATE ON public.{table}
                    FOR EACH ROW EXECUTE FUNCTION validate_tenant_access();
                    """
                    
                    try:
                        await self.connection.execute(trigger_sql)
                        self.log(f"Created tenant validation trigger for {table}")
                        self.fixes_applied.append(f"tenant validation trigger for {table}")
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            self.log(f"Failed to create tenant trigger for {table}: {str(e)}", "ERROR")
            
        except Exception as e:
            self.log(f"Failed to create triggers: {str(e)}", "ERROR")
    
    async def add_missing_constraints(self):
        """Add missing constraints without IF NOT EXISTS syntax."""
        try:
            self.log("Adding missing constraints...")
            
            # List of constraints to add (without IF NOT EXISTS)
            constraints = [
                {
                    'table': 'user_permissions',
                    'name': 'unique_user_permission',
                    'sql': 'ALTER TABLE public.user_permissions ADD CONSTRAINT unique_user_permission UNIQUE (user_id, permission_id);'
                },
                {
                    'table': 'centralized_logs',
                    'name': 'chk_centralized_logs_level',
                    'sql': "ALTER TABLE public.centralized_logs ADD CONSTRAINT chk_centralized_logs_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'));"
                },
                {
                    'table': 'apm_metrics',
                    'name': 'chk_apm_metrics_type',
                    'sql': "ALTER TABLE public.apm_metrics ADD CONSTRAINT chk_apm_metrics_type CHECK (metric_type IN ('counter', 'gauge', 'histogram', 'timer'));"
                },
                {
                    'table': 'dr_objectives',
                    'name': 'chk_dr_objectives_priority',
                    'sql': 'ALTER TABLE public.dr_objectives ADD CONSTRAINT chk_dr_objectives_priority CHECK (priority >= 1 AND priority <= 5);'
                },
                {
                    'table': 'dr_test_results',
                    'name': 'chk_dr_test_results_status',
                    'sql': "ALTER TABLE public.dr_test_results ADD CONSTRAINT chk_dr_test_results_status CHECK (status IN ('running', 'passed', 'failed', 'cancelled'));"
                },
                {
                    'table': 'dr_events',
                    'name': 'chk_dr_events_severity',
                    'sql': "ALTER TABLE public.dr_events ADD CONSTRAINT chk_dr_events_severity CHECK (severity IN ('info', 'warning', 'critical', 'emergency'));"
                },
                {
                    'table': 'dr_backup_metadata',
                    'name': 'chk_dr_backup_metadata_status',
                    'sql': "ALTER TABLE public.dr_backup_metadata ADD CONSTRAINT chk_dr_backup_metadata_status CHECK (backup_status IN ('running', 'completed', 'failed'));"
                },
                {
                    'table': 'configuration_drift',
                    'name': 'chk_configuration_drift_severity',
                    'sql': "ALTER TABLE public.configuration_drift ADD CONSTRAINT chk_configuration_drift_severity CHECK (drift_severity IN ('ok', 'warning', 'error'));"
                },
                {
                    'table': 'configuration_compliance_scans',
                    'name': 'chk_configuration_compliance_scans_status',
                    'sql': "ALTER TABLE public.configuration_compliance_scans ADD CONSTRAINT chk_configuration_compliance_scans_status CHECK (compliance_status IN ('compliant', 'non_compliant', 'not_applicable'));"
                }
            ]
            
            for constraint in constraints:
                # Check if table exists
                table_exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, constraint['table'])
                
                if table_exists:
                    # Check if constraint already exists
                    constraint_exists = await self.connection.fetchval("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE table_schema = 'public' 
                            AND table_name = $1 
                            AND constraint_name = $2
                        )
                    """, constraint['table'], constraint['name'])
                    
                    if not constraint_exists:
                        try:
                            await self.connection.execute(constraint['sql'])
                            self.log(f"Added constraint {constraint['name']} to {constraint['table']}")
                            self.fixes_applied.append(f"constraint {constraint['name']}")
                        except Exception as e:
                            self.log(f"Failed to add constraint {constraint['name']}: {str(e)}", "ERROR")
                    else:
                        self.log(f"Constraint {constraint['name']} already exists on {constraint['table']}")
                else:
                    self.log(f"Table {constraint['table']} does not exist, skipping constraint")
            
        except Exception as e:
            self.log(f"Failed to add constraints: {str(e)}", "ERROR")
    
    async def validate_final_schema(self):
        """Validate the final schema after fixes."""
        try:
            self.log("Validating final schema...")
            
            # Check table count
            table_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            
            # Check function count
            function_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.routines 
                WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
            """)
            
            # Check trigger count
            trigger_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.triggers 
                WHERE trigger_schema = 'public'
            """)
            
            # Check constraint count
            constraint_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE table_schema = 'public'
            """)
            
            # Check index count
            index_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'
            """)
            
            self.log(f"Final validation results:")
            self.log(f"  Tables: {table_count}")
            self.log(f"  Functions: {function_count}")
            self.log(f"  Triggers: {trigger_count}")
            self.log(f"  Constraints: {constraint_count}")
            self.log(f"  Indexes: {index_count}")
            
            return {
                'tables': table_count,
                'functions': function_count,
                'triggers': trigger_count,
                'constraints': constraint_count,
                'indexes': index_count,
                'fixes_applied': len(self.fixes_applied)
            }
            
        except Exception as e:
            self.log(f"Schema validation failed: {str(e)}", "ERROR")
            return {'error': str(e)}
    
    async def close_connection(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.log("Database connection closed")
    
    async def apply_all_fixes(self):
        """Apply all identified fixes."""
        try:
            self.log("Starting schema fixes...")
            
            await self.create_missing_functions()
            await self.create_missing_triggers()
            await self.add_missing_constraints()
            
            validation_results = await self.validate_final_schema()
            
            self.log(f"Schema fixes completed. Applied {len(self.fixes_applied)} fixes.")
            self.log(f"Errors encountered: {len(self.errors)}")
            
            return validation_results
            
        except Exception as e:
            self.log(f"Failed to apply fixes: {str(e)}", "ERROR")
            return {'error': str(e)}

async def main():
    """Main fix function."""
    fixer = SchemaFixer()
    
    try:
        # Connect to Supabase
        if not await fixer.connect_to_supabase():
            print("Failed to connect to Supabase. Exiting.")
            return 1
        
        # Apply fixes
        results = await fixer.apply_all_fixes()
        
        # Generate report
        print("\n" + "="*80)
        print("SCHEMA FIXES REPORT")
        print("="*80)
        print(f"Fixes Applied: {len(fixer.fixes_applied)}")
        print(f"Errors: {len(fixer.errors)}")
        print("\nFixes Applied:")
        for fix in fixer.fixes_applied:
            print(f"  • {fix}")
        
        if fixer.errors:
            print("\nErrors:")
            for error in fixer.errors:
                print(f"  • {error}")
        
        print(f"\nFinal Schema Status:")
        for key, value in results.items():
            if key != 'error':
                print(f"  {key}: {value}")
        
        print("="*80)
        
        return 0 if not fixer.errors else 1
        
    except Exception as e:
        fixer.log(f"Fix process failed with exception: {str(e)}", "ERROR")
        return 1
        
    finally:
        await fixer.close_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
