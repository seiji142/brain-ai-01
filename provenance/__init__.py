"""Provenance - Sistema de procedencia y control de valores sensibles."""

from .errors import (
    ProvenanceError,
    UnresolvedReferenceError,
    MissingProvenanceError,
    HandleError,
    PolicyViolation,
    ActionDenied,
)
from .types import ValueKind, MatchType, Candidate, public_metadata, SENSITIVE_KINDS
from .audit import log, redact, fingerprint
from .detectors import scan
from .resolver import Resolver
from .store import ResolvedStore
from .policies import (
    HandlePolicy, LiteralPolicy, EnumPolicy, PathPolicy,
    ACTION_POLICIES, CONFIRMATION_REQUIRED, ENFORCEMENT,
    validate_literal, validate_enum, validate_path,
)
from .gateway import ActionGateway

__all__ = [
    "ProvenanceError",
    "UnresolvedReferenceError",
    "MissingProvenanceError",
    "HandleError",
    "PolicyViolation",
    "ActionDenied",
    "ValueKind",
    "MatchType",
    "Candidate",
    "public_metadata",
    "SENSITIVE_KINDS",
    "log",
    "redact",
    "fingerprint",
    "scan",
    "Resolver",
    "ResolvedStore",
    "HandlePolicy",
    "LiteralPolicy",
    "EnumPolicy",
    "PathPolicy",
    "ACTION_POLICIES",
    "CONFIRMATION_REQUIRED",
    "ENFORCEMENT",
    "validate_literal",
    "validate_enum",
    "validate_path",
    "ActionGateway",
]
