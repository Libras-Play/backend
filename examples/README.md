# Examples and Templates

This directory contains example configuration files and templates for LibrasPlay.

⚠️ **DO NOT USE THESE FILES DIRECTLY** - Copy and customize them for your environment.

---

## 📁 Files

### Environment Variables Templates

#### `content-service.env.template`
Template for Content Service environment variables.
- **Copy to**: `services/content-service/.env`
- **Contains**: Database URL, AWS config, CORS settings
- **Used by**: Content service for educational content and PostgreSQL

#### `user-service.env.template`
Template for User Service environment variables.
- **Copy to**: `services/user-service/.env`
- **Contains**: Database URL, DynamoDB tables, Cognito config, service URLs
- **Used by**: User service for user data and progress tracking

#### `ml-service.env.template`
Template for ML Service environment variables.
- **Copy to**: `services/ml-service/.env`
- **Contains**: S3 bucket, model paths, processing settings
- **Used by**: ML service for sign language recognition

### Infrastructure Templates

#### `terraform.tfvars.example`
Template for Terraform infrastructure configuration.
- **Copy to**: `infra/terraform/terraform.tfvars`
- **Contains**: VPC settings, RDS config, ECS parameters, DynamoDB settings
- **Used by**: Terraform for AWS infrastructure deployment
- **Environments**: Includes examples for dev, staging, production

#### `docker-compose.example.yml`
Template for local development with Docker Compose.
- **Copy to**: `docker-compose.local.yml` (or use as reference)
- **Contains**: All services, PostgreSQL, DynamoDB Local, LocalStack
- **Used by**: Local development environment
- **Features**: Hot reloading, health checks, service networking

---

## 🚀 Quick Setup

### Local Development
```bash
# 1. Copy environment templates
cp examples/content-service.env.template services/content-service/.env
cp examples/user-service.env.template services/user-service/.env
cp examples/ml-service.env.template services/ml-service/.env

# 2. Copy Docker Compose template
cp examples/docker-compose.example.yml docker-compose.local.yml

# 3. Start local development
docker-compose -f docker-compose.local.yml up --build
```

### AWS Deployment
```bash
# 1. Copy Terraform template
cp examples/terraform.tfvars.example infra/terraform/terraform.tfvars

# 2. Customize terraform.tfvars with your AWS account details
# 3. Deploy infrastructure
cd infra/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## ⚙️ Customization Guide

### Environment Variables

**Database Configuration**:
```bash
# Local development (Docker)
DATABASE_URL=postgresql+asyncpg://postgres:localdev_password_123@localhost:5432/content_db

# Production (AWS RDS)
DATABASE_URL=postgresql+asyncpg://postgres:SECURE_PASSWORD@rds-endpoint:5432/content_db
```

**AWS Configuration**:
```bash
# Local development (LocalStack)
AWS_ENDPOINT_URL=http://localstack:4566
AWS_ACCESS_KEY_ID=localstack
AWS_SECRET_ACCESS_KEY=localstack

# Production (Real AWS)
AWS_REGION=us-east-1
# Use IAM roles, not access keys
```

### Terraform Variables

**Development Environment**:
```hcl
project_name = "libras-play"
environment = "dev"
db_instance_class = "db.t3.micro"
ecs_cpu = 256
ecs_memory = 512
ecs_desired_count = 1
```

**Production Environment**:
```hcl
project_name = "libras-play"
environment = "prod"
db_instance_class = "db.r5.large"
ecs_cpu = 1024
ecs_memory = 2048
ecs_desired_count = 3
db_multi_az = true
enable_https = true
```

### Docker Compose Customization

**Change Ports**:
```yaml
services:
  content-service:
    ports:
      - "8001:8001"  # Change first port: "9001:8001"
```

**Add Environment Variables**:
```yaml
services:
  content-service:
    environment:
      DEBUG: true
      LOG_LEVEL: DEBUG
      CUSTOM_SETTING: value
```

**Mount Additional Volumes**:
```yaml
services:
  content-service:
    volumes:
      - ./custom-config:/app/config:ro
      - ./logs:/app/logs
```

---

## 🔒 Security Notes

### Environment Files

✅ **DO**:
- Copy templates to `.env` files
- Add `.env` to `.gitignore`
- Use AWS Secrets Manager for production
- Rotate credentials regularly

❌ **DON'T**:
- Commit `.env` files with real credentials
- Use default passwords in production
- Share credentials via chat/email
- Use root database users

### Terraform Files

✅ **DO**:
- Copy `terraform.tfvars.example` to `terraform.tfvars`
- Add `terraform.tfvars` to `.gitignore`
- Use S3 backend for state storage
- Enable encryption at rest

❌ **DON'T**:
- Commit `terraform.tfvars` with real values
- Store Terraform state locally in production
- Use overly permissive security groups
- Disable security features

---

## 📚 Environment-Specific Examples

### Development (Local)
**Goal**: Fast development with minimal costs
- Docker Compose with LocalStack
- t3.micro instances
- Single task per service
- Local PostgreSQL and DynamoDB

**Cost**: ~$0/month (local only)

### Staging (AWS)
**Goal**: Production-like testing environment
- Real AWS services
- t3.small instances
- Single AZ deployment
- Development-grade monitoring

**Cost**: ~$200-300/month

### Production (AWS)
**Goal**: High availability and performance
- Multi-AZ deployment
- r5.large instances
- Auto-scaling enabled
- Full monitoring and security
- HTTPS with custom domain

**Cost**: ~$500-800/month

---

## 🔄 Template Updates

When templates are updated:

1. **Check for changes** in this directory
2. **Compare** with your current configuration
3. **Update** your files with new settings
4. **Test** changes in development first
5. **Deploy** to production after validation

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-20 | Initial templates |

---

## 🆘 Common Issues

**Issue**: `docker-compose up` fails with "port already in use"
**Solution**: Change port mappings in `docker-compose.local.yml`

**Issue**: Terraform plan fails with "invalid credentials"
**Solution**: Configure AWS CLI with proper IAM permissions

**Issue**: Services can't connect to database
**Solution**: Check database connection strings and network configuration

**Issue**: LocalStack services not accessible
**Solution**: Verify LocalStack is running and ports are mapped correctly

---

## 📞 Support

For template-related questions:
- **Documentation**: Check README.md in each service
- **GitHub Issues**: Open issue with "template" label  
- **Team Contact**: team@librasplay.com

---

**Last Updated**: 2025-11-20  
**Template Version**: 1.0.0  
**Compatibility**: LibrasPlay Backend v1.x