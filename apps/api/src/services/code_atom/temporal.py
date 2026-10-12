"""
Temporal history awareness and supersession engine for ATOM Code Lane.
Tracks code evolution, detects temporal query intent, resolves supersession across commits,
and preserves historical provenance without fabricating metadata.
"""

import re
from datetime import UTC, datetime

from apps.api.src.services.context_engine.retriever import RetrievedCandidate

TEMPORAL_KEYWORDS = {
    "history",
    "evolution",
    "evolved",
    "timeline",
    "chronology",
    "past",
    "previous",
    "previously",
    "earlier",
    "former",
    "prior",
    "historical",
    "superseded",
    "supersedes",
    "changelog",
    "diff",
    "diffs",
    "commits",
    "commit",
    "revision",
    "revisions",
    "blame",
    "before",
    "deleted",
    "removed",
    "deprecated",
}

TEMPORAL_REGEX_PATTERNS = [
    re.compile(r"\b(how|what)\s+(did|has|have|was|were)\s+.*?\b(change|evolve|modify|update|differ)\b", re.I),
    re.compile(r"\b(who|when)\s+.*?\b(changed|added|removed|deleted|created|modified|wrote|committed|introduced)\b", re.I),
    re.compile(r"\b(evolution|history|changes|commits|timeline)\s+of\b", re.I),
    re.compile(r"\bchanges\s+(in|to|for|across)\b", re.I),
    re.compile(r"\b(previous|earlier|past|older|former)\s+(version|implementation|commit|code|state)\b", re.I),
    re.compile(r"\b(version|commit|change)\s+history\b", re.I),
    re.compile(r"\bhow\s+.*\b(evolved|changed)\b", re.I),
    re.compile(r"\bwhat\s+(changed|was\s+changed|were\s+the\s+changes)\b", re.I),
]


def classify_temporal_intent(query_text: str) -> tuple[bool, str | None, list[str]]:
    """
    Analyzes query text to detect temporal intent, intent type, and detected temporal tokens.
    """
    if not query_text or not query_text.strip():
        return False, None, []

    cleaned = query_text.strip()
    words = re.findall(r"[A-Za-z0-9_.\-/]+", cleaned)
    detected: list[str] = []

    for w in words:
        clean_w = w.lower().strip(".,?!:;()[]{}'\"")
        if clean_w in TEMPORAL_KEYWORDS:
            detected.append(clean_w)

    is_temporal = len(detected) > 0
    if not is_temporal:
        for pat in TEMPORAL_REGEX_PATTERNS:
            if pat.search(cleaned):
                is_temporal = True
                break

    intent = "EVOLUTION" if is_temporal else None
    return is_temporal, intent, list(dict.fromkeys(detected))


def parse_candidate_timestamp(cand: RetrievedCandidate) -> datetime | None:
    """
    Safely parses timestamp from candidate metadata or provenance.
    Never fabricates timestamps or throws exceptions on missing or malformed data.
    """
    prov = cand.metadata.get("provenance") or {}
    ts_val = cand.metadata.get("committed_at") or prov.get("committed_at")
    if ts_val:
        if isinstance(ts_val, datetime):
            return ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=UTC)
        if isinstance(ts_val, str) and ts_val.strip():
            try:
                dt = datetime.fromisoformat(ts_val.strip().replace("Z", "+00:00"))
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                pass

    created_val = cand.metadata.get("created_at")
    if created_val:
        if isinstance(created_val, datetime):
            return created_val if created_val.tzinfo else created_val.replace(tzinfo=UTC)
        if isinstance(created_val, str) and created_val.strip():
            try:
                dt = datetime.fromisoformat(created_val.strip().replace("Z", "+00:00"))
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                pass

    return None


def _get_candidate_target(cand: RetrievedCandidate) -> tuple[str, str | None, str | None]:
    """
    Extracts (normalized_path, symbol_name, old_file_path) for scope tracking.
    """
    path = cand.path.strip().lower()
    prov = cand.metadata.get("provenance") or {}
    old_path = (cand.metadata.get("old_file_path") or prov.get("old_file_path") or "").strip().lower() or None

    symbol_name = cand.metadata.get("symbol_name") or prov.get("symbol_name")
    if not symbol_name and cand.name:
        stem = cand.name.split(" (")[0].strip()
        if stem and not any(stem.endswith(ext) for ext in (".py", ".ts", ".js", ".go", ".rs", ".java", ".json", ".md")):
            symbol_name = stem
    if symbol_name:
        symbol_name = symbol_name.strip().lower()

    return path, symbol_name, old_path


def resolve_temporal_supersession(candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]:
    """
    Resolves chronological relationships across code chunk candidates:
    1. Groups candidates targeting the same file or symbol (accounting for file renames).
    2. Identifies the latest active version and marks earlier versions as superseded.
    3. Handles deletions (ATOM_DELETE) so deleted code does not appear as active current code.
    4. Handles renames (ATOM_RENAME) preserving historical links without duplicate current evidence.
    5. Ensures unrelated files do not supersede each other.
    6. Safely handles missing timestamps without fabrication or crashes.
    """
    # 1. Build rename linkage map: old_path -> canonical_new_path
    rename_map: dict[str, str] = {}
    for cand in candidates:
        if cand.entity_type != "CHUNK":
            continue
        path, _, old_path = _get_candidate_target(cand)
        if old_path and old_path != path:
            rename_map[old_path] = path

    def get_canonical_path(p: str) -> str:
        curr = p
        visited = set()
        while curr in rename_map and curr not in visited:
            visited.add(curr)
            curr = rename_map[curr]
        return curr

    # 2. Group candidates by scope: scope_key -> list[RetrievedCandidate]
    scoped_groups: dict[tuple[str, str, str | None], list[RetrievedCandidate]] = {}
    for cand in candidates:
        if cand.entity_type != "CHUNK":
            continue

        path, symbol_name, old_path = _get_candidate_target(cand)
        canon_path = get_canonical_path(path)

        if symbol_name:
            scope_key = ("symbol", canon_path, symbol_name)
        else:
            scope_key = ("file", canon_path, None)

        scoped_groups.setdefault(scope_key, []).append(cand)

    # 3. For each group with 2+ candidates, evaluate chronological ordering and supersession
    for _scope_key, group in scoped_groups.items():
        if len(group) < 2:
            # Single candidate in scope
            single_cand = group[0]
            prov = single_cand.metadata.get("provenance") or {}
            c_type = str(single_cand.metadata.get("chunk_type") or prov.get("change_type") or "").upper()
            if "DELETE" in c_type or single_cand.name.upper().endswith("(DELETE)"):
                single_cand.metadata["is_deleted"] = True
                single_cand.metadata["is_current"] = False
            else:
                single_cand.metadata.setdefault("is_current", True)
                single_cand.metadata.setdefault("is_superseded", False)
            continue

        # Multiple candidates in scope: extract timestamps
        cand_with_ts: list[tuple[datetime | None, RetrievedCandidate]] = []
        for cand in group:
            ts = parse_candidate_timestamp(cand)
            cand_with_ts.append((ts, cand))

        # Check if verified timestamps are present for comparison
        known_ts = [item for item in cand_with_ts if item[0] is not None]

        if len(known_ts) >= 2:
            # Sort chronologically ascending
            known_ts.sort(key=lambda x: x[0])
            latest_ts, latest_cand = known_ts[-1]

            prov_latest = latest_cand.metadata.get("provenance") or {}
            c_type_latest = str(latest_cand.metadata.get("chunk_type") or prov_latest.get("change_type") or "").upper()
            is_latest_delete = "DELETE" in c_type_latest or latest_cand.name.upper().endswith("(DELETE)")

            latest_sha = latest_cand.metadata.get("commit_sha")

            for _ts, cand in known_ts[:-1]:
                cand.metadata["is_superseded"] = True
                cand.metadata["is_current"] = False
                if latest_sha:
                    cand.metadata["superseded_by_sha"] = latest_sha
                if latest_ts:
                    cand.metadata["superseded_by_date"] = latest_ts.isoformat()
                if is_latest_delete:
                    cand.metadata["is_deleted"] = True

            if is_latest_delete:
                latest_cand.metadata["is_deleted"] = True
                latest_cand.metadata["is_current"] = False
            else:
                latest_cand.metadata["is_current"] = True
                latest_cand.metadata["is_superseded"] = False

            # If some candidates in the group had missing timestamps, do NOT invent dates
            for _ts, cand in cand_with_ts:
                if _ts is None:
                    # Leave is_superseded False or safely unmarked without fabricating timestamps
                    cand.metadata.setdefault("is_superseded", False)

        elif len(known_ts) == 1:
            # Only one has timestamp, others don't: safely don't fabricate order
            for _ts, cand in cand_with_ts:
                cand.metadata.setdefault("is_superseded", False)
        else:
            # None have timestamps: safe fallback without crashing or guessing
            for _ts, cand in cand_with_ts:
                cand.metadata.setdefault("is_superseded", False)

        # Trace rename annotations
        for cand in group:
            path, _, old_path = _get_candidate_target(cand)
            if old_path and old_path != path:
                cand.metadata["renamed_from"] = old_path
            canon_path = get_canonical_path(path)
            if path != canon_path:
                cand.metadata["renamed_to"] = canon_path

    return candidates
