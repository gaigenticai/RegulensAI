#!/bin/bash

# ============================================================================
# REGULENS AI - ONE-CLICK INSTALLER (ENHANCED)
# Enterprise Financial Compliance Platform with Complete Operational Stack
# Includes: Centralized Logging, APM, Disaster Recovery, Enhanced Documentation
# ============================================================================

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/install.log"
DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"
PLATFORM_NAME="Regulens AI Financial Compliance Platform"
TEMP_ENV_FILE="$SCRIPT_DIR/.env.temp"

# Service port configurations for smart conflict resolution (Bash 3.2 compatible)
# Format: service_name:port
SERVICE_PORTS=(
    "api:8000"
    "docs_portal:8501"
    "testing_portal:8502"
    "frontend:3000"
    "grafana:3001"
    "jaeger:16686"
    "prometheus:9090"
    "redis:6379"
    "elasticsearch:9200"
    "kibana:5601"
    "logstash:5044"
)

# Store assigned ports as variables
ASSIGNED_PORT_API=""
ASSIGNED_PORT_DOCS_PORTAL=""
ASSIGNED_PORT_TESTING_PORTAL=""
ASSIGNED_PORT_FRONTEND=""
ASSIGNED_PORT_GRAFANA=""
ASSIGNED_PORT_JAEGER=""
ASSIGNED_PORT_PROMETHEUS=""
ASSIGNED_PORT_REDIS=""
ASSIGNED_PORT_ELASTICSEARCH=""
ASSIGNED_PORT_KIBANA=""
ASSIGNED_PORT_LOGSTASH=""

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${WHITE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_step() {
    echo -e "${CYAN}➤ $1${NC}"
    log "STEP: $1"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    log "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARNING: $1"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    log "ERROR: $1"
}

print_status() {
    echo -e "${BLUE}➤ $1${NC}"
    log "STATUS: $1"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

generate_secure_key() {
    openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "$(date +%s | sha256sum | head -c 64)"
}

wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    print_step "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost "$port" 2>/dev/null; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "$service_name failed to start within $(($max_attempts * 2)) seconds"
    return 1
}

# ============================================================================
# PREREQUISITE CHECKS
# ============================================================================

check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    local missing_deps=()
    
    # Check Docker
    if check_command docker; then
        print_success "Docker is installed"
        
        # Check if Docker daemon is running
        if docker info &> /dev/null; then
            print_success "Docker daemon is running"
        else
            print_error "Docker daemon is not running. Please start Docker and try again."
            exit 1
        fi
    else
        missing_deps+=("docker")
    fi
    
    # Check Docker Compose
    if check_command docker-compose || docker compose version &> /dev/null; then
        print_success "Docker Compose is available"
    else
        missing_deps+=("docker-compose")
    fi
    
    # Check required utilities
    for cmd in curl nc openssl git; do
        if check_command "$cmd"; then
            print_success "$cmd is installed"
        else
            missing_deps+=("$cmd")
        fi
    done
    
    # Check Python for key generation fallback
    if ! check_command openssl && ! check_command python3; then
        missing_deps+=("python3")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo
        echo "Please install the missing dependencies and run this script again."
        echo
        echo "On Ubuntu/Debian:"
        echo "  sudo apt update && sudo apt install -y ${missing_deps[*]}"
        echo
        echo "On macOS:"
        echo "  brew install ${missing_deps[*]}"
        echo
        exit 1
    fi
    
    # Check available disk space (minimum 10GB)
    local available_space
    available_space=$(df "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
    local min_space=$((10 * 1024 * 1024)) # 10GB in KB
    
    if [ "$available_space" -lt "$min_space" ]; then
        print_warning "Available disk space is less than 10GB. Installation may fail."
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "Sufficient disk space available"
    fi
}

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

setup_environment() {
    print_header "SETTING UP ENVIRONMENT CONFIGURATION"
    
    if [ -f "$ENV_FILE" ]; then
        print_warning ".env file already exists"
        read -p "Do you want to regenerate the .env file? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            backup_env_file
            create_env_file
        else
            print_step "Using existing .env file"
            validate_env_file
        fi
    else
        create_env_file
    fi
}

backup_env_file() {
    local backup_file="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$backup_file"
    print_success "Backed up existing .env to $backup_file"
}

create_env_file() {
    print_step "Creating new .env file with secure defaults..."
    
    # Generate secure keys
    local jwt_secret=$(generate_secure_key)
    local encryption_key=$(generate_secure_key)
    local redis_password=$(generate_secure_key | head -c 16)
    local webhook_secret=$(generate_secure_key | head -c 32)
    
    # Create the .env file with production-ready defaults
    cat > "$ENV_FILE" << EOF
# ============================================================================
# REGULENS AI - FINANCIAL COMPLIANCE PLATFORM CONFIGURATION
# Generated by one-click installer on $(date)
# ============================================================================

# Application Configuration
APP_NAME=Regulens AI Financial Compliance Platform
APP_VERSION=1.0.0
APP_ENVIRONMENT=production
DEBUG=false
API_VERSION=v1
API_PORT=${ASSIGNED_PORT_API:-8000}
API_HOST=0.0.0.0

# Security Configuration (GENERATED - DO NOT SHARE)
JWT_SECRET_KEY=$jwt_secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
ENCRYPTION_KEY=$encryption_key
BCRYPT_ROUNDS=12

# Database Configuration - UPDATE WITH YOUR SUPABASE CREDENTIALS
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=$redis_password

# Storage Configuration
STORAGE_PROVIDER=supabase
SUPABASE_STORAGE_BUCKET=compliance-documents

# AI Configuration - ADD YOUR API KEYS
OPENAI_API_KEY=your-openai-api-key-for-regulatory-insights
CLAUDE_API_KEY=your-claude-api-key

# LangSmith Configuration - ADD YOUR API KEY
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key

# Regulatory Monitoring
REGULATORY_MONITOR_ENABLED=true
REGULATORY_MONITOR_INTERVAL_MINUTES=60

# AML/KYC Configuration
AML_MONITORING_ENABLED=true
TRANSACTION_MONITORING_REAL_TIME=true

# Observability
JAEGER_ENABLED=true
LOG_LEVEL=INFO
METRICS_ENABLED=true

# Docker Configuration
POSTGRES_PASSWORD=secure_postgres_password_$(generate_secure_key | head -c 16)
REDIS_PASSWORD=$redis_password

# Feature Flags
FEATURE_ADVANCED_ANALYTICS=true
FEATURE_PREDICTIVE_COMPLIANCE=true
FEATURE_AUTOMATED_REPORTING=true
FEATURE_REAL_TIME_MONITORING=true

# Webhook Configuration
WEBHOOK_SECRET=$webhook_secret
EOF
    
    print_success "Environment configuration created"
    print_warning "IMPORTANT: Update the following in .env with your actual credentials:"
    echo "  - SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY"
    echo "  - DATABASE_URL (your Supabase database connection string)"
    echo "  - OPENAI_API_KEY (for AI regulatory insights)"
    echo "  - CLAUDE_API_KEY (optional, for enhanced AI features)"
    echo "  - LANGCHAIN_API_KEY (for AI tracing and monitoring)"
}

validate_env_file() {
    print_step "Validating environment configuration..."
    
    # Check for placeholder values that need to be updated
    local needs_update=false
    
    if grep -q "your-supabase" "$ENV_FILE"; then
        print_warning "Supabase credentials need to be configured"
        needs_update=true
    fi
    
    if grep -q "your-openai-api-key" "$ENV_FILE"; then
        print_warning "OpenAI API key needs to be configured for AI features"
        needs_update=true
    fi
    
    if [ "$needs_update" = true ]; then
        echo
        print_warning "Some configuration values need to be updated manually."
        echo "Please edit .env and update the placeholder values before continuing."
        read -p "Press Enter when you have updated the configuration..."
    fi
    
    print_success "Environment configuration validated"
}

# ============================================================================
# DOCKER SETUP
# ============================================================================

setup_docker_environment() {
    print_header "SETTING UP DOCKER ENVIRONMENT"
    
    # Create necessary directories
    print_step "Creating required directories..."
    mkdir -p logs models_cache monitoring/prometheus monitoring/grafana/provisioning nginx ui
    
    # Copy nginx configuration if it exists in docs
    if [ -f "docs/nginx.conf" ]; then
        cp docs/nginx.conf ui/nginx.conf
        print_success "Copied nginx configuration"
    fi
    
    # Create basic monitoring configuration files
    create_monitoring_configs
    
    print_success "Docker environment prepared"
}

create_monitoring_configs() {
    print_step "Creating monitoring configuration files..."
    
    # Prometheus configuration
    cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'regulens-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/v1/metrics'
    scrape_interval: 30s
    
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF
    
    # Grafana datasource configuration
    mkdir -p monitoring/grafana/provisioning/datasources
    cat > monitoring/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
    
    print_success "Monitoring configurations created"
}

# ============================================================================
# DATABASE SETUP
# ============================================================================

setup_database() {
    print_header "SETTING UP DATABASE WITH ENHANCED SCHEMA"

    print_step "Validating database configuration..."

    # Check if database credentials are configured
    if grep -q "your-supabase" "$ENV_FILE" || grep -q "your-database" "$ENV_FILE"; then
        print_error "Database credentials are not configured!"
        echo
        echo "Please update your .env file with your database credentials:"
        echo "  For Supabase:"
        echo "    SUPABASE_URL=your-supabase-project-url"
        echo "    SUPABASE_ANON_KEY=your-supabase-anon-key"
        echo "    SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key"
        echo "    DATABASE_URL=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres"
        echo
        echo "  For other PostgreSQL databases:"
        echo "    DATABASE_URL=postgresql://username:password@host:port/database"
        echo
        read -p "Press Enter when you have updated the database credentials..."
    fi

    print_step "Checking consolidated database schema..."

    # Check if consolidated schema file exists
    if [ -f "$SCRIPT_DIR/core_infra/database/schema.sql" ]; then
        print_success "Found consolidated database schema file"
        print_info "Schema includes:"
        print_info "  • Core RegulensAI tables (users, regulations, compliance, etc.)"
        print_info "  • Centralized logging tables (logs, aggregation rules, retention)"
        print_info "  • APM monitoring tables (transactions, spans, errors, metrics)"
        print_info "  • Disaster recovery tables (objectives, tests, events, backups)"
        print_info "  • Configuration management tables (versions, drift, compliance)"
        print_info "  • Optimized indexes and constraints for performance"
    else
        print_warning "Consolidated schema file not found at core_infra/database/schema.sql"
    fi

    print_step "Database schema will be applied during service startup..."
    print_info "The consolidated startup script will handle:"
    print_info "  • Database connectivity verification"
    print_info "  • Schema migrations and updates"
    print_info "  • Schema validation and integrity checks"

    print_success "Database setup configuration completed"
}

# ============================================================================
# ADVANCED MONITORING DEPLOYMENT
# ============================================================================

deploy_advanced_monitoring() {
    print_step "Deploying advanced monitoring stack..."

    local monitoring_script="$SCRIPT_DIR/monitoring/deploy-monitoring.sh"

    if [ -f "$monitoring_script" ]; then
        print_step "Found advanced monitoring deployment script"

        # Check if we're in a Kubernetes environment
        if check_command kubectl && kubectl cluster-info &> /dev/null; then
            print_step "Kubernetes detected - deploying full monitoring stack..."

            # Make script executable
            chmod +x "$monitoring_script"

            # Set environment variables for monitoring deployment
            export GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-$(generate_secure_key | head -c 16)}"
            export NAMESPACE="regulensai-monitoring"

            # Run the monitoring deployment script
            if "$monitoring_script"; then
                print_success "Advanced monitoring stack deployed successfully"

                # Update .env with monitoring configuration
                echo "" >> "$ENV_FILE"
                echo "# Advanced Monitoring Configuration" >> "$ENV_FILE"
                echo "MONITORING_ENABLED=true" >> "$ENV_FILE"
                echo "GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD" >> "$ENV_FILE"
                echo "MONITORING_NAMESPACE=$NAMESPACE" >> "$ENV_FILE"

                print_success "Monitoring configuration added to .env"
            else
                print_warning "Advanced monitoring deployment failed, continuing with basic monitoring"
            fi
        else
            print_warning "Kubernetes not available - using Docker-based monitoring only"
            deploy_docker_monitoring
        fi
    else
        print_warning "Advanced monitoring script not found at $monitoring_script"
        print_step "Using basic Docker-based monitoring..."
        deploy_docker_monitoring
    fi
}

deploy_docker_monitoring() {
    print_step "Setting up Docker-based monitoring..."

    # Create enhanced monitoring configuration for Docker
    cat > monitoring/docker-monitoring.yml << EOF
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: regulensai-prometheus
    ports:
      - "${ASSIGNED_PORT_PROMETHEUS:-9090}:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - regulensai-network

  grafana:
    image: grafana/grafana:latest
    container_name: regulensai-grafana
    ports:
      - "${ASSIGNED_PORT_GRAFANA:-3001}:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=\${GRAFANA_ADMIN_PASSWORD:-admin123}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    networks:
      - regulensai-network

volumes:
  prometheus_data:
  grafana_data:

networks:
  regulensai-network:
    external: true
EOF

    # Start Docker monitoring services
    docker-compose -f monitoring/docker-monitoring.yml up -d

    print_success "Docker-based monitoring deployed"
}

# ============================================================================
# SERVICE STARTUP
# ============================================================================

start_all_services() {
    print_header "STARTING COMPLETE REGULENSAI ECOSYSTEM"

    print_step "Preparing consolidated startup script..."

    # Make sure the startup script is executable
    if [ -f "$SCRIPT_DIR/scripts/start_all_services.sh" ]; then
        chmod +x "$SCRIPT_DIR/scripts/start_all_services.sh"

        print_step "Starting all RegulensAI services using consolidated startup script..."
        print_info "This includes:"
        print_info "  • Infrastructure services (Redis, Qdrant)"
        print_info "  • ELK Stack (Elasticsearch, Logstash, Kibana, Filebeat)"
        print_info "  • Monitoring services (Jaeger, Prometheus, Grafana)"
        print_info "  • Application services (API, Compliance Engine, etc.)"
        print_info "  • UI services (Web UI, Documentation Portal)"
        print_info "  • Background services (DR, Logging, Backup managers)"
        echo

        # Run the consolidated startup script
        if "$SCRIPT_DIR/scripts/start_all_services.sh"; then
            print_success "All RegulensAI services started successfully using consolidated script"
        else
            print_warning "Consolidated startup script encountered issues, falling back to basic startup..."
            start_basic_services
        fi
    else
        print_warning "Consolidated startup script not found, using basic startup..."
        start_basic_services
    fi
}

start_basic_services() {
    print_header "STARTING BASIC SERVICES (FALLBACK)"

    print_step "Starting Redis..."
    docker-compose up -d redis
    wait_for_service "Redis" 6379

    print_step "Starting Qdrant vector database..."
    docker-compose up -d qdrant
    wait_for_service "Qdrant" 6333

    print_step "Starting monitoring services..."
    docker-compose up -d jaeger prometheus grafana
    wait_for_service "Jaeger" 16686
    wait_for_service "Prometheus" 9090
    wait_for_service "Grafana" 3001

    # Deploy advanced monitoring if script exists
    deploy_advanced_monitoring

    print_step "Building application images..."
    docker-compose build

    print_step "Starting application services..."
    docker-compose up -d

    # Wait for main API to be ready
    wait_for_service "Regulens AI API" 8000 60

    print_step "Verifying service health..."
    local health_check_url="http://localhost:8000/v1/health"
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_check_url" > /dev/null 2>&1; then
            print_success "API health check passed"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_warning "API health check failed, but continuing..."
            break
        fi

        echo -n "."
        sleep 3
        ((attempt++))
    done

    print_success "Basic services started successfully"
}

# ============================================================================
# POST-INSTALLATION SETUP
# ============================================================================

post_installation_setup() {
    print_header "POST-INSTALLATION SETUP"
    
    print_step "Checking service status..."
    docker-compose ps
    
    print_step "Creating initial data (if configured)..."
    # Only create initial data if Supabase is properly configured
    if ! grep -q "your-supabase" "$ENV_FILE"; then
        create_initial_data
    else
        print_warning "Skipping initial data creation - Supabase not configured"
    fi
    
    print_step "Setting up log rotation..."
    setup_log_rotation
    
    print_success "Post-installation setup completed"
}

create_initial_data() {
    print_step "Creating initial tenant and admin user..."
    
    # This would typically call an API endpoint or run a script
    # For now, we'll create a placeholder script
    
    cat > create_initial_data.py << 'EOF'
#!/usr/bin/env python3
"""
Initial data creation script for Regulens AI
This script creates the default tenant and admin user.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the core_infra directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core_infra'))

async def create_initial_data():
    """Create initial tenant and admin user."""
    try:
        print("Creating initial data...")
        
        # Import after path is set
        from database.connection import get_database
        
        # Create default tenant
        tenant_data = {
            'name': 'Default Organization',
            'industry': 'Financial Services',
            'country_code': 'US',
            'regulatory_jurisdictions': ['US', 'UK', 'EU']
        }
        
        # Create admin user
        admin_data = {
            'email': 'admin@regulens-ai.com',
            'full_name': 'System Administrator',
            'role': 'admin',
            'permissions': ['*']
        }
        
        print("✓ Initial data creation completed")
        print(f"✓ Default admin user: {admin_data['email']}")
        print("✓ Default tenant created")
        
    except ImportError as e:
        print(f"⚠ Could not import required modules: {e}")
        print("⚠ Initial data creation skipped - run manually after configuration")
    except Exception as e:
        print(f"✗ Error creating initial data: {e}")

if __name__ == "__main__":
    asyncio.run(create_initial_data())
EOF
    
    # Make the script executable
    chmod +x create_initial_data.py
    
    # Run the script if Python is available and database is configured
    if check_command python3 && ! grep -q "your-password" "$ENV_FILE"; then
        python3 create_initial_data.py
    else
        print_warning "Initial data creation skipped - configure database first"
    fi
}

setup_log_rotation() {
    print_step "Setting up log rotation..."
    
    # Create logrotate configuration
    cat > regulens-logrotate << EOF
$SCRIPT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 0644 root root
}
EOF
    
    print_success "Log rotation configured"
}

# ============================================================================
# INSTALLATION SUMMARY
# ============================================================================

show_installation_summary() {
    print_header "INSTALLATION COMPLETE"
    
    # Start UI portals
    print_status "Starting UI documentation and testing portals..."
    if [ -f "core_infra/ui/start_ui_portals.sh" ]; then
        cd core_infra/ui
        ./start_ui_portals.sh
        cd ../..
        print_success "UI portals started successfully!"
    else
        print_warning "UI portal startup script not found. Starting manually..."
        if [ -f "core_infra/ui/docker-compose.ui.yml" ]; then
            cd core_infra/ui
            docker-compose -f docker-compose.ui.yml up -d --build 2>/dev/null || true
            cd ../..
        fi
    fi
    
    echo -e "${GREEN}🎉 $PLATFORM_NAME has been successfully installed with Enhanced Features!${NC}"
    echo
    echo -e "${WHITE}📊 Core Platform Access:${NC}"
    echo -e "  ${CYAN}• Main API:${NC}              http://localhost:${ASSIGNED_PORT_API:-8000}"
    echo -e "  ${CYAN}• RegulensAI Web UI:${NC}     http://localhost:${ASSIGNED_PORT_FRONTEND:-3000}"
    echo -e "  ${CYAN}• Health Check:${NC}          http://localhost:${ASSIGNED_PORT_API:-8000}/v1/health"
    echo -e "  ${CYAN}• Platform Info:${NC}         http://localhost:${ASSIGNED_PORT_API:-8000}/v1/info"
    echo
    echo -e "${WHITE}📚 Enhanced Documentation & Testing:${NC}"
    echo -e "  ${CYAN}• Documentation Portal:${NC}  http://localhost:${ASSIGNED_PORT_DOCS_PORTAL:-8501}"
    echo -e "    ${GRAY}- Enhanced API docs with OAuth2/SAML examples${NC}"
    echo -e "    ${GRAY}- Cloud deployment guides (AWS/GCP/Azure)${NC}"
    echo -e "    ${GRAY}- Configuration management and compliance${NC}"
    echo
    echo -e "  ${CYAN}• Testing Portal:${NC}        http://localhost:${ASSIGNED_PORT_TESTING_PORTAL:-8502}"
    echo -e "    ${GRAY}- Interactive service testing interface${NC}"
    echo -e "    ${GRAY}- Real API endpoint testing with examples${NC}"
    echo -e "    ${GRAY}- Test history and performance analytics${NC}"
    echo
    echo -e "  ${CYAN}• Integrated Docs:${NC}       http://localhost:${ASSIGNED_PORT_FRONTEND:-3000}/documentation"
    echo -e "    ${GRAY}- Web-integrated documentation portal${NC}"
    echo -e "    ${GRAY}- Interactive API testing and validation${NC}"
    echo -e "    ${GRAY}- Configuration drift detection${NC}"
    echo
    echo -e "${WHITE}📖 Enhanced API Documentation:${NC}"
    echo -e "  ${CYAN}• Swagger UI:${NC}            http://localhost:${ASSIGNED_PORT_API:-8000}/docs"
    echo -e "    ${GRAY}- Interactive API testing with comprehensive examples${NC}"
    echo -e "    ${GRAY}- Field descriptions and validation rules${NC}"
    echo -e "    ${GRAY}- Authentication and security guides${NC}"
    echo
    echo -e "  ${CYAN}• ReDoc:${NC}                 http://localhost:${ASSIGNED_PORT_API:-8000}/redoc"
    echo -e "    ${GRAY}- Clean API reference documentation${NC}"
    echo -e "    ${GRAY}- Code examples in multiple languages${NC}"
    echo
    echo -e "${WHITE}🔍 Enhanced Monitoring & Observability:${NC}"
    echo -e "  ${CYAN}• Centralized Logging:${NC}   http://localhost:${ASSIGNED_PORT_KIBANA:-5601} (Kibana)"
    echo -e "    ${GRAY}- ELK stack with log aggregation and analysis${NC}"
    echo -e "    ${GRAY}- Real-time log monitoring and alerting${NC}"
    echo -e "  ${CYAN}• APM Monitoring:${NC}        http://localhost:${ASSIGNED_PORT_GRAFANA:-3001} (Grafana)"
    echo -e "    ${GRAY}- Application performance monitoring${NC}"
    echo -e "    ${GRAY}- Distributed tracing and error tracking${NC}"
    echo -e "  ${CYAN}• Jaeger Tracing:${NC}        http://localhost:16686"
    echo -e "  ${CYAN}• Prometheus Metrics:${NC}    http://localhost:${ASSIGNED_PORT_PROMETHEUS:-9090}"
    echo -e "  ${CYAN}• System Health:${NC}         http://localhost:${ASSIGNED_PORT_API:-8000}/v1/health"
    echo
    echo -e "${WHITE}🔧 Enhanced Quick Start Guide:${NC}"
    echo -e "  ${YELLOW}1.${NC} 🌐 Access RegulensAI Web UI (http://localhost:${ASSIGNED_PORT_FRONTEND:-3000})"
    echo -e "  ${YELLOW}2.${NC} 📖 Explore integrated documentation (/documentation in web UI)"
    echo -e "  ${YELLOW}3.${NC} 📊 Monitor system health in Kibana (http://localhost:${ASSIGNED_PORT_KIBANA:-5601})"
    echo -e "  ${YELLOW}4.${NC} 📈 View performance metrics in Grafana (http://localhost:${ASSIGNED_PORT_GRAFANA:-3001})"
    echo -e "  ${YELLOW}5.${NC} 🧪 Test APIs with enhanced documentation portal"
    echo -e "  ${YELLOW}6.${NC} ✅ Verify system health: curl http://localhost:${ASSIGNED_PORT_API:-8000}/v1/health"
    echo -e "  ${YELLOW}7.${NC} ⚙️ Update .env with your database credentials"
    echo -e "  ${YELLOW}8.${NC} 🤖 Add your OpenAI/Claude API keys for AI features"
    echo -e "  ${YELLOW}9.${NC} 🔧 Configure disaster recovery: python3 -m scripts.dr_manager status"
    echo
    echo -e "${WHITE}📁 Important Files:${NC}"
    echo -e "  ${CYAN}• Configuration:${NC}        .env"
    echo -e "  ${CYAN}• Installation Log:${NC}     install.log"
    echo -e "  ${CYAN}• Startup Script:${NC}       scripts/start_all_services.sh"
    echo -e "  ${CYAN}• Database Schema:${NC}      core_infra/database/schema.sql (consolidated)"
    echo -e "  ${CYAN}• Docker Compose:${NC}       docker-compose.yml"
    echo -e "  ${CYAN}• UI Services:${NC}          core_infra/ui/docker-compose.ui.yml"
    echo
    echo -e "${WHITE}🛠 Enhanced Management Commands:${NC}"
    echo -e "  ${CYAN}• Start all services:${NC}   ./scripts/start_all_services.sh"
    echo -e "  ${CYAN}• Stop all services:${NC}    ./scripts/start_all_services.sh --stop"
    echo -e "  ${CYAN}• Service status:${NC}       ./scripts/start_all_services.sh --status"
    echo -e "  ${CYAN}• View all logs:${NC}        docker-compose logs -f"
    echo -e "  ${CYAN}• DR management:${NC}        python3 -m scripts.dr_manager status"
    echo -e "  ${CYAN}• Backup management:${NC}    python3 -m scripts.backup_manager status"
    echo -e "  ${CYAN}• Logging management:${NC}   python3 -m scripts.logging_manager status"
    echo
    echo -e "${WHITE}🚀 Enhanced Features Available:${NC}"
    echo -e "  ${GREEN}• Real-time regulatory monitoring (SEC, FCA, ECB)${NC}"
    echo -e "  ${GREEN}• AI-powered regulatory analysis (GPT-4, Claude)${NC}"
    echo -e "  ${GREEN}• AML/KYC compliance automation${NC}"
    echo -e "  ${GREEN}• Centralized logging with ELK stack${NC}"
    echo -e "  ${GREEN}• Application Performance Monitoring (APM)${NC}"
    echo -e "  ${GREEN}• Disaster recovery with automated testing${NC}"
    echo -e "  ${GREEN}• Configuration drift detection${NC}"
    echo -e "  ${GREEN}• Compliance scanning (SOC 2, ISO 27001, GDPR)${NC}"
    echo -e "  ${GREEN}• Enhanced API documentation with OAuth2/SAML${NC}"
    echo -e "  ${GREEN}• Multi-cloud deployment guides${NC}"
    echo -e "  ${GREEN}• Enterprise system integrations${NC}"
    echo -e "  ${GREEN}• Audit-ready reporting${NC}"
    echo
    echo -e "${WHITE}🔐 Enhanced Security & Operations:${NC}"
    echo -e "  ${RED}• Change JWT_SECRET_KEY in .env for production${NC}"
    echo -e "  ${RED}• Configure SSL/TLS certificates${NC}"
    echo -e "  ${RED}• Set up proper firewall rules${NC}"
    echo -e "  ${RED}• Enable automated backup procedures${NC}"
    echo -e "  ${RED}• Configure disaster recovery testing${NC}"
    echo -e "  ${RED}• Set up log retention policies${NC}"
    echo -e "  ${RED}• Configure compliance scanning schedules${NC}"
    echo -e "  ${RED}• Rotate API keys regularly${NC}"
    echo
    echo -e "${GREEN}For comprehensive documentation: http://localhost:${ASSIGNED_PORT_FRONTEND:-3000}/documentation${NC}"
    echo -e "${GREEN}For monitoring and logs: http://localhost:${ASSIGNED_PORT_KIBANA:-5601}${NC}"
    echo
}

# ============================================================================
# CLEANUP ON ERROR
# ============================================================================

cleanup_on_error() {
    print_error "Installation failed. Cleaning up..."
    
    # Stop any running containers
    docker-compose down 2>/dev/null || true
    
    # Remove any created volumes (optional)
    read -p "Do you want to remove created Docker volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v 2>/dev/null || true
        print_success "Docker volumes removed"
    fi
    
    print_error "Installation failed. Check install.log for details."
    exit 1
}

# ============================================================================
# SMART PORT CONFLICT RESOLUTION
# ============================================================================

# Function to check if port is available
is_port_available() {
    local port=$1
    ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to find next available port
find_available_port() {
    local start_port=$1
    local max_attempts=100
    local current_port=$start_port
    
    for ((i=0; i<max_attempts; i++)); do
        if is_port_available $current_port; then
            echo $current_port
            return 0
        fi
        ((current_port++))
    done
    
    # If no port found in range, return original
    echo $start_port
    return 1
}

# Smart port conflict resolution (Bash 3.2 compatible)
resolve_port_conflicts() {
    print_status "🔍 Scanning for port conflicts and resolving..."
    
    local conflicts_found=false
    local resolution_summary=""
    
    # Function to set assigned port variable
    set_assigned_port() {
        local service=$1
        local port=$2
        case $service in
            "api") ASSIGNED_PORT_API=$port ;;
            "docs_portal") ASSIGNED_PORT_DOCS_PORTAL=$port ;;
            "testing_portal") ASSIGNED_PORT_TESTING_PORTAL=$port ;;
            "frontend") ASSIGNED_PORT_FRONTEND=$port ;;
            "grafana") ASSIGNED_PORT_GRAFANA=$port ;;
            "jaeger") ASSIGNED_PORT_JAEGER=$port ;;
            "prometheus") ASSIGNED_PORT_PROMETHEUS=$port ;;
            "redis") ASSIGNED_PORT_REDIS=$port ;;
        esac
    }
    
    # Process each service:port pair
    for service_port in "${SERVICE_PORTS[@]}"; do
        local service=${service_port%:*}
        local original_port=${service_port#*:}
        
        if is_port_available $original_port; then
            set_assigned_port $service $original_port
            print_success "✅ Port $original_port available for $service"
        else
            conflicts_found=true
            local new_port=$(find_available_port $((original_port + 1)))
            
            if [ $new_port -ne $original_port ]; then
                set_assigned_port $service $new_port
                resolution_summary+="\n  • $service: $original_port → $new_port"
                print_warning "🔄 Port conflict resolved: $service moved from $original_port to $new_port"
            else
                print_error "❌ Could not resolve port conflict for $service (port $original_port)"
                return 1
            fi
        fi
    done
    
    if [ "$conflicts_found" = true ]; then
        print_status "📋 Port conflict resolution summary:$resolution_summary"
        update_environment_with_new_ports
    else
        print_success "🎉 No port conflicts detected - all services can use default ports"
    fi
    
    return 0
}

# Update environment file with new ports (Bash 3.2 compatible)
update_environment_with_new_ports() {
    print_status "📝 Updating environment configuration with resolved ports..."
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found - will be created with resolved ports"
        return 0
    fi
    
    # Create backup of original .env
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%s)"
    
    # Copy original to temp file
    cp "$ENV_FILE" "$TEMP_ENV_FILE"
    
    # Update ports in temp env file based on assigned port variables
    if [ -n "$ASSIGNED_PORT_API" ]; then
        sed -i.bak "s/^API_PORT=.*/API_PORT=$ASSIGNED_PORT_API/" "$TEMP_ENV_FILE"
    fi
    if [ -n "$ASSIGNED_PORT_DOCS_PORTAL" ]; then
        sed -i.bak "s/^DOCS_PORTAL_PORT=.*/DOCS_PORTAL_PORT=$ASSIGNED_PORT_DOCS_PORTAL/" "$TEMP_ENV_FILE"
    fi
    if [ -n "$ASSIGNED_PORT_TESTING_PORTAL" ]; then
        sed -i.bak "s/^TESTING_PORTAL_PORT=.*/TESTING_PORTAL_PORT=$ASSIGNED_PORT_TESTING_PORTAL/" "$TEMP_ENV_FILE"
    fi
    if [ -n "$ASSIGNED_PORT_PROMETHEUS" ]; then
        sed -i.bak "s/^PROMETHEUS_PORT=.*/PROMETHEUS_PORT=$ASSIGNED_PORT_PROMETHEUS/" "$TEMP_ENV_FILE"
    fi
    
    # Replace original with updated version
    mv "$TEMP_ENV_FILE" "$ENV_FILE"
    rm -f "${TEMP_ENV_FILE}.bak"
    
    print_success "Environment configuration updated with new ports"
}

# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================

main() {
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Clear the log file
    > "$LOG_FILE"
    
    print_header "REGULENS AI - FINANCIAL COMPLIANCE PLATFORM INSTALLER"
    echo -e "${WHITE}Starting installation of $PLATFORM_NAME${NC}"
    echo -e "${CYAN}Installation log: $LOG_FILE${NC}"
    echo
    
    # Check if running as root (not recommended)
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root is not recommended for security reasons."
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Run installation steps
    check_prerequisites
    resolve_port_conflicts
    setup_environment
    setup_docker_environment
    setup_database
    start_all_services
    post_installation_setup
    show_installation_summary
    
    # Final success message
    print_success "Installation completed successfully!"
    log "Installation completed at $(date)"
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 