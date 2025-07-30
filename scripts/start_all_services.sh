#!/bin/bash
# RegulensAI Complete Service Startup Script
# Starts all RegulensAI services in the correct order with dependency management

set -euo pipefail

# ============================================================================
# CONFIGURATION AND GLOBALS
# ============================================================================

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/startup.log"
PID_FILE="${PROJECT_ROOT}/logs/startup.pid"

# Service configuration
STARTUP_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=5
HEALTH_CHECK_TIMEOUT=60
MAX_RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Service status tracking
declare -A SERVICE_STATUS
declare -A SERVICE_PIDS
declare -A SERVICE_PORTS

# ============================================================================
# LOGGING AND UTILITY FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_header() {
    echo -e "\n${WHITE}============================================================================${NC}"
    echo -e "${WHITE} $1${NC}"
    echo -e "${WHITE}============================================================================${NC}\n"
}

# ============================================================================
# PREREQUISITE CHECKS
# ============================================================================

check_prerequisites() {
    log_header "CHECKING PREREQUISITES"
    
    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root is not recommended for security reasons"
    fi
    
    # Check required directories
    log_info "Checking directory structure..."
    mkdir -p "${PROJECT_ROOT}/logs"
    mkdir -p "${PROJECT_ROOT}/data"
    mkdir -p "${PROJECT_ROOT}/backups"
    mkdir -p "${PROJECT_ROOT}/config"
    
    # Check required files
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        log_error "Environment file (.env) not found. Please create it from .env.example"
        exit 1
    fi
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check for docker-compose or docker compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check Python for management scripts
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check available disk space (minimum 10GB)
    available_space=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $available_space -lt 10 ]]; then
        log_warning "Low disk space: ${available_space}GB available (minimum 10GB recommended)"
    fi
    
    # Check available memory (minimum 4GB)
    available_memory=$(free -g | awk 'NR==2{print $7}')
    if [[ $available_memory -lt 4 ]]; then
        log_warning "Low available memory: ${available_memory}GB (minimum 4GB recommended)"
    fi
    
    log_success "Prerequisites check completed"
}

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

setup_environment() {
    log_header "SETTING UP ENVIRONMENT"
    
    # Source environment variables
    log_info "Loading environment variables..."
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
    
    # Create Docker network if it doesn't exist
    log_info "Setting up Docker network..."
    if ! docker network ls | grep -q "regulens-network"; then
        docker network create regulens-network
        log_success "Created regulens-network"
    else
        log_info "regulens-network already exists"
    fi
    
    # Set service ports
    SERVICE_PORTS[database]=${DATABASE_PORT:-5432}
    SERVICE_PORTS[redis]=${REDIS_PORT:-6379}
    SERVICE_PORTS[elasticsearch]=${ELASTICSEARCH_PORT:-9200}
    SERVICE_PORTS[kibana]=${KIBANA_PORT:-5601}
    SERVICE_PORTS[api]=${API_PORT:-8000}
    SERVICE_PORTS[ui]=${UI_PORT:-3000}
    SERVICE_PORTS[prometheus]=${PROMETHEUS_PORT:-9090}
    SERVICE_PORTS[grafana]=${GRAFANA_PORT:-3001}
    
    log_success "Environment setup completed"
}

# ============================================================================
# HEALTH CHECK FUNCTIONS
# ============================================================================

wait_for_service() {
    local service_name="$1"
    local port="$2"
    local timeout="${3:-$HEALTH_CHECK_TIMEOUT}"
    local host="${4:-localhost}"
    
    log_info "Waiting for $service_name on $host:$port..."
    
    local count=0
    while [[ $count -lt $timeout ]]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "$service_name is ready on $host:$port"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        count=$((count + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    
    log_error "$service_name failed to start within $timeout seconds"
    return 1
}

wait_for_http_service() {
    local service_name="$1"
    local url="$2"
    local timeout="${3:-$HEALTH_CHECK_TIMEOUT}"
    
    log_info "Waiting for $service_name at $url..."
    
    local count=0
    while [[ $count -lt $timeout ]]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready at $url"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        count=$((count + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    
    log_error "$service_name failed to respond within $timeout seconds"
    return 1
}

check_service_health() {
    local service_name="$1"
    
    case "$service_name" in
        "database")
            if [[ -n "${DATABASE_URL:-}" ]]; then
                # For external database (Supabase), check connectivity
                python3 -c "
import asyncpg
import asyncio
async def check():
    try:
        conn = await asyncpg.connect('$DATABASE_URL')
        await conn.fetchval('SELECT 1')
        await conn.close()
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
        exit(1)
asyncio.run(check())
" && return 0 || return 1
            else
                wait_for_service "Database" "${SERVICE_PORTS[database]}"
            fi
            ;;
        "redis")
            wait_for_service "Redis" "${SERVICE_PORTS[redis]}"
            ;;
        "elasticsearch")
            wait_for_http_service "Elasticsearch" "http://localhost:${SERVICE_PORTS[elasticsearch]}/_cluster/health"
            ;;
        "kibana")
            wait_for_http_service "Kibana" "http://localhost:${SERVICE_PORTS[kibana]}/api/status"
            ;;
        "api")
            wait_for_http_service "RegulensAI API" "http://localhost:${SERVICE_PORTS[api]}/v1/health"
            ;;
        "ui")
            wait_for_http_service "RegulensAI UI" "http://localhost:${SERVICE_PORTS[ui]}"
            ;;
        "prometheus")
            wait_for_http_service "Prometheus" "http://localhost:${SERVICE_PORTS[prometheus]}/-/ready"
            ;;
        "grafana")
            wait_for_http_service "Grafana" "http://localhost:${SERVICE_PORTS[grafana]}/api/health"
            ;;
        *)
            log_warning "Unknown service: $service_name"
            return 1
            ;;
    esac
}

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

initialize_database() {
    log_header "INITIALIZING DATABASE"
    
    # Check if database is accessible
    log_info "Checking database connectivity..."
    if ! check_service_health "database"; then
        log_error "Database is not accessible"
        return 1
    fi
    
    # Run database migrations
    log_info "Running database migrations..."
    cd "$PROJECT_ROOT"
    
    if python3 -m core_infra.database.migrate; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        return 1
    fi
    
    # Verify schema
    log_info "Verifying database schema..."
    if python3 -c "
from core_infra.config import DatabaseConfig
import asyncio
async def verify():
    valid, errors = await DatabaseConfig.validate_schema('$DATABASE_URL')
    if not valid:
        print('Schema validation errors:', errors)
        exit(1)
    print('Schema validation passed')
asyncio.run(verify())
"; then
        log_success "Database schema verification passed"
    else
        log_warning "Database schema verification failed, but continuing..."
    fi
    
    return 0
}

# ============================================================================
# SERVICE STARTUP FUNCTIONS
# ============================================================================

start_infrastructure_services() {
    log_header "STARTING INFRASTRUCTURE SERVICES"
    
    cd "$PROJECT_ROOT"
    
    # Start Redis
    log_info "Starting Redis..."
    $COMPOSE_CMD up -d redis
    if check_service_health "redis"; then
        SERVICE_STATUS[redis]="running"
        log_success "Redis started successfully"
    else
        SERVICE_STATUS[redis]="failed"
        log_error "Redis failed to start"
        return 1
    fi
    
    # Start Qdrant vector database
    log_info "Starting Qdrant vector database..."
    $COMPOSE_CMD up -d qdrant
    if wait_for_service "Qdrant" 6333; then
        SERVICE_STATUS[qdrant]="running"
        log_success "Qdrant started successfully"
    else
        SERVICE_STATUS[qdrant]="failed"
        log_error "Qdrant failed to start"
        return 1
    fi
    
    return 0
}

start_elk_stack() {
    log_header "STARTING ELK STACK (CENTRALIZED LOGGING)"
    
    cd "$PROJECT_ROOT"
    
    # Start Elasticsearch
    log_info "Starting Elasticsearch..."
    $COMPOSE_CMD up -d elasticsearch
    if check_service_health "elasticsearch"; then
        SERVICE_STATUS[elasticsearch]="running"
        log_success "Elasticsearch started successfully"
    else
        SERVICE_STATUS[elasticsearch]="failed"
        log_error "Elasticsearch failed to start"
        return 1
    fi
    
    # Start Logstash
    log_info "Starting Logstash..."
    $COMPOSE_CMD up -d logstash
    if wait_for_service "Logstash" 5044; then
        SERVICE_STATUS[logstash]="running"
        log_success "Logstash started successfully"
    else
        SERVICE_STATUS[logstash]="failed"
        log_error "Logstash failed to start"
        return 1
    fi
    
    # Start Kibana
    log_info "Starting Kibana..."
    $COMPOSE_CMD up -d kibana
    if check_service_health "kibana"; then
        SERVICE_STATUS[kibana]="running"
        log_success "Kibana started successfully"
    else
        SERVICE_STATUS[kibana]="failed"
        log_error "Kibana failed to start"
        return 1
    fi
    
    # Start Filebeat
    log_info "Starting Filebeat..."
    $COMPOSE_CMD up -d filebeat
    SERVICE_STATUS[filebeat]="running"
    log_success "Filebeat started successfully"
    
    return 0
}

start_monitoring_services() {
    log_header "STARTING MONITORING SERVICES (APM)"
    
    cd "$PROJECT_ROOT"
    
    # Start Jaeger for distributed tracing
    log_info "Starting Jaeger..."
    $COMPOSE_CMD up -d jaeger
    if wait_for_service "Jaeger" 16686; then
        SERVICE_STATUS[jaeger]="running"
        log_success "Jaeger started successfully"
    else
        SERVICE_STATUS[jaeger]="failed"
        log_error "Jaeger failed to start"
        return 1
    fi
    
    # Start Prometheus
    log_info "Starting Prometheus..."
    $COMPOSE_CMD up -d prometheus
    if check_service_health "prometheus"; then
        SERVICE_STATUS[prometheus]="running"
        log_success "Prometheus started successfully"
    else
        SERVICE_STATUS[prometheus]="failed"
        log_error "Prometheus failed to start"
        return 1
    fi
    
    # Start Grafana
    log_info "Starting Grafana..."
    $COMPOSE_CMD up -d grafana
    if check_service_health "grafana"; then
        SERVICE_STATUS[grafana]="running"
        log_success "Grafana started successfully"
    else
        SERVICE_STATUS[grafana]="failed"
        log_error "Grafana failed to start"
        return 1
    fi
    
    return 0
}

start_application_services() {
    log_header "STARTING APPLICATION SERVICES"
    
    cd "$PROJECT_ROOT"
    
    # Build application images
    log_info "Building application images..."
    $COMPOSE_CMD build
    
    # Start core API service
    log_info "Starting RegulensAI API..."
    $COMPOSE_CMD up -d api
    if check_service_health "api"; then
        SERVICE_STATUS[api]="running"
        log_success "RegulensAI API started successfully"
    else
        SERVICE_STATUS[api]="failed"
        log_error "RegulensAI API failed to start"
        return 1
    fi
    
    # Start compliance engine
    log_info "Starting Compliance Engine..."
    $COMPOSE_CMD up -d compliance-engine
    SERVICE_STATUS[compliance-engine]="running"
    log_success "Compliance Engine started successfully"
    
    # Start notification service
    log_info "Starting Notification Service..."
    $COMPOSE_CMD up -d notification-service
    SERVICE_STATUS[notification-service]="running"
    log_success "Notification Service started successfully"
    
    # Start regulatory monitoring service
    log_info "Starting Regulatory Monitoring Service..."
    $COMPOSE_CMD up -d regulatory-monitor
    SERVICE_STATUS[regulatory-monitor]="running"
    log_success "Regulatory Monitoring Service started successfully"
    
    return 0
}

start_ui_services() {
    log_header "STARTING UI SERVICES"

    # Start main UI
    log_info "Starting RegulensAI UI..."
    $COMPOSE_CMD up -d ui
    if check_service_health "ui"; then
        SERVICE_STATUS[ui]="running"
        log_success "RegulensAI UI started successfully"
    else
        SERVICE_STATUS[ui]="failed"
        log_error "RegulensAI UI failed to start"
        return 1
    fi

    # Start UI portals if available
    if [[ -f "${PROJECT_ROOT}/core_infra/ui/docker-compose.ui.yml" ]]; then
        log_info "Starting additional UI portals..."
        cd "${PROJECT_ROOT}/core_infra/ui"

        if [[ -x "./start_ui_portals.sh" ]]; then
            ./start_ui_portals.sh
            SERVICE_STATUS[ui-portals]="running"
            log_success "UI portals started successfully"
        else
            log_warning "UI portals startup script not found or not executable"
        fi

        cd "$PROJECT_ROOT"
    fi

    return 0
}

start_background_services() {
    log_header "STARTING BACKGROUND SERVICES"

    # Start disaster recovery monitoring
    log_info "Starting Disaster Recovery monitoring..."
    if python3 -m scripts.dr_manager start --status > /dev/null 2>&1; then
        SERVICE_STATUS[dr-monitoring]="running"
        log_success "Disaster Recovery monitoring started successfully"
    else
        SERVICE_STATUS[dr-monitoring]="failed"
        log_warning "Disaster Recovery monitoring failed to start"
    fi

    # Start centralized logging manager
    log_info "Starting Centralized Logging manager..."
    if python3 -m scripts.logging_manager start > /dev/null 2>&1; then
        SERVICE_STATUS[logging-manager]="running"
        log_success "Centralized Logging manager started successfully"
    else
        SERVICE_STATUS[logging-manager]="failed"
        log_warning "Centralized Logging manager failed to start"
    fi

    # Start backup manager
    log_info "Starting Backup manager..."
    if python3 -m scripts.backup_manager start > /dev/null 2>&1; then
        SERVICE_STATUS[backup-manager]="running"
        log_success "Backup manager started successfully"
    else
        SERVICE_STATUS[backup-manager]="failed"
        log_warning "Backup manager failed to start"
    fi

    return 0
}

# ============================================================================
# HEALTH VERIFICATION
# ============================================================================

verify_all_services() {
    log_header "VERIFYING ALL SERVICES"

    local failed_services=()
    local total_services=0
    local healthy_services=0

    # Check all services
    for service in "${!SERVICE_STATUS[@]}"; do
        total_services=$((total_services + 1))

        if [[ "${SERVICE_STATUS[$service]}" == "running" ]]; then
            log_info "Checking $service..."

            case "$service" in
                "redis"|"elasticsearch"|"kibana"|"api"|"ui"|"prometheus"|"grafana")
                    if check_service_health "$service"; then
                        healthy_services=$((healthy_services + 1))
                        log_success "$service is healthy"
                    else
                        failed_services+=("$service")
                        log_error "$service health check failed"
                    fi
                    ;;
                *)
                    # For other services, assume healthy if status is running
                    healthy_services=$((healthy_services + 1))
                    log_success "$service is running"
                    ;;
            esac
        else
            failed_services+=("$service")
            log_error "$service is not running"
        fi
    done

    # Summary
    log_info "Service health summary: $healthy_services/$total_services services healthy"

    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_warning "Failed services: ${failed_services[*]}"
        return 1
    else
        log_success "All services are healthy"
        return 0
    fi
}

run_integration_tests() {
    log_header "RUNNING INTEGRATION TESTS"

    # Test API connectivity
    log_info "Testing API connectivity..."
    if curl -f -s "http://localhost:${SERVICE_PORTS[api]}/v1/health" > /dev/null; then
        log_success "API connectivity test passed"
    else
        log_error "API connectivity test failed"
        return 1
    fi

    # Test database connectivity through API
    log_info "Testing database connectivity through API..."
    if curl -f -s "http://localhost:${SERVICE_PORTS[api]}/v1/health/database" > /dev/null; then
        log_success "Database connectivity test passed"
    else
        log_error "Database connectivity test failed"
        return 1
    fi

    # Test Redis connectivity through API
    log_info "Testing Redis connectivity through API..."
    if curl -f -s "http://localhost:${SERVICE_PORTS[api]}/v1/health/redis" > /dev/null; then
        log_success "Redis connectivity test passed"
    else
        log_error "Redis connectivity test failed"
        return 1
    fi

    # Test logging system
    log_info "Testing centralized logging system..."
    if python3 -c "
from core_infra.logging.centralized_logging import get_centralized_logger
import asyncio
async def test():
    logger = await get_centralized_logger('startup_test')
    await logger.info('Startup integration test', category='system')
    print('Logging test passed')
asyncio.run(test())
" 2>/dev/null; then
        log_success "Centralized logging test passed"
    else
        log_warning "Centralized logging test failed"
    fi

    # Test APM system
    log_info "Testing APM system..."
    if python3 -c "
from core_infra.monitoring.apm_integration import apm_manager
import asyncio
async def test():
    await apm_manager.record_transaction('startup_test', 'test', 100, True)
    print('APM test passed')
asyncio.run(test())
" 2>/dev/null; then
        log_success "APM system test passed"
    else
        log_warning "APM system test failed"
    fi

    return 0
}

# ============================================================================
# CLEANUP AND ERROR HANDLING
# ============================================================================

cleanup() {
    log_info "Cleaning up..."

    # Remove PID file
    if [[ -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE"
    fi

    # If startup failed, optionally stop services
    if [[ "${1:-}" == "failed" ]]; then
        log_warning "Startup failed. Services may be in inconsistent state."
        log_info "To stop all services, run: $COMPOSE_CMD down"
        log_info "To view logs, run: $COMPOSE_CMD logs -f"
    fi
}

handle_error() {
    local exit_code=$?
    log_error "Startup script failed with exit code $exit_code"
    cleanup "failed"
    exit $exit_code
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    # Set up error handling
    trap handle_error ERR
    trap cleanup EXIT

    # Create PID file
    echo $$ > "$PID_FILE"

    # Start logging
    log_header "REGULENSAI COMPLETE SERVICE STARTUP"
    log_info "Starting RegulensAI ecosystem..."
    log_info "Script PID: $$"
    log_info "Log file: $LOG_FILE"

    # Execute startup sequence
    check_prerequisites
    setup_environment

    # Initialize database first
    if ! initialize_database; then
        log_error "Database initialization failed"
        exit 1
    fi

    # Start services in dependency order
    if ! start_infrastructure_services; then
        log_error "Infrastructure services startup failed"
        exit 1
    fi

    if ! start_elk_stack; then
        log_error "ELK stack startup failed"
        exit 1
    fi

    if ! start_monitoring_services; then
        log_error "Monitoring services startup failed"
        exit 1
    fi

    if ! start_application_services; then
        log_error "Application services startup failed"
        exit 1
    fi

    if ! start_ui_services; then
        log_error "UI services startup failed"
        exit 1
    fi

    if ! start_background_services; then
        log_warning "Some background services failed to start, but continuing..."
    fi

    # Verify all services
    if ! verify_all_services; then
        log_warning "Some services failed health checks"
    fi

    # Run integration tests
    if ! run_integration_tests; then
        log_warning "Some integration tests failed"
    fi

    # Success summary
    log_header "STARTUP COMPLETED SUCCESSFULLY"

    echo -e "\n${GREEN}🎉 RegulensAI ecosystem is now running!${NC}\n"

    echo -e "${WHITE}📊 Service Status:${NC}"
    for service in "${!SERVICE_STATUS[@]}"; do
        status="${SERVICE_STATUS[$service]}"
        if [[ "$status" == "running" ]]; then
            echo -e "  ${GREEN}✓${NC} $service: $status"
        else
            echo -e "  ${RED}✗${NC} $service: $status"
        fi
    done

    echo -e "\n${WHITE}🌐 Access URLs:${NC}"
    echo -e "  ${CYAN}• RegulensAI API:${NC}          http://localhost:${SERVICE_PORTS[api]}"
    echo -e "  ${CYAN}• RegulensAI UI:${NC}           http://localhost:${SERVICE_PORTS[ui]}"
    echo -e "  ${CYAN}• API Documentation:${NC}       http://localhost:${SERVICE_PORTS[api]}/docs"
    echo -e "  ${CYAN}• Kibana (Logging):${NC}        http://localhost:${SERVICE_PORTS[kibana]}"
    echo -e "  ${CYAN}• Grafana (Monitoring):${NC}    http://localhost:${SERVICE_PORTS[grafana]}"
    echo -e "  ${CYAN}• Prometheus:${NC}              http://localhost:${SERVICE_PORTS[prometheus]}"
    echo -e "  ${CYAN}• Jaeger (Tracing):${NC}        http://localhost:16686"

    echo -e "\n${WHITE}🛠 Management Commands:${NC}"
    echo -e "  ${CYAN}• View all logs:${NC}           $COMPOSE_CMD logs -f"
    echo -e "  ${CYAN}• Stop all services:${NC}       $COMPOSE_CMD down"
    echo -e "  ${CYAN}• Restart services:${NC}        $COMPOSE_CMD restart"
    echo -e "  ${CYAN}• Service status:${NC}          $COMPOSE_CMD ps"
    echo -e "  ${CYAN}• DR status:${NC}               python3 -m scripts.dr_manager status"
    echo -e "  ${CYAN}• Backup status:${NC}           python3 -m scripts.backup_manager status"

    echo -e "\n${WHITE}📋 Next Steps:${NC}"
    echo -e "  ${GREEN}1.${NC} Access the RegulensAI UI at http://localhost:${SERVICE_PORTS[ui]}"
    echo -e "  ${GREEN}2.${NC} Review the API documentation at http://localhost:${SERVICE_PORTS[api]}/docs"
    echo -e "  ${GREEN}3.${NC} Configure monitoring dashboards in Grafana"
    echo -e "  ${GREEN}4.${NC} Set up log analysis in Kibana"
    echo -e "  ${GREEN}5.${NC} Run disaster recovery tests: python3 -m scripts.dr_manager full-test --dry-run"

    echo -e "\n${WHITE}📁 Important Files:${NC}"
    echo -e "  ${CYAN}• Startup log:${NC}             $LOG_FILE"
    echo -e "  ${CYAN}• Environment config:${NC}      ${PROJECT_ROOT}/.env"
    echo -e "  ${CYAN}• Docker compose:${NC}          ${PROJECT_ROOT}/docker-compose.yml"
    echo -e "  ${CYAN}• Database schema:${NC}         ${PROJECT_ROOT}/core_infra/database/schema.sql"

    echo -e "\n${GREEN}RegulensAI is ready for enterprise use! 🚀${NC}\n"

    return 0
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "RegulensAI Complete Service Startup Script"
        echo "Usage: $0 [--help|--status|--stop]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --status       Show service status without starting"
        echo "  --stop         Stop all services"
        echo ""
        echo "Environment Variables:"
        echo "  STARTUP_TIMEOUT        - Service startup timeout (default: 300s)"
        echo "  HEALTH_CHECK_TIMEOUT   - Health check timeout (default: 60s)"
        echo "  COMPOSE_CMD            - Docker compose command (auto-detected)"
        exit 0
        ;;
    --status)
        log_info "Checking service status..."
        cd "$PROJECT_ROOT"
        $COMPOSE_CMD ps
        exit 0
        ;;
    --stop)
        log_info "Stopping all RegulensAI services..."
        cd "$PROJECT_ROOT"
        $COMPOSE_CMD down

        # Stop background services
        python3 -m scripts.dr_manager stop 2>/dev/null || true
        python3 -m scripts.logging_manager stop 2>/dev/null || true
        python3 -m scripts.backup_manager stop 2>/dev/null || true

        log_success "All services stopped"
        exit 0
        ;;
esac

# Execute main function
main "$@"
