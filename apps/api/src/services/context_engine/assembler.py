import uuid
from dataclasses import dataclass, field
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.ranker import RankedCandidate


def _json_safe(val: Any) -> Any:
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    if isinstance(val, list | tuple | set):
        return [_json_safe(v) for v in val]
    return val


@dataclass
class AssembledContext:
    prompt_context: str
    evidence_items: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    total_characters: int = 0
    candidate_count: int = 0
    proof_chains: list[dict[str, Any]] = field(default_factory=list)
    proof_chain_count: int = 0
    evidence_paths: list[dict[str, Any]] = field(default_factory=list)
    evidence_path_count: int = 0


class ContextAssembler:
    @staticmethod
    def assemble_context(
        ranked_candidates: list[RankedCandidate],
        max_tokens: int | None = None,
        proof_chains: list[Any] | None = None,
        evidence_paths: list[Any] | None = None,
        temporal_evidence: list[dict[str, Any]] | None = None,
    ) -> AssembledContext:
        budget_tokens = max_tokens or settings.CONTEXT_BUDGET_TOKENS
        # Approximate 4 characters per token
        char_budget = budget_tokens * 4

        sections: list[str] = []
        evidence_items: list[dict[str, Any]] = []
        related_entities: set[str] = set()

        current_chars = 0
        used_count = 0

        # -------------------------------------------------------------
        # 1. Format Grounded Proof Chains (Bounded to <= 25% of budget)
        # -------------------------------------------------------------
        formatted_proof_chains: list[dict[str, Any]] = []
        proof_chain_sections: list[str] = []
        proof_budget_chars = min(int(char_budget * 0.25), 2500) if proof_chains else 0
        current_proof_chars = 0

        if proof_chains:
            for chain in proof_chains:
                # Require valid GroundedProofChain with hops
                if not hasattr(chain, "hops") or not chain.hops:
                    continue

                valid_from_str = chain.valid_from.isoformat() if chain.valid_from else "Origin"
                valid_to_str = chain.valid_to.isoformat() if chain.valid_to else "Active"
                temporal_status = "HISTORICAL" if chain.is_historical else "CURRENT"

                conflict_line = ""
                if chain.has_conflict and chain.conflict_reasons:
                    conflict_line = f"- Conflict Warning: {'; '.join(chain.conflict_reasons)}\n"

                uncertain_line = ""
                if chain.has_uncertain_evidence and chain.uncertainty_reasons:
                    uncertain_line = f"- Uncertainty Note: {'; '.join(chain.uncertainty_reasons)}\n"

                hop_lines = []
                for h in chain.hops:
                    c_tag = " (conflict)" if getattr(h, "has_conflict", False) else ""
                    u_tag = " (uncertain)" if getattr(h, "is_uncertain", False) else ""
                    s_tag = " (superseded)" if getattr(h, "is_superseded", False) else ""
                    c_sha = getattr(h, "commit_sha", None)
                    commit_tag = f" [Commit: {c_sha[:8]}]" if c_sha else " [Commit: HEAD]"
                    inv_tag = " [INVERSE]" if getattr(h, "is_inverse", False) else ""
                    hop_lines.append(
                        f"  {h.hop_index + 1}. ({h.source_entity}, {h.relation}, {h.target_entity})"
                        f"{inv_tag}{commit_tag}{c_tag}{u_tag}{s_tag}"
                    )

                hops_formatted = "\n".join(hop_lines)
                intent_val = (
                    chain.temporal_intent.value
                    if hasattr(chain.temporal_intent, "value")
                    else str(chain.temporal_intent)
                )
                chain_text = (
                    f"### [PROOF CHAIN] {chain.source_entity} -> {chain.target_entity}\n"
                    f"- Scope: Repo: {chain.repository_id} | Branch: {chain.branch}\n"
                    f"- Temporal Status: {temporal_status} | Intent: {intent_val}\n"
                    f"- Validity Interval: [{valid_from_str} -> {valid_to_str}]\n"
                    f"- Direction: {chain.direction} | Proof Score: {chain.proof_score:.2f} | Confidence: {chain.confidence:.2f}\n"
                    f"{conflict_line}"
                    f"{uncertain_line}"
                    f"- Traversed Hops:\n{hops_formatted}\n"
                    f"- Grounded Explanation: {chain.explanation}\n"
                )

                if current_proof_chars + len(chain_text) > proof_budget_chars and formatted_proof_chains:
                    break

                proof_chain_sections.append(chain_text)
                current_proof_chars += len(chain_text)

                chain_item = {
                    "type": "proof_chain",
                    "file": chain.hops[0].source_entity if chain.hops else "",
                    "symbol": f"{chain.source_entity} -> {chain.target_entity}",
                    "lines": None,
                    "relevance": round(chain.proof_score, 4),
                    "snippet": chain.explanation,
                    "chain_id": str(chain.chain_id),
                    "source_entity": chain.source_entity,
                    "target_entity": chain.target_entity,
                    "canonical_relation": chain.canonical_relation,
                    "direction": chain.direction,
                    "repository_id": str(chain.repository_id),
                    "branch": chain.branch,
                    "temporal_intent": intent_val,
                    "is_historical": chain.is_historical,
                    "valid_from": chain.valid_from.isoformat() if chain.valid_from else None,
                    "valid_to": chain.valid_to.isoformat() if chain.valid_to else None,
                    "confidence": round(chain.confidence, 4),
                    "proof_score": round(chain.proof_score, 4),
                    "has_conflict": chain.has_conflict,
                    "conflict_reasons": chain.conflict_reasons,
                    "has_uncertain_evidence": chain.has_uncertain_evidence,
                    "uncertainty_reasons": chain.uncertainty_reasons,
                    "commit_shas": chain.commit_shas,
                    "supporting_triplet_ids": [str(tid) for tid in chain.supporting_triplet_ids],
                    "constituent_path_ids": chain.constituent_path_ids,
                    "hops": [
                        {
                            "hop_index": h.hop_index,
                            "source": h.source_entity,
                            "relation": h.relation,
                            "canonical_relation": (
                                h.canonical_relation.value
                                if hasattr(h.canonical_relation, "value")
                                else str(h.canonical_relation)
                            ),
                            "target": h.target_entity,
                            "is_inverse": h.is_inverse,
                            "commit_sha": h.commit_sha,
                            "confidence": h.confidence,
                            "is_uncertain": h.is_uncertain,
                            "has_conflict": h.has_conflict,
                            "is_superseded": h.is_superseded,
                        }
                        for h in chain.hops
                    ],
                    "explanation": chain.explanation,
                }
                formatted_proof_chains.append(chain_item)
                evidence_items.append(chain_item)

                if chain.source_entity:
                    related_entities.add(chain.source_entity)
                if chain.target_entity:
                    related_entities.add(chain.target_entity)
                for h in chain.hops:
                    if h.source_entity:
                        related_entities.add(h.source_entity)
                    if h.target_entity:
                        related_entities.add(h.target_entity)

        # -------------------------------------------------------------
        # 1b. Format Structure-Aware STAR-RAG Evidence Paths (<= 25% budget)
        # -------------------------------------------------------------
        formatted_evidence_paths: list[dict[str, Any]] = []
        evidence_path_sections: list[str] = []
        path_budget_chars = min(int(char_budget * 0.25), 2500) if evidence_paths else 0
        current_path_chars = 0

        if evidence_paths:
            for ep in evidence_paths:
                full_path_str = getattr(ep, "full_path_str", None) or (
                    ep.get("full_path_str", "") if isinstance(ep, dict) else ""
                )
                source_ent = getattr(ep, "source_entity", None) or (
                    ep.get("source_entity", "") if isinstance(ep, dict) else ""
                )
                target_ent = getattr(ep, "target_entity", None) or (
                    ep.get("target_entity", "") if isinstance(ep, dict) else ""
                )
                hops = getattr(ep, "hops", None) or (
                    ep.get("hops", []) if isinstance(ep, dict) else []
                )
                conf = getattr(ep, "confidence", None) or (
                    ep.get("confidence", 1.0) if isinstance(ep, dict) else 1.0
                )
                path_id = getattr(ep, "path_id", None) or (
                    ep.get("path_id", "") if isinstance(ep, dict) else f"path:{uuid.uuid4().hex[:8]}"
                )

                if not hops and not full_path_str:
                    continue

                hop_lines = []
                for idx, h in enumerate(hops, start=1):
                    s_name = getattr(h, "source_name", None) or (
                        h.get("source_name") if isinstance(h, dict) else ""
                    )
                    t_name = getattr(h, "target_name", None) or (
                        h.get("target_name") if isinstance(h, dict) else ""
                    )
                    rel = getattr(h, "relation", None) or (
                        h.get("relation") if isinstance(h, dict) else "CALLS"
                    )
                    s_file = getattr(h, "source_file", None) or (
                        h.get("source_file") if isinstance(h, dict) else ""
                    )
                    t_file = getattr(h, "target_file", None) or (
                        h.get("target_file") if isinstance(h, dict) else ""
                    )
                    line_no = getattr(h, "line_number", 1) or (
                        h.get("line_number", 1) if isinstance(h, dict) else 1
                    )
                    hop_lines.append(
                        f"  {idx}. ({s_name}, {rel}, {t_name}) [{s_file} -> {t_file}] (line {line_no})"
                    )

                hops_formatted = "\n".join(hop_lines) if hop_lines else f"  - {full_path_str}"
                path_text = (
                    f"### [STRUCTURE-AWARE STAR-RAG EVIDENCE PATH] {source_ent} -> {target_ent}\n"
                    f"- Call Hierarchy: {full_path_str}\n"
                    f"- Structural Confidence: {float(conf):.2f}\n"
                    f"- Traversed Hops:\n{hops_formatted}\n"
                )

                if current_path_chars + len(path_text) > path_budget_chars and formatted_evidence_paths:
                    break

                evidence_path_sections.append(path_text)
                current_path_chars += len(path_text)

                first_file = ""
                first_line = "1"
                if hops:
                    h0 = hops[0]
                    first_file = getattr(h0, "source_file", None) or (
                        h0.get("source_file") if isinstance(h0, dict) else ""
                    )
                    first_line = str(
                        getattr(h0, "line_number", "1")
                        or (h0.get("line_number", "1") if isinstance(h0, dict) else "1")
                    )

                first_rel = "CALLS"
                if hops:
                    h0 = hops[0]
                    first_rel = getattr(h0, "relation", "CALLS") if not isinstance(h0, dict) else h0.get("relation", "CALLS")

                path_item: dict[str, Any] = {
                    "type": "evidence_path",
                    "file": first_file,
                    "symbol": f"{source_ent} -> {target_ent}",
                    "lines": first_line,
                    "relevance": round(float(conf), 4),
                    "snippet": f"Structural call path: {full_path_str}",
                    "path_id": path_id,
                    "source_entity": source_ent,
                    "target_entity": target_ent,
                    "full_path_str": full_path_str,
                    "relationship_path": full_path_str,
                    "relationship_type": first_rel,
                    "relationship_hop": len(hops),
                    "connected_from": source_ent,
                    "retrieval_reason": f"STAR-RAG Structure-Aware path: {full_path_str}",
                    "hops": [
                        {
                            "hop_index": getattr(h, "hop_index", i) if not isinstance(h, dict) else h.get("hop_index", i),
                            "source": getattr(h, "source_name", "") if not isinstance(h, dict) else h.get("source_name", ""),
                            "source_file": getattr(h, "source_file", "") if not isinstance(h, dict) else h.get("source_file", ""),
                            "relation": getattr(h, "relation", "") if not isinstance(h, dict) else h.get("relation", ""),
                            "target": getattr(h, "target_name", "") if not isinstance(h, dict) else h.get("target_name", ""),
                            "target_file": getattr(h, "target_file", "") if not isinstance(h, dict) else h.get("target_file", ""),
                            "line_number": getattr(h, "line_number", 1) if not isinstance(h, dict) else h.get("line_number", 1),
                        }
                        for i, h in enumerate(hops)
                    ],
                    "provenance": {
                        "engine": "structure_aware_star_rag",
                        "path_id": path_id,
                        "hops_count": len(hops),
                    },
                }
                formatted_evidence_paths.append(path_item)
                evidence_items.append(path_item)

                if source_ent:
                    related_entities.add(source_ent)
                if target_ent:
                    related_entities.add(target_ent)
                for h in hops:
                    sn = getattr(h, "source_name", None) or (
                        h.get("source_name") if isinstance(h, dict) else None
                    )
                    tn = getattr(h, "target_name", None) or (
                        h.get("target_name") if isinstance(h, dict) else None
                    )
                    if sn:
                        related_entities.add(sn)
                    if tn:
                        related_entities.add(tn)

        # -------------------------------------------------------------
        # 1c. Format Temporal Historical Evidence (STAR-RAG)
        # -------------------------------------------------------------
        current_temp_chars = 0
        if temporal_evidence:
            temporal_budget_chars = min(int(char_budget * 0.25), 3000)
            temp_lines = [
                "## HISTORICAL TEMPORAL EVIDENCE (STAR-RAG)",
                "The following events represent verified historical repository changes and relationships.",
                "Distinguish historical implementations and previous states from current code.",
                "",
            ]
            for idx, tev in enumerate(temporal_evidence, start=1):
                ev_ts = tev.get("timestamp") or "Historical"
                c_sha = (tev.get("commit_sha") or "")[:8]
                c_tag = f" [Commit: {c_sha}]" if c_sha else ""
                s_rel_o = tev.get("relationship_path") or f"{tev.get('subject')} {tev.get('relation')} {tev.get('object')}"
                f_path = tev.get("file") or "Unknown"
                snippet = tev.get("snippet", "")
                change_type = tev.get("change_type") or "CHANGE"

                event_block = (
                    f"{idx}. **[{change_type}] {s_rel_o}**{c_tag}\n"
                    f"   - Timestamp: {ev_ts} (UTC)\n"
                    f"   - File: `{f_path}` (Lines {tev.get('lines', '1-20')})\n"
                    f"   - Temporal Status: HISTORICAL\n"
                    f"   - Detail: {snippet}\n"
                )
                if current_temp_chars + len(event_block) <= temporal_budget_chars:
                    temp_lines.append(event_block)
                    current_temp_chars += len(event_block)
                    evidence_items.append(tev)
                    if tev.get("subject"):
                        related_entities.add(tev["subject"])
                    if tev.get("object"):
                        related_entities.add(tev["object"])

            if len(temp_lines) > 4:
                sections.append("\n".join(temp_lines))

        # -------------------------------------------------------------
        # 2. Format Candidate Code Chunks
        # -------------------------------------------------------------
        current_chars += current_proof_chars + current_path_chars + current_temp_chars

        for r in ranked_candidates:
            cand = r.candidate

            # Compact whitespace and format content (max 2500 chars per candidate)
            compact_content = "\n".join(
                line for line in cand.content.splitlines() if line.strip()
            ) if cand.content else ""
            truncated_content = compact_content[:2500]
            if len(compact_content) > 2500:
                truncated_content += "\n... [truncated]"

            commit_info = ""
            sha = cand.metadata.get("commit_sha")
            msg = cand.metadata.get("commit_message")
            ts = cand.metadata.get("committed_at") or (cand.metadata.get("provenance") or {}).get("committed_at")
            author = cand.metadata.get("author") or (cand.metadata.get("provenance") or {}).get("author")
            c_type = cand.metadata.get("chunk_type") or (cand.metadata.get("provenance") or {}).get("change_type")

            if sha or msg or ts:
                sha_str = f"Commit: {sha[:8]}" if sha else "Commit: HEAD"
                parts = [sha_str]
                if ts:
                    parts.append(f"Date: {ts}")
                if author:
                    parts.append(f"Author: {author}")
                if c_type:
                    parts.append(f"Type: {c_type}")

                header = " | ".join(parts)
                if msg:
                    commit_info = f"- {header} — {msg}\n"
                else:
                    commit_info = f"- {header}\n"

            temporal_status = ""
            if cand.metadata.get("is_superseded"):
                by_sha = cand.metadata.get("superseded_by_sha")
                by_text = f" by {by_sha[:8]}" if by_sha else ""
                temporal_status = f"- Temporal Status: SUPERSEDED{by_text}\n"
            elif cand.metadata.get("is_deleted"):
                temporal_status = "- Temporal Status: DELETED\n"
            elif cand.metadata.get("is_current"):
                temporal_status = "- Temporal Status: CURRENT\n"

            relationship_info = ""
            rel_path = cand.metadata.get("relationship_path")
            rel_type = cand.metadata.get("relationship_type")
            rel_hop = cand.metadata.get("relationship_hop")
            rel_reason = cand.metadata.get("retrieval_reason")
            alt_paths = cand.metadata.get("alternative_paths")

            if rel_path or rel_type:
                rel_parts = []
                if rel_path:
                    rel_parts.append(f"Path: {rel_path}")
                elif rel_type:
                    rel_parts.append(f"Type: {rel_type}")
                if rel_hop:
                    rel_parts.append(f"Hop {rel_hop}")
                rel_header = " | ".join(rel_parts)
                relationship_info = f"- Relationship: {rel_header}\n"
                if rel_reason and rel_reason != rel_path:
                    relationship_info += f"- Relationship Reason: {rel_reason}\n"
                if alt_paths:
                    alt_str = ", ".join(alt_paths)
                    relationship_info += f"- Alternative Paths: {alt_str}\n"

            facts_info = ""
            raw_facts = cand.metadata.get("atomic_code_facts")
            if isinstance(raw_facts, list) and raw_facts:
                fact_lines = []
                for f in raw_facts[:4]:
                    if isinstance(f, dict) and f.get("statement"):
                        ftype = f.get("fact_type", "BEHAVIOR")
                        uncertain_tag = " (uncertain)" if f.get("is_uncertain") else ""
                        fact_lines.append(f"  * \"{f['statement']}\" [{ftype}]{uncertain_tag}")
                    elif isinstance(f, str):
                        fact_lines.append(f"  * \"{f}\"")
                if fact_lines:
                    facts_info = "- Grounded Semantic Facts:\n" + "\n".join(fact_lines) + "\n"

            rels_info = ""
            raw_rels = cand.metadata.get("temporal_relations")
            if isinstance(raw_rels, list) and raw_rels:
                rel_lines = []
                for rel in raw_rels[:4]:
                    if isinstance(rel, dict) and rel.get("subject") and rel.get("relation"):
                        subj = rel.get("canonical_subject") or rel.get("subject")
                        r_type = rel.get("relation")
                        obj = rel.get("canonical_object") or rel.get("object")
                        t_s = rel.get("t_start")
                        t_e = rel.get("t_end")
                        time_str = f" [t_start: {t_s or 'None'}, t_end: {t_e or 'None'}]"
                        conflict_tag = " (conflict)" if rel.get("has_temporal_conflict") else ""
                        uncertain_tag = " (uncertain)" if rel.get("is_uncertain") and not conflict_tag else ""
                        ended_tag = " (ended)" if t_e else ""
                        rel_lines.append(f"  * ({subj}, {r_type}, {obj}){time_str}{conflict_tag}{uncertain_tag}{ended_tag}")
                    elif isinstance(rel, str):
                        rel_lines.append(f"  * {rel}")
                if rel_lines:
                    rels_info = "- Grounded Temporal Relations:\n" + "\n".join(rel_lines) + "\n"

            scope_parts = []
            repo_id = cand.metadata.get("repository_id")
            snap_id = cand.metadata.get("snapshot_id")
            if repo_id:
                scope_parts.append(f"Repo: {repo_id}")
            if snap_id:
                scope_parts.append(f"Snapshot: {snap_id}")
            scope_info = f"- Scope: {' | '.join(scope_parts)}\n" if scope_parts else ""

            candidate_section = (
                f"### [{cand.entity_type}] {cand.path}\n"
                f"- Entity: {cand.name} (Lines {cand.start_line}-{cand.end_line})\n"
                f"{scope_info}"
                f"{temporal_status}"
                f"{commit_info}"
                f"{relationship_info}"
                f"{facts_info}"
                f"{rels_info}"
                f"- Relevance Score: {r.score}\n"
                f"- Code / Evidence Snippet:\n"
                f"```\n{truncated_content}\n```\n"
            )

            # Check budget
            if current_chars + len(candidate_section) > char_budget and used_count >= 3:
                # Always allow at least 3 candidates even if tight
                break

            sections.append(candidate_section)
            current_chars += len(candidate_section)
            used_count += 1

            # Prepare structured evidence item
            evidence_item: dict[str, Any] = {
                "type": cand.entity_type.lower(),
                "file": cand.path,
                "symbol": cand.name if cand.entity_type in ("SYMBOL", "CHUNK") else None,
                "lines": f"{cand.start_line}-{cand.end_line}",
                "relevance": r.score,
                "snippet": cand.content[:200],
            }
            if cand.file_id:
                evidence_item["file_id"] = str(cand.file_id)
            if cand.symbol_id:
                evidence_item["symbol_id"] = str(cand.symbol_id)

            if cand.metadata:
                for k in (
                    "repository_id",
                    "snapshot_id",
                    "commit_sha",
                    "commit_message",
                    "fingerprint",
                    "provenance",
                    "chunk_type",
                    "committed_at",
                    "is_superseded",
                    "is_current",
                    "is_deleted",
                    "superseded_by_sha",
                    "superseded_by_date",
                    "renamed_from",
                    "renamed_to",
                    "relationship_path",
                    "relationship_type",
                    "relationship_hop",
                    "connected_from",
                    "retrieval_reason",
                    "alternative_paths",
                    "atomic_code_facts",
                    "temporal_relations",
                ):
                    if k in cand.metadata and cand.metadata[k] is not None:
                        evidence_item[k] = _json_safe(cand.metadata[k])

            evidence_items.append(evidence_item)

            if cand.name and cand.name not in ("dependency", "import"):
                related_entities.add(cand.name)

        # -------------------------------------------------------------
        # 3. Assemble Unified Prompt Context
        # -------------------------------------------------------------
        context_parts = []
        if proof_chain_sections:
            context_parts.append("## EVOREASONER GROUNDED PROOF CHAINS\n" + "\n".join(proof_chain_sections))

        if evidence_path_sections:
            context_parts.append("## STRUCTURE-AWARE STAR-RAG EVIDENCE PATHS\n" + "\n".join(evidence_path_sections))

        if sections:
            if proof_chain_sections or evidence_path_sections:
                context_parts.append("## REPOSITORY CODE EVIDENCE\n" + "\n".join(sections))
            else:
                context_parts.append("\n".join(sections))

        final_prompt_context = (
            "\n\n".join(context_parts)
            if context_parts
            else "No specific code evidence retrieved for this query."
        )

        return AssembledContext(
            prompt_context=final_prompt_context,
            evidence_items=evidence_items,
            related_entities=sorted(related_entities),
            total_characters=len(final_prompt_context),
            candidate_count=used_count,
            proof_chains=formatted_proof_chains,
            proof_chain_count=len(formatted_proof_chains),
            evidence_paths=formatted_evidence_paths,
            evidence_path_count=len(formatted_evidence_paths),
        )
