import hashlib


def generate_code_atom_fingerprint(
    commit_sha: str,
    file_path: str,
    change_type: str,
    normalized_content: str,
    symbol_name: str | None = None,
    hunk_index: int = 0,
) -> str:
    """
    Computes a deterministic, reproducible SHA-256 fingerprint for an atomic code change unit.

    Fields used:
    - commit_sha
    - canonical file path
    - change type
    - symbol name (or 'NONE')
    - hunk index
    - normalized change content
    """
    clean_sha = commit_sha.strip().lower()
    clean_path = file_path.replace("\\", "/").strip().lower()
    clean_type = change_type.upper().strip()
    clean_symbol = symbol_name.strip() if symbol_name else "NONE"

    payload = (
        f"{clean_sha}:{clean_path}:{clean_type}:{clean_symbol}:{hunk_index}:{normalized_content}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_code_atom_id(fingerprint: str) -> str:
    """Generates a stable, reproducible atomic code change ID."""
    return f"atom-code-{fingerprint[:16]}"
