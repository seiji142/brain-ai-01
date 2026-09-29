"""Test canario anti-borrado (incidente 29/09/2026).

El 29/09/2026 la suite pytest borro `memory/` y `logs/` reales porque
`ai_architect/core/config.py` fija ROOT=Path.cwd() al importar y cuatro
fixtures `_clean_data` hacian `shutil.rmtree` sobre esos paths.
Ver `docs/INCIDENTE_20260929_MEMORIA.md` (Capa 1).

Estos tests fallan en rojo si algun *_DIR vuelve a resolver dentro de
rutas de produccion (repo) o fuera del tmp del sistema. Si alguien rompe
`tests/conftest.py`, la suite se pone roja EN VEZ de borrar datos.
"""
import os
import tempfile
from pathlib import Path

import ai_architect.core.config as cfg
import ai_architect.core.memory as mem
import ai_architect.core.vectorstore as vs
import ai_architect.pipelines.ingest as ingest
import ai_architect.pipelines.consolidate as consolidate
import ai_architect.pipelines.factcheck as factcheck
import ai_architect.core.retrieval as retrieval

REPO_ROOT = Path.cwd().resolve()
SYSTEM_TMP = Path(tempfile.gettempdir()).resolve()


def _collect_dirs():
  """Todos los *_DIR de config mas los nombres ya enlazados en consumidores."""
  return {
    "cfg.MEMORY_ROOT": cfg.MEMORY_ROOT,
    "cfg.LOG_DIR": cfg.LOG_DIR,
    "cfg.CHROMA_DIR": cfg.CHROMA_DIR,
    "cfg.EPISODIC_DIR": cfg.EPISODIC_DIR,
    "cfg.SEMANTIC_DIR": cfg.SEMANTIC_DIR,
    "cfg.WORKING_DIR": cfg.WORKING_DIR,
    "cfg.SUMMARIES_DIR": cfg.SUMMARIES_DIR,
    "cfg.REFLECTIONS_DIR": cfg.REFLECTIONS_DIR,
    "cfg.INDEXES_DIR": cfg.INDEXES_DIR,
    "cfg.TRACES_DIR": cfg.TRACES_DIR,
    "cfg.TOOLCALLS_DIR": cfg.TOOLCALLS_DIR,
    "cfg.EVALS_DIR": cfg.EVALS_DIR,
    "cfg.FAILS_DIR": cfg.FAILS_DIR,
    "mem.EPISODIC_DIR": mem.EPISODIC_DIR,
    "mem.SEMANTIC_DIR": mem.SEMANTIC_DIR,
    "mem.SUMMARIES_DIR": mem.SUMMARIES_DIR,
    "mem.REFLECTIONS_DIR": mem.REFLECTIONS_DIR,
    "ingest.TRACES_DIR": ingest.TRACES_DIR,
    "consolidate.TRACES_DIR": consolidate.TRACES_DIR,
    "factcheck.TRACES_DIR": factcheck.TRACES_DIR,
    "retrieval.TRACES_DIR": retrieval.TRACES_DIR,
    "vs.CHROMA_DIR": vs.CHROMA_DIR,
  }


def _assert_aislado(nombre, path):
  p = Path(path).resolve()
  assert REPO_ROOT not in p.parents and p != REPO_ROOT, (
    f"CANARIO ROJO: {nombre}={p} apunta a PRODUCCION "
    f"(repo {REPO_ROOT}). Ver docs/INCIDENTE_20260929_MEMORIA.md. "
    f"NO correr mas tests hasta aislar tests/conftest.py."
  )
  assert SYSTEM_TMP in p.parents or p == SYSTEM_TMP, (
    f"CANARIO ROJO: {nombre}={p} esta fuera del tmp del sistema "
    f"({SYSTEM_TMP}). La guardia de conftest debe abortar la corrida."
  )


def test_dirs_fuera_de_produccion():
  for nombre, path in _collect_dirs().items():
    _assert_aislado(nombre, path)


def test_env_apunta_a_tmp():
  """El env fijado al importar (antes de que conftest redirija) tambien es tmp."""
  for var in ("MEMORY_ROOT", "LOG_DIR", "CHROMA_PERSIST_DIR"):
    val = os.environ.get(var)
    assert val, f"CANARIO ROJO: env {var} no definido (conftest roto?)"
    _assert_aislado(f"env.{var}", val)


def test_chroma_no_es_produccion():
  """Foco extra en Chroma: es la unica copia que salvo la memoria el 29/09."""
  prod_sqlite = (REPO_ROOT / ".ai_memory" / "chroma" / "chroma.sqlite3").resolve()
  chroma_dir = Path(vs.CHROMA_DIR).resolve()
  assert chroma_dir != prod_sqlite.parent, (
    f"CANARIO ROJO: vectorstore.CHROMA_DIR={chroma_dir} es el Chroma real. "
    f"Un rmtree o purga aqui destruiria la fuente de recuperacion."
  )
  _assert_aislado("vs.CHROMA_DIR", chroma_dir)
