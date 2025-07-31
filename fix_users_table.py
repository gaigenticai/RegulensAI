#!/usr/bin/env python3
"""
Fix missing columns in users table
"""

import asyncio
import asyncpg
import sys

# Supabase connection configuration
SUPABASE_CONFIG = {
    'host': 'db.qoqzovknwsemxhlaobsv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'mdRh6u26EeogT2M0'
}

async def fix_users_table():
    """Fix missing columns in users table."""
    try:
        print("Connecting to Supabase...")
        connection = await asyncpg.connect(**SUPABASE_CONFIG)
        
        # Check current columns in users table
        columns = await connection.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        current_columns = [col['column_name'] for col in columns]
        print(f"Current users table columns: {current_columns}")
        
        # Add missing columns
        if 'first_name' not in current_columns:
            await connection.execute("""
                ALTER TABLE public.users 
                ADD COLUMN first_name text
            """)
            print("✓ Added first_name column")
        
        if 'last_name' not in current_columns:
            await connection.execute("""
                ALTER TABLE public.users 
                ADD COLUMN last_name text
            """)
            print("✓ Added last_name column")
        
        # Verify the fix
        updated_columns = await connection.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        updated_column_names = [col['column_name'] for col in updated_columns]
        print(f"Updated users table columns: {updated_column_names}")
        
        # Test CRUD operation
        import uuid
        test_user_id = str(uuid.uuid4())
        test_tenant_id = str(uuid.uuid4())
        
        # First create a test tenant
        await connection.execute("""
            INSERT INTO tenants (id, name, domain, industry, country_code, subscription_tier, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, test_tenant_id, 'Test Tenant', 'test.example.com', 'Technology', 'US', 'enterprise', True)
        
        # Now create a test user
        await connection.execute("""
            INSERT INTO users (id, tenant_id, email, first_name, last_name, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, test_user_id, test_tenant_id, 'test@example.com', 'Test', 'User', True)
        
        print("✓ CRUD test successful")
        
        # Clean up test data
        await connection.execute("DELETE FROM users WHERE id = $1", test_user_id)
        await connection.execute("DELETE FROM tenants WHERE id = $1", test_tenant_id)
        print("✓ Test data cleaned up")
        
        await connection.close()
        print("✅ Users table fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix users table: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_users_table())
    sys.exit(0 if success else 1)
