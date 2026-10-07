import re

from apps.api.src.schemas.code_atom import CodeChangeType, GitDiffHunk, GitFileDiff

HUNK_HEADER_REGEX = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@(?:\s+(?P<heading>.*))?$"
)


def _clean_diff_path(path: str) -> str:
    """Strips standard Git 'a/' or 'b/' prefixes from paths."""
    clean = path.strip()
    if clean.startswith("a/") or clean.startswith("b/"):
        return clean[2:]
    return clean


def parse_unified_diff(raw_diff: str) -> list[GitFileDiff]:
    """
    Parses a unified git diff text into structured GitFileDiff and GitDiffHunk objects.
    Robustly handles added, modified, deleted, and renamed files.
    """
    if not raw_diff or not raw_diff.strip():
        return []

    lines = raw_diff.splitlines()
    file_diffs: list[GitFileDiff] = []

    current_file_lines: list[str] = []
    file_blocks: list[list[str]] = []

    # 1. Segment raw diff into per-file diff blocks
    for line in lines:
        if line.startswith("diff --git "):
            if current_file_lines:
                file_blocks.append(current_file_lines)
            current_file_lines = [line]
        else:
            if current_file_lines:
                current_file_lines.append(line)
            else:
                # Diff without 'diff --git' header (e.g. single patch starting with '---')
                current_file_lines = [line]

    if current_file_lines:
        file_blocks.append(current_file_lines)

    # 2. Parse each file block
    for block in file_blocks:
        file_diff = _parse_single_file_block(block)
        if file_diff:
            file_diffs.append(file_diff)

    return file_diffs


def _parse_single_file_block(lines: list[str]) -> GitFileDiff | None:
    old_path: str | None = None
    new_path: str | None = None
    change_type = CodeChangeType.MODIFY
    raw_patch = "\n".join(lines)

    hunks: list[GitDiffHunk] = []
    current_hunk: GitDiffHunk | None = None
    hunk_index = 0

    idx = 0
    while idx < len(lines):
        line = lines[idx]

        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                old_path = _clean_diff_path(parts[2])
                new_path = _clean_diff_path(parts[3])

        elif line.startswith("new file mode"):
            change_type = CodeChangeType.ADD

        elif line.startswith("deleted file mode"):
            change_type = CodeChangeType.DELETE

        elif line.startswith("rename from "):
            old_path = line[len("rename from ") :].strip()
            change_type = CodeChangeType.RENAME

        elif line.startswith("rename to "):
            new_path = line[len("rename to ") :].strip()
            change_type = CodeChangeType.RENAME

        elif line.startswith("--- "):
            raw_old = line[4:].strip()
            if raw_old == "/dev/null":
                change_type = CodeChangeType.ADD
            elif not old_path:
                old_path = _clean_diff_path(raw_old)

        elif line.startswith("+++ "):
            raw_new = line[4:].strip()
            if raw_new == "/dev/null":
                change_type = CodeChangeType.DELETE
            elif not new_path:
                new_path = _clean_diff_path(raw_new)

        elif line.startswith("@@"):
            # Close previous hunk if open
            if current_hunk is not None:
                hunks.append(current_hunk)

            match = HUNK_HEADER_REGEX.match(line)
            if match:
                hunk_index += 1
                old_start = int(match.group("old_start"))
                old_count = int(match.group("old_count")) if match.group("old_count") else 1
                new_start = int(match.group("new_start"))
                new_count = int(match.group("new_count")) if match.group("new_count") else 1
                heading = match.group("heading")
                section_header = heading.strip() if heading else None

                current_hunk = GitDiffHunk(
                    hunk_index=hunk_index,
                    header=line,
                    section_header=section_header,
                    old_start_line=old_start,
                    old_line_count=old_count,
                    new_start_line=new_start,
                    new_line_count=new_count,
                    lines=[],
                    added_lines=[],
                    deleted_lines=[],
                    context_lines=[],
                )
            else:
                current_hunk = None

        elif current_hunk is not None:
            if line.startswith("+"):
                current_hunk.lines.append(line)
                current_hunk.added_lines.append(line[1:])
            elif line.startswith("-"):
                current_hunk.lines.append(line)
                current_hunk.deleted_lines.append(line[1:])
            elif line.startswith(" "):
                current_hunk.lines.append(line)
                current_hunk.context_lines.append(line[1:])
            elif line.startswith("\\ No newline at end of file"):
                pass
            else:
                # Context or comment line without leading space
                current_hunk.lines.append(" " + line)
                current_hunk.context_lines.append(line)

        idx += 1

    if current_hunk is not None:
        hunks.append(current_hunk)

    effective_path = new_path or old_path or "unknown_file"

    return GitFileDiff(
        old_path=old_path,
        new_path=effective_path,
        change_type=change_type,
        hunks=hunks,
        raw_patch=raw_patch,
    )
