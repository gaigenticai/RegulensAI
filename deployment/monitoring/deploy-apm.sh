#!/bin/bash
# RegulensAI APM System Deployment Script
# Enterprise-grade Application Performance Monitoring deployment with health checks and configuration

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment variables with defaults
ENVIRONMENT="${ENVIRONMENT:-production}"
APM_PROVIDER="${APM_PROVIDER:-custom}"
ELASTIC_APM_SERVER_URL="${ELASTIC_APM_SERVER_URL:-http://localhost:8200}"
ELASTIC_APM_SECRET_TOKEN="${ELASTIC_APM_SECRET_TOKEN:-}"
NEWRELIC_LICENSE_KEY="${NEWRELIC_LICENSE_KEY:-}"
DATADOG_API_KEY="${DATADOG_API_KEY:-}"

# Deployment configuration
DEPLOYMENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${DEPLOYMENT_DIR}/apm_deployment.log"
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=10  # 10 seconds

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

check_prerequisites() {
    log "Checking APM deployment prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed"
        exit 1
    fi
    
    # Check if RegulensAI is installed
    if ! python3 -c "import core_infra.monitoring.apm_integration" &> /dev/null; then
        log_error "RegulensAI APM module not found. Please install RegulensAI first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

install_apm_dependencies() {
    log "Installing APM dependencies..."
    
    # Install base dependencies
    pip3 install psutil tabulate
    
    # Install APM provider dependencies based on configuration
    case "$APM_PROVIDER" in
        "elastic_apm")
            log "Installing Elastic APM..."
            pip3 install elastic-apm
            ;;
        "newrelic")
            log "Installing New Relic..."
            pip3 install newrelic
            ;;
        "datadog")
            log "Installing Datadog..."
            pip3 install ddtrace
            ;;
        "all")
            log "Installing all APM providers..."
            pip3 install elastic-apm newrelic ddtrace
            ;;
        "custom")
            log "Using custom APM provider only"
            ;;
        *)
            log_error "Unknown APM provider: $APM_PROVIDER"
            exit 1
            ;;
    esac
    
    log_success "APM dependencies installed"
}

configure_apm_providers() {
    log "Configuring APM providers..."
    
    # Create APM configuration directory
    mkdir -p "${DEPLOYMENT_DIR}/config"
    
    # Generate APM configuration file
    cat > "${DEPLOYMENT_DIR}/config/apm_config.env" << EOF
# RegulensAI APM Configuration
ENVIRONMENT=${ENVIRONMENT}

# Performance Monitoring
PERFORMANCE_MONITORING_ENABLED=true
PERFORMANCE_BASELINE_UPDATE_INTERVAL=3600
PERFORMANCE_REGRESSION_THRESHOLD=20.0

# Database Performance Monitoring
DB_PERFORMANCE_MONITORING_ENABLED=true
DB_SLOW_QUERY_THRESHOLD=1.0
DB_QUERY_SAMPLING_RATE=1.0

# Error Tracking
ERROR_TRACKING_ENABLED=true
ERROR_RATE_ALERT_THRESHOLD=10.0
ERROR_AGGREGATION_WINDOW=300

# Resource Monitoring
RESOURCE_MONITORING_ENABLED=true
RESOURCE_MONITORING_INTERVAL=30
CPU_USAGE_ALERT_THRESHOLD=80.0
MEMORY_USAGE_ALERT_THRESHOLD=85.0

# Business Metrics
BUSINESS_METRICS_ENABLED=true
COMPLIANCE_PROCESSING_TIME_THRESHOLD=30.0
REGULATORY_INGESTION_RATE_THRESHOLD=100.0
EOF

    # Configure Elastic APM if enabled
    if [[ "$APM_PROVIDER" == "elastic_apm" || "$APM_PROVIDER" == "all" ]]; then
        cat >> "${DEPLOYMENT_DIR}/config/apm_config.env" << EOF

# Elastic APM Configuration
ELASTIC_APM_ENABLED=true
ELASTIC_APM_SERVICE_NAME=regulensai
ELASTIC_APM_SERVER_URL=${ELASTIC_APM_SERVER_URL}
ELASTIC_APM_SECRET_TOKEN=${ELASTIC_APM_SECRET_TOKEN}
ELASTIC_APM_SAMPLE_RATE=1.0
EOF
    fi
    
    # Configure New Relic if enabled
    if [[ "$APM_PROVIDER" == "newrelic" || "$APM_PROVIDER" == "all" ]]; then
        cat >> "${DEPLOYMENT_DIR}/config/apm_config.env" << EOF

# New Relic Configuration
NEWRELIC_ENABLED=true
NEWRELIC_LICENSE_KEY=${NEWRELIC_LICENSE_KEY}
EOF
        
        # Create New Relic configuration file
        cat > "${DEPLOYMENT_DIR}/config/newrelic.ini" << EOF
[newrelic]
license_key = ${NEWRELIC_LICENSE_KEY}
app_name = RegulensAI (${ENVIRONMENT})
monitor_mode = true
log_file = /var/log/regulensai/newrelic-agent.log
log_level = info
EOF
    fi
    
    # Configure Datadog if enabled
    if [[ "$APM_PROVIDER" == "datadog" || "$APM_PROVIDER" == "all" ]]; then
        cat >> "${DEPLOYMENT_DIR}/config/apm_config.env" << EOF

# Datadog Configuration
DATADOG_APM_ENABLED=true
DATADOG_SERVICE_NAME=regulensai
DATADOG_API_KEY=${DATADOG_API_KEY}
EOF
    fi
    
    log_success "APM providers configured"
}

setup_grafana_dashboards() {
    log "Setting up Grafana dashboards..."
    
    # Check if Grafana is available
    if curl -f http://localhost:3000/api/health &> /dev/null; then
        log "Grafana detected, importing APM dashboard..."
        
        # Import APM dashboard
        curl -X POST \
            -H "Content-Type: application/json" \
            -d @"${DEPLOYMENT_DIR}/grafana/dashboards/apm-dashboard.json" \
            http://admin:admin@localhost:3000/api/dashboards/db || log_error "Failed to import APM dashboard"
        
        log_success "Grafana dashboards configured"
    else
        log "Grafana not available, skipping dashboard setup"
    fi
}

start_apm_system() {
    log "Starting APM system..."
    
    # Source APM configuration
    if [[ -f "${DEPLOYMENT_DIR}/config/apm_config.env" ]]; then
        set -a
        source "${DEPLOYMENT_DIR}/config/apm_config.env"
        set +a
    fi
    
    # Start APM system using the CLI
    python3 -m scripts.apm_manager start --test || {
        log_error "Failed to start APM system"
        return 1
    }
    
    log_success "APM system started"
}

run_health_checks() {
    log "Running APM health checks..."
    
    local all_healthy=true
    
    # Check APM system status
    if ! python3 -m scripts.apm_manager status &> /dev/null; then
        log_error "APM system health check failed"
        all_healthy=false
    else
        log_success "APM system is healthy"
    fi
    
    # Check resource monitoring
    if ! python3 -m scripts.apm_manager resources &> /dev/null; then
        log_error "Resource monitoring health check failed"
        all_healthy=false
    else
        log_success "Resource monitoring is healthy"
    fi
    
    # Check database performance monitoring
    if ! python3 -m scripts.apm_manager database &> /dev/null; then
        log_error "Database performance monitoring health check failed"
        all_healthy=false
    else
        log_success "Database performance monitoring is healthy"
    fi
    
    # Check error tracking
    if ! python3 -m scripts.apm_manager errors &> /dev/null; then
        log_error "Error tracking health check failed"
        all_healthy=false
    else
        log_success "Error tracking is healthy"
    fi
    
    if [[ "$all_healthy" == true ]]; then
        log_success "All APM health checks passed"
        return 0
    else
        log_error "Some APM health checks failed"
        return 1
    fi
}

run_performance_test() {
    log "Running APM performance test..."
    
    # Run performance test to generate sample metrics
    python3 -m scripts.apm_manager test --count 100 || {
        log_error "APM performance test failed"
        return 1
    }
    
    log_success "APM performance test completed"
}

generate_apm_report() {
    log "Generating APM deployment report..."
    
    # Export current metrics
    python3 -m scripts.apm_manager export --output "${DEPLOYMENT_DIR}/apm_deployment_report.json" || {
        log_error "Failed to generate APM report"
        return 1
    }
    
    # Create summary report
    cat > "${DEPLOYMENT_DIR}/apm_deployment_summary.txt" << EOF
RegulensAI APM Deployment Summary
================================

Deployment Date: $(date)
Environment: ${ENVIRONMENT}
APM Provider: ${APM_PROVIDER}

Configuration:
- Performance Monitoring: Enabled
- Database Monitoring: Enabled
- Error Tracking: Enabled
- Resource Monitoring: Enabled
- Business Metrics: Enabled

Health Checks: $(if run_health_checks &> /dev/null; then echo "PASSED"; else echo "FAILED"; fi)

Access URLs:
- APM CLI: python3 -m scripts.apm_manager status
- Grafana Dashboard: http://localhost:3000/d/apm-dashboard
- Metrics Export: ${DEPLOYMENT_DIR}/apm_deployment_report.json

Next Steps:
1. Monitor APM dashboard for performance insights
2. Set up alerting rules for performance regressions
3. Configure business metric thresholds
4. Review and optimize slow queries
5. Set up automated performance testing

EOF
    
    log_success "APM deployment report generated"
}

# ============================================================================
# MAIN DEPLOYMENT PROCESS
# ============================================================================

main() {
    log "Starting RegulensAI APM system deployment"
    log "Environment: $ENVIRONMENT"
    log "APM Provider: $APM_PROVIDER"
    log "Deployment directory: $DEPLOYMENT_DIR"
    
    # Execute deployment steps
    check_prerequisites
    install_apm_dependencies
    configure_apm_providers
    setup_grafana_dashboards
    start_apm_system
    
    # Run health checks
    if run_health_checks; then
        # Run performance test
        run_performance_test
        
        # Generate deployment report
        generate_apm_report
        
        log_success "APM system deployment completed successfully!"
        
        echo ""
        echo "🎉 RegulensAI APM System is now ready!"
        echo ""
        echo "APM Provider: $APM_PROVIDER"
        echo "Environment: $ENVIRONMENT"
        echo ""
        echo "Management Commands:"
        echo "  Status: python3 -m scripts.apm_manager status"
        echo "  Database: python3 -m scripts.apm_manager database"
        echo "  Errors: python3 -m scripts.apm_manager errors"
        echo "  Resources: python3 -m scripts.apm_manager resources"
        echo "  Test: python3 -m scripts.apm_manager test --count 50"
        echo ""
        echo "Monitoring:"
        echo "  Grafana Dashboard: http://localhost:3000/d/apm-dashboard"
        echo "  Configuration: ${DEPLOYMENT_DIR}/config/apm_config.env"
        echo "  Deployment Report: ${DEPLOYMENT_DIR}/apm_deployment_summary.txt"
        echo ""
        
        return 0
    else
        log_error "APM system deployment failed health checks"
        return 1
    fi
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "RegulensAI APM System Deployment Script"
        echo "Usage: $0 [--help|--status|--test|--stop]"
        echo ""
        echo "Environment Variables:"
        echo "  ENVIRONMENT           - Deployment environment (default: production)"
        echo "  APM_PROVIDER          - APM provider (custom|elastic_apm|newrelic|datadog|all)"
        echo "  ELASTIC_APM_SERVER_URL - Elastic APM server URL"
        echo "  ELASTIC_APM_SECRET_TOKEN - Elastic APM secret token"
        echo "  NEWRELIC_LICENSE_KEY  - New Relic license key"
        echo "  DATADOG_API_KEY       - Datadog API key"
        exit 0
        ;;
    --status)
        log "Checking APM system status..."
        python3 -m scripts.apm_manager status
        exit $?
        ;;
    --test)
        log "Running APM performance test..."
        python3 -m scripts.apm_manager test --count 100
        exit $?
        ;;
    --stop)
        log "Stopping APM system..."
        python3 -m scripts.apm_manager stop
        log_success "APM system stopped"
        exit 0
        ;;
esac

# Execute main function
main "$@"
