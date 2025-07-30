"""
Tests for RegulensAI Load Testing Framework
Comprehensive testing of load testing configuration, execution, and reporting.
"""

import pytest
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import load testing components
from tests.load_testing.run_load_tests import LoadTestRunner


class TestLoadTestRunner:
    """Test load test runner functionality."""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration for testing."""
        config = {
            "scenarios": {
                "test_scenario": {
                    "description": "Test scenario",
                    "users": 10,
                    "spawn_rate": 2,
                    "run_time": "60s",
                    "host": "http://localhost:8000",
                    "user_classes": ["APILoadTestUser"],
                    "tags": ["test"]
                }
            },
            "environments": {
                "test": {
                    "host": "http://test.example.com",
                    "description": "Test environment"
                }
            },
            "performance_thresholds": {
                "response_time": {"p50": 500, "p95": 2000, "p99": 5000},
                "error_rate": {"max_percentage": 1.0},
                "throughput": {"min_rps": 10}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name
        
        yield config_path
        
        # Cleanup
        Path(config_path).unlink()
    
    @pytest.fixture
    def load_test_runner(self, temp_config):
        """Create load test runner with temporary config."""
        return LoadTestRunner(config_path=temp_config)
    
    def test_load_test_runner_initialization(self, load_test_runner):
        """Test load test runner initialization."""
        assert load_test_runner.config is not None
        assert "scenarios" in load_test_runner.config
        assert "test_scenario" in load_test_runner.config["scenarios"]
        assert load_test_runner.results_dir.exists()
    
    def test_list_scenarios(self, load_test_runner, capsys):
        """Test scenario listing functionality."""
        load_test_runner.list_scenarios()
        
        captured = capsys.readouterr()
        assert "Available Load Test Scenarios" in captured.out
        assert "test_scenario" in captured.out
        assert "Test scenario" in captured.out
    
    def test_build_locust_command(self, load_test_runner):
        """Test locust command building."""
        scenario = {
            "host": "http://localhost:8000",
            "users": 10,
            "spawn_rate": 2,
            "run_time": "60s",
            "user_classes": ["APILoadTestUser"]
        }
        
        results_file = Path("/tmp/test_results.csv")
        log_file = Path("/tmp/test_log.txt")
        
        cmd = load_test_runner._build_locust_command(scenario, results_file, log_file)
        
        assert "locust" in cmd
        assert "-f" in cmd
        assert "locustfile.py" in cmd
        assert "--host" in cmd
        assert "http://localhost:8000" in cmd
        assert "--users" in cmd
        assert "10" in cmd
        assert "--spawn-rate" in cmd
        assert "2" in cmd
        assert "--run-time" in cmd
        assert "60s" in cmd
        assert "--headless" in cmd
    
    def test_get_timeout(self, load_test_runner):
        """Test timeout calculation."""
        assert load_test_runner._get_timeout("60s") == 120  # 60 + 60 buffer
        assert load_test_runner._get_timeout("5m") == 420   # 300 + 120 buffer
        assert load_test_runner._get_timeout("1h") == 3900  # 3600 + 300 buffer
        assert load_test_runner._get_timeout("invalid") == 600  # default
    
    @patch('subprocess.run')
    def test_run_scenario_success(self, mock_subprocess, load_test_runner):
        """Test successful scenario execution."""
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test completed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = load_test_runner.run_scenario("test_scenario", "test")
        
        assert result["success"] is True
        assert result["scenario"] == "test_scenario"
        assert result["environment"] == "test"
        assert "test_id" in result
        assert "start_time" in result
        assert "end_time" in result
        assert "duration" in result
    
    @patch('subprocess.run')
    def test_run_scenario_failure(self, mock_subprocess, load_test_runner):
        """Test failed scenario execution."""
        # Mock failed subprocess execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Test failed"
        mock_subprocess.return_value = mock_result
        
        result = load_test_runner.run_scenario("test_scenario", "test")
        
        assert result["success"] is False
        assert result["scenario"] == "test_scenario"
        assert result["environment"] == "test"
    
    @patch('subprocess.run')
    def test_run_scenario_timeout(self, mock_subprocess, load_test_runner):
        """Test scenario execution timeout."""
        # Mock timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("locust", 60)
        
        result = load_test_runner.run_scenario("test_scenario", "test")
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    def test_run_scenario_invalid(self, load_test_runner):
        """Test running invalid scenario."""
        with pytest.raises(ValueError, match="Scenario 'invalid' not found"):
            load_test_runner.run_scenario("invalid", "test")
    
    @patch('subprocess.run')
    def test_run_test_suite(self, mock_subprocess, load_test_runner):
        """Test test suite execution."""
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Add more scenarios to config for suite testing
        load_test_runner.config["scenarios"]["scenario2"] = {
            "description": "Second test scenario",
            "users": 5,
            "spawn_rate": 1,
            "run_time": "30s",
            "host": "http://localhost:8000",
            "user_classes": ["APILoadTestUser"],
            "tags": ["test"]
        }
        
        with patch.object(load_test_runner, 'run_scenario') as mock_run:
            mock_run.return_value = {"success": True, "test_id": "test_123"}
            
            # Test custom suite
            results = load_test_runner.run_test_suite("smoke", "test")
            
            assert len(results) > 0
            assert all(r["success"] for r in results)
    
    def test_run_test_suite_invalid(self, load_test_runner):
        """Test running invalid test suite."""
        with pytest.raises(ValueError, match="Test suite 'invalid' not found"):
            load_test_runner.run_test_suite("invalid", "test")
    
    def test_parse_results_no_file(self, load_test_runner):
        """Test result parsing with no file."""
        non_existent_file = Path("/tmp/non_existent_results.csv")
        metrics = load_test_runner._parse_results(non_existent_file)
        
        assert metrics == {}
    
    @patch('pandas.read_csv')
    def test_parse_results_with_data(self, mock_read_csv, load_test_runner):
        """Test result parsing with data."""
        # Mock pandas DataFrame
        mock_df = Mock()
        mock_df.__getitem__.side_effect = lambda key: {
            "Request Count": Mock(sum=lambda: 1000),
            "Failure Count": Mock(sum=lambda: 10),
            "Average Response Time": Mock(mean=lambda: 250.5),
            "Min Response Time": Mock(min=lambda: 50),
            "Max Response Time": Mock(max=lambda: 1000),
            "Requests/s": Mock(mean=lambda: 15.5)
        }[key]
        
        mock_read_csv.return_value = mock_df
        
        # Create a fake stats file
        results_file = Path("/tmp/test_results.csv")
        stats_file = results_file.parent / f"{results_file.stem}_stats.csv"
        
        with patch.object(stats_file, 'exists', return_value=True):
            metrics = load_test_runner._parse_results(results_file)
        
        assert "total_requests" in metrics
        assert "total_failures" in metrics
        assert "average_response_time" in metrics
        assert "failure_rate" in metrics
    
    def test_generate_html_report(self, load_test_runner):
        """Test HTML report generation."""
        # Add test results
        load_test_runner.test_results = [
            {
                "test_id": "test_123",
                "scenario": "test_scenario",
                "environment": "test",
                "success": True,
                "duration": 60.5,
                "metrics": {
                    "total_requests": 1000,
                    "failure_rate": 1.5,
                    "average_response_time": 250
                }
            }
        ]
        
        html_content = load_test_runner._generate_html_report()
        
        assert "RegulensAI Load Test Report" in html_content
        assert "test_123" in html_content
        assert "test_scenario" in html_content
        assert "SUCCESS" in html_content
        assert "total_requests" in html_content


class TestLoadTestConfiguration:
    """Test load test configuration management."""
    
    def test_scenarios_config_structure(self):
        """Test scenarios configuration file structure."""
        config_path = Path(__file__).parent / "load_testing" / "config" / "scenarios.json"
        
        assert config_path.exists()
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Verify required sections
        assert "scenarios" in config
        assert "environments" in config
        assert "performance_thresholds" in config
        assert "test_data" in config
        
        # Verify scenario structure
        for scenario_name, scenario in config["scenarios"].items():
            assert "description" in scenario
            assert "users" in scenario
            assert "spawn_rate" in scenario
            assert "run_time" in scenario
            assert "host" in scenario
            assert "user_classes" in scenario
            assert "tags" in scenario
        
        # Verify environment structure
        for env_name, env in config["environments"].items():
            assert "host" in env
            assert "description" in env
        
        # Verify thresholds structure
        thresholds = config["performance_thresholds"]
        assert "response_time" in thresholds
        assert "error_rate" in thresholds
        assert "throughput" in thresholds


class TestLoadTestScripts:
    """Test load test scripts and utilities."""
    
    def test_locustfile_exists(self):
        """Test that locustfile exists."""
        locustfile_path = Path(__file__).parent / "load_testing" / "locustfile.py"
        assert locustfile_path.exists()
    
    def test_locustfile_syntax(self):
        """Test locustfile syntax validity."""
        locustfile_path = Path(__file__).parent / "load_testing" / "locustfile.py"
        
        # Try to compile the file
        with open(locustfile_path, 'r') as f:
            content = f.read()
        
        try:
            compile(content, str(locustfile_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Locustfile has syntax errors: {e}")
    
    def test_run_load_tests_script_exists(self):
        """Test that run_load_tests.py script exists."""
        script_path = Path(__file__).parent / "load_testing" / "run_load_tests.py"
        assert script_path.exists()
    
    def test_run_load_tests_help(self):
        """Test run_load_tests.py help functionality."""
        script_path = Path(__file__).parent / "load_testing" / "run_load_tests.py"
        
        result = subprocess.run(
            ["python", str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "RegulensAI Load Testing Runner" in result.stdout
        assert "list" in result.stdout
        assert "run" in result.stdout
        assert "suite" in result.stdout
        assert "report" in result.stdout


class TestLoadTestIntegration:
    """Integration tests for load testing framework."""
    
    @pytest.mark.integration
    def test_smoke_test_execution(self):
        """Test smoke test execution (requires running server)."""
        # This test requires a running RegulensAI server
        # Skip if server is not available
        import requests
        
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code != 200:
                pytest.skip("RegulensAI server not available")
        except:
            pytest.skip("RegulensAI server not available")
        
        # Run actual smoke test
        runner = LoadTestRunner()
        
        # Override scenario for quick test
        result = runner.run_scenario(
            "smoke_test", 
            "local",
            users=2,
            spawn_rate=1,
            run_time="10s"
        )
        
        assert result["success"] is True
        assert "metrics" in result or "error" not in result
    
    @pytest.mark.integration
    def test_load_test_cli_integration(self):
        """Test CLI integration (requires running server)."""
        import requests
        
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code != 200:
                pytest.skip("RegulensAI server not available")
        except:
            pytest.skip("RegulensAI server not available")
        
        script_path = Path(__file__).parent / "load_testing" / "run_load_tests.py"
        
        # Test list command
        result = subprocess.run(
            ["python", str(script_path), "list"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Available Load Test Scenarios" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
