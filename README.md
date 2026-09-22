# brain-ai-01

Servidor MCP para memoria persistente y sistema de provenance.

## Características

- **Memoria Persistente**: Busca y guarda episodios de decisiones
- **Provenance**: Control de procedencia para valores sensibles
- **Auto-start**: Se inicia automáticamente con opencode
- **Handles Opacos**: El modelo nunca ve valores secretos directamente

## Arquitectura

```
opencode
  ↓ (MCP)
mcp_bridge.py
  ↓ (HTTP)
mcp_server.py (FastAPI)
  ↓
provenance/
  ├── resolver.py (resuelve referencias)
  ├── store.py (handles SQLite)
  ├── gateway.py (valida acciones)
  └── audit.py (logging)
```

- **Central MCP server** at `localhost:8000`
- Projects connect via HTTP, never copy system code
- All data stays local; no cloud exposure

## Instalación

### Requisitos
- Python 3.10+
- uvicorn
- fastapi
- requests

### Pasos
```powershell
cd brain-ai-01
pip install -r requirements.txt
```

## Uso

### Con opencode (automático)
brain-ai-01 se inicia automáticamente cuando opencode hace la primera petición MCP.

### Manualmente
```powershell
cd brain-ai-01
.\start_server.ps1
```

## Tools MCP Disponibles

| Tool | Descripción | Cuándo usar |
|------|-------------|-------------|
| `memory_search` | Busca episodios en memoria | ANTES de responder preguntas sobre decisiones |
| `memory_save` | Guarda episodio en memoria | DESPUÉS de tomar una decisión importante |
| `memory_consolidate` | Consolida memoria | Periódicamente |
| `resolver_referencia` | Resuelve una referencia | Cuando necesitas un valor seguro |
| `describir_handle` | Devuelve metadatos de handle | Para verificar un handle |
| `ejecutar_accion` | Ejecuta una acción | Para acciones con efectos |

### Filtrado por proyecto en `memory_search` (21/09/2026)

Si pasas `project`, el filtro es **estricto por defecto**: solo se devuelven
items de ese proyecto. Nunca verás memoria de otros proyectos mezclada.

- `project` definido → solo ese proyecto (aislamiento).
- `project` + `include_other_projects=true` → opt-in cross-project
  (búsqueda explícita en todos los proyectos, rankeada por score).
- Sin `project` → búsqueda global (todos los proyectos).

Esto corrige la fuga donde `memory_search(project="X")` devolvía items
de `eleccion-db` u otros proyectos (ver CHANGELOG 2026-09-21).

### Ejemplo: Deploy con Handle

```
1. Usuario: "Haz deploy a staging"
2. Modelo: brain_ai_memory_search(query="GROQ_API_KEY")
3. Modelo: resolver_referencia("GROQ_API_KEY", expected_kind="secret")
4. Modelo: ejecutar_accion("deploy", {environment: "staging", api_key: {handle: "vh_abc123"}})
5. Resultado: Deploy exitoso
```

## Auto-start del Servidor

brain-ai-01 se inicia automáticamente cuando opencode hace la primera petición MCP.

### Cómo funciona
1. MCP bridge detecta conexión fallida (ConnectionError)
2. Llama a `ensure_server()` en `mcp_bridge.py`
3. `ensure_server()` ejecuta uvicorn con `CREATE_BREAKAWAY_FROM_JOB`
4. Espera hasta 30 segundos a que el servidor esté healthy
5. Reintenta la petición original

### Archivos de log
- `logs/bridge.log`: Intentos de auto-start y diagnósticos
- `logs/uvicorn.log`: stdout/stderr de uvicorn

## Troubleshooting

### El servidor no inicia automáticamente
```powershell
# Ver logs de auto-start
Get-Content logs/bridge.log -Tail 20

# Ver logs de uvicorn
Get-Content logs/uvicorn.log -Tail 50
```

### El servidor no responde
```powershell
# Verificar health
Invoke-RestMethod http://localhost:8000/health

# Reiniciar manualmente
.\start_server.ps1
```

### Violaciones en el audit log
```powershell
# Ver violaciones
python scripts/audit_report.py

# Ver handles activos
python -c "import sqlite3; print(sqlite3.connect('logs/handles.db').execute('SELECT COUNT(*) FROM handles').fetchone()[0])"
```

## Métricas

```powershell
# Reporte semanal
python scripts/metrics_report.py

# Reporte de auditoría
python scripts/audit_report.py
```

## Environment

Copy `.env.example` to `.env` and configure:
- `EMBEDDING_PROVIDER`: `hash` (offline) or `openai`
- Secrets go in `.env.secrets` (gitignored)

## Licencia

Proyecto privado - No distribuir.
