"""
Database connection management for Supabase
"""
import os
import asyncio
from supabase import create_client, Client
import asyncpg
from typing import Optional

# Global Supabase client
supabase: Optional[Client] = None
postgres_pool: Optional[asyncpg.Pool] = None

async def init_database():
    """Initialize database connections"""
    global supabase, postgres_pool
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")
    else:
        print("⚠️ Supabase credentials not found - running without database")
    
    # Initialize direct PostgreSQL connection for async operations
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            postgres_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
            print("✅ PostgreSQL connection pool initialized")
        except Exception as e:
            print(f"⚠️ PostgreSQL connection failed: {e}")
    
    return supabase

async def close_database():
    """Close database connections"""
    global postgres_pool
    
    if postgres_pool:
        await postgres_pool.close()
        print("✅ PostgreSQL connection pool closed")

def get_supabase() -> Optional[Client]:
    """Get Supabase client"""
    return supabase

def get_postgres_pool() -> Optional[asyncpg.Pool]:
    """Get PostgreSQL connection pool"""
    return postgres_pool

async def get_database():
    """Get database connection"""
    # Return a mock database connection for now
    return MockDatabase()

class MockDatabase:
    """Mock database for testing"""
    
    async def fetch(self, query, *args):
        """Mock fetch method"""
        return []
    
    async def fetchrow(self, query, *args):
        """Mock fetchrow method"""
        return None
    
    async def execute(self, query, *args):
        """Mock execute method"""
        return None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass 