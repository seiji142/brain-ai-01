# Changelog

Todos los cambios notables en brain-ai-01.

## [Unreleased]

### Added
- Mejoras propuestas (Fase 8): retry, revoke_all, cleanup, timeout configurable

### Changed
- Actualizar documentación completa

## [2026-09-21]

### Fixed
- **Filtrado estricto por proyecto en `retrieve()`** (fix fuga cross-project)

  **Problema:** `memory_search(project="X")` devolvía items de OTROS
  proyectos aunque se pasara el filtro. Causa raíz: un "fallback
  multi-proyecto" en `ai_architect/core/retrieval.py` que, siempre que
  había `project`, hacía una segunda query SIN filtro (`where=None`,
  `n_results=1000`) y mergeaba los candidatos sin filtrarlos después.
  El `hybrid_score` no tiene componente de proyecto, así que un doc
  ajeno con BM25 alto (p.ej. "Usar PostgreSQL como base de datos
  principal" de `eleccion-db`) desplazaba al correcto dentro de `top_k`.

  **Evidencia:** test B3 de la suite `personalizar-comportamiento-01`:
  `memory_search(project="test-ai-config")` devolvía 5/5 resultados de
  `eleccion-db` con score 0.87, provocando que los modelos mezclaran
  memoria ajena como si fuera contradicción propia.

  **Cambio:**
  - `retrieve(..., include_other_projects: bool = False)` — el fallback
    multi-proyecto ahora es **opt-in**. Por defecto: aislamiento estricto.
  - `project=None` sigue siendo búsqueda global (sin regresión).
  - Cascada: `RetrieveReq` (mcp_server) → schema `memory_search`
    (mcp_bridge) → `clients/memoria.buscar(incluir_otros=...)` →
    `scripts/retrieve_cli.py --include-other-projects`.
  - `scoring.py` NO se tocó: con filtro estricto no hace falta
    penalizar proyectos ajenos.

### Added
- `tests/test_retrieval_strict_project.py` — 4 tests: estricto por
  defecto, opt-in cross, global sin project, default de la firma.

### Tested
- pytest brain-ai-01: 57/60 PASS (3 FAIL preexistentes de redact y
  confidence, ajenos a este fix). Los 4 tests nuevos PASS.
- Memoria real intacta: 247 episodios / 101 semánticos antes y después
  (tests corrieron con `MEMORY_ROOT`/`CHROMA`/`LOG_DIR` en temp).
- Live: `POST /retrieve {project: "test-ai-config"}` → 10/10 solo
  test-ai-config, cero `eleccion-db`. Con `include_other_projects=true`
  → cross-project vuelve a funcionar.
- B3 re-run en `personalizar-comportamiento-01`: big-pickle PASS,
  qwen PASS, ninguna respuesta menciona `eleccion-db`.

## [2026-09-09]

### Added
- Auto-start del servidor brain-ai-01 con `ensure_server()`
- Scripts de métricas: `scripts/metrics_report.py`
- Reglas de memoria en `.ai/rules.md` (6.10-6.12)
- Sección "brain-ai-01: Primera Fuente" en `.ai/system.md`

### Fixed
- Eliminado `--reload` de `start_server.ps1` (causaba shutdown)
- Agregado `from pathlib import Path` en `mcp_bridge.py` (causaba crash silencioso)

### Tested
- Deploy con handle válido: `action_allowed` sin violaciones
- http_request con handle: `status: 200`
- memory_search: El modelo busca ANTES de responder
- Detección de discrepancias: MySQL vs PostgreSQL → pregunta al usuario

## [2026-09-08]

### Added
- Fase 0: Observabilidad (audit logging, detectores)
- Fase 1: Tipos + Resolver (ValueKind, Candidate, 4 fuentes)
- Fase 2: Store de Handles (SQLite, TTL 600s, max uses 3)
- Fase 3: Gateway + Políticas (warn mode)
- Fase 3.5: Cerrar Efectos (bash deny, write ask)
- Fase 5: Prompt Alineado (rules.md 6.5-6.9)
- Fase 6: Tests Red Team (23 tests)
- Fase 7: Métricas (scripts/audit_report.py)
- Scripts de testing: `scripts/test_provenance.py`

### Security
- bash=deny en opencode.json
- write=ask, edit=ask en opencode.json
- Handles con TTL y max_uses
- Detección de leaks (valores copiados como literales)
