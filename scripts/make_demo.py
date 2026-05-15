from ai_architect.pipelines.ingest import ingest_episode
from ai_architect.pipelines.summarize import summarize_episode
from ai_architect.pipelines.reflect import reflect_project
from ai_architect.pipelines.factcheck import factcheck_episode
from ai_architect.pipelines.consolidate import consolidate_project
from ai_architect.core.retrieval import retrieve
from ai_architect.pipelines.evaluate import evaluate_query
from ai_architect.core.utils import now_iso
from pathlib import Path
import json

def main():
    print(">>> Running demo...")

    ep1 = {
        "project": "demo-auth",
        "source_type": "meeting",
        "author": "ana",
        "title": "Decisión de autenticación",
        "summary": "El equipo decide usar JWT con refresh tokens rotativos y revocación por lista negra en Redis.",
        "timestamp": now_iso(),
        "decisions": [
            {"text": "Usar JWT con refresh tokens rotativos", "owner": "ana"},
            {"text": "Implementar revocación por lista negra en Redis", "owner": "luis"},
        ],
        "actions": [{"text": "Implementar servicio auth", "owner": "luis", "due_date": "2026-05-30T00:00:00Z"}],
        "risks": [{"text": "Riesgo de gestión de claves JWT", "severity": "high"}],
        "evidence": [{"type": "doc", "url_or_path": "confluence://auth/ADR-01", "excerpt": "ADR-01 aprueba JWT + refresh rotativo"}],
        "tags": ["auth", "seguridad"],
    }
    r1 = ingest_episode(ep1)
    print("Ingest ep1:", r1)

    ep2 = {
        "project": "demo-auth",
        "source_type": "pr",
        "author": "luis",
        "title": "Implementación auth service",
        "summary": "Se mergea implementación de JWT con refresh rotativos y blacklist Redis.",
        "timestamp": now_iso(),
        "decisions": [
            {"text": "Usar JWT con refresh tokens rotativos", "owner": "luis"},
        ],
        "actions": [{"text": "Configurar rotación y revocación", "owner": "luis"}],
        "risks": [{"text": "Fuga de refresh token", "severity": "medium"}],
        "evidence": [{"type": "pr", "url_or_path": "github.com/org/repo/pull/42", "excerpt": "PR #42 implementa refresh rotativo"}],
        "tags": ["auth", "backend"],
    }
    r2 = ingest_episode(ep2)
    print("Ingest ep2:", r2)

    summarize_episode(r1["episode_id"])
    summarize_episode(r2["episode_id"])
    reflect_project("demo-auth")
    factcheck_episode(r1["episode_id"])
    factcheck_episode(r2["episode_id"])

    cons = consolidate_project("demo-auth")
    print("Consolidate:", cons)

    ret = retrieve(query="decisión de autenticación JWT", top_k=3, project="demo-auth", collection="semantic")
    print("Retrieve (semantic):", json.dumps(ret, ensure_ascii=False, indent=2))

    ev = evaluate_query(query="decisión de autenticación JWT", project="demo-auth", top_k=3, collection="semantic")
    print("Evaluate:", json.dumps(ev, ensure_ascii=False, indent=2))

    print(">>> Demo completada. Revisa: memory/episodic/, memory/semantic/, memory/summaries/, memory/reflections/, logs/traces/, logs/evaluations/, .ai_memory/chroma/")

if __name__ == "__main__":
    main()
