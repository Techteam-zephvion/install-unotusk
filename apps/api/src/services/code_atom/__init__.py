from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    CodeChangeType,
    CodeDecompositionResult,
    GitCommitArtifact,
    GitDiffHunk,
    GitFileDiff,
)
from apps.api.src.services.code_atom.chunk_mapper import (
    generate_deterministic_chunk_id,
    map_atomic_code_change_to_code_chunk,
    resolve_and_map_atomic_changes,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.diff_parser import parse_unified_diff
from apps.api.src.services.code_atom.fingerprint import (
    generate_code_atom_fingerprint,
    generate_code_atom_id,
)
from apps.api.src.services.code_atom.git_extractor import extract_git_commit_artifact
from apps.api.src.services.code_atom.normalization import (
    normalize_code_change,
    normalize_diff_line,
)

__all__ = [
    "AtomicCodeChange",
    "CodeAtomDecomposer",
    "CodeChangeType",
    "CodeDecompositionResult",
    "GitCommitArtifact",
    "GitDiffHunk",
    "GitFileDiff",
    "extract_git_commit_artifact",
    "generate_code_atom_fingerprint",
    "generate_code_atom_id",
    "generate_deterministic_chunk_id",
    "map_atomic_code_change_to_code_chunk",
    "normalize_code_change",
    "normalize_diff_line",
    "parse_unified_diff",
    "resolve_and_map_atomic_changes",
]
