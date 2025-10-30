# Infrastructure as Code

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines the Infrastructure as Code (IaC) strategy for the Task Management System using Terraform, covering resource provisioning, state management, module design, environment configuration, and operational procedures for AWS infrastructure.

---

## IaC Philosophy

### Principles

1. **Everything as Code**: All infrastructure defined in version-controlled code
2. **Immutable Infrastructure**: Replace, don't modify (no manual changes)
3. **Declarative Configuration**: Define desired state, not steps
4. **Environment Parity**: Identical infrastructure across environments
5. **Self-Documenting**: Code is the source of truth

### Benefits

| Benefit               | Description                                          |
| --------------------- | ---------------------------------------------------- |
| **Reproducibility**   | Spin up identical environments on demand             |
| **Version Control**   | Track all infrastructure changes in git              |
| **Auditability**      | Who changed what and when                            |
| **Disaster Recovery** | Rebuild entire infrastructure from code              |
| **Collaboration**     | Review infrastructure changes like code              |
| **Testing**           | Test infrastructure changes in isolated environments |

---

## Repository Structure

```
infrastructure/
├── README.md
├── terraform/
│   ├── modules/
│   │   ├── networking/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   ├── database/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   ├── cache/
│   │   │   └── ...
│   │   ├── ecs/
│   │   │   └── ...
│   │   ├── alb/
│   │   │   └── ...
│   │   └── monitoring/
│   │       └── ...
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── terraform.tfvars
│   │   │   └── backend.tf
│   │   ├── staging/
│   │   │   └── ...
│   │   └── production/
│   │       └── ...
│   └── global/
│       ├── iam/
│       ├── ecr/
│       └── route53/
├── scripts/
│   ├── init-environment.sh
│   ├── plan-apply.sh
│   └── destroy-environment.sh
└── docs/
    └── runbooks/
```

---

## Terraform Modules

### Module Design Principles

**Single Responsibility**: Each module manages one logical unit

```
modules/database/     # Only RDS resources
modules/cache/        # Only ElastiCache resources
modules/networking/   # Only VPC/subnets/security groups
```

**Composable**: Modules can be combined

```hcl
module "networking" {
  source = "../../modules/networking"
}

module "database" {
  source              = "../../modules/database"
  vpc_id              = module.networking.vpc_id
  subnet_ids          = module.networking.database_subnet_ids
  security_group_ids  = [module.networking.database_sg_id]
}
```

**Reusable**: Same module for all environments

```hcl
# dev/main.tf
module "database" {
  source         = "../../modules/database"
  instance_class = "db.t3.micro"  # Small for dev
}

# production/main.tf
module "database" {
  source         = "../../modules/database"
  instance_class = "db.r6g.xlarge"  # Large for prod
}
```

---

## Networking Module

### VPC and Subnets

**modules/networking/main.tf**:

```hcl
# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.common_tags, {
    Name = "${var.environment}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = "${var.environment}-igw"
  })
}

# Public Subnets (for ALB)
resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true

  tags = merge(var.common_tags, {
    Name = "${var.environment}-public-${var.availability_zones[count.index]}"
    Type = "public"
  })
}

# Private Subnets (for ECS tasks)
resource "aws_subnet" "private_app" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 4)
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.common_tags, {
    Name = "${var.environment}-private-app-${var.availability_zones[count.index]}"
    Type = "private-app"
  })
}

# Private Subnets (for databases)
resource "aws_subnet" "private_data" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 8)
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.common_tags, {
    Name = "${var.environment}-private-data-${var.availability_zones[count.index]}"
    Type = "private-data"
  })
}

# NAT Gateways (one per AZ for high availability)
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-nat-eip-${var.availability_zones[count.index]}"
  })
}

resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.common_tags, {
    Name = "${var.environment}-nat-${var.availability_zones[count.index]}"
  })

  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-public-rt"
  })
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-private-rt-${var.availability_zones[count.index]}"
  })
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_app" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_route_table_association" "private_data" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private_data[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
```

**modules/networking/variables.tf**:

```hcl
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
```

**modules/networking/outputs.tf**:

```hcl
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_app_subnet_ids" {
  description = "IDs of private app subnets"
  value       = aws_subnet.private_app[*].id
}

output "private_data_subnet_ids" {
  description = "IDs of private data subnets"
  value       = aws_subnet.private_data[*].id
}
```

---

## Database Module

### RDS MySQL Instance

**modules/database/main.tf**:

```hcl
# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.common_tags, {
    Name = "${var.environment}-db-subnet-group"
  })
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  name   = "${var.environment}-mysql-params"
  family = "mysql8.0"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }

  parameter {
    name  = "max_connections"
    value = var.max_connections
  }

  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "long_query_time"
    value = "2"
  }

  tags = var.common_tags
}

# Security Group
resource "aws_security_group" "database" {
  name        = "${var.environment}-database-sg"
  description = "Security group for RDS database"
  vpc_id      = var.vpc_id

  ingress {
    description     = "MySQL from app"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = var.app_security_group_ids
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-database-sg"
  })
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.environment}-taskmanager-db"
  engine         = "mysql"
  engine_version = "8.0.35"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id           = var.kms_key_arn

  db_name  = var.database_name
  username = var.master_username
  password = var.master_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]

  multi_az               = var.multi_az
  publicly_accessible    = false
  backup_retention_period = var.backup_retention_days
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  enabled_cloudwatch_logs_exports = ["error", "general", "slowquery"]

  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = "${var.environment}-taskmanager-db-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  deletion_protection = var.deletion_protection

  tags = merge(var.common_tags, {
    Name = "${var.environment}-taskmanager-db"
  })
}

# Read Replica (for production)
resource "aws_db_instance" "replica" {
  count              = var.create_replica ? 1 : 0
  identifier         = "${var.environment}-taskmanager-db-replica"
  replicate_source_db = aws_db_instance.main.identifier
  instance_class     = var.replica_instance_class

  publicly_accessible = false
  skip_final_snapshot = true

  tags = merge(var.common_tags, {
    Name = "${var.environment}-taskmanager-db-replica"
    Role = "read-replica"
  })
}
```

**modules/database/variables.tf**:

```hcl
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for DB subnet group"
  type        = list(string)
}

variable "app_security_group_ids" {
  description = "Security group IDs allowed to connect"
  type        = list(string)
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Initial storage in GB"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Maximum storage for autoscaling"
  type        = number
  default     = 100
}

variable "database_name" {
  description = "Name of the database"
  type        = string
  default     = "taskmanager"
}

variable "master_username" {
  description = "Master username"
  type        = string
  sensitive   = true
}

variable "master_password" {
  description = "Master password"
  type        = string
  sensitive   = true
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on delete"
  type        = bool
  default     = false
}

variable "create_replica" {
  description = "Create read replica"
  type        = bool
  default     = false
}

variable "replica_instance_class" {
  description = "Instance class for replica"
  type        = string
  default     = "db.t3.micro"
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
}

variable "max_connections" {
  description = "Maximum number of connections"
  type        = string
  default     = "100"
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
```

---

## ECS Module

### Cluster and Services

**modules/ecs/main.tf**:

```hcl
# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-taskmanager"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      kms_key_id = var.kms_key_arn
      logging    = "OVERRIDE"

      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }

  tags = var.common_tags
}

# CloudWatch Log Group for ECS Exec
resource "aws_cloudwatch_log_group" "ecs_exec" {
  name              = "/aws/ecs/${var.environment}/execute-command"
  retention_in_days = 7
  kms_key_id        = var.kms_key_arn

  tags = var.common_tags
}

# Capacity Providers
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 2
  }

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 4
  }
}

# Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.environment}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow pulling images from ECR
resource "aws_iam_role_policy" "ecs_task_execution_ecr" {
  name = "ecr-access"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
      Resource = "*"
    }]
  })
}

# Allow accessing secrets
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ]
      Resource = [
        var.secrets_arns,
        var.kms_key_arn
      ]
    }]
  })
}

# Task Role (for application)
resource "aws_iam_role" "ecs_task" {
  name = "${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.common_tags
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/ecs/${var.environment}/taskmanager-api"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = var.common_tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/ecs/${var.environment}/taskmanager-worker"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = var.common_tags
}

# Task Definition - API
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.environment}-taskmanager-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "PORT", value = "8000" },
      { name = "LOG_LEVEL", value = var.log_level }
    ]

    secrets = [
      { name = "DATABASE_URL", valueFrom = "${var.secrets_prefix}/database-url" },
      { name = "REDIS_URL", valueFrom = "${var.secrets_prefix}/redis-url" },
      { name = "JWT_SECRET_KEY", valueFrom = "${var.secrets_prefix}/jwt-secret" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 40
    }

    linuxParameters = {
      capabilities = {
        drop = ["ALL"]
      }
    }

    user = "1000:1000"
  }])

  tags = var.common_tags
}

# ECS Service - API
resource "aws_ecs_service" "api" {
  name            = "${var.environment}-taskmanager-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.api_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "api"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 60

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100

    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }
  }

  enable_execute_command = true
  propagate_tags         = "SERVICE"

  tags = var.common_tags

  depends_on = [var.alb_listener_arn]
}

# Auto Scaling
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_capacity
  min_capacity       = var.api_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.environment}-api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

---

## Environment Configuration

### Production Environment

**environments/production/main.tf**:

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "taskmanager-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789012:key/xxx"
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "production"
      Project     = "taskmanager"
      ManagedBy   = "terraform"
    }
  }
}

# Common tags
locals {
  common_tags = {
    Environment = "production"
    Project     = "taskmanager"
    ManagedBy   = "terraform"
  }
}

# Networking
module "networking" {
  source = "../../modules/networking"

  environment        = "production"
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  common_tags        = local.common_tags
}

# Database
module "database" {
  source = "../../modules/database"

  environment             = "production"
  vpc_id                  = module.networking.vpc_id
  subnet_ids              = module.networking.private_data_subnet_ids
  app_security_group_ids  = [module.ecs.api_security_group_id]

  instance_class          = "db.r6g.xlarge"
  allocated_storage       = 100
  max_allocated_storage   = 1000
  multi_az                = true
  backup_retention_days   = 30
  deletion_protection     = true
  skip_final_snapshot     = false

  create_replica          = true
  replica_instance_class  = "db.r6g.large"

  master_username         = var.db_master_username
  master_password         = var.db_master_password
  kms_key_arn            = module.kms.key_arn
  max_connections         = "500"

  common_tags             = local.common_tags
}

# Cache (Redis)
module "cache" {
  source = "../../modules/cache"

  environment            = "production"
  vpc_id                 = module.networking.vpc_id
  subnet_ids             = module.networking.private_data_subnet_ids
  app_security_group_ids = [module.ecs.api_security_group_id]

  node_type              = "cache.r7g.large"
  num_cache_nodes        = 2
  automatic_failover     = true
  multi_az               = true

  common_tags            = local.common_tags
}

# ECS
module "ecs" {
  source = "../../modules/ecs"

  environment          = "production"
  vpc_id               = module.networking.vpc_id
  private_subnet_ids   = module.networking.private_app_subnet_ids

  ecr_repository_url   = var.ecr_repository_url
  image_tag            = var.image_tag

  api_cpu              = "1024"
  api_memory           = "2048"
  api_desired_count    = 5
  api_min_capacity     = 5
  api_max_capacity     = 50

  worker_cpu           = "512"
  worker_memory        = "1024"
  worker_desired_count = 10
  worker_min_capacity  = 5
  worker_max_capacity  = 100

  log_retention_days   = 30
  log_level            = "INFO"

  common_tags          = local.common_tags
}
```

**environments/production/terraform.tfvars**:

```hcl
aws_region = "us-east-1"

vpc_cidr = "10.0.0.0/16"

availability_zones = [
  "us-east-1a",
  "us-east-1b"
]

ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/taskmanager-api"
image_tag          = "v1.2.3"

# Database credentials (stored in environment variables or secrets)
# db_master_username = "admin"
# db_master_password = "<from-secrets>"
```

---

## State Management

### Remote Backend (S3 + DynamoDB)

**Setup Script**:

```bash
#!/bin/bash
# scripts/setup-terraform-backend.sh

set -euo pipefail

AWS_REGION="us-east-1"
BUCKET_NAME="taskmanager-terraform-state"
DYNAMODB_TABLE="terraform-state-lock"

# Create S3 bucket for state
aws s3api create-bucket \
  --bucket ${BUCKET_NAME} \
  --region ${AWS_REGION}

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket ${BUCKET_NAME} \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket ${BUCKET_NAME} \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name ${DYNAMODB_TABLE} \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION}

echo "✅ Terraform backend created successfully"
```

### State Locking

```hcl
terraform {
  backend "s3" {
    bucket         = "taskmanager-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789012:key/xxx"
    dynamodb_table = "terraform-state-lock"  # Prevents concurrent modifications
  }
}
```

**How it works**:

1. Terraform acquires lock in DynamoDB before operations
2. If lock exists, Terraform waits or fails
3. After completion, lock is released
4. Prevents race conditions and state corruption

---

## Terraform Workflows

### Initialize Environment

```bash
#!/bin/bash
# scripts/init-environment.sh

set -euo pipefail

ENVIRONMENT=${1:-dev}

cd "infrastructure/terraform/environments/${ENVIRONMENT}"

echo "🔧 Initializing Terraform for ${ENVIRONMENT}..."

terraform init \
  -upgrade \
  -backend-config="key=${ENVIRONMENT}/terraform.tfstate"

terraform validate

echo "✅ Terraform initialized successfully"
```

### Plan and Apply

```bash
#!/bin/bash
# scripts/plan-apply.sh

set -euo pipefail

ENVIRONMENT=${1:-dev}
ACTION=${2:-plan}

cd "infrastructure/terraform/environments/${ENVIRONMENT}"

case $ACTION in
  plan)
    echo "📋 Planning changes for ${ENVIRONMENT}..."
    terraform plan \
      -out=tfplan \
      -var-file=terraform.tfvars
    ;;

  apply)
    echo "🚀 Applying changes to ${ENVIRONMENT}..."

    # Require explicit confirmation for production
    if [ "$ENVIRONMENT" == "production" ]; then
      read -p "⚠️  Deploy to PRODUCTION? (type 'yes'): " CONFIRM
      if [ "$CONFIRM" != "yes" ]; then
        echo "Cancelled"
        exit 1
      fi
    fi

    terraform apply tfplan

    echo "✅ Changes applied successfully"
    ;;

  *)
    echo "Invalid action: $ACTION (use 'plan' or 'apply')"
    exit 1
    ;;
esac
```

### Destroy Environment

```bash
#!/bin/bash
# scripts/destroy-environment.sh

set -euo pipefail

ENVIRONMENT=${1}

if [ "$ENVIRONMENT" == "production" ]; then
  echo "❌ Cannot destroy production via script"
  echo "Use AWS Console or manual terraform destroy if absolutely necessary"
  exit 1
fi

cd "infrastructure/terraform/environments/${ENVIRONMENT}"

read -p "⚠️  DESTROY ${ENVIRONMENT}? (type 'yes'): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Cancelled"
  exit 1
fi

terraform destroy \
  -var-file=terraform.tfvars \
  -auto-approve

echo "✅ Environment destroyed"
```

---

## CI/CD Integration

### GitHub Actions Workflow

**.github/workflows/terraform.yml**:

```yaml
name: Terraform

on:
  push:
    branches: [main]
    paths:
      - "infrastructure/terraform/**"
  pull_request:
    branches: [main]
    paths:
      - "infrastructure/terraform/**"

env:
  AWS_REGION: us-east-1
  TF_VERSION: 1.5.0

jobs:
  terraform-validate:
    name: Validate
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, staging, production]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Format Check
        run: terraform fmt -check -recursive infrastructure/terraform/

      - name: Terraform Init
        working-directory: infrastructure/terraform/environments/${{ matrix.environment }}
        run: terraform init -backend=false

      - name: Terraform Validate
        working-directory: infrastructure/terraform/environments/${{ matrix.environment }}
        run: terraform validate

  terraform-plan:
    name: Plan
    runs-on: ubuntu-latest
    needs: [terraform-validate]
    if: github.event_name == 'pull_request'
    strategy:
      matrix:
        environment: [dev, staging]
    permissions:
      id-token: write
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-terraform
          aws-region: ${{ env.AWS_REGION }}

      - name: Terraform Init
        working-directory: infrastructure/terraform/environments/${{ matrix.environment }}
        run: terraform init

      - name: Terraform Plan
        working-directory: infrastructure/terraform/environments/${{ matrix.environment }}
        run: |
          terraform plan \
            -out=tfplan \
            -var-file=terraform.tfvars \
            -no-color \
            | tee plan.txt

      - name: Comment PR with plan
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('infrastructure/terraform/environments/${{ matrix.environment }}/plan.txt', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan (${{ matrix.environment }})\n\`\`\`\n${plan}\n\`\`\``
            });

  terraform-apply:
    name: Apply to Staging
    runs-on: ubuntu-latest
    needs: [terraform-validate]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-terraform
          aws-region: ${{ env.AWS_REGION }}

      - name: Terraform Init
        working-directory: infrastructure/terraform/environments/staging
        run: terraform init

      - name: Terraform Apply
        working-directory: infrastructure/terraform/environments/staging
        run: |
          terraform apply \
            -var-file=terraform.tfvars \
            -auto-approve
```

---

## Best Practices

### DO ✅

1. **Use modules** for reusability across environments
2. **Store state remotely** (S3 + DynamoDB locking)
3. **Use workspaces** or separate directories for environments
4. **Pin provider versions** for reproducibility
5. **Encrypt everything** (state, secrets, snapshots)
6. **Tag all resources** consistently
7. **Use variables** for environment-specific values
8. **Enable deletion protection** for critical resources
9. **Review plans** before applying (especially production)
10. **Use data sources** instead of hardcoding values

### DON'T ❌

1. **Don't store secrets** in .tfvars files (use Secrets Manager)
2. **Don't commit .tfstate** files to git
3. **Don't run terraform** without state locking
4. **Don't modify resources** manually (defeats IaC purpose)
5. **Don't use default VPC** (create custom VPC)
6. **Don't skip `terraform plan`** before apply
7. **Don't apply directly to production** (use staging first)
8. **Don't ignore drift** (run regular drift detection)

---

## Troubleshooting

### State Lock Issues

```bash
# Force unlock (use with caution!)
terraform force-unlock <lock-id>

# Check lock status
aws dynamodb get-item \
  --table-name terraform-state-lock \
  --key '{"LockID": {"S": "taskmanager-terraform-state/production/terraform.tfstate"}}'
```

### Import Existing Resources

```bash
# Import existing resource into state
terraform import module.database.aws_db_instance.main taskmanager-prod-db
```

### State Inspection

```bash
# List resources in state
terraform state list

# Show specific resource
terraform state show module.database.aws_db_instance.main

# Remove resource from state (doesn't delete actual resource)
terraform state rm module.database.aws_db_instance.replica
```

---

## Related Documents

- [Container Architecture](./container-architecture.md) - Docker specifications
- [ECS Deployment](./ecs-deployment.md) - ECS configuration
- [CI/CD Pipeline](./ci-cd-pipeline.md) - Deployment automation
- [Environment Management](./environments.md) - Environment configuration
- [Disaster Recovery](./disaster-recovery.md) - Backup and recovery

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)  
**Maintainer**: DevOps Team
