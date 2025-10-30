# Audit Logging

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines audit logging strategies for the Task Management System, covering security-relevant events, audit log schema, retention policies, and compliance reporting mechanisms.

---

## Audit Logging Principles

### Core Principles

1. **Comprehensive Coverage**: Log all security-relevant events
2. **Immutability**: Audit logs are append-only, never modified
3. **Tamper-Proof**: Cryptographic integrity verification
4. **Accountability**: Every action traceable to user or system
5. **Retention Compliance**: Meet regulatory requirements

---

## Audit Events

### Security-Relevant Events

| Category              | Events                                                             | Priority | Retention |
| --------------------- | ------------------------------------------------------------------ | -------- | --------- |
| **Authentication**    | Login success/failure, logout, password change, MFA enable/disable | High     | 12 months |
| **Authorization**     | Permission denied, role change, access attempt                     | High     | 12 months |
| **Data Access**       | View PII, export data, GDPR request                                | High     | 24 months |
| **Data Modification** | Create/update/delete entities                                      | Medium   | 12 months |
| **Configuration**     | Settings change, integration enabled                               | Medium   | 12 months |
| **Administrative**    | User invite, org settings, billing change                          | High     | 24 months |

### Audit Event Schema

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from enum import Enum

class AuditAction(str, Enum):
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"

    # Authorization
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"

    # Data Operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"

    # Administrative
    USER_INVITED = "user_invited"
    USER_DEACTIVATED = "user_deactivated"
    ORG_SETTINGS_CHANGED = "org_settings_changed"

@dataclass
class AuditLog:
    """Immutable audit log entry"""
    audit_id: UUID
    timestamp: datetime
    organization_id: UUID
    user_id: UUID | None  # None for system events
    action: AuditAction
    entity_type: str  # "user", "project", "task", etc.
    entity_id: UUID | None
    changes: dict | None  # Before/after state for updates
    ip_address: str
    user_agent: str
    request_id: UUID
    metadata: dict | None

    def __post_init__(self):
        """Validate audit log"""
        if self.timestamp > datetime.utcnow():
            raise ValueError("Timestamp cannot be in future")
```

### Database Schema

```sql
CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    organization_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    changes JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_id UUID NOT NULL,
    metadata JSONB,

    -- Indexes for common queries
    INDEX idx_org_timestamp (organization_id, timestamp DESC),
    INDEX idx_user_timestamp (user_id, timestamp DESC),
    INDEX idx_entity (entity_type, entity_id, timestamp DESC),
    INDEX idx_action_timestamp (action, timestamp DESC),
    INDEX idx_request (request_id),

    -- Foreign keys
    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)

) ENGINE=InnoDB
PARTITION BY RANGE (timestamp) (
    PARTITION p_2025_10 VALUES LESS THAN ('2025-11-01'),
    PARTITION p_2025_11 VALUES LESS THAN ('2025-12-01'),
    PARTITION p_2025_12 VALUES LESS THAN ('2026-01-01')
    -- New partitions added monthly
);
```

---

## Audit Logging Implementation

### Audit Service

```python
from contextlib import contextmanager
from uuid import uuid4

class AuditService:
    """Centralized audit logging service"""

    def __init__(self, db_session, redis_client):
        self.db = db_session
        self.redis = redis_client

    def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID | None = None,
        changes: dict | None = None,
        user: User | None = None,
        organization_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: UUID | None = None,
        metadata: dict | None = None
    ) -> AuditLog:
        """Create audit log entry"""

        audit_log = AuditLog(
            audit_id=uuid4(),
            timestamp=datetime.utcnow(),
            organization_id=organization_id or (user.organization_id if user else None),
            user_id=user.user_id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id or uuid4(),
            metadata=metadata
        )

        # Persist to database
        self.db.add(audit_log)
        self.db.commit()

        # Also publish to Redis for real-time monitoring
        self._publish_audit_event(audit_log)

        return audit_log

    def log_authentication(
        self,
        action: AuditAction,
        email: str,
        user_id: UUID | None,
        success: bool,
        ip_address: str,
        user_agent: str,
        reason: str | None = None
    ) -> None:
        """Log authentication event"""
        self.log(
            action=action,
            entity_type="user",
            entity_id=user_id,
            metadata={
                "email": email,
                "success": success,
                "reason": reason
            },
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_authorization_failure(
        self,
        user: User,
        permission: str,
        resource_type: str,
        resource_id: UUID,
        ip_address: str
    ) -> None:
        """Log failed authorization attempt"""
        self.log(
            action=AuditAction.PERMISSION_DENIED,
            entity_type=resource_type,
            entity_id=resource_id,
            user=user,
            metadata={
                "permission": permission,
                "denied_at": datetime.utcnow().isoformat()
            },
            ip_address=ip_address
        )

    def log_data_modification(
        self,
        action: AuditAction,
        entity_type: str,
        entity: any,
        changes: dict | None,
        user: User
    ) -> None:
        """Log data modification"""
        self.log(
            action=action,
            entity_type=entity_type,
            entity_id=getattr(entity, f"{entity_type}_id", None),
            changes=changes,
            user=user,
            metadata={
                "entity_name": getattr(entity, "name", None) or getattr(entity, "title", None)
            }
        )

    def _publish_audit_event(self, audit_log: AuditLog) -> None:
        """Publish audit event to Redis for real-time monitoring"""
        channel = f"audit:{audit_log.organization_id}"
        message = json.dumps({
            "audit_id": str(audit_log.audit_id),
            "action": audit_log.action.value,
            "entity_type": audit_log.entity_type,
            "timestamp": audit_log.timestamp.isoformat(),
            "user_id": str(audit_log.user_id) if audit_log.user_id else None
        })
        self.redis.publish(channel, message)
```

### Automatic Audit Logging

**Strategy**: Use decorators and middleware for automatic logging.

```python
from functools import wraps
from fastapi import Request

def audit_logged(action: AuditAction, entity_type: str):
    """Decorator to automatically log actions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)

            # Extract context
            request: Request = kwargs.get('request')
            user: User = kwargs.get('user') or kwargs.get('current_user')
            entity_id = kwargs.get(f'{entity_type}_id') or getattr(result, f'{entity_type}_id', None)

            # Log action
            audit_service.log(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user=user,
                ip_address=request.client.host if request else None,
                user_agent=request.headers.get('user-agent') if request else None,
                request_id=request.state.request_id if request else None
            )

            return result

        return wrapper
    return decorator

# Usage
@router.post("/projects")
@audit_logged(AuditAction.CREATE, "project")
async def create_project(
    data: CreateProjectRequest,
    user: User = Depends(get_current_user),
    request: Request = None
):
    """Create project (auto-audited)"""
    project = Project(...)
    project_repo.create(project)
    return project
```

---

## Change Tracking

### Track Before/After State

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class ChangeTracker(Generic[T]):
    """Track entity changes for audit logs"""

    def __init__(self, entity: T):
        self.before = self._serialize(entity)
        self.entity = entity

    def get_changes(self) -> dict:
        """Get changed fields"""
        after = self._serialize(self.entity)

        changes = {
            "before": {},
            "after": {}
        }

        for key, old_value in self.before.items():
            new_value = after.get(key)
            if old_value != new_value:
                changes["before"][key] = old_value
                changes["after"][key] = new_value

        return changes if changes["before"] else None

    def _serialize(self, entity: T) -> dict:
        """Serialize entity to dict"""
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        return entity.__dict__

# Usage
def update_task(task_id: UUID, updates: dict, user: User):
    task = task_repo.get_by_id(task_id)

    # Track changes
    tracker = ChangeTracker(task)

    # Apply updates
    task.title = updates.get('title', task.title)
    task.status = updates.get('status', task.status)
    task_repo.save(task)

    # Log with changes
    audit_service.log_data_modification(
        action=AuditAction.UPDATE,
        entity_type="task",
        entity=task,
        changes=tracker.get_changes(),
        user=user
    )
```

---

## Retention Policy

### Retention Periods

| Data Type                  | Hot Storage | Cold Storage (S3) | Total Retention |
| -------------------------- | ----------- | ----------------- | --------------- |
| **Authentication Events**  | 12 months   | 12-24 months      | 24 months       |
| **Data Modifications**     | 12 months   | None              | 12 months       |
| **GDPR Requests**          | 24 months   | 24-60 months      | 60 months       |
| **Failed Access Attempts** | 6 months    | None              | 6 months        |

### Automated Archival

```python
class AuditArchivalService:
    """Archive old audit logs to S3"""

    def __init__(self, db_session, s3_client):
        self.db = db_session
        self.s3 = s3_client
        self.bucket = 'taskmanager-audit-archive'

    def archive_old_logs(self, months_old: int = 12):
        """Archive audit logs older than specified months"""
        cutoff_date = datetime.utcnow() - timedelta(days=months_old * 30)

        # Get partition name
        partition_name = f"p_{cutoff_date.strftime('%Y_%m')}"

        # Export partition to S3
        export_path = f"s3://{self.bucket}/audit-logs/{partition_name}/"

        query = f"""
        SELECT * FROM audit_logs PARTITION ({partition_name})
        INTO OUTFILE S3 '{export_path}'
        FORMAT PARQUET
        COMPRESSION SNAPPY
        """

        self.db.execute(query)

        # Verify export
        if self._verify_export(partition_name):
            # Drop partition
            self.db.execute(f"ALTER TABLE audit_logs DROP PARTITION {partition_name}")
            logger.info(f"Archived and dropped partition {partition_name}")
        else:
            logger.error(f"Failed to verify export for {partition_name}")

    def _verify_export(self, partition_name: str) -> bool:
        """Verify S3 export completed"""
        # Check if S3 files exist
        prefix = f"audit-logs/{partition_name}/"
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return 'Contents' in response and len(response['Contents']) > 0
```

---

## Compliance Reporting

### Audit Reports

```python
class AuditReportService:
    """Generate compliance reports"""

    def generate_access_report(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """Generate access report for compliance"""

        logs = self.db.query(AuditLog).filter(
            AuditLog.organization_id == organization_id,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp < end_date,
            AuditLog.action.in_([
                AuditAction.LOGIN_SUCCESS,
                AuditAction.LOGIN_FAILURE,
                AuditAction.PERMISSION_DENIED
            ])
        ).all()

        report = {
            "organization_id": str(organization_id),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_logins": sum(1 for log in logs if log.action == AuditAction.LOGIN_SUCCESS),
                "failed_logins": sum(1 for log in logs if log.action == AuditAction.LOGIN_FAILURE),
                "permission_denials": sum(1 for log in logs if log.action == AuditAction.PERMISSION_DENIED)
            },
            "failed_login_attempts": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "email": log.metadata.get('email'),
                    "ip_address": log.ip_address,
                    "reason": log.metadata.get('reason')
                }
                for log in logs if log.action == AuditAction.LOGIN_FAILURE
            ],
            "unauthorized_access_attempts": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": str(log.user_id),
                    "resource": f"{log.entity_type}:{log.entity_id}",
                    "permission": log.metadata.get('permission')
                }
                for log in logs if log.action == AuditAction.PERMISSION_DENIED
            ]
        }

        return report

    def generate_data_access_report(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """Generate user data access report (GDPR Article 15)"""

        logs = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp < end_date
        ).all()

        return {
            "user_id": str(user_id),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "activities": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "action": log.action.value,
                    "entity": f"{log.entity_type}:{log.entity_id}",
                    "ip_address": log.ip_address
                }
                for log in logs
            ]
        }
```

---

## Real-Time Monitoring

### Audit Event Streaming

```python
class AuditMonitoringService:
    """Real-time audit event monitoring"""

    def __init__(self, redis_client):
        self.redis = redis_client

    def subscribe_to_events(self, organization_id: UUID, callback):
        """Subscribe to audit events for organization"""
        pubsub = self.redis.pubsub()
        channel = f"audit:{organization_id}"
        pubsub.subscribe(channel)

        for message in pubsub.listen():
            if message['type'] == 'message':
                event = json.loads(message['data'])
                callback(event)

    def detect_anomalies(self, organization_id: UUID):
        """Detect suspicious audit patterns"""
        # Get recent failed logins
        recent_failures = self.db.query(AuditLog).filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == AuditAction.LOGIN_FAILURE,
            AuditLog.timestamp >= datetime.utcnow() - timedelta(minutes=15)
        ).count()

        # Alert if > 10 failed logins in 15 minutes
        if recent_failures > 10:
            self._send_security_alert(
                organization_id,
                "High volume of failed login attempts detected"
            )
```

---

## Security Best Practices

### DO ✅

1. **Log All Security Events**: Authentication, authorization, data access
2. **Use Append-Only Storage**: Never modify/delete audit logs
3. **Include Context**: IP address, user agent, request ID
4. **Partition by Time**: Monthly partitions for efficient queries
5. **Archive to S3**: Long-term retention in cold storage
6. **Monitor in Real-Time**: Detect suspicious patterns
7. **Protect Audit Logs**: Separate permissions, encrypted storage

### DON'T ❌

1. **Don't Log Sensitive Data**: Passwords, tokens, PII content
2. **Don't Allow Modification**: Audit logs are immutable
3. **Don't Skip Failed Events**: Log failures, not just successes
4. **Don't Ignore Compliance**: Meet regulatory retention requirements
5. **Don't Expose Raw Logs**: Use reports, not direct database access
6. **Don't Forget Archival**: Manage storage costs with S3 lifecycle
7. **Don't Over-Log**: Balance detail with storage costs

---

## Related Documents

- [Authentication](./authentication.md)
- [Authorization](./authorization.md)
- [Data Protection](./data-protection.md)
- [Defense in Depth](./defense-in-depth.md)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
