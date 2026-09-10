from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..pipelines.ingest import ingest_episode
from ..core.retrieval import retrieve
from ..core.utils import now_iso, new_id
from ..pipelines.consolidate import consolidate_project
from ..pipelines.evaluate import evaluate_query

# Provenance - Fase 0-2
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from provenance.resolver import Resolver
from provenance.store import ResolvedStore
from provenance.sources import EnvSource, MemoriaSource, UserMessageSource, WorkspaceSource
from provenance.errors import ProvenanceError, HandleError

# Provenance - Fase 3: Gateway
from provenance.gateway import ActionGateway

app = FastAPI(title="AI Knowledge MCP", version="0.1.0")

# --- Inicialización de Provenance ---
_store = ResolvedStore()
_user_source = UserMessageSource()

# Importar memoria client para MemoriaSource
try:
    from ...clients import memoria as memoria_client
    _memoria_source = MemoriaSource(memoria_client)
except ImportError:
    _memoria_source = None

_sources = [EnvSource(), _user_source]
if _memoria_source:
    _sources.append(_memoria_source)
_sources.append(WorkspaceSource())

_resolver = Resolver(sources=_sources, store=_store)


# --- Ejecutores reales (Fase 3) ---

def _http_request(url: str, method: str = "GET", api_key: str = None,
                  timeout: int = 30, body: str = None) -> dict:
    """Ejecuta una petición HTTP real."""
    import httpx
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    r = httpx.request(method, url, headers=headers, content=body, timeout=timeout)
    return {"status_code": r.status_code, "body": r.text[:5000]}


def _write_file(path: str, content: str) -> dict:
    """Escribe un archivo en el workspace."""
    Path(path).write_text(content, encoding="utf-8")
    return {"written": path, "bytes": len(content)}


def _deploy(environment: str, api_key: str, region: str) -> dict:
    """Simula un deploy (para testing)."""
    return {
        "status": "deployed",
        "environment": environment,
        "region": region,
        "api_key_len": len(api_key) if api_key else 0,
    }


_gateway = ActionGateway(_store, executors={
    "http_request": _http_request,
    "write_file": _write_file,
    "deploy": _deploy,
})

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


# --- Endpoints de Provenance (Fase 1-2) ---

class ResolveRequest(BaseModel):
    expression: str
    expected_kind: Optional[str] = None
    session_id: str
    context: Optional[dict] = None

class IngestRequest(BaseModel):
    message_id: str
    text: str

class DescribeHandleRequest(BaseModel):
    handle: str
    session_id: str

@app.post("/resolve_reference")
def resolve_reference(req: ResolveRequest):
    """Resuelve una referencia contra fuentes autorizadas."""
    try:
        return _resolver.resolve(
            expression=req.expression,
            expected_kind=req.expected_kind,
            session_id=req.session_id,
            context=req.context,
        )
    except ProvenanceError as e:
        return {"ok": False, "error_code": e.code, "message": str(e)}

@app.post("/internal/ingest_user_message")
def ingest_user_message(req: IngestRequest):
    """Solo lo llama el bridge con el texto crudo. NO se expone como tool MCP."""
    n = _user_source.ingest(req.message_id, req.text)
    return {"ingested": n}

@app.post("/describe_handle")
def describe_handle(req: DescribeHandleRequest):
    """Devuelve metadatos de un handle sin exponer el valor."""
    result = _store.describe(req.handle, req.session_id)
    if not result:
        return {"ok": False, "error": "handle_not_found"}
    return {"ok": True, **result}


# --- Endpoints de Provenance (Fase 3: Gateway) ---

class ExecuteRequest(BaseModel):
    action: str
    params: dict
    session_id: str

@app.post("/actions/execute")
def execute_action(req: ExecuteRequest):
    """Ejecuta una acción a través del gateway de provenance."""
    try:
        result = _gateway.execute(req.action, req.params, req.session_id)
        return {"ok": True, "result": result}
    except ProvenanceError as e:
        return {"ok": False, "error_code": e.code, "message": str(e)}
