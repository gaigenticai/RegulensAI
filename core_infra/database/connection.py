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

    # Get settings from config system
    from core_infra.config import get_settings
    settings = get_settings()

    # Initialize Supabase client (temporarily disabled for testing)
    supabase_url = str(settings.supabase_url) if settings.supabase_url else None
    supabase_key = str(settings.supabase_anon_key) if settings.supabase_anon_key else None

    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            print("✅ Supabase client initialized")
        except Exception as e:
            print(f"⚠️ Supabase client initialization failed: {e}")
            print("⚠️ Continuing with PostgreSQL connection only")
    else:
        print("⚠️ Supabase credentials not found - running without database")

    # Initialize direct PostgreSQL connection for async operations
    database_url = str(settings.database_url) if settings.database_url else None
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

def get_database():
    """Get database connection context manager"""
    class DatabaseContext:
        def __init__(self, pool):
            self.pool = pool
            self.connection = None

        async def __aenter__(self):
            if self.pool:
                self.connection = await self.pool.acquire()
                return self.connection
            else:
                raise RuntimeError("Database pool not initialized")

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.connection:
                await self.pool.release(self.connection)

    return DatabaseContext(postgres_pool)