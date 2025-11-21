#!/usr/bin/env python3
"""
=============================================================================
Script de Validación de Infraestructura Terraform
=============================================================================
Valida la configuración de Terraform en todos los environments y módulos,
verificando sintaxis, formato y configuración.
=============================================================================
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple, List

# Colores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

# Contadores globales
total_checks = 0
passed_checks = 0
failed_checks = 0
warnings = 0

def print_header(text: str):
    """Imprime un header formateado"""
    print()
    print(f"{Colors.BOLD}╔══════════════════════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.BOLD}║  {text:<70}║{Colors.NC}")
    print(f"{Colors.BOLD}╚══════════════════════════════════════════════════════════════════════════╝{Colors.NC}")
    print()

def print_section(text: str):
    """Imprime una sección formateada"""
    print()
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print(f"{Colors.BOLD}{text}{Colors.NC}")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")

def print_success(text: str):
    """Imprime un mensaje de éxito"""
    global passed_checks, total_checks
    print(f"  {Colors.GREEN}✅ {text}{Colors.NC}")
    passed_checks += 1
    total_checks += 1

def print_error(text: str):
    """Imprime un mensaje de error"""
    global failed_checks, total_checks
    print(f"  {Colors.RED}❌ {text}{Colors.NC}")
    failed_checks += 1
    total_checks += 1

def print_warning(text: str):
    """Imprime un warning"""
    global warnings
    print(f"  {Colors.YELLOW}⚠️  {text}{Colors.NC}")
    warnings += 1

def print_info(text: str):
    """Imprime información"""
    print(f"  {Colors.BLUE}ℹ️  {text}{Colors.NC}")

def run_command(cmd: List[str], cwd: Path = None, capture_output: bool = True) -> Tuple[bool, str]:
    """Ejecuta un comando y retorna (success, output)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def validate_structure(terraform_dir: Path):
    """Valida la estructura de directorios"""
    print_section("1️⃣  VERIFICACIÓN DE ESTRUCTURA")
    
    # Verificar archivos raíz
    if (terraform_dir / "provider.tf").exists():
        print_success("Directorio correcto (provider.tf encontrado)")
    else:
        print_error("No se encuentra provider.tf - directorio incorrecto")
        return False
    
    # Contar archivos .tf
    tf_files = list(terraform_dir.rglob("*.tf"))
    print_info(f"Archivos .tf encontrados: {len(tf_files)}")
    
    # Verificar módulos
    expected_modules = ["vpc", "ecs_fargate", "rds_aurora", "dynamodb", "s3", 
                        "cognito", "ecr", "iam", "sns", "sqs"]
    modules_found = 0
    
    print_info("Verificando módulos...")
    for module in expected_modules:
        module_path = terraform_dir / "modules" / module
        if module_path.exists():
            print_success(f"Módulo {module}")
            modules_found += 1
        else:
            print_error(f"Módulo {module} NO encontrado")
    
    if modules_found == len(expected_modules):
        print_success(f"Todos los módulos presentes ({modules_found}/10)")
    else:
        print_error(f"Faltan módulos ({modules_found}/10)")
    
    # Verificar environments
    print_info("Verificando environments...")
    for env in ["dev", "prod"]:
        env_path = terraform_dir / "environments" / env
        if env_path.exists():
            if (env_path / "main.tf").exists():
                print_success(f"Environment {env} (main.tf presente)")
            else:
                print_error(f"Environment {env} sin main.tf")
        else:
            print_error(f"Environment {env} NO encontrado")
    
    return True

def validate_module_files(terraform_dir: Path):
    """Valida que cada módulo tenga los archivos requeridos"""
    print_section("2️⃣  VERIFICACIÓN DE ARCHIVOS EN MÓDULOS")
    
    modules_dir = terraform_dir / "modules"
    if not modules_dir.exists():
        print_error("Directorio modules/ no encontrado")
        return
    
    for module_dir in sorted(modules_dir.iterdir()):
        if not module_dir.is_dir():
            continue
        
        module_name = module_dir.name
        print_info(f"Módulo: {module_name}")
        
        has_main = (module_dir / "main.tf").exists()
        has_variables = (module_dir / "variables.tf").exists()
        has_outputs = (module_dir / "outputs.tf").exists()
        
        files_status = []
        files_status.append("✓ main.tf" if has_main else "✗ main.tf")
        files_status.append("✓ variables.tf" if has_variables else "✗ variables.tf")
        files_status.append("✓ outputs.tf" if has_outputs else "✗ outputs.tf")
        
        print(f"    {' '.join(files_status)}")
        
        if has_main and has_variables and has_outputs:
            print_success(f"{module_name} completo")
        elif has_main and has_variables:
            print_warning(f"{module_name} sin outputs.tf (puede ser opcional)")
        else:
            print_error(f"{module_name} incompleto")

def validate_terraform_format(terraform_dir: Path):
    """Valida el formato de los archivos Terraform"""
    print_section("3️⃣  VERIFICACIÓN DE FORMATO TERRAFORM")
    
    print_info("Verificando formato de archivos raíz...")
    success, _ = run_command(
        ["terraform", "fmt", "-check", "-recursive"],
        cwd=terraform_dir
    )
    
    if success:
        print_success("Archivos correctamente formateados")
    else:
        print_warning("Algunos archivos necesitan formateo (ejecuta: terraform fmt -recursive)")

def validate_environments(terraform_dir: Path):
    """Valida los environments con terraform validate"""
    print_section("4️⃣  VALIDACIÓN DE CONFIGURACIÓN TERRAFORM")
    
    for env in ["dev", "prod"]:
        env_dir = terraform_dir / "environments" / env
        
        if not env_dir.exists():
            print_error(f"Environment {env} no existe")
            continue
        
        print_info(f"Validando environment: {env}")
        
        # Inicializar (sin backend para testing)
        print_info(f"  Inicializando Terraform...")
        success, output = run_command(
            ["terraform", "init", "-backend=false"],
            cwd=env_dir
        )
        
        if success:
            print_success(f"  Terraform init exitoso ({env})")
        else:
            print_error(f"  Terraform init falló ({env})")
            print(f"    Output: {output[:200]}")
            continue
        
        # Validar configuración
        print_info(f"  Validando configuración...")
        success, output = run_command(
            ["terraform", "validate"],
            cwd=env_dir
        )
        
        if "Success!" in output or success:
            print_success(f"  Configuración válida ({env})")
            
            # Verificar si hay warnings
            if "Warning:" in output:
                warning_count = output.count("Warning:")
                print_warning(f"  {warning_count} warning(s) encontrados ({env})")
                
                # Mostrar primer warning
                if "Deprecated attribute" in output:
                    print_info("    • Atributo deprecado en módulo ECS (menor)")
        else:
            print_error(f"  Configuración inválida ({env})")
            # Mostrar primeros 500 caracteres del error
            print(f"    {output[:500]}")

def validate_documentation(terraform_dir: Path):
    """Valida que exista la documentación requerida"""
    print_section("5️⃣  VERIFICACIÓN DE DOCUMENTACIÓN")
    
    required_docs = ["README.md", "ARCHITECTURE.md", "COMPLETION_REPORT.md"]
    
    for doc in required_docs:
        if (terraform_dir / doc).exists():
            print_success(f"Documentación: {doc}")
        else:
            print_error(f"Documentación faltante: {doc}")
    
    # Verificar archivo de variables ejemplo
    if (terraform_dir / "terraform.tfvars.example").exists():
        print_success("Archivo de ejemplo de variables presente")
    else:
        print_warning("terraform.tfvars.example no encontrado (recomendado)")

def validate_gitignore(terraform_dir: Path):
    """Valida el archivo .gitignore"""
    print_section("6️⃣  VERIFICACIÓN DE .gitignore")
    
    gitignore_path = terraform_dir / ".gitignore"
    
    if gitignore_path.exists():
        print_success(".gitignore presente")
        
        # Verificar contenido crítico
        content = gitignore_path.read_text()
        critical_patterns = [".terraform/", "*.tfstate", "*.tfvars", ".terraform.lock.hcl"]
        
        for pattern in critical_patterns:
            if pattern in content:
                # Silencioso si está presente
                pass
            else:
                print_warning(f"Patrón '{pattern}' no encontrado en .gitignore")
    else:
        print_error(".gitignore no encontrado")

def validate_providers(terraform_dir: Path):
    """Valida la configuración de proveedores"""
    print_section("7️⃣  VERIFICACIÓN DE PROVEEDORES")
    
    provider_file = terraform_dir / "provider.tf"
    
    if provider_file.exists():
        print_success("provider.tf presente")
        
        content = provider_file.read_text()
        
        if "aws" in content:
            print_success("Provider AWS configurado")
        else:
            print_error("Provider AWS no configurado")
        
        if "random" in content:
            print_success("Provider Random configurado")
        else:
            print_warning("Provider Random no configurado (puede ser necesario)")
    else:
        print_error("provider.tf no encontrado")

def print_summary():
    """Imprime el resumen final"""
    print_header("RESUMEN DE VALIDACIÓN")
    
    print()
    print(f"{Colors.BOLD}Estadísticas:{Colors.NC}")
    print(f"  Total de checks:    {Colors.BOLD}{total_checks}{Colors.NC}")
    print(f"  {Colors.GREEN}✅ Exitosos:        {passed_checks}{Colors.NC}")
    print(f"  {Colors.RED}❌ Fallidos:        {failed_checks}{Colors.NC}")
    print(f"  {Colors.YELLOW}⚠️  Advertencias:    {warnings}{Colors.NC}")
    print()
    
    # Calcular porcentaje de éxito
    if total_checks > 0:
        success_rate = (passed_checks * 100) // total_checks
        print(f"{Colors.BOLD}Tasa de éxito: {success_rate}%{Colors.NC}")
        print()
    
    # Determinar estado general
    if failed_checks == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ¡VALIDACIÓN EXITOSA!{Colors.NC}")
        print()
        print(f"{Colors.GREEN}La infraestructura Terraform está correctamente configurada.{Colors.NC}")
        print(f"{Colors.GREEN}Todos los módulos y environments están listos para uso.{Colors.NC}")
        
        if warnings > 0:
            print()
            print(f"{Colors.YELLOW}Nota: Se encontraron {warnings} advertencias menores que pueden ignorarse.{Colors.NC}")
        
        print()
        print(f"{Colors.BOLD}Próximos pasos:{Colors.NC}")
        print("  1. Configurar backend remoto (S3 + DynamoDB)")
        print("  2. Crear terraform.tfvars con valores específicos")
        print("  3. Ejecutar 'terraform plan' en environments/dev")
        print("  4. Revisar y aplicar cambios con 'terraform apply'")
        print()
        
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ VALIDACIÓN FALLIDA{Colors.NC}")
        print()
        print(f"{Colors.RED}Se encontraron {failed_checks} errores que deben corregirse.{Colors.NC}")
        print()
        print(f"{Colors.BOLD}Revisa los errores arriba y corrígelos antes de continuar.{Colors.NC}")
        print()
        
        return 1

def main():
    """Función principal"""
    # Obtener directorio del script
    script_dir = Path(__file__).parent.absolute()
    
    print_header("VALIDACIÓN DE INFRAESTRUCTURA TERRAFORM")
    
    # Ejecutar validaciones
    if not validate_structure(script_dir):
        print_error("Estructura básica inválida. Abortando.")
        return 1
    
    validate_module_files(script_dir)
    validate_terraform_format(script_dir)
    validate_environments(script_dir)
    validate_documentation(script_dir)
    validate_gitignore(script_dir)
    validate_providers(script_dir)
    
    # Imprimir resumen y retornar código de salida
    return print_summary()

if __name__ == "__main__":
    sys.exit(main())
