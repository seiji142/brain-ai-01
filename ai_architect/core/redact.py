from .utils import redact_text

def redact_episode(episode: dict) -> dict:
    ep = dict(episode)
    ep["title"] = redact_text(ep.get("title", ""))
    ep["summary"] = redact_text(ep.get("summary", ""))
    ep["decisions"] = [
        {**d, "text": redact_text(d.get("text", ""))} for d in ep.get("decisions", [])
    ]
    ep["actions"] = [
        {**a, "text": redact_text(a.get("text", ""))} for a in ep.get("actions", [])
    ]
    ep["risks"] = [
        {**r, "text": redact_text(r.get("text", ""))} for r in ep.get("risks", [])
    ]
    ep["evidence"] = [
        {**e, "excerpt": redact_text(e.get("excerpt", ""))} for e in ep.get("evidence", [])
    ]
    ep["embedding_text"] = redact_text(ep.get("embedding_text", ""))
    return ep
