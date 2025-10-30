# Database Optimization Guide

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document provides comprehensive database optimization strategies for the Task Management System to achieve performance targets (query p95 < 50ms, p99 < 100ms) while maintaining scalability and data integrity. Optimization spans indexing, query patterns, connection management, and database configuration.

---

## Optimization Principles

### Core Principles

1. **Index Everything You Query**: Every WHERE, JOIN, ORDER BY needs an index
2. **Measure Before Optimizing**: Use EXPLAIN to understand query plans
3. **Optimize for Common Cases**: 80/20 rule - optimize frequent queries
4. **Balance Reads and Writes**: Indexes speed reads but slow writes
5. **Monitor Continuously**: Track slow queries and optimize iteratively

---

## Indexing Strategy

### Index Types

| Index Type           | Use Case                | Performance | Storage Cost |
| -------------------- | ----------------------- | ----------- | ------------ |
| **B-Tree (Default)** | Equality, range queries | Excellent   | Medium       |
| **Hash**             | Exact match only        | Fast        | Low          |
| **Full-Text**        | Text search             | Good        | High         |
| **Composite**        | Multi-column queries    | Excellent   | Medium-High  |

### Primary Indexes

#### User Management Context

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    organization_id UUID NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP,

    -- Indexes
    INDEX idx_email (email),                              -- Login by email
    INDEX idx_org_id (organization_id),                   -- List users by org
    INDEX idx_org_status (organization_id, status),       -- Active users by org
    INDEX idx_last_login (last_login_at DESC),            -- Find inactive users

    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
) ENGINE=InnoDB;

-- Organizations table
CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    owner_id UUID NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,

    -- Indexes
    INDEX idx_slug (slug),                                -- Access by slug
    INDEX idx_owner (owner_id),                           -- Find owned orgs
    INDEX idx_tier (subscription_tier),                   -- Analytics by tier

    FOREIGN KEY (owner_id) REFERENCES users(user_id)
) ENGINE=InnoDB;
```

#### Project Management Context

```sql
-- Projects table
CREATE TABLE projects (
    project_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    -- Indexes
    INDEX idx_org_id (organization_id),                   -- List projects by org
    INDEX idx_org_status (organization_id, status),       -- Active projects
    INDEX idx_owner (owner_id),                           -- Projects owned by user
    INDEX idx_updated (updated_at DESC),                  -- Recently updated
    INDEX idx_org_updated (organization_id, updated_at DESC), -- Org recent projects

    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
) ENGINE=InnoDB;
```

#### Task Management Context

```sql
-- Tasks table (partitioned by project_id)
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    assignee_id UUID,
    created_by UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    due_date TIMESTAMP,
    completed_at TIMESTAMP,

    -- Indexes
    INDEX idx_project_id (project_id),                    -- All tasks in project
    INDEX idx_project_status (project_id, status),        -- Filter by status
    INDEX idx_project_assignee (project_id, assignee_id), -- User's tasks in project
    INDEX idx_project_due (project_id, due_date),         -- Sort by due date
    INDEX idx_assignee_status (assignee_id, status),      -- User's open tasks
    INDEX idx_created_at (project_id, created_at DESC),   -- Recently created
    INDEX idx_updated_at (project_id, updated_at DESC),   -- Recently updated
    INDEX idx_priority (project_id, priority, due_date),  -- High priority tasks

    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (assignee_id) REFERENCES users(user_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
) ENGINE=InnoDB
PARTITION BY HASH(project_id) PARTITIONS 16;

-- Comments table
CREATE TABLE comments (
    comment_id UUID PRIMARY KEY,
    task_id UUID NOT NULL,
    project_id UUID NOT NULL,  -- Denormalized for partitioning
    author_id UUID NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    -- Indexes
    INDEX idx_task_id (project_id, task_id),              -- Comments for task
    INDEX idx_author (project_id, author_id),             -- User's comments
    INDEX idx_created (project_id, created_at DESC),      -- Recent comments

    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (author_id) REFERENCES users(user_id)
) ENGINE=InnoDB
PARTITION BY HASH(project_id) PARTITIONS 16;
```

#### Notification Context

```sql
-- Notifications table
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    read_at TIMESTAMP,

    -- Indexes
    INDEX idx_user_unread (user_id, is_read, created_at DESC), -- Unread notifications
    INDEX idx_user_type (user_id, type),                        -- Filter by type
    INDEX idx_org (organization_id, created_at DESC),           -- Org notifications
    INDEX idx_created (created_at DESC),                        -- Recent notifications

    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;
```

#### Audit Context

```sql
-- Audit logs (time-based partitions)
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    user_id UUID,
    event_type VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL,

    -- Indexes
    INDEX idx_org_created (organization_id, created_at DESC),   -- Org audit trail
    INDEX idx_user_created (user_id, created_at DESC),          -- User activity
    INDEX idx_resource (resource_type, resource_id, created_at DESC), -- Resource history
    INDEX idx_event_type (event_type, created_at DESC),         -- Event analytics

    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB
PARTITION BY RANGE (created_at) (
    PARTITION p_2025_10 VALUES LESS THAN ('2025-11-01'),
    PARTITION p_2025_11 VALUES LESS THAN ('2025-12-01'),
    PARTITION p_2025_12 VALUES LESS THAN ('2026-01-01')
);
```

---

## Composite Index Design

### Index Column Order

**Rule**: Most selective column first, then by query frequency.

**Example**:

```sql
-- ❌ BAD: Low selectivity first
CREATE INDEX idx_bad ON tasks (status, project_id);
-- Only 5 status values; scans many rows

-- ✅ GOOD: High selectivity first
CREATE INDEX idx_good ON tasks (project_id, status);
-- Thousands of projects; filters to small set quickly
```

### Covering Indexes

**Definition**: Index contains all columns needed by query (no table lookup).

```sql
-- Query: Get task titles for project
SELECT task_id, title, status
FROM tasks
WHERE project_id = ? AND status = 'TODO';

-- ✅ Covering index (no table access needed)
CREATE INDEX idx_covering ON tasks (project_id, status, task_id, title);
```

**Performance**:

- Without covering: ~20ms (index + table lookup)
- With covering: ~5ms (index only)

### Index Prefix

**Rule**: MySQL uses leftmost prefix of composite index.

```sql
-- Composite index
CREATE INDEX idx_composite ON tasks (project_id, status, priority);

-- ✅ Uses index
WHERE project_id = ?
WHERE project_id = ? AND status = ?
WHERE project_id = ? AND status = ? AND priority = ?

-- ❌ Does NOT use index
WHERE status = ?
WHERE priority = ?
WHERE status = ? AND priority = ?
```

---

## Query Optimization Patterns

### 1. Efficient Filtering

**Pattern**: Always include partition key and indexed columns in WHERE clause.

```python
# ❌ BAD: No partition key (scans all partitions)
def get_user_tasks(user_id: UUID) -> List[Task]:
    return db.query(Task).filter_by(assignee_id=user_id).all()
    # Query plan: Scan all 16 partitions (500ms)

# ✅ GOOD: Use materialized view partitioned by user_id
def get_user_tasks(user_id: UUID) -> List[Task]:
    return db.query(TaskAssignmentMV).filter_by(assignee_id=user_id).all()
    # Query plan: Single partition scan (10ms)

# ✅ GOOD: Include partition key if known
def get_project_tasks(project_id: UUID, assignee_id: UUID) -> List[Task]:
    return db.query(Task).filter_by(
        project_id=project_id,  # Partition key
        assignee_id=assignee_id
    ).all()
    # Query plan: Single partition scan (15ms)
```

### 2. Pagination

**Pattern**: Use keyset pagination instead of OFFSET for large datasets.

```python
# ❌ BAD: OFFSET pagination (slow for large offsets)
def get_tasks_offset(project_id: UUID, page: int, page_size: int) -> List[Task]:
    offset = (page - 1) * page_size
    return db.query(Task).filter_by(
        project_id=project_id
    ).order_by(Task.created_at.desc()).offset(offset).limit(page_size).all()
    # Page 100: Scans 10,000 rows to skip them (200ms)

# ✅ GOOD: Keyset pagination (consistent performance)
def get_tasks_keyset(
    project_id: UUID,
    last_seen_id: Optional[UUID],
    last_seen_date: Optional[datetime],
    page_size: int
) -> List[Task]:
    query = db.query(Task).filter_by(project_id=project_id)

    if last_seen_date:
        # Continue from last seen
        query = query.filter(
            (Task.created_at < last_seen_date) |
            ((Task.created_at == last_seen_date) & (Task.task_id > last_seen_id))
        )

    return query.order_by(
        Task.created_at.desc(),
        Task.task_id.asc()
    ).limit(page_size).all()
    # Any page: Only scans needed rows (20ms)
```

### 3. Aggregate Queries

**Pattern**: Use covering indexes or materialized aggregates.

```python
# ❌ BAD: Aggregate without covering index
def get_project_task_count(project_id: UUID) -> int:
    return db.query(Task).filter_by(project_id=project_id).count()
    # Scans all rows in partition (100ms for 10K tasks)

# ✅ BETTER: Use covering index
CREATE INDEX idx_project_count ON tasks (project_id, task_id);
# Count now only scans index (30ms)

# ✅ BEST: Use cached materialized aggregate
def get_project_statistics(project_id: UUID) -> dict:
    # Check cache first
    cached = aggregate_cache.get_project_stats(project_id)
    if cached:
        return cached  # 2ms

    # Compute and cache
    stats = {
        'total_tasks': db.query(Task).filter_by(project_id=project_id).count(),
        'completed': db.query(Task).filter_by(
            project_id=project_id,
            status='COMPLETED'
        ).count(),
        # ... more aggregates
    }

    aggregate_cache.set_project_stats(project_id, stats, ttl=300)
    return stats  # 50ms first time, 2ms after
```

### 4. JOIN Optimization

**Pattern**: Index foreign keys, limit result set before joining.

```sql
-- ❌ BAD: Join without indexes on foreign keys
SELECT t.*, u.full_name
FROM tasks t
JOIN users u ON t.assignee_id = u.user_id
WHERE t.project_id = ?;
-- Nested loop join: 200ms

-- ✅ GOOD: Indexed foreign keys
CREATE INDEX idx_tasks_assignee ON tasks (assignee_id);
CREATE INDEX idx_users_pk ON users (user_id);  -- Primary key auto-indexed
-- Hash join: 20ms

-- ✅ BETTER: Filter before joining
SELECT t.*, u.full_name
FROM (
    SELECT *
    FROM tasks
    WHERE project_id = ? AND status = 'TODO'
    LIMIT 100
) t
JOIN users u ON t.assignee_id = u.user_id;
-- Filters to 100 rows before join: 10ms
```

### 5. Subquery vs JOIN

**Pattern**: Prefer JOINs over subqueries in MySQL.

```python
# ❌ SLOW: Correlated subquery
query = """
SELECT p.*,
       (SELECT COUNT(*) FROM tasks WHERE project_id = p.project_id) as task_count
FROM projects p
WHERE organization_id = ?
"""
# Executes subquery for each row: 500ms

# ✅ FAST: LEFT JOIN with GROUP BY
query = """
SELECT p.*, COUNT(t.task_id) as task_count
FROM projects p
LEFT JOIN tasks t ON p.project_id = t.project_id
WHERE p.organization_id = ?
GROUP BY p.project_id
"""
# Single scan with aggregation: 50ms
```

---

## EXPLAIN Analysis

### Reading EXPLAIN Output

```sql
EXPLAIN SELECT *
FROM tasks
WHERE project_id = 'abc-123' AND status = 'TODO'
ORDER BY created_at DESC
LIMIT 10;
```

**Key Columns**:

| Column            | Good Value         | Bad Value      | Action             |
| ----------------- | ------------------ | -------------- | ------------------ |
| **type**          | const, eq_ref, ref | ALL, index     | Add index          |
| **possible_keys** | Shows indexes      | NULL           | Create index       |
| **key**           | Index name         | NULL           | Index not used     |
| **rows**          | < 1000             | > 10000        | Optimize query     |
| **Extra**         | Using index        | Using filesort | Add covering index |

**Example Analysis**:

```sql
-- ❌ BAD EXPLAIN
+------+-------+------+------+------+------+-------+-------------+
| type | key   | rows | Extra                                   |
+------+-------+------+------+------+------+-------+-------------+
| ALL  | NULL  | 50000| Using where; Using filesort             |
+------+-------+------+------+------+------+-------+-------------+

-- Problem: Full table scan (type=ALL), filesort (sorting in memory)
-- Solution: Add composite index

CREATE INDEX idx_project_status_created ON tasks (project_id, status, created_at DESC);

-- ✅ GOOD EXPLAIN
+------+---------------------------+------+-------+-----------------------+
| type | key                       | rows | Extra                         |
+------+---------------------------+------+-------+-----------------------+
| ref  | idx_project_status_created| 100  | Using where; Using index      |
+------+---------------------------+------+-------+-----------------------+

-- Result: Index scan (type=ref), no filesort, covering index
```

### Automated EXPLAIN Monitoring

```python
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def explain_slow_queries(conn, cursor, statement, parameters, context, executemany):
    """Auto-EXPLAIN slow queries"""
    start = time.time()

    # Execute query
    cursor.execute(statement, parameters)

    duration = time.time() - start

    # Log slow queries with EXPLAIN
    if duration > 0.1:  # 100ms threshold
        explain_query = f"EXPLAIN {statement}"
        explain_result = cursor.execute(explain_query).fetchall()

        logger.warning(
            f"Slow query detected: {duration:.2f}s\n"
            f"Query: {statement}\n"
            f"EXPLAIN: {explain_result}"
        )
```

---

## Connection Pooling

### Configuration

**Goal**: Maintain optimal connection pool size to balance concurrency and resource usage.

**Formula**: `pool_size = (core_count × 2) + effective_spindle_count`

For 4-core RDS instance: `pool_size = (4 × 2) + 1 = 9`

**SQLAlchemy Configuration**:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # Steady-state connections
    max_overflow=20,        # Additional connections under load
    pool_timeout=30,        # Wait 30s for connection before error
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Test connection before use
    echo_pool=True,         # Log pool events (dev only)
)
```

### Pool Monitoring

```python
from prometheus_client import Gauge

# Metrics
db_pool_size = Gauge('db_pool_connections_total', 'Total pool connections')
db_pool_checked_out = Gauge('db_pool_connections_checked_out', 'Checked out connections')
db_pool_overflow = Gauge('db_pool_connections_overflow', 'Overflow connections')

def monitor_pool():
    """Monitor connection pool health"""
    pool = engine.pool

    db_pool_size.set(pool.size())
    db_pool_checked_out.set(pool.checkedout())
    db_pool_overflow.set(pool.overflow())

    # Alert if pool exhausted
    if pool.checkedout() >= pool.size() + pool.overflow():
        logger.critical("Database connection pool exhausted!")
```

### Connection Leaks

**Problem**: Connections not returned to pool.

**Solution**: Always use context managers.

```python
# ❌ BAD: Manual connection management
conn = engine.connect()
result = conn.execute("SELECT ...")
# If exception occurs, connection leaks!

# ✅ GOOD: Context manager (auto-cleanup)
with engine.connect() as conn:
    result = conn.execute("SELECT ...")
# Connection always returned, even on exception

# ✅ BEST: SQLAlchemy session with auto-cleanup
@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage
with get_db_session() as db:
    user = db.query(User).filter_by(email=email).first()
```

---

## Read Replicas

### Purpose

- **Separate read and write traffic**: Master for writes, replicas for reads
- **Scale read throughput**: Add replicas as read load grows
- **Reduce master load**: Offload reporting and analytics queries

### Configuration

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random

# Master database (writes)
master_engine = create_engine(MASTER_DATABASE_URL, pool_size=10)
MasterSession = sessionmaker(bind=master_engine)

# Read replicas (reads)
replica_engines = [
    create_engine(REPLICA_1_URL, pool_size=20),
    create_engine(REPLICA_2_URL, pool_size=20),
]
ReplicaSession = sessionmaker()

def get_read_engine():
    """Load balance across read replicas"""
    return random.choice(replica_engines)

def get_db_session(read_only: bool = False):
    """Get database session based on operation type"""
    if read_only:
        engine = get_read_engine()
    else:
        engine = master_engine

    ReplicaSession.configure(bind=engine)
    return ReplicaSession()
```

### Repository Pattern with Replicas

```python
class TaskRepository:
    """Task repository with read/write splitting"""

    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """Read from replica"""
        session = get_db_session(read_only=True)
        return session.query(Task).filter_by(task_id=task_id).first()

    def list_by_project(self, project_id: UUID) -> List[Task]:
        """Read from replica"""
        session = get_db_session(read_only=True)
        return session.query(Task).filter_by(project_id=project_id).all()

    def save(self, task: Task) -> None:
        """Write to master"""
        session = get_db_session(read_only=False)
        session.add(task)
        session.commit()

    def delete(self, task_id: UUID) -> None:
        """Write to master"""
        session = get_db_session(read_only=False)
        task = session.query(Task).filter_by(task_id=task_id).first()
        if task:
            session.delete(task)
            session.commit()
```

### Replica Lag Monitoring

```python
def check_replica_lag() -> dict:
    """Monitor replication lag"""
    master_session = MasterSession()
    replica_session = get_db_session(read_only=True)

    # Get master position
    master_status = master_session.execute("SHOW MASTER STATUS").fetchone()
    master_log_file = master_status['File']
    master_log_pos = master_status['Position']

    # Get replica position
    replica_status = replica_session.execute("SHOW SLAVE STATUS").fetchone()
    replica_log_file = replica_status['Relay_Master_Log_File']
    replica_log_pos = replica_status['Exec_Master_Log_Pos']
    seconds_behind = replica_status['Seconds_Behind_Master']

    # Alert if lag > 5 seconds
    if seconds_behind > 5:
        logger.warning(f"Replica lag detected: {seconds_behind}s")

    return {
        'lag_seconds': seconds_behind,
        'master_position': f"{master_log_file}:{master_log_pos}",
        'replica_position': f"{replica_log_file}:{replica_log_pos}",
        'healthy': seconds_behind < 5
    }
```

---

## Database Configuration

### MySQL Configuration (my.cnf)

```ini
[mysqld]
# Connection settings
max_connections = 500
wait_timeout = 300
interactive_timeout = 300

# Buffer pool (70-80% of available RAM)
innodb_buffer_pool_size = 12G
innodb_buffer_pool_instances = 8

# Log settings
innodb_log_file_size = 1G
innodb_flush_log_at_trx_commit = 2  # Balance durability vs. performance
innodb_flush_method = O_DIRECT

# Query cache (disabled in MySQL 8.0+)
query_cache_type = 0

# Slow query log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 0.5  # Log queries > 500ms

# Performance schema
performance_schema = ON
```

### RDS Parameter Group

```yaml
# AWS RDS parameter group
Parameters:
  innodb_buffer_pool_size: "{DBInstanceClassMemory*3/4}"
  max_connections: 500
  slow_query_log: 1
  long_query_time: 0.5
  innodb_flush_log_at_trx_commit: 2
  innodb_file_per_table: 1
```

---

## Monitoring & Alerting

### Key Metrics

| Metric                    | Target   | Alert Threshold | Action                  |
| ------------------------- | -------- | --------------- | ----------------------- |
| **Query Latency p95**     | < 50ms   | > 100ms         | Optimize slow queries   |
| **Connection Pool Usage** | < 80%    | > 90%           | Increase pool size      |
| **Slow Query Count**      | < 10/min | > 50/min        | Add indexes             |
| **Replica Lag**           | < 1s     | > 5s            | Investigate replication |
| **Buffer Pool Hit Rate**  | > 99%    | < 95%           | Increase buffer pool    |

### Prometheus Queries

```promql
# Query latency p95
histogram_quantile(0.95,
  rate(db_query_duration_seconds_bucket[5m])
)

# Slow query rate
rate(mysql_slow_queries_total[5m])

# Connection pool exhaustion
(db_pool_connections_checked_out / db_pool_connections_total) > 0.9

# Replica lag
mysql_slave_lag_seconds > 5
```

---

## Best Practices

### DO ✅

1. **Always Use EXPLAIN**: Understand query execution plans
2. **Index Foreign Keys**: Essential for JOIN performance
3. **Use Composite Indexes**: Cover common multi-column queries
4. **Paginate Large Results**: Use keyset pagination
5. **Monitor Slow Queries**: Set up slow query logging
6. **Use Connection Pooling**: Reuse database connections
7. **Separate Read/Write**: Use read replicas for scaling
8. **Cache Aggressively**: Reduce database load

### DON'T ❌

1. **Don't Use SELECT \***: Fetch only needed columns
2. **Don't Over-Index**: Every index slows writes
3. **Don't Use OFFSET for Large Pages**: Use keyset pagination
4. **Don't Query in Loops**: Use batch queries or JOINs
5. **Don't Forget LIMIT**: Unbounded queries can kill performance
6. **Don't Ignore Covering Indexes**: Can eliminate table lookups
7. **Don't Trust ORM Blindly**: Review generated SQL

---

## Related Documents

- [Data Partitioning Strategy](./data-partitioning.md)
- [Caching Strategy](./caching.md)
- [Performance Targets](./performance.md)
- [Scalability Patterns](./scalability.md)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
