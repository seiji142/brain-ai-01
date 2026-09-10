"""Audit logging - escritura thread-safe a JSONL."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
AUDIT_PATH = Path(os.getenv("BRAIN_AUDIT_PATH", "logs/audit.jsonl"))
AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

SENSITIVE_HINTS = ("key", "token", "secret", "password", "passwd", "credential", "auth")


def fingerprint(value: str) -> str:
    """Genera una huellaSHA256 truncada de un valor. Nunca almacena el original."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def redact(obj: Any, key_name: str = "") -> Any:
    """Nunca escribas valores sensibles al log. Solo huellas."""
    if isinstance(obj, dict):
        return {k: redact(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v, key_name) for v in obj]
    if isinstance(obj, str):
        lowered = key_name.lower()
        if any(h in lowered for h in SENSITIVE_HINTS) or len(obj) > 200:
            return {"__redacted__": True, "fp": fingerprint(obj), "len": len(obj)}
        return obj
    return obj


def log(event: str, **fields: Any) -> None:
    """Escribe un evento de auditoría de forma thread-safe."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    line = json.dumps(record, ensure_ascii=False, default=str)
    with _LOCK:
        with AUDIT_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
