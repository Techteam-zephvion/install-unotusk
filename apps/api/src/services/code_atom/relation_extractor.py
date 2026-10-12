import asyncio
import hashlib
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    CodeChangeType,
    FactConfidence,
    FactType,
    RelationType,
    SemanticCodeFact,
    TemporalCodeRelation,
)
from apps.api.src.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Pattern recognizers for code relationships
CALL_PATTERN = re.compile(r"([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\(")
STANDALONE_CALL_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]{3,})\((.*?)\)")
IMPORT_FROM_PATTERN = re.compile(r"from\s+([A-Za-z0-9_.]+)\s+import\s+([A-Za-z0-9_,\s*]+)")
IMPORT_SIMPLE_PATTERN = re.compile(r"import\s+([A-Za-z0-9_.]+)")
CLASS_INHERIT_PATTERN = re.compile(r"class\s+([A-Za-z0-9_]+)\s*\(\s*([A-Za-z0-9_.]+)\s*\)\s*:")
DEF_PATTERN = re.compile(r"(?:def|async\s+def|function|func)\s+([A-Za-z0-9_]+)")
RAISE_PATTERN = re.compile(r"raise\s+([A-Za-z0-9_]+)")
THROW_PATTERN = re.compile(r"throw\s+new\s+([A-Za-z0-9_]+)")
CONFIG_KEY_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*:")


def parse_iso_timestamp(ts_val: Any) -> datetime | None:
    """
    Safely parses timestamp from datetime or ISO string.
    Never fabricates timestamps; returns None on missing or invalid input.
    """
    if ts_val is None:
        return None
    if isinstance(ts_val, datetime):
        return ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=UTC)
    if isinstance(ts_val, str) and ts_val.strip():
        cleaned = ts_val.strip()
        try:
            dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return None
    return None


def generate_relation_fingerprint(
    commit_sha: str | None,
    file_path: str | None,
    subject: str,
    relation: RelationType | str,
    target_object: str,
    t_start: datetime | None = None,
    t_end: datetime | None = None,
    t_obs: datetime | None = None,
) -> str:
    """Computes a deterministic, collision-resistant fingerprint for a temporal code relation."""
    norm_subj = re.sub(r"\s+", " ", subject.strip().lower())
    norm_rel = (
        relation.value if isinstance(relation, RelationType) else str(relation)
    ).strip().upper()
    norm_obj = re.sub(r"\s+", " ", target_object.strip().lower())
    clean_path = (file_path or "").replace("\\", "/").strip().lower()
    c_sha = (commit_sha or "").strip().lower()
    t_s_str = t_start.isoformat() if t_start else "none"
    t_e_str = t_end.isoformat() if t_end else "none"
    t_o_str = t_obs.isoformat() if t_obs else "none"

    content = f"{c_sha}:{clean_path}:{norm_subj}:{norm_rel}:{norm_obj}:{t_s_str}:{t_e_str}:{t_o_str}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_relation_id(fingerprint: str) -> str:
    """Generates a stable, reproducible relation ID from its fingerprint."""
    return f"rel-code-{fingerprint[:16]}"


def deduplicate_relations(relations: list[TemporalCodeRelation]) -> list[TemporalCodeRelation]:
    """Deduplicates a list of temporal relations based on their deterministic fingerprint."""
    seen: set[str] = set()
    deduped: list[TemporalCodeRelation] = []
    for rel in relations:
        if rel.fingerprint not in seen:
            seen.add(rel.fingerprint)
            deduped.append(rel)
    return deduped


def validate_grounded_relation_tokens(
    subject: str,
    target_object: str,
    raw_content: str,
    file_path: str | None = None,
    symbol_name: str | None = None,
    fact_statement: str | None = None,
) -> bool:
    """
    Validates that subject and object tokens mentioned in the relation
    have ground-truth presence in the raw diff, file path, symbol name, or fact statement.
    Prevents LLM hallucinations of non-existent methods, APIs, or libraries.
    """
    ignore_words = {
        "this", "that", "with", "when", "then", "from", "into", "over", "under",
        "service", "function", "method", "class", "module", "file", "logic",
        "value", "record", "updates", "checks", "returns", "raises", "allows",
        "defines", "calls", "saves", "marks", "imports", "renamed", "removed",
        "deleted", "payload", "result", "condition", "bypass", "format", "fails",
        "error", "exception", "handler", "configures", "configuration", "status",
        "token", "email", "dirty", "user", "active", "admin", "role", "check",
        "none", "self", "cls", "true", "false", "null", "undefined",
    }

    content_pool = f"{raw_content} {file_path or ''} {symbol_name or ''} {fact_statement or ''}".lower()

    for term in (subject, target_object):
        cleaned_term = term.strip("`'\" \t\r\n")
        # Extract alphanumeric candidate words
        words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", cleaned_term)
        for w in words:
            w_lower = w.lower()
            if w_lower in ignore_words:
                continue
            # If word is significant (length >= 4 or capitalized) and not in pool, reject
            if (len(w) >= 4 or w[0].isupper()) and w_lower not in content_pool:
                return False

    return True


def normalize_relation_name(raw: str) -> RelationType:
    """
    Normalizes arbitrary relation strings into standard affirmative RelationType enum.
    Removals/negations are affirmatively normalized (e.g. 'stops_calling' -> CALLS).
    """
    cleaned = raw.strip().upper()
    if cleaned in RelationType.__members__:
        return RelationType[cleaned]

    cleaned_lower = raw.strip().lower()

    if any(k in cleaned_lower for k in ("call", "invoke", "dispatch")):
        return RelationType.CALLS
    if any(k in cleaned_lower for k in ("import", "require", "include")):
        return RelationType.IMPORTS
    if any(k in cleaned_lower for k in ("define", "declare", "implement")):
        return RelationType.DEFINES
    if any(k in cleaned_lower for k in ("inherit", "extend", "subclass", "base")):
        return RelationType.INHERITS
    if any(k in cleaned_lower for k in ("mutate", "update", "set_", "modify", "touch")):
        return RelationType.MUTATES
    if any(k in cleaned_lower for k in ("config", "setting", "env")):
        return RelationType.CONFIGURES
    if any(k in cleaned_lower for k in ("validat", "check", "verify", "guard")):
        return RelationType.VALIDATES
    if any(k in cleaned_lower for k in ("raise", "throw", "error", "except")):
        return RelationType.RAISES

    return RelationType.REFERENCES


class TemporalRelationExtractor:
    """
    Module 2: Temporal 5-Tuple Extraction (Code Lane).
    Extracts structured (subject, relation, object, t_start, t_end) code relationships
    grounded in AtomicCodeChange and SemanticCodeFact units.
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider

    def extract_relations_from_facts(
        self,
        facts: list[SemanticCodeFact],
        change: AtomicCodeChange,
        commit_time: datetime | None = None,
    ) -> list[TemporalCodeRelation]:
        """
        Extracts temporal 5-tuples from Module 1 SemanticCodeFact units.
        Enforces:
        - Affirmative relation normalization for removals.
        - Separation of t_obs, t_start, t_end.
        - Missing timestamps remain explicitly None.
        - Deletions are never represented as active behavior.
        """
        relations: list[TemporalCodeRelation] = []

        # Resolve observation timestamp from parameter or change provenance
        t_obs: datetime | None = commit_time
        if t_obs is None and change.provenance:
            t_obs = parse_iso_timestamp(change.provenance.get("committed_at"))

        file_path = change.file_path
        symbol_name = change.symbol_name
        commit_sha = change.commit_sha
        base_file = os.path.basename(file_path)
        default_subject = symbol_name if symbol_name else base_file

        for fact in facts:
            stmt = fact.statement.strip()
            fact_type = fact.fact_type
            source_fact_id = fact.id
            is_removal = (
                fact_type == FactType.REMOVAL
                or change.change_type == CodeChangeType.DELETE
            )

            # Determine temporal boundaries
            if is_removal:
                # Ceased validity: t_end is verified at t_obs; prior t_start is unverified
                t_start = None
                t_end = t_obs
            elif change.change_type == CodeChangeType.ADD:
                # Newly introduced: t_start is verified at t_obs; currently active (t_end=None)
                t_start = t_obs
                t_end = None
            else:
                # MODIFY
                if fact_type == FactType.REMOVAL:
                    t_start = None
                    t_end = t_obs
                else:
                    t_start = t_obs
                    t_end = None

            # 1. REMOVAL facts
            if fact_type == FactType.REMOVAL:
                if "Removed file" in stmt:
                    # File removal: affirmative relation DEFINES ending at t_end
                    subj = base_file
                    rel_type = RelationType.DEFINES
                    obj = symbol_name or base_file
                else:
                    # Check what logic was removed
                    rel_type = RelationType.REFERENCES
                    obj = "logic"
                    # Try to parse removed call or import
                    call_m = CALL_PATTERN.search(stmt)
                    if call_m:
                        rel_type = RelationType.CALLS
                        obj = call_m.group(1)
                    elif "import" in stmt.lower():
                        rel_type = RelationType.IMPORTS
                        words = re.findall(r"`([^`]+)`", stmt)
                        obj = words[0] if words else "module"
                    elif "defines" in stmt.lower() or "function" in stmt.lower():
                        rel_type = RelationType.DEFINES
                        words = re.findall(r"`([^`]+)`", stmt)
                        obj = words[0] if words else "symbol"

                    subj = default_subject

                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=obj,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

            # 2. RELATIONSHIP facts (imports, calls, persistence)
            if fact_type == FactType.RELATIONSHIP:
                # Check import statement
                if "imports module" in stmt:
                    mod_m = re.search(r"imports module `([^`]+)`", stmt)
                    obj = mod_m.group(1).strip() if mod_m else "module"
                    subj = file_path
                    rel_type = RelationType.IMPORTS
                elif "calls `" in stmt:
                    call_m = re.search(r"calls `([^`]+)`", stmt)
                    call_str = call_m.group(1).strip() if call_m else ""
                    # If format is receiver.method(...)
                    if "." in call_str:
                        target_recv = call_str.split(".")[0].strip()
                        obj = target_recv
                    else:
                        obj = call_str
                    subj = default_subject
                    rel_type = RelationType.CALLS
                elif "persists" in stmt:
                    record_m = re.search(r"persists ([A-Za-z0-9_]+) record", stmt)
                    obj = record_m.group(1).strip() if record_m else "record"
                    subj = default_subject
                    rel_type = RelationType.MUTATES
                else:
                    subj = default_subject
                    rel_type = RelationType.REFERENCES
                    obj = "referenced_entity"

                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=obj,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

            # 3. STATE_CHANGE facts
            if fact_type == FactType.STATE_CHANGE:
                words = re.findall(r"`([^`]+)`", stmt)
                target_obj = words[0] if words else "state"
                if "." in target_obj:
                    target_obj = target_obj.split(".")[0]
                subj = default_subject
                rel_type = RelationType.MUTATES
                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=target_obj,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=target_obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

            # 4. ERROR_HANDLING facts (raises / throws)
            if fact_type == FactType.ERROR_HANDLING:
                exc_m = re.search(r"raises `([^`]+)`", stmt)
                exc_obj = exc_m.group(1).strip() if exc_m else "Exception"
                subj = default_subject
                rel_type = RelationType.RAISES
                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=exc_obj,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=exc_obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

            # 5. VALIDATION facts
            if fact_type == FactType.VALIDATION:
                cond_m = re.search(r"when `([^`]+)`", stmt)
                cond_obj = cond_m.group(1).strip() if cond_m else "validation_condition"
                subj = default_subject
                rel_type = RelationType.VALIDATES
                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=cond_obj,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=cond_obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

            # 6. CONFIGURATION facts
            if fact_type == FactType.CONFIGURATION:
                cfg_m = re.search(r"configures `([^`]+)`", stmt)
                cfg_key = cfg_m.group(1).strip() if cfg_m else "config_key"
                subj = file_path
                rel_type = RelationType.CONFIGURES
                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=cfg_key,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=cfg_key,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

            # 7. STRUCTURAL / BEHAVIOR definitions
            if "defines `" in stmt or "declares function `" in stmt:
                fn_m = re.search(r"(?:defines|declares function) `([^`]+)`", stmt)
                fn_name = fn_m.group(1).strip() if fn_m else "function"
                subj = file_path
                rel_type = RelationType.DEFINES
                fp = generate_relation_fingerprint(
                    commit_sha=commit_sha,
                    file_path=file_path,
                    subject=subj,
                    relation=rel_type,
                    target_object=fn_name,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subj,
                        relation=rel_type,
                        object=fn_name,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=fact.confidence,
                        is_uncertain=fact.is_uncertain,
                        source_fact_id=source_fact_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(fact.provenance),
                        fingerprint=fp,
                    )
                )
                continue

        return deduplicate_relations(relations)

    def extract_relations_deterministic(
        self,
        change: AtomicCodeChange,
        commit_time: datetime | None = None,
    ) -> list[TemporalCodeRelation]:
        """
        Derives comprehensive, grounded temporal code relationships from an AtomicCodeChange
        unit and its SemanticCodeFacts using deterministic AST, pattern, and lexical analysis.
        """
        relations: list[TemporalCodeRelation] = []

        # Resolve observation timestamp
        t_obs: datetime | None = commit_time
        if t_obs is None and change.provenance:
            t_obs = parse_iso_timestamp(change.provenance.get("committed_at"))

        file_path = change.file_path
        symbol_name = change.symbol_name
        commit_sha = change.commit_sha
        base_file = os.path.basename(file_path)
        subject = symbol_name if symbol_name else base_file
        change_type = change.change_type

        # 1. First extract relations grounded in semantic facts if present
        if change.atomic_facts:
            fact_relations = self.extract_relations_from_facts(
                change.atomic_facts, change, commit_time=t_obs
            )
            relations.extend(fact_relations)

        # 2. Deletion of entire file
        if change_type == CodeChangeType.DELETE:
            t_start = None
            t_end = t_obs
            rel_type = RelationType.DEFINES
            obj = symbol_name or base_file
            fp = generate_relation_fingerprint(
                commit_sha, file_path, base_file, rel_type, obj, t_start, t_end, t_obs
            )
            relations.append(
                TemporalCodeRelation(
                    id=generate_relation_id(fp),
                    subject=base_file,
                    relation=rel_type,
                    object=obj,
                    t_start=t_start,
                    t_end=t_end,
                    t_obs=t_obs,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    symbol_name=symbol_name,
                    provenance=dict(change.provenance),
                    fingerprint=fp,
                )
            )
            return deduplicate_relations(relations)

        # 3. Direct inspection of added lines
        for line in change.added_lines:
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("//"):
                continue

            t_start = t_obs
            t_end = None

            # A. Method call: receiver.method(...)
            for match in CALL_PATTERN.finditer(clean):
                receiver = match.group(1)
                method = match.group(2)
                # Ignore self, cls, this
                target_obj = receiver if receiver not in ("self", "cls", "this") else method
                rel_type = RelationType.CALLS
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, subject, rel_type, target_obj, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subject,
                        relation=rel_type,
                        object=target_obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

            # B. Standalone call: foo(bar)
            standalone_m = STANDALONE_CALL_PATTERN.match(clean)
            if standalone_m:
                fn_called = standalone_m.group(1)
                if fn_called not in ("if", "for", "while", "return", "def", "class", "print"):
                    rel_type = RelationType.CALLS
                    fp = generate_relation_fingerprint(
                        commit_sha, file_path, subject, rel_type, fn_called, t_start, t_end, t_obs
                    )
                    relations.append(
                        TemporalCodeRelation(
                            id=generate_relation_id(fp),
                            subject=subject,
                            relation=rel_type,
                            object=fn_called,
                            t_start=t_start,
                            t_end=t_end,
                            t_obs=t_obs,
                            confidence=FactConfidence.HIGH,
                            is_uncertain=False,
                            commit_sha=commit_sha,
                            file_path=file_path,
                            symbol_name=symbol_name,
                            provenance=dict(change.provenance),
                            fingerprint=fp,
                        )
                    )

            # C. Class inheritance: class Foo(Bar):
            inherit_m = CLASS_INHERIT_PATTERN.search(clean)
            if inherit_m:
                child_cls = inherit_m.group(1)
                parent_cls = inherit_m.group(2)
                rel_type = RelationType.INHERITS
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, child_cls, rel_type, parent_cls, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=child_cls,
                        relation=rel_type,
                        object=parent_cls,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

            # D. Import statements
            imp_from_m = IMPORT_FROM_PATTERN.search(clean)
            if imp_from_m:
                mod_name = imp_from_m.group(1).strip()
                rel_type = RelationType.IMPORTS
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, file_path, rel_type, mod_name, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=file_path,
                        relation=rel_type,
                        object=mod_name,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

            imp_simp_m = IMPORT_SIMPLE_PATTERN.search(clean)
            if imp_simp_m and not imp_from_m:
                mod_name = imp_simp_m.group(1).strip()
                rel_type = RelationType.IMPORTS
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, file_path, rel_type, mod_name, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=file_path,
                        relation=rel_type,
                        object=mod_name,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

            # E. Function definitions
            def_m = DEF_PATTERN.search(clean)
            if def_m:
                fn_name = def_m.group(1)
                rel_type = RelationType.DEFINES
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, file_path, rel_type, fn_name, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=file_path,
                        relation=rel_type,
                        object=fn_name,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

            # F. Raises
            raise_m = RAISE_PATTERN.search(clean) or THROW_PATTERN.search(clean)
            if raise_m:
                exc_name = raise_m.group(1)
                rel_type = RelationType.RAISES
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, subject, rel_type, exc_name, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subject,
                        relation=rel_type,
                        object=exc_name,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

        # 4. Direct inspection of deleted lines (Removals -> affirmative relations with t_end)
        for line in change.deleted_lines:
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("//"):
                continue

            # Ended relationship: t_start is None (unverified prior start), t_end is t_obs
            t_start = None
            t_end = t_obs

            # A. Deleted calls
            for match in CALL_PATTERN.finditer(clean):
                receiver = match.group(1)
                method = match.group(2)
                target_obj = receiver if receiver not in ("self", "cls", "this") else method
                rel_type = RelationType.CALLS
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, subject, rel_type, target_obj, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=subject,
                        relation=rel_type,
                        object=target_obj,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

            # B. Deleted imports
            imp_from_m = IMPORT_FROM_PATTERN.search(clean)
            if imp_from_m:
                mod_name = imp_from_m.group(1).strip()
                rel_type = RelationType.IMPORTS
                fp = generate_relation_fingerprint(
                    commit_sha, file_path, file_path, rel_type, mod_name, t_start, t_end, t_obs
                )
                relations.append(
                    TemporalCodeRelation(
                        id=generate_relation_id(fp),
                        subject=file_path,
                        relation=rel_type,
                        object=mod_name,
                        t_start=t_start,
                        t_end=t_end,
                        t_obs=t_obs,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        provenance=dict(change.provenance),
                        fingerprint=fp,
                    )
                )

        return deduplicate_relations(relations)

    async def extract_relations_async(
        self,
        change: AtomicCodeChange,
        commit_time: datetime | None = None,
        use_llm: bool = True,
        max_concurrency: int = 4,
    ) -> list[TemporalCodeRelation]:
        """
        Extracts temporal code relationships asynchronously with optional LLM grounding expansion.
        Falls back safely and completely to deterministic extraction if LLM is offline,
        unavailable, produces malformed/ungrounded output, or raises any error.
        """
        deterministic_relations = self.extract_relations_deterministic(
            change, commit_time=commit_time
        )

        if not use_llm:
            return deterministic_relations

        provider = self.llm_provider
        if provider is None:
            try:
                from apps.api.src.config.settings import settings
                from apps.api.src.services.llm.factory import get_llm_provider

                provider_name = (settings.LLM_PROVIDER or "offline").strip().lower()
                if provider_name != "offline":
                    provider = get_llm_provider(provider_name)
            except Exception as e:
                logger.debug(f"LLM provider resolution skipped for relations: {e}")
                provider = None

        if provider is None:
            return deterministic_relations

        semaphore = asyncio.Semaphore(max(1, max_concurrency))
        try:
            async with semaphore:
                llm_relations = await self._extract_relations_llm(
                    change, provider, commit_time=commit_time
                )
                if llm_relations:
                    # Combine LLM relations with deterministic relations and deduplicate
                    combined = list(deterministic_relations)
                    combined.extend(llm_relations)
                    return deduplicate_relations(combined)
        except Exception as exc:
            logger.warning(
                f"LLM temporal relation extraction failed for {change.file_path}: {exc}. "
                "Degrading safely to deterministic relations."
            )

        return deterministic_relations

    async def _extract_relations_llm(
        self,
        change: AtomicCodeChange,
        provider: LLMProvider,
        commit_time: datetime | None = None,
    ) -> list[TemporalCodeRelation]:
        """
        Calls configured LLM to extract structured code relationships with temporal validity,
        enforcing affirmative normalization, anti-hallucination token checking, and timestamp rules.
        """
        system_prompt = (
            "You are an authoritative temporal code-relationship extractor for the ATOM intelligence engine (Module 2).\n"
            "Given a code change and its semantic facts, extract structured code relationships with temporal validity.\n"
            "RULES:\n"
            "1. 5-Tuple Structure: (subject, relation, object, t_start, t_end).\n"
            "2. Affirmative Normalization: Ended/removed relationships MUST use affirmative relation names "
            "(e.g. CALLS, DEFINES, IMPORTS, INHERITS) with t_end set to the commit timestamp, NEVER negative relation names (such as stops_calling or deletes).\n"
            "3. Zero Fabrication: If validity start time is not verified by this commit (e.g. deleted or modified code whose creation is not in this commit), t_start MUST be null. NEVER invent dates.\n"
            "4. Grounding: Subject and object MUST exist in the provided diff, file path, symbol, or facts. Do not invent entities.\n"
            "5. Format: Return JSON strictly adhering to schema:\n"
            "{\n"
            '  "relations": [\n'
            "    {\n"
            '      "subject": "string",\n'
            '      "relation": "CALLS | DEFINES | IMPORTS | INHERITS | MUTATES | CONFIGURES | VALIDATES | RAISES | REFERENCES",\n'
            '      "object": "string",\n'
            '      "t_start": "ISO timestamp or null",\n'
            '      "t_end": "ISO timestamp or null",\n'
            '      "confidence": "HIGH | MEDIUM | UNCERTAIN",\n'
            '      "is_uncertain": false\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        t_obs: datetime | None = commit_time
        if t_obs is None and change.provenance:
            t_obs = parse_iso_timestamp(change.provenance.get("committed_at"))

        facts_text = ""
        if change.atomic_facts:
            facts_text = "\nSemantic Facts:\n" + "\n".join(
                f"- {f.statement} [{f.fact_type.value}]" for f in change.atomic_facts[:5]
            )

        user_prompt = (
            f"File: {change.file_path}\n"
            f"Symbol: {change.symbol_name or 'None'}\n"
            f"Change Type: {change.change_type.value}\n"
            f"Commit Message: {change.commit_message}\n"
            f"Observation Timestamp (t_obs): {t_obs.isoformat() if t_obs else 'null'}\n"
            f"Raw Diff:\n```\n{change.raw_content}\n```\n"
            f"{facts_text}\n"
        )

        res = await provider.generate_json(system_prompt, user_prompt)
        raw_relations = res.get("relations", []) if isinstance(res, dict) else []
        if not raw_relations or not isinstance(raw_relations, list):
            return []

        validated: list[TemporalCodeRelation] = []
        base_prov = dict(change.provenance)
        base_prov["atom_id"] = change.id
        base_prov["change_fingerprint"] = change.fingerprint
        base_prov["source"] = "llm_grounded"

        for rr in raw_relations:
            if not isinstance(rr, dict) or not rr.get("subject") or not rr.get("object"):
                continue

            subj = str(rr["subject"]).strip()
            obj = str(rr["object"]).strip()
            raw_rel = str(rr.get("relation", "REFERENCES")).strip()

            # Anti-hallucination validation
            if not validate_grounded_relation_tokens(
                subj, obj, change.raw_content, change.file_path, change.symbol_name
            ):
                logger.warning(
                    f"Rejecting ungrounded LLM temporal relation: ({subj}, {raw_rel}, {obj})"
                )
                continue

            # Normalize relation name affirmatively
            rel_type = normalize_relation_name(raw_rel)

            # Parse timestamps strictly without fabrication
            parsed_t_start = parse_iso_timestamp(rr.get("t_start"))
            parsed_t_end = parse_iso_timestamp(rr.get("t_end"))

            # If removal or deletion, enforce affirmative relation with t_end set to t_obs and t_start None
            if (
                change.change_type == CodeChangeType.DELETE
                or any(k in raw_rel.lower() for k in ("stop", "remov", "delet"))
            ):
                parsed_t_end = t_obs
                parsed_t_start = None

            # Parse confidence
            c_str = str(rr.get("confidence", "HIGH")).upper()
            try:
                confidence = FactConfidence(c_str)
            except ValueError:
                confidence = FactConfidence.HIGH

            is_uncertain = bool(rr.get("is_uncertain", False))

            fp = generate_relation_fingerprint(
                commit_sha=change.commit_sha,
                file_path=change.file_path,
                subject=subj,
                relation=rel_type,
                target_object=obj,
                t_start=parsed_t_start,
                t_end=parsed_t_end,
                t_obs=t_obs,
            )

            validated.append(
                TemporalCodeRelation(
                    id=generate_relation_id(fp),
                    subject=subj,
                    relation=rel_type,
                    object=obj,
                    t_start=parsed_t_start,
                    t_end=parsed_t_end,
                    t_obs=t_obs,
                    confidence=confidence,
                    is_uncertain=is_uncertain,
                    commit_sha=change.commit_sha,
                    file_path=change.file_path,
                    symbol_name=change.symbol_name,
                    provenance=base_prov,
                    fingerprint=fp,
                )
            )

        return validated
