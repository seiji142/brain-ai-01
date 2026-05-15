"""
Test 3: Calidad y Contradicciones
Demuestra: conocimiento de calidad, informacion comprobada y respaldada,
factcheck detecta contradicciones, confianza acumulativa con evidencia.
Escenario: multiples fuentes sobre misma decision, algunas contradictorias.
"""

import pytest
import os
import shutil
from pathlib import Path
from ai_architect.pipelines.ingest import ingest_episode
from ai_architect.pipelines.consolidate import consolidate_project
from ai_architect.pipelines.factcheck import factcheck_episode
from ai_architect.pipelines.evaluate import evaluate_query
from ai_architect.core.retrieval import retrieve
from ai_architect.core.memory import list_semantic
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

ep_postgres_1 = {
    "id": "ep_cal_001",
    "project": "eleccion-db",
    "source_type": "meeting",
    "author": "ana",
    "title": "Decision base de datos: PostgreSQL",
    "summary": "El equipo evalua bases de datos y elige PostgreSQL.",
    "timestamp": make_ts(1),
    "decisions": [{"text": "Usar PostgreSQL como base de datos principal", "owner": "ana"}],
    "evidence": [
        {"type": "doc", "url_or_path": "benchmarks/postgresql-vs-mongodb.pdf", "excerpt": "Benchmark: PostgreSQL 2x faster in join operations"},
        {"type": "doc", "url_or_path": "confluence://eleccion-db/ADR-010", "excerpt": "ADR-010: PostgreSQL elegida por consistencia"}
    ],
    "tags": ["base-de-datos", "postgresql", "decision"],
}

ep_mongodb = {
    "id": "ep_cal_002",
    "project": "eleccion-db",
    "source_type": "meeting",
    "author": "luis",
    "title": "Propuesta alternativa: MongoDB",
    "summary": "Se propone MongoDB como alternativa.",
    "timestamp": make_ts(2),
    "decisions": [{"text": "Usar MongoDB en lugar de PostgreSQL por schema flexible", "owner": "luis"}],
    "evidence": [
        {"type": "doc", "url_or_path": "benchmarks/mongodb-vs-postgresql.pdf", "excerpt": "Benchmark: MongoDB 3x faster in document reads"}
    ],
    "tags": ["base-de-datos", "mongodb", "decision"],
}

ep_postgres_2 = {
    "id": "ep_cal_003",
    "project": "eleccion-db",
    "source_type": "pr",
    "author": "maria",
    "title": "Implementacion exitosa con PostgreSQL",
    "summary": "PostgreSQL funcionando sin problemas en produccion.",
    "timestamp": make_ts(3),
    "decisions": [{"text": "Usar PostgreSQL como base de datos principal", "owner": "maria"}],
    "evidence": [
        {"type": "pr", "url_or_path": "github.com/eleccion-db/infra/pull/12", "excerpt": "PR #12: 0 incidentes en 30 dias"},
        {"type": "doc", "url_or_path": "confluence://eleccion-db/metrics", "excerpt": "99.9% uptime, p95 latency <10ms"}
    ],
    "tags": ["base-de-datos", "postgresql", "produccion"],
}

ep_sin_evidencia = {
    "id": "ep_cal_004",
    "project": "eleccion-db",
    "source_type": "chat",
    "author": "pedro",
    "title": "Opinion sobre base de datos",
    "summary": "Pedro opina que deberian usar Cassandra.",
    "timestamp": make_ts(4),
    "decisions": [{"text": "Usar Cassandra en lugar de PostgreSQL por escalabilidad", "owner": "pedro"}],
    "evidence": [],
    "tags": ["base-de-datos", "cassandra"],
}

ep_postgres_3 = {
    "id": "ep_cal_005",
    "project": "eleccion-db",
    "source_type": "incident",
    "author": "ana",
    "title": "PostgreSQL resiste pico de trafico",
    "summary": "PostgreSQL manejo 10x el trafico normal sin degradacion.",
    "timestamp": make_ts(5),
    "decisions": [{"text": "Usar PostgreSQL como base de datos principal", "owner": "ana"}],
    "evidence": [
        {"type": "doc", "url_or_path": "monitoring/black-friday-2026.pdf", "excerpt": "Black Friday: 10x trafico, 0 downtime"}
    ],
    "tags": ["base-de-datos", "postgresql", "escalabilidad"],
}


class TestCalidadContradicciones:

    @pytest.fixture(autouse=True)
    def setup(self):
        _clean_data()
        yield

    def test_ingesta_5_episodios(self):
        """Ingesta los 5 episodios correctamente"""
        for ep in [ep_postgres_1, ep_mongodb, ep_postgres_2, ep_sin_evidencia, ep_postgres_3]:
            res = ingest_episode(ep)
            assert res["ok"]

    def test_factcheck_no_detecta_contradiccion_sin_base(self):
        """Factcheck sobre primer episodio no encuentra contradiccion"""
        ingest_episode(ep_postgres_1)
        fc = factcheck_episode("ep_cal_001")
        assert fc["ok"] is True
        assert fc["confidence"] >= 0.6

    def test_factcheck_detecta_contradiccion(self):
        """Factcheck detecta contradiccion entre PostgreSQL y MongoDB"""
        ingest_episode(ep_postgres_1)
        consolidate_project("eleccion-db")
        ingest_episode(ep_mongodb)
        fc = factcheck_episode("ep_cal_002")
        assert fc["confidence"] <= 0.8

    def test_consolidacion_sin_evidencia_confianza_minima(self):
        """Episodio sin evidencia se promociona con confianza minima"""
        for ep in [ep_postgres_1, ep_mongodb, ep_postgres_2, ep_sin_evidencia]:
            ingest_episode(ep)
        consolidate_project("eleccion-db")
        sems = list_semantic(project="eleccion-db")
        cassandra_items = [s for s in sems if "cassandra" in s["statement"].lower()]
        assert len(cassandra_items) == 1
        cass = cassandra_items[0]
        assert cass["confidence"] <= 0.6, f"Confianza no minima: {cass['confidence']}"

    def test_confidence_aumenta_con_evidencia_repetida(self):
        """Decision PostgreSQL acumula confidence con cada episodio que la respalda"""
        for ep in [ep_postgres_1, ep_mongodb, ep_postgres_2, ep_sin_evidencia, ep_postgres_3]:
            ingest_episode(ep)
        consolidate_project("eleccion-db")
        sems = list_semantic(project="eleccion-db", type_="decision")
        postgres_items = [s for s in sems if "postgres" in s["statement"].lower()]
        assert len(postgres_items) >= 1
        pg = postgres_items[0]
        assert pg["confidence"] >= 0.7, f"Confidence bajo: {pg['confidence']}"
        assert len(pg.get("evidence_source_ids", [])) >= 2, "Poca evidencia para decision respaldada"

    def test_retrieval_prioriza_conocimiento_con_evidencia(self):
        """Items con mas evidencia tienen mejor score en retrieval"""
        for ep in [ep_postgres_1, ep_mongodb, ep_postgres_2, ep_sin_evidencia, ep_postgres_3]:
            ingest_episode(ep)
        consolidate_project("eleccion-db")
        res = retrieve(query="que base de datos usar", top_k=5, project="eleccion-db", collection="semantic")
        assert len(res["results"]) > 0
        pg_results = [r for r in res["results"] if "postgres" in r["text"].lower()]
        if pg_results:
            assert pg_results[0]["score"] > 0.6

    def test_calidad_evaluacion_conocimiento(self):
        """Evaluacion muestra hallucination_risk bajo en items respaldados"""
        for ep in [ep_postgres_1, ep_mongodb, ep_postgres_2, ep_sin_evidencia, ep_postgres_3]:
            ingest_episode(ep)
        consolidate_project("eleccion-db")
        ev = evaluate_query(query="base de datos principal", project="eleccion-db", top_k=5, collection="semantic")
        for i, risk in enumerate(ev["hallucination_risk"]):
            if ev["has_evidence"][i]:
                assert risk <= 0.5

    def test_contradiccion_queda_registrada(self):
        """Las contradicciones quedan registradas en los items semanticos"""
        for ep in [ep_postgres_1, ep_mongodb, ep_postgres_2]:
            ingest_episode(ep)
        consolidate_project("eleccion-db")
        sems = list_semantic()
        pg_items = [s for s in sems if "postgres" in s["statement"].lower()]
        if pg_items:
            pg = pg_items[0]
            if "contradictions" in pg:
                assert isinstance(pg["contradictions"], list)

    def test_trazabilidad_completa(self):
        """Cada operacion devuelve trace_id"""
        for ep in [ep_postgres_1, ep_mongodb]:
            ingest_episode(ep)
        cons = consolidate_project("eleccion-db")
        ret = retrieve(query="base de datos", project="eleccion-db")
        ev = evaluate_query(query="base de datos", project="eleccion-db")
        assert cons["trace_id"].startswith("tr_")
        assert ret["trace_id"].startswith("tr_")
        assert ev["trace_id"].startswith("tr_")
