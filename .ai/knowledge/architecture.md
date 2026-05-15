# Arquitectura

- `ai_architect/core/`: dominio (memory, retrieval, consolidation, scoring, router, embeddings, redact, utils, mcp_server)
- `ai_architect/pipelines/`: ingest, summarize, reflect, factcheck, evaluate, export
- `memory/`: datos (episodic/, semantic/, working/, summaries/, reflections/, indexes/)
- `.ai_memory/chroma/`: vector store persistente
- `logs/`: trazas, tool_calls, evaluations, failures
- `.ai/`: documentación/políticas/reglas (single source of truth operativo)
