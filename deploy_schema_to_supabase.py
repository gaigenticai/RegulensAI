#!/usr/bin/env python3
"""
RegulensAI Database Schema Deployment to Supabase
Deploys the consolidated schema.sql file to Supabase PostgreSQL database.
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple
import re

# Supabase connection configuration
SUPABASE_CONFIG = {
    'host': 'db.qoqzovknwsemxhlaobsv.supabase.co',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'mdRh6u26EeogT2M0'
}

SCHEMA_FILE_PATH = 'core_infra/database/schema.sql'

class SchemaDeployer:
    """Handles deployment of RegulensAI schema to Supabase."""
    
    def __init__(self):
        self.connection = None
        self.deployment_log = []
        self.errors = []
        self.warnings = []
        self.created_objects = {
            'tables': [],
            'indexes': [],
            'constraints': [],
            'functions': [],
            'triggers': []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log deployment messages."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.deployment_log.append(log_entry)
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
            
            # Test connection with a simple query
            version = await self.connection.fetchval("SELECT version()")
            self.log(f"Connected successfully. PostgreSQL version: {version[:50]}...")
            
            return True
            
        except Exception as e:
            self.log(f"Failed to connect to Supabase: {str(e)}", "ERROR")
            return False
    
    async def read_schema_file(self) -> str:
        """Read the consolidated schema file."""
        try:
            if not os.path.exists(SCHEMA_FILE_PATH):
                raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE_PATH}")
            
            with open(SCHEMA_FILE_PATH, 'r', encoding='utf-8') as file:
                schema_content = file.read()
            
            self.log(f"Schema file loaded: {len(schema_content)} characters")
            return schema_content
            
        except Exception as e:
            self.log(f"Failed to read schema file: {str(e)}", "ERROR")
            raise
    
    def split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements."""
        # Remove comments and split by semicolons
        statements = []
        current_statement = ""
        in_comment = False
        in_string = False
        
        lines = sql_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
            
            # Handle multi-line comments
            if '/*' in line and '*/' in line:
                # Single line comment, remove it
                line = re.sub(r'/\*.*?\*/', '', line).strip()
            elif '/*' in line:
                in_comment = True
                line = line[:line.index('/*')].strip()
            elif '*/' in line and in_comment:
                in_comment = False
                line = line[line.index('*/') + 2:].strip()
            
            if in_comment or not line:
                continue
            
            current_statement += " " + line
            
            # Check if statement is complete (ends with semicolon)
            if line.endswith(';'):
                statement = current_statement.strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        self.log(f"Split schema into {len(statements)} SQL statements")
        return statements
    
    async def execute_statement(self, statement: str) -> Tuple[bool, str]:
        """Execute a single SQL statement with error handling."""
        try:
            # Clean up the statement
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                return True, "Skipped comment or empty statement"
            
            # Execute the statement
            await self.connection.execute(statement)
            
            # Track created objects
            self.track_created_object(statement)
            
            return True, "Success"
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific PostgreSQL errors
            if "already exists" in error_msg.lower():
                self.log(f"Object already exists (skipping): {error_msg}", "WARNING")
                return True, f"Already exists: {error_msg}"
            elif "does not exist" in error_msg.lower() and "IF NOT EXISTS" in statement.upper():
                # This is expected for IF NOT EXISTS statements
                return True, "IF NOT EXISTS handled gracefully"
            else:
                self.log(f"SQL execution error: {error_msg}", "ERROR")
                self.log(f"Failed statement: {statement[:100]}...", "ERROR")
                return False, error_msg
    
    def track_created_object(self, statement: str):
        """Track created database objects for reporting."""
        statement_upper = statement.upper().strip()
        
        if statement_upper.startswith('CREATE TABLE'):
            table_match = re.search(r'CREATE TABLE.*?(\w+\.\w+|\w+)', statement_upper)
            if table_match:
                self.created_objects['tables'].append(table_match.group(1))
        
        elif statement_upper.startswith('CREATE INDEX'):
            index_match = re.search(r'CREATE.*?INDEX.*?(\w+)', statement_upper)
            if index_match:
                self.created_objects['indexes'].append(index_match.group(1))
        
        elif statement_upper.startswith('ALTER TABLE') and 'ADD CONSTRAINT' in statement_upper:
            constraint_match = re.search(r'ADD CONSTRAINT\s+(\w+)', statement_upper)
            if constraint_match:
                self.created_objects['constraints'].append(constraint_match.group(1))
        
        elif statement_upper.startswith('CREATE FUNCTION'):
            function_match = re.search(r'CREATE.*?FUNCTION\s+(\w+)', statement_upper)
            if function_match:
                self.created_objects['functions'].append(function_match.group(1))
        
        elif statement_upper.startswith('CREATE TRIGGER'):
            trigger_match = re.search(r'CREATE TRIGGER\s+(\w+)', statement_upper)
            if trigger_match:
                self.created_objects['triggers'].append(trigger_match.group(1))
    
    async def deploy_schema(self):
        """Deploy the complete schema to Supabase."""
        try:
            self.log("Starting RegulensAI schema deployment to Supabase...")
            
            # Read schema file
            schema_content = await self.read_schema_file()
            
            # Split into statements
            statements = self.split_sql_statements(schema_content)
            
            # Execute statements
            successful_statements = 0
            failed_statements = 0
            
            for i, statement in enumerate(statements, 1):
                self.log(f"Executing statement {i}/{len(statements)}...")
                
                success, message = await self.execute_statement(statement)
                
                if success:
                    successful_statements += 1
                else:
                    failed_statements += 1
                    # Continue with deployment even if some statements fail
                    continue
            
            self.log(f"Schema deployment completed: {successful_statements} successful, {failed_statements} failed")
            
            return successful_statements, failed_statements
            
        except Exception as e:
            self.log(f"Schema deployment failed: {str(e)}", "ERROR")
            raise
    
    async def validate_deployment(self):
        """Validate the deployed schema."""
        try:
            self.log("Validating deployed schema...")
            
            # Check table count
            table_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            
            self.log(f"Total tables created: {table_count}")
            
            # Check for specific RegulensAI core tables
            core_tables = ['tenants', 'users', 'regulations', 'compliance_tasks', 'risk_assessments']
            existing_core_tables = []
            
            for table in core_tables:
                exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                """, table)
                
                if exists:
                    existing_core_tables.append(table)
            
            self.log(f"Core RegulensAI tables found: {len(existing_core_tables)}/{len(core_tables)}")
            
            # Check indexes
            index_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'
            """)
            
            self.log(f"Total indexes created: {index_count}")
            
            # Test a simple query
            try:
                tenant_count = await self.connection.fetchval("SELECT COUNT(*) FROM tenants")
                self.log(f"Sample query successful - tenants table has {tenant_count} records")
            except Exception as e:
                self.log(f"Sample query failed: {str(e)}", "WARNING")
            
            return {
                'total_tables': table_count,
                'core_tables_found': len(existing_core_tables),
                'total_indexes': index_count,
                'validation_successful': table_count > 50  # Expect at least 50 tables
            }
            
        except Exception as e:
            self.log(f"Schema validation failed: {str(e)}", "ERROR")
            return {'validation_successful': False, 'error': str(e)}
    
    async def close_connection(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.log("Database connection closed")
    
    def generate_deployment_report(self, validation_results: Dict[str, Any]):
        """Generate comprehensive deployment report."""
        report = []
        report.append("=" * 80)
        report.append("REGULENSAI SCHEMA DEPLOYMENT REPORT")
        report.append("=" * 80)
        report.append(f"Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Target Database: Supabase PostgreSQL")
        report.append(f"Schema File: {SCHEMA_FILE_PATH}")
        report.append("")
        
        # Deployment Summary
        report.append("DEPLOYMENT SUMMARY:")
        report.append("-" * 40)
        report.append(f"Total Errors: {len(self.errors)}")
        report.append(f"Total Warnings: {len(self.warnings)}")
        report.append("")
        
        # Created Objects Summary
        report.append("CREATED OBJECTS:")
        report.append("-" * 40)
        for obj_type, objects in self.created_objects.items():
            report.append(f"{obj_type.title()}: {len(objects)}")
        report.append("")
        
        # Validation Results
        report.append("VALIDATION RESULTS:")
        report.append("-" * 40)
        for key, value in validation_results.items():
            report.append(f"{key}: {value}")
        report.append("")
        
        # Errors and Warnings
        if self.errors:
            report.append("ERRORS ENCOUNTERED:")
            report.append("-" * 40)
            for error in self.errors:
                report.append(f"• {error}")
            report.append("")
        
        if self.warnings:
            report.append("WARNINGS:")
            report.append("-" * 40)
            for warning in self.warnings:
                report.append(f"• {warning}")
            report.append("")
        
        # Final Status
        status = "SUCCESS" if validation_results.get('validation_successful', False) else "PARTIAL SUCCESS"
        report.append(f"DEPLOYMENT STATUS: {status}")
        report.append("=" * 80)
        
        return "\n".join(report)

async def main():
    """Main deployment function."""
    deployer = SchemaDeployer()
    
    try:
        # Connect to Supabase
        if not await deployer.connect_to_supabase():
            print("Failed to connect to Supabase. Exiting.")
            return 1
        
        # Deploy schema
        successful, failed = await deployer.deploy_schema()
        
        # Validate deployment
        validation_results = await deployer.validate_deployment()
        
        # Generate and display report
        report = deployer.generate_deployment_report(validation_results)
        print("\n" + report)
        
        # Save report to file
        with open('schema_deployment_report.txt', 'w') as f:
            f.write(report)
        
        deployer.log("Deployment report saved to schema_deployment_report.txt")
        
        return 0 if validation_results.get('validation_successful', False) else 1
        
    except Exception as e:
        deployer.log(f"Deployment failed with exception: {str(e)}", "ERROR")
        return 1
        
    finally:
        await deployer.close_connection()

if __name__ == "__main__":
    # Install required package if not available
    try:
        import asyncpg
    except ImportError:
        print("Installing required package: asyncpg")
        os.system("pip install asyncpg")
        import asyncpg
    
    # Run deployment
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
