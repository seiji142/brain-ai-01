# Contexto del proyecto

Este repositorio implementa un sistema de memoria para agentes/equipos:
- Memoria episódica: eventos/decisiones con evidencia.
- Memoria semántica: hechos/patrones/errores consolidados.
- Working/summaries/reflections/indexes para ciclo de aprendizaje.
- Chroma para vectores; JSON/MD para auditabilidad.
- FastAPI MCP para interoperabilidad multi-modelo.

## Endpoints del MCP Server

| Endpoint | Método | Uso |
|----------|--------|-----|
| `/health` | GET | Verificar que el servidor corre |
| `/ingest` | POST | Guardar episodio en memoria |
| `/retrieve` | POST | Buscar conocimiento (híbrido) |
| `/consolidate` | POST | Consolidar episodios a semántico |
| `/evaluate` | POST | Evaluar calidad de retrieval |
| `/check_contexto` | POST | Verificar si hay contexto sobre una entidad |
| `/guardar_contexto` | POST | Guardar contexto sobre una entidad (persona, API key, etc.) |

## Client canónico

- `clients/memoria.py` — copia oficial del helper Python.
- Cada proyecto copia este archivo (no importa directamente desde brain-ai-01).
- Detecta automáticamente la raíz de brain-ai-01 esté donde esté.
