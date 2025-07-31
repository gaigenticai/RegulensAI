#!/usr/bin/env python3
"""
Emergency Schema Fix - Creates all missing critical tables and columns
"""

import asyncio
import asyncpg
import uuid
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

class EmergencySchemaFixer:
    """Emergency fix for critical schema issues."""
    
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
    
    async def add_missing_column_to_tenants(self):
        """Add the missing domain column to tenants table."""
        try:
            self.log("Adding missing domain column to tenants table...")
            
            # Check if domain column exists
            domain_exists = await self.connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'tenants' AND column_name = 'domain'
                )
            """)
            
            if not domain_exists:
                await self.connection.execute("""
                    ALTER TABLE public.tenants 
                    ADD COLUMN domain text UNIQUE
                """)
                self.log("✓ Added domain column to tenants table")
                self.fixes_applied.append("Added domain column to tenants")
            else:
                self.log("Domain column already exists in tenants table")
            
        except Exception as e:
            self.log(f"Failed to add domain column to tenants: {str(e)}", "ERROR")
    
    async def create_missing_core_tables(self):
        """Create all missing core tables."""
        try:
            self.log("Creating missing core tables...")
            
            # Create risk_assessments table
            await self.create_risk_assessments_table()
            
            # Create regulations table
            await self.create_regulations_table()
            
            # Create roles table
            await self.create_roles_table()
            
            # Create user_roles table
            await self.create_user_roles_table()
            
            # Create ml_models table
            await self.create_ml_models_table()
            
            # Create ml_deployments table
            await self.create_ml_deployments_table()
            
        except Exception as e:
            self.log(f"Failed to create missing core tables: {str(e)}", "ERROR")
    
    async def create_risk_assessments_table(self):
        """Create the risk_assessments table."""
        try:
            self.log("Creating risk_assessments table...")
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.risk_assessments (
                id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
                assessment_type text NOT NULL,
                entity_type text NOT NULL,
                entity_id uuid NOT NULL,
                risk_score numeric(5,2) NOT NULL,
                risk_level text NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
                assessment_date timestamp with time zone NOT NULL DEFAULT now(),
                assessor_id uuid REFERENCES public.users(id),
                methodology text,
                risk_factors jsonb DEFAULT '{}',
                mitigation_measures jsonb DEFAULT '[]',
                review_date timestamp with time zone,
                status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'under_review', 'archived')),
                notes text,
                created_at timestamp with time zone DEFAULT now() NOT NULL,
                updated_at timestamp with time zone DEFAULT now() NOT NULL
            );
            """
            
            await self.connection.execute(create_sql)
            self.log("✓ Created risk_assessments table")
            self.fixes_applied.append("Created risk_assessments table")
            
        except Exception as e:
            self.log(f"Failed to create risk_assessments table: {str(e)}", "ERROR")
    
    async def create_regulations_table(self):
        """Create the regulations table."""
        try:
            self.log("Creating regulations table...")
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.regulations (
                id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                regulation_code text NOT NULL UNIQUE,
                title text NOT NULL,
                description text,
                jurisdiction text NOT NULL,
                regulatory_body text NOT NULL,
                category text NOT NULL,
                effective_date date,
                last_updated date,
                status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'proposed', 'superseded', 'repealed')),
                compliance_deadline date,
                penalty_description text,
                related_regulations text[],
                source_url text,
                document_references jsonb DEFAULT '[]',
                created_at timestamp with time zone DEFAULT now() NOT NULL,
                updated_at timestamp with time zone DEFAULT now() NOT NULL
            );
            """
            
            await self.connection.execute(create_sql)
            self.log("✓ Created regulations table")
            self.fixes_applied.append("Created regulations table")
            
        except Exception as e:
            self.log(f"Failed to create regulations table: {str(e)}", "ERROR")
    
    async def create_roles_table(self):
        """Create the roles table."""
        try:
            self.log("Creating roles table...")
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.roles (
                id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                name text NOT NULL UNIQUE,
                description text,
                permissions jsonb DEFAULT '[]',
                is_system_role boolean DEFAULT false NOT NULL,
                is_active boolean DEFAULT true NOT NULL,
                created_at timestamp with time zone DEFAULT now() NOT NULL,
                updated_at timestamp with time zone DEFAULT now() NOT NULL
            );
            """
            
            await self.connection.execute(create_sql)
            self.log("✓ Created roles table")
            self.fixes_applied.append("Created roles table")
            
            # Insert default roles
            await self.insert_default_roles()
            
        except Exception as e:
            self.log(f"Failed to create roles table: {str(e)}", "ERROR")
    
    async def create_user_roles_table(self):
        """Create the user_roles table."""
        try:
            self.log("Creating user_roles table...")
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.user_roles (
                id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
                role_id uuid NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
                granted_by uuid REFERENCES public.users(id),
                granted_at timestamp with time zone DEFAULT now() NOT NULL,
                expires_at timestamp with time zone,
                is_active boolean DEFAULT true NOT NULL,
                created_at timestamp with time zone DEFAULT now() NOT NULL,
                UNIQUE(user_id, role_id)
            );
            """
            
            await self.connection.execute(create_sql)
            self.log("✓ Created user_roles table")
            self.fixes_applied.append("Created user_roles table")
            
        except Exception as e:
            self.log(f"Failed to create user_roles table: {str(e)}", "ERROR")
    
    async def create_ml_models_table(self):
        """Create the ml_models table."""
        try:
            self.log("Creating ml_models table...")
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.ml_models (
                id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
                name text NOT NULL,
                description text,
                model_type text NOT NULL,
                version text NOT NULL,
                framework text,
                algorithm text,
                training_data_info jsonb DEFAULT '{}',
                hyperparameters jsonb DEFAULT '{}',
                performance_metrics jsonb DEFAULT '{}',
                model_path text,
                model_size_bytes bigint,
                training_started_at timestamp with time zone,
                training_completed_at timestamp with time zone,
                status text NOT NULL DEFAULT 'training' CHECK (status IN ('training', 'trained', 'deployed', 'archived', 'failed')),
                created_by uuid REFERENCES public.users(id),
                created_at timestamp with time zone DEFAULT now() NOT NULL,
                updated_at timestamp with time zone DEFAULT now() NOT NULL,
                UNIQUE(tenant_id, name, version)
            );
            """
            
            await self.connection.execute(create_sql)
            self.log("✓ Created ml_models table")
            self.fixes_applied.append("Created ml_models table")
            
        except Exception as e:
            self.log(f"Failed to create ml_models table: {str(e)}", "ERROR")
    
    async def create_ml_deployments_table(self):
        """Create the ml_deployments table."""
        try:
            self.log("Creating ml_deployments table...")
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.ml_deployments (
                id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
                model_id uuid NOT NULL REFERENCES public.ml_models(id) ON DELETE CASCADE,
                deployment_name text NOT NULL,
                environment text NOT NULL CHECK (environment IN ('development', 'staging', 'production')),
                endpoint_url text,
                deployment_config jsonb DEFAULT '{}',
                resource_allocation jsonb DEFAULT '{}',
                auto_scaling_config jsonb DEFAULT '{}',
                health_check_url text,
                status text NOT NULL DEFAULT 'deploying' CHECK (status IN ('deploying', 'active', 'inactive', 'failed', 'terminated')),
                deployed_at timestamp with time zone,
                last_health_check timestamp with time zone,
                deployment_logs jsonb DEFAULT '[]',
                created_by uuid REFERENCES public.users(id),
                created_at timestamp with time zone DEFAULT now() NOT NULL,
                updated_at timestamp with time zone DEFAULT now() NOT NULL,
                UNIQUE(tenant_id, deployment_name)
            );
            """
            
            await self.connection.execute(create_sql)
            self.log("✓ Created ml_deployments table")
            self.fixes_applied.append("Created ml_deployments table")
            
        except Exception as e:
            self.log(f"Failed to create ml_deployments table: {str(e)}", "ERROR")
    
    async def insert_default_roles(self):
        """Insert default system roles."""
        try:
            self.log("Inserting default roles...")
            
            default_roles = [
                {
                    'name': 'super_admin',
                    'description': 'Super Administrator with full system access',
                    'permissions': ['*'],
                    'is_system_role': True
                },
                {
                    'name': 'admin',
                    'description': 'Administrator with tenant-level access',
                    'permissions': ['tenant.*'],
                    'is_system_role': True
                },
                {
                    'name': 'compliance_officer',
                    'description': 'Compliance Officer with compliance management access',
                    'permissions': ['compliance.*', 'reports.view'],
                    'is_system_role': True
                },
                {
                    'name': 'analyst',
                    'description': 'Analyst with read access to data and reports',
                    'permissions': ['reports.view', 'data.read'],
                    'is_system_role': True
                },
                {
                    'name': 'user',
                    'description': 'Standard user with basic access',
                    'permissions': ['profile.manage'],
                    'is_system_role': True
                }
            ]
            
            for role in default_roles:
                # Check if role already exists
                exists = await self.connection.fetchval("""
                    SELECT EXISTS (SELECT 1 FROM roles WHERE name = $1)
                """, role['name'])
                
                if not exists:
                    await self.connection.execute("""
                        INSERT INTO roles (name, description, permissions, is_system_role)
                        VALUES ($1, $2, $3, $4)
                    """, role['name'], role['description'], role['permissions'], role['is_system_role'])
                    
                    self.log(f"✓ Inserted role: {role['name']}")
            
            self.fixes_applied.append("Inserted default roles")
            
        except Exception as e:
            self.log(f"Failed to insert default roles: {str(e)}", "ERROR")
    
    async def create_missing_triggers(self):
        """Create missing triggers for new tables."""
        try:
            self.log("Creating missing triggers...")
            
            new_tables = ['risk_assessments', 'regulations', 'roles', 'user_roles', 'ml_models', 'ml_deployments']
            
            for table in new_tables:
                # Check if table exists
                table_exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if table_exists:
                    # Check if table has updated_at column
                    has_updated_at = await self.connection.fetchval("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_schema = 'public' AND table_name = $1 AND column_name = 'updated_at'
                        )
                    """, table)
                    
                    if has_updated_at:
                        trigger_sql = f"""
                        CREATE TRIGGER update_{table}_updated_at
                        BEFORE UPDATE ON public.{table}
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                        """
                        
                        try:
                            await self.connection.execute(trigger_sql)
                            self.log(f"✓ Created update trigger for {table}")
                            self.fixes_applied.append(f"Created update trigger for {table}")
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                self.log(f"Failed to create trigger for {table}: {str(e)}", "ERROR")
            
        except Exception as e:
            self.log(f"Failed to create missing triggers: {str(e)}", "ERROR")
    
    async def run_final_validation(self):
        """Run final validation tests."""
        try:
            self.log("Running final validation...")
            
            # Test 1: Check all core tables exist
            core_tables = ['tenants', 'users', 'customers', 'transactions', 'notifications', 
                          'alerts', 'compliance_programs', 'compliance_requirements', 
                          'compliance_tasks', 'risk_assessments', 'regulations', 
                          'regulatory_sources', 'audit_logs', 'user_permissions',
                          'permissions', 'roles', 'user_roles']
            
            missing_tables = []
            for table in core_tables:
                exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if not exists:
                    missing_tables.append(table)
            
            if missing_tables:
                self.log(f"Still missing core tables: {missing_tables}", "ERROR")
            else:
                self.log("✓ All core tables exist")
            
            # Test 2: Check tenants table has domain column
            domain_exists = await self.connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'tenants' AND column_name = 'domain'
                )
            """)
            
            if domain_exists:
                self.log("✓ Tenants table has domain column")
            else:
                self.log("✗ Tenants table still missing domain column", "ERROR")
            
            # Test 3: Test CRUD operations with proper UUID
            test_tenant_id = str(uuid.uuid4())
            
            try:
                await self.connection.execute("""
                    INSERT INTO tenants (id, name, domain) VALUES ($1, $2, $3)
                """, test_tenant_id, 'Test Tenant', 'test.example.com')
                
                tenant = await self.connection.fetchrow("SELECT * FROM tenants WHERE id = $1", test_tenant_id)
                
                if tenant:
                    self.log("✓ CRUD operations working correctly")
                    
                    # Clean up
                    await self.connection.execute("DELETE FROM tenants WHERE id = $1", test_tenant_id)
                else:
                    self.log("✗ CRUD operations failed", "ERROR")
                    
            except Exception as e:
                self.log(f"✗ CRUD test failed: {str(e)}", "ERROR")
            
            return len(missing_tables) == 0 and domain_exists
            
        except Exception as e:
            self.log(f"Final validation failed: {str(e)}", "ERROR")
            return False
    
    async def close_connection(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.log("Database connection closed")

async def main():
    """Main emergency fix function."""
    fixer = EmergencySchemaFixer()
    
    try:
        # Connect to Supabase
        if not await fixer.connect_to_supabase():
            print("CRITICAL: Failed to connect to Supabase. Exiting.")
            return 1
        
        # Apply emergency fixes
        await fixer.add_missing_column_to_tenants()
        await fixer.create_missing_core_tables()
        await fixer.create_missing_triggers()
        
        # Run final validation
        validation_passed = await fixer.run_final_validation()
        
        # Generate report
        print("\n" + "="*80)
        print("EMERGENCY SCHEMA FIX REPORT")
        print("="*80)
        print(f"Fixes Applied: {len(fixer.fixes_applied)}")
        print(f"Errors: {len(fixer.errors)}")
        
        if fixer.fixes_applied:
            print("\nFixes Applied:")
            for fix in fixer.fixes_applied:
                print(f"  ✓ {fix}")
        
        if fixer.errors:
            print("\nErrors:")
            for error in fixer.errors:
                print(f"  ✗ {error}")
        
        if validation_passed:
            print("\n✅ EMERGENCY FIX STATUS: SUCCESS")
            print("All critical schema issues have been resolved!")
            return 0
        else:
            print("\n🚨 EMERGENCY FIX STATUS: ISSUES REMAIN")
            print("Some critical issues still need to be resolved.")
            return 1
        
    except Exception as e:
        fixer.log(f"Emergency fix failed with exception: {str(e)}", "ERROR")
        return 1
        
    finally:
        await fixer.close_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
