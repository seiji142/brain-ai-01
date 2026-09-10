# Changelog

Todos los cambios notables en brain-ai-01.

## [Unreleased]

### Added
- Mejoras propuestas (Fase 8): retry, revoke_all, cleanup, timeout configurable

### Changed
- Actualizar documentación completa

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
