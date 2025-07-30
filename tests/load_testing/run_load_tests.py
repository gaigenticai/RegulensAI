#!/usr/bin/env python3
"""
RegulensAI Load Testing Runner
Automated load testing execution with scenario management and reporting.
"""

import argparse
import json
import subprocess
import sys
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
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


class LoadTestRunner:
    """
    Load testing runner with scenario management and reporting.
    """
    
    def __init__(self, config_path: str = None):
        self.base_dir = Path(__file__).parent
        self.config_path = config_path or self.base_dir / "config" / "scenarios.json"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Test execution tracking
        self.current_test = None
        self.test_results = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load test configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info("Configuration loaded", config_path=str(self.config_path))
            return config
        except Exception as e:
            logger.error("Failed to load configuration", error=str(e))
            raise
    
    def list_scenarios(self):
        """List available test scenarios."""
        print("Available Load Test Scenarios:")
        print("=" * 50)
        
        for name, scenario in self.config["scenarios"].items():
            print(f"\n{name}:")
            print(f"  Description: {scenario['description']}")
            print(f"  Users: {scenario['users']}")
            print(f"  Duration: {scenario['run_time']}")
            print(f"  User Classes: {', '.join(scenario['user_classes'])}")
            print(f"  Tags: {', '.join(scenario['tags'])}")
    
    def run_scenario(self, scenario_name: str, environment: str = "local", **kwargs) -> Dict[str, Any]:
        """
        Run a specific load test scenario.
        
        Args:
            scenario_name: Name of the scenario to run
            environment: Target environment (local, staging, production)
            **kwargs: Override scenario parameters
            
        Returns:
            Dict containing test results and metadata
        """
        if scenario_name not in self.config["scenarios"]:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        scenario = self.config["scenarios"][scenario_name].copy()
        env_config = self.config["environments"].get(environment, {})
        
        # Override with environment and kwargs
        if env_config.get("host"):
            scenario["host"] = env_config["host"]
        
        for key, value in kwargs.items():
            if value is not None:
                scenario[key] = value
        
        logger.info("Starting load test", 
                   scenario=scenario_name, 
                   environment=environment,
                   config=scenario)
        
        # Prepare test execution
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_id = f"{scenario_name}_{environment}_{timestamp}"
        results_file = self.results_dir / f"{test_id}_results.csv"
        log_file = self.results_dir / f"{test_id}_log.txt"
        
        # Build locust command
        cmd = self._build_locust_command(scenario, results_file, log_file)
        
        # Execute test
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=self._get_timeout(scenario["run_time"])
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Process results
            test_result = {
                "test_id": test_id,
                "scenario": scenario_name,
                "environment": environment,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "duration": duration,
                "success": result.returncode == 0,
                "command": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "results_file": str(results_file),
                "log_file": str(log_file)
            }
            
            # Parse performance metrics if available
            if results_file.exists():
                test_result["metrics"] = self._parse_results(results_file)
            
            self.test_results.append(test_result)
            
            if test_result["success"]:
                logger.info("Load test completed successfully", 
                           test_id=test_id, 
                           duration=duration)
            else:
                logger.error("Load test failed", 
                            test_id=test_id, 
                            error=result.stderr)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            logger.error("Load test timed out", test_id=test_id)
            return {
                "test_id": test_id,
                "scenario": scenario_name,
                "environment": environment,
                "success": False,
                "error": "Test execution timed out"
            }
        except Exception as e:
            logger.error("Load test execution failed", test_id=test_id, error=str(e))
            return {
                "test_id": test_id,
                "scenario": scenario_name,
                "environment": environment,
                "success": False,
                "error": str(e)
            }
    
    def _build_locust_command(self, scenario: Dict[str, Any], results_file: Path, log_file: Path) -> List[str]:
        """Build locust command from scenario configuration."""
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--host", scenario["host"],
            "--users", str(scenario["users"]),
            "--spawn-rate", str(scenario["spawn_rate"]),
            "--run-time", scenario["run_time"],
            "--headless",
            "--csv", str(results_file.with_suffix("")),
            "--logfile", str(log_file),
            "--loglevel", "INFO"
        ]
        
        # Add user classes if specified
        if "user_classes" in scenario and scenario["user_classes"]:
            for user_class in scenario["user_classes"]:
                cmd.extend(["--class-picker", user_class])
        
        return cmd
    
    def _get_timeout(self, run_time: str) -> int:
        """Convert run_time string to timeout seconds."""
        if run_time.endswith('s'):
            return int(run_time[:-1]) + 60  # Add 60s buffer
        elif run_time.endswith('m'):
            return int(run_time[:-1]) * 60 + 120  # Add 2min buffer
        elif run_time.endswith('h'):
            return int(run_time[:-1]) * 3600 + 300  # Add 5min buffer
        else:
            return 600  # Default 10min timeout
    
    def _parse_results(self, results_file: Path) -> Dict[str, Any]:
        """Parse locust results CSV file."""
        try:
            import pandas as pd
            
            # Read the stats CSV file
            stats_file = results_file.parent / f"{results_file.stem}_stats.csv"
            if stats_file.exists():
                df = pd.read_csv(stats_file)
                
                # Calculate key metrics
                metrics = {
                    "total_requests": df["Request Count"].sum(),
                    "total_failures": df["Failure Count"].sum(),
                    "average_response_time": df["Average Response Time"].mean(),
                    "min_response_time": df["Min Response Time"].min(),
                    "max_response_time": df["Max Response Time"].max(),
                    "requests_per_second": df["Requests/s"].mean(),
                    "failure_rate": (df["Failure Count"].sum() / df["Request Count"].sum()) * 100 if df["Request Count"].sum() > 0 else 0
                }
                
                return metrics
        except Exception as e:
            logger.warning("Failed to parse results", error=str(e))
        
        return {}
    
    def run_test_suite(self, suite_name: str = "default", environment: str = "local") -> List[Dict[str, Any]]:
        """
        Run a predefined test suite.
        
        Args:
            suite_name: Name of the test suite
            environment: Target environment
            
        Returns:
            List of test results
        """
        suites = {
            "smoke": ["smoke_test"],
            "regression": ["smoke_test", "load_test", "api_focused"],
            "performance": ["load_test", "stress_test", "database_intensive"],
            "full": ["smoke_test", "load_test", "stress_test", "spike_test", "endurance_test"],
            "default": ["smoke_test", "load_test"]
        }
        
        if suite_name not in suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
        
        scenarios = suites[suite_name]
        results = []
        
        logger.info("Starting test suite", suite=suite_name, scenarios=scenarios)
        
        for scenario in scenarios:
            logger.info("Running scenario", scenario=scenario)
            result = self.run_scenario(scenario, environment)
            results.append(result)
            
            # Brief pause between tests
            time.sleep(10)
        
        logger.info("Test suite completed", suite=suite_name, total_tests=len(results))
        return results
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate test report from results."""
        if not self.test_results:
            return "No test results available"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_file or self.results_dir / f"load_test_report_{timestamp}.html"
        
        # Generate HTML report
        html_content = self._generate_html_report()
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        logger.info("Test report generated", report_file=str(report_file))
        return str(report_file)
    
    def _generate_html_report(self) -> str:
        """Generate HTML report content."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>RegulensAI Load Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .test-result { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .success { background-color: #d4edda; border-color: #c3e6cb; }
                .failure { background-color: #f8d7da; border-color: #f5c6cb; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
                .metric { background-color: #f8f9fa; padding: 10px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>RegulensAI Load Test Report</h1>
                <p>Generated: {timestamp}</p>
                <p>Total Tests: {total_tests}</p>
            </div>
        """.format(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.test_results)
        )
        
        for result in self.test_results:
            status_class = "success" if result["success"] else "failure"
            html += f"""
            <div class="test-result {status_class}">
                <h3>{result['scenario']} - {result['environment']}</h3>
                <p><strong>Test ID:</strong> {result['test_id']}</p>
                <p><strong>Duration:</strong> {result.get('duration', 'N/A')} seconds</p>
                <p><strong>Status:</strong> {'SUCCESS' if result['success'] else 'FAILED'}</p>
            """
            
            if "metrics" in result:
                html += '<div class="metrics">'
                for key, value in result["metrics"].items():
                    html += f'<div class="metric"><strong>{key}:</strong> {value}</div>'
                html += '</div>'
            
            html += '</div>'
        
        html += """
        </body>
        </html>
        """
        
        return html


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RegulensAI Load Testing Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List scenarios command
    list_parser = subparsers.add_parser("list", help="List available scenarios")
    
    # Run scenario command
    run_parser = subparsers.add_parser("run", help="Run a specific scenario")
    run_parser.add_argument("scenario", help="Scenario name to run")
    run_parser.add_argument("--environment", "-e", default="local",
                           choices=["local", "staging", "production"],
                           help="Target environment")
    run_parser.add_argument("--users", "-u", type=int, help="Override number of users")
    run_parser.add_argument("--spawn-rate", "-r", type=int, help="Override spawn rate")
    run_parser.add_argument("--run-time", "-t", help="Override run time")
    
    # Run suite command
    suite_parser = subparsers.add_parser("suite", help="Run a test suite")
    suite_parser.add_argument("suite", default="default", nargs="?",
                             choices=["smoke", "regression", "performance", "full", "default"],
                             help="Test suite to run")
    suite_parser.add_argument("--environment", "-e", default="local",
                             choices=["local", "staging", "production"],
                             help="Target environment")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate test report")
    report_parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    runner = LoadTestRunner()
    
    try:
        if args.command == "list":
            runner.list_scenarios()
        
        elif args.command == "run":
            kwargs = {}
            if args.users:
                kwargs["users"] = args.users
            if args.spawn_rate:
                kwargs["spawn_rate"] = args.spawn_rate
            if args.run_time:
                kwargs["run_time"] = args.run_time
            
            result = runner.run_scenario(args.scenario, args.environment, **kwargs)
            
            if result["success"]:
                print(f"✅ Test completed successfully: {result['test_id']}")
                return 0
            else:
                print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
                return 1
        
        elif args.command == "suite":
            results = runner.run_test_suite(args.suite, args.environment)
            
            successful = sum(1 for r in results if r["success"])
            total = len(results)
            
            print(f"Test suite completed: {successful}/{total} tests passed")
            
            if successful == total:
                print("✅ All tests passed")
                return 0
            else:
                print("❌ Some tests failed")
                return 1
        
        elif args.command == "report":
            report_file = runner.generate_report(args.output)
            print(f"Report generated: {report_file}")
            return 0
        
    except Exception as e:
        logger.error("Command execution failed", command=args.command, error=str(e))
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
