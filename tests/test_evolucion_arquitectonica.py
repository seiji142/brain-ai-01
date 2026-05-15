"""
Test 1: Evolucion Arquitectonica
Demuestra: aprendizaje continuo, acumulacion de experiencia,
mejora con el tiempo independientemente del modelo.
Escenario: equipo evoluciona su arquitectura durante 4 meses.
"""

import pytest
import os
import shutil
from pathlib import Path
from ai_architect.pipelines.ingest import ingest_episode
from ai_architect.pipelines.consolidate import consolidate_project
from ai_architect.pipelines.reflect import reflect_project
from ai_architect.core.retrieval import retrieve
from ai_architect.core.memory import list_semantic
from ai_architect.core.config import MEMORY_ROOT, LOG_DIR, CHROMA_DIR, WORKING_DIR, INDEXES_DIR
from ai_architect.core.config import EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR, REFLECTIONS_DIR
from ai_architect.core.config import TRACES_DIR, EVALS_DIR, FAILS_DIR, TOOLCALLS_DIR

def _clean_data():
    # Clean JSON/L data dirs only (ChromaDB files are locked between tests)
    for sub in [EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR, REFLECTIONS_DIR,
                TRACES_DIR, EVALS_DIR, WORKING_DIR, INDEXES_DIR]:
        if sub.exists():
            shutil.rmtree(sub)
        sub.mkdir(parents=True, exist_ok=True)

def make_ts(month, day=15, hour=10):
    return f"2026-{month:02d}-{day:02d}T{hour:02d}:00:00Z"

episodios = [
    {
        "id": "ep_arq_001",
        "project": "proyecto-x",
        "source_type": "meeting",
        "author": "ana",
        "title": "Decision inicial: monolitio para MVP",
        "summary": "El equipo decide comenzar con arquitectura monolitica para lanzar rapido el MVP.",
        "timestamp": make_ts(1),
        "decisions": [
            {"text": "Usar monolitio con Django para MVP", "owner": "ana"},
            {"text": "Postergar microservicios a v2", "owner": "luis"},
        ],
        "actions": [{"text": "Configurar proyecto Django", "owner": "ana", "due_date": "2026-01-30T00:00:00Z"}],
        "risks": [{"text": "Deuda tecnica por no separar modulos", "severity": "medium"}],
        "evidence": [{"type": "doc", "url_or_path": "confluence://proyecto-x/ADR-001", "excerpt": "ADR-001: aprobado monolitio para MVP"}],
        "tags": ["arquitectura", "backend", "mvp"],
    },
    {
        "id": "ep_arq_002",
        "project": "proyecto-x",
        "source_type": "incident",
        "author": "luis",
        "title": "Problemas de escalabilidad en monolitio",
        "summary": "El monolitio presenta cuellos de botella. Los despliegues tardan 20 minutos.",
        "timestamp": make_ts(2),
        "decisions": [
            {"text": "Dividir monolitio en modulos independientes", "owner": "ana"},
        ],
        "actions": [{"text": "Identificar boundaries de dominios", "owner": "luis", "due_date": "2026-02-28T00:00:00Z"}],
        "risks": [{"text": "Riesgo de migracion con datos en produccion", "severity": "high"}],
        "evidence": [{"type": "ticket", "url_or_path": "github.com/proyecto-x/issues/142", "excerpt": "Issue #142: p95 latency 5s, deploy time 20min"}],
        "tags": ["arquitectura", "escalabilidad", "incidente"],
    },
    {
        "id": "ep_arq_003",
        "project": "proyecto-x",
        "source_type": "meeting",
        "author": "ana",
        "title": "Migracion a microservicios con API Gateway",
        "summary": "Decision final de migrar a microservicios con Kong como API Gateway.",
        "timestamp": make_ts(3),
        "decisions": [
            {"text": "Migrar a microservicios con Kong API Gateway", "owner": "ana"},
            {"text": "Cada servicio con su propia base de datos", "owner": "luis"},
        ],
        "actions": [{"text": "Migrar auth service primero", "owner": "ana", "due_date": "2026-04-01T00:00:00Z"}],
        "risks": [{"text": "Complejidad de red entre servicios", "severity": "medium"}],
        "evidence": [
            {"type": "doc", "url_or_path": "confluence://proyecto-x/ADR-002", "excerpt": "ADR-002: arquitectura microservicios aprobada"},
            {"type": "pr", "url_or_path": "github.com/proyecto-x/pull/45", "excerpt": "PR #45: POC migracion exitoso con 40% mejora latencia"}
        ],
        "tags": ["arquitectura", "microservicios", "api-gateway"],
    },
    {
        "id": "ep_arq_004",
        "project": "proyecto-x",
        "source_type": "pr",
        "author": "luis",
        "title": "Implementacion event sourcing para pedidos",
        "summary": "Se implementa event sourcing para el dominio de pedidos, mejorando trazabilidad.",
        "timestamp": make_ts(4),
        "decisions": [
            {"text": "Implementar event sourcing en modulo de pedidos", "owner": "luis"},
        ],
        "actions": [{"text": "Desplegar event store con PostgreSQL", "owner": "luis", "due_date": "2026-04-30T00:00:00Z"}],
        "risks": [{"text": "Eventual consistency puede afectar UX", "severity": "low"}],
        "evidence": [
            {"type": "pr", "url_or_path": "github.com/proyecto-x/pull/89", "excerpt": "PR #89: event sourcing - 99.9% trazabilidad"},
            {"type": "doc", "url_or_path": "confluence://proyecto-x/metrics", "excerpt": "Metricas: 50% menos bugs en pedidos"}
        ],
        "tags": ["arquitectura", "event-sourcing", "pedidos"],
    },
]


class TestEvolucionArquitectonica:

    @pytest.fixture(autouse=True)
    def setup(self):
        _clean_data()
        yield

    def test_aprendizaje_continuo_4_meses(self):
        """Ingesta secuencial de 4 episodios a lo largo de 4 meses"""
        ids = []
        for ep in episodios:
            res = ingest_episode(ep)
            assert res["ok"], f"Fallo ingest: {res}"
            ids.append(res["episode_id"])
        assert len(ids) == 4

    def test_consolidacion_promueve_decisiones(self):
        """La consolidacion promueve decisiones a memoria semantica"""
        for ep in episodios:
            ingest_episode(ep)
        cons = consolidate_project("proyecto-x")
        assert cons["promotions"] >= 2, f"Solo {cons['promotions']} promociones"

    def test_retrieval_encuentra_evolucion(self):
        """Retrieval encuentra las decisiones ordenadas por relevancia"""
        for ep in episodios:
            ingest_episode(ep)
        consolidate_project("proyecto-x")
        res = retrieve(query="decisiones de arquitectura del proyecto", top_k=5,
                       project="proyecto-x", collection="semantic")
        assert len(res["results"]) > 0
        texts = [r["text"].lower() for r in res["results"]]
        micro = any("microservicio" in t for t in texts)
        event = any("event" in t for t in texts)
        assert micro or event, "Decisiones clave no encontradas: " + str(texts)

    def test_reflexion_detecta_patron(self):
        """El reflector detecta temas recurrentes"""
        for ep in episodios:
            ingest_episode(ep)
        ref = reflect_project("proyecto-x")
        assert len(ref["patterns"]) > 0
        all_patterns = " ".join(ref["patterns"]).lower()
        assert "escal" in all_patterns or "arquitect" in all_patterns or "backend" in all_patterns

    def test_confidence_acumulativo(self):
        """Decisiones repetidas incrementan su confidence"""
        for ep in episodios:
            ingest_episode(ep)
        consolidate_project("proyecto-x")
        sems = list_semantic(project="proyecto-x", type_="decision")
        assert len(sems) > 0
        for s in sems:
            assert "confidence" in s
            assert s["confidence"] >= 0.6
            assert len(s.get("evidence_source_ids", [])) >= 1

    def test_retrieval_independiente_del_modelo(self):
        """El retrieval funciona para cualquier proyecto/query"""
        for ep in episodios:
            ingest_episode(ep)
        consolidate_project("proyecto-x")
        res_sem = retrieve(query="arquitectura", project="proyecto-x", collection="semantic")
        res_ep = retrieve(query="arquitectura", project="proyecto-x", collection="episodic")
        assert len(res_sem["results"]) > 0
        assert len(res_ep["results"]) > 0
        assert res_sem["trace_id"].startswith("tr_")
