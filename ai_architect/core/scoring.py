import datetime as dt, math, re
from typing import Dict, Any, List
from .utils import ISO

# BM25 constants
BM25_K1 = 1.5
BM25_B = 0.75

def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-záéíóúñü0-9]+", text.lower())


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


def compute_bm25_scores(query: str, docs: List[str]) -> List[float]:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return [0.0] * len(docs)

    n = len(docs)
    doc_tokens = [_tokenize(d) for d in docs]
    doc_lens = [len(t) for t in doc_tokens]
    avg_dl = sum(doc_lens) / max(n, 1)

    # Compute IDF for each query token
    idf_map = {}
    for qt in set(q_tokens):
        df = sum(1 for dt in doc_tokens if qt in dt)
        if df == 0:
            idf_map[qt] = 0.0
        else:
            idf_map[qt] = math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    scores = []
    for dtoks in doc_tokens:
        dl = len(dtoks)
        score = 0.0
        for qt in set(q_tokens):
            tf = dtoks.count(qt)
            if tf == 0:
                continue
            idf = idf_map.get(qt, 0.0)
            numer = tf * (BM25_K1 + 1)
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * (dl / max(avg_dl, 1)))
            score += idf * numer / max(denom, 0.001)
        scores.append(score)

    max_s = max(scores) if scores else 1.0
    if max_s > 0:
        scores = [s / max_s for s in scores]
    return scores


def hybrid_score(item: Dict[str, Any], dist: float, bm25: float = 0.0) -> float:
    s_vec = cosine_from_distance(dist)
    ts = item.get("timestamp") or item.get("updated_at") or item.get("created_at") or ""
    s_rec = _recency_score(ts)
    s_ev = _evidence_score(item)
    s_cf = _confidence_score(item)
    # Hybrid: BM25 domina (keyword), hash vector es ruido, se minimiza
    score = 0.70 * bm25 + 0.08 * s_vec + 0.08 * s_rec + 0.08 * s_ev + 0.06 * s_cf
    if score > 1.0: score = 1.0
    if score < 0.0: score = 0.0
    return score
