# Environment Management

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines the environment management strategy for the Task Management System, covering environment separation, configuration management, promotion workflows, and environment-specific considerations for development, staging, and production environments.

---

## Environment Strategy

### Environment Types

| Environment     | Purpose                               | Uptime SLA           | Data                      | Users                            |
| --------------- | ------------------------------------- | -------------------- | ------------------------- | -------------------------------- |
| **Development** | Active development, experimentation   | None (best effort)   | Synthetic/test data       | Developers only                  |
| **Staging**     | Pre-production testing, QA validation | 95% (business hours) | Sanitized production copy | Internal team + select customers |
| **Production**  | Live customer-facing system           | 99.9% (24/7)         | Real customer data        | All customers                    |

### Environment Parity

**Goal**: Environments should be as similar as possible to reduce deployment surprises

```mermaid
graph LR
    Dev[Development<br/>Small Scale] --> Staging[Staging<br/>Medium Scale]
    Staging --> Prod[Production<br/>Full Scale]

    Dev -.->|Configuration| Config[Same Config Structure]
    Staging -.->|Configuration| Config
    Prod -.->|Configuration| Config

    Dev -.->|Code| Code[Same Codebase]
    Staging -.->|Code| Code
    Prod -.->|Code| Code

    style Dev fill:#e1f5e1
    style Staging fill:#fff4e1
    style Prod fill:#ffe1e1
```

**Differences by Design**:

- Resource sizes (CPU, memory, instance count)
- Logging verbosity (DEBUG in dev, INFO in prod)
- External integrations (sandbox APIs in non-prod)
- Data volumes (minimal in dev, subset in staging)

---

## Development Environment

### Purpose

- Local development and testing
- Rapid iteration and experimentation
- Feature branch testing
- Integration testing

### Infrastructure Configuration

**Size**: Minimal (cost-optimized)

| Component       | Specification                  | Cost/Month     |
| --------------- | ------------------------------ | -------------- |
| **VPC**         | 10.1.0.0/16                    | Free           |
| **RDS**         | db.t3.micro (1 vCPU, 1 GB RAM) | ~$15           |
| **ElastiCache** | cache.t3.micro (1 node)        | ~$12           |
| **ECS API**     | 0.25 vCPU, 512 MB × 2 tasks    | ~$15           |
| **ECS Worker**  | 0.25 vCPU, 512 MB × 2 tasks    | ~$15           |
| **ALB**         | Application Load Balancer      | ~$20           |
| **Total**       |                                | **~$77/month** |

### Terraform Configuration

**environments/dev/terraform.tfvars**:

```hcl
# AWS Configuration
aws_region = "us-east-1"

# Network Configuration
vpc_cidr = "10.1.0.0/16"
availability_zones = [
  "us-east-1a",
  "us-east-1b"
]

# Database Configuration
db_instance_class         = "db.t3.micro"
db_allocated_storage      = 20
db_max_allocated_storage  = 50
db_multi_az               = false
db_backup_retention_days  = 7
db_deletion_protection    = false
db_skip_final_snapshot    = true
db_create_replica         = false

# Cache Configuration
cache_node_type           = "cache.t3.micro"
cache_num_nodes           = 1
cache_automatic_failover  = false

# ECS Configuration
api_cpu                   = "256"
api_memory                = "512"
api_desired_count         = 2
api_min_capacity          = 2
api_max_capacity          = 5

worker_cpu                = "256"
worker_memory             = "512"
worker_desired_count      = 2
worker_min_capacity       = 1
worker_max_capacity       = 10

# Logging
log_retention_days        = 7
log_level                 = "DEBUG"

# Domain
domain_name               = "dev.taskmanager.internal"
```

### Environment Variables

```bash
# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://admin:password@dev-db.xxx.rds.amazonaws.com:5432/taskmanager
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=5

# Redis
REDIS_URL=redis://dev-cache.xxx.cache.amazonaws.com:6379/0

# Celery
CELERY_BROKER_URL=redis://dev-cache.xxx.cache.amazonaws.com:6379/0
CELERY_RESULT_BACKEND=redis://dev-cache.xxx.cache.amazonaws.com:6379/1
CELERY_WORKER_CONCURRENCY=2

# Authentication
JWT_SECRET_KEY=dev-secret-key-change-me
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours in dev

# External Services (sandbox)
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=2525
OAUTH_GOOGLE_CLIENT_ID=dev-google-client-id
OAUTH_GITHUB_CLIENT_ID=dev-github-client-id

# Feature Flags
ENABLE_REGISTRATION=true
ENABLE_EMAIL_VERIFICATION=false  # Skip in dev
ENABLE_RATE_LIMITING=false
```

### Access Control

**Who can access**:

- ✅ All developers
- ✅ QA team
- ❌ External users

**How to access**:

- VPN connection (AWS Client VPN)
- Bastion host for database access
- AWS SSO for console access

---

## Staging Environment

### Purpose

- Pre-production validation
- QA testing and regression testing
- Performance testing
- Integration testing with external services
- Customer preview (beta features)

### Infrastructure Configuration

**Size**: Medium (production-like)

| Component       | Specification                            | Cost/Month      |
| --------------- | ---------------------------------------- | --------------- |
| **VPC**         | 10.2.0.0/16                              | Free            |
| **RDS**         | db.t3.large (2 vCPU, 8 GB RAM), Multi-AZ | ~$180           |
| **ElastiCache** | cache.t3.medium (2 nodes, Multi-AZ)      | ~$80            |
| **ECS API**     | 0.5 vCPU, 1 GB × 3 tasks                 | ~$35            |
| **ECS Worker**  | 0.5 vCPU, 1 GB × 5 tasks                 | ~$60            |
| **ALB**         | Application Load Balancer                | ~$25            |
| **Total**       |                                          | **~$380/month** |

### Terraform Configuration

**environments/staging/terraform.tfvars**:

```hcl
# AWS Configuration
aws_region = "us-east-1"

# Network Configuration
vpc_cidr = "10.2.0.0/16"
availability_zones = [
  "us-east-1a",
  "us-east-1b"
]

# Database Configuration
db_instance_class         = "db.t3.large"
db_allocated_storage      = 50
db_max_allocated_storage  = 200
db_multi_az               = true  # Simulate production
db_backup_retention_days  = 14
db_deletion_protection    = true
db_skip_final_snapshot    = false
db_create_replica         = true  # Test read replicas
db_replica_instance_class = "db.t3.medium"

# Cache Configuration
cache_node_type           = "cache.t3.medium"
cache_num_nodes           = 2
cache_automatic_failover  = true

# ECS Configuration
api_cpu                   = "512"
api_memory                = "1024"
api_desired_count         = 3
api_min_capacity          = 3
api_max_capacity          = 10

worker_cpu                = "512"
worker_memory             = "1024"
worker_desired_count      = 5
worker_min_capacity       = 3
worker_max_capacity       = 20

# Logging
log_retention_days        = 30
log_level                 = "INFO"

# Domain
domain_name               = "staging.taskmanager.com"
```

### Environment Variables

```bash
# Application Configuration
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Database (from Secrets Manager)
DATABASE_URL=<from-secrets-manager>
DB_POOL_SIZE=20
DB_POOL_MAX_OVERFLOW=10

# Redis (from Secrets Manager)
REDIS_URL=<from-secrets-manager>

# Celery
CELERY_BROKER_URL=<from-secrets-manager>
CELERY_RESULT_BACKEND=<from-secrets-manager>
CELERY_WORKER_CONCURRENCY=4

# Authentication
JWT_SECRET_KEY=<from-secrets-manager>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# External Services (sandbox)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=<from-secrets-manager>
OAUTH_GOOGLE_CLIENT_ID=<from-secrets-manager>
OAUTH_GITHUB_CLIENT_ID=<from-secrets-manager>

# Feature Flags
ENABLE_REGISTRATION=true
ENABLE_EMAIL_VERIFICATION=true
ENABLE_RATE_LIMITING=true
```

### Access Control

**Who can access**:

- ✅ Developers
- ✅ QA team
- ✅ Product managers
- ✅ Select beta customers
- ❌ General public

**How to access**:

- Public URL: https://staging.taskmanager.com
- IP whitelist for admin endpoints
- Basic auth for non-production users

---

## Production Environment

### Purpose

- Live customer-facing system
- Real customer data
- 99.9% uptime SLA
- 24/7 monitoring and support

### Infrastructure Configuration

**Size**: Full scale (optimized for production)

| Component       | Specification                               | Cost/Month               |
| --------------- | ------------------------------------------- | ------------------------ |
| **VPC**         | 10.0.0.0/16                                 | Free                     |
| **RDS**         | db.r6g.xlarge (4 vCPU, 32 GB RAM), Multi-AZ | ~$850                    |
| **RDS Replica** | db.r6g.large (2 vCPU, 16 GB RAM)            | ~$400                    |
| **ElastiCache** | cache.r7g.large (3 nodes, Multi-AZ)         | ~$400                    |
| **ECS API**     | 1 vCPU, 2 GB × 5-50 tasks (auto-scale)      | ~$180-$1800              |
| **ECS Worker**  | 0.5 vCPU, 1 GB × 10-100 tasks (auto-scale)  | ~$180-$1800              |
| **ALB**         | Application Load Balancer + WAF             | ~$50                     |
| **CloudWatch**  | Logs + Metrics                              | ~$100                    |
| **S3**          | Backups + Static Assets                     | ~$50                     |
| **Total**       |                                             | **~$2,210-$5,450/month** |

### Terraform Configuration

**environments/production/terraform.tfvars**:

```hcl
# AWS Configuration
aws_region = "us-east-1"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = [
  "us-east-1a",
  "us-east-1b"
]

# Database Configuration
db_instance_class         = "db.r6g.xlarge"
db_allocated_storage      = 100
db_max_allocated_storage  = 1000
db_multi_az               = true
db_backup_retention_days  = 30
db_deletion_protection    = true
db_skip_final_snapshot    = false
db_create_replica         = true
db_replica_instance_class = "db.r6g.large"

# Cache Configuration
cache_node_type           = "cache.r7g.large"
cache_num_nodes           = 3
cache_automatic_failover  = true

# ECS Configuration
api_cpu                   = "1024"
api_memory                = "2048"
api_desired_count         = 5
api_min_capacity          = 5
api_max_capacity          = 50

worker_cpu                = "512"
worker_memory             = "1024"
worker_desired_count      = 10
worker_min_capacity       = 5
worker_max_capacity       = 100

# Logging
log_retention_days        = 30  # Hot data
log_archive_days          = 365  # Cold data (S3)
log_level                 = "INFO"

# Domain
domain_name               = "taskmanager.com"
```

### Environment Variables

```bash
# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (from Secrets Manager)
DATABASE_URL=<from-secrets-manager>
DATABASE_READER_URL=<from-secrets-manager>  # Read replica
DB_POOL_SIZE=50
DB_POOL_MAX_OVERFLOW=20

# Redis (from Secrets Manager)
REDIS_URL=<from-secrets-manager>

# Celery
CELERY_BROKER_URL=<from-secrets-manager>
CELERY_RESULT_BACKEND=<from-secrets-manager>
CELERY_WORKER_CONCURRENCY=4

# Authentication
JWT_SECRET_KEY=<from-secrets-manager>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# External Services (production)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=<from-secrets-manager>
SMTP_PASSWORD=<from-secrets-manager>
OAUTH_GOOGLE_CLIENT_ID=<from-secrets-manager>
OAUTH_GOOGLE_CLIENT_SECRET=<from-secrets-manager>
OAUTH_GITHUB_CLIENT_ID=<from-secrets-manager>
OAUTH_GITHUB_CLIENT_SECRET=<from-secrets-manager>

# Monitoring
SENTRY_DSN=<from-secrets-manager>
DATADOG_API_KEY=<from-secrets-manager>

# Feature Flags
ENABLE_REGISTRATION=true
ENABLE_EMAIL_VERIFICATION=true
ENABLE_RATE_LIMITING=true
ENABLE_MFA=false  # Future feature
```

### Access Control

**Who can access**:

- ✅ All customers (public)
- ✅ On-call engineers (AWS SSO)
- ✅ Database admins (via bastion, audit logged)

**Production Change Control**:

- ✅ All changes via CI/CD pipeline
- ✅ Peer review required (2 approvals)
- ✅ Automated tests must pass
- ✅ Security scan must pass
- ❌ No manual infrastructure changes
- ❌ No direct database modifications (use migrations)

---

## Configuration Management

### Secrets Management Strategy

**AWS Secrets Manager**:

```json
{
  "taskmanager/production/database-url": {
    "value": "postgresql://admin:xxx@prod-db.xxx.rds.amazonaws.com:5432/taskmanager",
    "rotation": "30 days",
    "kms_key": "arn:aws:kms:us-east-1:123456789012:key/xxx"
  },
  "taskmanager/production/jwt-secret": {
    "value": "xxx",
    "rotation": "90 days"
  },
  "taskmanager/production/oauth-google": {
    "client_id": "xxx",
    "client_secret": "xxx",
    "rotation": "manual"
  }
}
```

**ECS Task Definition Integration**:

```json
{
  "secrets": [
    {
      "name": "DATABASE_URL",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:taskmanager/production/database-url"
    },
    {
      "name": "JWT_SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:taskmanager/production/jwt-secret"
    }
  ]
}
```

### Environment-Specific Configuration Files

**config/environments/production.py**:

```python
from typing import Optional
from pydantic_settings import BaseSettings

class ProductionSettings(BaseSettings):
    """Production environment settings"""

    # Environment
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str
    database_reader_url: Optional[str] = None
    db_pool_size: int = 50
    db_pool_max_overflow: int = 20
    db_pool_recycle: int = 3600  # 1 hour

    # Redis
    redis_url: str
    redis_max_connections: int = 100

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15

    # CORS
    cors_origins: list[str] = [
        "https://taskmanager.com",
        "https://www.taskmanager.com"
    ]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # External Services
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str

    class Config:
        env_file = ".env.production"
        case_sensitive = False
```

---

## Environment Promotion Workflow

### Development → Staging

```mermaid
graph TB
    Dev[Development Branch] -->|PR Merged| Main[Main Branch]
    Main -->|CI: Build & Test| Build[Build Docker Images]
    Build -->|Push to ECR| ECR[ECR Registry]
    ECR -->|Auto Deploy| Staging[Staging Environment]
    Staging -->|Smoke Tests| Tests{Tests Pass?}
    Tests -->|Yes| Ready[Ready for Production]
    Tests -->|No| Rollback[Auto Rollback]
    Rollback --> Fix[Fix Issues in Dev]
```

**Automated Process**:

1. Developer merges PR to `main` branch
2. CI pipeline runs:
   - Lint, type check, unit tests
   - Build Docker images
   - Security scan
   - Push to ECR with tags: `latest`, `main-abc1234`
3. CD pipeline deploys to staging:
   - Run database migrations
   - Update ECS services
   - Wait for health checks
4. Automated smoke tests run
5. If pass: Ready for production
6. If fail: Automatic rollback

### Staging → Production

```mermaid
graph TB
    Staging[Staging Validated] -->|Manual Approval| Approve{Approval}
    Approve -->|Approved| Tag[Tag Release: v1.2.3]
    Tag -->|Trigger CD| Deploy[Deploy to Production]
    Deploy -->|Blue-Green| BlueGreen[Blue-Green Deployment]
    BlueGreen -->|10% Traffic| Canary[Canary Validation]
    Canary -->|Monitor 15min| Health{Healthy?}
    Health -->|Yes| Full[100% Traffic]
    Health -->|No| Rollback[Rollback to Blue]
    Full -->|Complete| Done[Deployment Complete]
```

**Manual Approval Process**:

1. QA validates staging environment
2. Product manager approves feature set
3. Engineer creates git tag: `v1.2.3`
4. Manual approval in GitHub Actions
5. CD pipeline deploys to production:
   - Pre-deployment checks
   - Run migrations (if needed)
   - Blue-green deployment via CodeDeploy
   - Gradual traffic shift (10% → 50% → 100%)
   - Monitor metrics for 15 minutes
   - Rollback if issues detected
6. Post-deployment validation
7. Notify team in Slack

**Approval Checklist**:

```markdown
## Production Deployment Approval

**Version**: v1.2.3
**Date**: 2025-10-30
**Approved by**: @alice, @bob

### Pre-Deployment Checks

- [x] All staging tests passing
- [x] No critical bugs in staging
- [x] Database migrations tested
- [x] Rollback plan documented
- [x] On-call engineer notified
- [x] Customer communication prepared (if needed)

### Deployment Window

- **Start**: 2025-10-30 14:00 UTC
- **Duration**: ~30 minutes
- **Rollback deadline**: 2025-10-30 15:00 UTC

### Monitoring

- Watch dashboards: System Health, API Performance
- Alert channels: #production-deploys, #on-call
- Escalation: @manager if issues detected
```

---

## Environment-Specific Behaviors

### Development Behaviors

```python
if settings.environment == "development":
    # Skip email verification
    user.email_verified = True

    # Disable rate limiting
    rate_limit_enabled = False

    # Use fixed seed for testing
    random.seed(42)

    # Extended JWT expiration
    jwt_access_token_expire_minutes = 1440  # 24 hours

    # Detailed error responses
    include_traceback = True
```

### Production Behaviors

```python
if settings.environment == "production":
    # Strict email verification
    if not user.email_verified:
        raise UnverifiedEmailError()

    # Rate limiting enabled
    rate_limit_enabled = True
    rate_limit_per_minute = 60

    # Short JWT expiration
    jwt_access_token_expire_minutes = 15

    # Sanitized error responses
    include_traceback = False

    # Enable monitoring
    sentry_enabled = True
    datadog_enabled = True
```

---

## Environment Comparison Matrix

| Feature                | Development           | Staging                | Production             |
| ---------------------- | --------------------- | ---------------------- | ---------------------- |
| **Uptime SLA**         | None                  | 95%                    | 99.9%                  |
| **Data**               | Synthetic             | Sanitized copy         | Real customer data     |
| **Database**           | Single AZ, no replica | Multi-AZ, with replica | Multi-AZ, with replica |
| **Auto Scaling**       | Disabled              | Enabled                | Enabled                |
| **Debug Mode**         | Enabled               | Disabled               | Disabled               |
| **Log Level**          | DEBUG                 | INFO                   | INFO                   |
| **JWT Expiration**     | 24 hours              | 15 minutes             | 15 minutes             |
| **Email Verification** | Skipped               | Required               | Required               |
| **Rate Limiting**      | Disabled              | Enabled                | Enabled                |
| **Monitoring**         | Basic                 | Full                   | Full + Alerting        |
| **Backups**            | 7 days                | 14 days                | 30 days                |
| **Deployment**         | Auto on PR merge      | Auto on main push      | Manual approval        |
| **Cost/Month**         | ~$80                  | ~$380                  | ~$2,200-$5,500         |

---

## Environment Lifecycle

### Creating New Environment

```bash
#!/bin/bash
# scripts/create-environment.sh

ENVIRONMENT=${1}  # dev, staging, production

echo "🔧 Creating ${ENVIRONMENT} environment..."

# 1. Create Terraform workspace
cd infrastructure/terraform/environments/${ENVIRONMENT}
terraform init
terraform workspace new ${ENVIRONMENT}

# 2. Create secrets in Secrets Manager
aws secretsmanager create-secret \
  --name "taskmanager/${ENVIRONMENT}/database-url" \
  --secret-string "postgresql://user:pass@localhost/db"

# 3. Apply Terraform
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars

# 4. Run database migrations
aws ecs run-task \
  --cluster ${ENVIRONMENT}-taskmanager \
  --task-definition taskmanager-migrations \
  --launch-type FARGATE

# 5. Deploy application
./scripts/deploy.sh ${ENVIRONMENT} v1.0.0

echo "✅ Environment created successfully"
```

### Destroying Environment

```bash
#!/bin/bash
# scripts/destroy-environment.sh

ENVIRONMENT=${1}

# Safety check
if [ "$ENVIRONMENT" == "production" ]; then
  echo "❌ Cannot destroy production via script"
  exit 1
fi

read -p "⚠️  DESTROY ${ENVIRONMENT}? (type 'yes'): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  exit 1
fi

# 1. Scale down services (prevent new data)
aws ecs update-service \
  --cluster ${ENVIRONMENT}-taskmanager \
  --service api \
  --desired-count 0

# 2. Backup database
aws rds create-db-snapshot \
  --db-instance-identifier ${ENVIRONMENT}-taskmanager-db \
  --db-snapshot-identifier ${ENVIRONMENT}-final-backup

# 3. Destroy infrastructure
cd infrastructure/terraform/environments/${ENVIRONMENT}
terraform destroy -var-file=terraform.tfvars -auto-approve

echo "✅ Environment destroyed"
```

---

## Best Practices

### DO ✅

1. **Use same codebase** across all environments
2. **Externalize configuration** (environment variables, secrets)
3. **Test in staging** before production
4. **Automate deployments** (no manual changes)
5. **Monitor all environments** (including dev/staging)
6. **Document differences** between environments
7. **Use IaC** (Terraform) for all infrastructure
8. **Rotate secrets regularly** (automated)
9. **Tag resources** with environment name
10. **Maintain environment parity** (as much as possible)

### DON'T ❌

1. **Don't hardcode environment-specific values**
2. **Don't deploy untested code** to production
3. **Don't skip staging** environment
4. **Don't use production data** in dev/staging
5. **Don't manually modify** production infrastructure
6. **Don't commit secrets** to version control
7. **Don't skip migrations** in any environment
8. **Don't ignore staging failures** ("works on my machine")

---

## Troubleshooting

### Environment Configuration Issues

```bash
# Verify environment variables
aws ecs describe-task-definition \
  --task-definition production-taskmanager-api \
  --query 'taskDefinition.containerDefinitions[0].environment'

# Check secrets
aws secretsmanager list-secrets \
  --filters Key=name,Values=taskmanager/production

# Verify ECS service configuration
aws ecs describe-services \
  --cluster production-taskmanager \
  --services api
```

### Environment Drift Detection

```bash
# Compare staging vs production
diff \
  <(aws ecs describe-task-definition --task-definition staging-api) \
  <(aws ecs describe-task-definition --task-definition production-api)

# Check for manual changes (Terraform drift)
cd infrastructure/terraform/environments/production
terraform plan -var-file=terraform.tfvars
# Should show "No changes"
```

---

## Related Documents

- [Infrastructure as Code](./infrastructure-as-code.md) - Terraform configuration
- [CI/CD Pipeline](./ci-cd-pipeline.md) - Deployment automation
- [Container Architecture](./container-architecture.md) - Container specifications
- [ECS Deployment](./ecs-deployment.md) - ECS configuration
- [Disaster Recovery](./disaster-recovery.md) - Backup and recovery

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)  
**Maintainer**: DevOps Team
