from typing import Dict, Any
from ..core.memory import load_episode, save_summary
from ..core.utils import now_iso

def summarize_episode(episode_id: str) -> Dict[str, Any]:
    ep = load_episode(episode_id)
    summary = {
        "episode_id": episode_id,
        "project": ep.get("project"),
        "title": ep.get("title"),
        "summary_text": ep.get("summary", ""),
        "decisions": ep.get("decisions", []),
        "actions": ep.get("actions", []),
        "risks": ep.get("risks", []),
        "created_at": now_iso(),
    }
    save_summary(summary)
    return summary
