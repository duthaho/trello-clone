# ADR-003: Bounded Context Definitions

**Status**: Accepted  
**Date**: 2025-10-30  
**Deciders**: Architecture Team  
**Context Owner**: System Architecture Design

## Context and Problem Statement

Following Domain-Driven Design principles, we need to define bounded contexts that partition the SaaS Task Management Platform into cohesive business domains. Each bounded context should have clear responsibilities, maintain its own consistency boundaries, and communicate with other contexts through well-defined contracts. We need to determine how to organize the business domain to maximize team autonomy, minimize coupling, and align with business capabilities.

## Decision Drivers

- **Business Alignment**: Contexts should reflect business capabilities, not technical layers
- **Team Autonomy**: Each context can be developed independently by different teams
- **Consistency Boundaries**: Clear rules about what data must be consistent within each context
- **Integration Contracts**: Explicit interfaces between contexts
- **Ubiquitous Language**: Each context has its own vocabulary from domain experts
- **Constitution Compliance**: Must support DDD principles (NON-NEGOTIABLE)

## Considered Options

1. **Five Bounded Contexts: Users, Projects, Tasks, Notifications, Audit** (Chosen)
2. Three Bounded Contexts: Core (Users+Projects+Tasks), Communication (Notifications), Compliance (Audit)
3. Seven Bounded Contexts: Users, Organizations, Projects, Tasks, Comments, Notifications, Audit
4. Single Context: Monolithic domain model

## Decision Outcome

**Chosen option**: "Five Bounded Contexts" because it provides the optimal balance of cohesion, autonomy, and complexity while aligning with business capabilities and team structure.

### Bounded Context Overview

| Context                | Responsibility                                              | Core Entities                        | Team          |
| ---------------------- | ----------------------------------------------------------- | ------------------------------------ | ------------- |
| **User Management**    | Authentication, authorization, user profiles, organizations | User, Organization, Role             | Identity Team |
| **Project Management** | Project lifecycle, membership, organization                 | Project, ProjectMember, ProjectTag   | Project Team  |
| **Task Management**    | Task workflow, assignments, comments, attachments           | Task, TaskComment, TaskAttachment    | Task Team     |
| **Notification**       | Multi-channel notifications, user preferences               | Notification, NotificationPreference | Platform Team |
| **Audit**              | Compliance logging, security audit trail                    | AuditLog                             | Security Team |

---

## Bounded Context Details

### 1. User Management Context

**Business Capability**: Manage user identities, authentication, authorization, and organizational structures.

**Ubiquitous Language**:

- **User**: Person with account access
- **Organization**: Multi-user tenant with subscription
- **Role**: Permission set (ADMIN, MEMBER, VIEWER)
- **Membership**: User-organization relationship
- **Authentication**: Verify user identity
- **Authorization**: Check user permissions

**Core Entities**:

- `User`: Identity, email, password, profile
- `Organization`: Tenant boundary, subscription tier
- `Role`: RBAC permission set
- `Membership`: User-org-role association

**Value Objects**:

- `Email`: Validated email address
- `PasswordHash`: Bcrypt-hashed password
- `SubscriptionTier`: FREE, PRO, ENTERPRISE

**Aggregates**:

- `User` (root): Manages own profile and authentication
- `Organization` (root): Manages members and subscriptions

**Domain Events**:

- `UserRegistered`
- `UserLoggedIn`
- `OrganizationCreated`
- `MemberAddedToOrganization`
- `UserRoleChanged`

**Invariants**:

- Email must be unique globally
- Organization must have at least one owner
- Member count cannot exceed subscription limit

**External Dependencies**: None (pure domain logic)

**Integration Points**:

- **→ Project Management**: Validates user organization membership
- **→ Task Management**: Validates user access to tasks
- **→ Notification**: Triggers notifications for user events
- **→ Audit**: Logs all user/org changes

---

### 2. Project Management Context

**Business Capability**: Organize work into projects, manage project teams, and control project visibility.

**Ubiquitous Language**:

- **Project**: Container for related tasks
- **Project Owner**: User responsible for project
- **Project Member**: User with project access
- **Project Visibility**: PRIVATE, TEAM, PUBLIC
- **Project Status**: ACTIVE, ARCHIVED, DELETED
- **Project Tag**: Categorization label

**Core Entities**:

- `Project`: Name, description, status, visibility
- `ProjectMember`: User-project-role association
- `ProjectTag`: Label with color

**Value Objects**:

- `ProjectSlug`: URL-friendly identifier
- `Color`: Hex color code
- `ProjectRole`: OWNER, ADMIN, CONTRIBUTOR, VIEWER

**Aggregates**:

- `Project` (root): Manages members and tags

**Domain Events**:

- `ProjectCreated`
- `ProjectArchived`
- `MemberAddedToProject`
- `MemberRemovedFromProject`
- `ProjectOwnershipTransferred`

**Invariants**:

- Project must have at least one owner
- Owner must be member of parent organization
- Project name unique within organization
- Cannot archive project with critical incomplete tasks (future enhancement)

**External Dependencies**:

- **User Management**: Validates organization membership

**Integration Points**:

- **← User Management**: Receives user/org validation
- **→ Task Management**: Provides project context for tasks
- **→ Notification**: Triggers project-related notifications
- **→ Audit**: Logs project changes

---

### 3. Task Management Context

**Business Capability**: Manage task lifecycle, assignments, comments, attachments, and workflow state transitions.

**Ubiquitous Language**:

- **Task**: Work item with title, description, status
- **Status**: TODO, IN_PROGRESS, IN_REVIEW, DONE, BLOCKED
- **Priority**: LOW, MEDIUM, HIGH, URGENT
- **Assignment**: Task-user association
- **Subtask**: Child task under parent
- **Comment**: Discussion on task
- **Attachment**: File linked to task

**Core Entities**:

- `Task`: Title, description, status, priority, due date
- `TaskComment`: User comment with markdown
- `TaskAttachment`: File metadata and storage path

**Value Objects**:

- `TaskStatus`: Enum with transition rules
- `TaskPriority`: Enum with ordering
- `Markdown`: Validated markdown content

**Aggregates**:

- `Task` (root): Manages comments, attachments, subtasks

**Domain Events**:

- `TaskCreated`
- `TaskAssigned`
- `TaskStatusChanged`
- `TaskCompleted`
- `CommentAdded`
- `AttachmentUploaded`

**Invariants**:

- Cannot assign to user not in project
- Cannot complete parent task with incomplete subtasks
- Position unique within project
- Due date must be future when set
- File size limited to 50 MB

**External Dependencies**:

- **User Management**: Validates user access
- **Project Management**: Validates project existence

**Integration Points**:

- **← User Management**: Receives user validation
- **← Project Management**: Receives project context
- **→ Notification**: Triggers task-related notifications
- **→ Audit**: Logs task changes

---

### 4. Notification Context

**Business Capability**: Deliver notifications to users across multiple channels (email, push, in-app) based on preferences.

**Ubiquitous Language**:

- **Notification**: Message to user about event
- **Channel**: Email, push, in-app
- **Preference**: User's channel settings per notification type
- **Notification Type**: TASK_ASSIGNED, MENTION, COMMENT, etc.
- **Read Status**: Unread vs read

**Core Entities**:

- `Notification`: Message, type, recipient, read status
- `NotificationPreference`: User settings per type and channel

**Value Objects**:

- `NotificationType`: Enum of event types
- `NotificationChannel`: EMAIL, PUSH, IN_APP
- `ActionURL`: Link to related resource

**Aggregates**:

- `Notification` (root): Single notification instance
- `NotificationPreference` (root): User's preferences

**Domain Events**:

- `NotificationCreated`
- `NotificationRead`
- `NotificationPreferenceUpdated`

**Invariants**:

- At least one channel enabled per type
- Action URL must be valid if present
- Cannot mark as read before creation

**External Dependencies**:

- Email service (AWS SES)
- Push notification service

**Integration Points**:

- **← User Management**: Subscribes to user events
- **← Project Management**: Subscribes to project events
- **← Task Management**: Subscribes to task events
- **→ Audit**: Logs notification delivery

---

### 5. Audit Context

**Business Capability**: Maintain immutable audit trail of all security-relevant and compliance-required system events.

**Ubiquitous Language**:

- **Audit Log**: Immutable record of action
- **Action**: CREATE, UPDATE, DELETE, LOGIN, etc.
- **Entity**: Object being acted upon
- **Change Set**: Before/after state
- **Correlation ID**: Request trace identifier

**Core Entities**:

- `AuditLog`: Timestamp, user, action, entity, changes

**Value Objects**:

- `AuditAction`: Enum of auditable actions
- `IPAddress`: Validated IP address
- `ChangeSet`: JSON before/after snapshot

**Aggregates**:

- `AuditLog` (root): Append-only record

**Domain Events**:

- `AuditLogCreated` (not republished to avoid loops)

**Invariants**:

- Cannot update or delete (append-only)
- Timestamp cannot be future
- Must have user_id or system_id
- Changes must be JSON-serializable

**External Dependencies**: None (pure domain logic)

**Integration Points**:

- **← All Contexts**: Subscribes to all domain events
- Data retention: 12 months hot storage, archive to S3 thereafter

---

## Context Integration Patterns

### Event-Driven Integration (Preferred)

Contexts communicate asynchronously via domain events:

```
User Management publishes: UserRemovedFromOrganization
  ↓
Project Management subscribes: Remove user from all org projects
  ↓
Task Management subscribes: Unassign user from all tasks
```

**Pros**: Loose coupling, resilience, scalability  
**Cons**: Eventual consistency, requires event bus

### Synchronous Integration (When Needed)

Some operations require immediate validation:

```
Task Assignment Request
  ↓
Task Management calls User Management: "Is user in project?"
  ↓
User Management returns: Yes/No
  ↓
Task Management: Assign or reject
```

**Pros**: Strong consistency, immediate feedback  
**Cons**: Tighter coupling, availability dependency

### Anti-Corruption Layer

Each context protects its domain model from external concepts:

```
Task Management Domain
  ↓
  [ACL: Maps external User ID → Internal Assignee]
  ↓
User Management API
```

---

## Context Boundaries - What Goes Where?

### User Management Owns

✅ User authentication and authorization  
✅ Organization and subscription management  
✅ Role and permission definitions  
✅ User profile and preferences (non-notification)  
❌ NOT: Task assignments (that's Task Management's concern)  
❌ NOT: Project access (that's Project Management's concern)

### Project Management Owns

✅ Project lifecycle (create, archive, delete)  
✅ Project membership and roles  
✅ Project tags and categorization  
❌ NOT: Tasks within projects (that's Task Management)  
❌ NOT: User authentication (that's User Management)

### Task Management Owns

✅ Task lifecycle and workflow  
✅ Task assignments and reassignments  
✅ Comments and attachments  
✅ Subtask relationships  
❌ NOT: User permissions (validates via User Management)  
❌ NOT: Project existence (validates via Project Management)

### Notification Owns

✅ Notification creation and delivery  
✅ User notification preferences  
✅ Read/unread status  
❌ NOT: What events trigger notifications (other contexts decide)  
❌ NOT: User authentication (that's User Management)

### Audit Owns

✅ Immutable audit trail  
✅ Compliance reporting  
✅ Security event logging  
❌ NOT: Authorization decisions (that's User Management)  
❌ NOT: Business logic (observes, doesn't participate)

---

## Shared Kernel vs Separate Models

**Decision**: Each context maintains its own domain model with NO shared entity classes.

**Rationale**:

- Prevents tight coupling between contexts
- Enables independent evolution of models
- Forces explicit integration contracts

**Example**:

```python
# User Management Context
class User:
    user_id: UUID
    email: Email
    full_name: str
    # ... user-specific logic

# Task Management Context
class TaskAssignee:
    user_id: UUID  # References User, but separate class
    display_name: str
    # ... task-specific needs
```

**Integration**: Use DTOs (Data Transfer Objects) or domain events to communicate between contexts.

---

## Future Microservices Evolution

If the system grows beyond monolithic deployment, these bounded contexts provide natural boundaries for microservices:

**Phase 1 (Current)**: Monolithic application with bounded contexts  
**Phase 2 (50K+ users)**: Extract Notification to separate service  
**Phase 3 (100K+ users)**: Extract Audit to separate service  
**Phase 4 (500K+ users)**: Split into full microservices

**Migration Strategy**:

1. Each context already has its own database schema (logical separation)
2. Replace in-process domain events with message queue (Kafka/SNS)
3. Deploy each context as separate container
4. Implement API gateway for routing

---

## Validation Criteria

This decision will be validated by:

1. **Team Autonomy**: Teams can work on different contexts without blocking
2. **Code Review**: No direct class references across context boundaries
3. **Test Independence**: Each context's tests run in isolation
4. **Integration Tests**: Event-driven integration works correctly
5. **Developer Survey**: Clear understanding of context responsibilities

---

## Trade-offs Analysis

### Five Contexts (Chosen) vs Three Contexts

**Five Contexts**:

- ✅ More granular team ownership
- ✅ Clearer single responsibilities
- ❌ More integration points to manage

**Three Contexts**:

- ✅ Fewer integration contracts
- ❌ Less clear ownership (User+Project+Task together is too broad)
- ❌ Harder to split teams

### Five Contexts vs Seven Contexts

**Five Contexts**:

- ✅ Sufficient granularity for current scale
- ✅ Manageable integration complexity

**Seven Contexts** (split Tasks and Comments separately):

- ❌ Over-engineering for initial scale
- ❌ Comments are tightly bound to Tasks (same aggregate)

### Five Contexts vs Single Context

**Five Contexts**:

- ✅ Team autonomy and parallel development
- ✅ Independent deployment (future microservices)

**Single Context**:

- ❌ Everything tightly coupled
- ❌ No clear boundaries
- ❌ Violates DDD principles

---

## Related Decisions

- [ADR-001: Clean Architecture with DDD](./adr-001-clean-architecture.md)
- [ADR-002: Technology Stack Selection](./adr-002-technology-stack.md)
- [ADR-004: Deployment Strategy](./adr-004-deployment-strategy.md)

## References

- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/)
- [Bounded Context Pattern](https://martinfowler.com/bliki/BoundedContext.html)
- [Context Mapping](https://www.infoq.com/articles/ddd-contextmapping/)
- [Implementing DDD (Vaughn Vernon)](https://vaughnvernon.com/iddd/)
- [Constitution: DDD Principle](../../.specify/memory/constitution.md#ii-domain-driven-design-ddd)
