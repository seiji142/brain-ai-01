"""Tests de collection="both" en retrieve (C1 de 16M, 29/09/2026).

El default de memory_search pasa a buscar en episodic + semantic y
mergear por score (misma semantica que clients/memoria.buscar).
Aislamiento via tests/conftest.py (tmp_path): no toca produccion.
"""
import pytest

from ai_architect.pipelines.ingest import ingest_episode
from ai_architect.pipelines.consolidate import consolidate_project
from ai_architect.core.retrieval import retrieve


EP = {
    "id": "ep_both_001",
    "project": "proj-both",
    "source_type": "chat",
    "author": "tester",
    "title": "Cache Redis para sesiones",
    "summary": "Se adopta Redis como cache de sesiones con TTL de 30 minutos",
    "timestamp": "2026-09-29T12:00:00Z",
    "decisions": [{"text": "Adoptar Redis como cache de sesiones"}],
    "actions": [],
    "risks": [],
    "evidence": [],
    "tags": ["cache", "redis"],
}


@pytest.fixture()
def seeded():
    res = ingest_episode(dict(EP))
    assert res["ok"], f"Fallo ingest: {res}"
    cons = consolidate_project("proj-both")
    assert cons["promotions"] >= 1, f"Sin promociones: {cons}"
    return res


def test_both_trae_ambas_colecciones(seeded):
    res = retrieve(query="Redis cache sesiones", top_k=5,
                   project="proj-both", collection="both")
    cols = {r["collection"] for r in res["results"]}
    assert "episodic" in cols, f"Falta episodic: {res['results']}"
    assert "semantic" in cols, f"Falta semantic: {res['results']}"


def test_both_respeta_top_k(seeded):
    res = retrieve(query="Redis cache sesiones", top_k=1,
                   project="proj-both", collection="both")
    assert len(res["results"]) == 1


def test_semantic_solo_sigue_igual(seeded):
    res = retrieve(query="Redis cache sesiones", top_k=5,
                   project="proj-both", collection="semantic")
    assert len(res["results"]) >= 1
    assert all(r["collection"] == "semantic" for r in res["results"])


def test_episodic_solo_sigue_igual(seeded):
    res = retrieve(query="Redis cache sesiones", top_k=5,
                   project="proj-both", collection="episodic")
    assert len(res["results"]) >= 1
    assert all(r["collection"] == "episodic" for r in res["results"])


def test_coleccion_desconocida_cae_a_semantic(seeded):
    res = retrieve(query="Redis cache sesiones", top_k=5,
                   project="proj-both", collection="inexistente")
    assert len(res["results"]) >= 1
    assert all(r["collection"] == "semantic" for r in res["results"])
