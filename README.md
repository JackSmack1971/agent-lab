# Agent Lab

[![Test Coverage](https://img.shields.io/badge/coverage->90%25-brightgreen.svg)](tests/README.md)

Agent Lab is a Gradio-based platform for configuring, testing, and comparing AI agents powered by OpenRouter-hosted language models. Features real-time cost monitoring and optimization suggestions to help manage AI conversation expenses.

## Features

### 🤖 Agent Testing
- Configure and test AI agents with multiple OpenRouter-hosted models
- Real-time streaming responses with cancellation support
- Session persistence and management
- Model catalog with dynamic updates and fallbacks
- Comprehensive keyboard shortcuts for enhanced productivity

### 💰 Cost Optimizer
- Real-time cost tracking during conversations
- Budget management and spending alerts
- Historical cost trends and analytics
- AI-powered optimization suggestions (context reduction, model switching, caching)
- Interactive cost visualization with 7-day trends

## Getting Started

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

For reproducible builds, install from the lockfile:
```bash
pip install -r requirements.lock
```

For development with flexible version ranges:
```bash
pip install -r requirements.txt
```

**Note:** The `requirements.lock` file contains exact versions for consistent CI builds. Update it by installing dependencies and running `pip freeze > requirements.lock`.

### 3. Configure environment variables
Copy the example file and set your credentials:
```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder with your actual OpenRouter API key.

## Running the Application

### Local Development (Python)
Launch the development server with:
```bash
python app.py
```

### Docker Development
For containerized development with Docker:

1. **Build and run with Docker Compose** (recommended):
   ```bash
   # Set your OpenRouter API key
   export OPENROUTER_API_KEY="your-api-key-here"

   # Build and start the container
   docker-compose up --build
   ```

2. **Or build and run manually**:
   ```bash
   # Build the image
   docker build -t agent-lab .

   # Run the container
   docker run -p 7860:7860 \
     -e OPENROUTER_API_KEY="your-api-key-here" \
     -v $(pwd)/data:/app/data \
     agent-lab
   ```

The application will be available at `http://localhost:7860`.

**Note:** Data persistence is handled through volume mounts to the `./data` directory.

## Deployment

Agent Lab uses automated CI/CD pipelines with staging validation and production deployment. All deployments are containerized using Docker and follow blue-green deployment patterns for zero-downtime updates.

### Automated Deployment Pipeline

The CI/CD pipeline automatically handles:
- **Code Validation**: Tests, security scans, and coverage checks (>85%)
- **Container Build**: Docker image creation and registry push
- **Staging Deployment**: Automatic deployment to staging on main branch pushes
- **Staging Validation**: Health checks and functionality testing
- **Production Deployment**: Automatic promotion after staging validation
- **Production Validation**: Post-deployment health and performance checks
- **Notifications**: Slack alerts for deployment status and issues

#### Deployment Triggers
- **Automatic**: Push to `main` branch triggers full pipeline (staging → production)
- **Manual**: Use GitHub Actions workflow dispatch for targeted deployments
- **Rollback**: Automatic on production failures, manual for intentional rollbacks

### Deployment Environments

#### Staging Environment
- **URL**: Configured via `STAGING_URL` secret
- **Purpose**: Pre-production validation and testing
- **Validation**: Health checks, functionality tests, performance benchmarks
- **Promotion**: Automatic to production after successful validation

#### Production Environment
- **URL**: Configured via `PRODUCTION_URL` secret
- **Purpose**: Live user-facing application
- **Monitoring**: Real-time health checks and alerting
- **Rollback**: Automatic failure recovery with previous stable version

### Rollback Procedures

#### Automatic Rollback
Production deployments automatically rollback on:
- Health check failures
- Functionality test failures
- Performance degradation
- Deployment timeouts

#### Manual Rollback
For intentional rollbacks or complex issues:

1. **Access Rollback Workflow**: GitHub Actions → "Manual Rollback"
2. **Specify Parameters**:
   - Target environment (staging/production)
   - Rollback reason (required)
   - Target version/commit (optional)
3. **Execute**: Click "Run workflow"
4. **Monitor**: Watch real-time status via workflow logs and Slack notifications

#### Emergency Rollback
For critical incidents:
```bash
# Via GitHub CLI
gh workflow run rollback.yml \
  -f target_environment=production \
  -f rollback_reason="Critical security issue"
```

### Deployment Monitoring

#### Health Checks
- **Application Health**: `/health` endpoint monitoring
- **Data Integrity**: Session and telemetry data validation
- **Performance**: Response time and resource usage monitoring

#### Notifications
- **Slack Integration**: Real-time deployment status updates
- **Failure Alerts**: Immediate notification of deployment issues
- **Rollback Alerts**: Automatic notification of rollback execution

#### Deployment Records
All deployments create detailed records including:
- Commit SHA and timestamp
- Environment and validation results
- Test coverage and security scan results
- Rollback history and reasons

### Infrastructure Requirements

#### Required Secrets
Set these in GitHub repository secrets:
- `OPENROUTER_API_KEY`: OpenRouter API access
- `CONTAINER_REGISTRY`: Docker registry URL
- `CONTAINER_USERNAME`: Registry authentication
- `CONTAINER_PASSWORD`: Registry authentication
- `STAGING_URL`: Staging environment URL
- `PRODUCTION_URL`: Production environment URL
- `SLACK_WEBHOOK_URL`: Slack notifications (optional)

#### Hosting Platform
The pipeline is designed to work with:
- **AWS ECS/Fargate**: Container orchestration
- **Google Cloud Run**: Serverless containers
- **Azure Container Instances**: Cloud container hosting
- **Kubernetes**: Custom orchestration
- **Docker Compose**: Local/development deployments

### Deployment Validation

Before deploying, ensure:
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Security scan clean (`safety check`)
- [ ] Test coverage >85% (`pytest --cov=agents --cov=services`)
- [ ] Docker build successful (`docker build -t agent-lab .`)
- [ ] Required secrets configured in GitHub

### Troubleshooting Deployments

#### Common Issues
- **Build Failures**: Check Python version compatibility (3.11+)
- **Test Failures**: Run tests locally with `pytest --tb=long`
- **Health Check Failures**: Verify application starts with `python app.py`
- **Container Issues**: Test locally with `docker-compose up`

#### Logs and Debugging
- **Workflow Logs**: GitHub Actions → Workflows → Deployment
- **Container Logs**: Check hosting platform logs
- **Application Logs**: Access via `/logs` endpoint (if configured)
- **Deployment Records**: Download from workflow artifacts

## Keyboard Shortcuts

Agent Lab includes comprehensive keyboard shortcut support for enhanced productivity. Press `Ctrl + /` (or `Cmd + /` on Mac) to view all available shortcuts, or see the [complete keyboard shortcuts documentation](docs/docs/user/keyboard_shortcuts.md) for detailed reference.

## Security

Agent Lab takes security seriously. Please review our [Security Policy](docs/security/SECURITY.md) for information about:

- Reporting security vulnerabilities
- Security best practices
- Supported versions and security updates
- Data handling and privacy considerations

### Security Features
- Local-only data storage (no cloud transmission)
- API key environment variable protection
- Input validation and sanitization
- Domain-restricted web tool access
- Comprehensive security audit logging

## Testing

### Run Tests
```bash
# Run all tests with coverage
pytest --cov=agents --cov=services tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v
```

### Coverage Requirements
- Maintain >90% test coverage for `agents/` and `services/` directories
- See `tests/README.md` for detailed testing documentation

## Notes
- An active OpenRouter API key is required to interact with hosted models.
- Ensure Python 3.11 or 3.12 is used for the best compatibility.
