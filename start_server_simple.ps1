# start_server_simple.ps1
# Versión simplificada para iniciar el servidor brain-ai-01
$ProjectRoot = $PSScriptRoot
$env:PYTHONPATH = $ProjectRoot

Write-Host "=== Iniciando brain-ai-01 ===" -ForegroundColor Cyan
Write-Host "Directorio: $ProjectRoot"

# Verificar que uvicorn está instalado
try {
    $uvicornVersion = python -c "import uvicorn; print(uvicorn.__version__)"
    Write-Host "uvicorn version: $uvicornVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: uvicorn no está instalado" -ForegroundColor Red
    Write-Host "Ejecuta: pip install uvicorn" -ForegroundColor Yellow
    exit 1
}

# Iniciar servidor
Write-Host "Iniciando servidor en puerto 8000..." -ForegroundColor Cyan
uvicorn ai_architect.core.mcp_server:app --host 0.0.0.0 --port 8000 --reload
