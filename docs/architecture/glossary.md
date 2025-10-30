# Architecture Glossary

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This glossary defines key architectural and Domain-Driven Design terms used throughout the Task Management System documentation. Terms are organized alphabetically with examples and references.

---

## A

### Aggregate

**Definition**: A cluster of domain objects (entities and value objects) treated as a single unit for data changes. One entity is the aggregate root, and all external access goes through it.

**Purpose**: Enforce invariants and consistency boundaries

**Example**:

```python
class Task:  # Aggregate Root
    task_id: UUID
    comments: List[Comment]  # Aggregate members

    def add_comment(self, text: str, author_id: UUID) -> None:
        # Aggregate enforces business rules
        if self.status == TaskStatus.DELETED:
            raise InvalidStateError("Cannot add comment to deleted task")

        comment = Comment.create(text, author_id)
        self.comments.append(comment)
```

**References**: [bounded-contexts.md](./bounded-contexts.md), [DDD Aggregates](https://martinfowler.com/bliki/DDD_Aggregate.html)

---

### Anti-Corruption Layer (ACL)

**Definition**: A translation layer that prevents external system concepts from polluting the domain model.

**Purpose**: Protect domain from external dependencies and legacy systems

**Example**:

```python
class LegacyUserAdapter:
    """Translates legacy user API to domain User entity"""

    def get_user(self, legacy_id: int) -> User:
        # Fetch from legacy API
        legacy_data = self.legacy_api.get_user(legacy_id)

        # Translate to domain model
        return User(
            user_id=UUID(legacy_data["uuid"]),
            email=Email(legacy_data["email_address"]),
            name=legacy_data["full_name"]
        )
```

**References**: [ADR-003](./decisions/adr-003-bounded-contexts.md#integration-patterns)

---

### Application Layer

**Definition**: The second layer from the outside in Clean Architecture. Orchestrates use cases and coordinates domain entities without containing business logic.

**Responsibilities**:

- Execute use cases (commands and queries)
- Coordinate domain entities
- Manage transactions
- Publish domain events
- Convert between DTOs and domain entities

**Example**:

```python
class CreateTaskUseCase:
    def execute(self, command: CreateTaskCommand) -> Task:
        # Orchestration only, no business logic
        project = self.project_repo.get_by_id(command.project_id)

        task = Task.create(  # Domain logic in entity
            title=command.title,
            project_id=command.project_id
        )

        self.task_repo.save(task)
        self.event_bus.publish_all(task.domain_events)

        return task
```

**References**: [layers.md](./layers.md#application-layer)

---

## B

### Bounded Context

**Definition**: An explicit boundary within which a domain model is defined and applicable. A linguistic boundary where terms have specific meanings.

**Purpose**: Manage complexity, enable team autonomy, support future microservices

**Example**: Our system has 5 bounded contexts:

1. **User Management**: Authentication, users, organizations
2. **Project Management**: Projects, membership, labels
3. **Task Management**: Tasks, comments, workflow
4. **Notification**: Multi-channel notifications
5. **Audit**: Security and compliance logs

**Key Principle**: Same term can have different meanings in different contexts (e.g., "User" in User Management vs Task Management)

**References**: [bounded-contexts.md](./bounded-contexts.md), [ADR-003](./decisions/adr-003-bounded-contexts.md)

---

## C

### Clean Architecture

**Definition**: An architectural pattern emphasizing separation of concerns through concentric layers with dependencies pointing inward.

**Core Principle**: **Dependency Rule** - Dependencies point INWARD. Outer layers depend on inner layers, never the reverse.

**Layers** (outside-in):

1. **Interface Layer**: API controllers, CLI, UI
2. **Infrastructure Layer**: Database, external services, frameworks
3. **Application Layer**: Use cases, application services
4. **Domain Layer**: Business entities, rules, events (pure)

**Benefits**:

- ✅ Independent of frameworks
- ✅ Testable (inner layers without outer)
- ✅ Independent of UI
- ✅ Independent of database
- ✅ Independent of external agencies

**References**: [layers.md](./layers.md), [ADR-001](./decisions/adr-001-clean-architecture.md)

---

### Command

**Definition**: An object representing an intent to change system state. Part of the CQRS pattern.

**Characteristics**:

- Imperative naming (CreateTask, UpdateUser)
- Contains all parameters for operation
- Returns void or result DTO
- May fail with business rule violations

**Example**:

```python
@dataclass(frozen=True)
class CreateTaskCommand:
    title: str
    description: str
    project_id: UUID
    created_by: UUID
    assignee_id: Optional[UUID] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
```

**Contrast with Query**: Commands change state, queries don't

**References**: [layers.md](./layers.md#commands-vs-queries)

---

### CQRS (Command Query Responsibility Segregation)

**Definition**: Pattern separating read operations (queries) from write operations (commands).

**Benefits**:

- Optimized read and write models
- Scalability (separate read/write databases)
- Simplified queries (no complex joins)

**Example**:

```python
# Command Side (write)
class CreateTaskUseCase:
    def execute(self, command: CreateTaskCommand) -> UUID:
        task = Task.create(...)
        self.task_repo.save(task)
        return task.task_id

# Query Side (read)
class GetTaskByIdQuery:
    def execute(self, task_id: UUID) -> TaskDTO:
        # Read from optimized query model
        return self.task_query_service.get_by_id(task_id)
```

**References**: [layers.md](./layers.md#application-layer)

---

## D

### Domain Event

**Definition**: An event representing something significant that happened in the domain. Past-tense naming indicates completed action.

**Purpose**: Decouple bounded contexts, enable event-driven architecture, audit trail

**Example**:

```python
@dataclass(frozen=True)
class TaskAssignedEvent:
    event_id: UUID
    task_id: UUID
    assignee_id: UUID
    assigned_by: UUID
    occurred_at: datetime

    def __post_init__(self):
        object.__setattr__(self, 'event_id', uuid4())
        object.__setattr__(self, 'occurred_at', datetime.now(UTC))
```

**Publishing**:

```python
class Task:
    def assign_to(self, user_id: UUID) -> None:
        self.assignee_id = user_id
        self.record_event(TaskAssignedEvent(
            task_id=self.task_id,
            assignee_id=user_id
        ))
```

**References**: [bounded-contexts.md](./bounded-contexts.md#domain-events)

---

### Domain Layer

**Definition**: The innermost layer in Clean Architecture containing core business logic. Has ZERO external dependencies.

**Characteristics**:

- Pure Python (no framework imports)
- Business rules and invariants
- Entities, value objects, domain events
- Repository interfaces (not implementations)

**Example**:

```python
# domain/tasks/entities.py - NO imports from FastAPI, SQLAlchemy, etc.
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

class Task:
    """Pure domain entity with business logic"""

    def complete(self) -> None:
        if self.status == TaskStatus.DELETED:
            raise InvalidStateError("Cannot complete deleted task")

        if self.has_pending_subtasks():
            raise BusinessRuleViolation("Complete subtasks first")

        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.record_event(TaskCompletedEvent(self.task_id))
```

**References**: [layers.md](./layers.md#domain-layer), [ADR-001](./decisions/adr-001-clean-architecture.md)

---

### DTO (Data Transfer Object)

**Definition**: An object carrying data between layers or processes without business logic.

**Purpose**: Decouple layers, control data exposure, optimize network transfer

**Example**:

```python
# Application Layer DTO
@dataclass(frozen=True)
class TaskDTO:
    task_id: UUID
    title: str
    status: str
    priority: str
    created_at: datetime

# Interface Layer (API) Schema
class TaskResponse(BaseModel):
    """Pydantic schema for API responses"""
    task_id: UUID
    title: str
    status: str
    priority: str
    created_at: datetime

    class Config:
        orm_mode = True
```

**References**: [layers.md](./layers.md#application-layer)

---

## E

### Entity

**Definition**: An object with a unique identity that persists over time, even if its attributes change.

**Key Characteristic**: Defined by **identity**, not attributes

**Example**:

```python
class User:
    """Entity with unique identity (user_id)"""

    user_id: UUID  # Identity
    email: Email
    name: str

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, User):
            return False
        return self.user_id == other.user_id  # Compare by identity

    def __hash__(self) -> int:
        return hash(self.user_id)
```

**Contrast with Value Object**:

- **Entity**: Defined by identity (User, Task, Project)
- **Value Object**: Defined by attributes (Email, Money, Address)

**References**: [bounded-contexts.md](./bounded-contexts.md#domain-entities)

---

### Event Sourcing

**Definition**: Storing state changes as a sequence of events rather than current state.

**Benefits**:

- Complete audit trail
- Time travel (replay events)
- Event-driven architecture

**Example**:

```python
class TaskEventStore:
    def append(self, event: DomainEvent) -> None:
        # Store event in database
        self.db.execute("""
            INSERT INTO event_store (
                event_id, aggregate_id, event_type,
                event_data, occurred_at
            ) VALUES (?, ?, ?, ?, ?)
        """, event.event_id, event.aggregate_id, ...)

    def get_events(self, aggregate_id: UUID) -> List[DomainEvent]:
        # Retrieve all events for aggregate
        rows = self.db.query("SELECT * FROM event_store WHERE aggregate_id = ?")
        return [self.deserialize(row) for row in rows]

    def rebuild(self, aggregate_id: UUID) -> Task:
        # Rebuild state from events
        events = self.get_events(aggregate_id)
        task = Task()
        for event in events:
            task.apply(event)
        return task
```

**Note**: Not fully implemented in our system, but event store exists for audit trail

**References**: [data-flows.md](./data-flows.md#event-driven)

---

## H

### HATEOAS (Hypermedia as the Engine of Application State)

**Definition**: REST principle where API responses include links to related resources and available actions.

**Purpose**: Make APIs self-documenting and discoverable

**Example**:

```json
{
  "task_id": "123e4567-...",
  "title": "Implement authentication",
  "status": "TODO",
  "_links": {
    "self": { "href": "/api/v1/tasks/123e4567-..." },
    "project": { "href": "/api/v1/projects/456e7890-..." },
    "assign": {
      "href": "/api/v1/tasks/123e4567-.../assign",
      "method": "PATCH"
    },
    "complete": {
      "href": "/api/v1/tasks/123e4567-.../complete",
      "method": "PATCH"
    }
  }
}
```

**References**: [api-design.md](./api-design.md#hateoas-hypermedia)

---

## I

### Idempotent

**Definition**: An operation that produces the same result regardless of how many times it's executed.

**HTTP Methods**:

- **Idempotent**: GET, PUT, DELETE (safe to retry)
- **Not Idempotent**: POST, PATCH (may create duplicates)

**Example**:

```python
# PUT is idempotent (replaces resource)
PUT /api/v1/tasks/123
{
  "title": "Updated title",
  "status": "IN_PROGRESS"
}
# Same result whether called once or multiple times

# POST is NOT idempotent (creates new resource)
POST /api/v1/tasks
{
  "title": "New task"
}
# Creates a new task each time
```

**Implementation**:

```python
@router.put("/tasks/{task_id}")
async def update_task(task_id: UUID, request: UpdateTaskRequest):
    # Idempotent: always replaces with same data
    task = await task_repo.get_by_id(task_id)
    task.update(request.title, request.status)
    await task_repo.save(task)
    return task
```

**References**: [api-design.md](./api-design.md#http-methods)

---

### Infrastructure Layer

**Definition**: The outermost layer in Clean Architecture responsible for external concerns (databases, APIs, frameworks).

**Responsibilities**:

- Implement repository interfaces
- Database access (SQLAlchemy)
- External API integration
- Message queues (Celery, Redis)
- Logging, metrics, tracing

**Example**:

```python
# infrastructure/persistence/repositories/task_repository.py
class SqlAlchemyTaskRepository(TaskRepository):  # Implements domain interface
    def __init__(self, session: Session, cache: RedisCache):
        self._session = session
        self._cache = cache

    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        # Try cache first
        cached = self._cache.get(f"task:{task_id}")
        if cached:
            return self._deserialize(cached)

        # Query database
        model = self._session.query(TaskModel).filter_by(task_id=task_id).first()
        if not model:
            return None

        # Map ORM model to domain entity
        task = self._mapper.to_entity(model)

        # Cache result
        self._cache.set(f"task:{task_id}", self._serialize(task), ttl=60)

        return task
```

**References**: [layers.md](./layers.md#infrastructure-layer)

---

### Interface Layer

**Definition**: The outermost layer in Clean Architecture handling external communication (HTTP, CLI, gRPC).

**Responsibilities**:

- Handle HTTP requests/responses
- Validate input (Pydantic schemas)
- Authentication/authorization
- Serialize/deserialize data
- Error handling and formatting

**Example**:

```python
# interface/api/v1/tasks/router.py
@router.post("/tasks", status_code=201)
async def create_task(
    request: CreateTaskRequest,  # Pydantic schema
    current_user: User = Depends(get_current_user),
    use_case: CreateTaskUseCase = Depends(get_create_task_use_case)
) -> TaskResponse:
    # Validate and convert to command
    command = CreateTaskCommand(
        title=request.title,
        project_id=request.project_id,
        created_by=current_user.user_id
    )

    # Execute use case
    task = await use_case.execute(command)

    # Convert to response DTO
    return TaskResponse.from_entity(task)
```

**References**: [layers.md](./layers.md#interface-layer)

---

### Invariant

**Definition**: A business rule or condition that must always be true for a domain object.

**Purpose**: Enforce data consistency and business logic

**Example**:

```python
class Task:
    def assign_to(self, user_id: UUID) -> None:
        # Invariant: Cannot assign deleted task
        if self.status == TaskStatus.DELETED:
            raise InvalidStateError("Cannot assign deleted task")

        # Invariant: Assignee must be project member
        if not self.project.has_member(user_id):
            raise BusinessRuleViolation("User must be project member")

        self.assignee_id = user_id
```

**References**: [bounded-contexts.md](./bounded-contexts.md)

---

## L

### Layered Architecture

**Definition**: Architectural pattern organizing code into horizontal layers with dependencies flowing downward.

**Our Layers** (Clean Architecture):

```
Interface Layer ↓
Infrastructure Layer ↓
Application Layer ↓
Domain Layer (no dependencies)
```

**Contrast with N-Tier**: Clean Architecture inverts dependencies using interfaces

**References**: [layers.md](./layers.md), [ADR-001](./decisions/adr-001-clean-architecture.md)

---

## M

### Microservices

**Definition**: Architectural style structuring an application as a collection of loosely coupled services.

**Our Approach**: Currently a modular monolith with bounded contexts designed for future microservices migration.

**Migration Path**:

```
Phase 1: Modular Monolith (Current)
  ↓
Phase 2: Extract Notification Service
  ↓
Phase 3: Extract Audit Service
  ↓
Phase 4: Extract remaining contexts as needed
```

**References**: [ADR-003](./decisions/adr-003-bounded-contexts.md#future-microservices-evolution)

---

## O

### ORM (Object-Relational Mapping)

**Definition**: Technique for converting data between incompatible type systems (object-oriented and relational databases).

**Our Tool**: SQLAlchemy 2.0+

**Example**:

```python
# ORM Model (Infrastructure Layer)
class TaskModel(Base):
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String(200), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))

    project = relationship("ProjectModel", back_populates="tasks")
```

**Mapping to Domain Entity**:

```python
class TaskMapper:
    def to_entity(self, model: TaskModel) -> Task:
        return Task(
            task_id=model.task_id,
            title=model.title,
            status=TaskStatus(model.status),
            project_id=model.project_id
        )

    def to_model(self, entity: Task) -> TaskModel:
        return TaskModel(
            task_id=entity.task_id,
            title=entity.title,
            status=entity.status.value
        )
```

**References**: [layers.md](./layers.md#infrastructure-layer)

---

## P

### Persistence Ignorance

**Definition**: Domain objects should not know how they're persisted (no database-specific code).

**Purpose**: Keep domain pure, enable testing without database

**Example**:

```python
# ✅ Good: Domain entity has no persistence logic
class Task:
    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

# ❌ Bad: Domain entity knows about database
class Task:
    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.session.commit()  # Persistence leak!
```

**References**: [layers.md](./layers.md#domain-layer)

---

## Q

### Query

**Definition**: An object representing an intent to read data without changing system state.

**Characteristics**:

- Interrogative naming (GetTaskById, ListProjects)
- Read-only operation
- Returns data (DTO)
- Never fails (returns empty/null if not found)

**Example**:

```python
@dataclass(frozen=True)
class GetTaskByIdQuery:
    task_id: UUID

class GetTaskByIdQueryHandler:
    def execute(self, query: GetTaskByIdQuery) -> Optional[TaskDTO]:
        # Read-only operation
        task = self.task_repo.get_by_id(query.task_id)
        return TaskDTO.from_entity(task) if task else None
```

**Contrast with Command**: Queries read state, commands change state

**References**: [layers.md](./layers.md#commands-vs-queries)

---

## R

### Repository

**Definition**: A collection-like interface for accessing domain entities, abstracting persistence details.

**Purpose**: Decouple domain from database, enable testing with in-memory implementations

**Pattern**:

```python
# Domain Layer: Repository Interface
class TaskRepository(ABC):
    @abstractmethod
    def get_by_id(self, task_id: UUID) -> Optional[Task]: ...

    @abstractmethod
    def save(self, task: Task) -> None: ...

    @abstractmethod
    def list_by_project(self, project_id: UUID) -> List[Task]: ...

# Infrastructure Layer: Implementation
class SqlAlchemyTaskRepository(TaskRepository):
    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        model = self._session.query(TaskModel).filter_by(task_id=task_id).first()
        return self._mapper.to_entity(model) if model else None
```

**Benefits**:

- ✅ Domain doesn't depend on database
- ✅ Easy to test with in-memory implementation
- ✅ Can swap databases without changing domain

**References**: [layers.md](./layers.md#repository-pattern)

---

### REST (Representational State Transfer)

**Definition**: Architectural style for designing networked applications using HTTP methods and resources.

**Principles**:

- **Client-Server**: Separation of concerns
- **Stateless**: Each request contains all needed information
- **Cacheable**: Responses can be cached
- **Uniform Interface**: Standardized communication
- **Layered System**: Hierarchical layers
- **Code on Demand** (optional): Server can send executable code

**Our Implementation**:

```
GET    /api/v1/tasks       - List tasks
POST   /api/v1/tasks       - Create task
GET    /api/v1/tasks/{id}  - Get task
PATCH  /api/v1/tasks/{id}  - Update task
DELETE /api/v1/tasks/{id}  - Delete task
```

**References**: [api-design.md](./api-design.md)

---

## S

### Service (Application Service)

**Definition**: A stateless object in the application layer that coordinates use cases.

**Purpose**: Orchestrate domain entities and repositories without containing business logic

**Example**:

```python
class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        event_bus: EventBus
    ):
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._event_bus = event_bus

    def create_task(self, command: CreateTaskCommand) -> Task:
        # Orchestration only, no business logic
        project = self._project_repo.get_by_id(command.project_id)

        task = Task.create(  # Business logic in entity
            title=command.title,
            project_id=command.project_id
        )

        self._task_repo.save(task)
        self._event_bus.publish_all(task.domain_events)

        return task
```

**Contrast with Domain Service**: Application services orchestrate, domain services implement business logic

**References**: [layers.md](./layers.md#application-layer)

---

### SOLID Principles

**Definition**: Five principles of object-oriented design for maintainable software.

**Principles**:

| Principle                 | Description                                 | Example                                        |
| ------------------------- | ------------------------------------------- | ---------------------------------------------- |
| **S**ingle Responsibility | One class, one reason to change             | `TaskRepository` only handles persistence      |
| **O**pen/Closed           | Open for extension, closed for modification | Use strategy pattern for notification channels |
| **L**iskov Substitution   | Subtypes must be substitutable              | Any `TaskRepository` implementation works      |
| **I**nterface Segregation | Many specific interfaces > one general      | `UserReader` + `UserWriter` vs one interface   |
| **D**ependency Inversion  | Depend on abstractions                      | Use cases depend on repository interfaces      |

**References**: [quickstart.md](./quickstart.md#design-principles)

---

## T

### TDD (Test-Driven Development)

**Definition**: Development approach where tests are written before production code.

**Workflow**:

```
🔴 RED → 🟢 GREEN → 🔵 REFACTOR
```

1. **RED**: Write failing test
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Improve code while keeping tests green

**Example**:

```python
# 1. RED: Write failing test
def test_complete_task_sets_status_and_timestamp():
    task = Task.create("Test task", project_id=uuid4())

    task.complete()

    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None

# 2. GREEN: Write minimal code
class Task:
    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

# 3. REFACTOR: Add business rule validation
class Task:
    def complete(self) -> None:
        if self.status == TaskStatus.DELETED:
            raise InvalidStateError("Cannot complete deleted task")

        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.record_event(TaskCompletedEvent(self.task_id))
```

**Benefits**:

- ✅ Tests document behavior
- ✅ High code coverage
- ✅ Design emerges from tests
- ✅ Confidence in refactoring

**References**: [.github/instructions/unit-and-integration-tests.instructions.md](../../.github/instructions/unit-and-integration-tests.instructions.md)

---

## U

### Ubiquitous Language

**Definition**: A common, rigorous language shared by developers and domain experts within a bounded context.

**Purpose**: Reduce translation errors, improve communication, align code with business

**Example** (Task Management Context):

| Term           | Meaning                                         | Usage                 |
| -------------- | ----------------------------------------------- | --------------------- |
| **Task**       | A unit of work in a project                     | "Create a new task"   |
| **Status**     | Current state of task (TODO, IN_PROGRESS, DONE) | "Update task status"  |
| **Assignment** | Linking a user to a task                        | "Assign task to user" |
| **Priority**   | Importance level (LOW, MEDIUM, HIGH, CRITICAL)  | "Set task priority"   |

**In Code**:

```python
# ✅ Good: Uses ubiquitous language
task.assign_to(user)
task.set_priority(TaskPriority.HIGH)

# ❌ Bad: Technical jargon
task.set_assignee_id(user.id)
task.update_priority_value(3)
```

**References**: [bounded-contexts.md](./bounded-contexts.md#ubiquitous-language)

---

### Use Case

**Definition**: A specific application task or business workflow. Represents one way the system is used.

**Characteristics**:

- Single responsibility
- Orchestrates domain entities
- Transaction boundary
- Returns result or throws exception

**Example**:

```python
class CreateTaskUseCase:
    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        authz: AuthorizationService,
        event_bus: EventBus
    ):
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._authz = authz
        self._event_bus = event_bus

    @transactional
    def execute(self, command: CreateTaskCommand) -> Task:
        # 1. Validate permissions
        if not self._authz.can_create_task(command.user_id, command.project_id):
            raise InsufficientPermissionsError()

        # 2. Validate project exists
        project = self._project_repo.get_by_id(command.project_id)
        if not project:
            raise ProjectNotFoundError()

        # 3. Create domain entity
        task = Task.create(
            title=command.title,
            project_id=command.project_id,
            created_by=command.user_id
        )

        # 4. Persist
        self._task_repo.save(task)

        # 5. Publish events
        self._event_bus.publish_all(task.domain_events)

        return task
```

**References**: [layers.md](./layers.md#application-layer)

---

## V

### Value Object

**Definition**: An immutable object defined by its attributes rather than identity. Two value objects with same attributes are considered equal.

**Key Characteristics**:

- **Immutable**: Cannot change after creation
- **No Identity**: Defined by attributes
- **Self-Validating**: Ensures validity in constructor

**Example**:

```python
@dataclass(frozen=True)
class Email:
    """Value object for email addresses"""
    value: str

    def __post_init__(self):
        if not self._is_valid(self.value):
            raise ValueError(f"Invalid email: {self.value}")

    @staticmethod
    def _is_valid(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Email):
            return False
        return self.value == other.value  # Compare by value, not identity
```

**Usage**:

```python
email1 = Email("user@example.com")
email2 = Email("user@example.com")

email1 == email2  # True - same value
email1 is email2  # False - different objects

# Immutable - this raises FrozenInstanceError
email1.value = "new@example.com"  # Error!
```

**Contrast with Entity**:

- **Value Object**: Defined by attributes (Email, Money, Address)
- **Entity**: Defined by identity (User, Task, Project)

**References**: [layers.md](./layers.md#value-objects)

---

## Related Documents

- [System Architecture Overview](./diagrams/01-system-overview.md)
- [Layer Responsibilities](./layers.md)
- [Bounded Contexts](./bounded-contexts.md)
- [API Design Guidelines](./api-design.md)
- [Quickstart Guide](./quickstart.md)
- [Architecture Decision Records](./decisions/)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
