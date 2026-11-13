"""
Path Scoring Engine for EvoReasoner (T2.5 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Implements a deterministic, explainable path-scoring formula evaluating evidence paths:
Path Score = w_conf * S_conf + w_rel * S_rel + w_cont * S_cont + w_temp * S_temp
             - w_unc * P_unc - w_conflict * P_conflict - w_len * P_len

Where:
- S_conf: Mean evidence confidence of triplets in path.
- S_rel: Relation alignment against the planned route.
- S_cont: Entity continuity across consecutive hops.
- S_temp: Temporal compatibility with the query intent.
- P_unc: Uncertainty penalty for unverified assertions.
- P_conflict: Penalty for unresolved temporal conflicts.
- P_len: Penalty for extraneous hops beyond the plan.

Final score is strictly clamped to [0.0, 1.0].
Route cost is kept separate from evidence confidence.
Path ranking score is an exploration priority metric, not a Bayesian truth probability.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from apps.api.src.schemas.evoreasoner import (
    BeamSearchConfig,
    EvidenceEdge,
    PathScoreBreakdown,
    ReasoningHop,
)
from apps.api.src.services.context_engine.memotime import TemporalIntentType

logger = logging.getLogger(__name__)


class PathScorer:
    """
    Deterministic path scoring engine for EvoReasoner.
    """

    @classmethod
    def evaluate_path(
        cls,
        edges: list[EvidenceEdge],
        planned_hops: list[ReasoningHop],
        intent_type: TemporalIntentType | str,
        config: BeamSearchConfig | None = None,
        as_of: datetime | None = None,
        until: datetime | None = None,
        reference_commit: str | None = None,
        target_commit: str | None = None,
    ) -> tuple[float, PathScoreBreakdown]:
        """
        Evaluates an evidence path and returns (final_score, breakdown).
        """
        cfg = config or BeamSearchConfig()

        if not edges:
            empty_breakdown = PathScoreBreakdown(
                evidence_confidence=0.0,
                relation_alignment=0.0,
                entity_continuity=0.0,
                temporal_compatibility=0.0,
                uncertainty_penalty=0.0,
                conflict_penalty=0.0,
                length_penalty=0.0,
                raw_score=0.0,
                final_score=0.0,
            )
            return 0.0, empty_breakdown

        k = len(edges)
        intent_str = (
            intent_type.value
            if isinstance(intent_type, TemporalIntentType)
            else str(intent_type).upper()
        )

        # 1. Evidence Confidence (S_conf): average confidence score
        conf_scores = [e.confidence_score for e in edges]
        s_conf = sum(conf_scores) / float(k)

        # 2. Relation Alignment (S_rel): match against planned route hops
        plan_len = len(planned_hops)
        if plan_len > 0:
            matches: list[float] = []
            for i, edge in enumerate(edges):
                if i < plan_len:
                    expected = planned_hops[i]
                    if edge.canonical_relation == expected.canonical_relation:
                        matches.append(1.0)
                    else:
                        matches.append(0.0)
                else:
                    # Extra hop beyond planned route
                    matches.append(0.2)
            s_rel = sum(matches) / float(len(matches))
        else:
            s_rel = 0.5  # Neutral default if no planned hops provided

        # 3. Entity Continuity (S_cont): step i target must equal step i+1 source
        continuity_checks: list[float] = []
        for i in range(k - 1):
            e_curr = edges[i]
            e_next = edges[i + 1]

            curr_target = (
                e_curr.subject_id.strip().lower()
                if e_curr.is_inverse
                else e_curr.object_id.strip().lower()
            )
            next_source = (
                e_next.object_id.strip().lower()
                if e_next.is_inverse
                else e_next.subject_id.strip().lower()
            )

            # Continuous if normalized names or namespaces match
            if curr_target == next_source:
                continuity_checks.append(1.0)
            elif curr_target.endswith(f"::{next_source}") or next_source.endswith(f"::{curr_target}"):
                continuity_checks.append(0.8)
            else:
                continuity_checks.append(0.0)

        s_cont = (sum(continuity_checks) / float(len(continuity_checks))) if continuity_checks else 1.0

        # 4. Temporal Compatibility (S_temp):
        temp_scores: list[float] = []
        for edge in edges:
            t_score = cls._score_edge_temporal(
                edge,
                intent_str,
                as_of=as_of,
                until=until,
                reference_commit=reference_commit,
                target_commit=target_commit,
            )
            temp_scores.append(t_score)

        s_temp = sum(temp_scores) / float(k)

        # Check overall path interval intersection
        v_froms = [e.valid_from for e in edges if e.valid_from is not None]
        v_tos = [e.valid_to for e in edges if e.valid_to is not None]
        if v_froms and v_tos and max(v_froms) > min(v_tos):
            # Contradictory interval intersection across hops (non-overlapping life spans)
            s_temp = max(0.0, s_temp - 0.4)

        # 5. Uncertainty Penalty (P_unc):
        unc_count = sum(1 for e in edges if e.is_uncertain)
        p_unc = float(unc_count) / float(k)

        # 6. Conflict Penalty (P_conflict):
        conflict_count = sum(1 for e in edges if e.has_temporal_conflict)
        p_conflict = float(conflict_count) / float(k)

        # 7. Length Penalty (P_len):
        extra_hops = max(0, k - plan_len) if plan_len > 0 else 0
        p_len = min(1.0, float(extra_hops) * 0.25)

        # Weighted aggregate
        raw_score = (
            cfg.w_confidence * s_conf
            + cfg.w_relation * s_rel
            + cfg.w_continuity * s_cont
            + cfg.w_temporal * s_temp
            - cfg.w_uncertainty_penalty * p_unc
            - cfg.w_conflict_penalty * p_conflict
            - cfg.w_length_penalty * p_len
        )

        final_score = round(max(0.0, min(1.0, raw_score)), 4)

        breakdown = PathScoreBreakdown(
            evidence_confidence=round(s_conf, 4),
            relation_alignment=round(s_rel, 4),
            entity_continuity=round(s_cont, 4),
            temporal_compatibility=round(s_temp, 4),
            uncertainty_penalty=round(p_unc, 4),
            conflict_penalty=round(p_conflict, 4),
            length_penalty=round(p_len, 4),
            raw_score=round(raw_score, 4),
            final_score=final_score,
        )

        return final_score, breakdown

    @classmethod
    def _score_edge_temporal(
        cls,
        edge: EvidenceEdge,
        intent_str: str,
        as_of: datetime | None = None,
        until: datetime | None = None,
        reference_commit: str | None = None,
        target_commit: str | None = None,
    ) -> float:
        """Evaluates temporal alignment of a single traversed edge across all 7 temporal intents."""
        is_active = edge.valid_to is None and edge.superseded_by_id is None
        is_superseded = edge.valid_to is not None or edge.superseded_by_id is not None

        if intent_str == "CURRENT":
            if is_active and not edge.has_temporal_conflict:
                return 1.0
            if is_active and edge.has_temporal_conflict:
                return 0.5
            if is_superseded:
                # Severe penalty for obsolete facts in current context
                return 0.05
            return 0.5

        if intent_str == "HISTORICAL":
            if is_superseded or "SUPERSEDE" in edge.relation.upper():
                return 1.0
            if is_active:
                return 0.4
            return 0.7

        if intent_str == "BEFORE":
            if reference_commit and edge.commit_sha == reference_commit:
                return 1.0
            if as_of:
                as_of_tz = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)
                # Valid at requested historical point:
                # 1. Started at or before as_of (or baseline)
                # 2. Did NOT expire before as_of (must be active or valid through as_of)
                if edge.valid_to and edge.valid_to < as_of_tz:
                    # Expired before the requested point: not valid at that point
                    return 0.1
                if edge.valid_from and edge.valid_from > as_of_tz:
                    # Created after the requested point
                    return 0.0
                return 1.0
            return 0.5

        if intent_str == "AFTER":
            if reference_commit and edge.commit_sha == reference_commit:
                return 1.0
            if as_of:
                as_of_tz = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)
                # Expired before anchor
                if edge.valid_to and edge.valid_to < as_of_tz:
                    return 0.0
                # Created at or after anchor
                if edge.valid_from and edge.valid_from >= as_of_tz:
                    return 1.0
                # Spans across anchor into post-anchor period
                if edge.valid_to is None or edge.valid_to > as_of_tz:
                    return 0.95
                return 0.2
            return 0.5

        if intent_str == "INTERVAL":
            start_tz = (as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)) if as_of else None
            end_tz = (until if until.tzinfo else until.replace(tzinfo=UTC)) if until else None
            if start_tz and edge.valid_to and edge.valid_to < start_tz:
                return 0.0
            if end_tz and edge.valid_from and edge.valid_from > end_tz:
                return 0.0
            return 1.0

        if intent_str == "DIFF":
            commit_candidates = [c for c in (reference_commit, target_commit) if c]
            if commit_candidates and edge.commit_sha in commit_candidates:
                return 1.0
            if edge.supersedes_id or edge.superseded_by_id or "SUPERSEDE" in edge.relation.upper():
                return 0.9
            return 0.5

        if intent_str == "EVOLUTION":
            if (
                edge.supersedes_id
                or edge.superseded_by_id
                or "SUPERSEDE" in edge.relation.upper()
                or edge.valid_to is not None
            ):
                return 1.0
            return 0.6

        return 0.5
