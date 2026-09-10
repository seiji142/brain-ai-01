"""Excepciones del sistema de provenance."""


class ProvenanceError(Exception):
    """Excepción base para errores de provenance."""
    code = "provenance_error"


class UnresolvedReferenceError(ProvenanceError):
    """Una referencia no pudo ser resuelta contra ninguna fuente."""
    code = "unresolved_reference"


class MissingProvenanceError(ProvenanceError):
    """Falta información de procedencia requerida."""
    code = "missing_provenance"


class HandleError(ProvenanceError):
    """Error relacionado con un handle (no encontrado, expirado, agotado, etc.)."""
    code = "handle_error"


class PolicyViolation(ProvenanceError):
    """Una acción violó una política declarada."""
    code = "policy_violation"


class ActionDenied(ProvenanceError):
    """Una acción fue denegada por el gateway."""
    code = "action_denied"
