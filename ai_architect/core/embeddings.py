import hashlib
import numpy as np
from typing import List
from .config import settings

def _hash_embed(text: str, dim: int = 1536) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    out = []
    seed = h
    while len(out) < dim:
        seed = hashlib.sha256(seed).digest()
        for b in seed:
            out.append((b / 255.0) * 2.0 - 1.0)
            if len(out) >= dim:
                break
    return out[:dim]

def embed_texts(texts: List[str]) -> List[List[float]]:
    if settings.embedding_provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            resp = client.embeddings.create(model=settings.openai_embedding_model, input=texts)
            return [d.embedding for d in resp.data]
        except Exception:
            return [_hash_embed(t) for t in texts]
    else:
        return [_hash_embed(t) for t in texts]

def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]
