#!/usr/bin/env python3
"""
Script de Verificación Ligero - Content Service
Verifica estructura sin requerir dependencias instaladas
"""

import sys
import json
from pathlib import Path

# Colores
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'=' * 80}{END}")
    print(f"{BLUE}{BOLD}{text.center(80)}{END}")
    print(f"{BLUE}{'=' * 80}{END}\n")

print_header("VERIFICACIÓN RÁPIDA - CONTENT SERVICE FASE 5")

errors = []
warnings = []

# 1. Verificar archivos principales
print(f"{YELLOW}[1/5]{END} Verificando archivos de migración...")

files = {
    "alembic.ini": "Configuración de Alembic",
    "alembic/env.py": "Environment runner asíncrono",
    "alembic/versions/0001_initial.py": "Migración inicial",
    "seed_data/seed_content.py": "Script de seeding",
    "seed_data/content_seed.json": "Datos de seed",
}

for file, desc in files.items():
    if Path(file).exists():
        print(f"{GREEN}✓{END} {desc}: {file}")
    else:
        print(f"{RED}✗{END} {desc}: {file}")
        errors.append(f"Missing: {file}")

# 2. Verificar scripts
print(f"\n{YELLOW}[2/5]{END} Verificando scripts de automatización...")

scripts = {
    "scripts/run_migrations.sh": "Ejecutar migraciones",
    "scripts/seed_all.sh": "Seed multi-servicio",
    "scripts/quick_migrate.sh": "Migración rápida",
    "scripts/create_migration.sh": "Crear migración",
    "scripts/rollback.sh": "Rollback de migraciones",
}

for script, desc in scripts.items():
    if Path(script).exists():
        size = Path(script).stat().st_size
        print(f"{GREEN}✓{END} {desc}: {script} ({size} bytes)")
    else:
        print(f"{RED}✗{END} {desc}: {script}")
        errors.append(f"Missing: {script}")

# 3. Verificar documentación
print(f"\n{YELLOW}[3/5]{END} Verificando documentación...")

docs = {
    ".env.example": "Template de variables de entorno",
    "scripts/README.md": "Documentación de scripts",
    "MIGRATION_COMPLETE.md": "Resumen de FASE 5",
    "WINDOWS_SETUP.md": "Guía de setup para Windows",
}

for doc, desc in docs.items():
    if Path(doc).exists():
        size = Path(doc).stat().st_size
        lines = len(Path(doc).read_text(encoding='utf-8').split('\n'))
        print(f"{GREEN}✓{END} {desc}: {doc} ({lines} líneas)")
    else:
        print(f"{YELLOW}⚠{END} {desc}: {doc}")
        warnings.append(f"Missing doc: {doc}")

# 4. Verificar migración inicial
print(f"\n{YELLOW}[4/5]{END} Verificando contenido de migración...")

migration_file = Path("alembic/versions/0001_initial.py")
if migration_file.exists():
    content = migration_file.read_text()
    
    tables = ["languages", "topics", "levels", "exercises", "signs", "translations", "achievements"]
    for table in tables:
        if f"'{table}'" in content or f'"{table}"' in content:
            print(f"{GREEN}✓{END} Tabla definida: {table}")
        else:
            print(f"{RED}✗{END} Tabla faltante: {table}")
            errors.append(f"Missing table: {table}")
    
    enums = ["difficultylevel", "exercisetype", "conditiontype"]
    for enum in enums:
        if enum.lower() in content.lower():
            print(f"{GREEN}✓{END} Enum definido: {enum}")

# 5. Verificar seed data
print(f"\n{YELLOW}[5/5]{END} Verificando datos de seed...")

seed_file = Path("seed_data/content_seed.json")
if seed_file.exists():
    try:
        data = json.loads(seed_file.read_text())
        stats = {
            "languages": len(data.get("languages", [])),
            "topics": len(data.get("topics", [])),
            "levels": len(data.get("levels", [])),
        }
        for key, count in stats.items():
            print(f"{GREEN}✓{END} Seed data - {key}: {count} registros")
    except json.JSONDecodeError as e:
        print(f"{RED}✗{END} JSON inválido: {e}")
        errors.append("Invalid JSON")

# Resumen
print_header("RESUMEN")

total_files = len(files) + len(scripts) + len(docs)
print(f"Archivos verificados: {total_files}")
print(f"Migración inicial: 7 tablas + 3 enums")
print(f"Scripts de automatización: {len(scripts)}")
print(f"Documentación: {len(docs)} archivos")

if errors:
    print(f"\n{RED}❌ Errores encontrados: {len(errors)}{END}")
    for error in errors:
        print(f"  {RED}✗{END} {error}")
    sys.exit(1)

if warnings:
    print(f"\n{YELLOW}⚠ Advertencias: {len(warnings)}{END}")
    for warning in warnings:
        print(f"  {YELLOW}⚠{END} {warning}")

if not errors:
    print(f"\n{GREEN}{BOLD}✅ FASE 5 COMPLETADA CORRECTAMENTE{END}")
    print_header("PRÓXIMOS PASOS")
    print(f"1. Configurar PostgreSQL:")
    print(f"   docker run -d --name postgres-content \\")
    print(f"     -e POSTGRES_USER=postgres \\")
    print(f"     -e POSTGRES_PASSWORD=postgres \\")
    print(f"     -e POSTGRES_DB=content_db \\")
    print(f"     -p 5432:5432 postgres:14-alpine")
    print(f"\n2. Copiar .env.example a .env.local")
    print(f"   cp .env.example .env.local")
    print(f"\n3. Ejecutar migraciones (Windows PowerShell):")
    print(f'   & "C:\\Program Files\\Git\\bin\\bash.exe" scripts/run_migrations.sh local')
    print(f"\n4. Ejecutar migraciones (Git Bash / Linux):")
    print(f"   chmod +x scripts/*.sh")
    print(f"   ./scripts/run_migrations.sh local")
    print(f"\n5. Cargar datos iniciales:")
    print(f"   ./scripts/seed_all.sh local")
    sys.exit(0)
