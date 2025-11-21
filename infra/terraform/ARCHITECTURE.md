# Aplicación Señas - AWS Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 INTERNET                                     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 │ HTTPS/HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LOAD BALANCER                            │
│  - Health checks: /health                                                    │
│  - Path routing: /content → content-service                                  │
│                  /users   → user-service                                     │
│                  /ml      → ml-service                                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              VPC (10.0.0.0/16)                                │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PUBLIC SUBNETS (2-3 AZs)                         │    │
│  │  - NAT Gateways                                                      │    │
│  │  - Internet Gateway                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   PRIVATE SUBNETS (2-3 AZs)                         │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │    │
│  │  │  ECS FARGATE     │  │  ECS FARGATE     │  │  ECS FARGATE    │  │    │
│  │  │                  │  │                  │  │                 │  │    │
│  │  │ Content Service  │  │  User Service    │  │  ML Service     │  │    │
│  │  │  Port: 8000      │  │  Port: 8001      │  │  Port: 8002     │  │    │
│  │  │  CPU: 256-512    │  │  CPU: 256-512    │  │  CPU: 512-1024  │  │    │
│  │  │  Memory: 512-1024│  │  Memory: 512-1024│  │  Memory: 1-2GB  │  │    │
│  │  │                  │  │                  │  │                 │  │    │
│  │  │  [PostgreSQL]────┼──┼──────────────────┼──┼─────────┐       │  │    │
│  │  │  [DynamoDB]      │  │  [DynamoDB]      │  │ [DynamoDB]      │  │    │
│  │  │  [S3]            │  │  [S3]            │  │ [S3]            │  │    │
│  │  │  [SQS/SNS]       │  │  [SQS/SNS]       │  │ [SQS/SNS]       │  │    │
│  │  │  [Cognito]       │  │  [Cognito]       │  │ [SageMaker]     │  │    │
│  │  └──────────────────┘  └──────────────────┘  └─────────────────┘  │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   DATABASE SUBNETS (2-3 AZs)                        │    │
│  │                                                                      │    │
│  │  ┌────────────────────────────────────────────────────────────┐    │    │
│  │  │        RDS AURORA SERVERLESS V2 (PostgreSQL 15.4)          │    │    │
│  │  │  - Cluster Endpoint: content_db                             │    │    │
│  │  │  - Min Capacity: 0.5-1 ACU (dev) / 1 ACU (prod)            │    │    │
│  │  │  - Max Capacity: 1-2 ACU (dev) / 4 ACU (prod)              │    │    │
│  │  │  - Backups: 3-14 days retention                             │    │    │
│  │  │  - Encryption: AES-256                                       │    │    │
│  │  └────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           AWS MANAGED SERVICES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  DynamoDB   │  │     S3      │  │    SQS      │  │    SNS      │        │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤        │
│  │ UserData    │  │ content-    │  │ video-      │  │ achievement │        │
│  │ UserProgress│  │  assets     │  │  processing │  │  -notifs    │        │
│  │ AiSessions  │  │ user-       │  │ ml-         │  │ level-      │        │
│  │             │  │  uploads    │  │  inference  │  │  completion │        │
│  │ PAY_PER_    │  │ ml-models   │  │             │  │ system-     │        │
│  │  REQUEST    │  │ video-      │  │ + DLQs      │  │  alerts     │        │
│  │             │  │  processing │  │             │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Cognito   │  │     ECR     │  │     IAM     │  │  Secrets    │        │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤        │
│  │ User Pool   │  │ content-    │  │ ECS         │  │ RDS         │        │
│  │ MFA: Optional│  │  service    │  │  Execution  │  │  Credentials│        │
│  │  (dev)      │  │ user-       │  │  Role       │  │             │        │
│  │ MFA: ON     │  │  service    │  │ ECS Task    │  │             │        │
│  │  (prod)     │  │ ml-service  │  │  Role       │  │             │        │
│  │             │  │             │  │  (scoped)   │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        TERRAFORM STATE MANAGEMENT                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  S3 Bucket: aplicacion-senas-terraform-state                                 │
│  - Versioning: Enabled                                                       │
│  - Encryption: AES-256                                                       │
│                                                                               │
│  DynamoDB Table: aplicacion-senas-terraform-locks                            │
│  - Prevents concurrent modifications                                         │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY & NETWORKING                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ✓ VPC Flow Logs → CloudWatch (prod only)                                   │
│  ✓ Security Groups: Least privilege (ECS ← ALB only)                        │
│  ✓ Private subnets for compute and database                                 │
│  ✓ NAT Gateway for outbound internet (AWS API calls)                        │
│  ✓ Encryption at rest: RDS, S3, DynamoDB, SQS, SNS                          │
│  ✓ Encryption in transit: TLS on ALB                                        │
│  ✓ IAM roles with scoped permissions (no wildcards)                         │
│  ✓ Secrets Manager for database credentials                                 │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONITORING & OBSERVABILITY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  • CloudWatch Logs: ECS task logs, RDS logs                                 │
│  • CloudWatch Metrics: CPU, Memory, Request Count                           │
│  • Container Insights: ECS cluster metrics (prod)                           │
│  • ECS Auto Scaling: Target tracking (CPU 70%, Memory 80%)                  │
│  • ALB Access Logs: Optional (can enable to S3)                             │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          DEPLOYMENT PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. GitHub Actions: Build Docker images                                     │
│  2. Push to ECR: tag with commit SHA                                        │
│  3. Terraform Apply: Update ECS task definitions                            │
│  4. ECS Rolling Update: Zero-downtime deployment                            │
│  5. Health Checks: ALB verifies /health endpoint                            │
│  6. Run Migrations: Alembic via bastion/VPN                                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Resource Sizing

| Service | Dev | Prod |
|---------|-----|------|
| **VPC AZs** | 2 | 3 |
| **NAT Gateways** | 1 (single) | 3 (per-AZ) |
| **ECS Tasks** | 3 (1 per service) | 5 (2 content, 2 user, 1 ml) |
| **RDS ACU Min** | 0.5 | 1 |
| **RDS ACU Max** | 1-2 | 4 |
| **RDS Backups** | 3 days | 14 days |
| **DynamoDB PITR** | Disabled | Enabled |
| **S3 Lifecycle** | None | 90 days |
| **Cognito MFA** | Optional | ON |
| **Container Insights** | Disabled | Enabled |

## Data Flow Examples

### Content Retrieval Flow
```
User → ALB → content-service → RDS Aurora → S3 (media) → User
```

### User Progress Tracking Flow
```
User → ALB → user-service → DynamoDB (UserProgress) → SNS (achievement) → User
```

### ML Inference Flow
```
User → ALB → ml-service → SQS (ml-inference) → SageMaker → DynamoDB (AiSessions) → User
```

### Video Processing Flow
```
User → ALB → content-service → S3 (user-uploads) → SQS (video-processing) → ml-service → S3 (processed) → User
```
