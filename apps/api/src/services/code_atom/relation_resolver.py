"""
Targeted Code Entity and Relationship Resolution for ATOM Code Lane (Module 2).
Provides:
1. Stable entity identity across commits and verified file renames without fuzzy merging.
2. Equivalent relationship label normalization and deterministic deduplication.
3. Safe temporal reconciliation retaining verified start/end timestamps and flagging conflicts.
4. Idempotent processing and complete provenance preservation.
"""

import hashlib
import logging
from datetime import datetime

from apps.api.src.schemas.code_atom import (
    FactConfidence,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom.relation_extractor import (
    normalize_relation_name,
)

logger = logging.getLogger(__name__)


def canonicalize_file_path(
    file_path: str | None,
    rename_history: dict[str, str] | None = None,
) -> str:
    """
    Normalizes a file path and resolves it across any known rename chain.
    Stable across OS separators and case.
    """
    if not file_path:
        return ""
    clean = file_path.replace("\\", "/").strip().lower().lstrip("/")
    if not rename_history:
        return clean

    # Walk rename history safely avoiding cycles
    curr = clean
    visited = set()
    norm_renames = {
        k.replace("\\", "/").strip().lower().lstrip("/"): v.replace("\\", "/").strip().lower().lstrip("/")
        for k, v in rename_history.items()
    }
    while curr in norm_renames and curr not in visited:
        visited.add(curr)
        curr = norm_renames[curr]
    return curr


class CodeEntityResolver:
    """
    Maintains stable code entity identity across commits and file renames.
    Enforces conservative matching: NEVER merges distinct symbols merely because
    names or embeddings are similar.
    """

    @staticmethod
    def build_qualified_identifier(
        name: str,
        file_path: str | None = None,
        rename_history: dict[str, str] | None = None,
    ) -> str:
        """
        Builds a canonical, collision-resistant identifier for a code symbol or module.
        Format: `<canonical_path>::<symbol_name>` when path is available, otherwise bare name.
        """
        trimmed = name.strip()
        if "::" in trimmed:
            raw_path, sym = trimmed.split("::", 1)
            canon_p = canonicalize_file_path(raw_path, rename_history)
            return f"{canon_p}::{sym.strip()}"

        if file_path:
            canon_p = canonicalize_file_path(file_path, rename_history)
            if canon_p:
                return f"{canon_p}::{trimmed}"

        return trimmed

    @classmethod
    def resolve_entity(
        cls,
        name: str,
        file_path: str | None = None,
        rename_history: dict[str, str] | None = None,
    ) -> tuple[str, list[str]]:
        """
        Resolves an entity to its canonical qualified name and returns all historical aliases.
        """
        trimmed = name.strip()
        aliases: list[str] = []

        if not trimmed:
            return "", []

        canonical_id = cls.build_qualified_identifier(trimmed, file_path, rename_history)

        # Record bare name as alias if qualified
        if "::" in canonical_id:
            bare_name = canonical_id.split("::")[-1]
            if bare_name != canonical_id:
                aliases.append(bare_name)

        # Record original pre-rename identifier if rename occurred
        if file_path and rename_history:
            orig_id = cls.build_qualified_identifier(trimmed, file_path, rename_history=None)
            if orig_id != canonical_id and orig_id not in aliases:
                aliases.append(orig_id)

        # If name itself had an old path that was renamed
        if "::" in trimmed and rename_history:
            if trimmed != canonical_id and trimmed not in aliases:
                aliases.append(trimmed)

        return canonical_id, aliases

    @classmethod
    def are_entities_equivalent(
        cls,
        entity_a: str,
        entity_b: str,
        rename_history: dict[str, str] | None = None,
    ) -> bool:
        """
        Conservatively checks if two entity representations refer to the exact same symbol.
        Distinct symbols with similar names (e.g. authenticate_token vs authenticate_user)
        MUST NOT be merged.
        """
        if not entity_a or not entity_b:
            return False

        norm_a = cls.build_qualified_identifier(entity_a, rename_history=rename_history).lower()
        norm_b = cls.build_qualified_identifier(entity_b, rename_history=rename_history).lower()

        if norm_a == norm_b:
            return True

        # If both are bare names without file paths, only exact equality counts
        if "::" not in norm_a and "::" not in norm_b:
            return norm_a == norm_b

        # If one is qualified and one is bare, check if symbol part matches exactly
        # ONLY if the bare name is an exact match for the symbol part
        sym_a = norm_a.split("::")[-1]
        sym_b = norm_b.split("::")[-1]
        if sym_a != sym_b:
            # Different symbol names: NEVER equivalent!
            return False

        # If symbol names are identical, check if file paths match under renames
        path_a = norm_a.split("::")[0] if "::" in norm_a else None
        path_b = norm_b.split("::")[0] if "::" in norm_b else None

        if path_a and path_b:
            canon_a = canonicalize_file_path(path_a, rename_history)
            canon_b = canonicalize_file_path(path_b, rename_history)
            return canon_a == canon_b

        # One qualified, one bare: do not guess across files unless explicitly aliased
        return False


def generate_reconciled_fingerprint(
    canonical_subject: str,
    relation: RelationType | str,
    canonical_object: str,
    t_start: datetime | None = None,
    t_end: datetime | None = None,
    t_obs: datetime | None = None,
) -> str:
    """Computes a deterministic, collision-resistant fingerprint for a reconciled relationship."""
    subj_norm = canonical_subject.strip().lower()
    rel_norm = (relation.value if isinstance(relation, RelationType) else str(relation)).strip().upper()
    obj_norm = canonical_object.strip().lower()
    t_s_str = t_start.isoformat() if t_start else "none"
    t_e_str = t_end.isoformat() if t_end else "none"
    t_o_str = t_obs.isoformat() if t_obs else "none"

    content = f"rec:{subj_norm}:{rel_norm}:{obj_norm}:{t_s_str}:{t_e_str}:{t_o_str}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class TemporalRelationResolver:
    """
    Module 2: Entity & Relationship Resolution and Temporal Reconciliation.
    Consolidates relationship instances into coherent, chronologically verified representations.
    """

    def __init__(self, rename_history: dict[str, str] | None = None):
        self.rename_history = rename_history or {}
        self.entity_resolver = CodeEntityResolver()

    def reconcile_relations(
        self,
        relations: list[TemporalCodeRelation],
    ) -> list[TemporalCodeRelation]:
        """
        Reconciles a collection of TemporalCodeRelation units across commits or chunks.

        Guarantees:
        1. Equivalent relationship labels are normalized consistently (CALLS, DEFINES, etc.).
        2. Truly identical relationships are deduplicated deterministically.
        3. Verified start and end times are preserved; missing timestamps never overwrite verified ones.
        4. Removals correctly end relationships with t_end without fabricating t_start.
        5. Conflicting temporal evidence (e.g. t_end < t_start) is safely flagged and preserved.
        6. Provenance and source commit history are aggregated and preserved.
        7. Reprocessing is 100% idempotent.
        """
        if not relations:
            return []

        # 1. Resolve canonical identities and group by (canonical_subject, relation, canonical_object)
        grouped: dict[tuple[str, str, str], list[TemporalCodeRelation]] = {}
        for rel in relations:
            canon_subj, _ = self.entity_resolver.resolve_entity(
                name=rel.canonical_subject or rel.subject,
                file_path=rel.file_path,
                rename_history=self.rename_history,
            )
            canon_obj, _ = self.entity_resolver.resolve_entity(
                name=rel.canonical_object or rel.object,
                file_path=None,
                rename_history=self.rename_history,
            )
            norm_rel_type = normalize_relation_name(
                rel.relation.value if isinstance(rel.relation, RelationType) else str(rel.relation)
            )

            group_key = (
                canon_subj.strip().lower(),
                norm_rel_type.value.lower(),
                canon_obj.strip().lower(),
            )
            grouped.setdefault(group_key, []).append(rel)

        reconciled_list: list[TemporalCodeRelation] = []

        # 2. Reconcile each group
        for (_k_subj, _k_rel, _k_obj), group in grouped.items():
            first = group[0]
            canon_subj, subj_aliases = self.entity_resolver.resolve_entity(
                name=first.canonical_subject or first.subject,
                file_path=first.file_path,
                rename_history=self.rename_history,
            )
            canon_obj, obj_aliases = self.entity_resolver.resolve_entity(
                name=first.canonical_object or first.object,
                file_path=None,
                rename_history=self.rename_history,
            )
            norm_rel_type = normalize_relation_name(
                first.relation.value if isinstance(first.relation, RelationType) else str(first.relation)
            )

            # Collect all aliases across group
            all_aliases: list[str] = list(subj_aliases) + list(obj_aliases)
            for item in group:
                all_aliases.extend(item.aliases)
                if item.subject != canon_subj:
                    all_aliases.append(item.subject)
                if item.object != canon_obj:
                    all_aliases.append(item.object)
            deduped_aliases = sorted(set(a for a in all_aliases if a and a not in (canon_subj, canon_obj)))

            # Reconcile Observation Time (t_obs): latest verified observation time
            known_obs = [r.t_obs for r in group if r.t_obs is not None]
            latest_obs = max(known_obs) if known_obs else None

            # Reconcile Start Time (t_start): retain verified introduction time (earliest verified)
            known_starts = [r.t_start for r in group if r.t_start is not None]
            merged_start = min(known_starts) if known_starts else None

            # Reconcile End Time (t_end): retain verified removal/end time (latest verified)
            known_ends = [r.t_end for r in group if r.t_end is not None]
            merged_end = max(known_ends) if known_ends else None

            # Detect and flag conflicting temporal evidence
            has_conflict = False
            conflict_detail = None
            if merged_start is not None and merged_end is not None:
                if merged_end < merged_start:
                    has_conflict = True
                    conflict_detail = (
                        f"Temporal conflict: validity end ({merged_end.isoformat()}) "
                        f"is earlier than start ({merged_start.isoformat()})."
                    )
                    logger.warning(
                        f"Temporal conflict detected for ({canon_subj}, {norm_rel_type.value}, {canon_obj}): "
                        f"{conflict_detail}"
                    )

            # Confidence and uncertainty
            has_uncertain = any(r.is_uncertain for r in group) or has_conflict
            if has_conflict:
                confidence = FactConfidence.UNCERTAIN
            elif all(r.confidence == FactConfidence.HIGH for r in group):
                confidence = FactConfidence.HIGH
            elif any(r.confidence == FactConfidence.UNCERTAIN for r in group):
                confidence = FactConfidence.UNCERTAIN
            else:
                confidence = FactConfidence.MEDIUM

            # Provenance and History aggregation
            all_commit_shas: set[str] = set()
            all_fact_ids: set[str] = set()
            for r in group:
                if r.commit_sha:
                    all_commit_shas.add(r.commit_sha)
                all_commit_shas.update(r.history_commit_shas)
                if r.source_fact_id:
                    all_fact_ids.add(r.source_fact_id)
                all_fact_ids.update(r.history_fact_ids)

            history_shas = sorted(all_commit_shas)
            history_facts = sorted(all_fact_ids)

            # Combined provenance
            base_prov = dict(first.provenance)
            base_prov["resolved_sources_count"] = len(group)
            base_prov["history_commit_shas"] = history_shas
            base_prov["history_fact_ids"] = history_facts
            if has_conflict:
                base_prov["temporal_conflict"] = conflict_detail

            # Generate deterministic fingerprint & ID
            fp = generate_reconciled_fingerprint(
                canonical_subject=canon_subj,
                relation=norm_rel_type,
                canonical_object=canon_obj,
                t_start=merged_start,
                t_end=merged_end,
                t_obs=latest_obs,
            )
            rec_id = f"rel-code-rec-{fp[:16]}"

            reconciled_list.append(
                TemporalCodeRelation(
                    id=rec_id,
                    subject=first.subject,
                    relation=norm_rel_type,
                    object=first.object,
                    t_start=merged_start,
                    t_end=merged_end,
                    t_obs=latest_obs,
                    confidence=confidence,
                    is_uncertain=has_uncertain,
                    source_fact_id=first.source_fact_id,
                    commit_sha=first.commit_sha,
                    file_path=first.file_path,
                    symbol_name=first.symbol_name,
                    canonical_subject=canon_subj,
                    canonical_object=canon_obj,
                    aliases=deduped_aliases,
                    has_temporal_conflict=has_conflict,
                    conflict_detail=conflict_detail,
                    history_commit_shas=history_shas,
                    history_fact_ids=history_facts,
                    provenance=base_prov,
                    fingerprint=fp,
                )
            )

        # Sort deterministically by canonical subject, relation, object
        reconciled_list.sort(
            key=lambda r: (
                (r.canonical_subject or r.subject).lower(),
                (r.relation.value if isinstance(r.relation, RelationType) else str(r.relation)).lower(),
                (r.canonical_object or r.object).lower(),
            )
        )
        return reconciled_list


def reconcile_code_relationships(
    relations: list[TemporalCodeRelation],
    rename_history: dict[str, str] | None = None,
) -> list[TemporalCodeRelation]:
    """
    Top-level helper function to reconcile a collection of temporal code relationships.
    Deduplicates identical relationships, resolves entity identities under renames,
    reconciles validity intervals without erasing known timestamps, and flags conflicts safely.
    """
    resolver = TemporalRelationResolver(rename_history=rename_history)
    return resolver.reconcile_relations(relations)
