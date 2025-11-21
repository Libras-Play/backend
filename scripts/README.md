# Active Scripts Documentation

This directory contains actively maintained scripts for LibrasPlay deployment and operations.

⚠️ **DO NOT use scripts from `/archive_private`** - they are deprecated.

---

## 📋 Available Scripts

### 🔨 Build and Deployment

#### `build-and-push-images.sh`
**Purpose**: Build Docker images for all services and push to ECR

**Usage**:
```bash
./build-and-push-images.sh [TAG]
```

**Examples**:
```bash
# Build with latest tag
./build-and-push-images.sh

# Build with specific version
./build-and-push-images.sh v1.2.3

# Build specific service
./build-and-push-images.sh latest content-service
```

**Prerequisites**:
- AWS CLI configured
- Docker running
- ECR repositories created
- Execute `./ecr-login.sh` first

**Output**: Pushes images to ECR with tags

---

#### `ecr-login.sh`
**Purpose**: Authenticate Docker with AWS ECR

**Usage**:
```bash
./ecr-login.sh [REGION]
```

**Examples**:
```bash
# Login to us-east-1 (default)
./ecr-login.sh

# Login to specific region
./ecr-login.sh us-west-2
```

**Prerequisites**:
- AWS CLI configured with ECR permissions
- Docker running

**Output**: Docker logged in to ECR registry

---

#### `safe_deploy.sh`
**Purpose**: Safely deploy services to ECS with health checks and rollback

**Usage**:
```bash
./safe_deploy.sh [ENVIRONMENT] [SERVICE]
```

**Examples**:
```bash
# Deploy all services to dev
./safe_deploy.sh dev

# Deploy specific service to production
./safe_deploy.sh prod user-service

# Deploy with custom image tag
TAG=v1.2.3 ./safe_deploy.sh prod
```

**Features**:
- ✅ Pre-deployment health checks
- ✅ Rolling deployment
- ✅ Post-deployment verification
- ✅ Automatic rollback on failure
- ✅ Slack notifications (if configured)

**Prerequisites**:
- ECS cluster and services exist
- Images already pushed to ECR
- Proper IAM permissions for ECS

---

### 🧪 Testing and Validation

#### `smoke-test-production.sh`
**Purpose**: Run comprehensive smoke tests against production environment

**Usage**:
```bash
./smoke-test-production.sh [ALB_URL]
```

**Examples**:
```bash
# Test using default ALB URL
./smoke-test-production.sh

# Test specific ALB
./smoke-test-production.sh https://libras-play-alb-123456789.us-east-1.elb.amazonaws.com
```

**Tests Performed**:
- ✅ Service health endpoints
- ✅ Authentication flow
- ✅ Database connectivity
- ✅ API functionality
- ✅ Response times
- ✅ Error handling

**Output**: 
- Detailed test results
- Performance metrics
- Pass/Fail status
- Logs saved to `/tmp/smoke-test-TIMESTAMP.log`

---

#### `smoke-test-simple.sh`
**Purpose**: Quick health check of all services

**Usage**:
```bash
./smoke-test-simple.sh [BASE_URL]
```

**Examples**:
```bash
# Test local development
./smoke-test-simple.sh http://localhost:8000

# Test production ALB
./smoke-test-simple.sh https://api.librasplay.com
```

**Tests**:
- ✅ `/health` endpoints
- ✅ HTTP status codes
- ✅ Response times < 5s

---

#### `acceptance-test-simple.sh`
**Purpose**: Run acceptance tests for key user flows

**Usage**:
```bash
./acceptance-test-simple.sh [ENVIRONMENT]
```

**Examples**:
```bash
# Test dev environment
./acceptance-test-simple.sh dev

# Test production
./acceptance-test-simple.sh prod
```

**User Flows Tested**:
- ✅ User registration and login
- ✅ Lives consumption and regeneration
- ✅ XP earning and leveling up
- ✅ Badge earning
- ✅ Streak tracking
- ✅ Daily missions

---

### 🔍 Validation and Debugging

#### `validate_ecr_repo.sh`
**Purpose**: Validate ECR repositories exist and have correct permissions

**Usage**:
```bash
./validate_ecr_repo.sh [REPOSITORY_NAME]
```

**Examples**:
```bash
# Validate all repositories
./validate_ecr_repo.sh

# Validate specific repository
./validate_ecr_repo.sh libras-play-content-service
```

**Checks**:
- ✅ Repository exists
- ✅ Push/pull permissions
- ✅ Lifecycle policies configured
- ✅ Image scan settings
- ✅ Recent images present

---

#### `seed_mission_templates.py`
**Purpose**: Seed daily mission templates into database

**Usage**:
```bash
python seed_mission_templates.py [ENVIRONMENT]
```

**Examples**:
```bash
# Seed dev environment
python seed_mission_templates.py dev

# Seed production (requires approval)
python seed_mission_templates.py prod --confirm
```

**What it does**:
- ✅ Creates default mission templates
- ✅ Sets up Portuguese and Spanish missions
- ✅ Configures XP rewards and requirements
- ✅ Validates data before insertion

**Prerequisites**:
- Database access configured
- Python environment with dependencies
- Proper environment variables set

---

## 🚦 Script Usage Patterns

### Typical Deployment Workflow

```bash
# 1. Login to ECR
./ecr-login.sh

# 2. Build and push new images
./build-and-push-images.sh v1.2.3

# 3. Deploy safely
./safe_deploy.sh prod

# 4. Run smoke tests
./smoke-test-production.sh

# 5. Run acceptance tests
./acceptance-test-simple.sh prod
```

### Local Development Workflow

```bash
# 1. Start local services with docker-compose
cd ..
docker-compose up --build

# 2. Test local services
./smoke-test-simple.sh http://localhost:8000

# 3. Run acceptance tests locally
./acceptance-test-simple.sh local
```

### Emergency Rollback Workflow

```bash
# 1. Check current deployment status
aws ecs describe-services --cluster libras-play-prod-cluster --services content-service user-service ml-service

# 2. Rollback to previous task definition
aws ecs update-service --cluster libras-play-prod-cluster --service content-service --task-definition content-service:PREVIOUS-REVISION

# 3. Verify rollback successful
./smoke-test-production.sh

# 4. Investigate issue
aws logs tail /ecs/content-service --follow
```

---

## 🔧 Configuration

### Environment Variables

Scripts read configuration from environment variables and `.env` files:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=123456789012

# ECS Configuration  
export ECS_CLUSTER_NAME=libras-play-dev-cluster
export CONTENT_SERVICE_NAME=content-service
export USER_SERVICE_NAME=user-service
export ML_SERVICE_NAME=ml-service

# ALB Configuration
export ALB_URL=https://libras-play-alb-123456789.us-east-1.elb.amazonaws.com

# Notification Configuration (optional)
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export NOTIFICATION_EMAIL=ops@librasplay.com
```

### Script Defaults

If not specified, scripts use these defaults:

- **AWS Region**: `us-east-1`
- **Environment**: `dev`
- **Image Tag**: `latest`
- **ECS Cluster**: `libras-play-${ENVIRONMENT}-cluster`
- **Timeout**: 300 seconds
- **Retry Count**: 3

---

## 🔒 Security Considerations

### Secrets Management

Scripts **DO NOT** contain hardcoded secrets. They retrieve sensitive data from:

- **AWS Secrets Manager**: Database passwords, API keys
- **Environment Variables**: Non-sensitive configuration
- **AWS Parameter Store**: Application configuration
- **IAM Roles**: AWS service authentication

### Permission Requirements

Scripts require appropriate IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:UpdateService",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow", 
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/ecs/*"
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: `./script.sh: Permission denied`

**Solution**: 
```bash
chmod +x scripts/*.sh
```

**Issue**: ECR login fails with "no basic auth credentials"

**Solution**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Re-login to ECR
./ecr-login.sh
```

**Issue**: ECS deployment hangs

**Solution**:
```bash
# Check service events
aws ecs describe-services --cluster CLUSTER --services SERVICE --query 'services[0].events'

# Check CloudWatch logs
aws logs tail /ecs/SERVICE-NAME --follow
```

**Issue**: Smoke tests fail with connection timeout

**Solution**:
```bash
# Check ALB target group health
aws elbv2 describe-target-health --target-group-arn TARGET-GROUP-ARN

# Check security groups allow traffic
aws ec2 describe-security-groups --group-ids sg-XXXXXXXX
```

---

## 📊 Monitoring and Logging

### Script Execution Logs

All scripts generate logs in `/tmp/` with timestamps:

```bash
# View recent script execution logs  
ls -la /tmp/*libras-play* | tail -10

# Monitor real-time logs
tail -f /tmp/safe-deploy-$(date +%Y%m%d).log
```

### CloudWatch Integration

Scripts push metrics and logs to CloudWatch:

- **Deployment Success/Failure**: Custom metrics
- **Test Results**: CloudWatch Insights
- **Performance Metrics**: Response times, error rates

### Slack Notifications

If configured, scripts send notifications to Slack:

```bash
# Set Slack webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Scripts automatically notify on:
# ✅ Successful deployments
# ❌ Failed deployments  
# ⚠️ Test failures
# 📊 Performance degradations
```

---

## 🔄 Maintenance

### Script Updates

When updating scripts:

1. **Test in development** environment first
2. **Update documentation** if behavior changes
3. **Maintain backward compatibility** when possible
4. **Version script changes** in git commits
5. **Notify team** of breaking changes

### Adding New Scripts

Follow this template for new scripts:

```bash
#!/bin/bash
# script-name.sh - Brief description
#
# Usage: ./script-name.sh [OPTIONS]
# 
# Author: Your Name
# Date: YYYY-MM-DD

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-dev}"

# Logging
LOG_FILE="/tmp/$(basename $0 .sh)-$(date +%Y%m%d_%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo "Starting $(basename $0) at $(date)"

# Your script logic here

echo "Completed $(basename $0) at $(date)"
```

---

## 📞 Support

For script-related issues:

1. **Check logs** in `/tmp/` directory
2. **Verify AWS permissions** and configuration
3. **Test in development** before production use
4. **Create GitHub issue** with logs and error details
5. **Contact team** via ops@librasplay.com for urgent issues

---

## 📚 References

- **AWS ECS CLI**: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI.html
- **Docker CLI**: https://docs.docker.com/engine/reference/commandline/cli/
- **Bash Best Practices**: https://google.github.io/styleguide/shellguide.html
- **AWS CLI**: https://docs.aws.amazon.com/cli/latest/userguide/

---

**Last Updated**: 2025-11-20  
**Maintained By**: LibrasPlay DevOps Team  
**Next Review**: 2025-12-20