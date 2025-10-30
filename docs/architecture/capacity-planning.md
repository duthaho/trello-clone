# Capacity Planning

**Version**: 1.0.0  
**Last Updated**: 2025-10-30  
**Status**: Active

## Overview

This document defines capacity planning strategies for the Task Management System across three growth phases (0-10K, 10K-50K, 50K-100K users). It provides resource sizing formulas, cost projections, and scaling triggers to guide infrastructure investment decisions.

---

## Growth Phases

### Phase Overview

| Phase       | Users    | Projects  | Tasks     | Monthly Cost | Timeframe    |
| ----------- | -------- | --------- | --------- | ------------ | ------------ |
| **Phase 1** | 0-10K    | 0-50K     | 0-500K    | $400-800     | Months 1-12  |
| **Phase 2** | 10K-50K  | 50K-250K  | 500K-2.5M | $800-2,000   | Months 13-24 |
| **Phase 3** | 50K-100K | 250K-500K | 2.5M-5M   | $2,000-4,000 | Months 25-36 |

---

## Phase 1: MVP Launch (0-10K Users)

### Target Metrics

**Users**: 0-10,000 total users (1,000 concurrent peak)  
**Projects**: ~5 projects per user = 50,000 projects  
**Tasks**: ~10 tasks per project = 500,000 tasks  
**API Requests**: ~5,000 req/s peak  
**Database**: ~500 GB total data

### Infrastructure Sizing

#### Compute (API Layer)

```yaml
Service: AWS ECS Fargate
Instance Type: 2 vCPU, 4 GB RAM per container
Container Count: 4-8 (auto-scaling)
CPU Utilization: 60-70% average
Memory Utilization: 60-70% average

Auto-Scaling Policy:
  Target CPU: 70%
  Target Memory: 70%
  Scale Up: Add 2 containers when CPU > 70% for 2 minutes
  Scale Down: Remove 1 container when CPU < 40% for 5 minutes
  Min Containers: 4
  Max Containers: 8
```

**Reasoning**:

- 2 vCPU handles ~600 req/s per container
- 4 containers = 2,400 req/s baseline
- 8 containers = 4,800 req/s peak capacity
- 4 GB RAM sufficient for FastAPI + in-memory cache

#### Database (MySQL RDS)

```yaml
Service: AWS RDS MySQL 8.0
Instance Type: db.r6g.large (2 vCPU, 16 GB RAM)
Storage: 500 GB GP3 (3,000 IOPS, 125 MB/s throughput)
Backup Retention: 7 days
Multi-AZ: Yes (for high availability)
Read Replicas: 1 replica (same instance type)

Estimated Performance:
  Write Throughput: 2,000 QPS
  Read Throughput: 10,000 QPS (with replica)
  Query Latency p95: 30-50ms
```

**Reasoning**:

- 16 GB RAM = 12 GB buffer pool (holds ~240K rows of 50KB each)
- GP3 storage = consistent IOPS (no burst credits)
- Read replica offloads 70% of read queries from master

#### Cache (Redis ElastiCache)

```yaml
Service: AWS ElastiCache Redis 7.0
Instance Type: cache.r6g.large (2 vCPU, 13.07 GB RAM)
Node Count: 2 (primary + replica)
Eviction Policy: allkeys-lru
Persistence: No (cache only, not primary storage)

Estimated Capacity:
  Memory Available: 13 GB
  Cache Entries: ~2.5M entries at 5 KB average
  Hit Rate Target: 80-85%
  Latency p95: 1-3ms
```

**Reasoning**:

- 13 GB holds 12 hours of hot data (sessions, frequently accessed entities)
- Replica provides high availability (failover < 1 minute)

#### Message Queue (Celery + Redis)

```yaml
Service: Same Redis instance as cache (separate database)
Workers: 4 Celery workers (2 vCPU, 4 GB RAM each)
Concurrency: 4 threads per worker = 16 concurrent jobs
Queue Depth Target: < 100 messages

Worker Auto-Scaling:
  Scale Up: Queue depth > 50 for 2 minutes
  Scale Down: Queue depth < 10 for 5 minutes
  Min Workers: 4
  Max Workers: 8
```

**Reasoning**:

- Redis as broker handles 10K+ messages/second
- 16 concurrent workers process ~160 jobs/minute (10s avg job time)
- Separate Redis database prevents cache eviction

### Cost Breakdown (Phase 1)

| Component             | Instance                  | Count                 | Unit Cost        | Monthly Cost    |
| --------------------- | ------------------------- | --------------------- | ---------------- | --------------- |
| **ECS Fargate**       | 2 vCPU, 4 GB              | 4 avg                 | $30/month        | $120            |
| **RDS MySQL**         | db.r6g.large              | 1 master + 1 replica  | $150/month       | $300            |
| **ElastiCache Redis** | cache.r6g.large           | 1 primary + 1 replica | $120/month       | $240            |
| **ECS Workers**       | 2 vCPU, 4 GB              | 4 workers             | $30/month        | $120            |
| **ALB**               | Application Load Balancer | 1                     | $20/month + data | $40             |
| **S3**                | Attachments storage       | 50 GB                 | $0.023/GB        | $5              |
| **CloudWatch**        | Logs + Metrics            | -                     | -                | $25             |
| **Data Transfer**     | Outbound                  | 500 GB                | $0.09/GB         | $45             |
| **Backup**            | RDS snapshots             | 1 TB                  | $0.095/GB        | $50             |
| **Total**             |                           |                       |                  | **~$945/month** |

**Cost Per User**: $945 / 10,000 = **$0.09/user/month**

### Scaling Triggers (Phase 1 → Phase 2)

| Metric              | Threshold  | Action                    |
| ------------------- | ---------- | ------------------------- |
| **Active Users**    | > 8,000    | Prepare Phase 2 migration |
| **API p95 Latency** | > 300ms    | Scale API containers      |
| **DB CPU**          | > 70%      | Upgrade to db.r6g.xlarge  |
| **Cache Hit Rate**  | < 70%      | Increase cache size       |
| **Worker Queue**    | > 100 msgs | Add workers               |

---

## Phase 2: Growth (10K-50K Users)

### Target Metrics

**Users**: 10,000-50,000 total users (5,000 concurrent peak)  
**Projects**: 250,000 projects  
**Tasks**: 2,500,000 tasks  
**API Requests**: ~10,000 req/s peak  
**Database**: ~2 TB total data

### Infrastructure Sizing

#### Compute (API Layer)

```yaml
Service: AWS ECS Fargate
Instance Type: 4 vCPU, 8 GB RAM per container
Container Count: 8-16 (auto-scaling)
CPU Utilization: 60-70% average

Auto-Scaling Policy:
  Target CPU: 70%
  Min Containers: 8
  Max Containers: 16

Estimated Performance:
  Baseline: 8 containers × 1,200 req/s = 9,600 req/s
  Peak: 16 containers × 1,200 req/s = 19,200 req/s
```

**Changes from Phase 1**:

- 2× vCPU per container (4 vCPU vs. 2 vCPU)
- 2× memory per container (8 GB vs. 4 GB)
- 2× container count baseline (8 vs. 4)

#### Database (MySQL RDS)

```yaml
Service: AWS RDS MySQL 8.0
Instance Type: db.r6g.xlarge (4 vCPU, 32 GB RAM)
Storage: 2 TB GP3 (12,000 IOPS, 500 MB/s throughput)
Read Replicas: 2 replicas (same instance type)

Estimated Performance:
  Write Throughput: 5,000 QPS
  Read Throughput: 30,000 QPS (with 2 replicas)
  Query Latency p95: 30-50ms
  Buffer Pool: 24 GB (holds ~480K rows)
```

**Changes from Phase 1**:

- 2× CPU (4 vCPU vs. 2 vCPU)
- 2× RAM (32 GB vs. 16 GB)
- 4× storage (2 TB vs. 500 GB)
- +1 read replica (2 vs. 1)

#### Cache (Redis ElastiCache)

```yaml
Service: AWS ElastiCache Redis 7.0
Instance Type: cache.r6g.xlarge (4 vCPU, 26.32 GB RAM)
Cluster Mode: Enabled (2 shards)
Node Count: 4 (2 shards × 2 nodes each)

Estimated Capacity:
  Memory Available: 26 GB per shard × 2 = 52 GB total
  Cache Entries: ~10M entries
  Hit Rate Target: 85%
```

**Changes from Phase 1**:

- Cluster mode enabled (sharding for horizontal scaling)
- 4× memory (52 GB vs. 13 GB)
- 2× vCPU per node

#### Workers

```yaml
Service: AWS ECS Fargate
Instance Type: 4 vCPU, 8 GB RAM per worker
Worker Count: 8-16 (auto-scaling)
Concurrency: 8 threads per worker = 64-128 concurrent jobs

Auto-Scaling Policy:
  Scale Up: Queue depth > 100 for 2 minutes
  Scale Down: Queue depth < 20 for 5 minutes
  Min Workers: 8
  Max Workers: 16
```

### Cost Breakdown (Phase 2)

| Component             | Instance                  | Count                 | Monthly Cost      |
| --------------------- | ------------------------- | --------------------- | ----------------- |
| **ECS Fargate**       | 4 vCPU, 8 GB              | 8 avg                 | $480              |
| **RDS MySQL**         | db.r6g.xlarge             | 1 master + 2 replicas | $900              |
| **ElastiCache Redis** | cache.r6g.xlarge          | 4 nodes (2 shards)    | $960              |
| **ECS Workers**       | 4 vCPU, 8 GB              | 8 workers             | $480              |
| **ALB**               | Application Load Balancer | 1                     | $60               |
| **S3**                | Attachments storage       | 500 GB                | $15               |
| **CloudWatch**        | Logs + Metrics            | -                     | $75               |
| **Data Transfer**     | Outbound                  | 2 TB                  | $180              |
| **Backup**            | RDS snapshots             | 4 TB                  | $190              |
| **Total**             |                           |                       | **~$3,340/month** |

**Cost Per User**: $3,340 / 50,000 = **$0.067/user/month**

**Cost Efficiency**: 25% reduction per user due to economies of scale.

### Scaling Triggers (Phase 2 → Phase 3)

| Metric           | Threshold | Action                    |
| ---------------- | --------- | ------------------------- |
| **Active Users** | > 40,000  | Prepare Phase 3 migration |
| **DB CPU**       | > 70%     | Upgrade to db.r6g.2xlarge |
| **IOPS**         | > 10,000  | Increase GP3 IOPS         |
| **Cache Memory** | > 80%     | Add cache shards          |

---

## Phase 3: Scale (50K-100K Users)

### Target Metrics

**Users**: 50,000-100,000 total users (10,000 concurrent peak)  
**Projects**: 500,000 projects  
**Tasks**: 5,000,000 tasks  
**API Requests**: ~20,000 req/s peak  
**Database**: ~5 TB total data

### Infrastructure Sizing

#### Compute (API Layer)

```yaml
Service: AWS ECS Fargate
Instance Type: 8 vCPU, 16 GB RAM per container
Container Count: 16-32 (auto-scaling)

Estimated Performance:
  Baseline: 16 containers × 2,000 req/s = 32,000 req/s
  Peak: 32 containers × 2,000 req/s = 64,000 req/s
```

#### Database (MySQL RDS)

```yaml
Service: AWS RDS MySQL 8.0
Instance Type: db.r6g.2xlarge (8 vCPU, 64 GB RAM)
Storage: 5 TB GP3 (16,000 IOPS, 1,000 MB/s throughput)
Read Replicas: 3 replicas (same instance type)
Partitioning: Enabled (by organization_id, project_id, timestamp)

Estimated Performance:
  Write Throughput: 10,000 QPS
  Read Throughput: 60,000 QPS (with 3 replicas)
  Query Latency p95: 30-50ms
```

**Consideration**: If single master bottleneck, consider **sharding** by region or organization.

#### Cache (Redis ElastiCache)

```yaml
Service: AWS ElastiCache Redis 7.0
Instance Type: cache.r6g.2xlarge (8 vCPU, 52.82 GB RAM)
Cluster Mode: Enabled (4 shards)
Node Count: 8 (4 shards × 2 nodes each)

Estimated Capacity:
  Memory Available: 52 GB per shard × 4 = 208 GB total
  Cache Entries: ~40M entries
  Hit Rate Target: 85-90%
```

#### Workers

```yaml
Service: AWS ECS Fargate
Instance Type: 8 vCPU, 16 GB RAM per worker
Worker Count: 16-32 (auto-scaling)
Concurrency: 16 threads per worker = 256-512 concurrent jobs
```

### Cost Breakdown (Phase 3)

| Component             | Instance                  | Count                 | Monthly Cost       |
| --------------------- | ------------------------- | --------------------- | ------------------ |
| **ECS Fargate**       | 8 vCPU, 16 GB             | 16 avg                | $1,920             |
| **RDS MySQL**         | db.r6g.2xlarge            | 1 master + 3 replicas | $2,400             |
| **ElastiCache Redis** | cache.r6g.2xlarge         | 8 nodes (4 shards)    | $3,840             |
| **ECS Workers**       | 8 vCPU, 16 GB             | 16 workers            | $1,920             |
| **ALB**               | Application Load Balancer | 1                     | $100               |
| **S3**                | Attachments storage       | 2 TB                  | $50                |
| **CloudWatch**        | Logs + Metrics            | -                     | $150               |
| **Data Transfer**     | Outbound                  | 5 TB                  | $450               |
| **Backup**            | RDS snapshots             | 10 TB                 | $475               |
| **Total**             |                           |                       | **~$11,305/month** |

**Cost Per User**: $11,305 / 100,000 = **$0.113/user/month**

---

## Resource Scaling Formulas

### API Compute

**Formula**: `Containers = ceil(Peak_RPS / Throughput_Per_Container)`

**Variables**:

- `Peak_RPS`: Peak requests per second (from monitoring)
- `Throughput_Per_Container`: ~600 req/s for 2 vCPU, ~1,200 req/s for 4 vCPU, ~2,000 req/s for 8 vCPU
- Add 20% headroom for spikes

**Example**:

```
Peak_RPS = 10,000
Throughput_Per_Container = 1,200 (4 vCPU)
Containers = ceil(10,000 / 1,200) × 1.2 = 10 containers
```

### Database Sizing

**Formula**: `Buffer_Pool_Size = Working_Set_Size × 1.2`

**Working Set Size**:

- Active users × avg rows per user × row size
- Example: 10,000 users × 100 rows × 5 KB = 5 GB working set
- Buffer pool = 5 GB × 1.2 = 6 GB minimum

**Storage Formula**: `Storage = (Users × Rows_Per_User × Row_Size) × Growth_Factor`

**Example**:

```
Users = 50,000
Rows_Per_User = 200 (tasks, comments, notifications)
Row_Size = 5 KB average
Growth_Factor = 1.5 (50% headroom)

Storage = 50,000 × 200 × 5 KB × 1.5
        = 75 GB × 1.5
        = 112 GB minimum
```

### Cache Sizing

**Formula**: `Cache_Size = Hot_Data_Size × 1.3`

**Hot Data** (Phase 2 example):

- User sessions: 5,000 concurrent × 2 KB = 10 MB
- User profiles: 50,000 users × 5 KB = 250 MB
- Projects: 50,000 projects × 10 KB = 500 MB
- Task lists: 10,000 lists × 50 KB = 500 MB
- Aggregates: 50,000 × 1 KB = 50 MB
- **Total**: 1.3 GB × 1.3 (overhead) = **1.7 GB minimum**

Recommended: 4× hot data size for 80%+ hit rate = **7 GB**

### Worker Sizing

**Formula**: `Workers = ceil(Job_Rate × Avg_Job_Time / Concurrency_Per_Worker)`

**Example**:

```
Job_Rate = 100 jobs/minute = 1.67 jobs/second
Avg_Job_Time = 10 seconds
Concurrency_Per_Worker = 4 threads

Workers = ceil(1.67 × 10 / 4) = ceil(4.2) = 5 workers
```

Add 50% headroom for spikes: **8 workers**

---

## Cost Optimization Strategies

### 1. Reserved Instances

**Savings**: 30-50% for 1-year commitment

```yaml
Phase 2 Reserved Instances:
  RDS MySQL (db.r6g.xlarge):
    On-Demand: $300/month × 3 = $900
    1-Year Reserved: $180/month × 3 = $540
    Savings: $360/month (40%)

  ElastiCache (cache.r6g.xlarge):
    On-Demand: $240/month × 4 = $960
    1-Year Reserved: $150/month × 4 = $600
    Savings: $360/month (37%)

Total Savings: $720/month ($8,640/year)
```

### 2. Spot Instances for Workers

**Savings**: 70-90% for interruptible workloads

```yaml
Workers (Phase 2):
  On-Demand: $60/month × 8 = $480
  Spot Instances: $12/month × 8 = $96
  Savings: $384/month (80%)
```

**Caveat**: Only for fault-tolerant background jobs, not real-time tasks.

### 3. S3 Lifecycle Policies

```yaml
Attachments Storage:
  0-30 days: S3 Standard ($0.023/GB)
  30-90 days: S3 Infrequent Access ($0.0125/GB) → 45% savings
  90+ days: S3 Glacier ($0.004/GB) → 83% savings
```

**Example** (1 TB storage):

- Without lifecycle: $23/month
- With lifecycle (50% old): $23 × 0.5 + $12.50 × 0.3 + $4 × 0.2 = **$16.05/month**
- Savings: $7/month (30%)

### 4. Auto-Scaling Optimization

**Strategy**: Aggressive scale-down during off-peak hours.

```yaml
Weekday Schedule:
  06:00-18:00 (peak): 16 API containers
  18:00-06:00 (off-peak): 8 API containers
  Savings: 8 containers × 12 hours × 30 days = 2,880 container-hours/month

Weekend Schedule:
  00:00-24:00 (light): 6 API containers
  Savings: 10 containers × 48 hours = 480 container-hours/month

Total Savings: ~3,360 container-hours/month × $0.04/hour = $134/month
```

---

## Monitoring & Capacity Alerts

### Key Metrics

| Metric                 | Monitor         | Alert Threshold      | Action                   |
| ---------------------- | --------------- | -------------------- | ------------------------ |
| **CPU Utilization**    | ECS, RDS        | > 70% for 5 min      | Scale up                 |
| **Memory Utilization** | ECS, RDS, Redis | > 80% for 5 min      | Scale up                 |
| **Disk IOPS**          | RDS             | > 80% of provisioned | Increase IOPS            |
| **Connection Pool**    | RDS             | > 80% of max         | Increase max_connections |
| **Cache Hit Rate**     | Redis           | < 70%                | Increase cache size      |
| **API Latency p95**    | ALB             | > 300ms              | Scale API containers     |
| **Queue Depth**        | Celery          | > 100 messages       | Add workers              |

### Capacity Planning Dashboard

```python
# Prometheus queries for capacity planning

# API container utilization
sum(rate(container_cpu_usage_seconds_total[5m])) by (service) / sum(container_spec_cpu_quota) by (service)

# Database connection pool usage
mysql_global_status_threads_connected / mysql_global_variables_max_connections

# Cache memory usage
redis_memory_used_bytes / redis_memory_max_bytes

# Projected time to capacity
predict_linear(
    mysql_global_status_threads_connected[1h],
    4 * 3600  # 4 hours ahead
) > (mysql_global_variables_max_connections * 0.8)
```

---

## Growth Projections

### User Growth Assumptions

| Phase       | Users      | Monthly Growth | Timeframe |
| ----------- | ---------- | -------------- | --------- |
| **Phase 1** | 0 → 10K    | +1,000/month   | 10 months |
| **Phase 2** | 10K → 50K  | +3,000/month   | 13 months |
| **Phase 3** | 50K → 100K | +4,000/month   | 12 months |

### Cost Growth Projection

```
Phase 1 (Month 10): $945/month → $0.09/user
Phase 2 (Month 23): $3,340/month → $0.067/user
Phase 3 (Month 35): $11,305/month → $0.113/user

3-Year Total Cost: $196,000
3-Year Average Cost per User: ~$0.08/user/month
```

### Revenue Requirements (Break-Even)

**Assumptions**:

- Infrastructure cost: $0.08/user/month
- Support & operations: $0.05/user/month
- Development & overhead: $0.07/user/month
- **Total cost**: $0.20/user/month

**Pricing**:

- Free tier: 1-5 users (loss leader)
- Pro tier: $10/user/month → 50× cost margin
- Enterprise tier: $20/user/month → 100× cost margin

**Break-Even**:

- 1,000 paying users × $10 = $10,000/month revenue
- 1,000 paying users × $0.20 = $200/month cost
- **Break-even at 2% paid conversion**

---

## Disaster Recovery & Capacity

### RTO/RPO Targets

| Data Type          | RPO (Data Loss) | RTO (Recovery Time) | Strategy                         |
| ------------------ | --------------- | ------------------- | -------------------------------- |
| **User Data**      | < 1 hour        | < 4 hours           | Automated snapshots every 30 min |
| **Tasks/Projects** | < 1 hour        | < 4 hours           | Automated snapshots every 30 min |
| **Audit Logs**     | < 24 hours      | < 8 hours           | Daily snapshots + S3 archival    |
| **Attachments**    | < 24 hours      | < 1 hour            | S3 versioning enabled            |

### DR Capacity

**Warm Standby** (different region):

- 50% capacity of primary region
- Automatic failover if primary region unavailable
- Additional cost: ~$5,000/month for Phase 3

**Cold Backup** (S3):

- Daily database exports to S3
- Weekly full backups
- Additional cost: ~$200/month for Phase 3

---

## Related Documents

- [Scalability Patterns](./scalability.md)
- [Performance Targets](./performance.md)
- [Data Partitioning](./data-partitioning.md)
- [Database Optimization](./database-optimization.md)

---

**Last Reviewed**: 2025-10-30  
**Next Review**: 2026-01-30 (Quarterly)
