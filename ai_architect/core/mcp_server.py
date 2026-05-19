from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..pipelines.ingest import ingest_episode
from ..core.retrieval import retrieve
from ..core.utils import now_iso, new_id
from ..pipelines.consolidate import consolidate_project
from ..pipelines.evaluate import evaluate_query

app = FastAPI(title="AI Knowledge MCP", version="0.1.0")

class IngestReq(BaseModel):
    episode: dict

class RetrieveReq(BaseModel):
    query: str
    top_k: int = 5
    project: Optional[str] = None
    tags: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    collection: str = "semantic"

class ConsolidateReq(BaseModel):
    project: Optional[str] = None

class EvaluateReq(BaseModel):
    query: str
    project: Optional[str] = None
    top_k: int = 5
    collection: str = "semantic"

class CheckContextoReq(BaseModel):
    nombre_base: str
    proyecto: Optional[str] = None

class GuardarContextoReq(BaseModel):
    nombre_base: str
    contexto: str
    proyecto: str = "brain-ai-01"
    source_type: str = "chat"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
def ingest(req: IngestReq):
    res = ingest_episode(req.episode)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res)
    return res

@app.post("/retrieve")
def retrieve_ep(req: RetrieveReq):
    res = retrieve(req.query, req.top_k, req.project, req.tags, req.date_from, req.date_to, req.collection)
    return res

@app.post("/consolidate")
def consolidate(req: ConsolidateReq):
    res = consolidate_project(req.project)
    return res

@app.post("/evaluate")
def evaluate(req: EvaluateReq):
    res = evaluate_query(req.query, req.project, req.top_k, req.collection)
    return res

@app.post("/check_contexto")
def check_contexto(req: CheckContextoReq):
    """Verifica si ya hay contexto guardado para una entidad (persona, API key, etc).
       El contexto es global (no depende del proyecto).
       Lee episodios con tag 'contexto' directamente del archivo."""
    from ..core.config import EPISODIC_DIR
    from ..core.utils import read_json
    nombre = req.nombre_base.lower()
    for f in EPISODIC_DIR.glob("*.json"):
        try:
            ep = read_json(f)
        except Exception:
            continue
        if "contexto" not in ep.get("tags", []):
            continue
        summary = ep.get("summary", "").lower()
        if nombre in summary:
            return {"ok": True, "tiene_contexto": True, "contexto": ep.get("summary", "")}
    return {"ok": True, "tiene_contexto": False, "contexto": None}

@app.post("/guardar_contexto")
def guardar_contexto(req: GuardarContextoReq):
    """Guarda contexto sobre una entidad en memoria."""
    ep = {
        "project": req.proyecto,
        "source_type": req.source_type,
        "author": "sistema",
        "title": f"Contexto: {req.nombre_base}",
        "summary": f"{req.nombre_base} es {req.contexto}",
        "timestamp": now_iso(),
        "tags": ["contexto", req.nombre_base],
        "decisions": [{"text": f"{req.nombre_base} es {req.contexto}"}],
    }
    res = ingest_episode(ep)
    return {"ok": res.get("ok"), "episode_id": res.get("episode_id")}
