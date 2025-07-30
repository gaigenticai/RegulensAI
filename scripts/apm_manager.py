#!/usr/bin/env python3
"""
RegulensAI APM Manager CLI
Command-line interface for managing Application Performance Monitoring system.
"""

import asyncio
import argparse
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import tabulate

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_infra.monitoring.apm_integration import (
    apm_manager,
    init_apm,
    shutdown_apm,
    get_performance_summary,
    get_database_performance,
    get_error_statistics,
    get_resource_metrics,
    track_compliance_processing_time,
    track_regulatory_data_ingestion,
    track_api_response_time
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


class APMManagerCLI:
    """Command-line interface for APM management."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def start_apm(self, args):
        """Start the APM system."""
        try:
            print("Starting APM system...")
            
            await init_apm()
            
            print("✅ APM system started successfully!")
            
            # Show status
            if args.status:
                await self.show_status(args)
            
            # Run test if requested
            if args.test:
                await self.run_performance_test(args)
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to start APM system: {e}")
            logger.error("APM system startup failed", error=str(e))
            return 1
    
    async def stop_apm(self, args):
        """Stop the APM system."""
        try:
            print("Stopping APM system...")
            
            await shutdown_apm()
            
            print("✅ APM system stopped successfully!")
            return 0
            
        except Exception as e:
            print(f"❌ Failed to stop APM system: {e}")
            logger.error("APM system shutdown failed", error=str(e))
            return 1
    
    async def show_status(self, args):
        """Show APM system status."""
        try:
            print("RegulensAI APM System Status")
            print("=" * 50)
            
            # Get performance summary
            summary = await get_performance_summary()
            
            # APM Providers
            print(f"\n🔧 Active APM Providers:")
            for provider in summary.get('active_providers', []):
                print(f"  • {provider}")
            
            # Database Performance
            db_stats = summary.get('database_stats', {})
            print(f"\n📊 Database Performance:")
            print(f"  Total Queries: {db_stats.get('total_queries', 0)}")
            print(f"  Average Query Time: {db_stats.get('average_query_time', 0):.3f}s")
            print(f"  Error Rate: {db_stats.get('error_rate', 0):.2%}")
            print(f"  Slow Queries: {db_stats.get('slow_query_count', 0)}")
            
            # Error Statistics
            error_stats = summary.get('error_stats', {})
            print(f"\n🚨 Error Statistics:")
            print(f"  Error Rate: {error_stats.get('error_rate', 0):.2f} errors/min")
            print(f"  Total Errors: {error_stats.get('total_errors', 0)}")
            
            # Resource Usage
            resource_stats = summary.get('resource_stats', {})
            print(f"\n💻 Resource Usage:")
            print(f"  CPU: {resource_stats.get('cpu_percent', 0):.1f}%")
            print(f"  Memory: {resource_stats.get('memory_percent', 0):.1f}%")
            print(f"  Memory RSS: {resource_stats.get('memory_rss', 0):.1f} MB")
            print(f"  File Descriptors: {resource_stats.get('file_descriptors', 0)}")
            
            # Business Metrics
            business_metrics = summary.get('business_metrics', {})
            print(f"\n📈 Business Metrics:")
            for metric_name, metric_data in business_metrics.items():
                if metric_data.get('count', 0) > 0:
                    latest = metric_data.get('latest', {})
                    if latest:
                        print(f"  {metric_name}: {latest.get('value', 0):.2f} (latest)")
            
            # Recent Regression Alerts
            regression_alerts = summary.get('regression_alerts', [])
            if regression_alerts:
                print(f"\n⚠️  Recent Performance Regressions:")
                for alert in regression_alerts[-5:]:  # Show last 5
                    print(f"  • {alert.get('service', 'unknown')}.{alert.get('operation', 'unknown')}: "
                          f"{alert.get('regression_percentage', 0):.1f}% slower")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get APM status: {e}")
            logger.error("APM status check failed", error=str(e))
            return 1
    
    async def show_database_performance(self, args):
        """Show detailed database performance statistics."""
        try:
            print("Database Performance Analysis")
            print("=" * 40)
            
            db_stats = await get_database_performance()
            
            # Overall statistics
            print(f"\n📊 Overall Statistics:")
            print(f"  Total Queries: {db_stats.get('total_queries', 0)}")
            print(f"  Total Execution Time: {db_stats.get('total_execution_time', 0):.3f}s")
            print(f"  Average Query Time: {db_stats.get('average_query_time', 0):.3f}s")
            print(f"  Error Rate: {db_stats.get('error_rate', 0):.2%}")
            print(f"  Slow Query Count: {db_stats.get('slow_query_count', 0)}")
            print(f"  Unique Query Patterns: {db_stats.get('unique_query_patterns', 0)}")
            
            # Connection pool stats
            pool_stats = db_stats.get('connection_pool', {})
            if pool_stats:
                print(f"\n🔗 Connection Pool:")
                print(f"  Active Connections: {pool_stats.get('active_connections', 0)}")
                print(f"  Idle Connections: {pool_stats.get('idle_connections', 0)}")
                print(f"  Total Connections: {pool_stats.get('total_connections', 0)}")
                print(f"  Connection Errors: {pool_stats.get('connection_errors', 0)}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get database performance: {e}")
            logger.error("Database performance check failed", error=str(e))
            return 1
    
    async def show_error_analysis(self, args):
        """Show detailed error analysis."""
        try:
            print("Error Analysis Report")
            print("=" * 30)
            
            error_stats = await get_error_statistics()
            
            print(f"\n🚨 Error Summary:")
            print(f"  Current Error Rate: {error_stats.get('error_rate', 0):.2f} errors/min")
            print(f"  Total Errors Tracked: {error_stats.get('total_errors', 0)}")
            
            # Top errors
            top_errors = error_stats.get('top_errors', [])
            if top_errors:
                print(f"\n🔥 Top Errors:")
                
                headers = ['Error Signature', 'Count', 'Affected Users', 'Last Seen']
                rows = []
                
                for error in top_errors[:10]:
                    rows.append([
                        error.get('error_signature', 'Unknown')[:50] + '...' if len(error.get('error_signature', '')) > 50 else error.get('error_signature', 'Unknown'),
                        error.get('count', 0),
                        error.get('affected_users', 0),
                        error.get('last_seen', 'Unknown')
                    ])
                
                print(tabulate.tabulate(rows, headers=headers, tablefmt='grid'))
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get error analysis: {e}")
            logger.error("Error analysis failed", error=str(e))
            return 1
    
    async def show_resource_metrics(self, args):
        """Show current resource metrics."""
        try:
            print("Resource Metrics")
            print("=" * 20)
            
            metrics = await get_resource_metrics()
            
            # CPU metrics
            print(f"\n🖥️  CPU Metrics:")
            print(f"  CPU Usage: {metrics.get('cpu_percent', 0):.1f}%")
            print(f"  User Time: {metrics.get('cpu_user_time', 0):.2f}s")
            print(f"  System Time: {metrics.get('cpu_system_time', 0):.2f}s")
            
            # Memory metrics
            print(f"\n💾 Memory Metrics:")
            print(f"  Memory Usage: {metrics.get('memory_percent', 0):.1f}%")
            print(f"  RSS Memory: {metrics.get('memory_rss', 0):.1f} MB")
            print(f"  VMS Memory: {metrics.get('memory_vms', 0):.1f} MB")
            
            # I/O metrics
            print(f"\n💿 I/O Metrics:")
            print(f"  Read Bytes: {metrics.get('io_read_bytes', 0):,}")
            print(f"  Write Bytes: {metrics.get('io_write_bytes', 0):,}")
            print(f"  Read Count: {metrics.get('io_read_count', 0):,}")
            print(f"  Write Count: {metrics.get('io_write_count', 0):,}")
            
            # Network metrics
            print(f"\n🌐 Network Metrics:")
            print(f"  Bytes Sent: {metrics.get('network_bytes_sent', 0):,}")
            print(f"  Bytes Received: {metrics.get('network_bytes_recv', 0):,}")
            print(f"  Packets Sent: {metrics.get('network_packets_sent', 0):,}")
            print(f"  Packets Received: {metrics.get('network_packets_recv', 0):,}")
            
            # Process metrics
            print(f"\n🔧 Process Metrics:")
            print(f"  File Descriptors: {metrics.get('file_descriptors', 0)}")
            print(f"  Threads: {metrics.get('threads', 0)}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get resource metrics: {e}")
            logger.error("Resource metrics check failed", error=str(e))
            return 1
    
    async def run_performance_test(self, args):
        """Run performance test to generate sample metrics."""
        try:
            print("Running APM performance test...")
            
            # Simulate compliance processing
            print("📋 Simulating compliance processing...")
            for i in range(args.count):
                processing_time = 5.0 + (i * 0.1)  # Simulate varying processing times
                await track_compliance_processing_time(
                    processing_time,
                    f"regulation_type_{i % 3}",
                    f"tenant_{i % 5}"
                )
                
                if i % 10 == 0:
                    print(f"  Processed {i + 1}/{args.count} compliance operations")
            
            # Simulate regulatory data ingestion
            print("📊 Simulating regulatory data ingestion...")
            for i in range(args.count // 2):
                records_processed = 100 + (i * 10)
                duration = 2.0 + (i * 0.05)
                await track_regulatory_data_ingestion(
                    records_processed,
                    f"source_{i % 3}",
                    duration
                )
            
            # Simulate API response times
            print("🌐 Simulating API response times...")
            endpoints = ['/api/v1/regulations', '/api/v1/compliance', '/api/v1/reports']
            methods = ['GET', 'POST', 'PUT']
            
            for i in range(args.count):
                endpoint = endpoints[i % len(endpoints)]
                method = methods[i % len(methods)]
                response_time = 100 + (i * 5)  # milliseconds
                status_code = 200 if i % 20 != 0 else 500  # 5% error rate
                
                await track_api_response_time(endpoint, method, response_time, status_code)
            
            print(f"✅ Performance test completed! Generated {args.count} test metrics")
            
            # Show updated status
            await asyncio.sleep(2)  # Allow metrics to be processed
            await self.show_status(args)
            
            return 0
            
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            logger.error("Performance test failed", error=str(e))
            return 1
    
    async def export_metrics(self, args):
        """Export performance metrics to file."""
        try:
            print(f"Exporting metrics to {args.output}...")
            
            summary = await get_performance_summary()
            
            # Add timestamp
            summary['export_timestamp'] = datetime.utcnow().isoformat()
            summary['export_format'] = 'json'
            
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            print(f"✅ Metrics exported to {args.output}")
            return 0
            
        except Exception as e:
            print(f"❌ Failed to export metrics: {e}")
            logger.error("Metrics export failed", error=str(e))
            return 1


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RegulensAI Application Performance Monitoring Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --test --status
  %(prog)s status
  %(prog)s database
  %(prog)s errors
  %(prog)s test --count 100
  %(prog)s export --output metrics.json
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start APM system")
    start_parser.add_argument("--test", action="store_true", help="Run test after starting")
    start_parser.add_argument("--status", action="store_true", help="Show status after starting")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop APM system")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show APM system status")
    
    # Database performance command
    db_parser = subparsers.add_parser("database", help="Show database performance")
    
    # Error analysis command
    error_parser = subparsers.add_parser("errors", help="Show error analysis")
    
    # Resource metrics command
    resource_parser = subparsers.add_parser("resources", help="Show resource metrics")
    
    # Performance test command
    test_parser = subparsers.add_parser("test", help="Run performance test")
    test_parser.add_argument("--count", "-c", type=int, default=50, help="Number of test operations")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export metrics to file")
    export_parser.add_argument("--output", "-o", default="apm_metrics.json", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = APMManagerCLI()
    
    # Execute command
    if args.command == "start":
        return await cli.start_apm(args)
    elif args.command == "stop":
        return await cli.stop_apm(args)
    elif args.command == "status":
        return await cli.show_status(args)
    elif args.command == "database":
        return await cli.show_database_performance(args)
    elif args.command == "errors":
        return await cli.show_error_analysis(args)
    elif args.command == "resources":
        return await cli.show_resource_metrics(args)
    elif args.command == "test":
        return await cli.run_performance_test(args)
    elif args.command == "export":
        return await cli.export_metrics(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
