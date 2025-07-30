#!/usr/bin/env python3
"""
RegulensAI Disaster Recovery Manager CLI
Command-line interface for managing disaster recovery procedures, testing, and monitoring.
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

from core_infra.disaster_recovery.dr_manager import (
    dr_manager,
    init_disaster_recovery,
    shutdown_disaster_recovery,
    get_dr_status,
    run_dr_test,
    run_full_dr_test,
    DRTestType
)
from core_infra.config import get_settings
import structlog
import logging

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


class DRManagerCLI:
    """Command-line interface for disaster recovery management."""
    
    def __init__(self):
        self.settings = get_settings()
logger = structlog.get_logger(__name__)
    
    async def start_dr(self, args):
        """Start the disaster recovery system."""
        try:
            logger.info("Starting disaster recovery system...")
            
            await init_disaster_recovery()
            
            logger.info("Disaster recovery system started successfully!")
            
            # Show status if requested
            if args.status:
                await self.show_status(args)
            
            # Run test if requested
            if args.test:
                await self.run_test_suite(args)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to start DR system: {e}")
            logger.error("DR system startup failed", error=str(e))
            return 1
    
    async def stop_dr(self, args):
        """Stop the disaster recovery system."""
        try:
            logger.info("Stopping disaster recovery system...")
            
            await shutdown_disaster_recovery()
            
            logger.info("Disaster recovery system stopped successfully!")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to stop DR system: {e}")
            logger.error("DR system shutdown failed", error=str(e))
            return 1
    
    async def show_status(self, args):
        """Show comprehensive DR status."""
        try:
                    logger.info("RegulensAI Disaster Recovery Status")
        logger.info("=" * 50)
            
            status = await get_dr_status()
            
            # Overall status
                    logger.info(f"Overall Status: {status['overall_status'].upper()}")
        logger.info(f"Health Score: {status['health_score']:.1f}/100")
        logger.info(f"Last Updated: {status['last_updated']}")
            
            # Component status
            logger.info("Component Status:")
            component_data = []
            headers = ['Component', 'Status', 'Priority', 'RTO', 'RPO', 'Last Test', 'Auto Recovery']
            
            for comp_name, comp_data in status['components'].items():
                component_data.append([
                    comp_name.replace('_', ' ').title(),
                    comp_data['status'].upper(),
                    comp_data['priority'],
                    f"{comp_data['rto_minutes']}m",
                    f"{comp_data['rpo_minutes']}m",
                    self._format_time(comp_data['last_test_time']),
                    "Yes" if comp_data['automated_recovery'] else "No"
                ])
            
            logger.info("\n" + tabulate.tabulate(component_data, headers=headers, tablefmt='grid'))
            
            # Recent events
            if status['recent_events']:
                logger.info("Recent Events (Last 10):")
                event_data = []
                event_headers = ['Time', 'Component', 'Type', 'Severity', 'Description']
                
                for event in status['recent_events'][:10]:
                    event_data.append([
                        self._format_time(event['timestamp']),
                        event['component'],
                        event['event_type'],
                        event['severity'].upper(),
                        event['description'][:50] + '...' if len(event['description']) > 50 else event['description']
                    ])
                
                logger.info("\n" + tabulate.tabulate(event_data, headers=event_headers, tablefmt='grid'))
            
            # Recent tests
            if status['recent_tests']:
                logger.info("Recent Tests (Last 5):")
                test_data = []
                test_headers = ['Component', 'Test Type', 'Status', 'Duration', 'RTO Met', 'RPO Met']
                
                for test in status['recent_tests'][:5]:
                    test_data.append([
                        test['component'],
                        test['test_type'],
                        test['status'].upper(),
                        f"{test['duration_minutes']:.1f}m" if test['duration_minutes'] else 'N/A',
                        "✓" if test['rto_achieved'] else "✗" if test['rto_achieved'] is False else 'N/A',
                        "✓" if test['rpo_achieved'] else "✗" if test['rpo_achieved'] is False else 'N/A'
                    ])
                
                logger.info("\n" + tabulate.tabulate(test_data, headers=test_headers, tablefmt='grid'))
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get DR status: {e}")
            logger.error("DR status check failed", error=str(e))
            return 1
    
    async def run_component_test(self, args):
        """Run DR test for specific component."""
        try:
            logger.info(f"Running {args.test_type} test for {args.component}...")
            
            result = await run_dr_test(args.component, args.test_type, args.dry_run)
            
                    logger.info("Test Results:")
        logger.info(f"Test ID: {result.test_id}")
        logger.info(f"Component: {result.component}")
        logger.info(f"Test Type: {result.test_type}")
        logger.info(f"Status: {result.status.upper()}")
        logger.info(f"Duration: {result.duration_minutes:.2f} minutes")
            
            if result.rto_achieved is not None:
                logger.info(f"RTO Achieved: {'Yes' if result.rto_achieved else 'No'}")
            
            if result.rpo_achieved is not None:
                logger.info(f"RPO Achieved: {'Yes' if result.rpo_achieved else 'No'}")
            
            # Validation results
            if result.validation_results:
                logger.info("Validation Results:")
                for check, passed in result.validation_results.items():
                    status = "✓ PASS" if passed else "✗ FAIL"
                    logger.info(f"  {check}: {status}")
            
            # Error messages
            if result.error_messages:
                logger.error("Errors:")
                for error in result.error_messages:
                    logger.error(f"  - {error}")
            
            # Recommendations
            if result.recommendations:
                logger.info("Recommendations:")
                for rec in result.recommendations:
                    logger.info(f"  - {rec}")
            
            return 0 if result.status == "passed" else 1
            
        except Exception as e:
            logger.error(f"Failed to run component test: {e}")
            logger.error("Component test failed", error=str(e))
            return 1
    
    async def run_full_test(self, args):
        """Run full DR test suite."""
        try:
                    logger.info("Running full disaster recovery test suite...")
        logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE TEST'}")
            
            results = await run_full_dr_test(args.dry_run)
            
            # Summary
            total_tests = len(results)
            passed_tests = sum(1 for r in results.values() if r.status == "passed")
            failed_tests = total_tests - passed_tests
            
                    logger.info("Full DR Test Summary:")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
            
            # Detailed results
            logger.info("Detailed Results:")
            result_data = []
            headers = ['Test', 'Component', 'Status', 'Duration', 'RTO', 'RPO']
            
            for test_name, result in results.items():
                result_data.append([
                    result.test_type,
                    result.component,
                    result.status.upper(),
                    f"{result.duration_minutes:.1f}m" if result.duration_minutes else 'N/A',
                    "✓" if result.rto_achieved else "✗" if result.rto_achieved is False else 'N/A',
                    "✓" if result.rpo_achieved else "✗" if result.rpo_achieved is False else 'N/A'
                ])
            
            logger.info("\n" + tabulate.tabulate(result_data, headers=headers, tablefmt='grid'))
            
            # Failed tests details
            failed_results = [r for r in results.values() if r.status == "failed"]
            if failed_results:
                logger.error("Failed Tests Details:")
                for result in failed_results:
                    logger.error(f"{result.component} - {result.test_type}:")
                    for error in result.error_messages:
                        logger.error(f"  - {error}")
                    for rec in result.recommendations:
                        logger.info(f"  Recommendation: {rec}")
            
            return 0 if failed_tests == 0 else 1
            
        except Exception as e:
            logger.error(f"Failed to run full DR test: {e}")
            logger.error("Full DR test failed", error=str(e))
            return 1
    
    async def run_test_suite(self, args):
        """Run automated test suite."""
        try:
            logger.info("Running automated DR test suite...")
            
            # Run backup validation for all components
            components = ['database', 'api_services', 'web_ui', 'monitoring', 'file_storage']
            
            for component in components:
                logger.info(f"Testing {component}...")
                
                # Backup validation
                backup_result = await run_dr_test(component, 'backup_validation', True)
                status = "✓" if backup_result.status == "passed" else "✗"
                logger.info(f"  Backup Validation: {status}")
                
                # Failover test (dry run only)
                failover_result = await run_dr_test(component, 'failover_test', True)
                status = "✓" if failover_result.status == "passed" else "✗"
                logger.info(f"  Failover Test: {status}")
            
            logger.info("Automated test suite completed!")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to run test suite: {e}")
            logger.error("Test suite failed", error=str(e))
            return 1
    
    async def export_status(self, args):
        """Export DR status to file."""
        try:
            logger.info(f"Exporting DR status to {args.output}...")
            
            status = await get_dr_status()
            
            # Add export metadata
            status['export_timestamp'] = datetime.utcnow().isoformat()
            status['export_format'] = 'json'
            
            with open(args.output, 'w') as f:
                json.dump(status, f, indent=2, default=str)
            
            logger.info(f"DR status exported to {args.output}")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to export status: {e}")
            logger.error("Status export failed", error=str(e))
            return 1
    
    def _format_time(self, time_str: Optional[str]) -> str:
        """Format timestamp for display."""
        if not time_str:
            return "Never"
        
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=dt.tzinfo)
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "Just now"
        except:
            return time_str


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RegulensAI Disaster Recovery Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --test --status
  %(prog)s status
  %(prog)s test database backup_validation --dry-run
  %(prog)s full-test --dry-run
  %(prog)s export --output dr_status.json
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start DR system")
    start_parser.add_argument("--test", action="store_true", help="Run test suite after starting")
    start_parser.add_argument("--status", action="store_true", help="Show status after starting")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop DR system")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show DR system status")
    
    # Component test command
    test_parser = subparsers.add_parser("test", help="Run component DR test")
    test_parser.add_argument("component", help="Component to test")
    test_parser.add_argument("test_type", help="Type of test to run")
    test_parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode")
    test_parser.add_argument("--live", action="store_true", help="Run live test (overrides dry-run)")
    
    # Full test command
    full_test_parser = subparsers.add_parser("full-test", help="Run full DR test suite")
    full_test_parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode")
    full_test_parser.add_argument("--live", action="store_true", help="Run live test (overrides dry-run)")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export DR status to file")
    export_parser.add_argument("--output", "-o", default="dr_status.json", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle live test override
    if hasattr(args, 'live') and args.live:
        args.dry_run = False
    
    cli = DRManagerCLI()
    
    # Execute command
    if args.command == "start":
        return await cli.start_dr(args)
    elif args.command == "stop":
        return await cli.stop_dr(args)
    elif args.command == "status":
        return await cli.show_status(args)
    elif args.command == "test":
        return await cli.run_component_test(args)
    elif args.command == "full-test":
        return await cli.run_full_test(args)
    elif args.command == "export":
        return await cli.export_status(args)
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
