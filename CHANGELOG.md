# Changelog

Todos los cambios notables en brain-ai-01.

## [Unreleased]

### Changed
- **C1 (16M, 29/09/2026): `memory_search` busca en ambas colecciones por
  defecto.** `retrieval.retrieve()` acepta `collection="both"` (merge por
  score, misma semántica que `clients/memoria.buscar`; `top_k*2` por
  colección); defaults en `mcp_bridge.py` (schema + handler) y
  `mcp_server.py` pasan a `"both"`. `semantic`/`episodic` explícitos
  intactos; valor desconocido sigue cayendo a `semantic`. Tests:
  `tests/test_retrieval_both_collections.py` 5/5, suite 74/74.

### Fixed
- **Incidente 29/09/2026: suite pytest borraba `memory/` y `logs/` reales.**
  Causa: `ai_architect/core/config.py` fija `ROOT = Path.cwd()` y
  `MEMORY_ROOT/LOG_DIR/CHROMA_DIR` al importar, y 4 archivos de test
  (`test_evolucion_arquitectonica`, `test_calidad_contradicciones`,
  `test_patrones_debugging`, `test_retrieval_strict_project`) hacian
  `shutil.rmtree` sobre esos paths via fixture `autouse`. El fixture de
  `test_memory.py` (env `MEMORY_ROOT/LOG_DIR/CHROMA_PERSIST_DIR/APP_ENV`)
  era inefectivo por inicializacion en el import. No habia `conftest.py`,
  `pytest.ini` ni `pyproject.toml`.
  Recuperacion: 375 episodios + 214 semanticos reconstruidos desde
  `.ai_memory/chroma` (unica copia intacta) con
  `scripts/recover_from_chroma.py`, marcados `_recovered_from_chroma`.
  Perdida permanente: `author`, `evidence[]`, `decisions[].owner`,
  estructura title/summary/decisions/actions/risks,
  `evidence_source_ids`, `contradictions`, historial `logs/traces/*.jsonl`.
  Backup previo en `docs/backup_20260929_003809_chroma/`.
  Aislamiento: nuevo `tests/conftest.py` (autouse, redirige todos los
  `*_DIR` a `tmp_path`, resetea `vectorstore._client`); `_clean_data()`
  de los 4 archivos neutralizado a no-op. Purga de 22 + 305 fixtures
  de Chroma con `scripts/purge_test_fixtures.py` (tras backup).
  Nota: `test_patrones_debugging.py::test_score_recency_prioriza_reciente`
  (umbral absoluto `score > 0.6`) falla con indice limpio de 4 docs;
  antes pasaba solo por contaminacion del indice real. Test fragil
  pendiente de ajuste, no relacionado con 16P.

### Added
- Mejoras propuestas (Fase 8): retry, revoke_all, cleanup, timeout configurable

### Changed
- Actualizar documentación completa

## [2026-09-28]

### Fixed
- **16L: `memory_save` ya no acepta guardar sin `project`**

  **Problema:** el servidor ya validaba (`ai_architect/pipelines/ingest.py:9`,
  `REQUIRED` → HTTP 400), pero el bridge no, y sus dos modos de fallo daban
  mensajes inútiles al modelo:

  | Qué mandaba el modelo | Qué veía |
  |---|---|
  | Call sin la key `project` | `Error ejecutando memory_save: 'project'` (`KeyError` crudo) |
  | `project: ""` o `null` | `Error al guardar: Unknown error` (el motivo real quedaba enterrado en `detail`) |

  **Cambio:** `handle_memory_save` valida `project` y `decision` con `.strip()`
  **antes** del request (0 HTTP en el error previsible) y desenvuelve `detail`
  para que el error real del servidor llegue al modelo. `clients/memoria.guardar`
  hace lo mismo con `ValueError` temprano.

  **No se tocó el `TOOLS` (schema publicado)**: el `inputSchema` ya declaraba
  `required: ["project", "decision"]`, así que el cambio **no altera la request
  de D1-D3 ni obliga a re-correr la suite**.

  **Tests:** `tests/test_mcp_bridge_validacion.py` — 6 casos sin HTTP
  (proyecto ausente/vacio/solo espacios, decision vacia, caso valido, error
  400 con `detail`). Verificado: 6/6 pass.

## [2026-09-23]

### Fixed
- **Bridge muerto por `NameError` en `mcp_bridge.py` (tarea 13)**

  **Problema:** el handshake MCP (`initialize`) fallaba con timeout de 30s
  en los tests API (`personalizar-comportamiento-01`). El bridge moría con
  exit code 1 al arrancar:

  ```
  mcp_bridge.py, line 175
      "default": false
  NameError: name 'false' is not defined
  ```

  **Causa raíz:** el commit `c87e984` (tarea 5, 21/09) agregó el literal
  JSON `false` en el schema de `memory_search.include_other_projects` en
  vez del booleano de Python `False`. El traceback era invisible porque
  el cliente (`tests/lib/mcp_client.py`) lanzaba el bridge con
  `stderr=subprocess.DEVNULL` y solo esperaba la respuesta, sin verificar
  si el proceso seguía vivo → timeout silencioso de 30s.

  **Nota:** había evidencia de `SYN_SENT [::1]:8000` en netstat
  (`localhost` resuelve primero a `::1` / IPv6 y uvicorn solo escucha
  `127.0.0.1`), pero era ruido secundario: la falla real ocurría antes
  de cualquier conexión HTTP, en el import del módulo.

  **Cambio:**
  - `mcp_bridge.py:175` — `false` → `False` (el bug).
  - `mcp_bridge.py` — `BRAIN_API` por defecto ahora es
    `http://127.0.0.1:8000` (IPv4 explícito, elimina el intento a `::1`).
  - `clients/memoria.py` — `API` ahora `http://127.0.0.1:8000`.

### Tested
- Post-fix: `initialize` 0.67s, `tools/list` 10 tools, `memory_search`
  real OK (antes: `MCPError: Timeout esperando respuesta a request 1`
  a los 30.43s).
- B3 re-run `--api qwen/qwen3.8-27b`: PASS 31.1s, `mcp_available=True`,
  `memory_used=True`, `arguments.project="test-ai-config"`.
- Documentación: sección TAREA 13 en
  `personalizar-comportamiento-01/docs/tests/sesion_20260921.md`.

### Nota (cliente de tests, repo personalizar-comportamiento-01)
- `mcp_client.py` ahora es fail-fast: si el bridge muere durante
  `_wait_response`, lanza `MCPError` con exit code + tail de stderr en
  vez de esperar el timeout completo. Cualquier crash futuro del bridge
  se diagnostica en ~1s con el error real.

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
