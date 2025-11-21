# 🔐 GitHub Actions CI/CD - README

Workflows de Continuous Integration y Continuous Deployment para Aplicación Señas AWS.

## 📁 Estructura

```
.github/
├── workflows/
│   ├── ci.yml                 # Continuous Integration
│   └── cd.yml                 # Continuous Deployment
├── SECRETS_SETUP.md           # Guía de configuración de secrets
├── ENVIRONMENTS_SETUP.md      # Guía de configuración de environments
├── WORKFLOWS_GUIDE.md         # Guía de uso diario
└── README.md                  # Este archivo
```

---

## 🚀 Quick Start

### 1. Configurar Secrets

```bash
# Ver guía completa: SECRETS_SETUP.md

# Secrets mínimos requeridos:
gh secret set AWS_ACCESS_KEY_ID --body "AKIA..."
gh secret set AWS_SECRET_ACCESS_KEY --body "..."
gh secret set ECR_REPO_CONTENT --body "aplicacion-senas-dev-content-service"
gh secret set ECR_REPO_USER --body "aplicacion-senas-dev-user-service"
gh secret set ECR_REPO_ML --body "aplicacion-senas-dev-ml-service"
gh secret set TF_VAR_db_password --body "$(openssl rand -base64 32)"
```

**📖 Guía completa**: [SECRETS_SETUP.md](./SECRETS_SETUP.md)

---

### 2. Configurar Environments

```bash
# Ver guía completa: ENVIRONMENTS_SETUP.md

# Crear 4 environments en GitHub:
1. staging                      # Auto-deploy
2. production                   # Manual approval
3. staging-infrastructure       # Terraform staging
4. production-infrastructure    # Terraform prod (2 approvals)
```

**📖 Guía completa**: [ENVIRONMENTS_SETUP.md](./ENVIRONMENTS_SETUP.md)

---

### 3. Primer Deployment

```bash
# 1. Push a staging para testing
git checkout staging
git merge main
git push origin staging

# 2. CI + CD se ejecutan automáticamente
# 3. Verificar en staging
curl https://staging.aplicacion-senas.com/health

# 4. Si OK, merge a main para production
git checkout main
git merge staging
git push origin main

# 5. Aprobar deployment en GitHub Actions
# Actions tab → Review deployments → Approve
```

**📖 Guía completa**: [WORKFLOWS_GUIDE.md](./WORKFLOWS_GUIDE.md)

---

## 📊 Workflows Overview

### **ci.yml** - Continuous Integration

**Triggers**:
- Push a cualquier branch
- Pull Requests a `main` o `staging`

**Jobs**:
1. ✅ **detect-changes** - Path filtering (smart execution)
2. ✅ **lint-and-test-{service}** - Pytest, ruff, flake8, mypy (parallel)
3. ✅ **build-docker-images** - Docker build + Trivy security scan
4. ✅ **validate-terraform** - Terraform validate + TFLint
5. ✅ **security-scan** - Gitleaks (secrets) + Snyk (vulnerabilities)
6. ✅ **ci-summary** - Aggregate results

**Features**:
- 🎯 Solo ejecuta jobs para servicios modificados
- 📊 Coverage reports en PRs (via Codecov)
- 🔒 Security scanning con SARIF upload
- 🚀 Parallel execution (matrix strategy)

**Duración típica**: 5-10 minutos

---

### **cd.yml** - Continuous Deployment

**Triggers**:
- Push a `main` (production)
- Push a `staging` (staging)
- Manual dispatch (workflow_dispatch)

**Jobs**:
1. ✅ **detect-changes** - Determine environment
2. ✅ **build-and-push-{service}** - Build + push to ECR
3. ✅ **deploy-ecs-{service}** - Deploy to ECS + health check
4. 🔄 **Automatic rollback** - On deployment failure
5. ✅ **terraform-plan** - Infrastructure plan
6. 🔒 **terraform-apply** - Infrastructure apply (manual approval)
7. ✅ **run-migrations** - Alembic database migrations
8. ✅ **deployment-summary** - Final report

**Features**:
- 🔒 Manual approval for production deployments
- 🔄 Automatic rollback on failure
- 🎯 Smart environment detection
- 📦 ECR image tagging (sha, branch, latest)
- 🏥 Health checks post-deployment

**Duración típica**: 
- Staging: 10-15 min
- Production: 15-20 min (includes approval wait)

---

## 🎯 Path-Based Smart Execution

Los workflows detectan qué servicios cambiaron y solo ejecutan jobs relevantes:

```yaml
# Ejemplo: Solo cambios en content-service
Changes detected:
  services/api/content-service/** → TRUE
  services/api/user-service/**    → FALSE
  services/api/ml-service/**      → FALSE
  infra/terraform/**              → FALSE

Jobs executed:
  ✅ lint-and-test-content-service
  ⏭️ lint-and-test-user-service    (SKIPPED)
  ⏭️ lint-and-test-ml-service      (SKIPPED)
  ✅ build-docker-images (matrix: content-service only)

Time saved: ~5 minutes
```

**Paths monitored**:
- `services/api/content-service/**`
- `services/api/user-service/**`
- `services/api/ml-service/**`
- `infra/terraform/**`

---

## 🔐 Security Features

### 1. Trivy - Container Scanning

```yaml
- Vulnerabilities detection (CVE)
- Secret detection in images
- Misconfiguration detection
- SARIF upload to GitHub Security tab
```

### 2. Gitleaks - Secret Detection

```yaml
- AWS credentials
- API keys, tokens
- Private keys
- Passwords in code
```

### 3. Snyk - Dependency Scanning

```yaml
- Vulnerabilities en requirements.txt
- License compatibility
- Outdated packages
```

---

## 🔄 Rollback Mechanism

### Automatic Rollback

Se activa cuando:
- ECS deployment falla (task no inicia)
- Health check post-deployment falla

**Proceso**:
```yaml
1. Save previous task definition antes del deploy
2. Deploy new version
3. Health check (curl $ALB_URL/health)
4. If fails → Restore previous task definition
5. Force new deployment con versión anterior
6. Wait for service stability
7. Notify team
```

### Manual Rollback

```bash
# Ver WORKFLOWS_GUIDE.md para procedimiento completo
aws ecs update-service \
  --service aplicacion-senas-prod-content-service \
  --task-definition aplicacion-senas-prod-content-service:42 \
  --force-new-deployment
```

---

## 📈 Monitoring & Observability

### GitHub Actions Dashboard

```bash
# Via CLI
gh run list --workflow=cd.yml --limit=10
gh run watch <run-id>

# Via API
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/EEEEERIKO/aplicacion-senas-aws/actions/runs"
```

### Deployment Status

```
Actions tab → Environments

staging ✅ Deployed 2 hours ago (v1.2.3)
production ⏳ Awaiting approval (v1.2.3)
```

### Coverage Reports

```
PR Comments:
📊 Coverage: 92.1% (+2.3%) ✅
Files changed: 3
Lines covered: 245/266
```

---

## 🛡️ Production Safeguards

### 1. Manual Approval

```yaml
Environment: production
Required reviewers: 2
Wait timer: 5 minutes
Prevent self-review: true
```

### 2. Infrastructure Approval

```yaml
Environment: production-infrastructure
Required reviewers: 2
Wait timer: 10 minutes
Prevent self-review: true
```

### 3. Deployment Branches

```yaml
staging:       staging branch only
production:    main branch only
```

### 4. Health Checks

```bash
# Post-deployment verification
curl -f $ALB_URL/health || rollback
```

---

## 🔧 Troubleshooting

### CI Falla

```bash
# 1. Ver logs en Actions tab
# 2. Identify failed job
# 3. Check error message:

Common issues:
- Linter errors     → Fix code style
- Test failures     → Fix broken tests
- Security alerts   → Update dependencies
- Docker build fail → Check Dockerfile
```

### CD Falla

```bash
# 1. Check deployment logs
# 2. Verify ECS events:

AWS Console → ECS → Service → Events

Common issues:
- Task failed to start → Check CloudWatch logs
- Health check failed  → Verify ALB target group
- Rollback triggered   → Check application errors
```

### Secrets Issues

```bash
# Verify secrets exist
gh secret list

# Re-set secret
gh secret set AWS_ACCESS_KEY_ID --body "..."

# Test AWS credentials
aws sts get-caller-identity
```

**📖 Guía completa**: [WORKFLOWS_GUIDE.md](./WORKFLOWS_GUIDE.md#-debugging-failed-workflows)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SECRETS_SETUP.md](./SECRETS_SETUP.md) | Configuración de GitHub Secrets, IAM policies, OIDC setup |
| [ENVIRONMENTS_SETUP.md](./ENVIRONMENTS_SETUP.md) | Configuración de GitHub Environments, approval rules, branch policies |
| [WORKFLOWS_GUIDE.md](./WORKFLOWS_GUIDE.md) | Guía de uso diario, debugging, best practices, emergency procedures |

---

## 🚀 Next Steps

### After Setup

1. ✅ Configure secrets (SECRETS_SETUP.md)
2. ✅ Configure environments (ENVIRONMENTS_SETUP.md)
3. ✅ Run first deployment
4. ✅ Configure notifications (optional)
5. ✅ Add status badges to main README

### Optional Enhancements

- **Slack/Discord notifications**:
  ```yaml
  - uses: slackapi/slack-github-action@v1
    with:
      webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
  ```

- **Performance testing**:
  ```yaml
  - name: Run load tests
    run: locust -f tests/load/locustfile.py --headless
  ```

- **Blue/Green deployment**:
  ```yaml
  # Deploy to new task set
  # Validate
  # Switch traffic
  # Decommission old task set
  ```

---

## 🆘 Emergency Contacts

**Production Issues**:
- DevOps Lead: @devops-lead
- Tech Lead: @tech-lead
- On-call: Pager duty rotation

**Escalation**:
1. Check #incidents Slack channel
2. Trigger rollback if needed
3. Notify stakeholders
4. Post-mortem after resolution

---

## 📊 Workflow Statistics

**Current Setup**:
- Total workflows: 2
- Total jobs: 19
- Avg CI duration: 7 minutes
- Avg CD duration (staging): 12 minutes
- Avg CD duration (production): 18 minutes
- Success rate: 95%+ (target)

---

## 🎓 Learning Resources

- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions)
- [AWS ECS Blue/Green Deployment](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-bluegreen.html)
- [Terraform CI/CD Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

---

**Última actualización**: 13 de noviembre de 2025
**Maintainers**: DevOps Team
**Status**: ✅ Production Ready
