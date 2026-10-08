def normalize_diff_line(line: str) -> str:
    """Normalizes a single diff or code line safely by trimming trailing whitespace and line endings."""
    return line.rstrip("\r\n \t")


def normalize_code_change(
    file_path: str,
    change_type: str,
    symbol_name: str | None,
    added_lines: list[str],
    deleted_lines: list[str],
    old_start_line: int | None = None,
    old_line_count: int | None = None,
    new_start_line: int | None = None,
    new_line_count: int | None = None,
) -> str:
    """
    Deterministically normalizes an atomic code change representation.

    Guarantees:
    1. Line ending and trailing whitespace normalization without modifying code semantics.
    2. Casing, language keywords, and identifier names are strictly preserved.
    3. Added and deleted lines are formatted consistently.
    4. Stable across operating systems and Git line-ending configurations.
    """
    clean_path = file_path.replace("\\", "/").strip().lower()
    clean_type = change_type.upper().strip()
    clean_symbol = symbol_name.strip() if symbol_name else "NONE"

    old_range_str = (
        f"{old_start_line or 0}:{old_line_count or 0}"
        if old_start_line is not None
        else "0:0"
    )
    new_range_str = (
        f"{new_start_line or 0}:{new_line_count or 0}"
        if new_start_line is not None
        else "0:0"
    )

    clean_deleted = [normalize_diff_line(line) for line in deleted_lines if line.strip()]
    clean_added = [normalize_diff_line(line) for line in added_lines if line.strip()]

    parts = [
        f"PATH:{clean_path}",
        f"TYPE:{clean_type}",
        f"SYMBOL:{clean_symbol}",
        f"OLD_RANGE:{old_range_str}",
        f"NEW_RANGE:{new_range_str}",
        "DELETED:",
    ]
    parts.extend(clean_deleted)
    parts.append("ADDED:")
    parts.extend(clean_added)

    return "\n".join(parts)
