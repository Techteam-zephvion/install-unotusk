"""
EvoReasoner Multi-Path Proof-Chain Aggregator (T2.6 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Consumes ranked EvidencePaths from T2.5 beam search and:
1. Validates each path using ProofChainValidator.
2. Identifies and deduplicates equivalent chains while capturing corroboration bonuses.
3. Combines complementary paths with verifiable entity and temporal continuity.
4. Preserves conflicting and uncertain evidence with explicit penalties and diagnostic annotations.
5. Deterministically ranks and bounds the final set of GroundedProofChains.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.api.src.schemas.code_atom import PropertyExclusivity
from apps.api.src.schemas.evoreasoner import (
    AggregatedProofResult,
    EvidencePath,
    GroundedProofChain,
    ProofAggregationConfig,
    ProofChainHop,
)
from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy
from apps.api.src.services.context_engine.memotime import TemporalIntentType
from apps.api.src.services.evoreasoner.validator import ProofChainValidator


class ProofChainAggregator:
    """Deterministic proof-chain aggregation and conflict preservation service."""

    @classmethod
    def aggregate_paths(
        cls,
        paths: list[EvidencePath],
        query_text: str = "",
        temporal_intent: TemporalIntentType = TemporalIntentType.CURRENT,
        repository_id: uuid.UUID | None = None,
        branch: str = "main",
        config: ProofAggregationConfig | None = None,
    ) -> AggregatedProofResult:
        """
        Validate, deduplicate, combine complementary, and score proof chains from evidence paths.
        """
        cfg = config or ProofAggregationConfig()
        diagnostics: dict[str, Any] = {
            "initial_paths_count": len(paths),
            "rejections": [],
        }

        if not paths:
            return AggregatedProofResult(
                query_text=query_text,
                temporal_intent=temporal_intent,
                repository_id=repository_id or uuid.uuid4(),
                branch=branch,
                chains=[],
                rejected_paths_count=0,
                deduplicated_chains_count=0,
                aggregation_diagnostics=diagnostics,
            )

        target_repo_id = repository_id or paths[0].repository_id

        # Step 1: Validate and convert all paths
        valid_chains: list[GroundedProofChain] = []
        rejected_count = 0

        for p in paths:
            ok, reason, chain = ProofChainValidator.validate_and_convert_path(
                path=p,
                expected_repo_id=target_repo_id,
                expected_branch=branch,
                temporal_intent=temporal_intent,
            )
            if not ok or chain is None:
                rejected_count += 1
                diagnostics["rejections"].append({"path_id": p.path_id, "reason": reason})
            else:
                chain.query_text = query_text
                valid_chains.append(chain)

        diagnostics["valid_initial_chains_count"] = len(valid_chains)

        # Step 2: Equivalent Chain Deduplication
        deduplicated_chains, deduplicated_count = cls._deduplicate_equivalent_chains(
            valid_chains, cfg
        )
        diagnostics["deduplicated_chains_count"] = deduplicated_count

        # Step 3: Complementary Path Combination (Multi-hop synthesis)
        combined_chains = cls._combine_complementary_chains(
            deduplicated_chains, cfg, target_repo_id, branch
        )
        diagnostics["combined_chains_generated"] = len(combined_chains) - len(deduplicated_chains)

        # Step 4: Conflict and Uncertainty Evaluation
        evaluated_chains = cls._evaluate_conflicts_and_uncertainty(combined_chains, cfg)

        # Step 5: Deterministic Ranking and Bounding
        # Order by (-proof_score, -confidence, len(hops), chain_id)
        evaluated_chains.sort(
            key=lambda c: (-round(c.proof_score, 4), -round(c.confidence, 4), len(c.hops), c.chain_id)
        )

        bounded_chains = evaluated_chains[: cfg.max_proof_chains]
        diagnostics["final_chains_count"] = len(bounded_chains)

        return AggregatedProofResult(
            query_text=query_text,
            temporal_intent=temporal_intent,
            repository_id=target_repo_id,
            branch=branch,
            chains=bounded_chains,
            rejected_paths_count=rejected_count,
            deduplicated_chains_count=deduplicated_count,
            aggregation_diagnostics=diagnostics,
        )

    @classmethod
    def _deduplicate_equivalent_chains(
        cls,
        chains: list[GroundedProofChain],
        config: ProofAggregationConfig,
    ) -> tuple[list[GroundedProofChain], int]:
        """
        Group chains by structural signature. Keep the best-scoring chain in each group,
        absorbing supporting metadata and applying a corroboration bonus.
        """
        signature_groups: dict[tuple, list[GroundedProofChain]] = {}

        for c in chains:
            sig = tuple(
                (h.source_entity, str(h.canonical_relation), h.target_entity)
                for h in c.hops
            )
            if sig not in signature_groups:
                signature_groups[sig] = []
            signature_groups[sig].append(c)

        deduplicated: list[GroundedProofChain] = []
        deduplicated_count = 0

        for group in signature_groups.values():
            if len(group) == 1:
                deduplicated.append(group[0])
                continue

            # Sort group by score descending
            group.sort(key=lambda x: (-x.proof_score, -x.confidence))
            best = group[0]
            deduplicated_count += len(group) - 1

            # Merge evidence from secondary chains
            all_path_ids = set(best.constituent_path_ids)
            all_triplets = set(best.supporting_triplet_ids)
            all_shas = set(best.commit_shas)
            all_scores = list(best.original_path_scores)

            for sec in group[1:]:
                all_path_ids.update(sec.constituent_path_ids)
                all_triplets.update(sec.supporting_triplet_ids)
                all_shas.update(sec.commit_shas)
                all_scores.extend(sec.original_path_scores)
                if sec.has_conflict:
                    best.has_conflict = True
                    best.conflict_reasons.extend(sec.conflict_reasons)
                if sec.has_uncertain_evidence:
                    best.has_uncertain_evidence = True
                    best.uncertainty_reasons.extend(sec.uncertainty_reasons)

            best.constituent_path_ids = sorted(all_path_ids)
            best.supporting_triplet_ids = list(all_triplets)
            best.commit_shas = sorted(all_shas)
            best.original_path_scores = all_scores

            # Apply corroboration bonus for independent path confirmation
            corroboration_bonus = min(0.10, config.corroboration_bonus * (len(group) - 1))
            best.proof_score = min(1.0, max(best.original_path_scores) + corroboration_bonus)

            deduplicated.append(best)

        return deduplicated, deduplicated_count

    @classmethod
    def _combine_complementary_chains(
        cls,
        chains: list[GroundedProofChain],
        config: ProofAggregationConfig,
        repository_id: uuid.UUID,
        branch: str,
    ) -> list[GroundedProofChain]:
        """
        Synthesize multi-hop proof chains by joining complementary sub-chains A -> B and B -> C
        when entity continuity and temporal interval intersection hold.
        """
        combined = list(chains)
        seen_endpoints = {(c.source_entity, c.target_entity) for c in chains}

        for i, chain_a in enumerate(chains):
            for j, chain_b in enumerate(chains):
                if i == j:
                    continue

                # Check connection: target of A matches source of B
                if chain_a.target_entity != chain_b.source_entity:
                    continue

                # Avoid simple direct cycle
                if chain_a.source_entity == chain_b.target_entity:
                    continue

                # Check if this endpoint pair already exists
                if (chain_a.source_entity, chain_b.target_entity) in seen_endpoints:
                    continue

                # Hop count boundary
                total_hops = len(chain_a.hops) + len(chain_b.hops)
                if total_hops > config.max_hops_per_chain:
                    continue

                # Check for intermediate entity circularity
                entities_a = {h.source_entity for h in chain_a.hops} | {h.target_entity for h in chain_a.hops}
                entities_b = {h.source_entity for h in chain_b.hops} | {h.target_entity for h in chain_b.hops}
                common = entities_a.intersection(entities_b)
                # The only common entity should be the junction point
                if common != {chain_a.target_entity}:
                    continue

                # Temporal validity intersection
                valid_froms = [dt for dt in (chain_a.valid_from, chain_b.valid_from) if dt is not None]
                valid_tos = [dt for dt in (chain_a.valid_to, chain_b.valid_to) if dt is not None]

                inter_from = max(valid_froms) if valid_froms else None
                inter_to = min(valid_tos) if valid_tos else None

                # Disallow combination if validity intervals are contradictory
                if inter_from and inter_to and inter_from > inter_to:
                    continue

                # Build combined hops with re-indexed positions
                new_hops: list[ProofChainHop] = []
                idx = 0
                for h in chain_a.hops:
                    new_h = h.model_copy()
                    new_h.hop_index = idx
                    new_hops.append(new_h)
                    idx += 1

                for h in chain_b.hops:
                    new_h = h.model_copy()
                    new_h.hop_index = idx
                    new_hops.append(new_h)
                    idx += 1

                # Calculate composite proof score with propagation decay
                decay_factor = 0.95
                composite_score = min(chain_a.proof_score, chain_b.proof_score) * decay_factor
                composite_conf = (chain_a.confidence + chain_b.confidence) / 2.0

                composite_chain = GroundedProofChain(
                    chain_id=str(uuid.uuid4()),
                    query_text=chain_a.query_text or chain_b.query_text,
                    temporal_intent=chain_a.temporal_intent,
                    source_entity=chain_a.source_entity,
                    target_entity=chain_b.target_entity,
                    canonical_relation=f"{chain_a.canonical_relation} -> {chain_b.canonical_relation}",
                    direction="forward" if chain_a.direction == "forward" and chain_b.direction == "forward" else "bidirectional",
                    repository_id=repository_id,
                    branch=branch,
                    hops=new_hops,
                    commit_shas=sorted(set(chain_a.commit_shas + chain_b.commit_shas)),
                    valid_from=inter_from,
                    valid_to=inter_to,
                    is_historical=chain_a.is_historical or chain_b.is_historical,
                    confidence=composite_conf,
                    has_uncertain_evidence=chain_a.has_uncertain_evidence or chain_b.has_uncertain_evidence,
                    uncertainty_reasons=chain_a.uncertainty_reasons + chain_b.uncertainty_reasons,
                    has_conflict=chain_a.has_conflict or chain_b.has_conflict,
                    conflict_reasons=chain_a.conflict_reasons + chain_b.conflict_reasons,
                    original_path_scores=[chain_a.proof_score, chain_b.proof_score],
                    proof_score=composite_score,
                    supporting_triplet_ids=list(set(chain_a.supporting_triplet_ids + chain_b.supporting_triplet_ids)),
                    constituent_path_ids=sorted(set(chain_a.constituent_path_ids + chain_b.constituent_path_ids)),
                    explanation=ProofChainValidator._generate_chain_explanation(
                        source=chain_a.source_entity,
                        target=chain_b.target_entity,
                        hops=new_hops,
                        is_historical=chain_a.is_historical or chain_b.is_historical,
                        has_conflict=chain_a.has_conflict or chain_b.has_conflict,
                        has_uncertain=chain_a.has_uncertain_evidence or chain_b.has_uncertain_evidence,
                    ),
                    metadata={"is_synthesized_composite": True},
                )

                seen_endpoints.add((chain_a.source_entity, chain_b.target_entity))
                combined.append(composite_chain)

        return combined

    @classmethod
    def _evaluate_conflicts_and_uncertainty(
        cls,
        chains: list[GroundedProofChain],
        config: ProofAggregationConfig,
    ) -> list[GroundedProofChain]:
        """
        Detect conflicts between parallel exclusive assertions and apply explicit scoring adjustments.
        Preserves all conflicting chains with explicit conflict diagnostic annotations.
        """
        # Group by (source_entity, relation) to detect conflicting exclusive assertions
        exclusive_claims: dict[tuple[str, str], list[GroundedProofChain]] = {}

        for c in chains:
            if len(c.hops) == 1:
                hop = c.hops[0]
                tax = CodeRelationTaxonomy.classify(hop.relation)
                if tax.exclusivity == PropertyExclusivity.EXCLUSIVE:
                    key = (c.source_entity, str(hop.canonical_relation))
                    if key not in exclusive_claims:
                        exclusive_claims[key] = []
                    exclusive_claims[key].append(c)

        for (src, rel), group in exclusive_claims.items():
            # If multiple distinct targets are asserted for an exclusive relation
            distinct_targets = {g.target_entity for g in group}
            if len(distinct_targets) > 1:
                for member in group:
                    member.has_conflict = True
                    conflict_msg = (
                        f"exclusive_relation_conflict: '{src}' has multiple targets for '{rel}': "
                        f"{sorted(distinct_targets)}"
                    )
                    if conflict_msg not in member.conflict_reasons:
                        member.conflict_reasons.append(conflict_msg)

        # Apply final explainable proof_score adjustments
        for c in chains:
            base_score = c.proof_score
            penalties = 0.0

            if c.has_uncertain_evidence:
                penalties += config.uncertainty_penalty
            if c.has_conflict:
                penalties += config.conflict_penalty

            adjusted = base_score - penalties
            c.proof_score = round(max(0.0, min(1.0, adjusted)), 4)

        return chains
