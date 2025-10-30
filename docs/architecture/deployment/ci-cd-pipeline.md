# CI/CD Pipeline

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Task Management System using GitHub Actions, covering automated testing, Docker image building, security scanning, and deployment automation.

---

## Pipeline Architecture

```mermaid
graph LR
    Dev[Developer] -->|git push| GH[GitHub]
    GH -->|trigger| CI[CI Pipeline]

    subgraph "CI Pipeline"
        Test[Run Tests]
        Lint[Lint & Type Check]
        Security[Security Scan]
        Build[Build Image]
        Scan[Scan Image]
    end

    CI --> Staging[Deploy to Staging]
    Staging -->|Smoke Tests| Approve{Manual Approval}
    Approve -->|approved| Prod[Deploy to Production]
    Approve -->|rejected| Stop[Stop]

    Prod --> Monitor[Monitor Metrics]
    Monitor -->|issues| Rollback[Auto Rollback]
    Monitor -->|success| Complete[Complete]
```

---

## Workflow Overview

### Pipelines

| Workflow              | Trigger           | Duration | Purpose                      |
| --------------------- | ----------------- | -------- | ---------------------------- |
| **CI**                | PR opened/updated | ~5 min   | Lint, test, build validation |
| **Build & Push**      | Push to main      | ~8 min   | Build images, push to ECR    |
| **Deploy Staging**    | Push to main      | ~12 min  | Auto-deploy to staging       |
| **Deploy Production** | Manual approval   | ~15 min  | Deploy to production         |
| **Security Scan**     | Daily, PR         | ~3 min   | Scan dependencies & images   |
| **E2E Tests**         | Deploy to staging | ~10 min  | End-to-end test suite        |

---

## CI Workflow

### Pull Request Checks

**.github/workflows/ci.yml**:

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"

jobs:
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install poetry==1.7.0
          poetry install --with dev

      - name: Run ruff (linter)
        run: poetry run ruff check src/ tests/

      - name: Run black (formatter check)
        run: poetry run black --check src/ tests/

      - name: Run isort (import sorting check)
        run: poetry run isort --check src/ tests/

  type-check:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install poetry==1.7.0
          poetry install --with dev

      - name: Run mypy
        run: poetry run mypy src/

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install poetry==1.7.0
          poetry install --with dev

      - name: Run pytest (unit tests)
        run: |
          poetry run pytest tests/unit/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term \
            --cov-fail-under=80 \
            -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: unittests
          token: ${{ secrets.CODECOV_TOKEN }}

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: taskmanager
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: taskmanager_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install poetry==1.7.0
          poetry install --with dev

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://taskmanager:testpass@localhost:5432/taskmanager_test
        run: poetry run alembic upgrade head

      - name: Run pytest (integration tests)
        env:
          DATABASE_URL: postgresql://taskmanager:testpass@localhost:5432/taskmanager_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          poetry run pytest tests/integration/ \
            --cov=src \
            --cov-report=xml \
            -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: integrationtests
          token: ${{ secrets.CODECOV_TOKEN }}

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: "fs"
          scan-ref: "."
          severity: "CRITICAL,HIGH"
          exit-code: "1"

      - name: Run Bandit (Python security linter)
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: Upload Bandit results
        uses: actions/upload-artifact@v4
        with:
          name: bandit-report
          path: bandit-report.json
```

### Status Checks

**Required Checks** (block merge if failing):

- ✅ Lint & format check
- ✅ Type check (mypy)
- ✅ Unit tests (>80% coverage)
- ✅ Integration tests
- ✅ Security scan (no critical/high vulnerabilities)

**Branch Protection Rules**:

```yaml
# .github/branch-protection.yml
branches:
  - name: main
    protection:
      required_status_checks:
        strict: true
        contexts:
          - "Lint & Format Check"
          - "Type Check"
          - "Unit Tests"
          - "Integration Tests"
          - "Security Scan"
      required_pull_request_reviews:
        required_approving_review_count: 1
        dismiss_stale_reviews: true
      enforce_admins: true
      required_linear_history: true
```

---

## Build & Push Workflow

### Docker Image Build

**.github/workflows/build.yml**:

```yaml
name: Build and Push Images

on:
  push:
    branches: [main]
    tags: ["v*"]

env:
  ECR_REGISTRY: 123456789012.dkr.ecr.us-east-1.amazonaws.com
  AWS_REGION: us-east-1

jobs:
  build-and-push:
    name: Build & Push Docker Images
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    strategy:
      matrix:
        image:
          - name: api
            dockerfile: Dockerfile
            context: .
          - name: worker
            dockerfile: Dockerfile.worker
            context: .
          - name: migrations
            dockerfile: Dockerfile.migrations
            context: .

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
          echo "full_tag=${VERSION}-${SHA}-${TIMESTAMP}" >> $GITHUB_OUTPUT

      - name: Build and push ${{ matrix.image.name }}
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.image.context }}
          file: ${{ matrix.image.dockerfile }}
          push: true
          tags: |
            ${{ env.ECR_REGISTRY }}/taskmanager-${{ matrix.image.name }}:${{ steps.meta.outputs.full_tag }}
            ${{ env.ECR_REGISTRY }}/taskmanager-${{ matrix.image.name }}:${{ steps.meta.outputs.version }}
            ${{ env.ECR_REGISTRY }}/taskmanager-${{ matrix.image.name }}:${{ steps.meta.outputs.sha }}
            ${{ env.ECR_REGISTRY }}/taskmanager-${{ matrix.image.name }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VERSION=${{ steps.meta.outputs.version }}
            COMMIT=${{ steps.meta.outputs.sha }}
            BUILD_DATE=${{ steps.meta.outputs.timestamp }}
          provenance: false

      - name: Scan image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.ECR_REGISTRY }}/taskmanager-${{ matrix.image.name }}:${{ steps.meta.outputs.sha }}
          severity: CRITICAL,HIGH
          exit-code: 1
          format: sarif
          output: trivy-results-${{ matrix.image.name }}.sarif

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results-${{ matrix.image.name }}.sarif
          category: trivy-${{ matrix.image.name }}

    outputs:
      image-tag: ${{ steps.meta.outputs.full_tag }}
```

### Build Optimization

**Cache Strategy**:

```yaml
# Use GitHub Actions cache for Docker layers
cache-from: type=gha
cache-to: type=gha,mode=max
# This caches:
# - Python dependencies (poetry install)
# - Intermediate build layers
# - Final image layers

# Result: 8-minute build → 2-minute build (cached)
```

**Parallel Builds**:

```yaml
strategy:
  matrix:
    image: [api, worker, migrations]
# Builds all 3 images in parallel
# Total time: max(build times) instead of sum(build times)
```

---

## Deployment Workflows

### Deploy to Staging

**.github/workflows/deploy-staging.yml**:

```yaml
name: Deploy to Staging

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  CLUSTER: taskmanager-staging
  ECR_REGISTRY: 123456789012.dkr.ecr.us-east-1.amazonaws.com

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [build-and-push] # Wait for images to be built
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Run database migrations
        run: |
          TASK_ARN=$(aws ecs run-task \
            --cluster ${{ env.CLUSTER }} \
            --task-definition taskmanager-migrations \
            --launch-type FARGATE \
            --network-configuration '{
              "awsvpcConfiguration": {
                "subnets": ["subnet-xxx"],
                "securityGroups": ["sg-xxx"],
                "assignPublicIp": "DISABLED"
              }
            }' \
            --overrides '{
              "containerOverrides": [{
                "name": "migrations",
                "environment": [{
                  "name": "IMAGE_TAG",
                  "value": "${{ needs.build-and-push.outputs.image-tag }}"
                }]
              }]
            }' \
            --query 'tasks[0].taskArn' \
            --output text)

          echo "Migration task: ${TASK_ARN}"

          # Wait for migrations to complete
          aws ecs wait tasks-stopped \
            --cluster ${{ env.CLUSTER }} \
            --tasks ${TASK_ARN}

          # Check exit code
          EXIT_CODE=$(aws ecs describe-tasks \
            --cluster ${{ env.CLUSTER }} \
            --tasks ${TASK_ARN} \
            --query 'tasks[0].containers[0].exitCode' \
            --output text)

          if [ "$EXIT_CODE" != "0" ]; then
            echo "::error::Migrations failed with exit code ${EXIT_CODE}"
            exit 1
          fi

          echo "✅ Migrations completed successfully"

      - name: Deploy API service
        run: |
          aws ecs update-service \
            --cluster ${{ env.CLUSTER }} \
            --service taskmanager-api \
            --force-new-deployment \
            --task-definition taskmanager-api:$(cat task-definition-api.json | jq -r '.revision')

      - name: Deploy Worker service
        run: |
          aws ecs update-service \
            --cluster ${{ env.CLUSTER }} \
            --service taskmanager-worker \
            --force-new-deployment \
            --task-definition taskmanager-worker:$(cat task-definition-worker.json | jq -r '.revision')

      - name: Wait for services to stabilize
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.CLUSTER }} \
            --services taskmanager-api taskmanager-worker

      - name: Run smoke tests
        run: |
          # Wait for health checks
          sleep 30

          # Test API health
          HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
            https://staging.taskmanager.com/health)

          if [ "$HEALTH" != "200" ]; then
            echo "::error::Health check failed: ${HEALTH}"
            exit 1
          fi

          # Test authentication endpoint
          AUTH=$(curl -s -o /dev/null -w "%{http_code}" \
            https://staging.taskmanager.com/api/v1/auth/login)

          if [ "$AUTH" != "401" ]; then
            echo "::error::Auth endpoint failed: ${AUTH}"
            exit 1
          fi

          echo "✅ Smoke tests passed"

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: "#deployments"
          slack-message: |
            Staging Deployment: ${{ job.status }}
            Version: ${{ needs.build-and-push.outputs.image-tag }}
            URL: https://staging.taskmanager.com
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

### Deploy to Production

**.github/workflows/deploy-production.yml**:

```yaml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      image-tag:
        description: "Image tag to deploy"
        required: true
        type: string
      skip-migrations:
        description: "Skip database migrations"
        required: false
        type: boolean
        default: false

env:
  AWS_REGION: us-east-1
  CLUSTER: taskmanager-prod

jobs:
  pre-deployment-checks:
    name: Pre-Deployment Checks
    runs-on: ubuntu-latest
    steps:
      - name: Verify image exists
        run: |
          aws ecr describe-images \
            --repository-name taskmanager-api \
            --image-ids imageTag=${{ inputs.image-tag }} \
            > /dev/null 2>&1

          if [ $? -ne 0 ]; then
            echo "::error::Image not found: ${{ inputs.image-tag }}"
            exit 1
          fi

      - name: Check staging deployment
        run: |
          # Verify this version was deployed to staging
          STAGING_IMAGE=$(aws ecs describe-services \
            --cluster taskmanager-staging \
            --services taskmanager-api \
            --query 'services[0].taskDefinition' \
            --output text)

          echo "Staging is running: ${STAGING_IMAGE}"
          echo "Deploying: ${{ inputs.image-tag }}"

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [pre-deployment-checks]
    environment:
      name: production
      url: https://api.taskmanager.com
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Create deployment in GitHub
        id: deployment
        uses: actions/github-script@v7
        with:
          script: |
            const deployment = await github.rest.repos.createDeployment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              ref: context.sha,
              environment: 'production',
              description: 'Deploying ${{ inputs.image-tag }}',
              auto_merge: false,
              required_contexts: []
            });
            return deployment.data.id;

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-prod
          aws-region: ${{ env.AWS_REGION }}

      - name: Run database migrations
        if: ${{ !inputs.skip-migrations }}
        run: |
          echo "🗄️ Running database migrations..."
          # Same as staging, but with prod cluster

      - name: Deploy with blue-green strategy
        run: |
          # Deploy via AWS CodeDeploy for blue-green
          aws deploy create-deployment \
            --application-name taskmanager \
            --deployment-group-name production \
            --deployment-config-name CodeDeployDefault.ECSLinear10PercentEvery3Minutes \
            --description "Deploy ${{ inputs.image-tag }}" \
            --s3-location bucket=taskmanager-deployments,key=appspec.yml,bundleType=YAML

      - name: Wait for deployment
        run: |
          # Monitor CodeDeploy deployment
          DEPLOYMENT_ID=$(aws deploy list-deployments \
            --application-name taskmanager \
            --deployment-group-name production \
            --query 'deployments[0]' \
            --output text)

          aws deploy wait deployment-successful \
            --deployment-id ${DEPLOYMENT_ID}

      - name: Run production smoke tests
        run: |
          # Critical path tests
          ./scripts/smoke-tests-prod.sh

      - name: Update deployment status
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.repos.createDeploymentStatus({
              owner: context.repo.owner,
              repo: context.repo.repo,
              deployment_id: ${{ steps.deployment.outputs.result }},
              state: '${{ job.status }}' === 'success' ? 'success' : 'failure',
              environment_url: 'https://api.taskmanager.com',
              description: 'Deployment ${{ job.status }}'
            });

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: "#production-deploys"
          slack-message: |
            🚀 Production Deployment: ${{ job.status }}
            Version: ${{ inputs.image-tag }}
            Deployed by: ${{ github.actor }}
            URL: https://api.taskmanager.com
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

---

## Automated Testing

### E2E Tests Workflow

**.github/workflows/e2e-tests.yml**:

```yaml
name: E2E Tests

on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types: [completed]
  workflow_dispatch:

jobs:
  e2e-tests:
    name: End-to-End Tests
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js (for Playwright)
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install Playwright
        run: |
          npm install -D @playwright/test
          npx playwright install --with-deps

      - name: Run E2E tests against staging
        env:
          BASE_URL: https://staging.taskmanager.com
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
        run: npx playwright test

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/

      - name: Comment PR with test results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('playwright-report/index.html', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## E2E Test Results\n\nTests passed! ✅'
            });
```

### Performance Tests

**.github/workflows/performance-tests.yml**:

```yaml
name: Performance Tests

on:
  schedule:
    - cron: "0 2 * * *" # Daily at 2 AM UTC
  workflow_dispatch:

jobs:
  load-test:
    name: Load Testing
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run k6 load tests
        uses: grafana/k6-action@v0.3.1
        with:
          filename: tests/performance/load-test.js
          cloud: true
          token: ${{ secrets.K6_CLOUD_TOKEN }}

      - name: Check performance thresholds
        run: |
          # Parse k6 results
          # Fail if P95 > 500ms or error rate > 1%
```

---

## Security Workflows

### Dependency Scanning

**.github/workflows/security-scan.yml**:

```yaml
name: Security Scan

on:
  schedule:
    - cron: "0 0 * * *" # Daily
  push:
    branches: [main]
  pull_request:

jobs:
  dependency-scan:
    name: Dependency Vulnerability Scan
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test
          args: --severity-threshold=high --fail-on=all

      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit --requirement requirements.txt

  secrets-scan:
    name: Scan for Secrets
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  sast-scan:
    name: Static Application Security Testing
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: python

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
```

---

## Secrets Management

### GitHub Secrets

**Required Secrets**:

```yaml
# AWS
AWS_ACCOUNT_ID: "123456789012"
AWS_REGION: "us-east-1"
AWS_ROLE_ARN: "arn:aws:iam::123456789012:role/github-actions"

# Container Registry
ECR_REGISTRY: "123456789012.dkr.ecr.us-east-1.amazonaws.com"

# Notifications
SLACK_BOT_TOKEN: "xoxb-..."

# Security Scanning
SNYK_TOKEN: "..."
CODECOV_TOKEN: "..."

# Testing
TEST_USER_EMAIL: "test@example.com"
TEST_USER_PASSWORD: "..."
```

### OIDC Authentication (Recommended)

**Setup**:

```yaml
# No long-lived AWS credentials needed!
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions
    aws-region: us-east-1
```

**IAM Trust Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:org/taskmanager:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

---

## Monitoring & Notifications

### Deployment Notifications

**Slack Integration**:

```yaml
- name: Notify Slack on deployment
  uses: slackapi/slack-github-action@v1
  with:
    channel-id: "#deployments"
    slack-message: |
      Deployment to ${{ inputs.environment }}: ${{ job.status }}
      Version: ${{ inputs.image-tag }}
      Deployed by: ${{ github.actor }}
      Workflow: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

### Deployment Tracking

**Create GitHub Release**:

```yaml
- name: Create GitHub Release
  uses: actions/create-release@v1
  with:
    tag_name: ${{ inputs.image-tag }}
    release_name: Release ${{ inputs.image-tag }}
    body: |
      ## Changes in this Release
      ${{ github.event.head_commit.message }}

      ## Deployment
      - Staging: ✅ Deployed
      - Production: ✅ Deployed

      ## Metrics
      - Build time: ${{ steps.build.outputs.duration }}
      - Tests: All passed
```

---

## Best Practices

### DO ✅

1. **Run tests in parallel** (lint, type check, unit, integration)
2. **Cache dependencies** (pip, Docker layers)
3. **Use matrix builds** for multiple images
4. **Scan for vulnerabilities** before deployment
5. **Require manual approval** for production
6. **Use OIDC** instead of long-lived credentials
7. **Tag images** with version + commit SHA
8. **Run smoke tests** after deployment
9. **Monitor deployments** for 15+ minutes
10. **Notify team** of deployment status

### DON'T ❌

1. **Don't skip tests** (even for hotfixes)
2. **Don't deploy without migrations** (if schema changed)
3. **Don't use latest tag** in production
4. **Don't store secrets** in code or workflow files
5. **Don't deploy during peak hours** (unless urgent)
6. **Don't skip security scans**
7. **Don't deploy untested code** to production
8. **Don't ignore failed tests** ("it works on my machine")

---

## Troubleshooting

### Common Issues

**1. Build Timeout**:

```yaml
# Increase timeout for slow builds
jobs:
  build:
    timeout-minutes: 30 # Default is 360
```

**2. Flaky Tests**:

```yaml
# Retry flaky tests
- name: Run tests with retries
  run: pytest --reruns 3 --reruns-delay 5
```

**3. Docker Build Failures**:

```bash
# Enable debug logging
- name: Build with debug
  run: docker build --progress=plain .
```

**4. Deployment Rollback**:

```bash
# Automatic rollback via circuit breaker
# Or manual rollback:
aws ecs update-service \
  --cluster prod \
  --service api \
  --task-definition taskmanager-api:42  # Previous version
```

---

## Related Documents

- [Container Architecture](./container-architecture.md) - Docker image specifications
- [ECS Deployment](./ecs-deployment.md) - ECS deployment strategies
- [Infrastructure as Code](./infrastructure-as-code.md) - Terraform for pipeline infrastructure
- [Testing Strategy](../testing/README.md) - Testing best practices
- [Security](../security/README.md) - Security scanning and compliance

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)  
**Maintainer**: DevOps Team
