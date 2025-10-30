# Trello Clone - SaaS Task Management Platform

A production-ready, enterprise-grade task management system built with **Clean Architecture** and **Domain-Driven Design** principles.

## 🏗️ Architecture

This project implements Clean Architecture with 5 bounded contexts:

- **Users** - User management, authentication, authorization
- **Projects** - Project organization and configuration
- **Tasks** - Task creation, assignment, and tracking
- **Notifications** - Real-time notifications and email delivery
- **Audit** - Security audit logging and compliance

See [Architecture Documentation](./docs/architecture/README.md) for comprehensive technical details.

## 🚀 Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: MySQL 8.0, SQLAlchemy 2.0, Alembic
- **Cache**: Redis 7
- **Message Queue**: Celery with Redis broker
- **Observability**: OpenTelemetry, Prometheus, Grafana
- **Deployment**: Docker, AWS ECS Fargate, Terraform
- **CI/CD**: GitHub Actions

## 📋 Prerequisites

- Python 3.11 or higher
- Docker & Docker Compose
- MySQL 8.0 (or use Docker Compose)
- Redis 7 (or use Docker Compose)

## 🛠️ Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/trello-clone.git
cd trello-clone
```

### 2. Set Up Python Environment

```bash

# Create virtual environment

python -m venv venv

# Activate virtual environment

# On Windows:

venv\\Scripts\\activate

# On macOS/Linux:

source venv/bin/activate

# Install dependencies

pip install -e ".[dev]"
```

### 3. Configure Environment

```bash

# Copy example environment file

cp .env.example .env

# Edit .env with your configuration

# Update database credentials, secret keys, etc.

```

### 4. Start Services with Docker Compose

```bash

# Start MySQL, Redis, Prometheus, Grafana

docker-compose -f docker/docker-compose.yml up -d mysql redis prometheus grafana

# Wait for services to be healthy

docker-compose -f docker/docker-compose.yml ps
```

### 5. Run Database Migrations

```bash

# Run Alembic migrations

alembic upgrade head
```

### 6. Start the Application

```bash

# Start FastAPI development server

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery worker

celery -A src.infrastructure.messaging.celery.app worker --loglevel=info
```

### 7. Verify Installation

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

## 🧪 Running Tests

```bash

# Run all tests

pytest

# Run with coverage

pytest --cov=src --cov-report=html --cov-report=term

# Run specific test types

pytest tests/unit # Unit tests only
pytest tests/integration # Integration tests only
pytest tests/contract # Contract tests only

# Run with markers

pytest -m "not slow" # Skip slow tests
```

## 🔍 Code Quality

```bash

# Linting with Ruff

ruff check src/ tests/

# Format with Black

black src/ tests/

# Type checking with MyPy

mypy src/

# Security scanning

bandit -r src/ -ll
safety check

# Run all quality checks

ruff check src/ tests/ && black --check src/ tests/ && mypy src/
```

## 🐳 Docker Development

```bash

# Build and run entire stack

docker-compose -f docker/docker-compose.yml up --build

# Run in detached mode

docker-compose -f docker/docker-compose.yml up -d

# View logs

docker-compose -f docker/docker-compose.yml logs -f api

# Stop services

docker-compose -f docker/docker-compose.yml down

# Clean up volumes

docker-compose -f docker/docker-compose.yml down -v
```

## 📚 Project Structure

```
trello-clone/
├── src/ # Source code
│ ├── domain/ # Domain layer (entities, value objects, events)
│ │ ├── users/
│ │ ├── projects/
│ │ ├── tasks/
│ │ ├── notifications/
│ │ └── audit/
│ ├── application/ # Application layer (use cases, services)
│ │ ├── users/
│ │ ├── projects/
│ │ ├── tasks/
│ │ ├── notifications/
│ │ └── audit/
│ ├── infrastructure/ # Infrastructure layer (databases, external services)
│ │ ├── persistence/
│ │ ├── messaging/
│ │ ├── external_services/
│ │ └── observability/
│ ├── interface/ # Interface layer (API endpoints)
│ │ └── api/v1/
│ └── shared/ # Shared utilities and configuration
│ └── config/
├── tests/ # Test suite
│ ├── unit/
│ ├── integration/
│ └── contract/
├── docs/ # Documentation
│ └── architecture/ # Architecture documentation
├── docker/ # Docker configuration
│ ├── Dockerfile
│ └── docker-compose.yml
├── alembic/ # Database migrations
│ └── versions/
├── .github/ # GitHub Actions workflows
│ └── workflows/
├── pyproject.toml # Project metadata and dependencies
└── README.md # This file
```

## 📖 Documentation

- **[Architecture Documentation](./docs/architecture/README.md)** - Comprehensive system architecture
- **[Quick Reference](./docs/architecture/QUICK_REFERENCE.md)** - One-page cheat sheet
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[FAQ](./docs/architecture/FAQ.md)** - Frequently asked questions

## 🤝 Contributing

1. Read the [Architecture Documentation](./docs/architecture/README.md)
2. Follow [Clean Architecture guidelines](./docs/architecture/layers.md)
3. Review [Coding Standards](./.github/copilot-instructions.md)
4. Write tests (minimum 80% coverage)
5. Run code quality checks before committing
6. Submit pull request with clear description

## 📝 Development Workflow

1. Create feature branch from `develop`
2. Implement feature following Clean Architecture layers
3. Write unit and integration tests
4. Run quality checks locally
5. Submit PR to `develop`
6. CI pipeline runs automatically
7. After approval, merge to `develop`
8. Release to `main` triggers production deployment

## 🔐 Security

- All passwords hashed with bcrypt
- JWT tokens for authentication
- RBAC for authorization
- TLS 1.3 in production
- Security audit logging
- Regular dependency updates
- OWASP Top 10 compliance

See [Security Architecture](./docs/architecture/security/README.md) for details.

## 📊 Monitoring

- **Logs**: Structured JSON logging with CloudWatch
- **Metrics**: Prometheus metrics exposed at `/metrics`
- **Tracing**: OpenTelemetry distributed tracing
- **Dashboards**: Grafana dashboards for visualization
- **Alerts**: CloudWatch alarms for critical issues

See [Observability Documentation](./docs/architecture/observability/README.md).

## 🚀 Deployment

### Staging

Pushes to `main` branch automatically deploy to staging environment.

### Production

Tagged releases (`v*`) deploy to production with blue-green deployment.

See [Deployment Documentation](./docs/architecture/deployment/README.md).

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 👥 Team

For questions or support, contact:

- Architecture Team: architecture@example.com
- DevOps Team: devops@example.com

## 🔗 Links

- **Production**: https://trello-clone.example.com
- **Staging**: https://staging.trello-clone.example.com
- **Documentation**: https://docs.trello-clone.example.com
- **Status Page**: https://status.trello-clone.example.com

---

Built with ❤️ using Clean Architecture and Domain-Driven Design
