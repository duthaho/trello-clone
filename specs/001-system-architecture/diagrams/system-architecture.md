# System Architecture Diagram

**Feature**: System Architecture Design  
**Date**: 2025-10-30

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser]
        MOBILE[Mobile App]
    end

    subgraph "CDN / Edge"
        ALB[Application Load Balancer]
    end

    subgraph "Interface Layer"
        API1[FastAPI Instance 1]
        API2[FastAPI Instance 2]
        APIN[FastAPI Instance N]
    end

    subgraph "Application Layer"
        UC_USER[User Use Cases]
        UC_PROJ[Project Use Cases]
        UC_TASK[Task Use Cases]
        UC_NOTIF[Notification Use Cases]
    end

    subgraph "Domain Layer"
        DOM_USER[User Domain]
        DOM_PROJ[Project Domain]
        DOM_TASK[Task Domain]
        DOM_NOTIF[Notification Domain]
        DOM_AUDIT[Audit Domain]
    end

    subgraph "Infrastructure Layer"
        REPOS[Repositories<br/>SQLAlchemy]
        CACHE[Redis Cache]
        EVENTS[Event Bus]
        METRICS[Prometheus Metrics]
        LOGS[Structured Logging]
    end

    subgraph "Async Workers"
        WORKER1[Celery Worker 1]
        WORKER2[Celery Worker 2]
        BEAT[Celery Beat Scheduler]
    end

    subgraph "Data Stores"
        DB[(MySQL Database<br/>AWS RDS)]
        REDIS[(Redis<br/>AWS ElastiCache)]
        S3[(S3 Bucket<br/>File Storage)]
    end

    subgraph "Observability"
        PROM[Prometheus]
        GRAF[Grafana]
        TRACE[OpenTelemetry]
    end

    subgraph "External Services"
        EMAIL[Email Service<br/>SES]
        PUSH[Push Notifications]
    end

    WEB --> ALB
    MOBILE --> ALB
    ALB --> API1
    ALB --> API2
    ALB --> APIN

    API1 --> UC_USER
    API1 --> UC_PROJ
    API1 --> UC_TASK
    API1 --> UC_NOTIF

    UC_USER --> DOM_USER
    UC_PROJ --> DOM_PROJ
    UC_TASK --> DOM_TASK
    UC_NOTIF --> DOM_NOTIF

    DOM_USER --> REPOS
    DOM_PROJ --> REPOS
    DOM_TASK --> REPOS
    DOM_NOTIF --> REPOS

    DOM_USER -.->|Domain Events| EVENTS
    DOM_PROJ -.->|Domain Events| EVENTS
    DOM_TASK -.->|Domain Events| EVENTS

    REPOS --> DB
    REPOS --> CACHE
    CACHE --> REDIS

    EVENTS --> REDIS
    EVENTS --> WORKER1
    EVENTS --> WORKER2

    WORKER1 --> EMAIL
    WORKER1 --> PUSH
    WORKER1 --> DOM_NOTIF

    BEAT --> REDIS

    API1 --> METRICS
    WORKER1 --> METRICS
    API1 --> LOGS

    METRICS --> PROM
    PROM --> GRAF
    LOGS --> TRACE

    style DOM_USER fill:#e1f5fe
    style DOM_PROJ fill:#e1f5fe
    style DOM_TASK fill:#e1f5fe
    style DOM_NOTIF fill:#e1f5fe
    style DOM_AUDIT fill:#e1f5fe
```

## Clean Architecture Layer Dependencies

```mermaid
graph BT
    DOMAIN[Domain Layer<br/>Entities, Value Objects, Events<br/>PURE PYTHON]
    APP[Application Layer<br/>Use Cases, Commands, Queries]
    INFRA[Infrastructure Layer<br/>Repositories, External Services]
    INTERFACE[Interface Layer<br/>API Controllers, Schemas]

    APP -->|depends on| DOMAIN
    INFRA -->|depends on| APP
    INFRA -->|depends on| DOMAIN
    INTERFACE -->|depends on| APP
    INTERFACE -->|depends on| INFRA
    INTERFACE -->|depends on| DOMAIN

    style DOMAIN fill:#4caf50,color:#fff
    style APP fill:#2196f3,color:#fff
    style INFRA fill:#ff9800,color:#fff
    style INTERFACE fill:#9c27b0,color:#fff
```

## Bounded Context Relationships

```mermaid
graph LR
    USER[User Management]
    PROJ[Project Management]
    TASK[Task Management]
    NOTIF[Notification]
    AUDIT[Audit]

    USER -->|validates| PROJ
    USER -->|validates| TASK
    PROJ -->|contains| TASK
    TASK -.->|triggers| NOTIF
    PROJ -.->|triggers| NOTIF
    USER -.->|triggers| NOTIF
    USER -->|logs| AUDIT
    PROJ -->|logs| AUDIT
    TASK -->|logs| AUDIT

    style USER fill:#e3f2fd
    style PROJ fill:#f3e5f5
    style TASK fill:#fff3e0
    style NOTIF fill:#e8f5e9
    style AUDIT fill:#fce4ec
```

## Deployment Architecture (AWS ECS)

```mermaid
graph TB
    subgraph "AWS Cloud (Single Region)"
        subgraph "Public Subnets"
            ALB[Application Load Balancer]
            NAT[NAT Gateway]
        end

        subgraph "Private Subnets (Availability Zone 1)"
            ECS1[ECS Cluster]
            API_TASK1[API Task 1]
            WORKER_TASK1[Worker Task 1]
        end

        subgraph "Private Subnets (Availability Zone 2)"
            ECS2[ECS Cluster]
            API_TASK2[API Task 2]
            WORKER_TASK2[Worker Task 2]
        end

        subgraph "Database Tier"
            RDS_PRIMARY[(RDS MySQL Primary)]
            RDS_REPLICA[(RDS MySQL Read Replica)]
            REDIS_PRIMARY[(ElastiCache Redis Primary)]
            REDIS_REPLICA[(ElastiCache Redis Replica)]
        end

        subgraph "Storage"
            S3[S3 Bucket<br/>File Attachments]
            ECR[ECR<br/>Docker Registry]
        end

        subgraph "Monitoring"
            CW[CloudWatch Logs]
            PROM_SVC[Prometheus<br/>EC2 Instance]
            GRAF_SVC[Grafana<br/>EC2 Instance]
        end
    end

    INTERNET[Internet] --> ALB
    ALB --> API_TASK1
    ALB --> API_TASK2

    API_TASK1 --> RDS_PRIMARY
    API_TASK1 --> RDS_REPLICA
    API_TASK1 --> REDIS_PRIMARY

    API_TASK2 --> RDS_PRIMARY
    API_TASK2 --> RDS_REPLICA
    API_TASK2 --> REDIS_PRIMARY

    WORKER_TASK1 --> REDIS_PRIMARY
    WORKER_TASK2 --> REDIS_PRIMARY

    WORKER_TASK1 --> RDS_PRIMARY
    WORKER_TASK2 --> RDS_PRIMARY

    RDS_PRIMARY -.->|replication| RDS_REPLICA
    REDIS_PRIMARY -.->|replication| REDIS_REPLICA

    API_TASK1 --> S3
    WORKER_TASK1 --> S3

    API_TASK1 -.->|logs| CW
    WORKER_TASK1 -.->|logs| CW

    API_TASK1 -.->|metrics| PROM_SVC
    PROM_SVC --> GRAF_SVC

    ECR -.->|pull images| ECS1
    ECR -.->|pull images| ECS2

    API_TASK1 --> NAT
    WORKER_TASK1 --> NAT
    NAT --> INTERNET
```

## Request Flow - Task Creation

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI (Interface)
    participant UC as Create Task Use Case (Application)
    participant Task as Task Entity (Domain)
    participant Repo as Task Repository (Infrastructure)
    participant DB as MySQL Database
    participant Events as Event Bus
    participant Worker as Celery Worker
    participant Notif as Notification Service

    Client->>API: POST /api/v1/tasks
    API->>API: Validate JWT Token
    API->>API: Validate Request Schema (Pydantic)
    API->>UC: execute(CreateTaskCommand)
    UC->>Task: create(title, description, project_id)
    Task->>Task: validate invariants
    Task->>Task: emit TaskCreated event
    UC->>Repo: save(task)
    Repo->>DB: INSERT INTO tasks
    DB-->>Repo: success
    Repo-->>UC: task_id
    UC->>Events: publish(TaskCreated)
    UC-->>API: TaskResponse
    API-->>Client: 201 Created {task}

    Events->>Worker: TaskCreated event
    Worker->>Notif: create notification
    Notif->>Worker: send email
    Worker-->>Events: ack
```

## Data Flow - User Authentication

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant AuthUC as Auth Use Case
    participant User as User Entity
    participant UserRepo as User Repository
    participant DB as MySQL
    participant Redis
    participant Audit as Audit Service

    Client->>API: POST /api/v1/auth/login
    API->>AuthUC: authenticate(email, password)
    AuthUC->>UserRepo: get_by_email(email)
    UserRepo->>DB: SELECT * FROM users WHERE email=?
    DB-->>UserRepo: user record
    UserRepo-->>AuthUC: User entity
    AuthUC->>User: verify_password(password)
    User->>User: bcrypt.verify(password, hash)
    User-->>AuthUC: password_valid=true
    AuthUC->>AuthUC: generate_jwt(user_id, roles)
    AuthUC->>Redis: SET session:{token} {user_data} EX 900
    Redis-->>AuthUC: OK
    AuthUC->>Audit: log_event(UserLoggedIn)
    Audit->>DB: INSERT INTO audit_logs
    AuthUC-->>API: {access_token, refresh_token}
    API-->>Client: 200 OK {tokens}
```

## Scaling Strategy

```mermaid
graph LR
    subgraph "Horizontal Scaling"
        API1[API Instance 1]
        API2[API Instance 2]
        API3[API Instance N]

        WORKER1[Worker 1]
        WORKER2[Worker 2]
        WORKER3[Worker N]
    end

    subgraph "Vertical Scaling"
        RDS[RDS MySQL<br/>Up to 64 vCPUs<br/>256 GB RAM]
        REDIS_CLUSTER[Redis Cluster<br/>Multi-node]
    end

    subgraph "Caching"
        CDN[CloudFront CDN<br/>Static Assets]
        REDIS_CACHE[Redis Cache<br/>Hot Data]
    end

    ALB[Load Balancer] --> API1
    ALB --> API2
    ALB --> API3

    REDIS_QUEUE[Redis Queue] --> WORKER1
    REDIS_QUEUE --> WORKER2
    REDIS_QUEUE --> WORKER3

    API1 --> REDIS_CACHE
    API2 --> REDIS_CACHE
    API3 --> REDIS_CACHE

    API1 --> RDS
    API2 --> RDS
    API3 --> RDS
```

## Legend

- **Solid lines** (→): Synchronous dependencies
- **Dotted lines** (-.->): Asynchronous events
- **Blue boxes**: Domain layer (pure business logic)
- **Orange boxes**: Infrastructure layer
- **Purple boxes**: Interface layer
- **Green boxes**: External services

## Notes

1. **Stateless API**: All API instances are identical and stateless, enabling horizontal scaling
2. **Event-Driven**: Bounded contexts communicate via domain events, reducing coupling
3. **Caching**: Redis caches frequently accessed data to reduce database load
4. **Async Processing**: Celery workers handle long-running tasks (email, reports)
5. **High Availability**: Multi-AZ deployment with automatic failover
6. **Observability**: Comprehensive metrics, logs, and traces for production monitoring
