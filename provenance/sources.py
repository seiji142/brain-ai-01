"""Fuentes de resolución de referencias."""

from __future__ import annotations

import difflib
import os
import re
from pathlib import Path
from typing import Protocol

from .types import Candidate, MatchType, ValueKind

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", ".")).resolve()


def _preview(value: str, kind: ValueKind) -> str:
    """Genera un preview no sensible del valor."""
    if kind in (ValueKind.SECRET,):
        return f"len={len(value)} ···{value[-4:]}" if len(value) > 8 else "len<=8"
    return value[:60]


class Source(Protocol):
    """Protocolo que toda fuente de resolución debe implementar."""
    name: str

    def lookup(self, expression: str, expected_kind: ValueKind | None) -> list[Candidate]: ...

    def enumerate_keys(self, expected_kind: ValueKind | None) -> list[str]: ...


class EnvSource:
    """Fuente de variables de entorno del sistema."""
    name = "env"

    # Alias explícitos y auditables. NO se generan automáticamente.
    ALIASES = {
        "api key de groq": "GROQ_API_KEY",
        "clave de groq": "GROQ_API_KEY",
    }

    def _kind_of(self, key: str) -> ValueKind:
        lowered = key.lower()
        if any(h in lowered for h in ("key", "token", "secret", "password")):
            return ValueKind.SECRET
        if lowered.endswith(("_url", "_endpoint", "_host")):
            return ValueKind.ENDPOINT
        return ValueKind.ENV_VAR

    def lookup(self, expression: str, expected_kind: ValueKind | None) -> list[Candidate]:
        expr = expression.strip()
        out: list[Candidate] = []

        if expr in os.environ:
            out.append(self._mk(expr, MatchType.EXACT))
        elif expr.lower() in self.ALIASES and self.ALIASES[expr.lower()] in os.environ:
            out.append(self._mk(self.ALIASES[expr.lower()], MatchType.ALIAS))
        else:
            near = difflib.get_close_matches(expr.upper(), list(os.environ), n=3, cutoff=0.82)
            out.extend(self._mk(k, MatchType.FUZZY) for k in near)

        if expected_kind:
            out = [c for c in out if c.kind == expected_kind]
        return out

    def _mk(self, key: str, match: MatchType) -> Candidate:
        value = os.environ[key]
        kind = self._kind_of(key)
        return Candidate(
            key=key, kind=kind, source=self.name,
            source_record_id=f"env:{key}", match_type=match,
            preview=_preview(value, kind), value=value,
        )

    def enumerate_keys(self, expected_kind: ValueKind | None) -> list[str]:
        keys = list(os.environ)
        if expected_kind:
            keys = [k for k in keys if self._kind_of(k) == expected_kind]
        return sorted(keys)


class MemoriaSource:
    """Adaptador sobre clients/memoria.py. Normaliza lo que devuelva tu cliente."""
    name = "memoria"

    def __init__(self, memoria_client):
        self.client = memoria_client

    def lookup(self, expression: str, expected_kind: ValueKind | None) -> list[Candidate]:
        raw = self.client.buscar(expression) or []
        if isinstance(raw, dict):
            raw = [raw]

        out = []
        for r in raw:
            key = r.get("key") or r.get("nombre") or expression
            value = r.get("value") or r.get("contenido") or ""
            rid = r.get("id") or r.get("record_id")
            if not rid or not value:
                continue  # sin id verificable no es procedencia
            kind = ValueKind(r.get("kind", ValueKind.CONFIG.value))
            if expected_kind and kind != expected_kind:
                continue
            out.append(Candidate(
                key=key, kind=kind, source=self.name,
                source_record_id=f"memoria:{rid}",
                match_type=MatchType.EXACT if key == expression else MatchType.FUZZY,
                preview=_preview(str(value), kind), value=str(value),
            ))
        return out

    def enumerate_keys(self, expected_kind: ValueKind | None) -> list[str]:
        return []


class UserMessageSource:
    """
    Valores declarados por el usuario, extraídos del transcript CRUDO por el bridge.
    Nunca se pueblan por una tool que el LLM pueda llamar.
    """
    name = "user_message"

    def __init__(self):
        self._store: dict[str, Candidate] = {}

    def ingest(self, message_id: str, text: str) -> int:
        """Llamar desde el bridge con el mensaje literal del usuario."""
        count = 0
        for m in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\s*=\s*([^\s\"']\+)", text):
            key, value = m.group(1), m.group(2)
            kind = ValueKind.SECRET if any(
                h in key.lower() for h in ("key", "token", "secret", "password")
            ) else ValueKind.CONFIG
            self._store[key] = Candidate(
                key=key, kind=kind, source=self.name,
                source_record_id=f"user_message:{message_id}:{m.start()}-{m.end()}",
                match_type=MatchType.EXACT,
                preview=_preview(value, kind), value=value,
            )
            count += 1
        return count

    def lookup(self, expression: str, expected_kind: ValueKind | None) -> list[Candidate]:
        c = self._store.get(expression.strip())
        if not c:
            return []
        if expected_kind and c.kind != expected_kind:
            return []
        return [c]

    def enumerate_keys(self, expected_kind: ValueKind | None) -> list[str]:
        return sorted(self._store)


class WorkspaceSource:
    """Fuente de archivos en el workspace."""
    name = "workspace"

    def lookup(self, expression: str, expected_kind: ValueKind | None) -> list[Candidate]:
        if expected_kind not in (None, ValueKind.PATH):
            return []
        candidate = (WORKSPACE_ROOT / expression).resolve()
        if not str(candidate).startswith(str(WORKSPACE_ROOT)):
            return []
        if not candidate.exists():
            return []
        return [Candidate(
            key=expression, kind=ValueKind.PATH, source=self.name,
            source_record_id=f"workspace:{candidate}",
            match_type=MatchType.EXACT, preview=str(candidate),
            value=str(candidate),
        )]

    def enumerate_keys(self, expected_kind: ValueKind | None) -> list[str]:
        return []
