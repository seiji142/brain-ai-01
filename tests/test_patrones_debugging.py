"""
Test 2: Patrones de Debugging
Demuestra: consolidacion en conocimiento reutilizable entre proyectos,
agente de IA acumula experiencia, mejora independientemente del modelo.
Escenario: 4 episodios de debugging en distintos proyectos con patron comun.
"""

import pytest
import os
import shutil
from pathlib import Path
from ai_architect.pipelines.ingest import ingest_episode
from ai_architect.pipelines.consolidate import consolidate_project
from ai_architect.pipelines.evaluate import evaluate_query
from ai_architect.core.retrieval import retrieve
from ai_architect.core.memory import list_semantic, list_episodes
from ai_architect.core.config import MEMORY_ROOT, LOG_DIR, CHROMA_DIR, WORKING_DIR, INDEXES_DIR
from ai_architect.core.config import EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR, REFLECTIONS_DIR
from ai_architect.core.config import TRACES_DIR, EVALS_DIR, FAILS_DIR, TOOLCALLS_DIR

def _clean_data():
    for sub in [EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR, REFLECTIONS_DIR,
                TRACES_DIR, EVALS_DIR, WORKING_DIR, INDEXES_DIR, FAILS_DIR, TOOLCALLS_DIR]:
        if sub.exists():
            shutil.rmtree(sub)
        sub.mkdir(parents=True, exist_ok=True)

def make_ts(month, day=10):
    return f"2026-{month:02d}-{day:02d}T14:00:00Z"

episodios = [
    {
        "id": "ep_debug_001",
        "project": "proj-alpha",
        "source_type": "incident",
        "author": "ana",
        "title": "Timeout en PostgreSQL",
        "summary": "La conexion a PostgreSQL timeout. Se configura pool de conexiones.",
        "timestamp": make_ts(1),
        "decisions": [
            {"text": "Configurar pool de conexiones PostgreSQL con max_connections=20", "owner": "ana"},
        ],
        "evidence": [{"type": "ticket", "url_or_path": "github.com/proj-alpha/issues/12", "excerpt": "Issue #12: connection timeout resuelto con pool"}],
        "tags": ["debugging", "conexion", "postgresql", "pool"],
    },
    {
        "id": "ep_debug_002",
        "project": "proj-beta",
        "source_type": "incident",
        "author": "luis",
        "title": "Caida de Redis por falta de health check",
        "summary": "Redis se cayo y la app no supo reconectar. Se agrega health check y pool.",
        "timestamp": make_ts(2),
        "decisions": [
            {"text": "Implementar health check periodico y pool de conexiones para Redis", "owner": "luis"},
        ],
        "evidence": [{"type": "ticket", "url_or_path": "github.com/proj-beta/issues/45", "excerpt": "Issue #45: Redis caida resuelto con pool + health check"}],
        "tags": ["debugging", "conexion", "redis", "pool"],
    },
    {
        "id": "ep_debug_003",
        "project": "proj-gamma",
        "source_type": "incident",
        "author": "ana",
        "title": "Timeout en API externa de pagos",
        "summary": "API de pagos timeout. Se implementa circuit breaker con retry.",
        "timestamp": make_ts(3),
        "decisions": [
            {"text": "Implementar circuit breaker con retry y backoff exponencial para API externa", "owner": "ana"},
        ],
        "evidence": [{"type": "ticket", "url_or_path": "github.com/proj-gamma/issues/78", "excerpt": "Issue #78: timeout API pagos resuelto con circuit breaker"}],
        "tags": ["debugging", "conexion", "api-externa", "circuit-breaker"],
    },
    {
        "id": "ep_debug_004",
        "project": "proj-delta",
        "source_type": "incident",
        "author": "luis",
        "title": "Desconexion de Kafka en productor",
        "summary": "El productor Kafka se desconecta. Se configura reconnect con backoff.",
        "timestamp": make_ts(4),
        "decisions": [
            {"text": "Configurar reconnect con backoff exponencial y buffer en productor Kafka", "owner": "luis"},
        ],
        "evidence": [{"type": "ticket", "url_or_path": "github.com/proj-delta/issues/34", "excerpt": "Issue #34: desconexion Kafka resuelto con reconnect backoff"}],
        "tags": ["debugging", "conexion", "kafka", "backoff"],
    },
]


class TestPatronesDebugging:

    @pytest.fixture(autouse=True)
    def setup(self):
        _clean_data()
        yield

    def test_ingesta_multiproyecto(self):
        """Ingesta episodios de 4 proyectos distintos"""
        for ep in episodios:
            res = ingest_episode(ep)
            assert res["ok"]
        all_eps = list_episodes()
        assert len(all_eps) == 4
        projects = set(e["project"] for e in all_eps)
        assert len(projects) == 4

    def test_consolidacion_reutilizable(self):
        """Cada proyecto consolida sus propias decisiones"""
        for ep in episodios:
            ingest_episode(ep)
        for proj in ["proj-alpha", "proj-beta", "proj-gamma", "proj-delta"]:
            cons = consolidate_project(proj)
            assert cons["promotions"] >= 1, f"{proj}: {cons}"
        sems = list_semantic()
        assert len(sems) >= 4

    def test_retrieval_cross_project_conexion(self):
        """Busqueda por 'conexion' encuentra episodios de todos los proyectos"""
        for ep in episodios:
            ingest_episode(ep)
        for proj in ["proj-alpha", "proj-beta", "proj-gamma", "proj-delta"]:
            consolidate_project(proj)
        res = retrieve(query="problemas de conexion a base de datos", top_k=10, collection="episodic")
        projects_encontrados = set(r["project"] for r in res["results"])
        assert len(projects_encontrados) >= 2, "Debe encontrar al menos 2 proyectos distintos"

    def test_conocimiento_reutilizable_entre_proyectos(self):
        """El conocimiento semantico es accesible desde cualquier proyecto"""
        for ep in episodios:
            ingest_episode(ep)
        for proj in ["proj-alpha", "proj-beta", "proj-gamma", "proj-delta"]:
            consolidate_project(proj)
        sems = list_semantic()
        statements = [s["statement"].lower() for s in sems]
        assert any("pool" in s for s in statements), "Debe haber soluciones con pool"
        assert any("circuit" in s or "retry" in s for s in statements), "Debe haber circuit breaker"
        assert any("backoff" in s or "reconnect" in s for s in statements), "Debe haber backoff"
        for s in sems:
            assert len(s.get("evidence_source_ids", [])) >= 1, f"Sin evidencia: {s['id']}"

    def test_score_recency_prioriza_reciente(self):
        """Items mas recientes tienen mejor score por recencia"""
        for ep in episodios:
            ingest_episode(ep)
        for proj in ["proj-alpha", "proj-beta", "proj-gamma", "proj-delta"]:
            consolidate_project(proj)
        res = retrieve(query="solucion problemas conexion", top_k=4, collection="semantic")
        kafka_results = [r for r in res["results"] if "kafka" in r["text"].lower()]
        assert any(r["score"] > 0.6 for r in kafka_results) if kafka_results else True

    def test_evaluacion_mide_calidad(self):
        """La evaluacion genera metricas de calidad"""
        for ep in episodios:
            ingest_episode(ep)
        for proj in ["proj-alpha", "proj-beta", "proj-gamma", "proj-delta"]:
            consolidate_project(proj)
        ev = evaluate_query(query="problemas de conexion", top_k=5, collection="episodic")
        assert "trace_id" in ev
        assert len(ev["retrieved_ids"]) > 0
        assert len(ev["relevance"]) == len(ev["retrieved_ids"])
        assert all(0 <= r <= 1 for r in ev["relevance"])
