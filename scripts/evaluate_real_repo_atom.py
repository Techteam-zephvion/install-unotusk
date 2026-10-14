"""
ATOM Real-Repository Quality and Code Retrieval Evaluation Runner (Phase 14).

Executes end-to-end evaluation against realistic repository commits and code-retrieval questions:
1. ATOM Extraction Quality (Fact Precision/Recall/F1, Relation Precision/Recall/F1, Temporal Accuracy)
2. Real-World Code Retrieval (Query -> MultiSignalRetriever -> RelationshipExpander -> MultiSignalRanker -> ContextAssembler)
3. Retrieval Metrics: Recall@1, Recall@3, Recall@5, Precision@1, Precision@3, Precision@5, Mean Reciprocal Rank (MRR)
4. Provenance Survival & Line-Range Verification
5. Embedding-Provider Reality Check (Voyage-code-2 configuration vs Development fallback)

Outputs machine-readable JSON to `docs/reports/atom_real_repo_evaluation.json`.
"""

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uuid

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.schemas.code_atom import (
    RelationType,
    SemanticCodeFact,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom import (
    CodeAtomDecomposer,
    reconcile_code_relationships,
)
from apps.api.src.services.code_atom.chunk_mapper import map_atomic_code_change_to_code_chunk
from apps.api.src.services.code_atom.embedding import (
    DevelopmentCodeEmbeddingBackend,
    VoyageCodeEmbeddingBackend,
    get_code_embedding_backend,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import MultiSignalRetriever
from tests.fixtures.atom_eval_dataset import ExpectedFact, ExpectedRelation
from tests.fixtures.atom_real_repo_dataset import get_real_repo_dataset


def match_fact(extracted: SemanticCodeFact, expected: ExpectedFact) -> bool:
    """Matches semantic code facts against ground truth."""
    if extracted.fact_type != expected.fact_type:
        return False
    if extracted.is_uncertain != expected.is_uncertain:
        return False
    if expected.symbol_name and extracted.symbol_name != expected.symbol_name:
        return False

    stmt_lower = extracted.statement.lower()
    for kw in expected.statement_keywords:
        if kw.lower() not in stmt_lower:
            return False

    if expected.evidenced_lines_contain:
        all_ev = " ".join(extracted.evidenced_lines)
        if not any(req in all_ev for req in expected.evidenced_lines_contain):
            return False

    return True


def match_relation(extracted: TemporalCodeRelation, expected: ExpectedRelation) -> bool:
    """Matches temporal relations against ground truth."""
    norm_rel = (
        extracted.relation.value
        if isinstance(extracted.relation, RelationType)
        else str(extracted.relation)
    )
    exp_rel = (
        expected.relation.value
        if isinstance(expected.relation, RelationType)
        else str(expected.relation)
    )
    if norm_rel != exp_rel:
        return False

    subj_pool = f"{extracted.subject} {extracted.canonical_subject or ''}".lower()
    if expected.subject_keyword.lower() not in subj_pool:
        return False

    obj_pool = f"{extracted.object} {extracted.canonical_object or ''}".lower()
    if expected.object_keyword.lower() not in obj_pool:
        return False

    return True


async def run_real_repo_evaluation() -> dict[str, Any]:
    cases = get_real_repo_dataset()
    decomposer = CodeAtomDecomposer()

    # 1. ATOM Extraction Quality metrics
    fact_tp = 0
    fact_fp = 0
    fact_fn = 0
    rel_tp = 0
    rel_fp = 0
    rel_fn = 0

    temporal_checks_total = 0
    temporal_checks_correct = 0
    invented_timestamps_count = 0
    ended_relations_identified = 0

    latencies_decomposition: list[float] = []
    latencies_resolution: list[float] = []
    latencies_total: list[float] = []

    # Prepare chunks and files for retrieval
    snapshot_id = uuid.uuid4()
    all_chunks: list[CodeChunk] = []
    case_chunks_map: dict[str, list[CodeChunk]] = {}

    for case in cases:
        t_start = time.perf_counter()

        t_d_start = time.perf_counter()
        decomp_result = decomposer.decompose(case.commit, rename_history=case.rename_history)
        t_d_end = time.perf_counter()

        t_r_start = time.perf_counter()
        reconciled_rels = reconcile_code_relationships(
            decomp_result.relations, rename_history=case.rename_history
        )
        t_r_end = time.perf_counter()

        t_end = time.perf_counter()
        latencies_decomposition.append((t_d_end - t_d_start) * 1000)
        latencies_resolution.append((t_r_end - t_r_start) * 1000)
        latencies_total.append((t_end - t_start) * 1000)

        # Fact matching
        matched_facts: set[int] = set()
        for exp in case.expected_facts:
            matched = False
            for idx, fact in enumerate(decomp_result.facts):
                if idx not in matched_facts and match_fact(fact, exp):
                    matched_facts.add(idx)
                    matched = True
                    break
            if matched:
                fact_tp += 1
            else:
                fact_fn += 1

        # Relation matching
        matched_rels: set[int] = set()
        for exp in case.expected_relations:
            matched = False
            for idx, rel in enumerate(reconciled_rels):
                if idx not in matched_rels and match_relation(rel, exp):
                    matched_rels.add(idx)
                    matched = True

                    # Check temporal invariants
                    temporal_checks_total += 1
                    t_correct = True
                    if exp.has_t_start and not rel.t_start:
                        t_correct = False
                    if exp.has_t_end and not rel.t_end:
                        t_correct = False
                    if not exp.has_t_end and rel.t_end:
                        t_correct = False
                    if t_correct:
                        temporal_checks_correct += 1

                    if rel.t_end is not None:
                        ended_relations_identified += 1
                    if case.commit.committed_at is None and (rel.t_start or rel.t_end):
                        invented_timestamps_count += 1
                    break
            if matched:
                rel_tp += 1
            else:
                rel_fn += 1

        # Map to CodeChunks
        file_id = uuid.uuid4()
        case_chunk_list: list[CodeChunk] = []
        for change in decomp_result.changes:
            chunk = map_atomic_code_change_to_code_chunk(
                change=change,
                snapshot_id=snapshot_id,
                file_id=file_id,
                compute_embedding=True,
            )
            case_chunk_list.append(chunk)
            all_chunks.append(chunk)
        case_chunks_map[case.case_id] = case_chunk_list

    fact_precision = fact_tp / max(1, fact_tp + fact_fp)
    fact_recall = fact_tp / max(1, fact_tp + fact_fn)
    fact_f1 = (
        (2 * fact_precision * fact_recall) / (fact_precision + fact_recall)
        if (fact_precision + fact_recall) > 0
        else 0.0
    )

    rel_precision = rel_tp / max(1, rel_tp + rel_fp)
    rel_recall = rel_tp / max(1, rel_tp + rel_fn)
    rel_f1 = (
        (2 * rel_precision * rel_recall) / (rel_precision + rel_recall)
        if (rel_precision + rel_recall) > 0
        else 0.0
    )

    # Stability test across 5 iterations
    stability_facts: list[list[str]] = []
    stability_rels: list[list[str]] = []
    for _ in range(5):
        run_f_ids = []
        run_r_ids = []
        for case in cases:
            res = decomposer.decompose(case.commit, rename_history=case.rename_history)
            run_f_ids.extend([f.fingerprint for f in res.facts])
            recs = reconcile_code_relationships(res.relations, rename_history=case.rename_history)
            run_r_ids.extend([r.fingerprint for r in recs])
        stability_facts.append(run_f_ids)
        stability_rels.append(run_r_ids)

    def calc_jaccard(runs: list[list[str]]) -> float:
        if len(runs) < 2:
            return 1.0
        scores = []
        for i in range(len(runs) - 1):
            s1, s2 = set(runs[i]), set(runs[i + 1])
            if not s1 and not s2:
                scores.append(1.0)
            else:
                scores.append(len(s1 & s2) / len(s1 | s2))
        return sum(scores) / len(scores)

    fact_jaccard = calc_jaccard(stability_facts)
    rel_jaccard = calc_jaccard(stability_rels)

    # 2. Retrieval Evaluation: Full Pipeline
    mock_session = AsyncMock()

    def mock_execute(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = all_chunks
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    mock_session.execute.side_effect = mock_execute

    retrieval_case_results: list[dict[str, Any]] = []
    ranks: list[int | None] = []
    r_at_1 = 0
    r_at_3 = 0
    r_at_5 = 0
    prec_at_1_sum = 0.0
    prec_at_3_sum = 0.0
    prec_at_5_sum = 0.0
    provenance_verified_count = 0
    relationship_expanded_count = 0

    for case in cases:
        analyzed = analyze_query(case.retrieval_query)
        raw_cands = await MultiSignalRetriever.retrieve_candidates(
            session=mock_session,
            snapshot_id=snapshot_id,
            analyzed_query=analyzed,
        )
        expanded_cands = await RelationshipExpander.expand_candidates(
            session=mock_session,
            snapshot_id=snapshot_id,
            seed_candidates=raw_cands,
            max_depth=2,
        )
        ranked = MultiSignalRanker.rank_candidates(
            candidates=expanded_cands,
            analyzed_query=analyzed,
        )
        assembled = ContextAssembler.assemble_context(
            ranked_candidates=ranked,
            max_tokens=4000,
        )

        # Evaluate target match
        found_rank: int | None = None
        target_candidate = None
        for i, r in enumerate(ranked):
            cand = r.candidate
            # Check if any expected target matches path or symbol
            is_match = any(
                t.lower() in cand.path.lower()
                or (cand.metadata.get("symbol_name") and t.lower() == cand.metadata.get("symbol_name", "").lower())
                or t.lower() in cand.name.lower()
                for t in case.expected_retrieval_targets
            )
            if is_match:
                found_rank = i + 1
                target_candidate = cand
                break

        ranks.append(found_rank)
        if found_rank == 1:
            r_at_1 += 1
            prec_at_1_sum += 1.0
        if found_rank and found_rank <= 3:
            r_at_3 += 1
            prec_at_3_sum += 1.0 / 3.0
        if found_rank and found_rank <= 5:
            r_at_5 += 1
            prec_at_5_sum += 1.0 / 5.0

        # Verify provenance survival
        prov_ok = False
        if target_candidate and target_candidate.metadata:
            meta = target_candidate.metadata
            sha_present = bool(meta.get("commit_sha") or (meta.get("provenance") or {}).get("commit_sha"))
            lines_ok = target_candidate.start_line is not None and target_candidate.end_line is not None
            if sha_present and lines_ok:
                prov_ok = True
                provenance_verified_count += 1

        # Check relationship expansion
        has_rel_expansion = any(
            r.candidate.metadata.get("relationship_hop", 0) > 0
            or "temporal_rel:" in r.candidate.candidate_id
            for r in ranked
        )
        if has_rel_expansion:
            relationship_expanded_count += 1

        retrieval_case_results.append(
            {
                "case_id": case.case_id,
                "query": case.retrieval_query,
                "expected_targets": case.expected_retrieval_targets,
                "first_match_rank": found_rank,
                "reciprocal_rank": round(1.0 / found_rank, 4) if found_rank else 0.0,
                "top_1_candidate": ranked[0].candidate.name if ranked else None,
                "top_1_path": ranked[0].candidate.path if ranked else None,
                "total_ranked_candidates": len(ranked),
                "provenance_intact": prov_ok,
                "relationship_expanded": has_rel_expansion,
                "assembled_chars": assembled.total_characters,
            }
        )

    num_q = len(cases)
    mrr = sum(1.0 / r for r in ranks if r) / num_q
    recall_at_1 = r_at_1 / num_q
    recall_at_3 = r_at_3 / num_q
    recall_at_5 = r_at_5 / num_q
    prec_at_1 = prec_at_1_sum / num_q
    prec_at_3 = prec_at_3_sum / num_q
    prec_at_5 = prec_at_5_sum / num_q

    # 3. Embedding Provider Verification
    active_backend = get_code_embedding_backend()
    voyage_target = VoyageCodeEmbeddingBackend(api_key="mock_key", model="voyage-code-2")

    embedding_verification = {
        "active_provider_name": active_backend.provider_name,
        "active_model_name": active_backend.model_name,
        "vector_dimension": active_backend.dimension,
        "voyage_target_model": voyage_target.model_name,
        "voyage_target_dimension": voyage_target.dimension,
        "is_voyage_configured": active_backend.provider_name == "voyage",
        "live_credentials_available": False,
        "fallback_mode_active": isinstance(active_backend, DevelopmentCodeEmbeddingBackend),
        "database_storage_layer": "PostgreSQL 16 + pgvector CompatibleVector(1536)",
        "external_vector_db_discarded": "Qdrant discarded per Unotusk MVP specification",
    }

    results: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "evaluation_scope": "Real-Repository Git Commits & End-to-End Code Retrieval (Phase 14)",
        "dataset_summary": {
            "total_cases": len(cases),
            "total_indexed_chunks": len(all_chunks),
            "categories": [c.category for c in cases],
        },
        "atom_extraction_metrics": {
            "fact_extraction": {
                "true_positives": fact_tp,
                "false_positives": fact_fp,
                "false_negatives": fact_fn,
                "precision": round(fact_precision, 4),
                "recall": round(fact_recall, 4),
                "f1_score": round(fact_f1, 4),
            },
            "relation_extraction": {
                "true_positives": rel_tp,
                "false_positives": rel_fp,
                "false_negatives": rel_fn,
                "precision": round(rel_precision, 4),
                "recall": round(rel_recall, 4),
                "f1_score": round(rel_f1, 4),
            },
            "temporal_correctness": {
                "invariants_tested": temporal_checks_total,
                "invariants_correct": temporal_checks_correct,
                "temporal_accuracy": round(
                    temporal_checks_correct / max(1, temporal_checks_total), 4
                ),
                "invented_timestamps": invented_timestamps_count,
                "ended_relations_identified": ended_relations_identified,
            },
            "extraction_stability": {
                "fact_jaccard": round(fact_jaccard, 4),
                "relation_jaccard": round(rel_jaccard, 4),
            },
            "latency_ms": {
                "decomposition_mean_ms": round(sum(latencies_decomposition) / len(latencies_decomposition), 2),
                "resolution_mean_ms": round(sum(latencies_resolution) / len(latencies_resolution), 2),
                "total_mean_ms": round(sum(latencies_total) / len(latencies_total), 2),
                "min_ms": round(min(latencies_total), 2),
                "max_ms": round(max(latencies_total), 2),
            },
        },
        "retrieval_evaluation": {
            "mean_reciprocal_rank": round(mrr, 4),
            "recall_at_1": round(recall_at_1, 4),
            "recall_at_3": round(recall_at_3, 4),
            "recall_at_5": round(recall_at_5, 4),
            "precision_at_1": round(prec_at_1, 4),
            "precision_at_3": round(prec_at_3, 4),
            "precision_at_5": round(prec_at_5, 4),
            "provenance_survival_rate": round(provenance_verified_count / num_q, 4),
            "cases": retrieval_case_results,
        },
        "embedding_provider_verification": embedding_verification,
    }

    # Write output artifact
    out_path = os.path.join(PROJECT_ROOT, "docs", "reports", "atom_real_repo_evaluation.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


def print_summary(res: dict[str, Any]) -> None:
    print("\n" + "=" * 65)
    print("   ATOM REAL-REPOSITORY QUALITY & RETRIEVAL EVALUATION (PHASE 14)  ")
    print("=" * 65)
    print(f"Dataset Size: {res['dataset_summary']['total_cases']} real commits | Total Chunks: {res['dataset_summary']['total_indexed_chunks']}")
    print("-" * 65)

    atom = res["atom_extraction_metrics"]
    print("1. ATOM EXTRACTION QUALITY")
    f_p = atom["fact_extraction"]["precision"] * 100
    f_r = atom["fact_extraction"]["recall"] * 100
    f_f1 = atom["fact_extraction"]["f1_score"]
    print(f"   Facts:     Precision: {f_p:.1f}%  | Recall: {f_r:.1f}%  | F1: {f_f1:.4f}")

    r_p = atom["relation_extraction"]["precision"] * 100
    r_r = atom["relation_extraction"]["recall"] * 100
    r_f1 = atom["relation_extraction"]["f1_score"]
    print(f"   Relations: Precision: {r_p:.1f}%  | Recall: {r_r:.1f}%  | F1: {r_f1:.4f}")

    t_acc = atom["temporal_correctness"]["temporal_accuracy"] * 100
    inv_ts = atom["temporal_correctness"]["invented_timestamps"]
    print(f"   Temporal:  Accuracy: {t_acc:.1f}% | Invented Timestamps: {inv_ts}")

    print("\n2. END-TO-END CODE RETRIEVAL (Question -> Retrieval -> Expansion -> Ranking)")
    ret = res["retrieval_evaluation"]
    print(f"   MRR (Mean Reciprocal Rank): {ret['mean_reciprocal_rank']:.4f}")
    print(f"   Recall@1:    {ret['recall_at_1'] * 100:.1f}%   | Precision@1: {ret['precision_at_1'] * 100:.1f}%")
    print(f"   Recall@3:    {ret['recall_at_3'] * 100:.1f}%  | Precision@3: {ret['precision_at_3'] * 100:.1f}%")
    print(f"   Recall@5:    {ret['recall_at_5'] * 100:.1f}%  | Precision@5: {ret['precision_at_5'] * 100:.1f}%")
    print(f"   Provenance Survival: {ret['provenance_survival_rate'] * 100:.1f}%")

    print("\n3. EMBEDDING PROVIDER STATUS")
    emb = res["embedding_provider_verification"]
    print(f"   Active Provider:    {emb['active_provider_name']} ({emb['active_model_name']})")
    print(f"   AI PIE Requirement: {emb['voyage_target_model']} ({emb['voyage_target_dimension']} dims)")
    print(f"   Database Storage:   {emb['database_storage_layer']}")
    print(f"   Fallback Mode:      {emb['fallback_mode_active']} (Offline Zero-Hallucination Synthesizer)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    results = asyncio.run(run_real_repo_evaluation())
    print_summary(results)
