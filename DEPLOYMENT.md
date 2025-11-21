# Deployment Guide

This guide covers different deployment options for the LibrasPlay backend services.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Environment Variables](#environment-variables)
6. [Database Setup](#database-setup)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

```bash
# Check installations
docker --version
python --version
git --version

# Should output:
# Docker version 20.10+
# Python 3.11+
# git version 2.x.x
```

---

## Local Development

The easiest way to get started is with Docker:

```bash
# Clone repository
git clone <your-repo-url>
cd libras-play-backend

# Copy environment templates
find . -name "*.env.template" -exec sh -c 'cp "$1" "${1%.template}"' _ {} \;

# Start all services
docker-compose up --build
```

Services will be available at:
- Content API: http://localhost:8001/docs
- User API: http://localhost:8002/docs
- ML API: http://localhost:8003/docs
- Adaptive API: http://localhost:8004/docs

---

## Docker Deployment

### Production Docker Compose

```bash
# Create production docker-compose file
cp docker-compose.yml docker-compose.prod.yml

# Edit environment variables for production
# Set proper database URLs, secrets, etc.

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Building Images

```bash
# Build all service images
docker-compose build

# Build individual service
docker build -t libras-play/content-service ./services/content-service

# Push to registry (optional)
docker tag libras-play/content-service your-registry/content-service:latest
docker push your-registry/content-service:latest
```

---

## Cloud Deployment

### AWS (Using Terraform)

The project includes Terraform configurations for AWS deployment:

```bash
# Navigate to terraform directory
cd infra/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply (creates infrastructure)
terraform apply
```

### Other Cloud Providers

The Docker setup can be deployed on any cloud platform that supports containers:

- **Google Cloud Run**: Deploy each service as a Cloud Run service
- **Azure Container Instances**: Use the Docker images with ACI
- **DigitalOcean App Platform**: Deploy using the included Dockerfiles
- **Heroku**: Use container registry deployment

---

## Environment Variables

### Required Environment Variables

Create `.env` files for each service:

#### Content Service
```bash
DATABASE_URL=postgresql://user:pass@host:5432/content_db
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
LOG_LEVEL=info
```

#### User Service  
```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
DYNAMODB_TABLE_PREFIX=libras-play
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

#### ML Service
```bash
ML_MODEL_PATH=/app/models
MAX_FILE_SIZE=10485760
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Security Notes

- Never commit real credentials to the repository
- Use environment variables or secret management services
- Rotate credentials regularly
- Use least-privilege access principles

---

## Database Setup

### PostgreSQL (Content Service)

```bash
# Create database
createdb libras_content

# Run migrations
cd services/content-service
alembic upgrade head

# Seed sample data (optional)
python seed_data/seed_content.py
```

### DynamoDB (User Service)

DynamoDB tables can be created automatically or via Terraform:

```bash
# Using AWS CLI
aws dynamodb create-table \
  --table-name libras-play-users \
  --attribute-definitions AttributeName=userId,AttributeType=S \
  --key-schema AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

---

## Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using the ports
lsof -i :8001
lsof -i :8002

# Stop conflicting services or change ports in docker-compose.yml
```

#### Database Connection Issues
```bash
# Check database connectivity
pg_isready -h localhost -p 5432

# Check DynamoDB local (if using)
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

#### Docker Issues
```bash
# Clean up Docker resources
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check logs
docker-compose logs service-name
```

### Getting Help

- Check the service logs: `docker-compose logs [service-name]`
- Verify environment variables are set correctly
- Ensure all required ports are available
- Check database connectivity and credentials

For additional help, open an issue in the GitHub repository.