from typing import Dict, Any, List, Optional
from .vectorstore import query_collection, COL_EPISODIC, COL_SEMANTIC
from .memory import load_episode, load_semantic
from .scoring import hybrid_score, compute_bm25_scores
from .utils import date_range_filter_ok, new_id, append_jsonl, now_iso
from .config import TRACES_DIR

def _build_where(project: Optional[str], tags: Optional[List[str]], date_from: Optional[str], date_to: Optional[str]) -> Optional[Dict[str, Any]]:
    where: Dict[str, Any] = {}
    if project:
        where["project"] = project
    if date_from or date_to:
        pass
    if not where:
        return None
    return where

def _load_candidates(collection: str, ids: List[str], metas: List[Dict], docs: List[str], dists: List[float],
                     tags: Optional[List[str]], date_from: Optional[str], date_to: Optional[str]) -> List:
    candidates: List[Dict[str, Any]] = []
    for i in range(len(ids)):
        item_id = ids[i]
        meta = metas[i] if i < len(metas) else {}
        doc = docs[i] if i < len(docs) else ""
        dist = dists[i] if i < len(dists) else 1.0
        if collection == "semantic":
            try:
                item = load_semantic(item_id)
            except Exception:
                item = {"id": item_id, "statement": doc, "project": meta.get("project",""),
                        "timestamp": meta.get("timestamp",""), "type": meta.get("type","fact"),
                        "confidence": meta.get("confidence",0.7), "evidence_source_ids": []}
        else:
            try:
                item = load_episode(item_id)
            except Exception:
                item = {"id": item_id, "summary": doc, "project": meta.get("project",""),
                        "timestamp": meta.get("timestamp",""), "evidence": []}
        ts = item.get("timestamp") or item.get("updated_at") or item.get("created_at") or meta.get("timestamp") or ""
        if not date_range_filter_ok(ts, date_from, date_to):
            continue
        if tags:
            item_tags = set(item.get("tags", []))
            if not any(t in item_tags for t in tags):
                meta_tags = set(meta.get("tags","").split(",")) if meta.get("tags") else set()
                if not any(t in meta_tags for t in tags):
                    continue
        text = item.get("statement") or item.get("summary") or item.get("title") or doc
        candidates.append((item, dist, text, ts, meta))
    return candidates


def _deduplicate(candidates: List) -> List:
    seen: set = set()
    unique: List = []
    for c in candidates:
        item_id = c[0].get("id")
        if item_id and item_id not in seen:
            seen.add(item_id)
            unique.append(c)
    return unique


def retrieve(query: str, top_k: int = 5, project: Optional[str] = None, tags: Optional[List[str]] = None,
             date_from: Optional[str] = None, date_to: Optional[str] = None, collection: str = "semantic") -> Dict[str, Any]:
    trace_id = new_id("tr_")
    where = _build_where(project, tags, date_from, date_to)
    if collection not in ("semantic", "episodic"):
        collection = "semantic"
    res = query_collection(collection, query, n_results=top_k*5, where=where)

    candidates: List[Dict[str, Any]] = _load_candidates(
        collection, res.get("ids", []), res.get("metadatas", []),
        res.get("documents", []), res.get("distances", []),
        tags, date_from, date_to
    )

    # Fallback multi-proyecto: si hay filtro de project, buscar todos los items sin filtro
    # para que BM25 + hybrid scoring encuentre matches en otros proyectos.
    # Usamos n_results alto (1000) para cubrir toda la coleccion, compensando hash embeddings.
    if project:
        fallback_res = query_collection(collection, query, n_results=1000, where=None)
        fallback_candidates = _load_candidates(
            collection, fallback_res.get("ids", []), fallback_res.get("metadatas", []),
            fallback_res.get("documents", []), fallback_res.get("distances", []),
            tags, date_from, date_to
        )
        candidates = _deduplicate(candidates + fallback_candidates)

    # BM25 scoring sobre todos los candidatos
    texts = [c[2] for c in candidates]
    bm25_scores = compute_bm25_scores(query, texts) if texts else []

    results: List[Dict[str, Any]] = []
    for idx, (item, dist, text, ts, meta) in enumerate(candidates):
        bm25 = bm25_scores[idx] if bm25_scores else 0.0
        score = hybrid_score(item, dist, bm25)
        results.append({
            "id": item.get("id", item.get("id")),
            "type": item.get("type", "episode" if collection=="episodic" else "semantic"),
            "text": text,
            "project": item.get("project", meta.get("project","")),
            "timestamp": ts,
            "score": round(score, 4),
            "evidence": item.get("evidence", []) or [{"type":"episode", "id": eid} for eid in item.get("evidence_source_ids", [])],
            "collection": collection,
        })

    # Ordenar por score descendente y limitar a top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]

    trace = {
        "trace_id": trace_id,
        "ts": now_iso(),
        "operation": "retrieve",
        "inputs": {"query": query, "top_k": top_k, "project": project, "tags": tags,
                   "date_from": date_from, "date_to": date_to, "collection": collection},
        "outputs": {"count": len(results), "results": results},
        "latency_ms": 0,
    }
    append_jsonl(TRACES_DIR / "retrieve.jsonl", trace)
    return {"trace_id": trace_id, "results": results}
