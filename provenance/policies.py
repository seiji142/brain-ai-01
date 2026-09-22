"""Políticas de validación por acción y campo."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .types import ValueKind


@dataclass
class HandlePolicy:
    """Campo que requiere un handle verificado (no acepta literales)."""
    expected_kind: ValueKind
    allowed_sources: set[str]
    mode: str = "verified_handle"


@dataclass
class LiteralPolicy:
    """Validación de tipo, longitud y patrón para literales."""
    type: type
    min: float | None = None
    max: float | None = None
    max_len: int = 200
    pattern: str | None = None
    mode: str = "literal"


@dataclass
class EnumPolicy:
    """Campo con conjunto finito de valores permitidos."""
    values: set[str]
    mode: str = "enum"


@dataclass
class PathPolicy:
    """Ruta que debe estar dentro del workspace y opcionalmente existir."""
    root: str
    must_exist: bool = True
    mode: str = "path"


# Modo por acción: "off" | "shadow" | "warn" | "enforce"
ENFORCEMENT: dict[str, str] = {
    "http_request": "warn",
    "run_shell": "warn",
    "write_file": "warn",
    "deploy": "warn",
}

# Acciones que requieren confirmación explícita antes de ejecutar
CONFIRMATION_REQUIRED: set[str] = {
    "write_file",
}

ACTION_POLICIES: dict[str, dict] = {
    "http_request": {
        "url": LiteralPolicy(str, max_len=2000, pattern=r"^https?://"),
        "method": EnumPolicy({"GET", "POST", "PUT", "DELETE", "PATCH"}),
        "api_key": HandlePolicy(ValueKind.SECRET, {"env", "user_message"}),
        "timeout": LiteralPolicy(int, min=1, max=120),
        "body": LiteralPolicy(str, max_len=20000),
    },
    "write_file": {
        "path": PathPolicy(root="."),
        "content": LiteralPolicy(str, max_len=200000),
    },
    "run_shell": {
        "command": LiteralPolicy(str, max_len=1000),
        "cwd": LiteralPolicy(str, max_len=500),
        "timeout": LiteralPolicy(int, min=1, max=120),
    },
    "deploy": {
        "environment": EnumPolicy({"staging", "production"}),
        "api_key": HandlePolicy(ValueKind.SECRET, {"env"}),
        "region": EnumPolicy({"us-east-1", "eu-west-1"}),
    },
}


def validate_literal(name: str, value, policy: LiteralPolicy):
    """Valida un valor literal contra una LiteralPolicy."""
    from .errors import PolicyViolation

    if not isinstance(value, policy.type):
        raise PolicyViolation(f"{name}: se esperaba {policy.type.__name__}")

    if isinstance(value, str):
        if len(value) > policy.max_len:
            raise PolicyViolation(f"{name}: excede max_len ({len(value)} > {policy.max_len})")
        if policy.pattern and not re.fullmatch(policy.pattern, value):
            raise PolicyViolation(f"{name}: no coincide con el patrón permitido")

    if isinstance(value, (int, float)):
        if policy.min is not None and value < policy.min:
            raise PolicyViolation(f"{name}: menor que {policy.min}")
        if policy.max is not None and value > policy.max:
            raise PolicyViolation(f"{name}: mayor que {policy.max}")

    return value


def validate_enum(name: str, value, policy: EnumPolicy):
    """Valida un valor contra un conjunto permitido."""
    from .errors import PolicyViolation

    if value not in policy.values:
        raise PolicyViolation(
            f"{name}: valor no permitido. Permitidos: {sorted(policy.values)}"
        )
    return value


def validate_path(name: str, value, policy: PathPolicy):
    """Valida que una ruta esté dentro del workspace."""
    from .errors import PolicyViolation

    root = Path(policy.root).resolve()
    target = (root / str(value)).resolve()

    if not str(target).startswith(str(root)):
        raise PolicyViolation(f"{name}: ruta fuera del workspace ({target})")
    if policy.must_exist and not target.exists():
        raise PolicyViolation(f"{name}: la ruta no existe ({target})")

    return str(target)
