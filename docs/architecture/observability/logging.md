# Logging Architecture

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines the comprehensive logging architecture for the Task Management System, covering structured logging, log levels, context propagation, log aggregation, and retention policies. The logging system provides visibility into application behavior, aids debugging, supports security auditing, and enables operational insights.

---

## Logging Principles

### 1. Structured Logging

**All logs MUST be in JSON format** for machine readability and queryability.

```json
{
  "timestamp": "2025-10-30T14:23:45.123Z",
  "level": "INFO",
  "service": "api",
  "message": "Task created successfully",
  "context": {
    "request_id": "req_8f4e2b1c",
    "user_id": "usr_a1b2c3d4",
    "organization_id": "org_12345",
    "task_id": "tsk_9876543",
    "project_id": "prj_abcdef"
  },
  "metadata": {
    "duration_ms": 45,
    "method": "POST",
    "path": "/api/v1/tasks",
    "status_code": 201
  }
}
```

### 2. Context Propagation

**Every log entry MUST include**:

- `request_id`: Unique identifier for request tracing
- `user_id`: Actor performing the action (if authenticated)
- `organization_id`: Tenant/organization scope

### 3. Log Levels

Use appropriate log levels based on severity:

| Level        | When to Use                 | Examples                                |
| ------------ | --------------------------- | --------------------------------------- |
| **DEBUG**    | Development/troubleshooting | Variable values, execution flow         |
| **INFO**     | Normal operations           | Request received, task completed        |
| **WARNING**  | Recoverable issues          | Deprecated API used, retry attempt      |
| **ERROR**    | Error requiring attention   | Failed database query, validation error |
| **CRITICAL** | System failure              | Database down, service crash            |

### 4. No Sensitive Data

**NEVER log**:

- Passwords or password hashes
- JWT tokens or API keys
- Credit card numbers
- Social Security Numbers
- Full email addresses (mask: `user@example.com` → `u***@example.com`)

---

## Logging Implementation

### Python Logging Configuration

```python
import logging
import logging.config
import json
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar

# Context variables for request-scoped data
request_id_ctx: ContextVar[str] = ContextVar('request_id', default=None)
user_id_ctx: ContextVar[str] = ContextVar('user_id', default=None)
organization_id_ctx: ContextVar[str] = ContextVar('organization_id', default=None)

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "taskmanager-api",  # Set via environment variable
            "logger": record.name,
            "message": record.getMessage(),
            "context": {
                "request_id": request_id_ctx.get(),
                "user_id": user_id_ctx.get(),
                "organization_id": organization_id_ctx.get(),
            },
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields from record
        if hasattr(record, 'metadata'):
            log_data["metadata"] = record.metadata

        # Add file/line info for ERROR and above
        if record.levelno >= logging.ERROR:
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }

        return json.dumps(log_data)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "infrastructure.logging.StructuredFormatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    },
    "loggers": {
        # Application loggers
        "domain": {"level": "INFO"},
        "application": {"level": "INFO"},
        "infrastructure": {"level": "INFO"},
        "interface": {"level": "INFO"},

        # Third-party loggers (reduce verbosity)
        "uvicorn": {"level": "WARNING"},
        "sqlalchemy.engine": {"level": "WARNING"},
        "boto3": {"level": "WARNING"},
        "botocore": {"level": "WARNING"},
    }
}

def configure_logging():
    """Initialize logging configuration"""
    logging.config.dictConfig(LOGGING_CONFIG)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name

    Usage:
        logger = get_logger(__name__)
        logger.info("Task created", extra={"metadata": {"task_id": task_id}})
    """
    return logging.getLogger(name)
```

### Context Propagation Middleware

```python
from fastapi import Request
import uuid

@app.middleware("http")
async def logging_context_middleware(request: Request, call_next):
    """
    Set logging context from request headers
    Context is propagated to all log entries during this request
    """
    # Extract or generate request ID
    request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
    request_id_ctx.set(request_id)

    # Set user context (from authenticated user)
    if hasattr(request.state, 'user'):
        user = request.state.user
        user_id_ctx.set(str(user.user_id))
        organization_id_ctx.set(str(user.organization_id))

    # Add request ID to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response
```

### Logger Usage Examples

```python
from infrastructure.logging import get_logger

logger = get_logger(__name__)

# INFO: Normal operation
logger.info(
    "Task created successfully",
    extra={
        "metadata": {
            "task_id": str(task.task_id),
            "project_id": str(task.project_id),
            "assignee_id": str(task.assignee_id),
            "priority": task.priority,
            "duration_ms": 45
        }
    }
)

# WARNING: Recoverable issue
logger.warning(
    "Task assignment failed, retrying",
    extra={
        "metadata": {
            "task_id": str(task.task_id),
            "attempt": 2,
            "max_attempts": 3,
            "error": str(error)
        }
    }
)

# ERROR: Error requiring attention
try:
    result = await task_repository.save(task)
except DatabaseError as e:
    logger.error(
        "Failed to save task to database",
        extra={
            "metadata": {
                "task_id": str(task.task_id),
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        },
        exc_info=True  # Include full stack trace
    )
    raise

# DEBUG: Troubleshooting (only in development)
logger.debug(
    "Processing task state transition",
    extra={
        "metadata": {
            "task_id": str(task.task_id),
            "from_status": old_status,
            "to_status": new_status,
            "validation_rules": [r.__class__.__name__ for r in rules]
        }
    }
)
```

---

## Log Categories

### 1. Request Logs

**Purpose**: Track all HTTP requests/responses

```json
{
  "timestamp": "2025-10-30T14:23:45.123Z",
  "level": "INFO",
  "service": "api",
  "message": "HTTP request completed",
  "context": {
    "request_id": "req_8f4e2b1c",
    "user_id": "usr_a1b2c3d4",
    "organization_id": "org_12345"
  },
  "metadata": {
    "method": "POST",
    "path": "/api/v1/tasks",
    "status_code": 201,
    "duration_ms": 45,
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.100",
    "request_size_bytes": 1024,
    "response_size_bytes": 512
  }
}
```

**Implementation**:

```python
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all HTTP requests and responses"""
    start_time = time.time()

    response = await call_next(request)

    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "HTTP request completed",
        extra={
            "metadata": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_agent": request.headers.get("user-agent"),
                "ip_address": request.client.host,
            }
        }
    )

    return response
```

### 2. Application Logs

**Purpose**: Business logic execution, use case flows

```python
# Use case execution
logger.info(
    "Executing create task use case",
    extra={
        "metadata": {
            "use_case": "CreateTaskUseCase",
            "project_id": str(project_id),
            "requested_by": str(user.user_id)
        }
    }
)

# Domain event
logger.info(
    "Domain event published",
    extra={
        "metadata": {
            "event_type": "TaskAssigned",
            "aggregate_id": str(task.task_id),
            "aggregate_type": "Task",
            "version": task.version
        }
    }
)

# Validation failure
logger.warning(
    "Task validation failed",
    extra={
        "metadata": {
            "task_id": str(task.task_id),
            "validation_errors": [
                {"field": "due_date", "error": "Must be in future"},
                {"field": "assignee", "error": "Not a project member"}
            ]
        }
    }
)
```

### 3. Database Logs

**Purpose**: Database operations, query performance

```python
# Slow query warning
if query_duration_ms > 1000:
    logger.warning(
        "Slow database query detected",
        extra={
            "metadata": {
                "query_type": "SELECT",
                "table": "tasks",
                "duration_ms": query_duration_ms,
                "filters": {"project_id": str(project_id)},
                "result_count": len(results)
            }
        }
    )

# Connection pool exhaustion
logger.error(
    "Database connection pool exhausted",
    extra={
        "metadata": {
            "pool_size": 20,
            "active_connections": 20,
            "waiting_requests": 5
        }
    }
)
```

### 4. Integration Logs

**Purpose**: External service interactions

```python
# External API call
logger.info(
    "Calling external OAuth provider",
    extra={
        "metadata": {
            "provider": "google",
            "endpoint": "/oauth2/v1/userinfo",
            "timeout_seconds": 5
        }
    }
)

# Integration failure with retry
logger.warning(
    "S3 upload failed, retrying",
    extra={
        "metadata": {
            "service": "s3",
            "bucket": "taskmanager-attachments",
            "key": "attachments/file-123.pdf",
            "attempt": 2,
            "max_attempts": 3,
            "error": "RequestTimeout"
        }
    }
)
```

### 5. Background Job Logs

**Purpose**: Celery task execution

```python
# Task started
logger.info(
    "Celery task started",
    extra={
        "metadata": {
            "task_name": "send_notification_email",
            "task_id": task_id,
            "args": {"user_id": str(user_id), "template": "task_assigned"},
            "queue": "emails"
        }
    }
)

# Task completed
logger.info(
    "Celery task completed",
    extra={
        "metadata": {
            "task_name": "send_notification_email",
            "task_id": task_id,
            "duration_ms": 2300,
            "status": "SUCCESS"
        }
    }
)

# Task failed
logger.error(
    "Celery task failed",
    extra={
        "metadata": {
            "task_name": "send_notification_email",
            "task_id": task_id,
            "attempt": 3,
            "max_retries": 3,
            "error": str(error)
        }
    },
    exc_info=True
)
```

### 6. Security Logs

**Purpose**: Authentication, authorization, security events

**Note**: Security events are also written to audit_logs table (see [audit-logging.md](../security/audit-logging.md))

```python
# Authentication success
logger.info(
    "User authenticated successfully",
    extra={
        "metadata": {
            "user_id": str(user.user_id),
            "auth_method": "jwt",
            "ip_address": request.client.host
        }
    }
)

# Authorization failure
logger.warning(
    "Permission denied",
    extra={
        "metadata": {
            "user_id": str(user.user_id),
            "required_permission": "task:delete",
            "resource_type": "Task",
            "resource_id": str(task.task_id)
        }
    }
)

# Suspicious activity
logger.error(
    "Multiple failed login attempts detected",
    extra={
        "metadata": {
            "user_id": str(user.user_id),
            "attempt_count": 5,
            "time_window_minutes": 5,
            "ip_addresses": ["192.168.1.100", "192.168.1.101"]
        }
    }
)
```

---

## Log Aggregation

### AWS CloudWatch Logs

**Architecture**:

```
ECS Containers → CloudWatch Logs Agent → CloudWatch Log Groups → CloudWatch Insights
                                                                ↓
                                                           S3 Archive (long-term)
```

**Log Groups**:

```yaml
Log Groups:
  /aws/ecs/taskmanager-api:
    Retention: 30 days
    Size: ~500 MB/day
    Purpose: API application logs

  /aws/ecs/taskmanager-worker:
    Retention: 30 days
    Size: ~200 MB/day
    Purpose: Celery worker logs

  /aws/rds/taskmanager-db/error:
    Retention: 7 days
    Size: ~50 MB/day
    Purpose: Database error logs

  /aws/rds/taskmanager-db/slowquery:
    Retention: 7 days
    Size: ~100 MB/day
    Purpose: Slow query logs (>1 second)
```

**Log Streaming Configuration** (ECS):

```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/aws/ecs/taskmanager-api",
      "awslogs-region": "us-east-1",
      "awslogs-stream-prefix": "api",
      "awslogs-datetime-format": "%Y-%m-%dT%H:%M:%S"
    }
  }
}
```

### Log Queries (CloudWatch Insights)

**Query 1: Error Rate by Endpoint**

```sql
fields @timestamp, metadata.path, metadata.status_code
| filter level = "ERROR"
| stats count() as error_count by metadata.path
| sort error_count desc
```

**Query 2: Slow Requests (>1 second)**

```sql
fields @timestamp, metadata.path, metadata.duration_ms, context.user_id
| filter metadata.duration_ms > 1000
| sort metadata.duration_ms desc
| limit 50
```

**Query 3: Failed Login Attempts by User**

```sql
fields @timestamp, context.user_id, metadata.ip_address
| filter message like /failed.*login/i
| stats count() as failure_count by context.user_id, metadata.ip_address
| filter failure_count > 3
| sort failure_count desc
```

**Query 4: Request Volume by Organization**

```sql
fields @timestamp
| filter context.organization_id != null
| stats count() as request_count by context.organization_id
| sort request_count desc
```

**Query 5: Database Query Performance**

```sql
fields @timestamp, metadata.query_type, metadata.table, metadata.duration_ms
| filter message like /database query/
| stats avg(metadata.duration_ms) as avg_duration,
        max(metadata.duration_ms) as max_duration,
        count() as query_count
  by metadata.table
| sort avg_duration desc
```

---

## Retention Policies

### Application Logs

| Log Type          | Hot Storage (CloudWatch) | Cold Storage (S3) | Total Retention        |
| ----------------- | ------------------------ | ----------------- | ---------------------- |
| **API Logs**      | 30 days                  | 365 days          | 395 days (~13 months)  |
| **Worker Logs**   | 30 days                  | 365 days          | 395 days               |
| **Error Logs**    | 90 days                  | 730 days          | 820 days (~27 months)  |
| **Security Logs** | 90 days                  | 1095 days         | 1185 days (~39 months) |

### Database Logs

| Log Type            | Retention                                            |
| ------------------- | ---------------------------------------------------- |
| **Error Logs**      | 7 days                                               |
| **Slow Query Logs** | 7 days                                               |
| **Audit Logs**      | See [audit-logging.md](../security/audit-logging.md) |

### Archive to S3

**Automated export to S3** for long-term retention and cost optimization:

```python
import boto3
from datetime import datetime, timedelta

def export_logs_to_s3(log_group: str, days_ago: int = 30):
    """
    Export CloudWatch logs to S3 for long-term storage
    Runs daily via Lambda
    """
    logs_client = boto3.client('logs')

    # Calculate time range
    end_time = datetime.utcnow() - timedelta(days=days_ago)
    start_time = end_time - timedelta(days=1)

    # Export to S3
    response = logs_client.create_export_task(
        logGroupName=log_group,
        fromTime=int(start_time.timestamp() * 1000),
        to=int(end_time.timestamp() * 1000),
        destination='taskmanager-logs-archive',
        destinationPrefix=f'{log_group}/{end_time.strftime("%Y/%m/%d")}'
    )

    logger.info(
        "Log export task created",
        extra={
            "metadata": {
                "log_group": log_group,
                "task_id": response['taskId'],
                "date": end_time.strftime("%Y-%m-%d")
            }
        }
    )
```

**S3 Bucket Configuration**:

```yaml
Bucket: taskmanager-logs-archive
Region: us-east-1

Lifecycle Policy:
  - Transition to Glacier: 90 days
  - Expire: 395 days (for application logs)
  - Expire: 820 days (for error logs)

Encryption: AES-256 (SSE-S3)
Versioning: Disabled
Public Access: Blocked
```

---

## Log Monitoring & Alerting

### CloudWatch Alarms

```yaml
Alarms:
  - Name: HighErrorRate
    Metric: Errors > 10 per minute
    Threshold: 10 errors/min
    Evaluation Periods: 2
    Action: SNS topic → PagerDuty

  - Name: SlowResponseTime
    Metric: P95 latency > 1 second
    Threshold: 1000 ms
    Evaluation Periods: 3
    Action: SNS topic → Slack #alerts

  - Name: DatabaseConnectionPoolExhausted
    Metric: ConnectionPoolExhausted events
    Threshold: 1 occurrence
    Evaluation Periods: 1
    Action: SNS topic → PagerDuty

  - Name: HighFailedLoginRate
    Metric: Failed login attempts > 10 per 5 minutes
    Threshold: 10 failures/5min
    Evaluation Periods: 1
    Action: SNS topic → Security team
```

### Log-Based Metrics

**Custom metrics derived from logs**:

```python
# Extract metrics from structured logs
metric_filters = [
    {
        "filter_name": "TaskCreationRate",
        "filter_pattern": '{ $.message = "Task created successfully" }',
        "metric_name": "TasksCreated",
        "metric_namespace": "TaskManager/Application",
        "metric_value": "1"
    },
    {
        "filter_name": "SlowQueries",
        "filter_pattern": '{ $.metadata.duration_ms > 1000 }',
        "metric_name": "SlowQueryCount",
        "metric_namespace": "TaskManager/Database",
        "metric_value": "1"
    },
    {
        "filter_name": "PermissionDenied",
        "filter_pattern": '{ $.message = "Permission denied" }',
        "metric_name": "AuthorizationFailures",
        "metric_namespace": "TaskManager/Security",
        "metric_value": "1"
    }
]
```

---

## Best Practices

### DO ✅

1. **Use structured logging** (JSON) for all services
2. **Include request_id** in every log entry
3. **Log at appropriate levels** (INFO for success, ERROR for failures)
4. **Include actionable context** (IDs, duration, error messages)
5. **Log exceptions with stack traces** using `exc_info=True`
6. **Use correlation IDs** for distributed tracing
7. **Mask sensitive data** before logging
8. **Monitor log volume** to detect anomalies

### DON'T ❌

1. **Don't log passwords, tokens, or secrets**
2. **Don't log excessive DEBUG in production**
3. **Don't use string concatenation** for log messages
4. **Don't log in tight loops** (aggregate instead)
5. **Don't ignore logging errors** (configure dead letter queue)
6. **Don't hardcode log levels** (use environment variables)
7. **Don't log raw SQL queries** with user input
8. **Don't create logs without context**

### Example: Bad vs Good Logging

❌ **Bad**:

```python
print("Task created")
logger.info("User: " + str(user_id))  # String concatenation
logger.debug(f"SQL: {query}")  # SQL with user input
logger.error("Error occurred")  # No context
```

✅ **Good**:

```python
logger.info(
    "Task created successfully",
    extra={
        "metadata": {
            "task_id": str(task.task_id),
            "project_id": str(task.project_id),
            "created_by": str(user.user_id),
            "duration_ms": 45
        }
    }
)
```

---

## Related Documents

- [Metrics](./metrics.md) - Application and infrastructure metrics
- [Tracing](./tracing.md) - Distributed tracing with OpenTelemetry
- [Alerting](./alerting.md) - Alert definitions and escalation
- [Audit Logging](../security/audit-logging.md) - Security audit trail
- [Incident Response](./incident-response.md) - Using logs during incidents

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
