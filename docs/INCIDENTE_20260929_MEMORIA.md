# Incidente 29/09/2026 — Borrado de `memory/` y `logs/` por la suite pytest

Audiencia: yo futuro + modelo que retome este repo.
Estado: recuperado y cerrado (commit `f56b12f` en `origin/main-clean`, suite 66/66).
Este documento es el análisis completo: causa, impacto, recuperación,
pérdidas permanentes, prevención y runbook operativo.

## 1. Resumen ejecutivo

Entre las ~00:05 y ~00:15 (UTC-3) del 29/09/2026 se corrió 8 veces la suite
pytest de este repo sobre los datos reales. 7 de esas corridas ejecutaron
fixtures con `shutil.rmtree` apuntando a las rutas de producción y borraron
`memory/` (`episodic`, `semantic`, `summaries`, `reflections`, `working`,
`indexes`) y `logs/` (`traces`, `evaluations`, `failures`, `tool_calls`).

Lo que salvó la memoria: `.ai_memory/chroma/chroma.sqlite3` (29 MB) **no**
estaba en la lista de borrado y quedó intacto, con los 375 episodios y 214
ítems semánticos reales indexados. Desde ahí se reconstruyó todo lo
recuperable. La búsqueda (`memory_search`) nunca se interrumpió porque lee
de Chroma vía `ai_architect/core/retrieval.py:32`.

Estado final verificado:

| Dato | Valor |
|---|---|
| `memory/episodic/` | 375 recuperados + 4 fixtures + saves legítimos posteriores |
| `memory/semantic/` | 214 recuperados + 4 fixtures |
| Chroma `episodic` / `semantic` | 375 / 214 reales (+ saves posteriores), 0 fixtures |
| Backup | `docs/backup_20260929_003809_chroma/` (2 copias sqlite + 5 reportes JSON) |
| Suite | 66/66 con aislamiento a `tmp_path` |
| Git | `f56b12f` en `origin/main-clean`, rama sincronizada |

## 2. Cronología

| Hora aprox. | Hecho |
|---|---|
| 00:05–00:15 | 8 corridas `pytest` (7 borran, 1 no: `test_mcp_bridge_validacion.py`, sin `_clean_data`) |
| 00:14–00:15 | `LastWriteTime` de los 4 fixtures restantes (`ep_arq_001..004`) — fin del borrado |
| 00:38 | Backup defensivo: copia archivo (29.257.728 bytes exactos) + backup online vía API sqlite |
| 00:38 | Inventario read-only: 397/519 totales → 375/22 y 214/305 (real/fixtures) |
| 00:39 | `tests/conftest.py` creado; 4 `_clean_data` neutralizados a no-op |
| 00:40 | Aislamiento verificado (test peligroso pasa escribiendo solo en tmp) |
| 00:41 | `recover_from_chroma.py --write`: 375 + 214 JSON reconstruidos |
| 00:41 | `purge_test_fixtures.py --write`: Chroma 375/214 |
| 00:42–00:44 | Suite 65/66 → test frágil reescrito → 66/66; `CHANGELOG.md`; episodios de memoria |
| posterior | Commit `f56b12f` + push a `origin/main-clean`; este documento |

## 3. Causa raíz (con citas)

1. `ai_architect/core/config.py:21-50`: `settings = Settings()` se ejecuta
   **al importar**; `ROOT = Path.cwd()` (línea 23) es la raíz del repo al
   correr pytest; `MEMORY_ROOT = ROOT / "memory"` (25), `LOG_DIR` (27),
   `EPISODIC_DIR` (29), etc. apuntan a producción. No hay redirección por
   entorno y el `mkdir` final (46-50) tiene efecto lateral.
2. Cuatro archivos definían `_clean_data()` con `shutil.rmtree` + fixture
   `@pytest.fixture(autouse=True)`:
   `tests/test_evolucion_arquitectonica.py:21-27`,
   `tests/test_calidad_contradicciones.py:22-28`,
   `tests/test_patrones_debugging.py:21-27`,
   `tests/test_retrieval_strict_project.py:17-24`.
3. `tests/test_memory.py:12-20` parecía aislar (`MEMORY_ROOT`, `LOG_DIR`,
   `CHROMA_PERSIST_DIR`, `APP_ENV=test`), pero es **inefectivo**: el import
   de la línea 6 congela la config antes de que el fixture setee el env.
4. No existía `tests/conftest.py`, ni `pytest.ini`, ni `pyproject.toml`
   (verificado con `Test-Path`).
5. `shutil.rmtree` en Windows no usa Papelera: borrado directo.
6. Sin recovery vía git: `.gitignore:2-4` excluye `memory/`, `logs/`,
   `.ai_memory/`.

El error humano: correr 7 veces una suite nunca leída sobre datos reales,
sin verificar si los fixtures aislaban. El error de diseño: una suite sin
ningún aislamiento.

## 4. Impacto cuantificado

Borrado vía `rmtree`: 375 episodios, 214 semánticos, `summaries`,
`reflections/`, `working/`, `indexes/`, `logs/traces/ingest.jsonl` (solo
quedaron 4 líneas de test) y demás `*.jsonl`, `logs/evaluations/`,
`logs/failures/`, `logs/tool_calls/`.

No tocado: `.ai_memory/chroma/`, `logs/audit.jsonl`, `logs/handles.db`,
`logs/server.log`, `logs/uvicorn.log`, `logs/bridge.log`, código y git.

Conteo Chroma verificado (`chromadb.PersistentClient`, ver
`docs/backup_20260929_003809_chroma/chroma_inventory.json`):
episodic 397 = 375 reales + 22 fixtures; semantic 519 = 214 + 305.
Reales por proyecto (episodic): personalizar-comportamiento-01 124,
test-ai-config 92, portfolio 54, proyecto-web 40, youtube-transcripts 36,
brain-ai-01 22, otros menores.

## 5. Recuperación ejecutada

1. **Backup primero**: `chroma.sqlite3` + `chroma_online_backup.sqlite3`
   (mismo tamaño byte a byte) + `chroma_inventory.json` en
   `docs/backup_20260929_003809_chroma/`. Los `.sqlite3` están
   intencionalmente **fuera de git** (solo en disco).
2. **Aislamiento**: `tests/conftest.py` (autouse) redirige todos los
   `*_DIR` —incluidos los nombres ya enlazados en `memory`, `ingest`,
   `consolidate`, `factcheck`, `retrieval`, `vectorstore`— a `tmp_path` y
   resetea `vectorstore._client`. Los 4 `_clean_data` quedaron como no-op
   documentado. Verificado: tests antes peligrosos pasan sin tocar
   producción (conteos 380/218 y 375/214 intactos tras cada corrida).
3. **Reconstrucción**: `scripts/recover_from_chroma.py` (dry-run primero:
   solo 1+1 con proyecto vacío, contenido legítimo verificado) y luego
   `--write`. Heurística episódica: línea 1 → `title`, línea 2 →
   `summary`, resto → `decisions[]` (maximiza `consolidate`); semántica:
   `statement` = documento menos la primera línea. Cada objeto lleva
   `_recovered_from_chroma: true`, `_recovery_notes` y
   `_recovery_lost_fields`. Verificado: `ep_0c550738…` de vuelta en disco.
4. **Purga** (autorizada, tras backup): `scripts/purge_test_fixtures.py`
   `--write` → Chroma 375/214, compuesta solo de reales. Esto curó además
   el test ambiental rojo (§7).
5. **Cierre**: suite 66/66, 16P verificado 19/19
   (`test_calidad_contradicciones.py` + `test_memory.py`: email PII
   re-activado en `utils.py:7-12`, dedup por texto de decisión en
   `consolidate.py:20-65`), `CHANGELOG.md`, episodios de memoria
   `ep_875217fb…` (incidente) y `ep_d7e8f7…` (cierre).

## 6. Pérdidas permanentes (aceptadas)

No existen en Chroma y no son reconstruibles:

- Episodios: `author`, `evidence[]` (`type/url_or_path/excerpt`),
  `decisions[].owner`, límites estructurales entre
  title/summary/decisions/actions/risks (actions/risks quedaron plegados
  en `decisions[]` por heurística).
- Semánticos: `evidence_source_ids`, `contradictions`, distinción
  `created_at` vs `updated_at` (un solo timestamp).
- Historial `logs/traces/*.jsonl` previo al borrado.
- Contenido real de `memory/summaries|reflections|working|indexes/`
  (quedan solo restos de fixtures).

Cómo distinguir dato original de reconstruido: flags `_recovered…` en
cada JSON. `memory_search` no se ve afectada (lee Chroma); `consolidate`
y `list_episodes` vuelven a funcionar sobre los JSON recuperados, con
scoring/evidencia degradados donde aplique.

## 7. Hallazgos colaterales (resueltos)

- **Test ambiental rojo** (`test_evolucion_arquitectonica.py::
  test_retrieval_encuentra_evolucion`, 5 copias de un statement huérfano):
  era contaminación del ranking por fixtures indexados en Chroma real.
  Curado con la purga.
- **Test frágil de recencia** (`test_patrones_debugging.py::
  test_score_recency_prioriza_reciente`): afirmaba `score > 0.6` con una
  query ("solucion problemas conexion") que no calza con el doc Kafka
  (tokens "desconecta" ≠ "conexion"); antes pasaba por contaminación del
  índice o en forma vacua. Reescrito con query discriminativa
  ("kafka reconnect backoff") y aserción relativa (top-1 = proj-delta),
  determinista en índice limpio.
- **`lastfailed` con fantasmas**: el caché listaba 2 tests de calidad que
  no existen ni en el archivo actual ni en HEAD (renombrados/eliminados;
  pytest conserva IDs no recolectados hasta `--cache-clear`). Solo era
  caché local, sin relación con los datos. Limpieza: `Remove-Item
  -Recurse -Force .pytest_cache`.

## 8. Prevención — 3 capas

**Capa 1 — Hacer el accidente imposible por construcción** (pendiente):
- Test canario que falle si `EPISODIC_DIR`/`CHROMA_DIR` resuelven dentro
  de rutas de producción (si alguien rompe el conftest, la suite se pone
  roja en vez de borrar).
- Guardia en `conftest.py`: abortar si algún `*_DIR` apunta fuera de tmp.
- Refactor de raíz (invasivo, a futuro): `config.py` con lectura
  perezosa (`get_*()` en vez de constantes al importar); `ROOT =
  Path.cwd()` no debe decidir datos.

**Capa 2 — Hacer el daño reversible** (pendiente):
- `scripts/backup_chroma.py` (copia online vía API sqlite + verificación
  con `inventory_chroma.py`) + Tarea Programada Windows diaria a carpeta
  fuera del árbol git, retención 7–14 copias. Peor caso futuro =
  restaurar, no reconstruir con pérdidas.

**Capa 3 — Regla operativa** (pendiente de escribir en `.ai/`):
- Checklist pre-`pytest`: verificar rama, `git status`, backup reciente.
  Prohibido `pytest` en este repo sin `tests/conftest.py` presente.

## 9. Runbook operativo

Respaldo (desde la raíz del repo):

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$dest = "docs\backup_${ts}_chroma"
New-Item -ItemType Directory -Path "$dest" -Force | Out-Null
Copy-Item -LiteralPath ".ai_memory\chroma\chroma.sqlite3" -Destination "$dest\" -Force
python scripts/inventory_chroma.py --out "$dest\chroma_inventory.json"
```

Copia online consistente (si el servidor tiene el sqlite bloqueado):

```powershell
python -c "import sqlite3; s=sqlite3.connect(r'.ai_memory\chroma\chroma.sqlite3'); d=sqlite3.connect(r'docs\backup_<ts>_chroma\chroma_online_backup.sqlite3'); s.backup(d); d.close(); s.close()"
```

Restauración (solo si `memory/*.json` se pierde y Chroma está sano):

```powershell
python scripts/recover_from_chroma.py --report <dest>\recovery_report_dryrun.json
# revisar el reporte (real vs fixtures, needs_review)
python scripts/recover_from_chroma.py --write --report <dest>\recovery_report_write.json
```

Purga de fixtures (solo tras backup):

```powershell
python scripts/purge_test_fixtures.py --report <dest>\purge_report_dryrun.json
python scripts/purge_test_fixtures.py --write --report <dest>\purge_report_write.json
```

Corrida segura de tests + guardia (conteos esperados: disco 380/218 —
más saves posteriores legítimos —, Chroma 375/214 + saves):

```powershell
python -m pytest tests/ -q
Get-ChildItem -LiteralPath "memory\episodic" | Measure-Object | Select-Object -ExpandProperty Count
Get-ChildItem -LiteralPath "memory\semantic" | Select-Object -ExpandProperty Count
```

Qué commitear / qué no: staging selectivo de `tests/`, `scripts/`,
`CHANGELOG.md`, `ai_architect/` y reportes `*.json` del backup.
**Nunca** `git add .` a ciegas: los `*.sqlite3` (decenas de MB) quedan
fuera de git, solo en disco. `memory/`, `logs/`, `.ai_memory/` están
gitignorados y no viajan al push.

## 10. Deudas y próximos pasos

- Refactor lazy de `config.py` (causa de fondo, §3.1 y Capa 1) —
  **diferido por decisión explícita, ver abajo**.
- Backup automático + test canario (Capas 1–2) — **hecho 29/09/2026**:
  `tests/test_aislamiento_seguro.py`, guardia abortiva en
  `tests/conftest.py`, `.ai/checklist_pre_pytest.md`,
  `scripts/backup_chroma.py` + Tarea Programada diaria
  `brain-ai-01-chroma-backup` (destino fuera del árbol git,
  retención 7). Commits `4417652` y `b4186a8` en `origin/main-clean`.
- `summaries/` real aceptado como perdido salvo que aparezca copia.
- Decidir publicación `main-clean` → `main` según roadmap (16P ya
  cerrado y verificado 19/19).

### Por qué el refactor lazy de `config.py` quedó diferido (29/09/2026)

Decisión de la sesión de prevención: no hacerlo ahora.

1. El riesgo ya está cubierto por 3 capas (test canario, guardia
   abortiva en `conftest.py`, backup automático + checklist):
   beneficio marginal bajo.
2. No es un cambio de un archivo: ~12 archivos hacen
   `from config import ...` (`core/memory.py`, `core/vectorstore.py`,
   `core/retrieval.py`, `pipelines/ingest.py`,
   `pipelines/consolidate.py`, `pipelines/factcheck.py`,
   `pipelines/export.py`, más 4 tests) y congelan los valores al
   importar. Hay que reescribir cada uso a `get_*()`, adaptar
   `conftest.py` + canario y re-verificar la suite completa.
3. Tocarlo ahora arriesga romper la suite 69/69 verde y pusheada.

Futuro: convertir las constantes de `config.py:21-50` en funciones
`get_*()` con resolución por llamada (leer entorno cada vez, sin
congelar paths al importar). Modelo a seguir: el import lazy ya
existente en `mcp_server.py:298`.
