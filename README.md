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

```python
from memoria import guardar, buscar, consolidar

# Store
guardar("proyecto-web", "Usar JWT con refresh tokens", tags=["auth"])

# Retrieve
results = buscar("autenticacion JWT", proyecto="proyecto-web")

# Consolidate (episodic → semantic)
consolidar("proyecto-web")
```

## Environment

Copy `.env.example` to `.env` and configure:
- `EMBEDDING_PROVIDER`: `hash` (offline) or `openai`
- Secrets go in `.env.secrets` (gitignored)

## License

MIT
