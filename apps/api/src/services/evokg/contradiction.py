"""
EvoKG Contradiction Engine and Temporal Lifecycle Resolver.
Reference: arXiv:2509.15464 (EvoReasoner / EvoKG: Temporal Reasoning with LLMs Augmented by Evolving KGs §3.2).

Provides:
1. Strict segregation between EXCLUSIVE and NON_EXCLUSIVE property evolution.
2. Confidence-aware contradiction resolution with a 0.65 threshold.
3. Chronological interval closing without destructive history loss.
4. Out-of-order historical insertion with interval bounding.
5. Branch-aware isolation and Git commit DAG ancestry verification.
6. Idempotent batch processing with complete diagnostics.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.schemas.code_atom import (
    FactConfidence,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom.relation_extractor import (
    parse_iso_timestamp,
)
from apps.api.src.services.code_atom.relation_resolver import (
    CodeEntityResolver,
)
from apps.api.src.services.code_atom.taxonomy import (
    CodeRelationTaxonomy,
)

logger = logging.getLogger(__name__)


class ResolutionAction(str, Enum):
    """Categorical action taken for an incoming relationship during contradiction resolution."""

    ACTIVATED = "ACTIVATED"
    SUPERSEDED = "SUPERSEDED"
    IDEMPOTENT_NOOP = "IDEMPOTENT_NOOP"
    HISTORICAL_INSERTION = "HISTORICAL_INSERTION"
    LOW_CONFIDENCE_CONFLICT = "LOW_CONFIDENCE_CONFLICT"
    BRANCH_ISOLATED = "BRANCH_ISOLATED"
    ANCESTRY_DISCONNECTED = "ANCESTRY_DISCONNECTED"
    REMOVAL_CLOSED = "REMOVAL_CLOSED"
    INVALID_INTERVAL_FLAGGED = "INVALID_INTERVAL_FLAGGED"
    CONCURRENT_ACTIVE = "CONCURRENT_ACTIVE"


class ResolutionDiagnostic(BaseModel):
    """Structured diagnostic record of a lifecycle decision."""

    relation_id: str
    subject: str
    relation: str
    object: str
    scope_key: str
    branch: str
    action: ResolutionAction
    reason: str
    target_relation_id: str | None = None
    superseded_relation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


@dataclass
class ContradictionResolutionResult:
    """Complete envelope returned by the contradiction engine."""

    active_relations: list[TemporalCodeRelation] = field(default_factory=list)
    superseded_relations: list[TemporalCodeRelation] = field(default_factory=list)
    historical_relations: list[TemporalCodeRelation] = field(default_factory=list)
    conflicting_relations: list[TemporalCodeRelation] = field(default_factory=list)
    diagnostics: list[ResolutionDiagnostic] = field(default_factory=list)
    all_relations: list[TemporalCodeRelation] = field(default_factory=list)


class EvoKGContradictionEngine:
    """
    Deterministic contradiction engine and temporal lifecycle resolver for EvoKG.
    (arXiv:2509.15464 §3.2)
    """

    def __init__(
        self,
        *,
        rename_history: dict[str, str] | None = None,
        commit_parents: dict[str, list[str]] | None = None,
        min_confidence_threshold: float = 0.65,
        default_branch: str = "main",
    ):
        self.rename_history = rename_history or {}
        self.commit_parents = commit_parents
        self.min_confidence_threshold = min_confidence_threshold
        self.default_branch = default_branch
        self.entity_resolver = CodeEntityResolver()

    # -------------------------------------------------------------------------
    # Commit Ancestry and Lineage Verification
    # -------------------------------------------------------------------------

    def is_ancestor(self, ancestor_sha: str | None, descendant_sha: str | None) -> bool | None:
        """
        Determines whether ancestor_sha is a verified ancestor of descendant_sha in the commit DAG.

        Returns:
            True if descendant reaches ancestor via parent traversal.
            False if traversal exhausts all known parents without finding ancestor.
            None if commit graph is not provided or ancestry is unavailable/incomplete.
        """
        if not ancestor_sha or not descendant_sha:
            return None

        clean_anc = ancestor_sha.strip().lower()
        clean_desc = descendant_sha.strip().lower()

        if clean_anc == clean_desc:
            return True

        if self.commit_parents is None:
            return None

        norm_parents = {
            k.strip().lower(): [p.strip().lower() for p in v]
            for k, v in self.commit_parents.items()
        }

        all_known = set(norm_parents.keys())
        for p_list in norm_parents.values():
            all_known.update(p_list)

        if clean_desc not in all_known or clean_anc not in all_known:
            return None

        visited: set[str] = set()
        queue: list[str] = [clean_desc]

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            parents = norm_parents.get(curr, [])
            for p in parents:
                if p == clean_anc:
                    return True
                if p not in visited:
                    queue.append(p)

        return False

    def can_supersede_lineage(
        self,
        rel_old: TemporalCodeRelation,
        rel_new: TemporalCodeRelation,
    ) -> tuple[bool, str]:
        """
        Verifies branch and commit ancestry compatibility between two relations.

        Returns:
            tuple[bool, str]: (is_compatible, diagnostic_reason)
        """
        branch_old = self._get_branch(rel_old)
        branch_new = self._get_branch(rel_new)

        c_old = self._get_commit(rel_old)
        c_new = self._get_commit(rel_new)

        # 1. Distinct branches: require explicit merge commit connection
        if branch_old != branch_new:
            if c_old and c_new and self.commit_parents:
                anc = self.is_ancestor(c_old, c_new)
                if anc is True:
                    return True, f"Cross-branch supersession permitted via verified merge ancestry: {c_old[:8]} -> {c_new[:8]}"
            return False, f"Branch isolation: '{branch_old}' does not match '{branch_new}' and merge ancestry is not established"

        # 2. Same branch: inspect commit DAG if provided
        if self.commit_parents is not None and c_old and c_new:
            anc = self.is_ancestor(c_old, c_new)
            if anc is False:
                # Parallel divergent commits within same branch name
                return False, f"Commit DAG disconnect: commit {c_old[:8]} is not an ancestor of {c_new[:8]} (parallel/divergent branch)"
            if anc is None:
                # Ancestry could not be verified in shallow graph
                return False, f"Unavailable ancestry: cannot confirm whether {c_old[:8]} precedes {c_new[:8]}"

        return True, "Branch and ancestry compatible"

    # -------------------------------------------------------------------------
    # Relation Metadata Helpers
    # -------------------------------------------------------------------------

    def _get_branch(self, rel: TemporalCodeRelation) -> str:
        b = rel.provenance.get("branch") if rel.provenance else None
        if b and str(b).strip():
            return str(b).strip()
        return self.default_branch

    def _get_commit(self, rel: TemporalCodeRelation) -> str | None:
        c = rel.commit_sha or (rel.provenance.get("commit_sha") if rel.provenance else None)
        return str(c).strip() if c else None

    def _get_effective_timestamp(self, rel: TemporalCodeRelation) -> datetime | None:
        if rel.t_start:
            return rel.t_start if rel.t_start.tzinfo else rel.t_start.replace(tzinfo=UTC)
        if rel.t_obs:
            return rel.t_obs if rel.t_obs.tzinfo else rel.t_obs.replace(tzinfo=UTC)
        if rel.provenance:
            raw_c = rel.provenance.get("committed_at") or rel.provenance.get("timestamp")
            parsed = parse_iso_timestamp(raw_c)
            if parsed:
                return parsed
        return None

    def _is_explicit_removal(self, rel: TemporalCodeRelation) -> bool:
        if rel.t_end is not None and rel.t_start is None:
            return True
        if rel.provenance:
            if rel.provenance.get("change_type") in ("DELETE", "REMOVAL"):
                return True
            if rel.provenance.get("is_removal") is True:
                return True
        if "(DELETE)" in rel.object.upper():
            return True
        return False

    def _canonicalize_subject(self, rel: TemporalCodeRelation) -> str:
        raw_name = rel.canonical_subject or rel.subject
        canon, _ = self.entity_resolver.resolve_entity(
            name=raw_name,
            file_path=rel.file_path,
            rename_history=self.rename_history,
        )
        return canon

    def _canonicalize_object(self, rel: TemporalCodeRelation) -> str:
        raw_name = rel.canonical_object or rel.object
        canon, _ = self.entity_resolver.resolve_entity(
            name=raw_name,
            file_path=None,
            rename_history=self.rename_history,
        )
        return canon

    def _prepare_relation(self, r: TemporalCodeRelation) -> TemporalCodeRelation:
        """Ensures canonical subject, object, scope key, and exclusivity flag are synchronized."""
        r_copy = r.model_copy(deep=True)
        r_copy.canonical_subject = self._canonicalize_subject(r_copy)
        r_copy.canonical_object = self._canonicalize_object(r_copy)

        if not r_copy.scope_key or r_copy.scope_key == "default":
            key, unc = CodeRelationTaxonomy.generate_scope_key(
                r_copy.relation,
                symbol_name=r_copy.symbol_name,
            )
            r_copy.scope_key = key
            if unc:
                r_copy.is_uncertain = True

        r_copy.is_exclusive = CodeRelationTaxonomy.is_exclusive(r_copy.relation)
        return r_copy

    # -------------------------------------------------------------------------
    # Core Batch Resolution Algorithm
    # -------------------------------------------------------------------------

    def resolve_contradictions(
        self,
        relations: list[TemporalCodeRelation],
        existing_relations: list[TemporalCodeRelation] | None = None,
    ) -> ContradictionResolutionResult:
        """
        Executes deterministic contradiction resolution and temporal lifecycle management
        over a collection of code relations.
        """
        diagnostics: list[ResolutionDiagnostic] = []

        # Master working pools with standardized entity identities
        pool: list[TemporalCodeRelation] = []
        if existing_relations:
            for item in existing_relations:
                pool.append(self._prepare_relation(item))

        if not relations:
            return self._build_result(pool, diagnostics)

        # 1. Pre-validation: check for invalid intervals in incoming relations
        validated_incoming: list[TemporalCodeRelation] = []
        for r in relations:
            r_prep = self._prepare_relation(r)

            # Interval validity check: t_end < t_start is an invalid interval
            if r_prep.t_start and r_prep.t_end and r_prep.t_end < r_prep.t_start:
                r_prep.has_temporal_conflict = True
                r_prep.is_uncertain = True
                r_prep.confidence = FactConfidence.UNCERTAIN
                r_prep.conflict_detail = (
                    f"Temporal conflict: validity end ({r_prep.t_end.isoformat()}) "
                    f"is earlier than start ({r_prep.t_start.isoformat()})."
                )
                r_prep.provenance["resolution_action"] = ResolutionAction.INVALID_INTERVAL_FLAGGED.value
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_prep.id,
                        subject=r_prep.canonical_subject,
                        relation=str(r_prep.relation),
                        object=r_prep.canonical_object,
                        scope_key=r_prep.scope_key,
                        branch=self._get_branch(r_prep),
                        action=ResolutionAction.INVALID_INTERVAL_FLAGGED,
                        reason=r_prep.conflict_detail,
                    )
                )

            validated_incoming.append(r_prep)

        # 2. Deterministic sorting: chronological order ascending, then stable ID
        def _sort_key(rel: TemporalCodeRelation) -> tuple[int, datetime, str]:
            ts = self._get_effective_timestamp(rel)
            has_ts = 1 if ts is not None else 0
            safe_ts = ts if ts is not None else datetime.min.replace(tzinfo=UTC)
            return (has_ts, safe_ts, rel.id)

        sorted_incoming = sorted(validated_incoming, key=_sort_key)

        # 3. Process each incoming relation sequentially
        for r_in in sorted_incoming:
            branch = self._get_branch(r_in)
            canon_subj = r_in.canonical_subject
            canon_obj = r_in.canonical_object
            canon_rel = CodeRelationTaxonomy.get_canonical_predicate(r_in.relation)
            is_excl = r_in.is_exclusive
            scope_key = r_in.scope_key or "default"
            t_new = self._get_effective_timestamp(r_in)

            # Handle explicit removal events
            if self._is_explicit_removal(r_in):
                self._handle_explicit_removal(
                    r_in=r_in,
                    pool=pool,
                    branch=branch,
                    canon_subj=canon_subj,
                    canon_rel=canon_rel,
                    canon_obj=canon_obj,
                    scope_key=scope_key,
                    diagnostics=diagnostics,
                )
                continue

            # -----------------------------------------------------------------
            # BRANCH A: NON-EXCLUSIVE RELATION (e.g. CALLS, IMPORTS, REFERENCES)
            # -----------------------------------------------------------------
            if not is_excl:
                # Look for exact existing edge: (branch, subj, rel, obj, scope)
                exact_match = None
                for existing in pool:
                    if (
                        self._get_branch(existing) == branch
                        and self.entity_resolver.are_entities_equivalent(existing.canonical_subject, canon_subj, self.rename_history)
                        and CodeRelationTaxonomy.get_canonical_predicate(existing.relation) == canon_rel
                        and self.entity_resolver.are_entities_equivalent(existing.canonical_object, canon_obj, self.rename_history)
                        and existing.scope_key == scope_key
                    ):
                        exact_match = existing
                        break

                if exact_match is not None:
                    # Rule 5: Idempotent refresh
                    self._merge_identical_assertion(exact_match, r_in)
                    diagnostics.append(
                        ResolutionDiagnostic(
                            relation_id=r_in.id,
                            subject=canon_subj,
                            relation=str(canon_rel.value),
                            object=canon_obj,
                            scope_key=scope_key,
                            branch=branch,
                            action=ResolutionAction.IDEMPOTENT_NOOP,
                            reason=f"Idempotent refresh of existing relation {exact_match.id}",
                            target_relation_id=exact_match.id,
                        )
                    )
                else:
                    # Rule 1: Concurrent active edge
                    r_in.provenance["resolution_action"] = ResolutionAction.CONCURRENT_ACTIVE.value
                    pool.append(r_in)
                    diagnostics.append(
                        ResolutionDiagnostic(
                            relation_id=r_in.id,
                            subject=canon_subj,
                            relation=str(canon_rel.value),
                            object=canon_obj,
                            scope_key=scope_key,
                            branch=branch,
                            action=ResolutionAction.CONCURRENT_ACTIVE,
                            reason="Non-exclusive relationship added concurrently without peer conflict",
                        )
                    )
                continue

            # -----------------------------------------------------------------
            # BRANCH B: EXCLUSIVE RELATION (e.g. DEFINES_RETURN_TYPE, SIGNATURE)
            # -----------------------------------------------------------------
            # Find active assertions in the exact slot: (branch, subj, rel, scope)
            active_slot_matches = [
                e
                for e in pool
                if (
                    self._get_branch(e) == branch
                    and self.entity_resolver.are_entities_equivalent(e.canonical_subject, canon_subj, self.rename_history)
                    and CodeRelationTaxonomy.can_supersede(e.relation, e.scope_key, r_in.relation, scope_key)
                    and e.t_end is None
                    and e.superseded_by_id is None
                    and not e.is_uncertain
                    and not e.has_temporal_conflict
                )
            ]

            # Also check if any active assertion exists on other branches
            other_branch_matches = [
                e
                for e in pool
                if (
                    self._get_branch(e) != branch
                    and self.entity_resolver.are_entities_equivalent(e.canonical_subject, canon_subj, self.rename_history)
                    and CodeRelationTaxonomy.can_supersede(e.relation, e.scope_key, r_in.relation, scope_key)
                    and e.t_end is None
                    and e.superseded_by_id is None
                )
            ]

            # Check cross-branch merge ancestry for other branch matches
            superseded_cross_branch = False
            for other in other_branch_matches:
                can_cross, cross_reason = self.can_supersede_lineage(other, r_in)
                if can_cross and r_in.confidence_score >= self.min_confidence_threshold and not r_in.is_uncertain:
                    # Valid merge commit supersession across branches!
                    t_close = t_new or datetime.now(UTC)
                    other.t_end = t_close
                    other.superseded_by_id = r_in.id
                    r_in.supersedes_id = other.id
                    other.provenance["superseded_at"] = t_close.isoformat()
                    other.provenance["superseded_by_commit"] = r_in.commit_sha
                    superseded_cross_branch = True
                    diagnostics.append(
                        ResolutionDiagnostic(
                            relation_id=r_in.id,
                            subject=canon_subj,
                            relation=str(canon_rel.value),
                            object=canon_obj,
                            scope_key=scope_key,
                            branch=branch,
                            action=ResolutionAction.SUPERSEDED,
                            reason=cross_reason,
                            target_relation_id=r_in.id,
                            superseded_relation_id=other.id,
                        )
                    )
                else:
                    # Rule: Different branch isolation
                    diagnostics.append(
                        ResolutionDiagnostic(
                            relation_id=r_in.id,
                            subject=canon_subj,
                            relation=str(canon_rel.value),
                            object=canon_obj,
                            scope_key=scope_key,
                            branch=branch,
                            action=ResolutionAction.BRANCH_ISOLATED,
                            reason=f"Different branch isolation from assertion {other.id} on '{self._get_branch(other)}'",
                            target_relation_id=other.id,
                        )
                    )

            if not active_slot_matches:
                # No active assertion on this branch in this slot: activate!
                r_in.provenance["resolution_action"] = ResolutionAction.ACTIVATED.value
                pool.append(r_in)
                if not superseded_cross_branch:
                    diagnostics.append(
                        ResolutionDiagnostic(
                            relation_id=r_in.id,
                            subject=canon_subj,
                            relation=str(canon_rel.value),
                            object=canon_obj,
                            scope_key=scope_key,
                            branch=branch,
                            action=ResolutionAction.ACTIVATED,
                            reason="No active assertion in exclusive slot; new assertion activated",
                        )
                    )
                continue

            # Compare against the current active assertion in this slot
            e_active = active_slot_matches[0]

            # Subcase B.1: Identical Object -> Rule 5 (Idempotency)
            if self.entity_resolver.are_entities_equivalent(e_active.canonical_object, canon_obj, self.rename_history):
                self._merge_identical_assertion(e_active, r_in)
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.IDEMPOTENT_NOOP,
                        reason=f"Idempotent refresh of active exclusive assertion {e_active.id}",
                        target_relation_id=e_active.id,
                    )
                )
                continue

            # Subcase B.2: Competing Object (Contradiction!)
            # Check commit ancestry compatibility
            can_lin, lin_reason = self.can_supersede_lineage(e_active, r_in)
            if not can_lin:
                # Ancestry disconnect or branch conflict!
                r_in.is_uncertain = True
                r_in.has_temporal_conflict = True
                r_in.confidence = FactConfidence.UNCERTAIN
                r_in.conflict_detail = lin_reason
                r_in.provenance["resolution_action"] = ResolutionAction.ANCESTRY_DISCONNECTED.value
                pool.append(r_in)
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.ANCESTRY_DISCONNECTED,
                        reason=lin_reason,
                        target_relation_id=e_active.id,
                    )
                )
                continue

            # Check timestamps
            t_old = self._get_effective_timestamp(e_active)
            if t_new is None or t_old is None:
                # Missing timestamp: do not fabricate!
                r_in.is_uncertain = True
                r_in.has_temporal_conflict = True
                r_in.confidence = FactConfidence.UNCERTAIN
                r_in.conflict_detail = "Missing timestamp in competing exclusive assertion; preserved as uncertain"
                r_in.provenance["resolution_action"] = ResolutionAction.LOW_CONFIDENCE_CONFLICT.value
                pool.append(r_in)
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.LOW_CONFIDENCE_CONFLICT,
                        reason=r_in.conflict_detail,
                        target_relation_id=e_active.id,
                    )
                )
                continue

            # Out-of-order historical assertion: t_new < t_old
            if t_new < t_old:
                # Rule 4: Out-of-order historical insertion
                r_in.t_start = t_new
                r_in.t_end = t_old
                r_in.superseded_by_id = e_active.id
                r_in.provenance["resolution_action"] = ResolutionAction.HISTORICAL_INSERTION.value
                pool.append(r_in)
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.HISTORICAL_INSERTION,
                        reason=f"Assertion predates active assertion {e_active.id} ({t_new.isoformat()} < {t_old.isoformat()}); inserted as historical interval",
                        target_relation_id=e_active.id,
                    )
                )
                continue

            # Chronologically newer: t_new >= t_old
            # Check confidence threshold (0.65)
            if r_in.confidence_score >= self.min_confidence_threshold and not r_in.is_uncertain:
                # Rule 2: Sufficient confidence -> Supersede!
                e_active.t_end = t_new
                e_active.superseded_by_id = r_in.id
                r_in.supersedes_id = e_active.id
                e_active.provenance["superseded_at"] = t_new.isoformat()
                if r_in.commit_sha:
                    e_active.provenance["superseded_by_commit"] = r_in.commit_sha

                r_in.t_start = t_new
                r_in.t_end = None
                r_in.provenance["resolution_action"] = ResolutionAction.ACTIVATED.value
                pool.append(r_in)

                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.SUPERSEDED,
                        reason=(
                            f"Exclusive supersession: incoming assertion (conf={r_in.confidence_score:.2f} "
                            f">= {self.min_confidence_threshold}) supersedes active assertion {e_active.id}"
                        ),
                        target_relation_id=r_in.id,
                        superseded_relation_id=e_active.id,
                    )
                )
            else:
                # Rule 3: Low-confidence conflict -> Retain as uncertain, keep existing active!
                r_in.is_uncertain = True
                r_in.has_temporal_conflict = True
                r_in.confidence = FactConfidence.UNCERTAIN
                r_in.conflict_detail = (
                    f"Low-confidence conflicting assertion (confidence_score={r_in.confidence_score:.2f} "
                    f"< {self.min_confidence_threshold}) conflicts with active assertion {e_active.id}"
                )
                r_in.provenance["resolution_action"] = ResolutionAction.LOW_CONFIDENCE_CONFLICT.value
                pool.append(r_in)
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.LOW_CONFIDENCE_CONFLICT,
                        reason=r_in.conflict_detail,
                        target_relation_id=e_active.id,
                    )
                )

        return self._build_result(pool, diagnostics)

    # -------------------------------------------------------------------------
    # Helper Resolution Handlers
    # -------------------------------------------------------------------------

    def _handle_explicit_removal(
        self,
        r_in: TemporalCodeRelation,
        pool: list[TemporalCodeRelation],
        branch: str,
        canon_subj: str,
        canon_rel: RelationType,
        canon_obj: str,
        scope_key: str,
        diagnostics: list[ResolutionDiagnostic],
    ) -> None:
        """Closes an active relationship matching explicit removal evidence."""
        close_time = (
            r_in.t_end
            or r_in.t_start
            or r_in.t_obs
            or datetime.now(UTC)
        )
        closed_any = False

        for existing in pool:
            if (
                self._get_branch(existing) == branch
                and self.entity_resolver.are_entities_equivalent(existing.canonical_subject, canon_subj, self.rename_history)
                and CodeRelationTaxonomy.get_canonical_predicate(existing.relation) == canon_rel
                and self.entity_resolver.are_entities_equivalent(existing.canonical_object, canon_obj, self.rename_history)
                and existing.scope_key == scope_key
                and existing.t_end is None
            ):
                existing.t_end = close_time
                existing.provenance["closed_by_removal"] = True
                existing.provenance["resolution_action"] = ResolutionAction.REMOVAL_CLOSED.value
                if r_in.commit_sha:
                    existing.provenance["closed_at_commit"] = r_in.commit_sha
                closed_any = True
                diagnostics.append(
                    ResolutionDiagnostic(
                        relation_id=r_in.id,
                        subject=canon_subj,
                        relation=str(canon_rel.value),
                        object=canon_obj,
                        scope_key=scope_key,
                        branch=branch,
                        action=ResolutionAction.REMOVAL_CLOSED,
                        reason=f"Explicit removal evidence closed active relation {existing.id}",
                        target_relation_id=existing.id,
                    )
                )

        if not closed_any:
            diagnostics.append(
                ResolutionDiagnostic(
                    relation_id=r_in.id,
                    subject=canon_subj,
                    relation=str(canon_rel.value),
                    object=canon_obj,
                    scope_key=scope_key,
                    branch=branch,
                    action=ResolutionAction.REMOVAL_CLOSED,
                    reason="Explicit removal event received, but no matching active relation was in scope",
                )
            )

    def _merge_identical_assertion(
        self,
        target: TemporalCodeRelation,
        source: TemporalCodeRelation,
    ) -> None:
        """Merges provenance and observation metadata into an identical relation idempotently."""
        # 1. Start time: earliest verified
        t_s1 = target.t_start if (not target.t_start or target.t_start.tzinfo) else target.t_start.replace(tzinfo=UTC)
        t_s2 = source.t_start if (not source.t_start or source.t_start.tzinfo) else source.t_start.replace(tzinfo=UTC)
        if t_s1 and t_s2:
            target.t_start = min(t_s1, t_s2)
        elif t_s2 and not t_s1:
            target.t_start = t_s2

        # 2. Observation time: latest observation
        t_o1 = target.t_obs if (not target.t_obs or target.t_obs.tzinfo) else target.t_obs.replace(tzinfo=UTC)
        t_o2 = source.t_obs if (not source.t_obs or source.t_obs.tzinfo) else source.t_obs.replace(tzinfo=UTC)
        if t_o1 and t_o2:
            target.t_obs = max(t_o1, t_o2)
        elif t_o2 and not t_o1:
            target.t_obs = t_o2

        # 3. End time: if verified end time present
        t_e1 = target.t_end if (not target.t_end or target.t_end.tzinfo) else target.t_end.replace(tzinfo=UTC)
        t_e2 = source.t_end if (not source.t_end or source.t_end.tzinfo) else source.t_end.replace(tzinfo=UTC)
        if t_e1 and t_e2:
            target.t_end = max(t_e1, t_e2)
        elif t_e2 and not t_e1:
            target.t_end = t_e2

        # 4. Aggregate commit SHAs
        shas: set[str] = set(target.history_commit_shas)
        if target.commit_sha:
            shas.add(target.commit_sha)
        if source.commit_sha:
            shas.add(source.commit_sha)
        shas.update(source.history_commit_shas)
        target.history_commit_shas = sorted(s for s in shas if s)

        # 5. Aggregate fact IDs
        facts: set[str] = set(target.history_fact_ids)
        if target.source_fact_id:
            facts.add(target.source_fact_id)
        if source.source_fact_id:
            facts.add(source.source_fact_id)
        facts.update(source.history_fact_ids)
        target.history_fact_ids = sorted(f for f in facts if f)

        # 6. Provenance merge
        if source.provenance:
            for k, v in source.provenance.items():
                if k not in target.provenance:
                    target.provenance[k] = v

    def _build_result(
        self,
        pool: list[TemporalCodeRelation],
        diagnostics: list[ResolutionDiagnostic],
    ) -> ContradictionResolutionResult:
        """Partitions the final relation pool into active, superseded, historical, and conflict sets."""
        active: list[TemporalCodeRelation] = []
        superseded: list[TemporalCodeRelation] = []
        historical: list[TemporalCodeRelation] = []
        conflicts: list[TemporalCodeRelation] = []

        for r in pool:
            act = r.provenance.get("resolution_action")
            if r.has_temporal_conflict or r.is_uncertain:
                conflicts.append(r)
            elif act == ResolutionAction.HISTORICAL_INSERTION.value or (
                r.t_end is not None and r.superseded_by_id is None
            ):
                historical.append(r)
            elif r.superseded_by_id is not None:
                superseded.append(r)
            elif r.t_end is not None:
                historical.append(r)
            else:
                active.append(r)

        return ContradictionResolutionResult(
            active_relations=active,
            superseded_relations=superseded,
            historical_relations=historical,
            conflicting_relations=conflicts,
            diagnostics=diagnostics,
            all_relations=pool,
        )
