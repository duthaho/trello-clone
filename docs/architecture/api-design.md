# API Design Guidelines

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines the API design principles, standards, and conventions for the Task Management System. All APIs follow RESTful principles with OpenAPI 3.0 documentation.

---

## API Philosophy

### Core Principles

1. **RESTful Design**: Resources are nouns, HTTP methods express actions
2. **Consistency**: Predictable patterns across all endpoints
3. **Versioning**: URI-based versioning for stability
4. **Security-First**: Authentication required by default
5. **Developer Experience**: Clear documentation, meaningful errors
6. **Performance**: Pagination, filtering, field selection

---

## Base URL Structure

```
https://api.taskmanager.com/api/v1/{resource}
```

**Components**:

- **Protocol**: HTTPS only (enforced by ALB)
- **Host**: `api.taskmanager.com`
- **Prefix**: `/api` (distinguishes API from web routes)
- **Version**: `/v1` (current version)
- **Resource**: Resource path (e.g., `/tasks`, `/projects`)

**Examples**:

```
https://api.taskmanager.com/api/v1/tasks
https://api.taskmanager.com/api/v1/projects/123/members
https://api.taskmanager.com/api/v1/users/me
```

---

## Versioning Strategy

### URI Versioning

**Pattern**: `/api/{version}/{resource}`

**Rationale**:

- ✅ Simple and explicit
- ✅ Cache-friendly (different URLs for different versions)
- ✅ Easy to test and debug
- ✅ Clear deprecation path

**Version Lifecycle**:

```mermaid
stateDiagram-v2
    [*] --> Active: Release v1
    Active --> Deprecated: Release v2
    Deprecated --> Sunset: +12 months
    Sunset --> [*]: +6 months

    note right of Active
        Fully supported
        New features added
    end note

    note right of Deprecated
        Maintained (bug fixes only)
        No new features
        Deprecation warnings in responses
    end note

    note right of Sunset
        Migration deadline announced
        Returns 410 Gone
    end note
```

**Deprecation Headers**:

```http
HTTP/1.1 200 OK
Sunset: Sat, 31 Dec 2026 23:59:59 GMT
Deprecation: true
Link: </api/v2/tasks>; rel="successor-version"
Warning: 299 - "API version v1 is deprecated. Migrate to v2 by 2026-12-31"
```

**Version Support Policy**:

- **Current version** (v1): Full support, new features
- **Previous version** (v0): Deprecated, 12-month support window
- **Older versions**: Sunset, return 410 Gone

---

## Resource Naming

### Conventions

1. **Use Nouns**: Resources are things, not actions
2. **Plural Names**: Collections use plural nouns
3. **Lowercase**: All lowercase with hyphens for readability
4. **Hierarchical**: Show relationships via nesting

**Examples**:

| ✅ Good                | ❌ Bad                   | Reason                    |
| ---------------------- | ------------------------ | ------------------------- |
| `/tasks`               | `/getTasks`              | Noun not verb             |
| `/users`               | `/user`                  | Plural for collections    |
| `/project-members`     | `/ProjectMembers`        | Lowercase with hyphens    |
| `/projects/{id}/tasks` | `/tasks?project_id={id}` | Hierarchical relationship |

### Resource Hierarchy

```
/api/v1/organizations/{org_id}
├── /projects
│   └── /{project_id}
│       ├── /tasks
│       ├── /members
│       └── /labels
├── /users/{user_id}
└── /roles
```

**Maximum Nesting**: 3 levels (for readability)

**Example**:

```
✅ /api/v1/projects/{id}/tasks/{task_id}/comments
❌ /api/v1/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/reactions
   (too deep - flatten to /api/v1/comments/{comment_id}/reactions)
```

---

## HTTP Methods

### Standard Methods

| Method     | Purpose              | Idempotent | Safe | Request Body | Response Body |
| ---------- | -------------------- | ---------- | ---- | ------------ | ------------- |
| **GET**    | Retrieve resource(s) | Yes        | Yes  | No           | Yes           |
| **POST**   | Create resource      | No         | No   | Yes          | Yes           |
| **PUT**    | Replace resource     | Yes        | No   | Yes          | Yes           |
| **PATCH**  | Update resource      | No         | No   | Yes          | Yes           |
| **DELETE** | Delete resource      | Yes        | No   | No           | No/Minimal    |

### Usage Examples

#### GET - Retrieve

```http
GET /api/v1/tasks/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Implement user authentication",
  "status": "IN_PROGRESS",
  "priority": "HIGH",
  "created_at": "2025-10-30T10:00:00Z"
}
```

#### POST - Create

```http
POST /api/v1/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Implement user authentication",
  "description": "Add JWT-based auth",
  "project_id": "456e7890-e89b-12d3-a456-426614174001",
  "priority": "HIGH"
}
```

```json
HTTP/1.1 201 Created
Location: /api/v1/tasks/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json

{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Implement user authentication",
  "status": "TODO",
  "created_at": "2025-10-30T14:23:45Z"
}
```

#### PATCH - Partial Update

```http
PATCH /api/v1/tasks/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "IN_PROGRESS",
  "assignee_id": "789e0123-e89b-12d3-a456-426614174002"
}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Implement user authentication",
  "status": "IN_PROGRESS",
  "assignee_id": "789e0123-e89b-12d3-a456-426614174002",
  "updated_at": "2025-10-30T15:30:00Z"
}
```

#### DELETE - Remove

```http
DELETE /api/v1/tasks/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

```json
HTTP/1.1 204 No Content
```

---

## Authentication & Authorization

### Authentication

**Method**: JWT (JSON Web Tokens) with OAuth2 Bearer scheme

**Token Types**:

| Token Type        | Purpose                 | Expiry     | Refresh           | Storage               |
| ----------------- | ----------------------- | ---------- | ----------------- | --------------------- |
| **Access Token**  | API authentication      | 15 minutes | Via refresh token | Memory/sessionStorage |
| **Refresh Token** | Obtain new access token | 30 days    | Manual re-login   | httpOnly cookie       |

**Authentication Flow**:

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant AuthService

    Client->>API: POST /api/v1/auth/login
    Note over Client: {email, password}

    API->>AuthService: authenticate()
    AuthService-->>API: {access_token, refresh_token}
    API-->>Client: 200 OK

    Note over Client: Store tokens

    Client->>API: GET /api/v1/tasks
    Note over Client: Authorization: Bearer <access_token>

    API->>API: Validate JWT

    alt Token Valid
        API-->>Client: 200 OK {tasks}
    else Token Expired
        API-->>Client: 401 Unauthorized
        Client->>API: POST /api/v1/auth/refresh
        Note over Client: {refresh_token}
        API-->>Client: 200 OK {new_access_token}
        Client->>API: Retry with new token
    end
```

**Authorization Header**:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**JWT Payload**:

```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000", // user_id
  "email": "user@example.com",
  "roles": ["user", "project_admin"],
  "org_id": "456e7890-e89b-12d3-a456-426614174001",
  "iat": 1698675825, // issued at
  "exp": 1698676725 // expires at (15 min)
}
```

### Authorization

**Model**: Role-Based Access Control (RBAC) with resource ownership

**Permission Levels**:

| Role            | Organization           | Project                  | Task                   |
| --------------- | ---------------------- | ------------------------ | ---------------------- |
| **Owner**       | Full control           | Full control             | Full control           |
| **Admin**       | Manage users, projects | Manage members, settings | Create, update, delete |
| **Contributor** | View                   | Create tasks, comment    | Update own, view all   |
| **Viewer**      | View                   | View only                | View only              |

**Authorization Checks**:

```python
# In controller/middleware
@require_permission("task:write")
async def update_task(task_id: UUID, current_user: User):
    # Permission decorator ensures:
    # 1. User is authenticated
    # 2. User has "task:write" permission
    # 3. User can access this specific task
    pass

# In use case
class UpdateTaskUseCase:
    def execute(self, command: UpdateTaskCommand, user_id: UUID):
        task = self.task_repo.get_by_id(command.task_id)

        # Check resource-level permission
        if not self.authz.can_modify_task(user_id, task):
            raise InsufficientPermissionsError()

        # Proceed with update
```

---

## Request Format

### Content Types

**Supported**:

- `application/json` (primary)
- `multipart/form-data` (file uploads)

**Example**:

```http
POST /api/v1/tasks
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "Task title",
  "description": "Task description"
}
```

### Query Parameters

**Conventions**:

- Use `snake_case` for parameter names
- Support common query operations
- Validate and sanitize all inputs

**Common Parameters**:

| Parameter | Purpose                   | Example                     |
| --------- | ------------------------- | --------------------------- |
| `page`    | Pagination page number    | `?page=2`                   |
| `limit`   | Items per page            | `?limit=50`                 |
| `sort`    | Sort order                | `?sort=-created_at,title`   |
| `filter`  | Filter results            | `?filter[status]=TODO`      |
| `fields`  | Field selection           | `?fields=id,title,status`   |
| `include` | Include related resources | `?include=assignee,project` |
| `q`       | Full-text search          | `?q=authentication`         |

**Examples**:

```http
# Pagination
GET /api/v1/tasks?page=2&limit=20

# Sorting (- prefix for descending)
GET /api/v1/tasks?sort=-created_at,priority

# Filtering
GET /api/v1/tasks?filter[status]=TODO&filter[priority]=HIGH

# Field selection (sparse fieldsets)
GET /api/v1/tasks?fields=id,title,status,assignee_id

# Include related resources
GET /api/v1/tasks?include=assignee,project,comments

# Full-text search
GET /api/v1/tasks?q=authentication

# Combined
GET /api/v1/tasks?filter[status]=TODO&sort=-priority&page=1&limit=20&include=assignee
```

---

## Response Format

### Success Response

**Structure**:

```json
{
  "data": {
    /* resource or array */
  },
  "meta": {
    /* metadata */
  },
  "links": {
    /* pagination links */
  }
}
```

**Single Resource**:

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Implement user authentication",
  "status": "TODO",
  "priority": "HIGH",
  "project_id": "456e7890-e89b-12d3-a456-426614174001",
  "assignee_id": null,
  "created_at": "2025-10-30T10:00:00Z",
  "updated_at": "2025-10-30T10:00:00Z"
}
```

**Collection**:

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "data": [
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Task 1",
      "status": "TODO"
    },
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174001",
      "title": "Task 2",
      "status": "IN_PROGRESS"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 47,
    "total_pages": 3
  },
  "links": {
    "self": "/api/v1/tasks?page=1&limit=20",
    "first": "/api/v1/tasks?page=1&limit=20",
    "next": "/api/v1/tasks?page=2&limit=20",
    "last": "/api/v1/tasks?page=3&limit=20"
  }
}
```

### Error Response

**Structure**:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": [
      /* validation errors */
    ],
    "request_id": "uuid",
    "timestamp": "ISO 8601"
  }
}
```

**Examples**:

**Validation Error (422)**:

```json
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "title",
        "error": "Field required"
      },
      {
        "field": "project_id",
        "error": "Invalid UUID format"
      }
    ],
    "request_id": "req_abc123",
    "timestamp": "2025-10-30T14:23:45Z"
  }
}
```

**Authorization Error (403)**:

```json
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "You do not have permission to modify this task",
    "details": {
      "required_permission": "task:write",
      "resource_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "request_id": "req_abc124",
    "timestamp": "2025-10-30T14:25:10Z"
  }
}
```

**Not Found (404)**:

```json
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Task not found",
    "details": {
      "resource_type": "task",
      "resource_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "request_id": "req_abc125",
    "timestamp": "2025-10-30T14:26:30Z"
  }
}
```

---

## HTTP Status Codes

### Standard Status Codes

| Code                          | Meaning                   | Usage                                     |
| ----------------------------- | ------------------------- | ----------------------------------------- |
| **200 OK**                    | Success                   | GET, PATCH successful                     |
| **201 Created**               | Resource created          | POST successful                           |
| **204 No Content**            | Success, no response body | DELETE successful                         |
| **400 Bad Request**           | Malformed request         | Invalid JSON syntax                       |
| **401 Unauthorized**          | Authentication required   | Missing/invalid token                     |
| **403 Forbidden**             | Insufficient permissions  | Valid token, no permission                |
| **404 Not Found**             | Resource doesn't exist    | Invalid resource ID                       |
| **409 Conflict**              | Business rule violation   | Duplicate email, invalid state transition |
| **422 Unprocessable Entity**  | Validation error          | Invalid field values                      |
| **429 Too Many Requests**     | Rate limit exceeded       | >1000 requests/minute                     |
| **500 Internal Server Error** | Server error              | Unhandled exception                       |
| **503 Service Unavailable**   | Temporary unavailability  | Maintenance, overload                     |

### Status Code Decision Tree

```mermaid
graph TD
    A[Receive Request] --> B{Valid JSON?}
    B -->|No| C[400 Bad Request]
    B -->|Yes| D{Authenticated?}

    D -->|No| E[401 Unauthorized]
    D -->|Yes| F{Authorized?}

    F -->|No| G[403 Forbidden]
    F -->|Yes| H{Valid Schema?}

    H -->|No| I[422 Validation Error]
    H -->|Yes| J{Resource Exists?}

    J -->|No| K[404 Not Found]
    J -->|Yes| L{Business Rules OK?}

    L -->|No| M[409 Conflict]
    L -->|Yes| N{Operation Type?}

    N -->|GET| O[200 OK]
    N -->|POST| P[201 Created]
    N -->|PATCH| O
    N -->|DELETE| Q[204 No Content]
```

---

## Pagination

### Cursor-Based Pagination (Recommended)

**Best for**: Large datasets, real-time data

**Request**:

```http
GET /api/v1/tasks?cursor=eyJpZCI6MTIzfQ&limit=20
```

**Response**:

```json
{
  "data": [
    /* 20 tasks */
  ],
  "meta": {
    "limit": 20,
    "has_more": true
  },
  "links": {
    "next": "/api/v1/tasks?cursor=eyJpZCI6MTQzfQ&limit=20"
  }
}
```

**Cursor Generation**:

```python
import base64
import json

def encode_cursor(last_id: int, last_created_at: datetime) -> str:
    data = {"id": last_id, "created_at": last_created_at.isoformat()}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def decode_cursor(cursor: str) -> dict:
    data = base64.urlsafe_b64decode(cursor.encode()).decode()
    return json.loads(data)
```

### Offset-Based Pagination

**Best for**: Small datasets, random access needed

**Request**:

```http
GET /api/v1/tasks?page=2&limit=20
```

**Response**:

```json
{
  "data": [
    /* 20 tasks */
  ],
  "meta": {
    "page": 2,
    "limit": 20,
    "total": 87,
    "total_pages": 5
  },
  "links": {
    "self": "/api/v1/tasks?page=2&limit=20",
    "first": "/api/v1/tasks?page=1&limit=20",
    "prev": "/api/v1/tasks?page=1&limit=20",
    "next": "/api/v1/tasks?page=3&limit=20",
    "last": "/api/v1/tasks?page=5&limit=20"
  }
}
```

**Default Limits**:

- Default `limit`: 20
- Maximum `limit`: 100
- Requests exceeding max return 400 Bad Request

---

## Filtering & Sorting

### Filtering

**Syntax**: `?filter[field]=value`

**Operators**:

| Operator     | Syntax                        | Example                               |
| ------------ | ----------------------------- | ------------------------------------- |
| Equals       | `filter[field]=value`         | `filter[status]=TODO`                 |
| Not equals   | `filter[field][ne]=value`     | `filter[status][ne]=DONE`             |
| Greater than | `filter[field][gt]=value`     | `filter[created_at][gt]=2025-01-01`   |
| Less than    | `filter[field][lt]=value`     | `filter[priority][lt]=3`              |
| In           | `filter[field][in]=val1,val2` | `filter[status][in]=TODO,IN_PROGRESS` |
| Like         | `filter[field][like]=pattern` | `filter[title][like]=%auth%`          |

**Examples**:

```http
# Single filter
GET /api/v1/tasks?filter[status]=TODO

# Multiple filters (AND)
GET /api/v1/tasks?filter[status]=TODO&filter[priority]=HIGH

# Date range
GET /api/v1/tasks?filter[created_at][gte]=2025-01-01&filter[created_at][lt]=2025-02-01

# IN operator
GET /api/v1/tasks?filter[status][in]=TODO,IN_PROGRESS
```

### Sorting

**Syntax**: `?sort=field1,-field2`

- Prefix with `-` for descending order
- Comma-separated for multiple fields

**Examples**:

```http
# Sort by created_at descending
GET /api/v1/tasks?sort=-created_at

# Sort by priority desc, then created_at asc
GET /api/v1/tasks?sort=-priority,created_at

# Sort by status, then title
GET /api/v1/tasks?sort=status,title
```

---

## Field Selection (Sparse Fieldsets)

**Purpose**: Reduce response size by selecting only needed fields

**Syntax**: `?fields=field1,field2,field3`

**Example**:

```http
GET /api/v1/tasks?fields=id,title,status
```

**Response**:

```json
{
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Implement authentication",
      "status": "TODO"
    }
  ]
}
```

**Benefits**:

- Reduced bandwidth
- Faster response times
- Mobile-friendly

---

## Rate Limiting

### Limits

| User Type           | Requests/Minute | Requests/Hour |
| ------------------- | --------------- | ------------- |
| **Unauthenticated** | 60              | 1,000         |
| **Authenticated**   | 1,000           | 60,000        |
| **Premium**         | 5,000           | 300,000       |

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1698676800
```

### Rate Limit Exceeded

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
Content-Type: application/json

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 45 seconds.",
    "details": {
      "limit": 1000,
      "window": "1 minute",
      "retry_after": 45
    },
    "request_id": "req_abc126",
    "timestamp": "2025-10-30T14:30:00Z"
  }
}
```

---

## File Uploads

### Single File Upload

```http
POST /api/v1/attachments
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Authorization: Bearer <token>

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="document.pdf"
Content-Type: application/pdf

[binary data]
------WebKitFormBoundary
Content-Disposition: form-data; name="task_id"

123e4567-e89b-12d3-a456-426614174000
------WebKitFormBoundary--
```

**Response**:

```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "attachment_id": "789e0123-e89b-12d3-a456-426614174002",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "url": "https://cdn.taskmanager.com/attachments/789e0123...",
  "created_at": "2025-10-30T15:00:00Z"
}
```

### File Constraints

| Constraint             | Limit                     |
| ---------------------- | ------------------------- |
| **Max file size**      | 10 MB                     |
| **Allowed types**      | PDF, PNG, JPG, DOCX, XLSX |
| **Max files per task** | 20                        |

---

## HATEOAS (Hypermedia)

### Embedding Links

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Implement authentication",
  "status": "TODO",
  "_links": {
    "self": {
      "href": "/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000"
    },
    "project": {
      "href": "/api/v1/projects/456e7890-e89b-12d3-a456-426614174001"
    },
    "comments": {
      "href": "/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000/comments"
    },
    "assign": {
      "href": "/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000/assign",
      "method": "PATCH"
    }
  }
}
```

---

## API Documentation

### OpenAPI 3.0 Specification

**Access**: `GET /api/docs` (Swagger UI)

**Specification**: `GET /api/openapi.json`

**Example**:

```yaml
openapi: 3.0.0
info:
  title: Task Management API
  version: 1.0.0
  description: RESTful API for task management system
  contact:
    email: api@taskmanager.com

servers:
  - url: https://api.taskmanager.com/api/v1
    description: Production
  - url: https://staging-api.taskmanager.com/api/v1
    description: Staging

paths:
  /tasks:
    get:
      summary: List tasks
      operationId: listTasks
      tags: [Tasks]
      security:
        - bearerAuth: []
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
      responses:
        "200":
          description: Successful response
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/TaskList"
```

---

## API Endpoint Inventory

### Authentication

| Method | Endpoint                       | Description               |
| ------ | ------------------------------ | ------------------------- |
| POST   | `/api/v1/auth/login`           | User login                |
| POST   | `/api/v1/auth/logout`          | User logout               |
| POST   | `/api/v1/auth/refresh`         | Refresh access token      |
| POST   | `/api/v1/auth/register`        | User registration         |
| POST   | `/api/v1/auth/forgot-password` | Request password reset    |
| POST   | `/api/v1/auth/reset-password`  | Reset password with token |

### Users

| Method | Endpoint             | Description         |
| ------ | -------------------- | ------------------- |
| GET    | `/api/v1/users/me`   | Get current user    |
| PATCH  | `/api/v1/users/me`   | Update current user |
| GET    | `/api/v1/users/{id}` | Get user by ID      |
| GET    | `/api/v1/users`      | List users (admin)  |

### Projects

| Method | Endpoint                                  | Description          |
| ------ | ----------------------------------------- | -------------------- |
| GET    | `/api/v1/projects`                        | List projects        |
| POST   | `/api/v1/projects`                        | Create project       |
| GET    | `/api/v1/projects/{id}`                   | Get project          |
| PATCH  | `/api/v1/projects/{id}`                   | Update project       |
| DELETE | `/api/v1/projects/{id}`                   | Delete project       |
| GET    | `/api/v1/projects/{id}/members`           | List project members |
| POST   | `/api/v1/projects/{id}/members`           | Add member           |
| DELETE | `/api/v1/projects/{id}/members/{user_id}` | Remove member        |

### Tasks

| Method | Endpoint                      | Description   |
| ------ | ----------------------------- | ------------- |
| GET    | `/api/v1/tasks`               | List tasks    |
| POST   | `/api/v1/tasks`               | Create task   |
| GET    | `/api/v1/tasks/{id}`          | Get task      |
| PATCH  | `/api/v1/tasks/{id}`          | Update task   |
| DELETE | `/api/v1/tasks/{id}`          | Delete task   |
| PATCH  | `/api/v1/tasks/{id}/assign`   | Assign task   |
| PATCH  | `/api/v1/tasks/{id}/status`   | Update status |
| GET    | `/api/v1/tasks/{id}/comments` | List comments |
| POST   | `/api/v1/tasks/{id}/comments` | Add comment   |

### Notifications

| Method | Endpoint                            | Description        |
| ------ | ----------------------------------- | ------------------ |
| GET    | `/api/v1/notifications`             | List notifications |
| PATCH  | `/api/v1/notifications/{id}/read`   | Mark as read       |
| PATCH  | `/api/v1/notifications/read-all`    | Mark all as read   |
| GET    | `/api/v1/notifications/preferences` | Get preferences    |
| PATCH  | `/api/v1/notifications/preferences` | Update preferences |

---

## Related Documents

- [Data Flows](./data-flows.md)
- [Authentication Architecture](./security/authentication.md)
- [Error Handling Patterns](./error-handling.md)
- [OpenAPI Specification](./openapi.yaml)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
