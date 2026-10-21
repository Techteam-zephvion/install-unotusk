from dataclasses import dataclass

from apps.api.src.services.code_atom.temporal import resolve_temporal_supersession
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

                # Merge metadata with provenance preservation
                if cand.metadata:
                    cand_hop = cand.metadata.get("relationship_hop")
                    exist_hop = existing.metadata.get("relationship_hop")
                    cand_path = cand.metadata.get("relationship_path")
                    exist_path = existing.metadata.get("relationship_path")

                    all_alts = list(existing.metadata.get("alternative_paths", []))
                    for p in cand.metadata.get("alternative_paths", []):
                        if p not in all_alts:
                            all_alts.append(p)

                    if cand_hop is not None and (exist_hop is None or cand_hop < exist_hop):
                        # cand has shorter hop
                        if exist_path and exist_path != cand_path and exist_path not in all_alts:
                            all_alts.append(exist_path)
                        existing.metadata.update(cand.metadata)
                        existing.metadata["alternative_paths"] = all_alts
                    elif exist_hop is not None and cand_hop is not None and cand_hop >= exist_hop:
                        # existing has equal or shorter hop
                        if cand_path and cand_path != exist_path and cand_path not in all_alts:
                            all_alts.append(cand_path)
                        for k, v in cand.metadata.items():
                            if (
                                k
                                not in (
                                    "relationship_hop",
                                    "relationship_path",
                                    "relationship_type",
                                    "connected_from",
                                    "retrieval_reason",
                                    "alternative_paths",
                                )
                                and k not in existing.metadata
                            ):
                                existing.metadata[k] = v
                        existing.metadata["alternative_paths"] = all_alts

                    # Merge and deduplicate temporal relations across merged candidates
                    all_existing_rels = existing.metadata.get("temporal_relations") or []
                    cand_rels = cand.metadata.get("temporal_relations") or []
                    if cand_rels:
                        merged_rels = list(all_existing_rels)
                        existing_keys = {
                            (
                                (r.get("canonical_subject") or r.get("subject", "")).lower(),
                                str(r.get("relation", "")).lower(),
                                (r.get("canonical_object") or r.get("object", "")).lower(),
                            )
                            for r in all_existing_rels
                            if isinstance(r, dict)
                        }
                        for r in cand_rels:
                            if isinstance(r, dict):
                                k = (
                                    (r.get("canonical_subject") or r.get("subject", "")).lower(),
                                    str(r.get("relation", "")).lower(),
                                    (r.get("canonical_object") or r.get("object", "")).lower(),
                                )
                                if k not in existing_keys:
                                    existing_keys.add(k)
                                    merged_rels.append(r)
                            elif r not in merged_rels:
                                merged_rels.append(r)
                        existing.metadata["temporal_relations"] = merged_rels

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

        # 2. Resolve temporal supersession across candidates
        resolve_temporal_supersession(unique_candidates)

        intermediate: list[tuple[float, float, RetrievedCandidate, list[str]]] = []

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
                elif sig.startswith("graph_expansion_hop"):
                    try:
                        hop_num = int(sig.replace("graph_expansion_hop", ""))
                    except ValueError:
                        hop_num = 3
                    weight_mult = max(0.2, round(0.5 * (0.75 ** (hop_num - 2)), 2))
                    score += val * weight_mult
                    reasons.append(f"Graph transitive {hop_num}-hop neighbor")

            # 2b. Add detailed relationship reason if available
            rel_type = cand.metadata.get("relationship_type")
            rel_hop = cand.metadata.get("relationship_hop")
            conn_from = cand.metadata.get("connected_from")
            if rel_type and rel_hop and rel_hop > 0:
                conn_desc = f" from '{conn_from}'" if conn_from else ""
                reasons.append(f"Connected {rel_type.lower()} (hop {rel_hop}){conn_desc}")

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
            for path_cand in analyzed_query.path_candidates:
                if path_cand.lower() in path_lower:
                    score += 0.8
                    reasons.append(f"Path candidate match for '{path_cand}'")

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

            # 5b. Test/mock/fixture demotion when query is not asking for tests
            is_test_query = any(k in ("test", "tests", "mock", "mocks", "fixture", "fixtures") for k in analyzed_query.keywords)
            path_normalized = path_lower.replace("\\", "/")
            is_test_file = any(
                part in path_normalized
                for part in ("/tests/", "/test/", "/mocks/", "/fixtures/", "tests/", "mocks/", "fixtures/")
            ) or path_normalized.split("/")[-1].startswith("test_") or "_test." in path_normalized
            if is_test_file and not is_test_query:
                score *= 0.7
                reasons.append("Test/mock file demoted for non-test query")


            # 6. Temporal adjustments based on query intent and code change lifecycle
            if not analyzed_query.is_temporal:
                # Current-state query: prioritize current active implementation, demote superseded and deleted
                if cand.metadata.get("is_deleted"):
                    score *= 0.15
                    reasons.append("Deleted code (demoted for current-state query)")
                elif cand.metadata.get("is_superseded"):
                    score *= 0.4
                    reasons.append("Historical superseded change (demoted for current-state query)")
                elif cand.metadata.get("is_ended_relation"):
                    score *= 0.2
                    reasons.append("Ended historical relation (demoted for current-state query)")
                elif cand.metadata.get("has_superseded_versions"):
                    score += 0.4
                    reasons.append("Latest active implementation")
            else:
                # Temporal / evolution query: highlight history, commit evidence, and change lineage
                if cand.metadata.get("commit_sha") or cand.metadata.get("committed_at"):
                    score += 0.6
                    reasons.append("Historical commit evidence")
                if cand.metadata.get("is_superseded"):
                    score += 0.4
                    reasons.append("Historical precursor in code evolution")
                if cand.metadata.get("is_deleted"):
                    score += 0.5
                    reasons.append("Deletion event in code evolution")
                if cand.metadata.get("is_ended_relation"):
                    score += 0.5
                    reasons.append("Historical ended relation evidence")
                if cand.metadata.get("renamed_from") or cand.metadata.get("renamed_to"):
                    score += 0.4
                    reasons.append("File rename lineage")

            # Normalize score (capped at 1.0)
            normalized_score = min(1.0, round(score / 3.0, 2))
            intermediate.append((score, normalized_score, cand, reasons))

        # Sort descending by raw score to preserve discrimination between strong candidates
        intermediate.sort(key=lambda item: item[0], reverse=True)

        ranked = [
            RankedCandidate(
                candidate=cand,
                score=norm_s,
                matched_reasons=reasons,
            )
            for _, norm_s, cand, reasons in intermediate
        ]


        # 6. Filter out negligible relevance candidates (noise threshold)
        # Ensure we keep at least 3 candidates (floor guarantee) if candidates exist
        if len(ranked) > 3:
            filtered = [r for r in ranked if r.score >= noise_threshold]
            if len(filtered) >= 3:
                return filtered
            return ranked[:3]

        return ranked
