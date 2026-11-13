"""
EvoKG (Evolving Knowledge Graph) Service Module.
Reference: arXiv:2509.15464 (EvoReasoner / EvoKG).

Provides:
- Deterministic contradiction detection and temporal lifecycle resolution (T2.2).
- High-integrity PostgreSQL persistence with temporal validity intervals, branch isolation,
  concurrency locking, and idempotent incremental ingestion (T2.3).
"""

from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.services.evokg.contradiction import (
    ContradictionResolutionResult,
    EvoKGContradictionEngine,
    ResolutionAction,
    ResolutionDiagnostic,
)
from apps.api.src.services.evokg.service import EvoKGPersistenceService

__all__ = [
    "ContradictionResolutionResult",
    "EvoKGContradictionEngine",
    "EvoKGPersistenceService",
    "EvoKGTriplet",
    "ResolutionAction",
    "ResolutionDiagnostic",
]
