from typing import Dict, Any, List
from ..core.memory import load_episode, list_semantic
from ..core.utils import now_iso, new_id
from ..core.config import TRACES_DIR
from ..core.utils import append_jsonl

def factcheck_episode(episode_id: str) -> Dict[str, Any]:
    trace_id = new_id("tr_")
    ep = load_episode(episode_id)
    project = ep.get("project")
    sems = list_semantic(project=project, type_="decision")
    matched: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []
    for d in ep.get("decisions", []):
        dtext = d.get("text","").lower()
        for s in sems:
            stext = s.get("statement","").lower()
            if dtext and stext and (dtext in stext or stext in dtext or len(set(dtext.split()) & set(stext.split())) >= 3):
                matched.append({"semantic_id": s.get("id"), "statement": s.get("statement")})
                if ("no usar" in dtext and "usar" in stext) or ("no usar" in stext and "usar" in dtext):
                    contradictions.append({"semantic_id": s.get("id"), "reason": "Posible contradicción (usar/no usar)"})
    confidence = 0.8
    if contradictions:
        confidence = max(0.3, confidence - 0.3)
    if len(ep.get("evidence", [])) == 0:
        confidence = max(0.2, confidence - 0.2)
    res = {
        "trace_id": trace_id,
        "episode_id": episode_id,
        "ok": len(contradictions) == 0,
        "confidence": round(confidence, 2),
        "matched_semantic_ids": [m["semantic_id"] for m in matched],
        "contradictions": contradictions,
        "actions": ["Revisar evidencia y alinear decisión"] if contradictions else ["Aprobado para consolidación"],
        "ts": now_iso(),
    }
    append_jsonl(TRACES_DIR / "factcheck.jsonl", res)
    return res
