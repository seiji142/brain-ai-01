from typing import Dict, Any, List
from ..core.memory import list_episodes, save_reflection
from ..core.utils import now_iso
from collections import Counter

def reflect_project(project: str | None = None, days: int = 30) -> Dict[str, Any]:
    eps = list_episodes(project=project)
    tag_counter = Counter()
    risk_counter = Counter()
    decision_themes: List[str] = []
    for ep in eps:
        for t in ep.get("tags", []):
            tag_counter[t] += 1
        for r in ep.get("risks", []):
            risk_counter[r.get("text","")] += 1
        for d in ep.get("decisions", []):
            txt = d.get("text","")
            if "autentic" in txt.lower() or "auth" in txt.lower():
                decision_themes.append("Autenticación/autorización recurrente")
                break
    patterns = [f"Top tag: {tag} ({cnt})" for tag, cnt in tag_counter.most_common(5)]
    if decision_themes:
        patterns.append("Tema recurrente: " + "; ".join(sorted(set(decision_themes))))
    contradictions: List[str] = []
    ref = {
        "scope": {"project": project, "days": days},
        "patterns": patterns,
        "contradictions": contradictions,
        "hypotheses": ["Revisar decisiones de auth si aparecen >2 veces en 30 días."],
        "created_at": now_iso(),
    }
    save_reflection(ref)
    return ref
