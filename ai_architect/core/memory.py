from pathlib import Path
from typing import Dict, Any, List
from .config import EPISODIC_DIR, SEMANTIC_DIR, SUMMARIES_DIR, REFLECTIONS_DIR
from .utils import write_json, read_json, now_iso, new_id, ensure_dir

def save_episode(episode: Dict[str, Any]) -> Path:
    if "id" not in episode:
        episode["id"] = new_id("ep_")
    if "created_at" not in episode:
        episode["created_at"] = now_iso()
    p = EPISODIC_DIR / f"{episode['id']}.json"
    write_json(p, episode)
    return p

def load_episode(episode_id: str) -> Dict[str, Any]:
    p = EPISODIC_DIR / f"{episode_id}.json"
    return read_json(p)

def list_episodes(project: str | None = None) -> List[Dict[str, Any]]:
    items = []
    for p in EPISODIC_DIR.glob("*.json"):
        try:
            d = read_json(p)
            if project and d.get("project") != project:
                continue
            items.append(d)
        except Exception:
            continue
    return items

def save_summary(summary: Dict[str, Any]) -> Path:
    if "id" not in summary:
        summary["id"] = new_id("sum_")
    if "created_at" not in summary:
        summary["created_at"] = now_iso()
    p = SUMMARIES_DIR / f"{summary['id']}.json"
    write_json(p, summary)
    return p

def save_semantic(item: Dict[str, Any]) -> Path:
    if "id" not in item:
        item["id"] = new_id("sem_")
    if "created_at" not in item:
        item["created_at"] = now_iso()
    if "updated_at" not in item:
        item["updated_at"] = now_iso()
    p = SEMANTIC_DIR / f"{item['id']}.json"
    write_json(p, item)
    return p

def load_semantic(semantic_id: str) -> Dict[str, Any]:
    p = SEMANTIC_DIR / f"{semantic_id}.json"
    return read_json(p)

def list_semantic(project: str | None = None, type_: str | None = None) -> List[Dict[str, Any]]:
    items = []
    for p in SEMANTIC_DIR.glob("*.json"):
        try:
            d = read_json(p)
            if project and d.get("project") != project:
                continue
            if type_ and d.get("type") != type_:
                continue
            items.append(d)
        except Exception:
            continue
    return items

def save_reflection(ref: Dict[str, Any]) -> Path:
    if "id" not in ref:
        ref["id"] = new_id("ref_")
    if "created_at" not in ref:
        ref["created_at"] = now_iso()
    p = REFLECTIONS_DIR / f"{ref['id']}.json"
    write_json(p, ref)
    return p
