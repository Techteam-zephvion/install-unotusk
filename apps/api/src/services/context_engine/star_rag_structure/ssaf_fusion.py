"""
Semantic-Structural Adaptive Fusion (SSAF) for Structure-Aware STAR-RAG.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).

Adaptively fuses independent candidate-level semantic and structural scores
conditioned on query intent, dynamically balancing the two streams.
"""

from __future__ import annotations

import math

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.types import SSAFFusionResult


class SemanticStructuralAdaptiveFusion:
    """
    Ranks candidates by dynamically fusing semantic and decoupled structural signals:
        Score(c) = beta_c * score_sem(c) + (1 - beta_c) * score_struct(c)
    where beta_c is an adaptive query-conditioned gating parameter.
    """

    def __init__(
        self,
        conflict_threshold: float = 0.40,
        default_beta: float = 0.55,
        temperature: float = 1.0,
        max_structural_weight: float = 0.15,
    ):
        self.conflict_threshold = conflict_threshold
        self.default_beta = default_beta
        self.temperature = max(1e-4, temperature)
        self.max_structural_weight = max_structural_weight

        # Keywords triggering strong structural tracing intent
        self.structural_trigger_keywords = {
            "trace", "caller", "callers", "callee", "callees", "calls", "called",
            "dependency", "dependencies", "depend", "path", "chain", "flow",
            "reach", "reaches", "hierarchy", "graph", "subgraph", "downstream", "upstream",
        }

        # Keywords triggering conceptual/semantic search intent
        self.semantic_trigger_keywords = {
            "explain", "what", "how", "concept", "business", "policy", "purpose",
            "meaning", "describe", "overview", "definition", "role", "validate",
        }

    def _determine_query_structural_bias(
        self,
        query_text: str,
        analyzed_query: AnalyzedQuery | None = None,
    ) -> float:
        """
        Determines structural bias in [-1.0, 1.0].
        Positive values indicate structural tracing intent; negative indicate conceptual semantics.
        """
        q_lower = query_text.lower()
        struct_matches = sum(1 for kw in self.structural_trigger_keywords if kw in q_lower)
        sem_matches = sum(1 for kw in self.semantic_trigger_keywords if kw in q_lower)

        # If query has explicit path or symbol candidates, bump structural affinity
        if analyzed_query:
            if getattr(analyzed_query, "path_candidates", None):
                struct_matches += len(analyzed_query.path_candidates)
            if getattr(analyzed_query, "is_temporal", False):
                struct_matches += 1

        total = struct_matches + sem_matches
        if total == 0:
            return 0.0

        # Returns in [-1.0, 1.0]
        return (struct_matches - sem_matches) / total

    def compute_candidate_semantic_score(self, candidate: RetrievedCandidate) -> float:
        """
        Extracts and normalizes the candidate's semantic signals
        (vector similarity, symbol matches, content matches, lexical density).
        """
        vec_sim = candidate.signals.get("vector_similarity", 0.0)
        sem_match = candidate.signals.get("semantic_match", 0.0)
        sym_match = candidate.signals.get("symbol_match", 0.0)
        content_match = candidate.signals.get("content_match", 0.0)
        file_match = candidate.signals.get("file_match", 0.0)

        # Raw semantic combination
        sem_raw = (
            (vec_sim * 1.5)
            + (sem_match * 1.2)
            + (sym_match * 1.3)
            + (content_match * 1.0)
            + (file_match * 0.8)
        )
        # Normalize into [0.0, 1.0]
        return min(1.0, round(sem_raw / 2.5, 4))

    def compute_candidate_structural_score(self, candidate: RetrievedCandidate) -> float:
        """
        Extracts and normalizes the candidate's structural signals
        from DTP ('dtp_structural') and legacy graph expansion signals.
        """
        dtp_score = candidate.signals.get("dtp_structural")
        if dtp_score is not None:
            return min(1.0, max(0.0, float(dtp_score)))

        # Fallback to legacy graph expansion signals if DTP was bypassed
        legacy_graph = candidate.signals.get("graph_expansion", 0.0)
        legacy_hop2 = candidate.signals.get("graph_expansion_hop2", 0.0)
        raw_struct = (legacy_graph * 1.0) + (legacy_hop2 * 0.7)
        return min(1.0, round(raw_struct, 4))

    def compute_adaptive_beta(
        self,
        sem_score: float,
        struct_score: float,
        structural_bias: float,
    ) -> float:
        """
        Calculates adaptive weighting parameter beta_c in (0.0, 1.0).
        beta_c weights the semantic stream; (1 - beta_c) weights the structural stream.
        """
        # Base logit from default_beta
        # default_beta = 0.55 -> logit_base approx 0.20
        logit = 0.20

        # Adjust logit based on query structural bias:
        # If structural_bias > 0 (e.g. trace), decrease logit -> lower beta -> higher structural weight
        logit -= structural_bias * 1.2

        # Candidate signal modulation:
        # If structural score is zero and candidate is a pure semantic match, preserve semantic
        if struct_score < 0.05 and sem_score > 0.5:
            logit += 1.5
        elif sem_score < 0.05 and struct_score > 0.5:
            # Candidate is purely a structural neighbor with no semantic match (e.g. general utility)
            # Penalize over-dependence on structural hub
            logit -= 0.5

        # Sigmoid gate
        try:
            beta = 1.0 / (1.0 + math.exp(-logit / self.temperature))
        except OverflowError:
            beta = 1.0 if logit > 0 else 0.0

        # Clamp beta within bounded range [0.15, 0.85] to guarantee neither stream is completely silenced
        return max(0.15, min(0.85, round(beta, 4)))

    def fuse_and_rank_candidates(
        self,
        candidates: list[RetrievedCandidate],
        query_text: str,
        analyzed_query: AnalyzedQuery | None = None,
    ) -> tuple[list[RankedCandidate], list[SSAFFusionResult]]:
        """
        Applies SSAF to candidate list, returning sorted RankedCandidates and diagnostic results.
        Preserves baseline ATOM ranking semantics (exact symbol, path, vector, test demotion)
        and adds query-conditioned bounded structural contributions from DTP.
        """
        from apps.api.src.services.context_engine.ranker import MultiSignalRanker

        analyzed = analyzed_query or AnalyzedQuery(raw_query=query_text)
        structural_bias = self._determine_query_structural_bias(query_text, analyzed)
        fusion_results: list[SSAFFusionResult] = []
        ranked_candidates: list[RankedCandidate] = []

        # 1. Deduplicate redundant / overlapping candidates using ATOM logic
        unique_candidates = MultiSignalRanker._deduplicate_candidates(candidates)

        # 2. Compute authoritative baseline ATOM scores and matched reasons
        atom_ranked = MultiSignalRanker.rank_candidates(
            candidates=unique_candidates,
            analyzed_query=analyzed,
            noise_threshold=0.0,
        )
        atom_map: dict[str, RankedCandidate] = {
            r.candidate.candidate_id: r for r in atom_ranked
        }

        for cand in unique_candidates:
            r_atom = atom_map.get(cand.candidate_id)
            score_atom = r_atom.score if r_atom else 0.0
            atom_reasons = list(r_atom.matched_reasons) if r_atom else []

            sem_s = self.compute_candidate_semantic_score(cand)
            struct_s = self.compute_candidate_structural_score(cand)

            beta = self.compute_adaptive_beta(sem_s, struct_s, structural_bias)

            # Conflict detection
            is_conflict = abs(sem_s - struct_s) >= self.conflict_threshold

            # Bounded structural contribution:
            # - If baseline ATOM score is very low (< 0.25), candidate is an irrelevant hub: 0 boost.
            # - If conflict where structural is high but semantic is weak: 0 boost to prevent hub leapfrogging.
            # - Otherwise: scaled contribution bounded by max_structural_weight (default 0.15).
            if score_atom < 0.25:
                struct_boost = 0.0
            elif is_conflict and struct_s > sem_s and sem_s < 0.35:
                struct_boost = 0.0
            else:
                effective_weight = min(self.max_structural_weight, (1.0 - beta) * 0.30)
                struct_boost = round(struct_s * effective_weight, 4)

            fused_score = min(1.0, max(0.0, round(score_atom + struct_boost, 4)))

            explanation: list[str] = list(atom_reasons)
            explanation.append(
                f"SSAF Adaptive Fusion (Score: {fused_score:.2f}, ATOM Base: {score_atom:.2f}, Struct Boost: +{struct_boost:.2f})"
            )
            explanation.append(f"Semantic Stream: {sem_s:.2f} (beta: {beta:.2f})")
            explanation.append(f"Structural DTP Stream: {struct_s:.2f} (weight: {1.0 - beta:.2f})")

            if is_conflict:
                if sem_s > struct_s:
                    explanation.append("Conflict: High semantic match with sparse/disconnected graph topology")
                else:
                    explanation.append("Conflict: Structural graph hub with low semantic relevance")

            if structural_bias > 0.2:
                explanation.append("Structural/Dependency tracing prioritized")
            elif structural_bias < -0.2:
                explanation.append("Conceptual/Semantic search prioritized")

            res = SSAFFusionResult(
                candidate_id=cand.candidate_id,
                candidate_name=cand.name,
                semantic_score=sem_s,
                structural_score=struct_s,
                adaptive_beta=beta,
                fused_score=fused_score,
                is_conflict=is_conflict,
                explanation=explanation,
            )
            fusion_results.append(res)

            ranked_candidates.append(
                RankedCandidate(
                    candidate=cand,
                    score=fused_score,
                    matched_reasons=explanation,
                )
            )

        # Sort descending by fused score, using ATOM score as tie-breaker
        ranked_candidates.sort(
            key=lambda r: (
                r.score,
                atom_map.get(r.candidate.candidate_id).score if atom_map.get(r.candidate.candidate_id) else 0.0,
            ),
            reverse=True,
        )
        fusion_results.sort(key=lambda f: f.fused_score, reverse=True)

        return ranked_candidates, fusion_results
