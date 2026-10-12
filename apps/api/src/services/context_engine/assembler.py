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


class ContextAssembler:
    @staticmethod
    def assemble_context(
        ranked_candidates: list[RankedCandidate],
        max_tokens: int | None = None,
    ) -> AssembledContext:
        budget_tokens = max_tokens or settings.CONTEXT_BUDGET_TOKENS
        # Approximate 4 characters per token
        char_budget = budget_tokens * 4

        sections: list[str] = []
        evidence_items: list[dict[str, Any]] = []
        related_entities: set[str] = set()

        current_chars = 0
        used_count = 0

        for r in ranked_candidates:
            cand = r.candidate

            # Truncate overly long content (e.g., max 1500 chars per single candidate)
            truncated_content = cand.content[:1500]
            if len(cand.content) > 1500:
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

            candidate_section = (
                f"### [{cand.entity_type}] {cand.path}\n"
                f"- Entity: {cand.name} (Lines {cand.start_line}-{cand.end_line})\n"
                f"{temporal_status}"
                f"{commit_info}"
                f"{relationship_info}"
                f"{facts_info}"
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
            if cand.metadata:
                for k in (
                    "commit_sha",
                    "commit_message",
                    "fingerprint",
                    "provenance",
                    "snapshot_id",
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
                ):
                    if k in cand.metadata and cand.metadata[k] is not None:
                        evidence_item[k] = _json_safe(cand.metadata[k])

            evidence_items.append(evidence_item)

            if cand.name and cand.name not in ("dependency", "import"):
                related_entities.add(cand.name)

        final_prompt_context = (
            "\n".join(sections)
            if sections
            else "No specific code evidence retrieved for this query."
        )

        return AssembledContext(
            prompt_context=final_prompt_context,
            evidence_items=evidence_items,
            related_entities=sorted(related_entities),
            total_characters=len(final_prompt_context),
            candidate_count=used_count,
        )
