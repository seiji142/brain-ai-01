# start_server.ps1
# Inicia el servidor MCP central de memoria persistente (brain-ai-01)
$ProjectRoot = $PSScriptRoot
$env:PYTHONPATH = $ProjectRoot
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "server.log"

Write-Host "=== Iniciando servidor MCP de brain-ai-01 ===" -ForegroundColor Cyan
Write-Host "Puerto: 8000"
Write-Host "Logs: $LogFile"

# NOTA: --reload eliminado para evitar problemas de recarga automática
uvicorn ai_architect.core.mcp_server:app --host 0.0.0.0 --port 8000 2>&1 | Tee-Object -FilePath $LogFile
