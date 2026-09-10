"""Resolver de referencias - orquesta fuentes y store de handles."""

from __future__ import annotations

from . import audit
from .types import SENSITIVE_KINDS, Candidate, MatchType, ValueKind, public_metadata


class Resolver:
    """Resuelve expresiones contra fuentes autorizadas y emite handles."""

    def __init__(self, sources: list, store=None):
        self.sources = sources
        self.store = store  # se conecta en Fase 2

    def resolve(
        self,
        expression: str,
        expected_kind: str | None,
        session_id: str,
        context: dict | None = None,
        allowed_sources: set[str] | None = None,
    ) -> dict:
        """Resuelve una expresión contra todas las fuentes configuradas."""
        kind = ValueKind(expected_kind) if expected_kind else None
        audit.log("resolve_request", expr=expression, kind=expected_kind,
                  session=session_id, context=context)

        candidates: list[Candidate] = []
        for src in self.sources:
            if allowed_sources and src.name not in allowed_sources:
                continue
            try:
                candidates.extend(src.lookup(expression, kind))
            except Exception as e:
                audit.log("source_error", source=src.name, error=str(e))

        if not candidates:
            result = {
                "status": "unresolved",
                "expression": expression,
                "available_keys": self._hint(kind, allowed_sources),
                "next_step": "Pregunta al usuario o usa una de las claves disponibles. "
                             "No inventes un valor ni un nombre de clave.",
            }
            audit.log("resolve_result", status="unresolved", expr=expression, session=session_id)
            return result

        if len(candidates) > 1:
            result = {
                "status": "ambiguous",
                "expression": expression,
                "candidates": [public_metadata(c) for c in candidates[:10]],
                "next_step": "Muestra estos candidatos al usuario y pídele que elija. "
                             "No selecciones por plausibilidad.",
            }
            audit.log("resolve_result", status="ambiguous", expr=expression,
                      n=len(candidates), session=session_id)
            return result

        c = candidates[0]

        if c.match_type == MatchType.FUZZY and c.kind in SENSITIVE_KINDS:
            audit.log("resolve_result", status="needs_confirmation", expr=expression,
                      key=c.key, session=session_id)
            return {
                "status": "needs_confirmation",
                "expression": expression,
                "candidate": public_metadata(c),
                "next_step": f"Coincidencia aproximada con '{c.key}'. Pide confirmación explícita "
                             f"al usuario antes de usarla.",
            }

        return self._issue(c, session_id, expression)

    def _issue(self, c: Candidate, session_id: str, expression: str) -> dict:
        """Emite un handle para el candidato resuelto."""
        if self.store is None:
            audit.log("resolve_result", status="resolved_no_store", key=c.key)
            return {"status": "resolved", **public_metadata(c)}

        handle = self.store.issue(
            key=c.key, value=c.value, kind=c.kind.value, source=c.source,
            source_record_id=c.source_record_id, session_id=session_id,
        )
        audit.log("resolve_result", status="resolved", key=c.key,
                  source=c.source, handle=handle, session=session_id)

        payload = {"status": "resolved", "handle": handle, **public_metadata(c)}
        if c.kind in SENSITIVE_KINDS:
            payload["value"] = None
            payload["note"] = "Valor no expuesto. Usa el handle en la acción."
        else:
            payload["value"] = c.value

        return payload

    def _hint(self, kind: ValueKind | None, allowed_sources: set[str] | None) -> list[str]:
        """Devuelve claves disponibles como hint para el modelo."""
        keys: list[str] = []
        for src in self.sources:
            if allowed_sources and src.name not in allowed_sources:
                continue
            keys.extend(src.enumerate_keys(kind))
        return sorted(set(keys))[:40]
