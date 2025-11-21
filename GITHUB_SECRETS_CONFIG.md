# 🔐 Configuración de GitHub Secrets - LibrasPlay Backend

> **⚠️ IMPORTANTE**: Este archivo contiene información sensible de tu cuenta AWS.  
> **NO SUBIR A GITHUB** - Solo para tu referencia local.

---

## 📋 Valores Detectados Automáticamente

### 1. AWS Account Information

```bash
AWS_ACCOUNT_ID = 019460294038
```

---

## 🔑 GitHub Secrets a Configurar

Ve a: https://github.com/Libras-Play/backend/settings/secrets/actions

### Opción 1: Deployment con AWS Access Keys (Básico)

| Secret Name | Valor | Descripción |
|-------------|-------|-------------|
| `AWS_ACCOUNT_ID` | `019460294038` | Tu AWS Account ID |
| `AWS_ACCESS_KEY_ID` | `AKIA...` ⚠️ **DEBES CREARLO** | Access Key de IAM User con permisos |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` ⚠️ **DEBES CREARLO** | Secret Key correspondiente |

#### ⚠️ Cómo crear Access Keys:
```bash
# 1. Ve a AWS Console → IAM → Users
# 2. Crea un usuario: github-actions-user
# 3. Attacha políticas: AmazonEC2ContainerRegistryFullAccess, AmazonECS_FullAccess
# 4. Security credentials → Create access key → CLI
# 5. Copia AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY
```

---

### Opción 2: Deployment con OIDC (Recomendado - Más Seguro)

Ya tienes el rol creado: `aplicacion-senas-aws-github-actions`

| Secret Name | Valor | Descripción |
|-------------|-------|-------------|
| `AWS_OIDC_ROLE_ARN` | `arn:aws:iam::019460294038:role/aplicacion-senas-aws-github-actions` | Para deployment de servicios |
| `AWS_OIDC_INFRA_ROLE_ARN` | ⚠️ **NECESITAS CREAR** otro rol para Terraform | Para cambios de infraestructura |

#### ✅ Rol existente detectado:
```
arn:aws:iam::019460294038:role/aplicacion-senas-aws-github-actions
```

---

### 3. ECR Repository URIs

Tus repositorios ECR detectados:

| Secret Name | Valor Real | Para qué servicio |
|-------------|------------|-------------------|
| `ECR_REPO_CONTENT` | `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-content-service` | Content Service |
| `ECR_REPO_USER` | `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-user-service` | User Service |
| `ECR_REPO_ML` | `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-dev-ml-service` | ML Service (dev) |

---

### 4. Database Password

| Secret Name | Valor | Descripción |
|-------------|-------|-------------|
| `TF_VAR_db_password` | ⚠️ **TÚ LO DEFINES** | Password seguro para RDS (min 8 chars, mayúsculas, números, símbolos) |

**Ejemplo de password seguro:**
```
LibrasPlay2025!SecureDB
```

---

## 🌐 Variables de Repositorio (No son secrets)

Ve a: https://github.com/Libras-Play/backend/settings/variables/actions

| Variable Name | Valor Real | Descripción |
|---------------|------------|-------------|
| `ALB_URL` | `http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com` | URL del Application Load Balancer |

---

## 📝 Cómo Agregar los Secrets en GitHub

### Paso a Paso:

1. **Ve a tu repositorio en GitHub:**
   ```
   https://github.com/Libras-Play/backend
   ```

2. **Settings** → **Secrets and variables** → **Actions**

3. **Click "New repository secret"**

4. **Para cada secret de la tabla:**
   - Name: `AWS_ACCOUNT_ID`
   - Secret: `019460294038`
   - Click "Add secret"

5. **Para variables (no secrets):**
   - Click en tab **"Variables"**
   - Click "New repository variable"
   - Name: `ALB_URL`
   - Value: `http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com`

---

## 🎯 Configuración Mínima Recomendada

Para que los workflows funcionen **SIN ERRORES**, configura estos **6 secrets**:

### Si usas Access Keys (más simple):

1. ✅ `AWS_ACCOUNT_ID` = `019460294038`
2. ⚠️ `AWS_ACCESS_KEY_ID` = *Debes crear en IAM*
3. ⚠️ `AWS_SECRET_ACCESS_KEY` = *Debes crear en IAM*
4. ✅ `ECR_REPO_CONTENT` = `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-content-service`
5. ✅ `ECR_REPO_USER` = `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-user-service`
6. ✅ `ECR_REPO_ML` = `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-dev-ml-service`

### Si usas OIDC (más seguro):

1. ✅ `AWS_OIDC_ROLE_ARN` = `arn:aws:iam::019460294038:role/aplicacion-senas-aws-github-actions`
2. ⚠️ `AWS_OIDC_INFRA_ROLE_ARN` = *Necesitas crear rol adicional*
3. ✅ `ECR_REPO_CONTENT` = `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-content-service`
4. ✅ `ECR_REPO_USER` = `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-user-service`
5. ✅ `ECR_REPO_ML` = `019460294038.dkr.ecr.us-east-1.amazonaws.com/libras-play-dev-ml-service`

---

## ⚠️ Secrets OPCIONALES (solo si usas esas features)

| Secret | Necesario si... |
|--------|----------------|
| `TF_VAR_db_password` | Vas a ejecutar Terraform desde GitHub Actions |
| `SNYK_TOKEN` | Quieres escaneo de vulnerabilidades con Snyk |
| `SONAR_TOKEN` | Quieres análisis de código con SonarCloud |

---

## 🔍 Verificar que funcionen

Después de configurar los secrets:

1. Ve a **Actions** en GitHub
2. Los workflows deberían ejecutarse sin errores de "secret not found"
3. Los warnings en VS Code desaparecerán

---

## 🛡️ Seguridad

✅ **Nunca** compartas los secrets con nadie  
✅ **Nunca** los pongas en código  
✅ **Rota** las claves cada 90 días  
✅ Usa **OIDC** en lugar de Access Keys cuando sea posible  

---

## 📞 Comandos Útiles

```bash
# Ver tu Account ID
aws sts get-caller-identity --query Account --output text

# Ver tus ECR repos
aws ecr describe-repositories --region us-east-1 --query 'repositories[*].repositoryUri'

# Ver tus ALBs
aws elbv2 describe-load-balancers --query 'LoadBalancers[*].DNSName'

# Ver roles IAM
aws iam list-roles --query 'Roles[*].RoleName' --output table
```

---

**Fecha de generación**: 21 de noviembre de 2025  
**Región AWS**: us-east-1  
**Proyecto**: LibrasPlay Backend  
