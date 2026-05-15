import chromadb
from typing import List, Dict, Any
from .config import CHROMA_DIR
from .embeddings import embed_texts, embed_text

COL_EPISODIC = "episodic"
COL_SEMANTIC = "semantic"

_client = None

def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client

def _collection(name: str):
    client = get_client()
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

def index_episode(episode: Dict[str, Any]) -> None:
    col = _collection(COL_EPISODIC)
    emb_text = episode.get("embedding_text") or episode.get("summary") or episode.get("title") or ""
    vec = embed_text(emb_text)
    meta = {
        "id": episode.get("id"),
        "project": episode.get("project", ""),
        "timestamp": episode.get("timestamp", ""),
        "source_type": episode.get("source_type", ""),
        "tags": ",".join(episode.get("tags", [])),
    }
    col.upsert(ids=[episode["id"]], embeddings=[vec], metadatas=[meta], documents=[emb_text])

def index_semantic(item: Dict[str, Any]) -> None:
    col = _collection(COL_SEMANTIC)
    emb_text = item.get("embedding_text") or item.get("statement") or ""
    vec = embed_text(emb_text)
    meta = {
        "id": item.get("id"),
        "project": item.get("project", ""),
        "type": item.get("type", ""),
        "timestamp": item.get("updated_at") or item.get("created_at", ""),
        "tags": ",".join(item.get("tags", [])),
        "confidence": float(item.get("confidence", 0.7)),
    }
    col.upsert(ids=[item["id"]], embeddings=[vec], metadatas=[meta], documents=[emb_text])

def query_collection(collection: str, query: str, n_results: int = 5, where: Dict[str, Any] | None = None) -> Dict[str, Any]:
    col = _collection(collection)
    vec = embed_text(query)
    res = col.query(query_embeddings=[vec], n_results=n_results, where=where,
                    include=["metadatas", "documents", "distances"])
    out = {"ids": res.get("ids", [[]])[0], "metadatas": res.get("metadatas", [[]])[0],
           "documents": res.get("documents", [[]])[0], "distances": res.get("distances", [[]])[0]}
    return out
