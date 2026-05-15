import datetime as dt
from typing import Dict, Any
from .utils import ISO

def _recency_score(ts_iso: str) -> float:
    try:
        t = dt.datetime.strptime(ts_iso, ISO)
        now = dt.datetime.utcnow()
        delta = now - t
        days = delta.days
        if days < 7: return 1.0
        if days < 30: return 0.8
        if days < 90: return 0.6
        if days < 365: return 0.4
        return 0.2
    except Exception:
        return 0.5

def _evidence_score(item: Dict[str, Any]) -> float:
    ev = item.get("evidence", [])
    if not ev:
        ev = item.get("evidence_source_ids", [])
    n = len(ev)
    s = 0.5 + 0.5 * (n / 5.0)
    if s > 1.0: s = 1.0
    if s < 0.0: s = 0.0
    return s

def _confidence_score(item: Dict[str, Any]) -> float:
    c = item.get("confidence", None)
    if c is None:
        return 0.7
    try:
        return float(c)
    except Exception:
        return 0.7

def cosine_from_distance(dist: float) -> float:
    sim = 1.0 - (dist / 2.0)
    if sim > 1.0: sim = 1.0
    if sim < 0.0: sim = 0.0
    return sim

def hybrid_score(item: Dict[str, Any], dist: float) -> float:
    s_vec = cosine_from_distance(dist)
    ts = item.get("timestamp") or item.get("updated_at") or item.get("created_at") or ""
    s_rec = _recency_score(ts)
    s_ev = _evidence_score(item)
    s_cf = _confidence_score(item)
    score = 0.45*s_vec + 0.20*s_rec + 0.20*s_ev + 0.15*s_cf
    if score > 1.0: score = 1.0
    if score < 0.0: score = 0.0
    return score
