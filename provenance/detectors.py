"""Detectores de patrones de secretos y campos referenciales."""

from __future__ import annotations

import re
from typing import Any

# Campos que jamás deberían aceptar un literal generado por el modelo.
REFERENTIAL_FIELDS = {
    "api_key", "apikey", "api-key", "token", "access_token", "refresh_token",
    "secret", "client_secret", "password", "passwd", "credential", "credentials",
    "authorization", "auth", "dsn", "connection_string", "database_url",
    "account_id", "tenant_id", "user_id", "project_id", "record_id",
    "endpoint", "base_url", "webhook_url", "host", "bucket",
}

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9_\-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."),  # JWT
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),                     # base64 largo
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"(?i)\b(your|tu|my|mi)[_\- ]?(api[_\- ]?key|token|secret)\b"),
    re.compile(r"(?i)\b(xxx\+|abc123|changeme|placeholder|example|foobar|dummy)\b"),
    re.compile(r"^\<.*\>$"),
]


def scan(tool: str, params: dict[str, Any]) -> list[dict]:
    """Escanea parámetros de una tool en busca de problemas de procedencia."""
    findings: list[dict] = []
    for name, value in _flatten(params):
        lowered = name.lower()

        if lowered in REFERENTIAL_FIELDS:
            findings.append({"type": "referential_field", "field": name, "tool": tool})

        if not isinstance(value, str):
            continue

        for pat in SECRET_PATTERNS:
            if pat.search(value):
                findings.append({"type": "secret_shape", "field": name, "pattern": pat.pattern})
                break

        for pat in PLACEHOLDER_PATTERNS:
            if pat.search(value):
                findings.append({"type": "placeholder_shape", "field": name})
                break

    return findings


def _flatten(obj: Any, prefix: str = ""):
    """Aplana estructuras anidadas en pares (nombre, valor)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj
