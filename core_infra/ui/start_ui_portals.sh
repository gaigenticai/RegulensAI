#!/bin/bash

# ============================================================================
# Regulens AI UI Portals Startup Script
# Starts Documentation Portal and Testing Portal
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if port is available
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port is already in use (required for $service)"
        print_status "Checking if it's our service..."
        
        # Try to get response from the port
        if curl -s -f "http://localhost:$port" >/dev/null 2>&1; then
            print_success "$service appears to be already running on port $port"
            return 0
        else
            print_error "Port $port is occupied by another service"
            return 1
        fi
    fi
    return 0
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" >/dev/null 2>&1; then
            print_success "$service is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service failed to start within expected time"
    return 1
}

# Main execution
main() {
    print_status "Starting Regulens AI UI Portals..."
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.ui.yml" ]; then
        print_error "docker-compose.ui.yml not found. Please run this script from the core_infra/ui directory."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "../.env" ]; then
        print_error ".env file not found in parent directory. Please ensure environment is configured."
        exit 1
    fi
    
    # Check required ports
    print_status "Checking port availability..."
    check_port 8000 "API Service" || exit 1
    check_port 8501 "Documentation Portal" || exit 1
    check_port 8502 "Testing Portal" || exit 1
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Create external network if it doesn't exist
    print_status "Setting up Docker network..."
    if ! docker network ls | grep -q "regulens-network"; then
        docker network create regulens-network
        print_success "Created regulens-network"
    else
        print_status "regulens-network already exists"
    fi
    
    # Start services
    print_status "Starting UI services with Docker Compose..."
    
    # Use docker compose (newer) or docker-compose (legacy)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # Build and start services
    $COMPOSE_CMD -f docker-compose.ui.yml up --build -d
    
    if [ $? -ne 0 ]; then
        print_error "Failed to start services"
        exit 1
    fi
    
    # Wait for services to be ready
    print_status "Verifying service health..."
    
    # Wait for API
    if ! wait_for_service "http://localhost:8000/v1/health" "API Service"; then
        print_warning "API Service not responding, but continuing with UI startup..."
    fi
    
    # Wait for Documentation Portal
    if ! wait_for_service "http://localhost:8501" "Documentation Portal"; then
        print_error "Documentation Portal failed to start"
        $COMPOSE_CMD -f docker-compose.ui.yml logs documentation-portal
        exit 1
    fi
    
    # Wait for Testing Portal
    if ! wait_for_service "http://localhost:8502" "Testing Portal"; then
        print_error "Testing Portal failed to start"
        $COMPOSE_CMD -f docker-compose.ui.yml logs testing-portal
        exit 1
    fi
    
    # Success message
    print_success "All UI portals are running successfully!"
    echo
    echo "==================================================================="
    echo "🚀 Regulens AI UI Portals Started Successfully"
    echo "==================================================================="
    echo
    echo "📚 Documentation Portal: http://localhost:8501"
    echo "   - Comprehensive user guides and API documentation"
    echo "   - Field-level explanations and deployment guides"
    echo "   - Advanced search functionality"
    echo
    echo "🧪 Testing Portal: http://localhost:8502"
    echo "   - Interactive service testing interface"
    echo "   - Real API endpoint testing"
    echo "   - Comprehensive test history and analytics"
    echo
    echo "📖 Enhanced API Documentation:"
    echo "   - Swagger UI: http://localhost:8000/docs"
    echo "   - ReDoc: http://localhost:8000/redoc"
    echo "   - OpenAPI JSON: http://localhost:8000/v1/openapi.json"
    echo
    echo "🔍 System Health:"
    echo "   - API Health: http://localhost:8000/v1/health"
    echo "   - Platform Info: http://localhost:8000/v1/info"
    echo "   - Metrics: http://localhost:8000/v1/metrics"
    echo
    echo "==================================================================="
    echo
    echo "📝 Usage Tips:"
    echo "• Use the Documentation Portal to understand all features"
    echo "• Use the Testing Portal to validate service functionality"
    echo "• Enhanced Swagger docs include comprehensive examples"
    echo "• All portals support real-time testing with live APIs"
    echo
    echo "🛠️ Management Commands:"
    echo "• View logs: $COMPOSE_CMD -f docker-compose.ui.yml logs -f"
    echo "• Stop services: $COMPOSE_CMD -f docker-compose.ui.yml down"
    echo "• Restart: $COMPOSE_CMD -f docker-compose.ui.yml restart"
    echo
}

# Trap ctrl-c and call cleanup
cleanup() {
    print_warning "Shutting down services..."
    $COMPOSE_CMD -f docker-compose.ui.yml down
    exit 0
}

trap cleanup INT

# Run main function
main "$@" 