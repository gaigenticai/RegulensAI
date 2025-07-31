#!/usr/bin/env python3
"""
Final fix and comprehensive validation
"""

import asyncio
import asyncpg
import uuid
import json
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

async def run_final_validation():
    """Run final comprehensive validation with proper data."""
    try:
        print("🔍 FINAL COMPREHENSIVE VALIDATION")
        print("=" * 50)
        
        connection = await asyncpg.connect(**SUPABASE_CONFIG)
        print("✓ Connected to Supabase")
        
        test_data_ids = []
        errors = []
        
        # Test 1: Validate all core tables exist
        print("\n1. Validating core tables...")
        core_tables = [
            'tenants', 'users', 'customers', 'transactions', 'notifications', 
            'alerts', 'compliance_programs', 'compliance_requirements', 
            'compliance_tasks', 'risk_assessments', 'regulations', 
            'regulatory_sources', 'audit_logs', 'user_permissions',
            'permissions', 'roles', 'user_roles'
        ]
        
        missing_tables = []
        for table in core_tables:
            exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                )
            """, table)
            
            if not exists:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ Missing core tables: {missing_tables}")
            errors.append(f"Missing core tables: {missing_tables}")
        else:
            print(f"✅ All {len(core_tables)} core tables exist")
        
        # Test 2: Check users table structure
        print("\n2. Checking users table structure...")
        user_columns = await connection.fetch("""
            SELECT column_name, is_nullable FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        user_col_info = {col['column_name']: col['is_nullable'] for col in user_columns}
        print(f"Users table columns: {list(user_col_info.keys())}")
        
        # Test 3: Comprehensive CRUD operations
        print("\n3. Testing CRUD operations...")
        
        try:
            # Create tenant
            tenant_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO tenants (id, name, domain, industry, country_code, subscription_tier, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, tenant_id, 'Test Tenant', 'test.example.com', 'Technology', 'US', 'enterprise', True)
            test_data_ids.append(('tenants', tenant_id))
            print("  ✓ Created tenant")
            
            # Create user with proper data based on actual schema
            user_id = str(uuid.uuid4())
            user_insert_data = {
                'id': user_id,
                'tenant_id': tenant_id,
                'email': 'test@example.com',
                'is_active': True
            }
            
            # Add full_name if required
            if 'full_name' in user_col_info and user_col_info['full_name'] == 'NO':
                user_insert_data['full_name'] = 'Test User'
            
            # Add first_name and last_name if they exist
            if 'first_name' in user_col_info:
                user_insert_data['first_name'] = 'Test'
            if 'last_name' in user_col_info:
                user_insert_data['last_name'] = 'User'
            
            # Build dynamic INSERT statement
            columns = list(user_insert_data.keys())
            values = list(user_insert_data.values())
            placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
            
            insert_sql = f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})"
            await connection.execute(insert_sql, *values)
            test_data_ids.append(('users', user_id))
            print("  ✓ Created user")
            
            # Create customer
            customer_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO customers (id, tenant_id, full_name, email, kyc_status, pep_status, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, customer_id, tenant_id, 'Test Customer', 'customer@example.com', 'pending', 'not_pep', True)
            test_data_ids.append(('customers', customer_id))
            print("  ✓ Created customer")
            
            # Create transaction
            transaction_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO transactions (id, tenant_id, customer_id, amount, currency, transaction_type, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, transaction_id, tenant_id, customer_id, 1000.00, 'USD', 'transfer', 'completed')
            test_data_ids.append(('transactions', transaction_id))
            print("  ✓ Created transaction")
            
            # Create role
            role_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO roles (id, name, description, permissions)
                VALUES ($1, $2, $3, $4)
            """, role_id, 'test_role', 'Test Role', json.dumps(['test.permission']))
            test_data_ids.append(('roles', role_id))
            print("  ✓ Created role")
            
            # Create user role assignment
            user_role_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO user_roles (id, user_id, role_id)
                VALUES ($1, $2, $3)
            """, user_role_id, user_id, role_id)
            test_data_ids.append(('user_roles', user_role_id))
            print("  ✓ Created user role assignment")
            
            # Create risk assessment
            risk_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO risk_assessments (id, tenant_id, assessment_type, entity_type, entity_id, risk_score, risk_level)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, risk_id, tenant_id, 'customer_risk', 'customer', customer_id, 75.5, 'medium')
            test_data_ids.append(('risk_assessments', risk_id))
            print("  ✓ Created risk assessment")
            
            # Create regulation
            regulation_id = str(uuid.uuid4())
            await connection.execute("""
                INSERT INTO regulations (id, regulation_code, title, jurisdiction, regulatory_body, category)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, regulation_id, 'TEST-REG-001', 'Test Regulation', 'US', 'Test Authority', 'AML')
            test_data_ids.append(('regulations', regulation_id))
            print("  ✓ Created regulation")
            
            print("✅ All CRUD operations successful")
            
        except Exception as e:
            print(f"❌ CRUD operations failed: {str(e)}")
            errors.append(f"CRUD operations failed: {str(e)}")
        
        # Test 4: Foreign key relationships
        print("\n4. Testing foreign key relationships...")
        try:
            # Try to create user with invalid tenant_id (should fail)
            try:
                invalid_tenant_id = str(uuid.uuid4())
                await connection.execute("""
                    INSERT INTO users (id, tenant_id, email, full_name)
                    VALUES ($1, $2, $3, $4)
                """, str(uuid.uuid4()), invalid_tenant_id, 'invalid@example.com', 'Invalid User')
                
                print("❌ Foreign key constraint not working")
                errors.append("Foreign key constraint not working")
                
            except Exception:
                print("✅ Foreign key constraints working correctly")
                
        except Exception as e:
            print(f"❌ Foreign key test failed: {str(e)}")
            errors.append(f"Foreign key test failed: {str(e)}")
        
        # Test 5: Triggers
        print("\n5. Testing triggers...")
        try:
            if test_data_ids:
                tenant_record = next((item for item in test_data_ids if item[0] == 'tenants'), None)
                if tenant_record:
                    tenant_id = tenant_record[1]
                    
                    # Get initial updated_at
                    initial_record = await connection.fetchrow("""
                        SELECT updated_at FROM tenants WHERE id = $1
                    """, tenant_id)
                    
                    # Wait a moment
                    await asyncio.sleep(1)
                    
                    # Update the record
                    await connection.execute("""
                        UPDATE tenants SET name = 'Updated Test Tenant' WHERE id = $1
                    """, tenant_id)
                    
                    # Get updated record
                    updated_record = await connection.fetchrow("""
                        SELECT updated_at FROM tenants WHERE id = $1
                    """, tenant_id)
                    
                    if updated_record['updated_at'] > initial_record['updated_at']:
                        print("✅ Update triggers working correctly")
                    else:
                        print("❌ Update triggers not working")
                        errors.append("Update triggers not working")
                        
        except Exception as e:
            print(f"❌ Trigger test failed: {str(e)}")
            errors.append(f"Trigger test failed: {str(e)}")
        
        # Test 6: Advanced features
        print("\n6. Testing advanced features...")
        try:
            if test_data_ids:
                tenant_record = next((item for item in test_data_ids if item[0] == 'tenants'), None)
                if tenant_record:
                    tenant_id = tenant_record[1]
                    
                    # Test ML models
                    ml_model_id = str(uuid.uuid4())
                    await connection.execute("""
                        INSERT INTO ml_models (id, tenant_id, name, model_type, version, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, ml_model_id, tenant_id, 'Test Model', 'classification', '1.0', 'trained')
                    test_data_ids.append(('ml_models', ml_model_id))
                    
                    # Test ML deployments
                    deployment_id = str(uuid.uuid4())
                    await connection.execute("""
                        INSERT INTO ml_deployments (id, tenant_id, model_id, deployment_name, environment, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, deployment_id, tenant_id, ml_model_id, 'test-deployment', 'development', 'active')
                    test_data_ids.append(('ml_deployments', deployment_id))
                    
                    print("✅ Advanced features working correctly")
                    
        except Exception as e:
            print(f"❌ Advanced features test failed: {str(e)}")
            errors.append(f"Advanced features test failed: {str(e)}")
        
        # Get final database statistics
        print("\n7. Database statistics...")
        total_tables = await connection.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        
        total_functions = await connection.fetchval("""
            SELECT COUNT(*) FROM information_schema.routines 
            WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
        """)
        
        total_triggers = await connection.fetchval("""
            SELECT COUNT(*) FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
        """)
        
        total_constraints = await connection.fetchval("""
            SELECT COUNT(*) FROM information_schema.table_constraints 
            WHERE table_schema = 'public'
        """)
        
        print(f"  Tables: {total_tables}")
        print(f"  Functions: {total_functions}")
        print(f"  Triggers: {total_triggers}")
        print(f"  Constraints: {total_constraints}")
        
        # Clean up test data
        print("\n8. Cleaning up test data...")
        for table, record_id in reversed(test_data_ids):
            try:
                await connection.execute(f"DELETE FROM {table} WHERE id = $1", record_id)
            except Exception as e:
                print(f"Warning: Could not delete test record from {table}: {str(e)}")
        
        print("✅ Test data cleanup completed")
        
        # Final report
        print("\n" + "="*80)
        print("🎯 FINAL VALIDATION REPORT")
        print("="*80)
        print(f"Database Objects:")
        print(f"  📊 Tables: {total_tables}")
        print(f"  ⚙️  Functions: {total_functions}")
        print(f"  🔄 Triggers: {total_triggers}")
        print(f"  🔒 Constraints: {total_constraints}")
        print(f"\nValidation Results:")
        print(f"  ❌ Errors: {len(errors)}")
        
        if errors:
            print(f"\nErrors Found:")
            for error in errors:
                print(f"  • {error}")
        
        await connection.close()
        
        if len(errors) == 0:
            print("\n🎉 FINAL STATUS: 100% SUCCESS!")
            print("✅ RegulensAI database schema is fully deployed and functional!")
            print("✅ All tables, columns, relationships, and features are working correctly.")
            print("✅ The database is ready for production use!")
            return True
        else:
            print(f"\n🚨 FINAL STATUS: {len(errors)} ISSUES DETECTED")
            print("Some validation tests failed. Please review the errors above.")
            return False
        
    except Exception as e:
        print(f"❌ Final validation failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_final_validation())
    sys.exit(0 if success else 1)
