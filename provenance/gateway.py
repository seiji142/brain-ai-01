"""Gateway de acciones - punto único de control para efectos."""

from __future__ import annotations

from typing import Callable

from . import audit
from .errors import ActionDenied, HandleError, PolicyViolation
from .policies import (
    ACTION_POLICIES, CONFIRMATION_REQUIRED, ENFORCEMENT, EnumPolicy,
    HandlePolicy, LiteralPolicy, PathPolicy, validate_enum, validate_literal,
    validate_path,
)


class ActionGateway:
    """Punto único de control para acciones con efectos."""

    def __init__(self, store, executors: dict[str, Callable]):
        self.store = store
        self.executors = executors

    def execute(self, action: str, params: dict, session_id: str):
        """Valida y ejecuta una acción contra las políticas declaradas."""
        mode = ENFORCEMENT.get(action, "enforce")  # deny by default para acciones nuevas
        policy = ACTION_POLICIES.get(action)

        if policy is None:
            audit.log("action_denied", action=action, session=session_id,
                      reason="no_policy", mode=mode)
            raise ActionDenied(
                f"La acción '{action}' no tiene política declarada. "
                f"Debe registrarse en ACTION_POLICIES antes de ejecutarse."
            )

        resolved: dict = {}
        handle_resolved: set[str] = set()  # campos que venían de handles
        violations: list[str] = []

        extra = set(params) - set(policy) - {"_session_id"}
        if extra:
            violations.append(f"campos no declarados: {sorted(extra)}")

        for field_name, field_policy in policy.items():
            if field_name not in params:
                continue
            supplied = params[field_name]
            try:
                resolved[field_name] = self._validate_field(
                    action, field_name, supplied, field_policy, session_id
                )
                if isinstance(field_policy, HandlePolicy):
                    handle_resolved.add(field_name)
            except (PolicyViolation, HandleError) as e:
                violations.append(f"{field_name}: {e}")
                resolved[field_name] = self._raw(supplied)

        leaks = self._detect_leaks(resolved, session_id, handle_resolved)
        violations.extend(leaks)

        if violations:
            audit.log("policy_violation", action=action, session=session_id,
                      mode=mode, violations=violations)

        if violations and mode == "enforce":
            raise ActionDenied(
                "Acción bloqueada por falta de procedencia.\n- " + "\n- ".join(violations)
                + "\n\nUsa resolver_referencia() para obtener un handle verificado."
            )

        if action in CONFIRMATION_REQUIRED:
            audit.log("confirmation_required", action=action, session=session_id,
                      params=resolved)
            return {
                "status": "needs_confirmation",
                "action": action,
                "params": resolved,
                "message": f"La acción '{action}' requiere confirmación explícita del usuario.",
            }

        if mode == "shadow":
            audit.log("action_shadow", action=action, session=session_id)
            return {"status": "shadow", "would_execute": action}

        audit.log("action_allowed", action=action, session=session_id,
                  mode=mode, had_violations=bool(violations))
        return self.executors[action](**resolved)

    def _validate_field(self, action: str, name: str, supplied, policy, session_id: str):
        """Valida un campo individual contra su política."""
        if isinstance(policy, HandlePolicy):
            handle = supplied.get("handle") if isinstance(supplied, dict) else None
            if not handle:
                raise PolicyViolation(
                    "requiere un handle verificado, se recibió un literal"
                )
            record = self.store.validate(
                handle=handle,
                session_id=session_id,
                expected_kind=policy.expected_kind.value,
                allowed_sources=policy.allowed_sources,
            )
            return record.value

        if isinstance(policy, EnumPolicy):
            return validate_enum(name, self._raw(supplied), policy)
        if isinstance(policy, LiteralPolicy):
            return validate_literal(name, self._raw(supplied), policy)
        if isinstance(policy, PathPolicy):
            return validate_path(name, self._raw(supplied), policy)

        raise PolicyViolation(f"{name}: tipo de política desconocido")

    @staticmethod
    def _raw(supplied):
        """Extrae el valor raw de un dict con handle o devuelve el valor directo."""
        if isinstance(supplied, dict) and "value" in supplied:
            return supplied["value"]
        return supplied

    def _detect_leaks(self, resolved: dict, session_id: str, handle_resolved: set[str] = None) -> list[str]:
        """Si un literal coincide con un secreto conocido, el modelo lo copió.
        Solo verifica campos que NO fueron resueltos vía handle."""
        if handle_resolved is None:
            handle_resolved = set()
        known = self.store.known_fingerprints(session_id)
        out = []
        for name, value in resolved.items():
            if name in handle_resolved:
                continue  # valor vía handle, no es un leak
            if isinstance(value, str) and len(value) >= 12:
                if audit.fingerprint(value) in known:
                    out.append(f"{name}: valor secreto copiado como literal")
                    audit.log("leak_detected", field=name, session=session_id)
        return out
