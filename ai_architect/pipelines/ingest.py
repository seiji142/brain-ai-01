from typing import Dict, Any
from ..core.utils import now_iso, new_id
from ..core.redact import redact_episode
from ..core.memory import save_episode
from ..core.vectorstore import index_episode
from ..core.utils import append_jsonl
from ..core.config import TRACES_DIR

REQUIRED = ["project", "source_type", "author", "title", "summary", "timestamp"]

def validate_episode(ep: Dict[str, Any]) -> tuple[bool, str]:
    for r in REQUIRED:
        if r not in ep or ep[r] in (None, ""):
            return False, f"Missing required field: {r}"
    try:
        from ..core.utils import ISO
        import datetime as dt
        dt.datetime.strptime(ep["timestamp"], ISO)
    except Exception:
        return False, "timestamp must be ISO8601 UTC (YYYY-MM-DDT%H:%M:%SZ)"
    return True, ""

def build_embedding_text(ep: Dict[str, Any]) -> str:
    parts = [ep.get("title",""), ep.get("summary","")]
    for d in ep.get("decisions", []):
        parts.append(d.get("text",""))
    for a in ep.get("actions", []):
        parts.append(a.get("text",""))
    for r in ep.get("risks", []):
        parts.append(r.get("text",""))
    return " \n".join([p for p in parts if p])

def ingest_episode(ep: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = new_id("tr_")
    ok, msg = validate_episode(ep)
    if not ok:
        append_jsonl(TRACES_DIR / "failures.jsonl", {"trace_id": trace_id, "op": "ingest", "error": msg, "ep": ep})
        return {"ok": False, "error": msg, "trace_id": trace_id}
    if "id" not in ep:
        ep["id"] = new_id("ep_")
    if "created_at" not in ep:
        ep["created_at"] = now_iso()
    ep = redact_episode(ep)
    ep["embedding_text"] = build_embedding_text(ep)
    save_episode(ep)
    try:
        index_episode(ep)
    except Exception as e:
        append_jsonl(TRACES_DIR / "failures.jsonl", {"trace_id": trace_id, "op": "ingest_index", "error": str(e), "episode_id": ep["id"]})
    append_jsonl(TRACES_DIR / "ingest.jsonl", {"trace_id": trace_id, "ts": now_iso(), "operation": "ingest", "episode_id": ep["id"], "project": ep.get("project")})
    return {"ok": True, "episode_id": ep["id"], "trace_id": trace_id}
