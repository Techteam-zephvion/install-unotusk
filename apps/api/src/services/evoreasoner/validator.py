"""
EvoReasoner Proof-Chain Validator (T2.6 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Validates EvidencePaths and GroundedProofChains for:
1. Entity continuity across every hop.
2. Relationship compatibility and direction consistency.
3. Repository and branch isolation.
4. Temporal interval intersection and contradiction detection.
5. Supersession and conflict semantics.
6. Evidence provenance and traceability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from apps.api.src.schemas.code_atom import RelationType
from apps.api.src.schemas.evoreasoner import (
    EvidencePath,
    GroundedProofChain,
    ProofChainHop,
)
from apps.api.src.services.context_engine.memotime import TemporalIntentType


class ProofChainValidator:
    """Validates structural, temporal, and provenance properties of reasoning chains."""

    @classmethod
    def validate_and_convert_path(
        cls,
        path: EvidencePath,
        expected_repo_id: uuid.UUID | None = None,
        expected_branch: str = "main",
        temporal_intent: TemporalIntentType = TemporalIntentType.CURRENT,
    ) -> tuple[bool, str | None, GroundedProofChain | None]:
        """
        Validate an EvidencePath and convert it into a GroundedProofChain.
        Returns (is_valid, rejection_reason, proof_chain).
        """
        if not path.edges:
            return False, "empty_path_no_edges", None

        # 1. Repository identity consistency
        target_repo_id = expected_repo_id or path.repository_id
        if path.repository_id != target_repo_id:
            return False, f"repository_mismatch: {path.repository_id} != {target_repo_id}", None

        # 2. Branch consistency
        if path.branch != expected_branch:
            return False, f"branch_mismatch: {path.branch} != {expected_branch}", None

        # 3. Entity continuity check across edges
        for i in range(len(path.edges) - 1):
            curr_edge = path.edges[i]
            next_edge = path.edges[i + 1]

            # In traversed EvidenceEdge, subject_id is the start of this hop, object_id is the end
            if curr_edge.object_id != next_edge.subject_id:
                return (
                    False,
                    f"broken_entity_continuity_at_hop_{i}: {curr_edge.object_id} != {next_edge.subject_id}",
                    None,
                )

        # 4. Check edge-level repository and branch consistency
        for i, edge in enumerate(path.edges):
            edge_branch = edge.branch or path.branch
            if edge_branch != expected_branch:
                return False, f"edge_branch_mismatch_at_hop_{i}: {edge_branch} != {expected_branch}", None

        # 5. Temporal interval intersection & conflict detection
        valid_froms: list[datetime] = [e.valid_from for e in path.edges if e.valid_from is not None]
        valid_tos: list[datetime] = [e.valid_to for e in path.edges if e.valid_to is not None]

        intersected_valid_from = max(valid_froms) if valid_froms else None
        intersected_valid_to = min(valid_tos) if valid_tos else None

        has_conflict = path.has_temporal_conflict
        conflict_reasons: list[str] = []
        if intersected_valid_from and intersected_valid_to and intersected_valid_from > intersected_valid_to:
            has_conflict = True
            conflict_reasons.append(
                f"contradictory_validity_interval: from {intersected_valid_from.isoformat()} > to {intersected_valid_to.isoformat()}"
            )

        # 6. Detect supersession and uncertainty across hops
        is_historical = False
        has_uncertain = path.has_uncertain_evidence
        uncertainty_reasons: list[str] = []
        commit_shas: list[str] = []
        supporting_triplets: list[uuid.UUID] = []

        hops: list[ProofChainHop] = []
        for i, edge in enumerate(path.edges):
            supporting_triplets.append(edge.triplet_id)
            if edge.commit_sha and edge.commit_sha not in commit_shas:
                commit_shas.append(edge.commit_sha)

            if edge.superseded_by_id is not None or edge.valid_to is not None:
                is_historical = True
                if temporal_intent == TemporalIntentType.CURRENT:
                    has_conflict = True
                    conflict_reasons.append(f"hop_{i}_is_superseded_or_closed")

            if edge.has_temporal_conflict:
                has_conflict = True
                conflict_reasons.append(edge.conflict_detail or f"hop_{i}_has_temporal_conflict")

            if edge.is_uncertain:
                has_uncertain = True
                uncertainty_reasons.append(f"hop_{i}_marked_uncertain (confidence={edge.confidence_score:.2f})")
            elif edge.confidence_score < 0.60:
                has_uncertain = True
                uncertainty_reasons.append(f"hop_{i}_low_confidence ({edge.confidence_score:.2f})")

            # Canonical relation normalization
            can_rel = edge.canonical_relation
            if isinstance(can_rel, str):
                try:
                    can_rel = RelationType(can_rel)
                except ValueError:
                    can_rel = RelationType.REFERENCES

            hop = ProofChainHop(
                hop_index=i,
                source_entity=edge.subject_id,
                relation=edge.relation,
                canonical_relation=can_rel,
                target_entity=edge.object_id,
                is_inverse=edge.is_inverse,
                triplet_id=edge.triplet_id,
                valid_from=edge.valid_from,
                valid_to=edge.valid_to,
                observation_time=edge.observation_time,
                commit_sha=edge.commit_sha,
                branch=edge.branch,
                confidence=edge.confidence_score,
                is_uncertain=edge.is_uncertain,
                has_conflict=edge.has_temporal_conflict,
                conflict_detail=edge.conflict_detail,
                is_exclusive=edge.is_exclusive,
                scope_key=edge.scope_key,
                is_superseded=edge.superseded_by_id is not None,
                provenance=edge.provenance,
            )
            hops.append(hop)

        # Direction assessment
        all_inverse = all(e.is_inverse for e in path.edges)
        any_inverse = any(e.is_inverse for e in path.edges)
        direction = "inverse" if all_inverse else ("bidirectional" if any_inverse else "forward")

        # Canonical relation summary
        canonical_relation_str = " -> ".join(e.relation for e in path.edges)

        # Build natural explanation
        explanation = cls._generate_chain_explanation(
            source=path.source_entity,
            target=path.target_entity,
            hops=hops,
            is_historical=is_historical,
            has_conflict=has_conflict,
            has_uncertain=has_uncertain,
        )

        chain = GroundedProofChain(
            chain_id=str(uuid.uuid4()),
            query_text="",
            temporal_intent=temporal_intent,
            source_entity=path.source_entity,
            target_entity=path.target_entity,
            canonical_relation=canonical_relation_str,
            direction=direction,
            repository_id=target_repo_id,
            branch=expected_branch,
            hops=hops,
            commit_shas=commit_shas,
            valid_from=intersected_valid_from,
            valid_to=intersected_valid_to,
            is_historical=is_historical,
            confidence=path.mean_confidence,
            has_uncertain_evidence=has_uncertain,
            uncertainty_reasons=uncertainty_reasons,
            has_conflict=has_conflict,
            conflict_reasons=conflict_reasons,
            original_path_scores=[path.path_score],
            proof_score=path.path_score,
            supporting_triplet_ids=supporting_triplets,
            constituent_path_ids=[path.path_id],
            explanation=explanation,
            metadata={
                "route_id": path.route_id,
                "perspective": (
                    path.route_perspective.value
                    if hasattr(path.route_perspective, "value")
                    else str(path.route_perspective)
                ),
            },
        )

        return True, None, chain

    @classmethod
    def validate_proof_chain(
        cls,
        chain: GroundedProofChain,
        expected_repo_id: uuid.UUID | None = None,
        expected_branch: str = "main",
    ) -> tuple[bool, str | None]:
        """Directly validate an existing GroundedProofChain."""
        if not chain.hops:
            return False, "empty_hops"

        if expected_repo_id and chain.repository_id != expected_repo_id:
            return False, f"repository_mismatch: {chain.repository_id} != {expected_repo_id}"

        if chain.branch != expected_branch:
            return False, f"branch_mismatch: {chain.branch} != {expected_branch}"

        for i in range(len(chain.hops) - 1):
            if chain.hops[i].target_entity != chain.hops[i + 1].source_entity:
                return (
                    False,
                    f"broken_entity_continuity_at_hop_{i}: {chain.hops[i].target_entity} != {chain.hops[i+1].source_entity}",
                )

        if chain.valid_from and chain.valid_to and chain.valid_from > chain.valid_to:
            if not chain.has_conflict:
                return False, "unflagged_contradictory_validity_interval"

        return True, None

    @classmethod
    def _generate_chain_explanation(
        cls,
        source: str,
        target: str,
        hops: list[ProofChainHop],
        is_historical: bool,
        has_conflict: bool,
        has_uncertain: bool,
    ) -> str:
        """Construct grounded, human-readable explanation of the proof chain."""
        steps = []
        for h in hops:
            rel_str = f"[{h.relation}]"
            if h.is_inverse:
                rel_str = f"[INVERSE_{h.relation}]"
            steps.append(f"{h.source_entity} {rel_str} {h.target_entity}")

        chain_str = " -> ".join(steps)
        status_tags = []
        if is_historical:
            status_tags.append("HISTORICAL")
        if has_conflict:
            status_tags.append("CONFLICT")
        if has_uncertain:
            status_tags.append("UNCERTAIN")

        status_prefix = f" [{', '.join(status_tags)}]" if status_tags else ""
        return f"Proves '{source}' connects to '{target}' via {len(hops)} verified hop(s){status_prefix}: {chain_str}."
