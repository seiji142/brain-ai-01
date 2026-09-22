"""
Test: Filtrado estricto por proyecto en retrieve()
Fix tarea 5 (personalizar-comportamiento-01): memory_search(project=X)
no debe devolver items de otros proyectos salvo opt-in include_other_projects.
"""

import pytest
import shutil
from ai_architect.pipelines.ingest import ingest_episode
from ai_architect.pipelines.consolidate import consolidate_project
from ai_architect.core.retrieval import retrieve
from ai_architect.core.config import (EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR,
                                      REFLECTIONS_DIR, TRACES_DIR, EVALS_DIR,
                                      WORKING_DIR, INDEXES_DIR, FAILS_DIR, TOOLCALLS_DIR)


def _clean_data():
    for sub in [EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR, REFLECTIONS_DIR,
                TRACES_DIR, EVALS_DIR, WORKING_DIR, INDEXES_DIR, FAILS_DIR, TOOLCALLS_DIR]:
        if sub.exists():
            shutil.rmtree(sub)
        sub.mkdir(parents=True, exist_ok=True)


def make_ts(month, day=10):
    return f"2026-{month:02d}-{day:02d}T14:00:00Z"


# Mismo texto clave en dos proyectos distintos: sin filtro estricto,
# el doc de proj-otro (BM25 identico) invadiria resultados de proj-propio.
EP_PROPIO = {
    "id": "ep_strict_own",
    "project": "proj-propio",
    "source_type": "decision",
    "author": "ana",
    "title": "Base de datos del proyecto propio",
    "summary": "Usamos MySQL como base de datos principal del proyecto propio.",
    "timestamp": make_ts(1),
    "decisions": [{"text": "Usar MySQL como base de datos principal", "owner": "ana"}],
    "evidence": [{"type": "doc", "url_or_path": "docs/adr-001.md", "excerpt": "ADR-001: MySQL elegido"}],
    "tags": ["base-de-datos", "mysql", "decision"],
}

EP_OTRO = {
    "id": "ep_strict_other",
    "project": "proj-otro",
    "source_type": "decision",
    "author": "luis",
    "title": "Base de datos de otro proyecto",
    "summary": "Usamos PostgreSQL como base de datos principal de otro proyecto.",
    "timestamp": make_ts(2),
    "decisions": [{"text": "Usar PostgreSQL como base de datos principal", "owner": "luis"}],
    "evidence": [{"type": "doc", "url_or_path": "docs/adr-002.md", "excerpt": "ADR-002: PostgreSQL elegido"}],
    "tags": ["base-de-datos", "postgresql", "decision"],
}


class TestRetrievalStrictProject:

    @pytest.fixture(autouse=True)
    def setup(self):
        _clean_data()
        yield

    def _ingest_both(self):
        assert ingest_episode(EP_PROPIO)["ok"]
        assert ingest_episode(EP_OTRO)["ok"]
        consolidate_project("proj-propio")
        consolidate_project("proj-otro")

    def test_project_filter_es_estricto_por_defecto(self):
        """Con project definido y sin flag, NUNCA devuelve otros proyectos"""
        self._ingest_both()
        res = retrieve(query="base de datos principal", top_k=10,
                       project="proj-propio", collection="semantic")
        assert len(res["results"]) > 0, "Debe encontrar items del proyecto pedido"
        projects = set(r["project"] for r in res["results"])
        assert projects == {"proj-propio"}, f"Fuga cross-project: {projects}"

    def test_include_other_projects_optin_permite_cross(self):
        """Con include_other_projects=True el fallback multi-proyecto funciona"""
        self._ingest_both()
        res = retrieve(query="base de datos principal", top_k=10,
                       project="proj-propio", include_other_projects=True,
                       collection="semantic")
        projects = set(r["project"] for r in res["results"])
        assert "proj-propio" in projects
        assert len(projects) >= 2, f"Opt-in deberia ver otros proyectos: {projects}"

    def test_sin_project_sigue_siendo_global(self):
        """Sin project la busqueda sigue siendo global (sin regresion)"""
        self._ingest_both()
        res = retrieve(query="base de datos principal", top_k=10, collection="semantic")
        projects = set(r["project"] for r in res["results"])
        assert len(projects) >= 2, f"Busqueda global debe ver todos: {projects}"

    def test_flag_default_es_false_en_firma(self):
        """include_other_projects default=False (aislamiento estricto)"""
        import inspect
        from ai_architect.core.retrieval import retrieve as fn
        sig = inspect.signature(fn)
        assert sig.parameters["include_other_projects"].default is False
