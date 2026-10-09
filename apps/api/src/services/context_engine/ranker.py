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
    def _deduplicate_candidates(
        candidates: list[RetrievedCandidate],
    ) -> list[RetrievedCandidate]:
        """Deduplicates duplicate chunks or overlapping entities in the same file."""
        deduped: dict[str, RetrievedCandidate] = {}

        for cand in candidates:
            # Create a logical deduplication key
            if cand.entity_type == "FILE":
                key = f"file:{cand.file_id}:{cand.path}"
            elif cand.entity_type == "CHUNK" and cand.metadata.get("fingerprint"):
                # Distinct ATOM code-change chunk identified by deterministic fingerprint
                key = f"chunk:atom:{cand.metadata['fingerprint']}"
            elif cand.symbol_id and not cand.metadata.get("commit_sha"):
                # Generic symbol candidate or symbol-mapped generic chunk
                key = f"sym:{cand.symbol_id}"
            elif cand.entity_type == "CHUNK":
                commit_key = cand.metadata.get("commit_sha") or "none"
                key = f"chunk:{cand.file_id}:{cand.path}:{cand.name}:{cand.start_line}:{cand.end_line}:{commit_key}"
            elif cand.entity_type == "DEPENDENCY":
                key = f"dep:{cand.file_id}:{cand.name}:{cand.start_line}"
            else:
                key = cand.candidate_id

            if key not in deduped:
                deduped[key] = cand
            else:
                existing = deduped[key]
                # Merge signals taking the maximum for each signal
                for sig, val in cand.signals.items():
                    existing.signals[sig] = max(existing.signals.get(sig, 0.0), val)
                # Merge metadata
                if cand.metadata:
                    existing.metadata.update(cand.metadata)
                # Keep richer content or preferred entity type (SYMBOL over generic CHUNK)
                if cand.entity_type == "SYMBOL" and existing.entity_type != "SYMBOL":
                    cand.signals = existing.signals
                    cand.metadata.update(existing.metadata)
                    deduped[key] = cand
                elif len(cand.content) > len(existing.content):
                    cand.signals = existing.signals
                    cand.metadata.update(existing.metadata)
                    deduped[key] = cand

        return list(deduped.values())

    @staticmethod
    def rank_candidates(
        candidates: list[RetrievedCandidate],
        analyzed_query: AnalyzedQuery,
        noise_threshold: float = 0.2,
    ) -> list[RankedCandidate]:
        # 1. Deduplicate redundant / overlapping candidates
        unique_candidates = MultiSignalRanker._deduplicate_candidates(candidates)

        ranked: list[RankedCandidate] = []

        for cand in unique_candidates:
            score = 0.0
            reasons: list[str] = []

            # 2. Base signal weights
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

            # 3. Exact name and path matching boost
            name_lower = cand.name.lower()
            name_stem = name_lower.split(" (")[0].strip()
            path_lower = cand.path.lower()
            for sym in analyzed_query.symbol_candidates:
                if sym.lower() in (name_lower, name_stem):
                    score += 1.5
                    reasons.append(f"Exact symbol match for '{sym}'")
                elif sym.lower() in path_lower:
                    score += 0.8

            # 4. Keyword density in name vs content vs commit message
            content_lower = cand.content.lower()
            commit_msg_lower = str(cand.metadata.get("commit_message", "")).lower()
            for kw in analyzed_query.keywords:
                if kw in name_lower or kw in name_stem:
                    score += 0.8
                elif commit_msg_lower and kw in commit_msg_lower:
                    score += 0.5
                    reasons.append(f"Commit message match for '{kw}'")
                elif kw in content_lower:
                    score += 0.3

            # 5. Concept keyword boost
            for concept in analyzed_query.concept_keywords:
                if concept in name_lower:
                    score += 0.6
                    reasons.append(f"Semantic concept match for '{concept}'")
                elif concept in content_lower:
                    score += 0.2

            # Normalize score (capped at 1.0)
            normalized_score = min(1.0, round(score / 3.0, 2))

            ranked.append(
                RankedCandidate(
                    candidate=cand,
                    score=normalized_score,
                    matched_reasons=reasons,
                )
            )

        # Sort descending by score
        ranked.sort(key=lambda r: r.score, reverse=True)

        # 6. Filter out negligible relevance candidates (noise threshold)
        # Ensure we keep at least 3 candidates (floor guarantee) if candidates exist
        if len(ranked) > 3:
            filtered = [r for r in ranked if r.score >= noise_threshold]
            if len(filtered) >= 3:
                return filtered
            return ranked[:3]

        return ranked
