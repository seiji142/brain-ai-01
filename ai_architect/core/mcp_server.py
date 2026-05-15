from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..pipelines.ingest import ingest_episode
from ..core.retrieval import retrieve
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
