#!/usr/bin/env python3
"""
Validación de GitHub Actions Workflows - FASE 7
Verifica sintaxis YAML, referencias, y configuración
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Colores ANSI
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

errors = 0
warnings = 0

def print_result(success: bool, message: str):
    """Imprime resultado con formato"""
    global errors
    if success:
        print(f"{GREEN}✅ {message}{NC}")
    else:
        print(f"{RED}❌ {message}{NC}")
        errors += 1

def print_warning(message: str):
    """Imprime warning"""
    global warnings
    print(f"{YELLOW}⚠️  {message}{NC}")
    warnings += 1

def print_info(message: str):
    """Imprime información"""
    print(f"ℹ️  {message}")

def print_header(title: str):
    """Imprime header de sección"""
    print(f"\n{BLUE}{title}{NC}")
    print("-" * 50)

def validate_yaml_syntax(file_path: Path) -> bool:
    """Valida sintaxis YAML básica"""
    try:
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True
    except ImportError:
        print_warning(f"PyYAML no instalado - usando validación básica")
        # Validación básica sin PyYAML
        return validate_yaml_basic(file_path)
    except yaml.YAMLError as e:
        print(f"  Error: {e}")
        return False

def validate_yaml_basic(file_path: Path) -> bool:
    """Validación YAML básica sin dependencias"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar indentación consistente
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if line.strip() and line[0] == '\t':
                print(f"  Línea {i}: Usar espacios, no tabs")
                return False
        
        # Verificar pares de llaves/corchetes
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            print(f"  Llaves desbalanceadas: {open_braces} abiertas, {close_braces} cerradas")
            return False
        
        return True
    except Exception as e:
        print(f"  Error al leer archivo: {e}")
        return False

def check_file_exists(file_path: Path) -> bool:
    """Verifica si un archivo existe"""
    return file_path.exists() and file_path.is_file()

def grep_in_file(file_path: Path, pattern: str) -> bool:
    """Busca un patrón en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return re.search(pattern, content, re.MULTILINE) is not None
    except Exception as e:
        print(f"  Error al buscar en {file_path}: {e}")
        return False

def count_lines(file_path: Path) -> int:
    """Cuenta líneas en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def main():
    """Función principal de validación"""
    print(f"{BLUE}{'='*50}")
    print("🔍 Validando GitHub Actions Workflows - FASE 7")
    print(f"{'='*50}{NC}\n")
    
    # Cambiar al directorio .github
    script_dir = Path(__file__).parent
    github_dir = script_dir.parent
    workflows_dir = script_dir
    
    # ============================================
    # 1. Validar sintaxis YAML
    # ============================================
    print_header("📝 1. Validando sintaxis YAML")
    
    ci_yml = workflows_dir / 'ci.yml'
    cd_yml = workflows_dir / 'cd.yml'
    
    if check_file_exists(ci_yml):
        result = validate_yaml_syntax(ci_yml)
        print_result(result, "ci.yml: sintaxis YAML correcta")
    else:
        print_result(False, "ci.yml NO encontrado")
    
    if check_file_exists(cd_yml):
        result = validate_yaml_syntax(cd_yml)
        print_result(result, "cd.yml: sintaxis YAML correcta")
    else:
        print_result(False, "cd.yml NO encontrado")
    
    # ============================================
    # 2. Validar Actions usadas
    # ============================================
    print_header("🔌 2. Validando GitHub Actions usadas")
    
    required_actions = {
        'actions/checkout@v4': 'Checkout repository',
        'actions/setup-python@v5': 'Setup Python',
        'docker/setup-buildx-action@v3': 'Setup Docker Buildx',
        'docker/metadata-action@v5': 'Docker metadata',
        'docker/build-push-action@v5': 'Build and push Docker',
        'aws-actions/configure-aws-credentials@v4': 'Configure AWS credentials',
        'aws-actions/amazon-ecr-login@v2': 'ECR login',
        'aws-actions/amazon-ecs-render-task-definition@v1': 'ECS render task definition',
        'aws-actions/amazon-ecs-deploy-task-definition@v1': 'ECS deploy task definition',
        'dorny/paths-filter@v3': 'Path filtering',
        'aquasecurity/trivy-action@master': 'Trivy security scan',
        'hashicorp/setup-terraform@v3': 'Setup Terraform',
    }
    
    for action, description in required_actions.items():
        found = (grep_in_file(ci_yml, f'uses: {action}') or 
                grep_in_file(cd_yml, f'uses: {action}'))
        print_result(found, f"{action} ({description})")
    
    # ============================================
    # 3. Validar secrets
    # ============================================
    print_header("🔐 3. Validando secrets referenciados")
    
    required_secrets = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'ECR_REPO_CONTENT',
        'ECR_REPO_USER',
        'ECR_REPO_ML',
        'TF_VAR_db_password',
    ]
    
    for secret in required_secrets:
        pattern = f'secrets\\.{secret}'
        found = (grep_in_file(ci_yml, pattern) or 
                grep_in_file(cd_yml, pattern))
        print_result(found, f"Secret {secret} referenciado")
    
    # ============================================
    # 4. Validar environments
    # ============================================
    print_header("🌍 4. Validando environments")
    
    # Los environments son dinámicos, verificar que se usan correctamente
    env_checks = [
        (r'(staging|\- staging)', "Environment 'staging' referenciado"),
        (r'(production|\- production)', "Environment 'production' referenciado"),
        (r'environment:\s*\n\s*name:.*infrastructure', "Environment '*-infrastructure' usado"),
        (r'needs\.detect-changes\.outputs\.environment', "Environments dinámicos configurados"),
    ]
    
    for pattern, description in env_checks:
        found = grep_in_file(cd_yml, pattern)
        print_result(found, description)
    
    # ============================================
    # 5. Validar path filters
    # ============================================
    print_header("📂 5. Validando path filters")
    
    expected_paths = [
        'services/api/content-service',
        'services/api/user-service',
        'services/api/ml-service',
        'infra/terraform',
    ]
    
    for path in expected_paths:
        found = grep_in_file(ci_yml, path)
        print_result(found, f"Path filter '{path}' configurado")
    
    # ============================================
    # 6. Validar job dependencies
    # ============================================
    print_header("🔗 6. Validando dependencias entre jobs")
    
    # CI dependencies
    checks = [
        (ci_yml, r'needs:\s*detect-changes', "CI: Jobs dependen de detect-changes"),
        (cd_yml, r'needs:.*detect-changes', "CD: build-and-push depende de detect-changes"),
        (cd_yml, r'needs:.*build-and-push', "CD: deploy-ecs depende de build-and-push"),
    ]
    
    for file_path, pattern, description in checks:
        found = grep_in_file(file_path, pattern)
        print_result(found, description)
    
    # ============================================
    # 7. Validar triggers
    # ============================================
    print_header("⚡ 7. Validando triggers de workflows")
    
    triggers = [
        (ci_yml, r'on:\s*\n\s*push:', "CI: trigger 'push'"),
        (ci_yml, r'pull_request:', "CI: trigger 'pull_request'"),
        (cd_yml, r'on:\s*\n\s*push:', "CD: trigger 'push'"),
        (cd_yml, r'workflow_dispatch:', "CD: trigger 'workflow_dispatch'"),
        (cd_yml, r'- main', "CD: branch 'main' en trigger"),
        (cd_yml, r'- staging', "CD: branch 'staging' en trigger"),
    ]
    
    for file_path, pattern, description in triggers:
        found = grep_in_file(file_path, pattern)
        print_result(found, description)
    
    # ============================================
    # 8. Validar rollback mechanism
    # ============================================
    print_header("🔄 8. Validando mecanismo de rollback")
    
    rollback_checks = [
        (r'previous-task-def', "Previous task definition se guarda"),
        (r'if:\s*failure\(\)', "Step con 'if: failure()' existe"),
        (r'task-definition.*\$\{\{\s*steps\.get-task-def\.outputs\.previous-task-def', "Rollback usa previous task definition"),
    ]
    
    for pattern, description in rollback_checks:
        found = grep_in_file(cd_yml, pattern)
        print_result(found, f"Rollback: {description}")
    
    # ============================================
    # 9. Validar health checks
    # ============================================
    print_header("🏥 9. Validando health checks")
    
    health_checks = [
        (r'health', "Health check configurado"),
        (r'/health', "Health endpoint '/health' referenciado"),
    ]
    
    for pattern, description in health_checks:
        found = grep_in_file(cd_yml, pattern)
        print_result(found, description)
    
    # ============================================
    # 10. Validar matrix strategy
    # ============================================
    print_header("🎯 10. Validando matrix strategy")
    
    matrix_checks = [
        (ci_yml, r'strategy:\s*\n\s*matrix:', "CI: Matrix strategy configurada"),
        (ci_yml, r'content-service', "CI Matrix: content-service"),
        (ci_yml, r'user-service', "CI Matrix: user-service"),
        (ci_yml, r'ml-service', "CI Matrix: ml-service"),
    ]
    
    for file_path, pattern, description in matrix_checks:
        found = grep_in_file(file_path, pattern)
        print_result(found, description)
    
    # ============================================
    # 11. Validar documentación
    # ============================================
    print_header("📚 11. Validando documentación")
    
    docs = [
        github_dir / 'SECRETS_SETUP.md',
        github_dir / 'ENVIRONMENTS_SETUP.md',
        github_dir / 'WORKFLOWS_GUIDE.md',
        github_dir / 'README.md',
    ]
    
    for doc in docs:
        if check_file_exists(doc):
            lines = count_lines(doc)
            print_result(True, f"{doc.name} existe ({lines} líneas)")
            if lines < 50:
                print_warning(f"  ├─ {doc.name} tiene < 50 líneas (puede estar incompleto)")
        else:
            print_result(False, f"{doc.name} NO existe")
    
    # ============================================
    # 12. Validar ejecución condicional
    # ============================================
    print_header("🎚️  12. Validando ejecución condicional")
    
    conditional_checks = [
        (r'if:.*needs\.detect-changes\.outputs', "Jobs usan outputs de detect-changes"),
        (r'if:.*github\.event(_name|\.inputs)', "CD usa inputs/eventos de workflow_dispatch"),
    ]
    
    for pattern, description in conditional_checks:
        found_ci = grep_in_file(ci_yml, pattern)
        found_cd = grep_in_file(cd_yml, pattern)
        found = found_ci or found_cd
        print_result(found, f"Conditional execution: {description}")
    
    # ============================================
    # RESUMEN
    # ============================================
    print(f"\n{BLUE}{'='*50}")
    print("📊 RESUMEN DE VALIDACIÓN")
    print(f"{'='*50}{NC}\n")
    
    # Estadísticas de workflows
    ci_lines = count_lines(ci_yml)
    cd_lines = count_lines(cd_yml)
    total_workflow_lines = ci_lines + cd_lines
    
    print("📝 Workflows:")
    print(f"  ├─ ci.yml: {ci_lines} líneas")
    print(f"  ├─ cd.yml: {cd_lines} líneas")
    print(f"  └─ Total: {total_workflow_lines} líneas\n")
    
    # Estadísticas de documentación
    total_doc_lines = sum(count_lines(doc) for doc in docs if check_file_exists(doc))
    for doc in docs:
        if check_file_exists(doc):
            doc_lines = count_lines(doc)
            print(f"📚 {doc.name}: {doc_lines} líneas")
    print(f"  └─ Total documentación: {total_doc_lines} líneas\n")
    
    # Jobs contados
    print("🔧 Componentes detectados:")
    ci_jobs = len(re.findall(r'^\s{2}\w+(-\w+)*:', open(ci_yml).read(), re.MULTILINE))
    cd_jobs = len(re.findall(r'^\s{2}\w+(-\w+)*:', open(cd_yml).read(), re.MULTILINE))
    print(f"  ├─ CI jobs: ~{ci_jobs}")
    print(f"  ├─ CD jobs: ~{cd_jobs}")
    print(f"  └─ Total jobs: ~{ci_jobs + cd_jobs}\n")
    
    # Resultados finales
    print("🔍 Resultados de validación:")
    print(f"  ├─ Errores: {errors}")
    print(f"  └─ Warnings: {warnings}\n")
    
    if errors == 0:
        print(f"{GREEN}✅ FASE 7 VALIDADA EXITOSAMENTE{NC}\n")
        print("🚀 Los workflows están listos para uso en producción!\n")
        print("Próximos pasos:")
        print("  1. Configurar GitHub Secrets (ver SECRETS_SETUP.md)")
        print("  2. Crear GitHub Environments (ver ENVIRONMENTS_SETUP.md)")
        print("  3. Hacer push a 'staging' para primer deployment\n")
        return 0
    else:
        print(f"{RED}❌ VALIDACIÓN FALLÓ CON {errors} ERROR(ES){NC}\n")
        print("Por favor revisar los errores arriba y corregir antes de usar en producción.\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
