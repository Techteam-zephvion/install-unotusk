"""
MemoTime: Tree-of-Time Foundation and Structured Temporal Intent for Code Lane.

Adapted from MemoTime (arXiv:2510.13614) for deterministic code intelligence:
- Structured temporal query intent classification across 8 core types.
- Hierarchical Tree of Time (ToT) representing query decomposition and subquestions.
- Monotonic progression and 13 Allen interval algebra relations.
- Incompatible bound detection and contradictory constraint validation.
- Safe integration with ATOM temporal facts and supersession resolution without fabricating timestamps.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from apps.api.src.services.code_atom.temporal import (
    TEMPORAL_KEYWORDS,
    parse_candidate_timestamp,
    resolve_temporal_supersession,
)
from apps.api.src.services.context_engine.retriever import RetrievedCandidate

logger = logging.getLogger(__name__)

# Extended temporal keywords including markers for current, interval, and boundaries
ALL_TEMPORAL_KEYWORDS = {
    *TEMPORAL_KEYWORDS,
    "current",
    "currently",
    "latest",
    "now",
    "present",
    "today",
    "after",
    "since",
    "between",
    "interval",
    "window",
}

# ISO 8601 Date regex: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
_ISO_DATE_REGEX = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?)\b"
)
# Git Commit SHA regex: 7-40 hex chars
_COMMIT_SHA_REGEX = re.compile(r"\b(?:commit\s+)?([0-9a-fA-F]{7,40})\b", re.I)


class TemporalIntentType(str, Enum):
    """Core categories of temporal query intent in code intelligence."""

    CURRENT = "CURRENT"  # Current/latest active implementation
    HISTORICAL = "HISTORICAL"  # Superseded, previous, or legacy implementation
    BEFORE = "BEFORE"  # Explicitly constrained before a point/event
    AFTER = "AFTER"  # Explicitly constrained after a point/event
    INTERVAL = "INTERVAL"  # Bounded window between two dates or commits
    DIFF = "DIFF"  # Specific commit or snapshot delta inspection
    EVOLUTION = "EVOLUTION"  # Multi-event historical progression across commits
    AMBIGUOUS = "AMBIGUOUS"  # Contradictory, unresolvable, or unsupported request


class ResolutionStatus(str, Enum):
    """Evidence resolution status of a node in the Tree of Time."""

    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"
    NO_EVIDENCE = "NO_EVIDENCE"
    CONTRADICTORY = "CONTRADICTORY"
    AMBIGUOUS = "AMBIGUOUS"
    UNBOUNDED_TEMPORAL = "UNBOUNDED_TEMPORAL"


class AllenIntervalRelation(str, Enum):
    """The 13 distinct Allen interval algebra relations between two time intervals."""

    BEFORE = "BEFORE"  # A < B
    AFTER = "AFTER"  # A > B
    MEETS = "MEETS"  # A m B (end_A == start_B)
    MET_BY = "MET_BY"  # A mi B (start_A == end_B)
    OVERLAPS = "OVERLAPS"  # A o B
    OVERLAPPED_BY = "OVERLAPPED_BY"  # A oi B
    DURING = "DURING"  # A d B (A strictly inside B)
    CONTAINS = "CONTAINS"  # A di B (B strictly inside A)
    STARTS = "STARTS"  # A s B (start_A == start_B, end_A < end_B)
    STARTED_BY = "STARTED_BY"  # A si B (start_A == start_B, end_A > end_B)
    FINISHES = "FINISHES"  # A f B (end_A == end_B, start_A > start_B)
    FINISHED_BY = "FINISHED_BY"  # A fi B (end_A == end_B, start_A < start_B)
    EQUALS = "EQUALS"  # A = B (start_A == start_B, end_A == end_B)

    @property
    def inverse(self) -> AllenIntervalRelation:
        """Returns the inverse Allen relation such that A r B <=> B r.inverse A."""
        _INVERSES = {
            AllenIntervalRelation.EQUALS: AllenIntervalRelation.EQUALS,
            AllenIntervalRelation.BEFORE: AllenIntervalRelation.AFTER,
            AllenIntervalRelation.AFTER: AllenIntervalRelation.BEFORE,
            AllenIntervalRelation.MEETS: AllenIntervalRelation.MET_BY,
            AllenIntervalRelation.MET_BY: AllenIntervalRelation.MEETS,
            AllenIntervalRelation.OVERLAPS: AllenIntervalRelation.OVERLAPPED_BY,
            AllenIntervalRelation.OVERLAPPED_BY: AllenIntervalRelation.OVERLAPS,
            AllenIntervalRelation.DURING: AllenIntervalRelation.CONTAINS,
            AllenIntervalRelation.CONTAINS: AllenIntervalRelation.DURING,
            AllenIntervalRelation.STARTS: AllenIntervalRelation.STARTED_BY,
            AllenIntervalRelation.STARTED_BY: AllenIntervalRelation.STARTS,
            AllenIntervalRelation.FINISHES: AllenIntervalRelation.FINISHED_BY,
            AllenIntervalRelation.FINISHED_BY: AllenIntervalRelation.FINISHES,
        }
        return _INVERSES[self]


@dataclass
class TemporalBound:
    """Represents a closed, half-open, or open temporal interval."""

    start: datetime | None = None
    end: datetime | None = None
    point: datetime | None = None
    is_start_inclusive: bool = True
    is_end_inclusive: bool = True
    reference_commit: str | None = None
    reference_symbol: str | None = None

    def is_valid(self) -> bool:
        """Returns False if start is strictly after end."""
        if self.start and self.end and self.start > self.end:
            return False
        return True

    def contains_point(self, pt: datetime) -> bool:
        """Checks if a point-in-time falls within this bound."""
        if not self.is_valid():
            return False
        if pt.tzinfo is None:
            pt = pt.replace(tzinfo=UTC)

        if self.start:
            s = self.start if self.start.tzinfo else self.start.replace(tzinfo=UTC)
            if self.is_start_inclusive and pt < s:
                return False
            if not self.is_start_inclusive and pt <= s:
                return False

        if self.end:
            e = self.end if self.end.tzinfo else self.end.replace(tzinfo=UTC)
            if self.is_end_inclusive and pt > e:
                return False
            if not self.is_end_inclusive and pt >= e:
                return False

        return True

    def overlaps(self, other: TemporalBound) -> bool:
        """Determines whether two intervals share any common point in time."""
        if not self.is_valid() or not other.is_valid():
            return False

        s1 = self.start or datetime.min.replace(tzinfo=UTC)
        e1 = self.end or datetime.max.replace(tzinfo=UTC)
        s2 = other.start or datetime.min.replace(tzinfo=UTC)
        e2 = other.end or datetime.max.replace(tzinfo=UTC)

        if s1.tzinfo is None:
            s1 = s1.replace(tzinfo=UTC)
        if e1.tzinfo is None:
            e1 = e1.replace(tzinfo=UTC)
        if s2.tzinfo is None:
            s2 = s2.replace(tzinfo=UTC)
        if e2.tzinfo is None:
            e2 = e2.replace(tzinfo=UTC)

        return max(s1, s2) <= min(e1, e2)


@dataclass
class TemporalConstraint:
    """A single relational or absolute temporal constraint."""

    constraint_id: str
    operator: str  # "BEFORE", "AFTER", "DURING", "INTERVAL", "SUPERSEDES", "SUPERSEDED_BY", "DEPENDS_ON"
    target_entity: str
    reference_entity: str | None = None
    bound: TemporalBound | None = None
    description: str = ""


@dataclass
class StructuredTemporalIntent:
    """Comprehensive typed representation of temporal query intent."""

    intent_type: TemporalIntentType
    is_temporal: bool
    confidence: float = 1.0
    constraints: list[TemporalConstraint] = field(default_factory=list)
    detected_keywords: list[str] = field(default_factory=list)
    raw_query: str = ""
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None
    is_contradictory: bool = False
    contradiction_reason: str | None = None
    reference_commits: list[str] = field(default_factory=list)
    target_entities: list[str] = field(default_factory=list)


@dataclass
class TimeTreeNode:
    """A node in the Tree of Time representing a temporal subquestion or milestone."""

    node_id: str
    query_subquestion: str
    intent_type: TemporalIntentType
    temporal_bound: TemporalBound | None = None
    target_entities: list[str] = field(default_factory=list)
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    ordering_index: int = 0
    constraints: list[TemporalConstraint] = field(default_factory=list)
    evidence_candidates: list[RetrievedCandidate] = field(default_factory=list)
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    resolution_notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TreeOfTime:
    """The complete hierarchical Tree of Time (ToT) decomposing a temporal query."""

    root_query: str
    root_intent: StructuredTemporalIntent
    nodes: dict[str, TimeTreeNode] = field(default_factory=dict)
    root_node_id: str = "root"
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)

    def add_node(self, node: TimeTreeNode) -> None:
        self.nodes[node.node_id] = node
        if node.parent_id and node.parent_id in self.nodes:
            if node.node_id not in self.nodes[node.parent_id].children_ids:
                self.nodes[node.parent_id].children_ids.append(node.node_id)

    def get_ordered_nodes(self) -> list[TimeTreeNode]:
        """Returns non-root nodes sorted by their ordering index."""
        leaf_nodes = [n for n in self.nodes.values() if n.node_id != self.root_node_id]
        leaf_nodes.sort(key=lambda n: n.ordering_index)
        return leaf_nodes


@dataclass
class MemoTimeRetrievalResult:
    """Result of executing the MemoTime operator-aware retrieval pipeline."""

    candidates: list[RetrievedCandidate]
    strategy_used: TemporalIntentType
    tree_of_time: TreeOfTime | None = None
    is_fallback: bool = False
    fallback_reason: str | None = None
    applied_signals_count: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)


class MemoTimeService:
    """
    Deterministic foundation service for MemoTime:
    - Analyzes query text into StructuredTemporalIntent.
    - Constructs and decomposes queries into a Tree of Time.
    - Enforces monotonic timestamps and detects constraint contradictions.
    - Evaluates Allen interval algebra relations.
    - Validates multi-entity bound compatibility.
    - Binds code evidence to tree nodes while respecting ATOM supersession.
    """

    @classmethod
    def is_retrieval_enabled(cls) -> bool:
        """Returns True if MemoTime retrieval pipeline is enabled in settings."""
        from apps.api.src.config.settings import settings

        return bool(settings.MEMOTIME_ENABLED)

    @classmethod
    def apply_memotime_retrieval(
        cls,
        candidates: list[RetrievedCandidate],
        analyzed_query: Any | None = None,
        query_text: str = "",
        tree_of_time: TreeOfTime | None = None,
    ) -> list[RetrievedCandidate]:
        """
        Applies operator-aware temporal retrieval strategy to code candidates
        based on StructuredTemporalIntent and Tree of Time.
        Gracefully falls back to baseline candidates if intent is ambiguous,
        contradictory, or if candidates lack temporal provenance.
        """
        result = cls.run_memotime_pipeline(
            candidates=candidates,
            analyzed_query=analyzed_query,
            query_text=query_text,
            tree_of_time=tree_of_time,
        )
        return result.candidates

    @classmethod
    def run_memotime_pipeline(
        cls,
        candidates: list[RetrievedCandidate],
        analyzed_query: Any | None = None,
        query_text: str = "",
        tree_of_time: TreeOfTime | None = None,
    ) -> MemoTimeRetrievalResult:
        """
        Executes the operator-aware temporal retrieval pipeline and returns
        diagnostic results along with prioritized/filtered candidates.
        """
        if not candidates:
            return MemoTimeRetrievalResult(
                candidates=[],
                strategy_used=TemporalIntentType.AMBIGUOUS,
                is_fallback=True,
                fallback_reason="No candidates provided",
            )

        q_text = query_text or (getattr(analyzed_query, "raw_query", "") if analyzed_query else "")
        target_symbols = getattr(analyzed_query, "symbol_candidates", []) if analyzed_query else []

        intent: StructuredTemporalIntent
        if analyzed_query and getattr(analyzed_query, "structured_temporal_intent", None):
            intent = analyzed_query.structured_temporal_intent
        else:
            intent = cls.parse_temporal_intent(q_text, target_symbols=target_symbols)

        tree = tree_of_time or cls.build_tree_of_time(q_text, target_symbols=target_symbols)

        # Safety / Contradiction Gate: fall back immediately if ambiguous or contradictory
        if intent.is_contradictory or not tree.is_valid or intent.intent_type == TemporalIntentType.AMBIGUOUS:
            reason = (
                intent.contradiction_reason
                or intent.ambiguity_reason
                or ("; ".join(tree.validation_errors) if tree.validation_errors else None)
                or "Ambiguous temporal intent"
            )
            return MemoTimeRetrievalResult(
                candidates=candidates,
                strategy_used=intent.intent_type,
                tree_of_time=tree,
                is_fallback=True,
                fallback_reason=reason,
                diagnostics={
                    "validation_errors": tree.validation_errors,
                    "is_contradictory": intent.is_contradictory,
                },
            )

        # Non-temporal query safety fallback: baseline ranking preserved
        if not intent.is_temporal:
            return MemoTimeRetrievalResult(
                candidates=candidates,
                strategy_used=TemporalIntentType.CURRENT,
                tree_of_time=tree,
                is_fallback=True,
                fallback_reason="Non-temporal query: baseline ranking preserved",
            )

        # Resolve chronological supersession across candidates
        resolved = resolve_temporal_supersession(candidates)
        strategy = intent.intent_type
        applied_count = 0
        diagnostics: dict[str, Any] = {"strategy": strategy.value}

        if strategy == TemporalIntentType.CURRENT:
            active_cands: list[RetrievedCandidate] = []
            other_cands: list[RetrievedCandidate] = []
            for c in resolved:
                is_curr = bool(c.metadata.get("is_current", True))
                is_sup = bool(c.metadata.get("is_superseded", False))
                is_del = bool(c.metadata.get("is_deleted", False))

                if is_curr and not is_sup and not is_del:
                    c.signals["memotime_temporal_match"] = 1.0
                    c.metadata["memotime_strategy"] = "CURRENT"
                    c.metadata["memotime_active_status"] = "ACTIVE"
                    active_cands.append(c)
                    applied_count += 1
                else:
                    status_lbl = "DELETED" if is_del else ("SUPERSEDED" if is_sup else "INACTIVE")
                    c.metadata["memotime_active_status"] = status_lbl
                    other_cands.append(c)

            final_cands = active_cands + other_cands if active_cands else resolved
            return MemoTimeRetrievalResult(
                candidates=final_cands,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        elif strategy == TemporalIntentType.HISTORICAL:
            hist_cands: list[RetrievedCandidate] = []
            other_cands: list[RetrievedCandidate] = []
            for c in resolved:
                is_sup = bool(c.metadata.get("is_superseded", False))
                is_del = bool(c.metadata.get("is_deleted", False))
                is_curr = bool(c.metadata.get("is_current", True))

                # A candidate is genuinely historical if it is superseded, deleted,
                # or explicitly not current. A timestamp alone does NOT make it historical.
                if is_sup or is_del or not is_curr:
                    c.signals["memotime_temporal_match"] = 1.0
                    c.signals["memotime_historical"] = 1.0
                    c.metadata["memotime_strategy"] = "HISTORICAL"
                    hist_cands.append(c)
                    applied_count += 1
                else:
                    other_cands.append(c)

            final_cands = hist_cands + other_cands if hist_cands else resolved
            return MemoTimeRetrievalResult(
                candidates=final_cands,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        elif strategy == TemporalIntentType.BEFORE:
            c_constraint = intent.constraints[0] if intent.constraints else None
            bound = c_constraint.bound if c_constraint else None
            end_dt = bound.end if bound else None
            ref_commit = bound.reference_commit if bound else None

            matched_cands: list[RetrievedCandidate] = []
            unmatched_cands: list[RetrievedCandidate] = []

            for c in resolved:
                ts = parse_candidate_timestamp(c)
                c_sha = str(c.metadata.get("commit_sha") or "")
                is_sup = bool(c.metadata.get("is_superseded", False))

                is_match = False
                if ref_commit and c_sha.startswith(ref_commit):
                    is_match = True
                elif end_dt and ts and ts < end_dt:
                    is_match = True
                elif not end_dt and not ref_commit and is_sup:
                    is_match = True

                if is_match:
                    c.signals["memotime_temporal_match"] = 1.0
                    c.metadata["memotime_strategy"] = "BEFORE"
                    matched_cands.append(c)
                    applied_count += 1
                else:
                    if end_dt and ts and ts >= end_dt:
                        c.signals["memotime_temporal_mismatch"] = 1.0
                    unmatched_cands.append(c)

            if not matched_cands:
                diagnostics["status"] = ResolutionStatus.UNBOUNDED_TEMPORAL.value
                diagnostics["note"] = "No candidates strictly before bound; preserving all evidence."
                final_cands = resolved
            else:
                final_cands = matched_cands + unmatched_cands

            return MemoTimeRetrievalResult(
                candidates=final_cands,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        elif strategy == TemporalIntentType.AFTER:
            c_constraint = intent.constraints[0] if intent.constraints else None
            bound = c_constraint.bound if c_constraint else None
            start_dt = bound.start if bound else None
            ref_commit = bound.reference_commit if bound else None

            matched_cands: list[RetrievedCandidate] = []
            unmatched_cands: list[RetrievedCandidate] = []

            for c in resolved:
                ts = parse_candidate_timestamp(c)
                is_curr = bool(c.metadata.get("is_current", True))
                is_sup = bool(c.metadata.get("is_superseded", False))

                is_match = False
                if start_dt and ts and ts > start_dt:
                    is_match = True
                elif not start_dt and is_curr and not is_sup:
                    is_match = True

                if is_match:
                    c.signals["memotime_temporal_match"] = 1.0
                    c.metadata["memotime_strategy"] = "AFTER"
                    matched_cands.append(c)
                    applied_count += 1
                else:
                    if start_dt and ts and ts <= start_dt:
                        c.signals["memotime_temporal_mismatch"] = 1.0
                    unmatched_cands.append(c)

            if not matched_cands:
                diagnostics["status"] = ResolutionStatus.UNBOUNDED_TEMPORAL.value
                diagnostics["note"] = "No candidates strictly after bound; preserving all evidence."
                final_cands = resolved
            else:
                final_cands = matched_cands + unmatched_cands

            return MemoTimeRetrievalResult(
                candidates=final_cands,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        elif strategy == TemporalIntentType.INTERVAL:
            c_constraint = intent.constraints[0] if intent.constraints else None
            bound = c_constraint.bound if c_constraint else None

            matched_cands: list[RetrievedCandidate] = []
            unmatched_cands: list[RetrievedCandidate] = []

            for c in resolved:
                ts = parse_candidate_timestamp(c)
                if bound and bound.is_valid() and ts:
                    if bound.contains_point(ts):
                        c.signals["memotime_temporal_match"] = 1.0
                        c.metadata["memotime_strategy"] = "INTERVAL"
                        matched_cands.append(c)
                        applied_count += 1
                    else:
                        c.signals["memotime_temporal_mismatch"] = 1.0
                        unmatched_cands.append(c)
                else:
                    unmatched_cands.append(c)

            if not matched_cands:
                diagnostics["status"] = ResolutionStatus.UNBOUNDED_TEMPORAL.value
                diagnostics["note"] = "Evidence lacked explicit timestamps for interval; preserving all evidence."
                final_cands = resolved
            else:
                final_cands = matched_cands + unmatched_cands

            return MemoTimeRetrievalResult(
                candidates=final_cands,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        elif strategy == TemporalIntentType.DIFF:
            ref_commit = intent.reference_commits[0] if intent.reference_commits else None
            matched_cands: list[RetrievedCandidate] = []
            unmatched_cands: list[RetrievedCandidate] = []

            for c in resolved:
                c_sha = str(c.metadata.get("commit_sha") or "")
                if ref_commit and c_sha.startswith(ref_commit):
                    c.signals["memotime_diff_match"] = 1.0
                    c.signals["memotime_temporal_match"] = 1.0
                    c.metadata["memotime_strategy"] = "DIFF"
                    matched_cands.append(c)
                    applied_count += 1
                else:
                    unmatched_cands.append(c)

            final_cands = matched_cands + unmatched_cands if matched_cands else resolved
            return MemoTimeRetrievalResult(
                candidates=final_cands,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        elif strategy == TemporalIntentType.EVOLUTION:
            # Sort candidates chronologically to map into ToT phases
            dated_cands = []
            undated_cands = []
            for c in resolved:
                ts = parse_candidate_timestamp(c)
                if ts:
                    dated_cands.append((ts, c))
                else:
                    undated_cands.append(c)

            dated_cands.sort(key=lambda x: x[0])
            sorted_cands = [c for _, c in dated_cands] + undated_cands

            n = len(sorted_cands)
            if n >= 3:
                origin_cands = [sorted_cands[0]]
                trans_cands = sorted_cands[1:-1]
                curr_cands = [sorted_cands[-1]]
            elif n == 2:
                origin_cands = [sorted_cands[0]]
                trans_cands = []
                curr_cands = [sorted_cands[1]]
            elif n == 1:
                origin_cands = []
                trans_cands = []
                curr_cands = [sorted_cands[0]]
            else:
                origin_cands, trans_cands, curr_cands = [], [], []

            origin_node = tree.nodes.get("phase_0_origin")
            trans_node = tree.nodes.get("phase_1_transition")
            curr_node = tree.nodes.get("phase_2_current")

            if origin_node:
                origin_node.evidence_candidates = origin_cands
                origin_node.resolution_status = (
                    ResolutionStatus.RESOLVED if origin_cands else ResolutionStatus.NO_EVIDENCE
                )
            if trans_node:
                trans_node.evidence_candidates = trans_cands
                trans_node.resolution_status = (
                    ResolutionStatus.RESOLVED if trans_cands else ResolutionStatus.NO_EVIDENCE
                )
            if curr_node:
                curr_node.evidence_candidates = curr_cands
                curr_node.resolution_status = (
                    ResolutionStatus.RESOLVED if curr_cands else ResolutionStatus.NO_EVIDENCE
                )

            for c in origin_cands:
                c.signals["memotime_evolution_phase"] = 1.0
                c.metadata["memotime_phase"] = "origin"
                c.metadata["memotime_chronological_order"] = 0
                applied_count += 1

            for c in trans_cands:
                c.signals["memotime_evolution_phase"] = 0.9
                c.metadata["memotime_phase"] = "transition"
                c.metadata["memotime_chronological_order"] = 1
                applied_count += 1

            for c in curr_cands:
                c.signals["memotime_evolution_phase"] = 1.0
                c.signals["memotime_temporal_match"] = 1.0
                c.metadata["memotime_phase"] = "current"
                c.metadata["memotime_chronological_order"] = 2
                applied_count += 1

            ordered_ev = origin_cands + trans_cands + curr_cands
            seen_ids = {c.candidate_id for c in ordered_ev}
            for c in resolved:
                if c.candidate_id not in seen_ids:
                    seen_ids.add(c.candidate_id)
                    ordered_ev.append(c)

            return MemoTimeRetrievalResult(
                candidates=ordered_ev,
                strategy_used=strategy,
                tree_of_time=tree,
                applied_signals_count=applied_count,
                diagnostics=diagnostics,
            )

        return MemoTimeRetrievalResult(
            candidates=resolved,
            strategy_used=strategy,
            tree_of_time=tree,
            is_fallback=True,
            fallback_reason="Non-temporal or unsupported strategy fallback",
        )

    @classmethod
    def parse_iso_datetime(cls, dt_str: str) -> datetime | None:
        """Safely parses an ISO date or datetime string with UTC timezone."""
        if not dt_str or not dt_str.strip():
            return None
        cleaned = dt_str.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            # Try date-only format YYYY-MM-DD
            try:
                dt = datetime.strptime(cleaned[:10], "%Y-%m-%d").replace(tzinfo=UTC)
                return dt
            except Exception:
                return None

    @classmethod
    def compute_allen_relation(
        cls, a: TemporalBound, b: TemporalBound
    ) -> AllenIntervalRelation | None:
        """
        Computes the exact Allen interval algebra relation between interval A and interval B.
        Returns None if either interval is invalid.
        """
        if not a.is_valid() or not b.is_valid():
            return None

        # Normalize endpoints with UTC
        s_a = (a.start or datetime.min).replace(tzinfo=UTC) if not a.start or not a.start.tzinfo else a.start
        e_a = (a.end or datetime.max).replace(tzinfo=UTC) if not a.end or not a.end.tzinfo else a.end
        s_b = (b.start or datetime.min).replace(tzinfo=UTC) if not b.start or not b.start.tzinfo else b.start
        e_b = (b.end or datetime.max).replace(tzinfo=UTC) if not b.end or not b.end.tzinfo else b.end

        # 1. EQUALS: start_A == start_B and end_A == end_B
        if s_a == s_b and e_a == e_b:
            return AllenIntervalRelation.EQUALS

        # 2. BEFORE: end_A < start_B
        if e_a < s_b:
            return AllenIntervalRelation.BEFORE

        # 3. AFTER: start_A > end_B
        if s_a > e_b:
            return AllenIntervalRelation.AFTER

        # 4. MEETS: end_A == start_B
        if e_a == s_b:
            return AllenIntervalRelation.MEETS

        # 5. MET_BY: start_A == end_B
        if s_a == e_b:
            return AllenIntervalRelation.MET_BY

        # 6. STARTS: start_A == start_B and end_A < end_B
        if s_a == s_b and e_a < e_b:
            return AllenIntervalRelation.STARTS

        # 7. STARTED_BY: start_A == start_B and end_A > end_B
        if s_a == s_b and e_a > e_b:
            return AllenIntervalRelation.STARTED_BY

        # 8. FINISHES: end_A == end_B and start_A > start_B
        if e_a == e_b and s_a > s_b:
            return AllenIntervalRelation.FINISHES

        # 9. FINISHED_BY: end_A == end_B and start_A < start_B
        if e_a == e_b and s_a < s_b:
            return AllenIntervalRelation.FINISHED_BY

        # 10. DURING: start_A > start_B and end_A < end_B
        if s_a > s_b and e_a < e_b:
            return AllenIntervalRelation.DURING

        # 11. CONTAINS: start_A < start_B and end_A > end_B
        if s_a < s_b and e_a > e_b:
            return AllenIntervalRelation.CONTAINS

        # 12. OVERLAPS: start_A < start_B < end_A < end_B
        if s_a < s_b < e_a < e_b:
            return AllenIntervalRelation.OVERLAPS

        # 13. OVERLAPPED_BY: start_B < start_A < end_B < end_A
        if s_b < s_a < e_b < e_a:
            return AllenIntervalRelation.OVERLAPPED_BY

        return None

    @classmethod
    def parse_temporal_intent(
        cls, query_text: str, target_symbols: list[str] | None = None
    ) -> StructuredTemporalIntent:
        """
        Parses query text to produce a deterministic StructuredTemporalIntent across 8 categories:
        CURRENT, HISTORICAL, BEFORE, AFTER, INTERVAL, DIFF, EVOLUTION, AMBIGUOUS.
        """
        if not query_text or not query_text.strip():
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.AMBIGUOUS,
                is_temporal=False,
                confidence=0.0,
                raw_query="",
                is_ambiguous=True,
                ambiguity_reason="Empty query",
            )

        q_lower = query_text.lower().strip()
        words = re.findall(r"[A-Za-z0-9_.\-/]+", q_lower)

        # Collect all detected temporal tokens
        detected_kw: list[str] = []
        for w in words:
            clean_w = w.strip(".,?!:;()[]{}'\"")
            if clean_w in ALL_TEMPORAL_KEYWORDS:
                detected_kw.append(clean_w)
        detected_keywords = list(dict.fromkeys(detected_kw))

        # Detect dates & commits
        dates_found = _ISO_DATE_REGEX.findall(query_text)
        commits_found = _COMMIT_SHA_REGEX.findall(query_text)
        entities = list(target_symbols or [])

        # Detect temporal markers
        has_current = bool(re.search(r"\b(current|currently|latest|now|present|active|today)\b", q_lower))
        has_historical = bool(
            re.search(r"\b(previous|previously|past|earlier|former|prior|superseded|deprecated|older|original)\b", q_lower)
        )
        has_evolution = bool(
            re.search(r"\b(evolve|evolved|evolution|history|timeline|chronology|across\s+commits)\b", q_lower)
        )
        has_diff = bool(re.search(r"\b(diff|diffs|what\s+changed\s+in|modifications?\s+in)\b", q_lower))
        has_between = bool(re.search(r"\bbetween\b.*?\band\b", q_lower) or re.search(r"\bfrom\b.*?\bto\b", q_lower))
        has_before = bool(re.search(r"\b(before|prior\s+to)\b", q_lower))
        has_after = bool(re.search(r"\b(after|since)\b", q_lower))

        # Check for contradictory or mutually exclusive intent directives
        if has_current and has_historical and not has_evolution and not has_between:
            # e.g., "What is the current previous implementation?"
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.AMBIGUOUS,
                is_temporal=True,
                confidence=0.5,
                raw_query=query_text,
                detected_keywords=detected_keywords,
                is_ambiguous=True,
                is_contradictory=True,
                ambiguity_reason="Conflicting temporal directives: query asserts both current and historical intent simultaneously.",
                contradiction_reason="Simultaneous assertion of CURRENT and HISTORICAL states.",
            )

        # Check for date interval contradictions: "between DateA and DateB" where DateA > DateB
        parsed_dates = [cls.parse_iso_datetime(d) for d in dates_found if cls.parse_iso_datetime(d)]
        if len(parsed_dates) >= 2 and has_between:
            d_start, d_end = parsed_dates[0], parsed_dates[1]
            if d_start > d_end:
                return StructuredTemporalIntent(
                    intent_type=TemporalIntentType.AMBIGUOUS,
                    is_temporal=True,
                    confidence=0.3,
                    raw_query=query_text,
                    detected_keywords=detected_keywords,
                    is_ambiguous=True,
                    is_contradictory=True,
                    contradiction_reason=f"Interval start ({d_start.date()}) is strictly after end ({d_end.date()}).",
                    ambiguity_reason="Inverted temporal interval bounds.",
                )

        # 1. INTERVAL: Bounded date or commit window
        if has_between and (len(parsed_dates) >= 2 or len(commits_found) >= 2):
            c_start = commits_found[0] if commits_found else None
            c_end = commits_found[1] if len(commits_found) > 1 else None
            d_start = parsed_dates[0] if parsed_dates else None
            d_end = parsed_dates[1] if len(parsed_dates) > 1 else None

            constraint = TemporalConstraint(
                constraint_id="c_interval_0",
                operator="INTERVAL",
                target_entity=entities[0] if entities else "code",
                bound=TemporalBound(start=d_start, end=d_end, reference_commit=c_end),
                description=f"Bounded window between {d_start or c_start} and {d_end or c_end}",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.INTERVAL,
                is_temporal=True,
                confidence=0.95,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["between", "interval"],
                raw_query=query_text,
                reference_commits=commits_found,
                target_entities=entities,
            )

        # 2. DIFF: Commit or changeset inspection
        if (
            (has_diff or ("commit" in words and len(commits_found) >= 1))
            and not has_evolution
            and not has_between
            and not has_before
            and not has_after
        ):
            c_sha = commits_found[0] if commits_found else None
            constraint = TemporalConstraint(
                constraint_id="c_diff_0",
                operator="EQUALS",
                target_entity=entities[0] if entities else "commit",
                bound=TemporalBound(reference_commit=c_sha),
                description=f"Inspect changeset for commit {c_sha}",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.DIFF,
                is_temporal=True,
                confidence=0.95,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["diff", "commit"],
                raw_query=query_text,
                reference_commits=commits_found,
                target_entities=entities,
            )

        # 3. BEFORE: Constrained prior to commit or date
        if has_before and (parsed_dates or commits_found or has_historical):
            d_end = parsed_dates[0] if parsed_dates else None
            c_ref = commits_found[0] if commits_found else None
            constraint = TemporalConstraint(
                constraint_id="c_before_0",
                operator="BEFORE",
                target_entity=entities[0] if entities else "code",
                bound=TemporalBound(end=d_end, reference_commit=c_ref, is_end_inclusive=False),
                description=f"State before {d_end or c_ref or 'event'}",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.BEFORE,
                is_temporal=True,
                confidence=0.9,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["before"],
                raw_query=query_text,
                reference_commits=commits_found,
                target_entities=entities,
            )

        # 4. AFTER: Constrained following commit or date
        if has_after and (parsed_dates or commits_found or has_current):
            d_start = parsed_dates[0] if parsed_dates else None
            c_ref = commits_found[0] if commits_found else None
            constraint = TemporalConstraint(
                constraint_id="c_after_0",
                operator="AFTER",
                target_entity=entities[0] if entities else "code",
                bound=TemporalBound(start=d_start, reference_commit=c_ref, is_start_inclusive=False),
                description=f"State after {d_start or c_ref or 'event'}",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.AFTER,
                is_temporal=True,
                confidence=0.9,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["after"],
                raw_query=query_text,
                reference_commits=commits_found,
                target_entities=entities,
            )

        # 5. EVOLUTION: Historical progression across multiple commits
        if has_evolution or (has_historical and has_current):
            constraint = TemporalConstraint(
                constraint_id="c_evolution_0",
                operator="EVOLUTION",
                target_entity=entities[0] if entities else "code",
                description="Chronological multi-event progression",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.EVOLUTION,
                is_temporal=True,
                confidence=0.9,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["evolution", "history"],
                raw_query=query_text,
                reference_commits=commits_found,
                target_entities=entities,
            )

        # 6. HISTORICAL: Prior / superseded implementation
        if has_historical:
            constraint = TemporalConstraint(
                constraint_id="c_historical_0",
                operator="SUPERSEDED",
                target_entity=entities[0] if entities else "code",
                description="Historical or superseded state",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.HISTORICAL,
                is_temporal=True,
                confidence=0.85,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["historical", "superseded"],
                raw_query=query_text,
                target_entities=entities,
            )

        # 7. CURRENT: Explicit current active implementation
        if has_current:
            constraint = TemporalConstraint(
                constraint_id="c_current_0",
                operator="CURRENT",
                target_entity=entities[0] if entities else "code",
                description="Current active state",
            )
            return StructuredTemporalIntent(
                intent_type=TemporalIntentType.CURRENT,
                is_temporal=True,
                confidence=0.85,
                constraints=[constraint],
                detected_keywords=detected_keywords or ["current"],
                raw_query=query_text,
                target_entities=entities,
            )

        # Default fallback for non-temporal code queries
        return StructuredTemporalIntent(
            intent_type=TemporalIntentType.CURRENT,
            is_temporal=False,
            confidence=1.0,
            raw_query=query_text,
            target_entities=entities,
        )

    @classmethod
    def build_tree_of_time(
        cls, query_text: str, target_symbols: list[str] | None = None
    ) -> TreeOfTime:
        """
        Constructs a hierarchical Tree of Time (ToT) decomposing the query into
        ordered, operator-aware sub-questions with explicit temporal bounds.
        """
        intent = cls.parse_temporal_intent(query_text, target_symbols=target_symbols)
        tree = TreeOfTime(root_query=query_text, root_intent=intent, root_node_id="root")

        # Root Node
        root_node = TimeTreeNode(
            node_id="root",
            query_subquestion=query_text,
            intent_type=intent.intent_type,
            target_entities=list(intent.target_entities),
            ordering_index=0,
            constraints=list(intent.constraints),
        )
        tree.add_node(root_node)

        entities_str = ", ".join(intent.target_entities) if intent.target_entities else "target component"

        # Multi-Phase Decomposition based on intent type
        if intent.intent_type == TemporalIntentType.EVOLUTION:
            # 3-Phase Chronological Decomposition: Origin -> Transition -> Current
            n_origin = TimeTreeNode(
                node_id="phase_0_origin",
                query_subquestion=f"What was the initial/historical implementation of {entities_str}?",
                intent_type=TemporalIntentType.HISTORICAL,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=0,
            )
            n_transition = TimeTreeNode(
                node_id="phase_1_transition",
                query_subquestion=f"How did {entities_str} change across intermediate commits?",
                intent_type=TemporalIntentType.EVOLUTION,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=1,
            )
            n_current = TimeTreeNode(
                node_id="phase_2_current",
                query_subquestion=f"What is the current active state of {entities_str}?",
                intent_type=TemporalIntentType.CURRENT,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=2,
            )
            tree.add_node(n_origin)
            tree.add_node(n_transition)
            tree.add_node(n_current)

        elif intent.intent_type == TemporalIntentType.BEFORE:
            c = intent.constraints[0] if intent.constraints else None
            n_sub = TimeTreeNode(
                node_id="node_before",
                query_subquestion=f"How was {entities_str} implemented prior to {c.bound.reference_commit if c and c.bound else 'reference point'}?",
                intent_type=TemporalIntentType.BEFORE,
                temporal_bound=c.bound if c else None,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=0,
                constraints=list(intent.constraints),
            )
            tree.add_node(n_sub)

        elif intent.intent_type == TemporalIntentType.AFTER:
            c = intent.constraints[0] if intent.constraints else None
            n_sub = TimeTreeNode(
                node_id="node_after",
                query_subquestion=f"What changes occurred in {entities_str} after {c.bound.reference_commit if c and c.bound else 'reference point'}?",
                intent_type=TemporalIntentType.AFTER,
                temporal_bound=c.bound if c else None,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=0,
                constraints=list(intent.constraints),
            )
            tree.add_node(n_sub)

        elif intent.intent_type == TemporalIntentType.INTERVAL:
            c = intent.constraints[0] if intent.constraints else None
            n_sub = TimeTreeNode(
                node_id="node_interval",
                query_subquestion=f"What modifications occurred in {entities_str} during the bounded interval?",
                intent_type=TemporalIntentType.INTERVAL,
                temporal_bound=c.bound if c else None,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=0,
                constraints=list(intent.constraints),
            )
            tree.add_node(n_sub)

        elif intent.intent_type == TemporalIntentType.HISTORICAL:
            n_sub = TimeTreeNode(
                node_id="node_historical",
                query_subquestion=f"What was the prior/superseded implementation of {entities_str}?",
                intent_type=TemporalIntentType.HISTORICAL,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=0,
                constraints=list(intent.constraints),
            )
            tree.add_node(n_sub)

        elif intent.intent_type == TemporalIntentType.AMBIGUOUS:
            root_node.resolution_status = (
                ResolutionStatus.CONTRADICTORY if intent.is_contradictory else ResolutionStatus.AMBIGUOUS
            )
            root_node.resolution_notes = intent.contradiction_reason or intent.ambiguity_reason

        else:
            # CURRENT / STANDARD
            n_sub = TimeTreeNode(
                node_id="node_current",
                query_subquestion=f"What is the current active code for {entities_str}?",
                intent_type=TemporalIntentType.CURRENT,
                target_entities=list(intent.target_entities),
                parent_id="root",
                ordering_index=0,
                constraints=list(intent.constraints),
            )
            tree.add_node(n_sub)

        # Validate temporal tree structure immediately
        cls.validate_temporal_constraints(tree)
        return tree

    @classmethod
    def validate_multi_entity_bounds(
        cls,
        entity_bounds: dict[str, TemporalBound],
        dependencies: list[tuple[str, str]] | None = None,
        coexistence_pairs: list[tuple[str, str]] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validates multi-entity temporal compatibility:
        1. Dependency introduction: If dependent entity A depends on B, B must exist before A ended.
        2. Coexistence: If entities A and B must coexist, their temporal intervals must overlap.
        """
        errors: list[str] = []

        if dependencies:
            for dep_ent, ref_ent in dependencies:
                b_dep = entity_bounds.get(dep_ent.lower())
                b_ref = entity_bounds.get(ref_ent.lower())
                if b_dep and b_ref:
                    # If dependent entity ended before dependency was introduced:
                    if b_dep.end and b_ref.start and b_ref.start > b_dep.end:
                        errors.append(
                            f"Incompatible multi-entity bounds: entity '{dep_ent}' (ends {b_dep.end}) "
                            f"depends on '{ref_ent}', but '{ref_ent}' was introduced later at {b_ref.start}."
                        )

        if coexistence_pairs:
            for ent_a, ent_b in coexistence_pairs:
                b_a = entity_bounds.get(ent_a.lower())
                b_b = entity_bounds.get(ent_b.lower())
                if b_a and b_b:
                    if not b_a.overlaps(b_b):
                        errors.append(
                            f"Incompatible multi-entity bounds: entities '{ent_a}' and '{ent_b}' "
                            f"have disjoint temporal intervals and cannot coexist."
                        )

        return len(errors) == 0, errors

    @classmethod
    def validate_temporal_constraints(cls, tree: TreeOfTime) -> tuple[bool, list[str]]:
        """
        Enforces monotonic timestamps, verifies bound validity, and detects contradictions
        including cross-entity dependency bounds.
        Sets tree.is_valid and tree.validation_errors.
        """
        errors: list[str] = []

        if tree.root_intent.is_contradictory:
            errors.append(f"Root intent contradiction: {tree.root_intent.contradiction_reason}")

        # Check bounds on all nodes
        for node_id, node in tree.nodes.items():
            if node.temporal_bound:
                if not node.temporal_bound.is_valid():
                    errors.append(
                        f"Node '{node_id}' has inverted bounds: start ({node.temporal_bound.start}) > end ({node.temporal_bound.end})."
                    )

        # Check monotonic progression across ordered siblings
        ordered = tree.get_ordered_nodes()
        for i in range(len(ordered) - 1):
            curr_n = ordered[i]
            next_n = ordered[i + 1]

            if curr_n.temporal_bound and next_n.temporal_bound:
                if curr_n.temporal_bound.end and next_n.temporal_bound.start:
                    if curr_n.temporal_bound.end > next_n.temporal_bound.start:
                        errors.append(
                            f"Non-monotonic temporal progression between node '{curr_n.node_id}' (ends {curr_n.temporal_bound.end}) "
                            f"and '{next_n.node_id}' (starts {next_n.temporal_bound.start})."
                        )

        # Check cross-entity dependency bounds in constraints
        all_constraints = list(tree.root_intent.constraints)
        for node in tree.nodes.values():
            all_constraints.extend(node.constraints)

        entity_bounds: dict[str, TemporalBound] = {}
        for node in tree.nodes.values():
            if node.temporal_bound and node.temporal_bound.is_valid():
                for ent in node.target_entities:
                    entity_bounds[ent.lower()] = node.temporal_bound

        for c in all_constraints:
            if c.reference_entity:
                ent = c.target_entity.lower()
                ref = c.reference_entity.lower()
                b_dep = entity_bounds.get(ent)
                b_ref = entity_bounds.get(ref) or c.bound
                if b_dep and b_ref:
                    if b_dep.end and b_ref.start and b_ref.start > b_dep.end:
                        errors.append(
                            f"Incompatible multi-entity bounds: entity '{c.target_entity}' ends at {b_dep.end} "
                            f"before dependency '{c.reference_entity}' is introduced at {b_ref.start}."
                        )

        tree.is_valid = len(errors) == 0
        tree.validation_errors = errors
        return tree.is_valid, errors

    @classmethod
    def bind_evidence_to_tree(
        cls, tree: TreeOfTime, candidates: list[RetrievedCandidate]
    ) -> TreeOfTime:
        """
        Binds retrieved code candidates to relevant nodes in the Tree of Time
        according to node intent, target entity, and temporal bounds.
        Reuses resolve_temporal_supersession to maintain fidelity without fabricating timestamps.
        """
        # Run supersession resolution to guarantee is_current/is_superseded flags are present
        resolved_candidates = resolve_temporal_supersession(candidates)

        for node_id, node in tree.nodes.items():
            if node_id == tree.root_node_id and len(tree.nodes) > 1:
                continue

            matched_cands: list[RetrievedCandidate] = []
            targets_lower = {t.lower().strip() for t in node.target_entities if t.strip()}

            for cand in resolved_candidates:
                # Entity matching (if node specifies target entities)
                if targets_lower:
                    name_stem = cand.name.split(" (")[0].lower().strip()
                    path_norm = cand.path.lower().replace("\\", "/")
                    sym_name = str(cand.metadata.get("symbol_name") or "").lower()
                    if not any(
                        t in name_stem or t in path_norm or t == sym_name
                        for t in targets_lower
                    ):
                        continue

                # Temporal condition matching
                cand_ts = parse_candidate_timestamp(cand)
                is_curr = bool(cand.metadata.get("is_current", True))
                is_sup = bool(cand.metadata.get("is_superseded", False))
                is_del = bool(cand.metadata.get("is_deleted", False))
                c_sha = str(cand.metadata.get("commit_sha") or "")

                if node.intent_type == TemporalIntentType.CURRENT:
                    if is_curr and not is_sup and not is_del:
                        matched_cands.append(cand)

                elif node.intent_type == TemporalIntentType.HISTORICAL:
                    if is_sup or is_del or not is_curr:
                        matched_cands.append(cand)

                elif node.intent_type == TemporalIntentType.BEFORE:
                    if node.temporal_bound:
                        if node.temporal_bound.reference_commit and c_sha:
                            if c_sha.startswith(node.temporal_bound.reference_commit):
                                matched_cands.append(cand)
                                continue
                        if cand_ts and node.temporal_bound.end:
                            if cand_ts < node.temporal_bound.end:
                                matched_cands.append(cand)
                                continue
                    # Fallback to historical candidates if missing timestamps
                    if is_sup or is_del:
                        matched_cands.append(cand)

                elif node.intent_type == TemporalIntentType.AFTER:
                    if node.temporal_bound:
                        if cand_ts and node.temporal_bound.start:
                            if cand_ts > node.temporal_bound.start:
                                matched_cands.append(cand)
                                continue
                    if is_curr and not is_sup:
                        matched_cands.append(cand)

                elif node.intent_type == TemporalIntentType.INTERVAL:
                    if node.temporal_bound and cand_ts:
                        if node.temporal_bound.contains_point(cand_ts):
                            matched_cands.append(cand)
                    else:
                        matched_cands.append(cand)

                else:
                    matched_cands.append(cand)

            node.evidence_candidates = matched_cands

            # Update resolution status
            if matched_cands:
                has_ts = any(parse_candidate_timestamp(c) is not None for c in matched_cands)
                if not has_ts and node.temporal_bound:
                    node.resolution_status = ResolutionStatus.UNBOUNDED_TEMPORAL
                    node.resolution_notes = (
                        "Evidence bound without explicit commit timestamps; ordering relies on relative supersession."
                    )
                else:
                    node.resolution_status = ResolutionStatus.RESOLVED
            else:
                node.resolution_status = ResolutionStatus.NO_EVIDENCE
                node.resolution_notes = "No matching candidates satisfied the entity and temporal constraints."

        return tree
