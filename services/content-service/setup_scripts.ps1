# =============================================================================
# Setup Scripts for Windows - Content Service
# =============================================================================
# 
# Este script configura permisos de ejecución para scripts Bash en Windows
# Uso: .\setup_scripts.ps1
#
# =============================================================================

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Content Service - Setup Scripts" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Verificar que Git Bash está instalado
$gitBashPath = "C:\Program Files\Git\bin\bash.exe"
if (-Not (Test-Path $gitBashPath)) {
    Write-Host "Error: Git Bash no encontrado en $gitBashPath" -ForegroundColor Red
    Write-Host "Por favor instala Git for Windows desde https://git-scm.com/downloads" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] Git Bash encontrado: $gitBashPath" -ForegroundColor Green
Write-Host ""

# Dar permisos de ejecución a scripts (Git atributos)
Write-Host "[2/3] Configurando permisos de ejecución..." -ForegroundColor Yellow

$scripts = @(
    "scripts/run_migrations.sh",
    "scripts/seed_all.sh",
    "scripts/quick_migrate.sh",
    "scripts/create_migration.sh",
    "scripts/rollback.sh"
)

foreach ($script in $scripts) {
    if (Test-Path $script) {
        # Agregar +x usando Git (funciona en Windows)
        git update-index --chmod=+x $script
        Write-Host "  [OK] $script" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] $script (no encontrado)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[3/3] Verificando permisos..." -ForegroundColor Yellow

# Verificar permisos
& $gitBashPath -c "ls -la scripts/*.sh | grep -E 'rwx'"

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Setup Completado" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Scripts configurados correctamente." -ForegroundColor Green
Write-Host ""
Write-Host "Uso en Windows:" -ForegroundColor Cyan
Write-Host '  bash scripts/run_migrations.sh local' -ForegroundColor White
Write-Host '  bash scripts/seed_all.sh local' -ForegroundColor White
Write-Host ""
Write-Host "Uso en WSL/Linux:" -ForegroundColor Cyan
Write-Host '  ./scripts/run_migrations.sh local' -ForegroundColor White
Write-Host '  ./scripts/seed_all.sh local' -ForegroundColor White
Write-Host ""
