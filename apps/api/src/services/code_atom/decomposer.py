import re
import uuid
from typing import Any

from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    CodeDecompositionResult,
    GitCommitArtifact,
    GitFileDiff,
)
from apps.api.src.services.code_atom.diff_parser import parse_unified_diff
from apps.api.src.services.code_atom.fingerprint import (
    generate_code_atom_fingerprint,
    generate_code_atom_id,
)
from apps.api.src.services.code_atom.normalization import normalize_code_change

SYMBOL_HEADER_PATTERN = re.compile(
    r"\b(?:def|class|function|fn|func|interface|type|struct|enum|export\s+(?:function|class|const|let))\s+([A-Za-z0-9_]+)"
)


class CodeAtomDecomposer:
    """
    Decomposes a Git commit artifact into atomic, verifiable, and traceable code changes.
    Maintains full provenance back to parent commit, snapshot, file, and symbol.
    """

    def decompose(
        self,
        commit: GitCommitArtifact,
        symbol_catalog: list[dict[str, Any]] | None = None,
    ) -> CodeDecompositionResult:
        """
        Decomposes a GitCommitArtifact into a collection of AtomicCodeChange units.

        Parameters:
        - commit: GitCommitArtifact containing commit metadata and diff.
        - symbol_catalog: Optional list of known symbol records (with name, start_line, end_line,
          file_path, id, symbol_type) to correlate hunks with AST symbols.
        """
        # 1. Resolve file diffs: use explicit file_diffs if provided, else parse raw_diff
        file_diffs = list(commit.file_diffs)
        if not file_diffs and commit.raw_diff:
            file_diffs = parse_unified_diff(commit.raw_diff)

        atomic_changes: list[AtomicCodeChange] = []
        files_affected: set[str] = set()
        symbols_affected: set[str] = set()
        warnings: list[str] = []

        for file_diff in file_diffs:
            files_affected.add(file_diff.new_path)

            if not file_diff.hunks:
                # File change with no hunks (e.g. empty file add/delete or pure rename)
                atomic_unit = self._create_file_level_atomic_change(
                    commit=commit,
                    file_diff=file_diff,
                )
                atomic_changes.append(atomic_unit)
                continue

            for hunk in file_diff.hunks:
                # Correlate symbol from symbol catalog or hunk section header
                symbol_id, symbol_name, symbol_type = self._resolve_symbol(
                    file_path=file_diff.new_path,
                    start_line=hunk.new_start_line,
                    end_line=hunk.new_start_line + hunk.new_line_count - 1,
                    section_header=hunk.section_header,
                    symbol_catalog=symbol_catalog,
                )

                if symbol_name:
                    symbols_affected.add(symbol_name)

                # Raw diff representation for this specific hunk
                raw_hunk_content = f"{hunk.header}\n" + "\n".join(hunk.lines)

                # Deterministic normalized representation
                normalized = normalize_code_change(
                    file_path=file_diff.new_path,
                    change_type=file_diff.change_type.value,
                    symbol_name=symbol_name,
                    added_lines=hunk.added_lines,
                    deleted_lines=hunk.deleted_lines,
                    old_start_line=hunk.old_start_line,
                    old_line_count=hunk.old_line_count,
                    new_start_line=hunk.new_start_line,
                    new_line_count=hunk.new_line_count,
                )

                # Fingerprint & stable identifier
                fingerprint = generate_code_atom_fingerprint(
                    commit_sha=commit.commit_sha,
                    file_path=file_diff.new_path,
                    change_type=file_diff.change_type.value,
                    normalized_content=normalized,
                    symbol_name=symbol_name,
                    hunk_index=hunk.hunk_index,
                )
                atom_id = generate_code_atom_id(fingerprint)

                # Comprehensive provenance
                provenance: dict[str, Any] = {
                    "repository_id": str(commit.repository_id) if commit.repository_id else None,
                    "snapshot_id": str(commit.snapshot_id) if commit.snapshot_id else None,
                    "project_id": str(commit.project_id) if commit.project_id else None,
                    "commit_sha": commit.commit_sha,
                    "commit_message": commit.commit_message,
                    "author_name": commit.author_name,
                    "author_email": commit.author_email,
                    "committed_at": commit.committed_at.isoformat()
                    if commit.committed_at
                    else None,
                    "file_path": file_diff.new_path,
                    "old_file_path": file_diff.old_path,
                    "symbol_name": symbol_name,
                    "symbol_id": str(symbol_id) if symbol_id else None,
                    "symbol_type": symbol_type,
                    "hunk_index": hunk.hunk_index,
                    "old_line_range": (hunk.old_start_line, hunk.old_line_count),
                    "new_line_range": (hunk.new_start_line, hunk.new_line_count),
                    "change_type": file_diff.change_type.value,
                }

                metadata: dict[str, Any] = {
                    "lines_added_count": len(hunk.added_lines),
                    "lines_deleted_count": len(hunk.deleted_lines),
                    "lines_context_count": len(hunk.context_lines),
                    "hunk_header": hunk.header,
                    "section_header": hunk.section_header,
                }

                change_unit = AtomicCodeChange(
                    id=atom_id,
                    commit_sha=commit.commit_sha,
                    commit_message=commit.commit_message,
                    snapshot_id=commit.snapshot_id,
                    project_id=commit.project_id,
                    file_path=file_diff.new_path,
                    old_file_path=file_diff.old_path,
                    change_type=file_diff.change_type,
                    symbol_id=symbol_id,
                    symbol_name=symbol_name,
                    symbol_type=symbol_type,
                    old_start_line=hunk.old_start_line,
                    old_line_count=hunk.old_line_count,
                    new_start_line=hunk.new_start_line,
                    new_line_count=hunk.new_line_count,
                    section_header=hunk.section_header,
                    raw_content=raw_hunk_content,
                    normalized_content=normalized,
                    added_lines=hunk.added_lines,
                    deleted_lines=hunk.deleted_lines,
                    context_lines=hunk.context_lines,
                    provenance=provenance,
                    fingerprint=fingerprint,
                    metadata=metadata,
                )
                atomic_changes.append(change_unit)

        if not atomic_changes and (commit.raw_diff or commit.file_diffs):
            warnings.append("Diff contained no parsable hunks or file changes.")

        return CodeDecompositionResult(
            commit_sha=commit.commit_sha,
            changes=atomic_changes,
            change_count=len(atomic_changes),
            files_affected=sorted(files_affected),
            symbols_affected=sorted(symbols_affected),
            warnings=warnings,
        )

    def _resolve_symbol(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        section_header: str | None,
        symbol_catalog: list[dict[str, Any]] | None,
    ) -> tuple[uuid.UUID | None, str | None, str | None]:
        """Resolves symbol identity from catalog or falls back to hunk header hint."""
        clean_file = file_path.replace("\\", "/").strip().lower()

        # 1. Try matching with provided AST symbol catalog
        if symbol_catalog:
            for sym in symbol_catalog:
                sym_path = str(sym.get("file_path", "")).replace("\\", "/").strip().lower()
                if sym_path and sym_path != clean_file:
                    continue

                sym_start = sym.get("start_line", 0)
                sym_end = sym.get("end_line", 0)
                # Check line range overlap
                if max(start_line, sym_start) <= min(end_line, sym_end):
                    raw_id = sym.get("id")
                    sym_uuid = uuid.UUID(str(raw_id)) if raw_id else None
                    return sym_uuid, sym.get("name"), sym.get("symbol_type")

        # 2. Fall back to parsing the diff hunk section header
        if section_header:
            match = SYMBOL_HEADER_PATTERN.search(section_header)
            if match:
                return None, match.group(1), "FUNCTION_OR_CLASS"

        return None, None, None

    def _create_file_level_atomic_change(
        self,
        commit: GitCommitArtifact,
        file_diff: GitFileDiff,
    ) -> AtomicCodeChange:
        """Handles file additions, deletions, or pure renames without hunk lines."""
        raw_content = file_diff.raw_patch or f"{file_diff.change_type.value} {file_diff.new_path}"
        normalized = normalize_code_change(
            file_path=file_diff.new_path,
            change_type=file_diff.change_type.value,
            symbol_name=None,
            added_lines=[],
            deleted_lines=[],
            old_start_line=0,
            old_line_count=0,
            new_start_line=0,
            new_line_count=0,
        )
        fingerprint = generate_code_atom_fingerprint(
            commit_sha=commit.commit_sha,
            file_path=file_diff.new_path,
            change_type=file_diff.change_type.value,
            normalized_content=normalized,
            symbol_name=None,
            hunk_index=0,
        )
        atom_id = generate_code_atom_id(fingerprint)

        provenance = {
            "repository_id": str(commit.repository_id) if commit.repository_id else None,
            "snapshot_id": str(commit.snapshot_id) if commit.snapshot_id else None,
            "project_id": str(commit.project_id) if commit.project_id else None,
            "commit_sha": commit.commit_sha,
            "commit_message": commit.commit_message,
            "author_name": commit.author_name,
            "author_email": commit.author_email,
            "committed_at": commit.committed_at.isoformat() if commit.committed_at else None,
            "file_path": file_diff.new_path,
            "old_file_path": file_diff.old_path,
            "symbol_name": None,
            "symbol_id": None,
            "symbol_type": None,
            "hunk_index": 0,
            "old_line_range": (0, 0),
            "new_line_range": (0, 0),
            "change_type": file_diff.change_type.value,
        }

        return AtomicCodeChange(
            id=atom_id,
            commit_sha=commit.commit_sha,
            commit_message=commit.commit_message,
            snapshot_id=commit.snapshot_id,
            project_id=commit.project_id,
            file_path=file_diff.new_path,
            old_file_path=file_diff.old_path,
            change_type=file_diff.change_type,
            raw_content=raw_content,
            normalized_content=normalized,
            added_lines=[],
            deleted_lines=[],
            context_lines=[],
            provenance=provenance,
            fingerprint=fingerprint,
            metadata={"is_file_level_change": True},
        )
