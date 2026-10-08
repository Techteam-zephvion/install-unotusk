from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    CodeChangeType,
    CodeDecompositionResult,
    GitCommitArtifact,
    GitDiffHunk,
    GitFileDiff,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.diff_parser import parse_unified_diff
from apps.api.src.services.code_atom.fingerprint import (
    generate_code_atom_fingerprint,
    generate_code_atom_id,
)
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
    "generate_code_atom_fingerprint",
    "generate_code_atom_id",
    "normalize_code_change",
    "normalize_diff_line",
    "parse_unified_diff",
]
