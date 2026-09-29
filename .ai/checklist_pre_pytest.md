# Checklist pre-pytest (obligatorio tras incidente 29/09/2026)

Prohibido `pytest` en este repo sin `tests/conftest.py` presente.
Sin ese archivo, `ai_architect/core/config.py` fija `ROOT = Path.cwd()`
al importar y los fixtures `_clean_data` borran `memory/` y `logs/`
reales con `shutil.rmtree`. Detalle: `docs/INCIDENTE_20260929_MEMORIA.md`.

## Destino canonico de backups (Capa 2)

- Carpeta: `%USERPROFILE%\brain-ai-01-backups\chroma`
  (fuera del arbol git; nunca dentro del repo).
- Formato: `backup_<yyyyMMdd_HHmmss>_chroma/` con copia online del
  sqlite + `chroma_inventory.json` + `backup_meta.json`.
- Retencion: ultimas **7** copias (las antiguas se podan).
- Override solo por entorno: `BRAIN_BACKUP_ROOT`.
- Este archivo es la fuente canonica del destino; si la ruta cambia,
  actualizar aqui Y el default de `scripts/backup_chroma.py`.

## Antes de correr tests

- [ ] Rama: `git branch --show-current` → debe ser la rama de trabajo
      (prevencion: `main-clean`, nunca experimentar sobre `main`).
- [ ] `git status --short` limpio o con solo cambios intencionales.
      Commits selectivos, NUNCA `git add .` (hay `*.sqlite3` de decenas
      de MB que quedan fuera de git, solo en disco).
- [ ] `Test-Path tests/conftest.py` → True. Si falta: DETENERSE, no
      correr pytest, restaurar el archivo primero.
- [ ] Backup reciente: ultima carpeta en el destino canonico con
      `chroma_inventory.json` de hoy (o del dia anterior como maximo).
      Si no hay: `python scripts/backup_chroma.py` antes de pytest.
- [ ] Test canario en verde: `python -m pytest tests/test_aislamiento_seguro.py -q`
      (si esta rojo, DETENERSE: el aislamiento esta roto).

## Despues de cada corrida (guardia de produccion)

Conteos esperados (baseline 29/09/2026 + saves legitimos posteriores):

```powershell
(Get-ChildItem -LiteralPath "memory\episodic" -File).Count
(Get-ChildItem -LiteralPath "memory\semantic" -File).Count
python -c "import chromadb; c=chromadb.PersistentClient(path='.ai_memory/chroma'); print({n: c.get_or_create_collection(name=n).count() for n in ('episodic','semantic')})"
```

- Baseline: disco 381 / 218, Chroma 377 / 214.
- Solo aceptable: IGUAL o MAYOR por saves legitimos posteriores.
- Si algun conteo BAJO: detenerse, no commitear, investigar
  (posible fixture escribiendo en produccion).
