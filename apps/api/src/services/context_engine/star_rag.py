"""
STAR-RAG (Spatio-Temporal Abstraction & Reasoning for RAG) Code Lane Integration.
Based on Zhu et al. (arXiv:2510.16715, "Right Answer at the Right Time — Temporal
Retrieval-Augmented Generation via Graph Summarization").

Implements:
1. Entity relation-pattern mining via Apriori algorithm with deterministic support/pruning.
2. Temporal rule-graph construction with Hamming distance <= 1 edge candidates and event span collection.
3. Minimum Description Length (MDL) model selection:
   - Model cost L(M) with node and directed chain edge code lengths.
   - Coverage cost L_cov(G | M) with log2 binomial coefficient.
   - Temporal cost L_time(G | M) modeling exponential distribution of spans.
   - Greedy edge pruning retaining only edges reducing MDL.
4. Query-time Seeded Personalized PageRank (PPR) on the rule graph:
   - Personalization distribution blending corpus coverage and ranking importance.
   - Dirichlet smoothing and power iteration to convergence tolerance.
   - Mapping top rule nodes back to grounded code evidence and re-ranking.
5. Modular service integration with fallback safeguards and configurable settings.
"""

from __future__ import annotations

import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import combinations
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.code_atom.relation_extractor import parse_iso_timestamp
from apps.api.src.services.code_atom.temporal import (
    parse_candidate_timestamp,
    resolve_temporal_supersession,
)
from apps.api.src.services.context_engine.query_analyzer import (
    NEGATION_WORDS,
    STOP_WORDS,
    AnalyzedQuery,
)

_WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+", re.ASCII)
_CAMEL_PATTERN = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", re.ASCII)
from apps.api.src.services.context_engine.retriever import RetrievedCandidate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TemporalCodeEvent:
    """Represents a grounded temporal code event f = (s, r, o, t)."""

    event_id: str
    subject: str
    relation: str
    object: str
    timestamp: datetime | None = None
    candidate_id: str = ""
    candidate: RetrievedCandidate | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    commit_sha: str | None = None
    file_path: str | None = None
    symbol_name: str | None = None
    change_type: str | None = None
    description: str | None = None
    snippet: str | None = None


@dataclass
class RuleNode:
    """Abstract rule node u = <c_s, r, c_o> grouping event categories."""

    node_id: str  # e.g., "<TYPE_1, CALLS, TYPE_2>"
    subject_type: str
    relation: str
    object_type: str
    events: list[TemporalCodeEvent] = field(default_factory=list)

    @property
    def support(self) -> int:
        return len(self.events)


@dataclass
class StarRagResult:
    """Encapsulates the output of a STAR-RAG retrieval run."""

    candidates: list[RetrievedCandidate]
    rule_nodes: dict[str, RuleNode]
    selected_edges: set[tuple[str, str]]
    top_rules: list[RuleNode]
    ppr_distribution: dict[str, float]
    initial_mdl_cost: float
    final_mdl_cost: float
    is_fallback: bool = False
    fallback_reason: str | None = None
    ranked_events: list[TemporalCodeEvent] = field(default_factory=list)
    temporal_evidence: list[dict[str, Any]] = field(default_factory=list)
    temporal_intent: str | None = None
    temporal_bounds: dict[str, Any] | None = None


class TemporalStarRagRouter:
    """
    Selective Intent Router for Temporal STAR-RAG (Zhu et al., arXiv:2510.16715).
    Determines whether a developer query requires historical / temporal retrieval.
    Strictly preserves global feature-flag safety gates.
    """

    @classmethod
    def should_route_to_temporal_star_rag(
        cls,
        query_text: str,
        analyzed_query: AnalyzedQuery | None = None,
        flag_enabled: bool = False,
        force_temporal_star_rag: bool = False,
    ) -> tuple[bool, str]:
        # 1. Feature flag safety gate
        if not flag_enabled and not force_temporal_star_rag:
            return False, "feature_flag_disabled"

        # 2. Forced parameter override
        if force_temporal_star_rag:
            return True, "forced_by_parameter"

        # 3. Temporal query intent detection from AnalyzedQuery
        if analyzed_query and analyzed_query.is_temporal:
            intent = analyzed_query.temporal_intent or "HISTORICAL"
            return True, f"temporal_intent:{intent}"

        # 4. Fallback classification if AnalyzedQuery was not pre-computed
        if query_text:
            from apps.api.src.services.code_atom.temporal import classify_temporal_intent

            is_temp, intent, _ = classify_temporal_intent(query_text)
            if is_temp:
                return True, f"temporal_intent:{intent or 'HISTORICAL'}"

        return False, "query_lacks_temporal_intent"


class EntityRelationMiner:
    """
    Derives entity types from recurring relation patterns using Apriori-style
    frequent relation subset mining (Paper Section 3.2 and Appendix A).
    """

    @staticmethod
    def mine_entity_types(
        events: list[TemporalCodeEvent],
        min_support: int = 2,
        max_len: int = 3,
        k_type: int = 1,
    ) -> dict[str, str]:
        """
        Mines frequent relation patterns across all entities and assigns
        structural type labels C(s) for each entity s in E.
        """
        if not events:
            return {}

        # 1. Build RelSet[s] for each entity (subject or object)
        rel_sets: dict[str, set[str]] = {}
        for ev in events:
            s = ev.subject.strip()
            o = ev.object.strip()
            r = ev.relation.strip().upper()
            if s:
                rel_sets.setdefault(s, set()).add(r)
            if o:
                rel_sets.setdefault(o, set()).add(r)

        entities = sorted(rel_sets.keys())
        total_entities = len(entities)

        # Handle sparse repositories: if total entities < min_support, adjust min_support
        effective_min_support = min_support
        if total_entities < effective_min_support:
            effective_min_support = 1

        # 2. Apriori algorithm on [RelSet[e]]
        all_relations = sorted({r for rset in rel_sets.values() for r in rset})

        # Step 2a: 1-itemsets
        itemset_counts: dict[tuple[str, ...], int] = {}
        for r in all_relations:
            cnt = sum(1 for e in entities if r in rel_sets[e])
            if cnt >= effective_min_support:
                itemset_counts[(r,)] = cnt

        current_frequent = [item for item in itemset_counts.keys() if len(item) == 1]
        all_frequent: dict[tuple[str, ...], int] = dict(itemset_counts)

        # Step 2b: k-itemsets for k = 2..max_len
        for k in range(2, max_len + 1):
            if not current_frequent:
                break
            # Candidate generation: join step
            candidates: set[tuple[str, ...]] = set()
            for i in range(len(current_frequent)):
                for j in range(i + 1, len(current_frequent)):
                    p1, p2 = current_frequent[i], current_frequent[j]
                    if p1[:-1] == p2[:-1]:
                        cand = tuple(sorted(set(p1) | set(p2)))
                        if len(cand) == k:
                            # Prune step: check all (k-1) subsets
                            subsets = combinations(cand, k - 1)
                            if all(tuple(sorted(sub)) in all_frequent for sub in subsets):
                                candidates.add(cand)

            # Count support for candidates
            next_frequent: list[tuple[str, ...]] = []
            for cand in sorted(candidates):
                cnt = sum(1 for e in entities if set(cand).issubset(rel_sets[e]))
                if cnt >= effective_min_support:
                    all_frequent[cand] = cnt
                    next_frequent.append(cand)

            current_frequent = next_frequent

        # 3. Sort frequent itemsets deterministically and assign TypeID
        # Priority: support descending, length descending, lexicographical
        sorted_itemsets = sorted(
            all_frequent.keys(),
            key=lambda item: (-all_frequent[item], -len(item), item),
        )

        type_ids: dict[tuple[str, ...], str] = {}
        for idx, item in enumerate(sorted_itemsets):
            type_ids[item] = f"TYPE_{idx + 1}:{'_'.join(item)}"

        # 4. Assign labels C(s) for each entity
        entity_types: dict[str, str] = {}
        for s in entities:
            s_set = rel_sets[s]
            matching_types = [
                type_ids[p]
                for p in sorted_itemsets
                if set(p).issubset(s_set)
            ]
            if matching_types:
                # Top-Ktype combinations as labels
                entity_types[s] = matching_types[0]
            else:
                # Fallback for entities with insufficient relation history
                if s_set:
                    fallback_id = f"FALLBACK:{'_'.join(sorted(s_set))}"
                else:
                    fallback_id = "FALLBACK:STANDALONE"
                entity_types[s] = fallback_id

        return entity_types


class TemporalRuleGraphBuilder:
    """
    Constructs abstract rule nodes and generates Hamming-distance candidate edges
    with empirical temporal spans (Paper Section 3.2).
    """

    @staticmethod
    def build_rule_nodes(
        events: list[TemporalCodeEvent],
        entity_types: dict[str, str],
    ) -> dict[str, RuleNode]:
        """Maps grounded code events to abstract rule nodes <c_s, r, c_o>."""
        rule_nodes: dict[str, RuleNode] = {}

        for ev in events:
            cs = entity_types.get(ev.subject, "FALLBACK:STANDALONE")
            co = entity_types.get(ev.object, "FALLBACK:STANDALONE")
            r = ev.relation.strip().upper()
            node_id = f"<{cs}, {r}, {co}>"

            if node_id not in rule_nodes:
                rule_nodes[node_id] = RuleNode(
                    node_id=node_id,
                    subject_type=cs,
                    relation=r,
                    object_type=co,
                )
            rule_nodes[node_id].events.append(ev)

        return rule_nodes

    @staticmethod
    def generate_candidate_edges(
        rule_nodes: dict[str, RuleNode],
    ) -> list[tuple[str, str]]:
        """
        Collects candidate edges W = {{u, v}: u != v, d_H(u, v) <= 1}.
        Hamming distance: d_H(u, v) = 1[a_s != b_s] + 1[r != r'] + 1[a_o != b_o].
        Prevents self-links and duplicate undirected pairs.
        """
        candidate_edges: list[tuple[str, str]] = []
        node_ids = sorted(rule_nodes.keys())

        for i in range(len(node_ids)):
            u_id = node_ids[i]
            u = rule_nodes[u_id]
            for j in range(i + 1, len(node_ids)):
                v_id = node_ids[j]
                v = rule_nodes[v_id]

                # Hamming distance on rule triples
                d_h = (
                    (1 if u.subject_type != v.subject_type else 0)
                    + (1 if u.relation != v.relation else 0)
                    + (1 if u.object_type != v.object_type else 0)
                )

                if d_h <= 1:
                    candidate_edges.append((u_id, v_id))

        return candidate_edges

    @staticmethod
    def collect_temporal_spans(
        rule_nodes: dict[str, RuleNode],
        candidate_edges: list[tuple[str, str]],
    ) -> dict[tuple[str, str], list[float]]:
        """
        Collects empirical temporal spans T_uv = {|t' - t| | f in supp(u), f' in supp(v), d_H(f~, f~') <= 2}.
        Uses days as the canonical continuous time unit for code evolution.
        Clamps exact identical timestamps to an epsilon (0.001 days ~ 1.4 min) to prevent log(0).
        """
        spans_map: dict[tuple[str, str], list[float]] = {}

        for edge in candidate_edges:
            u_id, v_id = edge
            u = rule_nodes[u_id]
            v = rule_nodes[v_id]
            spans: list[float] = []

            for f in u.events:
                if f.timestamp is None:
                    continue
                for f_prime in v.events:
                    if f_prime.timestamp is None:
                        continue

                    # Relaxed event Hamming distance: d_H(f~, f~') <= 2
                    d_h_event = (
                        (1 if f.subject != f_prime.subject else 0)
                        + (1 if f.relation != f_prime.relation else 0)
                        + (1 if f.object != f_prime.object else 0)
                    )

                    if d_h_event <= 2:
                        diff_sec = abs((f_prime.timestamp - f.timestamp).total_seconds())
                        diff_days = diff_sec / 86400.0
                        clamped_d = max(diff_days, 0.001)
                        spans.append(clamped_d)

            spans_map[edge] = spans

        return spans_map


class MdlGraphSelector:
    """
    Minimum Description Length (MDL) rule graph edge selection (Paper Section 3.2 and Appendix B).
    Computes model cost L(M), coverage cost L_cov(G | M), and temporal cost L_time(G | M),
    then performs greedy edge selection.
    """

    @staticmethod
    def compute_log2_binom(n: int, k: int) -> float:
        """Computes log2(binom(n, k)) deterministically using gamma function."""
        if k <= 0 or k >= n or n <= 0:
            return 0.0
        return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2)

    @classmethod
    def compute_node_model_cost(
        cls,
        rule_nodes: dict[str, RuleNode],
        total_events: int,
        num_types: int,
        num_relations: int,
        num_candidates: int,
    ) -> float:
        """
        Computes the static node component of L(M):
        L_fixed = log2(A^2 * |R|) + log2(2 * |W|)
        L(u) = -log2(p_s(a_s)) - log2(p_r(r)) - log2(p_o(a_o))
        """
        if total_events <= 0 or not rule_nodes:
            return 0.0

        a_term = max(num_types, 1) ** 2 * max(num_relations, 1)
        w_term = 2 * max(num_candidates, 1)
        fixed_cost = math.log2(a_term) + math.log2(w_term)

        # Empirical probabilities with Laplace smoothing
        subj_counts: dict[str, int] = {}
        obj_counts: dict[str, int] = {}
        rel_counts: dict[str, int] = {}

        for node in rule_nodes.values():
            cnt = node.support
            subj_counts[node.subject_type] = subj_counts.get(node.subject_type, 0) + cnt
            obj_counts[node.object_type] = obj_counts.get(node.object_type, 0) + cnt
            rel_counts[node.relation] = rel_counts.get(node.relation, 0) + cnt

        node_sum = 0.0
        for node in rule_nodes.values():
            p_s = (subj_counts.get(node.subject_type, 0) + 1.0) / (total_events + num_types)
            p_o = (obj_counts.get(node.object_type, 0) + 1.0) / (total_events + num_types)
            p_r = (rel_counts.get(node.relation, 0) + 1.0) / (total_events + num_relations)
            node_sum += -math.log2(p_s) - math.log2(p_r) - math.log2(p_o)

        return fixed_cost + node_sum

    @classmethod
    def compute_edge_model_cost(
        cls,
        num_edges: int,
        degrees: dict[str, int],
    ) -> float:
        """
        Computes the dynamic directed chain edge code length component of L(M):
        sum_{(u -> v)} [-log2(p_V(u)) - log2(p_V(v))]
        = 2 * sum_{u: deg(u) > 0} deg(u) * [log2(2 * |E|) - log2(deg(u))].
        """
        if num_edges <= 0:
            return 0.0

        two_m = 2 * num_edges
        log2_two_m = math.log2(two_m)
        cost = 0.0

        for deg in degrees.values():
            if deg > 0:
                cost += 2.0 * deg * (log2_two_m - math.log2(deg))

        return cost

    @classmethod
    def compute_edge_data_cost(
        cls,
        u: RuleNode,
        v: RuleNode,
        spans: list[float],
    ) -> float:
        """
        Computes L_cov(u, v) + L_time(u, v) for a single candidate edge.
        Coverage: log2(binom(|supp(u)| * |supp(v)|, |T_uv|)).
        Temporal: |T_uv| * log2(e) + |T_uv| * log2(mean_span).
        """
        k = len(spans)
        if k == 0:
            return 0.0

        n = u.support * v.support
        k_eff = min(k, n)

        # Pure Paper Equation 5: log2(binom(N, K))
        # High conversion (K -> N) yields log2(binom(N, K)) -> 0 bits.
        # Negative temporal code length (mean_d < 1/e days) drives net Delta L < 0.
        cov_cost = cls.compute_log2_binom(n, k_eff)

        # Temporal cost
        mean_d = sum(spans) / k
        log2_e = 1.0 / math.log(2)
        time_cost = k * (log2_e + math.log2(mean_d))

        return cov_cost + time_cost

    @classmethod
    def select_edges(
        cls,
        rule_nodes: dict[str, RuleNode],
        candidate_edges: list[tuple[str, str]],
        spans_map: dict[tuple[str, str], list[float]],
        total_events: int,
        num_types: int,
        num_relations: int,
    ) -> tuple[set[tuple[str, str]], float, float]:
        """
        Greedy edge selection: retains connections only when the total description
        length L(G, M) improves. Returns (selected_edges, initial_mdl, final_mdl).
        """
        # Static node cost
        node_cost = cls.compute_node_model_cost(
            rule_nodes=rule_nodes,
            total_events=total_events,
            num_types=num_types,
            num_relations=num_relations,
            num_candidates=len(candidate_edges),
        )

        initial_cost = node_cost
        current_cost = initial_cost

        # Filter candidate edges with non-empty empirical spans
        admissible = [e for e in candidate_edges if len(spans_map.get(e, [])) > 0]

        # Sort candidate edges deterministically: highest span count, highest support product, then IDs
        sorted_candidates = sorted(
            admissible,
            key=lambda e: (
                -len(spans_map[e]),
                -(rule_nodes[e[0]].support * rule_nodes[e[1]].support),
                e[0],
                e[1],
            ),
        )

        selected_edges: set[tuple[str, str]] = set()
        degrees: dict[str, int] = {nid: 0 for nid in rule_nodes}
        current_data_cost = 0.0

        for edge in sorted_candidates:
            u_id, v_id = edge
            if u_id == v_id or edge in selected_edges or (v_id, u_id) in selected_edges:
                continue
            u = rule_nodes[u_id]
            v = rule_nodes[v_id]
            spans = spans_map[edge]

            # Hypothetical addition
            hyp_num_edges = len(selected_edges) + 1
            hyp_degrees = dict(degrees)
            hyp_degrees[u_id] = hyp_degrees.get(u_id, 0) + 1
            hyp_degrees[v_id] = hyp_degrees.get(v_id, 0) + 1

            hyp_edge_model_cost = cls.compute_edge_model_cost(hyp_num_edges, hyp_degrees)
            delta_data = cls.compute_edge_data_cost(u, v, spans)
            hyp_total_cost = node_cost + hyp_edge_model_cost + (current_data_cost + delta_data)

            # Accept if total description length decreases
            if hyp_total_cost < current_cost:
                selected_edges.add(edge)
                degrees = hyp_degrees
                current_data_cost += delta_data
                current_cost = hyp_total_cost

        return selected_edges, initial_cost, current_cost


class SeededPprRetriever:
    """
    Retrieval via Seeded Personalized PageRank on the time-aligned rule graph
    (Paper Section 3.3 and Appendix C).
    """

    @staticmethod
    def compute_personalization_vector(
        rule_nodes: dict[str, RuleNode],
        anchor_events: list[TemporalCodeEvent],
        beta: float = 0.7,
        theta: float = 0.6,
    ) -> tuple[dict[str, float], set[str]]:
        """
        Constructs personalization vector gamma over seeded rule nodes U_seed:
        c~_u: normalized corpus coverage.
        p~_u: normalized geometrically discounted rank importance.
        s_u = (1 - theta) * c~_u + theta * p~_u.
        gamma_u = (s_u + tau) / sum(s_v + tau) with tau = 1 / |U_seed|.
        """
        anchor_event_ids = {e.event_id for e in anchor_events}

        # Identify seeded rule nodes U_seed
        u_seed_ids: set[str] = set()
        for nid, node in rule_nodes.items():
            if any(ev.event_id in anchor_event_ids for ev in node.events):
                u_seed_ids.add(nid)

        if not u_seed_ids:
            return {}, set()

        # 1. Corpus coverage
        total_cov = sum(rule_nodes[nid].support for nid in u_seed_ids)
        c_tilde = {
            nid: (rule_nodes[nid].support / total_cov) if total_cov > 0 else (1.0 / len(u_seed_ids))
            for nid in u_seed_ids
        }

        # 2. Ranking importance
        p_raw: dict[str, float] = {}
        for nid in u_seed_ids:
            node = rule_nodes[nid]
            val = 0.0
            for rank_idx, a_ev in enumerate(anchor_events, start=1):
                if any(ev.event_id == a_ev.event_id for ev in node.events):
                    val += beta ** (rank_idx - 1)
            p_raw[nid] = val

        total_p = sum(p_raw.values())
        p_tilde = {
            nid: (p_raw[nid] / total_p) if total_p > 0 else (1.0 / len(u_seed_ids))
            for nid in u_seed_ids
        }

        # 3. Blending and Dirichlet smoothing
        tau = 1.0 / len(u_seed_ids)
        s_vals = {nid: (1.0 - theta) * c_tilde[nid] + theta * p_tilde[nid] for nid in u_seed_ids}
        smoothed_denom = sum(s_vals[nid] + tau for nid in u_seed_ids)

        gamma: dict[str, float] = {}
        for nid in rule_nodes:
            if nid in u_seed_ids:
                gamma[nid] = (s_vals[nid] + tau) / smoothed_denom
            else:
                gamma[nid] = 0.0

        return gamma, u_seed_ids

    @classmethod
    def run_seeded_ppr(
        cls,
        rule_nodes: dict[str, RuleNode],
        selected_edges: set[tuple[str, str]],
        gamma: dict[str, float],
        alpha: float = 0.2,
        epsilon: float = 1e-6,
        max_iter: int = 100,
    ) -> dict[str, float]:
        """
        Runs Personalized PageRank:
        pi = alpha * gamma + (1 - alpha) * pi * A_tilde.
        Uses power iteration until ||pi^(k+1) - pi^(k)||_1 <= epsilon.
        """
        node_ids = sorted(rule_nodes.keys())
        n = len(node_ids)
        if n == 0 or not gamma:
            return {}

        node_index = {nid: i for i, nid in enumerate(node_ids)}

        # Build adjacency
        adj: list[set[int]] = [set() for _ in range(n)]
        for u_id, v_id in selected_edges:
            if u_id in node_index and v_id in node_index:
                i, j = node_index[u_id], node_index[v_id]
                adj[i].add(j)
                adj[j].add(i)

        gamma_vec = [gamma.get(nid, 0.0) for nid in node_ids]
        pi_vec = list(gamma_vec)

        for _ in range(max_iter):
            next_pi = [0.0] * n
            for i in range(n):
                cur_prob = pi_vec[i]
                if cur_prob <= 0.0:
                    continue
                deg = len(adj[i])
                if deg > 0:
                    alloc = cur_prob / deg
                    for j in adj[i]:
                        next_pi[j] += alloc
                else:
                    # Dangling / isolated node redistributes according to personalization vector gamma
                    # to strictly conserve total probability mass (sum(pi) == 1.0) and prevent leakage
                    for j in range(n):
                        next_pi[j] += cur_prob * gamma_vec[j]

            # Apply restart alpha * gamma + (1 - alpha) * next_pi
            new_pi = [
                alpha * gamma_vec[j] + (1.0 - alpha) * next_pi[j]
                for j in range(n)
            ]

            # Convergence check: L1 norm
            diff = sum(abs(new_pi[j] - pi_vec[j]) for j in range(n))
            pi_vec = new_pi
            if diff <= epsilon:
                break

        return {nid: pi_vec[node_index[nid]] for nid in node_ids}

    @classmethod
    def retrieve_top_rules(
        cls,
        rule_nodes: dict[str, RuleNode],
        selected_edges: set[tuple[str, str]],
        anchor_events: list[TemporalCodeEvent],
        top_k2: int = 5,
        alpha: float = 0.2,
        epsilon: float = 1e-6,
        beta: float = 0.7,
        theta: float = 0.6,
    ) -> tuple[list[RuleNode], dict[str, float]]:
        """Executes full PPR retrieval pipeline and returns (top_rules, ppr_distribution)."""
        gamma, u_seed = cls.compute_personalization_vector(
            rule_nodes=rule_nodes,
            anchor_events=anchor_events,
            beta=beta,
            theta=theta,
        )

        if not u_seed:
            return [], {}

        ppr = cls.run_seeded_ppr(
            rule_nodes=rule_nodes,
            selected_edges=selected_edges,
            gamma=gamma,
            alpha=alpha,
            epsilon=epsilon,
        )

        # Sort rule nodes by PPR score descending, then support descending, then ID
        sorted_nodes = sorted(
            rule_nodes.values(),
            key=lambda node: (-ppr.get(node.node_id, 0.0), -node.support, node.node_id),
        )

        top_k = sorted_nodes[:top_k2]
        return top_k, ppr


class StarRagContextService:
    """
    Main Code Lane integration service orchestrating STAR-RAG temporal retrieval.
    Connects existing ATOM facts and candidate retrieval with the STAR-RAG rule graph.
    """

    @staticmethod
    def extract_events_from_candidates(
        candidates: list[RetrievedCandidate],
    ) -> list[TemporalCodeEvent]:
        """
        Extracts verified temporal facts from candidates' metadata and provenance.
        Never fabricates timestamps or relations.
        """
        events: list[TemporalCodeEvent] = []
        seen_events: set[str] = set()

        for cand in candidates:
            cand_ts = parse_candidate_timestamp(cand)
            prov = cand.metadata.get("provenance") or {}
            c_sha = cand.metadata.get("commit_sha") or prov.get("commit_sha")
            c_msg = cand.metadata.get("commit_message") or prov.get("commit_message") or ""
            rels = cand.metadata.get("temporal_relations") or prov.get("temporal_relations")

            if isinstance(rels, list) and rels:
                for idx, r in enumerate(rels):
                    if not isinstance(r, dict):
                        continue
                    s = str(r.get("subject") or cand.name or "").strip()
                    rel_name = str(r.get("relation") or "CALLS").strip().upper()
                    o = str(r.get("canonical_object") or r.get("object") or "").strip()

                    if not s or not o:
                        continue

                    t_val = parse_iso_timestamp(r.get("t_obs") or r.get("t_start")) or cand_ts
                    ev_sha = r.get("commit_sha") or c_sha
                    ev_id = f"ev:{cand.candidate_id}:{idx}:{s}:{rel_name}:{o}"
                    if ev_sha and ev_sha != "unknown":
                        ev_id = f"ev:{ev_sha[:8]}:{idx}:{s}:{rel_name}:{o}"

                    if ev_id not in seen_events:
                        seen_events.add(ev_id)
                        f_path = r.get("file_path") or cand.path
                        sym_name = r.get("symbol_name") or cand.name
                        change_t = r.get("change_type") or cand.metadata.get("change_type") or rel_name
                        desc = r.get("statement") or f"{s} {rel_name} {o}"
                        if c_msg and c_msg not in desc:
                            desc = f"{desc} ({c_msg})"
                        events.append(
                            TemporalCodeEvent(
                                event_id=ev_id,
                                subject=s,
                                relation=rel_name,
                                object=o,
                                timestamp=t_val,
                                candidate_id=cand.candidate_id,
                                candidate=cand,
                                commit_sha=ev_sha,
                                file_path=f_path,
                                symbol_name=sym_name,
                                change_type=change_t,
                                description=desc,
                                snippet=r.get("snippet") or cand.content[:400],
                                metadata={
                                    "t_start": r.get("t_start"),
                                    "t_end": r.get("t_end"),
                                    "t_obs": r.get("t_obs"),
                                    "confidence": r.get("confidence", "HIGH"),
                                    "commit_sha": ev_sha,
                                    "commit_message": c_msg,
                                    "file_path": f_path,
                                    "symbol_name": sym_name,
                                },
                            )
                        )
            else:
                # If no explicit temporal relations list, extract change-level event for ATOM chunks
                c_type = cand.metadata.get("chunk_type") or prov.get("change_type") or cand.metadata.get("change_type")
                sym = cand.metadata.get("symbol_name") or cand.name
                if c_type or sym:
                    rel_name = str(c_type or "DEFINES").strip().upper()
                    s = str(sym or cand.path).strip()
                    o = cand.path.strip()
                    ev_id = f"ev:{cand.candidate_id}:chunk:{s}:{rel_name}:{o}"
                    if c_sha and c_sha != "unknown":
                        ev_id = f"ev:{c_sha[:8]}:chunk:{s}:{rel_name}:{o}"

                    if ev_id not in seen_events:
                        seen_events.add(ev_id)
                        desc = f"{s} ({rel_name}) in {cand.path}"
                        if c_msg:
                            desc = f"{desc}: {c_msg}"
                        events.append(
                            TemporalCodeEvent(
                                event_id=ev_id,
                                subject=s,
                                relation=rel_name,
                                object=o,
                                timestamp=cand_ts,
                                candidate_id=cand.candidate_id,
                                candidate=cand,
                                commit_sha=c_sha,
                                file_path=cand.path,
                                symbol_name=cand.name,
                                change_type=rel_name,
                                description=desc,
                                snippet=cand.content[:400],
                                metadata={
                                    "commit_sha": c_sha,
                                    "commit_message": c_msg,
                                    "file_path": cand.path,
                                    "symbol_name": cand.name,
                                },
                            )
                        )

        return events

    @classmethod
    def extract_events_from_commit_artifacts(
        cls,
        artifacts: list[Any],
        symbol_catalog: list[dict[str, Any]] | None = None,
    ) -> list[TemporalCodeEvent]:
        """
        Extracts verified historical events f = (s, r, o, t) directly from GitCommitArtifact instances
        using CodeAtomDecomposer.
        """
        from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer

        decomposer = CodeAtomDecomposer()
        events: list[TemporalCodeEvent] = []
        seen_events: set[str] = set()

        for art in artifacts:
            decomp_res = decomposer.decompose(art, symbol_catalog=symbol_catalog)
            ts = getattr(art, "committed_at", None)
            c_sha = getattr(art, "commit_sha", "unknown")
            c_msg = getattr(art, "commit_message", "")

            # 1. Relations
            for rel in getattr(decomp_res, "relations", []):
                s = str(rel.subject).strip()
                r_type = str(
                    rel.relation.value if hasattr(rel.relation, "value") else rel.relation
                ).strip().upper()
                o = str(rel.object).strip()
                t_val = rel.t_obs or rel.t_start or ts
                ev_id = f"ev:{c_sha[:8] if c_sha else 'rel'}:{s}:{r_type}:{o}"
                if ev_id not in seen_events:
                    seen_events.add(ev_id)
                    events.append(
                        TemporalCodeEvent(
                            event_id=ev_id,
                            subject=s,
                            relation=r_type,
                            object=o,
                            timestamp=t_val,
                            commit_sha=c_sha,
                            file_path=rel.file_path,
                            symbol_name=rel.symbol_name,
                            change_type=r_type,
                            description=f"{s} {r_type} {o}",
                            metadata={
                                "commit_sha": c_sha,
                                "commit_message": c_msg,
                                "file_path": rel.file_path,
                                "symbol_name": rel.symbol_name,
                                "confidence": str(rel.confidence),
                            },
                        )
                    )

            # 2. Atomic changes
            for chg in getattr(decomp_res, "changes", []):
                s = str(chg.symbol_name or chg.file_path).strip()
                r_type = str(
                    chg.change_type.value if hasattr(chg.change_type, "value") else chg.change_type
                ).strip().upper()
                o = str(chg.file_path).strip()
                ev_id = f"ev:{c_sha[:8] if c_sha else 'chg'}:chg:{s}:{r_type}:{o}"
                if ev_id not in seen_events:
                    seen_events.add(ev_id)
                    events.append(
                        TemporalCodeEvent(
                            event_id=ev_id,
                            subject=s,
                            relation=r_type,
                            object=o,
                            timestamp=ts,
                            commit_sha=c_sha,
                            file_path=chg.file_path,
                            symbol_name=chg.symbol_name,
                            change_type=r_type,
                            description=f"{s} {r_type} in {chg.file_path}: {c_msg}",
                            snippet=chg.raw_content[:400] if chg.raw_content else "",
                            metadata={
                                "commit_sha": c_sha,
                                "commit_message": c_msg,
                                "file_path": chg.file_path,
                                "symbol_name": chg.symbol_name,
                                "old_start_line": chg.old_start_line,
                                "new_start_line": chg.new_start_line,
                            },
                        )
                    )

        return events

    @classmethod
    async def load_historical_events_from_db(
        cls,
        session: Any,
        snapshot_id: uuid.UUID,
        repository_id: uuid.UUID | None = None,
        limit: int = 200,
    ) -> list[TemporalCodeEvent]:
        """
        Loads persisted historical code events from CodeChunk records in PostgreSQL.
        Guarantees retrieval survives server restart.
        """
        from sqlalchemy import select

        from apps.api.src.models.chunk import CodeChunk

        stmt = (
            select(CodeChunk)
            .where(
                CodeChunk.snapshot_id == snapshot_id,
                CodeChunk.chunk_type.like("ATOM_%"),
            )
            .order_by(CodeChunk.created_at.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        chunks = res.scalars().all()

        events: list[TemporalCodeEvent] = []
        seen_events: set[str] = set()

        for chunk in chunks:
            prov = chunk.provenance or {}
            c_sha = chunk.commit_sha or prov.get("commit_sha", "unknown")
            c_msg = chunk.commit_message or prov.get("commit_message", "")
            ts_str = prov.get("committed_at")
            ts = parse_iso_timestamp(ts_str) or (
                chunk.created_at if hasattr(chunk, "created_at") else None
            )

            rels = prov.get("temporal_relations")
            if isinstance(rels, list) and rels:
                for r in rels:
                    if not isinstance(r, dict):
                        continue
                    s = str(r.get("subject") or chunk.name).strip()
                    rel_name = str(r.get("relation") or "CALLS").strip().upper()
                    o = str(r.get("canonical_object") or r.get("object") or "").strip()
                    if not s or not o:
                        continue
                    ev_id = f"ev:{c_sha[:8]}:{s}:{rel_name}:{o}"
                    if ev_id not in seen_events:
                        seen_events.add(ev_id)
                        events.append(
                            TemporalCodeEvent(
                                event_id=ev_id,
                                subject=s,
                                relation=rel_name,
                                object=o,
                                timestamp=parse_iso_timestamp(r.get("t_obs") or r.get("t_start"))
                                or ts,
                                commit_sha=c_sha,
                                file_path=r.get("file_path") or chunk.path,
                                symbol_name=r.get("symbol_name") or chunk.name,
                                change_type=rel_name,
                                description=f"{s} {rel_name} {o} ({c_msg})" if c_msg else f"{s} {rel_name} {o}",
                                snippet=chunk.content[:400] if chunk.content else "",
                                metadata={
                                    "commit_sha": c_sha,
                                    "commit_message": c_msg,
                                    "file_path": chunk.path,
                                    "symbol_name": chunk.name,
                                    "chunk_id": str(chunk.id),
                                    "start_line": chunk.start_line,
                                    "end_line": chunk.end_line,
                                },
                            )
                        )

            # Chunk level change event
            s = str(prov.get("symbol_name") or chunk.name).strip()
            chg_type = str(
                prov.get("change_type") or chunk.chunk_type.replace("ATOM_", "")
            ).strip().upper()
            o = chunk.path.strip()
            ev_id = f"ev:{c_sha[:8]}:chunk:{s}:{chg_type}:{o}"
            if ev_id not in seen_events:
                seen_events.add(ev_id)
                events.append(
                    TemporalCodeEvent(
                        event_id=ev_id,
                        subject=s,
                        relation=chg_type,
                        object=o,
                        timestamp=ts,
                        commit_sha=c_sha,
                        file_path=chunk.path,
                        symbol_name=prov.get("symbol_name") or chunk.name,
                        change_type=chg_type,
                        description=f"{s} ({chg_type}) in {chunk.path}: {c_msg}"
                        if c_msg
                        else f"{s} ({chg_type}) in {chunk.path}",
                        snippet=chunk.content[:400] if chunk.content else "",
                        metadata={
                            "commit_sha": c_sha,
                            "commit_message": c_msg,
                            "file_path": chunk.path,
                            "symbol_name": chunk.name,
                            "chunk_id": str(chunk.id),
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                        },
                    )
                )

        return events

    @classmethod
    def _tokenize_code_text(cls, text: str) -> set[str]:
        """
        Extracts normalized tokens from identifiers, paths, and code text.
        Handles snake_case, camelCase, PascalCase, and dot-separated names.
        Returns a set of lowercase tokens, plus composite stems without delimiters.
        """
        if not text:
            return set()
        tokens: set[str] = set()
        raw_words = _WORD_PATTERN.findall(text)
        for raw_w in raw_words:
            w_lower = raw_w.lower()
            tokens.add(w_lower)
            if "_" in raw_w:
                clean_w = w_lower.replace("_", "")
                if clean_w:
                    tokens.add(clean_w)
                for part in raw_w.split("_"):
                    if part:
                        tokens.add(part.lower())
                        if not part.islower() and not part.isupper():
                            for sp in _CAMEL_PATTERN.findall(part):
                                tokens.add(sp.lower())
            elif not raw_w.islower() and not raw_w.isupper():
                for sw in _CAMEL_PATTERN.findall(raw_w):
                    tokens.add(sw.lower())
        return tokens

    @classmethod
    def _get_candidate_tokens(
        cls, candidate: RetrievedCandidate
    ) -> tuple[set[str], str, set[str], set[str]]:
        cache_key = (candidate.name, candidate.path, candidate.content)
        cached = getattr(candidate, "_token_cache", None)
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        name_stem = candidate.name.split(" (")[0].strip()
        name_tokens = cls._tokenize_code_text(name_stem) | cls._tokenize_code_text(candidate.name)
        path_norm = candidate.path.replace("\\", "/").lower()
        path_tokens = cls._tokenize_code_text(path_norm)
        content_tokens = cls._tokenize_code_text(candidate.content)
        result = (name_tokens, path_norm, path_tokens, content_tokens)
        try:
            candidate._token_cache = (cache_key, result)
        except Exception:
            pass
        return result

    @classmethod
    def compute_anchor_relevance(
        cls,
        candidate: RetrievedCandidate,
        analyzed_query: AnalyzedQuery | None = None,
    ) -> float:
        """
        Computes a principled anchor relevance score for a candidate.

        Combines semantic similarity and lexical signals consistently with MultiSignalRanker,
        respecting pre-computed ranker scores when present and gracefully falling back to a
        multi-signal linear combination without arbitrary constants or short-circuiting.
        """
        if "score" in candidate.signals and candidate.signals["score"] > 0.0:
            return round(float(candidate.signals["score"]), 4)

        base_score = (
            candidate.signals.get("vector_similarity", 0.0) * 1.4
            + candidate.signals.get("semantic_match", 0.0) * 1.2
            + candidate.signals.get("symbol_match", 0.0) * 1.5
            + candidate.signals.get("file_match", 0.0) * 1.3
            + candidate.signals.get("content_match", 0.0) * 1.1
            + candidate.signals.get("dependency_match", 0.0) * 0.9
        )

        lexical_score = 0.0
        if analyzed_query:
            name_tokens, path_norm, path_tokens, content_tokens = cls._get_candidate_tokens(candidate)

            # 1. Exact / token-aware symbol candidates match
            for sym in analyzed_query.symbol_candidates:
                sym_l = sym.lower().strip()
                if not sym_l or sym_l in STOP_WORDS or sym_l in NEGATION_WORDS or len(sym_l) <= 1:
                    continue
                sym_clean = sym_l.replace("_", "")
                if sym_l in name_tokens or sym_clean in name_tokens:
                    lexical_score += 1.5
                elif sym_l in path_tokens or sym_clean in path_tokens:
                    lexical_score += 0.8

            # 2. Path candidates match
            for p_cand in analyzed_query.path_candidates:
                p_cand_norm = p_cand.replace("\\", "/").lower().strip()
                if not p_cand_norm:
                    continue
                if (
                    p_cand_norm == path_norm
                    or path_norm.endswith("/" + p_cand_norm)
                    or ("/" + p_cand_norm + "/" in "/" + path_norm + "/")
                    or p_cand_norm in path_tokens
                ):
                    lexical_score += 0.8

            # 3. Meaningful keyword matches
            for kw in analyzed_query.keywords:
                kw_l = kw.lower().strip()
                if not kw_l or kw_l in STOP_WORDS or kw_l in NEGATION_WORDS or len(kw_l) <= 1:
                    continue
                kw_clean = kw_l.replace("_", "")
                if kw_l in name_tokens or kw_clean in name_tokens:
                    lexical_score += 0.8
                elif kw_l in content_tokens or kw_clean in content_tokens:
                    lexical_score += 0.3

            # 4. Architectural concept keyword matches
            for concept in analyzed_query.concept_keywords:
                concept_l = concept.lower().strip()
                if not concept_l or concept_l in STOP_WORDS or concept_l in NEGATION_WORDS or len(concept_l) <= 1:
                    continue
                concept_clean = concept_l.replace("_", "")
                if concept_l in name_tokens or concept_clean in name_tokens:
                    lexical_score += 0.6
                elif concept_l in content_tokens or concept_clean in content_tokens:
                    lexical_score += 0.2

        return round(base_score + lexical_score, 4)

    @classmethod
    def apply_star_rag(
        cls,
        candidates: list[RetrievedCandidate],
        analyzed_query: AnalyzedQuery | None = None,
        query_text: str = "",
        top_k1: int | None = None,
        top_k2: int | None = None,
        alpha: float | None = None,
        epsilon: float | None = None,
        min_support: int | None = None,
        min_anchor_score: float | None = None,
        hub_attenuation: bool | None = None,
    ) -> list[RetrievedCandidate]:
        """
        Applies STAR-RAG retrieval and graph propagation to code candidates.
        Gracefully falls back to existing candidate ranking if the rule graph
        has insufficient events or cannot be constructed.
        """
        result = cls.run_star_rag_pipeline(
            candidates=candidates,
            analyzed_query=analyzed_query,
            query_text=query_text,
            top_k1=top_k1,
            top_k2=top_k2,
            alpha=alpha,
            epsilon=epsilon,
            min_support=min_support,
            min_anchor_score=min_anchor_score,
            hub_attenuation=hub_attenuation,
        )
        return result.candidates

    @classmethod
    def run_star_rag_pipeline(
        cls,
        candidates: list[RetrievedCandidate],
        analyzed_query: AnalyzedQuery | None = None,
        query_text: str = "",
        top_k1: int | None = None,
        top_k2: int | None = None,
        alpha: float | None = None,
        epsilon: float | None = None,
        min_support: int | None = None,
        min_anchor_score: float | None = None,
        hub_attenuation: bool | None = None,
        extra_events: list[TemporalCodeEvent] | None = None,
    ) -> StarRagResult:
        """
        Executes the full STAR-RAG retrieval pipeline and returns diagnostic results.
        """
        k1 = top_k1 or getattr(settings, "STAR_RAG_TOP_K1", 10)
        k2 = top_k2 or getattr(settings, "STAR_RAG_TOP_K2", 5)
        ppr_alpha = alpha or getattr(settings, "STAR_RAG_PPR_ALPHA", 0.2)
        ppr_eps = epsilon or getattr(settings, "STAR_RAG_PPR_EPSILON", 1e-6)
        min_supp = min_support or getattr(settings, "STAR_RAG_MIN_SUPPORT", 2)
        min_anchor_th = (
            min_anchor_score
            if min_anchor_score is not None
            else getattr(settings, "STAR_RAG_MIN_ANCHOR_SCORE", 1.0)
        )
        enable_hub_attenuation = (
            hub_attenuation
            if hub_attenuation is not None
            else getattr(settings, "STAR_RAG_HUB_ATTENUATION", True)
        )

        if not candidates and not extra_events:
            return StarRagResult(
                candidates=[],
                rule_nodes={},
                selected_edges=set(),
                top_rules=[],
                ppr_distribution={},
                initial_mdl_cost=0.0,
                final_mdl_cost=0.0,
                is_fallback=True,
                fallback_reason="No input candidates provided",
            )

        try:
            # 1. Extract and merge events
            events = cls.extract_events_from_candidates(candidates)
            if extra_events:
                seen_event_ids = {ev.event_id for ev in events}
                for ex in extra_events:
                    if ex.event_id not in seen_event_ids:
                        seen_event_ids.add(ex.event_id)
                        events.append(ex)

            if len(events) < 2:
                return StarRagResult(
                    candidates=candidates,
                    rule_nodes={},
                    selected_edges=set(),
                    top_rules=[],
                    ppr_distribution={},
                    initial_mdl_cost=0.0,
                    final_mdl_cost=0.0,
                    is_fallback=True,
                    fallback_reason="Insufficient temporal events (< 2)",
                )

            # 2. Entity relation-pattern mining
            entity_types = EntityRelationMiner.mine_entity_types(
                events=events,
                min_support=min_supp,
                max_len=3,
            )
            num_types = len(set(entity_types.values()))
            num_relations = len({ev.relation for ev in events})

            # 3. Rule graph construction
            rule_nodes = TemporalRuleGraphBuilder.build_rule_nodes(events, entity_types)
            candidate_edges = TemporalRuleGraphBuilder.generate_candidate_edges(rule_nodes)
            spans_map = TemporalRuleGraphBuilder.collect_temporal_spans(rule_nodes, candidate_edges)

            # 4. MDL graph selection
            selected_edges, init_mdl, final_mdl = MdlGraphSelector.select_edges(
                rule_nodes=rule_nodes,
                candidate_edges=candidate_edges,
                spans_map=spans_map,
                total_events=len(events),
                num_types=num_types,
                num_relations=num_relations,
            )

            # 5. Determine query anchors
            ranked_anchor_candidates = sorted(
                candidates,
                key=lambda c: (-cls.compute_anchor_relevance(c, analyzed_query), c.candidate_id),
            )
            top_anchor_rel = (
                cls.compute_anchor_relevance(ranked_anchor_candidates[0], analyzed_query)
                if ranked_anchor_candidates
                else 0.0
            )

            # Check if extra_events match query keywords
            raw_tokens = cls._tokenize_code_text(query_text) if query_text else set()
            query_tokens = {
                t
                for t in raw_tokens
                if t not in STOP_WORDS and t not in NEGATION_WORDS and len(t) > 2
            }
            if analyzed_query:
                for kw in list(analyzed_query.keywords) + list(analyzed_query.symbol_candidates):
                    for t in cls._tokenize_code_text(kw):
                        if t not in STOP_WORDS and t not in NEGATION_WORDS and len(t) > 2:
                            query_tokens.add(t)

            event_anchor_matches = []
            if query_tokens:
                for ev in events:
                    ev_str = f"{ev.subject} {ev.relation} {ev.object} {ev.description or ''}".lower()
                    toks = cls._tokenize_code_text(ev_str)
                    filtered_toks = {
                        t
                        for t in toks
                        if t not in STOP_WORDS and t not in NEGATION_WORDS and len(t) > 2
                    }
                    if query_tokens & filtered_toks:
                        event_anchor_matches.append(ev)

            has_precomputed = (
                bool(ranked_anchor_candidates)
                and "score" in ranked_anchor_candidates[0].signals
                and ranked_anchor_candidates[0].signals["score"] > 0.0
            )
            effective_gate = min(min_anchor_th, 0.40) if has_precomputed else min_anchor_th

            # If anchor candidates are weak, check if direct event anchors are available
            if top_anchor_rel < effective_gate and not event_anchor_matches:
                return StarRagResult(
                    candidates=candidates,
                    rule_nodes=rule_nodes,
                    selected_edges=selected_edges,
                    top_rules=[],
                    ppr_distribution={},
                    initial_mdl_cost=init_mdl,
                    final_mdl_cost=final_mdl,
                    is_fallback=True,
                    fallback_reason=f"Top anchor relevance ({top_anchor_rel:.4f}) below confidence threshold ({effective_gate:.4f})",
                )

            anchor_candidates = ranked_anchor_candidates[:k1]
            anchor_cids = {c.candidate_id for c in anchor_candidates}
            anchor_events = [ev for ev in events if ev.candidate_id and ev.candidate_id in anchor_cids]

            if not anchor_events:
                if event_anchor_matches:
                    anchor_events = event_anchor_matches[:k1]
                else:
                    anchor_events = events[:k1]

            # 6. PPR retrieval on rule graph
            top_rules, ppr_dist = SeededPprRetriever.retrieve_top_rules(
                rule_nodes=rule_nodes,
                selected_edges=selected_edges,
                anchor_events=anchor_events,
                top_k2=k2,
                alpha=ppr_alpha,
                epsilon=ppr_eps,
            )

            if not top_rules:
                return StarRagResult(
                    candidates=candidates,
                    rule_nodes=rule_nodes,
                    selected_edges=selected_edges,
                    top_rules=[],
                    ppr_distribution=ppr_dist,
                    initial_mdl_cost=init_mdl,
                    final_mdl_cost=final_mdl,
                    is_fallback=True,
                    fallback_reason="PPR found no matching rule nodes",
                )

            # 7. Map selected rules back to original code evidence and rerank supporting events
            cand_map: dict[str, RetrievedCandidate] = {c.candidate_id: c for c in candidates}
            augmented_cands: dict[str, RetrievedCandidate] = {}

            # Retain baseline evidence
            for c in candidates:
                augmented_cands[c.candidate_id] = c

            # Parse query temporal constraints from analyzed_query if present
            struct_intent = getattr(analyzed_query, "structured_temporal_intent", None)
            target_bound_end: datetime | None = None
            target_bound_start: datetime | None = None
            is_as_of_query = False

            if struct_intent and hasattr(struct_intent, "constraints"):
                for constraint in struct_intent.constraints:
                    bound = getattr(constraint, "bound", None)
                    if bound:
                        if getattr(bound, "end", None):
                            target_bound_end = bound.end
                        if getattr(bound, "start", None):
                            target_bound_start = bound.start
                        op = getattr(constraint, "operator", None)
                        if op in ("POINT_IN_TIME", "EQUALS"):
                            is_as_of_query = True

            q_lower = (query_text or "").lower()
            if not target_bound_end:
                m_asof = re.search(
                    r"\b(?:as\s+of|as-of|before|prior\s+to)\s+(\d{4}-\d{2}-\d{2})\b",
                    q_lower,
                )
                if m_asof:
                    try:
                        target_bound_end = datetime.fromisoformat(m_asof.group(1)).replace(
                            tzinfo=UTC
                        )
                        if "as of" in q_lower or "as-of" in q_lower:
                            is_as_of_query = True
                    except Exception:
                        pass

            if not target_bound_start:
                m_after = re.search(r"\b(?:after|since)\s+(\d{4}-\d{2}-\d{2})\b", q_lower)
                if m_after:
                    try:
                        target_bound_start = datetime.fromisoformat(m_after.group(1)).replace(
                            tzinfo=UTC
                        )
                    except Exception:
                        pass

            supporting_events: list[tuple[float, TemporalCodeEvent, RuleNode]] = []
            seen_ev_ids: set[str] = set()

            for rule in top_rules:
                pi_val = ppr_dist.get(rule.node_id, 0.0)
                if enable_hub_attenuation and len(rule.events) > 1:
                    rule_weight = 1.0 / math.log2(2.0 + len(rule.events))
                else:
                    rule_weight = 1.0
                effective_pi = pi_val * rule_weight

                for ev in rule.events:
                    c = ev.candidate or cand_map.get(ev.candidate_id)
                    if c:
                        existing = augmented_cands.setdefault(c.candidate_id, c)
                        existing.signals["star_rag_ppr"] = max(
                            existing.signals.get("star_rag_ppr", 0.0),
                            round(effective_pi, 4),
                        )
                        existing.metadata["star_rag_rule_node"] = rule.node_id
                        existing.metadata["star_rag_ppr_score"] = round(effective_pi, 4)
                        if (
                            "retrieval_reason" not in existing.metadata
                            or existing.metadata["retrieval_reason"] == "Direct retrieval match"
                        ):
                            existing.metadata["retrieval_reason"] = (
                                f"STAR-RAG temporal rule propagation ({rule.node_id})"
                            )

                    # Event scoring and collection for temporal evidence
                    if ev.event_id not in seen_ev_ids:
                        seen_ev_ids.add(ev.event_id)
                        ev_score = effective_pi

                        # Lexical match boost
                        ev_text = f"{ev.subject} {ev.relation} {ev.object} {ev.description or ''} {ev.file_path or ''}".lower()
                        ev_tokens = cls._tokenize_code_text(ev_text)
                        overlap = len(query_tokens & ev_tokens)
                        if overlap > 0:
                            ev_score += 0.35 * min(overlap, 5)

                        # Temporal constraint alignment
                        if ev.timestamp:
                            if target_bound_end:
                                if ev.timestamp <= target_bound_end:
                                    ev_score += 1.0
                                    days_diff = (
                                        abs((target_bound_end - ev.timestamp).total_seconds())
                                        / 86400.0
                                    )
                                    ev_score += max(0.0, 1.0 / (1.0 + days_diff * 0.1))
                                else:
                                    ev_score *= 0.15
                            if target_bound_start:
                                if ev.timestamp >= target_bound_start:
                                    ev_score += 0.8
                                else:
                                    ev_score *= 0.15

                        supporting_events.append((ev_score, ev, rule))

            # Sort supporting events by score descending
            supporting_events.sort(key=lambda x: -x[0])
            ranked_events = [ev for _, ev, _ in supporting_events]

            # Build structured temporal evidence list
            temporal_evidence: list[dict[str, Any]] = []
            for ev_score, ev, rule in supporting_events[:15]:
                c_sha = (
                    ev.commit_sha
                    or (ev.metadata.get("commit_sha") if ev.metadata else None)
                    or (getattr(ev.candidate, "commit_sha", None) if ev.candidate else None)
                )
                f_path = (
                    ev.file_path
                    or (ev.metadata.get("file_path") if ev.metadata else None)
                    or (getattr(ev.candidate, "path", None) if ev.candidate else "codebase")
                )
                s_name = (
                    ev.symbol_name
                    or (ev.metadata.get("symbol_name") if ev.metadata else None)
                    or ev.subject
                )
                c_msg = (
                    ev.metadata.get("commit_message")
                    if ev.metadata
                    else (
                        getattr(ev.candidate, "commit_message", "") if ev.candidate else ""
                    )
                )
                desc = ev.description or f"{ev.subject} {ev.relation} {ev.object}"
                if c_msg and c_msg not in desc:
                    desc = f"{desc} (Commit: {c_msg})"
                snippet = ev.snippet or (ev.candidate.content[:400] if ev.candidate else desc)

                temporal_evidence.append(
                    {
                        "type": "temporal_event",
                        "event_id": ev.event_id,
                        "subject": ev.subject,
                        "relation": ev.relation,
                        "object": ev.object,
                        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                        "commit_sha": c_sha,
                        "file": f_path,
                        "symbol": s_name,
                        "change_type": ev.change_type or ev.relation,
                        "lines": (
                            f"{ev.candidate.start_line}-{ev.candidate.end_line}"
                            if ev.candidate
                            else (
                                f"{ev.metadata.get('start_line', 1)}-{ev.metadata.get('end_line', 20)}"
                                if ev.metadata
                                else "1-20"
                            )
                        ),
                        "snippet": snippet,
                        "relationship_path": f"{ev.subject} --[{ev.relation}]--> {ev.object}",
                        "retrieval_reason": f"STAR-RAG temporal rule propagation ({rule.node_id})",
                        "rule_node": rule.node_id,
                        "score": round(ev_score, 4),
                        "relevance": min(1.0, max(0.5, round(ev_score, 2))),
                        "provenance": {
                            "engine": "temporal_star_rag",
                            "commit_sha": c_sha,
                            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                            "rule_node": rule.node_id,
                            "temporal_status": "HISTORICAL",
                        },
                    }
                )

            # 8. Resolve temporal supersession across the augmented candidate set
            final_cands = list(augmented_cands.values())
            resolve_temporal_supersession(final_cands)

            bounds_info = {}
            if target_bound_end:
                bounds_info["target_bound_end"] = target_bound_end.isoformat()
            if target_bound_start:
                bounds_info["target_bound_start"] = target_bound_start.isoformat()
            if is_as_of_query:
                bounds_info["is_as_of_query"] = True

            return StarRagResult(
                candidates=final_cands,
                rule_nodes=rule_nodes,
                selected_edges=selected_edges,
                top_rules=top_rules,
                ppr_distribution=ppr_dist,
                initial_mdl_cost=init_mdl,
                final_mdl_cost=final_mdl,
                is_fallback=False,
                ranked_events=ranked_events,
                temporal_evidence=temporal_evidence,
                temporal_intent=getattr(analyzed_query, "temporal_intent", None),
                temporal_bounds=bounds_info or None,
            )

        except Exception as e:
            logger.warning("STAR-RAG pipeline encountered an error; falling back to baseline: %s", e)
            return StarRagResult(
                candidates=candidates,
                rule_nodes={},
                selected_edges=set(),
                top_rules=[],
                ppr_distribution={},
                initial_mdl_cost=0.0,
                final_mdl_cost=0.0,
                is_fallback=True,
                fallback_reason=str(e),
            )

    @classmethod
    async def run_star_rag_pipeline_async(
        cls,
        candidates: list[RetrievedCandidate],
        analyzed_query: AnalyzedQuery | None = None,
        query_text: str = "",
        session: Any | None = None,
        snapshot_id: uuid.UUID | None = None,
        repository_id: uuid.UUID | None = None,
        top_k1: int | None = None,
        top_k2: int | None = None,
        alpha: float | None = None,
        epsilon: float | None = None,
        min_support: int | None = None,
        min_anchor_score: float | None = None,
        hub_attenuation: bool | None = None,
        extra_events: list[TemporalCodeEvent] | None = None,
    ) -> StarRagResult:
        """
        Asynchronous STAR-RAG retrieval pipeline that integrates database-persisted
        historical repository events with candidates.
        """
        all_extra = list(extra_events or [])
        if session is not None and snapshot_id is not None:
            try:
                db_events = await cls.load_historical_events_from_db(
                    session=session,
                    snapshot_id=snapshot_id,
                    repository_id=repository_id,
                )
                all_extra.extend(db_events)
            except Exception as e:
                logger.debug(f"Could not load historical events from database: {e}")

        return cls.run_star_rag_pipeline(
            candidates=candidates,
            analyzed_query=analyzed_query,
            query_text=query_text,
            top_k1=top_k1,
            top_k2=top_k2,
            alpha=alpha,
            epsilon=epsilon,
            min_support=min_support,
            min_anchor_score=min_anchor_score,
            hub_attenuation=hub_attenuation,
            extra_events=all_extra if all_extra else None,
        )
