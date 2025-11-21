# AWS Deployment Guide

This is an **example** deployment guide for AWS. You can adapt this for your cloud provider of choice.

⚠️ **Note**: This guide contains AWS-specific configurations as an example. Replace account IDs, regions, and other specifics with your own values.

---

## 📋 Prerequisites

### Required Tools
- **AWS CLI** 2.0+ configured with appropriate IAM permissions
- **Terraform** 1.5+
- **Docker** 20.10+ for building images
- **ECR access** to push container images

### Required AWS Permissions
Your IAM user/role needs permissions for:
- ECS (clusters, services, task definitions)
- RDS (instances, security groups)
- DynamoDB (tables, indexes)
- ECR (repositories, image pushing)
- VPC (subnets, security groups, load balancers)
- IAM (roles, policies)
- Secrets Manager (create/read secrets)
- CloudWatch (log groups, metrics)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                Internet Gateway                  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────┐
│              Application Load Balancer           │
│         (libras-play-dev-alb)                   │
└─────┬──────────────┬──────────────┬─────────────┘
      │              │              │
┌─────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│ Content    │ │ User       │ │ ML         │
│ Service    │ │ Service    │ │ Service    │
│ (ECS)      │ │ (ECS)      │ │ (ECS)      │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │
      │              │              │
┌─────▼──────┐       │        ┌─────▼──────┐
│ RDS        │       │        │ S3 Bucket  │
│ PostgreSQL │       │        │ (videos,   │
│            │       │        │  models)   │
└────────────┘       │        └────────────┘
                     │
               ┌─────▼──────┐
               │ DynamoDB   │
               │ (7 tables) │
               └────────────┘
```

---

## 🚀 Deployment Steps

### Step 1: Configure AWS Credentials

```bash
# Configure AWS CLI (if not done)
aws configure

# Verify access
aws sts get-caller-identity
aws ecr describe-repositories --region us-east-1
```

### Step 2: Set Up Terraform Backend

⚠️ **IMPORTANT**: Store Terraform state in S3, not locally.

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket YOUR-TERRAFORM-STATE-BUCKET \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket YOUR-TERRAFORM-STATE-BUCKET \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name YOUR-TERRAFORM-LOCKS-TABLE \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 3: Configure Terraform Variables

```bash
cd infra/terraform

# Copy and customize terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# terraform.tfvars
# ⚠️ DO NOT COMMIT THIS FILE WITH REAL VALUES

# Basic Configuration
project_name = "libras-play"
environment  = "dev"  # or "staging", "prod"
region      = "us-east-1"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# Database Configuration (RDS)
db_instance_class = "db.t3.micro"  # Use larger for production
db_allocated_storage = 20
db_max_allocated_storage = 100

# ECS Configuration
ecs_cpu    = 256   # 0.25 vCPU
ecs_memory = 512   # 512 MB
ecs_desired_count = 1  # Number of instances per service

# Domain Configuration (optional)
domain_name = "api.yourapp.com"  # Leave empty for ALB DNS
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc123..."

# Tags
tags = {
  Project     = "LibrasPlay"
  Environment = "dev"
  ManagedBy   = "Terraform"
}
```

### Step 4: Initialize Terraform

```bash
cd infra/terraform

# Initialize with remote backend
terraform init

# Plan infrastructure changes
terraform plan -out=tfplan

# Review the plan carefully before applying
terraform show tfplan

# Apply changes
terraform apply tfplan
```

### Step 5: Set Up Secrets Manager

⚠️ **CRITICAL**: Store all database credentials in AWS Secrets Manager, not environment variables.

```bash
# Create database secret for Content Service
aws secretsmanager create-secret \
  --name libras-play/dev/content-service/db \
  --description "Content Service Database Credentials" \
  --secret-string '{
    "username": "postgres",
    "password": "YOUR-SECURE-PASSWORD-HERE",
    "host": "REPLACE-WITH-RDS-ENDPOINT",
    "port": 5432,
    "database": "content_db"
  }' \
  --region us-east-1

# Create database secret for User Service
aws secretsmanager create-secret \
  --name libras-play/dev/user-service/db \
  --description "User Service Database Credentials" \
  --secret-string '{
    "username": "postgres", 
    "password": "YOUR-SECURE-PASSWORD-HERE",
    "host": "REPLACE-WITH-RDS-ENDPOINT",
    "port": 5432,
    "database": "user_db"
  }' \
  --region us-east-1

# Create Cognito configuration secret
aws secretsmanager create-secret \
  --name libras-play/dev/cognito/config \
  --description "Cognito Configuration" \
  --secret-string '{
    "user_pool_id": "REPLACE-WITH-COGNITO-USER-POOL-ID",
    "client_id": "REPLACE-WITH-COGNITO-CLIENT-ID",
    "region": "us-east-1"
  }' \
  --region us-east-1
```

### Step 6: Build and Push Docker Images

```bash
# Navigate to scripts directory
cd scripts/

# Login to ECR
./ecr-login.sh

# Build and push all images
./build-and-push-images.sh

# Verify images were pushed
aws ecr list-images --repository-name libras-play-content-service --region us-east-1
aws ecr list-images --repository-name libras-play-user-service --region us-east-1
aws ecr list-images --repository-name libras-play-ml-service --region us-east-1
```

### Step 7: Deploy Services to ECS

ECS services are created by Terraform, but you need to update task definitions with the correct image URIs.

```bash
# Get ECR repository URIs (replace account ID)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

CONTENT_IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/libras-play-content-service:latest"
USER_IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/libras-play-user-service:latest"
ML_IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/libras-play-ml-service:latest"

echo "Content Service Image: $CONTENT_IMAGE"
echo "User Service Image: $USER_IMAGE"  
echo "ML Service Image: $ML_IMAGE"
```

Update your `terraform.tfvars` with these image URIs and re-run Terraform:

```hcl
# Add to terraform.tfvars
content_service_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/libras-play-content-service:latest"
user_service_image    = "123456789012.dkr.ecr.us-east-1.amazonaws.com/libras-play-user-service:latest"
ml_service_image      = "123456789012.dkr.ecr.us-east-1.amazonaws.com/libras-play-ml-service:latest"
```

```bash
# Apply updated configuration
terraform plan -out=tfplan
terraform apply tfplan
```

### Step 8: Run Database Migrations

```bash
# Connect to Content Service container to run migrations
CLUSTER_NAME="libras-play-dev-cluster"
SERVICE_NAME="content-service"

# Run Alembic migrations
aws ecs execute-command \
  --cluster $CLUSTER_NAME \
  --task "TASK-ID-HERE" \
  --container content-service \
  --interactive \
  --command "/bin/bash"

# Inside container:
# cd /app && alembic upgrade head
```

Or use ECS Run Task for migrations:

```bash
# Create migration task definition (one-time)
aws ecs run-task \
  --cluster libras-play-dev-cluster \
  --task-definition content-service-migration \
  --launch-type FARGATE \
  --network-configuration 'awsvpcConfiguration={subnets=["subnet-xxx","subnet-yyy"],securityGroups=["sg-zzz"],assignPublicIp=DISABLED}'
```

### Step 9: Verify Deployment

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names libras-play-dev-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "Application Load Balancer: $ALB_DNS"

# Test endpoints
curl http://$ALB_DNS/content/health
curl http://$ALB_DNS/users/health  
curl http://$ALB_DNS/ml/health

# Test API documentation
echo "Content API Docs: http://$ALB_DNS/content/docs"
echo "User API Docs: http://$ALB_DNS/users/docs"
echo "ML API Docs: http://$ALB_DNS/ml/docs"
```

---

## 🔐 Security Best Practices

### Secrets Management

✅ **DO**:
- Store all secrets in AWS Secrets Manager
- Use IAM roles for ECS tasks (not access keys)
- Enable encryption at rest for RDS and DynamoDB
- Use VPC private subnets for services
- Enable CloudTrail for audit logging

❌ **DON'T**:
- Put secrets in environment variables
- Commit credentials to git
- Use root AWS account for deployments
- Expose databases to public internet

### Network Security

```hcl
# Example security group (Terraform)
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-ecs-tasks"
  vpc_id      = aws_vpc.main.id

  # Allow inbound traffic from ALB only
  ingress {
    from_port       = 8000
    to_port         = 8003
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow outbound traffic (for AWS API calls)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### IAM Policies

Least privilege principle for ECS task execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:libras-play/dev/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem", 
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/user_progress_dev",
        "arn:aws:dynamodb:us-east-1:123456789012:table/user_lives_dev"
      ]
    }
  ]
}
```

---

## 📊 Monitoring and Logging

### CloudWatch Configuration

```bash
# View ECS service logs
aws logs tail /ecs/content-service --follow --region us-east-1
aws logs tail /ecs/user-service --follow --region us-east-1

# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "LibrasPlay-Dev" \
  --dashboard-body file://cloudwatch-dashboard.json
```

### Key Metrics to Monitor

- **ECS**: CPU utilization, memory utilization, task count
- **RDS**: CPU utilization, database connections, free storage space
- **DynamoDB**: Consumed read/write capacity, throttled requests
- **ALB**: Request count, response time, 5XX errors

### Alarms

```bash
# Example: High CPU alarm for ECS service
aws cloudwatch put-metric-alarm \
  --alarm-name "LibrasPlay-ContentService-HighCPU" \
  --alarm-description "Content Service CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value=content-service Name=ClusterName,Value=libras-play-dev-cluster \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:libras-play-alerts
```

---

## 🔄 CI/CD Integration

### GitHub Actions Deployment

See `.github/workflows/deploy.yml` for automated deployment:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
          
      - name: Build and push images
        run: ./scripts/build-and-push-images.sh
        
      - name: Deploy to ECS
        run: ./scripts/safe_deploy.sh
```

### Manual Deployment Script

```bash
# Use safe deployment script
./scripts/safe_deploy.sh

# This script:
# 1. Builds and pushes new images
# 2. Updates ECS task definitions
# 3. Performs rolling deployment
# 4. Runs health checks
# 5. Rolls back if deployment fails
```

---

## 🚨 Troubleshooting

### Common Issues

**Issue**: ECS service won't start, tasks keep stopping

**Solution**: Check CloudWatch logs and task definition configuration:
```bash
# Check service events
aws ecs describe-services \
  --cluster libras-play-dev-cluster \
  --services content-service \
  --query 'services[0].events'

# Check task logs
aws logs tail /ecs/content-service --follow
```

**Issue**: Database connection errors

**Solution**: Verify Secrets Manager configuration and security groups:
```bash
# Test secret retrieval
aws secretsmanager get-secret-value \
  --secret-id libras-play/dev/content-service/db

# Check RDS endpoint
aws rds describe-db-instances \
  --db-instance-identifier libras-play-dev-rds \
  --query 'DBInstances[0].Endpoint'
```

**Issue**: ALB health checks failing

**Solution**: Ensure services are listening on correct ports and paths:
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:...

# Test service directly (from within VPC)
curl http://TASK-IP:8001/content/health
```

---

## 💰 Cost Optimization

### Development Environment

Recommended configuration for development:

- **RDS**: db.t3.micro (burstable)
- **ECS**: 256 CPU / 512 MB memory per service
- **DynamoDB**: On-demand billing mode
- **No NAT Gateway**: Use VPC endpoints for AWS services

### Production Environment

Recommended configuration for production:

- **RDS**: db.t3.small or larger with Multi-AZ
- **ECS**: 512+ CPU / 1024+ MB memory per service
- **DynamoDB**: Provisioned mode with auto-scaling
- **CloudFront**: CDN for static assets

### Estimated Monthly Costs

| Component | Development | Production |
|-----------|-------------|------------|
| ECS Fargate (3 services) | $30-40 | $120-200 |
| RDS PostgreSQL | $15-20 | $50-100 |
| DynamoDB | $5-10 | $20-50 |
| ALB + Data Transfer | $20-25 | $50-100 |
| Other (CloudWatch, S3) | $5-10 | $20-40 |
| **Total** | **$75-105** | **$260-490** |

---

## 🔄 Updates and Maintenance

### Updating Services

```bash
# 1. Build new images with version tags
./scripts/build-and-push-images.sh v1.2.3

# 2. Update Terraform variables
# terraform.tfvars:
# content_service_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/libras-play-content-service:v1.2.3"

# 3. Apply Terraform changes
terraform plan -out=tfplan
terraform apply tfplan

# 4. Monitor deployment
./scripts/smoke-test-production.sh
```

### Database Migrations

```bash
# Run migrations during deployment
./scripts/run-migrations.sh

# Or manually via ECS exec
aws ecs execute-command \
  --cluster libras-play-dev-cluster \
  --task TASK-ID \
  --container content-service \
  --interactive \
  --command "alembic upgrade head"
```

---

## 📚 Additional Resources

- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **ECS Best Practices**: https://aws.amazon.com/blogs/containers/
- **RDS Security**: https://docs.aws.amazon.com/rds/latest/userguide/CHAP_BestPractices.Security.html
- **DynamoDB Best Practices**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html

---

## 🆘 Support

If you encounter issues with AWS deployment:

1. **Check CloudWatch logs** for detailed error messages
2. **Review security group** configurations
3. **Verify IAM permissions** for ECS task execution role
4. **Validate Secrets Manager** configuration
5. **Contact AWS Support** for infrastructure issues

**Emergency Contact**: ops@librasplay.com

---

**Last Updated**: 2025-11-20  
**Terraform Version**: 1.5+  
**AWS Provider Version**: 5.0+

---

⚠️ **REMEMBER**: 
- Never commit real credentials
- Always test in development first
- Use least privilege IAM policies
- Monitor costs regularly
- Keep infrastructure as code in version control