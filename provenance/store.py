"""Store de handles server-side - SQLite con TTL y max_uses."""

from __future__ import annotations

import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from . import audit
from .errors import HandleError

SCHEMA = """
CREATE TABLE IF NOT EXISTS handles (
    handle TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    value_fp TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    max_uses INTEGER NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_session ON handles(session_id);
CREATE INDEX IF NOT EXISTS idx_fp ON handles(value_fp);
"""


@dataclass
class HandleRecord:
    """Representa un handle validado y consumido."""
    handle: str
    key: str
    value: str
    kind: str
    source: str
    source_record_id: str
    session_id: str


class ResolvedStore:
    """Almacén de handles opacos para valores resueltos."""

    def __init__(self, db_path: str = "logs/handles.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def issue(
        self,
        *,
        key: str,
        value: str,
        kind: str,
        source: str,
        source_record_id: str,
        session_id: str,
        ttl_seconds: int = 600,
        max_uses: int = 3,
    ) -> str:
        """Emite un nuevo handle para un valor resuelto."""
        handle = "vh_" + secrets.token_urlsafe(18)
        now = time.time()
        self.conn.execute(
            "INSERT INTO handles VALUES (?,?,?,?,?,?,?,?,?,?,?,0,0)",
            (handle, key, value, audit.fingerprint(value), kind, source,
             source_record_id, session_id, now, now + ttl_seconds, max_uses),
        )
        self.conn.commit()
        audit.log("handle_issued", handle=handle, key=key, kind=kind,
                  source=source, session=session_id, ttl=ttl_seconds)
        return handle

    def validate(
        self,
        *,
        handle: str,
        session_id: str,
        expected_kind: str | None = None,
        allowed_sources: set[str] | None = None,
        consume: bool = True,
    ) -> HandleRecord:
        """Valida un handle y opcionalmente consume un uso."""
        row = self.conn.execute(
            "SELECT handle,key,value,kind,source,source_record_id,session_id,"
            "expires_at,max_uses,used,revoked FROM handles WHERE handle=?",
            (handle,),
        ).fetchone()

        if row is None:
            self._fail(handle, session_id, "handle_not_found")
        (h, key, value, kind, source, srid, sess, expires_at, max_uses, used, revoked) = row

        if revoked:
            self._fail(handle, session_id, "handle_revoked")
        if time.time() > expires_at:
            self._fail(handle, session_id, "handle_expired")
        if sess != session_id:
            self._fail(handle, session_id, "session_mismatch")
        if used >= max_uses:
            self._fail(handle, session_id, "handle_exhausted")
        if expected_kind and kind != expected_kind:
            self._fail(handle, session_id, f"kind_mismatch:{kind}!={expected_kind}")
        if allowed_sources and source not in allowed_sources:
            self._fail(handle, session_id, f"source_not_allowed:{source}")

        if consume:
            self.conn.execute("UPDATE handles SET used=used+1 WHERE handle=?", (handle,))
            self.conn.commit()

        audit.log("handle_validated", handle=handle, key=key, source=source,
                  session=session_id)
        return HandleRecord(h, key, value, kind, source, srid, sess)

    def describe(self, handle: str, session_id: str) -> dict | None:
        """Devuelve metadatos de un handle sin exponer el valor."""
        row = self.conn.execute(
            "SELECT key,kind,source,source_record_id,expires_at FROM handles "
            "WHERE handle=? AND session_id=?", (handle, session_id),
        ).fetchone()
        if not row:
            return None
        return {"handle": handle, "key": row[0], "kind": row[1],
                "source": row[2], "source_record_id": row[3], "expires_at": row[4]}

    def known_fingerprints(self, session_id: str) -> set[str]:
        """Devuelve las huellas de valores conocidos para una sesión."""
        rows = self.conn.execute(
            "SELECT value_fp FROM handles WHERE session_id=?", (session_id,)
        ).fetchall()
        return {r[0] for r in rows}

    def _fail(self, handle: str, session_id: str, reason: str) -> None:
        """Registra rechazo y lanza excepción."""
        audit.log("handle_rejected", handle=handle, session=session_id, reason=reason)
        raise HandleError(reason)
