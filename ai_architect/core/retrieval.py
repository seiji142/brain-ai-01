from typing import Dict, Any, List, Optional
from .vectorstore import query_collection, COL_EPISODIC, COL_SEMANTIC
from .memory import load_episode, load_semantic
from .scoring import hybrid_score
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

def retrieve(query: str, top_k: int = 5, project: Optional[str] = None, tags: Optional[List[str]] = None,
             date_from: Optional[str] = None, date_to: Optional[str] = None, collection: str = "semantic") -> Dict[str, Any]:
    trace_id = new_id("tr_")
    where = _build_where(project, tags, date_from, date_to)
    if collection not in ("semantic", "episodic"):
        collection = "semantic"
    res = query_collection(collection, query, n_results=top_k*2, where=where)

    results: List[Dict[str, Any]] = []
    ids = res.get("ids", [])
    metas = res.get("metadatas", [])
    docs = res.get("documents", [])
    dists = res.get("distances", [])

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
        score = hybrid_score(item, dist)
        results.append({
            "id": item_id,
            "type": item.get("type", "episode" if collection=="episodic" else "semantic"),
            "text": item.get("statement") or item.get("summary") or item.get("title") or doc,
            "project": item.get("project", meta.get("project","")),
            "timestamp": ts,
            "score": round(score, 4),
            "evidence": item.get("evidence", []) or [{"type":"episode", "id": eid} for eid in item.get("evidence_source_ids", [])],
            "collection": collection,
        })
        if len(results) >= top_k:
            break

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
