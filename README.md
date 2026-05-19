# brain-ai-01

Persistent cognitive layer for AI agents. A central MCP server that accumulates, consolidates, and retrieves knowledge across multiple projects using episodic + semantic memory with hybrid scoring (BM25 + vector + recency + confidence).

## Architecture

```
project-web ─┐
sistema-ventas ─┤  HTTP ──▶ brain-ai-01 (MCP Server)
juego-rpg ────┘           FastAPI + ChromaDB
                                │
                    ┌───────────┴───────────┐
                    │                       │
              Episodic Memory        Semantic Memory
              (raw experiences)      (consolidated facts)
```

- **Central MCP server** at `localhost:8000`
- Projects connect via HTTP, never copy system code
- All data stays local; no cloud exposure

## Quick Start

```powershell
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn ai_architect.core.mcp_server:app --reload --port 8000

# Or using the launcher
.\start_server.ps1
```

## Key Features

- **Dual memory**: Episodic (raw events) → consolidated → Semantic (validated facts)
- **Hybrid retrieval**: BM25 keyword scoring (70%) + vector similarity + recency + evidence + confidence
- **PII redaction**: Automatic detection and redaction of API keys and tokens
- **Multi-project**: Each project has isolated memory, but retrieval falls back across all projects
- **Pre-processors**: Scripts for ingesting text, images (via vision API), PDFs, and web pages

## Usage (from any project)

The canonical client lives at `clients/memoria.py`. Copy it to your project:

```powershell
copy brain-ai-01\clients\memoria.py tu-proyecto\memoria.py
```

### Core memory

```python
from memoria import guardar, buscar, consolidar

guardar("proyecto-web", "Usar JWT con refresh tokens", tags=["auth"])
results = buscar("autenticacion JWT", proyecto="proyecto-web")
consolidar("proyecto-web")
```

### Secrets with context awareness

```python
from memoria import guardar_secreto, leer_secreto, check_contexto, guardar_contexto

# Save a secret — if the entity has no context yet, contexto_faltante=true
r = guardar_secreto("TELEFONO_SHIZUMI", "099XXXXXX")
if r["contexto_faltante"]:
    # Agent should ask: "¿Quién es shizumi?"
    guardar_contexto(r["nombre_base"], "mi hermana")

# Next time the same entity appears, contexto_faltante=false → no question
guardar_secreto("EMAIL_SHIZUMI", "shizumi@gmail.com")  # contexto_faltante: false

# Read secrets
leer_secreto("GMAIL")  # → {"ok": true, "valor": "..."}
```

## Environment

Copy `.env.example` to `.env` and configure:
- `EMBEDDING_PROVIDER`: `hash` (offline) or `openai`
- Secrets go in `.env.secrets` (gitignored)

## License

MIT
