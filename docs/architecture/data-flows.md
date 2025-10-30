# Data Flows

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document describes end-to-end data flows for key system operations, showing how data moves through different layers and components. Each flow demonstrates Clean Architecture principles in action.

---

## Flow Categories

| Flow Type        | Examples                                  | Characteristics                             |
| ---------------- | ----------------------------------------- | ------------------------------------------- |
| **Synchronous**  | Authentication, Create Task, Get Projects | Client waits for response, <500ms           |
| **Asynchronous** | Send Email, Process Notification          | Background processing, eventual consistency |
| **Scheduled**    | Daily Digest, Cleanup Jobs                | Time-triggered, batch processing            |
| **Event-Driven** | Task Assignment → Notification            | Reactive, decoupled components              |

---

## Authentication Flow

### User Login

```mermaid
sequenceDiagram
    participant Client
    participant ALB
    participant API
    participant AuthController
    participant LoginUseCase
    participant UserRepo
    participant Cache
    participant DB
    participant AuditLog

    Client->>ALB: POST /api/v1/auth/login
    Note over Client: {email, password}

    ALB->>API: Forward request
    API->>AuthController: handle_login(request)

    AuthController->>LoginUseCase: execute(LoginCommand)

    LoginUseCase->>UserRepo: get_by_email(email)
    UserRepo->>Cache: check cache
    Cache-->>UserRepo: cache miss
    UserRepo->>DB: SELECT * FROM users WHERE email = ?
    DB-->>UserRepo: user_model
    UserRepo-->>LoginUseCase: User entity

    LoginUseCase->>LoginUseCase: verify_password(hashed)
    Note over LoginUseCase: bcrypt.verify()

    LoginUseCase->>LoginUseCase: generate_jwt_tokens()
    Note over LoginUseCase: access_token (15 min)<br/>refresh_token (30 days)

    LoginUseCase->>Cache: set(session:token, user_data, ttl=900)
    Cache-->>LoginUseCase: OK

    LoginUseCase->>AuditLog: log_event(UserLoggedIn)
    AuditLog-->>LoginUseCase: OK

    LoginUseCase-->>AuthController: TokenPair
    AuthController-->>API: 200 OK {access_token, refresh_token}
    API-->>ALB: response
    ALB-->>Client: JSON response
```

**Data Transformations**:

1. **Client Request** (JSON):

   ```json
   {
     "email": "user@example.com",
     "password": "SecurePass123!"
   }
   ```

2. **LoginCommand** (DTO):

   ```python
   LoginCommand(
       email="user@example.com",
       password="SecurePass123!"
   )
   ```

3. **Database Query**:

   ```sql
   SELECT user_id, email, password_hash, status, created_at
   FROM users
   WHERE email = 'user@example.com' AND status = 'ACTIVE'
   ```

4. **Domain Entity**:

   ```python
   User(
       user_id=UUID('...'),
       email=Email('user@example.com'),
       password_hash='$2b$12$...',
       status=UserStatus.ACTIVE
   )
   ```

5. **Response** (JSON):
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
     "token_type": "Bearer",
     "expires_in": 900
   }
   ```

**Performance Characteristics**:

- **p50**: 50ms
- **p95**: 120ms
- **p99**: 200ms
- **Database Queries**: 1 (cached after first access)
- **Cache Operations**: 2 (read + write)

---

### Token Validation (Middleware)

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant AuthMiddleware
    participant Cache
    participant JWT

    Client->>API: GET /api/v1/tasks
    Note over Client: Authorization: Bearer <token>

    API->>AuthMiddleware: validate_request()

    AuthMiddleware->>AuthMiddleware: extract_token(header)

    AuthMiddleware->>Cache: exists(blacklist:token)
    Cache-->>AuthMiddleware: false

    AuthMiddleware->>JWT: decode(token, secret)
    Note over JWT: Verify signature<br/>Check expiration
    JWT-->>AuthMiddleware: payload

    AuthMiddleware->>Cache: get(session:token)
    Cache-->>AuthMiddleware: user_context

    AuthMiddleware->>API: set request.user
    Note over API: Continue to controller
```

**Fast Path** (cached session):

- Cache check: 2ms
- JWT decode: 5ms
- **Total**: ~7ms overhead per request

---

## Task Creation Flow

### End-to-End Task Creation

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant TaskController
    participant AuthzService
    participant CreateTaskUseCase
    participant ProjectRepo
    participant TaskRepo
    participant Cache
    participant DB
    participant EventBus
    participant Queue
    participant Worker
    participant NotifService

    Client->>API: POST /api/v1/tasks
    Note over Client: Authorization: Bearer <token><br/>{title, description, project_id}

    API->>API: AuthMiddleware validates token
    API->>TaskController: create_task(request, current_user)

    TaskController->>TaskController: validate request schema
    Note over TaskController: Pydantic validation

    TaskController->>AuthzService: can_access_project(user_id, project_id)
    AuthzService->>Cache: get(authz:user:{id}:project:{id})

    alt Cache Hit
        Cache-->>AuthzService: true
    else Cache Miss
        AuthzService->>ProjectRepo: get_membership(project_id, user_id)
        ProjectRepo->>DB: SELECT * FROM project_members
        DB-->>ProjectRepo: membership
        ProjectRepo-->>AuthzService: membership
        AuthzService->>Cache: set(authz:..., true, ttl=300)
    end

    AuthzService-->>TaskController: authorized

    TaskController->>CreateTaskUseCase: execute(CreateTaskCommand)

    CreateTaskUseCase->>ProjectRepo: get_by_id(project_id)
    ProjectRepo->>Cache: get(project:{id})

    alt Cache Hit
        Cache-->>ProjectRepo: project
    else Cache Miss
        ProjectRepo->>DB: SELECT * FROM projects
        DB-->>ProjectRepo: project_model
        ProjectRepo->>Cache: set(project:{id}, ...)
    end

    ProjectRepo-->>CreateTaskUseCase: Project entity

    CreateTaskUseCase->>CreateTaskUseCase: Task.create(...)
    Note over CreateTaskUseCase: Domain entity created<br/>TaskCreatedEvent recorded

    CreateTaskUseCase->>TaskRepo: save(task)
    TaskRepo->>DB: BEGIN TRANSACTION
    TaskRepo->>DB: INSERT INTO tasks (...)
    DB-->>TaskRepo: task_id
    TaskRepo->>DB: COMMIT
    TaskRepo->>Cache: set(task:{id}, task_data, ttl=60)
    TaskRepo->>Cache: delete(tasks:project:{id}:*)
    Note over TaskRepo: Invalidate project task lists
    TaskRepo-->>CreateTaskUseCase: success

    CreateTaskUseCase->>EventBus: publish(TaskCreatedEvent)
    EventBus->>Queue: lpush(event_queue, event)
    Queue-->>EventBus: OK
    EventBus-->>CreateTaskUseCase: OK

    CreateTaskUseCase-->>TaskController: Task entity
    TaskController-->>API: 201 Created {task_response}
    API-->>Client: JSON response

    Note over Queue,Worker: Asynchronous processing

    Worker->>Queue: rpop(event_queue)
    Queue-->>Worker: TaskCreatedEvent

    Worker->>NotifService: handle_task_created(event)
    NotifService->>NotifService: create_notification()
    NotifService->>DB: INSERT INTO notifications
    NotifService->>Worker: enqueue(send_email_task)

    Worker->>Worker: send_email_task.delay()
    Note over Worker: Email sent asynchronously
```

**Data Transformations**:

1. **HTTP Request**:

   ```json
   POST /api/v1/tasks
   Authorization: Bearer eyJhbGci...
   Content-Type: application/json

   {
     "title": "Implement user authentication",
     "description": "Add JWT-based authentication",
     "project_id": "123e4567-e89b-12d3-a456-426614174000",
     "assignee_id": null,
     "due_date": "2025-11-15T23:59:59Z",
     "priority": "HIGH"
   }
   ```

2. **CreateTaskCommand** (Application Layer):

   ```python
   CreateTaskCommand(
       title="Implement user authentication",
       description="Add JWT-based authentication",
       project_id=UUID('123e4567-e89b-12d3-a456-426614174000'),
       created_by=UUID('user-id-from-token'),
       assignee_id=None,
       due_date=datetime(2025, 11, 15, 23, 59, 59),
       priority=TaskPriority.HIGH
   )
   ```

3. **Domain Entity Creation**:

   ```python
   task = Task.create(
       title="Implement user authentication",
       description="Add JWT-based authentication",
       project_id=UUID('123e4567-...'),
       created_by=UUID('user-id-...')
   )
   # task.task_id generated (UUID)
   # task.status = TaskStatus.TODO
   # task.created_at = datetime.now()
   # task.domain_events = [TaskCreatedEvent(...)]
   ```

4. **Database Insert**:

   ```sql
   INSERT INTO tasks (
       task_id, title, description, project_id,
       created_by, status, priority, due_date, created_at
   ) VALUES (
       '456e7890-e89b-12d3-a456-426614174001',
       'Implement user authentication',
       'Add JWT-based authentication',
       '123e4567-e89b-12d3-a456-426614174000',
       'user-id-from-token',
       'TODO',
       'HIGH',
       '2025-11-15 23:59:59',
       '2025-10-30 14:23:45'
   )
   ```

5. **Domain Event**:

   ```python
   TaskCreatedEvent(
       aggregate_id=UUID('456e7890-...'),
       task_id=UUID('456e7890-...'),
       title="Implement user authentication",
       project_id=UUID('123e4567-...'),
       created_by=UUID('user-id-...'),
       occurred_at=datetime.now()
   )
   ```

6. **HTTP Response**:

   ```json
   HTTP/1.1 201 Created
   Content-Type: application/json

   {
     "task_id": "456e7890-e89b-12d3-a456-426614174001",
     "title": "Implement user authentication",
     "description": "Add JWT-based authentication",
     "status": "TODO",
     "priority": "HIGH",
     "project_id": "123e4567-e89b-12d3-a456-426614174000",
     "created_by": "user-id-from-token",
     "assignee_id": null,
     "due_date": "2025-11-15T23:59:59Z",
     "created_at": "2025-10-30T14:23:45Z",
     "updated_at": "2025-10-30T14:23:45Z"
   }
   ```

**Performance Characteristics**:

- **Synchronous Path** (API response):
  - Authorization check: 5-10ms (cached)
  - Project lookup: 5-10ms (cached)
  - Task creation: 20-30ms (domain logic)
  - Database insert: 10-20ms
  - Cache operations: 5-10ms
  - **Total p95**: <100ms
- **Asynchronous Path** (event processing):
  - Event publish: 5ms
  - Worker pickup: 50-200ms (queue polling)
  - Notification creation: 20-50ms
  - Email delivery: 1-3 seconds (external service)

---

## Task Assignment Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant TaskController
    participant AssignTaskUseCase
    participant TaskRepo
    participant UserRepo
    participant EventBus
    participant DB
    participant Queue
    participant Worker
    participant NotifService
    participant EmailService

    Client->>API: PATCH /api/v1/tasks/{id}/assign
    Note over Client: {assignee_id}

    API->>TaskController: assign_task(task_id, assignee_id)
    TaskController->>AssignTaskUseCase: execute(command)

    AssignTaskUseCase->>TaskRepo: get_by_id(task_id)
    TaskRepo->>DB: SELECT * FROM tasks
    DB-->>TaskRepo: task_model
    TaskRepo-->>AssignTaskUseCase: Task entity

    AssignTaskUseCase->>UserRepo: get_by_id(assignee_id)
    UserRepo->>DB: SELECT * FROM users
    DB-->>UserRepo: user_model
    UserRepo-->>AssignTaskUseCase: User entity

    AssignTaskUseCase->>AssignTaskUseCase: task.assign_to(user)
    Note over AssignTaskUseCase: Domain method:<br/>- Validates user status<br/>- Records TaskAssignedEvent

    AssignTaskUseCase->>TaskRepo: save(task)
    TaskRepo->>DB: UPDATE tasks SET assignee_id = ?, updated_at = ?
    DB-->>TaskRepo: OK
    TaskRepo-->>AssignTaskUseCase: success

    AssignTaskUseCase->>EventBus: publish(TaskAssignedEvent)
    EventBus->>Queue: lpush(event_queue, event)

    AssignTaskUseCase-->>TaskController: Task entity
    TaskController-->>API: 200 OK
    API-->>Client: {task_response}

    Note over Worker: Background processing

    Worker->>Queue: rpop(event_queue)
    Queue-->>Worker: TaskAssignedEvent

    Worker->>NotifService: handle_task_assigned(event)

    NotifService->>NotifService: Check user preferences
    NotifService->>DB: SELECT * FROM notification_preferences
    DB-->>NotifService: preferences

    alt Email Enabled
        NotifService->>EmailService: send_task_assignment_email()
        EmailService->>EmailService: render_template()
        EmailService->>EmailService: AWS SES send_email()
        Note over EmailService: Subject: "Task Assigned: {title}"
    end

    NotifService->>DB: INSERT INTO notifications
    Note over NotifService: In-app notification

    NotifService-->>Worker: success
```

**Key Points**:

- **Synchronous**: Client gets immediate confirmation
- **Asynchronous**: Email sent in background (non-blocking)
- **User Preferences**: Notification channels configurable per user

---

## Notification Delivery Flow

### Multi-Channel Notification

```mermaid
sequenceDiagram
    participant EventBus
    participant Worker
    participant NotifService
    participant UserRepo
    participant NotifRepo
    participant EmailService
    participant PushService
    participant DB

    EventBus->>Worker: TaskAssignedEvent

    Worker->>NotifService: process_event(event)

    NotifService->>UserRepo: get_by_id(assignee_id)
    UserRepo->>DB: SELECT * FROM users
    DB-->>UserRepo: user
    UserRepo-->>NotifService: User entity

    NotifService->>NotifRepo: get_preferences(user_id)
    NotifRepo->>DB: SELECT * FROM notification_preferences
    DB-->>NotifRepo: preferences
    NotifRepo-->>NotifService: NotificationPreferences

    NotifService->>NotifService: create_notification()

    NotifService->>NotifRepo: save(notification)
    NotifRepo->>DB: INSERT INTO notifications
    DB-->>NotifRepo: notification_id
    NotifRepo-->>NotifService: Notification entity

    par Email Channel
        alt Email Enabled
            NotifService->>EmailService: send(template, data)
            EmailService->>EmailService: render_jinja_template()
            EmailService->>EmailService: aws_ses.send_email()
            EmailService-->>NotifService: message_id
            NotifService->>DB: UPDATE notifications SET email_sent_at = NOW()
        end
    and Push Channel
        alt Push Enabled & Device Token Exists
            NotifService->>PushService: send_push(user_id, message)
            PushService->>PushService: firebase.send()
            PushService-->>NotifService: success
            NotifService->>DB: UPDATE notifications SET push_sent_at = NOW()
        end
    and In-App Channel
        NotifService->>NotifService: Already saved to DB
        Note over NotifService: Available via GET /api/v1/notifications
    end

    NotifService-->>Worker: success
```

**Notification Channels**:

| Channel     | Delivery Method          | Latency     | Retry Logic                    |
| ----------- | ------------------------ | ----------- | ------------------------------ |
| **In-App**  | Database insert          | Immediate   | N/A (persistent)               |
| **Email**   | AWS SES                  | 1-3 seconds | 3 retries, exponential backoff |
| **Push**    | Firebase Cloud Messaging | 500ms-2s    | 3 retries, exponential backoff |
| **Webhook** | HTTP POST                | 1-5 seconds | 5 retries, exponential backoff |

**User Preferences**:

```python
class NotificationPreferences:
    user_id: UUID
    email_enabled: bool = True
    push_enabled: bool = True
    email_digest: bool = True  # Daily digest
    email_frequency: str = "IMMEDIATE"  # or "DIGEST", "DISABLED"
    channels: Dict[str, ChannelConfig] = {
        "task_assigned": {"email": True, "push": True, "in_app": True},
        "task_completed": {"email": False, "push": True, "in_app": True},
        "comment_added": {"email": False, "push": False, "in_app": True},
        "due_date_reminder": {"email": True, "push": True, "in_app": True}
    }
```

---

## Daily Digest Flow (Scheduled)

```mermaid
sequenceDiagram
    participant CeleryBeat
    participant Queue
    participant Worker
    participant DigestService
    participant NotifRepo
    participant UserRepo
    participant EmailService
    participant DB

    Note over CeleryBeat: Cron: 8:00 AM daily

    CeleryBeat->>Queue: enqueue(generate_daily_digest)

    Worker->>Queue: dequeue task
    Queue-->>Worker: generate_daily_digest

    Worker->>DigestService: generate_all_digests()

    DigestService->>UserRepo: list_users_with_digest_enabled()
    UserRepo->>DB: SELECT * FROM users JOIN notification_preferences
    DB-->>UserRepo: user_list
    UserRepo-->>DigestService: List[User]

    loop For each user
        DigestService->>NotifRepo: get_unread_since(user_id, yesterday)
        NotifRepo->>DB: SELECT * FROM notifications WHERE ...
        DB-->>NotifRepo: notifications
        NotifRepo-->>DigestService: List[Notification]

        alt Has unread notifications
            DigestService->>DigestService: aggregate_notifications()
            Note over DigestService: Group by type<br/>Calculate stats

            DigestService->>EmailService: send_digest(user, summary)
            EmailService->>EmailService: render_template("daily_digest.html")
            Note over EmailService: Summary:<br/>- 5 new tasks assigned<br/>- 3 comments on your tasks<br/>- 2 tasks completed

            EmailService->>EmailService: aws_ses.send_email()
            EmailService-->>DigestService: message_id

            DigestService->>DB: INSERT INTO email_logs
        end
    end

    DigestService-->>Worker: Summary(sent=245, skipped=31, failed=2)
    Worker->>Worker: Log metrics
```

**Digest Email Structure**:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Your Daily Update</title>
  </head>
  <body>
    <h1>Good morning, {{user.name}}!</h1>

    <section>
      <h2>📋 Tasks (5 new)</h2>
      <ul>
        <li>
          <strong>High Priority:</strong> Implement authentication (Due: Today)
        </li>
        <li>Fix bug in user profile (Due: Tomorrow)</li>
        <!-- ... -->
      </ul>
    </section>

    <section>
      <h2>💬 Comments (3 new)</h2>
      <ul>
        <li>@john commented on "Implement authentication"</li>
        <!-- ... -->
      </ul>
    </section>

    <section>
      <h2>✅ Completed (2 tasks)</h2>
      <ul>
        <li>Design mockups - by @sarah</li>
        <!-- ... -->
      </ul>
    </section>

    <footer>
      <a href="{{app_url}}/notifications">View all notifications</a>
      <a href="{{app_url}}/settings/notifications">Manage preferences</a>
    </footer>
  </body>
</html>
```

---

## Project Creation Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant ProjectController
    participant CreateProjectUseCase
    participant ProjectRepo
    participant OrgRepo
    participant EventBus
    participant DB
    participant Cache

    Client->>API: POST /api/v1/projects
    Note over Client: {name, organization_id}

    API->>ProjectController: create_project(request, current_user)
    ProjectController->>CreateProjectUseCase: execute(command)

    CreateProjectUseCase->>OrgRepo: get_by_id(organization_id)
    OrgRepo->>DB: SELECT * FROM organizations
    DB-->>OrgRepo: organization
    OrgRepo-->>CreateProjectUseCase: Organization entity

    CreateProjectUseCase->>CreateProjectUseCase: org.can_create_project(user_id)
    Note over CreateProjectUseCase: Check membership & permissions

    CreateProjectUseCase->>CreateProjectUseCase: Project.create(...)
    Note over CreateProjectUseCase: Domain entity created<br/>Owner auto-assigned

    CreateProjectUseCase->>DB: BEGIN TRANSACTION

    CreateProjectUseCase->>ProjectRepo: save(project)
    ProjectRepo->>DB: INSERT INTO projects
    DB-->>ProjectRepo: project_id

    CreateProjectUseCase->>ProjectRepo: add_member(project_id, user_id, OWNER)
    ProjectRepo->>DB: INSERT INTO project_members
    DB-->>ProjectRepo: member_id

    CreateProjectUseCase->>DB: COMMIT

    CreateProjectUseCase->>Cache: delete(projects:org:{org_id}:*)
    Note over Cache: Invalidate org project lists

    CreateProjectUseCase->>EventBus: publish(ProjectCreatedEvent)
    EventBus->>EventBus: publish event

    CreateProjectUseCase-->>ProjectController: Project entity
    ProjectController-->>API: 201 Created
    API-->>Client: {project_response}
```

**Transaction Boundary**:

```python
@transactional
def execute(self, command: CreateProjectCommand) -> Project:
    # All database operations within this method
    # are part of a single transaction

    org = self.org_repo.get_by_id(command.organization_id)

    project = Project.create(
        name=command.name,
        organization_id=command.organization_id
    )

    self.project_repo.save(project)  # INSERT INTO projects
    self.project_repo.add_member(
        project.project_id,
        command.created_by,
        ProjectRole.OWNER
    )  # INSERT INTO project_members

    # Both operations commit together or rollback together

    return project
```

---

## Error Handling Flow

### Validation Error

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Controller
    participant UseCase

    Client->>API: POST /api/v1/tasks
    Note over Client: {title: "", project_id: "invalid"}

    API->>Controller: create_task(request)
    Controller->>Controller: validate_schema(request_body)
    Note over Controller: Pydantic validation

    Controller-->>API: ValidationError
    API-->>Client: 422 Unprocessable Entity
    Note over Client: {<br/>  "detail": [<br/>    {"field": "title", "error": "min length 1"},<br/>    {"field": "project_id", "error": "invalid UUID"}<br/>  ]<br/>}
```

### Business Logic Error

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Controller
    participant UseCase
    participant TaskRepo
    participant DB

    Client->>API: PATCH /api/v1/tasks/{id}/complete

    API->>Controller: complete_task(task_id)
    Controller->>UseCase: execute(command)

    UseCase->>TaskRepo: get_by_id(task_id)
    TaskRepo->>DB: SELECT
    DB-->>TaskRepo: task
    TaskRepo-->>UseCase: Task entity

    UseCase->>UseCase: task.complete()
    Note over UseCase: Domain rule:<br/>Cannot complete task<br/>with pending subtasks

    UseCase-->>Controller: DomainError("Cannot complete task with pending subtasks")
    Controller-->>API: 409 Conflict
    API-->>Client: {<br/>  "error": "TASK_HAS_PENDING_SUBTASKS",<br/>  "message": "Cannot complete...",<br/>  "pending_count": 3<br/>}
```

### Infrastructure Error with Retry

```mermaid
sequenceDiagram
    participant Worker
    participant EmailService
    participant AWS_SES

    Worker->>EmailService: send_email(to, subject, body)
    EmailService->>AWS_SES: send_email()
    AWS_SES-->>EmailService: ThrottlingException

    EmailService->>EmailService: Retry attempt 1
    Note over EmailService: Wait 2 seconds

    EmailService->>AWS_SES: send_email()
    AWS_SES-->>EmailService: ThrottlingException

    EmailService->>EmailService: Retry attempt 2
    Note over EmailService: Wait 4 seconds

    EmailService->>AWS_SES: send_email()
    AWS_SES-->>EmailService: Success

    EmailService-->>Worker: MessageId
```

---

## Performance Optimization Patterns

### Cache-Aside Pattern

```mermaid
sequenceDiagram
    participant Service
    participant Cache
    participant Repository
    participant DB

    Service->>Cache: get(key)

    alt Cache Hit
        Cache-->>Service: data
    else Cache Miss
        Cache-->>Service: None
        Service->>Repository: fetch_from_db()
        Repository->>DB: SELECT
        DB-->>Repository: data
        Repository-->>Service: entity
        Service->>Cache: set(key, data, ttl)
        Cache-->>Service: OK
    end

    Service->>Service: process(data)
```

### Write-Through Cache

```mermaid
sequenceDiagram
    participant Service
    participant Repository
    participant DB
    participant Cache

    Service->>Repository: save(entity)
    Repository->>DB: UPDATE
    DB-->>Repository: success
    Repository->>Cache: set(key, entity)
    Cache-->>Repository: OK
    Repository->>Cache: delete(related_list_keys)
    Cache-->>Repository: OK
    Repository-->>Service: success
```

### Database Query Optimization

**Before** (N+1 Query Problem):

```python
# Fetch project
project = project_repo.get_by_id(project_id)  # 1 query

# Fetch tasks (N queries - BAD!)
for task_id in project.task_ids:
    task = task_repo.get_by_id(task_id)  # N queries
    tasks.append(task)
```

**After** (Eager Loading):

```python
# Fetch project with tasks in one query
project = project_repo.get_by_id_with_tasks(project_id)  # 1 query with JOIN
```

**SQL**:

```sql
-- Optimized query
SELECT
    p.project_id, p.name, p.created_at,
    t.task_id, t.title, t.status, t.priority
FROM projects p
LEFT JOIN tasks t ON t.project_id = p.project_id
WHERE p.project_id = ?
```

---

## Data Consistency Patterns

### Eventual Consistency (Event-Driven)

```mermaid
graph LR
    A[Task Completed] --> B[TaskCompletedEvent]
    B --> C[Update Analytics]
    B --> D[Send Notification]
    B --> E[Update Search Index]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#e8f5e9
    style E fill:#e8f5e9
```

**Characteristics**:

- Task completion happens immediately (strong consistency)
- Analytics, notifications, search updates happen asynchronously (eventual consistency)
- Acceptable delay: <5 seconds
- Retry on failure ensures eventual consistency

### Strong Consistency (Transaction)

```python
@transactional
def transfer_task(self, task_id: UUID, from_project: UUID, to_project: UUID):
    # All operations are atomic
    task = self.task_repo.get_by_id(task_id)
    task.transfer_to_project(to_project)

    self.task_repo.save(task)  # UPDATE tasks SET project_id = ?

    # Update project statistics in same transaction
    self.project_repo.decrement_task_count(from_project)
    self.project_repo.increment_task_count(to_project)

    # Commit or rollback all together
```

---

## Related Documents

- [System Architecture Overview](./diagrams/01-system-overview.md)
- [Component Interactions](./components.md)
- [Layer Responsibilities](./layers.md)
- [API Design Guidelines](./api-design.md)
- [Performance Tuning](./observability/performance.md)
- [Error Handling Patterns](./error-handling.md)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
