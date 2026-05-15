from typing import Dict, Any, List
from ..core.retrieval import retrieve
from ..core.utils import now_iso, new_id
from ..core.config import EVALS_DIR
from ..core.utils import append_jsonl

def evaluate_query(query: str, project: str | None = None, top_k: int = 5, collection: str = "semantic") -> Dict[str, Any]:
    trace_id = new_id("tr_")
    r = retrieve(query=query, top_k=top_k, project=project, collection=collection)
    results = r.get("results", [])
    relevance = []
    has_evidence = []
    halluc_risk = []
    for res in results:
        rel = min(1.0, res.get("score", 0.0) + 0.2)
        ev = len(res.get("evidence", [])) > 0
        hr = 1.0 - rel
        if ev:
            hr = max(0.0, hr - 0.3)
        relevance.append(round(rel, 2))
        has_evidence.append(ev)
        halluc_risk.append(round(hr, 2))
    eval_rec = {
        "trace_id": trace_id,
        "ts": now_iso(),
        "query": query,
        "project": project,
        "collection": collection,
        "retrieved_ids": [x["id"] for x in results],
        "scores": [x["score"] for x in results],
        "relevance": relevance,
        "has_evidence": has_evidence,
        "hallucination_risk": halluc_risk,
        "notes": "Heurístico (demo). Sustituir por evaluación humana o LLM judge.",
    }
    append_jsonl(EVALS_DIR / "evaluations.jsonl", eval_rec)
    return eval_rec
