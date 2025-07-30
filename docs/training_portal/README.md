# RegulensAI Training Portal

## Overview

The RegulensAI Training Portal is a comprehensive web-based training platform that provides interactive learning experiences, progress tracking, assessments, certificates, and collaborative features. Built with enterprise-grade security and scalability in mind.

## Features

### 🎓 Interactive Training Modules
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Interactive Content**: Code examples, exercises, quizzes, and hands-on activities
- **Progress Tracking**: Real-time progress monitoring with detailed analytics
- **Bookmarks**: Save important sections and create personal learning notes
- **Search Functionality**: Advanced search with filters and semantic matching

### 📊 Assessment & Certification
- **Interactive Quizzes**: Multiple choice, text, and practical assessments
- **Automated Scoring**: Instant feedback with detailed explanations
- **Digital Certificates**: PDF and image certificates with QR code verification
- **Achievement System**: Badges and milestones for learning accomplishments
- **Certificate Verification**: Public verification system with unique codes

### 💬 Collaborative Learning
- **Discussion Forums**: Module-specific Q&A and knowledge sharing
- **Voting System**: Community-driven content quality through upvoting
- **Expert Moderation**: Pinned posts and verified answers
- **Social Features**: Share achievements and certificates on social media

### 📈 Analytics & Reporting
- **Learning Analytics**: Detailed progress tracking and performance metrics
- **Engagement Metrics**: Time spent, completion rates, and learning patterns
- **Custom Reports**: Exportable reports for compliance and training records
- **Real-time Dashboards**: Live monitoring of training activities

## Architecture

### Frontend Components
- **React 18** with Material-UI for responsive design
- **Progressive Web App** capabilities for offline access
- **Real-time updates** using WebSocket connections
- **Accessibility** compliant with WCAG 2.1 AA standards

### Backend Services
- **Flask REST API** with JWT authentication
- **PostgreSQL** database with optimized indexing
- **Redis** for caching and session management
- **Celery** for background task processing

### Infrastructure
- **Kubernetes** deployment with auto-scaling
- **AWS S3** for content storage and delivery
- **CloudFront CDN** for global content distribution
- **Prometheus & Grafana** for monitoring and alerting

## Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.9+ with pip
- PostgreSQL 13+
- Redis 6+
- Docker and Docker Compose (for development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/gaigenticai/RegulensAI.git
   cd RegulensAI
   ```

2. **Install dependencies**
   ```bash
   # Frontend
   cd core_infra/ui
   npm install

   # Backend
   cd ../..
   pip install -r requirements.txt
   ```

3. **Set up database**
   ```bash
   # Create database
   createdb regulensai_training

   # Run migrations
   python -m alembic upgrade head

   # Load training content
   python scripts/training_content_converter.py
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start development servers**
   ```bash
   # Backend
   python app.py

   # Frontend (in another terminal)
   cd core_infra/ui
   npm start
   ```

### Production Deployment

1. **Build Docker images**
   ```bash
   docker build -t regulensai/training-portal:latest .
   ```

2. **Deploy to Kubernetes**
   ```bash
   kubectl apply -f k8s/training-portal/
   ```

3. **Configure monitoring**
   ```bash
   kubectl apply -f k8s/training-portal/monitoring.yaml
   ```

## API Documentation

### Authentication
All API endpoints require JWT authentication except for certificate verification.

```bash
# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {...}
}
```

### Training Modules

```bash
# Get all modules
GET /api/v1/training/modules?category=notification_management&difficulty=intermediate

# Get specific module
GET /api/v1/training/modules/{module_id}

# Search modules
GET /api/v1/training/modules/search?q=notification&category=all
```

### Enrollments

```bash
# Enroll in module
POST /api/v1/training/enrollments
{
  "module_id": "uuid",
  "target_completion_date": "2024-12-31T23:59:59Z"
}

# Update section progress
POST /api/v1/training/enrollments/{enrollment_id}/sections/{section_id}/progress
{
  "status": "completed",
  "time_spent_minutes": 30,
  "notes": "Section completed successfully"
}
```

### Certificates

```bash
# Generate certificate
POST /api/v1/training/certificates/generate
{
  "enrollment_id": "uuid"
}

# Download certificate
GET /api/v1/training/certificates/{certificate_id}/download?format=pdf

# Verify certificate
GET /api/v1/training/certificates/verify/{verification_code}
```

## Content Management

### Training Content Structure

Training modules are organized hierarchically:

```
Module
├── Sections (ordered)
│   ├── Content (Markdown/HTML)
│   ├── Interactive Elements
│   │   ├── Code Exercises
│   │   ├── Quizzes
│   │   └── Checklists
│   └── Progress Tracking
└── Assessments
    ├── Questions
    ├── Scoring Rules
    └── Certificates
```

### Content Conversion

Use the training content converter to transform existing markdown documentation:

```bash
python scripts/training_content_converter.py
```

This will:
- Parse markdown files into interactive sections
- Extract code examples as exercises
- Generate quiz questions from content
- Create database insert statements

### Content Guidelines

1. **Accessibility**: Use semantic HTML and proper heading structure
2. **Interactivity**: Include exercises and quizzes every 10-15 minutes
3. **Progressive Disclosure**: Break complex topics into digestible sections
4. **Multimedia**: Use images, videos, and interactive elements appropriately
5. **Assessment**: Align assessments with learning objectives

## Security

### Authentication & Authorization
- JWT tokens with configurable expiration
- Role-based access control (RBAC)
- Multi-factor authentication support
- Session management with Redis

### Data Protection
- Encryption at rest and in transit
- PII data anonymization
- GDPR compliance features
- Audit logging for all actions

### Infrastructure Security
- Network policies for pod-to-pod communication
- Service mesh with mTLS
- Regular security scanning
- Vulnerability management

## Monitoring & Observability

### Metrics
- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: Enrollment rates, completion rates, certificate generation
- **Infrastructure Metrics**: CPU, memory, disk, network usage
- **Custom Metrics**: Active users, concurrent sessions, content engagement

### Logging
- Structured logging with JSON format
- Centralized log aggregation with ELK stack
- Log retention and archival policies
- Security event monitoring

### Alerting
- Prometheus alerting rules for critical issues
- PagerDuty integration for incident response
- Slack notifications for warnings
- Email alerts for certificate generation

## Performance Optimization

### Caching Strategy
- **Redis**: Session data, user preferences, frequently accessed content
- **CDN**: Static assets, images, videos
- **Database**: Query result caching, connection pooling
- **Application**: In-memory caching for configuration data

### Auto-scaling
- **Horizontal Pod Autoscaler**: CPU, memory, and custom metrics
- **Vertical Pod Autoscaler**: Right-sizing containers
- **Cluster Autoscaler**: Node scaling based on demand
- **Predictive Scaling**: ML-based scaling for known patterns

### Database Optimization
- **Indexing**: Optimized indexes for common queries
- **Partitioning**: Time-based partitioning for analytics data
- **Read Replicas**: Separate read and write workloads
- **Connection Pooling**: Efficient database connection management

## Testing

### Unit Tests
```bash
# Run unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=core_infra --cov-report=html
```

### Integration Tests
```bash
# Run integration tests
pytest tests/integration/ -v

# Specific test file
pytest tests/integration/test_training_portal.py -v
```

### End-to-End Tests
```bash
# Run E2E tests
npm run test:e2e

# Specific test suite
npm run test:e2e -- --spec="training-workflow.spec.js"
```

### Load Testing
```bash
# Run load tests
k6 run tests/load/training_portal_load_test.js

# With custom parameters
k6 run --vus 100 --duration 5m tests/load/training_portal_load_test.js
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database credentials and connectivity
   - Verify connection pool settings
   - Monitor database resource usage

2. **Certificate Generation Failures**
   - Check file system permissions
   - Verify S3 bucket access
   - Monitor background job queue

3. **High Memory Usage**
   - Review caching configuration
   - Check for memory leaks in application code
   - Monitor garbage collection metrics

4. **Slow Response Times**
   - Analyze database query performance
   - Check CDN cache hit rates
   - Review application profiling data

### Debug Mode

Enable debug mode for detailed logging:

```bash
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
python app.py
```

### Health Checks

Monitor application health:

```bash
# Application health
curl http://localhost:8080/health

# Database connectivity
curl http://localhost:8080/health/database

# Redis connectivity
curl http://localhost:8080/health/redis
```

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite
4. Submit pull request
5. Code review and approval
6. Merge to main

### Code Standards

- **Python**: Follow PEP 8 with Black formatting
- **JavaScript**: ESLint with Airbnb configuration
- **Documentation**: Comprehensive docstrings and comments
- **Testing**: Minimum 80% code coverage

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

## Support

### Documentation
- [API Reference](./api_reference.md)
- [User Guide](./user_guide.md)
- [Administrator Guide](./admin_guide.md)
- [Troubleshooting Guide](./troubleshooting.md)

### Community
- [GitHub Issues](https://github.com/gaigenticai/RegulensAI/issues)
- [Discussion Forum](https://github.com/gaigenticai/RegulensAI/discussions)
- [Slack Channel](https://regulensai.slack.com/channels/training-portal)

### Enterprise Support
For enterprise customers:
- 24/7 technical support
- Dedicated customer success manager
- Priority bug fixes and feature requests
- Custom training and onboarding

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and releases.
