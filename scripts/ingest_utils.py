"""
Funciones compartidas para scripts de ingesta (PDF, imagen, texto, web, etc.)
"""
import httpx, json, sys, shutil, re
from pathlib import Path
from datetime import datetime

MCP_URL = "http://localhost:8000"


def mcp_ingest(episode: dict, timeout: int = 60) -> dict | None:
    r = httpx.post(f"{MCP_URL}/ingest", json={"episode": episode}, timeout=timeout)
    if r.status_code != 200:
        print(f"  [ERROR] MCP ({r.status_code}): {r.text[:200]}", file=sys.stderr)
        return None
    return r.json()


def save_media(src: Path, project: str, dest_dir: Path) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"{project}_{ts}_{src.name}"
    shutil.copy2(src, dest)
    return dest


def extract_decisions(text: str, title: str = "", max_decisions: int = 5) -> list[dict]:
    decisions = []
    seen = set()

    def _add(t: str):
        t = t.strip()[:300]
        if t and t.lower() not in seen:
            seen.add(t.lower())
            decisions.append({"text": t})

    if title:
        _add(title)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        if len(decisions) >= max_decisions:
            break
        if len(line) < 5:
            continue
        if re.match(r"^(Pagina|pag|Sistema|NOTAS|[-_ ]+)$", line):
            continue
        if re.search(r"\d+%", line):
            _add(line)
        elif re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ][a-záéíóúñ]+.*:", line):
            _add(line)

    if not decisions:
        for line in lines:
            if len(line) >= 20:
                _add(line)
                break

    return decisions


def build_episode(
    project: str,
    source_type: str,
    author: str,
    title: str,
    summary: str,
    decisions: list[dict] | None = None,
    evidence: list[dict] | None = None,
    tags: list[str] | None = None,
    actions: list[dict] | None = None,
    risks: list[dict] | None = None,
) -> dict:
    return {
        "project": project,
        "source_type": source_type,
        "author": author,
        "title": title,
        "summary": summary[:5000],
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions": decisions or [],
        "actions": actions or [],
        "risks": risks or [],
        "evidence": evidence or [],
        "tags": tags or [],
    }
