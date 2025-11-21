#!/usr/bin/env python3
"""
Script de Verificación - Content Service
Verifica que todas las migraciones y configuración estén correctas
"""

import asyncio
import sys
import os
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(80)}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.END}\n")

def print_ok(text):
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_info(text):
    print(f"  {text}")

async def main():
    print_header("CONTENT SERVICE - VERIFICACIÓN COMPLETA")
    
    errors = []
    warnings = []
    
    # 1. Verificar estructura de archivos
    print(f"{Colors.YELLOW}[1/8]{Colors.END} Verificando estructura de archivos...")
    
    required_files = [
        "alembic.ini",
        "alembic/env.py",
        "alembic/versions/0001_initial.py",
        "seed_data/seed_content.py",
        "seed_data/content_seed.json",
        "scripts/run_migrations.sh",
        "scripts/seed_all.sh",
        "scripts/quick_migrate.sh",
        "scripts/create_migration.sh",
        "scripts/rollback.sh",
        ".env.example",
        "scripts/README.md",
        "requirements.txt",
        "app/main.py",
        "app/models.py",
    ]
    
    for file in required_files:
        if Path(file).exists():
            print_ok(f"Archivo existe: {file}")
        else:
            print_error(f"Archivo faltante: {file}")
            errors.append(f"Missing file: {file}")
    
    # 2. Verificar permisos de scripts
    print(f"\n{Colors.YELLOW}[2/8]{Colors.END} Verificando permisos de scripts...")
    
    scripts = [
        "scripts/run_migrations.sh",
        "scripts/seed_all.sh",
        "scripts/quick_migrate.sh",
        "scripts/create_migration.sh",
        "scripts/rollback.sh",
    ]
    
    for script in scripts:
        if Path(script).exists():
            # En Windows, simplemente verificar que existe
            print_ok(f"Script disponible: {script}")
        else:
            print_error(f"Script faltante: {script}")
            errors.append(f"Missing script: {script}")
    
    # 3. Verificar dependencias Python
    print(f"\n{Colors.YELLOW}[3/8]{Colors.END} Verificando dependencias...")
    
    try:
        import alembic
        from alembic import __version__ as alembic_version
        print_ok(f"Alembic instalado: v{alembic_version}")
    except ImportError:
        print_error("Alembic no está instalado")
        errors.append("Alembic not installed")
    except AttributeError:
        print_ok("Alembic instalado")
    
    try:
        import sqlalchemy
        print_ok(f"SQLAlchemy instalado: v{sqlalchemy.__version__}")
    except ImportError:
        print_error("SQLAlchemy no está instalado")
        errors.append("SQLAlchemy not installed")
    
    try:
        import asyncpg
        print_ok(f"asyncpg instalado")
    except ImportError:
        print_error("asyncpg no está instalado")
        errors.append("asyncpg not installed")
    
    try:
        import fastapi
        print_ok(f"FastAPI instalado: v{fastapi.__version__}")
    except ImportError:
        print_error("FastAPI no está instalado")
        errors.append("FastAPI not installed")
    
    # 4. Verificar configuración de Alembic
    print(f"\n{Colors.YELLOW}[4/8]{Colors.END} Verificando configuración de Alembic...")
    
    if Path("alembic.ini").exists():
        with open("alembic.ini") as f:
            content = f.read()
            if "script_location = alembic" in content:
                print_ok("script_location configurado correctamente")
            else:
                print_error("script_location no configurado")
                errors.append("Invalid alembic.ini config")
    
    # 5. Verificar env.py
    print(f"\n{Colors.YELLOW}[5/8]{Colors.END} Verificando env.py...")
    
    if Path("alembic/env.py").exists():
        with open("alembic/env.py") as f:
            content = f.read()
            checks = {
                "run_async_migrations": "Función async encontrada",
                "target_metadata": "target_metadata configurado",
                "get_settings": "Carga settings correctamente",
            }
            
            for check, msg in checks.items():
                if check in content:
                    print_ok(msg)
                else:
                    print_warning(f"No encontrado: {check}")
                    warnings.append(f"env.py missing: {check}")
    
    # 6. Verificar migración inicial
    print(f"\n{Colors.YELLOW}[6/8]{Colors.END} Verificando migración inicial...")
    
    migration_file = Path("alembic/versions/0001_initial.py")
    if migration_file.exists():
        with open(migration_file) as f:
            content = f.read()
            
            tables = [
                "languages", "topics", "levels", "exercises",
                "signs", "translations", "achievements"
            ]
            
            for table in tables:
                if f"create_table('{table}'" in content or f'create_table("{table}"' in content:
                    print_ok(f"Tabla definida: {table}")
                else:
                    print_error(f"Tabla faltante: {table}")
                    errors.append(f"Missing table in migration: {table}")
            
            # Verificar enums
            enums = ["difficultylevel", "exercisetype", "conditiontype"]
            for enum in enums:
                if enum in content.lower():
                    print_ok(f"Enum definido: {enum}")
                else:
                    print_warning(f"Enum no encontrado: {enum}")
                    warnings.append(f"Missing enum: {enum}")
    
    # 7. Verificar seed data
    print(f"\n{Colors.YELLOW}[7/8]{Colors.END} Verificando seed data...")
    
    if Path("seed_data/content_seed.json").exists():
        import json
        with open("seed_data/content_seed.json") as f:
            try:
                data = json.load(f)
                if "languages" in data:
                    print_ok(f"Seed data: {len(data['languages'])} idiomas")
                if "topics" in data:
                    print_ok(f"Seed data: {len(data['topics'])} temas")
                if "levels" in data:
                    print_ok(f"Seed data: {len(data['levels'])} niveles")
            except json.JSONDecodeError as e:
                print_error(f"JSON inválido: {e}")
                errors.append("Invalid JSON in seed data")
    
    # 8. Verificar variables de entorno
    print(f"\n{Colors.YELLOW}[8/8]{Colors.END} Verificando variables de entorno...")
    
    env_vars = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ]
    
    if Path(".env.local").exists():
        print_ok(".env.local existe")
        with open(".env.local") as f:
            env_content = f.read()
            for var in env_vars:
                if var in env_content:
                    print_ok(f"Variable definida: {var}")
                else:
                    print_warning(f"Variable faltante: {var}")
                    warnings.append(f"Missing env var: {var}")
    else:
        print_warning(".env.local no existe (usar .env.example como plantilla)")
        warnings.append("No .env.local file")
    
    # Resumen final
    print_header("RESUMEN DE VERIFICACIÓN")
    
    print(f"Archivos verificados: {len(required_files)}")
    print(f"Scripts verificados: {len(scripts)}")
    print(f"Dependencias verificadas: 4")
    
    if errors:
        print(f"\n{Colors.RED}Errores encontrados: {len(errors)}{Colors.END}")
        for error in errors:
            print_error(error)
    else:
        print(f"\n{Colors.GREEN}✓ Sin errores críticos{Colors.END}")
    
    if warnings:
        print(f"\n{Colors.YELLOW}Advertencias: {len(warnings)}{Colors.END}")
        for warning in warnings:
            print_warning(warning)
    
    if not errors and not warnings:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡TODO VERIFICADO CORRECTAMENTE!{Colors.END}")
        print_header("SIGUIENTE PASO: EJECUTAR MIGRACIONES")
        print(f"  Windows PowerShell:")
        print(f'    & "C:\\Program Files\\Git\\bin\\bash.exe" scripts/run_migrations.sh local')
        print(f"\n  Git Bash / Linux:")
        print(f"    ./scripts/run_migrations.sh local")
        return 0
    elif errors:
        print(f"\n{Colors.RED}❌ VERIFICACIÓN FALLIDA - CORREGIR ERRORES{Colors.END}")
        return 1
    else:
        print(f"\n{Colors.YELLOW}⚠ VERIFICACIÓN COMPLETADA CON ADVERTENCIAS{Colors.END}")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
