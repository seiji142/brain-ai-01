import re, json, uuid, hashlib, datetime as dt
from pathlib import Path
from typing import Any, Dict

ISO = "%Y-%m-%dT%H:%M:%SZ"

PII_PATTERNS = [
    # re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # re.compile(r"\b(?:\+?\d[\d\s\-]{7,}\d)\b"),
    # re.compile(r"\b\d{6,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9\-\._~+/=]{20,}\b", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]

def now_iso() -> str:
    return dt.datetime.utcnow().strftime(ISO)

def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex}"

def redact_text(text: str) -> str:
    red = text
    for pat in PII_PATTERNS:
        red = pat.sub("[REDACTED]", red)
    return red

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def write_json(p: Path, data: Dict[str, Any]) -> None:
    ensure_dir(p.parent)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

def read_json(p: Path) -> Dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def append_jsonl(p: Path, data: Dict[str, Any]) -> None:
    ensure_dir(p.parent)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def date_range_filter_ok(ts_iso: str, date_from: str | None, date_to: str | None) -> bool:
    try:
        t = dt.datetime.strptime(ts_iso, ISO)
        if date_from:
            df = dt.datetime.strptime(date_from, ISO)
            if t < df:
                return False
        if date_to:
            dtto = dt.datetime.strptime(date_to, ISO)
            if t > dtto:
                return False
        return True
    except Exception:
        return True
