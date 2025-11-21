# GitHub Secrets Configuration

This document lists all GitHub Secrets and Variables required for the CI/CD pipelines.

## Required for CI (Continuous Integration)

**None** - The CI pipeline runs without any secrets required.

## Optional for Security Scanning

- `SNYK_TOKEN` - Snyk API token for dependency vulnerability scanning (optional)

## Required for CD (Continuous Deployment)

These secrets are **only required if you plan to deploy to AWS**:

### AWS Authentication (Choose ONE method)

#### Option 1: Long-term Credentials (cd.yml)
- `AWS_ACCESS_KEY_ID` - AWS access key ID
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key
- `AWS_ACCOUNT_ID` - Your AWS account ID

#### Option 2: OIDC/Short-term Credentials (cd-secure.yml) - RECOMMENDED
- `AWS_OIDC_ROLE_ARN` - ARN of the IAM role to assume via OIDC

### AWS Resources
- `ECR_REPO_CONTENT` - ECR repository name for content-service
- `ECR_REPO_USER` - ECR repository name for user-service  
- `ECR_REPO_ML` - ECR repository name for ml-service

### Database
- `TF_VAR_db_password` - Database password for Terraform

### Application Configuration
These are **Variables** (not secrets):
- `ALB_URL` - Application Load Balancer URL for health checks

## How to Configure Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with its value

## For Open Source Contributors

If you're contributing to this project and only running CI tests, **you don't need to configure any secrets**. The CI pipeline will run successfully without them.

The CD (deployment) workflows will be skipped if you don't have the required AWS secrets configured.

## Disabling Secret Warnings

To remove the warnings about missing secrets in VS Code or GitHub Actions:

1. The warnings are informational - they don't prevent the workflows from running
2. You can ignore them if you're only working on CI (testing/linting)
3. If deploying to AWS, configure the secrets listed above
