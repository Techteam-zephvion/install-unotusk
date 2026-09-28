from dataclasses import dataclass

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


@dataclass
class RankedCandidate:
    candidate: RetrievedCandidate
    score: float
    matched_reasons: list[str]


class MultiSignalRanker:
    @staticmethod
    def rank_candidates(
        candidates: list[RetrievedCandidate],
        analyzed_query: AnalyzedQuery,
    ) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []

        for cand in candidates:
            score = 0.0
            reasons: list[str] = []

            # 1. Base signal weights
            for sig, val in cand.signals.items():
                if sig == "symbol_match":
                    score += val * 1.5
                    reasons.append(f"Symbol match ({val})")
                elif sig == "file_match":
                    score += val * 1.3
                    reasons.append(f"Path match ({val})")
                elif sig == "content_match":
                    score += val * 1.1
                    reasons.append("Code content text match")
                elif sig == "vector_similarity":
                    score += val * 1.4
                    reasons.append(f"Vector semantic similarity ({round(val, 2)})")
                elif sig == "semantic_match":
                    score += val * 1.2
                    reasons.append(f"Semantic concept match ({val})")
                elif sig == "dependency_match":
                    score += val * 0.9
                    reasons.append("Dependency import match")
                elif sig == "graph_expansion":
                    score += val * 0.7
                    reasons.append("Graph relationship neighbor")
                elif sig == "graph_expansion_hop2":
                    score += val * 0.5
                    reasons.append("Graph transitive 2-hop neighbor")

            # 2. Exact name matching boost
            name_lower = cand.name.lower()
            path_lower = cand.path.lower()
            for sym in analyzed_query.symbol_candidates:
                if sym.lower() == name_lower:
                    score += 1.5
                    reasons.append(f"Exact symbol match for '{sym}'")
                elif sym.lower() in path_lower:
                    score += 0.8

            # 3. Keyword density in content
            content_lower = cand.content.lower()
            for kw in analyzed_query.keywords:
                if kw in name_lower:
                    score += 0.8
                elif kw in content_lower:
                    score += 0.3

            # 4. Concept keyword boost
            for concept in analyzed_query.concept_keywords:
                if concept in name_lower:
                    score += 0.6
                    reasons.append(f"Semantic concept match for '{concept}'")
                elif concept in content_lower:
                    score += 0.2

            # Normalize score (capped at 1.0 for UI display)
            normalized_score = min(1.0, round(score / 3.0, 2))
            if normalized_score < 0.1:
                normalized_score = 0.1

            ranked.append(
                RankedCandidate(
                    candidate=cand,
                    score=normalized_score,
                    matched_reasons=reasons,
                )
            )

        # Sort descending by score
        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked
