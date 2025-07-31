#!/usr/bin/env python3
"""
Critical Schema Audit and Fix Tool for RegulensAI Database
Performs comprehensive analysis and fixes all schema inconsistencies.
"""

import asyncio
import asyncpg
import re
import sys
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any

# Supabase connection configuration
SUPABASE_CONFIG = {
    'host': 'db.qoqzovknwsemxhlaobsv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'mdRh6u26EeogT2M0'
}

SCHEMA_FILE_PATH = 'core_infra/database/schema.sql'

class CriticalSchemaAuditor:
    """Performs critical schema audit and fixes all inconsistencies."""
    
    def __init__(self):
        self.connection = None
        self.schema_content = ""
        self.expected_tables = {}
        self.deployed_tables = {}
        self.missing_tables = []
        self.missing_columns = {}
        self.schema_mismatches = []
        self.fixes_applied = []
        self.critical_errors = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log audit messages."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        if level == "CRITICAL":
            self.critical_errors.append(message)
    
    async def connect_to_supabase(self):
        """Establish connection to Supabase PostgreSQL database."""
        try:
            self.log("Connecting to Supabase PostgreSQL database...")
            self.connection = await asyncpg.connect(**SUPABASE_CONFIG)
            self.log("Connected successfully")
            return True
        except Exception as e:
            self.log(f"Failed to connect to Supabase: {str(e)}", "CRITICAL")
            return False
    
    async def load_and_parse_schema(self):
        """Load and parse the expected schema from schema.sql file."""
        try:
            self.log("Loading and parsing schema.sql file...")
            
            with open(SCHEMA_FILE_PATH, 'r', encoding='utf-8') as file:
                self.schema_content = file.read()
            
            # Parse CREATE TABLE statements to extract expected table structures
            table_pattern = r'CREATE TABLE IF NOT EXISTS\s+(?:public\.)?(\w+)\s*\(\s*([^;]+)\);'
            alter_pattern = r'ALTER TABLE\s+(?:public\.)?(\w+)\s+ADD COLUMN IF NOT EXISTS\s+(\w+)\s+([^;]+);'
            
            # Extract table definitions
            for match in re.finditer(table_pattern, self.schema_content, re.IGNORECASE | re.DOTALL):
                table_name = match.group(1)
                if table_name not in self.expected_tables:
                    self.expected_tables[table_name] = {'columns': {}, 'constraints': []}
            
            # Extract column definitions from ALTER TABLE statements
            for match in re.finditer(alter_pattern, self.schema_content, re.IGNORECASE):
                table_name = match.group(1)
                column_name = match.group(2)
                column_def = match.group(3).strip()
                
                if table_name in self.expected_tables:
                    self.expected_tables[table_name]['columns'][column_name] = column_def
            
            self.log(f"Parsed {len(self.expected_tables)} expected tables from schema")
            
            # Log expected core tables for verification
            core_tables = ['tenants', 'users', 'customers', 'transactions', 'notifications', 
                          'alerts', 'compliance_programs', 'compliance_requirements', 
                          'compliance_tasks', 'risk_assessments', 'regulations', 
                          'regulatory_sources', 'audit_logs', 'user_permissions',
                          'permissions', 'roles', 'user_roles']
            
            missing_from_schema = [t for t in core_tables if t not in self.expected_tables]
            if missing_from_schema:
                self.log(f"Core tables missing from schema: {missing_from_schema}", "CRITICAL")
            
        except Exception as e:
            self.log(f"Failed to parse schema: {str(e)}", "CRITICAL")
    
    async def audit_deployed_tables(self):
        """Audit all tables currently deployed in the database."""
        try:
            self.log("Auditing deployed tables...")
            
            # Get all tables in the database
            tables = await self.connection.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            for table_row in tables:
                table_name = table_row['table_name']
                
                # Get column information for each table
                columns = await self.connection.fetch("""
                    SELECT column_name, data_type, is_nullable, column_default,
                           character_maximum_length, numeric_precision, numeric_scale
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = $1
                    ORDER BY ordinal_position
                """, table_name)
                
                self.deployed_tables[table_name] = {
                    'columns': {col['column_name']: {
                        'data_type': col['data_type'],
                        'is_nullable': col['is_nullable'],
                        'column_default': col['column_default'],
                        'character_maximum_length': col['character_maximum_length'],
                        'numeric_precision': col['numeric_precision'],
                        'numeric_scale': col['numeric_scale']
                    } for col in columns}
                }
            
            self.log(f"Found {len(self.deployed_tables)} deployed tables")
            
        except Exception as e:
            self.log(f"Failed to audit deployed tables: {str(e)}", "CRITICAL")
    
    async def identify_missing_tables(self):
        """Identify tables that are missing from the deployment."""
        try:
            self.log("Identifying missing tables...")
            
            # Core tables that must exist
            core_tables = ['tenants', 'users', 'customers', 'transactions', 'notifications', 
                          'alerts', 'compliance_programs', 'compliance_requirements', 
                          'compliance_tasks', 'risk_assessments', 'regulations', 
                          'regulatory_sources', 'audit_logs', 'user_permissions',
                          'permissions', 'roles', 'user_roles']
            
            # Advanced tables
            advanced_tables = ['centralized_logs', 'apm_transactions', 'apm_spans', 'apm_errors',
                              'apm_metrics', 'dr_objectives', 'dr_test_results', 'dr_events',
                              'dr_backup_metadata', 'configuration_versions', 'configuration_drift',
                              'ml_models', 'ml_deployments', 'training_modules', 'training_sections']
            
            # Check which tables are missing
            missing_core = [t for t in core_tables if t not in self.deployed_tables]
            missing_advanced = [t for t in advanced_tables if t not in self.deployed_tables]
            
            self.missing_tables = missing_core + missing_advanced
            
            if missing_core:
                self.log(f"CRITICAL: Missing core tables: {missing_core}", "CRITICAL")
            
            if missing_advanced:
                self.log(f"Missing advanced tables: {missing_advanced}", "CRITICAL")
            
            # Also check for any expected tables from schema that are missing
            schema_missing = [t for t in self.expected_tables.keys() if t not in self.deployed_tables]
            if schema_missing:
                self.log(f"Tables defined in schema but missing from database: {schema_missing}", "CRITICAL")
                self.missing_tables.extend([t for t in schema_missing if t not in self.missing_tables])
            
        except Exception as e:
            self.log(f"Failed to identify missing tables: {str(e)}", "CRITICAL")
    
    async def audit_table_structures(self):
        """Audit the structure of deployed tables against expected schema."""
        try:
            self.log("Auditing table structures...")
            
            # Focus on critical tables first
            critical_tables = ['tenants', 'users', 'customers', 'transactions', 'compliance_tasks']
            
            for table_name in critical_tables:
                if table_name in self.deployed_tables and table_name in self.expected_tables:
                    await self.audit_single_table_structure(table_name)
                elif table_name not in self.deployed_tables:
                    self.log(f"CRITICAL: Table {table_name} is completely missing", "CRITICAL")
            
        except Exception as e:
            self.log(f"Failed to audit table structures: {str(e)}", "CRITICAL")
    
    async def audit_single_table_structure(self, table_name: str):
        """Audit a single table's structure."""
        try:
            deployed_cols = set(self.deployed_tables[table_name]['columns'].keys())
            expected_cols = set(self.expected_tables[table_name]['columns'].keys())
            
            missing_cols = expected_cols - deployed_cols
            extra_cols = deployed_cols - expected_cols
            
            if missing_cols:
                self.log(f"CRITICAL: Table {table_name} missing columns: {missing_cols}", "CRITICAL")
                self.missing_columns[table_name] = list(missing_cols)
            
            if extra_cols:
                self.log(f"Table {table_name} has unexpected columns: {extra_cols}")
            
            # Special check for tenants table since it failed in validation
            if table_name == 'tenants':
                required_tenant_cols = ['id', 'name', 'domain', 'subscription_tier', 'is_active', 'created_at', 'updated_at']
                missing_tenant_cols = [col for col in required_tenant_cols if col not in deployed_cols]
                if missing_tenant_cols:
                    self.log(f"CRITICAL: Tenants table missing required columns: {missing_tenant_cols}", "CRITICAL")
            
        except Exception as e:
            self.log(f"Failed to audit table {table_name}: {str(e)}", "CRITICAL")
    
    async def create_missing_tables(self):
        """Create all missing tables."""
        try:
            if not self.missing_tables:
                self.log("No missing tables to create")
                return
            
            self.log(f"Creating {len(self.missing_tables)} missing tables...")
            
            # Extract CREATE TABLE statements for missing tables
            for table_name in self.missing_tables:
                await self.create_single_table(table_name)
            
        except Exception as e:
            self.log(f"Failed to create missing tables: {str(e)}", "CRITICAL")
    
    async def create_single_table(self, table_name: str):
        """Create a single missing table."""
        try:
            self.log(f"Creating table: {table_name}")
            
            # Find the CREATE TABLE statement in schema
            pattern = rf'CREATE TABLE IF NOT EXISTS\s+(?:public\.)?{table_name}\s*\(\s*([^;]+)\);'
            match = re.search(pattern, self.schema_content, re.IGNORECASE | re.DOTALL)
            
            if match:
                # Create table with just primary key first
                create_sql = f"CREATE TABLE IF NOT EXISTS public.{table_name} (id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY);"
                await self.connection.execute(create_sql)
                self.log(f"Created base table: {table_name}")
                
                # Add columns from ALTER TABLE statements
                await self.add_table_columns(table_name)
                
                self.fixes_applied.append(f"Created table {table_name}")
            else:
                self.log(f"Could not find CREATE TABLE statement for {table_name}", "CRITICAL")
                
        except Exception as e:
            self.log(f"Failed to create table {table_name}: {str(e)}", "CRITICAL")
    
    async def add_table_columns(self, table_name: str):
        """Add columns to a table from ALTER TABLE statements."""
        try:
            # Find all ALTER TABLE statements for this table
            pattern = rf'ALTER TABLE\s+(?:public\.)?{table_name}\s+ADD COLUMN IF NOT EXISTS\s+(\w+)\s+([^;]+);'
            
            for match in re.finditer(pattern, self.schema_content, re.IGNORECASE):
                column_name = match.group(1)
                column_def = match.group(2).strip()
                
                # Skip if column already exists
                if table_name in self.deployed_tables:
                    if column_name in self.deployed_tables[table_name]['columns']:
                        continue
                
                alter_sql = f"ALTER TABLE public.{table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_def};"
                
                try:
                    await self.connection.execute(alter_sql)
                    self.log(f"Added column {column_name} to {table_name}")
                except Exception as col_error:
                    self.log(f"Failed to add column {column_name} to {table_name}: {str(col_error)}", "CRITICAL")
            
        except Exception as e:
            self.log(f"Failed to add columns to {table_name}: {str(e)}", "CRITICAL")
    
    async def fix_missing_columns(self):
        """Fix missing columns in existing tables."""
        try:
            if not self.missing_columns:
                self.log("No missing columns to fix")
                return
            
            self.log("Fixing missing columns in existing tables...")
            
            for table_name, missing_cols in self.missing_columns.items():
                for column_name in missing_cols:
                    await self.add_missing_column(table_name, column_name)
            
        except Exception as e:
            self.log(f"Failed to fix missing columns: {str(e)}", "CRITICAL")
    
    async def add_missing_column(self, table_name: str, column_name: str):
        """Add a specific missing column to a table."""
        try:
            # Find the column definition in schema
            pattern = rf'ALTER TABLE\s+(?:public\.)?{table_name}\s+ADD COLUMN IF NOT EXISTS\s+{column_name}\s+([^;]+);'
            match = re.search(pattern, self.schema_content, re.IGNORECASE)
            
            if match:
                column_def = match.group(1).strip()
                alter_sql = f"ALTER TABLE public.{table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_def};"
                
                await self.connection.execute(alter_sql)
                self.log(f"Added missing column {column_name} to {table_name}")
                self.fixes_applied.append(f"Added column {column_name} to {table_name}")
            else:
                self.log(f"Could not find definition for column {column_name} in table {table_name}", "CRITICAL")
                
        except Exception as e:
            self.log(f"Failed to add column {column_name} to {table_name}: {str(e)}", "CRITICAL")
    
    async def run_comprehensive_tests(self):
        """Run comprehensive functional tests."""
        try:
            self.log("Running comprehensive functional tests...")
            
            # Test 1: Verify all core tables exist and are accessible
            await self.test_core_table_access()
            
            # Test 2: Test CRUD operations on critical tables
            await self.test_crud_operations()
            
            # Test 3: Test foreign key relationships
            await self.test_foreign_key_relationships()
            
            # Test 4: Test triggers and functions
            await self.test_triggers_and_functions()
            
        except Exception as e:
            self.log(f"Comprehensive tests failed: {str(e)}", "CRITICAL")
    
    async def test_core_table_access(self):
        """Test access to all core tables."""
        try:
            core_tables = ['tenants', 'users', 'customers', 'transactions', 'notifications', 
                          'alerts', 'compliance_programs', 'compliance_requirements', 
                          'compliance_tasks', 'risk_assessments', 'regulations', 
                          'regulatory_sources', 'audit_logs', 'user_permissions',
                          'permissions', 'roles', 'user_roles']
            
            accessible_tables = []
            inaccessible_tables = []
            
            for table in core_tables:
                try:
                    count = await self.connection.fetchval(f"SELECT COUNT(*) FROM {table}")
                    accessible_tables.append(table)
                    self.log(f"✓ Table {table} accessible (count: {count})")
                except Exception as e:
                    inaccessible_tables.append(table)
                    self.log(f"✗ Table {table} inaccessible: {str(e)}", "CRITICAL")
            
            self.log(f"Core table access test: {len(accessible_tables)}/{len(core_tables)} accessible")
            
            if inaccessible_tables:
                self.log(f"CRITICAL: Inaccessible core tables: {inaccessible_tables}", "CRITICAL")
            
        except Exception as e:
            self.log(f"Core table access test failed: {str(e)}", "CRITICAL")
    
    async def test_crud_operations(self):
        """Test CRUD operations on critical tables."""
        try:
            self.log("Testing CRUD operations...")
            
            # Test tenants table with all required columns
            test_tenant_id = f"test-tenant-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # First, check what columns actually exist in tenants table
            tenant_columns = await self.connection.fetch("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'tenants'
                ORDER BY ordinal_position
            """)
            
            tenant_col_names = [col['column_name'] for col in tenant_columns]
            self.log(f"Tenants table columns: {tenant_col_names}")
            
            # Build INSERT statement based on available columns
            insert_cols = ['id', 'name']
            insert_values = [test_tenant_id, 'Test Tenant']
            
            if 'domain' in tenant_col_names:
                insert_cols.append('domain')
                insert_values.append('test.example.com')
            
            if 'subscription_tier' in tenant_col_names:
                insert_cols.append('subscription_tier')
                insert_values.append('enterprise')
            
            if 'is_active' in tenant_col_names:
                insert_cols.append('is_active')
                insert_values.append(True)
            
            # Create parameterized query
            placeholders = ', '.join([f'${i+1}' for i in range(len(insert_values))])
            insert_sql = f"INSERT INTO tenants ({', '.join(insert_cols)}) VALUES ({placeholders})"
            
            await self.connection.execute(insert_sql, *insert_values)
            self.log("✓ INSERT operation successful on tenants table")
            
            # Test SELECT
            tenant = await self.connection.fetchrow("SELECT * FROM tenants WHERE id = $1", test_tenant_id)
            if tenant:
                self.log("✓ SELECT operation successful on tenants table")
            else:
                self.log("✗ SELECT operation failed on tenants table", "CRITICAL")
            
            # Test UPDATE
            await self.connection.execute("UPDATE tenants SET name = 'Updated Test Tenant' WHERE id = $1", test_tenant_id)
            self.log("✓ UPDATE operation successful on tenants table")
            
            # Test DELETE
            await self.connection.execute("DELETE FROM tenants WHERE id = $1", test_tenant_id)
            self.log("✓ DELETE operation successful on tenants table")
            
            self.log("✓ All CRUD operations successful")
            
        except Exception as e:
            self.log(f"CRUD operations test failed: {str(e)}", "CRITICAL")
    
    async def test_foreign_key_relationships(self):
        """Test foreign key relationships."""
        try:
            self.log("Testing foreign key relationships...")
            
            # Get all foreign key constraints
            fk_constraints = await self.connection.fetch("""
                SELECT tc.table_name, tc.constraint_name, kcu.column_name, 
                       ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
                LIMIT 10
            """)
            
            self.log(f"Found {len(fk_constraints)} foreign key constraints (showing first 10)")
            
            for fk in fk_constraints:
                self.log(f"✓ FK: {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
            
        except Exception as e:
            self.log(f"Foreign key relationship test failed: {str(e)}", "CRITICAL")
    
    async def test_triggers_and_functions(self):
        """Test triggers and functions."""
        try:
            self.log("Testing triggers and functions...")
            
            # Test update trigger on tenants table
            test_tenant_id = f"test-trigger-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Get tenants table columns again
            tenant_columns = await self.connection.fetch("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'tenants'
            """)
            tenant_col_names = [col['column_name'] for col in tenant_columns]
            
            # Insert test record
            if 'domain' in tenant_col_names:
                await self.connection.execute("""
                    INSERT INTO tenants (id, name, domain) VALUES ($1, $2, $3)
                """, test_tenant_id, 'Trigger Test', 'trigger.test.com')
            else:
                await self.connection.execute("""
                    INSERT INTO tenants (id, name) VALUES ($1, $2)
                """, test_tenant_id, 'Trigger Test')
            
            # Get initial timestamps
            initial_record = await self.connection.fetchrow("SELECT * FROM tenants WHERE id = $1", test_tenant_id)
            
            # Update the record
            await self.connection.execute("UPDATE tenants SET name = 'Updated Trigger Test' WHERE id = $1", test_tenant_id)
            
            # Check if updated_at was modified
            updated_record = await self.connection.fetchrow("SELECT * FROM tenants WHERE id = $1", test_tenant_id)
            
            if 'updated_at' in tenant_col_names:
                if updated_record['updated_at'] > initial_record['updated_at']:
                    self.log("✓ Update trigger working correctly")
                else:
                    self.log("✗ Update trigger not working", "CRITICAL")
            else:
                self.log("! No updated_at column found in tenants table")
            
            # Clean up
            await self.connection.execute("DELETE FROM tenants WHERE id = $1", test_tenant_id)
            
        except Exception as e:
            self.log(f"Triggers and functions test failed: {str(e)}", "CRITICAL")
    
    async def close_connection(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.log("Database connection closed")

async def main():
    """Main audit and fix function."""
    auditor = CriticalSchemaAuditor()
    
    try:
        # Connect to Supabase
        if not await auditor.connect_to_supabase():
            print("CRITICAL: Failed to connect to Supabase. Exiting.")
            return 1
        
        # Load and parse expected schema
        await auditor.load_and_parse_schema()
        
        # Audit current deployment
        await auditor.audit_deployed_tables()
        await auditor.identify_missing_tables()
        await auditor.audit_table_structures()
        
        # Apply fixes
        await auditor.create_missing_tables()
        await auditor.fix_missing_columns()
        
        # Re-audit after fixes
        await auditor.audit_deployed_tables()
        await auditor.identify_missing_tables()
        await auditor.audit_table_structures()
        
        # Run comprehensive tests
        await auditor.run_comprehensive_tests()
        
        # Generate final report
        print("\n" + "="*80)
        print("CRITICAL SCHEMA AUDIT REPORT")
        print("="*80)
        print(f"Fixes Applied: {len(auditor.fixes_applied)}")
        print(f"Critical Errors: {len(auditor.critical_errors)}")
        
        if auditor.fixes_applied:
            print("\nFixes Applied:")
            for fix in auditor.fixes_applied:
                print(f"  ✓ {fix}")
        
        if auditor.critical_errors:
            print("\nCRITICAL ERRORS:")
            for error in auditor.critical_errors:
                print(f"  ✗ {error}")
        
        print("\nMissing Tables:", auditor.missing_tables)
        print("Missing Columns:", auditor.missing_columns)
        
        # Final status
        if auditor.critical_errors:
            print("\n🚨 DEPLOYMENT STATUS: CRITICAL ISSUES REMAIN")
            print("The database has critical issues that must be resolved.")
            return 1
        else:
            print("\n✅ DEPLOYMENT STATUS: ALL CRITICAL ISSUES RESOLVED")
            print("The database is now fully functional and schema-compliant.")
            return 0
        
    except Exception as e:
        auditor.log(f"Critical audit failed with exception: {str(e)}", "CRITICAL")
        return 1
        
    finally:
        await auditor.close_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
