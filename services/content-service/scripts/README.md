# Content Service - Scripts de Migraciones y Seeding

## 📋 Índice

- [Descripción General](#descripción-general)
- [Scripts Disponibles](#scripts-disponibles)
- [Configuración](#configuración)
- [Workflows Comunes](#workflows-comunes)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

Este directorio contiene scripts de automatización para gestionar migraciones de base de datos y seeding de datos iniciales en **content-service**.

### Stack Tecnológico
- **Alembic 1.12.1**: Manejo de migraciones de PostgreSQL
- **SQLAlchemy 2.0**: ORM asíncrono con `asyncpg`
- **PostgreSQL 14+**: Base de datos relacional

### Estructura de Base de Datos
```
content_db
├── languages      (idiomas: es, pt-BR, en)
├── topics         (temas: gramática, vocabulario, etc.)
├── levels         (niveles por tema con dificultad)
├── exercises      (ejercicios con opciones JSON)
├── signs          (diccionario de señas con tags)
├── translations   (traducciones i18n)
└── achievements   (logros/gamificación)
```

---

## 📜 Scripts Disponibles

### 1. `run_migrations.sh` - Migraciones Automatizadas

**Propósito**: Ejecuta migraciones de Alembic en diferentes ambientes con validación completa.

**Uso**:
```bash
./scripts/run_migrations.sh [environment]
```

**Ambientes soportados**:
- `local` (default): LocalStack/Docker local
- `dev`: Desarrollo en AWS
- `staging`: Staging en AWS
- `production`: Producción en AWS

**Pasos ejecutados**:
1. ✅ Configura variables de entorno según ambiente
2. ✅ Verifica disponibilidad de PostgreSQL (30 reintentos)
3. ✅ Crea base de datos si no existe
4. ✅ Ejecuta `alembic upgrade head`
5. ✅ Verifica existencia de las 7 tablas esperadas

**Ejemplo**:
```bash
# Ambiente local
./scripts/run_migrations.sh local

# Staging (requiere .env.staging)
./scripts/run_migrations.sh staging
```

**Salida esperada**:
```
========================================
  Content Service - Database Migrations
  Environment: local
========================================

[1/5] Setting environment variables...
✓ Environment variables set
  Database: content_db
  Host: localhost:5432

[2/5] Waiting for PostgreSQL...
✓ PostgreSQL is ready

[3/5] Checking database...
✓ Database 'content_db' exists

[4/5] Running Alembic migrations...
  Checking current database revision...
  Current revision: none
  Target revision: 0001_initial
  Applying migrations...
✓ Migrations applied successfully

[5/5] Verifying migrations...
  ✓ Table 'languages' exists
  ✓ Table 'topics' exists
  ✓ Table 'levels' exists
  ✓ Table 'exercises' exists
  ✓ Table 'signs' exists
  ✓ Table 'translations' exists
  ✓ Table 'achievements' exists
✓ All tables verified successfully

========================================
✓ Migrations completed successfully
========================================
```

---

### 2. `seed_all.sh` - Seeding Multi-Servicio

**Propósito**: Ejecuta migraciones + seeding de content-service + user-service en un solo comando.

**Uso**:
```bash
./scripts/seed_all.sh [environment]
```

**Pasos ejecutados**:
1. ✅ Ejecuta `run_migrations.sh` (migraciones de PostgreSQL)
2. ✅ Ejecuta `seed_content.py` (carga `content_seed.json`)
3. ✅ Ejecuta `seed_demo_users.py` en user-service (DynamoDB)
4. ✅ Verifica conteo de registros en cada tabla

**Ejemplo**:
```bash
# Seed completo local
./scripts/seed_all.sh local

# Seed en staging (requiere confirmación para production)
./scripts/seed_all.sh staging
```

**Salida esperada**:
```
========================================
  Multi-Service Database Seeding
  Environment: local
========================================

[1/4] Running migrations...
  Running content-service migrations...
✓ Migrations completed

[2/4] Seeding content-service...
  Executing content seed script...
✓ Content-service seeded successfully

[3/4] Seeding user-service (optional)...
  Found user-service, seeding demo users...
✓ User-service seeded successfully

[4/4] Verifying seeded data...
  Checking content-service data...

  Content-service records:
    Languages:  3
    Topics:     12
    Levels:     36
    Exercises:  108

✓ Content-service data verified

========================================
✓ Seeding completed successfully
========================================
```

---

### 3. `quick_migrate.sh` - Migración Rápida

**Propósito**: Script rápido para desarrollo local sin validaciones exhaustivas.

**Uso**:
```bash
./scripts/quick_migrate.sh
```

**Pasos ejecutados**:
- `alembic upgrade head`
- `alembic current` (muestra revisión actual)

**Ejemplo**:
```bash
./scripts/quick_migrate.sh
```

**Salida esperada**:
```
🚀 Quick Migration - Content Service

📊 Database: content_db@localhost:5432

⬆️  Running migrations...
✅ Migrations completed

Current revision:
0001_initial (head)
```

---

### 4. `create_migration.sh` - Crear Nuevas Migraciones

**Propósito**: Genera nueva migración usando Alembic autogenerate.

**Uso**:
```bash
./scripts/create_migration.sh "mensaje descriptivo"
```

**Ejemplo**:
```bash
# Crear migración para nueva tabla
./scripts/create_migration.sh "add user preferences table"

# Crear migración para agregar columna
./scripts/create_migration.sh "add avatar_url to users"
```

**Salida esperada**:
```
🔧 Creating new migration: add user preferences table

Generating alembic/versions/abc123def456_add_user_preferences_table.py ...  done

✅ Migration created successfully

Next steps:
  1. Review the generated migration file in alembic/versions/
  2. Edit if needed (autogenerate may not catch everything)
  3. Run: alembic upgrade head
```

**⚠️ Notas importantes**:
- **Autogenerate NO detecta todo**: Revisar siempre el archivo generado
- **No detecta**:
  - Cambios de tipo de datos (requiere cast explícito)
  - Renombramientos de columnas/tablas
  - Cambios de constraints complejos
- **Editar manualmente** si es necesario

---

### 5. `rollback.sh` - Rollback de Migraciones

**Propósito**: Revierte migraciones a una versión anterior.

**Uso**:
```bash
./scripts/rollback.sh [steps|base]
```

**Opciones**:
- Sin argumentos: Rollback 1 paso
- `2`: Rollback 2 pasos
- `base`: Rollback completo (⚠️ **DROPS ALL TABLES**)

**Ejemplo**:
```bash
# Rollback 1 migración
./scripts/rollback.sh

# Rollback 2 migraciones
./scripts/rollback.sh 2

# Rollback completo (requiere confirmación)
./scripts/rollback.sh base
```

**Salida esperada**:
```
⚠️  Rollback Migration - Content Service

Current revision:
0001_initial (head)

Rolling back to: -1
✅ Rollback completed

New revision:
(empty)
```

---

## ⚙️ Configuración

### Variables de Entorno Requeridas

#### PostgreSQL (Content Service)
```bash
# Database connection
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=content_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Connection string (auto-generado por scripts)
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
```

#### AWS/DynamoDB (User Service - opcional)
```bash
# AWS credentials (local usa LocalStack)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_ENDPOINT_URL=http://localhost:4566

# DynamoDB table
DYNAMODB_TABLE_USER_DATA=UserData
```

### Archivos de Configuración por Ambiente

Crear archivos `.env.{environment}` en la raíz del servicio:

#### `.env.local` (LocalStack)
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=content_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

#### `.env.dev` (AWS Development)
```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=${SECRET_FROM_AWS_SECRETS_MANAGER}
POSTGRES_DB=content_db_dev
POSTGRES_HOST=dev-postgres.cluster-abc123.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
```

#### `.env.production` (AWS Production)
```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=${SECRET_FROM_AWS_SECRETS_MANAGER}
POSTGRES_DB=content_db
POSTGRES_HOST=prod-postgres.cluster-xyz789.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
```

---

## 🔄 Workflows Comunes

### 1. Setup Inicial (Primera vez)

```bash
# 1. Instalar dependencias
cd services/content-service
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp .env.example .env.local
# Editar .env.local si es necesario

# 3. Iniciar PostgreSQL local (Docker)
docker run -d \
  --name postgres-content \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=content_db \
  -p 5432:5432 \
  postgres:14-alpine

# 4. Ejecutar migraciones
./scripts/run_migrations.sh local

# 5. Cargar datos iniciales
./scripts/seed_all.sh local

# 6. Verificar
psql -h localhost -U postgres -d content_db -c "SELECT * FROM languages;"
```

### 2. Desarrollo Diario

```bash
# Crear nueva migración después de editar models.py
./scripts/create_migration.sh "add new column to exercises"

# Revisar archivo generado
cat alembic/versions/abc123_add_new_column_to_exercises.py

# Aplicar migración
./scripts/quick_migrate.sh

# Si hay error, hacer rollback y corregir
./scripts/rollback.sh
# Editar migration file
./scripts/quick_migrate.sh
```

### 3. CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml (ejemplo)
- name: Run Database Migrations
  run: |
    cd services/content-service
    ./scripts/run_migrations.sh ${{ env.ENVIRONMENT }}

- name: Seed Data (dev/staging only)
  if: env.ENVIRONMENT != 'production'
  run: |
    cd services/content-service
    ./scripts/seed_all.sh ${{ env.ENVIRONMENT }}
```

### 4. Cambios en Modelos

```bash
# 1. Editar app/models.py
vim app/models.py

# 2. Crear migración autogenerada
./scripts/create_migration.sh "add user_preferences table"

# 3. Revisar y editar migración si es necesario
vim alembic/versions/abc123_add_user_preferences_table.py

# 4. Aplicar localmente
./scripts/quick_migrate.sh

# 5. Testear
python -m pytest tests/

# 6. Commit
git add alembic/versions/ app/models.py
git commit -m "feat: add user preferences table"
```

---

## 🐛 Troubleshooting

### Error: "PostgreSQL not ready after 30 attempts"

**Causa**: PostgreSQL no está corriendo o configuración incorrecta.

**Solución**:
```bash
# Verificar si PostgreSQL está corriendo
docker ps | grep postgres

# Si no está corriendo, iniciarlo
docker start postgres-content

# O crear nuevo contenedor
docker run -d \
  --name postgres-content \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=content_db \
  -p 5432:5432 \
  postgres:14-alpine

# Verificar conectividad
pg_isready -h localhost -p 5432 -U postgres
```

### Error: "Database 'content_db' does not exist"

**Causa**: Base de datos no creada (script debería crearla automáticamente).

**Solución**:
```bash
# Crear manualmente
createdb -h localhost -U postgres content_db

# O vía psql
psql -h localhost -U postgres -c "CREATE DATABASE content_db;"
```

### Error: "alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'"

**Causa**: Base de datos tiene revisiones que no existen en `alembic/versions/`.

**Solución**:
```bash
# Opción 1: Rollback a base y re-migrar
./scripts/rollback.sh base
./scripts/quick_migrate.sh

# Opción 2: Limpiar tabla alembic_version y re-migrar
psql -h localhost -U postgres -d content_db -c "DELETE FROM alembic_version;"
./scripts/quick_migrate.sh
```

### Error: "Permission denied: ./run_migrations.sh"

**Causa**: Scripts no tienen permisos de ejecución.

**Solución**:
```bash
# Dar permisos de ejecución a todos los scripts
chmod +x scripts/*.sh

# O individualmente
chmod +x scripts/run_migrations.sh
chmod +x scripts/seed_all.sh
```

### Warning: "Content-service has insufficient data"

**Causa**: `seed_content.py` no se ejecutó correctamente.

**Solución**:
```bash
# Ejecutar seed manualmente con logs
python seed_data/seed_content.py

# Verificar errores
psql -h localhost -U postgres -d content_db -c "SELECT COUNT(*) FROM languages;"
psql -h localhost -U postgres -d content_db -c "SELECT COUNT(*) FROM exercises;"

# Si hay errores, limpiar y re-seed
psql -h localhost -U postgres -d content_db -c "TRUNCATE languages CASCADE;"
./scripts/seed_all.sh local
```

### Error en Production: "Migration failed"

**Causa**: Conflictos con datos existentes.

**Solución**:
```bash
# 1. NO hacer rollback en producción sin backup
# 2. Crear backup primero
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# 3. Revisar logs de Alembic
tail -f alembic.log

# 4. Si es constraint violation, editar migration para manejar datos existentes
vim alembic/versions/abc123_migration.py

# 5. Re-ejecutar
./scripts/run_migrations.sh production
```

---

## 📚 Recursos Adicionales

### Comandos Útiles de Alembic

```bash
# Ver historial de migraciones
alembic history

# Ver revisión actual
alembic current

# Ver todas las heads
alembic heads

# Upgrade a revisión específica
alembic upgrade abc123

# Downgrade a revisión específica
alembic downgrade abc123

# Ver SQL sin ejecutar
alembic upgrade head --sql

# Crear migración vacía (manual)
alembic revision -m "manual migration"
```

### Comandos Útiles de PostgreSQL

```bash
# Conectar a base de datos
psql -h localhost -U postgres -d content_db

# Listar tablas
\dt

# Describir tabla
\d languages

# Ver datos
SELECT * FROM languages LIMIT 10;

# Contar registros
SELECT COUNT(*) FROM exercises;

# Ver revisión de Alembic
SELECT * FROM alembic_version;

# Backup
pg_dump -h localhost -U postgres content_db > backup.sql

# Restore
psql -h localhost -U postgres content_db < backup.sql
```

### Logs y Debugging

```bash
# Habilitar logs de Alembic (editar alembic.ini)
[loggers]
keys = root,sqlalchemy,alembic

[logger_alembic]
level = DEBUG
handlers =
qualname = alembic

# Ver logs de PostgreSQL (Docker)
docker logs postgres-content

# Ver queries ejecutados (editar alembic/env.py)
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    echo=True  # <-- Agregar esta línea
)
```

---

## ✅ Checklist de Pre-Deployment

Antes de hacer deploy a staging/production:

- [ ] Migraciones probadas localmente
- [ ] Rollback probado localmente
- [ ] Tests pasan (`pytest tests/`)
- [ ] Backup de base de datos creado
- [ ] Variables de entorno configuradas en AWS Secrets Manager
- [ ] Scripts tienen permisos de ejecución (`chmod +x`)
- [ ] Documentación actualizada si hay cambios en schema
- [ ] Team notificado de cambios en BD
- [ ] Plan de rollback documentado

---

## 🤝 Contribuciones

Para agregar nuevas migraciones o modificar scripts:

1. **Crear branch**: `git checkout -b feat/add-new-table`
2. **Editar models.py**: Agregar/modificar modelos
3. **Crear migración**: `./scripts/create_migration.sh "descripción"`
4. **Revisar migration file**: Editar manualmente si es necesario
5. **Testear localmente**: `./scripts/quick_migrate.sh`
6. **Testear rollback**: `./scripts/rollback.sh && ./scripts/quick_migrate.sh`
7. **Commit**: `git commit -am "feat: add new table"`
8. **PR**: Crear Pull Request con descripción de cambios

---

**Última actualización**: 2024
**Mantenedor**: ERIKO Team
**Versión de Alembic**: 1.12.1
**Versión de PostgreSQL**: 14+
