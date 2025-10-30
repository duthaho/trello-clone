# Architecture Documentation Navigation

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document provides visual navigation guides for the architecture documentation, showing how different documents relate to each other and recommended reading paths for different roles.

---

## Complete Documentation Map

```mermaid
graph TB
    Start[📖 Start Here] --> README[README.md<br/>Architecture Overview]
    README --> Quick[Quickstart Guide]
    README --> TOC[Table of Contents]
    README --> Glossary[Glossary]

    Quick --> Foundation[Foundation Documents]
    TOC --> Foundation

    Foundation --> Layers[Layers<br/>Clean Architecture]
    Foundation --> Components[Components<br/>System Parts]
    Foundation --> Contexts[Bounded Contexts<br/>DDD Domains]

    Layers --> Design[System Design]
    Components --> Design
    Contexts --> Design

    Design --> Diagrams[System Diagrams]
    Design --> DataFlows[Data Flows]
    Design --> API[API Design]

    Design --> ADRs[Architecture Decisions]
    ADRs --> ADR001[ADR-001<br/>Clean Architecture]
    ADRs --> ADR002[ADR-002<br/>Tech Stack]
    ADRs --> ADR003[ADR-003<br/>Bounded Contexts]

    Foundation --> Scale[Scalability & Performance]
    Scale --> Scalability[Scalability Patterns]
    Scale --> Performance[Performance Targets]
    Scale --> Caching[Caching Strategy]
    Scale --> DBOpt[Database Optimization]
    Scale --> Partition[Data Partitioning]
    Scale --> Capacity[Capacity Planning]

    Foundation --> Security[Security Architecture]
    Security --> Auth[Authentication]
    Security --> Authz[Authorization]
    Security --> DataProt[Data Protection]
    Security --> AuditLog[Audit Logging]
    Security --> OWASP[OWASP Compliance]
    Security --> Defense[Defense in Depth]

    Foundation --> Observability[Observability & Operations]
    Observability --> Logging[Logging]
    Observability --> Metrics[Metrics]
    Observability --> Tracing[Distributed Tracing]
    Observability --> Dashboards[Dashboards]
    Observability --> Alerting[Alerting]
    Observability --> Incident[Incident Response]
    Observability --> Runbooks[Runbooks]

    Foundation --> Deployment[Deployment & Infrastructure]
    Deployment --> Containers[Container Architecture]
    Deployment --> ECS[ECS Deployment]
    Deployment --> CICD[CI/CD Pipeline]
    Deployment --> Envs[Environment Management]
    Deployment --> IaC[Infrastructure as Code]
    Deployment --> DR[Disaster Recovery]

    style Start fill:#e1f5e1
    style README fill:#e1f5e1
    style Foundation fill:#fff4e1
    style Scale fill:#e1e5ff
    style Security fill:#ffe1e1
    style Observability fill:#f5e1ff
    style Deployment fill:#e1f5ff
```

---

## Learning Paths by Role

### Developer Path

**Goal**: Understand architecture to build features effectively

```mermaid
graph LR
    S1[1. Quickstart] --> S2[2. Layers]
    S2 --> S3[3. Components]
    S3 --> S4[4. Bounded Contexts]
    S4 --> S5[5. API Design]
    S5 --> S6[6. Data Flows]
    S6 --> S7[7. Logging/Metrics]

    style S1 fill:#e1f5e1
    style S2 fill:#e1f5e1
    style S3 fill:#e1f5e1
    style S4 fill:#e1f5e1
    style S5 fill:#fff4e1
    style S6 fill:#fff4e1
    style S7 fill:#fff4e1
```

**Reading List**:

1. [Quickstart Guide](./quickstart.md) - 15 min
2. [Layers](./layers.md) - 30 min
3. [Components](./components.md) - 30 min
4. [Bounded Contexts](./bounded-contexts.md) - 45 min
5. [API Design](./api-design.md) - 30 min
6. [Data Flows](./data-flows.md) - 30 min
7. [Logging](./observability/logging.md) - 20 min

**Total Time**: ~3.5 hours

---

### DevOps Engineer Path

**Goal**: Deploy and operate the system in production

```mermaid
graph LR
    D1[1. System Overview] --> D2[2. Container Architecture]
    D2 --> D3[3. ECS Deployment]
    D3 --> D4[4. CI/CD Pipeline]
    D4 --> D5[5. Environments]
    D5 --> D6[6. IaC Terraform]
    D6 --> D7[7. Disaster Recovery]
    D7 --> D8[8. Monitoring]

    style D1 fill:#e1f5e1
    style D2 fill:#e1f5ff
    style D3 fill:#e1f5ff
    style D4 fill:#e1f5ff
    style D5 fill:#e1f5ff
    style D6 fill:#e1f5ff
    style D7 fill:#e1f5ff
    style D8 fill:#f5e1ff
```

**Reading List**:

1. [System Overview](./diagrams/01-system-overview.md) - 20 min
2. [Container Architecture](./deployment/container-architecture.md) - 45 min
3. [ECS Deployment](./deployment/ecs-deployment.md) - 60 min
4. [CI/CD Pipeline](./deployment/ci-cd-pipeline.md) - 45 min
5. [Environment Management](./deployment/environments.md) - 45 min
6. [Infrastructure as Code](./deployment/infrastructure-as-code.md) - 45 min
7. [Disaster Recovery](./deployment/disaster-recovery.md) - 45 min
8. [Monitoring (Dashboards, Alerting, Runbooks)](./observability/) - 60 min

**Total Time**: ~6 hours

---

### Security Engineer Path

**Goal**: Validate security architecture and compliance

```mermaid
graph LR
    Sec1[1. Security Overview] --> Sec2[2. Authentication]
    Sec2 --> Sec3[3. Authorization]
    Sec3 --> Sec4[4. Data Protection]
    Sec4 --> Sec5[5. OWASP Compliance]
    Sec5 --> Sec6[6. Audit Logging]
    Sec6 --> Sec7[7. Defense in Depth]

    style Sec1 fill:#e1f5e1
    style Sec2 fill:#ffe1e1
    style Sec3 fill:#ffe1e1
    style Sec4 fill:#ffe1e1
    style Sec5 fill:#ffe1e1
    style Sec6 fill:#ffe1e1
    style Sec7 fill:#ffe1e1
```

**Reading List**:

1. [Security README](./security/README.md) - 10 min
2. [Authentication](./security/authentication.md) - 45 min
3. [Authorization](./security/authorization.md) - 45 min
4. [Data Protection](./security/data-protection.md) - 45 min
5. [OWASP Compliance](./security/owasp-compliance.md) - 60 min
6. [Audit Logging](./security/audit-logging.md) - 30 min
7. [Defense in Depth](./security/defense-in-depth.md) - 30 min

**Total Time**: ~4.5 hours

---

### Architect Path

**Goal**: Understand complete architecture and design decisions

```mermaid
graph LR
    A1[1. README] --> A2[2. ADRs]
    A2 --> A3[3. System Overview]
    A3 --> A4[4. Bounded Contexts]
    A4 --> A5[5. Scalability]
    A5 --> A6[6. Security]
    A6 --> A7[7. Observability]
    A7 --> A8[8. Deployment]

    style A1 fill:#e1f5e1
    style A2 fill:#fff4e1
    style A3 fill:#fff4e1
    style A4 fill:#fff4e1
    style A5 fill:#e1e5ff
    style A6 fill:#ffe1e1
    style A7 fill:#f5e1ff
    style A8 fill:#e1f5ff
```

**Reading List**:

1. [README.md](./README.md) - 15 min
2. All ADRs ([ADR-001](./decisions/adr-001-clean-architecture.md), [002](./decisions/adr-002-technology-stack.md), [003](./decisions/adr-003-bounded-contexts.md)) - 90 min
3. [System Overview](./diagrams/01-system-overview.md) - 30 min
4. [Bounded Contexts](./bounded-contexts.md) - 45 min
5. [Scalability](./scalability.md) + [Performance](./performance.md) + [Capacity Planning](./capacity-planning.md) - 120 min
6. All Security docs - 120 min
7. Observability overview - 60 min
8. Deployment overview - 90 min

**Total Time**: ~10 hours (comprehensive)

---

### Product Manager Path

**Goal**: Understand system capabilities and constraints

```mermaid
graph LR
    P1[1. Quickstart] --> P2[2. Bounded Contexts]
    P2 --> P3[3. Capacity Planning]
    P3 --> P4[4. Performance Targets]
    P4 --> P5[5. Incident Response]

    style P1 fill:#e1f5e1
    style P2 fill:#fff4e1
    style P3 fill:#e1e5ff
    style P4 fill:#e1e5ff
    style P5 fill:#f5e1ff
```

**Reading List**:

1. [Quickstart Guide](./quickstart.md) - 15 min
2. [Bounded Contexts](./bounded-contexts.md) - 30 min (feature domains)
3. [Capacity Planning](./capacity-planning.md) - 30 min (cost projections)
4. [Performance Targets](./performance.md) - 20 min (SLAs)
5. [Incident Response](./observability/incident-response.md) - 15 min

**Total Time**: ~2 hours

---

## Document Relationships

### Core Documents Hub

```mermaid
graph TB
    README[README.md<br/>📖 Central Hub]

    README --> Foundation[Foundation Layer]
    README --> ADRs[Architecture Decisions]
    README --> Scale[Scalability]
    README --> Sec[Security]
    README --> Obs[Observability]
    README --> Deploy[Deployment]

    Foundation --> Layers[Layers]
    Foundation --> Components[Components]
    Foundation --> Contexts[Bounded Contexts]

    Layers -.References.-> Components
    Components -.References.-> Contexts
    Contexts -.Implements.-> ADRs

    Scale -.Uses.-> Components
    Scale -.References.-> Contexts

    Sec -.Protects.-> Layers
    Sec -.Audits.-> Contexts

    Obs -.Monitors.-> Components
    Obs -.Traces.-> DataFlows[Data Flows]

    Deploy -.Deploys.-> Components
    Deploy -.Isolates.-> Envs[Environments]

    style README fill:#e1f5e1,stroke:#333,stroke-width:4px
    style Foundation fill:#fff4e1
    style Scale fill:#e1e5ff
    style Sec fill:#ffe1e1
    style Obs fill:#f5e1ff
    style Deploy fill:#e1f5ff
```

---

## Implementation Dependencies

### Document Build Order

```mermaid
graph TB
    Setup[Setup: README, Glossary, Quickstart]

    Setup --> Found[Foundation: Layers, Components, Contexts]
    Setup --> ADRs[ADRs: 001, 002, 003]

    Found --> Tech[Technology Choices]
    ADRs --> Tech

    Tech --> Impl[Implementation Docs]

    Impl --> Scale[Scalability Docs]
    Impl --> Sec[Security Docs]
    Impl --> Obs[Observability Docs]
    Impl --> Deploy[Deployment Docs]

    Scale --> DataFlows[Data Flows]
    Scale --> API[API Design]

    style Setup fill:#e1f5e1
    style Found fill:#fff4e1
    style ADRs fill:#fff4e1
    style Impl fill:#e1e5ff
```

**Dependency Rules**:

1. **Setup** documents can be created first (no dependencies)
2. **Foundation** and **ADRs** must exist before implementation docs
3. **Implementation docs** (Scale, Security, Observability, Deployment) can be created in parallel
4. **Cross-cutting docs** (Data Flows, API Design) reference multiple areas

---

## Documentation Categories

### By Abstraction Level

```mermaid
graph TB
    subgraph "High Level - Strategic"
        README[README.md]
        ADRs[ADRs]
        Overview[System Overview]
    end

    subgraph "Mid Level - Tactical"
        Layers[Layers]
        Components[Components]
        Contexts[Bounded Contexts]
        Patterns[Patterns]
    end

    subgraph "Low Level - Implementation"
        API[API Design]
        DataFlows[Data Flows]
        Code[Code Examples]
        Configs[Configurations]
    end

    README --> Layers
    ADRs --> Components
    Overview --> Contexts

    Layers --> API
    Components --> DataFlows
    Contexts --> Code
    Patterns --> Configs

    style README fill:#e1f5e1
    style Layers fill:#fff4e1
    style API fill:#e1e5ff
```

---

## Cross-Cutting Concerns Map

### Security Touchpoints

```mermaid
graph LR
    Security[Security Architecture]

    Security --> Auth[Authentication<br/>JWT + OAuth2]
    Security --> Authz[Authorization<br/>RBAC]
    Security --> DataProt[Data Protection<br/>Encryption]
    Security --> Audit[Audit Logging<br/>Compliance]

    Auth -.Secures.-> API[API Layer]
    Authz -.Controls.-> Components[Components]
    DataProt -.Encrypts.-> DB[(Database)]
    Audit -.Logs.-> Events[Domain Events]

    API -.Uses.-> Cache[(Redis Cache)]
    Components -.Access.-> DB
    DB -.Backs up to.-> S3[S3 Storage]
    Events -.Stream to.-> Queue[Message Queue]

    style Security fill:#ffe1e1
    style Auth fill:#ffe1e1
    style Authz fill:#ffe1e1
    style DataProt fill:#ffe1e1
    style Audit fill:#ffe1e1
```

### Observability Touchpoints

```mermaid
graph LR
    Obs[Observability Framework]

    Obs --> Logs[Structured Logging]
    Obs --> Metrics[Metrics Collection]
    Obs --> Traces[Distributed Tracing]
    Obs --> Alerts[Alerting]

    Logs -.Captures.-> API[API Requests]
    Metrics -.Measures.-> Services[Services]
    Traces -.Follows.-> Flows[Data Flows]
    Alerts -.Monitors.-> Infra[Infrastructure]

    API -.Generates.-> Events[Events]
    Services -.Execute.-> Tasks[Background Tasks]
    Flows -.Involve.-> DB[(Database)]
    Infra -.Runs.-> ECS[ECS Cluster]

    style Obs fill:#f5e1ff
    style Logs fill:#f5e1ff
    style Metrics fill:#f5e1ff
    style Traces fill:#f5e1ff
    style Alerts fill:#f5e1ff
```

---

## Quick Reference Cards

### New Developer Onboarding (Day 1-5)

| Day       | Focus                 | Documents                           | Time    |
| --------- | --------------------- | ----------------------------------- | ------- |
| **Day 1** | Architecture Overview | README, Quickstart, Glossary        | 2 hours |
| **Day 2** | Clean Architecture    | Layers, Components, ADR-001         | 3 hours |
| **Day 3** | Domain Model          | Bounded Contexts, Data Flows        | 3 hours |
| **Day 4** | API & Integration     | API Design, Authentication, Caching | 3 hours |
| **Day 5** | Operations            | Logging, Metrics, Deployment        | 2 hours |

**Total**: 13 hours of reading over 5 days

---

### Pre-Production Checklist

Review these documents before going to production:

```mermaid
graph TB
    Start{Production Ready?}

    Start --> Sec[Security: All 7 docs reviewed?]
    Sec -->|Yes| Obs[Observability: Monitoring setup?]
    Sec -->|No| SecFix[Review Security docs]

    Obs -->|Yes| Deploy[Deployment: IaC + DR ready?]
    Obs -->|No| ObsFix[Setup Monitoring]

    Deploy -->|Yes| Perf[Performance: Load tested?]
    Deploy -->|No| DeployFix[Complete Deployment]

    Perf -->|Yes| Ready[✅ Production Ready]
    Perf -->|No| PerfFix[Run Load Tests]

    style Start fill:#fff4e1
    style Ready fill:#e1f5e1
    style SecFix fill:#ffe1e1
    style ObsFix fill:#ffe1e1
    style DeployFix fill:#ffe1e1
    style PerfFix fill:#ffe1e1
```

**Required Documents**:

- ✅ All Security documents (Authentication, Authorization, Data Protection, Audit Logging, OWASP, Defense in Depth)
- ✅ Observability setup (Logging, Metrics, Tracing, Dashboards, Alerting)
- ✅ Deployment ready (Containers, ECS, CI/CD, Environments, IaC, Disaster Recovery)
- ✅ Performance validated (Performance targets, Load test results against targets)

---

## Document Update Flow

```mermaid
graph TB
    Change[Architecture Change]

    Change --> Impact{Impact Analysis}

    Impact --> Foundation[Foundation Change?]
    Impact --> Feature[Feature Change?]
    Impact --> Ops[Operational Change?]

    Foundation --> UpdateADR[Update/Create ADR]
    UpdateADR --> UpdateCore[Update Core Docs]
    UpdateCore --> UpdateDependent[Update Dependent Docs]

    Feature --> UpdateContext[Update Bounded Context]
    UpdateContext --> UpdateAPI[Update API Design]
    UpdateAPI --> UpdateFlows[Update Data Flows]

    Ops --> UpdateDeploy[Update Deployment Docs]
    UpdateDeploy --> UpdateRunbooks[Update Runbooks]
    UpdateRunbooks --> UpdateMonitoring[Update Monitoring]

    UpdateDependent --> Review[Review All Changes]
    UpdateFlows --> Review
    UpdateMonitoring --> Review

    Review --> UpdateTOC[Update Table of Contents]
    UpdateTOC --> Done[✅ Documentation Updated]

    style Change fill:#fff4e1
    style Done fill:#e1f5e1
```

---

## Navigation Best Practices

### For Reading

1. **Start with your role's learning path** (see above)
2. **Follow "Related Documents" links** at bottom of each document
3. **Use Table of Contents** for comprehensive overview
4. **Search by keyword** if looking for specific topic

### For Contributing

1. **Check document dependencies** before updating
2. **Update cross-references** when adding new documents
3. **Add entry to Table of Contents**
4. **Update navigation.md** if adding new category
5. **Follow document template** (see any existing doc)

### For Reviewing

1. **Use learning paths** to review by role
2. **Check cross-references** are accurate
3. **Verify diagrams render** correctly
4. **Validate code examples** are up-to-date

---

## Related Documents

- **[README.md](./README.md)** - Main architecture documentation index
- **[Table of Contents](./TABLE_OF_CONTENTS.md)** - Complete document listing
- **[Quickstart Guide](./quickstart.md)** - Getting started guide
- **[Glossary](./glossary.md)** - Key terms and definitions

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)  
**Maintainer**: Architecture Team  
**Feedback**: Submit documentation feedback via GitHub Issues
