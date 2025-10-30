# Container Architecture

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines the container architecture for the Task Management System, covering Docker image construction, multi-stage builds, security hardening, and optimization strategies for production deployments on AWS ECS.

---

## Container Strategy

### Design Principles

1. **Minimal Base Images**: Use Alpine or distroless for smaller attack surface
2. **Multi-Stage Builds**: Separate build and runtime dependencies
3. **Immutable Images**: No runtime modifications, rebuild for changes
4. **Security First**: Run as non-root, scan for vulnerabilities
5. **Reproducible Builds**: Pin all dependencies, use lock files

### Container Types

| Container      | Purpose                    | Base Image         | Size Target |
| -------------- | -------------------------- | ------------------ | ----------- |
| **API**        | FastAPI application        | python:3.11-slim   | < 200 MB    |
| **Worker**     | Celery background tasks    | python:3.11-slim   | < 200 MB    |
| **Migrations** | Database schema migrations | python:3.11-alpine | < 150 MB    |
| **CLI**        | Management commands        | python:3.11-alpine | < 150 MB    |

---

## API Container

### Dockerfile

```dockerfile
# ============================================================================
# Stage 1: Builder - Install dependencies and build artifacts
# ============================================================================
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to not create virtual env (we're in a container)
RUN poetry config virtualenvs.create false

# Install Python dependencies
RUN poetry install --only main --no-interaction --no-ansi --no-root

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install application
RUN poetry build && pip install --no-cache-dir dist/*.whl

# ============================================================================
# Stage 2: Runtime - Minimal runtime environment
# ============================================================================
FROM python:3.11-slim AS runtime

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /build/src /app/src
COPY --from=builder /build/alembic /app/alembic
COPY --from=builder /build/alembic.ini /app/

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "taskmanager.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build Optimization

**Multi-Stage Benefits**:

- Builder stage: 800 MB (with build tools)
- Runtime stage: 180 MB (only runtime deps)
- **Reduction**: 77% smaller final image

**Layer Caching Strategy**:

```dockerfile
# 1. Copy dependency files first (changes infrequently)
COPY pyproject.toml poetry.lock ./

# 2. Install dependencies (cached unless deps change)
RUN poetry install --only main

# 3. Copy application code last (changes frequently)
COPY src/ ./src/
```

### Security Hardening

**1. Non-Root User**:

```dockerfile
# Create dedicated user with specific UID
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
USER appuser
```

**2. Read-Only Root Filesystem** (ECS task definition):

```json
{
  "readonlyRootFilesystem": true,
  "mountPoints": [
    {
      "sourceVolume": "tmp",
      "containerPath": "/tmp",
      "readOnly": false
    }
  ]
}
```

**3. Drop Capabilities**:

```json
{
  "linuxParameters": {
    "capabilities": {
      "drop": ["ALL"]
    }
  }
}
```

---

## Worker Container

### Dockerfile

```dockerfile
# ============================================================================
# Stage 1: Builder (same as API)
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.7.0

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-interaction --no-ansi --no-root

COPY src/ ./src/
RUN poetry build && pip install --no-cache-dir dist/*.whl

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r celeryuser && useradd -r -g celeryuser -u 1001 celeryuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build/src /app/src

RUN chown -R celeryuser:celeryuser /app

USER celeryuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    C_FORCE_ROOT=false

# Health check for Celery worker
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A taskmanager.celery inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker
CMD ["celery", "-A", "taskmanager.celery", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=1000"]
```

### Worker Configuration

**Environment Variables**:

```bash
# Core settings
CELERY_BROKER_URL=redis://taskmanager-cache.xxx.cache.amazonaws.com:6379/0
CELERY_RESULT_BACKEND=redis://taskmanager-cache.xxx.cache.amazonaws.com:6379/1
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=["json"]
CELERY_TIMEZONE=UTC
CELERY_ENABLE_UTC=true

# Performance
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_WORKER_CONCURRENCY=4

# Monitoring
CELERY_WORKER_SEND_TASK_EVENTS=true
CELERY_TASK_SEND_SENT_EVENT=true
```

---

## Migrations Container

### Dockerfile

```dockerfile
# ============================================================================
# Minimal migration runner using Alpine
# ============================================================================
FROM python:3.11-alpine AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    postgresql-client \
    libpq

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi --no-root

# Copy migration files
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY src/taskmanager/domain/models/ ./src/taskmanager/domain/models/

# Create non-root user
RUN addgroup -g 1002 migrator && \
    adduser -D -u 1002 -G migrator migrator

RUN chown -R migrator:migrator /app

USER migrator

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Run migrations
CMD ["alembic", "upgrade", "head"]
```

### Migration Strategy

**Pre-Deployment Migrations**:

```bash
# Run as ECS task before deploying new API version
aws ecs run-task \
  --cluster prod \
  --task-definition taskmanager-migrations:5 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxx"],
      "securityGroups": ["sg-xxx"],
      "assignPublicIp": "DISABLED"
    }
  }'

# Wait for completion
aws ecs wait tasks-stopped \
  --cluster prod \
  --tasks <task-arn>

# Check exit code
aws ecs describe-tasks \
  --cluster prod \
  --tasks <task-arn> \
  --query 'tasks[0].containers[0].exitCode'
```

---

## Image Optimization

### Size Optimization

**Techniques**:

1. **Use Slim Base Images**:

```dockerfile
# ❌ Full image: 900 MB
FROM python:3.11

# ✅ Slim image: 120 MB
FROM python:3.11-slim

# ✅ Alpine image: 50 MB (but slower builds)
FROM python:3.11-alpine
```

2. **Multi-Stage Builds**:

```dockerfile
# ❌ Single stage: All build tools in final image (800 MB)
FROM python:3.11-slim
RUN apt-get install build-essential
COPY . .
RUN poetry install

# ✅ Multi-stage: Only runtime in final image (180 MB)
FROM python:3.11-slim AS builder
RUN apt-get install build-essential
RUN poetry install

FROM python:3.11-slim AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
```

3. **Remove Package Manager Cache**:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    package1 package2 \
    && rm -rf /var/lib/apt/lists/*
```

4. **Minimize Layers**:

```dockerfile
# ❌ Multiple layers
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2
RUN rm -rf /var/lib/apt/lists/*

# ✅ Single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends package1 package2 && \
    rm -rf /var/lib/apt/lists/*
```

5. **Use .dockerignore**:

```dockerignore
# .dockerignore
.git/
.github/
.vscode/
tests/
docs/
*.md
.pytest_cache/
.coverage
.env
*.pyc
__pycache__/
```

### Build Performance

**BuildKit Features**:

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with cache mount (faster dependency installs)
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --cache-from taskmanager-api:latest \
  --tag taskmanager-api:v1.2.3 \
  .
```

**Layer Caching Strategy**:

```dockerfile
# Order by change frequency (least to most)
COPY pyproject.toml poetry.lock ./      # Changes rarely
RUN poetry install                       # Cached unless above changes
COPY alembic/ ./alembic/                # Changes occasionally
COPY src/ ./src/                        # Changes frequently
```

---

## Image Tagging Strategy

### Tagging Convention

```bash
# Format: <registry>/<repository>:<version>-<commit>-<timestamp>
123456789012.dkr.ecr.us-east-1.amazonaws.com/taskmanager-api:v1.2.3-abc1234-20251030T143022Z

# Components:
# - v1.2.3: Semantic version from git tag
# - abc1234: Short commit SHA
# - 20251030T143022Z: Build timestamp (UTC)
```

### Tag Types

**1. Version Tags** (immutable):

```bash
taskmanager-api:v1.2.3
taskmanager-api:v1.2.3-abc1234
taskmanager-api:v1.2.3-abc1234-20251030T143022Z
```

**2. Environment Tags** (mutable):

```bash
taskmanager-api:latest           # Latest build from main
taskmanager-api:staging          # Currently deployed to staging
taskmanager-api:production       # Currently deployed to production
```

**3. Branch Tags** (mutable):

```bash
taskmanager-api:main
taskmanager-api:develop
taskmanager-api:feature-xyz
```

### Tagging Script

```bash
#!/bin/bash
# scripts/tag-image.sh

set -euo pipefail

IMAGE_NAME=${1:-taskmanager-api}
GIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "v0.0.0")
GIT_SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
REGISTRY="123456789012.dkr.ecr.us-east-1.amazonaws.com"

# Build full tag
FULL_TAG="${GIT_TAG}-${GIT_SHA}-${TIMESTAMP}"

# Build image with multiple tags
docker build \
  --tag "${REGISTRY}/${IMAGE_NAME}:${FULL_TAG}" \
  --tag "${REGISTRY}/${IMAGE_NAME}:${GIT_TAG}" \
  --tag "${REGISTRY}/${IMAGE_NAME}:${GIT_SHA}" \
  --tag "${REGISTRY}/${IMAGE_NAME}:latest" \
  --build-arg VERSION="${GIT_TAG}" \
  --build-arg COMMIT="${GIT_SHA}" \
  --build-arg BUILD_DATE="${TIMESTAMP}" \
  .

echo "Built image: ${REGISTRY}/${IMAGE_NAME}:${FULL_TAG}"
```

---

## Security Scanning

### Container Scanning Tools

**1. Trivy** (vulnerability scanner):

```bash
# Scan image for vulnerabilities
trivy image --severity HIGH,CRITICAL \
  taskmanager-api:v1.2.3

# Scan during build
docker build -t taskmanager-api:v1.2.3 .
trivy image --exit-code 1 --severity CRITICAL \
  taskmanager-api:v1.2.3

# CI integration
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: taskmanager-api:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: 1
```

**2. ECR Image Scanning**:

```bash
# Enable scan on push
aws ecr put-image-scanning-configuration \
  --repository-name taskmanager-api \
  --image-scanning-configuration scanOnPush=true

# View scan results
aws ecr describe-image-scan-findings \
  --repository-name taskmanager-api \
  --image-id imageTag=v1.2.3
```

**3. Hadolint** (Dockerfile linter):

```bash
# Lint Dockerfile
hadolint Dockerfile

# CI integration
docker run --rm -i hadolint/hadolint < Dockerfile
```

### Security Best Practices

**Checklist**:

- ✅ Use official base images from trusted sources
- ✅ Pin specific versions (not `latest`)
- ✅ Run as non-root user
- ✅ Scan for vulnerabilities before deployment
- ✅ Use read-only root filesystem
- ✅ Drop unnecessary capabilities
- ✅ Set resource limits (CPU, memory)
- ✅ Use secrets management (not environment variables)
- ✅ Minimize installed packages
- ✅ Keep base images updated

---

## Container Registry

### Amazon ECR Configuration

**Repository Setup**:

```bash
# Create repositories
aws ecr create-repository \
  --repository-name taskmanager-api \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS

aws ecr create-repository \
  --repository-name taskmanager-worker \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS

# Set lifecycle policy (keep last 10 versions)
aws ecr put-lifecycle-policy \
  --repository-name taskmanager-api \
  --lifecycle-policy-text file://ecr-lifecycle-policy.json
```

**Lifecycle Policy**:

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 production images",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["v"],
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Remove untagged images after 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

### Image Push Workflow

```bash
#!/bin/bash
# scripts/push-image.sh

set -euo pipefail

IMAGE_NAME=${1}
VERSION=${2}
REGISTRY="123456789012.dkr.ecr.us-east-1.amazonaws.com"

# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ${REGISTRY}

# Push all tags
docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
docker push ${REGISTRY}/${IMAGE_NAME}:latest

echo "Pushed ${IMAGE_NAME}:${VERSION} to ECR"
```

---

## Local Development

### Docker Compose for Local Development

```yaml
# docker-compose.yml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://taskmanager:password@postgres:5432/taskmanager
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
    depends_on:
      - postgres
      - redis
    volumes:
      - ./src:/app/src # Hot reload
    command: uvicorn taskmanager.api.main:app --host 0.0.0.0 --reload

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
      target: runtime
    environment:
      - DATABASE_URL=postgresql://taskmanager:password@postgres:5432/taskmanager
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - ENVIRONMENT=development
    depends_on:
      - postgres
      - redis
    volumes:
      - ./src:/app/src
    command: celery -A taskmanager.celery worker --loglevel=info

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=taskmanager
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=taskmanager
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Development Dockerfile

```dockerfile
# Dockerfile.dev - Optimized for fast iteration
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (including dev dependencies)
RUN poetry config virtualenvs.create false && \
    poetry install --with dev --no-interaction

# Copy source (will be overridden by volume mount)
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["uvicorn", "taskmanager.api.main:app", "--host", "0.0.0.0", "--reload"]
```

---

## Build Automation

### GitHub Actions Workflow

```yaml
# .github/workflows/build-images.yml
name: Build and Push Container Images

on:
  push:
    branches: [main, develop]
    tags: ["v*"]
  pull_request:
    branches: [main]

env:
  ECR_REGISTRY: 123456789012.dkr.ecr.us-east-1.amazonaws.com
  AWS_REGION: us-east-1

jobs:
  build-api:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Extract metadata
        id: meta
        run: |
          VERSION=$(git describe --tags --always --dirty)
          SHA=$(git rev-parse --short HEAD)
          TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
          echo "version=${VERSION}" >> $GITHUB_OUTPUT
          echo "sha=${SHA}" >> $GITHUB_OUTPUT
          echo "timestamp=${TIMESTAMP}" >> $GITHUB_OUTPUT

      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          push: true
          tags: |
            ${{ env.ECR_REGISTRY }}/taskmanager-api:${{ steps.meta.outputs.version }}
            ${{ env.ECR_REGISTRY }}/taskmanager-api:${{ steps.meta.outputs.sha }}
            ${{ env.ECR_REGISTRY }}/taskmanager-api:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VERSION=${{ steps.meta.outputs.version }}
            COMMIT=${{ steps.meta.outputs.sha }}
            BUILD_DATE=${{ steps.meta.outputs.timestamp }}

      - name: Scan image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.ECR_REGISTRY }}/taskmanager-api:${{ steps.meta.outputs.sha }}
          severity: CRITICAL,HIGH
          exit-code: 1
```

---

## Monitoring & Observability

### Container Metrics

**Prometheus Metrics**:

```python
# Expose container metrics
from prometheus_client import Gauge

container_info = Gauge(
    'container_info',
    'Container information',
    ['version', 'commit', 'build_date']
)

container_info.labels(
    version=os.getenv('VERSION', 'unknown'),
    commit=os.getenv('COMMIT', 'unknown'),
    build_date=os.getenv('BUILD_DATE', 'unknown')
).set(1)
```

**CloudWatch Container Insights**:

```json
{
  "containerInsights": true,
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/aws/ecs/taskmanager-api",
      "awslogs-region": "us-east-1",
      "awslogs-stream-prefix": "api"
    }
  }
}
```

---

## Best Practices Summary

### DO ✅

1. **Use multi-stage builds** for smaller images
2. **Pin all versions** (base image, dependencies)
3. **Run as non-root user** for security
4. **Scan images** for vulnerabilities before deployment
5. **Use .dockerignore** to exclude unnecessary files
6. **Set health checks** for container orchestration
7. **Tag images** with version, commit SHA, timestamp
8. **Use BuildKit** for faster builds and better caching
9. **Minimize layers** by combining commands
10. **Document build arguments** and environment variables

### DON'T ❌

1. **Don't use `latest` tag** in production
2. **Don't run as root** in containers
3. **Don't install unnecessary packages** (bloats image)
4. **Don't embed secrets** in images (use secrets management)
5. **Don't skip vulnerability scanning**
6. **Don't ignore .dockerignore** (slows builds, larger images)
7. **Don't use mutable tags** for deployments (staging/prod)
8. **Don't rebuild entire image** for small changes (use layer caching)

---

## Related Documents

- [ECS Deployment](./ecs-deployment.md) - ECS task definitions and service configuration
- [CI/CD Pipeline](./ci-cd-pipeline.md) - Automated build and deployment
- [Infrastructure as Code](./infrastructure-as-code.md) - Terraform for container infrastructure
- [Security Architecture](../security/README.md) - Security hardening and compliance

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)  
**Maintainer**: DevOps Team
