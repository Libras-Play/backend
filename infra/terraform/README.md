# LibrasPlay - Terraform Infrastructure (AWS Example)

Example Infrastructure as Code (IaC) for deploying LibrasPlay on AWS using Terraform. You can adapt this for other cloud providers.

## 🏗️ Architecture

**Modular Structure:**
- 10 reusable modules (VPC, ECR, ECS Fargate, RDS Aurora, DynamoDB, S3, Cognito, IAM, SQS, SNS)
- 2 environments: `dev` and `prod`
- Remote state management with S3 + DynamoDB locking

**Example AWS Services:**
- **Compute:** ECS Fargate (microservices)
- **Database:** RDS Aurora Serverless v2 (PostgreSQL)
- **NoSQL:** DynamoDB (user data, progress, sessions)
- **Storage:** S3 (content assets, uploads, models)
- **Auth:** Cognito User Pool
- **Messaging:** SQS + SNS (processing, notifications)
- **Networking:** VPC with public/private subnets
- **Container Registry:** ECR
- **Load Balancing:** Application Load Balancer

## 📋 Prerequisites

- **Terraform:** >= 1.6.0 ([Install](https://developer.hashicorp.com/terraform/downloads))
- **AWS CLI:** v2 ([Install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- **AWS Credentials:** Configured via `aws configure` or environment variables
- **Permissions:** AdministratorAccess or custom policy with permissions for EC2, ECS, RDS, DynamoDB, S3, IAM, Cognito, SQS, SNS

## 🚀 Quick Start

### 1. Setup Terraform Backend

The backend stores Terraform state remotely in S3 with DynamoDB locking to prevent concurrent modifications.

```bash
cd infra/terraform
chmod +x scripts/setup_backend.sh
./scripts/setup_backend.sh
```

This creates:
- **S3 Bucket:** `libras-play-terraform-state` (versioned, encrypted)
- **DynamoDB Table:** `libras-play-terraform-locks`

### 2. Deploy Development Environment

```bash
cd environments/dev

# Initialize Terraform (download providers and modules)
terraform init

# Review planned changes
terraform plan

# Apply infrastructure
terraform apply

# Outputs (save these!)
terraform output
```

**Important Outputs:**
- `alb_dns_name`: Load balancer endpoint
- `ecr_repositories`: Docker registry URLs for pushing images
- `rds_endpoint`: Database connection string
- `dynamodb_tables`: Table names for application config

### 3. Build and Push Docker Images

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-east-1.amazonaws.com

# Get repository URLs from Terraform outputs
CONTENT_REPO=$(terraform output -raw ecr_repositories | jq -r '.["content-service"]')
USER_REPO=$(terraform output -raw ecr_repositories | jq -r '.["user-service"]')
ML_REPO=$(terraform output -raw ecr_repositories | jq -r '.["ml-service"]')

# Build and push (from project root)
cd ../../../services/api/content-service
docker build -t $CONTENT_REPO:latest .
docker push $CONTENT_REPO:latest

cd ../user-service
docker build -t $USER_REPO:latest .
docker push $USER_REPO:latest

cd ../ml-service
docker build -t $ML_REPO:latest .
docker push $ML_REPO:latest
```

### 4. Verify Deployment

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test services
curl http://$ALB_DNS/content/health
curl http://$ALB_DNS/users/health
curl http://$ALB_DNS/ml/health
```

### 5. Run Database Migrations

```bash
# Connect to RDS via bastion or VPN, then:
cd ../../../scripts
python run_migrations.py --env dev
```

## 📁 Project Structure

```
infra/terraform/
├── modules/               # Reusable Terraform modules
│   ├── vpc/              # VPC, subnets, NAT gateway
│   ├── ecr/              # Container registries
│   ├── ecs_fargate/      # ECS cluster, tasks, ALB
│   ├── rds_aurora/       # Aurora Serverless v2
│   ├── dynamodb/         # DynamoDB tables
│   ├── s3/               # S3 buckets
│   ├── cognito/          # User Pool
│   ├── iam/              # ECS execution/task roles
│   ├── sqs/              # SQS queues + DLQs
│   └── sns/              # SNS topics
├── environments/
│   ├── dev/main.tf       # Development config
│   └── prod/main.tf      # Production config
├── scripts/
│   └── setup_backend.sh  # Backend initialization
├── provider.tf           # AWS provider config
├── variables.tf          # Global variables
├── outputs.tf            # Global outputs
└── terraform.tfvars.example
```

## 🔐 Security Best Practices

✅ **Implemented:**
- VPC with isolated subnets (public, private, database)
- Security groups with least privilege (ECS tasks only accept traffic from ALB)
- IAM roles with minimal permissions (scoped to specific resources)
- Encryption at rest (RDS, S3, DynamoDB, SQS, SNS)
- Encryption in transit (TLS for ALB)
- Private subnets for ECS tasks and RDS
- Secrets stored in AWS Secrets Manager
- No hardcoded credentials

🔒 **Additional Recommendations:**
- Enable AWS GuardDuty and Security Hub
- Implement AWS WAF on ALB
- Use VPN or AWS PrivateLink for database access
- Enable CloudTrail for audit logging
- Implement AWS Config rules
- Use AWS Systems Manager Session Manager instead of bastion hosts

## 🔧 Configuration

### Environment Variables

For GitHub Actions or local development:

```bash
export TF_VAR_aws_region="us-east-1"
export TF_VAR_project_name="libras-play"
export TF_VAR_environment="dev"
```

### Customization

Edit `environments/dev/main.tf` or `environments/prod/main.tf`:

```hcl
# Example: Increase ECS task resources
services = {
  content-service = {
    cpu    = 512  # Change from 256
    memory = 1024 # Change from 512
    desired_count = 2 # Scale to 2 tasks
  }
}
```

## 🤖 GitHub Actions Integration

### Workflow Example

Create `.github/workflows/terraform-deploy.yml`:

```yaml
name: Terraform Deploy

on:
  push:
    branches: [main]
    paths: ['infra/terraform/**']
  pull_request:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0
      
      - name: Terraform Init
        working-directory: infra/terraform/environments/dev
        run: terraform init
      
      - name: Terraform Plan
        working-directory: infra/terraform/environments/dev
        run: terraform plan -no-color
        continue-on-error: true
      
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        working-directory: infra/terraform/environments/dev
        run: terraform apply -auto-approve
```

### Required GitHub Secrets

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## 📊 Cost Estimation

**Development (Monthly):**
- ECS Fargate (3 tasks, 256 CPU, 512 MB): ~$25
- RDS Aurora Serverless v2 (0.5-1 ACU): ~$30
- DynamoDB (on-demand): ~$5
- S3 (100 GB): ~$2.30
- NAT Gateway (1): ~$32
- ALB: ~$16
- **Total: ~$110/month**

**Production (Monthly):**
- ECS Fargate (5 tasks, higher CPU/memory): ~$80
- RDS Aurora Serverless v2 (1-4 ACU): ~$120
- DynamoDB (on-demand): ~$20
- S3 (500 GB): ~$11.50
- NAT Gateway (3): ~$96
- ALB: ~$16
- **Total: ~$343/month**

Use [AWS Pricing Calculator](https://calculator.aws/) for accurate estimates.

## 🐛 Troubleshooting

### Issue: `Error locking state`

**Solution:** Another process is using the state. Wait or manually release the lock:

```bash
# Get lock ID from error message
terraform force-unlock <LOCK_ID>
```

### Issue: `InvalidParameterException: No container instances were found`

**Solution:** ECS tasks need time to start. Wait 2-3 minutes after `terraform apply`.

### Issue: `CannotPullContainerError`

**Solution:** Images must be pushed to ECR before ECS can pull them. See "Build and Push Docker Images" section.

### Issue: `AccessDenied` when creating resources

**Solution:** Ensure AWS credentials have sufficient permissions. Check IAM policy.

## 🔄 Updating Infrastructure

```bash
# Pull latest changes
git pull origin main

# Review changes
cd infra/terraform/environments/dev
terraform plan

# Apply updates
terraform apply

# Update ECS service (force new deployment)
aws ecs update-service \
  --cluster libras-play-dev-cluster \
  --service content-service \
  --force-new-deployment
```

## 🗑️ Cleanup

**Warning:** This will delete ALL resources and data!

```bash
cd infra/terraform/environments/dev
terraform destroy

# For production (extra confirmation)
cd ../prod
terraform destroy -auto-approve=false
```

## 📚 Additional Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Aurora Serverless v2 Guide](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

## 📝 License

See [LICENSE](../../LICENSE) file.

## 🤝 Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md).
