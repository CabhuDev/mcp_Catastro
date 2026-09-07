# Setup reproducible para MCP Catastro en Windows
# Ejecutar desde la raíz del proyecto: .\setup-env.ps1

$ErrorActionPreference = "Stop"

Write-Host "🐍 CONFIGURANDO MCP CATASTRO CON UV" -ForegroundColor Cyan

if (-not (Test-Path "mcp_server.py") -or -not (Test-Path "uv.lock")) {
    Write-Host "❌ Ejecuta este script desde la raíz del proyecto." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Instalando uv 0.9.7..." -ForegroundColor Yellow
    python -m pip install "uv==0.9.7"
}

Write-Host "🔒 Sincronizando exactamente uv.lock..." -ForegroundColor Yellow
uv python install 3.14
uv sync --python 3.14 --locked --all-extras --dev

Write-Host "🔍 Verificando dependencias críticas..." -ForegroundColor Yellow
uv run --locked python -c "import httpx, mcp, pydantic; print('✅ Dependencias: OK')"

Write-Host "🧪 Ejecutando pruebas..." -ForegroundColor Yellow
uv run --locked pytest -q

Write-Host "`n🎉 Entorno reproducible preparado correctamente." -ForegroundColor Green
Write-Host "🚀 Servidor: uv run --locked python mcp_server.py" -ForegroundColor Cyan
