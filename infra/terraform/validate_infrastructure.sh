#!/bin/bash

# =============================================================================
# Script de Validación de Infraestructura Terraform
# =============================================================================
# Este script valida la configuración de Terraform en todos los environments
# y módulos, verificando sintaxis, formato y configuración.
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Contadores
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Función para imprimir headers
print_header() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  $1${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Función para imprimir secciones
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Función para checks exitosos
print_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

# Función para checks fallidos
print_error() {
    echo -e "  ${RED}❌ $1${NC}"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

# Función para warnings
print_warning() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

# Función para info
print_info() {
    echo -e "  ${BLUE}ℹ️  $1${NC}"
}

# Cambiar al directorio del script
cd "$(dirname "$0")"

print_header "VALIDACIÓN DE INFRAESTRUCTURA TERRAFORM"

# =============================================================================
# 1. VERIFICACIÓN DE ESTRUCTURA
# =============================================================================
print_section "1️⃣  VERIFICACIÓN DE ESTRUCTURA"

# Verificar que estamos en el directorio correcto
if [ ! -f "provider.tf" ]; then
    print_error "No se encuentra provider.tf - directorio incorrecto"
    exit 1
else
    print_success "Directorio correcto (provider.tf encontrado)"
fi

# Contar archivos .tf
TF_FILES=$(find . -name "*.tf" -type f | wc -l)
print_info "Archivos .tf encontrados: $TF_FILES"

# Verificar módulos
print_info "Verificando módulos..."
EXPECTED_MODULES=("vpc" "ecs_fargate" "rds_aurora" "dynamodb" "s3" "cognito" "ecr" "iam" "sns" "sqs")
MODULES_FOUND=0

for module in "${EXPECTED_MODULES[@]}"; do
    if [ -d "modules/$module" ]; then
        print_success "Módulo $module"
        ((MODULES_FOUND++))
    else
        print_error "Módulo $module NO encontrado"
    fi
done

if [ $MODULES_FOUND -eq ${#EXPECTED_MODULES[@]} ]; then
    print_success "Todos los módulos presentes ($MODULES_FOUND/10)"
else
    print_error "Faltan módulos ($MODULES_FOUND/10)"
fi

# Verificar environments
print_info "Verificando environments..."
for env in dev prod; do
    if [ -d "environments/$env" ]; then
        if [ -f "environments/$env/main.tf" ]; then
            print_success "Environment $env (main.tf presente)"
        else
            print_error "Environment $env sin main.tf"
        fi
    else
        print_error "Environment $env NO encontrado"
    fi
done

# =============================================================================
# 2. VERIFICACIÓN DE ARCHIVOS REQUERIDOS EN MÓDULOS
# =============================================================================
print_section "2️⃣  VERIFICACIÓN DE ARCHIVOS EN MÓDULOS"

for module_dir in modules/*/; do
    module_name=$(basename "$module_dir")
    print_info "Módulo: $module_name"
    
    has_main=false
    has_variables=false
    has_outputs=false
    
    if [ -f "$module_dir/main.tf" ]; then
        has_main=true
        echo -n "    ✓ main.tf "
    else
        echo -n "    ✗ main.tf "
    fi
    
    if [ -f "$module_dir/variables.tf" ]; then
        has_variables=true
        echo -n "✓ variables.tf "
    else
        echo -n "✗ variables.tf "
    fi
    
    if [ -f "$module_dir/outputs.tf" ]; then
        has_outputs=true
        echo "✓ outputs.tf"
    else
        echo "✗ outputs.tf"
    fi
    
    if [ "$has_main" = true ] && [ "$has_variables" = true ] && [ "$has_outputs" = true ]; then
        print_success "$module_name completo"
    elif [ "$has_main" = true ] && [ "$has_variables" = true ]; then
        print_warning "$module_name sin outputs.tf (opcional)"
    else
        print_error "$module_name incompleto"
    fi
done

# =============================================================================
# 3. VERIFICACIÓN DE FORMATO
# =============================================================================
print_section "3️⃣  VERIFICACIÓN DE FORMATO TERRAFORM"

print_info "Verificando formato de archivos raíz..."
if terraform fmt -check provider.tf outputs.tf > /dev/null 2>&1; then
    print_success "Archivos raíz correctamente formateados"
else
    print_warning "Archivos raíz necesitan formateo (terraform fmt)"
fi

print_info "Verificando formato de módulos..."
MODULES_WITH_FORMAT_ISSUES=0
for module_dir in modules/*/; do
    module_name=$(basename "$module_dir")
    if terraform fmt -check "$module_dir" > /dev/null 2>&1; then
        echo -n ""  # Silencioso si está OK
    else
        print_warning "Módulo $module_name necesita formateo"
        ((MODULES_WITH_FORMAT_ISSUES++))
    fi
done

if [ $MODULES_WITH_FORMAT_ISSUES -eq 0 ]; then
    print_success "Todos los módulos correctamente formateados"
fi

# =============================================================================
# 4. VALIDACIÓN DE ENVIRONMENTS
# =============================================================================
print_section "4️⃣  VALIDACIÓN DE CONFIGURACIÓN TERRAFORM"

for env in dev prod; do
    env_dir="environments/$env"
    
    if [ ! -d "$env_dir" ]; then
        print_error "Environment $env no existe"
        continue
    fi
    
    print_info "Validando environment: $env"
    
    cd "$env_dir"
    
    # Inicializar (sin backend para testing)
    print_info "  Inicializando Terraform..."
    if terraform init -backend=false > /dev/null 2>&1; then
        print_success "  Terraform init exitoso ($env)"
    else
        print_error "  Terraform init falló ($env)"
        cd ../..
        continue
    fi
    
    # Validar configuración
    print_info "  Validando configuración..."
    VALIDATION_OUTPUT=$(terraform validate 2>&1)
    
    if echo "$VALIDATION_OUTPUT" | grep -q "Success!"; then
        print_success "  Configuración válida ($env)"
        
        # Verificar si hay warnings
        if echo "$VALIDATION_OUTPUT" | grep -q "Warning:"; then
            WARNING_COUNT=$(echo "$VALIDATION_OUTPUT" | grep -c "Warning:" || true)
            print_warning "  $WARNING_COUNT warning(s) encontrados ($env)"
        fi
    else
        print_error "  Configuración inválida ($env)"
        echo "$VALIDATION_OUTPUT"
    fi
    
    cd ../..
done

# =============================================================================
# 5. VERIFICACIÓN DE DOCUMENTACIÓN
# =============================================================================
print_section "5️⃣  VERIFICACIÓN DE DOCUMENTACIÓN"

REQUIRED_DOCS=("README.md" "ARCHITECTURE.md" "COMPLETION_REPORT.md")
for doc in "${REQUIRED_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        print_success "Documentación: $doc"
    else
        print_error "Documentación faltante: $doc"
    fi
done

# Verificar si existe archivo de variables ejemplo
if [ -f "terraform.tfvars.example" ]; then
    print_success "Archivo de ejemplo de variables presente"
else
    print_warning "terraform.tfvars.example no encontrado (recomendado)"
fi

# =============================================================================
# 6. VERIFICACIÓN DE .gitignore
# =============================================================================
print_section "6️⃣  VERIFICACIÓN DE .gitignore"

if [ -f ".gitignore" ]; then
    print_success ".gitignore presente"
    
    # Verificar contenido crítico
    CRITICAL_PATTERNS=(".terraform/" "*.tfstate" "*.tfvars" ".terraform.lock.hcl")
    for pattern in "${CRITICAL_PATTERNS[@]}"; do
        if grep -q "$pattern" .gitignore; then
            echo -n ""  # Silencioso
        else
            print_warning "Patrón '$pattern' no encontrado en .gitignore"
        fi
    done
else
    print_error ".gitignore no encontrado"
fi

# =============================================================================
# 7. ANÁLISIS DE DEPENDENCIAS ENTRE MÓDULOS
# =============================================================================
print_section "7️⃣  ANÁLISIS DE DEPENDENCIAS"

print_info "Verificando referencias entre módulos en environments/dev/main.tf..."

if [ -f "environments/dev/main.tf" ]; then
    # Contar módulos declarados
    MODULE_CALLS=$(grep -c "^module \"" environments/dev/main.tf || true)
    print_info "Módulos declarados en dev: $MODULE_CALLS"
    
    # Verificar que todos los módulos son referenciados
    for module in "${EXPECTED_MODULES[@]}"; do
        if grep -q "module \"$module\"" environments/dev/main.tf; then
            echo -n ""  # Silencioso
        else
            print_warning "Módulo $module no referenciado en dev/main.tf"
        fi
    done
    
    print_success "Análisis de dependencias completado"
else
    print_error "No se puede analizar dependencias (falta dev/main.tf)"
fi

# =============================================================================
# 8. VERIFICACIÓN DE PROVEEDORES
# =============================================================================
print_section "8️⃣  VERIFICACIÓN DE PROVEEDORES"

if [ -f "provider.tf" ]; then
    print_success "provider.tf presente"
    
    # Verificar providers críticos
    if grep -q "aws" provider.tf; then
        print_success "Provider AWS configurado"
    else
        print_error "Provider AWS no configurado"
    fi
    
    if grep -q "random" provider.tf; then
        print_success "Provider Random configurado"
    else
        print_warning "Provider Random no configurado (puede ser necesario)"
    fi
else
    print_error "provider.tf no encontrado"
fi

# =============================================================================
# RESUMEN FINAL
# =============================================================================
print_header "RESUMEN DE VALIDACIÓN"

echo ""
echo -e "${BOLD}Estadísticas:${NC}"
echo -e "  Total de checks:    ${BOLD}$TOTAL_CHECKS${NC}"
echo -e "  ${GREEN}✅ Exitosos:        $PASSED_CHECKS${NC}"
echo -e "  ${RED}❌ Fallidos:        $FAILED_CHECKS${NC}"
echo -e "  ${YELLOW}⚠️  Advertencias:    $WARNINGS${NC}"
echo ""

# Calcular porcentaje de éxito
if [ $TOTAL_CHECKS -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    echo -e "${BOLD}Tasa de éxito: $SUCCESS_RATE%${NC}"
    echo ""
fi

# Determinar estado general
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ ¡VALIDACIÓN EXITOSA!${NC}"
    echo ""
    echo -e "${GREEN}La infraestructura Terraform está correctamente configurada.${NC}"
    echo -e "${GREEN}Todos los módulos y environments están listos para uso.${NC}"
    
    if [ $WARNINGS -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}Nota: Se encontraron $WARNINGS advertencias menores que pueden ignorarse.${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}Próximos pasos:${NC}"
    echo "  1. Configurar backend remoto (S3 + DynamoDB)"
    echo "  2. Crear terraform.tfvars con valores específicos"
    echo "  3. Ejecutar 'terraform plan' en environments/dev"
    echo "  4. Revisar y aplicar cambios con 'terraform apply'"
    echo ""
    
    exit 0
else
    echo -e "${RED}${BOLD}❌ VALIDACIÓN FALLIDA${NC}"
    echo ""
    echo -e "${RED}Se encontraron $FAILED_CHECKS errores que deben corregirse.${NC}"
    echo ""
    echo -e "${BOLD}Revisa los errores arriba y corrígelos antes de continuar.${NC}"
    echo ""
    
    exit 1
fi
