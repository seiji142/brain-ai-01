from typing import Dict, Any
from ..core.memory import save_semantic, list_semantic
from ..core.vectorstore import index_semantic
from ..core.utils import now_iso, new_id
from ..core.config import TRACES_DIR
from ..core.utils import append_jsonl
from .summarize import summarize_episode
from .factcheck import factcheck_episode

def _build_statement(ep: dict) -> str:
    summary = (ep.get("summary") or "").strip()
    decisions = ep.get("decisions", [])
    if decisions:
        dtexts = "\n".join(d.get("text", "") for d in decisions if d.get("text"))
        if summary:
            return summary + "\n" + dtexts
        return dtexts
    return summary

def _build_embedding_text(ep: dict) -> str:
    parts = []
    if ep.get("title"):
        parts.append(ep["title"])
    if ep.get("summary"):
        parts.append(ep["summary"])
    for d in ep.get("decisions", []):
        if d.get("text"):
            parts.append(d["text"])
    return "\n".join(parts)

def consolidate_project(project: str | None = None) -> Dict[str, Any]:
    trace_id = new_id("tr_")
    from ..core.memory import list_episodes
    eps = list_episodes(project=project)
    promotions = 0
    contradictions = 0
    for ep in eps:
        try:
            summarize_episode(ep["id"])
        except Exception:
            pass
        fc = factcheck_episode(ep["id"])
        if not fc["ok"]:
            contradictions += 1
            continue
        if fc["confidence"] < 0.6:
            continue
        decisions = ep.get("decisions", [])
        summary = (ep.get("summary") or "").strip()
        if not decisions and not summary:
            continue
        sems = list_semantic(project=ep.get("project"), type_="decision")
        dup = False
        candidate_text = _build_statement(ep).lower()
        for s in sems:
            if s.get("statement","").lower() == candidate_text:
                dup = True
                ev = set(s.get("evidence_source_ids", []))
                ev.add(ep["id"])
                s["evidence_source_ids"] = list(ev)
                s["confidence"] = min(1.0, s.get("confidence", 0.6) + 0.05)
                s["updated_at"] = now_iso()
                save_semantic(s)
                index_semantic(s)
                break
        if dup:
            continue
        item = {
            "type": "decision",
            "project": ep.get("project"),
            "statement": _build_statement(ep),
            "confidence": fc["confidence"],
            "evidence_source_ids": [ep["id"]],
            "contradictions": fc.get("contradictions", []),
            "tags": ep.get("tags", []),
            "embedding_text": _build_embedding_text(ep),
        }
        save_semantic(item)
        index_semantic(item)
        promotions += 1

    res = {"trace_id": trace_id, "ts": now_iso(), "operation": "consolidate", "project": project,
           "promotions": promotions, "contradictions": contradictions}
    append_jsonl(TRACES_DIR / "consolidate.jsonl", res)
    return res
