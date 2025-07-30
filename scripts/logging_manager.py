#!/usr/bin/env python3
"""
RegulensAI Logging Manager CLI
Command-line interface for managing centralized logging system.
"""

import asyncio
import argparse
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_infra.logging.centralized_logging import (
    logging_manager, 
    LogLevel, 
    LogCategory,
    get_centralized_logger
)
from core_infra.config import get_settings
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class LoggingManagerCLI:
    """Command-line interface for logging management."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def start_logging(self, args):
        """Start the centralized logging system."""
        try:
            print("Starting centralized logging system...")
            
            await logging_manager.start()
            
            print("✅ Centralized logging system started successfully!")
            
            # Test the system
            if args.test:
                await self.test_logging_system()
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to start logging system: {e}")
            logger.error("Logging system startup failed", error=str(e))
            return 1
    
    async def stop_logging(self, args):
        """Stop the centralized logging system."""
        try:
            print("Stopping centralized logging system...")
            
            await logging_manager.stop()
            
            print("✅ Centralized logging system stopped successfully!")
            return 0
            
        except Exception as e:
            print(f"❌ Failed to stop logging system: {e}")
            logger.error("Logging system shutdown failed", error=str(e))
            return 1
    
    async def show_status(self, args):
        """Show logging system status."""
        try:
            stats = await logging_manager.get_log_statistics()
            
            print("RegulensAI Centralized Logging Status")
            print("=" * 45)
            print(f"Status: {stats['status']}")
            print(f"Buffer Size: {stats['buffer_size']}/{stats['max_buffer_size']}")
            print(f"Elasticsearch: {'Enabled' if stats['elasticsearch_enabled'] else 'Disabled'}")
            print(f"File Logging: {'Enabled' if stats['file_logging_enabled'] else 'Disabled'}")
            print(f"Active Loggers: {stats['active_loggers']}")
            
            if stats['logger_names']:
                print(f"Logger Names: {', '.join(stats['logger_names'])}")
            
            # Test Elasticsearch connection
            if stats['elasticsearch_enabled']:
                print("\nTesting Elasticsearch connection...")
                es_status = await logging_manager.test_elasticsearch_connection()
                print(f"Elasticsearch Status: {es_status['status']}")
                print(f"Message: {es_status['message']}")
                
                if es_status['status'] == 'connected':
                    print(f"Cluster: {es_status.get('cluster_name', 'Unknown')}")
                    print(f"Version: {es_status.get('version', 'Unknown')}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
            logger.error("Status check failed", error=str(e))
            return 1
    
    async def test_logging_system(self):
        """Test the logging system with sample logs."""
        try:
            print("\nTesting logging system...")
            
            # Get a test logger
            test_logger = await get_centralized_logger("test_logger")
            
            # Test different log levels and categories
            await test_logger.info("Test info message", category=LogCategory.APPLICATION)
            await test_logger.warning("Test warning message", category=LogCategory.SECURITY)
            await test_logger.error("Test error message", category=LogCategory.SYSTEM)
            await test_logger.audit("Test audit message", user_id="test_user", action="test_action")
            await test_logger.performance("Test performance message", duration_ms=150.5)
            
            # Test with context
            context_logger = test_logger.with_context(
                user_id="test_user_123",
                tenant_id="test_tenant_456",
                request_id="test_request_789"
            )
            
            await context_logger.info("Test message with context")
            
            print("✅ Test logs sent successfully!")
            
            # Flush logs
            await logging_manager.flush_logs()
            print("✅ Logs flushed to destinations!")
            
        except Exception as e:
            print(f"❌ Logging test failed: {e}")
            raise
    
    async def flush_logs(self, args):
        """Manually flush all buffered logs."""
        try:
            print("Flushing buffered logs...")
            
            await logging_manager.flush_logs()
            
            print("✅ Logs flushed successfully!")
            return 0
            
        except Exception as e:
            print(f"❌ Failed to flush logs: {e}")
            logger.error("Log flush failed", error=str(e))
            return 1
    
    async def test_elasticsearch(self, args):
        """Test Elasticsearch connection."""
        try:
            print("Testing Elasticsearch connection...")
            
            result = await logging_manager.test_elasticsearch_connection()
            
            print(f"Status: {result['status']}")
            print(f"Message: {result['message']}")
            
            if result['status'] == 'connected':
                print(f"Cluster Name: {result.get('cluster_name', 'Unknown')}")
                print(f"Version: {result.get('version', 'Unknown')}")
                print("✅ Elasticsearch connection successful!")
                return 0
            else:
                print("❌ Elasticsearch connection failed!")
                return 1
                
        except Exception as e:
            print(f"❌ Elasticsearch test failed: {e}")
            logger.error("Elasticsearch test failed", error=str(e))
            return 1
    
    async def send_test_logs(self, args):
        """Send test logs to the system."""
        try:
            print(f"Sending {args.count} test logs...")
            
            test_logger = await get_centralized_logger("test_generator")
            
            for i in range(args.count):
                # Vary log levels and categories
                if i % 10 == 0:
                    await test_logger.error(f"Test error message {i}", 
                                          category=LogCategory.APPLICATION,
                                          test_id=i)
                elif i % 7 == 0:
                    await test_logger.warning(f"Test warning message {i}", 
                                            category=LogCategory.SECURITY,
                                            test_id=i)
                elif i % 5 == 0:
                    await test_logger.audit(f"Test audit message {i}", 
                                          user_id=f"user_{i % 100}",
                                          action="test_action",
                                          test_id=i)
                elif i % 3 == 0:
                    await test_logger.performance(f"Test performance message {i}", 
                                                 duration_ms=float(i * 10),
                                                 test_id=i)
                else:
                    await test_logger.info(f"Test info message {i}", 
                                         category=LogCategory.APPLICATION,
                                         test_id=i)
                
                if args.delay and i % 10 == 0:
                    await asyncio.sleep(args.delay)
            
            print(f"✅ Sent {args.count} test logs successfully!")
            
            # Flush logs
            await logging_manager.flush_logs()
            print("✅ Logs flushed to destinations!")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to send test logs: {e}")
            logger.error("Test log generation failed", error=str(e))
            return 1
    
    async def show_config(self, args):
        """Show current logging configuration."""
        try:
            config = logging_manager.config
            
            print("RegulensAI Logging Configuration")
            print("=" * 40)
            print(f"Buffer Size: {config['buffer_size']}")
            print(f"Flush Interval: {config['flush_interval']}s")
            print(f"Retry Attempts: {config['retry_attempts']}")
            print(f"Retry Delay: {config['retry_delay']}s")
            
            print("\nElasticsearch Configuration:")
            es_config = config['elasticsearch']
            print(f"  Enabled: {es_config['enabled']}")
            print(f"  Host: {es_config['host']}")
            print(f"  Port: {es_config['port']}")
            print(f"  Scheme: {es_config['scheme']}")
            print(f"  Username: {es_config['username'] or 'Not set'}")
            print(f"  Verify Certs: {es_config['verify_certs']}")
            print(f"  Timeout: {es_config['timeout']}s")
            
            print("\nFile Output Configuration:")
            file_config = config['file_output']
            print(f"  Enabled: {file_config.get('enabled', True)}")
            print(f"  Directory: {file_config['directory']}")
            
            print("\nExternal Services:")
            external_config = config['external_services']
            print(f"  Webhooks: {len(external_config['webhooks'])} configured")
            print(f"  SIEM Enabled: {external_config['siem']['enabled']}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to show config: {e}")
            logger.error("Config display failed", error=str(e))
            return 1
    
    async def tail_logs(self, args):
        """Tail logs from file output."""
        try:
            log_dir = Path(self.settings.log_directory)
            
            if args.category:
                log_file = log_dir / f"regulensai-{args.category}.log"
            else:
                log_file = log_dir / "regulensai-application.log"
            
            if not log_file.exists():
                print(f"❌ Log file not found: {log_file}")
                return 1
            
            print(f"Tailing log file: {log_file}")
            print("Press Ctrl+C to stop")
            print("-" * 50)
            
            # Simple tail implementation
            with open(log_file, 'r') as f:
                # Go to end of file
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        # Parse JSON and pretty print
                        try:
                            log_data = json.loads(line.strip())
                            timestamp = log_data.get('timestamp', 'Unknown')
                            level = log_data.get('level', 'INFO')
                            message = log_data.get('message', '')
                            print(f"[{timestamp}] {level}: {message}")
                        except json.JSONDecodeError:
                            print(line.strip())
                    else:
                        await asyncio.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\n✅ Stopped tailing logs")
            return 0
        except Exception as e:
            print(f"❌ Failed to tail logs: {e}")
            logger.error("Log tailing failed", error=str(e))
            return 1


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RegulensAI Centralized Logging Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --test
  %(prog)s status
  %(prog)s test-logs --count 100 --delay 0.1
  %(prog)s tail --category security
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start centralized logging")
    start_parser.add_argument("--test", action="store_true", help="Run test after starting")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop centralized logging")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show logging system status")
    
    # Flush command
    flush_parser = subparsers.add_parser("flush", help="Flush buffered logs")
    
    # Test Elasticsearch command
    es_test_parser = subparsers.add_parser("test-es", help="Test Elasticsearch connection")
    
    # Send test logs command
    test_logs_parser = subparsers.add_parser("test-logs", help="Send test logs")
    test_logs_parser.add_argument("--count", "-c", type=int, default=10, help="Number of test logs")
    test_logs_parser.add_argument("--delay", "-d", type=float, default=0, help="Delay between batches")
    
    # Show config command
    config_parser = subparsers.add_parser("config", help="Show logging configuration")
    
    # Tail logs command
    tail_parser = subparsers.add_parser("tail", help="Tail log files")
    tail_parser.add_argument("--category", "-c", help="Log category to tail")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = LoggingManagerCLI()
    
    # Execute command
    if args.command == "start":
        return await cli.start_logging(args)
    elif args.command == "stop":
        return await cli.stop_logging(args)
    elif args.command == "status":
        return await cli.show_status(args)
    elif args.command == "flush":
        return await cli.flush_logs(args)
    elif args.command == "test-es":
        return await cli.test_elasticsearch(args)
    elif args.command == "test-logs":
        return await cli.send_test_logs(args)
    elif args.command == "config":
        return await cli.show_config(args)
    elif args.command == "tail":
        return await cli.tail_logs(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
