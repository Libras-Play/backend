#!/bin/bash

# Script de validación para GitHub Actions workflows
# Valida sintaxis YAML, references, y configuración

set -e

echo "🔍 Validando GitHub Actions Workflows - FASE 7"
echo "================================================"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Función para imprimir resultados
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        ((ERRORS++))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

print_info() {
    echo -e "ℹ️  $1"
}

# ============================================
# 1. Validar YAML Syntax
# ============================================
echo "📝 1. Validando sintaxis YAML..."
echo "-----------------------------------"

if command -v yamllint &> /dev/null; then
    if yamllint .github/workflows/ci.yml 2>&1 | grep -q "error"; then
        print_result 1 "ci.yml tiene errores de sintaxis YAML"
        yamllint .github/workflows/ci.yml
    else
        print_result 0 "ci.yml: sintaxis YAML correcta"
    fi
    
    if yamllint .github/workflows/cd.yml 2>&1 | grep -q "error"; then
        print_result 1 "cd.yml tiene errores de sintaxis YAML"
        yamllint .github/workflows/cd.yml
    else
        print_result 0 "cd.yml: sintaxis YAML correcta"
    fi
else
    print_warning "yamllint no instalado - skip validación YAML syntax"
    print_info "Install: pip install yamllint"
fi

echo ""

# ============================================
# 2. Validar Actions existentes
# ============================================
echo "🔌 2. Validando GitHub Actions usadas..."
echo "-----------------------------------"

declare -A ACTIONS=(
    ["actions/checkout@v4"]="actions/checkout"
    ["actions/setup-python@v5"]="actions/setup-python"
    ["docker/setup-buildx-action@v3"]="docker/setup-buildx-action"
    ["docker/login-action@v3"]="docker/login-action"
    ["docker/metadata-action@v5"]="docker/metadata-action"
    ["docker/build-push-action@v5"]="docker/build-push-action"
    ["aws-actions/configure-aws-credentials@v4"]="aws-actions/configure-aws-credentials"
    ["aws-actions/amazon-ecr-login@v2"]="aws-actions/amazon-ecr-login"
    ["aws-actions/amazon-ecs-render-task-definition@v1"]="aws-actions/amazon-ecs-render-task-definition"
    ["aws-actions/amazon-ecs-deploy-task-definition@v1"]="aws-actions/amazon-ecs-deploy-task-definition"
    ["dorny/paths-filter@v3"]="dorny/paths-filter"
    ["aquasecurity/trivy-action@master"]="aquasecurity/trivy-action"
    ["gitleaks/gitleaks-action@v2"]="gitleaks/gitleaks-action"
    ["snyk/actions/python@master"]="snyk/actions"
    ["hashicorp/setup-terraform@v3"]="hashicorp/setup-terraform"
)

for action_version in "${!ACTIONS[@]}"; do
    action_name="${ACTIONS[$action_version]}"
    if grep -r "uses: $action_version" .github/workflows/ &> /dev/null; then
        print_result 0 "$action_version encontrada"
    else
        print_result 1 "$action_version NO encontrada (esperada)"
    fi
done

echo ""

# ============================================
# 3. Validar secrets referenciados
# ============================================
echo "🔐 3. Validando secrets referenciados..."
echo "-----------------------------------"

REQUIRED_SECRETS=(
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "ECR_REPO_CONTENT"
    "ECR_REPO_USER"
    "ECR_REPO_ML"
    "TF_VAR_db_password"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if grep -r "secrets\.$secret" .github/workflows/ &> /dev/null; then
        print_result 0 "Secret $secret referenciado en workflows"
    else
        print_result 1 "Secret $secret NO encontrado en workflows"
    fi
done

# Secrets opcionales
OPTIONAL_SECRETS=(
    "SNYK_TOKEN"
    "CODECOV_TOKEN"
    "SLACK_WEBHOOK_URL"
)

for secret in "${OPTIONAL_SECRETS[@]}"; do
    if grep -r "secrets\.$secret" .github/workflows/ &> /dev/null; then
        print_info "Secret opcional $secret encontrado"
    fi
done

echo ""

# ============================================
# 4. Validar environments
# ============================================
echo "🌍 4. Validando environments configurados..."
echo "-----------------------------------"

REQUIRED_ENVS=(
    "staging"
    "production"
    "staging-infrastructure"
    "production-infrastructure"
)

for env in "${REQUIRED_ENVS[@]}"; do
    if grep -r "environment: $env\|environment:\s*\n\s*name: $env" .github/workflows/cd.yml &> /dev/null; then
        print_result 0 "Environment '$env' referenciado en cd.yml"
    else
        print_result 1 "Environment '$env' NO encontrado en cd.yml"
    fi
done

echo ""

# ============================================
# 5. Validar paths en path filters
# ============================================
echo "📂 5. Validando path filters..."
echo "-----------------------------------"

EXPECTED_PATHS=(
    "services/api/content-service/**"
    "services/api/user-service/**"
    "services/api/ml-service/**"
    "infra/terraform/**"
)

for path in "${EXPECTED_PATHS[@]}"; do
    if grep -r "$path" .github/workflows/ci.yml &> /dev/null; then
        print_result 0 "Path filter '$path' encontrado"
    else
        print_result 1 "Path filter '$path' NO encontrado"
    fi
done

# Verificar que los paths existen
echo ""
print_info "Verificando que los paths monitoreados existen..."

if [ -d "../../backend/services" ]; then
    BASE_DIR="../../backend"
elif [ -d "../services/api" ]; then
    BASE_DIR=".."
else
    print_warning "No se encuentra directorio de servicios - skip verificación de paths"
    BASE_DIR=""
fi

if [ -n "$BASE_DIR" ]; then
    for service in content-service user-service ml-service; do
        if [ -d "$BASE_DIR/services/api/$service" ] || [ -d "$BASE_DIR/services/$service" ]; then
            print_result 0 "Directorio $service existe"
        else
            print_warning "Directorio $service NO existe - workflow puede no ejecutarse"
        fi
    done
fi

echo ""

# ============================================
# 6. Validar job dependencies
# ============================================
echo "🔗 6. Validando dependencias entre jobs..."
echo "-----------------------------------"

# CI.yml dependencies
if grep -A 5 "job: lint-and-test-content-service" .github/workflows/ci.yml | grep -q "needs: detect-changes"; then
    print_result 0 "CI: lint-and-test jobs dependen de detect-changes"
else
    print_result 1 "CI: lint-and-test jobs NO dependen de detect-changes"
fi

# CD.yml dependencies
if grep -A 5 "job: build-and-push-content-service" .github/workflows/cd.yml | grep -q "needs: detect-changes"; then
    print_result 0 "CD: build-and-push jobs dependen de detect-changes"
else
    print_result 1 "CD: build-and-push jobs NO dependen de detect-changes"
fi

if grep -A 10 "job: deploy-ecs-content-service" .github/workflows/cd.yml | grep -q "needs: build-and-push-content-service"; then
    print_result 0 "CD: deploy-ecs jobs dependen de build-and-push"
else
    print_result 1 "CD: deploy-ecs jobs NO dependen de build-and-push"
fi

echo ""

# ============================================
# 7. Validar triggers
# ============================================
echo "⚡ 7. Validando triggers de workflows..."
echo "-----------------------------------"

# CI triggers
if grep -A 10 "^on:" .github/workflows/ci.yml | grep -q "push:"; then
    print_result 0 "CI: trigger 'push' configurado"
else
    print_result 1 "CI: trigger 'push' NO configurado"
fi

if grep -A 10 "^on:" .github/workflows/ci.yml | grep -q "pull_request:"; then
    print_result 0 "CI: trigger 'pull_request' configurado"
else
    print_result 1 "CI: trigger 'pull_request' NO configurado"
fi

# CD triggers
if grep -A 15 "^on:" .github/workflows/cd.yml | grep -q "push:"; then
    print_result 0 "CD: trigger 'push' configurado"
else
    print_result 1 "CD: trigger 'push' NO configurado"
fi

if grep -A 15 "^on:" .github/workflows/cd.yml | grep -q "workflow_dispatch:"; then
    print_result 0 "CD: trigger 'workflow_dispatch' configurado"
else
    print_result 1 "CD: trigger 'workflow_dispatch' NO configurado"
fi

# Verificar branches en push trigger
if grep -A 20 "^on:" .github/workflows/cd.yml | grep -A 5 "push:" | grep -q "main"; then
    print_result 0 "CD: branch 'main' en trigger push"
else
    print_result 1 "CD: branch 'main' NO en trigger push"
fi

if grep -A 20 "^on:" .github/workflows/cd.yml | grep -A 5 "push:" | grep -q "staging"; then
    print_result 0 "CD: branch 'staging' en trigger push"
else
    print_result 1 "CD: branch 'staging' NO en trigger push"
fi

echo ""

# ============================================
# 8. Validar rollback mechanism
# ============================================
echo "🔄 8. Validando mecanismo de rollback..."
echo "-----------------------------------"

# Verificar que se guarda previous task definition
if grep -A 50 "deploy-ecs-content-service" .github/workflows/cd.yml | grep -q "previous-task-def"; then
    print_result 0 "Rollback: Previous task definition se guarda"
else
    print_result 1 "Rollback: Previous task definition NO se guarda"
fi

# Verificar que existe step de rollback con if: failure()
if grep -A 100 "deploy-ecs-content-service" .github/workflows/cd.yml | grep -q "if: failure()"; then
    print_result 0 "Rollback: Step con 'if: failure()' existe"
else
    print_result 1 "Rollback: Step con 'if: failure()' NO existe"
fi

# Verificar que se usa previous task def en rollback
if grep -A 100 "deploy-ecs-content-service" .github/workflows/cd.yml | grep "if: failure()" -A 20 | grep -q "previous-task-def"; then
    print_result 0 "Rollback: Usa previous task definition"
else
    print_result 1 "Rollback: NO usa previous task definition"
fi

echo ""

# ============================================
# 9. Validar health checks
# ============================================
echo "🏥 9. Validando health checks..."
echo "-----------------------------------"

if grep -A 100 "deploy-ecs-content-service" .github/workflows/cd.yml | grep -q "health"; then
    print_result 0 "Health check configurado en deploy jobs"
else
    print_result 1 "Health check NO configurado en deploy jobs"
fi

if grep -A 100 "deploy-ecs-content-service" .github/workflows/cd.yml | grep -q "/health"; then
    print_result 0 "Health endpoint '/health' referenciado"
else
    print_warning "Health endpoint '/health' NO encontrado - verificar ALB health check"
fi

echo ""

# ============================================
# 10. Validar matrix strategy
# ============================================
echo "🎯 10. Validando matrix strategy..."
echo "-----------------------------------"

# CI matrix
if grep -A 5 "build-docker-images" .github/workflows/ci.yml | grep -q "matrix:"; then
    print_result 0 "CI: Matrix strategy configurada en build-docker-images"
else
    print_result 1 "CI: Matrix strategy NO configurada en build-docker-images"
fi

# Verificar servicios en matrix
if grep -A 10 "build-docker-images" .github/workflows/ci.yml | grep -q "content-service"; then
    print_result 0 "CI Matrix: content-service incluido"
else
    print_result 1 "CI Matrix: content-service NO incluido"
fi

if grep -A 10 "build-docker-images" .github/workflows/ci.yml | grep -q "user-service"; then
    print_result 0 "CI Matrix: user-service incluido"
else
    print_result 1 "CI Matrix: user-service NO incluido"
fi

if grep -A 10 "build-docker-images" .github/workflows/ci.yml | grep -q "ml-service"; then
    print_result 0 "CI Matrix: ml-service incluido"
else
    print_result 1 "CI Matrix: ml-service NO incluido"
fi

echo ""

# ============================================
# 11. Validar documentación
# ============================================
echo "📚 11. Validando documentación..."
echo "-----------------------------------"

DOCS=(
    ".github/SECRETS_SETUP.md"
    ".github/ENVIRONMENTS_SETUP.md"
    ".github/WORKFLOWS_GUIDE.md"
    ".github/README.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        print_result 0 "Documentación: $doc existe"
        
        # Verificar tamaño mínimo (debe tener contenido)
        if [ $(wc -l < "$doc") -gt 50 ]; then
            print_result 0 "  ├─ Contenido: > 50 líneas ✓"
        else
            print_warning "  ├─ Contenido: < 50 líneas (parece incompleto)"
        fi
    else
        print_result 1 "Documentación: $doc NO existe"
    fi
done

echo ""

# ============================================
# 12. Validar conditional execution
# ============================================
echo "🎚️  12. Validando ejecución condicional..."
echo "-----------------------------------"

# Verificar que jobs tienen condiciones basadas en needs.detect-changes.outputs
if grep -A 3 "job: lint-and-test-content-service" .github/workflows/ci.yml | grep -q "if:.*needs.detect-changes.outputs"; then
    print_result 0 "Conditional execution: lint-and-test usa outputs de detect-changes"
else
    print_result 1 "Conditional execution: lint-and-test NO usa outputs de detect-changes"
fi

echo ""

# ============================================
# RESUMEN
# ============================================
echo ""
echo "================================================"
echo "📊 RESUMEN DE VALIDACIÓN"
echo "================================================"
echo ""

# Contar líneas de código
CI_LINES=$(wc -l < .github/workflows/ci.yml)
CD_LINES=$(wc -l < .github/workflows/cd.yml)
TOTAL_WORKFLOW_LINES=$((CI_LINES + CD_LINES))

echo "📝 Workflows:"
echo "  ├─ ci.yml: $CI_LINES líneas"
echo "  ├─ cd.yml: $CD_LINES líneas"
echo "  └─ Total: $TOTAL_WORKFLOW_LINES líneas"
echo ""

# Contar documentación
TOTAL_DOC_LINES=0
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        DOC_LINES=$(wc -l < "$doc")
        TOTAL_DOC_LINES=$((TOTAL_DOC_LINES + DOC_LINES))
        echo "📚 $doc: $DOC_LINES líneas"
    fi
done
echo "  └─ Total documentación: $TOTAL_DOC_LINES líneas"
echo ""

echo "🔍 Resultados de validación:"
echo "  ├─ Errores: $ERRORS"
echo "  └─ Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ FASE 7 VALIDADA EXITOSAMENTE${NC}"
    echo ""
    echo "🚀 Los workflows están listos para uso en producción!"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Configurar GitHub Secrets (ver SECRETS_SETUP.md)"
    echo "  2. Crear GitHub Environments (ver ENVIRONMENTS_SETUP.md)"
    echo "  3. Hacer push a 'staging' para primer deployment"
    echo ""
    exit 0
else
    echo -e "${RED}❌ VALIDACIÓN FALLÓ CON $ERRORS ERROR(ES)${NC}"
    echo ""
    echo "Por favor revisar los errores arriba y corregir antes de usar en producción."
    echo ""
    exit 1
fi
