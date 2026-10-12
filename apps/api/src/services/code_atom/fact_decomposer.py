import hashlib
import logging
import os
import re

from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    CodeChangeType,
    FactConfidence,
    FactType,
    SemanticCodeFact,
)
from apps.api.src.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Patterns for semantic code fact extraction
GUARD_PATTERN = re.compile(
    r"^\s*if\s+(?:not\s+)?([A-Za-z0-9_.\(\)\'\"\s<>=!]+?)\s*:\s*(?:return\s*(.*)|raise\s*(.*))?$"
)
GUARD_INLINE_RETURN = re.compile(r"^\s*if\s+(.+?)\s*:\s*return(?:\s+(.*))?$")
GUARD_INLINE_RAISE = re.compile(r"^\s*if\s+(.+?)\s*:\s*raise\s+(.+)$")
METHOD_CALL_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\((.*?)\)\s*$")
ASSIGNMENT_CALL_PATTERN = re.compile(r"^\s*(?:[A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\((.*?)\)\s*$")
IMPORT_PATTERN = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))")
RAISE_PATTERN = re.compile(r"^\s*raise\s+([A-Za-z0-9_]+)(?:\((.*?)\))?")
THROW_PATTERN = re.compile(r"^\s*throw\s+new\s+([A-Za-z0-9_]+)(?:\((.*?)\))?")
RETURN_PATTERN = re.compile(r"^\s*return\s+(.+)$")
DEF_PATTERN = re.compile(r"^\s*(?:def|async\s+def|function|func)\s+([A-Za-z0-9_]+)")
CLASS_FIELD_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_\[\],\s]+)\s*=\s*(.+)$")
CONFIG_KEY_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*(.+)$")
SIMPLE_VAR_ASSIGN_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*([+\-*/%]?=)\s*(.+)$")


def generate_fact_fingerprint(
    commit_sha: str,
    file_path: str,
    symbol_name: str | None,
    statement: str,
    fact_type: FactType | str,
) -> str:
    """Computes a deterministic, normalized fingerprint for an atomic code fact."""
    norm_stmt = re.sub(r"\s+", " ", statement.strip().lower())
    clean_path = file_path.replace("\\", "/").strip().lower()
    clean_sym = (symbol_name or "").strip().lower()
    ftype_val = fact_type.value if isinstance(fact_type, FactType) else str(fact_type)
    content = f"{commit_sha.strip().lower()}:{clean_path}:{clean_sym}:{norm_stmt}:{ftype_val}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_fact_id(fingerprint: str) -> str:
    """Generates a stable, reproducible fact ID from its fingerprint."""
    return f"fact-code-{fingerprint[:16]}"


def deduplicate_facts(facts: list[SemanticCodeFact]) -> list[SemanticCodeFact]:
    """Deduplicates a list of facts based on their deterministic fingerprint."""
    seen: set[str] = set()
    deduped: list[SemanticCodeFact] = []
    for fact in facts:
        if fact.fingerprint not in seen:
            seen.add(fact.fingerprint)
            deduped.append(fact)
    return deduped


def validate_grounded_tokens(
    statement: str,
    raw_content: str,
    file_path: str,
    symbol_name: str | None,
) -> bool:
    """
    Validates that specific identifier tokens mentioned in a semantic statement
    have ground-truth presence in the raw diff, file path, or symbol name.
    Prevents LLM hallucinations of non-existent methods, APIs, or libraries.
    """
    # Extract identifiers (CamelCase or snake_case with length >= 4) from statement
    candidates = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", statement)
    # Common English words and keywords to ignore
    ignore_words = {
        "this", "that", "with", "when", "then", "from", "into", "over", "under",
        "service", "function", "method", "class", "module", "file", "logic",
        "value", "record", "updates", "checks", "returns", "raises", "allows",
        "defines", "calls", "saves", "marks", "imports", "renamed", "removed",
        "deleted", "payload", "result", "condition", "bypass", "format", "fails",
        "error", "exception", "handler", "configures", "configuration", "status",
        "token", "email", "dirty", "user", "active", "admin", "role", "check"
    }

    content_lower = f"{raw_content} {file_path} {symbol_name or ''}".lower()

    # 1. Verify all tokens inside backticks
    backticked = re.findall(r"`([^`]+)`", statement)
    for snippet in backticked:
        words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", snippet)
        for w in words:
            if w.lower() in ignore_words:
                continue
            if w.lower() not in content_lower:
                return False

    # 2. Verify any PascalCase / CamelCase class or API names in the statement
    for token in candidates:
        if token.lower() in ignore_words:
            continue
        if token[0].isupper() and any(c.islower() for c in token[1:]) and len(token) >= 5:
            if token.lower() not in content_lower:
                return False

    return True


class SemanticFactExtractor:
    """
    Module 1: Atomic Fact Decomposition (Code Lane).
    Decomposes Git code changes into small, self-contained, semantically meaningful facts
    grounded in actual source modifications.
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider

    def extract_facts_deterministic(self, change: AtomicCodeChange) -> list[SemanticCodeFact]:
        """
        Derives self-contained, grounded semantic facts from an AtomicCodeChange unit
        using deterministic AST, pattern, and lexical analysis.
        """
        facts: list[SemanticCodeFact] = []
        file_path = change.file_path
        symbol_name = change.symbol_name
        commit_sha = change.commit_sha
        commit_message = change.commit_message
        change_type = change.change_type
        base_file = os.path.basename(file_path)
        subject = symbol_name if symbol_name else base_file
        ext = os.path.splitext(file_path)[1].lower()
        is_config = ext in (".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".env")

        base_prov = dict(change.provenance)
        base_prov["atom_id"] = change.id
        base_prov["change_fingerprint"] = change.fingerprint

        # 1. Pure File Deletions
        if change_type == CodeChangeType.DELETE:
            stmt = f"Removed file `{file_path}`."
            fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.REMOVAL)
            return [
                SemanticCodeFact(
                    id=generate_fact_id(fp),
                    statement=stmt,
                    fact_type=FactType.REMOVAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    file_path=file_path,
                    symbol_name=symbol_name,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    change_type=change_type,
                    evidenced_lines=change.deleted_lines[:5],
                    provenance=base_prov,
                    fingerprint=fp,
                )
            ]

        # 2. File Renames
        if change_type == CodeChangeType.RENAME:
            old_p = change.old_file_path or "original file"
            stmt = f"Renamed `{old_p}` to `{file_path}`."
            fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.STRUCTURAL)
            return [
                SemanticCodeFact(
                    id=generate_fact_id(fp),
                    statement=stmt,
                    fact_type=FactType.STRUCTURAL,
                    confidence=FactConfidence.HIGH,
                    is_uncertain=False,
                    file_path=file_path,
                    symbol_name=symbol_name,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    change_type=change_type,
                    evidenced_lines=[],
                    provenance=base_prov,
                    fingerprint=fp,
                )
            ]

        # 3. Modify with ONLY deleted lines (Removal of specific logic)
        if not change.added_lines and change.deleted_lines:
            for del_line in change.deleted_lines:
                clean_del = del_line.strip()
                if not clean_del or clean_del.startswith("#") or clean_del.startswith("//"):
                    continue
                stmt = f"{subject} removed logic: `{clean_del}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.REMOVAL)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.REMOVAL,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[del_line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
            return deduplicate_facts(facts)

        # 4. Added lines analysis
        added_lines = [line.strip() for line in change.added_lines if line.strip()]
        if not added_lines:
            # File-level change with no lines
            stmt = f"{subject} modified in `{file_path}`."
            fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.BEHAVIOR)
            return [
                SemanticCodeFact(
                    id=generate_fact_id(fp),
                    statement=stmt,
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.MEDIUM,
                    is_uncertain=True,
                    file_path=file_path,
                    symbol_name=symbol_name,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    change_type=change_type,
                    evidenced_lines=[],
                    provenance=base_prov,
                    fingerprint=fp,
                )
            ]

        idx = 0
        while idx < len(added_lines):
            line = added_lines[idx]

            # A. Pair checking: `if <cond>:` followed by `return` or `raise`
            if line.startswith("if ") and line.endswith(":") and idx + 1 < len(added_lines):
                cond = line[3:-1].strip()
                next_line = added_lines[idx + 1]

                # Check if next line is raise / throw
                raise_m = RAISE_PATTERN.search(next_line) or THROW_PATTERN.search(next_line)
                if raise_m:
                    exc_name = raise_m.group(1)
                    stmt = f"{subject} raises `{exc_name}` when `{cond}`."
                    fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.ERROR_HANDLING)
                    facts.append(
                        SemanticCodeFact(
                            id=generate_fact_id(fp),
                            statement=stmt,
                            fact_type=FactType.ERROR_HANDLING,
                            confidence=FactConfidence.HIGH,
                            is_uncertain=False,
                            file_path=file_path,
                            symbol_name=symbol_name,
                            commit_sha=commit_sha,
                            commit_message=commit_message,
                            change_type=change_type,
                            evidenced_lines=[line, next_line],
                            provenance=base_prov,
                            fingerprint=fp,
                        )
                    )
                    idx += 2
                    continue

                # Check if next line is return
                ret_m = RETURN_PATTERN.search(next_line)
                if ret_m:
                    ret_val = ret_m.group(1).rstrip(";").strip()
                    if ("test" in cond.lower() or "bypass" in cond.lower()) and ret_val in ("True", "true"):
                        stmt = f"{subject} allows bypass and returns True when `{cond}`."
                    else:
                        stmt = f"{subject} returns `{ret_val}` when `{cond}`."
                    fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.VALIDATION)
                    facts.append(
                        SemanticCodeFact(
                            id=generate_fact_id(fp),
                            statement=stmt,
                            fact_type=FactType.VALIDATION,
                            confidence=FactConfidence.HIGH,
                            is_uncertain=False,
                            file_path=file_path,
                            symbol_name=symbol_name,
                            commit_sha=commit_sha,
                            commit_message=commit_message,
                            change_type=change_type,
                            evidenced_lines=[line, next_line],
                            provenance=base_prov,
                            fingerprint=fp,
                        )
                    )
                    idx += 2
                    continue

            # B. Inline guard: `if <cond>: return <val>`
            inline_ret = GUARD_INLINE_RETURN.search(line)
            if inline_ret:
                cond = inline_ret.group(1).strip()
                ret_val = (inline_ret.group(2) or "").rstrip(";").strip()
                if ("test" in cond.lower() or "bypass" in cond.lower()) and ret_val in ("True", "true"):
                    stmt = f"{subject} allows bypass and returns True when `{cond}`."
                elif ret_val:
                    stmt = f"{subject} returns `{ret_val}` when `{cond}`."
                else:
                    stmt = f"{subject} returns when `{cond}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.VALIDATION)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.VALIDATION,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # C. Inline guard: `if <cond>: raise <exc>`
            inline_raise = GUARD_INLINE_RAISE.search(line)
            if inline_raise:
                cond = inline_raise.group(1).strip()
                exc_expr = inline_raise.group(2).strip()
                stmt = f"{subject} raises `{exc_expr}` when `{cond}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.ERROR_HANDLING)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.ERROR_HANDLING,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # D. Standalone Raise / Throw
            raise_m = RAISE_PATTERN.search(line) or THROW_PATTERN.search(line)
            if raise_m:
                exc_name = raise_m.group(1)
                stmt = f"{subject} raises `{exc_name}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.ERROR_HANDLING)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.ERROR_HANDLING,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # E. Standalone Return (e.g. hash computation or payload)
            ret_m = RETURN_PATTERN.search(line)
            if ret_m:
                ret_expr = ret_m.group(1).rstrip(";").strip()
                if "sha256" in ret_expr or "md5" in ret_expr or "hashlib" in ret_expr:
                    stmt = f"{subject} computes and returns a cryptographic hash digest of input."
                    ftype = FactType.BEHAVIOR
                elif ret_expr.startswith("{") and ret_expr.endswith("}"):
                    stmt = f"{subject} returns response payload `{ret_expr}`."
                    ftype = FactType.BEHAVIOR
                else:
                    stmt = f"{subject} returns `{ret_expr}`."
                    ftype = FactType.BEHAVIOR
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, ftype)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=ftype,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # F. Method call / State Mutation (e.g. user.set_email(new_email), user.mark_dirty())
            method_m = METHOD_CALL_PATTERN.search(line) or ASSIGNMENT_CALL_PATTERN.search(line)
            if method_m:
                receiver = method_m.group(1)
                method_name = method_m.group(2)
                args = method_m.group(3).strip()
                full_call = f"{receiver}.{method_name}({args})"

                # Distinguish state mutation vs persistence vs relationship
                if method_name.startswith("set_") or "email" in method_name:
                    stmt = f"{subject} updates {method_name.replace('set_', '')} via `{full_call}`."
                    ftype = FactType.STATE_CHANGE
                elif method_name in ("mark_dirty", "touch", "mark_active", "invalidate"):
                    stmt = f"{subject} marks {receiver} state dirty via `{full_call}`."
                    ftype = FactType.STATE_CHANGE
                elif method_name in ("save", "persist", "commit", "insert", "update"):
                    stmt = f"{subject} persists {receiver} record via `{full_call}`."
                    ftype = FactType.RELATIONSHIP
                else:
                    stmt = f"{subject} calls `{full_call}`."
                    ftype = FactType.RELATIONSHIP

                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, ftype)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=ftype,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # G. Import statements
            import_m = IMPORT_PATTERN.search(line)
            if import_m:
                mod_name = import_m.group(1) or import_m.group(2)
                stmt = f"`{file_path}` imports module `{mod_name.strip()}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.RELATIONSHIP)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.RELATIONSHIP,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # H. Class field definition
            class_field_m = CLASS_FIELD_PATTERN.search(line)
            if class_field_m:
                field_name = class_field_m.group(1)
                default_val = class_field_m.group(3).strip()
                stmt = f"{subject} defines `{field_name}` field with default `{default_val}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.STRUCTURAL)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.STRUCTURAL,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # I. Function/Handler definition
            def_m = DEF_PATTERN.search(line)
            if def_m:
                fn_name = def_m.group(1)
                next_ret = next(
                    (line_item for line_item in added_lines[idx + 1 : idx + 4] if "return" in line_item),
                    None,
                )
                if next_ret:
                    ret_m2 = RETURN_PATTERN.search(next_ret)
                    ret_str = ret_m2.group(1).rstrip(";").strip() if ret_m2 else ""
                    stmt = f"`{file_path}` defines `{fn_name}` returning `{ret_str}`."
                else:
                    stmt = f"`{file_path}` declares function `{fn_name}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.BEHAVIOR)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.BEHAVIOR,
                        confidence=FactConfidence.HIGH,
                        is_uncertain=False,
                        file_path=file_path,
                        symbol_name=fn_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # J. Config file key-values (YAML / JSON / INI)
            if is_config:
                cfg_m = CONFIG_KEY_VALUE_PATTERN.search(line)
                if cfg_m:
                    cfg_key = cfg_m.group(1).strip()
                    cfg_val = cfg_m.group(2).strip()
                    stmt = f"`{file_path}` configures `{cfg_key}` as `{cfg_val}`."
                    fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.CONFIGURATION)
                    facts.append(
                        SemanticCodeFact(
                            id=generate_fact_id(fp),
                            statement=stmt,
                            fact_type=FactType.CONFIGURATION,
                            confidence=FactConfidence.HIGH,
                            is_uncertain=False,
                            file_path=file_path,
                            symbol_name=symbol_name,
                            commit_sha=commit_sha,
                            commit_message=commit_message,
                            change_type=change_type,
                            evidenced_lines=[line],
                            provenance=base_prov,
                            fingerprint=fp,
                        )
                    )
                    idx += 1
                    continue

            # K. Ambiguous / Insufficient Evidence (e.g. x = 1, pass, i += 1)
            simple_assign_m = SIMPLE_VAR_ASSIGN_PATTERN.search(line)
            if simple_assign_m:
                var_name = simple_assign_m.group(1)
                val = simple_assign_m.group(3).strip()
                # Do NOT fabricate business rules; record literal action and mark UNCERTAIN
                stmt = f"{subject} assigns `{val}` to variable `{var_name}`."
                fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.BEHAVIOR)
                facts.append(
                    SemanticCodeFact(
                        id=generate_fact_id(fp),
                        statement=stmt,
                        fact_type=FactType.BEHAVIOR,
                        confidence=FactConfidence.UNCERTAIN,
                        is_uncertain=True,
                        file_path=file_path,
                        symbol_name=symbol_name,
                        commit_sha=commit_sha,
                        commit_message=commit_message,
                        change_type=change_type,
                        evidenced_lines=[line],
                        provenance=base_prov,
                        fingerprint=fp,
                    )
                )
                idx += 1
                continue

            # Ignored punctuation or closing braces
            if line in ("}", "];", ");", "pass", "...", "end"):
                idx += 1
                continue

            # L. General unclassified line -> mark UNCERTAIN without fabricating
            stmt = f"{subject} updates implementation line in `{file_path}`: `{line[:60]}`."
            fp = generate_fact_fingerprint(commit_sha, file_path, symbol_name, stmt, FactType.BEHAVIOR)
            facts.append(
                SemanticCodeFact(
                    id=generate_fact_id(fp),
                    statement=stmt,
                    fact_type=FactType.BEHAVIOR,
                    confidence=FactConfidence.UNCERTAIN,
                    is_uncertain=True,
                    file_path=file_path,
                    symbol_name=symbol_name,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    change_type=change_type,
                    evidenced_lines=[line],
                    provenance=base_prov,
                    fingerprint=fp,
                )
            )
            idx += 1

        return deduplicate_facts(facts)

    async def extract_facts_async(
        self,
        change: AtomicCodeChange,
        use_llm: bool = True,
    ) -> list[SemanticCodeFact]:
        """
        Extracts semantic atomic facts with optional LLM grounding expansion.
        Falls back safely and completely to deterministic extraction if LLM is offline,
        unavailable, produces ungrounded claims, or raises any error.
        """
        deterministic_facts = self.extract_facts_deterministic(change)

        if not use_llm:
            return deterministic_facts

        # Resolve provider
        provider = self.llm_provider
        if provider is None:
            try:
                from apps.api.src.config.settings import settings
                from apps.api.src.services.llm.factory import get_llm_provider

                provider_name = (settings.LLM_PROVIDER or "offline").strip().lower()
                if provider_name != "offline":
                    provider = get_llm_provider(provider_name)
            except Exception as e:
                logger.debug(f"LLM provider resolution skipped: {e}")
                provider = None

        if provider is None:
            return deterministic_facts

        try:
            llm_facts = await self._extract_facts_llm(change, provider)
            if llm_facts:
                return deduplicate_facts(llm_facts)
        except Exception as exc:
            logger.warning(
                f"LLM atomic fact extraction failed for {change.file_path}: {exc}. "
                "Degrading safely to deterministic facts."
            )

        return deterministic_facts

    async def _extract_facts_llm(
        self,
        change: AtomicCodeChange,
        provider: LLMProvider,
    ) -> list[SemanticCodeFact]:
        """
        Calls the configured LLM to decompose code changes into grounded atomic facts,
        enforcing strict anti-hallucination and grounding verification rules.
        """
        system_prompt = (
            "You are an authoritative code-fact extractor for the ATOM intelligence engine.\n"
            "Decompose the following code change into small, self-contained, semantically meaningful atomic facts about code behavior.\n"
            "RULES:\n"
            "1. Grounding: Every fact MUST be directly evidenced by the added or modified lines.\n"
            "2. Zero Hallucination: Do NOT invent API calls, business rules, dependencies, or runtime paths not present in the diff.\n"
            "3. Deletions: Do NOT treat deleted lines as active behavior. Mark removed code as 'REMOVAL'.\n"
            "4. Ambiguity: If evidence is insufficient, set 'is_uncertain': true and 'confidence': 'UNCERTAIN'.\n"
            "5. Self-Contained: Express one behavior per fact, resolving ambiguous references using file path and symbol.\n"
            "Respond strictly in JSON with format:\n"
            "{\n"
            '  "facts": [\n'
            "    {\n"
            '      "statement": "string",\n'
            '      "fact_type": "BEHAVIOR | VALIDATION | ERROR_HANDLING | STATE_CHANGE | RELATIONSHIP | REMOVAL | CONFIGURATION | STRUCTURAL",\n'
            '      "confidence": "HIGH | MEDIUM | UNCERTAIN",\n'
            '      "is_uncertain": false,\n'
            '      "evidenced_lines": ["code line"]\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"File: {change.file_path}\n"
            f"Symbol: {change.symbol_name or 'None'}\n"
            f"Change Type: {change.change_type.value}\n"
            f"Commit Message: {change.commit_message}\n"
            f"Raw Diff:\n```\n{change.raw_content}\n```\n"
        )

        res = await provider.generate_json(system_prompt, user_prompt)
        raw_facts = res.get("facts", []) if isinstance(res, dict) else []
        if not raw_facts or not isinstance(raw_facts, list):
            return []

        validated_facts: list[SemanticCodeFact] = []
        base_prov = dict(change.provenance)
        base_prov["atom_id"] = change.id
        base_prov["change_fingerprint"] = change.fingerprint
        base_prov["source"] = "llm_grounded"

        for rf in raw_facts:
            if not isinstance(rf, dict) or not rf.get("statement"):
                continue

            stmt = str(rf["statement"]).strip()
            # Verify grounding of claimed tokens
            if not validate_grounded_tokens(stmt, change.raw_content, change.file_path, change.symbol_name):
                logger.warning(f"Rejecting ungrounded LLM fact: '{stmt}'")
                continue

            # Validate deleted lines not claimed as active behavior
            if change.change_type == CodeChangeType.DELETE and rf.get("fact_type") != "REMOVAL":
                logger.warning(f"Correcting LLM fact for deleted file to REMOVAL: '{stmt}'")
                rf["fact_type"] = "REMOVAL"

            # Parse FactType safely
            ft_str = str(rf.get("fact_type", "BEHAVIOR")).upper()
            try:
                fact_type = FactType(ft_str)
            except ValueError:
                fact_type = FactType.BEHAVIOR

            # Parse FactConfidence safely
            fc_str = str(rf.get("confidence", "HIGH")).upper()
            try:
                confidence = FactConfidence(fc_str)
            except ValueError:
                confidence = FactConfidence.HIGH

            is_uncertain = bool(rf.get("is_uncertain", False))
            ev_lines = [str(x) for x in rf.get("evidenced_lines", []) if isinstance(x, str)]

            fp = generate_fact_fingerprint(
                change.commit_sha, change.file_path, change.symbol_name, stmt, fact_type
            )

            validated_facts.append(
                SemanticCodeFact(
                    id=generate_fact_id(fp),
                    statement=stmt,
                    fact_type=fact_type,
                    confidence=confidence,
                    is_uncertain=is_uncertain,
                    file_path=change.file_path,
                    symbol_name=change.symbol_name,
                    commit_sha=change.commit_sha,
                    commit_message=change.commit_message,
                    change_type=change.change_type,
                    evidenced_lines=ev_lines,
                    provenance=base_prov,
                    fingerprint=fp,
                )
            )

        return validated_facts
