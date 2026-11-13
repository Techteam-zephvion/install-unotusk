"""
EvoReasoner Beam Search and Graph Traversal Engine (T2.5 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Implements a bounded, deterministic beam search over persisted EvoKG triplets:
1. Executes reasoning routes from MultiRoutePlan (T2.4).
2. Traverses forward and inverse edges grounded in persisted evokg_triplets.
3. Enforces strict entity continuity, branch isolation, and cycle prevention.
4. Bounded by beam width, maximum path depth, max expansions per node, and global expansion budget.
5. Evaluates explainable path ranking scores via PathScorer.
6. Returns typed EvidencePath objects ready for downstream evidence aggregation.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.schemas.evoreasoner import (
    BeamSearchConfig,
    EvidenceEdge,
    EvidencePath,
    MultiRoutePlan,
    PathScoreBreakdown,
    PathSearchResult,
    ReasoningHop,
    ReasoningRoute,
)
from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy
from apps.api.src.services.context_engine.memotime import TemporalIntentType
from apps.api.src.services.evoreasoner.path_scorer import PathScorer

logger = logging.getLogger(__name__)


@dataclass
class _CandidateBeamPath:
    """Internal working state for a path undergoing beam search expansion."""

    current_node: str
    edges: list[EvidenceEdge] = field(default_factory=list)
    visited_nodes: set[str] = field(default_factory=set)
    score: float = 0.0
    score_breakdown: PathScoreBreakdown | None = None

    @property
    def canonical_signature(self) -> str:
        return "==>".join(
            f"[{e.subject_id}]--{e.relation}:{1 if e.is_inverse else 0}-->[{e.object_id}]"
            for e in self.edges
        )


class EvoBeamSearchEngine:
    """
    Bounded graph traversal and beam search engine executing EvoReasoner routes.
    """

    @classmethod
    async def search_paths(
        cls,
        session: AsyncSession,
        repository_id: uuid.UUID,
        route_plan: MultiRoutePlan | None = None,
        branch: str = "main",
        grounded_entities: list[str] | None = None,
        config: BeamSearchConfig | None = None,
        as_of: datetime | None = None,
        until: datetime | None = None,
        reference_commit: str | None = None,
        target_commit: str | None = None,
        plan: MultiRoutePlan | None = None,
    ) -> PathSearchResult:
        """
        Executes beam search across all selected routes in a MultiRoutePlan.
        """
        cfg = config or BeamSearchConfig()
        resolved_plan = route_plan or plan

        # Handle empty plan or missing query
        if not resolved_plan or not resolved_plan.selected_routes:
            return PathSearchResult(
                query_text=route_plan.query_text if route_plan else "",
                temporal_intent=route_plan.temporal_intent if route_plan else TemporalIntentType.CURRENT,
                repository_id=repository_id,
                branch=branch,
                paths=[],
                total_paths_explored=0,
                total_expansions=0,
                search_diagnostics={"reason": "empty_route_plan"},
            )

        intent = resolved_plan.temporal_intent

        # Validate temporal intent requirements and anchors
        temporal_diagnostic = None
        is_unsupported = False

        if intent == TemporalIntentType.BEFORE and not as_of and not reference_commit:
            temporal_diagnostic = "missing_temporal_anchor"
            is_unsupported = True
        elif intent == TemporalIntentType.AFTER and not as_of and not reference_commit:
            temporal_diagnostic = "missing_temporal_anchor"
            is_unsupported = True
        elif intent == TemporalIntentType.INTERVAL:
            if not as_of and not until:
                temporal_diagnostic = "missing_interval_bounds"
                is_unsupported = True
            elif as_of and until and as_of > until:
                temporal_diagnostic = "contradictory_interval_bounds"
                is_unsupported = True
        elif intent == TemporalIntentType.DIFF and not reference_commit and not target_commit:
            temporal_diagnostic = "missing_commit_anchor"
            is_unsupported = True
        elif intent == TemporalIntentType.AMBIGUOUS:
            temporal_diagnostic = "ambiguous_temporal_intent"
            is_unsupported = True

        if is_unsupported:
            return PathSearchResult(
                query_text=resolved_plan.query_text,
                temporal_intent=intent,
                repository_id=repository_id,
                branch=branch,
                paths=[],
                total_paths_explored=0,
                total_expansions=0,
                search_diagnostics={
                    "unsupported_temporal_intent": True,
                    "temporal_diagnostic": temporal_diagnostic,
                    "reason": f"Cannot execute {intent.value} query: {temporal_diagnostic}",
                },
            )

        all_candidate_paths: list[EvidencePath] = []
        total_expansions_counter = 0
        total_paths_explored = 0
        triplet_cache: dict[tuple[Any, ...], list[EvoKGTriplet]] = {}
        timed_out = False
        t_start = time.perf_counter()

        # Execute beam search for each selected route
        for route in resolved_plan.selected_routes:
            if (time.perf_counter() - t_start) > cfg.timeout_seconds:
                timed_out = True
                break

            # Determine start entity
            start_entity = None
            if grounded_entities and len(grounded_entities) > 0:
                start_entity = grounded_entities[0]
            elif route.hops:
                start_entity = route.hops[0].source_entity

            if not start_entity:
                continue

            route_paths, expansions = await cls.execute_route_beam(
                session=session,
                repository_id=repository_id,
                route=route,
                branch=branch,
                start_entity=start_entity,
                config=cfg,
                intent_type=resolved_plan.temporal_intent,
                as_of=as_of,
                until=until,
                reference_commit=reference_commit,
                target_commit=target_commit,
                triplet_cache=triplet_cache,
            )

            total_expansions_counter += expansions
            total_paths_explored += len(route_paths)
            all_candidate_paths.extend(route_paths)

            if total_expansions_counter >= cfg.max_total_expansions:
                break

        # Deduplicate paths across routes (by triplet id sequence)
        deduped_paths: dict[str, EvidencePath] = {}
        for path in all_candidate_paths:
            sig = path.canonical_signature
            if sig not in deduped_paths or path.path_score > deduped_paths[sig].path_score:
                deduped_paths[sig] = path

        # Deterministic ranking:
        # 1. path_score DESC (higher evidence score first)
        # 2. route_estimated_cost ASC (lower exploration cost tie-breaker)
        # 3. canonical_signature ASC (stable lexicographical tie-breaker)
        ranked = list(deduped_paths.values())
        ranked.sort(
            key=lambda p: (
                -p.path_score,
                p.route_estimated_cost,
                p.canonical_signature,
            )
        )

        final_paths = ranked[: cfg.max_returned_paths]

        return PathSearchResult(
            query_text=resolved_plan.query_text,
            temporal_intent=resolved_plan.temporal_intent,
            repository_id=repository_id,
            branch=branch,
            paths=final_paths,
            total_paths_explored=total_paths_explored,
            total_expansions=total_expansions_counter,
            search_diagnostics={
                "routes_executed": len(resolved_plan.selected_routes),
                "paths_retained": len(final_paths),
                "beam_width": cfg.beam_width,
                "max_path_depth": cfg.max_path_depth,
                "timed_out": timed_out,
            },
        )

    @classmethod
    async def execute_route_beam(
        cls,
        session: AsyncSession,
        repository_id: uuid.UUID,
        route: ReasoningRoute,
        branch: str = "main",
        start_entity: str | None = None,
        config: BeamSearchConfig | None = None,
        intent_type: TemporalIntentType = TemporalIntentType.CURRENT,
        as_of: datetime | None = None,
        until: datetime | None = None,
        reference_commit: str | None = None,
        target_commit: str | None = None,
        triplet_cache: dict[tuple[Any, ...], list[EvoKGTriplet]] | None = None,
    ) -> tuple[list[EvidencePath], int]:
        """
        Executes bounded beam search for a single planned reasoning route.
        """
        cfg = config or BeamSearchConfig()
        expansions = 0

        if not route.hops:
            return [], expansions

        root_entity = start_entity or route.hops[0].source_entity
        initial_state = _CandidateBeamPath(
            current_node=root_entity,
            edges=[],
            visited_nodes={root_entity.strip().lower()},
            score=0.0,
        )

        beam: list[_CandidateBeamPath] = [initial_state]
        max_depth = min(len(route.hops), cfg.max_path_depth)

        for depth in range(1, max_depth + 1):
            hop = route.hops[depth - 1]
            next_beam: list[_CandidateBeamPath] = []

            for path in beam:
                if expansions >= cfg.max_total_expansions:
                    break

                # Query database for compatible outgoing or incoming triplet expansions
                candidate_triplets = await cls._fetch_compatible_triplets(
                    session=session,
                    repository_id=repository_id,
                    branch=branch,
                    current_node=path.current_node,
                    hop=hop,
                    intent_type=intent_type,
                    limit=cfg.max_expansions_per_node,
                    as_of=as_of,
                    until=until,
                    reference_commit=reference_commit,
                    target_commit=target_commit,
                    triplet_cache=triplet_cache,
                )
                expansions += 1

                for triplet in candidate_triplets:
                    is_inv = hop.is_inverse
                    next_node = triplet.subject_id if is_inv else triplet.object_id
                    next_node_norm = next_node.strip().lower()

                    # 1. Cycle Prevention: reject repeated entities along the path
                    if next_node_norm in path.visited_nodes:
                        continue

                    # 2. Entity Continuity Validation: confirm contiguous transition
                    expected_source = (
                        triplet.object_id.strip().lower()
                        if is_inv
                        else triplet.subject_id.strip().lower()
                    )
                    curr_node_norm = path.current_node.strip().lower()
                    if expected_source != curr_node_norm and not (
                        expected_source.endswith(f"::{curr_node_norm}")
                        or curr_node_norm.endswith(f"::{expected_source}")
                    ):
                        continue

                    # Create grounded EvidenceEdge
                    edge = cls._triplet_to_edge(triplet, is_inverse=is_inv)
                    new_edges = path.edges + [edge]
                    new_visited = path.visited_nodes | {next_node_norm}

                    # Score candidate path extension
                    path_score, breakdown = PathScorer.evaluate_path(
                        edges=new_edges,
                        planned_hops=route.hops[:depth],
                        intent_type=intent_type,
                        config=cfg,
                        as_of=as_of,
                        until=until,
                        reference_commit=reference_commit,
                        target_commit=target_commit,
                    )

                    candidate_path = _CandidateBeamPath(
                        current_node=next_node,
                        edges=new_edges,
                        visited_nodes=new_visited,
                        score=path_score,
                        score_breakdown=breakdown,
                    )
                    next_beam.append(candidate_path)

            if not next_beam:
                # No valid expansions found at this depth
                break

            # Deduplicate candidate paths within beam
            dedup_beam: dict[str, _CandidateBeamPath] = {}
            for cp in next_beam:
                sig = cp.canonical_signature
                if sig not in dedup_beam or cp.score > dedup_beam[sig].score:
                    dedup_beam[sig] = cp

            # Sort and prune beam to beam_width
            sorted_candidates = list(dedup_beam.values())
            sorted_candidates.sort(
                key=lambda cp: (
                    -cp.score,
                    len(cp.edges),
                    cp.canonical_signature,
                )
            )
            beam = sorted_candidates[: cfg.beam_width]

        # Convert surviving beam paths with at least 1 edge into EvidencePath objects
        result_paths: list[EvidencePath] = []
        for idx, candidate in enumerate(beam):
            if not candidate.edges:
                continue

            src = candidate.edges[0].subject_id if not candidate.edges[0].is_inverse else candidate.edges[0].object_id
            tgt = candidate.edges[-1].object_id if not candidate.edges[-1].is_inverse else candidate.edges[-1].subject_id

            # Calculate true interval intersection across all constituent hops
            v_from_candidates = [e.valid_from for e in candidate.edges if e.valid_from is not None]
            path_valid_from = max(v_from_candidates) if v_from_candidates else None

            v_to_candidates = [e.valid_to for e in candidate.edges if e.valid_to is not None]
            path_valid_to = min(v_to_candidates) if v_to_candidates else None

            has_interval_contradiction = False
            if path_valid_from and path_valid_to and path_valid_from > path_valid_to:
                has_interval_contradiction = True

            commits = list(dict.fromkeys(e.commit_sha for e in candidate.edges if e.commit_sha))
            has_unc = any(e.is_uncertain for e in candidate.edges)
            has_conf = any(e.has_temporal_conflict for e in candidate.edges) or has_interval_contradiction
            mean_conf = sum(e.confidence_score for e in candidate.edges) / float(len(candidate.edges))

            ev_path = EvidencePath(
                path_id=f"path_{route.route_id}_{idx}",
                route_id=route.route_id,
                route_perspective=route.perspective,
                source_entity=src,
                target_entity=tgt,
                edges=candidate.edges,
                repository_id=repository_id,
                branch=branch,
                commit_shas=commits,
                valid_from=path_valid_from,
                valid_to=path_valid_to,
                mean_confidence=round(mean_conf, 4),
                has_uncertain_evidence=has_unc,
                has_temporal_conflict=has_conf,
                route_estimated_cost=route.estimated_cost,
                path_score=candidate.score,
                score_breakdown=candidate.score_breakdown
                or PathScorer.evaluate_path(
                    candidate.edges,
                    route.hops,
                    intent_type,
                    cfg,
                    as_of=as_of,
                    until=until,
                    reference_commit=reference_commit,
                    target_commit=target_commit,
                )[1],
                canonical_signature=candidate.canonical_signature,
                is_complete=(len(candidate.edges) == len(route.hops)),
                search_diagnostics={
                    "hop_count": len(candidate.edges),
                    "depth_reached": len(candidate.edges),
                    "has_interval_contradiction": has_interval_contradiction,
                },
            )
            result_paths.append(ev_path)

        return result_paths, expansions

    @classmethod
    async def _fetch_compatible_triplets(
        cls,
        session: AsyncSession,
        repository_id: uuid.UUID,
        branch: str,
        current_node: str,
        hop: ReasoningHop,
        intent_type: TemporalIntentType,
        limit: int,
        as_of: datetime | None = None,
        until: datetime | None = None,
        reference_commit: str | None = None,
        target_commit: str | None = None,
        triplet_cache: dict[tuple[Any, ...], list[EvoKGTriplet]] | None = None,
    ) -> list[EvoKGTriplet]:
        """
        Executes bounded, indexed query against evokg_triplets with request-scoped caching.
        """
        intent_val = (
            intent_type.value
            if isinstance(intent_type, TemporalIntentType)
            else str(intent_type).upper()
        )
        cache_key = (
            repository_id,
            branch,
            current_node.strip().lower(),
            hop.canonical_relation.value if hasattr(hop.canonical_relation, 'value') else str(hop.canonical_relation),
            hop.is_inverse,
            intent_val,
            limit,
            as_of,
            until,
            reference_commit,
            target_commit,
        )
        if triplet_cache is not None and cache_key in triplet_cache:
            return triplet_cache[cache_key]
        canon_rel = hop.canonical_relation
        rel_str = canon_rel.value

        filters = [
            EvoKGTriplet.repository_id == repository_id,
            EvoKGTriplet.branch == branch,
        ]

        # Forward vs Inverse Direction
        if hop.is_inverse:
            filters.append(
                or_(
                    EvoKGTriplet.object_id == current_node,
                    EvoKGTriplet.object_id.ilike(f"%::{current_node}"),
                    EvoKGTriplet.object_id.ilike(f"{current_node}::%"),
                )
            )
        else:
            filters.append(
                or_(
                    EvoKGTriplet.subject_id == current_node,
                    EvoKGTriplet.subject_id.ilike(f"%::{current_node}"),
                    EvoKGTriplet.subject_id.ilike(f"{current_node}::%"),
                )
            )

        # Relation filtering (match canonical or raw relation)
        raw_rel_str = hop.relation if isinstance(hop.relation, str) else hop.relation.value
        filters.append(
            or_(
                EvoKGTriplet.relation == rel_str,
                EvoKGTriplet.relation == raw_rel_str,
            )
        )

        # Temporal Context Filtering across all 7 temporal intents
        intent_val = (
            intent_type.value
            if isinstance(intent_type, TemporalIntentType)
            else str(intent_type).upper()
        )

        if intent_val == "CURRENT":
            # Active relations only (not closed and not superseded)
            filters.append(EvoKGTriplet.valid_to.is_(None))
            filters.append(EvoKGTriplet.superseded_by_id.is_(None))

        elif intent_val == "HISTORICAL":
            # Either explicitly historical, superseded, or valid before current
            pass

        elif intent_val == "BEFORE":
            if as_of:
                as_of_tz = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)
                # Valid at/before historical anchor:
                # 1. Started at or before as_of: valid_from <= as_of (or baseline None)
                # 2. Did NOT expire before as_of: valid_to is None OR valid_to >= as_of
                filters.append(
                    or_(
                        EvoKGTriplet.valid_from.is_(None),
                        EvoKGTriplet.valid_from <= as_of_tz,
                    )
                )
                filters.append(
                    or_(
                        EvoKGTriplet.valid_to.is_(None),
                        EvoKGTriplet.valid_to >= as_of_tz,
                    )
                )
            elif reference_commit:
                filters.append(
                    or_(
                        EvoKGTriplet.commit_sha == reference_commit,
                        EvoKGTriplet.commit_sha.is_(None),
                    )
                )

        elif intent_val == "AFTER":
            if as_of:
                as_of_tz = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)
                # Valid in post-anchor context:
                # Must NOT have expired before as_of: valid_to is None OR valid_to >= as_of
                filters.append(
                    or_(
                        EvoKGTriplet.valid_to.is_(None),
                        EvoKGTriplet.valid_to >= as_of_tz,
                    )
                )
            elif reference_commit:
                filters.append(
                    or_(
                        EvoKGTriplet.commit_sha == reference_commit,
                        EvoKGTriplet.commit_sha.is_(None),
                    )
                )

        elif intent_val == "INTERVAL":
            start_tz = (as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)) if as_of else None
            end_tz = (until if until.tzinfo else until.replace(tzinfo=UTC)) if until else None
            if start_tz:
                filters.append(
                    or_(
                        EvoKGTriplet.valid_to.is_(None),
                        EvoKGTriplet.valid_to >= start_tz,
                    )
                )
            if end_tz:
                filters.append(
                    or_(
                        EvoKGTriplet.valid_from.is_(None),
                        EvoKGTriplet.valid_from <= end_tz,
                    )
                )

        elif intent_val == "DIFF":
            commit_candidates = [c for c in (reference_commit, target_commit) if c]
            if commit_candidates:
                filters.append(
                    or_(
                        EvoKGTriplet.commit_sha.in_(commit_candidates),
                        EvoKGTriplet.supersedes_id.is_not(None),
                        EvoKGTriplet.superseded_by_id.is_not(None),
                    )
                )

        elif intent_val == "EVOLUTION":
            # For EVOLUTION queries, we do not filter out superseded triplets
            pass

        if reference_commit and intent_val not in ("BEFORE", "AFTER", "DIFF"):
            filters.append(
                or_(
                    EvoKGTriplet.commit_sha == reference_commit,
                    EvoKGTriplet.commit_sha.is_(None),
                )
            )

        if intent_val == "EVOLUTION":
            order_clause = [EvoKGTriplet.observation_time.asc(), EvoKGTriplet.confidence_score.desc()]
        else:
            order_clause = [EvoKGTriplet.confidence_score.desc(), EvoKGTriplet.observation_time.desc()]

        stmt = (
            select(EvoKGTriplet)
            .where(and_(*filters))
            .order_by(*order_clause)
            .limit(limit)
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    def _triplet_to_edge(cls, t: EvoKGTriplet, is_inverse: bool = False) -> EvidenceEdge:
        """Converts an EvoKGTriplet database record into an EvidenceEdge schema."""
        canon = CodeRelationTaxonomy.get_canonical_predicate(t.relation)

        v_from = t.valid_from
        if v_from and v_from.tzinfo is None:
            v_from = v_from.replace(tzinfo=UTC)

        v_to = t.valid_to
        if v_to and v_to.tzinfo is None:
            v_to = v_to.replace(tzinfo=UTC)

        obs = t.observation_time
        if obs and obs.tzinfo is None:
            obs = obs.replace(tzinfo=UTC)

        return EvidenceEdge(
            triplet_id=t.id,
            subject_id=t.subject_id,
            relation=t.relation,
            canonical_relation=canon,
            object_id=t.object_id,
            valid_from=v_from,
            valid_to=v_to,
            observation_time=obs,
            commit_sha=t.commit_sha,
            branch=t.branch,
            confidence_score=t.confidence_score,
            is_uncertain=t.is_uncertain,
            has_temporal_conflict=t.has_temporal_conflict,
            conflict_detail=t.conflict_detail,
            is_exclusive=t.is_exclusive,
            scope_key=t.scope_key,
            is_inverse=is_inverse,
            superseded_by_id=t.superseded_by_id,
            supersedes_id=t.supersedes_id,
            provenance=dict(t.provenance) if t.provenance else {},
        )
