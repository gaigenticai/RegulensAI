# 🖥️ Regulens AI User Interface Portals

This directory contains the web-based user interface portals for the Regulens AI Financial Compliance Platform.

## 🚀 Available Portals

### 📚 Documentation Portal (Port 8501)
Comprehensive documentation and user guides

**Features:**
- 🏠 **Platform Overview** - System introduction and key features
- 🛠️ **Services Guide** - Detailed service documentation  
- 🔌 **API Reference** - Complete API documentation with examples
- 📝 **Field Guide** - Field-level configuration documentation
- 🚀 **Deployment** - Step-by-step deployment instructions
- 🔧 **Configuration** - Environment variable reference
- 📋 **Complete Feature List** - **NEW!** Comprehensive catalog of all 60+ features across 6 phases
- 🏗️ **Software Architecture** - **NEW!** Complete technology stack with professional architecture diagram

**New Documentation Features:**

#### 📋 Complete Feature List Tab
- **60+ Features** organized by implementation phases (1-6)
- **Phase-by-phase breakdown** with completion status
- **Core capability categories** (Compliance, AI/ML, Workflow, Analytics, Integration, Infrastructure)
- **Supported integrations** for banking systems, GRC platforms, RPA tools, and AI providers
- **Feature statistics** and metrics dashboard

#### 🏗️ Software Architecture Tab  
- **Professional system architecture diagram** (Mermaid format)
- **Complete technology stack** with 40+ software components
- **Version information** and usage details for each technology
- **Performance specifications** and scalability metrics
- **System requirements** (minimum, recommended, enterprise)
- **Deployment architecture** patterns and best practices

### 🧪 Testing Portal (Port 8502)
Interactive service testing interface

## 🏗️ Architecture

```
core_infra/ui/
├── documentation_portal/
│   ├── app.py                 # Main documentation application
│   └── Dockerfile            # Container configuration
├── testing_portal/
│   ├── app.py                 # Interactive testing interface
│   └── Dockerfile            # Container configuration
├── swagger_config.py          # Enhanced Swagger configuration
├── requirements.txt           # Python dependencies
├── docker-compose.ui.yml      # UI services orchestration
├── start_ui_portals.sh        # Startup script
└── README.md                  # This file
```

## 🚀 Quick Start

### Option 1: Automatic (Recommended)
The UI portals are automatically started as part of the main installation:
```bash
./oneclickinstall.sh
```

### Option 2: Manual Start
From the `core_infra/ui` directory:
```bash
chmod +x start_ui_portals.sh
./start_ui_portals.sh
```

### Option 3: Docker Compose Only
```bash
cd core_infra/ui
docker-compose -f docker-compose.ui.yml up -d --build
```

## 📚 Documentation Portal Features

### 🔍 Advanced Search
- **Semantic Search**: Find content by meaning, not just keywords
- **Real-time Results**: Instant search as you type
- **Contextual Results**: Shows related configuration and API endpoints
- **Cross-reference Links**: Jump between related topics

### 📖 Comprehensive Guides
- **Platform Overview**: Architecture, features, and capabilities
- **Service Guides**: Detailed documentation for each service
- **API Reference**: Complete endpoint documentation with examples
- **Deployment Guide**: Step-by-step setup instructions
- **Configuration Guide**: All environment variables explained

### 🛠️ Interactive Features
- **Field-level Explanations**: Detailed descriptions for every parameter
- **Code Examples**: Copy-paste ready code snippets
- **Configuration Validation**: Check your settings
- **Troubleshooting**: Common issues and solutions

## 🧪 Testing Portal Features

### 🔌 Service Testing
- **All Endpoints**: Test every API endpoint interactively
- **Real Data**: Uses actual API calls, not mocks
- **Authentication**: Built-in login and token management
- **Request Builder**: Visual request construction

### 📊 Test Analytics
- **Test History**: Track all test executions
- **Performance Metrics**: Response times and success rates
- **Visualization**: Charts and graphs of test results
- **Export Capabilities**: Download test results

### 🔧 Developer Tools
- **cURL Generation**: Auto-generate cURL commands
- **Request/Response Inspector**: Detailed HTTP transaction views
- **Batch Testing**: Run comprehensive test suites
- **Error Debugging**: Detailed error information

## 📖 Enhanced Swagger Documentation

### ✨ Rich Examples
- **Comprehensive Request Examples**: Real-world use cases
- **Response Examples**: Success and error scenarios
- **Field Descriptions**: Detailed parameter explanations
- **Authentication Guides**: Security implementation details

### 🔗 Interactive Testing
- **Try It Out**: Execute requests directly from documentation
- **Authentication Integration**: Built-in auth handling
- **Parameter Validation**: Real-time input validation
- **Response Formatting**: Pretty-printed JSON responses

## 🔧 Configuration

All UI portals are configured through environment variables in the main `.env` file:

```bash
# Documentation Portal
DOCS_PORTAL_ENABLED=true
DOCS_PORTAL_PORT=8501
DOCS_SEARCH_ENABLED=true

# Testing Portal  
TESTING_PORTAL_ENABLED=true
TESTING_PORTAL_PORT=8502
TESTING_AUTO_LOGIN=true

# Enhanced Swagger
SWAGGER_UI_ENHANCED=true
SWAGGER_EXAMPLES_ENABLED=true
API_DOCS_ENHANCED=true
```

## 🐳 Docker Configuration

### Services
- **documentation-portal**: Streamlit-based documentation interface
- **testing-portal**: Interactive testing environment
- **api**: Main API service (dependency)

### Networks
All services use the `regulens-network` for internal communication.

### Health Checks
- Automated health monitoring for all services
- Graceful startup sequencing
- Automatic restart on failure

## 🔄 Development Workflow

### Local Development
```bash
# Install dependencies
cd core_infra/ui
pip install -r requirements.txt

# Run documentation portal
cd documentation_portal
streamlit run app.py --server.port=8501

# Run testing portal (in another terminal)
cd ../testing_portal
streamlit run app.py --server.port=8502
```

### Docker Development
```bash
# Build and run with auto-reload
docker-compose -f docker-compose.ui.yml up --build

# View logs
docker-compose -f docker-compose.ui.yml logs -f

# Restart specific service
docker-compose -f docker-compose.ui.yml restart documentation-portal
```

## 📋 Management Commands

### Service Management
```bash
# Start all UI portals
./start_ui_portals.sh

# Stop all UI portals
docker-compose -f docker-compose.ui.yml down

# Restart specific portal
docker-compose -f docker-compose.ui.yml restart testing-portal

# View logs
docker-compose -f docker-compose.ui.yml logs -f documentation-portal
```

### Health Checks
```bash
# Check documentation portal
curl http://localhost:8501

# Check testing portal
curl http://localhost:8502

# Check enhanced API docs
curl http://localhost:8000/docs
```

## 🚀 Usage Examples

### Documentation Portal
1. Visit `http://localhost:8501`
2. Use the search bar to find specific topics
3. Navigate through sections using the sidebar
4. Copy configuration examples and code snippets
5. Follow deployment guides step-by-step

### Testing Portal
1. Visit `http://localhost:8502`
2. Test API connection with "Test API Connection"
3. Login using "Quick Login (Test User)"
4. Select a service and endpoint to test
5. Modify request data and execute tests
6. Review results and test history

### Enhanced Swagger
1. Visit `http://localhost:8000/docs`
2. Expand endpoint sections for details
3. Click "Try it out" to test endpoints
4. Use provided examples or customize requests
5. Review comprehensive response documentation

## 🔍 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Check what's using the port
lsof -i :8501

# Kill process if needed
kill -9 $(lsof -t -i:8501)
```

**Docker Network Issues**
```bash
# Recreate network
docker network rm regulens-network
docker network create regulens-network
```

**Service Not Starting**
```bash
# Check logs for errors
docker-compose -f docker-compose.ui.yml logs documentation-portal

# Rebuild with no cache
docker-compose -f docker-compose.ui.yml build --no-cache
```

### Performance Optimization

**Streamlit Performance**
- Set `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`
- Use `--server.runOnSave=false` for production
- Enable caching for expensive operations

**Container Resources**
- Allocate sufficient memory (minimum 1GB per portal)
- Use volume mounts for development
- Implement health checks for reliability

## 🛡️ Security Considerations

### Authentication
- Testing portal uses the main API authentication
- Documentation portal is read-only, no sensitive data exposure
- All API calls go through the secure API layer

### Network Security
- All services communicate over internal Docker network
- No direct database access from UI portals
- Rate limiting applies to all API calls

### Data Privacy
- No sensitive data is stored in UI portal containers
- All test data is ephemeral
- Authentication tokens are managed securely

## 📈 Monitoring and Analytics

### Metrics Available
- **Portal Usage**: Page views, search queries, test executions
- **API Testing**: Response times, success rates, error patterns
- **User Behavior**: Feature usage, documentation section popularity

### Integration with Observability
- Jaeger tracing for UI portal requests
- Prometheus metrics for portal performance
- Structured logging for debugging

## 🤝 Contributing

### Adding New Documentation
1. Update `documentation_portal/app.py`
2. Add new sections to the documentation data structure
3. Include search keywords and cross-references
4. Test the new content thoroughly

### Adding New Test Cases
1. Update `testing_portal/app.py`
2. Add new endpoints to the service definitions
3. Include realistic test data examples
4. Validate with actual API responses

### Enhancing Swagger Documentation
1. Update `swagger_config.py`
2. Add new examples and field descriptions
3. Test with actual API endpoints
4. Ensure comprehensive coverage

## 📞 Support

For issues related to the UI portals:

1. **Check the logs**: `docker-compose -f docker-compose.ui.yml logs -f`
2. **Verify API connectivity**: Test `http://localhost:8000/v1/health`
3. **Review configuration**: Check environment variables in `.env`
4. **Restart services**: `./start_ui_portals.sh`

For feature requests or bugs, please refer to the main project documentation portal at `http://localhost:8501` for comprehensive troubleshooting guides. 