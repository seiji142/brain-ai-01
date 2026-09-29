"""Aislamiento obligatorio de tests (incidente 29/09/2026).

Sin este archivo, `ai_architect/core/config.py` fija ROOT=Path.cwd() y
MEMORY_ROOT/LOG_DIR/CHROMA_DIR a produccion al importar, y los
_clean_data() con shutil.rmtree borraban memory/ y logs/ reales.

Este conftest redirige TODOS los *_DIR a tmp_path por test, incluyendo
los nombres ya enlazados en los modulos consumidores
(memory, ingest, consolidate, factcheck, retrieval, vectorstore).
"""
import os
import tempfile
from pathlib import Path

# 1) Antes de cualquier import de ai_architect: env a un tmp global.
#    Evita que config.Settings() congele paths de produccion en la importacion.
_GLOBAL_TMP = Path(tempfile.mkdtemp(prefix="brainai_pytest_"))
os.environ["APP_ENV"] = "test"
os.environ["MEMORY_ROOT"] = str(_GLOBAL_TMP / "memory")
os.environ["LOG_DIR"] = str(_GLOBAL_TMP / "logs")
os.environ["CHROMA_PERSIST_DIR"] = str(_GLOBAL_TMP / "chroma")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_brain_ai_dirs(tmp_path, monkeypatch):
  """Redirige dirs de produccion a tmp_path. Autouse en todo tests/."""
  import ai_architect.core.config as cfg
  import ai_architect.core.memory as mem
  import ai_architect.core.vectorstore as vs
  import ai_architect.pipelines.ingest as ingest
  import ai_architect.pipelines.consolidate as consolidate
  import ai_architect.pipelines.factcheck as factcheck
  import ai_architect.core.retrieval as retrieval

  mem_root = tmp_path / "memory"
  log_dir = tmp_path / "logs"
  chroma_dir = tmp_path / "chroma"
  episodic = mem_root / "episodic"
  semantic = mem_root / "semantic"
  working = mem_root / "working"
  summaries = mem_root / "summaries"
  reflections = mem_root / "reflections"
  indexes = mem_root / "indexes"
  traces = log_dir / "traces"
  toolcalls = log_dir / "tool_calls"
  evals = log_dir / "evaluations"
  fails = log_dir / "failures"
  for p in (episodic, semantic, working, summaries, reflections,
            indexes, traces, toolcalls, evals, fails, chroma_dir):
    p.mkdir(parents=True, exist_ok=True)

  # Modulo config
  monkeypatch.setattr(cfg, "MEMORY_ROOT", mem_root)
  monkeypatch.setattr(cfg, "LOG_DIR", log_dir)
  monkeypatch.setattr(cfg, "CHROMA_DIR", chroma_dir)
  monkeypatch.setattr(cfg, "EPISODIC_DIR", episodic)
  monkeypatch.setattr(cfg, "SEMANTIC_DIR", semantic)
  monkeypatch.setattr(cfg, "WORKING_DIR", working)
  monkeypatch.setattr(cfg, "SUMMARIES_DIR", summaries)
  monkeypatch.setattr(cfg, "REFLECTIONS_DIR", reflections)
  monkeypatch.setattr(cfg, "INDEXES_DIR", indexes)
  monkeypatch.setattr(cfg, "TRACES_DIR", traces)
  monkeypatch.setattr(cfg, "TOOLCALLS_DIR", toolcalls)
  monkeypatch.setattr(cfg, "EVALS_DIR", evals)
  monkeypatch.setattr(cfg, "FAILS_DIR", fails)
  # Consumidores con nombres enlazados en el import
  monkeypatch.setattr(mem, "EPISODIC_DIR", episodic)
  monkeypatch.setattr(mem, "SEMANTIC_DIR", semantic)
  monkeypatch.setattr(mem, "SUMMARIES_DIR", summaries)
  monkeypatch.setattr(mem, "REFLECTIONS_DIR", reflections)
  monkeypatch.setattr(ingest, "TRACES_DIR", traces)
  monkeypatch.setattr(consolidate, "TRACES_DIR", traces)
  monkeypatch.setattr(factcheck, "TRACES_DIR", traces)
  monkeypatch.setattr(retrieval, "TRACES_DIR", traces)
  monkeypatch.setattr(vs, "CHROMA_DIR", chroma_dir)
  monkeypatch.setattr(vs, "_client", None)

  # Guardia: ningun test debe apuntar a la memoria real
  yield

  monkeypatch.setattr(vs, "_client", None)
