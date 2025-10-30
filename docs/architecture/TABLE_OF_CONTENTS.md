# Architecture Documentation - Table of Contents

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Quick Navigation

| Section                                                    | Description                                | Key Documents                           |
| ---------------------------------------------------------- | ------------------------------------------ | --------------------------------------- |
| **[Getting Started](#getting-started)**                    | Start here for overview and quick start    | README, Quickstart, Glossary            |
| **[Foundation](#foundation)**                              | Core architecture concepts and decisions   | Layers, Components, Bounded Contexts    |
| **[Architecture Decisions](#architecture-decisions)**      | ADRs documenting key technical choices     | ADR-001, ADR-002, ADR-003               |
| **[System Design](#system-design)**                        | System-level architecture and interactions | Diagrams, Data Flows, API Design        |
| **[Scalability & Performance](#scalability--performance)** | Guidelines for scale and performance       | Scalability, Performance, Caching       |
| **[Security](#security)**                                  | Security architecture and compliance       | Authentication, Authorization, OWASP    |
| **[Observability](#observability)**                        | Monitoring, logging, and operations        | Metrics, Logging, Tracing, Alerts       |
| **[Deployment](#deployment)**                              | Infrastructure and deployment strategy     | Containers, ECS, CI/CD, Environments    |
| **[Data Architecture](#data-architecture)**                | Database design and optimization           | Bounded Contexts, Database Optimization |

---

## Getting Started

### Essential Reading (Start Here)

1. **[README.md](./README.md)** - Architecture documentation index and overview
2. **[Quickstart Guide](./quickstart.md)** - Getting started with the architecture
3. **[Glossary](./glossary.md)** - Key terms and definitions (DDD, Clean Architecture)

### Understanding the System

4. **[Technology Choices](./technology-choices.md)** - Why we chose Python, FastAPI, MySQL, Redis, etc.
5. **[Diagram Rendering](./DIAGRAM_RENDERING.md)** - How to view Mermaid diagrams in documentation

---

## Foundation

### Core Architecture Concepts

1. **[Layers](./layers.md)** - Clean Architecture layer responsibilities

   - Domain Layer (entities, value objects, aggregates)
   - Application Layer (use cases, services)
   - Infrastructure Layer (repositories, external services)
   - Interface Layer (API controllers, DTOs)

2. **[Components](./components.md)** - System components and interactions

   - API Gateway
   - Application Services
   - Domain Models
   - Repositories
   - Cache Layer
   - Message Queue
   - Background Workers

3. **[Bounded Contexts](./bounded-contexts.md)** - Domain-Driven Design contexts
   - User & Organization Management
   - Project & Task Management
   - Collaboration & Comments
   - Notifications
   - Audit & Compliance

---

## Architecture Decisions

### Architecture Decision Records (ADRs)

1. **[ADR-001: Clean Architecture](./decisions/adr-001-clean-architecture.md)**

   - Status: Accepted
   - Decision: Adopt Clean Architecture with DDD tactical patterns
   - Consequences: Clear separation of concerns, testability, domain-centric design

2. **[ADR-002: Technology Stack](./decisions/adr-002-technology-stack.md)**

   - Status: Accepted
   - Decision: Python 3.11+, FastAPI, MySQL 8.0+, Redis 7.0+, Celery
   - Consequences: Modern async Python, strong typing, proven scalability

3. **[ADR-003: Bounded Contexts](./decisions/adr-003-bounded-contexts.md)**
   - Status: Accepted
   - Decision: Define 5 bounded contexts with clear boundaries
   - Consequences: Modular design, future microservices path, clear ownership

---

## System Design

### Architecture Diagrams

1. **[System Overview Diagram](./diagrams/01-system-overview.md)** - High-level system architecture
   - Component diagram
   - Deployment architecture
   - Data flow overview
   - Integration points

### Design Documentation

2. **[Data Flows](./data-flows.md)** - Common system flows

   - User authentication flow (JWT + OAuth2)
   - Task creation and assignment flow
   - Notification delivery flow
   - Background job processing flow

3. **[API Design](./api-design.md)** - RESTful API architecture
   - API versioning strategy (`/api/v1/`)
   - Authentication (JWT tokens, OAuth2)
   - Error handling and status codes
   - Pagination and filtering
   - Rate limiting

---

## Scalability & Performance

### Scalability Strategy

1. **[Scalability Patterns](./scalability.md)** - How the system scales

   - Horizontal scaling (stateless API design)
   - Vertical scaling (database resources)
   - Caching strategy (Redis multi-layer)
   - Async processing (Celery workers)
   - Load balancing (AWS ALB)

2. **[Performance Targets](./performance.md)** - Performance requirements
   - API response times (p50/p95/p99 < 200ms/500ms/1000ms)
   - Database query times (p95 < 100ms)
   - Background job processing (< 5 seconds average)
   - Concurrent user targets (1,000+ simultaneous users)
   - Throughput targets (10,000+ requests/minute)

### Data & Caching

3. **[Data Partitioning](./data-partitioning.md)** - Partitioning strategy

   - User data by `organization_id`
   - Task data by `project_id`
   - Audit logs by timestamp (monthly tables)

4. **[Caching Strategy](./caching.md)** - Multi-layer caching

   - User sessions (Redis, 15-min TTL)
   - Project metadata (5-min TTL)
   - Task lists (1-min TTL)
   - Notification counts (real-time)
   - Cache invalidation patterns

5. **[Database Optimization](./database-optimization.md)** - Query optimization

   - Indexing strategy (from data model)
   - Query patterns and optimization
   - Read replica usage
   - Connection pooling (50 connections)

6. **[Capacity Planning](./capacity-planning.md)** - Growth scenarios
   - Phase 1: 0-10K users
   - Phase 2: 10K-50K users
   - Phase 3: 50K-100K users
   - Resource scaling formulas
   - Cost projections per user

---

## Security

### Security Architecture

**Index**: [Security README](./security/README.md)

1. **[Authentication](./security/authentication.md)** - User authentication

   - JWT token structure (access + refresh tokens)
   - OAuth2 flows (Google, GitHub, Microsoft)
   - Token refresh strategy (15-min access, 7-day refresh)
   - Password hashing (bcrypt with salt)
   - Session management (Redis)
   - Multi-factor authentication (future)

2. **[Authorization](./security/authorization.md)** - Access control

   - RBAC model (5 roles: SUPER_ADMIN, ORG_ADMIN, PROJECT_MANAGER, MEMBER, VIEWER)
   - Permission system (resource-level permissions)
   - Cross-organization isolation (strict data separation)
   - Resource-level access control (project/task ownership)

3. **[Data Protection](./security/data-protection.md)** - Data security

   - Encryption at rest (AWS RDS, KMS)
   - Encryption in transit (TLS 1.3)
   - Secrets management (AWS Secrets Manager)
   - PII handling (data minimization)
   - GDPR compliance (right to be forgotten, data anonymization after 30 days)

4. **[Audit Logging](./security/audit-logging.md)** - Security audit trail

   - Security-relevant events (login attempts, permission changes, data access)
   - Audit log schema (actor, action, resource, timestamp)
   - Retention policy (12 months hot, archive to S3)
   - Compliance reporting (SOC 2, GDPR, HIPAA)

5. **[OWASP Compliance](./security/owasp-compliance.md)** - Security best practices

   - OWASP Top 10 mapping
   - Mitigation strategies for each threat
   - Security testing requirements

6. **[Defense in Depth](./security/defense-in-depth.md)** - Layered security
   - Network layer security (VPC, security groups, WAF)
   - Application layer security (input validation, CSRF protection)
   - Data layer security (encryption, access control)
   - Monitoring layer (GuardDuty, CloudTrail, security alerts)

---

## Observability

### Monitoring & Operations

**Index**: [Observability README](./observability/README.md)

1. **[Logging](./observability/logging.md)** - Structured logging

   - JSON format (structured logs)
   - Log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - Context propagation (request_id, user_id, organization_id)
   - Log aggregation (CloudWatch Logs)
   - Retention policies (30 days hot, 365 days archive)

2. **[Metrics](./observability/metrics.md)** - System metrics

   - Application metrics (Prometheus format)
   - Business metrics (task completion rate, user activity)
   - Infrastructure metrics (CPU, memory, disk, network)
   - SLI/SLO definitions (availability 99.9%, error rate < 1%, p95 latency < 500ms)

3. **[Distributed Tracing](./observability/tracing.md)** - Request tracing

   - OpenTelemetry integration
   - Trace context propagation (across services)
   - Span attributes (HTTP requests, database queries, cache operations)
   - Jaeger backend configuration

4. **[Dashboards](./observability/dashboards.md)** - Grafana dashboards

   - System Health dashboard
   - API Performance dashboard
   - Database Performance dashboard
   - Worker Queue dashboard
   - Business Metrics dashboard

5. **[Alerting](./observability/alerting.md)** - Alert strategy

   - Alert severity levels (P1: critical, P2: high, P3: medium)
   - Alert routing (PagerDuty integration)
   - Alert thresholds (API p95 > 1s, error rate > 5%, DB connection pool > 80%)
   - On-call runbooks

6. **[Incident Response](./observability/incident-response.md)** - Incident handling

   - MTTD (mean time to detect < 5 min)
   - MTTR (mean time to recovery < 30 min)
   - Incident severity classification (SEV1-SEV4)
   - Post-mortem template

7. **[Runbooks](./observability/runbooks/README.md)** - Operational procedures
   - Database failover procedure
   - Cache eviction procedure
   - Worker scaling procedure
   - Deployment rollback procedure

---

## Deployment

### Infrastructure & Deployment

1. **[Container Architecture](./deployment/container-architecture.md)** - Docker containers

   - Dockerfile specifications (API, Worker, Migrations)
   - Multi-stage builds (builder + runtime)
   - Image optimization (800MB → 180MB, 77% reduction)
   - Security hardening (non-root users, read-only filesystem)
   - Image tagging strategy (`v1.2.3-abc1234-timestamp`)
   - ECR configuration (lifecycle policies, scanning)

2. **[ECS Deployment](./deployment/ecs-deployment.md)** - AWS ECS orchestration

   - ECS cluster configuration (Fargate + Fargate Spot)
   - Task definitions (API: 1 vCPU/2GB, Worker: 0.5 vCPU/1GB)
   - Service configuration (desired count, health checks)
   - Deployment strategies (Rolling, Blue-Green, Canary)
   - Auto-scaling policies (CPU 70%, Memory 80%, ALB requests 1000/target)
   - Circuit breaker (automatic rollback)

3. **[CI/CD Pipeline](./deployment/ci-cd-pipeline.md)** - Continuous deployment

   - CI workflow (lint, type check, unit tests, integration tests, security scan)
   - Build workflow (Docker multi-image builds, Trivy scanning)
   - Deploy staging (automated on main push, smoke tests)
   - Deploy production (manual approval, blue-green deployment)
   - E2E tests (Playwright after staging deployment)
   - Security workflows (daily dependency scan, secrets scan, SAST)

4. **[Environment Management](./deployment/environments.md)** - Environment strategy

   - Development environment (minimal resources, $77/month)
   - Staging environment (production-like, $380/month)
   - Production environment (full scale, $2,200-5,500/month)
   - Configuration management (AWS Secrets Manager, environment variables)
   - Promotion workflow (dev → staging → production with validation gates)
   - Environment parity principles

5. **[Infrastructure as Code](./deployment/infrastructure-as-code.md)** - Terraform

   - Repository structure (modules/, environments/, global/)
   - Networking module (VPC, subnets, NAT gateways)
   - Database module (RDS MySQL Multi-AZ, read replicas)
   - ECS module (cluster, services, auto-scaling)
   - State management (S3 backend, DynamoDB locking)
   - Terraform workflows (init, plan, apply, destroy)
   - CI/CD integration (GitHub Actions)

6. **[Disaster Recovery](./deployment/disaster-recovery.md)** - Backup & recovery
   - RTO/RPO targets (RPO 5 min, RTO 1 hour)
   - Backup strategy (RDS automated backups, cross-region replication)
   - Disaster scenarios (AZ failure, region failure, data corruption, security breach)
   - Recovery procedures (bash scripts for failover, PITR restoration)
   - Backup verification (automated quarterly DR drills)
   - Compliance (SOC 2, GDPR, HIPAA, PCI DSS)

---

## Data Architecture

### Database Design

1. **[Bounded Contexts](./bounded-contexts.md)** - Data model by context

   - User & Organization Management
   - Project & Task Management
   - Collaboration & Comments
   - Notifications
   - Audit & Compliance
   - Entity relationships and aggregates

2. **[Database Optimization](./database-optimization.md)** - Database performance

   - Indexing strategy (composite indexes, covering indexes)
   - Query optimization patterns (N+1 query prevention, eager loading)
   - Read replica usage (read-heavy operations)
   - Connection pooling (pgBouncer, SQLAlchemy pool)

3. **[Data Partitioning](./data-partitioning.md)** - Data distribution
   - Partitioning by `organization_id`
   - Partitioning by `project_id`
   - Time-based partitioning (audit logs)
   - Sharding considerations (future)

---

## Document Organization

### By User Story

| User Story                           | Priority | Documents                                                                                         | Status      |
| ------------------------------------ | -------- | ------------------------------------------------------------------------------------------------- | ----------- |
| **US1: Architecture Foundation**     | P1 (MVP) | Layers, Components, Data Flows, API Design, Diagrams, Quickstart, Glossary                        | ✅ Complete |
| **US2: Scalability & Performance**   | P1       | Scalability, Performance, Caching, Database Optimization, Data Partitioning, Capacity Planning    | ✅ Complete |
| **US3: Security Architecture**       | P1       | Authentication, Authorization, Data Protection, Audit Logging, OWASP Compliance, Defense in Depth | ✅ Complete |
| **US4: Observability & Operations**  | P2       | Logging, Metrics, Tracing, Dashboards, Alerting, Incident Response, Runbooks                      | ✅ Complete |
| **US5: Deployment & Infrastructure** | P2       | Containers, ECS, CI/CD, Environments, IaC, Disaster Recovery                                      | ✅ Complete |

### By Role

#### For Developers

- Start: [Quickstart Guide](./quickstart.md)
- Architecture: [Layers](./layers.md), [Components](./components.md), [Bounded Contexts](./bounded-contexts.md)
- API: [API Design](./api-design.md), [Data Flows](./data-flows.md)
- Testing: [Observability](./observability/) (logging, metrics)

#### For DevOps Engineers

- Start: [Deployment Overview](./deployment/)
- Infrastructure: [Container Architecture](./deployment/container-architecture.md), [ECS Deployment](./deployment/ecs-deployment.md)
- Automation: [CI/CD Pipeline](./deployment/ci-cd-pipeline.md), [Infrastructure as Code](./deployment/infrastructure-as-code.md)
- Operations: [Environment Management](./deployment/environments.md), [Disaster Recovery](./deployment/disaster-recovery.md)

#### For Security Engineers

- Start: [Security README](./security/README.md)
- Authentication: [Authentication](./security/authentication.md), [Authorization](./security/authorization.md)
- Compliance: [OWASP Compliance](./security/owasp-compliance.md), [Audit Logging](./security/audit-logging.md)
- Data: [Data Protection](./security/data-protection.md), [Defense in Depth](./security/defense-in-depth.md)

#### For Architects

- Start: [README.md](./README.md), [ADRs](./decisions/)
- Design: [System Overview](./diagrams/01-system-overview.md), [Bounded Contexts](./bounded-contexts.md)
- Scale: [Scalability](./scalability.md), [Performance](./performance.md), [Capacity Planning](./capacity-planning.md)
- Evolution: [Technology Choices](./technology-choices.md), ADRs

#### For Product Managers

- Start: [Quickstart Guide](./quickstart.md), [Glossary](./glossary.md)
- Business: [Capacity Planning](./capacity-planning.md) (cost projections)
- Features: [Bounded Contexts](./bounded-contexts.md) (feature domains)
- Operations: [Incident Response](./observability/incident-response.md)

---

## Document Statistics

| Category                      | Document Count   | Total Size  |
| ----------------------------- | ---------------- | ----------- |
| **Foundation**                | 8 docs           | ~120 KB     |
| **Architecture Decisions**    | 3 ADRs           | ~45 KB      |
| **System Design**             | 3 docs           | ~60 KB      |
| **Scalability & Performance** | 6 docs           | ~150 KB     |
| **Security**                  | 7 docs           | ~180 KB     |
| **Observability**             | 8 docs           | ~200 KB     |
| **Deployment**                | 6 docs           | ~170 KB     |
| **Total**                     | **41 documents** | **~925 KB** |

---

## Navigation Tips

### Finding Documents

1. **By Topic**: Use the section headers above
2. **By Role**: Use the "By Role" section to find relevant documents
3. **By Priority**: Start with US1 (MVP) documents, then US2-US5
4. **Search**: Use your editor's search function (Ctrl+F / Cmd+F)

### Understanding Diagrams

- All diagrams use Mermaid syntax
- See [Diagram Rendering](./DIAGRAM_RENDERING.md) for viewing instructions
- GitHub renders Mermaid natively in markdown
- Use MkDocs or VS Code Mermaid extension for local viewing

### Following Cross-References

- Documents link to related documentation
- Use "Related Documents" section at bottom of each document
- ADRs reference the architecture they impact

---

## Recent Updates

| Date       | Change                                         | Documents Affected                                                                              |
| ---------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 2025-10-30 | Created comprehensive deployment documentation | Container, ECS, CI/CD, Environments, IaC, DR (6 docs)                                           |
| 2025-10-30 | Added observability framework                  | Logging, Metrics, Tracing, Dashboards, Alerting, Incident Response, Runbooks (8 docs)           |
| 2025-10-30 | Completed security architecture                | Authentication, Authorization, Data Protection, Audit Logging, OWASP, Defense in Depth (7 docs) |
| 2025-10-30 | Initial architecture foundation                | All foundational documents (US1-US3)                                                            |

---

## Contributing to Documentation

### Adding New Documents

1. Follow the document template structure:

   - Version and metadata
   - Overview section
   - Technical details with code examples
   - Best practices (DO/DON'T lists)
   - Related documents section

2. Add Mermaid diagrams where appropriate
3. Update this Table of Contents
4. Update the main [README.md](./README.md)
5. Add cross-references to related documents

### Updating Existing Documents

1. Update the "Last Updated" date
2. Document changes in "Recent Updates" section (if significant)
3. Maintain version number (semantic versioning for docs)
4. Verify all cross-references still work

---

## Related Documents

- **[README.md](./README.md)** - Main architecture documentation index
- **[Quickstart Guide](./quickstart.md)** - Getting started quickly
- **[Glossary](./glossary.md)** - Key terms and definitions
- **[Navigation Diagram](./navigation.md)** - Visual guide to documentation structure

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)  
**Maintainer**: Architecture Team  
**Status**: Active - 41 documents, 5 user stories complete
