"""Tipos del sistema de provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ValueKind(str, Enum):
    """Tipos de valor que el sistema puede resolver."""
    SECRET = "secret"
    ENV_VAR = "env_var"
    PATH = "path"
    ENDPOINT = "endpoint"
    RECORD_ID = "record_id"
    CONFIG = "config"
    FREE_TEXT = "free_text"


SENSITIVE_KINDS = {ValueKind.SECRET, ValueKind.ENDPOINT, ValueKind.RECORD_ID}


class MatchType(str, Enum):
    """Tipo de coincidencia en la resolución."""
    EXACT = "exact"      # el nombre coincide con una clave existente
    ALIAS = "alias"      # coincide vía alias declarado explícitamente
    FUZZY = "fuzzy"      # coincidencia aproximada: nunca auto-resuelve nada sensible


@dataclass
class Candidate:
    """Un candidato resuelto de una fuente."""
    key: str                     # nombre canónico real, p.ej. "GROQ_API_KEY"
    kind: ValueKind
    source: str                  # "env" | "memoria" | "user_message" | "workspace"
    source_record_id: str        # prueba de que existe en algún lado
    match_type: MatchType
    preview: str | None = None   # metadato NO sensible
    value: str = field(repr=False, default="")


def public_metadata(c: Candidate) -> dict:
    """Lo único que puede ver el LLM sobre un candidato."""
    return {
        "key": c.key,
        "kind": c.kind.value,
        "source": c.source,
        "source_record_id": c.source_record_id,
        "match": c.match_type.value,
        "preview": c.preview,
    }
