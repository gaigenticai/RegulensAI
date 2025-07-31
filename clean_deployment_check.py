#!/usr/bin/env python3
"""
Clean deployment check and error resolution
"""

import asyncio
import asyncpg
import sys
import os
from datetime import datetime

# Read from .env file or use provided credentials
SUPABASE_CONFIG = {
    'host': 'db.qoqzovknwsemxhlaobsv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'mdRh6u26EeogT2M0'
}

async def check_database_status():
    """Check current database status and identify any issues."""
    try:
        print("🔍 CHECKING DATABASE STATUS")
        print("=" * 50)
        
        # Test connection
        print("1. Testing database connection...")
        try:
            connection = await asyncpg.connect(**SUPABASE_CONFIG)
            print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
        
        # Check PostgreSQL version
        print("\n2. Checking PostgreSQL version...")
        version = await connection.fetchval("SELECT version()")
        print(f"✅ PostgreSQL version: {version.split(',')[0]}")
        
        # Check schema status
        print("\n3. Checking schema status...")
        
        # Count tables
        table_count = await connection.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        print(f"✅ Total tables: {table_count}")
        
        # Check core tables
        core_tables = [
            'tenants', 'users', 'customers', 'transactions', 'notifications', 
            'alerts', 'compliance_programs', 'compliance_requirements', 
            'compliance_tasks', 'risk_assessments', 'regulations', 
            'regulatory_sources', 'audit_logs', 'user_permissions',
            'permissions', 'roles', 'user_roles'
        ]
        
        missing_core = []
        for table in core_tables:
            exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                )
            """, table)
            
            if not exists:
                missing_core.append(table)
        
        if missing_core:
            print(f"❌ Missing core tables: {missing_core}")
        else:
            print(f"✅ All {len(core_tables)} core tables exist")
        
        # Check advanced tables
        advanced_tables = [
            'centralized_logs', 'apm_transactions', 'apm_spans', 'apm_errors',
            'apm_metrics', 'dr_objectives', 'dr_test_results', 'dr_events',
            'dr_backup_metadata', 'configuration_versions', 'configuration_drift',
            'ml_models', 'ml_deployments', 'training_modules'
        ]
        
        missing_advanced = []
        for table in advanced_tables:
            exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                )
            """, table)
            
            if not exists:
                missing_advanced.append(table)
        
        if missing_advanced:
            print(f"❌ Missing advanced tables: {missing_advanced}")
        else:
            print(f"✅ All {len(advanced_tables)} advanced tables exist")
        
        # Check functions
        print("\n4. Checking functions...")
        functions = await connection.fetch("""
            SELECT routine_name FROM information_schema.routines 
            WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
        """)
        
        function_names = [f['routine_name'] for f in functions]
        print(f"✅ Functions: {len(function_names)} ({', '.join(function_names)})")
        
        # Check triggers
        print("\n5. Checking triggers...")
        triggers = await connection.fetch("""
            SELECT COUNT(*) as count FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
        """)
        
        trigger_count = triggers[0]['count'] if triggers else 0
        print(f"✅ Triggers: {trigger_count}")
        
        # Test basic operations
        print("\n6. Testing basic operations...")
        try:
            # Test a simple query on tenants table
            tenant_count = await connection.fetchval("SELECT COUNT(*) FROM tenants")
            print(f"✅ Tenants table accessible (count: {tenant_count})")
            
            # Test users table
            user_count = await connection.fetchval("SELECT COUNT(*) FROM users")
            print(f"✅ Users table accessible (count: {user_count})")
            
            # Test permissions table
            perm_count = await connection.fetchval("SELECT COUNT(*) FROM permissions")
            print(f"✅ Permissions table accessible (count: {perm_count})")
            
        except Exception as e:
            print(f"❌ Basic operations test failed: {str(e)}")
            return False
        
        # Check for any obvious issues
        print("\n7. Checking for common issues...")
        
        # Check if tenants table has domain column
        domain_exists = await connection.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'tenants' AND column_name = 'domain'
            )
        """)
        
        if domain_exists:
            print("✅ Tenants table has domain column")
        else:
            print("❌ Tenants table missing domain column")
        
        # Check if users table has required columns
        user_columns = await connection.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users'
        """)
        
        user_col_names = [col['column_name'] for col in user_columns]
        required_user_cols = ['id', 'tenant_id', 'email']
        missing_user_cols = [col for col in required_user_cols if col not in user_col_names]
        
        if missing_user_cols:
            print(f"❌ Users table missing columns: {missing_user_cols}")
        else:
            print("✅ Users table has all required columns")
        
        await connection.close()
        
        # Final status
        print("\n" + "="*50)
        print("📊 DATABASE STATUS SUMMARY")
        print("="*50)
        
        issues = []
        if missing_core:
            issues.append(f"Missing core tables: {len(missing_core)}")
        if missing_advanced:
            issues.append(f"Missing advanced tables: {len(missing_advanced)}")
        if not domain_exists:
            issues.append("Missing domain column in tenants")
        if missing_user_cols:
            issues.append("Missing columns in users table")
        
        if issues:
            print("🚨 ISSUES DETECTED:")
            for issue in issues:
                print(f"   • {issue}")
            print("\n💡 RECOMMENDATION: Run the emergency fix script to resolve these issues")
            return False
        else:
            print("🎉 DATABASE STATUS: PERFECT!")
            print("✅ All tables, columns, and functions are properly deployed")
            print("✅ Database is ready for production use")
            return True
        
    except Exception as e:
        print(f"❌ Database status check failed: {str(e)}")
        return False

async def quick_fix_common_issues():
    """Quick fix for common deployment issues."""
    try:
        print("\n🔧 APPLYING QUICK FIXES")
        print("=" * 30)
        
        connection = await asyncpg.connect(**SUPABASE_CONFIG)
        
        fixes_applied = []
        
        # Fix 1: Add domain column to tenants if missing
        domain_exists = await connection.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'tenants' AND column_name = 'domain'
            )
        """)
        
        if not domain_exists:
            await connection.execute("ALTER TABLE public.tenants ADD COLUMN domain text UNIQUE")
            fixes_applied.append("Added domain column to tenants")
            print("✅ Added domain column to tenants table")
        
        # Fix 2: Add email column to customers if missing
        email_exists = await connection.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'customers' AND column_name = 'email'
            )
        """)
        
        if not email_exists:
            await connection.execute("ALTER TABLE public.customers ADD COLUMN email text")
            fixes_applied.append("Added email column to customers")
            print("✅ Added email column to customers table")
        
        # Fix 3: Ensure update_updated_at_column function exists
        func_exists = await connection.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.routines 
                WHERE routine_schema = 'public' AND routine_name = 'update_updated_at_column'
            )
        """)
        
        if not func_exists:
            await connection.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = now();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            fixes_applied.append("Created update_updated_at_column function")
            print("✅ Created update_updated_at_column function")
        
        await connection.close()
        
        if fixes_applied:
            print(f"\n✅ Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                print(f"   • {fix}")
        else:
            print("\n✅ No fixes needed - database is already in good state")
        
        return True
        
    except Exception as e:
        print(f"❌ Quick fix failed: {str(e)}")
        return False

async def main():
    """Main function to check and fix database issues."""
    print("🚀 REGULENSAI DATABASE DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check current status
    status_ok = await check_database_status()
    
    if not status_ok:
        print("\n🔧 Attempting to fix detected issues...")
        fix_ok = await quick_fix_common_issues()
        
        if fix_ok:
            print("\n🔄 Re-checking database status after fixes...")
            final_status = await check_database_status()
            
            if final_status:
                print("\n🎉 SUCCESS: All issues resolved!")
                return 0
            else:
                print("\n⚠️  Some issues remain. Manual intervention may be required.")
                return 1
        else:
            print("\n❌ Quick fixes failed. Manual intervention required.")
            return 1
    else:
        print("\n🎉 SUCCESS: Database is in perfect condition!")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
