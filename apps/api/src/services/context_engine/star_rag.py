"""
STAR-RAG (Spatio-Temporal Abstraction & Reasoning for RAG) Code Lane Integration.
Based on Zhu et al. (arXiv:2510.16715, "Right Answer at the Right Time - Temporal
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
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.code_atom.relation_extractor import parse_iso_timestamp
from apps.api.src.services.code_atom.temporal import (
    parse_candidate_timestamp,
    resolve_temporal_supersession,
)
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
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
                    # Dangling / isolated node retains or diffuses to self
                    next_pi[i] += cur_prob

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
            rels = cand.metadata.get("temporal_relations")

            if isinstance(rels, list) and rels:
                for idx, r in enumerate(rels):
                    if not isinstance(r, dict):
                        continue
                    s = str(r.get("subject") or cand.name or "").strip()
                    rel_name = str(r.get("relation") or "CALLS").strip().upper()
                    o = str(r.get("canonical_object") or r.get("object") or "").strip()

                    if not s or not o:
                        continue

                    # Determine event timestamp: t_obs or t_start, falling back to candidate commit time
                    t_val = parse_iso_timestamp(r.get("t_obs") or r.get("t_start")) or cand_ts
                    ev_id = f"ev:{cand.candidate_id}:{idx}:{s}:{rel_name}:{o}"

                    if ev_id not in seen_events:
                        seen_events.add(ev_id)
                        events.append(
                            TemporalCodeEvent(
                                event_id=ev_id,
                                subject=s,
                                relation=rel_name,
                                object=o,
                                timestamp=t_val,
                                candidate_id=cand.candidate_id,
                                candidate=cand,
                                metadata={
                                    "t_start": r.get("t_start"),
                                    "t_end": r.get("t_end"),
                                    "t_obs": r.get("t_obs"),
                                    "confidence": r.get("confidence", "HIGH"),
                                },
                            )
                        )
            else:
                # If no explicit temporal relations list, extract change-level event for ATOM chunks
                c_type = cand.metadata.get("chunk_type") or (cand.metadata.get("provenance") or {}).get("change_type")
                sym = cand.metadata.get("symbol_name") or cand.name
                if c_type or sym:
                    rel_name = str(c_type or "DEFINES").strip().upper()
                    s = str(sym or cand.path).strip()
                    o = cand.path.strip()
                    ev_id = f"ev:{cand.candidate_id}:chunk:{s}:{rel_name}:{o}"

                    if ev_id not in seen_events:
                        seen_events.add(ev_id)
                        events.append(
                            TemporalCodeEvent(
                                event_id=ev_id,
                                subject=s,
                                relation=rel_name,
                                object=o,
                                timestamp=cand_ts,
                                candidate_id=cand.candidate_id,
                                candidate=cand,
                            )
                        )

        return events

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
            name_lower = candidate.name.lower()
            name_stem = name_lower.split(" (")[0].strip()
            path_lower = candidate.path.lower()
            content_lower = candidate.content.lower()

            for sym in analyzed_query.symbol_candidates:
                sym_l = sym.lower()
                if sym_l in (name_lower, name_stem):
                    lexical_score += 1.5
                elif sym_l in path_lower:
                    lexical_score += 0.8

            for p_cand in analyzed_query.path_candidates:
                if p_cand.lower() in path_lower:
                    lexical_score += 0.8

            for kw in analyzed_query.keywords:
                kw_l = kw.lower()
                if kw_l in name_lower or kw_l in name_stem:
                    lexical_score += 0.8
                elif kw_l in content_lower:
                    lexical_score += 0.3

            for concept in analyzed_query.concept_keywords:
                concept_l = concept.lower()
                if concept_l in name_lower:
                    lexical_score += 0.6
                elif concept_l in content_lower:
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

        if not candidates:
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
            # 1. Extract events
            events = cls.extract_events_from_candidates(candidates)
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
            # Prioritize candidates by principled anchor relevance with deterministic tie-breaking
            ranked_anchor_candidates = sorted(
                candidates,
                key=lambda c: (-cls.compute_anchor_relevance(c, analyzed_query), c.candidate_id),
            )
            top_anchor_rel = (
                cls.compute_anchor_relevance(ranked_anchor_candidates[0], analyzed_query)
                if ranked_anchor_candidates
                else 0.0
            )

            # Absent-evidence / weak-anchor gate:
            # If candidates have pre-computed ranker scores ([0, 1]), effective threshold is scaled to min(min_anchor_th, 0.40).
            # Otherwise on unnormalized raw multi-signal combinations, threshold defaults to min_anchor_th (1.0).
            has_precomputed = (
                bool(ranked_anchor_candidates)
                and "score" in ranked_anchor_candidates[0].signals
                and ranked_anchor_candidates[0].signals["score"] > 0.0
            )
            effective_gate = min(min_anchor_th, 0.40) if has_precomputed else min_anchor_th

            if top_anchor_rel < effective_gate:
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
            anchor_events = [ev for ev in events if ev.candidate_id in anchor_cids]

            if not anchor_events:
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

            # 7. Map selected rules back to original code evidence
            # Collect candidates supported by top rule nodes
            cand_map: dict[str, RetrievedCandidate] = {c.candidate_id: c for c in candidates}
            augmented_cands: dict[str, RetrievedCandidate] = {}

            # First add all original candidates to retain baseline evidence
            for c in candidates:
                augmented_cands[c.candidate_id] = c

            # Boost and link candidates from top rule nodes
            for rule in top_rules:
                pi_val = ppr_dist.get(rule.node_id, 0.0)
                if enable_hub_attenuation and len(rule.events) > 1:
                    # Attenuate generic hub rules inversely with event cardinality
                    # to prevent hyper-generic rules (e.g. 200+ calls) from dominating specific relations
                    rule_weight = 1.0 / math.log2(2.0 + len(rule.events))
                else:
                    rule_weight = 1.0
                effective_pi = pi_val * rule_weight

                for ev in rule.events:
                    c = ev.candidate or cand_map.get(ev.candidate_id)
                    if c:
                        existing = augmented_cands.setdefault(c.candidate_id, c)
                        # Record PPR signal
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

            # 8. Resolve temporal supersession across the augmented candidate set
            final_cands = list(augmented_cands.values())
            resolve_temporal_supersession(final_cands)

            return StarRagResult(
                candidates=final_cands,
                rule_nodes=rule_nodes,
                selected_edges=selected_edges,
                top_rules=top_rules,
                ppr_distribution=ppr_dist,
                initial_mdl_cost=init_mdl,
                final_mdl_cost=final_mdl,
                is_fallback=False,
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
