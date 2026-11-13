"""
E3 Unsupervised Metrics for Software Information Extraction & Ontology Proposals.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

Directly adapts metric families from:
"Comparison of Unsupervised Metrics for Evaluating Judicial Decision Extraction" (arXiv:2510.01792)
for software engineering artifacts, code diffs, and ontology proposals.
"""

import re
from typing import Any

from experiments.e3_sparse_confidence.schema import SufficiencyLevel


def tokenize_symbol(symbol: str) -> list[str]:
    """Splits identifiers on camelCase transitions, underscores, dots, and colons."""
    if not symbol:
        return []
    # Replace separators with spaces
    s = re.sub(r"[._:/\\-]+", " ", symbol)
    # Split camelCase: e.g. "LegacySessionAuth" -> "Legacy Session Auth"
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    tokens = [t.lower().strip() for t in s.split() if t.strip()]
    return tokens


def tokenize_diff(diff_text: str) -> set[str]:
    """Extracts a set of normalized alphanumeric identifier tokens from source diff text."""
    if not diff_text:
        return set()
    raw_tokens = re.findall(r"[A-Za-z0-9_]{2,}", diff_text)
    token_set: set[str] = set()
    for tok in raw_tokens:
        tok_lower = tok.lower()
        token_set.add(tok_lower)
        # Also include sub-tokens
        for subtok in tokenize_symbol(tok):
            token_set.add(subtok)
    return token_set


def compute_provenance_completeness(evidence: Any) -> float:
    """
    Citation/Provenance Coverage Metric (arXiv:2510.01792 adaptation).
    Verifies completeness and syntactic validity of source evidence.

    Components:
    - file_path present and valid (0.35)
    - start_line & end_line valid positive integers with start <= end (0.25)
    - diff_snippet present and non-empty (0.25)
    - grounded_tokens present (0.15)
    """
    if evidence is None:
        return 0.0

    score = 0.0

    # 1. File path validation
    file_path = getattr(evidence, "file_path", "") or ""
    if file_path and isinstance(file_path, str) and len(file_path.strip()) > 1:
        if any(file_path.endswith(ext) for ext in [".py", ".ts", ".js", ".go", ".yml", ".yaml", ".json", ".dart"]):
            score += 0.35
        else:
            score += 0.25

    # 2. Line number validity
    start_line = getattr(evidence, "start_line", None)
    end_line = getattr(evidence, "end_line", None)
    if start_line is not None and isinstance(start_line, int) and start_line > 0:
        if end_line is not None and isinstance(end_line, int) and end_line >= start_line:
            score += 0.25
        elif end_line is None:
            score += 0.15

    # 3. Diff snippet presence
    diff_snippet = getattr(evidence, "diff_snippet", "") or ""
    if diff_snippet and isinstance(diff_snippet, str) and len(diff_snippet.strip()) > 3:
        score += 0.25

    # 4. Grounded tokens presence
    grounded_tokens = getattr(evidence, "grounded_tokens", []) or []
    if grounded_tokens and len(grounded_tokens) > 0:
        score += 0.15

    return min(1.0, round(score, 4))


def compute_term_frequency_coherence(symbol_name: str, diff_text: str) -> float:
    """
    Term Frequency Coherence Metric (arXiv:2510.01792 adaptation).
    Measures alignment between extracted symbol identifier tokens and the diff vocabulary.
    """
    if not symbol_name or not diff_text:
        return 0.0

    symbol_tokens = tokenize_symbol(symbol_name)
    if not symbol_tokens:
        return 0.0

    diff_vocab = tokenize_diff(diff_text)
    if not diff_vocab:
        return 0.0

    matched = sum(1 for tok in symbol_tokens if tok in diff_vocab)
    ratio = matched / len(symbol_tokens)

    # Direct exact substring match in diff gets full 1.0
    if symbol_name in diff_text or symbol_name.lower() in diff_text.lower():
        return 1.0

    return min(1.0, round(ratio, 4))


def compute_intra_block_coherence(
    fact_type: str,
    name: str,
    subject_or_target: str = "",
    object_name: str = "",
) -> float:
    """
    Intra-Block Semantic Coherence Metric (arXiv:2510.01792 adaptation).
    Assesses syntactic and semantic harmony within a single extracted fact.

    Checks naming conventions, entity types, and relation-type compatibility.
    """
    score = 0.85  # Standard baseline for well-formed items

    clean_type = fact_type.upper().strip() if fact_type else "OTHER"

    # Check Entity naming conventions
    if clean_type in ("CLASS", "SERVICE", "DATASTORE"):
        # Expecting PascalCase or underscore naming
        if re.search(r"^[A-Z][A-Za-z0-9_]*$", name):
            score += 0.15
        else:
            score -= 0.10
    elif clean_type in ("FUNCTION", "METHOD"):
        # Expecting snake_case or camelCase
        if re.search(r"^[a-z][a-zA-Z0-9_]*$", name):
            score += 0.15
        elif name.isupper():
            score -= 0.15
    elif clean_type in ("FILE", "MODULE"):
        # Expecting path, dot, or extension
        if any(sep in name for sep in ("/", "\\", ".")):
            score += 0.15

    # Check Relation argument compatibility
    if subject_or_target and object_name:
        if clean_type == "CALLS":
            # Calling should connect callables or services
            if subject_or_target == object_name:
                score -= 0.40  # Self-call without recursion indicator is suspicious
            else:
                score += 0.10
        elif clean_type == "DEFINES":
            # Container defines member
            if subject_or_target == object_name:
                score -= 0.50
            else:
                score += 0.10
        elif clean_type == "IMPORTS":
            # Subject imports object
            if "." in object_name or "/" in object_name or re.match(r"^[a-zA-Z0-9_]+$", object_name):
                score += 0.10

    return max(0.0, min(1.0, round(score, 4)))


def compute_structural_consistency(
    relations: list[Any],
    concepts: list[Any] | None = None,
) -> tuple[float, list[str]]:
    """
    Structural Consistency Metric (arXiv:2510.01792 adaptation).
    Detects cycle violations, invalid self-referencing containment, and hierarchy inversions.
    """
    violations: list[str] = []
    if not relations and not concepts:
        return 1.0, violations

    penalties = 0.0

    # 1. Check direct circular relations in tree-like relations (SPECIALIZES, COMPOSED_OF, DEFINES)
    hierarchical_pairs: set[tuple[str, str]] = set()
    for rel in relations:
        rel_type = (getattr(rel, "relation_type", "") or getattr(rel, "relation", "")).upper()
        subj = getattr(rel, "subject", "") or getattr(rel, "subject_concept_id", "")
        obj = getattr(rel, "object", "") or getattr(rel, "object_concept_id", "")

        if not subj or not obj:
            continue

        if subj == obj:
            violations.append(f"Self-referencing relationship '{rel_type}' on '{subj}'")
            penalties += 0.25
            continue

        if rel_type in ("SPECIALIZES", "COMPOSED_OF", "DEFINES", "INHERITS"):
            if (obj, subj) in hierarchical_pairs:
                violations.append(f"Circular hierarchy detected between '{subj}' and '{obj}' for {rel_type}")
                penalties += 0.40
            hierarchical_pairs.add((subj, obj))

    # 2. Check concept parent-child validity if concepts provided
    if concepts:
        for c in concepts:
            cid = getattr(c, "concept_id", None) or getattr(c, "id", "")
            pid = getattr(c, "parent_concept_id", None)
            if pid and pid == cid:
                violations.append(f"Concept '{cid}' is its own parent")
                penalties += 0.35

    score = max(0.0, 1.0 - penalties)
    return round(score, 4), violations


def compute_redundancy_penalty(items: list[Any], key_fn: Any = None) -> tuple[float, list[str]]:
    """
    Redundancy Penalty Metric (arXiv:2510.01792 adaptation).
    Penalizes duplicate or overlapping facts extracted from identical evidence spans.
    """
    if not items or len(items) <= 1:
        return 0.0, []

    if key_fn is None:
        def default_key(item: Any) -> str:
            name = getattr(item, "entity_name", getattr(item, "name", ""))
            fpath = getattr(item, "file_path", "")
            return f"{name}::{fpath}"
        key_fn = default_key

    seen_keys: dict[str, int] = {}
    redundant_items: list[str] = []

    for item in items:
        k = key_fn(item)
        if not k:
            continue
        seen_keys[k] = seen_keys.get(k, 0) + 1
        if seen_keys[k] > 1:
            redundant_items.append(k)

    duplicate_count = sum(count - 1 for count in seen_keys.values() if count > 1)
    redundancy_ratio = duplicate_count / len(items)

    # Redundancy penalty capped at 0.60
    penalty = min(0.60, round(redundancy_ratio, 4))
    return penalty, redundant_items


def compute_corroboration_score(
    occurrences: list[Any],
) -> tuple[float, int, int]:
    """
    Cross-Source / Multi-Commit Corroboration Metric.
    Distinguishes:
    - Multiple independent files or commits (true corroboration).
    - Single observation (valid baseline direct evidence, not penalized for project sparsity).
    - Multiple occurrences in the exact same file hunk (redundant duplication, not independent support).

    Returns: (corroboration_score, independent_files_count, independent_commits_count)
    """
    if not occurrences:
        return 0.50, 0, 0

    unique_files: set[str] = set()
    unique_commits: set[str] = set()

    for occ in occurrences:
        ev = getattr(occ, "evidence", None)
        if ev is not None:
            if isinstance(ev, list):
                for e in ev:
                    fp = getattr(e, "file_path", "")
                    csha = getattr(e, "commit_sha", "")
                    if fp:
                        unique_files.add(fp)
                    if csha:
                        unique_commits.add(csha)
            else:
                fp = getattr(ev, "file_path", "")
                csha = getattr(ev, "commit_sha", "")
                if fp:
                    unique_files.add(fp)
                if csha:
                    unique_commits.add(csha)
        else:
            fp = getattr(occ, "file_path", "")
            csha = getattr(occ, "commit_sha", "")
            if fp:
                unique_files.add(fp)
            if csha:
                unique_commits.add(csha)

    n_files = len(unique_files)
    n_commits = len(unique_commits)

    # Baseline for single verified observation: 0.50
    # Corroborated across 2 files or 2 commits: 0.80
    # Corroborated across 3+ files or commits: 1.00
    if n_files >= 3 or n_commits >= 3:
        score = 1.00
    elif n_files >= 2 or n_commits >= 2:
        score = 0.80
    else:
        score = 0.50

    return score, n_files, n_commits


def detect_contradictions(relations: list[Any]) -> tuple[float, list[str]]:
    """
    Contradiction & Conflict Detection Metric.
    Identifies contradictory relationship assertions (e.g. mutual replacement, or opposite semantics).
    """
    contradictions: list[str] = []
    if not relations:
        return 0.0, contradictions

    relation_map: dict[tuple[str, str], list[str]] = {}
    for rel in relations:
        rtype = (getattr(rel, "relation_type", "") or getattr(rel, "relation", "")).upper()
        subj = getattr(rel, "subject", "") or getattr(rel, "subject_concept_id", "")
        obj = getattr(rel, "object", "") or getattr(rel, "object_concept_id", "")

        if not subj or not obj:
            continue

        pair = (subj, obj)
        relation_map.setdefault(pair, []).append(rtype)

    penalties = 0.0
    for (subj, obj), types in relation_map.items():
        reverse_pair = (obj, subj)
        reverse_types = relation_map.get(reverse_pair, [])

        # Contradiction: A REPLACES B and B REPLACES A
        if "REPLACES" in types and "REPLACES" in reverse_types:
            contradictions.append(f"Contradictory reciprocal REPLACES relation between '{subj}' and '{obj}'")
            penalties += 0.35

        # Contradiction: A SUPERSEDES B and B SUPERSEDES A
        if "SUPERSEDES" in types and "SUPERSEDES" in reverse_types:
            contradictions.append(f"Contradictory reciprocal SUPERSEDES relation between '{subj}' and '{obj}'")
            penalties += 0.35

        # Contradiction: same subject-object has both INHERITS and CALLS as primary link in sparse data
        if "INHERITS" in types and "CALLS" in types:
            contradictions.append(f"Conflicting INHERITS and CALLS relationships asserted for ({subj} -> {obj})")
            penalties += 0.20

    penalty_score = min(0.60, round(penalties, 4))
    return penalty_score, contradictions


def compute_keyword_pseudo_f1(diff_text: str, extracted_symbol_names: list[str]) -> dict[str, float]:
    """
    Keyword Pseudo-Ground-Truth Proxy (arXiv:2510.01792 adaptation).
    Extracts candidate symbol identifiers from diff hunk headers and lines,
    computing pseudo-precision, pseudo-recall, and pseudo-F1.

    Explicitly labeled as a heuristic proxy, not true ground truth extraction accuracy.
    """
    if not diff_text or not extracted_symbol_names:
        return {"pseudo_precision": 0.0, "pseudo_recall": 0.0, "pseudo_f1": 0.0}

    # Heuristic pattern to identify declared symbols in diff
    # Matches: def foo, class Bar, import baz, function qux
    patterns = [
        r"(?:def|class|function|var|const|let)\s+([A-Za-z0-9_]+)",
        r"(?:import|from)\s+([A-Za-z0-9_]+)",
        r"@@\s+.*\s+(?:def|class)\s+([A-Za-z0-9_]+)",
    ]

    candidate_symbols: set[str] = set()
    for p in patterns:
        for m in re.finditer(p, diff_text):
            sym = m.group(1).strip()
            if len(sym) > 2:
                candidate_symbols.add(sym.lower())

    if not candidate_symbols:
        # Fallback to general identifiers in added lines
        added_lines = [
            line_str[1:]
            for line_str in diff_text.splitlines()
            if line_str.startswith("+") and not line_str.startswith("+++")
        ]
        for line in added_lines:
            tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", line)
            candidate_symbols.update(t.lower() for t in tokens[:5])

    if not candidate_symbols:
        return {"pseudo_precision": 1.0, "pseudo_recall": 1.0, "pseudo_f1": 1.0}

    extracted_normalized = {s.lower() for s in extracted_symbol_names if s}

    true_positives = len(extracted_normalized.intersection(candidate_symbols))
    pseudo_precision = true_positives / len(extracted_normalized) if extracted_normalized else 0.0
    pseudo_recall = true_positives / len(candidate_symbols) if candidate_symbols else 0.0

    if pseudo_precision + pseudo_recall > 0:
        pseudo_f1 = (2 * pseudo_precision * pseudo_recall) / (pseudo_precision + pseudo_recall)
    else:
        pseudo_f1 = 0.0

    return {
        "pseudo_precision": round(pseudo_precision, 4),
        "pseudo_recall": round(pseudo_recall, 4),
        "pseudo_f1": round(pseudo_f1, 4),
    }


def compute_evidence_sufficiency(
    commit_count: int,
    file_count: int,
    fact_count: int,
    diff_chars_count: int,
) -> tuple[SufficiencyLevel, float]:
    """
    Evaluates evidence sufficiency and computes a normalized sparsity index.

    A project with 1 commit but clean, extensive diff and multiple facts is SPARSE,
    NOT CRITICALLY_INSUFFICIENT.

    Sparsity index: 1.0 = highly sparse, 0.0 = abundant evidence.
    """
    if commit_count == 0 or fact_count == 0 or diff_chars_count < 20:
        return SufficiencyLevel.CRITICALLY_INSUFFICIENT, 1.0

    if commit_count >= 5 and file_count >= 5 and fact_count >= 15:
        sufficiency = SufficiencyLevel.ABUNDANT
        sparsity = 0.15
    elif commit_count >= 3 or (file_count >= 3 and fact_count >= 8):
        sufficiency = SufficiencyLevel.MODERATE
        sparsity = 0.40
    elif fact_count >= 1 and diff_chars_count >= 50:
        sufficiency = SufficiencyLevel.SPARSE
        sparsity = 0.70
    else:
        sufficiency = SufficiencyLevel.CRITICALLY_INSUFFICIENT
        sparsity = 0.95

    return sufficiency, sparsity
