# RegulensAI Load Testing Makefile
# Convenient commands for running load tests

.PHONY: help list smoke load stress spike endurance api database monitoring suite-smoke suite-regression suite-performance suite-full report clean install

# Default target
help:
	@echo "RegulensAI Load Testing Commands"
	@echo "================================"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install load testing dependencies"
	@echo ""
	@echo "Individual Tests:"
	@echo "  smoke            Run smoke test (5 users, 1 min)"
	@echo "  load             Run load test (50 users, 5 min)"
	@echo "  stress           Run stress test (200 users, 10 min)"
	@echo "  spike            Run spike test (100 users, 3 min)"
	@echo "  endurance        Run endurance test (30 users, 30 min)"
	@echo "  api              Run API-focused test (60 users, 4 min)"
	@echo "  database         Run database-intensive test (40 users, 5 min)"
	@echo "  monitoring       Run monitoring system test (25 users, 3 min)"
	@echo ""
	@echo "Test Suites:"
	@echo "  suite-smoke      Run smoke test suite"
	@echo "  suite-regression Run regression test suite"
	@echo "  suite-performance Run performance test suite"
	@echo "  suite-full       Run full test suite"
	@echo ""
	@echo "Utilities:"
	@echo "  list             List all available scenarios"
	@echo "  report           Generate test report"
	@echo "  clean            Clean up test results"
	@echo ""
	@echo "Environment Variables:"
	@echo "  ENV=local|staging|production  Target environment (default: local)"
	@echo "  USERS=N                       Override number of users"
	@echo "  SPAWN_RATE=N                  Override spawn rate"
	@echo "  RUN_TIME=Xs|Xm|Xh            Override run time"

# Environment configuration
ENV ?= local
PYTHON ?= python3
RUNNER = $(PYTHON) run_load_tests.py

# Install dependencies
install:
	@echo "Installing load testing dependencies..."
	pip install locust pandas structlog
	@echo "Dependencies installed successfully"

# List available scenarios
list:
	@echo "Listing available load test scenarios..."
	$(RUNNER) list

# Individual test scenarios
smoke:
	@echo "Running smoke test..."
	$(RUNNER) run smoke_test --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

load:
	@echo "Running load test..."
	$(RUNNER) run load_test --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

stress:
	@echo "Running stress test..."
	$(RUNNER) run stress_test --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

spike:
	@echo "Running spike test..."
	$(RUNNER) run spike_test --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

endurance:
	@echo "Running endurance test..."
	$(RUNNER) run endurance_test --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

api:
	@echo "Running API-focused test..."
	$(RUNNER) run api_focused --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

database:
	@echo "Running database-intensive test..."
	$(RUNNER) run database_intensive --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

monitoring:
	@echo "Running monitoring system test..."
	$(RUNNER) run monitoring_test --environment $(ENV) $(if $(USERS),--users $(USERS)) $(if $(SPAWN_RATE),--spawn-rate $(SPAWN_RATE)) $(if $(RUN_TIME),--run-time $(RUN_TIME))

# Test suites
suite-smoke:
	@echo "Running smoke test suite..."
	$(RUNNER) suite smoke --environment $(ENV)

suite-regression:
	@echo "Running regression test suite..."
	$(RUNNER) suite regression --environment $(ENV)

suite-performance:
	@echo "Running performance test suite..."
	$(RUNNER) suite performance --environment $(ENV)

suite-full:
	@echo "Running full test suite..."
	$(RUNNER) suite full --environment $(ENV)

# Generate report
report:
	@echo "Generating test report..."
	$(RUNNER) report

# Clean up results
clean:
	@echo "Cleaning up test results..."
	rm -rf results/*.csv results/*.txt results/*.html
	@echo "Test results cleaned"

# Quick test commands with predefined parameters
quick-smoke:
	@echo "Running quick smoke test..."
	$(RUNNER) run smoke_test --environment $(ENV) --users 3 --spawn-rate 1 --run-time 30s

quick-load:
	@echo "Running quick load test..."
	$(RUNNER) run load_test --environment $(ENV) --users 20 --spawn-rate 5 --run-time 120s

# Development helpers
dev-test: quick-smoke
	@echo "Development test completed"

ci-test: suite-smoke
	@echo "CI test suite completed"

# Performance benchmarking
benchmark-api:
	@echo "Running API benchmark..."
	$(RUNNER) run api_focused --environment $(ENV) --users 100 --spawn-rate 10 --run-time 300s

benchmark-database:
	@echo "Running database benchmark..."
	$(RUNNER) run database_intensive --environment $(ENV) --users 50 --spawn-rate 5 --run-time 300s

benchmark-full:
	@echo "Running full system benchmark..."
	$(RUNNER) run stress_test --environment $(ENV) --users 150 --spawn-rate 15 --run-time 600s

# Monitoring and alerting tests
test-monitoring-alerts:
	@echo "Testing monitoring and alerting..."
	$(RUNNER) run monitoring_test --environment $(ENV) --users 30 --spawn-rate 10 --run-time 180s

# Backup system load testing
test-backup-load:
	@echo "Testing backup system under load..."
	$(RUNNER) run api_focused --environment $(ENV) --users 20 --spawn-rate 2 --run-time 300s

# Configuration validation load testing
test-config-validation:
	@echo "Testing configuration validation under load..."
	$(RUNNER) run api_focused --environment $(ENV) --users 15 --spawn-rate 3 --run-time 240s

# Help for specific scenarios
help-scenarios:
	@echo "Load Test Scenario Details"
	@echo "=========================="
	@echo ""
	@echo "smoke_test:"
	@echo "  Purpose: Basic functionality verification"
	@echo "  Users: 5, Duration: 1 min"
	@echo "  Use: Quick health check"
	@echo ""
	@echo "load_test:"
	@echo "  Purpose: Normal operational load simulation"
	@echo "  Users: 50, Duration: 5 min"
	@echo "  Use: Regular performance testing"
	@echo ""
	@echo "stress_test:"
	@echo "  Purpose: Find system breaking points"
	@echo "  Users: 200, Duration: 10 min"
	@echo "  Use: Capacity planning"
	@echo ""
	@echo "spike_test:"
	@echo "  Purpose: Sudden traffic increase simulation"
	@echo "  Users: 100, Duration: 3 min"
	@echo "  Use: Auto-scaling validation"
	@echo ""
	@echo "endurance_test:"
	@echo "  Purpose: Long-running stability testing"
	@echo "  Users: 30, Duration: 30 min"
	@echo "  Use: Memory leak detection"

# Environment-specific shortcuts
local: ENV=local
local: load

staging: ENV=staging
staging: smoke

production: ENV=production
production: quick-smoke

# Validation targets
validate-local:
	@echo "Validating local environment..."
	curl -f http://localhost:8000/health || (echo "Local server not running" && exit 1)
	@echo "Local environment validated"

validate-staging:
	@echo "Validating staging environment..."
	curl -f https://staging.regulens.ai/health || (echo "Staging server not accessible" && exit 1)
	@echo "Staging environment validated"

# Combined validation and testing
test-local: validate-local quick-smoke
test-staging: validate-staging smoke
test-production: validate-production quick-smoke

# Documentation
docs:
	@echo "Load Testing Documentation"
	@echo "========================="
	@echo ""
	@echo "Configuration: config/scenarios.json"
	@echo "Results: results/"
	@echo "Logs: results/*_log.txt"
	@echo "Reports: results/*_report.html"
	@echo ""
	@echo "For detailed usage, run: make help"
